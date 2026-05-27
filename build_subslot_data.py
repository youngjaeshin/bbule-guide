#!/usr/bin/env python3
"""Build web/data_subslot.json and inline SUBSLOT_DATA from extracted output."""

from __future__ import annotations

import json
import re
from pathlib import Path

from build_mercenary_data import normalize_effect_text

BASE = Path(__file__).resolve().parent
INPUT_JSON = BASE / "output" / "sub_slot_troops.json"
OUTPUT_JSON = BASE / "web" / "data_subslot.json"
INDEX_HTML = BASE / "web" / "index.html"


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_entries(rows: list[dict]) -> list[dict]:
    entries = []
    for row in rows:
        effects = [
            normalize_effect_text(effect.get("description", ""))
            for effect in row.get("effects_resolved", [])
            if effect.get("description")
        ]
        entries.append({
            "index": row["index"],
            "name": row.get("name", ""),
            "desc": row.get("description", ""),
            "icon": row.get("icon", 0),
            "effects": effects,
        })
    return entries


def replace_inline_subslot_data(entries: list[dict]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    compact = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    new_html, count = re.subn(
        r"const SUBSLOT_DATA\s*=\s*(\[.*?\]);",
        lambda _match: f"const SUBSLOT_DATA={compact};",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise SystemExit("SUBSLOT_DATA block not found in web/index.html")
    INDEX_HTML.write_text(new_html, encoding="utf-8")


def main() -> None:
    rows = load_json(INPUT_JSON)
    entries = build_entries(rows)
    OUTPUT_JSON.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    replace_inline_subslot_data(entries)
    print(f"Wrote {len(entries)} sub-slot skills to {OUTPUT_JSON}")
    print("Updated SUBSLOT_DATA in web/index.html")


if __name__ == "__main__":
    main()
