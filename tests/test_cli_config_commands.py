"""Tests for CLI config/translate command wiring."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mediascribe.cli.app import app

runner = CliRunner()


def test_config_set_get_and_list(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    set_result = runner.invoke(app, ["config", "set", "whisper_model", "small"])
    assert set_result.exit_code == 0

    get_result = runner.invoke(app, ["config", "get", "whisper_model"])
    assert get_result.exit_code == 0
    assert "whisper_model" in get_result.output
    assert "small" in get_result.output

    list_result = runner.invoke(app, ["config", "list"])
    assert list_result.exit_code == 0
    assert "whisper_model" in list_result.output
    assert "small" in list_result.output


def test_config_get_redacts_secrets_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    set_result = runner.invoke(app, ["config", "set", "openai_api_key", "sk-test-secret"])
    assert set_result.exit_code == 0

    get_result = runner.invoke(app, ["config", "get", "openai_api_key"])
    assert get_result.exit_code == 0
    assert "redacted" in get_result.output.lower()
    assert "sk-test-secret" not in get_result.output

    get_raw_result = runner.invoke(app, ["config", "get", "openai_api_key", "--raw"])
    assert get_raw_result.exit_code == 0
    assert "sk-test-secret" in get_raw_result.output


def test_translate_command_invokes_helper(monkeypatch, tmp_path: Path) -> None:
    import mediascribe.cli.output as output_module

    srt_path = tmp_path / "sample.srt"
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHello\n",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    def fake_run_translate_for_srt(
        source_srt_path: Path,
        target_language: str,
        output_path: Path | None = None,
        profile: str | None = None,
        translation_model: str | None = None,
        custom_instructions: str | None = None,
        enable_review: bool | None = None,
    ) -> Path:
        calls["source_srt_path"] = source_srt_path
        calls["target_language"] = target_language
        calls["output_path"] = output_path
        calls["profile"] = profile
        calls["translation_model"] = translation_model
        calls["custom_instructions"] = custom_instructions
        calls["enable_review"] = enable_review
        return source_srt_path.with_name("out.srt")

    monkeypatch.setattr(output_module, "run_translate_for_srt", fake_run_translate_for_srt)

    result = runner.invoke(app, ["translate", str(srt_path), "--to", "en", "--no-review"])
    assert result.exit_code == 0
    assert calls["source_srt_path"] == srt_path
    assert calls["target_language"] == "en"
    assert calls["enable_review"] is False
