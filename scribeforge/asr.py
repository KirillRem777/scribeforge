"""Transcribe WAV files with whisper.cpp and auto-repair repetition loops.

whisper large-v3 occasionally falls into a repetition loop: instead of the
real speech it repeats one phrase dozens of times and silently drops the rest
of the talk. This module detects that (a line repeated >= LOOP_THRESHOLD times,
or suspiciously low text density) and re-runs the file with anti-loop flags
(`-mc 0 -et 2.8`) that break the self-feeding context and raise the entropy
threshold for temperature fallback.
"""
from __future__ import annotations

import collections
import os
import shutil
import subprocess

from .sources import Talk

LOOP_THRESHOLD = 4          # a single line repeated this many times == loop
MIN_DENSITY = 650           # chars per minute below this == likely dropped audio


def _require(binary: str) -> str:
    path = shutil.which(binary) or (binary if os.path.exists(binary) else None)
    if not path:
        raise RuntimeError(
            f"`{binary}` not found. Install whisper.cpp (see README) and make "
            f"sure `whisper-cli` is on PATH."
        )
    return path


def _max_repeat(txt_path: str) -> int:
    lines = [l.strip() for l in open(txt_path, encoding="utf-8") if l.strip()]
    if not lines:
        return 0
    return collections.Counter(lines).most_common(1)[0][1]


def looks_looped(txt_path: str, duration: float) -> bool:
    if not os.path.exists(txt_path):
        return False
    if _max_repeat(txt_path) >= LOOP_THRESHOLD:
        return True
    minutes = max(duration / 60, 1)
    density = os.path.getsize(txt_path) / minutes
    return density < MIN_DENSITY


def _run_whisper(whisper: str, model: str, wav: str, out_prefix: str,
                 lang: str, anti_loop: bool) -> None:
    cmd = [whisper, "-m", model, "-f", wav, "-l", lang, "-bs", "5",
           "-otxt", "-of", out_prefix]
    if anti_loop:
        # -mc 0  : do not feed previous text as context (stops loop self-feeding)
        # -et 2.8: raise entropy threshold so low-entropy (repetitive) output
        #          triggers temperature fallback
        cmd += ["-mc", "0", "-et", "2.8"]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_one(talk: Talk, audio_dir: str, model: str, lang: str,
                   whisper_bin: str = "whisper-cli") -> Talk:
    whisper = _require(whisper_bin)
    if not os.path.exists(model):
        raise RuntimeError(
            f"whisper model not found: {model}. Download a ggml model "
            f"(e.g. ggml-large-v3.bin) — see README."
        )
    out_prefix = os.path.join(audio_dir, talk.slug)
    txt = out_prefix + ".txt"

    if not (os.path.exists(txt) and os.path.getsize(txt) > 200):
        _run_whisper(whisper, model, talk.wav, out_prefix, lang, anti_loop=False)

    # Loop guard: detect and re-run once with anti-loop flags.
    if looks_looped(txt, talk.duration):
        _run_whisper(whisper, model, talk.wav, out_prefix, lang, anti_loop=True)

    talk.raw_txt = txt
    return talk
