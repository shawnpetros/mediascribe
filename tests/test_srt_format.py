"""Tests for SRT format helpers — read, write, convert.

Covers:
- srt_time / srt_to_sec roundtrip
- fmt_ts display formatting
- segments_to_srt / dicts_to_srt
- read_srt / save_srt (file I/O)
- srt_to_segments (file → Segment objects)
- Edge cases: empty segments, translation mode, empty text filtering
"""

import pytest
from pathlib import Path

from pysrt import SubRipFile

from mediascribe.core.job import Segment
from mediascribe.formats.srt import (
    dicts_to_srt,
    fmt_ts,
    read_srt,
    save_srt,
    segments_to_srt,
    srt_time,
    srt_to_sec,
    srt_to_segments,
)


# ── Time conversion roundtrip ────────────────────────────────────────────────

class TestTimeConversion:
    def test_zero(self):
        t = srt_time(0.0)
        assert srt_to_sec(t) == pytest.approx(0.0, abs=0.01)

    def test_simple_seconds(self):
        t = srt_time(5.5)
        assert srt_to_sec(t) == pytest.approx(5.5, abs=0.01)

    def test_minutes(self):
        t = srt_time(125.0)  # 2:05
        assert srt_to_sec(t) == pytest.approx(125.0, abs=0.01)

    def test_hours(self):
        t = srt_time(3661.5)  # 1:01:01.500
        assert srt_to_sec(t) == pytest.approx(3661.5, abs=0.01)

    def test_roundtrip_precision(self):
        """Various timestamps should survive the roundtrip."""
        values = [0.0, 0.001, 1.234, 59.999, 60.0, 3600.0, 7199.999]
        for v in values:
            t = srt_time(v)
            result = srt_to_sec(t)
            assert result == pytest.approx(v, abs=0.01), f"Failed for {v}"


# ── fmt_ts display formatting ────────────────────────────────────────────────

class TestFmtTs:
    def test_zero(self):
        assert fmt_ts(0.0) == "00:00"

    def test_seconds_only(self):
        assert fmt_ts(45.0) == "00:45"

    def test_minutes_and_seconds(self):
        assert fmt_ts(125.0) == "02:05"

    def test_large_values(self):
        assert fmt_ts(3600.0) == "60:00"  # just shows total minutes


# ── segments_to_srt ──────────────────────────────────────────────────────────

class TestSegmentsToSrt:
    def test_basic_conversion(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=3.0, end=5.0, text="World"),
        ]
        srt = segments_to_srt(segs)
        assert len(srt) == 2
        assert srt[0].text == "Hello"
        assert srt[1].text == "World"

    def test_empty_text_filtered(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=3.0, end=5.0, text="  "),
            Segment(index=3, start=6.0, end=8.0, text="World"),
        ]
        srt = segments_to_srt(segs)
        assert len(srt) == 2

    def test_translation_mode(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="こんにちは",
                    translation="Hello"),
        ]
        srt = segments_to_srt(segs, use_translation=True)
        assert srt[0].text == "Hello"

    def test_translation_fallback_to_text(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="こんにちは",
                    translation=None),
        ]
        srt = segments_to_srt(segs, use_translation=True)
        assert srt[0].text == "こんにちは"

    def test_empty_list(self):
        srt = segments_to_srt([])
        assert len(srt) == 0


# ── dicts_to_srt ─────────────────────────────────────────────────────────────

class TestDictsToSrt:
    def test_basic(self):
        dicts = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 3.0, "end": 5.0, "text": "World"},
        ]
        srt = dicts_to_srt(dicts)
        assert len(srt) == 2

    def test_empty_text_filtered(self):
        dicts = [
            {"start": 0.0, "end": 2.0, "text": ""},
            {"start": 3.0, "end": 5.0, "text": "World"},
        ]
        srt = dicts_to_srt(dicts)
        assert len(srt) == 1

    def test_indices_are_sequential(self):
        dicts = [
            {"start": 0.0, "end": 2.0, "text": "A"},
            {"start": 3.0, "end": 5.0, "text": "B"},
            {"start": 6.0, "end": 8.0, "text": "C"},
        ]
        srt = dicts_to_srt(dicts)
        assert [s.index for s in srt] == [1, 2, 3]


# ── File I/O ─────────────────────────────────────────────────────────────────

class TestFileIO:
    def test_save_and_read_roundtrip(self, tmp_path: Path):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello World"),
            Segment(index=2, start=3.0, end=5.0, text="Testing SRT"),
        ]
        srt = segments_to_srt(segs)
        path = tmp_path / "test.srt"

        save_srt(srt, path)
        assert path.exists()

        loaded = read_srt(path)
        assert len(loaded) == 2
        assert loaded[0].text == "Hello World"
        assert loaded[1].text == "Testing SRT"

    def test_srt_to_segments(self, tmp_path: Path):
        segs = [
            Segment(index=1, start=1.5, end=3.5, text="First line"),
            Segment(index=2, start=5.0, end=7.0, text="Second line"),
        ]
        srt = segments_to_srt(segs)
        path = tmp_path / "test.srt"
        save_srt(srt, path)

        result = srt_to_segments(path)
        assert len(result) == 2
        assert result[0].text == "First line"
        assert result[0].start == pytest.approx(1.5, abs=0.01)
        assert result[1].text == "Second line"

    def test_unicode_roundtrip(self, tmp_path: Path):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="日本語テスト"),
            Segment(index=2, start=3.0, end=5.0, text="한국어 테스트"),
        ]
        srt = segments_to_srt(segs)
        path = tmp_path / "unicode.srt"

        save_srt(srt, path)
        loaded = read_srt(path)
        assert loaded[0].text == "日本語テスト"
        assert loaded[1].text == "한국어 테스트"
