"""FFmpeg/ffprobe wrapper functions."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mediascribe.core.job import MediaInfo, MediaType


async def probe_file(path: Path) -> MediaInfo:
    """Run ffprobe on a file and return structured MediaInfo."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    data = json.loads(stdout)

    info = MediaInfo()

    # Determine media type and extract stream info
    streams = data.get("streams", [])
    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            info.media_type = MediaType.VIDEO
            info.codec_video = stream.get("codec_name")
            info.width = int(stream.get("width", 0)) or None
            info.height = int(stream.get("height", 0)) or None
        elif codec_type == "audio":
            if info.media_type == MediaType.UNKNOWN:
                info.media_type = MediaType.AUDIO
            info.codec_audio = stream.get("codec_name")
            info.sample_rate = int(stream.get("sample_rate", 0)) or None
            info.channels = int(stream.get("channels", 0)) or None

    # Duration from format
    fmt = data.get("format", {})
    info.duration_sec = float(fmt.get("duration", 0))

    return info


async def extract_audio(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> None:
    """Extract audio from a media file as WAV."""
    cmd = [
        "ffmpeg", "-y", "-nostdin",
        "-i", str(input_path),
        "-vn",
        "-ac", str(channels),
        "-ar", str(sample_rate),
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")


async def split_audio(
    input_path: Path,
    output_dir: Path,
    chunk_duration_sec: int = 180,
) -> list[Path]:
    """Split audio into fixed-duration chunks for chunked transcription."""
    info = await probe_file(input_path)
    total = info.duration_sec
    chunks: list[Path] = []

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, start in enumerate(range(0, int(total) + 1, chunk_duration_sec)):
        chunk_path = output_dir / f"chunk_{i:03d}.wav"
        cmd = [
            "ffmpeg", "-y", "-nostdin",
            "-i", str(input_path),
            "-ss", str(start),
            "-t", str(chunk_duration_sec),
            "-ac", "1", "-ar", "16000",
            str(chunk_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if chunk_path.exists() and chunk_path.stat().st_size > 0:
            chunks.append(chunk_path)

    return chunks
