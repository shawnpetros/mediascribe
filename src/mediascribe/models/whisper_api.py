"""OpenAI Whisper API transcription client.

Alternative to local faster-whisper — uses OpenAI's cloud Whisper API.
Faster, no local GPU needed, but costs ~$0.006/min.
"""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from mediascribe.utils.ffmpeg import convert_to_mp3


def transcribe_via_api(
    audio_path: Path,
    client: OpenAI | None = None,
    language: str | None = None,
) -> list[dict]:
    """Transcribe an audio file via OpenAI's Whisper API.

    Args:
        audio_path: Path to audio file (WAV or mp3).
        client: Optional OpenAI client. Creates one if not provided.
        language: Source language code (e.g., "ja"). None = auto-detect.

    Returns:
        List of segment dicts: [{start, end, text}].
    """
    if client is None:
        client = OpenAI()

    # Convert to mp3 if WAV (stay under 25 MB upload limit)
    upload_path = audio_path
    temp_mp3 = None
    if audio_path.suffix.lower() == ".wav":
        temp_mp3 = audio_path.with_suffix(".tmp.mp3")
        convert_to_mp3(audio_path, temp_mp3, bitrate="64k")
        upload_path = temp_mp3

    try:
        with open(upload_path, "rb") as f:
            params = {
                "model": "whisper-1",
                "file": f,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }
            if language:
                params["language"] = language

            resp = client.audio.transcriptions.create(**params)

        segments: list[dict] = []
        for s in resp.segments:
            if isinstance(s, dict):
                text, start, end = s["text"].strip(), s["start"], s["end"]
            else:
                text, start, end = s.text.strip(), s.start, s.end
            if text:
                segments.append({"start": start, "end": end, "text": text})

        return segments
    finally:
        if temp_mp3 and temp_mp3.exists():
            temp_mp3.unlink(missing_ok=True)
