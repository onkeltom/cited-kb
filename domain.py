"""Load the domain pack (copy domain.example to domain/ and edit)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAIN = ROOT / "domain"


def require(*names: str) -> None:
    missing = [n for n in names if not (DOMAIN / n).exists()]
    if missing:
        sys.exit(
            "missing "
            + ", ".join(f"domain/{n}" for n in missing)
            + ". Run: cp -R domain.example domain"
        )


def categories() -> dict:
    require("categories.json")
    return json.loads((DOMAIN / "categories.json").read_text(encoding="utf-8"))


def card_spec() -> dict:
    require("card.json")
    return json.loads((DOMAIN / "card.json").read_text(encoding="utf-8"))


def layer1() -> str:
    require("layer1.md")
    return (DOMAIN / "layer1.md").read_text(encoding="utf-8").strip()


def whisper_prompt() -> str:
    path = DOMAIN / "whisper_prompt.txt"
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    print(
        "no domain/whisper_prompt.txt — using a generic prompt. "
        "Copy domain.example and add the names in your field.",
        file=sys.stderr,
    )
    return "A recorded conversation."


def reviewer() -> str:
    if (DOMAIN / "categories.json").exists():
        name = (categories().get("reviewer") or "").strip()
        if name:
            return name
    return "you"


def codebook_date() -> str:
    if (DOMAIN / "categories.json").exists():
        return categories().get("as_of") or "?"
    return "?"
