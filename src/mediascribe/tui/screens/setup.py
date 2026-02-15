"""Setup screen — API key entry and validation."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from mediascribe.core.config import _default_config_dir


class SetupScreen(Screen):
    """API key onboarding — enter and validate keys, save to config."""

    DEFAULT_CSS = """
    SetupScreen {
        align: center middle;
    }
    SetupScreen #setup-box {
        width: 72;
        height: auto;
        border: round $accent;
        padding: 2 4;
    }
    SetupScreen #setup-title {
        text-align: center;
        text-style: bold;
        margin: 0 0 1 0;
    }
    SetupScreen #setup-desc {
        color: $text-muted;
        margin: 0 0 2 0;
    }
    SetupScreen .field-label {
        margin: 1 0 0 0;
    }
    SetupScreen Input {
        margin: 0 0 1 0;
    }
    SetupScreen #status-msg {
        margin: 1 0;
        text-align: center;
    }
    SetupScreen #save-btn {
        margin: 1 0 0 0;
        width: 100%;
    }
    SetupScreen #skip-btn {
        width: 100%;
    }
    """

    BINDINGS = [
        ("escape", "skip", "Skip"),
    ]

    def compose(self) -> ComposeResult:
        with Center(), Vertical(id="setup-box"):
                yield Label("API Key Setup", id="setup-title")
                yield Label(
                    "Enter your OpenAI API key for transcription (API mode) and translation.\n"
                    "The key is saved locally to ~/.config/mediascribe/.env",
                    id="setup-desc",
                )

                yield Label("OpenAI API Key", classes="field-label")
                yield Input(
                    placeholder="sk-...",
                    password=True,
                    id="openai-key-input",
                )

                yield Label(
                    "HuggingFace Token (optional, for diarization)",
                    classes="field-label",
                )
                yield Input(
                    placeholder="hf_...",
                    password=True,
                    id="hf-token-input",
                )

                yield Static("", id="status-msg")

                with Center():
                    yield Button("Save & Continue", variant="primary", id="save-btn")
                    yield Button("Skip for now", variant="default", id="skip-btn")

    @on(Button.Pressed, "#save-btn")
    def _save_keys(self) -> None:
        openai_key = self.query_one("#openai-key-input", Input).value.strip()
        hf_token = self.query_one("#hf-token-input", Input).value.strip()

        if not openai_key:
            self.query_one("#status-msg", Static).update(
                "[yellow]Please enter an OpenAI API key, or skip.[/yellow]"
            )
            return

        self._do_save(openai_key, hf_token)

    @work(thread=True)
    def _do_save(self, openai_key: str, hf_token: str) -> None:
        """Save API keys to .env file and optionally validate."""
        config_dir = _default_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        env_file = config_dir / ".env"

        lines: list[str] = []
        if openai_key:
            lines.append(f"MEDIASCRIBE_OPENAI_API_KEY={openai_key}")
        if hf_token:
            lines.append(f"MEDIASCRIBE_HUGGINGFACE_TOKEN={hf_token}")

        env_file.write_text("\n".join(lines) + "\n")

        # Try a quick validation
        valid = False
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            client.models.list()
            valid = True
        except Exception:
            pass

        if valid:
            self.app.call_from_thread(
                self.query_one("#status-msg", Static).update,
                "[green]✓ API key validated! Saved to config.[/green]",
            )
            # Navigate after a brief pause
            import time
            time.sleep(0.5)
            self.app.call_from_thread(self.app.push_screen, "picker")
        else:
            self.app.call_from_thread(
                self.query_one("#status-msg", Static).update,
                "[yellow]Key saved but could not validate (network issue or invalid key).\n"
                "You can continue — the key will be used when running pipelines.[/yellow]",
            )

    @on(Button.Pressed, "#skip-btn")
    def action_skip(self) -> None:
        self.app.push_screen("picker")
