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
from typing import Annotated, Optional

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
        )

    console.print(f"\n[bold green]All {len(files)} files processed.[/bold green]")


# ── config ───────────────────────────────────────────────────────────────────


@app.command()
def config() -> None:
    """View or edit configuration."""
    console.print("[yellow]Config management — coming in Phase 2.[/yellow]")
    console.print("For now, set OPENAI_API_KEY in your environment or .env file.")


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    try:
        from mediascribe.tui import run_tui
    except ImportError:
        console.print("[red]TUI dependencies not installed.[/red]")
        console.print("Install with: pip install mediascribe[tui]")
        raise typer.Exit(1)

    run_tui()


if __name__ == "__main__":
    app()
