"""Tests for the diarize step.

Covers:
- Skip when no audio path
- Skip when no segments
- Skip when no HuggingFace token
- Skip when pyannote not installed
- Speaker label formatting
- Speaker assignment logic
- can_skip behavior
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, PipelineEvent
from mediascribe.core.job import Job, Segment
from mediascribe.steps.diarize import (
    DiarizeStep,
    _assign_speakers,
    _format_speaker_label,
)


def _make_events() -> tuple[EventBus, list[PipelineEvent]]:
    bus = EventBus()
    log: list[PipelineEvent] = []
    bus.subscribe(log.append)
    return bus, log


class TestFormatSpeakerLabel:
    def test_pyannote_format(self):
        assert _format_speaker_label("SPEAKER_00") == "Speaker 1"
        assert _format_speaker_label("SPEAKER_01") == "Speaker 2"
        assert _format_speaker_label("SPEAKER_09") == "Speaker 10"

    def test_non_pyannote_format(self):
        assert _format_speaker_label("Alice") == "Alice"
        assert _format_speaker_label("custom_label") == "custom_label"


class TestAssignSpeakers:
    def test_assigns_majority_speaker(self):
        class MockTurn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class MockDiarization:
            def itertracks(self, yield_label=False):
                return [
                    (MockTurn(0.0, 5.0), None, "SPEAKER_00"),
                    (MockTurn(5.0, 10.0), None, "SPEAKER_01"),
                    (MockTurn(10.0, 15.0), None, "SPEAKER_00"),
                ]

        segments = [
            {"index": 1, "start": 0.0, "end": 4.0},
            {"index": 2, "start": 5.0, "end": 9.0},
            {"index": 3, "start": 10.0, "end": 14.0},
        ]

        result = _assign_speakers(segments, MockDiarization())
        assert result[1] == "Speaker 1"
        assert result[2] == "Speaker 2"
        assert result[3] == "Speaker 1"

    def test_no_overlap(self):
        class MockDiarization:
            def itertracks(self, yield_label=False):
                return [
                    (MagicMock(start=100.0, end=105.0), None, "SPEAKER_00"),
                ]

        segments = [{"index": 1, "start": 0.0, "end": 4.0}]
        result = _assign_speakers(segments, MockDiarization())
        assert 1 not in result


class TestDiarizeStepSkipping:
    def test_skip_no_audio(self, tmp_path: Path):
        step = DiarizeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        settings = MediascribeSettings()
        events, _ = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True

    def test_skip_no_segments(self, tmp_path: Path):
        step = DiarizeStep()
        audio = tmp_path / "audio.wav"
        audio.touch()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.audio_path = audio
        settings = MediascribeSettings()
        events, _ = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True

    def test_skip_no_hf_token(self, tmp_path: Path):
        step = DiarizeStep()
        audio = tmp_path / "audio.wav"
        audio.touch()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.audio_path = audio
        job.segments = [Segment(index=1, start=0.0, end=2.0, text="Test")]
        settings = MediascribeSettings()
        events, _ = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True
        assert result.data.get("reason") == "no_token"

    @patch.dict("sys.modules", {"pyannote": None, "pyannote.audio": None})
    def test_skip_pyannote_not_installed(self, tmp_path: Path):
        step = DiarizeStep()
        audio = tmp_path / "audio.wav"
        audio.touch()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.audio_path = audio
        job.segments = [Segment(index=1, start=0.0, end=2.0, text="Test")]
        settings = MediascribeSettings(huggingface_token="hf_test")
        events, _ = _make_events()

        result = step.execute(job, settings, events)
        assert result.data.get("skipped") is True


class TestDiarizeStepCanSkip:
    def test_skip_when_speakers_assigned(self, tmp_path: Path):
        step = DiarizeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [
            Segment(index=1, start=0.0, end=2.0, text="Test", speaker="Speaker 1"),
        ]
        assert step.can_skip(job) is True

    def test_no_skip_when_no_speakers(self, tmp_path: Path):
        step = DiarizeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        job.segments = [
            Segment(index=1, start=0.0, end=2.0, text="Test"),
        ]
        assert step.can_skip(job) is False

    def test_no_skip_when_empty_segments(self, tmp_path: Path):
        step = DiarizeStep()
        job = Job(input_path=tmp_path / "x.mp4", output_dir=tmp_path)
        assert step.can_skip(job) is False


class TestDiarizeStepMetadata:
    def test_name(self):
        step = DiarizeStep()
        assert step.name == "diarize"

    def test_not_required(self):
        step = DiarizeStep()
        assert step.required is False
