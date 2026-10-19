"""Download source video, transcribe, let Claude pick highlights, render vertical captioned clips."""
import json
import subprocess
from pathlib import Path

import yt_dlp
from faster_whisper import WhisperModel

from .config import (SOURCES_DIR, CLIPS_DIR, WHISPER_MODEL, CLIP_MIN_SEC, CLIP_MAX_SEC, CLIPS_PER_SOURCE)
from .db import conn
from .llm import ask_json
from .rules import check_clip

HIGHLIGHT_SYSTEM = f"""You choose the best short-form clips from a timestamped transcript.
Return a JSON array of up to {{n}} objects:
{{{{"start": float, "end": float, "title": str, "description": str, "hashtags": [str]}}}}
Rules: each clip {CLIP_MIN_SEC}-{CLIP_MAX_SEC} seconds, starts and ends on sentence boundaries,
self-contained, strong hook in the first 3 seconds. No overlapping clips.
Always include these required hashtags in every clip's hashtags: {{required}}.
{{credit}}"""


def download(url: str) -> Path:
    opts = {
        "outtmpl": str(SOURCES_DIR / "%(id)s.%(ext)s"),
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
        return Path(y.prepare_filename(info)).with_suffix(".mp4")


def transcribe(video: Path) -> list[dict]:
    model = WhisperModel(WHISPER_MODEL, compute_type="int8")
    segs, _ = model.transcribe(str(video), word_timestamps=False, vad_filter=True)
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]


def _srt_ts(t: float) -> str:
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _write_srt(segments: list[dict], start: float, end: float, path: Path):
    lines, i = [], 1
    for s in segments:
        if s["end"] < start or s["start"] > end:
            continue
        a, b = max(s["start"], start) - start, min(s["end"], end) - start
        lines.append(f"{i}\n{_srt_ts(a)} --> {_srt_ts(b)}\n{s['text']}\n")
        i += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def render(video: Path, start: float, end: float, segments: list[dict], out: Path):
    srt = out.with_suffix(".srt")
    _write_srt(segments, start, end, srt)
    style = "FontSize=14,Bold=1,Outline=2,Alignment=2,MarginV=80"
    vf = (
        "crop=ih*9/16:ih,scale=1080:1920,"
        f"subtitles={srt.as_posix()}:force_style='{style}'"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", str(video),
         "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)],
        check=True, capture_output=True,
    )


def process_sources() -> int:
    made = 0
    with conn() as c:
        rows = c.execute(
            "SELECT s.id sid, s.url, s.campaign_id cid, c.rules_json FROM sources s "
            "JOIN campaigns c ON c.id=s.campaign_id WHERE s.status IN ('new','downloaded') AND c.status='rules_ok'"
        ).fetchall()
        for r in rows:
            rules = json.loads(r["rules_json"])
            try:
                video = download(r["url"])
                c.execute("UPDATE sources SET path=?, status='downloaded' WHERE id=?", (str(video), r["sid"]))
                segs = transcribe(video)
                transcript = "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segs)
                system = HIGHLIGHT_SYSTEM.format(
                    n=CLIPS_PER_SOURCE,
                    required=", ".join(rules.get("required_hashtags", [])) or "(none)",
                    credit=f"Mention/credit required: {rules['required_mentions_or_credit']}"
                    if rules.get("required_mentions_or_credit") else "",
                )
                picks = ask_json(system, transcript[:120000])
                for i, p in enumerate(picks):
                    dur = p["end"] - p["start"]
                    caption = f"{p['title']}\n{p['description']}\n{' '.join(p['hashtags'])}"
                    ok, why = check_clip(rules, dur, caption)
                    out = CLIPS_DIR / f"{video.stem}_{i:02d}.mp4"
                    if ok:
                        render(video, p["start"], p["end"], segs, out)
                        made += 1
                    c.execute(
                        "INSERT INTO clips(source_id,campaign_id,path,title,description,hashtags,duration,status) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (r["sid"], r["cid"], str(out), p["title"], p["description"],
                         " ".join(p["hashtags"]), dur, "approved" if ok else f"rejected: {why}"),
                    )
                c.execute("UPDATE sources SET status='clipped' WHERE id=?", (r["sid"],))
                print(f"[clips] {video.name}: {len(picks)} candidates")
            except Exception as e:
                c.execute("UPDATE sources SET status='failed' WHERE id=?", (r["sid"],))
                print(f"[err] {r['url']}: {e}")
    return made
