"""Tests for extended config settings — profile field, output_formats."""

from mediascribe.core.config import MediascribeSettings


class TestProfileSetting:
    def test_default_profile(self):
        settings = MediascribeSettings()
        assert settings.profile == "general"

    def test_custom_profile(self):
        settings = MediascribeSettings(profile="anime")
        assert settings.profile == "anime"


class TestOutputFormats:
    def test_default_output_formats(self):
        settings = MediascribeSettings()
        assert settings.output_formats == ["srt"]

    def test_custom_output_formats(self):
        settings = MediascribeSettings(output_formats=["srt", "vtt", "json"])
        assert settings.output_formats == ["srt", "vtt", "json"]


class TestHardwareDetection:
    def test_hardware_profile_import(self):
        from mediascribe.core.hardware import HardwareProfile, detect_hardware

        hw = detect_hardware()
        assert isinstance(hw, HardwareProfile)
        assert hw.cpu_count >= 1
        assert hw.ram_gb > 0

    def test_recommended_concurrency(self):
        from mediascribe.core.hardware import HardwareProfile

        hw = HardwareProfile(
            cpu_count=8,
            cpu_brand="test",
            ram_gb=16.0,
            has_gpu=False,
            gpu_name=None,
            os_name="Linux",
            arch="x86_64",
        )
        assert hw.recommended_concurrency >= 1

    def test_recommended_compute_type(self):
        from mediascribe.core.hardware import HardwareProfile

        hw = HardwareProfile(
            cpu_count=4,
            cpu_brand="test",
            ram_gb=8.0,
            has_gpu=True,
            gpu_name="RTX 4090",
            os_name="Linux",
            arch="x86_64",
        )
        assert hw.recommended_compute_type == "float16"

    def test_estimate_transcription_time(self):
        from mediascribe.core.hardware import HardwareProfile, estimate_transcription_time

        hw = HardwareProfile(
            cpu_count=4,
            cpu_brand="test",
            ram_gb=8.0,
            has_gpu=False,
            gpu_name=None,
            os_name="Linux",
            arch="x86_64",
        )
        low, high = estimate_transcription_time(600.0, hw)
        assert low > 0
        assert high > low
