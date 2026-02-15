"""Typer CLI application — the non-TUI entry point.

Usage:
    mediascribe transcribe video.mp4 --lang ja --translate en
    mediascribe batch ./videos/ --profile anime --translate en
    mediascribe config set openai_api_key sk-...
    mediascribe tui  # Launch the full TUI
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from mediascribe import __version__

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


@app.command()
def transcribe(
    file: Annotated[Path, typer.Argument(help="Input audio or video file")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Source language (auto-detect if omitted)")] = "",
    translate: Annotated[str, typer.Option("--translate", "-t", help="Target language for translation")] = "",
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile: general, anime, podcast, meeting")] = "general",
    model: Annotated[str, typer.Option("--model", "-m", help="Transcription model")] = "large-v3",
    mode: Annotated[str, typer.Option("--mode", help="Transcription mode: local, api, auto")] = "auto",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("./output"),
    custom: Annotated[str, typer.Option("--custom", help="Custom instructions for translation")] = "",
) -> None:
    """Transcribe (and optionally translate) a single file."""
    # TODO: Wire up to pipeline
    console.print(f"[bold]Transcribing:[/bold] {file}")
    console.print(f"  Profile: {profile} | Model: {model} | Mode: {mode}")
    if lang:
        console.print(f"  Source language: {lang}")
    if translate:
        console.print(f"  Translating to: {translate}")
    console.print("[yellow]Pipeline execution not yet implemented — scaffold only.[/yellow]")


@app.command()
def batch(
    folder: Annotated[Path, typer.Argument(help="Folder of input files")],
    profile: Annotated[str, typer.Option("--profile", "-p")] = "general",
    translate: Annotated[str, typer.Option("--translate", "-t")] = "",
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("./output"),
) -> None:
    """Process all media files in a folder."""
    console.print(f"[bold]Batch processing:[/bold] {folder}")
    console.print("[yellow]Not yet implemented — scaffold only.[/yellow]")


@app.command()
def config() -> None:
    """View or edit configuration."""
    console.print("[yellow]Not yet implemented — scaffold only.[/yellow]")


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    console.print("[yellow]TUI not yet implemented — Phase 2.[/yellow]")


if __name__ == "__main__":
    app()
