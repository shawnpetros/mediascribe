"""Tests for the DiarizeStep — speaker attribution logic."""

from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job, Segment
from mediascribe.steps.diarize import DiarizeStep, _find_speaker


class TestFindSpeaker:
    def test_exact_overlap(self):
        turns = [(0.0, 5.0, "SPEAKER_00"), (5.0, 10.0, "SPEAKER_01")]
        assert _find_speaker(0.0, 5.0, turns) == "SPEAKER_00"

    def test_partial_overlap_picks_dominant(self):
        turns = [(0.0, 3.0, "SPEAKER_00"), (2.0, 8.0, "SPEAKER_01")]
        assert _find_speaker(1.0, 7.0, turns) == "SPEAKER_01"

    def test_no_overlap(self):
        turns = [(0.0, 5.0, "SPEAKER_00")]
        assert _find_speaker(10.0, 15.0, turns) is None

    def test_empty_turns(self):
        assert _find_speaker(0.0, 5.0, []) is None

    def test_single_turn_covers_all(self):
        turns = [(0.0, 100.0, "SPEAKER_00")]
        assert _find_speaker(10.0, 20.0, turns) == "SPEAKER_00"

    def test_many_speakers_picks_best(self):
        turns = [
            (0.0, 2.0, "A"),
            (2.0, 4.0, "B"),
            (4.0, 9.0, "C"),
        ]
        assert _find_speaker(3.0, 8.0, turns) == "C"


class TestDiarizeStepSkipCases:
    def test_skips_when_no_audio(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
        job.segments = [Segment(index=1, start=0.0, end=1.0, text="Hello")]
        settings = MediascribeSettings(output_dir=tmp_path)
        events = EventBus()

        step = DiarizeStep()
        result = step.execute(job, settings, events)
        assert result.data.get("skipped")

    def test_skips_when_no_segments(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
        job.audio_path = tmp_path / "audio.wav"
        job.audio_path.write_bytes(b"fake")
        settings = MediascribeSettings(output_dir=tmp_path)
        events = EventBus()

        step = DiarizeStep()
        result = step.execute(job, settings, events)
        assert result.data.get("skipped")

    def test_skips_when_no_hf_token_or_pyannote(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
        job.audio_path = tmp_path / "audio.wav"
        job.audio_path.write_bytes(b"fake")
        job.segments = [Segment(index=1, start=0.0, end=1.0, text="Hello")]
        settings = MediascribeSettings(output_dir=tmp_path)
        events = EventBus()

        step = DiarizeStep()
        result = step.execute(job, settings, events)
        assert result.data.get("skipped")
        reason = result.data.get("reason", "")
        assert "HF token" in reason or "pyannote not installed" in reason


class TestDiarizeCanSkip:
    def test_can_skip_all_labeled(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        job.segments = [
            Segment(index=1, start=0.0, end=1.0, text="Hello", speaker="A"),
            Segment(index=2, start=1.0, end=2.0, text="World", speaker="B"),
        ]
        step = DiarizeStep()
        assert step.can_skip(job) is True

    def test_cannot_skip_unlabeled(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        job.segments = [
            Segment(index=1, start=0.0, end=1.0, text="Hello", speaker="A"),
            Segment(index=2, start=1.0, end=2.0, text="World"),
        ]
        step = DiarizeStep()
        assert step.can_skip(job) is False

    def test_cannot_skip_empty_segments(self):
        job = Job(input_path=Path("test.mp4"), output_dir=Path("/tmp"))
        step = DiarizeStep()
        assert step.can_skip(job) is False
