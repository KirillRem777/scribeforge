"""Assemble polished transcripts into one document.

Always writes a combined Markdown file. If a Chrome/Chromium binary is found,
also renders a clean branded PDF (headless --print-to-pdf) — Chrome handles any
script/alphabet (Cyrillic, CJK, ...) perfectly.
"""
from __future__ import annotations

import html as H
import os
import shutil
import subprocess

from .sources import Talk

CHROME_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        p = shutil.which(c) if "/" not in c else (c if os.path.exists(c) else None)
        if p:
            return p
    return None


def _md_to_html(md: str) -> str:
    try:
        import markdown
        return markdown.markdown(md)
    except ImportError:
        import re
        t = H.escape(md)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        return "".join(f"<p>{p.strip()}</p>" for p in t.split("\n\n") if p.strip())


def _fmt_dur(s: float) -> str:
    s = int(s or 0)
    return f"{s // 60} min {s % 60:02d} sec"


CSS = """
@page { size: A4; margin: 22mm 20mm; }
* { box-sizing: border-box; }
body { font-family: 'PT Serif', Georgia, serif; color:#1f2937; font-size:11.5pt; line-height:1.62; }
h1,h2,.talk-head .sp,strong { font-family:'Inter','Helvetica Neue',Arial,sans-serif; }
.cover { height:247mm; display:flex; flex-direction:column; justify-content:center; page-break-after:always; }
.cover .kick { font-family:'Inter',sans-serif; font-weight:700; letter-spacing:.16em; text-transform:uppercase; font-size:11pt; color:#6b7280; }
.cover h1 { font-size:32pt; font-weight:800; margin:14px 0 8px; letter-spacing:-.01em; }
.cover .dot { color:#e11d48; }
.cover .sub { font-size:13pt; color:#4b5563; max-width:150mm; }
.hair { height:2px; background:#e11d48; width:64px; margin:18px 0; }
.toc { page-break-after:always; }
.toc h2 { font-size:15pt; text-transform:uppercase; letter-spacing:.02em; }
.toc ul { list-style:none; padding:0; }
.toc li { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #e5e7eb; font-family:'Inter',sans-serif; font-size:10pt; }
.toc .du { color:#9ca3af; }
.talk { page-break-inside:auto; }
.talk-head { border-left:3px solid #e11d48; padding-left:12px; margin:26px 0 10px; }
.talk-head .sp { font-weight:700; font-size:14pt; }
.talk-head .du { font-family:'Inter',sans-serif; font-size:8.5pt; letter-spacing:.05em; text-transform:uppercase; color:#9ca3af; margin-top:3px; }
.talk-head .ti { font-family:'Inter',sans-serif; font-size:9pt; color:#6b7280; margin-top:2px; }
.body p { margin:0 0 10px; text-align:justify; }
.foot { margin-top:28px; padding-top:8px; border-top:1px solid #e5e7eb; font-family:'Inter',sans-serif; font-size:8pt; color:#9ca3af; text-align:center; }
"""


def _render_html(talks: list[Talk], title: str, subtitle: str) -> str:
    fonts = ('<link href="https://fonts.googleapis.com/css2?'
             'family=Inter:wght@400;700;800&family=PT+Serif:ital,wght@0,400;0,700;1,400'
             '&display=swap" rel="stylesheet">')
    cover = (f'<section class="cover"><div class="kick">{H.escape(subtitle)}</div>'
             f'<div class="hair"></div><h1>{H.escape(title)}<span class="dot">.</span></h1>'
             f'<div class="sub">Full text transcripts of {len(talks)} recorded talks.</div></section>')
    toc_items = "".join(
        f'<li><span>{H.escape(t.speaker or t.title or t.slug)}</span>'
        f'<span class="du">{_fmt_dur(t.duration)}</span></li>' for t in talks)
    toc = f'<section class="toc"><h2>Contents</h2><ul>{toc_items}</ul></section>'
    sections = ""
    for t in talks:
        body = _md_to_html(open(t.clean_md, encoding="utf-8").read())
        ti = f'<div class="ti">{H.escape(t.title)}</div>' if t.title else ""
        sections += (
            f'<div class="talk"><div class="talk-head">'
            f'<div class="sp">{H.escape(t.speaker or t.title or "Talk")}</div>{ti}'
            f'<div class="du">{_fmt_dur(t.duration)}</div></div>'
            f'<div class="body">{body}</div></div>')
    foot = f'<div class="foot">{H.escape(title)} — generated with scribeforge</div>'
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts}'
            f'<style>{CSS}</style></head><body>{cover}{toc}{sections}{foot}</body></html>')


def build_markdown(talks: list[Talk], title: str, out_md: str) -> str:
    parts = [f"# {title}\n"]
    for t in talks:
        head = t.speaker or t.title or t.slug
        parts.append(f"\n## {head}")
        if t.title and t.title != head:
            parts.append(f"*{t.title}*")
        parts.append(f"_{_fmt_dur(t.duration)}_\n")
        parts.append(open(t.clean_md, encoding="utf-8").read())
        parts.append("\n---")
    os.makedirs(os.path.dirname(out_md) or ".", exist_ok=True)
    open(out_md, "w", encoding="utf-8").write("\n".join(parts))
    return out_md


def build_pdf(talks: list[Talk], title: str, subtitle: str, out_pdf: str) -> str | None:
    chrome = _find_chrome()
    if not chrome:
        return None
    html_path = out_pdf.replace(".pdf", ".html")
    open(html_path, "w", encoding="utf-8").write(_render_html(talks, title, subtitle))
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={out_pdf}", "file://" + os.path.abspath(html_path)],
        check=True, capture_output=True,
    )
    return out_pdf if os.path.exists(out_pdf) else None
