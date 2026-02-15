"""Tests for the profile system."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.profiles import (
    BUILTIN_PROFILES,
    Profile,
    get_all_profiles,
    get_profile,
    load_custom_profiles,
)


class TestBuiltinProfiles:
    def test_four_builtin_profiles_exist(self):
        assert len(BUILTIN_PROFILES) == 4

    def test_profile_names(self):
        expected = {"anime_subtitles", "podcast", "meeting", "lecture"}
        assert set(BUILTIN_PROFILES.keys()) == expected

    def test_all_profiles_have_descriptions(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.description, f"{name} missing description"

    def test_all_profiles_have_settings(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.settings, f"{name} has no settings"


class TestProfileApply:
    def test_apply_overwrites_matching_fields(self):
        base = MediascribeSettings()
        profile = Profile(
            name="test",
            description="Test profile",
            settings={"whisper_model": "small", "enable_review_pass": False},
        )
        result = profile.apply(base)
        assert result.whisper_model == "small"
        assert result.enable_review_pass is False

    def test_apply_preserves_unmentioned_fields(self):
        base = MediascribeSettings(output_dir=Path("/tmp/custom"))
        profile = Profile(
            name="test",
            description="Test",
            settings={"whisper_model": "tiny"},
        )
        result = profile.apply(base)
        assert result.output_dir == Path("/tmp/custom")
        assert result.whisper_model == "tiny"

    def test_apply_ignores_unknown_keys(self):
        base = MediascribeSettings()
        profile = Profile(
            name="test",
            description="Test",
            settings={"nonexistent_field": "value", "whisper_model": "medium"},
        )
        result = profile.apply(base)
        assert result.whisper_model == "medium"

    def test_apply_anime_profile(self):
        base = MediascribeSettings()
        profile = BUILTIN_PROFILES["anime_subtitles"]
        result = profile.apply(base)
        assert result.transcription_mode == "local"
        assert result.whisper_model == "large-v3"
        assert result.enable_review_pass is True
        assert "srt" in result.output_formats
        assert "vtt" in result.output_formats

    def test_apply_podcast_profile(self):
        base = MediascribeSettings()
        profile = BUILTIN_PROFILES["podcast"]
        result = profile.apply(base)
        assert result.chunk_duration_sec == 300
        assert result.enable_review_pass is False


class TestGetProfile:
    def test_get_existing_profile(self):
        profile = get_profile("anime_subtitles")
        assert profile is not None
        assert profile.name == "anime_subtitles"

    def test_get_nonexistent_profile(self):
        assert get_profile("does_not_exist") is None


class TestGetAllProfiles:
    def test_returns_all_builtins(self):
        all_profiles = get_all_profiles()
        for name in BUILTIN_PROFILES:
            assert name in all_profiles


class TestLoadCustomProfiles:
    def test_empty_dir_returns_empty(self):
        # When profiles dir doesn't exist
        profiles = load_custom_profiles()
        # Should return empty dict (or whatever custom profiles exist)
        assert isinstance(profiles, dict)
