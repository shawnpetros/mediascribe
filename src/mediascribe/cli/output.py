"""CLI output helpers — wire pipeline steps together with Rich progress."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.core.pipeline import Pipeline
from mediascribe.steps.detect import DetectStep
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
    if target_language:
        pipeline.add_step(TranslateStep())
        if enable_review:
            pipeline.add_step(ReviewStep())

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
    console.print(f"  [bold]Output:[/bold]")
    for p in sorted(output_dir.glob(f"{job.stem}*")):
        console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")
