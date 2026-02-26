"""File picker screen — browse and select media files for processing."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Label, Static

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",
}


class MediaDirectoryTree(DirectoryTree):
    """Directory tree filtered to show only media files and directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [
            p for p in paths
            if p.is_dir() or p.suffix.lower() in MEDIA_EXTENSIONS
        ]


class PickerScreen(Screen):
    """File/folder picker for selecting media files to process."""

    DEFAULT_CSS = """
    PickerScreen {
        layout: vertical;
    }

    #picker-title {
        text-style: bold;
        text-align: center;
        margin: 1;
    }

    #picker-layout {
        height: 1fr;
    }

    #tree-pane {
        width: 2fr;
        border: tall $primary;
        margin: 0 1;
    }

    #selection-pane {
        width: 1fr;
        border: tall $accent;
        margin: 0 1;
        padding: 1;
    }

    #selected-list {
        height: 1fr;
        overflow-y: auto;
    }

    #selection-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #picker-actions {
        dock: bottom;
        height: 3;
        layout: horizontal;
        padding: 0 1;
    }

    #picker-actions Button {
        margin: 0 1;
    }
    """

    selected_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Label("Select Media Files", id="picker-title")
        with Horizontal(id="picker-layout"):
            yield MediaDirectoryTree(Path.cwd(), id="tree-pane")
            with Vertical(id="selection-pane"):
                yield Label("Selected Files:", id="selection-title")
                yield Static("(none)", id="selected-list")
        with Horizontal(id="picker-actions"):
            yield Button("Back", variant="default", id="btn-back")
            yield Button("Clear", variant="warning", id="btn-clear")
            yield Button("Next", variant="primary", id="btn-next")

    def on_mount(self) -> None:
        self.selected_files = []

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = event.path
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            if path not in self.selected_files:
                self.selected_files.append(path)
                self._update_selection()

    def _update_selection(self) -> None:
        widget = self.query_one("#selected-list", Static)
        if not self.selected_files:
            widget.update("(none)")
        else:
            lines = [f"  {i+1}. {f.name}" for i, f in enumerate(self.selected_files)]
            widget.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-clear":
            self.selected_files = []
            self._update_selection()
        elif event.button.id == "btn-next":
            if self.selected_files:
                from mediascribe.tui.screens.profile import ProfileScreen
                self.app.push_screen(ProfileScreen(self.selected_files))
            else:
                self.query_one("#selected-list", Static).update(
                    "[yellow]Select at least one file.[/yellow]"
                )
