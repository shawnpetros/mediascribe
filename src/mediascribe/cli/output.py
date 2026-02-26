"""CLI output helpers — wire pipeline steps together with Rich progress."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from mediascribe.core.config import MediascribeSettings, _default_config_dir
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
    """Run the full pipeline on a single file with CLI output."""
    from dotenv import load_dotenv
    load_dotenv()

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

    events = EventBus()
    events.subscribe(_make_event_handler())

    pipeline = Pipeline(settings, events)
    pipeline.add_step(DetectStep())
    pipeline.add_step(NormalizeStep())
    pipeline.add_step(TranscribeStep())
    if target_language:
        pipeline.add_step(TranslateStep())
        if enable_review:
            pipeline.add_step(ReviewStep())

    job = Job(
        input_path=input_path.resolve(),
        output_dir=output_dir.resolve(),
    )

    mode_str = transcription_mode if transcription_mode != "auto" else f"auto ({whisper_model})"
    console.print("╔══════════════════════════════════════════════════════════╗")
    console.print("║  [bold]mediascribe[/bold] — media transcription pipeline             ║")
    console.print(f"║  Transcription: {mode_str:<40s}║")
    if target_language:
        console.print(f"║  Translation:   {translation_model:<40s}║")
    console.print("╚══════════════════════════════════════════════════════════╝")

    result = pipeline.run(job)

    if result.error:
        console.print(f"\n[bold red]Pipeline failed: {result.error}[/bold red]")
        raise SystemExit(1)

    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    for p in sorted(output_dir.glob(f"{job.stem}*")):
        console.print(f"    {p.name}")
    console.print(f"{'─' * 60}")


# ── Standalone translate ─────────────────────────────────────────────────────


def run_translate_srt(
    srt_path: Path,
    target_language: str,
    output_dir: Path,
    profile: str = "general",
    translation_model: str = "gpt-4.1",
    custom_instructions: str = "",
    enable_review: bool = True,
    batch_size: int = 15,
) -> None:
    """Translate an existing SRT file without running the full pipeline."""
    from dotenv import load_dotenv
    load_dotenv()

    from mediascribe.formats.srt import read_srt, save_srt
    from mediascribe.models.prompts import TEMPLATES, render_prompt
    from mediascribe.steps.translate import build_translated_srt, translate_subtitles
    from mediascribe.steps.review import review_translations

    settings = MediascribeSettings(
        target_language=target_language,
        translation_model=translation_model,
        custom_instructions=custom_instructions,
        enable_review_pass=enable_review,
        output_dir=output_dir,
        translation_batch_size=batch_size,
    )

    events = EventBus()
    events.subscribe(_make_event_handler())

    template = TEMPLATES.get(profile, TEMPLATES["general"])
    system_translate, system_review = render_prompt(
        template, target_language, custom_instructions,
    )

    stem = srt_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    draft_path = output_dir / f"{stem}_{target_language}_draft.srt"
    final_path = output_dir / f"{stem}_{target_language}.srt"

    console.print("╔══════════════════════════════════════════════════════════╗")
    console.print("║  [bold]mediascribe[/bold] — standalone SRT translation               ║")
    console.print(f"║  Source:   {srt_path.name:<46s}║")
    console.print(f"║  Target:   {target_language:<46s}║")
    console.print(f"║  Profile:  {profile:<46s}║")
    console.print(f"║  Model:    {translation_model:<46s}║")
    console.print("╚══════════════════════════════════════════════════════════╝")

    source_srt = read_srt(srt_path)
    console.print(f"\n  Loaded {len(source_srt)} subtitles from {srt_path.name}")

    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None

    events.emit(PipelineEvent(
        type=EventType.STEP_START,
        step_name="translate",
        message="Translating subtitles",
    ))

    translations = translate_subtitles(
        source_srt=source_srt,
        system_prompt=system_translate,
        model=translation_model,
        api_key=api_key,
        batch_size=batch_size,
        events=events,
    )

    translated_srt = build_translated_srt(source_srt, translations)
    save_srt(translated_srt, draft_path)

    events.emit(PipelineEvent(
        type=EventType.STEP_COMPLETE,
        step_name="translate",
        message=f"Draft translation: {draft_path.name} ({len(translations)} subs)",
    ))

    if enable_review:
        events.emit(PipelineEvent(
            type=EventType.STEP_START,
            step_name="review",
            message="Reviewing translation quality",
        ))

        reviewed = review_translations(
            source_srt=source_srt,
            draft_srt=translated_srt,
            review_prompt=system_review,
            model=translation_model,
            api_key=api_key,
            events=events,
        )

        from pysrt import SubRipFile, SubRipItem
        final_srt = SubRipFile()
        for i, sub in enumerate(source_srt):
            text = reviewed.get(i + 1, translated_srt[i].text if i < len(translated_srt) else "")
            final_srt.append(SubRipItem(
                index=i + 1,
                start=sub.start,
                end=sub.end,
                text=text,
            ))
        save_srt(final_srt, final_path)

        events.emit(PipelineEvent(
            type=EventType.STEP_COMPLETE,
            step_name="review",
            message=f"Final translation: {final_path.name}",
        ))
    else:
        import shutil
        shutil.copy2(draft_path, final_path)

    console.print(f"\n{'─' * 60}")
    console.print("  [bold]Output:[/bold]")
    console.print(f"    {draft_path.name}")
    if enable_review:
        console.print(f"    {final_path.name}")
    console.print(f"{'─' * 60}")


# ── Config management ────────────────────────────────────────────────────────


_CONFIG_DESCRIPTIONS: dict[str, str] = {
    "openai_api_key": "OpenAI API key for transcription and translation",
    "huggingface_token": "HuggingFace token for speaker diarization models",
    "transcription_mode": "Transcription engine: local, api, or auto",
    "whisper_model": "Whisper model size (tiny, base, small, medium, large-v3)",
    "whisper_device": "Device for Whisper (auto, cpu, cuda)",
    "whisper_compute": "Compute type (int8, float16, float32)",
    "chunk_duration_sec": "Audio chunk length in seconds",
    "chunk_overlap_sec": "Overlap between chunks in seconds",
    "word_timestamps": "Enable word-level timestamps",
    "translation_model": "OpenAI model for translation",
    "translation_batch_size": "Subtitles per translation API call",
    "enable_review_pass": "Enable two-pass translation review",
    "custom_instructions": "Custom instructions for translation prompts",
    "source_language": "Source language code (None = auto-detect)",
    "target_language": "Target language code (None = skip translation)",
    "max_concurrency": "Max concurrent processing jobs",
    "output_dir": "Default output directory",
    "output_formats": "Output format list (srt, vtt, txt, json, md)",
    "max_subtitle_duration_sec": "Maximum subtitle display duration",
    "min_gap_sec": "Minimum gap between subtitles",
    "chars_per_second": "Reading speed for duration estimation",
}


def _load_user_config() -> dict[str, Any]:
    """Load user config from TOML file."""
    config_file = _default_config_dir() / "config.toml"
    if config_file.exists():
        return tomllib.loads(config_file.read_text(encoding="utf-8"))
    return {}


def _save_user_config(data: dict[str, Any]) -> None:
    """Save user config to TOML file."""
    config_dir = _default_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"

    lines: list[str] = []
    for key, value in sorted(data.items()):
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif isinstance(value, list):
            items = ", ".join(f'"{v}"' for v in value)
            lines.append(f"{key} = [{items}]")
        else:
            lines.append(f'{key} = "{value}"')

    config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show_config() -> None:
    """Display current effective configuration."""
    settings = MediascribeSettings()
    user_config = _load_user_config()

    table = Table(title="mediascribe configuration", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    for field_name in sorted(settings.model_fields):
        if field_name in ("config_dir",):
            continue
        value = getattr(settings, field_name)
        if hasattr(value, "get_secret_value"):
            display = "****" if value else "(not set)"
        elif value is None:
            display = "(not set)"
        else:
            display = str(value)

        source = "user config" if field_name in user_config else "default"
        import os
        env_key = f"MEDIASCRIBE_{field_name.upper()}"
        if env_key in os.environ:
            source = "env var"

        table.add_row(field_name, display, source)

    console.print(table)
    console.print(f"\n  Config file: {_default_config_dir() / 'config.toml'}")


def set_config_value(key: str, value: str) -> None:
    """Set a config key in the user config file."""
    if key not in MediascribeSettings.model_fields:
        console.print(f"[red]Error:[/red] Unknown config key: {key}")
        console.print(f"Run [bold]mediascribe config list[/bold] to see available keys.")
        return

    user_config = _load_user_config()
    field_info = MediascribeSettings.model_fields[key]
    annotation = field_info.annotation

    parsed: Any = value
    if annotation is bool or str(annotation) == "bool":
        parsed = value.lower() in ("true", "1", "yes")
    elif annotation is int or str(annotation) == "int":
        parsed = int(value)
    elif annotation is float or str(annotation) == "float":
        parsed = float(value)

    user_config[key] = parsed
    _save_user_config(user_config)
    console.print(f"[green]Set[/green] {key} = {parsed}")
    console.print(f"  Saved to {_default_config_dir() / 'config.toml'}")


def get_config_value(key: str) -> None:
    """Print a single config value."""
    if key not in MediascribeSettings.model_fields:
        console.print(f"[red]Error:[/red] Unknown config key: {key}")
        return

    settings = MediascribeSettings()
    value = getattr(settings, key)
    if hasattr(value, "get_secret_value"):
        display = "****" if value else "(not set)"
    elif value is None:
        display = "(not set)"
    else:
        display = str(value)

    console.print(f"{key} = {display}")


def list_config_keys() -> None:
    """List all config keys with descriptions."""
    table = Table(title="Available Configuration Keys", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Description")
    table.add_column("Default", style="dim")

    settings = MediascribeSettings()
    for field_name in sorted(settings.model_fields):
        if field_name in ("config_dir",):
            continue
        desc = _CONFIG_DESCRIPTIONS.get(field_name, "")
        value = getattr(settings, field_name)
        if hasattr(value, "get_secret_value"):
            default = "(secret)"
        elif value is None:
            default = "(none)"
        else:
            default = str(value)
        table.add_row(field_name, desc, default)

    console.print(table)


# ── Model management ────────────────────────────────────────────────────────


WHISPER_MODELS = {
    "tiny": "~75 MB — fastest, lowest accuracy",
    "base": "~140 MB — fast, basic accuracy",
    "small": "~460 MB — good balance of speed and accuracy",
    "medium": "~1.5 GB — higher accuracy, slower",
    "large-v3": "~3 GB — best accuracy, requires more resources",
    "large-v3-turbo": "~1.6 GB — near-large accuracy, faster",
    "distil-large-v3": "~1.5 GB — distilled, faster inference",
}


def list_whisper_models() -> None:
    """List available Whisper models with download status."""
    from mediascribe.utils.paths import xdg_cache_dir

    cache_dir = xdg_cache_dir() / "models"

    table = Table(title="Whisper Models", show_header=True)
    table.add_column("Model", style="cyan")
    table.add_column("Description")
    table.add_column("Status", style="green")

    for name, desc in WHISPER_MODELS.items():
        model_dir = cache_dir / f"faster-whisper-{name}"
        status = "downloaded" if model_dir.exists() else "not downloaded"
        style = "green" if model_dir.exists() else "dim"
        table.add_row(name, desc, f"[{style}]{status}[/{style}]")

    console.print(table)
    console.print(f"\n  Cache directory: {cache_dir}")


def download_whisper_model(model_name: str) -> None:
    """Download a Whisper model using huggingface_hub."""
    if model_name not in WHISPER_MODELS:
        console.print(f"[red]Error:[/red] Unknown model: {model_name}")
        console.print(f"Available: {', '.join(WHISPER_MODELS)}")
        return

    console.print(f"Downloading [bold]{model_name}[/bold]...")
    console.print(f"  {WHISPER_MODELS[model_name]}")

    try:
        from huggingface_hub import snapshot_download
        from mediascribe.utils.paths import xdg_cache_dir

        cache_dir = xdg_cache_dir() / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        repo_id = f"Systran/faster-whisper-{model_name}"
        local_dir = cache_dir / f"faster-whisper-{model_name}"

        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
        )
        console.print(f"\n[green]Downloaded[/green] {model_name} to {local_dir}")
    except ImportError:
        console.print("[red]Error:[/red] huggingface_hub not available.")
        console.print("The model will be auto-downloaded on first use via faster-whisper.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
