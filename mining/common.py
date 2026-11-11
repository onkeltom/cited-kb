"""Shared helpers for the mining layer (claim → category tags)."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from domain import DOMAIN, codebook_date, reviewer  # noqa: E402

MINING = Path(__file__).resolve().parent
TAGS = MINING / "tags.jsonl"
CALIBRATION = DOMAIN / "calibration.jsonl"
GLOSSES = DOMAIN / "glosses.json"
CATS = DOMAIN / "categories.json"
DB = ROOT / "cited.sqlite"
ROBUST_PREFIX = "G"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_categories(robust_only: bool = True) -> list[dict]:
    from domain import require
    require("categories.json")
    data = json.loads(CATS.read_text(encoding="utf-8"))
    out = []
    for c in data["categories"]:
        if robust_only and not (c["id"].startswith(ROBUST_PREFIX) and c.get("status") == "robust"):
            continue
        out.append({
            "id": c["id"],
            "name": c["name"],
            "definition": c["definition"],
            "status": c.get("status"),
            "aliases": c.get("aliases") or [],
        })
    return out


def cat_embed_text(c: dict) -> str:
    parts = [c["name"], c["definition"]] + list(c.get("aliases") or [])
    return ". ".join(p for p in parts if p)


def load_calibration() -> dict[str, dict]:
    """clear/fuzzy/unclear ratings from domain/calibration.jsonl."""
    if not CALIBRATION.exists():
        return {}
    out = {}
    for line in CALIBRATION.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[row["id"]] = row
    return out


def load_glosses() -> dict[str, dict]:
    if not GLOSSES.exists():
        return {}
    return json.loads(GLOSSES.read_text(encoding="utf-8"))


def unclear_category_ids(calibration: dict[str, dict] | None = None) -> set[str]:
    cal = calibration if calibration is not None else load_calibration()
    return {cid for cid, row in cal.items() if row.get("rating") == "unclear"}


def important_category_ids(calibration: dict[str, dict] | None = None) -> set[str]:
    cal = calibration if calibration is not None else load_calibration()
    out = set()
    for cid, row in cal.items():
        note = (row.get("note") or "").lower()
        if "important" in note or row.get("important"):
            out.add(cid)
    return out


def load_tags() -> list[dict]:
    if not TAGS.exists():
        return []
    rows = []
    for line in TAGS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def save_tags(rows: list[dict]) -> None:
    TAGS.parent.mkdir(parents=True, exist_ok=True)
    with TAGS.open("w", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda x: (x.get("claim_id", ""), x.get("category_id") or "")):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def upsert_tags(new_rows: list[dict], replace_candidates: bool = False) -> tuple[int, int]:
    """Merge new rows into tags.jsonl. Returns (added, skipped)."""
    existing = load_tags()
    by_id = {r["tag_id"]: r for r in existing}
    added = skipped = 0
    for r in new_rows:
        tid = r["tag_id"]
        old = by_id.get(tid)
        if old is None:
            by_id[tid] = r
            added += 1
            continue
        if old.get("status") in ("accepted", "rejected", "none"):
            skipped += 1
            continue
        if replace_candidates and old.get("status") == "candidate":
            by_id[tid] = r
            added += 1
        else:
            skipped += 1
    save_tags(list(by_id.values()))
    return added, skipped


def tag_id(claim_id: str, category_id: str) -> str:
    return f"{claim_id}|{category_id or 'none'}"


def load_claims(kind: str | None = "claim", episode: str | None = None) -> list[dict]:
    if not DB.exists():
        sys.exit("no cited.sqlite; run: python3 cited.py reindex")
    c = sqlite3.connect(DB)
    where, params = ["1=1"], []
    if kind:
        where.append("cl.kind = ?")
        params.append(kind)
    if episode:
        where.append("cl.video_id = ?")
        params.append(episode)
    sql = f"""SELECT cl.id, cl.video_id, cl.kind, cl.at, cl.text, cl.speaker,
                     v.guest, v.company, v.channel, v.date, v.tags,
                     k.topics, k.ai_stance, k.vendor_guest, k.sponsored
              FROM claims cl
              JOIN videos v ON v.id = cl.video_id
              LEFT JOIN cards k ON k.id = cl.video_id
              WHERE {' AND '.join(where)}
              ORDER BY v.date DESC, cl.start"""
    rows = []
    for r in c.execute(sql, params):
        rows.append({
            "claim_id": r[0], "video_id": r[1], "kind": r[2], "at": r[3], "text": r[4],
            "speaker": r[5] or "", "guest": r[6] or "", "company": r[7] or "",
            "show": r[8] or "", "date": r[9] or "", "tags": r[10] or "",
            "topics": r[11] or "", "ai_stance": r[12] or "",
            "vendor_guest": r[13] or "", "sponsored": r[14] or "",
        })
    c.close()
    return rows


def coded_episode_ids() -> set[str]:
    codes = ROOT / "gt" / "codes"
    if not codes.exists():
        return set()
    return {p.stem for p in codes.glob("*.jsonl")}
