"""Job model — represents one file being processed through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    UNKNOWN = "unknown"


@dataclass
class MediaInfo:
    """Detected information about the input file."""

    media_type: MediaType = MediaType.UNKNOWN
    duration_sec: float = 0.0
    codec_video: str | None = None
    codec_audio: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    language: str | None = None  # auto-detected source language
    width: int | None = None
    height: int | None = None


@dataclass
class Segment:
    """A single transcribed/translated segment."""

    index: int
    start: float  # seconds
    end: float  # seconds
    text: str
    translation: str | None = None
    speaker: str | None = None
    confidence: float | None = None


@dataclass
class Job:
    """One file being processed through the pipeline.

    Accumulates results as each step completes. Steps read from and write to
    the Job, making it the central data object for the pipeline.
    """

    # Input
    input_path: Path
    output_dir: Path

    # Detected metadata (populated by detect step)
    media_info: MediaInfo = field(default_factory=MediaInfo)

    # Intermediate files (populated by normalize step)
    audio_path: Path | None = None

    # Results (populated by transcribe/translate/analyze steps)
    segments: list[Segment] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)

    # State
    status: JobStatus = JobStatus.PENDING
    current_step: str | None = None
    error: str | None = None

    @property
    def stem(self) -> str:
        """Input filename without extension."""
        return self.input_path.stem

    @property
    def duration_str(self) -> str:
        """Duration as MM:SS string."""
        d = self.media_info.duration_sec
        return f"{int(d // 60):02d}:{int(d % 60):02d}"
