"""Detect step — identifies file type, codec, duration, and language via ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job, MediaInfo, MediaType
from mediascribe.steps.base import PipelineStep, StepResult


def probe_file(path: Path) -> MediaInfo:
    """Run ffprobe on a file and return structured MediaInfo."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(r.stdout)

    info = MediaInfo()

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            info.media_type = MediaType.VIDEO
            info.codec_video = stream.get("codec_name")
            info.width = int(stream.get("width", 0)) or None
            info.height = int(stream.get("height", 0)) or None
        elif codec_type == "audio":
            if info.media_type == MediaType.UNKNOWN:
                info.media_type = MediaType.AUDIO
            info.codec_audio = stream.get("codec_name")
            info.sample_rate = int(stream.get("sample_rate", 0)) or None
            info.channels = int(stream.get("channels", 0)) or None

    fmt = data.get("format", {})
    info.duration_sec = float(fmt.get("duration", 0))

    return info


class DetectStep(PipelineStep):
    """Detect media type, codec, duration, and other file metadata."""

    name = "detect"
    description = "Detecting file type and metadata"

    def execute(
        self,
        job: Job,
        settings: MediascribeSettings,
        events: EventBus,
    ) -> StepResult:
        info = probe_file(job.input_path)
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
