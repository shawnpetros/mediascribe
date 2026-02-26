"""Diarize step — speaker attribution via pyannote.audio.

Requires the optional ``diarize`` extra:
    pip install mediascribe[diarize]

Which installs pyannote.audio >= 3.0.  A HuggingFace token with accepted
model license is needed (set via ``huggingface_token`` config or
``MEDIASCRIBE_HUGGINGFACE_TOKEN`` env var).

The step runs the pyannote speaker-diarization pipeline on the
normalised audio file, then assigns speaker labels to each segment
based on temporal overlap.
"""

from __future__ import annotations

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job
from mediascribe.steps.base import PipelineStep, StepResult


def _find_speaker(
    seg_start: float, seg_end: float, turns: list[tuple[float, float, str]]
) -> str | None:
    """Find the speaker with the most temporal overlap for a segment."""
    best_speaker: str | None = None
    best_overlap = 0.0

    for turn_start, turn_end, speaker in turns:
        overlap_start = max(seg_start, turn_start)
        overlap_end = min(seg_end, turn_end)
        overlap = max(0.0, overlap_end - overlap_start)

        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker

    return best_speaker


class DiarizeStep(PipelineStep):
    """Speaker diarization — assigns speaker labels to segments.

    Uses pyannote.audio's pretrained speaker-diarization-3.1 pipeline
    to segment the audio by speaker, then labels each transcription
    segment with the dominant speaker in its time range.

    Output: Updates ``seg.speaker`` on each ``job.segments`` entry.
    """

    name = "diarize"
    description = "Identifying speakers"
    required = False

    def execute(
        self,
        job: Job,
        settings: MediascribeSettings,
        events: EventBus,
    ) -> StepResult:
        try:
            from pyannote.audio import Pipeline as PyannotePipeline
        except ImportError:
            events.warn(
                "pyannote.audio not installed — install with: pip install mediascribe[diarize]",
                step=self.name,
            )
            return StepResult(data={"skipped": True, "reason": "pyannote not installed"})

        if not job.audio_path or not job.audio_path.exists():
            events.warn("No normalised audio file found — skipping diarization", step=self.name)
            return StepResult(data={"skipped": True, "reason": "no audio"})

        if not job.segments:
            events.warn("No segments to label — skipping diarization", step=self.name)
            return StepResult(data={"skipped": True, "reason": "no segments"})

        hf_token: str | None = None
        if settings.huggingface_token:
            hf_token = settings.huggingface_token.get_secret_value()

        if not hf_token:
            events.warn(
                "HuggingFace token not set — required for diarization. "
                "Set MEDIASCRIBE_HUGGINGFACE_TOKEN or huggingface_token in config.",
                step=self.name,
            )
            return StepResult(data={"skipped": True, "reason": "no HF token"})

        events.log("Loading pyannote speaker-diarization pipeline...", step=self.name)

        try:
            pipeline = PyannotePipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
        except Exception as exc:
            events.warn(f"Failed to load diarization model: {exc}", step=self.name)
            return StepResult(data={"skipped": True, "reason": str(exc)})

        events.log(f"Running diarization on {job.audio_path.name}...", step=self.name)
        diarization = pipeline(str(job.audio_path))

        # Extract speaker turns as (start, end, speaker) tuples
        turns: list[tuple[float, float, str]] = []
        speaker_set: set[str] = set()

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            turns.append((turn.start, turn.end, speaker))
            speaker_set.add(speaker)

        events.log(f"Found {len(speaker_set)} speakers, {len(turns)} turns", step=self.name)

        # Assign speaker labels to segments
        labeled_count = 0
        for seg in job.segments:
            speaker = _find_speaker(seg.start, seg.end, turns)
            if speaker:
                seg.speaker = speaker
                labeled_count += 1

        events.log(
            f"Labeled {labeled_count}/{len(job.segments)} segments with speakers",
            step=self.name,
        )

        return StepResult(
            data={
                "speakers": sorted(speaker_set),
                "speaker_count": len(speaker_set),
                "turn_count": len(turns),
                "labeled_segments": labeled_count,
            }
        )

    def can_skip(self, job: Job) -> bool:
        return all(seg.speaker is not None for seg in job.segments) if job.segments else False
