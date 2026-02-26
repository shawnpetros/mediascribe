"""Tests for _clean_segments — Whisper artifact removal.

Covers:
- Empty/whitespace-only text removal
- Punctuation-only artifact removal
- Consecutive duplicate removal
- Whitespace stripping
- Normal segments pass through
"""

from mediascribe.steps.transcribe import _clean_segments


def _seg(text: str, start: float = 0.0, end: float = 1.0) -> dict:
    return {"text": text, "start": start, "end": end}


class TestCleanSegments:
    def test_empty_list(self):
        assert _clean_segments([]) == []

    def test_normal_segments_pass(self):
        segs = [_seg("hello"), _seg("world")]
        result = _clean_segments(segs)
        assert len(result) == 2
        assert result[0]["text"] == "hello"
        assert result[1]["text"] == "world"

    def test_empty_text_removed(self):
        segs = [_seg("hello"), _seg(""), _seg("world")]
        result = _clean_segments(segs)
        assert len(result) == 2

    def test_whitespace_only_removed(self):
        segs = [_seg("hello"), _seg("   "), _seg("world")]
        result = _clean_segments(segs)
        assert len(result) == 2

    def test_punctuation_artifacts_removed(self):
        """Whisper sometimes outputs lone punctuation marks."""
        artifacts = [",", "。", ".", "、"]
        for art in artifacts:
            segs = [_seg("hello"), _seg(art), _seg("world")]
            result = _clean_segments(segs)
            assert len(result) == 2, f"Artifact '{art}' was not removed"

    def test_consecutive_duplicates_removed(self):
        segs = [_seg("hello"), _seg("hello"), _seg("world")]
        result = _clean_segments(segs)
        assert len(result) == 2
        assert result[0]["text"] == "hello"
        assert result[1]["text"] == "world"

    def test_non_consecutive_duplicates_kept(self):
        segs = [_seg("hello"), _seg("world"), _seg("hello")]
        result = _clean_segments(segs)
        assert len(result) == 3

    def test_whitespace_stripped(self):
        segs = [_seg("  hello  "), _seg("  world  ")]
        result = _clean_segments(segs)
        assert result[0]["text"] == "hello"
        assert result[1]["text"] == "world"

    def test_all_artifacts_result_in_empty(self):
        segs = [_seg(""), _seg(","), _seg("。"), _seg("   ")]
        result = _clean_segments(segs)
        assert len(result) == 0

    def test_mixed_artifacts_and_valid(self):
        segs = [
            _seg("real text"),
            _seg(","),
            _seg("real text"),  # consecutive dup of first
            _seg("。"),
            _seg("different"),
        ]
        result = _clean_segments(segs)
        assert len(result) == 2
        assert result[0]["text"] == "real text"
        assert result[1]["text"] == "different"
