# mediascribe — Project Tracker

> Living document for implementation tracking and session handoff.
> Update after every work session.

---

## Current Status

**Phase:** 1 — Core Library + CLI (MVP)
**Last Session:** 2026-02-14
**Last Agent/Session Notes:** Initial architecture, spec docs, project scaffold created. Existing Yokai Watch pipeline serves as proven reference implementation for transcription, translation, timing, and validation logic.

---

## Session Log

### Session 1 — 2026-02-14
**Focus:** Architecture & planning
**Completed:**
- Built and iterated on Yokai Watch subtitle pipeline (proof of concept)
  - Chunked transcription with loop/hallucination detection
  - Word-level timestamps for accurate subtitle timing
  - Batched GPT-4.1 translation with context overlap + review pass
  - Subtitle timing post-processing (duration cap, gap enforcement)
  - Idempotent pipeline with skip-if-exists
  - API transcription mode as alternative to local
- Created SPEC.md with full feature specification
- Created PROJECT.md (this file)
- Created project scaffold (pyproject.toml, module structure)

**Key Decisions:**
- Python + Textual for TUI (native ML ecosystem)
- Typer for CLI mode
- Pydantic Settings for config
- Step-based pipeline with event system
- Profile-based presets for different use cases

**Open Questions:**
- [ ] Final package name (mediascribe? scribeflow? subforge?)
- [ ] PyPI name availability check
- [ ] Diarization model choice (pyannote vs whisperx)
- [ ] Whether to support real-time/streaming transcription

---

## Phase 1 — Core Library + CLI (MVP)

### 1.1 Project Foundation
- [x] Spec document (SPEC.md)
- [x] Project tracker (PROJECT.md)
- [x] pyproject.toml with dependencies
- [x] Module directory structure
- [ ] .gitignore
- [ ] Basic test structure
- [ ] CI config (GitHub Actions)
- [ ] Dev environment setup docs

### 1.2 Core Abstractions
- [ ] `core/config.py` — Pydantic settings with .env + XDG support
- [ ] `core/job.py` — Job model (file + config + state + results)
- [ ] `core/pipeline.py` — Pipeline orchestrator (step sequencing, events)
- [ ] `core/events.py` — Event system (progress, error, completion)
- [ ] `core/hardware.py` — CPU/RAM/GPU detection

### 1.3 Pipeline Steps (extract from reference pipeline)
- [ ] `steps/base.py` — Abstract step interface
- [ ] `steps/detect.py` — File type + language detection via ffprobe
- [ ] `steps/normalize.py` — Audio extraction + normalization
- [ ] `steps/transcribe.py` — Local (chunked + validated) + API modes
- [ ] `steps/timing.py` — Word-timestamp timing + duration cap + gaps
- [ ] `steps/translate.py` — Batched OpenAI translation
- [ ] `steps/review.py` — Second-pass AI quality check

### 1.4 Format Handlers
- [ ] `formats/srt.py` — SRT read/write
- [ ] `formats/vtt.py` — WebVTT output
- [ ] `formats/transcript.py` — Plain text transcript

### 1.5 Model Management
- [ ] `models/whisper_local.py` — faster-whisper loading/caching
- [ ] `models/whisper_api.py` — OpenAI Whisper API client
- [ ] `models/openai_client.py` — OpenAI chat API wrapper
- [ ] `models/prompts.py` — Prompt template system

### 1.6 Utilities
- [ ] `utils/ffmpeg.py` — FFmpeg/ffprobe wrapper functions
- [ ] `utils/paths.py` — XDG dirs, temp file management
- [ ] `utils/logging.py` — Structured logging setup

### 1.7 CLI Interface
- [ ] `cli/app.py` — Typer app shell
- [ ] `cli/commands/transcribe.py` — `mediascribe transcribe <file>`
- [ ] `cli/commands/translate.py` — `mediascribe translate <srt>`
- [ ] `cli/commands/config.py` — `mediascribe config set/get/list`
- [ ] `cli/commands/batch.py` — `mediascribe batch <folder>`
- [ ] Rich-based progress output

---

## Phase 2 — TUI + Profiles

### 2.1 TUI Application
- [ ] `tui/app.py` — Textual app shell with screen navigation
- [ ] `tui/screens/welcome.py` — Welcome + dependency check
- [ ] `tui/screens/setup.py` — API key onboarding
- [ ] `tui/screens/picker.py` — File/folder picker
- [ ] `tui/screens/profile.py` — Profile selection + config
- [ ] `tui/screens/pipeline.py` — Live execution progress
- [ ] `tui/screens/results.py` — Output review

### 2.2 Profile System
- [ ] Profile TOML schema
- [ ] Built-in profiles: anime_subtitles, podcast, meeting, lecture
- [ ] Custom profile creation
- [ ] Profile-to-pipeline config mapping

### 2.3 Smart Features
- [ ] Custom prompt builder (user intent → system prompt)
- [ ] Hardware detection + concurrency recommendation
- [ ] Processing time estimation
- [ ] Large batch warnings

---

## Phase 3 — Advanced Features

- [ ] Speaker diarization (pyannote.audio integration)
- [ ] Analyze step (summarize, topics, action items)
- [ ] Markdown transcript format with speaker labels
- [ ] JSON export format
- [ ] Model download/cache management CLI
- [ ] Checkpoint-based resume on interrupt
- [ ] Plugin system for custom steps

---

## Phase 4 — Distribution

- [ ] PyPI publishing
- [ ] Homebrew tap
- [ ] Docker image
- [ ] User documentation
- [ ] GitHub Actions CI/CD

---

## Technical Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-14 | Python over Go/Rust for core | Native ML ecosystem (faster-whisper, pyannote), same language as pipeline |
| 2026-02-14 | Textual for TUI | Modern, beautiful, pure Python, has file picker widgets |
| 2026-02-14 | Typer for CLI | FastAPI-style, Rich integration, works alongside TUI |
| 2026-02-14 | Pydantic Settings for config | Type-safe, .env support, validation, serialization |
| 2026-02-14 | Step-based pipeline | Each step is independent, testable, skippable, composable |
| 2026-02-14 | Event-driven progress | Decouples pipeline from UI — same events drive CLI, TUI, or API |
| 2026-02-14 | Chunked transcription (3-min) | Eliminates hallucination, enables per-chunk validation + retry |
| 2026-02-14 | Word timestamps default on | Accurate subtitle timing, no more wall-to-wall subtitles |
| 2026-02-14 | gpt-4.1 for translation | Better nuance/wordplay vs mini, cost is negligible for text |

---

## Reference Implementation

The Yokai Watch pipeline (`../pipeline.py`) serves as the proven reference for:
- **Chunked transcription** with loop detection and retry
- **Word-timestamp timing** with duration cap and gap enforcement
- **Batched translation** with context overlap
- **Two-pass review** for quality
- **Idempotent execution** with skip-if-exists

All of this logic will be extracted into the modular step system.

---

## Handoff Notes

When picking up this project in a new session:

1. Read this PROJECT.md for current status
2. Read SPEC.md for architecture and feature details
3. Check the current phase and find the next unchecked task
4. Reference `../pipeline.py` for proven implementation patterns
5. Run tests before and after changes: `hatch run test`
6. Update this file after completing work
