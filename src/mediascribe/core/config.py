"""Application configuration and user config persistence.

Config hierarchy (highest priority wins):
  1. CLI flags / TUI input (explicit runtime overrides)
  2. Environment variables (MEDIASCRIBE_*)
  3. .env file in working directory
  4. User config (~/.config/mediascribe/config.toml)
  5. Built-in defaults (below)
"""

from __future__ import annotations

import json
import os
import tomllib
from contextlib import suppress
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_FILENAME = "config.toml"
_NONE_SENTINELS = {"none", "null", ""}


def _default_config_dir() -> Path:
    """XDG-compliant config directory."""
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

    # API keys
    openai_api_key: SecretStr | None = None
    huggingface_token: SecretStr | None = None

    # Transcription
    transcription_mode: Literal["local", "api", "auto"] = "auto"
    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_compute: str = "int8"
    chunk_duration_sec: int = 180
    chunk_overlap_sec: int = 15
    word_timestamps: bool = True

    # Translation
    translation_model: str = "gpt-4.1"
    translation_profile: Literal["general", "anime", "podcast", "meeting"] = "general"
    translation_batch_size: int = 15
    enable_review_pass: bool = True
    custom_instructions: str = ""

    # Source/target language
    source_language: str | None = None
    target_language: str | None = None

    # Processing
    max_concurrency: int = 1
    output_dir: Path = Path("./output")
    output_formats: list[str] = ["srt"]

    # Subtitle timing
    max_subtitle_duration_sec: float = 7.0
    min_gap_sec: float = 0.15
    chars_per_second: float = 5.0

    # Paths
    config_dir: Path = _default_config_dir()

    def ensure_dirs(self) -> None:
        """Create config and output directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def config_file_path(config_dir: Path | None = None) -> Path:
    """Return the resolved user config TOML path."""
    return (config_dir or _default_config_dir()) / CONFIG_FILENAME


def list_setting_keys() -> list[str]:
    """Return all valid settings keys."""
    return sorted(MediascribeSettings.model_fields.keys())


def is_valid_setting_key(key: str) -> bool:
    """Return True if key maps to a settings field."""
    return key in MediascribeSettings.model_fields


def _unwrap_optional(annotation: Any) -> Any:
    """If Optional[T], return T; otherwise return annotation unchanged."""
    origin = get_origin(annotation)
    if origin not in (UnionType, Union):
        return annotation

    args = [a for a in get_args(annotation) if a is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


def _annotation_is_secret(annotation: Any) -> bool:
    annotation = _unwrap_optional(annotation)
    if annotation is SecretStr:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    return any(_annotation_is_secret(arg) for arg in get_args(annotation))


def is_secret_setting(key: str) -> bool:
    """Return True if key represents secret config."""
    field = MediascribeSettings.model_fields.get(key)
    if not field:
        return False
    return _annotation_is_secret(field.annotation)


def _parse_bool(raw_value: str) -> bool:
    v = raw_value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw_value!r}")


def _parse_value(annotation: Any, raw_value: str) -> Any:
    annotation = _unwrap_optional(annotation)
    raw = raw_value.strip()

    if raw.lower() in _NONE_SENTINELS:
        return None

    origin = get_origin(annotation)
    if origin is Literal:
        valid = tuple(get_args(annotation))
        if raw not in valid:
            raise ValueError(f"Expected one of {valid}, got {raw!r}")
        return raw

    if annotation is bool:
        return _parse_bool(raw)
    if annotation is int:
        return int(raw)
    if annotation is float:
        return float(raw)
    if annotation is Path:
        return Path(raw)
    if annotation is SecretStr:
        return raw
    if annotation is str:
        return raw

    if origin is list:
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("JSON list required for list value")
            return [str(item) for item in parsed]
        return [part.strip() for part in raw.split(",") if part.strip()]

    return raw


def parse_setting_value(key: str, raw_value: str) -> Any:
    """Parse a CLI-provided string value according to key's field type."""
    field = MediascribeSettings.model_fields.get(key)
    if field is None:
        raise KeyError(f"Unknown setting: {key}")
    return _parse_value(field.annotation, raw_value)


def _plain_value(value: Any) -> Any:
    """Convert rich Python values to TOML-safe primitives."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_plain_value(v) for v in value]
    return value


def _toml_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _to_toml_literal(value: Any) -> str:
    value = _plain_value(value)

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _toml_quote(value)
    if isinstance(value, list):
        return "[" + ", ".join(_to_toml_literal(v) for v in value) + "]"
    raise TypeError(f"Unsupported config value type: {type(value)!r}")


def load_user_config(path: Path | None = None) -> dict[str, Any]:
    """Load persisted user config from TOML (unknown keys ignored)."""
    cfg_path = path or config_file_path()
    if not cfg_path.exists():
        return {}

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    valid_keys = set(MediascribeSettings.model_fields.keys())
    return {k: v for k, v in data.items() if k in valid_keys}


def save_user_config(values: dict[str, Any], path: Path | None = None) -> Path:
    """Write user config to TOML, removing keys set to None."""
    cfg_path = path or config_file_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for key in sorted(values.keys()):
        if not is_valid_setting_key(key):
            continue
        value = _plain_value(values[key])
        if value is None:
            continue
        lines.append(f"{key} = {_to_toml_literal(value)}")

    content = "\n".join(lines) + ("\n" if lines else "")
    cfg_path.write_text(content, encoding="utf-8")
    with suppress(OSError):
        cfg_path.chmod(0o600)
    return cfg_path


def _environment_setting_keys() -> set[str]:
    """Return settings keys explicitly set via env or .env."""
    keys: set[str] = set()
    valid_keys = set(MediascribeSettings.model_fields.keys())

    for env_name in os.environ:
        if not env_name.startswith("MEDIASCRIBE_"):
            continue
        key = env_name.removeprefix("MEDIASCRIBE_").lower()
        if key in valid_keys:
            keys.add(key)

    dotenv_path = Path(".env")
    if dotenv_path.exists():
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue
            env_name = line.split("=", 1)[0].strip()
            if not env_name.startswith("MEDIASCRIBE_"):
                continue
            key = env_name.removeprefix("MEDIASCRIBE_").lower()
            if key in valid_keys:
                keys.add(key)

    return keys


def load_settings(overrides: dict[str, Any] | None = None) -> MediascribeSettings:
    """Load effective settings from config + environment + overrides."""
    merged = load_user_config()

    # Env and .env must outrank persisted user config.
    for key in _environment_setting_keys():
        merged.pop(key, None)

    if overrides:
        for key, value in overrides.items():
            if key in MediascribeSettings.model_fields and value is not None:
                merged[key] = value

    return MediascribeSettings(**merged)
