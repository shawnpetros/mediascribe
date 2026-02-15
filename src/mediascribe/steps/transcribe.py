"""Transcribe step — speech-to-text via local Whisper or OpenAI API.

Supports two modes:
- **local**: Chunked transcription via faster-whisper with loop/hallucination
  detection, validation, and retry with escalating anti-hallucination params.
- **api**: Single-shot transcription via OpenAI's Whisper API (faster, costs money).

Both modes produce the same output: a list of segments with start/end/text,
which are written to a source-language SRT file with optimized timing.
"""

from __future__ import annotations

import re
import shutil
import time
from collections import Counter
from pathlib import Path

from pysrt import SubRipFile, SubRipItem

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, Segment
from mediascribe.formats.srt import dicts_to_srt, fmt_ts, save_srt, srt_time
from mediascribe.steps.base import PipelineStep, StepResult
from mediascribe.steps.timing import fix_subtitle_timing
from mediascribe.utils.ffmpeg import probe_duration, split_audio


# ── Validation ───────────────────────────────────────────────────────────────


MAX_RETRIES = 3


def validate_segments(segs: list[dict]) -> tuple[bool, str]:
    """Check for hallucination patterns in transcription output.

    Returns:
        (ok, reason) — ok is True if segments look clean.
    """
    if len(segs) < 4:
        return True, "ok"

    texts = [s["text"] for s in segs]

    # Check for consecutive identical lines (hallucination signature)
    run_len, max_run = 1, 1
    for i in range(1, len(texts)):
        if texts[i] == texts[i - 1]:
            run_len += 1
            max_run = max(max_run, run_len)
        else:
            run_len = 1
    if max_run >= 4:
        return False, f"loop: {max_run}× consecutive repeats"

    # Check if one line dominates >35% of output
    c = Counter(texts)
    top_text, top_n = c.most_common(1)[0]
    if top_n > len(texts) * 0.35 and len(texts) > 6:
        return False, f"dominant: '{top_text[:30]}…' ({top_n}/{len(texts)})"

    # Suspiciously short average text
    avg_len = sum(len(t) for t in texts) / len(texts)
    if avg_len < 2 and len(texts) > 5:
        return False, f"avg text too short ({avg_len:.1f} chars)"

    return True, "ok"


# ── Post-processing ──────────────────────────────────────────────────────────


def _deduplicate_segments(segments: list[dict]) -> list[dict]:
    """Sort and deduplicate segments at chunk boundaries."""
    segments.sort(key=lambda s: s["start"])
    deduped: list[dict] = []

    for s in segments:
        if deduped:
            prev = deduped[-1]
            # Same text and nearly same timestamp → merge
            if s["text"] == prev["text"] and abs(s["start"] - prev["start"]) < 2.0:
                prev["end"] = max(prev["end"], s["end"])
                continue
            # Same text, overlapping → skip
            if s["text"] == prev["text"] and s["start"] < prev["end"] + 0.5:
                continue
        deduped.append(s)

    return deduped


def _clean_segments(segments: list[dict]) -> list[dict]:
    """Remove artifacts and clean up Whisper output."""
    clean: list[dict] = []
    prev_text = ""

    for s in segments:
        t = s["text"].strip()
        if not t or t in (",", "。", ".", "、"):
            continue
        if t == prev_text:  # consecutive duplicate
            continue
        s["text"] = t
        clean.append(s)
        prev_text = t

    return clean


# ── Local Transcription (chunked) ────────────────────────────────────────────


def _transcribe_local(
    wav_path: Path,
    output_dir: Path,
    settings: MediascribeSettings,
    events: EventBus,
    stem: str,
) -> list[dict]:
    """Chunked local transcription with loop detection and retries."""
    from mediascribe.models.whisper_local import transcribe_chunk

    dur = probe_duration(wav_path)
    chunk_sec = settings.chunk_duration_sec
    n_chunks = int(dur // chunk_sec) + (1 if dur % chunk_sec > 0 else 0)

    events.log(
        f"Duration: {fmt_ts(dur)} | {n_chunks} chunks × {chunk_sec}s",
        step="transcribe",
    )

    # Split WAV into chunks
    chunk_dir = output_dir / "_chunks" / stem
    chunks = split_audio(wav_path, chunk_dir, chunk_sec)
    events.log(f"Split into {len(chunks)} chunks", step="transcribe")

    # Transcribe each chunk
    all_segments: list[dict] = []
    chunk_times: list[float] = []

    for ci, chunk_path in enumerate(chunks):
        offset = ci * chunk_sec
        end_sec = min(offset + chunk_sec, dur)
        label = f"Chunk {ci + 1}/{len(chunks)}  {fmt_ts(offset)}→{fmt_ts(end_sec)}"

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name="transcribe",
            message=label,
            progress=(ci / len(chunks)),
        ))

        ct0 = time.time()
        segs = None

        for retry in range(MAX_RETRIES):
            attempt = transcribe_chunk(
                chunk_path=chunk_path,
                offset=offset,
                language=settings.source_language,
                vocab_prompt="",  # set via profile/config
                model_name=settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute,
                retry=retry,
                word_timestamps=settings.word_timestamps,
            )
            ok, reason = validate_segments(attempt)

            if ok:
                segs = attempt
                if retry > 0:
                    events.log(f"Retry {retry} passed validation", step="transcribe")
                break
            else:
                events.warn(
                    f"Attempt {retry + 1}/{MAX_RETRIES}: {reason}",
                    step="transcribe",
                )

        if segs is None:
            events.warn("All retries failed — using last attempt", step="transcribe")
            segs = attempt  # type: ignore[assignment]

        ct_elapsed = time.time() - ct0
        chunk_times.append(ct_elapsed)
        avg_time = sum(chunk_times) / len(chunk_times)
        remaining = avg_time * (len(chunks) - ci - 1)

        events.log(
            f"{len(segs)} segments | {ct_elapsed:.0f}s | ETA: {fmt_ts(remaining)}",
            step="transcribe",
        )

        all_segments.extend(segs)

    # Cleanup chunk files
    if chunk_dir.exists():
        shutil.rmtree(chunk_dir)
    chunks_root = chunk_dir.parent
    if chunks_root.exists() and not any(chunks_root.iterdir()):
        chunks_root.rmdir()

    return all_segments


# ── API Transcription ────────────────────────────────────────────────────────


def _transcribe_api(
    wav_path: Path,
    settings: MediascribeSettings,
    events: EventBus,
) -> list[dict]:
    """Transcribe via OpenAI Whisper API."""
    from mediascribe.models.whisper_api import transcribe_via_api
    from mediascribe.models.openai_client import get_client

    dur = probe_duration(wav_path)
    cost = dur / 60 * 0.006

    events.log(
        f"Duration: {fmt_ts(dur)} | Est. cost: ${cost:.3f}",
        step="transcribe",
    )

    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    client = get_client(api_key)

    events.emit(PipelineEvent(
        type=EventType.STEP_PROGRESS,
        step_name="transcribe",
        message="Uploading and transcribing via API…",
        progress=0.3,
    ))

    segments = transcribe_via_api(
        audio_path=wav_path,
        client=client,
        language=settings.source_language,
    )

    # Validate even API output
    ok, reason = validate_segments(segments)
    if not ok:
        events.warn(f"Validation: {reason} — keeping (API generally reliable)", step="transcribe")

    return segments


# ── Pipeline Step ────────────────────────────────────────────────────────────


class TranscribeStep(PipelineStep):
    """Transcribe audio to source-language SRT.

    Supports local (chunked faster-whisper) and API (OpenAI) modes.
    Output: <stem>_<lang>.srt in the job's output directory.
    Also populates job.segments with Segment objects.
    """

    name = "transcribe"
    description = "Transcribing audio to text"

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if not job.audio_path or not job.audio_path.exists():
            raise FileNotFoundError("No audio file found. Run normalize step first.")

        lang = settings.source_language or "unknown"
        srt_path = job.output_dir / f"{job.stem}_{lang}.srt"
        stem = job.stem

        # Choose transcription mode
        mode = settings.transcription_mode
        if mode == "auto":
            # Default to local if no API key, otherwise local (user can override)
            mode = "local"

        events.log(f"Mode: {mode} | Model: {settings.whisper_model}", step=self.name)

        if mode == "api":
            raw_segments = _transcribe_api(job.audio_path, settings, events)
        else:
            raw_segments = _transcribe_local(
                job.audio_path, job.output_dir, settings, events, stem,
            )

        # Post-process
        deduped = _deduplicate_segments(raw_segments)
        clean = _clean_segments(deduped)

        events.log(
            f"Raw: {len(raw_segments)} → Deduped: {len(deduped)} → Clean: {len(clean)}",
            step=self.name,
        )

        # Build SRT and fix timing
        srt = dicts_to_srt(clean)
        fix_subtitle_timing(
            srt,
            min_gap=settings.min_gap_sec,
            max_duration=settings.max_subtitle_duration_sec,
        )
        save_srt(srt, srt_path)

        # Populate job segments
        job.segments = [
            Segment(
                index=i + 1,
                start=s["start"],
                end=s["end"],
                text=s["text"],
            )
            for i, s in enumerate(clean)
        ]

        events.log(f"{len(srt)} subtitles → {srt_path.name}", step=self.name)

        return StepResult(data={
            "srt_path": str(srt_path),
            "segment_count": len(clean),
            "mode": mode,
        })

    def can_skip(self, job: Job) -> bool:
        """Skip if SRT already exists."""
        from mediascribe.formats.srt import srt_to_segments

        lang = "unknown"  # We don't have settings here, check any matching SRT
        # Look for any *_*.srt file matching the stem
        for p in job.output_dir.glob(f"{job.stem}_*.srt"):
            if "_en" not in p.stem:  # Skip translation SRTs
                job.segments = srt_to_segments(p)
                return True
        return False
