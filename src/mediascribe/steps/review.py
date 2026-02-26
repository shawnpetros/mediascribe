"""Review step — second-pass AI quality check on translations.

Sends source + draft translation side-by-side to a reviewer prompt
that checks for consistency, accuracy, tone, and formatting issues.

This is the final quality gate before output.
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


# ── Review Logic ─────────────────────────────────────────────────────────────

REVIEW_BATCH_SIZE = 20


def review_translations(
    source_srt: SubRipFile,
    draft_srt: SubRipFile,
    review_prompt: str,
    model: str,
    api_key: str | None = None,
    batch_size: int = REVIEW_BATCH_SIZE,
    events: EventBus | None = None,
) -> dict[int, str]:
    """Review and correct translations via AI second pass.

    Sends source + draft side-by-side in batches. The AI checks for
    consistency, accuracy, and tone issues.

    Args:
        source_srt: Original source-language SRT.
        draft_srt: Draft translated SRT.
        review_prompt: System prompt for the reviewer.
        model: OpenAI model name.
        api_key: Optional API key.
        batch_size: Lines per review API call.
        events: Optional event bus for progress.

    Returns:
        Dict mapping subtitle ID → reviewed text.
    """
    client = get_client(api_key)

    pairs = [
        {
            "id": i + 1,
            "ja": source_srt[i].text.strip(),
            "en": draft_srt[i].text.strip(),
        }
        for i in range(min(len(source_srt), len(draft_srt)))
    ]

    reviewed: dict[int, str] = {}
    total_batches = max(1, (len(pairs) + batch_size - 1) // batch_size)

    for batch_num, start in enumerate(range(0, len(pairs), batch_size), 1):
        batch = pairs[start: start + batch_size]
        id_range = f"{batch[0]['id']}–{batch[-1]['id']}"

        if events:
            events.emit(PipelineEvent(
                type=EventType.STEP_PROGRESS,
                step_name="review",
                message=f"Reviewing {batch_num}/{total_batches} (subs {id_range})",
                progress=batch_num / total_batches,
            ))

        try:
            result = call_openai_json(client, model, review_prompt, batch, temp=0.2)
            for item in result:
                reviewed[item["id"]] = item["text"]
        except (json.JSONDecodeError, KeyError):
            if events:
                events.warn(f"Parse error in review batch — keeping drafts", step="review")
            for item in batch:
                reviewed[item["id"]] = item["en"]

    return reviewed


# ── Pipeline Step ────────────────────────────────────────────────────────────


class ReviewStep(PipelineStep):
    """Second-pass quality review of translated subtitles.

    Reads source SRT + draft translated SRT, sends them to the AI
    reviewer, and outputs the final reviewed SRT.

    Output: <stem>_<target>.srt in the job's output directory.
    """

    name = "review"
    description = "Reviewing translation quality"

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if not settings.target_language:
            events.log("No target language — skipping review", step=self.name)
            return StepResult(data={"skipped": True})

        if not settings.enable_review_pass:
            events.log("Review pass disabled", step=self.name)
            return StepResult(data={"skipped": True})

        target = settings.target_language
        source_lang = settings.source_language or "unknown"

        # Find source and draft SRTs
        source_srt_path = job.output_dir / f"{job.stem}_{source_lang}.srt"
        draft_path = job.output_dir / f"{job.stem}_{target}_draft.srt"
        final_path = job.output_dir / f"{job.stem}_{target}.srt"

        if not source_srt_path.exists():
            candidates = [p for p in job.output_dir.glob(f"{job.stem}_*.srt")
                          if "_en" not in p.stem and "_draft" not in p.stem]
            if candidates:
                source_srt_path = candidates[0]
            else:
                raise FileNotFoundError(f"No source SRT for {job.stem}")

        if not draft_path.exists():
            raise FileNotFoundError(f"No draft SRT found: {draft_path}")

        template = TEMPLATES.get(settings.profile, TEMPLATES["general"])
        _, review_prompt = render_prompt(
            template, target, settings.custom_instructions,
        )

        events.log(f"Model: {settings.translation_model}", step=self.name)

        source_srt = read_srt(source_srt_path)
        draft_srt = read_srt(draft_path)
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None

        reviewed = review_translations(
            source_srt=source_srt,
            draft_srt=draft_srt,
            review_prompt=review_prompt,
            model=settings.translation_model,
            api_key=api_key,
            events=events,
        )

        # Build final SRT with source timing
        final_srt = SubRipFile()
        for i, sub in enumerate(source_srt):
            text = reviewed.get(i + 1, draft_srt[i].text if i < len(draft_srt) else "")
            final_srt.append(SubRipItem(
                index=i + 1,
                start=sub.start,
                end=sub.end,
                text=text,
            ))

        save_srt(final_srt, final_path)

        # Update job segments
        for seg in job.segments:
            if seg.index in reviewed:
                seg.translation = reviewed[seg.index]

        events.log(
            f"Final subtitles → {final_path.name} ({len(final_srt)} subs)",
            step=self.name,
        )

        return StepResult(data={
            "final_path": str(final_path),
            "reviewed_count": len(reviewed),
        })

    def can_skip(self, job: Job) -> bool:
        """Skip if final (non-draft) translation SRT exists."""
        if not hasattr(job, '_settings_cache'):
            return False
        # Look for final SRT (not draft)
        for p in job.output_dir.glob(f"{job.stem}_*.srt"):
            if "_draft" not in p.stem and p.stem != f"{job.stem}_{job.media_info.language or 'unknown'}":
                return True
        return False
