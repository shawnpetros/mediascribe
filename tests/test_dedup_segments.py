"""Tests for segment deduplication — overlap boundary reconciliation.

Covers:
- No duplicates (passthrough)
- Exact text + close timestamps → merge
- Exact text + overlapping → skip
- Fuzzy similar text + close timestamps → keep longer
- Out-of-order input (sorts by start time)
- Mixed scenarios at real overlap boundaries
- _text_similar helper edge cases
"""

import pytest

from mediascribe.steps.transcribe import _deduplicate_segments, _text_similar


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seg(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end}


# ── _text_similar ────────────────────────────────────────────────────────────

class TestTextSimilar:
    def test_identical_strings(self):
        assert _text_similar("hello world", "hello world") is True

    def test_empty_strings(self):
        assert _text_similar("", "") is True

    def test_one_empty(self):
        assert _text_similar("hello", "") is False
        assert _text_similar("", "hello") is False

    def test_very_different_lengths(self):
        assert _text_similar("hi", "this is a very long sentence") is False

    def test_similar_transcriptions(self):
        # Whisper might transcribe the same audio slightly differently
        assert _text_similar("それは何ですか", "それは何ですか？") is True

    def test_completely_different(self):
        assert _text_similar("hello world", "goodbye moon") is False

    def test_minor_difference(self):
        assert _text_similar("the quick brown fox", "the quick brown box") is True

    def test_threshold_parameter(self):
        # With a very high threshold, even small diffs fail
        assert _text_similar("abc", "abd", threshold=1.0) is False
        # With a low threshold, even big diffs pass
        assert _text_similar("abc", "xyz", threshold=0.0) is True


# ── No duplicates ────────────────────────────────────────────────────────────

class TestNoDuplicates:
    def test_empty_list(self):
        assert _deduplicate_segments([]) == []

    def test_single_segment(self):
        segs = [_seg("hello", 0.0, 1.0)]
        result = _deduplicate_segments(segs)
        assert len(result) == 1
        assert result[0]["text"] == "hello"

    def test_unique_segments_unchanged(self):
        segs = [
            _seg("line one", 0.0, 2.0),
            _seg("line two", 3.0, 5.0),
            _seg("line three", 6.0, 8.0),
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 3


# ── Exact text + close timestamps → merge ────────────────────────────────────

class TestExactMerge:
    def test_same_text_close_start(self):
        segs = [
            _seg("hello", 10.0, 12.0),
            _seg("hello", 10.5, 13.0),  # same text, start within 2s
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 1
        assert result[0]["end"] == 13.0  # extended to max end

    def test_same_text_at_boundary(self):
        # Chunk 1 ends at 180s, chunk 2 starts at 165s (15s overlap)
        segs = [
            _seg("こんにちは", 178.0, 180.0),
            _seg("こんにちは", 178.5, 181.0),  # same from overlap chunk
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 1
        assert result[0]["end"] == 181.0


# ── Exact text, overlapping → skip ──────────────────────────────────────────

class TestExactSkip:
    def test_same_text_overlapping_timeline(self):
        segs = [
            _seg("hello", 10.0, 14.0),
            _seg("hello", 13.0, 15.0),  # still within prev's end + 0.5
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 1


# ── Fuzzy similar text → keep longer ─────────────────────────────────────────

class TestFuzzyDedup:
    def test_similar_text_keep_longer(self):
        segs = [
            _seg("quick brown fox", 10.0, 12.0),
            _seg("the quick brown fox", 10.2, 12.5),  # longer, more complete
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 1
        assert result[0]["text"] == "the quick brown fox"

    def test_similar_text_keep_first_if_longer(self):
        # First is longer and more complete → keep it, extend end
        segs = [
            _seg("the quick brown fox", 10.0, 12.0),
            _seg("quick brown fox", 10.2, 12.5),  # shorter version
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 1
        assert result[0]["text"] == "the quick brown fox"
        assert result[0]["end"] == 12.5  # end extended from shorter

    def test_different_text_not_deduped(self):
        segs = [
            _seg("completely different", 10.0, 12.0),
            _seg("totally unrelated text", 10.2, 12.5),
        ]
        result = _deduplicate_segments(segs)
        assert len(result) == 2


# ── Sorting ──────────────────────────────────────────────────────────────────

class TestSorting:
    def test_out_of_order_gets_sorted(self):
        segs = [
            _seg("third", 6.0, 8.0),
            _seg("first", 0.0, 2.0),
            _seg("second", 3.0, 5.0),
        ]
        result = _deduplicate_segments(segs)
        assert [s["text"] for s in result] == ["first", "second", "third"]


# ── Realistic overlap scenario ───────────────────────────────────────────────

class TestRealisticOverlap:
    def test_two_chunks_with_overlap(self):
        """Simulate what happens with 180s chunks and 15s overlap.

        Chunk 1 covers 0-180s, Chunk 2 covers 165-345s.
        Segment near boundary (175s) appears in both chunks.
        """
        chunk1_segs = [
            _seg("line at 170s", 170.0, 173.0),
            _seg("sentence at boundary", 175.0, 179.0),
        ]
        chunk2_segs = [
            _seg("sentence at boundary", 175.2, 179.5),  # from overlap
            _seg("new line at 185s", 185.0, 188.0),
        ]

        all_segs = chunk1_segs + chunk2_segs
        result = _deduplicate_segments(all_segs)

        # Should have 3 unique segments
        assert len(result) == 3
        texts = [s["text"] for s in result]
        assert "line at 170s" in texts
        assert "sentence at boundary" in texts
        assert "new line at 185s" in texts

    def test_three_chunks_with_overlaps(self):
        """Multiple overlaps across 3 chunks."""
        segs = [
            # Chunk 1
            _seg("intro", 0.0, 3.0),
            _seg("boundary 1", 175.0, 179.0),
            # Chunk 2 overlap zone
            _seg("boundary 1", 175.3, 179.2),  # dup from overlap
            _seg("middle", 200.0, 203.0),
            _seg("boundary 2", 340.0, 344.0),
            # Chunk 3 overlap zone
            _seg("boundary 2", 340.5, 344.5),  # dup from overlap
            _seg("outro", 400.0, 403.0),
        ]

        result = _deduplicate_segments(segs)
        texts = [s["text"] for s in result]

        assert len(result) == 5
        assert texts == ["intro", "boundary 1", "middle", "boundary 2", "outro"]
