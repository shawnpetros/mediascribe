"""Setup screen — API key entry and validation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static


class SetupScreen(Screen):
    """API key configuration screen.

    Allows entering and validating OpenAI API key and
    optional HuggingFace token for diarization.
    """

    DEFAULT_CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-box {
        width: 70;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }

    .field-label {
        margin-top: 1;
        text-style: bold;
    }

    .field-hint {
        color: $text-muted;
        margin-bottom: 0;
    }

    #status-msg {
        margin-top: 1;
        height: auto;
    }

    #setup-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #setup-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="setup-box"):
                yield Label("[bold]Setup[/bold]")
                yield Label("OpenAI API Key", classes="field-label")
                yield Label("Required for transcription (API mode) and translation", classes="field-hint")
                yield Input(placeholder="sk-...", password=True, id="openai-key")
                yield Label("HuggingFace Token (optional)", classes="field-label")
                yield Label("For speaker diarization — requires pyannote model access", classes="field-hint")
                yield Input(placeholder="hf_...", password=True, id="hf-token")
                yield Static("", id="status-msg")
                with Center(id="setup-buttons"):
                    yield Button("Save", variant="primary", id="btn-save")
                    yield Button("Back", variant="default", id="btn-back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-save":
            self._save_config()

    def _save_config(self) -> None:
        from mediascribe.core.config import _default_config_dir

        openai_key = self.query_one("#openai-key", Input).value.strip()
        hf_token = self.query_one("#hf-token", Input).value.strip()

        config_dir = _default_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"

        lines: list[str] = []
        if openai_key:
            lines.append(f'openai_api_key = "{openai_key}"')
        if hf_token:
            lines.append(f'huggingface_token = "{hf_token}"')

        if lines:
            existing = ""
            if config_file.exists():
                existing = config_file.read_text(encoding="utf-8")
            for line in lines:
                key = line.split("=")[0].strip()
                import re
                existing = re.sub(rf'^{key}\s*=.*$', line, existing, flags=re.MULTILINE)
                if key not in existing:
                    existing += f"\n{line}"
            config_file.write_text(existing.strip() + "\n", encoding="utf-8")

            status = self.query_one("#status-msg", Static)
            status.update(f"[green]Saved to {config_file}[/green]")
        else:
            status = self.query_one("#status-msg", Static)
            status.update("[yellow]No values to save[/yellow]")
