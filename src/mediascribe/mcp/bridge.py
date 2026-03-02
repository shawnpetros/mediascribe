"""Pipeline adapter — constructs and runs pipelines, returns Job objects."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from mediascribe.core.config import MediascribeSettings, TranscriptionMode
from mediascribe.core.events import EventBus, EventHandler
from mediascribe.core.job import Job, JobStatus
from mediascribe.core.pipeline import Pipeline
from mediascribe.formats.srt import srt_to_segments
from mediascribe.steps.analyze import AnalyzeStep
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.export import ExportStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.review import ReviewStep
from mediascribe.steps.transcribe import TranscribeStep
from mediascribe.steps.translate import TranslateStep


class PipelineError(Exception):
    """Raised when a pipeline run fails.

    The partially-completed Job is attached so callers can inspect
    whatever results were produced before the failure.
    """

    def __init__(self, message: str, job: Job | None = None) -> None:
        super().__init__(message)
        self.job = job


def run_transcription(
    file_path: str,
    source_language: str | None = None,
    target_language: str | None = None,
    profile: str = "general",
    whisper_model: str = "large-v3",
    translation_model: str = "gpt-4.1",
    transcription_mode: str = "auto",
    output_formats: list[str] | None = None,
    enable_analyze: bool = False,
    enable_diarize: bool = False,
    enable_review: bool = True,
    custom_instructions: str = "",
    output_dir: str | None = None,
    on_progress: EventHandler | None = None,
) -> Job:
    """Run the full transcription pipeline and return the Job.

    This mirrors cli/output.py's run_pipeline_for_file but returns the Job
    instead of printing Rich output.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        PipelineError: If the pipeline fails (job attached with partial results).
    """
    from dotenv import load_dotenv

    load_dotenv()

    input_path = Path(file_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    out = Path(output_dir).resolve() if output_dir else Path("./output").resolve()

    settings = MediascribeSettings(
        source_language=source_language,
        target_language=target_language,
        translation_model=translation_model,
        whisper_model=whisper_model,
        transcription_mode=cast(TranscriptionMode, transcription_mode),
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=out,
        profile=profile,
        output_formats=output_formats or ["srt"],
    )
    settings.ensure_dirs()

    events = EventBus()
    if on_progress is not None:
        events.subscribe(on_progress)

    pipeline = Pipeline(settings, events)
    pipeline.add_step(DetectStep())
    pipeline.add_step(NormalizeStep())
    pipeline.add_step(TranscribeStep())
    if enable_diarize:
        from mediascribe.steps.diarize import DiarizeStep

        pipeline.add_step(DiarizeStep())
    if target_language:
        pipeline.add_step(TranslateStep())
        if enable_review:
            pipeline.add_step(ReviewStep())
    if enable_analyze:
        pipeline.add_step(AnalyzeStep())
    pipeline.add_step(ExportStep())

    job = Job(input_path=input_path, output_dir=out)
    result = pipeline.run(job)

    if result.status == JobStatus.FAILED:
        raise PipelineError(result.error or "Pipeline failed", job=result)

    return result


def run_translation(
    srt_path: str,
    target_language: str = "en",
    profile: str = "general",
    translation_model: str = "gpt-4.1",
    custom_instructions: str = "",
    enable_review: bool = True,
    output_dir: str | None = None,
    on_progress: EventHandler | None = None,
) -> Job:
    """Translate an existing SRT file and return the Job.

    This mirrors cli/output.py's run_translate_srt but returns the Job
    instead of printing Rich output.

    Raises:
        FileNotFoundError: If the SRT file doesn't exist.
        PipelineError: If the pipeline fails (job attached with partial results).
    """
    from dotenv import load_dotenv

    load_dotenv()

    srt = Path(srt_path).resolve()
    if not srt.exists():
        raise FileNotFoundError(f"SRT file not found: {srt_path}")

    out = Path(output_dir).resolve() if output_dir else Path("./output").resolve()

    settings = MediascribeSettings(
        target_language=target_language,
        translation_model=translation_model,
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=out,
        profile=profile,
    )
    settings.ensure_dirs()

    events = EventBus()
    if on_progress is not None:
        events.subscribe(on_progress)

    # Copy source SRT into output dir so translate step can find it
    stem = srt.stem
    source_srt_dest = out / f"{stem}_source.srt"
    shutil.copy2(srt, source_srt_dest)
    settings.source_language = "source"

    job = Job(input_path=srt, output_dir=out)
    job.segments = srt_to_segments(srt)

    pipeline = Pipeline(settings, events)
    pipeline.add_step(TranslateStep())
    if enable_review:
        pipeline.add_step(ReviewStep())

    result = pipeline.run(job)

    if result.status == JobStatus.FAILED:
        raise PipelineError(result.error or "Translation failed", job=result)

    return result
