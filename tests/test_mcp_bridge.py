"""Tests for MCP bridge functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mediascribe.core.job import Job, JobStatus, Segment
from mediascribe.mcp.bridge import PipelineError, run_transcription, run_translation


class TestPipelineError:
    def test_with_job(self, tmp_path: Path) -> None:
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
        error = PipelineError("Something failed", job=job)

        assert str(error) == "Something failed"
        assert error.job is job

    def test_without_job(self) -> None:
        error = PipelineError("Something failed")

        assert str(error) == "Something failed"
        assert error.job is None


class TestRunTranscription:
    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            run_transcription(file_path="/nonexistent/file.mp4")

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_returns_completed_job(self, mock_pipeline_cls: MagicMock, tmp_path: Path) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value

        def run_side_effect(job: Job) -> Job:
            job.status = JobStatus.COMPLETED
            job.segments = [Segment(index=1, start=0.0, end=2.5, text="Hello world")]
            return job

        mock_pipeline.run.side_effect = run_side_effect

        result = run_transcription(
            file_path=str(input_file),
            output_dir=str(tmp_path / "output"),
        )

        assert result.status == JobStatus.COMPLETED
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world"

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_failed_pipeline_raises_error(
        self, mock_pipeline_cls: MagicMock, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value

        def run_side_effect(job: Job) -> Job:
            job.status = JobStatus.FAILED
            job.error = "Transcription failed: out of memory"
            return job

        mock_pipeline.run.side_effect = run_side_effect

        with pytest.raises(PipelineError, match="out of memory") as exc_info:
            run_transcription(
                file_path=str(input_file),
                output_dir=str(tmp_path / "output"),
            )

        assert exc_info.value.job is not None
        assert exc_info.value.job.status == JobStatus.FAILED

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_progress_callback_subscribed(
        self, mock_pipeline_cls: MagicMock, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=input_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        callback = MagicMock()
        run_transcription(
            file_path=str(input_file),
            output_dir=str(tmp_path / "output"),
            on_progress=callback,
        )

        # Pipeline was constructed and run
        assert mock_pipeline_cls.called
        assert mock_pipeline.run.called

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_translate_steps_added_with_target_language(
        self, mock_pipeline_cls: MagicMock, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=input_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_transcription(
            file_path=str(input_file),
            target_language="en",
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "TranslateStep" in step_types
        assert "ReviewStep" in step_types

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_no_translate_steps_without_target_language(
        self, mock_pipeline_cls: MagicMock, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=input_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_transcription(
            file_path=str(input_file),
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "TranslateStep" not in step_types

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_analyze_step_added_when_enabled(
        self, mock_pipeline_cls: MagicMock, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=input_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_transcription(
            file_path=str(input_file),
            enable_analyze=True,
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "AnalyzeStep" in step_types

    @patch("mediascribe.mcp.bridge.Pipeline")
    def test_core_steps_always_present(self, mock_pipeline_cls: MagicMock, tmp_path: Path) -> None:
        input_file = tmp_path / "test.mp4"
        input_file.touch()

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=input_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_transcription(
            file_path=str(input_file),
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "DetectStep" in step_types
        assert "NormalizeStep" in step_types
        assert "TranscribeStep" in step_types
        assert "ExportStep" in step_types


class TestRunTranslation:
    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="SRT file not found"):
            run_translation(srt_path="/nonexistent/file.srt")

    @patch("mediascribe.mcp.bridge.Pipeline")
    @patch("mediascribe.mcp.bridge.srt_to_segments")
    def test_returns_completed_job(
        self,
        mock_srt_to_segments: MagicMock,
        mock_pipeline_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:00,000 --> 00:00:02,500\nHello\n")

        mock_srt_to_segments.return_value = [
            Segment(index=1, start=0.0, end=2.5, text="Hello"),
        ]

        mock_pipeline = mock_pipeline_cls.return_value

        def run_side_effect(job: Job) -> Job:
            job.status = JobStatus.COMPLETED
            job.segments[0].translation = "Hola"
            return job

        mock_pipeline.run.side_effect = run_side_effect

        result = run_translation(
            srt_path=str(srt_file),
            target_language="es",
            output_dir=str(tmp_path / "output"),
        )

        assert result.status == JobStatus.COMPLETED
        assert result.segments[0].translation == "Hola"

    @patch("mediascribe.mcp.bridge.Pipeline")
    @patch("mediascribe.mcp.bridge.srt_to_segments")
    def test_failed_translation_raises_error(
        self,
        mock_srt_to_segments: MagicMock,
        mock_pipeline_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:00,000 --> 00:00:02,500\nTest\n")

        mock_srt_to_segments.return_value = [
            Segment(index=1, start=0.0, end=2.5, text="Test"),
        ]

        mock_pipeline = mock_pipeline_cls.return_value

        def run_side_effect(job: Job) -> Job:
            job.status = JobStatus.FAILED
            job.error = "API key invalid"
            return job

        mock_pipeline.run.side_effect = run_side_effect

        with pytest.raises(PipelineError, match="API key invalid") as exc_info:
            run_translation(
                srt_path=str(srt_file),
                output_dir=str(tmp_path / "output"),
            )

        assert exc_info.value.job is not None

    @patch("mediascribe.mcp.bridge.Pipeline")
    @patch("mediascribe.mcp.bridge.srt_to_segments")
    def test_translate_and_review_steps_added(
        self,
        mock_srt_to_segments: MagicMock,
        mock_pipeline_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:00,000 --> 00:00:02,500\nTest\n")

        mock_srt_to_segments.return_value = [
            Segment(index=1, start=0.0, end=2.5, text="Test"),
        ]

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=srt_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_translation(
            srt_path=str(srt_file),
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "TranslateStep" in step_types
        assert "ReviewStep" in step_types

    @patch("mediascribe.mcp.bridge.Pipeline")
    @patch("mediascribe.mcp.bridge.srt_to_segments")
    def test_review_skipped_when_disabled(
        self,
        mock_srt_to_segments: MagicMock,
        mock_pipeline_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:00,000 --> 00:00:02,500\nTest\n")

        mock_srt_to_segments.return_value = [
            Segment(index=1, start=0.0, end=2.5, text="Test"),
        ]

        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = Job(
            input_path=srt_file,
            output_dir=tmp_path / "output",
            status=JobStatus.COMPLETED,
        )

        run_translation(
            srt_path=str(srt_file),
            enable_review=False,
            output_dir=str(tmp_path / "output"),
        )

        step_types = [type(c.args[0]).__name__ for c in mock_pipeline.add_step.call_args_list]
        assert "TranslateStep" in step_types
        assert "ReviewStep" not in step_types
