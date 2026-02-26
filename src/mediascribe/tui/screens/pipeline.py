"""Pipeline execution screen — live progress display."""

from __future__ import annotations

import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, RichLog

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.core.pipeline import Pipeline
from mediascribe.steps.detect import DetectStep
from mediascribe.steps.normalize import NormalizeStep
from mediascribe.steps.transcribe import TranscribeStep


class PipelineScreen(Screen):
    """Runs the processing pipeline with live progress."""

    DEFAULT_CSS = """
    PipelineScreen {
        layout: vertical;
    }

    #progress-section {
        height: auto;
        padding: 1 2;
    }

    #log-section {
        height: 1fr;
        padding: 0 2;
    }

    #pipeline-buttons {
        height: auto;
        dock: bottom;
        padding: 1;
        align: center middle;
        border-top: solid $primary;
    }
    """

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self._thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="progress-section"):
            yield Label(f"[bold]Processing:[/bold] {self.file_path.name}")
            yield ProgressBar(total=100, show_eta=True, id="main-progress")
            yield Label("", id="step-label")
        with Vertical(id="log-section"):
            yield RichLog(highlight=True, markup=True, id="log-panel")
        yield Button("Done", variant="primary", id="btn-done", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self._thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self._thread.start()

    def _run_pipeline(self) -> None:
        from dotenv import load_dotenv
        load_dotenv()

        settings = MediascribeSettings()
        settings.ensure_dirs()

        events = EventBus()
        events.subscribe(self._on_event)

        pipeline = Pipeline(settings, events)
        pipeline.add_step(DetectStep())
        pipeline.add_step(NormalizeStep())
        pipeline.add_step(TranscribeStep())

        job = Job(
            input_path=self.file_path.resolve(),
            output_dir=settings.output_dir.resolve(),
        )

        pipeline.run(job)

        self.app.call_from_thread(self._on_complete, job)

    def _on_event(self, event: PipelineEvent) -> None:
        def update() -> None:
            log = self.query_one("#log-panel", RichLog)
            progress = self.query_one("#main-progress", ProgressBar)
            step_label = self.query_one("#step-label", Label)

            match event.type:
                case EventType.STEP_START:
                    step_label.update(f"  [cyan]{event.message}[/cyan]")
                    log.write(f"[bold cyan]> {event.message}[/bold cyan]")
                case EventType.STEP_PROGRESS:
                    pct = int(event.progress * 100)
                    progress.update(progress=pct)
                    log.write(f"  {event.message} [{pct}%]")
                case EventType.STEP_COMPLETE:
                    log.write(f"  [green]OK[/green] {event.message}")
                case EventType.STEP_SKIPPED:
                    log.write(f"  [dim]skip {event.message}[/dim]")
                case EventType.STEP_ERROR:
                    log.write(f"  [red]ERR {event.message}[/red]")
                case EventType.LOG:
                    log.write(f"  {event.message}")
                case EventType.WARNING:
                    log.write(f"  [yellow]WARN {event.message}[/yellow]")
                case EventType.JOB_COMPLETE:
                    progress.update(progress=100)
                    step_label.update("[bold green]Complete[/bold green]")
                case EventType.JOB_ERROR:
                    step_label.update(f"[bold red]{event.message}[/bold red]")

        self.app.call_from_thread(update)

    def _on_complete(self, job: Job) -> None:
        self.query_one("#btn-done", Button).disabled = False
        progress = self.query_one("#main-progress", ProgressBar)
        progress.update(progress=100)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            self.app.pop_screen()
            self.app.pop_screen()
