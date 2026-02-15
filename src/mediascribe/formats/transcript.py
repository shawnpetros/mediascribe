"""Plain text and Markdown transcript output."""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.job import Segment
from mediascribe.formats.srt import fmt_ts


def segments_to_text(
    segments: list[Segment],
    use_translation: bool = False,
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> str:
    """Convert segments to a plain text transcript.

    Args:
        segments: List of Segment objects.
        use_translation: Use translation text instead of source text.
        include_timestamps: Prefix each line with [MM:SS].
        include_speakers: Include speaker labels if available.

    Returns:
        Formatted transcript string.
    """
    lines = []
    for seg in segments:
        text = (seg.translation if use_translation and seg.translation else seg.text).strip()
        if not text:
            continue

        parts = []
        if include_timestamps:
            parts.append(f"[{fmt_ts(seg.start)}]")
        if include_speakers and seg.speaker:
            parts.append(f"{seg.speaker}:")
        parts.append(text)

        lines.append(" ".join(parts))

    return "\n".join(lines)


def save_transcript(
    segments: list[Segment],
    path: Path,
    use_translation: bool = False,
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> None:
    """Write segments to a plain text transcript file."""
    content = segments_to_text(
        segments,
        use_translation=use_translation,
        include_timestamps=include_timestamps,
        include_speakers=include_speakers,
    )
    path.write_text(content, encoding="utf-8")
