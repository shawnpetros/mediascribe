"""Tests for the ExportStep — multi-format output writer."""

import json
from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job, Segment
from mediascribe.steps.export import ExportStep


def _make_job(tmp_path: Path) -> Job:
    job = Job(input_path=tmp_path / "test.mp4", output_dir=tmp_path)
    job.segments = [
        Segment(index=1, start=0.0, end=2.5, text="Hello world"),
        Segment(index=2, start=3.0, end=5.0, text="Second line"),
        Segment(
            index=3,
            start=6.0,
            end=8.0,
            text="Third line",
            translation="Tercera linea",
        ),
    ]
    return job


class TestExportSRT:
    def test_writes_srt_file(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["srt"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        srt_files = list(tmp_path.glob("*.srt"))
        assert len(srt_files) >= 1

    def test_srt_not_overwritten_if_exists(self, tmp_path: Path):
        existing = tmp_path / "test_unknown.srt"
        existing.write_text("existing content")

        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["srt"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        step.execute(job, settings, events)

        assert existing.read_text() == "existing content"


class TestExportVTT:
    def test_writes_vtt_file(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["vtt"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        vtt_files = list(tmp_path.glob("*.vtt"))
        assert len(vtt_files) == 1
        content = vtt_files[0].read_text()
        assert "WEBVTT" in content
        assert "Hello world" in content


class TestExportTXT:
    def test_writes_txt_file(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["txt"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        txt_files = list(tmp_path.glob("*.txt"))
        assert len(txt_files) == 1
        content = txt_files[0].read_text()
        assert "Hello world" in content


class TestExportJSON:
    def test_writes_json_file(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["json"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text())
        assert "metadata" in data
        assert "segments" in data
        assert len(data["segments"]) == 3

    def test_json_includes_translations(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_formats=["json"], output_dir=tmp_path)
        events = EventBus()

        step = ExportStep()
        step.execute(job, settings, events)

        data = json.loads(list(tmp_path.glob("*.json"))[0].read_text())
        seg3 = data["segments"][2]
        assert seg3["translation"] == "Tercera linea"


class TestMultiFormat:
    def test_writes_all_formats(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(
            output_formats=["srt", "vtt", "txt", "json"],
            output_dir=tmp_path,
        )
        events = EventBus()

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        assert result.data["count"] == 4
        assert len(list(tmp_path.glob("*.srt"))) >= 1
        assert len(list(tmp_path.glob("*.vtt"))) == 1
        assert len(list(tmp_path.glob("*.txt"))) == 1
        assert len(list(tmp_path.glob("*.json"))) == 1

    def test_unknown_format_warns(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(
            output_formats=["srt", "invalid_format"],
            output_dir=tmp_path,
        )
        warnings = []
        events = EventBus()
        events.subscribe(
            lambda e: warnings.append(e.message) if e.type.value == "warning" else None
        )

        step = ExportStep()
        result = step.execute(job, settings, events)

        assert result.success
        assert any("invalid_format" in w for w in warnings)

    def test_can_skip_returns_false(self, tmp_path: Path):
        job = _make_job(tmp_path)
        step = ExportStep()
        assert step.can_skip(job) is False
