"""Live log output panel for the pipeline execution screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class LogPanel(Widget):
    """Scrolling log panel showing pipeline event messages."""

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        border: round $surface-lighten-2;
        padding: 0 1;
    }
    LogPanel .log-title {
        dock: top;
        text-style: bold;
        color: $text-muted;
        padding: 0 0 0 0;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, wrap=True, id="log-output")

    def write_log(self, message: str) -> None:
        """Append a plain log message."""
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(f"  {message}")
        except Exception:
            pass

    def write_step(self, step: str, message: str) -> None:
        """Append a step-related message."""
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(f"[bold cyan]▶ [{step}][/bold cyan] {message}")
        except Exception:
            pass

    def write_success(self, message: str) -> None:
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(f"[green]✓[/green] {message}")
        except Exception:
            pass

    def write_error(self, message: str) -> None:
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(f"[red]✗[/red] {message}")
        except Exception:
            pass

    def write_warning(self, message: str) -> None:
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(f"[yellow]⚠[/yellow] {message}")
        except Exception:
            pass

    def clear(self) -> None:
        try:
            log = self.query_one("#log-output", RichLog)
            log.clear()
        except Exception:
            pass
