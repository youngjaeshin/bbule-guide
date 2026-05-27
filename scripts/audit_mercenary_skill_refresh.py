#!/usr/bin/env python3
"""Report same-name mercenary skills whose web text differs from APK candidates.

This is an audit tool, not a fixer. It should be clean after mercenary skill
effects are rebuilt from APK output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_mercenary_data import build_skill_fallbacks, normalize_effect_text  # noqa: E402


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="Maximum samples to print")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when masked candidates exist")
    args = parser.parse_args()

    creatures = load_json(ROOT / "output" / "creatures.json")
    web_mercs = load_json(ROOT / "web" / "data_mercenaries.json")
    web_by_id = {m["id"]: m for m in web_mercs}
    fallback = build_skill_fallbacks()

    same_name = []
    masked = []
    missing_candidate = []

    for creature in creatures:
        web = web_by_id.get(creature["hero_id"])
        if not web:
            continue
        old_skills = {s.get("slot"): s for s in web.get("skills", [])}
        for raw_skill in creature.get("skills", []):
            old_skill = old_skills.get(raw_skill["slot"])
            if not old_skill or old_skill.get("이름") != raw_skill.get("name"):
                continue
            same_name.append((creature, raw_skill, old_skill))
            source = fallback.get(raw_skill["id"], {})
            effects = [normalize_effect_text(e) for e in source.get("effects", []) if e]
            if not effects:
                missing_candidate.append((creature, raw_skill, old_skill))
                continue
            candidate = normalize_effect_text(" / ".join(effects))
            current = normalize_effect_text(old_skill.get("효과", ""))
            if candidate != current:
                masked.append((creature, raw_skill, current, candidate))

    print(f"Same-name skills compared against APK candidates: {len(same_name)}")
    print(f"Same-name skills with no APK candidate effect text: {len(missing_candidate)}")
    print(f"Same-name skills where APK candidate differs from current web text: {len(masked)}")
    if masked:
        print("\nSamples:")
        for creature, raw_skill, current, candidate in masked[: args.limit]:
            print(f"- {creature['grade']} {creature['name']} slot {raw_skill['slot']} {raw_skill['name']} id={raw_skill['id']}")
            print(f"  current:   {current}")
            print(f"  candidate: {candidate}")

    if args.strict and masked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
