"""File picker screen — select files or folders for processing."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, ListItem, ListView, Static

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov",  # video
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",  # audio
}


def _is_media_file(path: Path) -> bool:
    return path.suffix.lower() in MEDIA_EXTENSIONS


def _file_size_str(path: Path) -> str:
    try:
        size = path.stat().st_size
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.0f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
    except OSError:
        return "?"


class PickerScreen(Screen):
    """File/folder picker — browse filesystem and select media files."""

    DEFAULT_CSS = """
    PickerScreen {
        layout: vertical;
    }
    PickerScreen #picker-header {
        dock: top;
        height: 3;
        padding: 1 2;
        text-style: bold;
        background: $primary-background;
    }
    PickerScreen #file-list {
        height: 1fr;
        margin: 1 2;
        border: round $surface-lighten-2;
    }
    PickerScreen #selected-info {
        dock: bottom;
        height: auto;
        padding: 1 2;
        background: $surface;
    }
    PickerScreen #button-row {
        dock: bottom;
        height: 3;
        padding: 0 2;
    }
    PickerScreen .file-item {
        padding: 0 1;
    }
    PickerScreen #next-btn {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("a", "add_files", "Add Files"),
        ("f", "add_folder", "Add Folder"),
        ("d", "remove_selected", "Remove"),
        ("n", "next_screen", "Next"),
        ("escape", "back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.selected_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Label("Select Media Files", id="picker-header")
        yield ListView(id="file-list")
        yield Static("No files selected", id="selected-info")
        with Horizontal(id="button-row"):
            yield Button("+ Add Files", variant="primary", id="add-files-btn")
            yield Button("+ Add Folder", variant="default", id="add-folder-btn")
            yield Button("Remove Selected", variant="warning", id="remove-btn")
            yield Button("Next →", variant="success", id="next-btn")

    def _update_info(self) -> None:
        count = len(self.selected_files)
        if count == 0:
            text = "No files selected"
        else:
            total_size = sum(f.stat().st_size for f in self.selected_files if f.exists())
            size_str = _file_size_str(Path("/"))  # placeholder
            if total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.0f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            text = f"{count} file{'s' if count != 1 else ''} selected ({size_str} total)"

        self.query_one("#selected-info", Static).update(text)

    def _refresh_list(self) -> None:
        listview = self.query_one("#file-list", ListView)
        listview.clear()
        for path in self.selected_files:
            size = _file_size_str(path)
            item = ListItem(Label(f"  {path.name}  [{size}]  — {path.parent}"))
            listview.append(item)
        self._update_info()

    @on(Button.Pressed, "#add-files-btn")
    def action_add_files(self) -> None:
        """Open file picker dialog."""
        from textual_fspicker import FileOpen, Filters

        filters = Filters(
            ("Media files", lambda p: _is_media_file(p)),
            ("All files", lambda _: True),
        )

        def handle_result(path: Path | None) -> None:
            if path and path not in self.selected_files:
                self.selected_files.append(path)
                self._refresh_list()

        self.app.push_screen(FileOpen(title="Select Media File", filters=filters), handle_result)

    @on(Button.Pressed, "#add-folder-btn")
    def action_add_folder(self) -> None:
        """Open directory picker and add all media files from it."""
        from textual_fspicker import SelectDirectory

        def handle_result(path: Path | None) -> None:
            if path and path.is_dir():
                new_files = sorted(
                    f for f in path.iterdir()
                    if f.is_file() and _is_media_file(f) and f not in self.selected_files
                )
                self.selected_files.extend(new_files)
                self._refresh_list()

        self.app.push_screen(SelectDirectory(title="Select Folder"), handle_result)

    @on(Button.Pressed, "#remove-btn")
    def action_remove_selected(self) -> None:
        """Remove the highlighted item from the list."""
        listview = self.query_one("#file-list", ListView)
        if listview.index is not None and 0 <= listview.index < len(self.selected_files):
            self.selected_files.pop(listview.index)
            self._refresh_list()

    @on(Button.Pressed, "#next-btn")
    def action_next_screen(self) -> None:
        if not self.selected_files:
            self.notify("Please select at least one file.", severity="warning")
            return
        self.app.push_screen("profile")

    def action_back(self) -> None:
        self.app.pop_screen()
