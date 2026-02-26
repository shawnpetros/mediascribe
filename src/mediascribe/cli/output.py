"""CLI output helpers — wire pipeline steps together with Rich progress."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.core.pipeline import Pipeline
from mediascribe.steps.analyze import AnalyzeStep
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.diarize import DiarizeStep
from mediascribe.steps.export import ExportStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.review import ReviewStep
from mediascribe.steps.transcribe import TranscribeStep
from mediascribe.steps.translate import TranslateStep

console = Console()


def _make_event_handler() -> callable:
    """Create a Rich-based event handler for the CLI."""

    def handler(event: PipelineEvent) -> None:
        match event.type:
            case EventType.JOB_START:
                console.print(f"\n╔{'═' * 58}╗")
                console.print(f"║  [bold]{event.message:<56s}[/bold]║")
                console.print(f"╚{'═' * 58}╝")

            case EventType.STEP_START:
                console.print(f"\n  [bold cyan]▶ {event.message}[/bold cyan]")

            case EventType.STEP_PROGRESS:
                pct = int(event.progress * 100)
                console.print(f"    {event.message} [{pct}%]")

            case EventType.STEP_COMPLETE:
                console.print(f"  [green]✓[/green] {event.message}")

            case EventType.STEP_SKIPPED:
                console.print(f"  [dim]⏭  {event.message}[/dim]")

            case EventType.STEP_ERROR:
                console.print(f"  [red]✗ {event.message}[/red]")

            case EventType.JOB_COMPLETE:
                console.print(f"\n  [bold green]✅ {event.message}[/bold green]")

            case EventType.JOB_ERROR:
                console.print(f"\n  [bold red]❌ {event.message}[/bold red]")

            case EventType.LOG:
                step = f"[{event.step_name}] " if event.step_name else ""
                console.print(f"    {step}{event.message}")

            case EventType.WARNING:
                step = f"[{event.step_name}] " if event.step_name else ""
                console.print(f"    [yellow]⚠ {step}{event.message}[/yellow]")

    return handler


def run_pipeline_for_file(
    input_path: Path,
    output_dir: Path,
    source_language: str | None = None,
    target_language: str | None = None,
    profile: str = "general",
    translation_model: str = "gpt-4.1",
    whisper_model: str = "large-v3",
    transcription_mode: str = "auto",
    custom_instructions: str = "",
    enable_review: bool = True,
    output_formats: list[str] | None = None,
    enable_diarize: bool = False,
    enable_analyze: bool = False,
) -> None:
    """Run the full pipeline on a single file with CLI output.

    This is the main entry point called by CLI commands.
    """
    from dotenv import load_dotenv

    load_dotenv()

    # Build settings
    settings = MediascribeSettings(
        source_language=source_language,
        target_language=target_language,
        translation_model=translation_model,
        whisper_model=whisper_model,
        transcription_mode=transcription_mode,
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=output_dir,
        profile=profile,
        output_formats=output_formats or ["srt"],
    )
    settings.ensure_dirs()

    # Set up event bus with CLI handler
    events = EventBus()
    events.subscribe(_make_event_handler())

    # Build pipeline
    pipeline = Pipeline(settings, events)
    pipeline.add_step(DetectStep())
    pipeline.add_step(NormalizeStep())
    pipeline.add_step(TranscribeStep())
    if enable_diarize:
        pipeline.add_step(DiarizeStep())
    if target_language:
        pipeline.add_step(TranslateStep())
        if enable_review:
            pipeline.add_step(ReviewStep())
    if enable_analyze:
        pipeline.add_step(AnalyzeStep())
    pipeline.add_step(ExportStep())

    # Create job
    job = Job(
        input_path=input_path.resolve(),
        output_dir=output_dir.resolve(),
    )

    # Print banner
    mode_str = transcription_mode if transcription_mode != "auto" else f"auto ({whisper_model})"
    console.print("╔══════════════════════════════════════════════════════════╗")
    console.print("║  [bold]mediascribe[/bold] — media transcription pipeline             ║")
    console.print(f"║  Transcription: {mode_str:<40s}║")
    if target_language:
        console.print(f"║  Translation:   {translation_model:<40s}║")
    console.print("╚══════════════════════════════════════════════════════════╝")

    # Run
    result = pipeline.run(job)

    if result.error:
        console.print(f"\n[bold red]Pipeline failed: {result.error}[/bold red]")
        raise SystemExit(1)

    # Summary
    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    for p in sorted(output_dir.glob(f"{job.stem}*")):
        console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")


def run_translate_srt(
    srt_path: Path,
    output_dir: Path,
    target_language: str = "en",
    profile: str = "general",
    translation_model: str = "gpt-4.1",
    custom_instructions: str = "",
    enable_review: bool = True,
) -> None:
    """Translate an existing SRT file without re-transcribing.

    Runs only the translate (and optionally review) steps on an SRT file,
    producing a translated SRT in the output directory.
    """
    import shutil

    from dotenv import load_dotenv

    from mediascribe.formats.srt import srt_to_segments

    load_dotenv()

    settings = MediascribeSettings(
        target_language=target_language,
        translation_model=translation_model,
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=output_dir,
        profile=profile,
    )
    settings.ensure_dirs()

    events = EventBus()
    events.subscribe(_make_event_handler())

    # Copy source SRT into output dir so translate step can find it
    stem = srt_path.stem
    source_srt_dest = output_dir.resolve() / f"{stem}_source.srt"
    shutil.copy2(srt_path, source_srt_dest)
    settings.source_language = "source"

    # Build a minimal job with segments loaded from the SRT
    job = Job(
        input_path=srt_path.resolve(),
        output_dir=output_dir.resolve(),
    )
    job.segments = srt_to_segments(srt_path)

    # Build translate-only pipeline
    pipeline = Pipeline(settings, events)
    pipeline.add_step(TranslateStep())
    if enable_review:
        pipeline.add_step(ReviewStep())

    console.print("╔══════════════════════════════════════════════════════════╗")
    console.print("║  [bold]mediascribe[/bold] — SRT translation pipeline               ║")
    console.print(f"║  Model:    {translation_model:<45s}║")
    console.print(f"║  Profile:  {profile:<45s}║")
    console.print(f"║  Target:   {target_language:<45s}║")
    console.print("╚══════════════════════════════════════════════════════════╝")

    result = pipeline.run(job)

    if result.error:
        console.print(f"\n[bold red]Translation failed: {result.error}[/bold red]")
        raise SystemExit(1)

    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    for p in sorted(output_dir.glob(f"{stem}*")):
        if p != source_srt_dest:
            console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")
