"""CLI output helpers — wire pipeline steps together with Rich progress."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from rich.console import Console

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.core.pipeline import Pipeline
from mediascribe.formats.json_export import save_json
from mediascribe.formats.transcript import save_transcript
from mediascribe.formats.vtt import save_vtt
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.review import ReviewStep
from mediascribe.steps.transcribe import TranscribeStep
from mediascribe.steps.translate import TranslateStep

console = Console()


def _make_event_handler() -> Callable[[PipelineEvent], None]:
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


def _export_additional_formats(job: Job, settings: MediascribeSettings) -> None:
    """Export job segments to VTT, transcript, JSON per output_formats config."""
    if not job.segments:
        return

    use_translation = bool(settings.target_language and any(s.translation for s in job.segments))
    lang = (
        settings.target_language
        if use_translation
        else (settings.source_language or (job.media_info.language if job.media_info else None) or "unknown")
    )
    base_name = f"{job.stem}_{lang}"

    for fmt in settings.output_formats:
        fmt_lower = fmt.lower()
        if fmt_lower == "srt":
            # SRT is already written by transcribe/review steps
            continue
        if fmt_lower == "vtt":
            path = job.output_dir / f"{base_name}.vtt"
            save_vtt(job.segments, path, use_translation=use_translation)
            console.print(f"    [dim]Exported VTT → {path.name}[/dim]")
        elif fmt_lower in ("transcript", "txt"):
            path = job.output_dir / f"{base_name}.txt"
            save_transcript(
                job.segments,
                path,
                use_translation=use_translation,
                include_timestamps=True,
                include_speakers=True,
            )
            console.print(f"    [dim]Exported transcript → {path.name}[/dim]")
        elif fmt_lower == "json":
            path = job.output_dir / f"{job.stem}.json"
            save_json(job, path)
            console.print(f"    [dim]Exported JSON → {path.name}[/dim]")


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
        transcription_mode=cast(Literal["local", "api", "auto"], transcription_mode or "auto"),
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=output_dir,
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

    # Multi-format export (VTT, transcript, JSON) — SRT is already written by pipeline
    _export_additional_formats(job, settings)

    # Summary
    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    for p in sorted(output_dir.glob(f"{job.stem}*")):
        console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")
