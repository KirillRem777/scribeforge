"""Tests for the repetition-loop detector — scribeforge's core differentiator.

These cover the two heuristics in `scribeforge.asr.looks_looped`:
  1. a single line repeated >= LOOP_THRESHOLD times, and
  2. text density (chars per minute) below MIN_DENSITY for the audio length.

No whisper binary or model is needed — the detector reads a plain .txt file.
"""
import os

from scribeforge.asr import (
    LOOP_THRESHOLD,
    MIN_DENSITY,
    _max_repeat,
    looks_looped,
)


def _write(tmp_path, name, text):
    p = os.path.join(str(tmp_path), name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_max_repeat_counts_the_dominant_line(tmp_path):
    p = _write(tmp_path, "loop.txt", ("the\n" * 121) + "real speech here\n")
    assert _max_repeat(p) == 121


def test_max_repeat_ignores_blank_lines(tmp_path):
    p = _write(tmp_path, "blanks.txt", "alpha\n\n\nbeta\n\n")
    assert _max_repeat(p) == 1


def test_max_repeat_empty_file_is_zero(tmp_path):
    p = _write(tmp_path, "empty.txt", "")
    assert _max_repeat(p) == 0


def test_looped_when_a_line_repeats_past_threshold(tmp_path):
    text = "intro line\n" + ("stuck phrase\n" * LOOP_THRESHOLD)
    p = _write(tmp_path, "looped.txt", text)
    # generous duration so density alone would NOT trip it — repetition must
    assert looks_looped(p, duration=1800) is True


def test_clean_dense_transcript_is_not_looped(tmp_path):
    # ~30 unique, content-rich lines over a 1-minute clip → high density, no repeat
    body = "".join(
        f"Sentence number {i} carries some genuine, non-repeating content.\n"
        for i in range(40)
    )
    p = _write(tmp_path, "clean.txt", body)
    assert looks_looped(p, duration=60) is False


def test_looped_when_density_too_low(tmp_path):
    # a few words spread over a long talk → far below MIN_DENSITY, no repeat
    p = _write(tmp_path, "sparse.txt", "a\nb\nc\nd\ne\n")
    assert looks_looped(p, duration=1800) is True


def test_density_threshold_boundary(tmp_path):
    # one minute of audio; put clearly more than MIN_DENSITY chars on unique lines
    text = "".join(f"line {i} padding padding padding\n" for i in range(60))
    p = _write(tmp_path, "dense.txt", text)
    assert os.path.getsize(p) / 1 > MIN_DENSITY
    assert looks_looped(p, duration=60) is False


def test_missing_file_is_not_looped(tmp_path):
    assert looks_looped(os.path.join(str(tmp_path), "nope.txt"), 60) is False
