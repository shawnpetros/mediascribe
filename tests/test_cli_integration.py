"""Integration tests — verify the CLI entry point loads and responds correctly.

These tests invoke the actual CLI binary via subprocess, ensuring the
installed package works end-to-end (entry point resolves, imports succeed,
commands respond). They catch the class of bug where unit tests pass but
the app doesn't actually start.
"""

from __future__ import annotations

import subprocess
import sys


def _run(*args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    """Run mediascribe as a subprocess via ``python -m mediascribe``."""
    return subprocess.run(
        [sys.executable, "-m", "mediascribe", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestAppLoads:
    """The app should start, print help, and exit cleanly."""

    def test_help_exits_zero(self):
        r = _run("--help")
        assert r.returncode == 0

    def test_help_shows_usage(self):
        r = _run("--help")
        assert "Usage" in r.stdout

    def test_help_lists_commands(self):
        r = _run("--help")
        assert "transcribe" in r.stdout
        assert "batch" in r.stdout
        assert "translate" in r.stdout
        assert "config" in r.stdout
        assert "tui" in r.stdout

    def test_no_args_shows_help(self):
        r = _run()
        # Typer exits 2 for no_args_is_help (usage error), but still prints help
        assert "Usage" in r.stdout


class TestVersion:
    def test_version_flag(self):
        r = _run("--version")
        assert r.returncode == 0
        assert "mediascribe" in r.stdout

    def test_version_matches_package(self):
        from mediascribe import __version__

        r = _run("--version")
        assert __version__ in r.stdout

    def test_short_version_flag(self):
        r = _run("-V")
        assert r.returncode == 0
        assert "mediascribe" in r.stdout


class TestSubcommandHelp:
    """Each subcommand should respond to --help without errors."""

    def test_transcribe_help(self):
        r = _run("transcribe", "--help")
        assert r.returncode == 0
        assert "Transcribe" in r.stdout

    def test_batch_help(self):
        r = _run("batch", "--help")
        assert r.returncode == 0
        assert "folder" in r.stdout.lower() or "Process" in r.stdout

    def test_translate_help(self):
        r = _run("translate", "--help")
        assert r.returncode == 0
        assert "Translate" in r.stdout

    def test_config_help(self):
        r = _run("config", "--help")
        assert r.returncode == 0
        assert "config" in r.stdout.lower()

    def test_tui_help(self):
        r = _run("tui", "--help")
        assert r.returncode == 0


class TestConfigCommands:
    """Config subcommands should work without external dependencies."""

    def test_config_show(self):
        r = _run("config", "show")
        assert r.returncode == 0
        assert "Profile" in r.stdout
        assert "Whisper model" in r.stdout

    def test_config_path(self):
        r = _run("config", "path")
        assert r.returncode == 0
        assert "Config directory" in r.stdout

    def test_config_profiles(self):
        r = _run("config", "profiles")
        assert r.returncode == 0
        assert "general" in r.stdout
        assert "anime" in r.stdout


class TestErrorHandling:
    """Bad input should produce useful errors, not tracebacks."""

    def test_transcribe_missing_file(self):
        r = _run("transcribe", "/nonexistent/file.mp4")
        assert r.returncode != 0
        assert "not found" in r.stdout.lower() or "error" in r.stdout.lower()

    def test_translate_missing_file(self):
        r = _run("translate", "/nonexistent/file.srt")
        assert r.returncode != 0

    def test_translate_wrong_extension(self):
        r = _run("translate", "file.mp4")
        assert r.returncode != 0
        assert "srt" in r.stdout.lower() or "Error" in r.stdout

    def test_batch_not_a_directory(self):
        r = _run("batch", "/nonexistent/dir")
        assert r.returncode != 0

    def test_unknown_command(self):
        r = _run("notacommand")
        assert r.returncode != 0


class TestModuleEntry:
    """``python -m mediascribe`` should behave identically to the binary."""

    def test_module_help(self):
        r = subprocess.run(
            [sys.executable, "-m", "mediascribe", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert r.returncode == 0
        assert "Usage" in r.stdout

    def test_module_version(self):
        r = subprocess.run(
            [sys.executable, "-m", "mediascribe", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert r.returncode == 0
        assert "mediascribe" in r.stdout


class TestImportSmoke:
    """Core modules should import without side effects or errors."""

    def test_import_package(self):
        import mediascribe

        assert hasattr(mediascribe, "__version__")

    def test_import_cli(self):
        from mediascribe.cli.app import app, main

        assert callable(main)
        assert app is not None

    def test_import_pipeline(self):
        from mediascribe.core.pipeline import Pipeline

        assert Pipeline is not None

    def test_import_all_steps(self):
        from mediascribe.steps.analyze import AnalyzeStep
        from mediascribe.steps.detect import DetectStep
        from mediascribe.steps.diarize import DiarizeStep
        from mediascribe.steps.export import ExportStep
        from mediascribe.steps.normalize import NormalizeStep
        from mediascribe.steps.review import ReviewStep
        from mediascribe.steps.transcribe import TranscribeStep
        from mediascribe.steps.translate import TranslateStep

        for cls in [
            DetectStep,
            NormalizeStep,
            TranscribeStep,
            TranslateStep,
            ReviewStep,
            ExportStep,
            DiarizeStep,
            AnalyzeStep,
        ]:
            assert cls.name is not None

    def test_import_all_formats(self):
        from mediascribe.formats import json_export, srt, transcript, vtt

        assert callable(srt.save_srt)
        assert callable(vtt.save_vtt)
        assert callable(transcript.save_transcript)
        assert callable(json_export.save_json)

    def test_import_profiles(self):
        from mediascribe.core.profiles import list_profiles, load_profile

        assert callable(load_profile)
        assert callable(list_profiles)
