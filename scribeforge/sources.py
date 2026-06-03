"""Parse a sources file into a list of talk items.

Format (one talk per line, ` | ` separated, last two fields optional):

    https://rutube.ru/video/<id>/        | Jane Speaker      | Opening keynote
    https://youtu.be/<id>                 | John Doe
    https://example.com/talk.mp4

Blank lines and lines starting with `#` are ignored.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict


@dataclass
class Talk:
    url: str
    speaker: str = ""
    title: str = ""
    # filled in by the pipeline:
    slug: str = ""
    wav: str = ""
    raw_txt: str = ""
    clean_md: str = ""
    duration: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def _slugify(text: str, fallback: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"\s+", "-", text)
    return (text[:48] or fallback).strip("-")


def parse_sources(path: str) -> list[Talk]:
    talks: list[Talk] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            url = parts[0]
            speaker = parts[1] if len(parts) > 1 else ""
            title = parts[2] if len(parts) > 2 else ""
            idx = len(talks) + 1  # sequential talk number, not file line number
            base = _slugify(speaker or title, f"talk{idx:02d}")
            talks.append(Talk(url=url, speaker=speaker, title=title,
                              slug=f"{idx:02d}-{base}"))
    return talks


def load_manifest(path: str) -> list[Talk]:
    data = json.load(open(path, encoding="utf-8"))
    return [Talk(**t) for t in data]


def save_manifest(talks: list[Talk], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump([t.to_dict() for t in talks], open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
