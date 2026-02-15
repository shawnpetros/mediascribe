# mediascribe — Specification

> A TUI-first tool for transcribing, translating, and analyzing audio/video media.

## 1. Product Overview

**mediascribe** is an installable CLI/TUI tool that takes audio or video files and produces transcriptions, translations, subtitles, and AI-powered analysis. It supports local (faster-whisper) and cloud (OpenAI) transcription, speaker diarization, multi-language translation, and customizable post-processing.

### Target Users
- Content creators subtitling foreign-language video
- Podcast producers needing transcripts with speaker labels
- Researchers analyzing interview/meeting recordings
- Anyone who needs accurate, configurable media-to-text

### Install & Run
```bash
pipx install mediascribe    # primary distribution
brew install mediascribe     # via homebrew tap
mediascribe                  # launch TUI
mediascribe transcribe ./my-video.mp4  # direct CLI
```

---

## 2. Use Cases

### UC-1: Video Subtitling (e.g., anime, YouTube, lectures)
**Input:** 1+ video files (mp4, mkv, webm, avi)
**Flow:** normalize → extract audio → transcribe → [translate] → [review] → output SRT/VTT
**Output:** Subtitle files synced to video timing
**Key features:** Word-level timestamps, timing optimization, kid-friendly/context-aware translation

### UC-2: Audio Transcription (e.g., podcasts, interviews)
**Input:** 1+ audio files (mp3, wav, m4a, flac)
**Flow:** normalize → transcribe → [diarize] → [translate] → [analyze] → output
**Output:** Transcript with optional speaker labels, timestamps
**Key features:** Speaker diarization, paragraph segmentation, summary generation

### UC-3: Meeting/Recording Analysis
**Input:** Audio/video recording
**Flow:** transcribe → diarize → analyze → output
**Output:** Transcript + AI-generated summary, action items, key topics
**Key features:** Speaker attribution, topic extraction, action item detection

### UC-4: Batch Processing
**Input:** Folder of 100+ files
**Flow:** detect hardware → estimate time → warn user → process with managed concurrency
**Output:** One output per input, organized in output directory
**Key features:** Hardware-aware concurrency, progress dashboard, resume on interrupt

---

## 3. Architecture

### 3.1 Layer Diagram
```
┌─────────────────────────────────────────────┐
│              UI Layer (TUI / CLI)            │
│  Textual App  │  Typer CLI  │  Python API   │
├─────────────────────────────────────────────┤
│            Pipeline Orchestrator             │
│  Job queue → Step execution → Event stream  │
├─────────────────────────────────────────────┤
│              Pipeline Steps                  │
│ detect │ normalize │ transcribe │ translate  │
│ diarize │ timing │ analyze │ export         │
├─────────────────────────────────────────────┤
│             Core Services                    │
│  Config │ Models │ Formats │ FFmpeg │ AI     │
└─────────────────────────────────────────────┘
```

### 3.2 Data Flow
```
Input File(s)
    │
    ▼
[Detect] → file type, duration, codec, language guess
    │
    ▼
[Normalize] → standardized audio (16kHz mono WAV)
    │
    ▼
[Transcribe] → raw segments [{start, end, text, confidence}]
    │         (local: overlap-chunked + validated + deduped | API: single-shot)
    │
    ├──▶ [Diarize] → speaker labels per segment (optional)
    │
    ▼
[Timing Fix] → cleaned segments with natural display timing
    │
    ▼
[Translate] → [{start, end, source_text, target_text}] (optional)
    │
    ▼
[Review] → quality-checked translation (optional, 2nd AI pass)
    │
    ▼
[Analyze] → summary, topics, action items (optional)
    │
    ▼
[Export] → SRT, VTT, TXT, JSON, Markdown
```

### 3.3 Module Structure
```
src/mediascribe/
├── __init__.py              # Package metadata, version
├── __main__.py              # `python -m mediascribe` entry point
│
├── core/                    # Core abstractions
│   ├── config.py            # Settings via pydantic-settings
│   ├── job.py               # Job model (file → pipeline → output)
│   ├── pipeline.py          # Pipeline orchestrator
│   ├── events.py            # Event system (progress, errors, completion)
│   └── hardware.py          # CPU/RAM/GPU detection, concurrency calc
│
├── steps/                   # Pipeline steps (each is independent)
│   ├── base.py              # Abstract step interface
│   ├── detect.py            # File type + language detection
│   ├── normalize.py         # Audio extraction + normalization
│   ├── transcribe.py        # Transcription (local + API modes)
│   ├── diarize.py           # Speaker diarization
│   ├── timing.py            # Subtitle timing optimization
│   ├── translate.py         # AI translation (batched, context-aware)
│   ├── review.py            # AI review pass
│   └── analyze.py           # Post-processing (summarize, extract)
│
├── formats/                 # Output format handlers
│   ├── srt.py               # SubRip subtitle format
│   ├── vtt.py               # WebVTT subtitle format
│   ├── transcript.py        # Plain text / Markdown transcript
│   └── json_export.py       # Structured JSON output
│
├── models/                  # AI model management
│   ├── whisper_local.py     # faster-whisper model loading/caching
│   ├── whisper_api.py       # OpenAI Whisper API client
│   ├── openai_client.py     # OpenAI chat/translation client
│   └── prompts.py           # Prompt templates + custom prompt builder
│
├── cli/                     # Command-line interface
│   ├── app.py               # Typer app with subcommands
│   ├── commands/
│   │   ├── transcribe.py    # `mediascribe transcribe`
│   │   ├── translate.py     # `mediascribe translate`
│   │   ├── analyze.py       # `mediascribe analyze`
│   │   ├── config.py        # `mediascribe config`
│   │   └── batch.py         # `mediascribe batch`
│   └── output.py            # Rich console output helpers
│
├── tui/                     # Textual TUI application
│   ├── app.py               # Main Textual app
│   ├── screens/
│   │   ├── welcome.py       # Welcome + onboarding check
│   │   ├── setup.py         # API key entry + validation
│   │   ├── picker.py        # File/folder picker
│   │   ├── profile.py       # Profile selection + config
│   │   ├── pipeline.py      # Pipeline execution + live progress
│   │   └── results.py       # Output review + export
│   └── widgets/
│       ├── file_browser.py  # File tree widget
│       ├── progress_bar.py  # Per-job progress
│       └── log_panel.py     # Live log output
│
└── utils/
    ├── ffmpeg.py             # FFmpeg/ffprobe wrapper
    ├── logging.py            # Structured logging setup
    └── paths.py              # XDG dirs, temp file management
```

---

## 4. Feature Set (Phased)

### Phase 1 — Core Library + CLI (MVP)

| Feature | Description |
|---------|-------------|
| **Project scaffold** | pyproject.toml, module structure, dev tooling |
| **Config system** | Pydantic settings, .env, XDG config dir (`~/.config/mediascribe/`) |
| **Detect step** | ffprobe-based file type, codec, duration, channel detection |
| **Normalize step** | Extract audio, convert to 16kHz mono WAV |
| **Transcribe step** | Local (faster-whisper, overlap-chunked + validated) and API (OpenAI) modes |
| **Timing step** | Word-timestamp-based timing + duration cap + gap enforcement |
| **Translate step** | Batched OpenAI translation with context overlap |
| **Review step** | Second-pass AI quality check |
| **SRT/VTT export** | Standard subtitle format output |
| **CLI interface** | `mediascribe transcribe <file>` with flags |
| **Progress reporting** | Rich-based console progress (per-chunk, per-step) |
| **Batch processing** | Process multiple files, skip completed |

### Phase 2 — TUI + Profiles

| Feature | Description |
|---------|-------------|
| **TUI shell** | Textual app with screen navigation |
| **Onboarding screen** | API key entry, validation, storage |
| **File picker screen** | Browse filesystem, select files/folders |
| **Profile system** | Presets: anime_subtitles, podcast, meeting, lecture, custom |
| **Config screen** | Visual pipeline configuration |
| **Progress screen** | Live per-file, per-step progress with ETA |
| **Results screen** | Preview output, approve, export |
| **Custom prompt builder** | User describes intent → AI generates translation prompt |
| **Hardware detection** | CPU/RAM/GPU detection, concurrency recommendation |
| **Concurrency warnings** | Estimate processing time, warn for large batches |

### Phase 3 — Advanced Features

| Feature | Description |
|---------|-------------|
| **Speaker diarization** | pyannote.audio integration, speaker-labeled output |
| **Analyze step** | AI summarization, topic extraction, action items |
| **Transcript format** | Markdown/text output with speaker labels, paragraphs |
| **JSON export** | Structured data export for downstream tools |
| **Language auto-detect** | Whisper-based source language detection |
| **Model management** | Download, cache, update Whisper models |
| **Resume/retry** | Interrupt-safe processing, checkpoint-based resume |
| **Plugin system** | Custom steps via entry points |

### Phase 4 — Distribution + Polish

| Feature | Description |
|---------|-------------|
| **pipx distribution** | PyPI publish, `pipx install mediascribe` |
| **Homebrew tap** | `brew install mediascribe` via custom tap |
| **Docker image** | For CI/server/headless use |
| **Documentation** | User guide, API docs, examples |
| **CI/CD** | GitHub Actions: test, lint, build, publish |

---

## 5. Technology Stack

### Runtime
- **Python 3.12+** — native ML ecosystem, async support
- **ffmpeg 6+** — external dependency (detected at startup)

### Core Dependencies
| Package | Purpose | Phase |
|---------|---------|-------|
| `faster-whisper` | Local Whisper transcription | 1 |
| `openai` | API transcription + translation | 1 |
| `pysrt` | SRT file handling | 1 |
| `pydantic-settings` | Type-safe configuration | 1 |
| `python-dotenv` | .env file loading | 1 |
| `typer` | CLI framework | 1 |
| `rich` | Console output, progress bars | 1 |
| `textual` | TUI framework | 2 |
| `textual-fspicker` | TUI file picker widget | 2 |
| `pyannote.audio` | Speaker diarization | 3 |
| `psutil` | Hardware detection | 2 |

### Dev Dependencies
| Package | Purpose |
|---------|---------|
| `pytest` | Testing |
| `ruff` | Linting + formatting |
| `mypy` | Type checking |
| `hatch` | Build system |

---

## 6. Configuration Design

### Config Hierarchy (highest priority wins)
1. CLI flags / TUI input
2. Environment variables (`MEDIASCRIBE_*`)
3. Project `.env` file (in working directory)
4. User config file (`~/.config/mediascribe/config.toml`)
5. Built-in defaults

### Config Schema (Pydantic)
```python
class MediascribeSettings(BaseSettings):
    # API Keys
    openai_api_key: SecretStr
    huggingface_token: SecretStr | None = None  # for diarization

    # Transcription
    transcription_mode: Literal["local", "api", "auto"] = "auto"
    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_compute: str = "int8"
    chunk_duration_sec: int = 180
    chunk_overlap_sec: int = 15

    # Translation
    translation_model: str = "gpt-4.1"
    translation_batch_size: int = 15
    enable_review_pass: bool = True

    # Processing
    max_concurrency: int = 1  # auto-detected if 0
    output_dir: Path = Path("./output")
    output_formats: list[str] = ["srt"]

    # Source
    source_language: str | None = None  # None = auto-detect
    target_language: str | None = None  # None = no translation
```

### Profile System
Profiles are named config presets stored in `~/.config/mediascribe/profiles/`:

```toml
# ~/.config/mediascribe/profiles/anime_subtitles.toml
[transcription]
mode = "local"
model = "large-v3"
chunk_duration = 180

[translation]
model = "gpt-4.1"
target_language = "en"
enable_review = true
custom_instructions = """
This is a children's anime. Keep translations kid-friendly.
Preserve character catchphrases and humor.
"""

[output]
formats = ["srt", "vtt"]
fix_timing = true
```

---

## 7. Pipeline Step Interface

Every step implements a standard interface for composability:

```python
class PipelineStep(ABC):
    """Base class for all pipeline steps."""

    name: str                    # e.g., "transcribe"
    description: str             # Human-readable description
    required: bool = True        # Can this step be skipped?

    @abstractmethod
    async def execute(self, job: Job, context: PipelineContext) -> StepResult:
        """Execute this step. Emits events via context."""
        ...

    @abstractmethod
    def can_skip(self, job: Job) -> bool:
        """Return True if output already exists (idempotency)."""
        ...

    def estimate_duration(self, job: Job) -> float | None:
        """Optional: estimate seconds this step will take."""
        return None
```

Each step:
- Receives a `Job` (input file + config + accumulated results)
- Emits progress events via `PipelineContext`
- Returns a `StepResult` with outputs + metadata
- Can be skipped if output exists (idempotent)
- Can estimate its duration for ETA display

---

## 8. TUI Screen Flow

```
[Welcome] → [Setup?] → [File Picker] → [Config] → [Run] → [Results]
    │            │
    │            └── Only shown if API keys not configured
    │
    └── Check for ffmpeg, show version info
```

### Welcome Screen
- App title + version
- Check ffmpeg installation
- Check if API keys are configured
- "Get Started" button → Setup or File Picker

### Setup Screen
- OpenAI API key input (with validation — makes a test call)
- HuggingFace token (optional, for diarization)
- Save to `~/.config/mediascribe/config.toml`

### File Picker Screen
- Directory tree browser (Textual DirectoryTree)
- File type filter (video, audio, all)
- Multi-select support
- Show file metadata (duration, codec, size)
- "Next" → Config

### Config Screen
- Profile dropdown (anime, podcast, meeting, custom)
- Source language (auto-detect or select)
- Target language (none = transcript only, or select)
- Transcription mode (accurate/balanced/fast)
- Custom instructions text area
- Output format checkboxes (SRT, VTT, TXT, JSON)
- Advanced: concurrency, chunk size, model selection
- Hardware info display + processing time estimate

### Run Screen
- Per-file progress bars
- Current step indicator
- Live log panel
- ETA display
- Cancel button (graceful interrupt)

### Results Screen
- File list with status (✓/✗)
- Preview pane for output files
- "Open in Finder" / "Copy path" buttons
- "Process more" → back to File Picker

---

## 9. Output Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| SubRip | `.srt` | Video subtitles (most compatible) |
| WebVTT | `.vtt` | Web video subtitles |
| Transcript | `.txt` | Plain text transcript |
| Markdown | `.md` | Speaker-labeled transcript with formatting |
| JSON | `.json` | Structured data for downstream processing |

### JSON Output Schema
```json
{
  "metadata": {
    "source_file": "episode.mp4",
    "duration_sec": 1128,
    "source_language": "ja",
    "target_language": "en",
    "model": "large-v3",
    "processed_at": "2026-02-14T12:00:00Z"
  },
  "segments": [
    {
      "index": 1,
      "start": 13.85,
      "end": 15.85,
      "source_text": "まさかことが",
      "target_text": "I never imagined this would happen.",
      "speaker": null,
      "confidence": 0.94
    }
  ],
  "analysis": {
    "summary": "...",
    "topics": ["..."],
    "action_items": ["..."]
  }
}
```

---

## 10. Key Design Decisions

### 10.1 Package Name: `mediascribe`
Both `mediascribe` and `scribeflow` are available on PyPI. `subforge` is taken.
We chose **mediascribe** — clear, descriptive ("media in, scribed text out"),
covers all use cases (subtitles, transcripts, meeting notes), and the import
name is clean (`import mediascribe`).

### 10.2 Diarization: pyannote.audio 3.x
We use **pyannote.audio** directly rather than WhisperX because:
- We already own the transcription pipeline (chunked faster-whisper with validation).
- WhisperX bundles its own transcription, which conflicts with our architecture.
- pyannote is the actual diarization engine either way (WhisperX uses it under the hood).
- Direct pyannote gives us full control and future-proofs for model swaps.
- Requires a HuggingFace token (gated model), configured via `huggingface_token`.

### 10.3 No Real-Time Streaming (v1)
Streaming transcription is **out of scope** for v1. Rationale:
- Fundamentally different architecture (VAD-gated ring buffers, partial results, event streams).
- Our batch pipeline (chunked + validated + deduped) produces significantly better results.
- Primary use cases are all file-based (anime, podcasts, meetings, lectures).
- Could be added as a separate `mediascribe live` command in a future phase.

### 10.4 Overlap-Based Chunking
When splitting audio for chunked transcription, chunks **overlap by 15 seconds**
(configurable via `chunk_overlap_sec`) so that sentences at boundaries are fully
captured in at least one chunk. Post-processing deduplication reconciles the
overlap zone using:
1. Exact text match + close timestamps → merge (extend end time)
2. Fuzzy text similarity + overlapping time → keep the longer (more complete) version
3. Exact match still on screen → skip duplicate

This eliminates mid-sentence cuts that caused dropped words or hallucinations
at chunk boundaries.

```
Without overlap (risky):
  Chunk 1: [0:00 ──────── 3:00]
  Chunk 2:                      [3:00 ──────── 6:00]
                            ↑ sentence split here

With overlap (safe, default):
  Chunk 1: [0:00 ──────── 3:00 ── 3:15]
  Chunk 2:                [2:45 ── 3:00 ──────── 6:00 ── 6:15]
                          ├── 30s overlap zone ──┤
```

---

## 11. 12-Factor Compliance

| Factor | Implementation |
|--------|----------------|
| 1. Codebase | Single git repo |
| 2. Dependencies | pyproject.toml with hatch, locked via pip-compile |
| 3. Config | .env files + XDG config dir + env vars |
| 4. Backing services | OpenAI API, HuggingFace as attached resources |
| 5. Build/release/run | hatch build → PyPI publish → pipx install |
| 6. Processes | Stateless, one process per file |
| 7. Port binding | N/A (CLI tool) |
| 8. Concurrency | Configurable worker pool, hardware-aware |
| 9. Disposability | SIGINT handler, checkpoint-based resume |
| 10. Dev/prod parity | Same pipeline code everywhere |
| 11. Logs | Structured logging to stdout, Rich formatting |
| 12. Admin | `mediascribe config`, `mediascribe cache clear` |
