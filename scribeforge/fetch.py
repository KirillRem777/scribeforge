"""Download audio for each talk and normalise to 16 kHz mono WAV.

Uses yt-dlp (any site it supports: YouTube, RuTube, Vimeo, direct files, ...)
and ffmpeg. Both must be on PATH.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from .sources import Talk


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise RuntimeError(
            f"`{binary}` not found on PATH. Install it first "
            f"(see README → Requirements)."
        )
    return path


def probe_duration(wav: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", wav],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def fetch_one(talk: Talk, audio_dir: str) -> Talk:
    ytdlp = _require("yt-dlp")
    ffmpeg = _require("ffmpeg")
    os.makedirs(audio_dir, exist_ok=True)

    wav = os.path.join(audio_dir, talk.slug + ".wav")
    if os.path.exists(wav) and os.path.getsize(wav) > 100_000:
        talk.wav = wav
        talk.duration = talk.duration or probe_duration(wav)
        return talk

    # -x extracts audio; works even when the source is HLS-only (e.g. RuTube),
    # where no standalone audio format exists.
    mp3 = os.path.join(audio_dir, talk.slug + ".mp3")
    subprocess.run(
        [ytdlp, "-x", "--audio-format", "mp3", "--no-warnings",
         "-o", os.path.join(audio_dir, talk.slug + ".%(ext)s"), talk.url],
        check=True,
    )
    if not os.path.exists(mp3):
        raise RuntimeError(f"yt-dlp produced no audio for {talk.url}")

    subprocess.run(
        [ffmpeg, "-y", "-i", mp3, "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", wav],
        check=True, capture_output=True,
    )
    os.remove(mp3)

    talk.wav = wav
    talk.duration = probe_duration(wav)
    return talk
