"""Results screen — review output files after pipeline execution."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static


class ResultsScreen(Screen[None]):
    """Post-pipeline results review screen."""

    DEFAULT_CSS = """
    ResultsScreen {
        align: center middle;
    }

    #results-box {
        width: 72;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: tall $primary;
    }

    #results-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    #output-list {
        height: auto;
        max-height: 20;
        overflow-y: auto;
        margin: 1 0;
    }

    #results-actions {
        margin-top: 1;
        layout: horizontal;
    }

    #results-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="results-box"):
            yield Label("Results", id="results-title")
            yield Static(id="output-list")
            with Horizontal(id="results-actions"):
                yield Button("Process More", variant="primary", id="btn-more")
                yield Button("Quit", variant="error", id="btn-quit")

    def on_mount(self) -> None:
        output_dir = Path("./output")
        self._show_outputs(output_dir)

    def _show_outputs(self, output_dir: Path) -> None:
        widget = self.query_one("#output-list", Static)

        if not output_dir.exists():
            widget.update("[yellow]No output directory found.[/yellow]")
            return

        files = sorted(output_dir.iterdir())
        output_files = [f for f in files if f.is_file()]

        if not output_files:
            widget.update("[yellow]No output files found.[/yellow]")
            return

        lines = [f"[bold]Output directory:[/bold] {output_dir.resolve()}\n"]
        for f in output_files:
            size = f.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            ext = f.suffix.upper().lstrip(".")
            lines.append(f"  [green]OK[/green]  {f.name:<40s} {size_str:>10s}  ({ext})")

        lines.append(f"\n[bold]{len(output_files)} file(s) generated.[/bold]")
        widget.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-more":
            from mediascribe.tui.screens.picker import PickerScreen

            self.app.push_screen(PickerScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()
