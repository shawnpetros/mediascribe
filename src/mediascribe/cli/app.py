"""Typer CLI application — the non-TUI entry point.

Usage:
    mediascribe transcribe video.mp4 --lang ja --translate en
    mediascribe transcribe podcast.mp3 --translate en --profile podcast
    mediascribe batch ./videos/ --profile anime --translate en
    mediascribe config set openai_api_key sk-...
    mediascribe tui  # Launch the full TUI (Phase 2)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from pydantic import SecretStr
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
config_app = typer.Typer(
    help="Persist and inspect mediascribe configuration values.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def _render_value(value: Any) -> str:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return "null"
    return str(value)


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
    lang: Annotated[str | None, typer.Option("--lang", "-l", help="Source language code (e.g., ja, en, es). Auto-detect if omitted")] = None,
    translate: Annotated[str | None, typer.Option("--translate", "-t", help="Target language for translation (e.g., en)")] = None,
    profile: Annotated[str | None, typer.Option("--profile", "-p", help="Prompt profile: general, anime, podcast, meeting")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Translation model")] = None,
    whisper_model: Annotated[str | None, typer.Option("--whisper-model", help="Whisper model size")] = None,
    mode: Annotated[str | None, typer.Option("--mode", help="Transcription mode: local, api, auto")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory")] = None,
    custom: Annotated[str | None, typer.Option("--custom", help="Custom instructions for translation")] = None,
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
        source_language=lang,
        target_language=translate,
        profile=profile,
        translation_model=model,
        whisper_model=whisper_model,
        transcription_mode=mode,
        custom_instructions=custom,
        enable_review=False if no_review else None,
    )


# ── batch ────────────────────────────────────────────────────────────────────


@app.command()
def batch(
    folder: Annotated[Path, typer.Argument(help="Folder of input files")],
    lang: Annotated[str | None, typer.Option("--lang", "-l")] = None,
    translate: Annotated[str | None, typer.Option("--translate", "-t")] = None,
    profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    whisper_model: Annotated[str | None, typer.Option("--whisper-model")] = None,
    mode: Annotated[str | None, typer.Option("--mode")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    custom: Annotated[str | None, typer.Option("--custom")] = None,
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
            source_language=lang,
            target_language=translate,
            profile=profile,
            translation_model=model,
            whisper_model=whisper_model,
            transcription_mode=mode,
            custom_instructions=custom,
            enable_review=False if no_review else None,
        )

    console.print(f"\n[bold green]All {len(files)} files processed.[/bold green]")


# ── translate ────────────────────────────────────────────────────────────────


@app.command()
def translate(
    srt: Annotated[Path, typer.Argument(help="Source .srt file to translate")],
    to: Annotated[str, typer.Option("--to", "-t", help="Target language code (e.g., en)")],
    profile: Annotated[str | None, typer.Option("--profile", "-p", help="Prompt profile")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Translation model")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output .srt path or output directory")] = None,
    custom: Annotated[str | None, typer.Option("--custom", help="Custom translation instructions")] = None,
    no_review: Annotated[bool, typer.Option("--no-review", help="Skip review pass")] = False,
) -> None:
    """Translate an existing subtitle file without re-transcribing media."""
    from mediascribe.cli.output import run_translate_for_srt

    if not srt.exists():
        console.print(f"[red]Error:[/red] SRT file not found: {srt}")
        raise typer.Exit(1)

    run_translate_for_srt(
        source_srt_path=srt,
        target_language=to,
        output_path=output,
        profile=profile,
        translation_model=model,
        custom_instructions=custom,
        enable_review=False if no_review else None,
    )


# ── config ───────────────────────────────────────────────────────────────────


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Setting key (e.g. whisper_model)")],
    value: Annotated[str, typer.Argument(help='Value (use "null" to unset)')],
) -> None:
    """Persist a config value to ~/.config/mediascribe/config.toml."""
    from mediascribe.core.config import (
        MediascribeSettings,
        is_secret_setting,
        is_valid_setting_key,
        load_user_config,
        parse_setting_value,
        save_user_config,
    )

    k = _normalize_key(key)
    if not is_valid_setting_key(k):
        console.print(f"[red]Error:[/red] Unknown key: {key}")
        raise typer.Exit(1)

    try:
        parsed = parse_setting_value(k, value)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Invalid value for {k}: {exc}")
        raise typer.Exit(1)

    user_cfg = load_user_config()
    if parsed is None:
        user_cfg.pop(k, None)
    else:
        user_cfg[k] = parsed

    try:
        MediascribeSettings(**user_cfg)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Config validation failed: {exc}")
        raise typer.Exit(1)

    path = save_user_config(user_cfg)
    if parsed is None:
        console.print(f"[green]Unset[/green] {k}")
    elif is_secret_setting(k):
        console.print(f"[green]Set[/green] {k} = [dim]<redacted>[/dim]")
    else:
        console.print(f"[green]Set[/green] {k} = {_render_value(parsed)}")
    console.print(f"[dim]Saved: {path}[/dim]")


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Setting key")],
    raw: Annotated[bool, typer.Option("--raw", help="Show raw secret values")] = False,
) -> None:
    """Read one effective config value (merged from env/.env/config/defaults)."""
    from mediascribe.core.config import (
        is_secret_setting,
        is_valid_setting_key,
        load_settings,
        load_user_config,
    )

    k = _normalize_key(key)
    if not is_valid_setting_key(k):
        console.print(f"[red]Error:[/red] Unknown key: {key}")
        raise typer.Exit(1)

    settings = load_settings()
    value = getattr(settings, k)

    if is_secret_setting(k) and not raw and value is not None:
        display = "<redacted>"
    else:
        display = _render_value(value)

    source = "config.toml" if k in load_user_config() else "env/.env/default"
    console.print(f"{k} = {display}")
    console.print(f"[dim]source: {source}[/dim]")


@config_app.command("list")
def config_list(
    all_values: Annotated[bool, typer.Option("--all", help="Show all effective settings")] = False,
    raw_secrets: Annotated[bool, typer.Option("--raw-secrets", help="Show secret values")] = False,
) -> None:
    """List persisted config keys, or all effective keys with --all."""
    from mediascribe.core.config import (
        is_secret_setting,
        list_setting_keys,
        load_settings,
        load_user_config,
    )

    user_cfg = load_user_config()
    settings = load_settings()

    if all_values:
        keys = list_setting_keys()
        if not keys:
            console.print("[yellow]No settings found.[/yellow]")
            return
        for key in keys:
            value = getattr(settings, key)
            if is_secret_setting(key) and not raw_secrets and value is not None:
                display = "<redacted>"
            else:
                display = _render_value(value)
            console.print(f"{key} = {display}")
        return

    if not user_cfg:
        console.print("[yellow]No persisted config values yet.[/yellow]")
        console.print("Use [bold]mediascribe config set <key> <value>[/bold] to store one.")
        return

    for key in sorted(user_cfg.keys()):
        value = user_cfg[key]
        if is_secret_setting(key) and not raw_secrets and value is not None:
            display = "<redacted>"
        else:
            display = _render_value(value)
        console.print(f"{key} = {display}")


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    console.print("[yellow]TUI — coming in Phase 2.[/yellow]")
    console.print("Use the CLI commands for now: mediascribe transcribe <file>")


if __name__ == "__main__":
    app()
