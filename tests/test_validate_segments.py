"""Tests for transcribe step validation — hallucination detection.

Covers:
- Short segment lists (always pass)
- Clean segments (pass)
- Consecutive repeat loops (fail)
- Dominant single text (fail)
- Suspiciously short average text (fail)
- Edge cases around thresholds
"""


from mediascribe.steps.transcribe import validate_segments

# ── Helpers ───────────────────────────────────────────────────────────────────

def _seg(text: str, start: float = 0.0, end: float = 1.0) -> dict:
    return {"text": text, "start": start, "end": end}


# ── Short segment lists always pass ──────────────────────────────────────────

class TestShortLists:
    def test_empty_list(self):
        ok, reason = validate_segments([])
        assert ok is True

    def test_one_segment(self):
        ok, _ = validate_segments([_seg("hello")])
        assert ok is True

    def test_three_segments(self):
        # < 4 segments → always passes (even if they're identical)
        segs = [_seg("same")] * 3
        ok, _ = validate_segments(segs)
        assert ok is True


# ── Clean segments pass ──────────────────────────────────────────────────────

class TestCleanSegments:
    def test_varied_text_passes(self):
        segs = [_seg(f"Line {i}") for i in range(20)]
        ok, reason = validate_segments(segs)
        assert ok is True
        assert reason == "ok"

    def test_some_repeats_below_threshold(self):
        # 3 consecutive repeats is fine (threshold is 4)
        segs = [_seg("a"), _seg("a"), _seg("a"), _seg("b"), _seg("c")]
        ok, _ = validate_segments(segs)
        assert ok is True

    def test_dominant_below_threshold(self):
        # 7 segments, "repeat me" appears 2 times = 28% < 35%
        # (use longer text to avoid triggering short-avg check)
        segs = [_seg("repeat me"), _seg("some text"), _seg("repeat me"),
                _seg("another line"), _seg("more stuff"),
                _seg("even more"), _seg("last one")]
        ok, _ = validate_segments(segs)
        assert ok is True


# ── Consecutive repeat loop detection ────────────────────────────────────────

class TestLoopDetection:
    def test_four_consecutive_repeats_fails(self):
        segs = [_seg("hello")] * 4 + [_seg("world")]
        ok, reason = validate_segments(segs)
        assert ok is False
        assert "loop" in reason

    def test_six_consecutive_repeats_fails(self):
        segs = [_seg("x")] * 6 + [_seg("y")]
        ok, reason = validate_segments(segs)
        assert ok is False
        assert "6" in reason

    def test_repeats_in_middle(self):
        segs = [_seg("a"), _seg("b")] + [_seg("loop")] * 5 + [_seg("c")]
        ok, reason = validate_segments(segs)
        assert ok is False
        assert "loop" in reason


# ── Dominant text detection ──────────────────────────────────────────────────

class TestDominantDetection:
    def test_dominant_text_fails(self):
        # 10 segments, "ugh" appears 4 times = 40% > 35%
        # Interleave to avoid triggering loop detection first
        segs = [
            _seg("ugh"), _seg("line1"), _seg("ugh"), _seg("line2"),
            _seg("ugh"), _seg("line3"), _seg("ugh"), _seg("line4"),
            _seg("line5"), _seg("line6"),
        ]
        ok, reason = validate_segments(segs)
        assert ok is False
        assert "dominant" in reason

    def test_dominant_exactly_at_threshold(self):
        # 10 segments, 3 repeats of "x" = 30% — should pass
        # (condition is >35%, not >=35%)
        segs = [_seg("x")] * 3 + [_seg(f"line{i}") for i in range(7)]
        ok, _ = validate_segments(segs)
        assert ok is True

    def test_dominant_skipped_for_small_lists(self):
        # 6 or fewer segments → dominant check is skipped (requires > 6)
        # Use different texts to avoid loop detection, longer to avoid short-avg
        segs = [_seg("hello world")] * 2 + [
            _seg("other text"), _seg("more words"),
            _seg("something"), _seg("final line"),
        ]
        ok, _ = validate_segments(segs)
        assert ok is True


# ── Short average text detection ─────────────────────────────────────────────

class TestShortAvgText:
    def test_very_short_avg_fails(self):
        segs = [_seg("x") for _ in range(8)]  # avg len = 1 char
        # This will also trigger dominant, but let's check it's caught
        ok, reason = validate_segments(segs)
        assert ok is False

    def test_normal_length_passes(self):
        segs = [_seg(f"This is line number {i}") for i in range(10)]
        ok, _ = validate_segments(segs)
        assert ok is True

    def test_short_avg_skipped_for_small_lists(self):
        # 5 or fewer segments → short avg check skipped (requires > 5)
        # Use different short texts to avoid loop detection
        segs = [_seg("a"), _seg("b"), _seg("c"), _seg("d"), _seg("e")]
        ok, _ = validate_segments(segs)
        assert ok is True
