"""Translate step — AI-powered batched translation via OpenAI.

Translates source-language subtitles to the target language using
configurable prompt templates (profile-based) with context overlap
between batches for continuity.

Produces a draft translation SRT with the same timing as the source.
"""

from __future__ import annotations

import json
from pathlib import Path

from pysrt import SubRipFile, SubRipItem

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.formats.srt import read_srt, save_srt
from mediascribe.models.openai_client import call_openai_json, get_client
from mediascribe.models.prompts import TEMPLATES, render_prompt
from mediascribe.steps.base import PipelineStep, StepResult


# ── Translation Logic ────────────────────────────────────────────────────────


def translate_subtitles(
    source_srt: SubRipFile,
    system_prompt: str,
    model: str,
    api_key: str | None = None,
    batch_size: int = 15,
    batch_overlap: int = 2,
    events: EventBus | None = None,
) -> dict[int, str]:
    """Translate all subtitles with batched API calls.

    Args:
        source_srt: Source-language SubRipFile.
        system_prompt: System prompt with translation instructions.
        model: OpenAI model name for translation.
        api_key: Optional API key (uses env var if not provided).
        batch_size: Number of subtitles per API call.
        batch_overlap: Overlap between batches for context continuity.
        events: Optional event bus for progress reporting.

    Returns:
        Dict mapping subtitle ID → translated text.
    """
    client = get_client(api_key)
    items = [{"id": i + 1, "text": sub.text.strip()} for i, sub in enumerate(source_srt)]

    translated: dict[int, str] = {}
    step = batch_size - batch_overlap
    total_batches = max(1, (len(items) + step - 1) // step)

    for batch_num, start in enumerate(range(0, len(items), step), 1):
        batch = items[start: start + batch_size]
        id_range = f"{batch[0]['id']}–{batch[-1]['id']}"

        if events:
            events.emit(PipelineEvent(
                type=EventType.STEP_PROGRESS,
                step_name="translate",
                message=f"Batch {batch_num}/{total_batches} (subs {id_range})",
                progress=batch_num / total_batches,
            ))

        try:
            result = call_openai_json(client, model, system_prompt, batch)
            for item in result:
                if item["id"] not in translated:
                    translated[item["id"]] = item["text"]
        except (json.JSONDecodeError, KeyError) as e:
            if events:
                events.warn(f"Batch error ({e}), falling back line-by-line", step="translate")
            # Fallback: translate one at a time
            for item in batch:
                if item["id"] in translated:
                    continue
                try:
                    single = call_openai_json(client, model, system_prompt, [item])
                    translated[single[0]["id"]] = single[0]["text"]
                except Exception:
                    translated[item["id"]] = item["text"]  # keep source as fallback

    return translated


def build_translated_srt(source_srt: SubRipFile, translations: dict[int, str]) -> SubRipFile:
    """Build a translated SRT using source timing and translated text."""
    out = SubRipFile()
    for i, sub in enumerate(source_srt):
        out.append(SubRipItem(
            index=i + 1,
            start=sub.start,
            end=sub.end,
            text=translations.get(i + 1, sub.text),
        ))
    return out


# ── Pipeline Step ────────────────────────────────────────────────────────────


class TranslateStep(PipelineStep):
    """First-pass translation: source → target language.

    Uses the profile's translation prompt template, merged with any
    custom instructions from settings.

    Output: <stem>_<target>_draft.srt in the job's output directory.
    """

    name = "translate"
    description = "Translating subtitles"

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if not settings.target_language:
            events.log("No target language set — skipping translation", step=self.name)
            return StepResult(data={"skipped": True})

        # Find source SRT
        source_lang = settings.source_language or "unknown"
        source_srt_path = job.output_dir / f"{job.stem}_{source_lang}.srt"
        if not source_srt_path.exists():
            # Try to find any source SRT
            candidates = [p for p in job.output_dir.glob(f"{job.stem}_*.srt")
                          if "_en" not in p.stem and "_draft" not in p.stem]
            if candidates:
                source_srt_path = candidates[0]
            else:
                raise FileNotFoundError(f"No source SRT found for {job.stem}")

        target = settings.target_language
        draft_path = job.output_dir / f"{job.stem}_{target}_draft.srt"

        template = TEMPLATES.get(settings.profile, TEMPLATES["general"])
        system_prompt, _ = render_prompt(
            template, target, settings.custom_instructions,
        )

        events.log(f"Model: {settings.translation_model}", step=self.name)

        source_srt = read_srt(source_srt_path)
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None

        translations = translate_subtitles(
            source_srt=source_srt,
            system_prompt=system_prompt,
            model=settings.translation_model,
            api_key=api_key,
            batch_size=settings.translation_batch_size,
            events=events,
        )

        translated_srt = build_translated_srt(source_srt, translations)
        save_srt(translated_srt, draft_path)

        # Also update job segments with translations
        for seg in job.segments:
            if seg.index in translations:
                seg.translation = translations[seg.index]

        events.log(
            f"Draft translation → {draft_path.name} ({len(translated_srt)} subs)",
            step=self.name,
        )

        return StepResult(data={
            "draft_path": str(draft_path),
            "translated_count": len(translations),
        })

    def can_skip(self, job: Job) -> bool:
        """Skip if draft translation SRT already exists."""
        for p in job.output_dir.glob(f"{job.stem}_*_draft.srt"):
            return True
        return False
