"""Results screen — display output files and analysis."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from mediascribe.core.job import Job


class ResultsScreen(Screen):
    """Display processing results and output file list."""

    DEFAULT_CSS = """
    ResultsScreen {
        layout: vertical;
    }

    #results-content {
        height: 1fr;
        padding: 1 2;
    }

    #file-list {
        height: auto;
        margin: 1 0;
    }

    #analysis-section {
        height: auto;
        margin: 1 0;
        border: solid $primary;
        padding: 1;
    }

    #results-buttons {
        height: auto;
        dock: bottom;
        padding: 1;
        align: center middle;
    }
    """

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="results-content"):
            yield Label(f"[bold]Results:[/bold] {self.job.input_path.name}")
            yield Label(f"Status: {self.job.status.value}")
            yield Static(id="file-list")
            if self.job.analysis:
                yield Label("[bold]Analysis[/bold]", classes="section-title")
                yield Static(id="analysis-section")
        with Horizontal(id="results-buttons"):
            yield Button("Process More", variant="primary", id="btn-more")
            yield Button("Quit", variant="error", id="btn-quit")
        yield Footer()

    def on_mount(self) -> None:
        output_dir = self.job.output_dir
        files = sorted(output_dir.glob(f"{self.job.stem}*"))
        if files:
            file_text = "\n".join(f"  {f.name}" for f in files)
            self.query_one("#file-list", Static).update(
                f"[bold]Output files:[/bold]\n{file_text}"
            )

        if self.job.analysis:
            analysis = self.job.analysis
            parts = []
            if "summary" in analysis:
                parts.append(f"[bold]Summary:[/bold] {analysis['summary']}")
            if "topics" in analysis:
                parts.append(f"[bold]Topics:[/bold] {', '.join(analysis['topics'])}")
            if "action_items" in analysis and analysis["action_items"]:
                items = "\n".join(f"  - {item}" for item in analysis["action_items"])
                parts.append(f"[bold]Action Items:[/bold]\n{items}")
            self.query_one("#analysis-section", Static).update("\n\n".join(parts))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-quit":
            self.app.exit()
        elif event.button.id == "btn-more":
            from mediascribe.tui.screens.picker import PickerScreen
            self.app.switch_screen(PickerScreen())
