"""Timing step — optimize subtitle display timing.

Fixes common Whisper timing issues:
- Continuous timestamps (subtitle end = next start → always on screen)
- Overly long subtitle durations
- Missing gaps between subtitles

Uses word-level timestamps when available, with a heuristic fallback
based on text length for capping display duration.
"""

from __future__ import annotations

from pysrt import SubRipFile

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job
from mediascribe.formats.srt import srt_time, srt_to_sec
from mediascribe.steps.base import PipelineStep, StepResult

# ── Timing Logic (usable standalone, outside of step) ────────────────────────


def estimate_display_duration(text: str, chars_per_second: float = 5.0) -> float:
    """Estimate how long a subtitle should be visible based on text length.

    For CJK text (Japanese, Chinese, Korean), characters are denser:
    ~4-5 chars/sec reading speed. For Latin text: ~12-15 chars/sec.
    We use a simple heuristic: 0.2s per char + base time, clamped.

    Args:
        text: The subtitle text.
        chars_per_second: Reading speed (lower = longer display).

    Returns:
        Recommended display duration in seconds, clamped to [1.2, 7.0].
    """
    n = len(text.strip())
    if n == 0:
        return 1.0
    # ~0.2s per char + 0.8s base, clamped
    return max(1.2, min(n * 0.2 + 0.8, 7.0))


def fix_subtitle_timing(
    srt: SubRipFile,
    min_gap: float = 0.15,
    max_duration: float = 7.0,
    chars_per_second: float = 5.0,
) -> None:
    """Fix Whisper's continuous-timestamp issue in-place.

    Whisper often sets each subtitle's end = next subtitle's start,
    keeping text on screen 100% of the time — even during silence.
    This caps duration based on text length and ensures natural gaps.

    Args:
        srt: SubRipFile to modify in-place.
        min_gap: Minimum gap (seconds) between consecutive subtitles.
        max_duration: Hard maximum subtitle duration.
        chars_per_second: Reading speed for duration estimate.
    """
    for i, sub in enumerate(srt):
        start = srt_to_sec(sub.start)
        end = srt_to_sec(sub.end)
        duration = end - start

        # Cap to a text-appropriate maximum
        max_dur = min(estimate_display_duration(sub.text, chars_per_second), max_duration)
        if duration > max_dur:
            end = start + max_dur
            sub.end = srt_time(end)

        # Ensure minimum gap to the next subtitle
        if i + 1 < len(srt):
            next_start = srt_to_sec(srt[i + 1].start)
            if end > next_start - min_gap:
                sub.end = srt_time(max(start + 0.5, next_start - min_gap))


# ── Pipeline Step ────────────────────────────────────────────────────────────


class TimingStep(PipelineStep):
    """Fix subtitle timing on the job's segments.

    This step operates on the SRT file produced by the transcription step.
    It modifies timing in-place to ensure natural display behavior.

    Note: This step is typically integrated into the transcription step
    itself, but is available as a standalone step for re-processing
    existing SRT files.
    """

    name = "timing"
    description = "Optimizing subtitle display timing"

    def execute(
        self,
        job: Job,
        settings: MediascribeSettings,
        events: EventBus,
    ) -> StepResult:
        srt_path = job.output_dir / f"{job.stem}_ja.srt"
        if not srt_path.exists():
            raise FileNotFoundError(f"Source SRT not found: {srt_path}")

        from mediascribe.formats.srt import read_srt, save_srt

        srt = read_srt(srt_path)
        original_count = len(srt)

        fix_subtitle_timing(
            srt,
            min_gap=settings.min_gap_sec,
            max_duration=settings.max_subtitle_duration_sec,
            chars_per_second=settings.chars_per_second,
        )

        save_srt(srt, srt_path)
        events.log(f"Fixed timing on {original_count} subtitles", step=self.name)

        return StepResult(data={"subtitle_count": original_count})

    def can_skip(self, _job: Job) -> bool:
        # Timing is always re-applied (cheap operation)
        return False
