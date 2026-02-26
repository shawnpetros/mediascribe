"""Welcome screen — startup checks, version info, navigation."""

from __future__ import annotations

import shutil

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from mediascribe import __version__


class WelcomeScreen(Screen):
    """First screen shown on launch. Checks dependencies and offers navigation."""

    DEFAULT_CSS = """
    WelcomeScreen {
        align: center middle;
    }

    #welcome-box {
        width: 64;
        height: auto;
        padding: 1 2;
        border: tall $primary;
    }

    #welcome-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #welcome-version {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #checks {
        margin: 1 0;
    }

    .check-line {
        margin-left: 2;
    }

    #welcome-actions {
        margin-top: 1;
        height: auto;
    }

    #welcome-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome-box"):
            yield Label("mediascribe", id="welcome-title")
            yield Label(f"v{__version__}", id="welcome-version")
            yield Static(id="checks")
            with Center(id="welcome-actions"):
                yield Button("Get Started", variant="primary", id="btn-start")
                yield Button("Setup API Keys", variant="default", id="btn-setup")
                yield Button("Quit", variant="error", id="btn-quit")

    def on_mount(self) -> None:
        checks = self._run_checks()
        self.query_one("#checks", Static).update(checks)

    def _run_checks(self) -> str:
        lines = []

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            lines.append("[green]OK[/green]  ffmpeg found")
        else:
            lines.append("[red]!!![/red]  ffmpeg not found — required for audio processing")

        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            lines.append("[green]OK[/green]  ffprobe found")
        else:
            lines.append("[red]!!![/red]  ffprobe not found — required for media detection")

        from mediascribe.core.config import MediascribeSettings
        try:
            settings = MediascribeSettings()
            if settings.openai_api_key:
                lines.append("[green]OK[/green]  OpenAI API key configured")
            else:
                lines.append("[yellow]--[/yellow]  OpenAI API key not set")

            if settings.huggingface_token:
                lines.append("[green]OK[/green]  HuggingFace token configured")
            else:
                lines.append("[dim]--[/dim]  HuggingFace token not set (optional)")
        except Exception:
            lines.append("[yellow]--[/yellow]  Could not load settings")

        try:
            from mediascribe.core.hardware import detect_hardware
            hw = detect_hardware()
            lines.append(f"[dim]    CPU: {hw.cpu_count} cores, RAM: {hw.ram_gb:.1f} GB[/dim]")
            if hw.gpu_name:
                lines.append(f"[dim]    GPU: {hw.gpu_name}[/dim]")
        except Exception:
            pass

        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            from mediascribe.tui.screens.picker import PickerScreen
            self.app.push_screen(PickerScreen())
        elif event.button.id == "btn-setup":
            from mediascribe.tui.screens.setup import SetupScreen
            self.app.push_screen(SetupScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()
