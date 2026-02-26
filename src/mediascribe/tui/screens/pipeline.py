"""Pipeline execution screen — runs the pipeline with live progress display."""

from __future__ import annotations

import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Log, ProgressBar, Static


class PipelineScreen(Screen):
    """Live pipeline execution with progress and log output."""

    DEFAULT_CSS = """
    PipelineScreen {
        layout: vertical;
    }

    #pipeline-title {
        text-style: bold;
        text-align: center;
        margin: 1;
    }

    #progress-section {
        height: 5;
        margin: 0 2;
    }

    #progress-label {
        margin-bottom: 0;
    }

    #log-section {
        height: 1fr;
        margin: 1 2;
        border: tall $primary;
    }

    #pipeline-actions {
        dock: bottom;
        height: 3;
        layout: horizontal;
        padding: 0 1;
    }

    #pipeline-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, files: list[Path], config: dict) -> None:
        super().__init__()
        self.files = files
        self.config = config
        self._completed = False
        self._error = False

    def compose(self) -> ComposeResult:
        yield Label("Pipeline Execution", id="pipeline-title")
        with Vertical(id="progress-section"):
            yield Static("Preparing...", id="progress-label")
            yield ProgressBar(total=100, show_eta=True, id="progress-bar")
        yield Log(id="log-section", highlight=True, auto_scroll=True)
        with Vertical(id="pipeline-actions"):
            yield Button("Done", variant="primary", id="btn-done", disabled=True)

    def on_mount(self) -> None:
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _log(self, message: str) -> None:
        self.app.call_from_thread(self._append_log, message)

    def _append_log(self, message: str) -> None:
        self.query_one("#log-section", Log).write_line(message)

    def _set_progress(self, label: str, pct: float) -> None:
        self.app.call_from_thread(self._update_progress, label, pct)

    def _update_progress(self, label: str, pct: float) -> None:
        self.query_one("#progress-label", Static).update(label)
        self.query_one("#progress-bar", ProgressBar).update(progress=pct)

    def _finish(self, success: bool) -> None:
        self.app.call_from_thread(self._on_finish, success)

    def _on_finish(self, success: bool) -> None:
        self._completed = True
        self._error = not success
        btn = self.query_one("#btn-done", Button)
        btn.disabled = False
        if success:
            self.query_one("#progress-label", Static).update(
                "[bold green]Pipeline complete![/bold green]"
            )
        else:
            self.query_one("#progress-label", Static).update(
                "[bold red]Pipeline failed.[/bold red]"
            )

    def _run_pipeline(self) -> None:
        """Execute the pipeline in a background thread."""
        from dotenv import load_dotenv

        from mediascribe.core.config import MediascribeSettings
        from mediascribe.core.events import EventBus, EventType, PipelineEvent
        from mediascribe.core.job import Job
        from mediascribe.core.pipeline import Pipeline
        from mediascribe.steps.analyze import AnalyzeStep
        from mediascribe.steps.detect import DetectStep
        from mediascribe.steps.diarize import DiarizeStep
        from mediascribe.steps.export import ExportStep
        from mediascribe.steps.normalize import NormalizeStep
        from mediascribe.steps.review import ReviewStep
        from mediascribe.steps.transcribe import TranscribeStep
        from mediascribe.steps.translate import TranslateStep

        load_dotenv()

        output_dir = Path("./output")
        cfg = self.config

        settings = MediascribeSettings(
            source_language=cfg.get("source_language"),
            target_language=cfg.get("target_language"),
            custom_instructions=cfg.get("custom_instructions", ""),
            enable_review_pass=cfg.get("enable_review", True),
            output_dir=output_dir,
            profile=cfg.get("profile", "general"),
            output_formats=cfg.get("output_formats", ["srt"]),
        )
        settings.ensure_dirs()

        total_files = len(self.files)
        all_success = True

        for file_idx, input_path in enumerate(self.files):
            file_pct_base = (file_idx / total_files) * 100
            file_pct_range = 100 / total_files

            self._log(f"\n{'=' * 50}")
            self._log(f"  [{file_idx + 1}/{total_files}] {input_path.name}")
            self._log(f"{'=' * 50}")

            events = EventBus()

            def make_handler(base: float, frange: float):
                def handler(event: PipelineEvent) -> None:
                    match event.type:
                        case EventType.STEP_START:
                            self._log(f"  >> {event.message}")
                        case EventType.STEP_PROGRESS:
                            pct = base + (event.progress * frange * 0.8)
                            self._set_progress(
                                f"[{file_idx + 1}/{total_files}] {event.message}",
                                pct,
                            )
                        case EventType.STEP_COMPLETE:
                            self._log(f"  OK {event.message}")
                        case EventType.STEP_SKIPPED:
                            self._log(f"  -- {event.message}")
                        case EventType.STEP_ERROR:
                            self._log(f"  !! {event.message}")
                        case EventType.LOG:
                            step = f"[{event.step_name}] " if event.step_name else ""
                            self._log(f"     {step}{event.message}")
                        case EventType.WARNING:
                            step = f"[{event.step_name}] " if event.step_name else ""
                            self._log(f"  !! {step}{event.message}")
                        case EventType.JOB_COMPLETE:
                            self._log(f"  ** {event.message}")
                        case EventType.JOB_ERROR:
                            self._log(f"  !! {event.message}")
                return handler

            events.subscribe(make_handler(file_pct_base, file_pct_range))

            pipeline = Pipeline(settings, events)
            pipeline.add_step(DetectStep())
            pipeline.add_step(NormalizeStep())
            pipeline.add_step(TranscribeStep())
            if cfg.get("enable_diarize"):
                pipeline.add_step(DiarizeStep())
            if cfg.get("target_language"):
                pipeline.add_step(TranslateStep())
                if cfg.get("enable_review", True):
                    pipeline.add_step(ReviewStep())
            if cfg.get("enable_analyze"):
                pipeline.add_step(AnalyzeStep())
            pipeline.add_step(ExportStep())

            job = Job(
                input_path=input_path.resolve(),
                output_dir=output_dir.resolve(),
            )

            try:
                result = pipeline.run(job)
                if result.error:
                    self._log(f"  FAILED: {result.error}")
                    all_success = False
            except Exception as exc:
                self._log(f"  EXCEPTION: {exc}")
                all_success = False

        self._set_progress("Complete", 100)
        self._finish(all_success)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            if self._completed:
                from mediascribe.tui.screens.results import ResultsScreen
                self.app.push_screen(ResultsScreen())
