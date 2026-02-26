"""JSON structured export format."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mediascribe.core.job import Job


def job_to_json(job: Job) -> dict[str, Any]:
    """Convert a completed job to a structured JSON-serializable dict."""
    return {
        "metadata": {
            "source_file": job.input_path.name,
            "duration_sec": job.media_info.duration_sec,
            "source_language": job.media_info.language,
            "media_type": job.media_info.media_type.value,
            "processed_at": datetime.now(UTC).isoformat(),
        },
        "segments": [
            {
                "index": seg.index,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "translation": seg.translation,
                "speaker": seg.speaker,
                "confidence": seg.confidence,
            }
            for seg in job.segments
        ],
        "analysis": job.analysis,
    }


def save_json(job: Job, path: Path) -> None:
    """Write job results to a JSON file."""
    data = job_to_json(job)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
