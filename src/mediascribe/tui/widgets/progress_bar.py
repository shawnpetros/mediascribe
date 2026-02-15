"""Per-step and per-job progress bar widgets for the pipeline screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar


class StepProgress(Widget):
    """Progress indicator for a single pipeline step."""

    DEFAULT_CSS = """
    StepProgress {
        height: 3;
        padding: 0 1;
    }
    StepProgress .step-name {
        width: 1fr;
        color: $text-muted;
    }
    StepProgress .step-name.active {
        color: $accent;
        text-style: bold;
    }
    StepProgress .step-name.done {
        color: $success;
    }
    StepProgress .step-name.error {
        color: $error;
    }
    StepProgress .step-status {
        width: 4;
        text-align: right;
    }
    StepProgress ProgressBar {
        padding: 0;
    }
    """

    status: reactive[str] = reactive("pending")  # pending, active, done, skipped, error
    progress: reactive[float] = reactive(0.0)

    def __init__(self, step_name: str, description: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.step_name = step_name
        self.description = description

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(f"  {self.description}", classes="step-name", id="step-label")
            yield Label("", classes="step-status", id="step-icon")
        yield ProgressBar(total=100, show_eta=False, show_percentage=True, id="step-bar")

    def watch_status(self, value: str) -> None:
        try:
            label = self.query_one("#step-label", Label)
            icon = self.query_one("#step-icon", Label)
            bar = self.query_one("#step-bar", ProgressBar)
        except Exception:
            return

        label.remove_class("active", "done", "error")

        if value == "pending":
            icon.update("  ")
            bar.update(progress=0)
        elif value == "active":
            label.add_class("active")
            icon.update("▶ ")
        elif value == "done":
            label.add_class("done")
            icon.update("✓ ")
            bar.update(progress=100)
        elif value == "skipped":
            icon.update("⏭ ")
            bar.update(progress=100)
        elif value == "error":
            label.add_class("error")
            icon.update("✗ ")

    def watch_progress(self, value: float) -> None:
        try:
            bar = self.query_one("#step-bar", ProgressBar)
            bar.update(progress=int(value * 100))
        except Exception:
            pass


class JobProgress(Widget):
    """Overall progress for a single file being processed."""

    DEFAULT_CSS = """
    JobProgress {
        height: auto;
        padding: 1;
        margin: 0 1;
        border: round $primary;
    }
    JobProgress .job-header {
        text-style: bold;
        padding: 0 0 1 0;
    }
    JobProgress .job-info {
        color: $text-muted;
    }
    """

    def __init__(self, filename: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filename = filename
        self._step_widgets: dict[str, StepProgress] = {}

    def compose(self) -> ComposeResult:
        yield Label(f" {self.filename}", classes="job-header")
        yield Label("", classes="job-info", id="job-info")
        yield Vertical(id="steps-container")

    def add_step(self, step_name: str, description: str) -> StepProgress:
        """Add a step progress widget."""
        step = StepProgress(step_name, description)
        self._step_widgets[step_name] = step
        container = self.query_one("#steps-container", Vertical)
        container.mount(step)
        return step

    def set_step_status(self, step_name: str, status: str) -> None:
        if step_name in self._step_widgets:
            self._step_widgets[step_name].status = status

    def set_step_progress(self, step_name: str, progress: float) -> None:
        if step_name in self._step_widgets:
            self._step_widgets[step_name].progress = progress

    def set_info(self, text: str) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            self.query_one("#job-info", Label).update(f"  {text}")
