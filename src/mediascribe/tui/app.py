"""Textual TUI application for mediascribe.

Provides an interactive interface with screen navigation:
  Welcome → Setup → File Picker → Config → Run → Results
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from mediascribe import __version__


class MediascribeApp(App):
    """Main TUI application for mediascribe."""

    TITLE = "mediascribe"
    SUB_TITLE = f"v{__version__}"
    CSS_PATH = None

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("?", "help", "Help", show=True),
    ]

    DEFAULT_CSS = """
    Screen {
        background: $surface;
    }

    #welcome-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    .title {
        text-style: bold;
        color: $accent;
        text-align: center;
        width: 100%;
    }

    .subtitle {
        color: $text-muted;
        text-align: center;
        width: 100%;
    }

    .section-title {
        text-style: bold;
        margin-top: 1;
    }

    #status-panel {
        height: auto;
        margin: 1 2;
        padding: 1 2;
        border: solid $primary;
    }

    #button-bar {
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        from mediascribe.tui.screens.welcome import WelcomeScreen
        yield WelcomeScreen()

    def on_mount(self) -> None:
        self.title = "mediascribe"
        self.sub_title = f"v{__version__}"

    def action_help(self) -> None:
        self.push_screen("help")
