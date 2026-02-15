"""Normalize step — extract and standardize audio for transcription.

For video input: extracts the audio track as 16kHz mono WAV.
For audio input: converts to 16kHz mono WAV if not already.

The output WAV file is the standard input for all transcription modes.
"""

from __future__ import annotations

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, MediaType
from mediascribe.steps.base import PipelineStep, StepResult
from mediascribe.utils.ffmpeg import extract_audio


class NormalizeStep(PipelineStep):
    """Extract/normalize audio to 16kHz mono WAV."""

    name = "normalize"
    description = "Extracting audio for transcription"

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if job.media_info.media_type == MediaType.UNKNOWN:
            raise RuntimeError("Cannot normalize: unknown media type. Run detect step first.")

        # Output WAV path: <output_dir>/<stem>.wav
        wav_path = job.output_dir / f"{job.stem}.wav"

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name=self.name,
            message=f"Extracting audio → {wav_path.name}",
            progress=0.1,
        ))

        extract_audio(
            input_path=job.input_path,
            output_path=wav_path,
            sample_rate=16000,
            channels=1,
        )

        job.audio_path = wav_path
        events.log(f"Audio extracted → {wav_path.name}", step=self.name)

        return StepResult(data={"audio_path": str(wav_path)})

    def can_skip(self, job: Job) -> bool:
        """Skip if the WAV already exists."""
        wav_path = job.output_dir / f"{job.stem}.wav"
        if wav_path.exists():
            job.audio_path = wav_path  # Populate job even when skipping
            return True
        return False
