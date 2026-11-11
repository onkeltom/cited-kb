#!/usr/bin/env python3
"""Human gate for mining tag candidates. Prevalence only counts accepted.

  python3 cited.py mine walk
  .venv/bin/python mining/review.py walk --limit 25 --min-score 0.55
  .venv/bin/python mining/review.py walk --category G01
  .venv/bin/python mining/review.py walk --include-unclear
  .venv/bin/python mining/review.py list [--status candidate] [-n 20] [--category G01]
  .venv/bin/python mining/review.py show TAG_ID
  .venv/bin/python mining/review.py accept TAG_ID [--by NAME]
  .venv/bin/python mining/review.py reject TAG_ID [--by NAME]
  .venv/bin/python mining/review.py none CLAIM_ID [--by NAME]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DB, important_category_ids, load_calibration, load_categories, load_glosses,
    load_tags, reviewer, save_tags, tag_id, unclear_category_ids, utc_now,
)

WRAP = 88


def claim_row(claim_id: str) -> dict:
    if not DB.exists():
        return {}
    c = sqlite3.connect(DB)
    row = c.execute(
        """SELECT cl.id, cl.video_id, cl.kind, cl.at, cl.text, cl.speaker,
                  v.title, v.channel, v.guest, v.company, v.date, v.url,
                  k.vendor_guest, k.sponsored, k.ai_stance, k.topics
           FROM claims cl
           JOIN videos v ON v.id = cl.video_id
           LEFT JOIN cards k ON k.id = cl.video_id
           WHERE cl.id=?""",
        (claim_id,),
    ).fetchone()
    c.close()
    if not row:
        return {}
    keys = ("claim_id", "video_id", "kind", "at", "text", "speaker", "title", "show",
            "guest", "company", "date", "url", "vendor_guest", "sponsored",
            "ai_stance", "topics")
    return dict(zip(keys, row))


def claim_text(claim_id: str) -> str:
    return claim_row(claim_id).get("text") or ""


def passage(video_id: str, at: str, window: int = 1) -> list[tuple[str, str]]:
    """Return neighbouring transcript paragraphs around at."""
    if not DB.exists() or not video_id or not at:
        return []
    c = sqlite3.connect(DB)
    rows = c.execute(
        "SELECT CAST(start AS INT), text FROM chunks WHERE video_id=? "
        "ORDER BY CAST(start AS INT)",
        (video_id,),
    ).fetchall()
    c.close()
    if not rows:
        return []
    # parse mm:ss
    parts = [int(x) for x in at.split(":")]
    target = 0
    for p in parts:
        target = target * 60 + p
    i = 0
    for j, (start, _) in enumerate(rows):
        if start <= target:
            i = j
    lo = max(0, i - window)
    hi = min(len(rows), i + window + 1)
    out = []
    for start, text in rows[lo:hi]:
        m, s = divmod(int(start), 60)
        h, m = divmod(m, 60)
        stamp = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        out.append((stamp, text))
    return out


def find_tag(rows: list[dict], key: str) -> dict | None:
    for r in rows:
        if r.get("tag_id") == key:
            return r
    hits = [r for r in rows if r.get("tag_id", "").startswith(key) or key in r.get("tag_id", "")]
    if len(hits) == 1:
        return hits[0]
    if hits:
        print("ambiguous; matches:")
        for h in hits[:10]:
            print(f"  {h['tag_id']}")
        sys.exit(1)
    return None


def set_status(tag_key: str, status: str, by: str):
    rows = load_tags()
    r = find_tag(rows, tag_key)
    if not r:
        sys.exit(f"unknown tag {tag_key}")
    r["status"] = status
    r["decided_by"] = by
    r["reviewed_at"] = utc_now()
    save_tags(rows)
    print(f"{status}: {r['tag_id']}")


def mark_none(claim_id: str, by: str, reason: str = ""):
    rows = load_tags()
    for r in rows:
        if r.get("claim_id") == claim_id and r.get("status") == "candidate" and r.get("category_id"):
            r["status"] = "rejected"
            r["decided_by"] = by
            r["reviewed_at"] = utc_now()
    tid = tag_id(claim_id, "none")
    merged = {r["tag_id"]: r for r in rows}
    merged[tid] = {
        "tag_id": tid,
        "claim_id": claim_id,
        "category_id": "",
        "status": "none",
        "method": "human",
        "score": 0.0,
        "rationale": reason or "no robust G-category fits",
        "decided_by": by,
        "at": utc_now(),
        "reviewed_at": utc_now(),
    }
    save_tags(list(merged.values()))


def cmd_list(a):
    rows = load_tags()
    if a.status:
        rows = [r for r in rows if r.get("status") == a.status]
    if a.category:
        rows = [r for r in rows if r.get("category_id") == a.category]
    rows = sorted(rows, key=lambda r: (-float(r.get("score") or 0), r.get("claim_id", "")))
    shown = 0
    for r in rows:
        if shown >= a.n:
            break
        text = claim_text(r["claim_id"])
        cat = r.get("category_id") or "none"
        print(f"[{r.get('score', 0):.2f}] {r['status']:9} {cat:4}  {r['claim_id']}")
        print(f"         {r.get('rationale', '')}")
        if text:
            print(f"         {text[:160]}")
        print(f"         tag_id: {r['tag_id']}")
        shown += 1
    print(f"{shown} shown ({len(rows)} matched)")


def cmd_show(a):
    rows = load_tags()
    r = find_tag(rows, a.tag_id)
    if not r:
        sys.exit(f"unknown tag {a.tag_id}")
    for k in ("tag_id", "claim_id", "category_id", "status", "score", "method",
              "rationale", "decided_by", "at", "reviewed_at", "video_id", "claim_at"):
        if k in r and r[k] not in (None, ""):
            print(f"{k}: {r[k]}")
    text = claim_text(r["claim_id"])
    if text:
        print(f"text: {text}")
    vid = r.get("video_id") or r["claim_id"].split("@", 1)[0]
    at = r.get("claim_at") or ""
    if at:
        print(f"verify: python3 cited.py show {vid} --at {at} --window 1")


def cmd_none(a):
    mark_none(a.claim_id, _by(a.by), a.reason)
    print(f"none: {a.claim_id}")


def _by(name: str | None) -> str:
    return name or reviewer()


def _wrap(label: str, text: str, indent: str = "  "):
    body = textwrap.fill(text, width=WRAP, initial_indent=indent, subsequent_indent=indent)
    print(f"{label}")
    print(body)


def _briefing(unclear: set[str], important: set[str], excluding_unclear: bool):
    print(textwrap.dedent("""
    =====================================================================
    Mining review walk — decide whether a claim fits one of your categories
    =====================================================================

    You are deciding whether a card claim is a fair instance of a category
    you wrote. Candidates were proposed by embedding similarity; they are often
    wrong. Accept only when the claim fits the definition, not merely the topic.

    Keys each turn:
      a  accept this category for this claim
      r  reject this category (claim may still get another category)
         (only when you understand both and it is wrong — if unsure, use s)
      n  none — no category fits; reject sibling candidates too
      s  skip for now
      p  show a wider transcript window
      ?  help
      q  quit and print a session summary

    Prevalence stats only count accepted tags. Vendor guests and sponsored
    episodes get a hard WARNING banner — be stricter before accepting.
    """).strip())
    if unclear:
        ids = ", ".join(sorted(unclear))
        if excluding_unclear:
            print(f"\nUnclear categories excluded from queue: {ids}")
            print("  Pass --include-unclear to review them (default: skip).")
        else:
            print(f"\nUnclear categories (may appear): {ids}")
            print("  Accept only when the quiet/gaming or structure→freedom move is unmistakable.")
    if important:
        print(f"\nImportant categories (starred in cards): {', '.join(sorted(important))}")
    print()


def cmd_walk(a):
    if not sys.stdin.isatty() and not a.yes:
        sys.exit("walk needs an interactive terminal (or pass --yes for scripting)")

    cats = {c["id"]: c for c in load_categories(robust_only=True)}
    calibration = load_calibration()
    glosses = load_glosses()
    unclear = unclear_category_ids(calibration)
    important = important_category_ids(calibration)

    rows = load_tags()
    queue = [
        r for r in rows
        if r.get("status") == "candidate"
        and r.get("category_id")
        and float(r.get("score") or 0) >= a.min_score
    ]
    if a.category:
        queue = [r for r in queue if r["category_id"] == a.category]
    excluded_unclear = 0
    excluding_unclear = not a.include_unclear and not a.category
    if excluding_unclear:
        kept = []
        for r in queue:
            if r["category_id"] in unclear:
                excluded_unclear += 1
            else:
                kept.append(r)
        queue = kept
    # Prefer important categories slightly in sort (still mostly by score)
    queue.sort(
        key=lambda r: (
            0 if r["category_id"] in important else 1,
            -float(r.get("score") or 0),
            r.get("claim_id", ""),
        )
    )
    if a.limit:
        queue = queue[: a.limit]
    if not queue:
        sys.exit("no candidate tags match filters")

    _briefing(unclear, important, excluding_unclear)
    print(f"Queue: {len(queue)} candidates "
          f"(min-score {a.min_score}"
          + (f", category {a.category}" if a.category else "")
          + (", include-unclear" if a.include_unclear else "")
          + ")"
          + (f"; excluded {excluded_unclear} unclear-cat candidates" if excluded_unclear else "")
          + ".\n")

    stats = {"accepted": 0, "rejected": 0, "none": 0, "skipped": 0}
    done_claims_none: set[str] = set()
    i = 0
    while i < len(queue):
        # reload after each write so sibling status stays fresh
        live = {r["tag_id"]: r for r in load_tags()}
        r = live.get(queue[i]["tag_id"], queue[i])
        if r.get("status") != "candidate" or r["claim_id"] in done_claims_none:
            i += 1
            continue

        meta = claim_row(r["claim_id"])
        cat = cats.get(r["category_id"], {})
        siblings = [
            s for s in live.values()
            if s.get("claim_id") == r["claim_id"]
            and s.get("status") == "candidate"
            and s.get("category_id")
            and s["tag_id"] != r["tag_id"]
        ]
        siblings.sort(key=lambda s: -float(s.get("score") or 0))

        vendor = meta.get("vendor_guest") == "yes"
        sponsored = meta.get("sponsored") if meta.get("sponsored") in ("series", "guest", "ads") else ""
        who = ", ".join(x for x in (meta.get("guest"), meta.get("company")) if x) or meta.get("show", "")

        cal = calibration.get(r["category_id"], {})
        gloss = glosses.get(r["category_id"], {})
        is_unclear = r["category_id"] in unclear
        is_important = r["category_id"] in important

        print("=" * 72)
        head = f"[{i + 1}/{len(queue)}]  score {float(r.get('score') or 0):.2f}  →  {r['category_id']}"
        if is_important:
            head += "  ★ IMPORTANT"
        print(head)
        if is_important:
            print("*" * 72)
            print("IMPORTANT CATEGORY")
            print("  Marked in calibration as especially worth getting right for later")
            print("  packets / story. Prefer a clean accept or a clear reject — avoid shrug.")
            print("*" * 72)
        if is_unclear:
            print("~" * 72)
            print("WARNING: UNCLEAR CATEGORY (calibration)")
            note = cal.get("note") or "hard to spot in card claims"
            print(f"  {r['category_id']}: {note}")
            print("  Default advice: skip (s) unless the category move is unmistakable.")
            print("~" * 72)
        if vendor or sponsored:
            print("!" * 72)
            if vendor and sponsored:
                print(f"WARNING: VENDOR GUEST + SPONSORED ({sponsored})")
                print(f"  Guest/company sells HR/AI/work tech or related consulting, and the")
                print(f"  episode is labelled sponsored={sponsored}. Discount product pitches;")
                print(f"  only accept if the claim is still a clean instance of the category.")
            elif vendor:
                print("WARNING: VENDOR GUEST")
                print(f"  {who or 'This guest'} works for a company that sells HR, AI or work")
                print("  technology / related consulting. Treat optimistic claims cautiously;")
                print("  accept only if the move matches the category, not the pitch.")
            else:
                print(f"WARNING: SPONSORED EPISODE ({sponsored})")
                print("  Series partner / guest-as-sponsor / ads. Check the claim is not just")
                print("  a partner narrative before accepting.")
            print("!" * 72)
        print(f"Episode: {meta.get('title') or r.get('video_id')}")
        print(f"         {who}  |  {meta.get('show', '')}  |  {meta.get('date', '')}")
        print(f"Claim @ {meta.get('at') or r.get('claim_at')}  ({meta.get('kind') or r.get('claim_kind')})")
        _wrap("Claim:", meta.get("text") or "(missing claim text)")
        if meta.get("speaker"):
            print(f"  speaker: {meta['speaker']}")
        print()
        print(f"Category {r['category_id']}: {cat.get('name', '?')}")
        if gloss.get("plain"):
            _wrap("Plain:", gloss["plain"])
            if gloss.get("look_for"):
                print(f"  look for: {gloss['look_for']}")
            if gloss.get("not"):
                print(f"  not: {gloss['not']}")
        _wrap("Definition:", cat.get("definition") or "(unknown category)")
        print(f"  rationale: {r.get('rationale', '')}")
        if siblings:
            print("  other candidates on this claim:")
            for s in siblings:
                mark = " ★" if s["category_id"] in important else ""
                u = " ~unclear" if s["category_id"] in unclear else ""
                print(f"    [{float(s.get('score') or 0):.2f}] {s['category_id']}{mark}{u}  "
                      f"{s.get('rationale', '')}")
        print()
        paras = passage(r.get("video_id") or meta.get("video_id", ""),
                        r.get("claim_at") or meta.get("at", ""), window=a.window)
        if paras:
            print("Transcript (verify):")
            for stamp, text in paras:
                snippet = textwrap.shorten(text, width=WRAP - 12, placeholder="…")
                print(f"  [{stamp}] {snippet}")
        else:
            print("  (no transcript chunk found; use cited.py show)")
        print()
        hints = []
        if vendor or sponsored:
            hints.append("vendor/sponsored — be stricter")
        if is_unclear:
            hints.append("unclear cat — prefer s")
        if is_important:
            hints.append("important — decide cleanly")
        prompt = "Decision" + (f" ({'; '.join(hints)})" if hints else "")
        print(f"{prompt}: [a]ccept  [r]eject  [n]one  [s]kip  [p]assage+  [?]  [q]uit")

        while True:
            try:
                choice = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nstopped.")
                choice = "q"
            if choice in ("?", "h", "help"):
                print("  a = this claim is a fair instance of this category")
                print("  r = wrong category (leave claim open for other tags)")
                print("     use r only when you understand both; if unsure → s")
                print("  n = no category fits; reject siblings and mark none")
                print("  s = skip; come back later")
                print("  p = print a wider transcript window")
                print("  q = quit")
                print("  Note: VENDOR / SPONSORED → discount the pitch.")
                print("  UNCLEAR category → prefer s unless the move is obvious.")
                print("  ★ IMPORTANT → worth a clean accept or reject.")
                continue
            if choice == "p":
                wider = passage(r.get("video_id") or meta.get("video_id", ""),
                                r.get("claim_at") or meta.get("at", ""), window=a.window + 2)
                for stamp, text in wider:
                    print(f"  [{stamp}] {textwrap.fill(text, width=WRAP - 4)}")
                continue
            if choice in ("a", "r", "n", "s", "q"):
                break
            print("  enter a, r, n, s, p, ?, or q")

        if choice == "q":
            break
        if choice == "s":
            stats["skipped"] += 1
            i += 1
            continue
        if choice == "a":
            set_status(r["tag_id"], "accepted", _by(a.by))
            stats["accepted"] += 1
            i += 1
            continue
        if choice == "r":
            set_status(r["tag_id"], "rejected", _by(a.by))
            stats["rejected"] += 1
            i += 1
            continue
        if choice == "n":
            mark_none(r["claim_id"], _by(a.by))
            done_claims_none.add(r["claim_id"])
            print(f"none: {r['claim_id']}")
            stats["none"] += 1
            i += 1
            continue

    print()
    print("Session summary:",
          f"accepted={stats['accepted']}",
          f"rejected={stats['rejected']}",
          f"none={stats['none']}",
          f"skipped={stats['skipped']}")
    print("Full prevalence: python3 cited.py mine stats")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("walk", help="interactive 1-by-1 review with claim + category context")
    p.add_argument("--limit", type=int, help="max candidates this session")
    p.add_argument("--min-score", type=float, default=0.55, help="only walk candidates ≥ this score")
    p.add_argument("--category", help="only this category id")
    p.add_argument("--include-unclear", action="store_true",
                   help="include categories marked unclear in domain/calibration.jsonl")
    p.add_argument("--window", type=int, default=1, help="transcript paragraphs each side")
    p.add_argument("--by", default=None, help="name recorded on the decision (default: domain reviewer)")
    p.add_argument("--yes", action="store_true", help="allow non-TTY (for tests)")
    p.set_defaults(fn=cmd_walk)

    p = sub.add_parser("list", help="list tags")
    p.add_argument("--status", default="candidate")
    p.add_argument("--category")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("show", help="show one tag")
    p.add_argument("tag_id")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("accept", help="accept a candidate tag")
    p.add_argument("tag_id")
    p.add_argument("--by", default=None, help="name recorded on the decision")
    p.set_defaults(fn=lambda a: set_status(a.tag_id, "accepted", _by(a.by)))

    p = sub.add_parser("reject", help="reject a candidate tag")
    p.add_argument("tag_id")
    p.add_argument("--by", default=None, help="name recorded on the decision")
    p.set_defaults(fn=lambda a: set_status(a.tag_id, "rejected", _by(a.by)))

    p = sub.add_parser("none", help="mark a claim as matching no robust category")
    p.add_argument("claim_id")
    p.add_argument("--by", default=None, help="name recorded on the decision")
    p.add_argument("--reason", default="")
    p.set_defaults(fn=cmd_none)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
