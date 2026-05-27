#!/usr/bin/env python3
"""Build web/data_mercenaries.json from extracted creature data.

APK output is the source of truth for skill effects because same-name skills can
change values or effect types between game versions. Existing web data is used
only for manual passive, portrait, and exclusive-item fields, plus skill text
when APK output has no effect candidate.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).parent
CREATURES_JSON = BASE / "output" / "creatures.json"
MERC_SKILLS_JSON = BASE / "output" / "mercenary_skills.json"
SUB_SLOT_JSON = BASE / "output" / "sub_slot_troops.json"
RANDOM_SKILLS_JSON = BASE / "output" / "random_merc_skills.json"
RANDOM_WEB_JSON = BASE / "web" / "data_random_merc.json"
MERC_WEB_JSON = BASE / "web" / "data_mercenaries.json"
INDEX_HTML = BASE / "web" / "index.html"
MERC_IMG_DIR = BASE / "web" / "images" / "mercenary"

PASSIVE_OVERRIDES = {
    391: "적들의 회피 확률 감소 +0.5%",
    538: "모든 용병의 강타 확률 +1%",
    539: "모든 용병의 봉인 무효화 확률 +2.4%, 적들의 무력화 효과 감소 3.6%",
    540: "추가 데미지 +1000",
    541: None,
    542: "소울 클릭 배수 증폭 +0.5%",
    543: None,
    544: "모든 용병의 추가 클릭 데미지 증폭 +1%",
    545: None,
    546: "모든 용병의 추가 클릭 데미지 증폭 +1%",
    547: "모든 용병의 아티팩트 효과 증폭 +1%, 모든 용병의 주얼 효과 증폭 +4%",
    548: "모든 용병의 치명타 배수 증폭 +1%",
    549: "모든 용병의 치명타 배수 증폭 +1%",
    550: None,
}

PLAIN_MULTIPLIER_TERMS_RE = (
    r"강타\s*배수|"
    r"행운\s*배수|"
    r"클릭\s*크리티컬\s*배수|"
    r"소울\s*클릭\s*배수|"
    r"치명타\s*배수|"
    r"연타\s*배수"
)
PLAIN_MULTIPLIER_PERCENT_RE = re.compile(
    rf"((?:{PLAIN_MULTIPLIER_TERMS_RE})(?!\s*증폭)(?:(?!증폭|/|,).)*?)([+-]?)\s*(\d+(?:\.\d+)?)%"
)
AMPLIFICATION_RAW_RE = re.compile(
    r"(증폭(?:(?!/|,).)*?)([+-])\s*(\d+(?:\.\d+)?)(?!\s*[%\d.])"
)
DAMAGE_MULTIPLIER_PLUS_RE = re.compile(
    r"(확률로\s*[^/,]*?데미지가)\s+\+(\d+(?:\.\d+)?)배"
)


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def format_raw_multiplier(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return f"{text}.0" if "." not in text else text


def format_percent(value: float) -> str:
    text = f"{value * 100:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def normalize_amplification(match: re.Match) -> str:
    prefix, sign, raw_value = match.groups()
    return f"{prefix}{sign}{format_percent(float(raw_value))}%"


def normalize_plain_multiplier(match: re.Match) -> str:
    prefix, sign, percent_value = match.groups()
    raw_value = float(percent_value) / 100
    return f"{prefix}{sign}{format_raw_multiplier(raw_value)}"


def normalize_effect_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace(" × ", " X ")
    text = re.sub(r"%{2,}", "%", text)
    text = re.sub(
        r"동료들의 다음 (물리|마법|혼합|카오스|트리니티) 공격에 \{1\}배 데미지 추가",
        r"동료들의 다음 \1 공격을 강화",
        text,
    )
    text = AMPLIFICATION_RAW_RE.sub(normalize_amplification, text)
    text = PLAIN_MULTIPLIER_PERCENT_RE.sub(normalize_plain_multiplier, text)
    text = re.sub(r"(?<=[가-힣A-Za-z\]\)])([+-](?:\d|\[))", r" \1", text)
    if re.search(r"\s[+-](?:\d|\[)", text):
        text = DAMAGE_MULTIPLIER_PLUS_RE.sub(r"\1 \2배", text)
    else:
        text = re.sub(r"(?<=[가-힣A-Za-z\]\)])(?=\d)", " +", text, count=1)
        text = re.sub(r" (?=\d)", " +", text, count=1)
    text = DAMAGE_MULTIPLIER_PLUS_RE.sub(r"\1 \2배", text)
    return text


def normalize_skill_entry(skill: dict) -> dict:
    normalized = dict(skill)
    name = normalized.get("이름", "")
    effect_text = normalize_effect_text(normalized.get("효과", ""))
    normalized["효과"] = effect_text
    normalized["표시"] = f"{name} / {effect_text}" if effect_text else name
    return normalized


def build_skill_fallbacks() -> dict[int, dict]:
    fallback = {}

    for path in (MERC_SKILLS_JSON, SUB_SLOT_JSON, RANDOM_SKILLS_JSON):
        for s in load_json(path):
            if s["index"] in fallback:
                continue
            effects = [
                normalize_effect_text(e.get("description", ""))
                for e in s.get("effects_resolved", [])
                if e.get("description")
            ]
            fallback[s["index"]] = {
                "name": s.get("name", ""),
                "desc": s.get("description", ""),
                "effects": effects,
            }

    # Legacy web random-merc data is a last-resort fallback only. APK output is
    # the source of truth because same-name skills can change between versions.
    for s in load_json(RANDOM_WEB_JSON):
        if s["index"] in fallback:
            continue
        fallback[s["index"]] = {
            "name": s["name"],
            "desc": s.get("desc", ""),
            "effects": [normalize_effect_text(e) for e in s.get("effects", [])],
        }
    return fallback


def convert_skill(raw_skill: dict, old_skill: dict | None, fallback: dict[int, dict]) -> dict:
    source = fallback.get(raw_skill["id"], {})
    effects = source.get("effects", [])
    effect_text = normalize_effect_text(" / ".join(effects))
    name = raw_skill.get("name", "") or source.get("name", "") or "없음"
    desc = raw_skill.get("description", "") or source.get("desc", "")
    if old_skill and not effect_text:
        return normalize_skill_entry({
            **old_skill,
            "이름": name or old_skill.get("이름", ""),
            "설명": desc or old_skill.get("설명", ""),
        })
    return normalize_skill_entry({
        "slot": raw_skill["slot"],
        "이름": name,
        "설명": desc,
        "효과": effect_text,
        "표시": f"{name} / {effect_text}" if effect_text else name,
    })


def convert_creature(creature: dict, old_entry: dict | None, fallback: dict[int, dict]) -> dict:
    stats = creature.get("sheet_stats", {})
    types = creature.get("types", {})
    hero_id = creature["hero_id"]
    old_skills = {
        s.get("slot"): s
        for s in (old_entry or {}).get("skills", [])
        if isinstance(s, dict)
    }

    portrait = (old_entry or {}).get("portrait", "")
    candidate = f"{creature['grade']}_{creature['name']}.png"
    if (MERC_IMG_DIR / candidate).exists():
        portrait = candidate

    passive = (
        PASSIVE_OVERRIDES[hero_id]
        if hero_id in PASSIVE_OVERRIDES
        else (old_entry or {}).get("passive")
    )
    if isinstance(passive, str):
        passive = normalize_effect_text(passive)

    return {
        "id": hero_id,
        "name": creature.get("name", ""),
        "grade": creature.get("grade", ""),
        "subtitle": creature.get("subtitle", ""),
        "story": creature.get("story", ""),
        "portrait": portrait,
        "race": types.get("race") or "없음",
        "house": types.get("house") or "없음",
        "location": types.get("location") or "없음",
        "gender": types.get("gender") or "없음",
        "religion": types.get("religion") or "없음",
        "individuality": types.get("individuality") or "없음",
        "damageType": creature.get("attackType_kr", ""),
        "attackCooldown": stats.get("attack_cooldown", creature.get("attackCooldown", 0)),
        "baseDPS": stats.get("base_dps", 0),
        "growthDPS": stats.get("growth_dps", 0),
        "baseDamage": stats.get("base_damage", 0),
        "growthDamage": stats.get("growth_damage", 0),
        "baseClickDamage": stats.get("base_click_damage", 0),
        "growthClickDamage": stats.get("growth_click_damage", 0),
        "skills": [
            convert_skill(skill, old_skills.get(skill["slot"]), fallback)
            for skill in sorted(creature.get("skills", []), key=lambda s: s["slot"])
        ],
        "canG": creature.get("canG", False),
        "canAwaken": creature.get("canAwaken", False),
        "exclusiveItems": (old_entry or {}).get("exclusiveItems", []),
        "passive": passive,
    }


def replace_inline_merc_data(mercs: list[dict]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r"const MERC_DATA\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        raise SystemExit("MERC_DATA block not found in web/index.html")
    compact = json.dumps(mercs, ensure_ascii=False, separators=(",", ":"))
    html = html[:match.start()] + f"const MERC_DATA={compact};" + html[match.end():]
    INDEX_HTML.write_text(html, encoding="utf-8")


def main() -> None:
    creatures = load_json(CREATURES_JSON)
    old_mercs = load_json(MERC_WEB_JSON) if MERC_WEB_JSON.exists() else []
    old_by_id = {m["id"]: m for m in old_mercs}
    raw_by_id = {c["hero_id"]: c for c in creatures}
    fallback = build_skill_fallbacks()

    result = []
    seen = set()
    for old in old_mercs:
        raw = raw_by_id.get(old["id"])
        if raw:
            result.append(convert_creature(raw, old, fallback))
            seen.add(old["id"])

    for raw in creatures:
        if raw["hero_id"] not in seen:
            result.append(convert_creature(raw, None, fallback))

    MERC_WEB_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    replace_inline_merc_data(result)

    missing_portraits = sum(1 for m in result if not m.get("portrait"))
    print(f"Wrote {len(result)} mercenaries to {MERC_WEB_JSON}")
    print(f"  Added: {len(result) - len(old_mercs)}")
    print(f"  Missing portraits: {missing_portraits}")


if __name__ == "__main__":
    main()
