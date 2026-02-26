"""Tests for persisted config helpers and settings precedence."""

from __future__ import annotations

from pathlib import Path

from mediascribe.core.config import (
    config_file_path,
    load_settings,
    load_user_config,
    parse_setting_value,
    save_user_config,
)


def test_config_file_path_uses_xdg_config_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config_file_path() == tmp_path / "mediascribe" / "config.toml"


def test_save_and_load_user_config_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    save_user_config(
        {
            "whisper_model": "small",
            "enable_review_pass": False,
            "output_formats": ["srt", "vtt"],
        },
        path=path,
    )

    loaded = load_user_config(path=path)
    assert loaded["whisper_model"] == "small"
    assert loaded["enable_review_pass"] is False
    assert loaded["output_formats"] == ["srt", "vtt"]


def test_parse_setting_value_for_common_types() -> None:
    assert parse_setting_value("enable_review_pass", "false") is False
    assert parse_setting_value("chunk_duration_sec", "240") == 240
    assert parse_setting_value("min_gap_sec", "0.25") == 0.25
    assert parse_setting_value("output_formats", "srt,vtt,txt") == ["srt", "vtt", "txt"]
    assert parse_setting_value("output_formats", '["srt", "json"]') == ["srt", "json"]
    assert parse_setting_value("output_dir", "./custom-out") == Path("./custom-out")
    assert parse_setting_value("target_language", "null") is None


def test_load_settings_applies_env_over_persisted_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_user_config({"whisper_model": "small"})
    monkeypatch.setenv("MEDIASCRIBE_WHISPER_MODEL", "medium")

    settings = load_settings()
    assert settings.whisper_model == "medium"


def test_load_settings_applies_explicit_overrides_highest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_user_config({"whisper_model": "small"})
    monkeypatch.setenv("MEDIASCRIBE_WHISPER_MODEL", "medium")

    settings = load_settings({"whisper_model": "large-v3"})
    assert settings.whisper_model == "large-v3"


def test_load_settings_respects_dotenv_over_persisted(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    save_user_config({"translation_model": "gpt-4.1"})
    (workdir / ".env").write_text("MEDIASCRIBE_TRANSLATION_MODEL=gpt-4.1-mini\n", encoding="utf-8")

    settings = load_settings()
    assert settings.translation_model == "gpt-4.1-mini"
