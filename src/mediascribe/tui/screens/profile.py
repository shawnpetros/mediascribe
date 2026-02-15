"""Profile selection + configuration screen."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Label,
    Select,
    Static,
    TextArea,
)

from mediascribe.core.hardware import detect_hardware
from mediascribe.core.profiles import get_all_profiles

# Common languages for source/target selection
LANGUAGES = [
    ("Auto-detect", ""),
    ("English", "en"),
    ("Japanese", "ja"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Chinese", "zh"),
    ("Korean", "ko"),
    ("Portuguese", "pt"),
    ("Italian", "it"),
    ("Russian", "ru"),
    ("Arabic", "ar"),
    ("Hindi", "hi"),
]


class ProfileScreen(Screen):
    """Configure pipeline settings — profile, languages, output formats."""

    DEFAULT_CSS = """
    ProfileScreen {
        layout: vertical;
    }
    ProfileScreen #profile-header {
        dock: top;
        height: 3;
        padding: 1 2;
        text-style: bold;
        background: $primary-background;
    }
    ProfileScreen #config-scroll {
        height: 1fr;
        margin: 0 2;
    }
    ProfileScreen .section-title {
        text-style: bold;
        margin: 1 0 0 0;
        color: $accent;
    }
    ProfileScreen .field-label {
        margin: 1 0 0 0;
    }
    ProfileScreen Select {
        margin: 0 0 1 0;
    }
    ProfileScreen Input {
        margin: 0 0 1 0;
    }
    ProfileScreen TextArea {
        height: 5;
        margin: 0 0 1 0;
    }
    ProfileScreen #output-formats {
        layout: horizontal;
        height: 3;
    }
    ProfileScreen #hw-info {
        margin: 1 0;
        padding: 1;
        border: round $surface-lighten-2;
        color: $text-muted;
    }
    ProfileScreen #button-row {
        dock: bottom;
        height: 3;
        padding: 0 2;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Pipeline Configuration", id="profile-header")

        with VerticalScroll(id="config-scroll"):
            # Profile selection
            yield Label("Profile", classes="section-title")
            profiles = get_all_profiles()
            profile_options = [(f"{p.name} — {p.description}", p.name) for p in profiles.values()]
            profile_options.insert(0, ("None (custom settings)", ""))
            yield Select(profile_options, value="", id="profile-select")

            # Languages
            yield Label("Languages", classes="section-title")

            yield Label("Source Language", classes="field-label")
            source_opts = [(name, code) for name, code in LANGUAGES]
            yield Select(source_opts, value="", id="source-lang")

            yield Label("Target Language (leave empty to skip translation)", classes="field-label")
            target_opts = [("No translation", "")] + [
                (name, code) for name, code in LANGUAGES if code
            ]
            yield Select(target_opts, value="", id="target-lang")

            # Transcription
            yield Label("Transcription", classes="section-title")

            yield Label("Mode", classes="field-label")
            yield Select(
                [("Auto", "auto"), ("Local (faster-whisper)", "local"), ("API (OpenAI)", "api")],
                value="auto",
                id="transcription-mode",
            )

            yield Label("Whisper Model", classes="field-label")
            yield Select(
                [
                    ("large-v3 (best quality)", "large-v3"),
                    ("medium (balanced)", "medium"),
                    ("small (fast)", "small"),
                    ("tiny (fastest)", "tiny"),
                ],
                value="large-v3",
                id="whisper-model",
            )

            # Translation
            yield Label("Translation", classes="section-title")

            yield Label("Translation Model", classes="field-label")
            yield Select(
                [("gpt-4.1 (best)", "gpt-4.1"), ("gpt-4.1-mini (faster)", "gpt-4.1-mini")],
                value="gpt-4.1",
                id="translation-model",
            )

            yield Checkbox(
                "Enable review pass (second AI quality check)",
                value=True,
                id="review-pass",
            )

            # Custom instructions
            yield Label("Custom Instructions", classes="field-label")
            yield TextArea(
                "",
                id="custom-instructions",
            )

            # Output formats
            yield Label("Output Formats", classes="section-title")
            with Horizontal(id="output-formats"):
                yield Checkbox("SRT", value=True, id="fmt-srt")
                yield Checkbox("VTT", value=False, id="fmt-vtt")
                yield Checkbox("TXT", value=False, id="fmt-txt")
                yield Checkbox("JSON", value=False, id="fmt-json")

            # Hardware info
            yield Static("Detecting hardware...", id="hw-info")

        with Horizontal(id="button-row"):
            yield Button("← Back", variant="default", id="back-btn")
            yield Button("Run Pipeline →", variant="success", id="run-btn")

    def on_mount(self) -> None:
        self._detect_hardware()

    def _detect_hardware(self) -> None:
        """Show hardware info and ETA estimate."""
        try:
            hw = detect_hardware()
            lines = [
                f"CPU: {hw.cpu_brand} ({hw.cpu_count} cores)",
                f"RAM: {hw.ram_gb:.1f} GB",
                f"GPU: {hw.gpu_name or 'None detected'}",
                f"Recommended concurrency: {hw.recommended_concurrency}",
                f"Recommended compute type: {hw.recommended_compute_type}",
            ]

            # Estimate time if we have files
            picker = self.app.get_screen("picker")
            if hasattr(picker, "selected_files") and picker.selected_files:
                n_files = len(picker.selected_files)
                lines.append(f"\nFiles to process: {n_files}")

            self.query_one("#hw-info", Static).update("\n".join(lines))
        except Exception:
            self.query_one("#hw-info", Static).update("Hardware detection unavailable")

    @on(Select.Changed, "#profile-select")
    def _on_profile_change(self, event: Select.Changed) -> None:
        """Apply profile settings when a profile is selected."""
        profile_name = event.value
        if not profile_name:
            return

        profiles = get_all_profiles()
        profile = profiles.get(profile_name)
        if not profile:
            return

        s = profile.settings

        # Apply settings to form fields
        if "transcription_mode" in s:
            self.query_one("#transcription-mode", Select).value = s["transcription_mode"]
        if "whisper_model" in s:
            self.query_one("#whisper-model", Select).value = s["whisper_model"]
        if "enable_review_pass" in s:
            self.query_one("#review-pass", Checkbox).value = s["enable_review_pass"]
        if "output_formats" in s:
            fmts = s["output_formats"]
            self.query_one("#fmt-srt", Checkbox).value = "srt" in fmts
            self.query_one("#fmt-vtt", Checkbox).value = "vtt" in fmts
            self.query_one("#fmt-txt", Checkbox).value = "txt" in fmts
            self.query_one("#fmt-json", Checkbox).value = "json" in fmts

    def _collect_settings(self) -> dict:
        """Collect all settings from form fields."""
        formats = []
        if self.query_one("#fmt-srt", Checkbox).value:
            formats.append("srt")
        if self.query_one("#fmt-vtt", Checkbox).value:
            formats.append("vtt")
        if self.query_one("#fmt-txt", Checkbox).value:
            formats.append("txt")
        if self.query_one("#fmt-json", Checkbox).value:
            formats.append("json")

        if not formats:
            formats = ["srt"]  # default fallback

        return {
            "source_language": self.query_one("#source-lang", Select).value or None,
            "target_language": self.query_one("#target-lang", Select).value or None,
            "transcription_mode": self.query_one("#transcription-mode", Select).value,
            "whisper_model": self.query_one("#whisper-model", Select).value,
            "translation_model": self.query_one("#translation-model", Select).value,
            "enable_review_pass": self.query_one("#review-pass", Checkbox).value,
            "custom_instructions": self.query_one("#custom-instructions", TextArea).text,
            "output_formats": formats,
        }

    @on(Button.Pressed, "#run-btn")
    def _start_pipeline(self) -> None:
        settings = self._collect_settings()
        # Store settings on the app for the pipeline screen to use
        self.app._pipeline_settings = settings  # type: ignore[attr-defined]
        self.app.push_screen("pipeline")

    @on(Button.Pressed, "#back-btn")
    def action_back(self) -> None:
        self.app.pop_screen()
