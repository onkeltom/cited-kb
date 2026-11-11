#!/usr/bin/env python3
"""Packets: the questions you are learning, gathered from accepted tags."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB, MINING, ROOT, codebook_date, load_categories, load_claims, load_tags  # noqa: E402

PACKETS = MINING / "packets"
REGISTRY = PACKETS / "registry.json"
AUTO_START = "<!-- AUTO-CITES-START -->"
AUTO_END = "<!-- AUTO-CITES-END -->"


def layer1_text() -> str:
    sys.path.insert(0, str(ROOT))
    from domain import layer1  # noqa: WPS433
    return layer1()


def load_registry() -> dict:
    if not REGISTRY.exists():
        sys.exit(f"missing {REGISTRY}")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def packet_path(pid: str, reg: dict | None = None) -> Path:
    reg = reg or load_registry()
    meta = reg["packets"].get(pid)
    if not meta:
        sys.exit(f"unknown packet {pid!r}; known: {', '.join(sorted(reg['packets']))}")
    return PACKETS / meta["file"]


def claim_lookup() -> dict[str, dict]:
    return {c["claim_id"]: c for c in load_claims(kind=None)}


def episode_url(video_id: str) -> str:
    if not DB.exists():
        return ""
    c = sqlite3.connect(DB)
    row = c.execute("SELECT url FROM videos WHERE id=?", (video_id,)).fetchone()
    c.close()
    return (row[0] if row else "") or ""


def accepted_for_categories(categories: list[str], limit: int = 40) -> list[dict]:
    tags = [t for t in load_tags() if t.get("status") == "accepted" and t.get("category_id")]
    if categories:
        want = set(categories)
        tags = [t for t in tags if t["category_id"] in want]
    tags.sort(key=lambda t: (-float(t.get("score") or 0), t.get("claim_id", "")))
    # one row per claim (best category already filtered)
    seen, out = set(), []
    claims = claim_lookup()
    for t in tags:
        cid = t["claim_id"]
        if cid in seen:
            continue
        seen.add(cid)
        cl = claims.get(cid, {})
        out.append({**t, **{k: cl.get(k, "") for k in (
            "text", "at", "guest", "company", "show", "vendor_guest", "sponsored", "video_id"
        )}})
        if len(out) >= limit:
            break
    return out


def none_misfits(limit: int = 40) -> list[dict]:
    """Claims marked status=none (no robust category) — drift / anomaly pool."""
    tags = [t for t in load_tags() if t.get("status") == "none"]
    tags.sort(key=lambda t: t.get("at", t.get("claim_id", "")), reverse=True)
    claims = claim_lookup()
    seen, out = set(), []
    for t in tags:
        cid = t["claim_id"]
        if cid in seen:
            continue
        seen.add(cid)
        cl = claims.get(cid, {})
        out.append({**t, **{k: cl.get(k, "") for k in (
            "text", "at", "guest", "company", "show", "vendor_guest", "sponsored", "video_id"
        )}})
        if len(out) >= limit:
            break
    return out


def format_cite(i: int, row: dict, layer_by_cat: dict | None = None) -> str:
    vid = row.get("video_id") or row["claim_id"].split("@", 1)[0]
    cat = row.get("category_id") or "none"
    layer = (layer_by_cat or {}).get(cat, "?")
    who = row.get("guest") or row.get("show") or "?"
    if row.get("company"):
        who = f"{who}, {row['company']}"
    flags = []
    if row.get("vendor_guest") == "yes":
        flags.append("V")
    if row.get("sponsored") in ("series", "guest", "ads"):
        flags.append(f"S={row['sponsored']}")
    flag_s = (" · " + " ".join(flags)) if flags else ""
    text = (row.get("text") or "").strip()
    if len(text) > 160:
        text = text[:157] + "…"
    url = episode_url(vid)
    lines = [
        f"{i}. **{cat}** (layer {layer}) — {who} · `{vid}` @ {row.get('at', '?')}{flag_s}",
        f"   {text}",
        f"   id: `{row.get('claim_id')}` · tag: `{row.get('tag_id', '')}`",
        f"   verify: `python3 cited.py show {vid} --at {row.get('at', '0:00')} --window 1`",
    ]
    if url:
        lines.append(f"   url: {url}")
    return "\n".join(lines)


def auto_cites_block(pid: str, reg: dict | None = None) -> str:
    reg = reg or load_registry()
    meta = reg["packets"][pid]
    if meta.get("anomaly"):
        rows = none_misfits(limit=meta.get("max_support", 25))
        header = "Claims marked `none` (no category fit). Review before inventing a category.\n\n"
    else:
        rows = accepted_for_categories(meta.get("categories") or [], limit=meta.get("max_support", 10) * 2)
        rows = rows[: meta.get("max_support", 10)]
        header = (
            f"Auto pool from **accepted** tags in {', '.join(meta.get('categories') or [])}. "
            f"Codebook dated {codebook_date()}. "
            "Curate by hand. The pool is not proof.\n\n"
        )
    if not rows:
        body = "_No matching rows yet. Run mine walk / mark none, then refresh._\n"
    else:
        body = "\n\n".join(
            format_cite(i, r, meta.get("layer_by_cat") or {}) for i, r in enumerate(rows, 1)
        ) + "\n"
    vendor_n = sum(1 for r in rows if r.get("vendor_guest") == "yes")
    footer = f"\n_Pool size: {len(rows)}; vendor_guest=yes: {vendor_n}/{len(rows) or 1}_\n"
    return header + body + footer


def upsert_auto_section(text: str, block: str) -> str:
    chunk = f"{AUTO_START}\n## Accepted pool (auto)\n\n{block}{AUTO_END}"
    if AUTO_START in text and AUTO_END in text:
        return re.sub(
            re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END),
            chunk,
            text,
            count=1,
            flags=re.S,
        )
    return text.rstrip() + "\n\n" + chunk + "\n"


def ensure_packet_stub(pid: str, reg: dict | None = None) -> Path:
    reg = reg or load_registry()
    meta = reg["packets"][pid]
    path = PACKETS / meta["file"]
    if path.exists():
        return path
    cats = ", ".join(meta.get("categories") or []) or "(anomaly / none)"
    research = ", ".join(meta.get("research") or []) or "—"
    one_liner = (
        "_Claims that fit no category. Look here before you invent one._"
        if meta.get("anomaly")
        else "_One sentence: the question this packet is for._"
    )
    path.write_text(
        f"""# Packet: {meta['title']}

updated: auto  
status: living  
categories: {cats}  
research: {research}  

## One-liner

{one_liner}

## Support cites (max {meta.get('max_support', 10)})

Prefer cites you would say out loud. Verify with `cited.py show` before quoting.
_Seed from Accepted pool (auto) below after refresh._

## Limits

- What you do not hold yet is in domain/layer1.md.
- A claim that does not fit stays `none`. That is not a new category.

## Your conclusion

- _Empty. This is your learning. The episodes did not write it._

## Changelog

- stub created by `cited packet`

{AUTO_START}
## Accepted pool (auto)

_Run `python3 cited.py packet refresh {pid}`._
{AUTO_END}
""",
        encoding="utf-8",
    )
    return path


def cmd_list(_argv=None):
    reg = load_registry()
    print(f"codebook dated: {codebook_date()}")
    print("what you hold: domain/layer1.md")
    print()
    for pid, meta in sorted(reg["packets"].items()):
        path = PACKETS / meta["file"]
        flag = "ok" if path.exists() else "MISSING"
        cats = ",".join(meta.get("categories") or []) or "anomaly"
        qs = ",".join(meta.get("research") or []) or "-"
        print(f"{pid:22} [{flag}] cats={cats} research={qs}  {meta['title'][:50]}")


def cmd_show(argv):
    if not argv:
        sys.exit("usage: packet show PACKET_ID")
    pid = argv[0]
    reg = load_registry()
    path = ensure_packet_stub(pid, reg)
    print(path.read_text(encoding="utf-8"))


def cmd_refresh(argv):
    if not argv:
        sys.exit("usage: packet refresh PACKET_ID|all")
    reg = load_registry()
    targets = list(reg["packets"]) if argv[0] == "all" else [argv[0]]
    for pid in targets:
        if pid not in reg["packets"]:
            sys.exit(f"unknown packet {pid}")
        path = ensure_packet_stub(pid, reg)
        block = auto_cites_block(pid, reg)
        text = upsert_auto_section(path.read_text(encoding="utf-8"), block)
        path.write_text(text, encoding="utf-8")
        print(f"refreshed {pid} → {path.relative_to(ROOT)}")


def cmd_new(argv):
    if len(argv) < 2:
        sys.exit("usage: packet new ID \"Title\" [--cats G01,G02] [--research Q1]")
    pid, title = argv[0], argv[1]
    cats, research = [], []
    args = argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--cats" and i + 1 < len(args):
            cats = [x.strip() for x in args[i + 1].split(",") if x.strip()]
            i += 2
        elif args[i] == "--research" and i + 1 < len(args):
            research = [x.strip() for x in args[i + 1].split(",") if x.strip()]
            i += 2
        else:
            sys.exit(f"unknown arg {args[i]}")
    reg = load_registry()
    if pid in reg["packets"]:
        sys.exit(f"packet {pid} already exists")
    fname = f"{pid}.md"
    reg["packets"][pid] = {
        "file": fname,
        "title": title,
        "categories": cats,
        "layer_by_cat": {c: 2 for c in cats},
        "research": research,
        "max_support": 10,
        "curated": False,
    }
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ensure_packet_stub(pid, reg)
    cmd_refresh([pid])
    print(f"created {pid}")


def resolve_brief_target(name: str, reg: dict) -> list[str]:
    """Return packet ids for a packet name or Qn key."""
    if name in reg["packets"]:
        return [name]
    q = name.upper() if name.upper().startswith("Q") else name
    if q in reg.get("research_map", {}):
        return list(reg["research_map"][q])
    # allow q6-measurement style already handled; try Q6 from q6
    m = re.fullmatch(r"[Qq](\d+)", name)
    if m:
        key = f"Q{m.group(1)}"
        if key in reg.get("research_map", {}):
            return list(reg["research_map"][key])
    sys.exit(
        f"unknown brief target {name!r}; packets: {', '.join(sorted(reg['packets']))}; "
        f"research: {', '.join(sorted(reg.get('research_map', {})))}"
    )


def cmd_brief(argv):
    """Print a token-small briefing for agents / humans."""
    ap_n = 8
    args = list(argv)
    if args and args[0] == "-n":
        ap_n = int(args[1])
        args = args[2:]
    elif args and args[0].startswith("-n"):
        ap_n = int(args[0][2:])
        args = args[1:]
    if not args:
        sys.exit("usage: brief [-n 8] PACKET_ID|Qn")
    name = args[0]
    reg = load_registry()
    pids = resolve_brief_target(name, reg)

    # corpus denom one-liner
    from corpus_stats import corpus_summary_line  # local helper in mining

    print("=== BRIEF ===")
    print(corpus_summary_line())
    print()
    print(layer1_text())
    print(f"Codebook dated: {codebook_date()}")
    print()
    for pid in pids:
        meta = reg["packets"][pid]
        path = ensure_packet_stub(pid, reg)
        print(f"--- packet: {pid} — {meta['title']} ---")
        print(f"file: {path.relative_to(ROOT)}")
        print(f"categories: {', '.join(meta.get('categories') or []) or 'anomaly/none'}")
        print(f"research Qs: {', '.join(meta.get('research') or []) or '—'}")
        print()
        if meta.get("anomaly"):
            rows = none_misfits(limit=ap_n)
        else:
            rows = accepted_for_categories(meta.get("categories") or [], limit=ap_n)
        if not rows:
            print("_no cites_")
        else:
            for i, r in enumerate(rows, 1):
                print(format_cite(i, r, meta.get("layer_by_cat") or {}))
                print()
        vendor_n = sum(1 for r in rows if r.get("vendor_guest") == "yes")
        print(f"vendor_guest among brief cites: {vendor_n}/{len(rows)}")
        print()
    print("Rules: paraphrase by default; quotes ≤15 words via cited.py show --at; "
          "keep your conclusion separate from what the speakers said.")


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        sys.exit("usage: packets_lib.py list|show|refresh|new|brief ...")
    cmd, rest = argv[0], argv[1:]
    {"list": cmd_list, "show": cmd_show, "refresh": cmd_refresh,
     "new": cmd_new, "brief": cmd_brief}[cmd](rest)


if __name__ == "__main__":
    main()
