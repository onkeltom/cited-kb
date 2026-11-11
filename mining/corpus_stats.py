#!/usr/bin/env python3
"""Corpus denominators + drift signals (shared by cited corpus / mine stats)."""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB, ROOT, codebook_date, coded_episode_ids, load_tags  # noqa: E402

CDIR = ROOT / "cards"
TDIR = ROOT / "transcripts"


def _kept(tags: str) -> bool:
    tset = {x.strip() for x in (tags or "").split(",") if x.strip()}
    return "personal" not in tset and "fixture" not in tset


def analysis_eligible_ids() -> set[str]:
    ids = set()
    if not TDIR.exists():
        return ids
    for p in TDIR.glob("*.md"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            continue
        try:
            _, fm, _ = text.split("---\n", 2)
        except ValueError:
            continue
        vid, tags = None, ""
        for line in fm.splitlines():
            if line.startswith("id:"):
                vid = line.split(":", 1)[1].strip()
            if line.startswith("tags:"):
                tags = line.split(":", 1)[1].strip()
        if vid and _kept(tags.strip("[]")):
            ids.add(vid)
    return ids


def card_ids() -> set[str]:
    if not CDIR.exists():
        return set()
    return {p.stem for p in CDIR.glob("*.md")}


def gaps_sample(limit: int = 12) -> list[str]:
    """Pull ## Gaps bullets from cards — first-class drift signals."""
    out = []
    if not CDIR.exists():
        return out
    for p in sorted(CDIR.glob("*.md")):
        body = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"## Gaps\s*\n(.*?)(?:\n## |\Z)", body, re.S)
        if not m:
            continue
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                out.append(f"{p.stem}: {line[2:].strip()}")
                if len(out) >= limit:
                    return out
    return out


def drift_report() -> str:
    tags = load_tags()
    by_status = Counter(t.get("status", "?") for t in tags)
    accepted = [t for t in tags if t.get("status") == "accepted"]
    none_rows = [t for t in tags if t.get("status") == "none"]
    candidates = [t for t in tags if t.get("status") == "candidate"]
    lines = [
        "=== codebook drift signals ===",
        f"tag rows: {len(tags)}  "
        + ", ".join(f"{s} ({by_status[s]})" for s in ("candidate", "accepted", "rejected", "none") if by_status[s]),
    ]
    # none rate among decided (accepted+rejected+none)
    decided = by_status["accepted"] + by_status["rejected"] + by_status["none"]
    if decided:
        lines.append(
            f"none among decided tags: {by_status['none']}/{decided} "
            f"({100 * by_status['none'] / decided:.1f}%)"
        )
    lines.append(f"open candidates still in queue: {len(candidates)}")
    lines.append(f"accepted tags: {len(accepted)}; none-marked claims (unique): "
                 f"{len({t['claim_id'] for t in none_rows})}")

    # per-category accept vs reject for robust cats
    ar = defaultdict(lambda: Counter())
    for t in tags:
        cid = t.get("category_id")
        if not cid:
            continue
        ar[cid][t.get("status", "?")] += 1
    lines.append("accept/reject by category (top churn):")
    scored = []
    for cid, ctr in ar.items():
        a, r = ctr.get("accepted", 0), ctr.get("rejected", 0)
        if a + r >= 5:
            scored.append((r / (a + r), cid, a, r))
    for rate, cid, a, r in sorted(scored, reverse=True)[:8]:
        lines.append(f"  {cid}: accepted {a}, rejected {r} (reject rate {100 * rate:.0f}%)")

    lines.append(f"codebook dated: {codebook_date()}")
    lines.append("Write the decision down: hold, clarify a definition, or add a provisional category.")
    lines.append("anomaly packet: python3 cited.py packet refresh anomaly && python3 cited.py brief anomaly")
    gaps = gaps_sample(8)
    if gaps:
        lines.append("sample Gaps (card drift signals):")
        for g in gaps:
            lines.append(f"  - {g[:120]}")
    return "\n".join(lines)


def corpus_report(with_drift: bool = False) -> str:
    eligible = analysis_eligible_ids()
    cards = card_ids()
    codes_dir = ROOT / "gt" / "codes"
    coded = len(coded_episode_ids()) if codes_dir.is_dir() else None
    lines = ["=== cited corpus denominators ==="]
    if not DB.exists():
        lines.append("cited.sqlite missing — run: python3 cited.py reindex")
        lines.append(f"transcripts fetched (files): {len(eligible)}")
        lines.append(f"cards on disk: {len(cards)}")
        if coded is not None:
            lines.append(f"open-coding archive (gt/codes): {coded}")
        return "\n".join(lines)

    c = sqlite3.connect(DB)
    db_eligible = 0
    for (tags,) in c.execute("SELECT tags FROM videos"):
        if _kept(tags):
            db_eligible += 1
    card_n = 0
    for (tags,) in c.execute(
        "SELECT v.tags FROM cards k JOIN videos v ON v.id = k.id"
    ):
        if _kept(tags):
            card_n += 1
    kept_ids = [vid for vid, tags in c.execute("SELECT id, tags FROM videos") if _kept(tags)]
    if kept_ids:
        marks = ",".join("?" * len(kept_ids))
        claims_n = c.execute(
            f"SELECT COUNT(*) FROM claims WHERE video_id IN ({marks})", kept_ids
        ).fetchone()[0]
        by_kind = dict(c.execute(
            f"SELECT kind, COUNT(*) FROM claims WHERE video_id IN ({marks}) GROUP BY kind",
            kept_ids,
        ).fetchall())
    else:
        claims_n, by_kind = 0, {}
    fixture_n = sum(
        1 for (tags,) in c.execute("SELECT tags FROM videos")
        if "fixture" in {x.strip() for x in (tags or "").split(",") if x.strip()}
    )

    shows = Counter()
    for ch, tags in c.execute("SELECT channel, tags FROM videos"):
        if _kept(tags):
            shows[ch or "?"] += 1

    tags = load_tags()
    by_status = Counter(t.get("status", "?") for t in tags)
    accepted = by_status.get("accepted", 0)
    # vendor share among accepted
    vendor_acc = 0
    if accepted:
        for t in tags:
            if t.get("status") != "accepted":
                continue
            vid = t.get("video_id") or t["claim_id"].split("@", 1)[0]
            row = c.execute(
                "SELECT vendor_guest FROM cards WHERE id=?", (vid,)
            ).fetchone()
            if row and row[0] == "yes":
                vendor_acc += 1
    c.close()

    kind_s = ", ".join(
        f"{k} {by_kind.get(k, 0)}" for k in ("claim", "evidence", "moment") if k in by_kind
    )
    lines += [
        f"fetched for study:        {db_eligible}  (files≈{len(eligible)}; excludes personal and the fixture)",
        f"shows:                    {len(shows)}",
        f"cards:                    {card_n}  (on disk {len(cards)}; still to card {max(0, db_eligible - card_n)})",
        f"claims:                   {claims_n}" + (f"  ({kind_s})" if kind_s else ""),
        f"synthetic fixture:        {fixture_n}  (indexed so search works; not part of these counts)",
    ]
    if coded is not None:
        lines.append(f"open-coding archive:      {coded}  (gt/codes; not part of ordinary study)")
    lines += [
        f"mining tags:              {len(tags)}  "
        + ", ".join(f"{s} {by_status[s]}" for s in ("candidate", "accepted", "rejected", "none") if by_status[s]),
        f"accepted tags:            {accepted}"
        + (f"  (vendor_guest {vendor_acc}/{accepted} = {100 * vendor_acc / accepted:.0f}%)" if accepted else ""),
        f"codebook dated:           {codebook_date()}",
        "",
        "Do not mix: episodes fetched ≠ cards written ≠ accepted tags.",
        "What you currently hold is domain/layer1.md.",
    ]
    if with_drift:
        lines.append("")
        lines.append(drift_report())
    return "\n".join(lines)


def corpus_summary_line() -> str:
    """One line for briefs."""
    if not DB.exists():
        return "corpus: (no cited.sqlite)"
    c = sqlite3.connect(DB)
    eligible = 0
    for (tags,) in c.execute("SELECT tags FROM videos"):
        if _kept(tags):
            eligible += 1
    kept_ids = [vid for vid, tags in c.execute("SELECT id, tags FROM videos") if _kept(tags)]
    if kept_ids:
        marks = ",".join("?" * len(kept_ids))
        claims_n = c.execute(
            f"SELECT COUNT(*) FROM claims WHERE video_id IN ({marks})", kept_ids
        ).fetchone()[0]
    else:
        claims_n = 0
    c.close()
    accepted = sum(1 for t in load_tags() if t.get("status") == "accepted")
    extra = ""
    if (ROOT / "gt" / "codes").is_dir():
        extra = f"; open-coding={len(coded_episode_ids())}"
    return (
        f"denoms: fetched={eligible}{extra}; claims={claims_n}; accepted-tags={accepted}"
    )
