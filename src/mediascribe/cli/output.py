"""CLI output helpers — wire pipeline steps together with Rich progress."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from mediascribe.core.config import load_settings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.core.pipeline import Pipeline
from mediascribe.formats.srt import read_srt, save_srt
from mediascribe.models.prompts import TEMPLATES, render_prompt
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.review import ReviewStep, review_translations
from mediascribe.steps.transcribe import TranscribeStep
from mediascribe.steps.translate import TranslateStep, build_translated_srt, translate_subtitles

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
    output_dir: Path | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
    profile: str | None = None,
    translation_model: str | None = None,
    whisper_model: str | None = None,
    transcription_mode: str | None = None,
    custom_instructions: str | None = None,
    enable_review: bool | None = None,
) -> None:
    """Run the full pipeline on a single file with CLI output.

    This is the main entry point called by CLI commands.
    """
    from dotenv import load_dotenv

    load_dotenv()

    # Build settings from config/.env + explicit CLI overrides
    settings = load_settings(
        {
            "source_language": source_language,
            "target_language": target_language,
            "translation_profile": profile,
            "translation_model": translation_model,
            "whisper_model": whisper_model,
            "transcription_mode": transcription_mode,
            "custom_instructions": custom_instructions,
            "enable_review_pass": enable_review,
            "output_dir": output_dir,
        }
    )
    settings.ensure_dirs()
    effective_output_dir = settings.output_dir.resolve()

    # Set up event bus with CLI handler
    events = EventBus()
    events.subscribe(_make_event_handler())

    # Build pipeline
    pipeline = Pipeline(settings, events)
    pipeline.add_step(DetectStep())
    pipeline.add_step(NormalizeStep())
    pipeline.add_step(TranscribeStep())
    if settings.target_language:
        pipeline.add_step(TranslateStep())
        if settings.enable_review_pass:
            pipeline.add_step(ReviewStep())

    # Create job
    job = Job(
        input_path=input_path.resolve(),
        output_dir=effective_output_dir,
    )

    # Print banner
    mode_str = (
        settings.transcription_mode
        if settings.transcription_mode != "auto"
        else f"auto ({settings.whisper_model})"
    )
    console.print("╔══════════════════════════════════════════════════════════╗")
    console.print("║  [bold]mediascribe[/bold] — media transcription pipeline             ║")
    console.print(f"║  Transcription: {mode_str:<40s}║")
    if settings.target_language:
        console.print(f"║  Translation:   {settings.translation_model:<40s}║")
    console.print("╚══════════════════════════════════════════════════════════╝")

    # Run
    result = pipeline.run(job)

    if result.error:
        console.print(f"\n[bold red]Pipeline failed: {result.error}[/bold red]")
        raise SystemExit(1)

    # Summary
    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    for p in sorted(effective_output_dir.glob(f"{job.stem}*")):
        console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")


def _resolve_translate_output_path(
    source_srt_path: Path,
    target_language: str,
    output_path: Path | None,
) -> Path:
    default_name = f"{source_srt_path.stem}_{target_language}.srt"
    if output_path is None:
        return source_srt_path.with_name(default_name)
    if output_path.suffix.lower() == ".srt":
        return output_path
    return output_path / default_name


def run_translate_for_srt(
    source_srt_path: Path,
    target_language: str,
    output_path: Path | None = None,
    profile: str | None = None,
    translation_model: str | None = None,
    custom_instructions: str | None = None,
    enable_review: bool | None = None,
) -> Path:
    """Translate an existing SRT file to a target language."""
    from dotenv import load_dotenv

    load_dotenv()

    settings = load_settings(
        {
            "target_language": target_language,
            "translation_profile": profile,
            "translation_model": translation_model,
            "custom_instructions": custom_instructions,
            "enable_review_pass": enable_review,
        }
    )
    if not settings.target_language:
        raise ValueError("target_language is required")

    source_srt_path = source_srt_path.resolve()
    source_srt = read_srt(source_srt_path)

    events = EventBus()
    events.subscribe(_make_event_handler())

    profile_name = settings.translation_profile
    template = TEMPLATES.get(profile_name, TEMPLATES["general"])
    system_prompt, review_prompt = render_prompt(
        template,
        settings.target_language,
        settings.custom_instructions,
    )
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None

    events.emit(
        PipelineEvent(
            type=EventType.STEP_START,
            step_name="translate",
            message=f"Starting translate: {source_srt_path.name}",
        )
    )
    translations = translate_subtitles(
        source_srt=source_srt,
        system_prompt=system_prompt,
        model=settings.translation_model,
        api_key=api_key,
        batch_size=settings.translation_batch_size,
        events=events,
    )
    draft_srt = build_translated_srt(source_srt, translations)
    events.emit(
        PipelineEvent(
            type=EventType.STEP_COMPLETE,
            step_name="translate",
            message=f"Completed translate ({len(translations)} lines)",
        )
    )

    final_path = _resolve_translate_output_path(
        source_srt_path, settings.target_language, output_path
    ).resolve()
    final_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path = final_path.with_name(f"{final_path.stem}_draft.srt")
    save_srt(draft_srt, draft_path)

    if settings.enable_review_pass:
        events.emit(
            PipelineEvent(
                type=EventType.STEP_START,
                step_name="review",
                message=f"Starting review: {draft_path.name}",
            )
        )
        reviewed = review_translations(
            source_srt=source_srt,
            draft_srt=draft_srt,
            review_prompt=review_prompt,
            model=settings.translation_model,
            api_key=api_key,
            events=events,
        )
        final_srt = build_translated_srt(source_srt, reviewed)
        events.emit(
            PipelineEvent(
                type=EventType.STEP_COMPLETE,
                step_name="review",
                message=f"Completed review ({len(reviewed)} lines)",
            )
        )
    else:
        final_srt = draft_srt

    save_srt(final_srt, final_path)
    console.print(f"\n[bold green]✅ Final subtitles:[/bold green] {final_path}")
    console.print(f"[dim]Draft saved:[/dim] {draft_path}")
    return final_path
