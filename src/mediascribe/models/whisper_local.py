"""Local Whisper model management via faster-whisper.

Handles lazy loading, caching, and transcription of audio chunks
with configurable anti-hallucination parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Lazy import — faster_whisper is heavy and we don't want to load it
# unless local transcription is actually used.
_model_cache: dict[str, Any] = {}


def get_model(
    model_name: str = "large-v3",
    device: str = "auto",
    compute_type: str = "int8",
) -> Any:
    """Lazy-load and cache a faster-whisper WhisperModel.

    Args:
        model_name: Whisper model size (e.g., "large-v3", "medium", "small").
        device: Device to use ("auto", "cpu", "cuda").
        compute_type: Compute type ("int8", "float16", "float32").

    Returns:
        A faster_whisper.WhisperModel instance.
    """
    cache_key = f"{model_name}:{device}:{compute_type}"
    if cache_key not in _model_cache:
        from faster_whisper import WhisperModel

        _model_cache[cache_key] = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
    return _model_cache[cache_key]


def transcribe_chunk(
    chunk_path: Path,
    offset: float = 0.0,
    language: str | None = None,
    vocab_prompt: str = "",
    model_name: str = "large-v3",
    device: str = "auto",
    compute_type: str = "int8",
    retry: int = 0,
    word_timestamps: bool = True,
) -> list[dict]:
    """Transcribe a single audio chunk.

    Args:
        chunk_path: Path to the audio file (WAV).
        offset: Time offset to add to all timestamps (for chunked transcription).
        language: Source language code (e.g., "ja"). None = auto-detect.
        vocab_prompt: Vocabulary hints for the model.
        model_name: Whisper model name.
        device: Device for inference.
        compute_type: Numeric precision.
        retry: Retry attempt number (0 = first try). Higher values apply
               stricter anti-hallucination parameters.
        word_timestamps: Use word-level timestamps for precise timing.

    Returns:
        List of segment dicts: [{start, end, text}].
    """
    model = get_model(model_name, device, compute_type)

    params: dict[str, Any] = {
        "language": language,
        "task": "transcribe",
        "beam_size": 10 if retry == 0 else 5,
        "temperature": 0,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 300 + retry * 150,
            "speech_pad_ms": 200,
        },
        "initial_prompt": vocab_prompt or None,
        "word_timestamps": word_timestamps,
        "condition_on_previous_text": (retry == 0),
    }

    # Escalate anti-hallucination on retries
    if retry > 0:
        params.update(
            no_speech_threshold=0.5,
            log_prob_threshold=-0.8,
            hallucination_silence_threshold=2.0,
        )

    gen, _info = model.transcribe(str(chunk_path), **params)

    segments: list[dict] = []
    for seg in gen:
        text = seg.text.strip()
        if not text:
            continue
        # Use word-level boundaries for tight timing when available
        if word_timestamps and seg.words:
            seg_start = seg.words[0].start + offset
            seg_end = seg.words[-1].end + offset
        else:
            seg_start = seg.start + offset
            seg_end = seg.end + offset
        segments.append({"start": seg_start, "end": seg_end, "text": text})

    return segments
