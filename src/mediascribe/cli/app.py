"""Typer CLI application — the non-TUI entry point.

Usage:
    mediascribe transcribe video.mp4 --lang ja --translate en
    mediascribe transcribe podcast.mp3 --translate en --profile podcast
    mediascribe batch ./videos/ --profile anime --translate en
    mediascribe config set openai_api_key sk-...
    mediascribe tui  # Launch the full TUI (Phase 2)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mediascribe import __version__

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

app = typer.Typer(
    name="mediascribe",
    help="Transcribe, translate, and analyze audio/video media.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"mediascribe [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-V", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """mediascribe — Transcribe, translate, and analyze audio/video media."""


# ── transcribe ───────────────────────────────────────────────────────────────


@app.command()
def transcribe(
    file: Annotated[Path, typer.Argument(help="Input audio or video file")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Source language code (e.g., ja, en, es). Auto-detect if omitted")] = "",
    translate: Annotated[str, typer.Option("--translate", "-t", help="Target language for translation (e.g., en)")] = "",
    profile: Annotated[str, typer.Option("--profile", "-p", help="Prompt profile: general, anime, podcast, meeting")] = "general",
    model: Annotated[str, typer.Option("--model", "-m", help="Translation model")] = "gpt-4.1",
    whisper_model: Annotated[str, typer.Option("--whisper-model", help="Whisper model size")] = "large-v3",
    mode: Annotated[str, typer.Option("--mode", help="Transcription mode: local, api, auto")] = "auto",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("./output"),
    custom: Annotated[str, typer.Option("--custom", help="Custom instructions for translation")] = "",
    no_review: Annotated[bool, typer.Option("--no-review", help="Skip the review (second) pass")] = False,
    formats: Annotated[str, typer.Option("--formats", "-f", help="Output formats: srt,vtt,txt,json (comma-separated)")] = "srt",
) -> None:
    """Transcribe (and optionally translate) a single file."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    output_formats = [f.strip().lower() for f in formats.split(",") if f.strip()]

    run_pipeline_for_file(
        input_path=file,
        output_dir=output,
        source_language=lang or None,
        target_language=translate or None,
        profile=profile,
        translation_model=model,
        whisper_model=whisper_model,
        transcription_mode=mode,
        custom_instructions=custom,
        enable_review=not no_review,
        output_formats=output_formats,
    )


# ── batch ────────────────────────────────────────────────────────────────────


@app.command()
def batch(
    folder: Annotated[Path, typer.Argument(help="Folder of input files")],
    lang: Annotated[str, typer.Option("--lang", "-l")] = "",
    translate: Annotated[str, typer.Option("--translate", "-t")] = "",
    profile: Annotated[str, typer.Option("--profile", "-p")] = "general",
    model: Annotated[str, typer.Option("--model", "-m")] = "gpt-4.1",
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("./output"),
    custom: Annotated[str, typer.Option("--custom")] = "",
    no_review: Annotated[bool, typer.Option("--no-review")] = False,
    formats: Annotated[str, typer.Option("--formats", "-f", help="Output formats: srt,vtt,txt,json")] = "srt",
) -> None:
    """Process all media files in a folder."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {folder}")
        raise typer.Exit(1)

    output_formats = [f.strip().lower() for f in formats.split(",") if f.strip()]

    # Find all media files
    extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov",
                  ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in extensions)

    if not files:
        console.print(f"[yellow]No media files found in {folder}[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Batch processing {len(files)} files[/bold]\n")

    for i, f in enumerate(files, 1):
        console.print(f"\n{'═' * 60}")
        console.print(f"  [{i}/{len(files)}] {f.name}")
        console.print(f"{'═' * 60}\n")

        run_pipeline_for_file(
            input_path=f,
            output_dir=output,
            source_language=lang or None,
            target_language=translate or None,
            profile=profile,
            translation_model=model,
            custom_instructions=custom,
            enable_review=not no_review,
            output_formats=output_formats,
        )

    console.print(f"\n[bold green]All {len(files)} files processed.[/bold green]")


# ── translate (standalone) ────────────────────────────────────────────────────


@app.command()
def translate(
    srt_file: Annotated[Path, typer.Argument(help="Input SRT file to translate")],
    target: Annotated[str, typer.Option("--target", "-t", help="Target language code (e.g., en, es)")],
    source_lang: Annotated[str, typer.Option("--source", "-s", help="Source language (for prompt context)")] = "auto",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory")] = None,
    model: Annotated[str, typer.Option("--model", "-m", help="Translation model")] = "gpt-4.1",
    no_review: Annotated[bool, typer.Option("--no-review", help="Skip the review pass")] = False,
    custom: Annotated[str, typer.Option("--custom", help="Custom instructions for translation")] = "",
) -> None:
    """Translate an existing SRT file to another language."""
    from dotenv import load_dotenv
    load_dotenv()

    from mediascribe.core.config import MediascribeSettings
    from mediascribe.core.events import EventBus, EventType, PipelineEvent
    from mediascribe.formats.srt import read_srt, save_srt
    from mediascribe.models.prompts import TEMPLATES, render_prompt
    from mediascribe.steps.review import review_translations
    from mediascribe.steps.translate import build_translated_srt, translate_subtitles

    if not srt_file.exists():
        console.print(f"[red]Error:[/red] File not found: {srt_file}")
        raise typer.Exit(1)

    if srt_file.suffix.lower() != ".srt":
        console.print(f"[yellow]Warning:[/yellow] Expected .srt file, got {srt_file.suffix}")

    out_dir = (
        output
        if output and output.is_dir()
        else (output.parent if output else srt_file.parent)
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = MediascribeSettings(
        target_language=target,
        source_language=source_lang if source_lang != "auto" else None,
        translation_model=model,
        custom_instructions=custom,
        enable_review_pass=not no_review,
        output_dir=out_dir,
    )
    settings.ensure_dirs()

    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    if not api_key:
        console.print("[red]Error:[/red] OPENAI_API_KEY not set. Set it in env or .env file.")
        raise typer.Exit(1)

    events = EventBus()

    def handler(ev: PipelineEvent) -> None:
        if ev.type == EventType.STEP_PROGRESS:
            console.print(f"    {ev.message} [{int(ev.progress * 100)}%]")
        elif ev.type in (EventType.STEP_START, EventType.STEP_COMPLETE):
            console.print(f"  [cyan]{ev.message}[/cyan]")

    events.subscribe(handler)

    console.print(f"\n[bold]Translating[/bold] {srt_file.name} → {target}\n")

    source_srt = read_srt(srt_file)
    template = TEMPLATES.get("general", TEMPLATES["general"])
    system_prompt, review_prompt = render_prompt(
        template, target, settings.custom_instructions,
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
    stem = srt_file.stem.replace("_draft", "").rsplit("_", 1)[0] if "_" in srt_file.stem else srt_file.stem
    draft_path = out_dir / f"{stem}_{target}_draft.srt"
    save_srt(draft_srt, draft_path)

    final_srt = draft_srt
    final_path = out_dir / f"{stem}_{target}.srt"

    if not no_review and settings.enable_review_pass:
        reviewed = review_translations(
            source_srt=source_srt,
            draft_srt=draft_srt,
            review_prompt=review_prompt,
            model=settings.translation_model,
            api_key=api_key,
            events=events,
        )
        from pysrt import SubRipFile, SubRipItem
        final_srt = SubRipFile()
        for i, sub in enumerate(source_srt):
            text = reviewed.get(i + 1, draft_srt[i].text if i < len(draft_srt) else "")
            final_srt.append(SubRipItem(index=i + 1, start=sub.start, end=sub.end, text=text))
    else:
        final_path = draft_path

    if final_path != draft_path:
        save_srt(final_srt, final_path)

    console.print(f"\n[green]Done.[/green] Output: {final_path}")
    if draft_path != final_path:
        console.print(f"  Draft: {draft_path}")


# ── config ───────────────────────────────────────────────────────────────────


config_app = typer.Typer(help="View or edit configuration.")


@config_app.command("list")
def config_list() -> None:
    """List all configuration values (from env + config file)."""
    from dotenv import load_dotenv
    load_dotenv()

    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    config_path = settings.config_dir / "config.env"

    console.print("[bold]Configuration[/bold] (env + config file)\n")
    console.print(f"  Config file: [dim]{config_path}[/dim]")
    console.print(f"  Exists: [dim]{config_path.exists()}[/dim]\n")

    # Show key settings (mask secrets)
    def _mask(val: str | None, key: str) -> str:
        if val is None:
            return "[dim]not set[/dim]"
        s = str(val)
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            return f"***{s[-4:]}" if len(s) > 4 else "***"
        return s

    for k in sorted(settings.model_fields):
        v = getattr(settings, k, None)
        if k == "openai_api_key" and v:
            v = v.get_secret_value() if hasattr(v, "get_secret_value") else v
        if k == "huggingface_token" and v:
            v = v.get_secret_value() if hasattr(v, "get_secret_value") else v
        console.print(f"  [cyan]{k}[/cyan]: {_mask(v, k)}")


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Setting name (e.g., openai_api_key)")],
) -> None:
    """Get a specific configuration value."""
    from dotenv import load_dotenv
    load_dotenv()

    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    if key not in settings.model_fields:
        console.print(f"[red]Unknown setting:[/red] {key}")
        raise typer.Exit(1)

    v = getattr(settings, key, None)
    if hasattr(v, "get_secret_value"):
        v = "***" if v else None
    console.print(v if v is not None else "[dim]not set[/dim]")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Setting name")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a configuration value (persists to config file)."""
    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    if key not in settings.model_fields:
        console.print(f"[red]Unknown setting:[/red] {key}")
        raise typer.Exit(1)

    config_path = settings.config_dir / "config.env"
    settings.config_dir.mkdir(parents=True, exist_ok=True)

    # Read existing
    lines: list[str] = []
    if config_path.exists():
        lines = [ln.rstrip() for ln in config_path.read_text(encoding="utf-8").splitlines()]

    # Env var name
    env_key = f"MEDIASCRIBE_{key.upper()}"

    # Update or append
    found = False
    for i, ln in enumerate(lines):
        if ln.startswith(f"{env_key}=") or ln.startswith(f"{env_key} "):
            lines[i] = f'{env_key}={value}'
            found = True
            break
    if not found:
        lines.append(f'{env_key}={value}')

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"[green]Set[/green] {key} → [dim]saved to {config_path}[/dim]")


app.add_typer(config_app, name="config")


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    console.print("[yellow]TUI — coming in Phase 2.[/yellow]")
    console.print("Use the CLI commands for now: mediascribe transcribe <file>")


if __name__ == "__main__":
    app()
