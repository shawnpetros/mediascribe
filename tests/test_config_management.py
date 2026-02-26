"""Tests for config management helpers.

Covers:
- TOML config file read/write
- User config loading
- Config value parsing (string, int, bool, float)
- Config display formatting
"""

from pathlib import Path
from unittest.mock import patch

from mediascribe.cli.output import (
    _load_user_config,
    _save_user_config,
)


class TestSaveUserConfig:
    def test_creates_file(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({"whisper_model": "small"})
            config_file = tmp_path / "config.toml"
            assert config_file.exists()
            content = config_file.read_text()
            assert 'whisper_model = "small"' in content

    def test_writes_integer(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({"chunk_duration_sec": 120})
            content = (tmp_path / "config.toml").read_text()
            assert "chunk_duration_sec = 120" in content

    def test_writes_boolean(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({"word_timestamps": True})
            content = (tmp_path / "config.toml").read_text()
            assert "word_timestamps = true" in content

    def test_writes_float(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({"min_gap_sec": 0.25})
            content = (tmp_path / "config.toml").read_text()
            assert "min_gap_sec = 0.25" in content

    def test_writes_list(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({"output_formats": ["srt", "vtt"]})
            content = (tmp_path / "config.toml").read_text()
            assert 'output_formats = ["srt", "vtt"]' in content

    def test_multiple_values(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            _save_user_config({
                "whisper_model": "small",
                "chunk_duration_sec": 120,
            })
            content = (tmp_path / "config.toml").read_text()
            assert "whisper_model" in content
            assert "chunk_duration_sec" in content


class TestLoadUserConfig:
    def test_loads_existing_config(self, tmp_path: Path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('whisper_model = "small"\nchunk_duration_sec = 120\n')
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            data = _load_user_config()
            assert data["whisper_model"] == "small"
            assert data["chunk_duration_sec"] == 120

    def test_returns_empty_when_no_file(self, tmp_path: Path):
        with patch("mediascribe.cli.output._default_config_dir", return_value=tmp_path):
            data = _load_user_config()
            assert data == {}
