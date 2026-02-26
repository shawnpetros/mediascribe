"""Tests for CLI commands — config, translate, models.

Covers:
- Config show/set/get/list/path commands
- Translate command validation
- Models list command
- User config TOML read/write
- Version callback
"""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mediascribe.cli.app import app

runner = CliRunner()


class TestVersionFlag:
    def test_version_output(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "mediascribe" in result.output

    def test_short_version_flag(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0


class TestConfigShow:
    def test_shows_table(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "mediascribe configuration" in result.output

    def test_shows_default_values(self):
        result = runner.invoke(app, ["config", "show"])
        assert "whisper_model" in result.output
        assert "translation_model" in result.output

    def test_default_invocation(self):
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "mediascribe configuration" in result.output


class TestConfigSet:
    def test_set_known_key(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            result = runner.invoke(app, ["config", "set", "whisper_model", "small"])
            assert result.exit_code == 0
            assert "Set" in result.output
            assert "small" in result.output

            config_file = tmp_path / "config.toml"
            assert config_file.exists()
            assert "small" in config_file.read_text()

    def test_set_unknown_key(self):
        result = runner.invoke(app, ["config", "set", "nonexistent_key", "value"])
        assert "Unknown config key" in result.output

    def test_set_integer_value(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            result = runner.invoke(app, ["config", "set", "chunk_duration_sec", "120"])
            assert result.exit_code == 0
            config_file = tmp_path / "config.toml"
            assert "120" in config_file.read_text()

    def test_set_boolean_value(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            result = runner.invoke(app, ["config", "set", "word_timestamps", "false"])
            assert result.exit_code == 0


class TestConfigGet:
    def test_get_known_key(self):
        result = runner.invoke(app, ["config", "get", "whisper_model"])
        assert result.exit_code == 0
        assert "whisper_model" in result.output
        assert "large-v3" in result.output

    def test_get_unknown_key(self):
        result = runner.invoke(app, ["config", "get", "fake_key"])
        assert "Unknown config key" in result.output

    def test_get_none_value(self):
        result = runner.invoke(app, ["config", "get", "source_language"])
        assert "not set" in result.output


class TestConfigList:
    def test_lists_all_keys(self):
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "Available Configuration Keys" in result.output
        assert "whisper_model" in result.output
        assert "translation_model" in result.output
        assert "openai_api_key" in result.output

    def test_includes_descriptions(self):
        result = runner.invoke(app, ["config", "list"])
        assert "Whisper model size" in result.output


class TestConfigPath:
    def test_prints_path(self):
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert "config.toml" in result.output


class TestTranslateCommand:
    def test_missing_file(self, tmp_path: Path):
        result = runner.invoke(app, ["translate", str(tmp_path / "missing.srt"), "--target", "en"])
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_non_srt_file(self, tmp_path: Path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not an srt")
        result = runner.invoke(app, ["translate", str(txt_file), "--target", "en"])
        assert result.exit_code != 0
        assert ".srt" in result.output


class TestTranscribeCommand:
    def test_missing_file(self, tmp_path: Path):
        result = runner.invoke(app, ["transcribe", str(tmp_path / "missing.mp4")])
        assert result.exit_code != 0
        assert "File not found" in result.output


class TestBatchCommand:
    def test_not_a_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("hi")
        result = runner.invoke(app, ["batch", str(f)])
        assert result.exit_code != 0
        assert "Not a directory" in result.output

    def test_empty_directory(self, tmp_path: Path):
        result = runner.invoke(app, ["batch", str(tmp_path)])
        assert "No media files found" in result.output


class TestModelsListCommand:
    def test_lists_models(self):
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        assert "Whisper Models" in result.output
        assert "large-v3" in result.output
        assert "tiny" in result.output

    def test_shows_descriptions(self):
        result = runner.invoke(app, ["models", "list"])
        assert "best accuracy" in result.output or "fastest" in result.output


class TestModelsPathCommand:
    def test_prints_path(self):
        result = runner.invoke(app, ["models", "path"])
        assert result.exit_code == 0
        assert "models" in result.output
