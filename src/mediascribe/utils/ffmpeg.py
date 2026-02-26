"""FFmpeg/ffprobe wrapper functions.

All functions are synchronous. For TUI use, the pipeline runs in a
background thread so these blocking calls don't freeze the UI.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    """Get audio/video duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    return float(r.stdout.strip())


def probe_json(path: Path) -> dict:
    """Get full ffprobe JSON output for a file."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def extract_audio(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> None:
    """Extract audio from a media file as WAV."""
    cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg extract_audio failed: {r.stderr.decode()}")


def split_audio(
    input_path: Path,
    output_dir: Path,
    chunk_duration_sec: int = 180,
    overlap_sec: int = 15,
) -> tuple[list[Path], list[float]]:
    """Split audio into overlapping chunks for chunked transcription.

    Each chunk overlaps its neighbour by ``overlap_sec`` so that sentences
    at chunk boundaries are fully captured in at least one chunk.  The
    post-processing dedup step then reconciles the overlap zone.

    Args:
        input_path: Path to the source audio file.
        output_dir: Directory to write chunk WAV files into.
        chunk_duration_sec: Duration of each chunk (seconds).
        overlap_sec: Overlap between adjacent chunks (seconds).
            Set to 0 to disable overlap (hard cuts).

    Returns:
        (chunks, offsets) — file paths and their start-time offsets (sec).
    """
    total = probe_duration(input_path)
    stride = max(chunk_duration_sec - overlap_sec, 1)
    chunks: list[Path] = []
    offsets: list[float] = []

    output_dir.mkdir(parents=True, exist_ok=True)

    idx = 0
    offset = 0.0
    while offset < total:
        # Last chunk may be shorter — that's fine, ffmpeg stops at EOF
        actual_duration = min(chunk_duration_sec, total - offset)
        chunk_path = output_dir / f"chunk_{idx:03d}.wav"
        if not chunk_path.exists():
            cmd = [
                "ffmpeg",
                "-y",
                "-nostdin",
                "-i",
                str(input_path),
                "-ss",
                str(offset),
                "-t",
                str(actual_duration),
                "-ac",
                "1",
                "-ar",
                "16000",
                str(chunk_path),
            ]
            subprocess.run(cmd, capture_output=True)

        if chunk_path.exists() and chunk_path.stat().st_size > 0:
            chunks.append(chunk_path)
            offsets.append(offset)
        offset += stride
        idx += 1

    return chunks, offsets


def convert_to_mp3(input_path: Path, output_path: Path, bitrate: str = "64k") -> None:
    """Convert audio to mp3 (e.g., for API upload size reduction)."""
    cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i",
        str(input_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg convert_to_mp3 failed: {r.stderr.decode()}")
