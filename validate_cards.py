#!/usr/bin/env python3
"""Validate cards against domain/card.json and their transcripts.
usage: python3 validate_cards.py CARDS_DIR TRANSCRIPTS_DIR [ids...]"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def spec():
    path = ROOT / "domain" / "card.json"
    if not path.exists():
        sys.exit("missing domain/card.json. Run: cp -R domain.example domain")
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", s.lower().replace("’", "'"))).strip()


def fm(text):
    _, f, body = text.split("---\n", 2)
    d = {}
    for line in f.splitlines():
        k, _, v = line.partition(":")
        d[k.strip()] = v.strip().strip('"')
    return d, body


def check(card, tdir, rules):
    probs = []
    try:
        meta, body = fm(card.read_text(encoding="utf-8"))
    except ValueError:
        return ["no frontmatter"]
    for k in rules["required"]:
        if k not in meta:
            probs.append(f"missing {k}")
    for k, allowed in rules["enums"].items():
        if k in meta and meta[k] not in set(allowed):
            probs.append(f"{k}={meta[k]!r}")
    topics = set(rules["topics"])
    tops = [t.strip() for t in meta.get("topics", "").strip("[]").split(",") if t.strip()]
    lo, hi = rules.get("topics_min", 2), rules.get("topics_max", 5)
    if not lo <= len(tops) <= hi or any(t not in topics for t in tops):
        probs.append(f"topics {tops}")
    for h in rules["headings"]:
        if h not in body:
            probs.append(f"heading {h}")
    words = len(re.sub(r"\[\d+(?::\d\d)+\]|^#+.*$", "", body, flags=re.M).split())
    if not rules.get("words_min", 100) <= words <= rules.get("words_max", 320):
        probs.append(f"{words} words")
    src = list(tdir.glob(f"*_{meta.get('id', '???')}.md"))
    if not src:
        return probs + ["transcript not found"]
    tmeta, tbody = fm(src[0].read_text(encoding="utf-8"))
    for k, tk in (("title", "title"), ("show", "channel"), ("guest", "guest"), ("date", "date")):
        if meta.get(k, "") != tmeta.get(tk, ""):
            probs.append(f"{k} differs from transcript")
    stamps = set(re.findall(r"^\[(\d+(?::\d\d)+)\]", tbody, re.M))
    used = re.findall(r"\[(\d+(?::\d\d)+)\]", body)
    bad = [s for s in used if s not in stamps]
    if bad:
        probs.append(f"unknown timestamps {bad}")
    if len(used) < rules.get("timestamps_min", 5):
        probs.append(f"only {len(used)} timestamps")
    ntext = norm(tbody)
    quotes = re.findall(r"\"([^\"]{3,200})\"", body.replace("“", '"').replace("”", '"'))
    if len(quotes) > rules.get("quotes_max", 2):
        probs.append(f"{len(quotes)} quotes")
    for q in quotes:
        if len(q.split()) >= rules.get("quote_words_max", 12):
            probs.append(f"quote too long ({len(q.split())} words)")
        if norm(q) not in ntext:
            probs.append(f"quote not verbatim: {q[:50]!r}")
    return probs


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: python3 validate_cards.py CARDS_DIR TRANSCRIPTS_DIR [ids...]")
    rules = spec()
    cdir, tdir = Path(sys.argv[1]), Path(sys.argv[2])
    ids = sys.argv[3:]
    cards = [cdir / f"{i}.md" for i in ids] if ids else sorted(cdir.glob("*.md"))
    ok = 0
    for c in cards:
        p = check(c, tdir, rules) if c.exists() else ["card missing"]
        if p:
            print(f"FAIL {c.stem}: " + "; ".join(p))
        else:
            ok += 1
    print(f"{ok}/{len(cards)} cards pass")


if __name__ == "__main__":
    main()
