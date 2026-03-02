"""Application configuration via pydantic-settings.

Config hierarchy (highest priority wins):
  1. CLI flags / TUI input (passed directly)
  2. Environment variables (MEDIASCRIBE_*)
  3. .env file in working directory
  4. User config (~/.config/mediascribe/config.toml)
  5. Built-in defaults (below)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

TranscriptionMode = Literal["local", "api", "auto"]


def _default_config_dir() -> Path:
    """XDG-compliant config directory."""
    import os

    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "mediascribe"


class MediascribeSettings(BaseSettings):
    """All application settings, loadable from env / .env / config file."""

    model_config = SettingsConfigDict(
        env_prefix="MEDIASCRIBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API Keys ─────────────────────────────────────────
    openai_api_key: SecretStr | None = None
    huggingface_token: SecretStr | None = None

    # ── Transcription ────────────────────────────────────
    transcription_mode: TranscriptionMode = "auto"
    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_compute: str = "int8"
    chunk_duration_sec: int = 180
    chunk_overlap_sec: int = 15
    word_timestamps: bool = True

    # ── Translation ──────────────────────────────────────
    translation_model: str = "gpt-4.1"
    translation_batch_size: int = 15
    enable_review_pass: bool = True
    custom_instructions: str = ""
    profile: str = "general"

    # ── Source / Target ──────────────────────────────────
    source_language: str | None = None  # None = auto-detect
    target_language: str | None = None  # None = skip translation

    # ── Processing ───────────────────────────────────────
    max_concurrency: int = 1
    output_dir: Path = Path("./output")
    output_formats: list[str] = ["srt"]

    # ── Subtitle Timing ──────────────────────────────────
    max_subtitle_duration_sec: float = 7.0
    min_gap_sec: float = 0.15
    chars_per_second: float = 5.0  # for duration cap heuristic

    # ── Paths ────────────────────────────────────────────
    config_dir: Path = _default_config_dir()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Add TOML config file as a settings source.

        Priority (highest first):
          1. init kwargs (CLI flags)
          2. Environment variables (MEDIASCRIBE_*)
          3. .env file
          4. ~/.config/mediascribe/config.toml
          5. Built-in defaults
        """
        toml_path = _default_config_dir() / "config.toml"
        toml_source = TomlConfigSettingsSource(
            settings_cls,
            toml_file=toml_path if toml_path.exists() else None,
        )
        return init_settings, env_settings, dotenv_settings, toml_source, file_secret_settings

    def ensure_dirs(self) -> None:
        """Create config and output directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
