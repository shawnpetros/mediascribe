"""Tests for the analyze step.

Covers:
- Skipping when no segments exist
- Skipping when transcript too short
- Skipping when analysis already exists (can_skip)
- Analysis result population on job
- Error handling during API call
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, Segment
from mediascribe.steps.analyze import AnalyzeStep


def _make_events() -> tuple[EventBus, list[PipelineEvent]]:
    bus = EventBus()
    log: list[PipelineEvent] = []
    bus.subscribe(log.append)
    return bus, log


class TestAnalyzeStepSkipping:
    def test_skip_no_segments(self, tmp_path: Path):
        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        settings = MediascribeSettings()
        events, log = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True

    def test_skip_short_transcript(self, tmp_path: Path):
        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [Segment(index=1, start=0.0, end=1.0, text="Hi")]
        settings = MediascribeSettings()
        events, log = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True

    def test_can_skip_when_analysis_exists(self, tmp_path: Path):
        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.analysis = {"summary": "test"}
        assert step.can_skip(job) is True

    def test_cannot_skip_when_no_analysis(self, tmp_path: Path):
        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        assert step.can_skip(job) is False


class TestAnalyzeStepExecution:
    @patch("mediascribe.steps.analyze.analyze_transcript")
    def test_populates_job_analysis(self, mock_analyze, tmp_path: Path):
        mock_analyze.return_value = {
            "summary": "A test summary",
            "topics": ["testing", "code"],
            "key_points": ["point one"],
            "action_items": [],
            "sentiment": "neutral",
            "word_count": 100,
        }

        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [
            Segment(index=i, start=float(i), end=float(i + 1), text=f"Segment {i} text content here")
            for i in range(10)
        ]

        settings = MediascribeSettings(openai_api_key="sk-test")
        events, log = _make_events()

        result = step.execute(job, settings, events)
        assert result.success is not False
        assert job.analysis["summary"] == "A test summary"
        assert "testing" in job.analysis["topics"]
        mock_analyze.assert_called_once()

    @patch("mediascribe.steps.analyze.analyze_transcript")
    def test_handles_api_error(self, mock_analyze, tmp_path: Path):
        mock_analyze.side_effect = Exception("API error")

        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [
            Segment(index=i, start=float(i), end=float(i + 1), text=f"Segment {i} with enough text here")
            for i in range(10)
        ]

        settings = MediascribeSettings()
        events, log = _make_events()

        result = step.execute(job, settings, events)
        assert result.success is False

    @patch("mediascribe.steps.analyze.analyze_transcript")
    def test_includes_speaker_labels(self, mock_analyze, tmp_path: Path):
        mock_analyze.return_value = {
            "summary": "Discussion between speakers",
            "topics": [],
            "key_points": [],
            "action_items": [],
            "sentiment": "neutral",
            "word_count": 50,
        }

        step = AnalyzeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [
            Segment(index=1, start=0.0, end=5.0, text="Hello how are you", speaker="Speaker 1"),
            Segment(index=2, start=5.0, end=10.0, text="I am doing great thanks", speaker="Speaker 2"),
            Segment(index=3, start=10.0, end=15.0, text="Great to hear about your progress", speaker="Speaker 1"),
        ]

        settings = MediascribeSettings(openai_api_key="sk-test")
        events, log = _make_events()

        step.execute(job, settings, events)

        call_args = mock_analyze.call_args
        transcript = call_args[1]["transcript_text"] if "transcript_text" in call_args[1] else call_args[0][0]
        assert "[Speaker 1]" in transcript
        assert "[Speaker 2]" in transcript


class TestAnalyzeStepMetadata:
    def test_name(self):
        step = AnalyzeStep()
        assert step.name == "analyze"

    def test_not_required(self):
        step = AnalyzeStep()
        assert step.required is False
