# mediascribe — Project Tracker

> Living document for implementation tracking and session handoff.
> Update after every work session.

---

## Current Status

**Phase:** 1 — Core Library + CLI (MVP) — **COMPLETE + AUDITED**
**Last Session:** 2026-02-26
**Last Agent/Session Notes:** Feature audit completed. Implemented standalone `translate` command, real `config set/get/list`, profile-aware translation/review prompts, fixed CLI entrypoint wiring, and added GitHub Actions CI workflow.

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

### Session 2 — 2026-02-15
**Focus:** Full extraction of pipeline.py into modular architecture
**Completed:**
- Refactored to sync-first pattern (Steps + Pipeline are synchronous)
- Extracted format handlers: SRT, VTT, transcript (plain text), JSON export
- Extracted AI model wrappers: OpenAI client, Whisper local + API
- Extracted all pipeline steps:
  - detect.py — ffprobe-based file type/codec/duration detection
  - normalize.py — audio extraction to 16kHz mono WAV
  - transcribe.py — chunked local + API with validation/retry/dedup
  - timing.py — subtitle display duration + gap optimization
  - translate.py — batched OpenAI translation with context overlap
  - review.py — AI second-pass quality check
- Wired CLI (transcribe, batch) to real pipeline execution
- Created cli/output.py with Rich event handler
- Smoke tested detect step against real media file
- All imports verified clean

**Commits:**
1. chore: initial project scaffold
2. refactor: sync-first pattern for steps and pipeline
3. feat: format handlers — SRT, VTT, transcript, JSON export
4. feat: AI model wrappers — OpenAI client, Whisper local + API
5. feat: normalize step — extract audio to 16kHz mono WAV
6. feat: timing step — subtitle display duration and gap optimization
7. feat: transcribe step — chunked local + API with validation
8. feat: translate step — batched AI translation with context overlap
9. feat: review step — AI second-pass quality check on translations
10. feat: wire CLI to real pipeline — end-to-end functional

**Resolved Questions:**
- [x] Package name -> **mediascribe** (available on PyPI; scribeflow also available; subforge taken)
- [x] Diarization -> **pyannote.audio 3.x** directly (we own transcription; WhisperX conflicts)
- [x] Streaming -> **No for v1** (different architecture, niche demand, quality tradeoff)
- [x] Chunk boundary accuracy -> **Overlap-based chunking** (15s overlap + fuzzy dedup)

### Session 3 — 2026-02-15 (continued)
**Focus:** Resolve open questions, overlap-chunking QoL, test suite
**Completed:**
- Resolved all open questions (package name, diarization, streaming, chunking)
- Implemented overlap-based chunking in split_audio (15s configurable overlap)
- Added fuzzy text similarity dedup for chunk boundary reconciliation
- Added chunk_overlap_sec config setting
- Updated SPEC.md with design decisions (section 10)
- Wrote comprehensive test suite for core logic

**Commits:**
11. feat: overlap-based chunking — eliminates mid-sentence cuts
12. test: comprehensive test suite for core logic modules
13. docs: resolve open questions, update SPEC.md + PROJECT.md

### Session 4 — 2026-02-26
**Focus:** Feature audit + close remaining Phase 1 CLI/Foundation gaps
**Completed:**
- Audited documented feature sets against implementation status
- Implemented persistent config management:
  - `mediascribe config set`
  - `mediascribe config get`
  - `mediascribe config list`
  - TOML-backed persisted config at XDG config path
- Implemented standalone subtitle translation command:
  - `mediascribe translate <srt> --to <lang>`
- Wired translation profile selection into translate/review steps
- Fixed CLI entrypoints (`python -m mediascribe` and console script)
- Added GitHub Actions CI workflow (`ruff` + `pytest`)
- Added development environment setup guide (`docs/DEVELOPMENT.md`)
- Added tests for config persistence and CLI config/translate command wiring

---

## Phase 1 — Core Library + CLI (MVP)

### 1.1 Project Foundation
- [x] Spec document (SPEC.md)
- [x] Project tracker (PROJECT.md)
- [x] pyproject.toml with dependencies
- [x] Module directory structure
- [x] .gitignore
- [x] Git repo initialized
- [x] Basic test structure
- [x] CI config (GitHub Actions)
- [x] Dev environment setup docs

### 1.2 Core Abstractions
- [x] core/config.py — Pydantic settings with .env + XDG support
- [x] core/job.py — Job model (file + config + state + results)
- [x] core/pipeline.py — Pipeline orchestrator (step sequencing, events)
- [x] core/events.py — Event system (progress, error, completion)
- [x] core/hardware.py — CPU/RAM/GPU detection

### 1.3 Pipeline Steps (extracted from reference pipeline)
- [x] steps/base.py — Abstract step interface (sync-first)
- [x] steps/detect.py — File type + language detection via ffprobe
- [x] steps/normalize.py — Audio extraction + normalization
- [x] steps/transcribe.py — Overlap-chunked local + API with validation/retry/dedup
- [x] steps/timing.py — Word-timestamp timing + duration cap + gaps
- [x] steps/translate.py — Batched OpenAI translation with context overlap
- [x] steps/review.py — Second-pass AI quality check

### 1.4 Format Handlers
- [x] formats/srt.py — SRT read/write + segment conversion
- [x] formats/vtt.py — WebVTT output
- [x] formats/transcript.py — Plain text transcript with timestamps/speakers
- [x] formats/json_export.py — Structured JSON export

### 1.5 Model Management
- [x] models/whisper_local.py — faster-whisper loading/caching
- [x] models/whisper_api.py — OpenAI Whisper API client
- [x] models/openai_client.py — OpenAI chat API wrapper (JSON parse)
- [x] models/prompts.py — Prompt template system (4 profiles)

### 1.6 Utilities
- [x] utils/ffmpeg.py — FFmpeg/ffprobe wrapper functions (with overlap chunking)
- [x] utils/paths.py — XDG dirs, temp file management
- [x] utils/logging.py — Structured logging setup (Rich)

### 1.7 CLI Interface
- [x] cli/app.py — Typer app with transcribe, batch, config, tui commands
- [x] cli/output.py — Rich event handler + pipeline runner
- [x] End-to-end pipeline wiring (detect -> normalize -> transcribe -> translate -> review)
- [x] mediascribe translate <srt> — standalone translate command
- [x] mediascribe config set/get/list — config management

---

## Phase 2 — TUI + Profiles

### 2.1 TUI Application
- [ ] tui/app.py — Textual app shell with screen navigation
- [ ] tui/screens/welcome.py — Welcome + dependency check
- [ ] tui/screens/setup.py — API key onboarding
- [ ] tui/screens/picker.py — File/folder picker
- [ ] tui/screens/profile.py — Profile selection + config
- [ ] tui/screens/pipeline.py — Live execution progress
- [ ] tui/screens/results.py — Output review

### 2.2 Profile System
- [ ] Profile TOML schema
- [ ] Built-in profiles: anime_subtitles, podcast, meeting, lecture
- [ ] Custom profile creation
- [ ] Profile-to-pipeline config mapping

### 2.3 Smart Features
- [ ] Custom prompt builder (user intent -> system prompt)
- [ ] Hardware detection + concurrency recommendation
- [ ] Processing time estimation
- [ ] Large batch warnings

---

## Phase 3 — Advanced Features

- [ ] Speaker diarization (pyannote.audio 3.x integration)
- [ ] Analyze step (summarize, topics, action items)
- [ ] Markdown transcript format with speaker labels
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
| 2026-02-14 | Python over Go/Rust | Native ML ecosystem (faster-whisper, pyannote) |
| 2026-02-14 | Textual for TUI | Modern, beautiful, pure Python, has file picker |
| 2026-02-14 | Typer for CLI | FastAPI-style, Rich integration |
| 2026-02-14 | Pydantic Settings | Type-safe, .env support, validation |
| 2026-02-14 | Step-based pipeline | Independent, testable, skippable, composable |
| 2026-02-14 | Event-driven progress | Decouples pipeline from UI |
| 2026-02-14 | Chunked transcription | Eliminates hallucination, enables validation |
| 2026-02-14 | Word timestamps on | Accurate timing, no wall-to-wall subs |
| 2026-02-14 | gpt-4.1 for translation | Better nuance vs mini |
| 2026-02-15 | Sync-first steps | Simpler code, TUI wraps in bg thread |
| 2026-02-15 | mediascribe name | Available on PyPI, clear, covers all use cases |
| 2026-02-15 | pyannote.audio 3.x | Best-in-class diarization, decoupled from transcription |
| 2026-02-15 | No streaming v1 | Different architecture, niche demand, quality tradeoff |
| 2026-02-15 | Overlap chunking (15s) | Eliminates mid-sentence cuts at chunk boundaries |

---

## Reference Implementation

The Yokai Watch pipeline (../pipeline.py) serves as the proven reference for:
- **Chunked transcription** with loop detection and retry
- **Word-timestamp timing** with duration cap and gap enforcement
- **Batched translation** with context overlap
- **Two-pass review** for quality
- **Idempotent execution** with skip-if-exists

This logic has been fully extracted into the modular step system.

---

## Handoff Notes

When picking up this project in a new session:

1. Read this PROJECT.md for current status
2. Read SPEC.md for architecture and feature details
3. Check the current phase and find the next unchecked task
4. Reference ../pipeline.py for the original proven patterns
5. Run tests: cd mediascribe && pip install -e ".[dev]" && pytest
6. Update this file after completing work
7. Commit after each feature: git add -A && git commit -m "feat: ..."
