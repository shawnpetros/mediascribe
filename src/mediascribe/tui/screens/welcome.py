"""Welcome screen — startup, health checks, and navigation."""

from __future__ import annotations

import shutil

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from mediascribe import __version__


class WelcomeScreen(Screen):
    """Initial screen shown on TUI launch.

    Checks for ffmpeg, API key status, and provides
    navigation to file picker or setup.
    """

    DEFAULT_CSS = """
    WelcomeScreen {
        align: center middle;
    }

    #welcome-box {
        width: 70;
        height: auto;
        border: double $accent;
        padding: 1 2;
    }

    #title-label {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
    }

    #version-label {
        text-align: center;
        color: $text-muted;
        width: 100%;
        margin-bottom: 1;
    }

    #status-list {
        margin: 1 0;
        height: auto;
    }

    .status-item {
        margin-left: 2;
    }

    #nav-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #nav-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="welcome-box"):
                yield Label("mediascribe", id="title-label")
                yield Label(
                    f"v{__version__} — Transcribe, translate, and analyze media",
                    id="version-label",
                )
                yield Static(id="status-list")
                with Center(id="nav-buttons"):
                    yield Button("Get Started", variant="primary", id="btn-start")
                    yield Button("Setup", variant="default", id="btn-setup")
                    yield Button("Quit", variant="error", id="btn-quit")
        yield Footer()

    def on_mount(self) -> None:
        status = self._check_status()
        self.query_one("#status-list", Static).update(status)

    def _check_status(self) -> str:
        lines = []

        ffmpeg_ok = shutil.which("ffmpeg") is not None
        icon = "[green]✓[/green]" if ffmpeg_ok else "[red]✗[/red]"
        lines.append(f"  {icon} ffmpeg: {'found' if ffmpeg_ok else 'NOT FOUND'}")

        ffprobe_ok = shutil.which("ffprobe") is not None
        icon = "[green]✓[/green]" if ffprobe_ok else "[red]✗[/red]"
        lines.append(f"  {icon} ffprobe: {'found' if ffprobe_ok else 'NOT FOUND'}")

        import os
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MEDIASCRIBE_OPENAI_API_KEY")
        icon = "[green]✓[/green]" if api_key else "[yellow]○[/yellow]"
        lines.append(f"  {icon} OpenAI API key: {'configured' if api_key else 'not set'}")

        hf_token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("MEDIASCRIBE_HUGGINGFACE_TOKEN")
        icon = "[green]✓[/green]" if hf_token else "[dim]○[/dim]"
        lines.append(f"  {icon} HuggingFace token: {'configured' if hf_token else 'not set (optional)'}")

        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-quit":
            self.app.exit()
        elif event.button.id == "btn-setup":
            from mediascribe.tui.screens.setup import SetupScreen
            self.app.push_screen(SetupScreen())
        elif event.button.id == "btn-start":
            from mediascribe.tui.screens.picker import PickerScreen
            self.app.push_screen(PickerScreen())
