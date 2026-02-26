# mediascribe — Developer Setup

> How to set up a development environment for contributing to mediascribe.

## Prerequisites

- **Python 3.12+**
- **ffmpeg** (for audio/video processing)
- **Git**

## Quick Start

```bash
# Clone the repo
git clone https://github.com/shawnpetros/mediascribe.git
cd mediascribe

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or:  .venv\Scripts\activate   # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v
```

## Dev Dependencies

The `[dev]` extra installs:

- **pytest** — test runner
- **pytest-asyncio** — async test support
- **ruff** — linting and formatting
- **mypy** — type checking

## Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run the test suite |
| `pytest -v` | Verbose test output |
| `ruff check src/ tests/` | Lint the codebase |
| `ruff format src/ tests/` | Format code |
| `mypy src/` | Type check |

## Project Structure

```
src/mediascribe/
├── core/       # Config, job, pipeline, events
├── steps/      # Pipeline steps (detect, transcribe, translate, etc.)
├── formats/    # SRT, VTT, transcript, JSON export
├── models/     # Whisper, OpenAI clients
├── cli/        # Typer CLI
├── tui/        # Textual TUI (Phase 2)
└── utils/      # ffmpeg, paths, logging
```

## Environment

For transcription/translation features, set:

- `OPENAI_API_KEY` — required for API transcription and translation
- `MEDIASCRIBE_*` — any config override (e.g. `MEDIASCRIBE_WHISPER_MODEL=base`)

Or use a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

## CI

GitHub Actions runs on push/PR to `main`:

- Install deps
- Run tests
- Lint (ruff)
- Type check (mypy)

See [.github/workflows/ci.yml](../.github/workflows/ci.yml).
