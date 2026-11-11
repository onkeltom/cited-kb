#!/usr/bin/env python3
"""Prevalence and coverage for mining tags. Counts only accepted (unless --all).

  .venv/bin/python mining/stats.py
  .venv/bin/python mining/stats.py --all
  .venv/bin/python mining/stats.py --category G01
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB, load_categories, load_claims, load_tags  # noqa: E402


def episode_meta(video_ids: set[str]) -> dict[str, dict]:
    if not DB.exists() or not video_ids:
        return {}
    c = sqlite3.connect(DB)
    out = {}
    for vid in video_ids:
        row = c.execute(
            """SELECT v.channel, v.guest, v.company, k.vendor_guest, k.sponsored
               FROM videos v LEFT JOIN cards k ON k.id = v.id WHERE v.id=?""",
            (vid,),
        ).fetchone()
        if row:
            out[vid] = {
                "show": row[0] or "", "guest": row[1] or "", "company": row[2] or "",
                "vendor_guest": row[3] or "", "sponsored": row[4] or "",
            }
    c.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="include candidates/rejected in category counts")
    ap.add_argument("--category", help="detail one category")
    ap.add_argument("--drift", action="store_true", help="print codebook drift signals (none-rate, Gaps)")
    a = ap.parse_args(argv)

    if a.drift:
        from corpus_stats import drift_report  # noqa: WPS433
        print(drift_report())
        if not a.category and not a.all:
            return

    tags = load_tags()
    claims = load_claims(kind="claim")
    claim_ids = {c["claim_id"] for c in claims}
    by_status = Counter(r.get("status", "?") for r in tags)
    touched = {r["claim_id"] for r in tags}
    print(f"claim bullets: {len(claims)}")
    print(f"tag rows: {len(tags)}  "
          + ", ".join(f"{s} ({by_status[s]})" for s in ("candidate", "accepted", "rejected", "none") if by_status[s]))
    print(f"claims with any tag row: {len(touched & claim_ids)} / {len(claim_ids)}")
    print(f"claims with no tag row yet: {len(claim_ids - touched)}")

    want = {"accepted"} if not a.all else {"accepted", "candidate"}
    rows = [r for r in tags if r.get("status") in want and r.get("category_id")]
    if a.category:
        rows = [r for r in rows if r["category_id"] == a.category]

    cats = {c["id"]: c for c in load_categories(robust_only=True)}
    by_cat = Counter(r["category_id"] for r in rows)
    vids_by_cat = defaultdict(set)
    for r in rows:
        vid = r.get("video_id") or r["claim_id"].split("@", 1)[0]
        vids_by_cat[r["category_id"]].add(vid)

    print()
    label = "accepted" if not a.all else "accepted+candidate"
    print(f"by category ({label}):")
    for cid in sorted(cats):
        n = by_cat.get(cid, 0)
        eps = len(vids_by_cat.get(cid, ()))
        name = cats[cid]["name"]
        print(f"  {cid}  {n:4d} tags  {eps:3d} eps  {name}")

    meta = episode_meta({vid for s in vids_by_cat.values() for vid in s})
    vendor_tags = sum(
        1 for r in rows
        if meta.get(r.get("video_id") or r["claim_id"].split("@", 1)[0], {}).get("vendor_guest") == "yes"
    )
    if rows:
        print(f"\nvendor_guest=yes among counted tags: {vendor_tags}/{len(rows)} "
              f"({100 * vendor_tags / len(rows):.0f}%)")

    if a.category:
        print(f"\ndetail {a.category}:")
        for r in sorted(rows, key=lambda x: -float(x.get("score") or 0))[:30]:
            print(f"  [{r.get('score', 0):.2f}] {r['status']:9} {r['claim_id']}")
            print(f"           {r.get('rationale', '')}")


if __name__ == "__main__":
    main()
