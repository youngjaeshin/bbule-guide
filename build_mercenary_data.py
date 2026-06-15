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

EXTRACTED_SKILL_FILES = (
    MERC_SKILLS_JSON,
    SUB_SLOT_JSON,
    RANDOM_SKILLS_JSON,
)

# Some APK skill rows share the same skill index but have different effects.
# Creature rows only store the shared index, so user-verified duplicates need a
# mercenary/slot-specific selector to avoid silently taking the first row.
SKILL_SOURCE_OVERRIDES = {
    (None, None, 353): {
        "types": [56, 0, 0],
        "effects": [0.02, 0.0, 0.0],
        "reason": "보호막 관통 is in-game verified as the 2% candidate for listed mercenary uses.",
    },
    (None, None, 417): {
        "types": [9, 15, 0],
        "effects": [0.4, 1.0, 0.0],
        "reason": "정당한 분노+ is in-game verified as 공격 속도 40% / 클릭 데미지 100%.",
    },
    (None, None, 505): {
        "types": [109, 0, 0],
        "effects": [0.06, 0.0, 0.0],
        "reason": "끌어당김의 법칙 is in-game verified as 뿔레정수 획득 확률 6%.",
    },
    (None, None, 566): {
        "types": [32, 97, 0],
        "effects": [-5.0, 0.02, 0.0],
        "resolved_effects": [
            {
                "type_code": 32,
                "type_name": "연타 불가",
                "value": -5.0,
                "value_display": "",
                "description": "연타 불가",
            },
            {
                "type_code": 97,
                "type_name": "모든 마법 용병의 최종 데미지",
                "value": 0.02,
                "value_display": "2%",
                "description": "모든 마법 용병의 최종 데미지 2%",
            },
        ],
        "reason": "행성파괴 is in-game verified as 연타 불가, not 연타 확률 -500%.",
    },
    (219, 5, 335): {
        "types": [20, 0, 0],
        "effects": [0.16, 0.0, 0.0],
        "reason": "하라의 귀여움 is in-game verified as personal 강타 확률 16%, not all mixed 연타 확률 4%.",
    },
    (225, 5, 348): {
        "types": [15, 43, 122],
        "effects": [3.0, 0.5, 0.3],
        "reason": "촉진된 진화++ uses the verified raw APK candidate; skill display scaling is applied during extraction.",
    },
    (335, 5, 618): {
        "types": [149, 171, 0],
        "effects": [0.003, 0.5, 0.0],
        "reason": "남다른 우정 is in-game verified as the click-damage awakening/Crixus candidate.",
    },
    (383, 4, 752): {
        "types": [56, 109, 292],
        "effects": [0.04, 0.06, 0.4],
        "reason": "니헤르의 투구 is in-game verified as the penetration/essence/helmet candidate.",
    },
    (514, 1, 1157): {
        "types": [46, 1069, 0],
        "effects": [0.4, 1.6, 0.0],
        "reason": "한푼만 주세요+ is in-game verified as the 40%/160% gold candidate.",
    },
    (514, 2, 1160): {
        "types": [7, 32, 0],
        "effects": [10000.0, 0.08, 0.0],
        "reason": "효과적 구걸법+ is in-game verified as 추가 데미지 10000 plus 연타 확률 8%.",
    },
    (514, 5, 1163): {
        "types": [1, 33, 256],
        "effects": [2.0, 0.02, 0.02],
        "reason": "푸시니아의 작업복+ is in-game verified as the three-effect candidate.",
    },
}

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
    text = re.sub(
        r"공격시 \+(\d+(?:\.\d+)?%의 확률로 다음 트리니티 공격에)",
        r"공격시 \1",
        text,
    )
    text = re.sub(r"(확률로) \+(\d+(?:\.\d+)?)배", r"\1 \2배", text)
    text = re.sub(r"(걸어) \+(\d+(?:\.\d+)?)초동안", r"\1 \2초동안", text)
    text = re.sub(r"매 \+(\d+번 공격시)", r"매 \1", text)
    text = re.sub(
        r"(다음 (?:(?:물리|마법|혼합|카오스) )?공격(?:에)? )\+(\d+(?:\.\d+)?배)",
        r"\1\2",
        text,
    )
    text = re.sub(r"(다음 공격 )\+(\d+(?:\.\d+)?초)", r"\1\2", text)
    return text


def normalize_skill_entry(skill: dict) -> dict:
    normalized = dict(skill)
    name = normalized.get("이름", "")
    effect_text = normalize_effect_text(normalized.get("효과", ""))
    normalized["효과"] = effect_text
    normalized["표시"] = f"{name} / {effect_text}" if effect_text else name
    return normalized


def _normalize_source(path: Path, skill: dict) -> dict:
    effects = [
        normalize_effect_text(e.get("description", ""))
        for e in skill.get("effects_resolved", [])
        if e.get("description")
    ]
    return {
        "index": skill["index"],
        "name": skill.get("name", ""),
        "desc": skill.get("description", ""),
        "effects": effects,
        "effects_resolved": skill.get("effects_resolved", []),
        "types": skill.get("types", []),
        "raw_effects": skill.get("effects", []),
        "source": path.name,
    }


def build_skill_sources(include_legacy_random: bool = True) -> dict[int, list[dict]]:
    sources: dict[int, list[dict]] = {}

    for path in EXTRACTED_SKILL_FILES:
        for s in load_json(path):
            sources.setdefault(s["index"], []).append(_normalize_source(path, s))

    # Legacy web random-merc data is a last-resort fallback only. APK output is
    # the source of truth because same-name skills can change between versions.
    if not include_legacy_random:
        return sources

    for s in load_json(RANDOM_WEB_JSON):
        if s["index"] in sources:
            continue
        sources.setdefault(s["index"], []).append({
            "index": s["index"],
            "name": s["name"],
            "desc": s.get("desc", ""),
            "effects": [normalize_effect_text(e) for e in s.get("effects", [])],
            "effects_resolved": [],
            "types": [],
            "raw_effects": [],
            "source": RANDOM_WEB_JSON.name,
        })
    return sources


def build_skill_fallbacks() -> dict[int, dict]:
    """Return the default first candidate per skill id for legacy callers."""
    return {
        skill_id: candidates[0]
        for skill_id, candidates in build_skill_sources().items()
        if candidates
    }


def _same_values(left: list, right: list) -> bool:
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if isinstance(a, float) or isinstance(b, float):
            if abs(float(a) - float(b)) > 0.000001:
                return False
        elif a != b:
            return False
    return True


def _source_matches_override(source: dict, override: dict) -> bool:
    if "types" in override and list(source.get("types", [])) != list(override["types"]):
        return False
    if "effects" in override and not _same_values(source.get("raw_effects", []), override["effects"]):
        return False
    return True


def _apply_source_override(source: dict, override: dict) -> dict:
    if "resolved_effects" not in override:
        return source

    resolved = override["resolved_effects"]
    patched = dict(source)
    patched["effects_resolved"] = resolved
    patched["effects"] = [
        normalize_effect_text(effect.get("description", ""))
        for effect in resolved
        if effect.get("description")
    ]
    patched["types"] = [effect.get("type_code", 0) for effect in resolved]
    patched["raw_effects"] = [effect.get("value", 0.0) for effect in resolved]
    return patched


def select_skill_source(
    skill_id: int,
    sources: dict[int, list[dict]],
    *,
    hero_id: int | None = None,
    slot: int | None = None,
) -> dict:
    candidates = sources.get(skill_id, [])
    if not candidates:
        return {}

    override = (
        SKILL_SOURCE_OVERRIDES.get((hero_id, slot, skill_id))
        or SKILL_SOURCE_OVERRIDES.get((None, None, skill_id))
    )
    if not override:
        return candidates[0]

    for source in candidates:
        if _source_matches_override(source, override):
            return _apply_source_override(source, override)
    raise RuntimeError(
        f"Skill source override did not match any APK candidate: "
        f"hero={hero_id}, slot={slot}, skill={skill_id}"
    )


def convert_skill(raw_skill: dict, old_skill: dict | None, source: dict) -> dict:
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


def convert_creature(creature: dict, old_entry: dict | None, sources: dict[int, list[dict]]) -> dict:
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
            convert_skill(
                skill,
                old_skills.get(skill["slot"]),
                select_skill_source(
                    skill["id"],
                    sources,
                    hero_id=hero_id,
                    slot=skill["slot"],
                ),
            )
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
    sources = build_skill_sources()

    result = []
    seen = set()
    for old in old_mercs:
        raw = raw_by_id.get(old["id"])
        if raw:
            result.append(convert_creature(raw, old, sources))
            seen.add(old["id"])

    for raw in creatures:
        if raw["hero_id"] not in seen:
            result.append(convert_creature(raw, None, sources))

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
