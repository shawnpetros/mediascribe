"""Profile system — named configuration presets for common use cases.

Profiles are TOML files stored in ~/.config/mediascribe/profiles/.
Built-in profiles are embedded; users can create custom ones.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from typing import Any

from mediascribe.core.config import MediascribeSettings, _default_config_dir


@dataclass
class Profile:
    """A named configuration preset."""

    name: str
    description: str
    settings: dict[str, Any] = field(default_factory=dict)

    def apply(self, base: MediascribeSettings) -> MediascribeSettings:
        """Create new settings by overlaying this profile on base settings."""
        overrides = {}
        for key, value in self.settings.items():
            if hasattr(base, key):
                overrides[key] = value
        return base.model_copy(update=overrides)


# ── Built-in Profiles ───────────────────────────────────────────────

BUILTIN_PROFILES: dict[str, Profile] = {
    "anime_subtitles": Profile(
        name="anime_subtitles",
        description="Anime/animation subtitling (Japanese → target language)",
        settings={
            "transcription_mode": "local",
            "whisper_model": "large-v3",
            "chunk_duration_sec": 180,
            "translation_batch_size": 15,
            "enable_review_pass": True,
            "output_formats": ["srt", "vtt"],
        },
    ),
    "podcast": Profile(
        name="podcast",
        description="Podcast/interview transcription with speaker focus",
        settings={
            "transcription_mode": "auto",
            "whisper_model": "large-v3",
            "chunk_duration_sec": 300,
            "enable_review_pass": False,
            "output_formats": ["txt", "srt"],
        },
    ),
    "meeting": Profile(
        name="meeting",
        description="Meeting recordings — transcription + action items",
        settings={
            "transcription_mode": "auto",
            "whisper_model": "large-v3",
            "chunk_duration_sec": 300,
            "enable_review_pass": False,
            "output_formats": ["txt", "json"],
        },
    ),
    "lecture": Profile(
        name="lecture",
        description="Lectures/presentations — accurate long-form transcription",
        settings={
            "transcription_mode": "local",
            "whisper_model": "large-v3",
            "chunk_duration_sec": 300,
            "chunk_overlap_sec": 20,
            "enable_review_pass": False,
            "output_formats": ["txt", "srt"],
        },
    ),
}


def load_custom_profiles() -> dict[str, Profile]:
    """Load user-created profiles from ~/.config/mediascribe/profiles/."""
    profiles_dir = _default_config_dir() / "profiles"
    if not profiles_dir.exists():
        return {}

    custom: dict[str, Profile] = {}
    for toml_file in sorted(profiles_dir.glob("*.toml")):
        try:
            data = tomllib.loads(toml_file.read_text())
            name = toml_file.stem
            desc = data.pop("description", f"Custom profile: {name}")

            # Flatten nested sections into flat settings dict
            flat: dict[str, Any] = {}
            for section_key, section_val in data.items():
                if isinstance(section_val, dict):
                    flat.update(section_val)
                else:
                    flat[section_key] = section_val

            custom[name] = Profile(name=name, description=desc, settings=flat)
        except Exception:
            continue  # skip malformed profile files

    return custom


def get_all_profiles() -> dict[str, Profile]:
    """Get all profiles — built-in + custom (custom overrides built-in)."""
    profiles = dict(BUILTIN_PROFILES)
    profiles.update(load_custom_profiles())
    return profiles


def get_profile(name: str) -> Profile | None:
    """Get a profile by name, or None if not found."""
    return get_all_profiles().get(name)
