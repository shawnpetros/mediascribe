"""Smoke tests for TUI module imports and basic structure."""

from __future__ import annotations


class TestTuiImports:
    """Verify all TUI modules import without error."""

    def test_import_app(self):
        from mediascribe.tui.app import MediascribeApp, run_tui
        assert MediascribeApp is not None
        assert run_tui is not None

    def test_import_welcome_screen(self):
        from mediascribe.tui.screens.welcome import WelcomeScreen
        assert WelcomeScreen is not None

    def test_import_setup_screen(self):
        from mediascribe.tui.screens.setup import SetupScreen
        assert SetupScreen is not None

    def test_import_picker_screen(self):
        from mediascribe.tui.screens.picker import PickerScreen, MEDIA_EXTENSIONS
        assert PickerScreen is not None
        assert ".mp4" in MEDIA_EXTENSIONS
        assert ".mp3" in MEDIA_EXTENSIONS

    def test_import_profile_screen(self):
        from mediascribe.tui.screens.profile import ProfileScreen, LANGUAGES
        assert ProfileScreen is not None
        assert len(LANGUAGES) > 5

    def test_import_pipeline_screen(self):
        from mediascribe.tui.screens.pipeline import PipelineScreen, STEP_DEFS
        assert PipelineScreen is not None
        assert len(STEP_DEFS) == 3

    def test_import_results_screen(self):
        from mediascribe.tui.screens.results import ResultsScreen
        assert ResultsScreen is not None

    def test_import_widgets(self):
        from mediascribe.tui.widgets import JobProgress, LogPanel, StepProgress
        assert JobProgress is not None
        assert LogPanel is not None
        assert StepProgress is not None


class TestMediaExtensions:
    """Verify the media file extensions are correct."""

    def test_video_extensions(self):
        from mediascribe.tui.screens.picker import MEDIA_EXTENSIONS
        for ext in (".mp4", ".mkv", ".webm", ".avi", ".mov"):
            assert ext in MEDIA_EXTENSIONS

    def test_audio_extensions(self):
        from mediascribe.tui.screens.picker import MEDIA_EXTENSIONS
        for ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"):
            assert ext in MEDIA_EXTENSIONS


class TestAppScreenRegistration:
    """Verify the app has all screens registered."""

    def test_screens_registered(self):
        from mediascribe.tui.app import MediascribeApp
        expected_screens = {"welcome", "setup", "picker", "profile", "pipeline", "results"}
        assert set(MediascribeApp.SCREENS.keys()) == expected_screens
