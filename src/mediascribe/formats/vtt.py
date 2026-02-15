"""WebVTT subtitle format output.

Converts segments or SRT data to WebVTT (.vtt) format.
"""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.job import Segment


def _vtt_timestamp(sec: float) -> str:
    """Format seconds as HH:MM:SS.mmm for VTT."""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    ms = round((sec - int(sec)) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{ms:03d}"


def segments_to_vtt(segments: list[Segment], use_translation: bool = False) -> str:
    """Convert segments to a WebVTT string.

    Args:
        segments: List of Segment objects.
        use_translation: If True, use translation text.

    Returns:
        WebVTT formatted string.
    """
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, start=1):
        text = (seg.translation if use_translation and seg.translation else seg.text).strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_vtt_timestamp(seg.start)} --> {_vtt_timestamp(seg.end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def save_vtt(segments: list[Segment], path: Path, use_translation: bool = False) -> None:
    """Write segments to a .vtt file."""
    content = segments_to_vtt(segments, use_translation=use_translation)
    path.write_text(content, encoding="utf-8")
