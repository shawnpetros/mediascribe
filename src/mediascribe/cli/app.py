"""Typer CLI application — the non-TUI entry point.

Usage:
    mediascribe transcribe video.mp4 --lang ja --translate en
    mediascribe transcribe podcast.mp3 --translate en --profile podcast
    mediascribe translate subs.srt --target en --profile anime
    mediascribe batch ./videos/ --profile anime --translate en
    mediascribe config show
    mediascribe config set openai_api_key sk-...
    mediascribe models list
    mediascribe tui
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from mediascribe import __version__

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

app = typer.Typer(
    name="mediascribe",
    help="Transcribe, translate, and analyze audio/video media.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
config_app = typer.Typer(help="View and manage configuration.")
models_app = typer.Typer(help="Manage Whisper models.")
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"mediascribe [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
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
) -> None:
    """Transcribe (and optionally translate) a single file."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

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
    )


# ── translate (standalone) ───────────────────────────────────────────────────


@app.command()
def translate(
    srt_file: Annotated[Path, typer.Argument(help="Source-language SRT file to translate")],
    target: Annotated[str, typer.Option("--target", "-t", help="Target language (e.g., en, ja, es)")],
    profile: Annotated[str, typer.Option("--profile", "-p", help="Prompt profile: general, anime, podcast, meeting")] = "general",
    model: Annotated[str, typer.Option("--model", "-m", help="Translation model")] = "gpt-4.1",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory (default: same as input)")] = Path(""),
    custom: Annotated[str, typer.Option("--custom", help="Custom instructions for translation")] = "",
    no_review: Annotated[bool, typer.Option("--no-review", help="Skip the review (second) pass")] = False,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Subtitles per API call")] = 15,
) -> None:
    """Translate an existing SRT file to another language."""
    from mediascribe.cli.output import run_translate_srt

    if not srt_file.exists():
        console.print(f"[red]Error:[/red] File not found: {srt_file}")
        raise typer.Exit(1)

    if srt_file.suffix.lower() != ".srt":
        console.print(f"[red]Error:[/red] Expected an .srt file, got: {srt_file.suffix}")
        raise typer.Exit(1)

    out_dir = output if str(output) else srt_file.parent
    run_translate_srt(
        srt_path=srt_file,
        target_language=target,
        output_dir=out_dir,
        profile=profile,
        translation_model=model,
        custom_instructions=custom,
        enable_review=not no_review,
        batch_size=batch_size,
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
) -> None:
    """Process all media files in a folder."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {folder}")
        raise typer.Exit(1)

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
        )

    console.print(f"\n[bold green]All {len(files)} files processed.[/bold green]")


# ── config ───────────────────────────────────────────────────────────────────


@config_app.callback(invoke_without_command=True)
def config_default(ctx: typer.Context) -> None:
    """View or manage configuration settings."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)


@config_app.command("show")
def config_show() -> None:
    """Display current configuration."""
    from mediascribe.cli.output import show_config

    show_config()


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key (e.g., openai_api_key)")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a configuration value in the user config file."""
    from mediascribe.cli.output import set_config_value

    set_config_value(key, value)


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Configuration key to read")],
) -> None:
    """Get a specific configuration value."""
    from mediascribe.cli.output import get_config_value

    get_config_value(key)


@config_app.command("list")
def config_list() -> None:
    """List all available configuration keys and their descriptions."""
    from mediascribe.cli.output import list_config_keys

    list_config_keys()


@config_app.command("path")
def config_path() -> None:
    """Print the path to the user config file."""
    from mediascribe.core.config import _default_config_dir

    config_file = _default_config_dir() / "config.toml"
    console.print(str(config_file))


# ── models ───────────────────────────────────────────────────────────────────


@models_app.command("list")
def models_list() -> None:
    """List available and downloaded Whisper models."""
    from mediascribe.cli.output import list_whisper_models

    list_whisper_models()


@models_app.command("download")
def models_download(
    model_name: Annotated[str, typer.Argument(help="Model to download (e.g., large-v3, medium, small, base, tiny)")] = "large-v3",
) -> None:
    """Download a Whisper model to the local cache."""
    from mediascribe.cli.output import download_whisper_model

    download_whisper_model(model_name)


@models_app.command("path")
def models_path() -> None:
    """Print the model cache directory."""
    from mediascribe.utils.paths import xdg_cache_dir

    console.print(str(xdg_cache_dir() / "models"))


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    try:
        from mediascribe.tui.app import MediascribeApp
        app_instance = MediascribeApp()
        app_instance.run()
    except ImportError:
        console.print("[red]Error:[/red] TUI dependencies not installed.")
        console.print("Install with: [bold]pip install mediascribe\\[tui][/bold]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
