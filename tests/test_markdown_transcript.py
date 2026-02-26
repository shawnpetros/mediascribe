"""Tests for Markdown transcript format.

Covers:
- Empty segment handling
- Basic text generation
- Speaker labels as headings
- Paragraph grouping by time gaps
- Paragraph grouping by speaker changes
- Timestamp formatting
- Table of contents generation
- save_markdown file output
- save_markdown_from_job with metadata
"""

from pathlib import Path

from mediascribe.core.job import Job, MediaInfo, Segment
from mediascribe.formats.transcript import (
    _fmt_ts_full,
    _group_into_paragraphs,
    save_markdown,
    save_markdown_from_job,
    segments_to_markdown,
)


class TestFmtTsFull:
    def test_zero(self):
        assert _fmt_ts_full(0.0) == "00:00"

    def test_seconds_only(self):
        assert _fmt_ts_full(45.0) == "00:45"

    def test_minutes(self):
        assert _fmt_ts_full(125.0) == "02:05"

    def test_hours(self):
        assert _fmt_ts_full(3661.0) == "01:01:01"

    def test_fractional_seconds_truncated(self):
        assert _fmt_ts_full(90.7) == "01:30"


class TestGroupIntoParagraphs:
    def test_empty(self):
        assert _group_into_paragraphs([], 5.0, False) == []

    def test_single_segment(self):
        segs = [Segment(index=1, start=0.0, end=2.0, text="Hello")]
        result = _group_into_paragraphs(segs, 5.0, False)
        assert len(result) == 1
        assert len(result[0]) == 1

    def test_continuous_segments_same_paragraph(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=2.0, end=4.0, text="World"),
            Segment(index=3, start=4.0, end=6.0, text="Test"),
        ]
        result = _group_into_paragraphs(segs, 5.0, False)
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_time_gap_creates_new_paragraph(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=10.0, end=12.0, text="Later"),
        ]
        result = _group_into_paragraphs(segs, 5.0, False)
        assert len(result) == 2

    def test_speaker_change_creates_new_paragraph(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello", speaker="Speaker 1"),
            Segment(index=2, start=2.0, end=4.0, text="Hi", speaker="Speaker 2"),
        ]
        result = _group_into_paragraphs(segs, 5.0, False)
        assert len(result) == 2

    def test_empty_text_skipped(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=2.0, end=4.0, text=""),
            Segment(index=3, start=4.0, end=6.0, text="World"),
        ]
        result = _group_into_paragraphs(segs, 5.0, False)
        assert len(result) == 1
        assert len(result[0]) == 2


class TestSegmentsToMarkdown:
    def test_empty_segments(self):
        result = segments_to_markdown([], title="Test")
        assert "# Test" in result
        assert "No segments" in result

    def test_basic_output(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello world"),
            Segment(index=2, start=2.0, end=4.0, text="Second line"),
        ]
        result = segments_to_markdown(segs, title="My Transcript")
        assert "# My Transcript" in result
        assert "Hello world" in result
        assert "Second line" in result

    def test_timestamps_included(self):
        segs = [Segment(index=1, start=65.0, end=68.0, text="Test")]
        result = segments_to_markdown(segs, include_timestamps=True)
        assert "*[01:05]*" in result

    def test_timestamps_excluded(self):
        segs = [Segment(index=1, start=65.0, end=68.0, text="Test")]
        result = segments_to_markdown(segs, include_timestamps=False)
        assert "[01:05]" not in result

    def test_speaker_labels(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello", speaker="Alice"),
            Segment(index=2, start=5.0, end=7.0, text="Hi", speaker="Bob"),
        ]
        result = segments_to_markdown(segs, include_speakers=True)
        assert "### Alice" in result
        assert "### Bob" in result

    def test_speaker_toc(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello", speaker="Alice"),
            Segment(index=2, start=5.0, end=7.0, text="Hi", speaker="Bob"),
        ]
        result = segments_to_markdown(segs, include_toc=True)
        assert "## Speakers" in result
        assert "- Alice" in result
        assert "- Bob" in result

    def test_translation_mode(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Original", translation="Translated"),
        ]
        result = segments_to_markdown(segs, use_translation=True)
        assert "Translated" in result

    def test_translation_fallback_to_source(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Source only"),
        ]
        result = segments_to_markdown(segs, use_translation=True)
        assert "Source only" in result


class TestSaveMarkdown:
    def test_creates_file(self, tmp_path: Path):
        segs = [Segment(index=1, start=0.0, end=2.0, text="Hello world")]
        path = tmp_path / "output.md"
        save_markdown(segs, path, title="Test")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Test" in content
        assert "Hello world" in content

    def test_unicode(self, tmp_path: Path):
        segs = [Segment(index=1, start=0.0, end=2.0, text="こんにちは世界")]
        path = tmp_path / "output.md"
        save_markdown(segs, path)
        content = path.read_text(encoding="utf-8")
        assert "こんにちは世界" in content


class TestSaveMarkdownFromJob:
    def test_includes_metadata(self, tmp_path: Path):
        job = Job(
            input_path=tmp_path / "video.mp4",
            output_dir=tmp_path / "out",
        )
        job.segments = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
        ]
        job.media_info = MediaInfo(duration_sec=120.0, language="en")

        path = tmp_path / "transcript.md"
        save_markdown_from_job(job, path)

        content = path.read_text(encoding="utf-8")
        assert "video.mp4" in content
        assert "02:00" in content
        assert "Language: en" in content
