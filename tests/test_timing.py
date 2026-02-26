"""Tests for subtitle timing optimization.

Covers:
- estimate_display_duration (text length → duration)
- fix_subtitle_timing:
  - Duration capping based on text length
  - Minimum gap enforcement between consecutive subtitles
  - Edge cases: single subtitle, overlapping, very long text
"""

import pytest
from pysrt import SubRipFile, SubRipItem

from mediascribe.formats.srt import srt_time, srt_to_sec
from mediascribe.steps.timing import estimate_display_duration, fix_subtitle_timing

# ── estimate_display_duration ────────────────────────────────────────────────

class TestEstimateDisplayDuration:
    def test_empty_text(self):
        assert estimate_display_duration("") == 1.0

    def test_whitespace_only(self):
        assert estimate_display_duration("   ") == 1.0

    def test_short_text_minimum(self):
        # 2 chars → 0.2*2 + 0.8 = 1.2 (minimum clamp)
        d = estimate_display_duration("hi")
        assert d == pytest.approx(1.2)

    def test_medium_text(self):
        # 15 chars → 0.2*15 + 0.8 = 3.8
        text = "Hello everyone!"  # 15 chars
        d = estimate_display_duration(text)
        assert d == pytest.approx(3.8)

    def test_long_text_capped(self):
        # Very long text should cap at 7.0
        text = "x" * 100
        d = estimate_display_duration(text)
        assert d == 7.0

    def test_cjk_text(self):
        # CJK characters: 5 chars → 0.2*5 + 0.8 = 1.8
        d = estimate_display_duration("こんにちは")
        assert d == pytest.approx(1.8)

    def test_monotonically_increasing(self):
        """Longer text should always get longer or equal duration."""
        prev = 0.0
        for n in range(0, 50):
            d = estimate_display_duration("x" * n)
            assert d >= prev
            prev = d


# ── fix_subtitle_timing ──────────────────────────────────────────────────────

def _make_sub(index: int, start: float, end: float, text: str) -> SubRipItem:
    return SubRipItem(
        index=index,
        start=srt_time(start),
        end=srt_time(end),
        text=text,
    )


def _make_srt(items: list[tuple[float, float, str]]) -> SubRipFile:
    srt = SubRipFile()
    for i, (start, end, text) in enumerate(items, start=1):
        srt.append(_make_sub(i, start, end, text))
    return srt


class TestFixSubtitleTiming:
    def test_empty_srt(self):
        srt = SubRipFile()
        fix_subtitle_timing(srt)  # should not crash
        assert len(srt) == 0

    def test_single_subtitle_duration_capped(self):
        """A subtitle with 3 chars displayed for 20s should be capped."""
        srt = _make_srt([(0.0, 20.0, "Hey")])
        fix_subtitle_timing(srt)
        end = srt_to_sec(srt[0].end)
        # "Hey" = 3 chars → estimate = max(1.2, min(3*0.2+0.8, 7.0)) = 1.4
        assert end < 5.0  # way less than 20s

    def test_long_text_gets_longer_display(self):
        """Longer text should be allowed longer display time."""
        short_srt = _make_srt([(0.0, 20.0, "Hi")])
        long_srt = _make_srt([(0.0, 20.0, "This is a much longer subtitle text")])

        fix_subtitle_timing(short_srt)
        fix_subtitle_timing(long_srt)

        short_end = srt_to_sec(short_srt[0].end)
        long_end = srt_to_sec(long_srt[0].end)
        assert long_end > short_end

    def test_gap_enforcement(self):
        """Subtitles that are too close should have a minimum gap enforced."""
        srt = _make_srt([
            (0.0, 2.95, "First"),
            (3.0, 5.0, "Second"),
        ])
        fix_subtitle_timing(srt, min_gap=0.15)

        first_end = srt_to_sec(srt[0].end)
        second_start = srt_to_sec(srt[1].start)
        gap = second_start - first_end
        assert gap >= 0.14  # slight float tolerance

    def test_continuous_timestamps_fixed(self):
        """Whisper's worst habit: end of sub N = start of sub N+1.

        This keeps subtitles on screen 100% of the time with no breaks.
        fix_subtitle_timing should introduce gaps.
        """
        srt = _make_srt([
            (0.0, 3.0, "A"),
            (3.0, 6.0, "B"),
            (6.0, 9.0, "C"),
        ])
        fix_subtitle_timing(srt, min_gap=0.15)

        for i in range(len(srt) - 1):
            this_end = srt_to_sec(srt[i].end)
            next_start = srt_to_sec(srt[i + 1].start)
            assert next_start - this_end >= 0.14

    def test_already_good_timing_unchanged(self):
        """Subtitles with proper gaps and reasonable durations stay the same."""
        srt = _make_srt([
            (0.0, 1.5, "Hello everyone"),  # 14 chars → est ~3.6s, actual 1.5 → ok
            (2.0, 3.5, "How are you"),     # 11 chars → est ~3.0s, actual 1.5 → ok
        ])
        original_times = [
            (srt_to_sec(s.start), srt_to_sec(s.end)) for s in srt
        ]
        fix_subtitle_timing(srt, min_gap=0.15)
        new_times = [
            (srt_to_sec(s.start), srt_to_sec(s.end)) for s in srt
        ]
        assert original_times == new_times

    def test_max_duration_parameter(self):
        """Custom max_duration should override the text-based estimate."""
        srt = _make_srt([(0.0, 100.0, "x" * 50)])
        fix_subtitle_timing(srt, max_duration=3.0)
        end = srt_to_sec(srt[0].end)
        assert end <= 3.0

    def test_gap_doesnt_make_duration_negative(self):
        """If enforcing gap would push end before start, clamp to start+0.5."""
        srt = _make_srt([
            (0.0, 0.8, "A"),
            (0.6, 2.0, "B"),  # starts before A ends
        ])
        fix_subtitle_timing(srt, min_gap=0.15)

        first_end = srt_to_sec(srt[0].end)
        first_start = srt_to_sec(srt[0].start)
        assert first_end >= first_start + 0.4  # at least some visible time
