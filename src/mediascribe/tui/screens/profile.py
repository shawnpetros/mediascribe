"""Profile/config screen — configure pipeline settings before running."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static


class ProfileScreen(Screen):
    """Pipeline configuration screen — profile, languages, options."""

    DEFAULT_CSS = """
    ProfileScreen {
        align: center middle;
    }

    #profile-box {
        width: 72;
        height: auto;
        padding: 1 2;
        border: tall $primary;
    }

    #profile-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    .config-row {
        height: 3;
        margin-bottom: 0;
    }

    .config-label {
        width: 24;
        padding-top: 1;
    }

    .config-input {
        width: 1fr;
    }

    #file-summary {
        color: $text-muted;
        margin-bottom: 1;
    }

    #profile-actions {
        margin-top: 1;
        layout: horizontal;
    }

    #profile-actions Button {
        margin: 0 1;
    }

    #format-checks {
        layout: horizontal;
        height: 3;
    }

    #format-checks Checkbox {
        margin-right: 2;
    }
    """

    def __init__(self, files: list[Path]) -> None:
        super().__init__()
        self.files = files

    def compose(self) -> ComposeResult:
        profiles = [
            ("General", "general"),
            ("Anime", "anime"),
            ("Podcast", "podcast"),
            ("Meeting", "meeting"),
        ]

        with Vertical(id="profile-box"):
            yield Label("Pipeline Configuration", id="profile-title")
            yield Static(
                f"Processing {len(self.files)} file(s)",
                id="file-summary",
            )

            with Horizontal(classes="config-row"):
                yield Label("Profile:", classes="config-label")
                yield Select(profiles, value="general", id="sel-profile", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Label("Translate to:", classes="config-label")
                yield Input(
                    placeholder="e.g., en (leave empty for none)",
                    id="inp-target",
                    classes="config-input",
                )

            with Horizontal(classes="config-row"):
                yield Label("Source language:", classes="config-label")
                yield Input(placeholder="auto-detect", id="inp-source", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Label("Output formats:", classes="config-label")
                with Horizontal(id="format-checks"):
                    yield Checkbox("SRT", value=True, id="chk-srt")
                    yield Checkbox("VTT", value=False, id="chk-vtt")
                    yield Checkbox("TXT", value=False, id="chk-txt")
                    yield Checkbox("JSON", value=False, id="chk-json")

            yield Checkbox("Enable review pass", value=True, id="chk-review")
            yield Checkbox("Enable speaker diarization", value=False, id="chk-diarize")
            yield Checkbox("Enable AI analysis", value=False, id="chk-analyze")

            with Horizontal(classes="config-row"):
                yield Label("Custom instructions:", classes="config-label")
                yield Input(placeholder="(optional)", id="inp-custom", classes="config-input")

            with Horizontal(id="profile-actions"):
                yield Button("Back", variant="default", id="btn-back")
                yield Button("Run Pipeline", variant="primary", id="btn-run")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-run":
            config = self._gather_config()
            from mediascribe.tui.screens.pipeline import PipelineScreen

            self.app.push_screen(PipelineScreen(self.files, config))

    def _gather_config(self) -> dict:
        formats = []
        if self.query_one("#chk-srt", Checkbox).value:
            formats.append("srt")
        if self.query_one("#chk-vtt", Checkbox).value:
            formats.append("vtt")
        if self.query_one("#chk-txt", Checkbox).value:
            formats.append("txt")
        if self.query_one("#chk-json", Checkbox).value:
            formats.append("json")

        profile_sel = self.query_one("#sel-profile", Select)

        return {
            "profile": str(profile_sel.value) if profile_sel.value != Select.BLANK else "general",
            "target_language": self.query_one("#inp-target", Input).value.strip() or None,
            "source_language": self.query_one("#inp-source", Input).value.strip() or None,
            "output_formats": formats or ["srt"],
            "enable_review": self.query_one("#chk-review", Checkbox).value,
            "enable_diarize": self.query_one("#chk-diarize", Checkbox).value,
            "enable_analyze": self.query_one("#chk-analyze", Checkbox).value,
            "custom_instructions": self.query_one("#inp-custom", Input).value.strip(),
        }
