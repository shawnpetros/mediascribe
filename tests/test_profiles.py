"""Tests for the profile system — TOML loading and built-in profiles."""

from pathlib import Path

from mediascribe.core.profiles import (
    BUILTIN_PROFILES,
    Profile,
    list_profiles,
    load_profile,
    save_builtin_profiles,
)


class TestBuiltinProfiles:
    def test_general_exists(self):
        assert "general" in BUILTIN_PROFILES

    def test_anime_exists(self):
        assert "anime" in BUILTIN_PROFILES

    def test_podcast_exists(self):
        assert "podcast" in BUILTIN_PROFILES

    def test_meeting_exists(self):
        assert "meeting" in BUILTIN_PROFILES

    def test_all_have_descriptions(self):
        for name, data in BUILTIN_PROFILES.items():
            assert "description" in data, f"Missing description for {name}"


class TestLoadProfile:
    def test_load_builtin_general(self, tmp_path: Path):
        p = load_profile("general", config_dir=tmp_path)
        assert p.name == "general"
        assert isinstance(p.description, str)

    def test_load_builtin_anime(self, tmp_path: Path):
        p = load_profile("anime", config_dir=tmp_path)
        assert p.name == "anime"
        assert "local" in str(p.overrides.get("transcription_mode", ""))

    def test_load_builtin_podcast(self, tmp_path: Path):
        p = load_profile("podcast", config_dir=tmp_path)
        assert p.name == "podcast"

    def test_load_builtin_meeting(self, tmp_path: Path):
        p = load_profile("meeting", config_dir=tmp_path)
        assert p.name == "meeting"
        assert "json" in p.overrides.get("output_formats", [])

    def test_load_nonexistent_raises(self, tmp_path: Path):
        import pytest

        with pytest.raises(FileNotFoundError):
            load_profile("nonexistent_profile", config_dir=tmp_path)

    def test_load_user_profile(self, tmp_path: Path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_file = profiles_dir / "custom.toml"
        profile_file.write_text(
            'description = "My custom profile"\n'
            "\n"
            "[transcription]\n"
            'mode = "api"\n'
            "\n"
            "[translation]\n"
            'model = "gpt-4o"\n'
            'target_language = "fr"\n'
            "\n"
            "[output]\n"
            'formats = ["srt", "vtt"]\n',
            encoding="utf-8",
        )

        p = load_profile("custom", config_dir=tmp_path)
        assert p.name == "custom"
        assert p.description == "My custom profile"
        assert p.overrides["transcription_mode"] == "api"
        assert p.overrides["translation_model"] == "gpt-4o"
        assert p.overrides["target_language"] == "fr"
        assert p.overrides["output_formats"] == ["srt", "vtt"]

    def test_user_profile_overrides_builtin(self, tmp_path: Path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "anime.toml").write_text(
            'description = "My anime profile"\n\n[transcription]\nmode = "api"\n',
            encoding="utf-8",
        )

        p = load_profile("anime", config_dir=tmp_path)
        assert p.description == "My anime profile"
        assert p.overrides["transcription_mode"] == "api"


class TestListProfiles:
    def test_lists_builtins(self, tmp_path: Path):
        profiles = list_profiles(config_dir=tmp_path)
        assert "general" in profiles
        assert "anime" in profiles
        assert "podcast" in profiles
        assert "meeting" in profiles

    def test_includes_user_profiles(self, tmp_path: Path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "my_custom.toml").write_text('description = "test"')

        profiles = list_profiles(config_dir=tmp_path)
        assert "my_custom" in profiles
        assert "general" in profiles

    def test_sorted(self, tmp_path: Path):
        profiles = list_profiles(config_dir=tmp_path)
        assert profiles == sorted(profiles)


class TestSaveBuiltinProfiles:
    def test_creates_profile_files(self, tmp_path: Path):
        save_builtin_profiles(tmp_path)
        profiles_dir = tmp_path / "profiles"
        assert (profiles_dir / "anime.toml").exists()
        assert (profiles_dir / "podcast.toml").exists()
        assert (profiles_dir / "meeting.toml").exists()

    def test_does_not_overwrite(self, tmp_path: Path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "anime.toml").write_text("custom content")

        save_builtin_profiles(tmp_path)
        assert (profiles_dir / "anime.toml").read_text() == "custom content"


class TestProfileApply:
    def test_apply_merges_overrides(self):
        p = Profile(
            name="test",
            overrides={"transcription_mode": "local", "whisper_model": "small"},
        )
        result = p.apply({"output_dir": "/tmp"})
        assert result["transcription_mode"] == "local"
        assert result["whisper_model"] == "small"
        assert result["output_dir"] == "/tmp"

    def test_apply_cli_overrides_profile(self):
        p = Profile(
            name="test",
            overrides={"transcription_mode": "local"},
        )
        result = p.apply({"transcription_mode": "api"})
        assert result["transcription_mode"] == "api"

    def test_apply_skips_none_values(self):
        p = Profile(
            name="test",
            overrides={"transcription_mode": "local"},
        )
        result = p.apply({"transcription_mode": None})
        assert result["transcription_mode"] == "local"
