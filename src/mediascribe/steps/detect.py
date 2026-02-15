"""Detect step — identifies file type, codec, duration, and language via ffprobe."""

from __future__ import annotations

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job, MediaInfo, MediaType
from mediascribe.steps.base import PipelineStep, StepResult
from mediascribe.utils.ffmpeg import probe_file


class DetectStep(PipelineStep):
    """Detect media type, codec, duration, and other file metadata."""

    name = "detect"
    description = "Detecting file type and metadata"

    async def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus
    ) -> StepResult:
        info = await probe_file(job.input_path)
        job.media_info = info
        events.log(
            f"Detected: {info.media_type.value} | "
            f"{job.duration_str} | "
            f"{info.codec_audio or 'no audio'}",
            step=self.name,
        )
        return StepResult(data={"media_type": info.media_type.value})

    def can_skip(self, job: Job) -> bool:
        return job.media_info.media_type != MediaType.UNKNOWN
