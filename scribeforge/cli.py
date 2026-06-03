"""scribeforge command-line entry point.

    scribeforge run sources.txt \
        --model ~/models/ggml-large-v3.bin \
        --lang ru \
        --out out/ \
        --title "My Conference" \
        --roster "Jane Speaker, John Doe"

Runs the whole pipeline: fetch -> transcribe (+loop repair) -> polish -> render.
Every step is resumable: re-running skips work whose output already exists.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .sources import parse_sources, save_manifest
from .fetch import fetch_one
from .asr import transcribe_one, looks_looped
from .polish import polish_one, DEFAULT_PROMPT
from .pdf import build_markdown, build_pdf


def _default_model() -> str:
    for p in (os.path.expanduser("~/.cache/whisper/ggml-large-v3.bin"),
              os.path.expanduser("~/models/ggml-large-v3.bin")):
        if os.path.exists(p):
            return p
    return ""


def cmd_run(args: argparse.Namespace) -> int:
    talks = parse_sources(args.sources)
    if not talks:
        print("No talks found in sources file.", file=sys.stderr)
        return 1
    audio_dir = os.path.join(args.out, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    roster = args.roster or ", ".join(
        sorted({t.speaker for t in talks if t.speaker}))
    prompt = DEFAULT_PROMPT
    if args.prompt:
        prompt = open(args.prompt, encoding="utf-8").read()

    n = len(talks)
    for i, talk in enumerate(talks, 1):
        tag = f"[{i}/{n}] {talk.speaker or talk.title or talk.slug}"
        try:
            print(f"{tag}: fetching audio …", flush=True)
            fetch_one(talk, audio_dir)
            print(f"{tag}: transcribing ({talk.duration/60:.0f} min) …", flush=True)
            transcribe_one(talk, audio_dir, args.model, args.lang,
                           whisper_bin=args.whisper)
            if looks_looped(talk.raw_txt, talk.duration):
                print(f"{tag}: WARNING still looks looped after retry", flush=True)
            if not args.no_polish:
                print(f"{tag}: polishing …", flush=True)
                polish_one(talk, audio_dir, model=args.llm_model,
                           base_url=args.base_url, roster=roster,
                           system_prompt=prompt)
        except Exception as exc:  # keep going; report at the end
            print(f"{tag}: ERROR {exc}", file=sys.stderr, flush=True)

    save_manifest(talks, os.path.join(args.out, "manifest.json"))

    done = [t for t in talks if t.clean_md and os.path.exists(t.clean_md)]
    if not done:
        # fall back to raw transcripts so nothing is lost
        for t in talks:
            if t.raw_txt and not t.clean_md:
                t.clean_md = t.raw_txt
        done = [t for t in talks if t.clean_md and os.path.exists(t.clean_md)]

    md = build_markdown(done, args.title, os.path.join(args.out, "transcripts.md"))
    print(f"\nMarkdown: {md}")
    pdf = build_pdf(done, args.title, args.subtitle,
                    os.path.join(args.out, "transcripts.pdf"))
    if pdf:
        print(f"PDF:      {pdf}")
    else:
        print("PDF:      skipped (no Chrome/Chromium found) — Markdown only")
    print(f"Done: {len(done)}/{n} talks.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scribeforge",
                                description="Talks & videos -> clean transcripts.")
    p.add_argument("--version", action="version", version=f"scribeforge {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the full pipeline")
    r.add_argument("sources", help="sources file (see examples/sources.example.txt)")
    r.add_argument("--out", default="out", help="output directory (default: out/)")
    r.add_argument("--model", default=_default_model(),
                   help="path to whisper.cpp ggml model (e.g. ggml-large-v3.bin)")
    r.add_argument("--whisper", default="whisper-cli",
                   help="whisper.cpp binary name/path (default: whisper-cli)")
    r.add_argument("--lang", default="auto", help="language code, e.g. ru/en (default: auto)")
    r.add_argument("--title", default="Transcripts", help="document title")
    r.add_argument("--subtitle", default="Transcripts", help="cover kicker text")
    r.add_argument("--roster", default="",
                   help="comma-separated correct speaker spellings (helps name fixes)")
    r.add_argument("--llm-model", default=os.getenv("SCRIBEFORGE_MODEL", "gpt-4o-mini"),
                   help="LLM model for polishing (default: gpt-4o-mini)")
    r.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL"),
                   help="OpenAI-compatible base URL (e.g. http://localhost:11434/v1)")
    r.add_argument("--prompt", help="path to a custom polish prompt file")
    r.add_argument("--no-polish", action="store_true",
                   help="skip LLM polishing, keep raw transcripts")
    r.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
