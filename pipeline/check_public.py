"""Publication check for the rendered site (run by build.py after every render).

Fails if the published pages or CSV headers carry internal references: variable or
dataset codes, file or pipeline words, internal project names, file sizes. Warns about
long sentences in the page copy, which should stay short and direct.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser

import yaml

from .config import SITE_OUT, SITE_SRC

# case-sensitive codes and names, then case-insensitive words
DENY_CODES = [r"migr_", r"\w_ci\b", r"PWGTP", r"PERWT", r"BPLD", r"YRIMMIG", r"OBS_FLAG", r"agedef", r"COMPLET",
              r"FLown", r"HDMF", r"ICFO", r"ICLI", r"I-821", r"Age Shift", r"IDB26", r"LAC33", r"\bGRF\b",
              r"SEGOB", r"SIAMIR", r"\bIGM\b", r"\bPUMS\b", r"\bEU27_2020\b"]
DENY_WORDS = [r"\bparquet\b", r"\bpipeline\b", r"\bextract(ed|s|or)?\b", r"\bfolders?\b", r"\bdecks?\b",
              r"\bscripts?\b", r"\bcache[ds]?\b", r"\d+(\.\d+)?\s?(GB|MB)\b", r"\bsource code\b",
              r"\bbuilt with (python|plotly|jinja|quarto)",
              r"\blast build\b", r"\bwhat we hold\b", r"\bbook draft\b"]
MAX_WORDS = 25


class _Text(HTMLParser):
    """Visible text of a page: skips <script> and <style> (the chart data lives in scripts)."""

    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def _scan(text: str, where: str) -> list[str]:
    hits = []
    for pat in DENY_CODES:
        for m in re.finditer(pat, text):
            hits.append(f"{where}: '{m.group(0)}' … {text[max(0, m.start() - 40):m.end() + 40]!r}")
    for pat in DENY_WORDS:
        for m in re.finditer(pat, text, flags=re.I):
            hits.append(f"{where}: '{m.group(0)}' … {text[max(0, m.start() - 40):m.end() + 40]!r}")
    return hits


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k not in ("href", "id", "accent", "section", "kind", "type"):
                yield from _strings(v)


def long_sentences() -> list[str]:
    out = []
    for f in sorted((SITE_SRC / "content").glob("*.yml")):
        for s in _strings(yaml.safe_load(f.read_text(encoding="utf-8"))):
            for sent in re.split(r"(?<=[.!?])\s+", re.sub(r"<[^>]+>", "", s)):
                n = len(sent.split())
                if n > MAX_WORDS:
                    out.append(f"{f.name}: {n} words: {sent[:90]}…")
    return out


def run() -> int:
    hits = []
    for page in sorted(SITE_OUT.glob("*.html")):
        p = _Text()
        p.feed(page.read_text(encoding="utf-8"))
        hits += _scan(" ".join(p.parts), page.name)
    for csv in sorted((SITE_OUT / "data").glob("*.csv")):
        header = csv.read_text(encoding="utf-8").splitlines()[0]
        hits += _scan(header, f"data/{csv.name} header")
    longs = long_sentences()
    for w in longs:
        print(f"  [check] long sentence: {w}")
    if hits:
        for h in hits:
            print(f"  [check] INTERNAL REFERENCE: {h}")
        print(f"  [check] FAILED: {len(hits)} internal reference(s)")
        return 1
    print(f"  [check] no internal references in {len(list(SITE_OUT.glob('*.html')))} pages and their CSVs; "
          f"{len(longs)} long sentence(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
