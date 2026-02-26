"""Main Textual application for mediascribe.

Provides a screen-based TUI workflow:
  Welcome -> [Setup] -> File Picker -> Config -> Pipeline Run -> Results
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from mediascribe.tui.screens.welcome import WelcomeScreen


class MediascribeApp(App[None]):
    """The mediascribe TUI application."""

    TITLE = "mediascribe"
    SUB_TITLE = "Transcribe, translate, and analyze media"
    CSS_PATH = None

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #app-header {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
    }

    .title-text {
        text-style: bold;
        color: $text;
    }

    .section-title {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }

    .dim-text {
        color: $text-muted;
    }

    .error-text {
        color: $error;
    }

    .success-text {
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())


def run_tui() -> None:
    """Launch the mediascribe TUI."""
    app = MediascribeApp()
    app.run()
