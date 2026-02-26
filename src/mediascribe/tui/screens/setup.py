"""Setup screen — API key configuration and validation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static


class SetupScreen(Screen):
    """API key entry and validation screen."""

    DEFAULT_CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-box {
        width: 64;
        height: auto;
        padding: 1 2;
        border: tall $primary;
    }

    #setup-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    .field-label {
        margin-top: 1;
    }

    #setup-status {
        margin-top: 1;
    }

    #setup-actions {
        margin-top: 1;
        layout: horizontal;
    }

    #setup-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-box"):
            yield Label("API Key Setup", id="setup-title")
            yield Label("OpenAI API Key (required for translation):", classes="field-label")
            yield Input(placeholder="sk-...", id="openai-key", password=True)
            yield Label("HuggingFace Token (optional, for diarization):", classes="field-label")
            yield Input(placeholder="hf_...", id="hf-token", password=True)
            yield Static(id="setup-status")
            with Vertical(id="setup-actions"):
                yield Button("Save & Continue", variant="primary", id="btn-save")
                yield Button("Back", variant="default", id="btn-back")

    def on_mount(self) -> None:
        from mediascribe.core.config import MediascribeSettings

        try:
            settings = MediascribeSettings()
            if settings.openai_api_key:
                self.query_one("#openai-key", Input).value = "***configured***"
            if settings.huggingface_token:
                self.query_one("#hf-token", Input).value = "***configured***"
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save_keys()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def _save_keys(self) -> None:
        openai_key = self.query_one("#openai-key", Input).value.strip()
        hf_token = self.query_one("#hf-token", Input).value.strip()
        status = self.query_one("#setup-status", Static)

        if openai_key and openai_key != "***configured***":
            from mediascribe.core.config import _default_config_dir

            config_dir = _default_config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.toml"

            lines: list[str] = []
            if config_file.exists():
                for line in config_file.read_text().splitlines():
                    if not line.strip().startswith(
                        "openai_api_key"
                    ) and not line.strip().startswith("huggingface_token"):
                        lines.append(line)

            lines.append(f'openai_api_key = "{openai_key}"')
            if hf_token and hf_token != "***configured***":
                lines.append(f'huggingface_token = "{hf_token}"')

            config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            status.update("[green]Keys saved! You can now proceed.[/green]")
        else:
            status.update("[yellow]No changes made.[/yellow]")
