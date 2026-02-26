"""File picker screen — browse and select media files."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Label,
    Static,
)

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",
}


class FilteredDirectoryTree(DirectoryTree):
    """Directory tree that highlights media files."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [
            p for p in paths
            if p.is_dir() or p.suffix.lower() in MEDIA_EXTENSIONS
        ]


class PickerScreen(Screen):
    """File/folder selection screen."""

    DEFAULT_CSS = """
    PickerScreen {
        layout: vertical;
    }

    #picker-layout {
        height: 1fr;
    }

    #tree-panel {
        width: 2fr;
        height: 100%;
        border-right: solid $primary;
    }

    #info-panel {
        width: 1fr;
        padding: 1 2;
    }

    #selected-label {
        margin-top: 1;
        text-style: bold;
    }

    #selected-info {
        height: auto;
        margin: 1 0;
    }

    #picker-buttons {
        height: auto;
        dock: bottom;
        padding: 1;
        align: center middle;
        border-top: solid $primary;
    }

    #picker-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="picker-layout"):
            with Vertical(id="tree-panel"):
                yield Label("[bold]Select a media file or folder[/bold]")
                yield FilteredDirectoryTree(Path.cwd(), id="dir-tree")
            with Vertical(id="info-panel"):
                yield Label("Selected:", id="selected-label")
                yield Static("(none)", id="selected-info")
        with Horizontal(id="picker-buttons"):
            yield Button("Process", variant="primary", id="btn-process", disabled=True)
            yield Button("Back", variant="default", id="btn-back")
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = event.path
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            self.selected_path = path
            info = f"[bold]{path.name}[/bold]\n"
            info += f"Path: {path}\n"
            info += f"Size: {path.stat().st_size / (1024*1024):.1f} MB\n"
            info += f"Type: {path.suffix}"
            self.query_one("#selected-info", Static).update(info)
            self.query_one("#btn-process", Button).disabled = False
        else:
            self.selected_path = None
            self.query_one("#selected-info", Static).update("Not a media file")
            self.query_one("#btn-process", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-process" and self.selected_path:
            from mediascribe.tui.screens.pipeline import PipelineScreen
            self.app.push_screen(PipelineScreen(self.selected_path))
