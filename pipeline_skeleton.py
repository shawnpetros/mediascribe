#!/usr/bin/env python3 -u
"""
Subtitle Pipeline Skeleton
═══════════════════════════
Concatenate clips → extract audio → transcribe (local or API) → translate → review

Usage:
  python pipeline_skeleton.py                  # all episodes, local transcription
  python pipeline_skeleton.py 1                # single episode
  python pipeline_skeleton.py --api            # use OpenAI Whisper API
  python pipeline_skeleton.py --force-transcribe
  python pipeline_skeleton.py --force-translate
  python pipeline_skeleton.py --model gpt-4.1-mini
"""

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import time
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import pysrt
from pysrt import SubRipFile, SubRipItem, SubRipTime
from openai import OpenAI

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent

EPISODES = {
    1: {"concat_file": BASE_DIR / "concat_ep1.txt"},
    # 2: {"concat_file": BASE_DIR / "concat_ep2.txt"},
}

WHISPER_MODEL   = "large-v3"
WHISPER_DEVICE  = "auto"
WHISPER_COMPUTE = "int8"
CHUNK_SEC       = 180
MAX_RETRIES     = 3

DEFAULT_MODEL   = "gpt-4.1"
BATCH_SIZE      = 15
BATCH_OVERLAP   = 2
REVIEW_BATCH    = 20

VOCAB_PROMPT = ""  # domain-specific vocabulary hints for Whisper

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def ts(sec: float) -> str:
    return f"{int(sec // 60):02d}:{int(sec % 60):02d}"

def srt_time(sec: float) -> SubRipTime:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    ms = round((sec - int(sec)) * 1000)
    return SubRipTime(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

def run_cmd(cmd: list[str], desc: str = "") -> None:
    label = desc or " ".join(cmd[:5])
    print(f"\n{'─'*60}\n  {label}\n{'─'*60}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(1)

def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())

def _srt_to_sec(t: SubRipTime) -> float:
    return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000

def fix_subtitle_timing(srt: SubRipFile, min_gap: float = 0.15) -> None:
    """Cap duration to text-appropriate length and ensure gaps between subs."""
    for i, sub in enumerate(srt):
        start = _srt_to_sec(sub.start)
        end = _srt_to_sec(sub.end)
        max_dur = max(1.2, min(len(sub.text.strip()) * 0.15 + 0.8, 7.0))
        if end - start > max_dur:
            end = start + max_dur
            sub.end = srt_time(end)
        if i + 1 < len(srt):
            next_start = _srt_to_sec(srt[i + 1].start)
            if end > next_start - min_gap:
                sub.end = srt_time(max(start + 0.5, next_start - min_gap))

def delete_downstream(ep: int, from_step: str) -> None:
    cascade = {
        "transcribe": [f"Ep{ep}_ja.srt", f"Ep{ep}_en_draft.srt", f"Ep{ep}_en.srt"],
        "translate":  [f"Ep{ep}_en_draft.srt", f"Ep{ep}_en.srt"],
    }
    for fname in cascade.get(from_step, []):
        p = BASE_DIR / fname
        if p.exists():
            p.unlink()
            print(f"  🗑  Deleted {fname}")

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Concatenate clips → single video
# ═══════════════════════════════════════════════════════════════════════════════

def step_concat(ep: int) -> Path:
    out = BASE_DIR / f"Ep{ep}.mp4"
    if out.exists():
        return out
    run_cmd([
        "ffmpeg", "-nostdin", "-f", "concat", "-safe", "0",
        "-i", str(EPISODES[ep]["concat_file"]),
        "-c", "copy", "-movflags", "+faststart", "-y", str(out),
    ], desc=f"Concatenating Ep{ep}")
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Extract audio → 16 kHz mono WAV
# ═══════════════════════════════════════════════════════════════════════════════

def step_extract_audio(mp4: Path, ep: int) -> Path:
    out = BASE_DIR / f"ep{ep}.wav"
    if out.exists():
        return out
    run_cmd([
        "ffmpeg", "-nostdin", "-i", str(mp4),
        "-vn", "-ac", "1", "-ar", "16000", "-y", str(out),
    ], desc=f"Extracting audio → {out.name}")
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Transcribe — chunked local (faster-whisper) or OpenAI API
# ═══════════════════════════════════════════════════════════════════════════════

def validate_segments(segs: list[dict]) -> tuple[bool, str]:
    """Detect hallucination: loops, dominant lines, suspiciously short text."""
    if len(segs) < 4:
        return True, "ok"
    texts = [s["text"] for s in segs]
    run_len, max_run = 1, 1
    for i in range(1, len(texts)):
        if texts[i] == texts[i - 1]:
            run_len += 1
            max_run = max(max_run, run_len)
        else:
            run_len = 1
    if max_run >= 4:
        return False, f"loop: {max_run}× consecutive repeats"
    c = Counter(texts)
    top_text, top_n = c.most_common(1)[0]
    if top_n > len(texts) * 0.35 and len(texts) > 6:
        return False, f"dominant: '{top_text[:30]}…' ({top_n}/{len(texts)})"
    avg_len = sum(len(t) for t in texts) / len(texts)
    if avg_len < 2 and len(texts) > 5:
        return False, f"avg text too short ({avg_len:.1f} chars)"
    return True, "ok"


def _get_whisper_model():
    if not hasattr(_get_whisper_model, "_model"):
        from faster_whisper import WhisperModel
        _get_whisper_model._model = WhisperModel(
            WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE,
        )
    return _get_whisper_model._model


def _transcribe_one_chunk(chunk_path: Path, offset: float, lang: str = "ja",
                          retry: int = 0) -> list[dict]:
    model = _get_whisper_model()
    params = dict(
        language=lang,
        task="transcribe",
        beam_size=10 if retry == 0 else 5,
        temperature=0,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300 + retry * 150, "speech_pad_ms": 200},
        initial_prompt=VOCAB_PROMPT or None,
        word_timestamps=True,
        condition_on_previous_text=(retry == 0),
    )
    if retry > 0:
        params.update(
            no_speech_threshold=0.5,
            log_prob_threshold=-0.8,
            hallucination_silence_threshold=2.0,
        )
    gen, _ = model.transcribe(str(chunk_path), **params)
    segs = []
    for s in gen:
        t = s.text.strip()
        if not t:
            continue
        if s.words:
            seg_start, seg_end = s.words[0].start + offset, s.words[-1].end + offset
        else:
            seg_start, seg_end = s.start + offset, s.end + offset
        segs.append({"start": seg_start, "end": seg_end, "text": t})
    return segs


def step_transcribe_local(wav: Path, ep: int) -> Path:
    out = BASE_DIR / f"Ep{ep}_ja.srt"
    if out.exists():
        return out

    dur = probe_duration(wav)
    n_chunks = int(dur // CHUNK_SEC) + (1 if dur % CHUNK_SEC > 0 else 0)
    print(f"\n  TRANSCRIBE Ep{ep} — local | {ts(dur)} | {n_chunks} chunks\n")

    # Split into chunks
    chunk_dir = BASE_DIR / "_chunks" / f"ep{ep}"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunks, offset, idx = [], 0.0, 0
    while offset < dur:
        cp = chunk_dir / f"c{idx:03d}.wav"
        if not cp.exists():
            subprocess.run(
                ["ffmpeg", "-nostdin", "-i", str(wav),
                 "-ss", str(offset), "-t", str(CHUNK_SEC), "-y", str(cp)],
                capture_output=True,
            )
        chunks.append((cp, offset, idx))
        offset += CHUNK_SEC
        idx += 1

    # Transcribe each chunk with retry on hallucination
    all_segs = []
    for cp, off, ci in chunks:
        segs = None
        for r in range(MAX_RETRIES):
            attempt = _transcribe_one_chunk(cp, off, retry=r)
            ok, reason = validate_segments(attempt)
            if ok:
                segs = attempt
                break
            print(f"  ⚠ Chunk {ci+1} attempt {r+1}: {reason}")
        if segs is None:
            segs = attempt
        all_segs.extend(segs)
        print(f"  Chunk {ci+1}/{len(chunks)}: {len(segs)} segments")

    # Sort + deduplicate at chunk boundaries
    all_segs.sort(key=lambda s: s["start"])
    deduped = []
    for s in all_segs:
        if deduped:
            prev = deduped[-1]
            if s["text"] == prev["text"] and abs(s["start"] - prev["start"]) < 2.0:
                prev["end"] = max(prev["end"], s["end"])
                continue
            if s["text"] == prev["text"] and s["start"] < prev["end"] + 0.5:
                continue
        deduped.append(s)

    # Remove trivial / consecutive-duplicate lines
    clean, prev_text = [], ""
    for s in deduped:
        t = s["text"].strip()
        if not t or t in (",", "。", ".") or t == prev_text:
            continue
        s["text"] = t
        clean.append(s)
        prev_text = t

    # Build SRT
    srt = SubRipFile()
    for i, s in enumerate(clean, 1):
        srt.append(SubRipItem(index=i, start=srt_time(s["start"]),
                              end=srt_time(s["end"]), text=s["text"]))
    fix_subtitle_timing(srt)
    srt.save(str(out), encoding="utf-8")
    print(f"  ✅ {len(srt)} subtitles → {out.name}")

    # Cleanup
    for f in chunk_dir.iterdir():
        f.unlink()
    chunk_dir.rmdir()
    chunks_root = BASE_DIR / "_chunks"
    if chunks_root.exists() and not any(chunks_root.iterdir()):
        chunks_root.rmdir()
    return out


def step_transcribe_api(wav: Path, ep: int) -> Path:
    out = BASE_DIR / f"Ep{ep}_ja.srt"
    if out.exists():
        return out

    dur = probe_duration(wav)
    print(f"\n  TRANSCRIBE Ep{ep} — API (whisper-1) | {ts(dur)}\n")

    # Convert to mp3 to stay under 25 MB upload limit
    mp3 = BASE_DIR / f"_ep{ep}_temp.mp3"
    if not mp3.exists():
        subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(wav),
             "-codec:a", "libmp3lame", "-b:a", "64k", "-y", str(mp3)],
            capture_output=True,
        )

    client = OpenAI()
    with open(mp3, "rb") as f:
        resp = client.audio.transcriptions.create(
            model="whisper-1", file=f, language="ja",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segs = []
    for s in resp.segments:
        text = s["text"].strip() if isinstance(s, dict) else s.text.strip()
        start = s["start"] if isinstance(s, dict) else s.start
        end = s["end"] if isinstance(s, dict) else s.end
        if text:
            segs.append({"start": start, "end": end, "text": text})

    # Deduplicate
    clean, prev_text = [], ""
    for s in segs:
        t = s["text"].strip()
        if not t or t in (",", "。", ".") or t == prev_text:
            continue
        s["text"] = t
        clean.append(s)
        prev_text = t

    srt = SubRipFile()
    for i, s in enumerate(clean, 1):
        srt.append(SubRipItem(index=i, start=srt_time(s["start"]),
                              end=srt_time(s["end"]), text=s["text"]))
    fix_subtitle_timing(srt)
    srt.save(str(out), encoding="utf-8")
    print(f"  ✅ {len(srt)} subtitles → {out.name}")
    mp3.unlink(missing_ok=True)
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Translate (first pass)
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_TRANSLATE = textwrap.dedent("""\
    You are a professional subtitle translator from Japanese to English.
    You receive JSON [{id, text}].
    Return JSON [{id, text}] with English translations.
    Return ONLY the JSON array, no markdown, no explanation.
    Keep lines ≤42 chars when possible.
""")

SYSTEM_REVIEW = textwrap.dedent("""\
    You review English subtitle translations for accuracy and naturalness.
    You receive JSON [{id, ja, en}] — original + draft.
    Fix any mistranslations, awkward phrasing, or consistency issues.
    If a line is already good, keep it as-is.
    Return JSON [{id, text}] with corrected English.
    Return ONLY the JSON array with ALL ids.
""")


def _call_openai(client: OpenAI, model: str, system: str,
                 payload: list, max_tokens: int = 2000,
                 temp: float = 0.3) -> list[dict]:
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        max_output_tokens=max_tokens,
        temperature=temp,
    )
    raw = resp.output_text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def step_translate(ja_srt_path: Path, ep: int, model: str) -> Path:
    out = BASE_DIR / f"Ep{ep}_en_draft.srt"
    if out.exists():
        return out

    print(f"\n  TRANSLATE Ep{ep} — pass 1 ({model})\n")

    client = OpenAI()
    subs = pysrt.open(str(ja_srt_path), encoding="utf-8")
    items = [{"id": i + 1, "text": sub.text.strip()} for i, sub in enumerate(subs)]

    translated = {}
    step = BATCH_SIZE - BATCH_OVERLAP

    for start in range(0, len(items), step):
        batch = items[start : start + BATCH_SIZE]
        try:
            result = _call_openai(client, model, SYSTEM_TRANSLATE, batch)
            for item in result:
                if item["id"] not in translated:
                    translated[item["id"]] = item["text"]
        except (json.JSONDecodeError, KeyError):
            for item in batch:
                if item["id"] not in translated:
                    try:
                        single = _call_openai(client, model, SYSTEM_TRANSLATE, [item])
                        translated[single[0]["id"]] = single[0]["text"]
                    except Exception:
                        translated[item["id"]] = item["text"]

    out_srt = SubRipFile()
    for i, sub in enumerate(subs):
        out_srt.append(SubRipItem(
            index=i + 1, start=sub.start, end=sub.end,
            text=translated.get(i + 1, sub.text),
        ))
    out_srt.save(str(out), encoding="utf-8")
    print(f"  ✓ Draft → {out.name} ({len(out_srt)} subs)")
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Review (second pass)
# ═══════════════════════════════════════════════════════════════════════════════

def step_review(ja_srt_path: Path, draft_path: Path, ep: int, model: str) -> Path:
    out = BASE_DIR / f"Ep{ep}_en.srt"
    if out.exists():
        return out

    print(f"\n  REVIEW Ep{ep} — pass 2 ({model})\n")

    client = OpenAI()
    ja_subs = pysrt.open(str(ja_srt_path), encoding="utf-8")
    en_subs = pysrt.open(str(draft_path), encoding="utf-8")

    pairs = [
        {"id": i + 1, "ja": ja_subs[i].text.strip(), "en": en_subs[i].text.strip()}
        for i in range(min(len(ja_subs), len(en_subs)))
    ]

    reviewed = {}
    for start in range(0, len(pairs), REVIEW_BATCH):
        batch = pairs[start : start + REVIEW_BATCH]
        try:
            result = _call_openai(client, model, SYSTEM_REVIEW, batch, temp=0.2)
            for item in result:
                reviewed[item["id"]] = item["text"]
        except (json.JSONDecodeError, KeyError):
            for item in batch:
                reviewed[item["id"]] = item["en"]

    out_srt = SubRipFile()
    for i, sub in enumerate(ja_subs):
        en = reviewed.get(i + 1, en_subs[i].text if i < len(en_subs) else "")
        out_srt.append(SubRipItem(index=i + 1, start=sub.start, end=sub.end, text=en))
    out_srt.save(str(out), encoding="utf-8")
    print(f"  ✓ Final → {out.name} ({len(out_srt)} subs)")
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def process_episode(ep: int, args: argparse.Namespace) -> None:
    if args.force_transcribe:
        delete_downstream(ep, "transcribe")
    elif args.force_translate:
        delete_downstream(ep, "translate")

    mp4 = step_concat(ep)
    wav = step_extract_audio(mp4, ep)

    if args.api:
        ja_srt = step_transcribe_api(wav, ep)
    else:
        ja_srt = step_transcribe_local(wav, ep)

    draft_srt = step_translate(ja_srt, ep, args.model)
    final_srt = step_review(ja_srt, draft_srt, ep, args.model)

    print(f"\n  ✅ Ep{ep} done — {final_srt.name}")


def main():
    parser = argparse.ArgumentParser(description="Subtitle Pipeline")
    parser.add_argument("episode", nargs="?", default="all")
    parser.add_argument("--api", action="store_true",
                        help="Use OpenAI Whisper API instead of local model")
    parser.add_argument("--force-transcribe", action="store_true")
    parser.add_argument("--force-translate", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    if args.episode == "all":
        for ep in sorted(EPISODES):
            process_episode(ep, args)
    else:
        ep = int(args.episode)
        if ep not in EPISODES:
            sys.exit(f"Unknown episode: {ep}")
        process_episode(ep, args)

    print("\nDone!")


if __name__ == "__main__":
    main()
