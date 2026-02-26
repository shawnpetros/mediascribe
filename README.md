# mediascribe

TUI-first tool for transcribing, translating, and analyzing audio/video media.

**mediascribe** takes audio or video files and produces transcriptions, translations, subtitles, and AI-powered analysis. It supports local (faster-whisper) and cloud (OpenAI) transcription, speaker diarization, multi-language translation, and customizable prompt profiles.

## Install

### From PyPI (recommended)

```bash
pipx install mediascribe          # isolated install
pip install mediascribe            # or into current environment
```

### With optional extras

```bash
pip install mediascribe[tui]       # Textual TUI interface
pip install mediascribe[diarize]   # speaker diarization (pyannote.audio)
pip install mediascribe[all]       # everything
```

### From Homebrew (after first PyPI release)

```bash
brew tap shawnpetros/mediascribe
brew install mediascribe
```

> **Note:** This requires the tap repo to exist — see [Publishing > Homebrew](#homebrew) for setup instructions.

### From source

```bash
git clone https://github.com/shawnpetros/mediascribe.git
cd mediascribe
make install                       # editable install with dev tools
```

### Requirements

- **Python 3.12+**
- **FFmpeg 6+** — install via `brew install ffmpeg` or `apt install ffmpeg`
- **OpenAI API key** — for translation and API transcription mode

## Quick Start

```bash
# Transcribe a video (auto-detects language)
mediascribe transcribe video.mp4

# Transcribe Japanese audio → English subtitles
mediascribe transcribe podcast.mp3 --lang ja --translate en

# Use the anime profile with multiple output formats
mediascribe transcribe anime.mkv --translate en --profile anime --formats srt,vtt

# Translate an existing SRT file
mediascribe translate subtitles.srt --target en --profile anime

# Batch process a folder
mediascribe batch ./recordings/ --translate en --formats srt,txt,json

# Enable speaker diarization and AI analysis
mediascribe transcribe meeting.mp4 --diarize --analyze --formats srt,txt,json

# Launch the interactive TUI
mediascribe tui
```

## Configuration

```bash
# Show current settings
mediascribe config show

# Set your API key
mediascribe config set openai_api_key sk-...

# Initialize config directory with profile templates
mediascribe config init

# List available profiles
mediascribe config profiles
```

Configuration is loaded from (highest priority first):
1. CLI flags
2. Environment variables (`MEDIASCRIBE_*`)
3. `.env` file in working directory
4. `~/.config/mediascribe/config.toml`
5. Built-in defaults

### Profiles

Profiles are named config presets. Built-in profiles: `general`, `anime`, `podcast`, `meeting`.

Create custom profiles as TOML files in `~/.config/mediascribe/profiles/`:

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

## Development

```bash
git clone https://github.com/shawnpetros/mediascribe.git
cd mediascribe
make install          # install editable + dev deps
make test             # run test suite (184 tests)
make lint             # run ruff linter
make format           # auto-format code
make typecheck        # run mypy
make check            # all of the above
make build            # build sdist + wheel
make help             # show all targets
```

### Make Targets

| Target | Description |
|--------|-------------|
| `make install` | Install package in editable mode with dev extras |
| `make install-all` | Install with all optional extras (tui, diarize, dev) |
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

## Publishing

### Fully automated (recommended)

The entire release pipeline is automated. To ship a new version:

```bash
# 1. Bump version in both files
#    - pyproject.toml:  version = "0.2.0"
#    - src/mediascribe/__init__.py:  __version__ = "0.2.0"
# 2. Commit and merge to main
git add -A && git commit -m "release: v0.2.0"
git push
```

What happens automatically on merge to main:
1. **release.yml** detects the version change in `pyproject.toml`, creates a `v0.2.0` tag
2. **publish.yml** triggers on the new tag:
   - Runs full CI (tests, lint, typecheck)
   - Builds sdist + wheel
   - Smoke tests the built wheel (CLI loads, commands respond)
   - Publishes to PyPI via trusted publisher (OIDC)
   - Creates a GitHub Release with auto-generated notes
   - Updates the Homebrew tap formula with the new version + SHA256

### One-time setup

**PyPI:** Configure trusted publisher in your [PyPI project settings](https://pypi.org/manage/project/mediascribe/settings/publishing/) to trust the `publish.yml` workflow from your GitHub repo.

**Homebrew tap:**

1. Create a GitHub repo named **`shawnpetros/homebrew-mediascribe`** with a `Formula/` directory
2. Add a repo secret `HOMEBREW_TAP_TOKEN` in the mediascribe repo — a [personal access token](https://github.com/settings/tokens) with `repo` scope on the tap repo
3. Optionally set a repo variable `HOMEBREW_TAP_REPO` if the tap is at a different path (defaults to `shawnpetros/homebrew-mediascribe`)

After setup, users install via:

```bash
brew tap shawnpetros/mediascribe
brew install mediascribe
```

### Manual publishing

```bash
make build-check     # build + validate
make publish-test    # upload to TestPyPI first
make publish         # upload to PyPI
```

## Architecture

```
Input File(s)
    │
    ▼
[Detect] → file type, duration, codec
    │
    ▼
[Normalize] → 16kHz mono WAV
    │
    ▼
[Transcribe] → segments (overlap-chunked + validated + deduped)
    │
    ├──▶ [Diarize] → speaker labels (optional)
    │
    ▼
[Timing] → subtitle timing optimization
    │
    ▼
[Translate] → target language (optional, batched + context overlap)
    │
    ▼
[Review] → AI quality check (optional)
    │
    ▼
[Analyze] → summary, topics, action items (optional)
    │
    ▼
[Export] → SRT, VTT, TXT, JSON
```

See [docs/SPEC.md](docs/SPEC.md) for the full specification and [docs/PROJECT.md](docs/PROJECT.md) for implementation status.

## License

MIT
