"""Tests for TUI application components.

Covers:
- App instantiation
- Welcome screen composition
- Setup screen composition
- Picker screen composition
- Screen imports work correctly
"""

import pytest


class TestTuiImports:
    def test_import_app(self):
        from mediascribe.tui.app import MediascribeApp
        assert MediascribeApp is not None

    def test_import_welcome_screen(self):
        from mediascribe.tui.screens.welcome import WelcomeScreen
        assert WelcomeScreen is not None

    def test_import_setup_screen(self):
        from mediascribe.tui.screens.setup import SetupScreen
        assert SetupScreen is not None

    def test_import_picker_screen(self):
        from mediascribe.tui.screens.picker import PickerScreen
        assert PickerScreen is not None

    def test_import_pipeline_screen(self):
        from mediascribe.tui.screens.pipeline import PipelineScreen
        assert PipelineScreen is not None

    def test_import_results_screen(self):
        from mediascribe.tui.screens.results import ResultsScreen
        assert ResultsScreen is not None


class TestMediascribeApp:
    def test_app_creation(self):
        from mediascribe.tui.app import MediascribeApp
        app = MediascribeApp()
        assert app.TITLE == "mediascribe"

    def test_app_has_bindings(self):
        from mediascribe.tui.app import MediascribeApp
        app = MediascribeApp()
        binding_keys = [b.key for b in app.BINDINGS]
        assert "q" in binding_keys


class TestWelcomeScreen:
    def test_screen_creation(self):
        from mediascribe.tui.screens.welcome import WelcomeScreen
        screen = WelcomeScreen()
        assert screen is not None


class TestPickerScreen:
    def test_media_extensions(self):
        from mediascribe.tui.screens.picker import MEDIA_EXTENSIONS
        assert ".mp4" in MEDIA_EXTENSIONS
        assert ".mp3" in MEDIA_EXTENSIONS
        assert ".wav" in MEDIA_EXTENSIONS
        assert ".mkv" in MEDIA_EXTENSIONS
