"""Profile system — named config presets loaded from TOML files.

Profiles are stored as TOML files in ``~/.config/mediascribe/profiles/``.
Four built-in profiles ship with the package; users can create custom
profiles by adding ``.toml`` files to the profiles directory.

A profile can override any MediascribeSettings field, plus provide
custom_instructions for the translation prompt.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Profile:
    """A named configuration preset."""

    name: str
    description: str = ""
    overrides: dict[str, Any] = field(default_factory=dict)

    def apply(self, settings_kwargs: dict[str, Any]) -> dict[str, Any]:
        """Merge profile overrides into a settings kwargs dict.

        CLI flags take priority over profile values — only set keys that
        are not already explicitly provided.
        """
        merged = dict(self.overrides)
        merged.update({k: v for k, v in settings_kwargs.items() if v is not None})
        return merged


BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "general": {
        "description": "General-purpose subtitle translation",
    },
    "anime": {
        "description": "Anime/animation subtitling with character-aware translation",
        "overrides": {
            "transcription_mode": "local",
            "whisper_model": "large-v3",
            "enable_review_pass": True,
            "output_formats": ["srt", "vtt"],
        },
    },
    "podcast": {
        "description": "Podcast/interview transcription with speaker awareness",
        "overrides": {
            "enable_review_pass": True,
            "output_formats": ["srt", "txt"],
        },
    },
    "meeting": {
        "description": "Meeting/recording transcription with action item awareness",
        "overrides": {
            "enable_review_pass": True,
            "output_formats": ["srt", "txt", "json"],
        },
    },
}


def _parse_toml_profile(name: str, data: dict[str, Any]) -> Profile:
    """Parse a profile from a TOML dict (top-level or nested sections)."""
    description = data.get("description", "")

    overrides: dict[str, Any] = {}

    # Flatten TOML sections into flat settings keys
    section_key_map = {
        "transcription": {
            "mode": "transcription_mode",
            "model": "whisper_model",
            "device": "whisper_device",
            "compute": "whisper_compute",
            "chunk_duration": "chunk_duration_sec",
            "chunk_overlap": "chunk_overlap_sec",
        },
        "translation": {
            "model": "translation_model",
            "batch_size": "translation_batch_size",
            "target_language": "target_language",
            "enable_review": "enable_review_pass",
            "custom_instructions": "custom_instructions",
        },
        "output": {
            "formats": "output_formats",
            "dir": "output_dir",
        },
    }

    for section, key_map in section_key_map.items():
        if section in data and isinstance(data[section], dict):
            for toml_key, settings_key in key_map.items():
                if toml_key in data[section]:
                    overrides[settings_key] = data[section][toml_key]

    # Top-level keys that map directly
    for key in ("source_language", "target_language", "custom_instructions",
                "max_concurrency", "profile"):
        if key in data:
            overrides[key] = data[key]

    return Profile(name=name, description=description, overrides=overrides)


def load_profile(name: str, config_dir: Path | None = None) -> Profile:
    """Load a profile by name.

    Checks user profiles directory first, then falls back to built-ins.

    Args:
        name: Profile name (without .toml extension).
        config_dir: Override config directory (for testing).

    Returns:
        Profile object.

    Raises:
        FileNotFoundError: If the profile doesn't exist.
    """
    if config_dir is None:
        from mediascribe.core.config import _default_config_dir
        config_dir = _default_config_dir()

    # Check user profiles directory
    profiles_dir = config_dir / "profiles"
    user_file = profiles_dir / f"{name}.toml"
    if user_file.exists():
        with open(user_file, "rb") as f:
            data = tomllib.load(f)
        return _parse_toml_profile(name, data)

    # Fall back to built-in profiles
    if name in BUILTIN_PROFILES:
        builtin = BUILTIN_PROFILES[name]
        return Profile(
            name=name,
            description=builtin.get("description", ""),
            overrides=dict(builtin.get("overrides", {})),
        )

    raise FileNotFoundError(
        f"Profile '{name}' not found. Available: {', '.join(list_profiles(config_dir))}"
    )


def list_profiles(config_dir: Path | None = None) -> list[str]:
    """List all available profile names (built-in + user)."""
    names = set(BUILTIN_PROFILES.keys())

    if config_dir is None:
        from mediascribe.core.config import _default_config_dir
        config_dir = _default_config_dir()

    profiles_dir = config_dir / "profiles"
    if profiles_dir.is_dir():
        for f in profiles_dir.glob("*.toml"):
            names.add(f.stem)

    return sorted(names)


def save_builtin_profiles(config_dir: Path) -> None:
    """Write built-in profile TOML files to the profiles directory."""
    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    profile_tomls = {
        "anime": (
            '# Anime subtitling profile\n'
            'description = "Anime/animation subtitling with character-aware translation"\n'
            '\n'
            '[transcription]\n'
            'mode = "local"\n'
            'model = "large-v3"\n'
            'chunk_duration = 180\n'
            '\n'
            '[translation]\n'
            'model = "gpt-4.1"\n'
            'enable_review = true\n'
            'custom_instructions = """\n'
            'Preserve character catchphrases and verbal tics.\n'
            'Keep humor punchy and age-appropriate.\n'
            '"""\n'
            '\n'
            '[output]\n'
            'formats = ["srt", "vtt"]\n'
        ),
        "podcast": (
            '# Podcast transcription profile\n'
            'description = "Podcast/interview transcription with speaker awareness"\n'
            '\n'
            '[transcription]\n'
            'mode = "auto"\n'
            'model = "large-v3"\n'
            '\n'
            '[translation]\n'
            'enable_review = true\n'
            'custom_instructions = """\n'
            'Preserve speaker tone and conversational style.\n'
            'Translate idioms naturally.\n'
            '"""\n'
            '\n'
            '[output]\n'
            'formats = ["srt", "txt"]\n'
        ),
        "meeting": (
            '# Meeting transcription profile\n'
            'description = "Meeting/recording transcription with action item awareness"\n'
            '\n'
            '[transcription]\n'
            'mode = "auto"\n'
            'model = "large-v3"\n'
            '\n'
            '[translation]\n'
            'enable_review = true\n'
            'custom_instructions = """\n'
            'Preserve technical terminology accurately.\n'
            'Keep action items and decisions clearly translated.\n'
            '"""\n'
            '\n'
            '[output]\n'
            'formats = ["srt", "txt", "json"]\n'
        ),
    }

    for name, content in profile_tomls.items():
        path = profiles_dir / f"{name}.toml"
        if not path.exists():
            path.write_text(content, encoding="utf-8")
