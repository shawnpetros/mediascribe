"""Pure serialization functions — convert domain objects to JSON-safe dicts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.job import Job


def job_to_result(job: Job) -> dict[str, Any]:
    """Convert a completed Job to a JSON-serializable result dict."""
    segments = [
        {
            "index": s.index,
            "start": s.start,
            "end": s.end,
            "text": s.text,
            **({"translation": s.translation} if s.translation else {}),
            **({"speaker": s.speaker} if s.speaker else {}),
            **({"confidence": s.confidence} if s.confidence is not None else {}),
        }
        for s in job.segments
    ]

    result: dict[str, Any] = {
        "status": job.status.value,
        "input_path": str(job.input_path),
        "output_dir": str(job.output_dir),
        "segment_count": len(segments),
        "segments": segments,
    }

    if job.media_info.duration_sec > 0:
        result["duration"] = job.duration_str
        result["media_type"] = job.media_info.media_type.value

    if job.analysis:
        result["analysis"] = job.analysis

    if job.error:
        result["error"] = job.error

    return result


def settings_to_result(settings: MediascribeSettings) -> dict[str, Any]:
    """Convert settings to a dict with secrets redacted."""
    return {
        "profile": settings.profile,
        "transcription_mode": settings.transcription_mode,
        "whisper_model": settings.whisper_model,
        "whisper_device": settings.whisper_device,
        "whisper_compute": settings.whisper_compute,
        "translation_model": settings.translation_model,
        "translation_batch_size": settings.translation_batch_size,
        "enable_review_pass": settings.enable_review_pass,
        "source_language": settings.source_language,
        "target_language": settings.target_language,
        "output_formats": settings.output_formats,
        "output_dir": str(settings.output_dir),
        "max_concurrency": settings.max_concurrency,
        "openai_api_key": "***configured***" if settings.openai_api_key else None,
        "huggingface_token": "***configured***" if settings.huggingface_token else None,
    }


def profiles_to_result(config_dir: Path | None = None) -> dict[str, Any]:
    """List all profiles with descriptions."""
    from mediascribe.core.profiles import list_profiles, load_profile

    names = list_profiles(config_dir)
    profiles: list[dict[str, Any]] = []

    for name in names:
        try:
            p = load_profile(name, config_dir)
            profiles.append(
                {
                    "name": p.name,
                    "description": p.description,
                    "overrides": p.overrides,
                }
            )
        except FileNotFoundError:
            profiles.append(
                {
                    "name": name,
                    "description": "(load error)",
                    "overrides": {},
                }
            )

    return {"profiles": profiles}
