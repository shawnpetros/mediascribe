"""Main Textual TUI application for mediascribe.

Screen flow:
    Welcome → [Setup] → Picker → Profile → Pipeline → Results
"""

from __future__ import annotations

from textual.app import App

from mediascribe.tui.screens.picker import PickerScreen
from mediascribe.tui.screens.pipeline import PipelineScreen
from mediascribe.tui.screens.profile import ProfileScreen
from mediascribe.tui.screens.results import ResultsScreen
from mediascribe.tui.screens.setup import SetupScreen
from mediascribe.tui.screens.welcome import WelcomeScreen


class MediascribeApp(App):
    """The mediascribe TUI application."""

    TITLE = "mediascribe"
    SUB_TITLE = "Transcribe, translate, and analyze media"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    SCREENS = {
        "welcome": WelcomeScreen,
        "setup": SetupScreen,
        "picker": PickerScreen,
        "profile": ProfileScreen,
        "pipeline": PipelineScreen,
        "results": ResultsScreen,
    }

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Start on the welcome screen."""
        self.push_screen("welcome")


def run_tui() -> None:
    """Entry point to launch the TUI application."""
    app = MediascribeApp()
    app.run()
