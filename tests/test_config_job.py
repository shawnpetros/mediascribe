"""Tests for config and job models.

Covers:
- MediascribeSettings defaults and validation
- Settings from environment variables
- Job creation and properties
- JobStatus, MediaType enums
- MediaInfo defaults
- Segment model
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.job import (
    Job,
    JobStatus,
    MediaInfo,
    MediaType,
    Segment,
)


# ── MediascribeSettings ─────────────────────────────────────────────────────

class TestSettings:
    def test_defaults(self):
        settings = MediascribeSettings()
        assert settings.transcription_mode == "auto"
        assert settings.whisper_model == "large-v3"
        assert settings.chunk_duration_sec == 180
        assert settings.chunk_overlap_sec == 15
        assert settings.word_timestamps is True
        assert settings.translation_model == "gpt-4.1"
        assert settings.translation_profile == "general"
        assert settings.translation_batch_size == 15
        assert settings.enable_review_pass is True
        assert settings.source_language is None
        assert settings.target_language is None
        assert settings.max_concurrency == 1
        assert settings.output_formats == ["srt"]
        assert settings.max_subtitle_duration_sec == 7.0
        assert settings.min_gap_sec == 0.15
        assert settings.chars_per_second == 5.0

    def test_api_key_is_secret(self):
        settings = MediascribeSettings(openai_api_key="sk-test-123")
        # SecretStr should not leak the key in repr
        assert "sk-test-123" not in repr(settings)
        assert settings.openai_api_key.get_secret_value() == "sk-test-123"

    def test_api_key_none_by_default(self):
        settings = MediascribeSettings()
        assert settings.openai_api_key is None

    def test_env_var_override(self):
        with patch.dict(os.environ, {"MEDIASCRIBE_WHISPER_MODEL": "small"}):
            settings = MediascribeSettings()
            assert settings.whisper_model == "small"

    def test_chunk_overlap_setting(self):
        settings = MediascribeSettings(chunk_overlap_sec=30)
        assert settings.chunk_overlap_sec == 30

    def test_ensure_dirs(self, tmp_path: Path):
        settings = MediascribeSettings(
            config_dir=tmp_path / "config",
            output_dir=tmp_path / "output",
        )
        settings.ensure_dirs()
        assert (tmp_path / "config").is_dir()
        assert (tmp_path / "output").is_dir()


# ── Job Model ────────────────────────────────────────────────────────────────

class TestJob:
    def test_creation(self, tmp_path: Path):
        input_file = tmp_path / "video.mp4"
        input_file.touch()
        job = Job(input_path=input_file, output_dir=tmp_path / "out")
        assert job.status == JobStatus.PENDING
        assert job.segments == []
        assert job.analysis == {}
        assert job.audio_path is None
        assert job.error is None

    def test_stem_property(self, tmp_path: Path):
        job = Job(
            input_path=tmp_path / "My Video File.mp4",
            output_dir=tmp_path / "out",
        )
        assert job.stem == "My Video File"

    def test_duration_str_property(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.media_info.duration_sec = 125.0  # 2:05
        assert job.duration_str == "02:05"

    def test_duration_str_zero(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        assert job.duration_str == "00:00"


# ── JobStatus Enum ───────────────────────────────────────────────────────────

class TestJobStatus:
    def test_values(self):
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


# ── MediaType Enum ───────────────────────────────────────────────────────────

class TestMediaType:
    def test_values(self):
        assert MediaType.VIDEO.value == "video"
        assert MediaType.AUDIO.value == "audio"
        assert MediaType.UNKNOWN.value == "unknown"


# ── MediaInfo ────────────────────────────────────────────────────────────────

class TestMediaInfo:
    def test_defaults(self):
        info = MediaInfo()
        assert info.media_type == MediaType.UNKNOWN
        assert info.duration_sec == 0.0
        assert info.codec_video is None
        assert info.codec_audio is None
        assert info.language is None


# ── Segment ──────────────────────────────────────────────────────────────────

class TestSegment:
    def test_creation(self):
        seg = Segment(index=1, start=0.0, end=2.0, text="Hello")
        assert seg.index == 1
        assert seg.start == 0.0
        assert seg.end == 2.0
        assert seg.text == "Hello"
        assert seg.translation is None
        assert seg.speaker is None
        assert seg.confidence is None

    def test_with_all_fields(self):
        seg = Segment(
            index=1,
            start=0.0,
            end=2.0,
            text="こんにちは",
            translation="Hello",
            speaker="Speaker 1",
            confidence=0.95,
        )
        assert seg.translation == "Hello"
        assert seg.speaker == "Speaker 1"
        assert seg.confidence == 0.95
