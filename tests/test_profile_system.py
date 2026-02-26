"""Tests for the profile system.

Covers:
- Profile field on settings
- Profile selection in config
- All built-in profiles exist
- Profile rendering with templates
"""

from mediascribe.core.config import MediascribeSettings
from mediascribe.models.prompts import TEMPLATES, render_prompt


class TestProfileSetting:
    def test_default_profile(self):
        settings = MediascribeSettings()
        assert settings.profile == "general"

    def test_custom_profile(self):
        settings = MediascribeSettings(profile="anime")
        assert settings.profile == "anime"

    def test_all_builtin_profiles_exist(self):
        for name in ["general", "anime", "podcast", "meeting"]:
            assert name in TEMPLATES


class TestProfileRendering:
    def test_general_profile(self):
        template = TEMPLATES["general"]
        sys_translate, sys_review = render_prompt(template, "en")
        assert "subtitle translator" in sys_translate.lower()
        assert "review" in sys_review.lower()

    def test_anime_profile(self):
        template = TEMPLATES["anime"]
        sys_translate, sys_review = render_prompt(template, "en")
        assert "anime" in sys_translate.lower()
        assert "catchphrase" in sys_translate.lower() or "character" in sys_review.lower()

    def test_podcast_profile(self):
        template = TEMPLATES["podcast"]
        sys_translate, sys_review = render_prompt(template, "en")
        assert "podcast" in sys_translate.lower() or "interview" in sys_translate.lower()

    def test_meeting_profile(self):
        template = TEMPLATES["meeting"]
        sys_translate, sys_review = render_prompt(template, "en")
        assert "meeting" in sys_translate.lower() or "business" in sys_translate.lower()

    def test_custom_instructions_merged(self):
        template = TEMPLATES["general"]
        sys_translate, _ = render_prompt(
            template, "en", custom_instructions="Keep it formal"
        )
        assert "Keep it formal" in sys_translate

    def test_empty_custom_instructions(self):
        template = TEMPLATES["general"]
        sys_translate, _ = render_prompt(template, "en", custom_instructions="")
        assert "Additional instructions" not in sys_translate

    def test_target_language_substituted(self):
        template = TEMPLATES["general"]
        sys_translate, _ = render_prompt(template, "Spanish")
        assert "Spanish" in sys_translate
