"""Welcome screen — app title, dependency check, get started."""

from __future__ import annotations

import shutil

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from mediascribe import __version__


class WelcomeScreen(Screen):
    """First screen shown on launch — branding + dependency check."""

    DEFAULT_CSS = """
    WelcomeScreen {
        align: center middle;
    }
    WelcomeScreen #welcome-box {
        width: 64;
        height: auto;
        border: double $accent;
        padding: 2 4;
    }
    WelcomeScreen #app-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }
    WelcomeScreen #app-subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 2 0;
    }
    WelcomeScreen .dep-ok {
        color: $success;
    }
    WelcomeScreen .dep-missing {
        color: $error;
    }
    WelcomeScreen .dep-section {
        margin: 1 0;
    }
    WelcomeScreen #get-started {
        margin: 2 0 0 0;
        width: 100%;
    }
    WelcomeScreen #version-label {
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        ("enter", "start", "Get Started"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Center(), Vertical(id="welcome-box"):
            yield Label("mediascribe", id="app-title")
            yield Label(
                "Transcribe, translate, and analyze audio/video media",
                id="app-subtitle",
            )
            yield Static(id="dep-status")
            with Center():
                yield Button("Get Started", variant="primary", id="get-started")
            yield Label(f"v{__version__}", id="version-label")

    def on_mount(self) -> None:
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check for required external tools and API keys."""
        lines: list[str] = []

        # Check ffmpeg
        ffmpeg_path = shutil.which("ffmpeg")
        ffprobe_path = shutil.which("ffprobe")
        if ffmpeg_path and ffprobe_path:
            lines.append("[green]  ✓ ffmpeg found[/green]")
        else:
            missing = []
            if not ffmpeg_path:
                missing.append("ffmpeg")
            if not ffprobe_path:
                missing.append("ffprobe")
            lines.append(f"[red]  ✗ Missing: {', '.join(missing)}[/red]")

        # Check OpenAI API key
        from mediascribe.core.config import MediascribeSettings

        try:
            settings = MediascribeSettings()
            has_key = settings.openai_api_key is not None
        except Exception:
            has_key = False

        if has_key:
            lines.append("[green]  ✓ OpenAI API key configured[/green]")
        else:
            lines.append(
                "[yellow]  ○ OpenAI API key not set"
                " (needed for API mode / translation)[/yellow]"
            )

        self.query_one("#dep-status", Static).update("\n".join(lines))

    @on(Button.Pressed, "#get-started")
    def action_start(self) -> None:
        """Move to the next screen."""
        # Check if API key is configured; if not, go to setup
        from mediascribe.core.config import MediascribeSettings

        try:
            settings = MediascribeSettings()
            has_key = settings.openai_api_key is not None
        except Exception:
            has_key = False

        if has_key:
            self.app.push_screen("picker")
        else:
            self.app.push_screen("setup")

    def action_quit(self) -> None:
        self.app.exit()
