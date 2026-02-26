"""Plain text and Markdown transcript output."""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.job import Job, Segment
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


# ── Markdown transcript ──────────────────────────────────────────────────────


def _fmt_ts_full(sec: float) -> str:
    """Format seconds as HH:MM:SS for markdown."""
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def segments_to_markdown(
    segments: list[Segment],
    title: str = "Transcript",
    use_translation: bool = False,
    include_timestamps: bool = True,
    include_speakers: bool = True,
    include_toc: bool = True,
    paragraph_gap_sec: float = 5.0,
) -> str:
    """Convert segments to a Markdown-formatted transcript.

    Groups segments into paragraphs based on speaker changes and
    time gaps. Produces a structured document with optional table
    of contents.

    Args:
        segments: Transcribed/translated segments.
        title: Document title.
        use_translation: Use translation text instead of source.
        include_timestamps: Show timestamps for paragraphs.
        include_speakers: Show speaker labels as headings.
        include_toc: Generate a table of contents from speakers.
        paragraph_gap_sec: Time gap that triggers a new paragraph.
    """
    if not segments:
        return f"# {title}\n\n*No segments.*\n"

    lines: list[str] = [f"# {title}\n"]

    speakers_seen: list[str] = []
    for seg in segments:
        if seg.speaker and seg.speaker not in speakers_seen:
            speakers_seen.append(seg.speaker)

    if include_toc and speakers_seen:
        lines.append("## Speakers\n")
        for spk in speakers_seen:
            lines.append(f"- {spk}")
        lines.append("")

    lines.append("---\n")

    paragraphs = _group_into_paragraphs(
        segments, paragraph_gap_sec, use_translation,
    )

    current_speaker: str | None = None
    for para in paragraphs:
        first_seg = para[0]

        if include_speakers and first_seg.speaker and first_seg.speaker != current_speaker:
            current_speaker = first_seg.speaker
            lines.append(f"\n### {current_speaker}\n")

        if include_timestamps:
            ts = _fmt_ts_full(first_seg.start)
            lines.append(f"*[{ts}]*\n")

        texts: list[str] = []
        for seg in para:
            text = (seg.translation if use_translation and seg.translation else seg.text).strip()
            if text:
                texts.append(text)

        lines.append(" ".join(texts) + "\n")

    return "\n".join(lines)


def _group_into_paragraphs(
    segments: list[Segment],
    gap_sec: float,
    use_translation: bool,
) -> list[list[Segment]]:
    """Group segments into paragraphs by speaker changes and time gaps."""
    if not segments:
        return []

    paragraphs: list[list[Segment]] = [[segments[0]]]

    for seg in segments[1:]:
        prev = paragraphs[-1][-1]
        text = (seg.translation if use_translation and seg.translation else seg.text).strip()
        if not text:
            continue

        speaker_changed = seg.speaker != prev.speaker and seg.speaker is not None
        time_gap = seg.start - prev.end > gap_sec

        if speaker_changed or time_gap:
            paragraphs.append([seg])
        else:
            paragraphs[-1].append(seg)

    return paragraphs


def save_markdown(
    segments: list[Segment],
    path: Path,
    title: str = "Transcript",
    use_translation: bool = False,
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> None:
    """Write segments to a Markdown transcript file."""
    content = segments_to_markdown(
        segments,
        title=title,
        use_translation=use_translation,
        include_timestamps=include_timestamps,
        include_speakers=include_speakers,
    )
    path.write_text(content, encoding="utf-8")


def save_markdown_from_job(job: Job, path: Path, use_translation: bool = False) -> None:
    """Write a complete Markdown transcript from a Job, including metadata."""
    title = f"Transcript: {job.input_path.name}"
    content = segments_to_markdown(
        job.segments,
        title=title,
        use_translation=use_translation,
    )

    metadata = [
        f"\n---\n",
        f"*Source: {job.input_path.name}*  ",
        f"*Duration: {job.duration_str}*  ",
    ]
    if job.media_info.language:
        metadata.append(f"*Language: {job.media_info.language}*  ")
    metadata.append("")

    full = content + "\n".join(metadata)
    path.write_text(full, encoding="utf-8")
