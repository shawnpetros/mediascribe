# mediascribe

TUI-first tool for transcribing, translating, and analyzing audio/video media.

Supports local transcription (faster-whisper), cloud transcription (OpenAI Whisper API), AI-powered translation with context-aware batching, speaker diarization, and content analysis.

## Installation

```bash
pip install mediascribe           # core CLI
pip install mediascribe[tui]      # with TUI interface
pip install mediascribe[diarize]  # with speaker diarization
pip install mediascribe[all]      # everything
```

## Quick Start

```bash
# Transcribe a video file
mediascribe transcribe video.mp4

# Transcribe and translate to English
mediascribe transcribe video.mp4 --lang ja --translate en

# Use the anime profile for better subtitle translation
mediascribe transcribe anime.mkv --lang ja --translate en --profile anime

# Translate an existing SRT file
mediascribe translate subs.srt --target en --profile podcast

# Process all media files in a folder
mediascribe batch ./videos/ --translate en

# Launch the interactive TUI
mediascribe tui
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `mediascribe transcribe <file>` | Transcribe (and optionally translate) a media file |
| `mediascribe translate <srt>` | Translate an existing SRT file |
| `mediascribe batch <folder>` | Process all media files in a folder |
| `mediascribe config show` | Display current configuration |
| `mediascribe config set <key> <value>` | Set a configuration value |
| `mediascribe config get <key>` | Get a configuration value |
| `mediascribe config list` | List all available settings |
| `mediascribe models list` | List available Whisper models |
| `mediascribe models download <name>` | Download a Whisper model |
| `mediascribe tui` | Launch the interactive TUI |

## Configuration

Configuration follows a hierarchy (highest priority wins):

1. CLI flags
2. Environment variables (`MEDIASCRIBE_*`)
3. `.env` file in working directory
4. User config (`~/.config/mediascribe/config.toml`)
5. Built-in defaults

```bash
# Set your OpenAI API key
mediascribe config set openai_api_key sk-...

# Or use environment variables
export MEDIASCRIBE_OPENAI_API_KEY=sk-...

# View all settings
mediascribe config show
```

## Profiles

Built-in translation profiles optimize prompts for different content:

| Profile | Use Case |
|---------|----------|
| `general` | General-purpose subtitle translation (default) |
| `anime` | Anime/animation with character awareness |
| `podcast` | Podcast/interview with speaker personality |
| `meeting` | Business meetings with action item awareness |

```bash
mediascribe transcribe video.mp4 --translate en --profile anime
```

## Output Formats

Configure `output_formats` to auto-generate multiple formats:

```bash
mediascribe config set output_formats '["srt", "vtt", "txt", "md", "json"]'
```

| Format | Extension | Description |
|--------|-----------|-------------|
| SRT | `.srt` | SubRip subtitles (default) |
| VTT | `.vtt` | WebVTT subtitles |
| TXT | `.txt` | Plain text transcript |
| MD | `.md` | Markdown with speakers and structure |
| JSON | `.json` | Structured data export |

## Pipeline Architecture

```
Input File → Detect → Normalize → Transcribe → [Diarize] → Timing →
[Translate] → [Review] → [Analyze] → Export (SRT/VTT/TXT/MD/JSON)
```

Each step is independent, testable, and skippable (idempotent). The pipeline emits events for progress tracking, which drives both CLI and TUI output.

## Development

```bash
pip install -e ".[dev]"
pytest                    # run tests (230 tests)
ruff check src/ tests/    # lint
ruff format src/ tests/   # format
```

See [docs/SPEC.md](docs/SPEC.md) for full specification and [docs/PROJECT.md](docs/PROJECT.md) for implementation status.

## License

MIT
