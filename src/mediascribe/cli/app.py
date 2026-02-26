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
    lang: Annotated[
        str,
        typer.Option(
            "--lang", "-l", help="Source language code (e.g., ja, en, es). Auto-detect if omitted"
        ),
    ] = "",
    translate: Annotated[
        str, typer.Option("--translate", "-t", help="Target language for translation (e.g., en)")
    ] = "",
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Prompt profile: general, anime, podcast, meeting"),
    ] = "general",
    model: Annotated[str, typer.Option("--model", "-m", help="Translation model")] = "gpt-4.1",
    whisper_model: Annotated[
        str, typer.Option("--whisper-model", help="Whisper model size")
    ] = "large-v3",
    mode: Annotated[
        str, typer.Option("--mode", help="Transcription mode: local, api, auto")
    ] = "auto",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path(
        "./output"
    ),
    custom: Annotated[
        str, typer.Option("--custom", help="Custom instructions for translation")
    ] = "",
    no_review: Annotated[
        bool, typer.Option("--no-review", help="Skip the review (second) pass")
    ] = False,
    formats: Annotated[
        str,
        typer.Option("--formats", "-f", help="Output formats (comma-separated): srt,vtt,txt,json"),
    ] = "srt",
    diarize: Annotated[
        bool, typer.Option("--diarize", help="Enable speaker diarization (requires pyannote.audio)")
    ] = False,
    analyze: Annotated[
        bool, typer.Option("--analyze", help="Enable AI analysis (summary, topics, action items)")
    ] = False,
) -> None:
    """Transcribe (and optionally translate) a single file."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    output_formats = [f.strip() for f in formats.split(",") if f.strip()]

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
        enable_diarize=diarize,
        enable_analyze=analyze,
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
    formats: Annotated[
        str, typer.Option("--formats", "-f", help="Output formats: srt,vtt,txt,json")
    ] = "srt",
    diarize: Annotated[bool, typer.Option("--diarize", help="Enable speaker diarization")] = False,
    analyze: Annotated[bool, typer.Option("--analyze", help="Enable AI analysis")] = False,
) -> None:
    """Process all media files in a folder."""
    from mediascribe.cli.output import run_pipeline_for_file

    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {folder}")
        raise typer.Exit(1)

    # Find all media files
    extensions = {
        ".mp4",
        ".mkv",
        ".webm",
        ".avi",
        ".mov",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
    }
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in extensions)

    if not files:
        console.print(f"[yellow]No media files found in {folder}[/yellow]")
        raise typer.Exit(0)

    output_formats = [f.strip() for f in formats.split(",") if f.strip()]

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
            enable_diarize=diarize,
            enable_analyze=analyze,
        )

    console.print(f"\n[bold green]All {len(files)} files processed.[/bold green]")


# ── translate ─────────────────────────────────────────────────────────────────


@app.command()
def translate(
    srt_file: Annotated[Path, typer.Argument(help="Input SRT file to translate")],
    target: Annotated[
        str, typer.Option("--target", "-t", help="Target language (e.g., en, es, fr)")
    ] = "en",
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Prompt profile: general, anime, podcast, meeting"),
    ] = "general",
    model: Annotated[str, typer.Option("--model", "-m", help="Translation model")] = "gpt-4.1",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path(
        "./output"
    ),
    custom: Annotated[
        str, typer.Option("--custom", help="Custom instructions for translation")
    ] = "",
    no_review: Annotated[
        bool, typer.Option("--no-review", help="Skip the review (second) pass")
    ] = False,
) -> None:
    """Translate an existing SRT file without re-transcribing."""
    from mediascribe.cli.output import run_translate_srt

    if not srt_file.exists():
        console.print(f"[red]Error:[/red] File not found: {srt_file}")
        raise typer.Exit(1)
    if srt_file.suffix.lower() != ".srt":
        console.print(f"[red]Error:[/red] Expected an SRT file, got: {srt_file.suffix}")
        raise typer.Exit(1)

    run_translate_srt(
        srt_path=srt_file,
        output_dir=output,
        target_language=target,
        profile=profile,
        translation_model=model,
        custom_instructions=custom,
        enable_review=not no_review,
    )


# ── config ───────────────────────────────────────────────────────────────────


config_app = typer.Typer(
    name="config",
    help="View and manage mediascribe configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration values."""
    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    console.print("\n[bold]Current Configuration[/bold]\n")

    fields = [
        ("Profile", settings.profile),
        ("Transcription mode", settings.transcription_mode),
        ("Whisper model", settings.whisper_model),
        ("Whisper device", settings.whisper_device),
        ("Whisper compute", settings.whisper_compute),
        ("Chunk duration (sec)", settings.chunk_duration_sec),
        ("Chunk overlap (sec)", settings.chunk_overlap_sec),
        ("Translation model", settings.translation_model),
        ("Translation batch size", settings.translation_batch_size),
        ("Review pass enabled", settings.enable_review_pass),
        ("Source language", settings.source_language or "auto-detect"),
        ("Target language", settings.target_language or "(none)"),
        ("Output formats", ", ".join(settings.output_formats)),
        ("Output directory", str(settings.output_dir)),
        ("Max concurrency", settings.max_concurrency),
        ("Config directory", str(settings.config_dir)),
        ("OpenAI API key", "***configured***" if settings.openai_api_key else "(not set)"),
        ("HuggingFace token", "***configured***" if settings.huggingface_token else "(not set)"),
    ]

    for label, value in fields:
        console.print(f"  {label + ':':<26s} {value}")
    console.print()


@config_app.command("path")
def config_path() -> None:
    """Show the configuration directory path."""
    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    config_dir = settings.config_dir
    config_file = config_dir / "config.toml"
    profiles_dir = config_dir / "profiles"

    console.print(f"\n  Config directory:  {config_dir}")
    console.print(f"  Config file:      {config_file}")
    console.print(f"  Profiles dir:     {profiles_dir}")
    console.print(f"  Config exists:    {'yes' if config_file.exists() else 'no'}")
    console.print()


@config_app.command("set")
def config_set(
    key: Annotated[
        str, typer.Argument(help="Config key (e.g., openai_api_key, profile, translation_model)")
    ],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a configuration value in config.toml."""
    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    config_dir = settings.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"

    existing: dict[str, str] = {}
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip().strip('"')

    existing[key] = value

    lines = []
    for k, v in sorted(existing.items()):
        if v.lower() in ("true", "false") or v.isdigit():
            lines.append(f"{k} = {v}")
        else:
            lines.append(f'{k} = "{v}"')

    config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"  [green]Set {key} = {value}[/green] in {config_file}")


@config_app.command("init")
def config_init() -> None:
    """Create default config file and directory structure."""
    from mediascribe.core.config import MediascribeSettings
    from mediascribe.core.profiles import save_builtin_profiles

    settings = MediascribeSettings()
    config_dir = settings.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "profiles").mkdir(exist_ok=True)

    config_file = config_dir / "config.toml"
    if config_file.exists():
        console.print(f"  [yellow]Config already exists:[/yellow] {config_file}")
    else:
        config_file.write_text(
            "# mediascribe configuration\n"
            "# See: mediascribe config show\n"
            "\n"
            '# openai_api_key = "sk-..."\n'
            '# profile = "general"\n'
            '# transcription_mode = "auto"\n'
            '# whisper_model = "large-v3"\n'
            '# translation_model = "gpt-4.1"\n'
            '# target_language = "en"\n'
            '# output_formats = ["srt"]\n',
            encoding="utf-8",
        )
        console.print(f"  [green]Created config:[/green] {config_file}")

    save_builtin_profiles(config_dir)
    console.print(f"  [green]Profiles dir:[/green]  {config_dir / 'profiles'}")


@config_app.command("profiles")
def config_profiles() -> None:
    """List available profiles."""
    from mediascribe.core.config import MediascribeSettings
    from mediascribe.core.profiles import list_profiles, load_profile

    settings = MediascribeSettings()
    profiles = list_profiles(settings.config_dir)

    console.print("\n[bold]Available Profiles[/bold]\n")
    for name in profiles:
        try:
            p = load_profile(name, settings.config_dir)
            desc = p.description or "(no description)"
            console.print(f"  [bold]{name:<16s}[/bold] {desc}")
        except FileNotFoundError:
            console.print(f"  [bold]{name:<16s}[/bold] (load error)")
    console.print()


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    try:
        from mediascribe.tui.app import run_tui

        run_tui()
    except ImportError:
        console.print("[red]TUI requires the 'tui' extra:[/red]")
        console.print("  pip install mediascribe[tui]")


if __name__ == "__main__":
    app()
