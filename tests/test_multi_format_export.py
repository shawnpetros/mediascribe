"""Tests for multi-format export functionality.

Covers:
- VTT export triggered by output_formats config
- TXT export triggered by output_formats config
- MD export triggered by output_formats config
- JSON export triggered by output_formats config
- No export when format not in list
- Empty segments produce no output
"""

from pathlib import Path

from mediascribe.cli.output import _export_additional_formats
from mediascribe.core.config import MediascribeSettings
from mediascribe.core.job import Job, MediaInfo, Segment


def _make_job(tmp_path: Path) -> Job:
    job = Job(
        input_path=tmp_path / "video.mp4",
        output_dir=tmp_path,
    )
    job.segments = [
        Segment(index=1, start=0.0, end=2.0, text="Hello"),
        Segment(index=2, start=2.0, end=4.0, text="World"),
    ]
    job.media_info = MediaInfo(duration_sec=4.0)
    return job


class TestExportVtt:
    def test_vtt_created(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path, output_formats=["srt", "vtt"])
        _export_additional_formats(job, settings)
        assert (tmp_path / "video.vtt").exists()

    def test_vtt_not_created_when_not_in_formats(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path, output_formats=["srt"])
        _export_additional_formats(job, settings)
        assert not (tmp_path / "video.vtt").exists()


class TestExportTxt:
    def test_txt_created(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path, output_formats=["srt", "txt"])
        _export_additional_formats(job, settings)
        path = tmp_path / "video.txt"
        assert path.exists()
        content = path.read_text()
        assert "Hello" in content


class TestExportMarkdown:
    def test_md_created(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path, output_formats=["srt", "md"])
        _export_additional_formats(job, settings)
        path = tmp_path / "video.md"
        assert path.exists()
        content = path.read_text()
        assert "# Transcript" in content
        assert "Hello" in content


class TestExportJson:
    def test_json_created(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(output_dir=tmp_path, output_formats=["srt", "json"])
        _export_additional_formats(job, settings)
        path = tmp_path / "video.json"
        assert path.exists()

        import json
        data = json.loads(path.read_text())
        assert "segments" in data
        assert len(data["segments"]) == 2


class TestExportEmpty:
    def test_no_export_with_empty_segments(self, tmp_path: Path):
        job = Job(input_path=tmp_path / "video.mp4", output_dir=tmp_path)
        settings = MediascribeSettings(
            output_dir=tmp_path,
            output_formats=["srt", "vtt", "txt", "md", "json"],
        )
        _export_additional_formats(job, settings)
        assert not (tmp_path / "video.vtt").exists()
        assert not (tmp_path / "video.txt").exists()
        assert not (tmp_path / "video.md").exists()
        assert not (tmp_path / "video.json").exists()


class TestExportAllFormats:
    def test_all_formats_at_once(self, tmp_path: Path):
        job = _make_job(tmp_path)
        settings = MediascribeSettings(
            output_dir=tmp_path,
            output_formats=["srt", "vtt", "txt", "md", "json"],
        )
        _export_additional_formats(job, settings)
        assert (tmp_path / "video.vtt").exists()
        assert (tmp_path / "video.txt").exists()
        assert (tmp_path / "video.md").exists()
        assert (tmp_path / "video.json").exists()
