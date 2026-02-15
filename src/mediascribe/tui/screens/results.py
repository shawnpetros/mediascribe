"""Results screen — review output files after pipeline completion."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, ListItem, ListView, Static, TextArea

from mediascribe.core.job import Job, JobStatus


class ResultsScreen(Screen):
    """Review pipeline output — file list, preview, and actions."""

    DEFAULT_CSS = """
    ResultsScreen {
        layout: vertical;
    }
    ResultsScreen #results-header {
        dock: top;
        height: 3;
        padding: 1 2;
        text-style: bold;
        background: $primary-background;
    }
    ResultsScreen #summary {
        height: auto;
        padding: 1 2;
    }
    ResultsScreen #results-body {
        height: 1fr;
        layout: horizontal;
    }
    ResultsScreen #file-list-panel {
        width: 1fr;
        margin: 0 1 0 2;
        border: round $surface-lighten-2;
    }
    ResultsScreen #preview-panel {
        width: 2fr;
        margin: 0 2 0 1;
        border: round $surface-lighten-2;
    }
    ResultsScreen #preview-area {
        height: 1fr;
    }
    ResultsScreen #button-row {
        dock: bottom;
        height: 3;
        padding: 0 2;
    }
    """

    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("p", "process_more", "Process More"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._output_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Label("Results", id="results-header")
        yield Static("", id="summary")
        with Horizontal(id="results-body"):
            yield ListView(id="file-list-panel")
            yield TextArea(
                "Select a file to preview its contents.",
                read_only=True,
                id="preview-area",
            )
        with Horizontal(id="button-row"):
            yield Button("Process More Files", variant="primary", id="more-btn")
            yield Button("Quit", variant="default", id="quit-btn")

    def on_mount(self) -> None:
        self._load_results()

    def _load_results(self) -> None:
        """Load completed/failed jobs and list output files."""
        completed: list[Job] = getattr(self.app, "_completed_jobs", [])
        failed: list[Job] = getattr(self.app, "_failed_jobs", [])

        # Build summary
        lines = []
        if completed:
            n = len(completed)
            lines.append(
                f"[green]✓ {n} file{'s' if n != 1 else ''} completed[/green]"
            )
        if failed:
            lines.append(f"[red]✗ {len(failed)} file{'s' if len(failed) != 1 else ''} failed[/red]")
            for job in failed:
                lines.append(f"  [red]{job.input_path.name}: {job.error}[/red]")

        self.query_one("#summary", Static).update("\n".join(lines) if lines else "No results.")

        # Gather output files
        self._output_files = []
        listview = self.query_one("#file-list-panel", ListView)

        for job in completed:
            output_dir = job.output_dir
            if output_dir.exists():
                for path in sorted(output_dir.glob(f"{job.stem}*")):
                    if path.is_file():
                        self._output_files.append(path)
                        size = self._file_size_str(path)
                        icon = "✓" if job.status == JobStatus.COMPLETED else "✗"
                        item = ListItem(
                            Label(f"{icon}  {path.name}  [{size}]")
                        )
                        listview.append(item)

        if not self._output_files:
            listview.append(ListItem(Label("  No output files generated.")))

    @on(ListView.Selected, "#file-list-panel")
    def _preview_file(self, event: ListView.Selected) -> None:
        """Preview the selected output file."""
        idx = event.list_view.index
        if idx is None or idx >= len(self._output_files):
            return

        path = self._output_files[idx]
        try:
            content = path.read_text(encoding="utf-8")
            # Truncate very long files for preview
            if len(content) > 10000:
                content = content[:10000] + "\n\n... (truncated for preview)"
            self.query_one("#preview-area", TextArea).load_text(content)
        except Exception as exc:
            self.query_one("#preview-area", TextArea).load_text(f"Error reading file: {exc}")

    @on(Button.Pressed, "#more-btn")
    def action_process_more(self) -> None:
        """Go back to picker to process more files."""
        # Pop back to picker (remove pipeline + results screens)
        while len(self.app.screen_stack) > 1:
            screen = self.app.screen_stack[-1]
            if hasattr(screen, "selected_files"):
                # We're at the picker
                break
            self.app.pop_screen()
        else:
            self.app.push_screen("picker")

    @on(Button.Pressed, "#quit-btn")
    def action_quit_app(self) -> None:
        self.app.exit()

    @staticmethod
    def _file_size_str(path: Path) -> str:
        try:
            size = path.stat().st_size
            if size < 1024:
                return f"{size} B"
            if size < 1024 * 1024:
                return f"{size / 1024:.0f} KB"
            return f"{size / (1024 * 1024):.1f} MB"
        except OSError:
            return "?"
