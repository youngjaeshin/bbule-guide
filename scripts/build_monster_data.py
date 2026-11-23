"""Build monster and invader guide data from a verified APK research directory."""

import argparse
import json
from pathlib import Path


def read_json(source_dir, name):
    return json.loads((source_dir / name).read_text(encoding="utf-8"))


def build_data(source_dir, output_path):
    traits = read_json(source_dir, "몬스터별_고유값_전수표_v1890.json")
    rules = read_json(source_dir, "구간별_공격무효화_저항_공격규칙_v1890.json")["rules"]
    general = read_json(source_dir, "unified_rules.json")
    evidence = read_json(source_dir, "apk_mechanism_evidence.json")
    invaders = read_json(source_dir, "침략자별_레벨별_디버프_v1890.json")
    highlights = read_json(source_dir, "특징적인_몬스터_선별_v1890.json")
    tiers = []
    for tier in general["tiers"]:
        common = next(
            row for row in evidence["baseline_execution"]
            if row["difficulty"] == tier["difficulty"] and row["kind"] == "ordinary"
        )
        boss = next(
            row for row in evidence["baseline_execution"]
            if row["difficulty"] == tier["difficulty"] and row["kind"] == "boss"
        )
        rule = next(row for row in rules["tiers"] if row["name"] == tier["name"])
        rate = next(
            row["hit_duration_reduction_effect_rate"]
            for row in rules["strong_attack"]["tiers"]
            if row["name"] == tier["name"]
        )
        tiers.append({
            "name": tier["name"],
            "difficulty": tier["difficulty"],
            "start": tier["start"],
            "end": tier["end"],
            "draws": tier["total_draws"],
            "statuses": tier["statuses"],
            "resistance": rule["resistance_bonus_percent_points"],
            "recovery_rate": rate,
            "boss_zero": {
                key: boss["stats"][key] - common["stats"][key]
                for key in tier["statuses"]
            },
            "boss_fixed": {
                key: boss["positive_cooldown_execution"]["stats"][key] - common["stats"][key]
                for key in tier["statuses"]
            },
        })
    monsters = [{
        "key": f"{row['kind']}:{row['record_id']}",
        "kind": row["kind"],
        "id": row["record_id"],
        "name": row["name"],
        "positions": row["reference_stage_positions"],
        "null": row["intrinsic_attack_null_percent_points"],
        "resistance": row["intrinsic_resistance_percent"],
        "interval": row["attack"]["source_interval_seconds"],
        "all_attack": row["attack"]["source_all_attack_percent"],
    } for row in traits["monsters"]]
    combat = invaders["combat_modifiers"]
    invader_data = [{
        "id": row["type_id"],
        "name": row["name"],
        "ranges": row["ranges"],
        "recovery_rate": next(
            case["effect_rate"] for case in combat["hit_checks"]
            if case["type_id"] == row["type_id"]
        ),
        "damage_factor": next(
            case["fixed_factor"] for case in combat["damage_checks"]
            if case["type_id"] == row["type_id"] and case["bonus"] == 0
        ),
    } for row in invaders["invaders"]]
    for invader in invader_data:
        for level_range in invader["ranges"]:
            values = level_range["values"]
            values["base_stats"]["disable"] = max(0, values["base_stats"]["disable"])
            values["maximum_by_field"]["disable"] = max(0, values["maximum_by_field"]["disable"])
    source_info = {
        "game_version": "1890 TEST_6",
        "reviewed_on": "2026-11-23",
        "basis": "APK 코드와 원본 데이터",
    }
    payload = {
        "tiers": tiers,
        "monsters": monsters,
        "highlights": {
            f"{entry['monster']['kind']}:{entry['monster']['record_id']}": entry["feature_text"]
            for entry in highlights["selected_monsters"]
        },
        "types": rules["attack_selection"]["types"],
        "source": {**source_info, "ordinary_records": 387, "boss_records": 109},
    }
    invader_payload = {
        "invaders": invader_data,
        "source": {**source_info, "invader_types": 7, "display_level_range": [1, 150]},
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    output_path.with_name("data_invader_debuffs.json").write_text(
        json.dumps(invader_payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"몬스터 {len(monsters)}개 · 침략자 {len(invader_data)}종 저장")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parents[1] / "web/data_monsters.json",
    )
    args = parser.parse_args()
    build_data(args.source, args.out)


if __name__ == "__main__":
    main()
