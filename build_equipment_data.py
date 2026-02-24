#!/usr/bin/env python3
"""
Build data_equipment.json from APK-extracted binary data.
Source: output/equipment.json (NOT xlsx)
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EQUIP_JSON = os.path.join(BASE_DIR, "equipment.json")
CREATURES_JSON = os.path.join(BASE_DIR, "creatures.json")
EQUIP_IMG_DIR = os.path.join(BASE_DIR, "web", "images", "equip")
OUTPUT_JSON = os.path.join(BASE_DIR, "web", "data_equipment.json")

def main():
    # Load source data
    with open(EQUIP_JSON, encoding="utf-8") as f:
        equip_data = json.load(f)

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

        specialized_heroes = [{"name": n, "bonus": bonus} for n in unique_names]

        # Portrait matching: try {GRADE}_{name}.png
        # Store only filename; JS prepends IMG_BASE.equip
        portrait_filename = f"{grade}_{name}.png"
        if portrait_filename in img_files:
            portrait = portrait_filename
        else:
            portrait = ""

        effect_0 = item.get("effect_0", "")
        effect_20 = item.get("effect_20", "")
        effect_0_g = item.get("effect_0_g", "")
        effect_20_g = item.get("effect_20_g", "")

        icon = item.get("icon", -1)

        entry = {
            "name": name,
            "icon": icon,
            "grade": grade,
            "effect_type": effect_type,
            "mainEffect": main_effect,
            "mainEffect_desc": desc,
            "effect_0": effect_0,
            "effect_20": effect_20,
            "specializedHeroes": specialized_heroes,
            "is_upgradeable": is_available_g,
            "portrait": portrait,
        }
        if is_available_g and (effect_0_g or effect_20_g):
            entry["effect_0_g"] = effect_0_g
            entry["effect_20_g"] = effect_20_g
        result.append(entry)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Written {len(result)} items to {OUTPUT_JSON}")

    # Stats
    no_portrait = sum(1 for x in result if not x["portrait"])
    no_effect = sum(1 for x in result if not x["effect_type"])
    print(f"  - Items without portrait: {no_portrait}")
    print(f"  - Items without effect_type: {no_effect}")
    print(f"  - Items with specialized heroes: {sum(1 for x in result if x['specializedHeroes'])}")
    print(f"  - G-upgradeable items: {sum(1 for x in result if x['is_upgradeable'])}")

if __name__ == "__main__":
    main()
