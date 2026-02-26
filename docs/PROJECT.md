# mediascribe — Project Tracker

> Living document for implementation tracking and session handoff.
> Update after every work session.

---

## Current Status

**Phase:** 1-3 — Core + TUI + Advanced Features — **FEATURE-COMPLETE**
**Last Session:** 2026-02-26
**Last Agent/Session Notes:** Feature set completeness audit performed. All Phase 1 gaps resolved, Phase 2 TUI implemented, Phase 3 features (diarization, analysis, markdown) implemented, CI/CD added, comprehensive test suite expanded to 230 tests.

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
**Focus:** Feature set completeness audit + implementation of all remaining features
**Completed:**
- Performed comprehensive feature audit across all phases
- **Phase 1 gaps resolved:**
  - `mediascribe translate <srt>` — standalone SRT translation command
  - `mediascribe config show/set/get/list/path` — full config management CLI
  - GitHub Actions CI workflow (test + lint + typecheck)
- **Phase 2 features implemented:**
  - TUI application with Textual (welcome, setup, picker, pipeline, results screens)
  - Profile system wired into translate/review steps via `settings.profile`
  - `mediascribe models list/download/path` — model management CLI
- **Phase 3 features implemented:**
  - Speaker diarization step (pyannote.audio integration with graceful fallbacks)
  - Analyze step (AI-powered summary, topics, key points, action items)
  - Markdown transcript format with speaker labels, TOC, paragraph grouping
  - Multi-format export (VTT/TXT/MD/JSON triggered by `output_formats` config)
- **Testing:** Expanded from 128 to 230 tests covering all new features
- **CI/CD:** GitHub Actions workflow for test, lint, typecheck

**Commits:**
14. feat: standalone translate command, config CLI, model management
15. test: comprehensive test suite for new features
16. feat: profile system wiring, multi-format export, additional tests
17. docs: update PROJECT.md and README with new features

---

## Phase 1 — Core Library + CLI (MVP) ✅

### 1.1 Project Foundation
- [x] Spec document (SPEC.md)
- [x] Project tracker (PROJECT.md)
- [x] pyproject.toml with dependencies
- [x] Module directory structure
- [x] .gitignore
- [x] Git repo initialized
- [x] Basic test structure
- [x] CI config (GitHub Actions)

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
- [x] cli/app.py — Typer app with transcribe, batch, config, tui, translate, models commands
- [x] cli/output.py — Rich event handler + pipeline runner + config/model management
- [x] End-to-end pipeline wiring (detect -> normalize -> transcribe -> translate -> review)
- [x] mediascribe translate <srt> — standalone translate command
- [x] mediascribe config show/set/get/list/path — config management
- [x] mediascribe models list/download/path — model management

---

## Phase 2 — TUI + Profiles ✅

### 2.1 TUI Application
- [x] tui/app.py — Textual app shell with screen navigation
- [x] tui/screens/welcome.py — Welcome + dependency check
- [x] tui/screens/setup.py — API key onboarding
- [x] tui/screens/picker.py — File/folder picker (filtered for media)
- [x] tui/screens/pipeline.py — Live execution progress (threaded)
- [x] tui/screens/results.py — Output review

### 2.2 Profile System
- [x] Built-in profiles: general, anime, podcast, meeting
- [x] Profile wired to translate/review steps via settings.profile
- [x] Profile selection via CLI flags (--profile)
- [x] Custom instructions merged with profiles

### 2.3 Smart Features
- [x] Hardware detection + concurrency recommendation
- [x] Processing time estimation
- [ ] Custom prompt builder (user intent -> system prompt) — deferred
- [ ] Large batch warnings — deferred

---

## Phase 3 — Advanced Features ✅

- [x] Speaker diarization (pyannote.audio 3.x integration with fallbacks)
- [x] Analyze step (summarize, topics, key points, action items)
- [x] Markdown transcript format with speaker labels, TOC, paragraphs
- [x] Multi-format export (VTT, TXT, MD, JSON via output_formats config)
- [x] Model download/cache management CLI
- [ ] Checkpoint-based resume on interrupt — deferred
- [ ] Plugin system for custom steps — deferred

---

## Phase 4 — Distribution

- [ ] PyPI publishing
- [ ] Homebrew tap
- [ ] Docker image
- [ ] User documentation
- [x] GitHub Actions CI/CD

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
| 2026-02-26 | Profile via settings | Simple, composable, avoids extra config file complexity |
| 2026-02-26 | Graceful diarize fallback | Skip with warning if pyannote/token not available |
| 2026-02-26 | Multi-format export | Automatic generation based on output_formats setting |

---

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| core/config + job | 15 | Settings, Job, Segment, enums |
| core/pipeline | 12 | Execution, skipping, errors, events |
| core/events | 4 | Bus, subscriptions, convenience methods |
| steps/transcribe (validate) | 9 | Hallucination detection |
| steps/transcribe (dedup) | 11 | Overlap dedup, fuzzy matching |
| steps/transcribe (clean) | 10 | Artifact removal |
| steps/diarize | 12 | Skipping, speaker assignment |
| steps/analyze | 9 | Skipping, execution, errors |
| formats/srt | 12 | Time conversion, I/O, segments |
| formats/vtt + json | 12 | VTT output, JSON structure |
| formats/transcript (md) | 16 | Paragraphs, speakers, TOC, metadata |
| cli/commands | 23 | Config, translate, batch, models |
| config management | 8 | TOML read/write |
| tui | 10 | Imports, app creation, screens |
| profiles | 8 | Settings, rendering, templates |
| multi-format export | 7 | VTT/TXT/MD/JSON export |
| **Total** | **230** | |

---

## Handoff Notes

When picking up this project in a new session:

1. Read this PROJECT.md for current status
2. Read SPEC.md for architecture and feature details
3. Check the current phase and find the next unchecked task
4. Run tests: `pip install -e ".[dev]" && pytest`
5. For TUI: `pip install -e ".[tui]"` then `mediascribe tui`
6. For diarization: `pip install -e ".[diarize]"` + HuggingFace token
7. Update this file after completing work
8. Commit after each feature: `git add -A && git commit -m "feat: ..."`

### Remaining Work (deferred features)
- Custom prompt builder (user describes intent, AI generates system prompt)
- Large batch warnings (estimate time, warn before processing)
- Checkpoint-based resume on interrupt
- Plugin system for custom pipeline steps
- PyPI publishing / Homebrew tap / Docker image
- User documentation site
