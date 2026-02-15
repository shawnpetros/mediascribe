"""Capture screenshots of each TUI screen for documentation."""

import asyncio
from pathlib import Path

SCREENSHOTS_DIR = Path(__file__).parent.parent / "docs" / "screenshots"


async def capture_screenshots() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Welcome Screen ─────────────────────────────────────
    from mediascribe.tui.app import MediascribeApp

    app = MediascribeApp()
    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "01_welcome.svg"))
        print("✓ Welcome screen captured")

        # ── 2. Setup Screen ───────────────────────────────────
        app.push_screen("setup")
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "02_setup.svg"))
        print("✓ Setup screen captured")

        # ── 3. Picker Screen ──────────────────────────────────
        app.push_screen("picker")
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "03_picker.svg"))
        print("✓ Picker screen captured")

        # ── 4. Profile Screen ─────────────────────────────────
        app.push_screen("profile")
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "04_profile.svg"))
        print("✓ Profile screen captured")

        # ── 5. Pipeline Screen (empty/preparing state) ────────
        # Store fake settings so pipeline screen can mount
        app._pipeline_settings = {
            "source_language": None,
            "target_language": "en",
            "transcription_mode": "auto",
            "whisper_model": "large-v3",
            "translation_model": "gpt-4.1",
            "enable_review_pass": True,
            "custom_instructions": "",
            "output_formats": ["srt"],
        }
        app.push_screen("pipeline")
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "05_pipeline.svg"))
        print("✓ Pipeline screen captured")

        # ── 6. Results Screen ─────────────────────────────────
        app._completed_jobs = []
        app._failed_jobs = []
        app.push_screen("results")
        await pilot.pause()
        app.save_screenshot(str(SCREENSHOTS_DIR / "06_results.svg"))
        print("✓ Results screen captured")

        await pilot.exit(None)

    print(f"\nAll screenshots saved to {SCREENSHOTS_DIR}/")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
