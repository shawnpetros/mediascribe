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

### From Homebrew

```bash
brew tap shawnpetros/mediascribe
brew install mediascribe
```

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

### PyPI (automated)

Releases are published automatically via GitHub Actions when a version tag is pushed:

```bash
# 1. Update version in pyproject.toml and src/mediascribe/__init__.py
# 2. Commit and tag
git add -A && git commit -m "release: v0.2.0"
git tag v0.2.0
git push && git push --tags
```

The publish workflow will:
1. Run the full CI suite (tests, lint, typecheck)
2. Build sdist and wheel
3. Publish to PyPI via trusted publisher (OIDC)
4. Create a GitHub Release with generated notes

**Setup required:** Configure PyPI trusted publisher in your PyPI project settings to trust the `publish.yml` workflow from your GitHub repo.

### PyPI (manual)

```bash
make build-check     # build + validate
make publish-test    # upload to TestPyPI first
make publish         # upload to PyPI
```

### Homebrew

A formula template is included at `homebrew/mediascribe.rb`. To set up a tap:

1. Create a repo `github.com/shawnpetros/homebrew-mediascribe`
2. After publishing to PyPI, update the formula:
   ```bash
   ./scripts/update-homebrew-formula.sh 0.1.0
   ```
3. Copy `homebrew/mediascribe.rb` to `Formula/mediascribe.rb` in the tap repo
4. Users install via:
   ```bash
   brew tap shawnpetros/mediascribe
   brew install mediascribe
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
