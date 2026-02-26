"""Export step — writes output files in all requested formats.

Reads the final segments from the job and writes each format
specified in settings.output_formats. Supports: srt, vtt, txt, json.
"""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job
from mediascribe.formats.json_export import save_json
from mediascribe.formats.srt import segments_to_srt, save_srt
from mediascribe.formats.transcript import save_transcript
from mediascribe.formats.vtt import save_vtt
from mediascribe.steps.base import PipelineStep, StepResult

FORMAT_EXTENSIONS = {"srt", "vtt", "txt", "json"}


class ExportStep(PipelineStep):
    """Write output files in all formats requested by settings.output_formats.

    This step runs after all processing is complete. It reads job.segments
    and writes one file per requested format into job.output_dir.

    Supported formats:
        srt  — SubRip subtitle file
        vtt  — WebVTT subtitle file
        txt  — Plain text transcript with timestamps
        json — Structured JSON export with metadata
    """

    name = "export"
    description = "Exporting output files"

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        formats = settings.output_formats
        has_translation = settings.target_language is not None
        lang_suffix = settings.target_language or settings.source_language or "unknown"
        written: list[str] = []

        for fmt in formats:
            fmt = fmt.lower().strip()
            if fmt not in FORMAT_EXTENSIONS:
                events.warn(f"Unknown output format '{fmt}' — skipping", step=self.name)
                continue

            try:
                path = self._write_format(
                    fmt, job, settings, lang_suffix, has_translation,
                )
                written.append(path.name)
                events.log(f"Wrote {path.name}", step=self.name)
            except Exception as exc:
                events.warn(f"Failed to write {fmt}: {exc}", step=self.name)

        return StepResult(data={"written": written, "count": len(written)})

    def _write_format(
        self,
        fmt: str,
        job: Job,
        settings: MediascribeSettings,
        lang_suffix: str,
        has_translation: bool,
    ) -> Path:
        stem = job.stem

        if fmt == "srt":
            path = job.output_dir / f"{stem}_{lang_suffix}.srt"
            if not path.exists():
                srt = segments_to_srt(job.segments, use_translation=has_translation)
                save_srt(srt, path)
            return path

        if fmt == "vtt":
            path = job.output_dir / f"{stem}_{lang_suffix}.vtt"
            save_vtt(job.segments, path, use_translation=has_translation)
            return path

        if fmt == "txt":
            path = job.output_dir / f"{stem}_{lang_suffix}.txt"
            save_transcript(
                job.segments, path,
                use_translation=has_translation,
                include_timestamps=True,
                include_speakers=True,
            )
            return path

        if fmt == "json":
            path = job.output_dir / f"{stem}.json"
            save_json(job, path)
            return path

        raise ValueError(f"Unsupported format: {fmt}")

    def can_skip(self, job: Job) -> bool:
        return False
