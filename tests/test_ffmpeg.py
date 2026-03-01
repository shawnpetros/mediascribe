"""Tests for FFmpeg wrapper functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mediascribe.utils.ffmpeg import extract_audio, probe_duration, probe_json


class TestProbeDuration:
    def test_returns_float(self):
        mock_result = MagicMock()
        mock_result.stdout = "123.456\n"
        with patch("subprocess.run", return_value=mock_result):
            assert probe_duration(Path("test.wav")) == pytest.approx(123.456)

    def test_raises_on_empty_output(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result), pytest.raises(ValueError):
            probe_duration(Path("test.wav"))


class TestProbeJson:
    def test_parses_json_output(self):
        mock_result = MagicMock()
        mock_result.stdout = '{"format": {"duration": "10.5"}}'
        with patch("subprocess.run", return_value=mock_result):
            result = probe_json(Path("test.wav"))
            assert result["format"]["duration"] == "10.5"


class TestExtractAudio:
    def test_raises_on_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"ffmpeg error"
        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="ffmpeg extract_audio failed"),
        ):
            extract_audio(Path("input.mp4"), Path("output.wav"))

    def test_succeeds_on_zero_return(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            extract_audio(Path("input.mp4"), Path("output.wav"))
