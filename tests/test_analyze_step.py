"""Tests for the AnalyzeStep — AI analysis skip/edge cases."""

from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job
from mediascribe.steps.analyze import AnalyzeStep


class TestAnalyzeSkipCases:
    def test_skips_when_no_segments(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path)
        events = EventBus()

        step = AnalyzeStep()
        result = step.execute(job, settings, events)
        assert result.data.get("skipped")

    def test_not_required(self):
        step = AnalyzeStep()
        assert step.required is False


class TestAnalyzeCanSkip:
    def test_can_skip_if_summary_exists(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        job.analysis = {"summary": "This is a test summary."}
        step = AnalyzeStep()
        assert step.can_skip(job) is True

    def test_cannot_skip_if_no_analysis(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        step = AnalyzeStep()
        assert step.can_skip(job) is False

    def test_cannot_skip_if_empty_summary(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        job.analysis = {"summary": ""}
        step = AnalyzeStep()
        assert step.can_skip(job) is False


class TestAnalyzeStepMeta:
    def test_step_name(self):
        step = AnalyzeStep()
        assert step.name == "analyze"

    def test_step_description(self):
        step = AnalyzeStep()
        assert "Analyzing" in step.description
