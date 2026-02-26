"""Diarize step — speaker attribution via pyannote.audio.

Assigns speaker labels to each segment based on audio analysis.
Requires pyannote.audio >= 3.0 and a HuggingFace token (free,
but the model is gated and requires license acceptance).

GPU is recommended but CPU works (significantly slower).
"""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.steps.base import PipelineStep, StepResult


def _assign_speakers(
    segments: list[dict],
    diarization_result: object,
) -> dict[int, str]:
    """Map diarization speaker turns to transcription segments.

    For each segment, find which speaker is talking for the majority
    of its time span. Uses the pyannote Timeline/Annotation interface.
    """
    speaker_map: dict[int, str] = {}

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_idx = seg["index"]

        speaker_times: dict[str, float] = {}
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            overlap_start = max(seg_start, turn.start)
            overlap_end = min(seg_end, turn.end)
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > 0:
                speaker_times[speaker] = speaker_times.get(speaker, 0.0) + overlap

        if speaker_times:
            best_speaker = max(speaker_times, key=speaker_times.get)
            speaker_map[seg_idx] = _format_speaker_label(best_speaker)

    return speaker_map


def _format_speaker_label(raw_label: str) -> str:
    """Convert pyannote labels (SPEAKER_00) to readable form (Speaker 1)."""
    if raw_label.startswith("SPEAKER_"):
        num = int(raw_label.split("_")[1]) + 1
        return f"Speaker {num}"
    return raw_label


class DiarizeStep(PipelineStep):
    """Speaker diarization — assign speaker labels to segments.

    Uses pyannote.audio to identify speaker turns, then maps them
    to existing transcription segments via time overlap.

    Modifies job.segments in-place by setting the speaker field.
    """

    name = "diarize"
    description = "Identifying speakers"
    required = False

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if not job.audio_path or not job.audio_path.exists():
            events.warn("No audio file — skipping diarization", step=self.name)
            return StepResult(data={"skipped": True})

        if not job.segments:
            events.warn("No segments to diarize", step=self.name)
            return StepResult(data={"skipped": True})

        hf_token = (
            settings.huggingface_token.get_secret_value()
            if settings.huggingface_token else None
        )
        if not hf_token:
            events.warn(
                "No HuggingFace token — skipping diarization. "
                "Set MEDIASCRIBE_HUGGINGFACE_TOKEN to enable.",
                step=self.name,
            )
            return StepResult(data={"skipped": True, "reason": "no_token"})

        try:
            from pyannote.audio import Pipeline as PyannotePipeline
        except ImportError:
            events.warn(
                "pyannote.audio not installed. "
                "Install with: pip install mediascribe[diarize]",
                step=self.name,
            )
            return StepResult(data={"skipped": True, "reason": "not_installed"})

        events.log("Loading diarization model...", step=self.name)

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name=self.name,
            message="Loading pyannote model",
            progress=0.1,
        ))

        pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name=self.name,
            message="Running diarization",
            progress=0.3,
        ))

        diarization = pipeline(str(job.audio_path))

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name=self.name,
            message="Mapping speakers to segments",
            progress=0.8,
        ))

        seg_dicts = [
            {"index": s.index, "start": s.start, "end": s.end}
            for s in job.segments
        ]
        speaker_map = _assign_speakers(seg_dicts, diarization)

        assigned = 0
        unique_speakers: set[str] = set()
        for seg in job.segments:
            if seg.index in speaker_map:
                seg.speaker = speaker_map[seg.index]
                unique_speakers.add(seg.speaker)
                assigned += 1

        events.log(
            f"Assigned {assigned}/{len(job.segments)} segments to "
            f"{len(unique_speakers)} speakers",
            step=self.name,
        )

        return StepResult(data={
            "speakers": sorted(unique_speakers),
            "assigned_count": assigned,
        })

    def can_skip(self, job: Job) -> bool:
        """Skip if segments already have speaker labels."""
        if not job.segments:
            return False
        return any(s.speaker for s in job.segments)
