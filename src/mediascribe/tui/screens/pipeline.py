"""Pipeline execution screen — live progress display."""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, JobStatus
from mediascribe.core.pipeline import Pipeline
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.review import ReviewStep
from mediascribe.steps.transcribe import TranscribeStep
from mediascribe.steps.translate import TranslateStep
from mediascribe.tui.widgets.log_panel import LogPanel
from mediascribe.tui.widgets.progress_bar import JobProgress

# Step definitions for the progress display
STEP_DEFS = [
    ("detect", "Detect file type and metadata"),
    ("normalize", "Extract and normalize audio"),
    ("transcribe", "Transcribe audio to text"),
]

TRANSLATE_STEPS = [
    ("translate", "Translate to target language"),
    ("review", "AI quality review pass"),
]


class PipelineScreen(Screen):
    """Run the pipeline and show live progress."""

    DEFAULT_CSS = """
    PipelineScreen {
        layout: vertical;
    }
    PipelineScreen #pipeline-header {
        dock: top;
        height: 3;
        padding: 1 2;
        text-style: bold;
        background: $primary-background;
    }
    PipelineScreen #jobs-scroll {
        height: 2fr;
        margin: 0 2;
    }
    PipelineScreen LogPanel {
        height: 1fr;
        margin: 0 2;
    }
    PipelineScreen #pipeline-status {
        dock: bottom;
        height: auto;
        padding: 1 2;
        background: $surface;
    }
    PipelineScreen #button-row {
        dock: bottom;
        height: 3;
        padding: 0 2;
    }
    PipelineScreen #cancel-btn {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._cancelled = False
        self._completed_jobs: list[Job] = []
        self._failed_jobs: list[Job] = []
        self._job_widgets: dict[str, JobProgress] = {}

    def compose(self) -> ComposeResult:
        yield Label("Pipeline Execution", id="pipeline-header")
        yield VerticalScroll(id="jobs-scroll")
        yield LogPanel(id="log-panel")
        yield Static("Preparing...", id="pipeline-status")
        with Horizontal(id="button-row"):
            yield Button("Cancel", variant="error", id="cancel-btn")
            yield Button("View Results →", variant="success", id="results-btn", disabled=True)

    def on_mount(self) -> None:
        self._start_processing()

    def _start_processing(self) -> None:
        """Kick off pipeline execution in a worker thread."""
        self._running = True
        self._cancelled = False
        self._run_all_jobs()

    @work(thread=True)
    def _run_all_jobs(self) -> None:
        """Run pipeline for all selected files (in worker thread)."""
        from dotenv import load_dotenv
        load_dotenv()

        # Get files and settings from previous screens
        picker = self.app.get_screen("picker")
        files: list[Path] = getattr(picker, "selected_files", [])
        settings_dict: dict = getattr(self.app, "_pipeline_settings", {})

        if not files:
            self.app.call_from_thread(self._update_status, "No files to process.")
            return

        total = len(files)
        self.app.call_from_thread(
            self._update_status,
            f"Processing {total} file{'s' if total != 1 else ''}...",
        )

        for i, file_path in enumerate(files):
            if self._cancelled:
                self.app.call_from_thread(
                    self._update_status, f"Cancelled after {i}/{total} files."
                )
                break

            self._process_single_file(file_path, settings_dict, i + 1, total)

        if not self._cancelled:
            completed = len(self._completed_jobs)
            failed = len(self._failed_jobs)
            status = f"Done: {completed} completed"
            if failed:
                status += f", {failed} failed"
            self.app.call_from_thread(self._update_status, status)

        self._running = False
        self.app.call_from_thread(self._enable_results_button)

    def _process_single_file(
        self, file_path: Path, settings_dict: dict, index: int, total: int
    ) -> None:
        """Process a single file through the pipeline."""
        target_language = settings_dict.get("target_language")
        enable_review = settings_dict.get("enable_review_pass", True)

        # Build settings
        settings = MediascribeSettings(
            source_language=settings_dict.get("source_language"),
            target_language=target_language,
            transcription_mode=settings_dict.get("transcription_mode", "auto"),
            whisper_model=settings_dict.get("whisper_model", "large-v3"),
            translation_model=settings_dict.get("translation_model", "gpt-4.1"),
            enable_review_pass=enable_review,
            custom_instructions=settings_dict.get("custom_instructions", ""),
            output_formats=settings_dict.get("output_formats", ["srt"]),
        )
        settings.ensure_dirs()

        # Create job
        job = Job(
            input_path=file_path.resolve(),
            output_dir=settings.output_dir.resolve(),
        )

        # Determine which steps to show
        steps = list(STEP_DEFS)
        if target_language:
            steps.extend(TRANSLATE_STEPS)
            if not enable_review:
                steps = [s for s in steps if s[0] != "review"]

        # Create UI progress widget
        job_key = str(file_path)
        self.app.call_from_thread(self._add_job_widget, file_path.name, job_key, steps)

        # Build event bus with handler
        events = EventBus()
        events.subscribe(lambda evt: self._handle_event(evt, job_key))

        # Build pipeline
        pipeline = Pipeline(settings, events)
        pipeline.add_step(DetectStep())
        pipeline.add_step(NormalizeStep())
        pipeline.add_step(TranscribeStep())
        if target_language:
            pipeline.add_step(TranslateStep())
            if enable_review:
                pipeline.add_step(ReviewStep())

        # Run
        result = pipeline.run(job)

        if result.status == JobStatus.COMPLETED:
            self._completed_jobs.append(result)
        else:
            self._failed_jobs.append(result)

    def _handle_event(self, event: PipelineEvent, job_key: str) -> None:
        """Handle pipeline events from the worker thread."""
        log_panel = None

        def _update() -> None:
            nonlocal log_panel
            try:
                log_panel = self.query_one("#log-panel", LogPanel)
            except Exception:
                return

            step = event.step_name or ""

            if event.type == EventType.JOB_START:
                log_panel.write_log(event.message)
            elif event.type == EventType.STEP_START:
                self._set_job_step_status(job_key, step, "active")
                log_panel.write_step(step, event.message)
            elif event.type == EventType.STEP_PROGRESS:
                self._set_job_step_progress(job_key, step, event.progress)
            elif event.type == EventType.STEP_COMPLETE:
                self._set_job_step_status(job_key, step, "done")
                log_panel.write_success(event.message)
            elif event.type == EventType.STEP_SKIPPED:
                self._set_job_step_status(job_key, step, "skipped")
                log_panel.write_log(f"Skipped: {event.message}")
            elif event.type == EventType.STEP_ERROR:
                self._set_job_step_status(job_key, step, "error")
                log_panel.write_error(event.message)
            elif event.type == EventType.JOB_COMPLETE:
                log_panel.write_success(event.message)
            elif event.type == EventType.JOB_ERROR:
                log_panel.write_error(event.message)
            elif event.type == EventType.LOG:
                log_panel.write_log(f"[{step}] {event.message}" if step else event.message)
            elif event.type == EventType.WARNING:
                log_panel.write_warning(f"[{step}] {event.message}" if step else event.message)

        self.app.call_from_thread(_update)

    def _add_job_widget(
        self, filename: str, job_key: str, steps: list[tuple[str, str]]
    ) -> None:
        """Add a job progress widget to the UI (called on main thread)."""
        container = self.query_one("#jobs-scroll", VerticalScroll)
        widget = JobProgress(filename)
        container.mount(widget)
        self._job_widgets[job_key] = widget

        for step_name, step_desc in steps:
            widget.add_step(step_name, step_desc)

    def _set_job_step_status(self, job_key: str, step_name: str, status: str) -> None:
        if job_key in self._job_widgets:
            self._job_widgets[job_key].set_step_status(step_name, status)

    def _set_job_step_progress(self, job_key: str, step_name: str, progress: float) -> None:
        if job_key in self._job_widgets:
            self._job_widgets[job_key].set_step_progress(step_name, progress)

    def _update_status(self, text: str) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            self.query_one("#pipeline-status", Static).update(text)

    def _enable_results_button(self) -> None:
        try:
            self.query_one("#results-btn", Button).disabled = False
            self.query_one("#cancel-btn", Button).disabled = True
        except Exception:
            pass

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        self._cancelled = True
        self._update_status("Cancelling after current file...")

    @on(Button.Pressed, "#results-btn")
    def _go_to_results(self) -> None:
        # Store results for the results screen
        self.app._completed_jobs = self._completed_jobs  # type: ignore[attr-defined]
        self.app._failed_jobs = self._failed_jobs  # type: ignore[attr-defined]
        self.app.push_screen("results")
