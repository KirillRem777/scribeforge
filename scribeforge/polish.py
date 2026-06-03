"""Polish a raw transcript into clean, readable text via an LLM.

Provider-agnostic: talks to any OpenAI-compatible Chat Completions endpoint
(OpenAI, Azure OpenAI, local servers like Ollama / LM Studio / vLLM — anything
that honours `base_url`). Configure via env or CLI:

    OPENAI_API_KEY   (required for hosted providers; any non-empty value for
                      local servers that ignore it)
    OPENAI_BASE_URL  (optional, e.g. http://localhost:11434/v1 for Ollama)
    SCRIBEFORGE_MODEL (optional, default: gpt-4o-mini)
"""
from __future__ import annotations

import os
import textwrap

from .sources import Talk

DEFAULT_PROMPT = textwrap.dedent("""\
    You are an expert transcript editor. The input is a raw automatic
    transcript (from whisper) of a recorded talk. Turn it into clean, readable
    prose WITHOUT losing meaning, facts or figures.

    Rules:
    1. Fix speech-recognition errors in names, terms and titles. Correct
       spellings, if provided, are listed in the context below.
    2. Remove filler words, false starts, stutters and verbatim repetitions.
    3. Add correct punctuation, split into paragraphs, make grammatical
       sentences.
    4. Do NOT add anything of your own. Do not invent or extend facts, numbers
       or claims. This is copy-editing, not summarising or shortening.
    5. Keep every number, percentage, date, name and direct quote exactly.
    6. Preserve the speaker's voice and first-person tone.
    7. Label turns: prefix the main speaker's lines with `**<name>:**`, the
       host/moderator with `**Host:**`, audience with `**Q:**`. If two people
       speak, label both by name.

    Output ONLY the finished, polished transcript in Markdown. No preamble, no
    notes, no list of edits. The first character of your reply is the
    transcript itself. Write in the same language as the input.
""")


def _client(base_url: str | None):
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The `openai` package is required for the polish step. "
            "Install with: pip install openai"
        ) from exc
    kwargs = {}
    if base_url:
        kwargs["base_url"] = base_url
    # API key falls back to OPENAI_API_KEY; local servers accept any value.
    if not os.getenv("OPENAI_API_KEY"):
        kwargs["api_key"] = "sk-local"
    return OpenAI(**kwargs)


def build_context(talk: Talk, roster: str = "") -> str:
    bits = []
    if talk.title:
        bits.append(f"Talk title/track: {talk.title}")
    if talk.speaker:
        bits.append(f"Main speaker: {talk.speaker}")
    if roster:
        bits.append(f"Correct spellings of all speakers: {roster}")
    return "\n".join(bits) or "(no extra context)"


def polish_one(talk: Talk, audio_dir: str, *, model: str, base_url: str | None,
               roster: str = "", system_prompt: str = DEFAULT_PROMPT) -> Talk:
    clean = os.path.join(audio_dir, talk.slug + ".clean.md")
    if os.path.exists(clean) and os.path.getsize(clean) > 200:
        talk.clean_md = clean
        return talk

    raw = open(talk.raw_txt, encoding="utf-8").read()
    context = build_context(talk, roster)
    user_msg = f"## Context\n{context}\n\n## Raw transcript\n{raw}"

    client = _client(base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )
    text = resp.choices[0].message.content.strip()
    open(clean, "w", encoding="utf-8").write(text)
    talk.clean_md = clean
    return talk
