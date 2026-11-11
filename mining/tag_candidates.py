#!/usr/bin/env python3
"""Propose category tags for claim bullets. Never auto-accepts.

Uses local BGE embeddings (models/bge-small) plus light keyword overlap.
Run with the project venv:  .venv/bin/python mining/tag_candidates.py ...

  .venv/bin/python mining/tag_candidates.py                 # all claim-kind bullets
  .venv/bin/python mining/tag_candidates.py --episode ID
  .venv/bin/python mining/tag_candidates.py --coded-only    # only if gt/codes is present
  .venv/bin/python mining/tag_candidates.py --uncoded-only
  .venv/bin/python mining/tag_candidates.py --limit 20 --min-score 0.50
  .venv/bin/python mining/tag_candidates.py --write-none   # also record below-threshold as none-candidates
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT, cat_embed_text, coded_episode_ids, load_categories, load_claims,
    load_tags, tag_id, upsert_tags, utc_now,
)

BGE = ROOT / "models" / "bge-small"
TOK = re.compile(r"[a-z']{3,}")
STOP = {
    "the", "and", "for", "that", "with", "from", "this", "into", "onto", "are", "was",
    "were", "been", "being", "have", "has", "had", "not", "but", "they", "their", "them",
    "what", "when", "where", "which", "while", "about", "than", "then", "also", "only",
    "over", "under", "between", "through", "without", "within", "because", "instead",
}


def keywords(text: str) -> set[str]:
    return {t for t in TOK.findall(text.lower()) if t not in STOP}


def keyword_score(claim: str, cat_text: str) -> float:
    a, b = keywords(claim), keywords(cat_text)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def encode(texts: list[str]):
    import numpy as np
    if not BGE.exists():
        sys.exit(f"missing {BGE}; need models/bge-small for candidate tagging")
    sys.path.insert(0, str(ROOT))
    from kbbert import Encoder
    return Encoder(BGE).encode(texts, batch=16)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episode", help="only this episode id")
    ap.add_argument("--kind", default="claim", help="claim|evidence|moment, or 'all'")
    ap.add_argument("--coded-only", action="store_true",
                    help="only episodes listed in gt/codes, when that archive is present")
    ap.add_argument("--uncoded-only", action="store_true",
                    help="skip episodes listed in gt/codes, when that archive is present")
    ap.add_argument("--limit", type=int, help="max claims to consider")
    ap.add_argument("--max-tags", type=int, default=2, help="max category proposals per claim")
    ap.add_argument("--min-score", type=float, default=0.50,
                    help="minimum blended score (0.85*embed + 0.15*keyword)")
    ap.add_argument("--write-none", action="store_true",
                    help="also write none-candidates when nothing clears --min-score")
    ap.add_argument("--force", action="store_true", help="replace existing candidate rows")
    ap.add_argument("--dry-run", action="store_true", help="print proposals; do not write tags.jsonl")
    a = ap.parse_args(argv)

    cats = load_categories(robust_only=True)
    if not cats:
        sys.exit("no robust categories in domain/categories.json")

    kind = None if a.kind == "all" else a.kind
    claims = load_claims(kind=kind, episode=a.episode)
    coded = coded_episode_ids()
    if a.coded_only:
        claims = [c for c in claims if c["video_id"] in coded]
    if a.uncoded_only:
        claims = [c for c in claims if c["video_id"] not in coded]
    if a.limit:
        claims = claims[: a.limit]
    if not claims:
        sys.exit("no claims matched filters (run cited.py reindex first?)")

    existing = load_tags()
    decided_claims = {
        r["claim_id"] for r in existing
        if r.get("status") in ("accepted", "rejected", "none")
    }
    # skip claims that already have a human decision (any category or none)
    pending = [c for c in claims if c["claim_id"] not in decided_claims or a.force]
    if not pending:
        print("nothing to tag: all matching claims already have a human decision")
        return

    cat_texts = [cat_embed_text(c) for c in cats]
    print(f"embedding {len(cats)} categories + {len(pending)} claims …", file=sys.stderr)
    cat_X = encode(cat_texts)
    claim_X = encode([c["text"] for c in pending])

    new_rows = []
    proposed = 0
    nones = 0
    for i, claim in enumerate(pending):
        sims = claim_X[i] @ cat_X.T
        scored = []
        for j, cat in enumerate(cats):
            kw = keyword_score(claim["text"], cat_texts[j])
            # blend: embedding dominates; keyword is a light boost (cap 1.0)
            score = float(min(1.0, 0.85 * float(sims[j]) + 0.15 * kw))
            scored.append((score, float(sims[j]), kw, cat))
        scored.sort(reverse=True, key=lambda x: x[0])
        picks = [s for s in scored if s[0] >= a.min_score][: a.max_tags]
        if not picks:
            nones += 1
            if a.write_none:
                new_rows.append({
                    "tag_id": tag_id(claim["claim_id"], "none"),
                    "claim_id": claim["claim_id"],
                    "category_id": "",
                    "status": "candidate",
                    "method": "bge+keyword",
                    "score": round(float(scored[0][0]), 4) if scored else 0.0,
                    "rationale": f"no category ≥ {a.min_score}; best was "
                                 f"{scored[0][3]['id']} ({scored[0][0]:.2f})" if scored else "no categories",
                    "decided_by": "tag_candidates",
                    "at": utc_now(),
                    "video_id": claim["video_id"],
                    "claim_at": claim["at"],
                    "claim_kind": claim["kind"],
                })
            continue
        for score, sim, kw, cat in picks:
            proposed += 1
            new_rows.append({
                "tag_id": tag_id(claim["claim_id"], cat["id"]),
                "claim_id": claim["claim_id"],
                "category_id": cat["id"],
                "status": "candidate",
                "method": "bge+keyword",
                "score": round(score, 4),
                "rationale": f"{cat['name']} (embed={sim:.2f}, kw={kw:.2f})",
                "decided_by": "tag_candidates",
                "at": utc_now(),
                "video_id": claim["video_id"],
                "claim_at": claim["at"],
                "claim_kind": claim["kind"],
            })

    if a.dry_run:
        for r in new_rows[:30]:
            print(f"{r['status']:9} {r.get('category_id') or 'none':4} {r['score']:.2f}  "
                  f"{r['claim_id']}\n          {r['rationale']}")
        if len(new_rows) > 30:
            print(f"… {len(new_rows) - 30} more")
        print(f"dry-run: {proposed} category proposals, {nones} none-candidates, "
              f"{len(pending)} claims")
        return

    added, skipped = upsert_tags(new_rows, replace_candidates=a.force)
    print(f"wrote candidates: +{added} rows ({skipped} skipped); "
          f"{proposed} category proposals, {nones} none-candidates over {len(pending)} claims")
    print("review with: python3 cited.py mine walk")


if __name__ == "__main__":
    main()
