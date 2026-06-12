#!/usr/bin/env python3
"""Report same-name mercenary skills whose web text differs from APK candidates.

This is an audit tool, not a fixer. It should be clean after mercenary skill
effects are rebuilt from APK output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_mercenary_data import (  # noqa: E402
    SKILL_SOURCE_OVERRIDES,
    build_skill_sources,
    normalize_effect_text,
    select_skill_source,
)


MALFORMED_EFFECT_PATTERNS = (
    ("unresolved placeholder", re.compile(r"\{[1-9]\}")),
    ("missing damage multiplier", re.compile(r"(?:데미지가|공격에)\s*배")),
    ("missing attack multiplier", re.compile(r"확률로\s*배\s*데미지")),
    ("percent-suffixed multiplier", re.compile(r"[+-]?\d+(?:\.\d+)?%배")),
    ("duplicated percent value", re.compile(r"([+-]?\d+(?:\.\d+)?%)\s+\1")),
)

UNRESOLVED_EFFECT_RE = re.compile(r"효과\s*\+?\d+|효과\d+")


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def candidate_text(source: dict) -> str:
    return normalize_effect_text(" / ".join(source.get("effects", [])))


def skill_ref(creature: dict, raw_skill: dict) -> dict:
    return {
        "grade": creature["grade"],
        "mercenary": creature["name"],
        "hero_id": creature["hero_id"],
        "slot": raw_skill["slot"],
        "skill_id": raw_skill["id"],
        "skill": raw_skill["name"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="Maximum samples to print")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when masked candidates exist")
    parser.add_argument("--strict-unresolved", action="store_true", help="Exit nonzero when unresolved effect text exists")
    parser.add_argument("--strict-ambiguous", action="store_true", help="Exit nonzero when an ambiguous APK skill has no selector override")
    parser.add_argument("--json-output", help="Write the full audit result to this JSON file")
    args = parser.parse_args()

    creatures = load_json(ROOT / "output" / "creatures.json")
    web_mercs = load_json(ROOT / "web" / "data_mercenaries.json")
    web_by_id = {m["id"]: m for m in web_mercs}
    sources = build_skill_sources()

    same_name = []
    masked = []
    missing_candidate = []
    malformed = []
    unresolved = []
    ambiguous = []

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
            candidates = sources.get(raw_skill["id"], [])
            source = select_skill_source(
                raw_skill["id"],
                sources,
                hero_id=creature["hero_id"],
                slot=raw_skill["slot"],
            )
            if len(candidates) > 1:
                ambiguous.append((
                    creature,
                    raw_skill,
                    source,
                    candidates,
                    (
                        (creature["hero_id"], raw_skill["slot"], raw_skill["id"]) in SKILL_SOURCE_OVERRIDES
                        or (None, None, raw_skill["id"]) in SKILL_SOURCE_OVERRIDES
                    ),
                ))
            effects = [normalize_effect_text(e) for e in source.get("effects", []) if e]
            if not effects:
                missing_candidate.append((creature, raw_skill, old_skill))
                continue
            candidate = normalize_effect_text(" / ".join(effects))
            current = normalize_effect_text(old_skill.get("효과", ""))
            if UNRESOLVED_EFFECT_RE.search(candidate):
                unresolved.append((creature, raw_skill, candidate))
            hits = [
                label
                for label, pattern in MALFORMED_EFFECT_PATTERNS
                if pattern.search(current)
            ]
            if hits:
                malformed.append((creature, raw_skill, current, hits))
            if candidate != current:
                masked.append((creature, raw_skill, current, candidate))

    print(f"Same-name skills compared against APK candidates: {len(same_name)}")
    print(f"Same-name skills with no APK candidate effect text: {len(missing_candidate)}")
    print(f"Same-name skills where APK candidate differs from current web text: {len(masked)}")
    print(f"Malformed effect texts: {len(malformed)}")
    print(f"Unresolved APK effect texts needing in-game verification: {len(unresolved)}")
    print(f"Ambiguous APK skill candidates used by mercenaries: {len(ambiguous)}")
    print(f"Ambiguous candidates with selector overrides: {sum(1 for *_, has_override in ambiguous if has_override)}")
    if masked:
        print("\nSamples:")
        for creature, raw_skill, current, candidate in masked[: args.limit]:
            print(f"- {creature['grade']} {creature['name']} slot {raw_skill['slot']} {raw_skill['name']} id={raw_skill['id']}")
            print(f"  current:   {current}")
            print(f"  candidate: {candidate}")
    if malformed:
        print("\nMalformed samples:")
        for creature, raw_skill, current, hits in malformed[: args.limit]:
            print(f"- {creature['grade']} {creature['name']} slot {raw_skill['slot']} {raw_skill['name']} id={raw_skill['id']}")
            print(f"  reason:    {', '.join(hits)}")
            print(f"  current:   {current}")
    if unresolved:
        print("\nUnresolved effect samples:")
        for creature, raw_skill, candidate in unresolved[: args.limit]:
            print(f"- {creature['grade']} {creature['name']} slot {raw_skill['slot']} {raw_skill['name']} id={raw_skill['id']}")
            print(f"  apk:       {candidate}")
    if ambiguous:
        print("\nAmbiguous APK candidate samples:")
        for creature, raw_skill, selected, candidates, has_override in ambiguous[: args.limit]:
            status = "override" if has_override else "default-first"
            selected_text = candidate_text(selected)
            print(f"- {creature['grade']} {creature['name']} slot {raw_skill['slot']} {raw_skill['name']} id={raw_skill['id']} ({status})")
            print(f"  selected:  {selected_text}")
            for idx, candidate in enumerate(candidates, start=1):
                text = candidate_text(candidate)
                print(f"  cand {idx}:   {text}")

    if args.json_output:
        report = {
            "summary": {
                "same_name_compared": len(same_name),
                "missing_candidate": len(missing_candidate),
                "masked": len(masked),
                "malformed": len(malformed),
                "unresolved": len(unresolved),
                "ambiguous": len(ambiguous),
                "ambiguous_with_overrides": sum(1 for *_, has_override in ambiguous if has_override),
            },
            "masked": [
                {**skill_ref(creature, raw_skill), "current": current, "candidate": candidate}
                for creature, raw_skill, current, candidate in masked
            ],
            "malformed": [
                {**skill_ref(creature, raw_skill), "current": current, "reasons": hits}
                for creature, raw_skill, current, hits in malformed
            ],
            "unresolved": [
                {**skill_ref(creature, raw_skill), "apk": candidate}
                for creature, raw_skill, candidate in unresolved
            ],
            "ambiguous": [
                {
                    **skill_ref(creature, raw_skill),
                    "selection": "override" if has_override else "default-first",
                    "selected": candidate_text(selected),
                    "candidates": [
                        {
                            "source": candidate.get("source"),
                            "types": candidate.get("types", []),
                            "effects": candidate.get("raw_effects", []),
                            "text": candidate_text(candidate),
                        }
                        for candidate in candidates
                    ],
                }
                for creature, raw_skill, selected, candidates, has_override in ambiguous
            ],
            "missing_candidate": [
                {**skill_ref(creature, raw_skill), "current": old_skill.get("효과", "")}
                for creature, raw_skill, old_skill in missing_candidate
            ],
        }
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote full audit report: {out_path}")

    if args.strict and (masked or malformed):
        return 1
    if args.strict_unresolved and unresolved:
        return 1
    if args.strict_ambiguous and any(not has_override for *_, has_override in ambiguous):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
