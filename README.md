# mediascribe

TUI-first tool for transcribing, translating, and analyzing audio/video media.

[![PyPI version](https://img.shields.io/pypi/v/mediascribe)](https://pypi.org/project/mediascribe/)
[![Python versions](https://img.shields.io/pypi/pyversions/mediascribe)](https://pypi.org/project/mediascribe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## What It Does

**mediascribe** takes audio or video files and produces transcriptions, translations, subtitles, and AI-powered analysis. It supports local transcription via faster-whisper, cloud transcription via the OpenAI API, speaker diarization, multi-language translation, and customizable prompt profiles.

```
Input File(s)
    |
    v
[Detect] --> file type, duration, codec
    |
    v
[Normalize] --> 16kHz mono WAV
    |
    v
[Transcribe] --> segments (overlap-chunked + validated + deduped)
    |
    |---> [Diarize] --> speaker labels (optional)
    |
    v
[Timing] --> subtitle timing optimization
    |
    v
[Translate] --> target language (optional, batched + context overlap)
    |
    v
[Review] --> AI quality check (optional)
    |
    v
[Analyze] --> summary, topics, action items (optional)
    |
    v
[Export] --> SRT, VTT, TXT, JSON
```

## Install

### Prerequisites

- **Python 3.12+**
- **FFmpeg 6+** -- install via `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Debian/Ubuntu)

### From PyPI (recommended)

```bash
pipx install mediascribe          # isolated install (recommended)
pip install mediascribe            # or into current environment
```

### With optional extras

| Extra | What it adds | Install command |
|-------|-------------|-----------------|
| `tui` | Interactive Textual TUI | `pip install mediascribe[tui]` |
| `diarize` | Speaker diarization (pyannote.audio) | `pip install mediascribe[diarize]` |
| `mcp` | MCP server for LLM agent integration | `pip install mediascribe[mcp]` |
| `all` | Everything above | `pip install mediascribe[all]` |

### From Homebrew

```bash
brew tap shawnpetros/mediascribe
brew install mediascribe
```

### From source

```bash
git clone https://github.com/shawnpetros/mediascribe.git
cd mediascribe
make install          # editable install with dev deps
```

## Setup

### Getting an OpenAI API Key

An OpenAI API key is required for translation, API-mode transcription, and AI analysis.

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign in (or create an account)
3. Navigate to **API keys** in the left sidebar
4. Click **Create new secret key**, copy it

Configure the key using any of these methods (highest priority first):

```bash
# Option 1: Set via CLI (saved to ~/.config/mediascribe/config.toml)
mediascribe config set openai_api_key sk-...

# Option 2: Environment variable
export MEDIASCRIBE_OPENAI_API_KEY=sk-...

# Option 3: .env file in your working directory
echo 'MEDIASCRIBE_OPENAI_API_KEY=sk-...' >> .env
```

### HuggingFace Token (optional)

Required only for speaker diarization. The pyannote.audio models are gated and need a HuggingFace access token.

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a token with **read** access
3. Accept the model agreements for [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

```bash
mediascribe config set huggingface_token hf_...
# or
export MEDIASCRIBE_HUGGINGFACE_TOKEN=hf_...
```

## Usage

### Transcribe a single file

```bash
# Auto-detect language, output SRT
mediascribe transcribe video.mp4

# Specify source language
mediascribe transcribe podcast.mp3 --lang ja
```

### Transcribe and translate

```bash
# Japanese audio --> English subtitles
mediascribe transcribe podcast.mp3 --lang ja --translate en

# With the anime profile and multiple output formats
mediascribe transcribe anime.mkv --translate en --profile anime --formats srt,vtt
```

### Batch process a directory

```bash
mediascribe batch ./recordings/ --translate en --formats srt,txt,json
```

Processes all media files in the folder (mp4, mkv, webm, avi, mov, mp3, wav, m4a, flac, ogg, aac).

### Translate existing subtitles

```bash
# Translate an SRT file without re-transcribing
mediascribe translate subtitles.srt --target en

# With a specific profile and custom instructions
mediascribe translate subtitles.srt --target es --profile anime --custom "Preserve honorifics"
```

### Speaker diarization

Requires the `diarize` extra and a HuggingFace token (see [Setup](#huggingface-token-optional)).

```bash
mediascribe transcribe meeting.mp4 --diarize --formats srt,txt
```

### AI analysis

Generates a summary, topic list, and action items alongside the transcription.

```bash
mediascribe transcribe meeting.mp4 --analyze --formats srt,txt,json
```

Combine with diarization for full meeting notes:

```bash
mediascribe transcribe meeting.mp4 --diarize --analyze --formats srt,txt,json
```

### Output formats

| Format | Description |
|--------|-------------|
| `srt` | SubRip subtitles -- widely supported by media players |
| `vtt` | WebVTT subtitles -- for web/HTML5 video |
| `txt` | Plain text transcript |
| `json` | Structured JSON with segments, timing, speakers, and analysis |

Specify multiple formats with `--formats srt,vtt,txt,json`. Default: `srt`.

### Whisper model selection

Use `--whisper-model` to choose accuracy vs. speed. Local transcription only (`--mode local` or `--mode auto` when no API key is set).

| Model | Parameters | Relative Speed | Best For |
|-------|-----------|----------------|----------|
| `tiny` | 39M | Fastest | Quick drafts, testing |
| `base` | 74M | Fast | Simple audio, clear speech |
| `small` | 244M | Moderate | Good balance for most use cases |
| `medium` | 769M | Slow | Higher accuracy, multilingual |
| `large-v3` | 1.5B | Slowest | Best accuracy (default) |

### Transcription modes

| Mode | Description |
|------|-------------|
| `auto` | Uses OpenAI API if key is set, otherwise falls back to local (default) |
| `local` | Always use faster-whisper locally |
| `api` | Always use the OpenAI Whisper API |

### Interactive TUI

```bash
mediascribe tui
```

Requires the `tui` extra: `pip install mediascribe[tui]`.

## Profiles

Profiles are named configuration presets that bundle transcription, translation, and output settings.

### Built-in profiles

| Profile | Description | Key Settings |
|---------|-------------|-------------|
| `general` | General-purpose subtitle translation | Defaults |
| `anime` | Anime/animation subtitling with character-aware translation | Local mode, large-v3, review pass, SRT + VTT |
| `podcast` | Podcast/interview transcription with speaker awareness | Review pass, SRT + TXT |
| `meeting` | Meeting/recording transcription with action item awareness | Review pass, SRT + TXT + JSON |

Use a profile with `--profile`:

```bash
mediascribe transcribe anime.mkv --translate en --profile anime
```

### Creating custom profiles

Add TOML files to `~/.config/mediascribe/profiles/`:

```toml
# ~/.config/mediascribe/profiles/lectures.toml
description = "University lecture transcription"

[transcription]
mode = "local"
model = "large-v3"

[translation]
target_language = "en"
enable_review = true
custom_instructions = """
Preserve technical terminology accurately.
Format mathematical expressions clearly.
"""

[output]
formats = ["srt", "txt", "json"]
```

Run `mediascribe config init` to create the profiles directory and populate it with built-in profile templates you can customize.

## Configuration

### Config commands

```bash
mediascribe config show       # Show current settings
mediascribe config set KEY VALUE  # Set a value in config.toml
mediascribe config init       # Create config dir + profile templates
mediascribe config path       # Show config directory location
mediascribe config profiles   # List available profiles
```

### Priority order

Configuration is loaded from (highest priority first):

1. CLI flags
2. Environment variables (`MEDIASCRIBE_*`)
3. `.env` file in working directory
4. `~/.config/mediascribe/config.toml`
5. Built-in defaults

### Environment variables

All settings can be set via environment variables with the `MEDIASCRIBE_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIASCRIBE_OPENAI_API_KEY` | | OpenAI API key |
| `MEDIASCRIBE_HUGGINGFACE_TOKEN` | | HuggingFace token (for diarization) |
| `MEDIASCRIBE_TRANSCRIPTION_MODE` | `auto` | `local`, `api`, or `auto` |
| `MEDIASCRIBE_WHISPER_MODEL` | `large-v3` | Whisper model size |
| `MEDIASCRIBE_WHISPER_DEVICE` | `auto` | Compute device (`auto`, `cpu`, `cuda`) |
| `MEDIASCRIBE_WHISPER_COMPUTE` | `int8` | Compute type for faster-whisper |
| `MEDIASCRIBE_CHUNK_DURATION_SEC` | `180` | Audio chunk length in seconds |
| `MEDIASCRIBE_CHUNK_OVERLAP_SEC` | `15` | Overlap between chunks in seconds |
| `MEDIASCRIBE_WORD_TIMESTAMPS` | `true` | Enable word-level timestamps |
| `MEDIASCRIBE_TRANSLATION_MODEL` | `gpt-4.1` | OpenAI model for translation |
| `MEDIASCRIBE_TRANSLATION_BATCH_SIZE` | `15` | Segments per translation batch |
| `MEDIASCRIBE_ENABLE_REVIEW_PASS` | `true` | Run a second review pass on translations |
| `MEDIASCRIBE_CUSTOM_INSTRUCTIONS` | | Custom instructions for translation |
| `MEDIASCRIBE_PROFILE` | `general` | Default profile name |
| `MEDIASCRIBE_SOURCE_LANGUAGE` | | Source language code (auto-detect if unset) |
| `MEDIASCRIBE_TARGET_LANGUAGE` | | Target language code (skip translation if unset) |
| `MEDIASCRIBE_MAX_CONCURRENCY` | `1` | Max parallel processing tasks |
| `MEDIASCRIBE_OUTPUT_DIR` | `./output` | Default output directory |
| `MEDIASCRIBE_OUTPUT_FORMATS` | `["srt"]` | Default output formats |
| `MEDIASCRIBE_MAX_SUBTITLE_DURATION_SEC` | `7.0` | Max subtitle display duration |
| `MEDIASCRIBE_MIN_GAP_SEC` | `0.15` | Minimum gap between subtitles |
| `MEDIASCRIBE_CHARS_PER_SECOND` | `5.0` | Reading speed for duration heuristic |
| `MEDIASCRIBE_CONFIG_DIR` | `~/.config/mediascribe` | Config directory path |

## MCP Server

mediascribe includes an [MCP](https://modelcontextprotocol.io/) server that lets LLM agents (like Claude) transcribe, translate, and query configuration programmatically.

### Starting the server

```bash
mediascribe mcp
```

Or directly via the entry point:

```bash
mediascribe-mcp
```

Requires the `mcp` extra: `pip install mediascribe[mcp]`.

### Available tools

| Tool | Description |
|------|-------------|
| `transcribe` | Transcribe an audio or video file (full pipeline: detect, normalize, transcribe, translate, analyze, export) |
| `translate` | Translate an existing SRT subtitle file without re-transcribing |
| `list_profiles` | List all available configuration profiles |
| `get_config` | Show the current configuration (secrets redacted) |

### Claude Desktop integration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mediascribe": {
      "command": "mediascribe-mcp"
    }
  }
}
```

If installed in a virtual environment, use the full path:

```json
{
  "mcpServers": {
    "mediascribe": {
      "command": "/path/to/venv/bin/mediascribe-mcp"
    }
  }
}
```

## Pipeline

Each step in the pipeline runs only when needed:

```
Input File(s)
    |
    v
[Detect]      file type, duration, codec
    |
    v
[Normalize]   convert to 16kHz mono WAV
    |
    v
[Transcribe]  overlap-chunked segments, validated and deduped
    |
    |---> [Diarize]    speaker labels (optional, --diarize)
    |
    v
[Timing]      subtitle timing optimization
    |
    v
[Translate]   target language (optional, --translate)
    |
    v
[Review]      AI quality check (optional, enabled by default)
    |
    v
[Analyze]     summary, topics, action items (optional, --analyze)
    |
    v
[Export]       SRT, VTT, TXT, JSON
```

See [docs/SPEC.md](docs/SPEC.md) for the full specification and [docs/PROJECT.md](docs/PROJECT.md) for implementation status.

<details>
<summary>Development</summary>

### Getting started

```bash
git clone https://github.com/shawnpetros/mediascribe.git
cd mediascribe
make install          # editable install with dev deps
make check            # run all checks (lint + format + types + tests)
```

### Make targets

| Target | Description |
|--------|-------------|
| `make install` | Install package in editable mode with dev extras |
| `make install-all` | Install with all optional extras (tui, diarize, mcp, dev) |
| `make test` | Run test suite |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Run ruff linter |
| `make format` | Auto-format code with ruff |
| `make typecheck` | Run mypy type checker |
| `make check` | Run all checks (lint + format + types + tests) |
| `make build` | Build sdist and wheel |
| `make build-check` | Build and validate distribution with twine |
| `make publish-test` | Publish to TestPyPI |
| `make publish` | Publish to PyPI |
| `make clean` | Remove all build/cache artifacts |
| `make version` | Show current package version |

### Publishing

The release pipeline is fully automated. To ship a new version:

1. Bump version in `pyproject.toml` and `src/mediascribe/__init__.py`
2. Commit and merge to main

On merge, CI will:
- Create a git tag
- Run full CI (tests, lint, typecheck)
- Build and smoke-test the wheel
- Publish to PyPI via trusted publisher (OIDC)
- Create a GitHub Release
- Update the Homebrew tap formula

For manual publishing:

```bash
make build-check     # build + validate
make publish-test    # upload to TestPyPI
make publish         # upload to PyPI
```

#### Homebrew tap setup

1. Create a repo named `shawnpetros/homebrew-mediascribe` with a `Formula/` directory
2. Add a repo secret `HOMEBREW_TAP_TOKEN` (personal access token with `repo` scope)
3. Optionally set `HOMEBREW_TAP_REPO` if the tap is at a different path

</details>

## License

MIT
