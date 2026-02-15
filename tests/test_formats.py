"""Tests for VTT and JSON export format handlers.

Covers:
- VTT timestamp formatting
- segments_to_vtt output
- VTT with translations
- save_vtt file I/O
- JSON export structure
- JSON with all optional fields
- save_json file I/O
"""

import json
import pytest
from pathlib import Path

from mediascribe.core.job import Job, MediaInfo, MediaType, Segment
from mediascribe.formats.vtt import _vtt_timestamp, segments_to_vtt, save_vtt
from mediascribe.formats.json_export import job_to_json, save_json


# ── VTT Timestamps ──────────────────────────────────────────────────────────

class TestVttTimestamp:
    def test_zero(self):
        assert _vtt_timestamp(0.0) == "00:00:00.000"

    def test_simple(self):
        assert _vtt_timestamp(5.5) == "00:00:05.500"

    def test_minutes(self):
        assert _vtt_timestamp(125.0) == "00:02:05.000"

    def test_hours(self):
        assert _vtt_timestamp(3661.5) == "01:01:01.500"

    def test_milliseconds(self):
        assert _vtt_timestamp(0.123) == "00:00:00.123"


# ── segments_to_vtt ─────────────────────────────────────────────────────────

class TestSegmentsToVtt:
    def test_basic_output(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=3.0, end=5.0, text="World"),
        ]
        vtt = segments_to_vtt(segs)
        assert vtt.startswith("WEBVTT")
        assert "Hello" in vtt
        assert "World" in vtt
        assert "00:00:00.000 --> 00:00:02.000" in vtt

    def test_empty_text_filtered(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="Hello"),
            Segment(index=2, start=3.0, end=5.0, text="  "),
        ]
        vtt = segments_to_vtt(segs)
        assert "Hello" in vtt
        assert vtt.count("-->") == 1  # only one cue

    def test_translation_mode(self):
        segs = [
            Segment(index=1, start=0.0, end=2.0, text="こんにちは",
                    translation="Hello"),
        ]
        vtt = segments_to_vtt(segs, use_translation=True)
        assert "Hello" in vtt
        assert "こんにちは" not in vtt

    def test_empty_list(self):
        vtt = segments_to_vtt([])
        assert vtt.startswith("WEBVTT")
        assert "-->" not in vtt


class TestSaveVtt:
    def test_file_written(self, tmp_path: Path):
        segs = [Segment(index=1, start=0.0, end=2.0, text="Test")]
        path = tmp_path / "test.vtt"
        save_vtt(segs, path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "WEBVTT" in content
        assert "Test" in content


# ── JSON Export ──────────────────────────────────────────────────────────────

def _make_job(tmp_path: Path) -> Job:
    f = tmp_path / "video.mp4"
    f.touch()
    job = Job(input_path=f, output_dir=tmp_path / "out")
    job.media_info = MediaInfo(
        media_type=MediaType.VIDEO,
        duration_sec=120.0,
        language="ja",
    )
    job.segments = [
        Segment(index=1, start=0.0, end=2.0, text="こんにちは",
                translation="Hello", confidence=0.95),
        Segment(index=2, start=3.0, end=5.0, text="世界",
                translation="World", speaker="Speaker 1"),
    ]
    return job


class TestJobToJson:
    def test_structure(self, tmp_path: Path):
        job = _make_job(tmp_path)
        data = job_to_json(job)

        assert "metadata" in data
        assert "segments" in data
        assert "analysis" in data

    def test_metadata(self, tmp_path: Path):
        job = _make_job(tmp_path)
        data = job_to_json(job)
        meta = data["metadata"]

        assert meta["source_file"] == "video.mp4"
        assert meta["duration_sec"] == 120.0
        assert meta["source_language"] == "ja"
        assert meta["media_type"] == "video"
        assert "processed_at" in meta

    def test_segments(self, tmp_path: Path):
        job = _make_job(tmp_path)
        data = job_to_json(job)
        segs = data["segments"]

        assert len(segs) == 2
        assert segs[0]["text"] == "こんにちは"
        assert segs[0]["translation"] == "Hello"
        assert segs[0]["confidence"] == 0.95
        assert segs[1]["speaker"] == "Speaker 1"

    def test_empty_segments(self, tmp_path: Path):
        f = tmp_path / "empty.mp4"
        f.touch()
        job = Job(input_path=f, output_dir=tmp_path)
        data = job_to_json(job)
        assert data["segments"] == []

    def test_analysis_included(self, tmp_path: Path):
        job = _make_job(tmp_path)
        job.analysis = {"summary": "A test video", "topics": ["greeting"]}
        data = job_to_json(job)
        assert data["analysis"]["summary"] == "A test video"


class TestSaveJson:
    def test_file_written(self, tmp_path: Path):
        job = _make_job(tmp_path)
        path = tmp_path / "output.json"
        save_json(job, path)

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["metadata"]["source_file"] == "video.mp4"
        assert len(data["segments"]) == 2

    def test_unicode_preserved(self, tmp_path: Path):
        job = _make_job(tmp_path)
        path = tmp_path / "unicode.json"
        save_json(job, path)

        content = path.read_text(encoding="utf-8")
        assert "こんにちは" in content  # ensure_ascii=False
