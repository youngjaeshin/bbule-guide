#!/usr/bin/env python3
"""
Build data_equipment.json from APK-extracted binary data.
Source: output/equipment.json (NOT xlsx)
"""
import json
import os
import re
from equipment_capture_overrides import apply_capture_overrides

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EQUIP_JSON = os.path.join(BASE_DIR, "output", "equipment.json")
CREATURES_JSON = os.path.join(BASE_DIR, "output", "creatures.json")
EQUIP_IMG_DIR = os.path.join(BASE_DIR, "web", "images", "equip")
OUTPUT_JSON = os.path.join(BASE_DIR, "web", "data_equipment.json")
INDEX_HTML = os.path.join(BASE_DIR, "web", "index.html")
# Item sets + second options (optional). Generated from game data outside this repo;
# see item_set_data.json "_source" for the game version.
ITEM_SET_JSON = os.path.join(BASE_DIR, "item_set_data.json")


def load_item_sets():
    if not os.path.exists(ITEM_SET_JSON):
        return None
    with open(ITEM_SET_JSON, encoding="utf-8") as f:
        return json.load(f)


def find_set_record(item_sets, item):
    """Match by game index, or by (name, grade) for guide-only rows such as captured items with negative indexes."""
    rec = item_sets["items"].get(str(item["index"]))
    if rec:
        return rec
    for rec in item_sets["items"].values():
        if rec["name"] == item["name"].strip() and rec["grade"] == item["grade"]:
            return rec
    return None


def guide_row(by_index, by_key, key, rec):
    return by_index.get(key) or by_key.get((rec["name"], rec["grade"]))


def build_item_set_const(item_sets, result):
    """Inline ITEM_SET_DATA: sets with members (guide names) and set options."""
    by_index = {str(x["index"]): x for x in result}
    by_key = {(x["name"].strip(), x["grade"]): x for x in result}
    members = {}
    for key, rec in item_sets["items"].items():
        if not rec.get("set"):
            continue
        row = guide_row(by_index, by_key, key, rec)
        members.setdefault(rec["set"], []).append({
            "index": row["index"] if row else int(key),
            "name": row["name"] if row else rec["name"],
            "grade": row["grade"] if row else rec["grade"],
            "inGuide": row is not None,
        })
    options = []
    for opt in item_sets["setOptions"]:
        opt = dict(opt)
        key = str(opt.get("itemIndex"))
        rec = item_sets["items"].get(key)
        row = guide_row(by_index, by_key, key, rec) if rec else None
        if row:
            opt["item"] = row["name"]
            opt["itemIndex"] = row["index"]
        options.append(opt)
    return {
        "gameVersion": item_sets.get("gameVersion", ""),
        "sets": [{"name": s["name"], "members": members.get(s["name"], [])} for s in item_sets["sets"]],
        "setOptions": options,
    }


def main():
    # Load source data
    with open(EQUIP_JSON, encoding="utf-8") as f:
        equip_data = json.load(f)
    equip_data = apply_capture_overrides(equip_data)
    item_sets = load_item_sets()

    with open(CREATURES_JSON, encoding="utf-8") as f:
        creatures_data = json.load(f)

    # Build hero_id -> name lookup
    hero_lookup = {}
    for c in creatures_data:
        hero_lookup[c["hero_id"]] = c["name"]

    # Build set of available portrait image filenames
    img_files = set(os.listdir(EQUIP_IMG_DIR))

    result = []
    for item in equip_data:
        name = item["name"]
        grade = item["grade"]
        effect_type = item.get("mainType_name", "")
        main_effect = item["mainEffect"]
        desc = item.get("mainEffect_desc", "")
        specialized_effect = item.get("specializedEffect", 0.0)
        is_available_g = item.get("isAvailableG", False)
        g_evidence = item.get("gUpgradeEvidence", {})
        verified_g = (g_evidence.get("effects_verified") is True
                      and g_evidence.get("source_type") in {"game_screenshot", "community_screenshot"})

        # Resolve specialized heroes from specializedHero IDs
        specialized_hero_ids = item.get("specializedHero", [])
        seen_names = set()
        unique_names = []
        for hid in specialized_hero_ids:
            if hid >= 0:
                hname = hero_lookup.get(hid, "")
                if hname and hname not in seen_names:
                    seen_names.add(hname)
                    unique_names.append(hname)

        # Compute bonus: specializedEffect * 100 as integer if whole number
        bonus_raw = specialized_effect * 100
        bonus = int(bonus_raw) if bonus_raw == int(bonus_raw) else round(bonus_raw, 1)

        specialized_heroes = (item['specializedHeroes'] if 'specializedHeroes' in item
                              else [{"name": n, "bonus": bonus} for n in unique_names])

        # Portrait matching: try {GRADE}_{name}.png
        # Store only filename; JS prepends IMG_BASE.equip
        portrait_filename = f"{grade}_{name}.png"
        if portrait_filename in img_files:
            portrait = portrait_filename
        elif item.get('image', '').startswith('images/equip/'):
            portrait = item['image'].split('/')[-1]
        else:
            portrait = ""

        effect_0 = item.get("effect_0", "")
        effect_20 = item.get("effect_20", "")
        effect_0_g = item.get("effect_0_g", "")
        effect_20_g = item.get("effect_20_g", "")

        icon = item.get("icon", -1)

        entry = {
            "index": item['index'],
            "name": name,
            "icon": icon,
            "grade": grade,
            "mainType": item.get('mainType'),
            "effect_type": effect_type,
            "mainEffect": main_effect,
            "mainEffect_display": item.get('mainEffect_display'),
            "mainEffect_desc": desc,
            "effect_0": effect_0,
            "effect_20": effect_20,
            "specializedHeroes": specialized_heroes,
            "specializedEffect": specialized_effect,
            "specializedHero": [hero_id for hero_id in specialized_hero_ids if hero_id >= 0],
            "is_upgradeable": is_available_g if verified_g or not is_available_g else None,
            "portrait": portrait,
        }
        for field in ('gameIndex', 'indexSource', 'effect_0_value', 'effect_20_value',
                      'coefficient_0', 'coefficient_20', 'effect_unit', 'effect_20_source',
                      'can_enhance', 'enhancement', 'effectCode', 'image', 'captureEvidence',
                      'legacySpecializedTargets', 'gUpgradeSource', 'testOnly'):
            if field in item:
                entry[field] = item[field]
        if is_available_g:
            entry["gUpgradeVerified"] = verified_g
        if is_available_g and verified_g and (effect_0_g or effect_20_g):
            entry["effect_0_g"] = effect_0_g
            entry["effect_20_g"] = effect_20_g
        if item_sets:
            set_rec = find_set_record(item_sets, item)
            if set_rec:
                if set_rec.get("set"):
                    entry["set"] = set_rec["set"]
                if set_rec.get("opt2"):
                    entry["opt2"] = set_rec["opt2"]
        result.append(entry)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Written {len(result)} items to {OUTPUT_JSON}")

    equip_json_compact = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    with open(INDEX_HTML, encoding="utf-8") as f:
        html = f.read()
    pattern = r"const\s+EQUIP_DATA\s*=\s*\[.*?\];"
    new_decl = f"const EQUIP_DATA = {equip_json_compact};"
    new_html, count = re.subn(pattern, new_decl, html, flags=re.DOTALL)
    if count == 0:
        raise RuntimeError("Could not find EQUIP_DATA in index.html")
    if item_sets:
        set_const = json.dumps(build_item_set_const(item_sets, result), ensure_ascii=False, separators=(",", ":"))
        set_decl = f"const ITEM_SET_DATA = {set_const};"
        set_pattern = r"^const\s+ITEM_SET_DATA\s*=.*$"
        new_html, set_count = re.subn(set_pattern, lambda m: set_decl, new_html, flags=re.MULTILINE)
        if set_count == 0:
            new_html = new_html.replace(new_decl, new_decl + "\n" + set_decl, 1)
        print(f"Updated ITEM_SET_DATA ({len(item_sets['sets'])} sets, {len(item_sets['setOptions'])} set options)")
    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Updated EQUIP_DATA in {INDEX_HTML} ({count} occurrence)")

    # Stats
    no_portrait = sum(1 for x in result if not (x["portrait"] or x.get('image')))
    no_effect = sum(1 for x in result if not x["effect_type"])
    print(f"  - Items without portrait: {no_portrait}")
    print(f"  - Items without effect_type: {no_effect}")
    print(f"  - Items with specialized heroes: {sum(1 for x in result if x['specializedHeroes'])}")
    print(f"  - G-upgradeable items: {sum(1 for x in result if x['is_upgradeable'])}")

if __name__ == "__main__":
    main()
