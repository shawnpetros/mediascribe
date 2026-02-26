# Development Setup

This project targets Python 3.12+.

## Prerequisites

- Python 3.12
- `ffmpeg` and `ffprobe` on `PATH`

## Local setup

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run checks

```bash
ruff check .
pytest
```

## Optional extras

TUI dependencies:

```bash
pip install -e ".[tui]"
```

Diarization dependencies:

```bash
pip install -e ".[diarize]"
```

## Useful commands

```bash
mediascribe --help
mediascribe config list
mediascribe transcribe path/to/input.mp4 --translate en
mediascribe translate path/to/source.srt --to en
```
