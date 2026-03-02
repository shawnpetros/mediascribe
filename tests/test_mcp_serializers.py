"""Tests for MCP serializer functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.job import Job, JobStatus, MediaInfo, MediaType, Segment
from mediascribe.mcp.serializers import job_to_result, profiles_to_result, settings_to_result


class TestJobToResult:
    def test_basic_job(self, tmp_path: Path) -> None:
        job = Job(
            input_path=tmp_path / "test.mp4",
            output_dir=tmp_path / "output",
        )
        job.status = JobStatus.COMPLETED
        job.segments = [
            Segment(index=1, start=0.0, end=2.5, text="Hello world"),
            Segment(index=2, start=2.5, end=5.0, text="Goodbye world"),
        ]

        result = job_to_result(job)

        assert result["status"] == "completed"
        assert result["segment_count"] == 2
        assert len(result["segments"]) == 2
        assert result["segments"][0]["text"] == "Hello world"
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] == 2.5

    def test_segments_with_translation(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED
        job.segments = [
            Segment(index=1, start=0.0, end=2.5, text="Hello", translation="Hola"),
        ]

        result = job_to_result(job)
        assert result["segments"][0]["translation"] == "Hola"

    def test_optional_fields_omitted_when_none(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED
        job.segments = [
            Segment(index=1, start=0.0, end=2.5, text="Hello"),
        ]

        seg = job_to_result(job)["segments"][0]
        assert "translation" not in seg
        assert "speaker" not in seg
        assert "confidence" not in seg

    def test_segments_with_speaker(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED
        job.segments = [
            Segment(index=1, start=0.0, end=2.5, text="Hello", speaker="SPEAKER_00"),
        ]

        assert job_to_result(job)["segments"][0]["speaker"] == "SPEAKER_00"

    def test_segments_with_confidence(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED
        job.segments = [
            Segment(index=1, start=0.0, end=2.5, text="Hello", confidence=0.95),
        ]

        assert job_to_result(job)["segments"][0]["confidence"] == 0.95

    def test_media_info_included_when_present(self, tmp_path: Path) -> None:
        job = Job(
            input_path=tmp_path / "test.mp4",
            output_dir=tmp_path / "output",
            media_info=MediaInfo(media_type=MediaType.VIDEO, duration_sec=125.0),
        )
        job.status = JobStatus.COMPLETED

        result = job_to_result(job)
        assert result["duration"] == "02:05"
        assert result["media_type"] == "video"

    def test_no_duration_when_zero(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED

        result = job_to_result(job)
        assert "duration" not in result
        assert "media_type" not in result

    def test_analysis_included(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED
        job.analysis = {"summary": "A test video", "topics": ["testing"]}

        result = job_to_result(job)
        assert result["analysis"]["summary"] == "A test video"
        assert result["analysis"]["topics"] == ["testing"]

    def test_analysis_omitted_when_empty(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED

        assert "analysis" not in job_to_result(job)

    def test_failed_job_includes_error(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.FAILED
        job.error = "Transcription failed"

        result = job_to_result(job)
        assert result["status"] == "failed"
        assert result["error"] == "Transcription failed"

    def test_error_omitted_when_none(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path / "output")
        job.status = JobStatus.COMPLETED

        assert "error" not in job_to_result(job)


class TestSettingsToResult:
    def test_basic_defaults(self, tmp_path: Path) -> None:
        empty_config = tmp_path / "config"
        empty_config.mkdir()
        with patch("mediascribe.core.config._default_config_dir", return_value=empty_config):
            settings = MediascribeSettings(config_dir=empty_config)
        result = settings_to_result(settings)

        assert result["profile"] == "general"
        assert result["whisper_model"] == "large-v3"
        assert result["translation_model"] == "gpt-4.1"
        assert result["openai_api_key"] is None
        assert result["huggingface_token"] is None

    def test_secrets_redacted(self) -> None:
        settings = MediascribeSettings(openai_api_key="sk-test-key-12345")
        result = settings_to_result(settings)

        assert result["openai_api_key"] == "***configured***"
        assert "sk-test" not in str(result)

    def test_output_dir_is_string(self) -> None:
        settings = MediascribeSettings()
        result = settings_to_result(settings)

        assert isinstance(result["output_dir"], str)

    def test_all_expected_keys_present(self) -> None:
        settings = MediascribeSettings()
        result = settings_to_result(settings)

        expected_keys = {
            "profile",
            "transcription_mode",
            "whisper_model",
            "whisper_device",
            "whisper_compute",
            "translation_model",
            "translation_batch_size",
            "enable_review_pass",
            "source_language",
            "target_language",
            "output_formats",
            "output_dir",
            "max_concurrency",
            "openai_api_key",
            "huggingface_token",
        }
        assert set(result.keys()) == expected_keys


class TestProfilesToResult:
    def test_lists_builtin_profiles(self) -> None:
        result = profiles_to_result()
        names = [p["name"] for p in result["profiles"]]

        assert "general" in names
        assert "anime" in names
        assert "podcast" in names
        assert "meeting" in names

    def test_profiles_have_descriptions(self) -> None:
        result = profiles_to_result()

        for profile in result["profiles"]:
            assert "description" in profile
            assert isinstance(profile["description"], str)

    def test_profiles_have_overrides(self) -> None:
        result = profiles_to_result()

        for profile in result["profiles"]:
            assert "overrides" in profile
            assert isinstance(profile["overrides"], dict)

    def test_anime_profile_has_overrides(self) -> None:
        result = profiles_to_result()
        anime = next(p for p in result["profiles"] if p["name"] == "anime")

        assert anime["overrides"]["whisper_model"] == "large-v3"
        assert anime["overrides"]["transcription_mode"] == "local"
