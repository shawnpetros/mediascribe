"""SRT subtitle format helpers.

Wraps pysrt with convenience functions for building, reading,
and manipulating SubRip (.srt) subtitle files.
"""

from __future__ import annotations

from pathlib import Path

from pysrt import SubRipFile, SubRipItem, SubRipTime

from mediascribe.core.job import Segment

# ── Time Conversion ──────────────────────────────────────────────────────────


def srt_time(sec: float) -> SubRipTime:
    """Convert float seconds to SubRipTime."""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    ms = round((sec - int(sec)) * 1000)
    return SubRipTime(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))


def srt_to_sec(t: SubRipTime) -> float:
    """Convert SubRipTime to float seconds."""
    return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000


def fmt_ts(sec: float) -> str:
    """Format seconds as MM:SS for display."""
    return f"{int(sec // 60):02d}:{int(sec % 60):02d}"


# ── Building SRT from Segments ───────────────────────────────────────────────


def segments_to_srt(segments: list[Segment], use_translation: bool = False) -> SubRipFile:
    """Convert a list of Segment objects to a SubRipFile.

    Args:
        segments: List of Segment objects with start/end/text.
        use_translation: If True, use segment.translation as the text.
                         Falls back to segment.text if translation is None.

    Returns:
        A pysrt SubRipFile ready to save.
    """
    srt = SubRipFile()
    for i, seg in enumerate(segments, start=1):
        text = (seg.translation if use_translation and seg.translation else seg.text).strip()
        if not text:
            continue
        srt.append(SubRipItem(
            index=i,
            start=srt_time(seg.start),
            end=srt_time(seg.end),
            text=text,
        ))
    return srt


def dicts_to_srt(segments: list[dict]) -> SubRipFile:
    """Convert raw dicts [{start, end, text}] to SubRipFile.

    Useful when working with Whisper output before converting to Segment objects.
    """
    srt = SubRipFile()
    for i, s in enumerate(segments, start=1):
        text = s["text"].strip()
        if not text:
            continue
        srt.append(SubRipItem(
            index=i,
            start=srt_time(s["start"]),
            end=srt_time(s["end"]),
            text=text,
        ))
    return srt


# ── Reading SRT ──────────────────────────────────────────────────────────────


def read_srt(path: Path) -> SubRipFile:
    """Read an SRT file, handling encoding."""
    return SubRipFile.open(str(path), encoding="utf-8")


def srt_to_segments(path: Path) -> list[Segment]:
    """Load an SRT file and convert to list of Segment objects."""
    subs = read_srt(path)
    segments = []
    for sub in subs:
        segments.append(Segment(
            index=sub.index,
            start=srt_to_sec(sub.start),
            end=srt_to_sec(sub.end),
            text=sub.text.strip(),
        ))
    return segments


# ── Writing SRT ──────────────────────────────────────────────────────────────


def save_srt(srt: SubRipFile, path: Path) -> None:
    """Save a SubRipFile to disk."""
    srt.save(str(path), encoding="utf-8")
