"""
Extract 허수아비침략자 sheet data from xlsx and save as JSON.
Source: 뿔레 전쟁 클리커 공략 모음 최종 수정일 26-2-22.xlsx
Output: web/data_scarecrow_invader.json
"""

import json
import os
import openpyxl

XLSX_PATH = "/Users/shin542/Desktop/Code/bbule/뿔레 전쟁 클리커 공략 모음 최종 수정일 26-2-22.xlsx"
OUTPUT_PATH = "/Users/shin542/Desktop/Code/bbule/web/data_scarecrow_invader.json"
SHEET_NAME = "허수아비침략자"


def cell_str(cell_value) -> str:
    """Convert cell value to stripped string; return '' for None/empty."""
    if cell_value is None:
        return ""
    return str(cell_value).strip()


def main():
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb[SHEET_NAME]

    # --- Invader types from row 3 (1-indexed) ---
    # "미래 침략자 125 고대침략자 150 차원 침략자 750 아카식 1250 -각 스테이지 클리어시 도전 가능"
    invader_types = [
        {"name": "미래의 침략자", "unlockStage": 125},
        {"name": "고대의 침략자", "unlockStage": 150},
        {"name": "차원 침략자",   "unlockStage": 750},
        {"name": "아카식 침략자", "unlockStage": 1250},
        {"name": "거울 침략자",   "unlockStage": None},
    ]

    # --- Invader rewards: rows 7-156 (1-indexed), cols 1-6 ---
    # Col1=level, Col2=미래, Col3=고대, Col4=차원, Col5=아카식, Col6=거울
    rewards = []
    for r in range(7, 157):  # rows 7 to 156 inclusive (levels 1-150)
        level_val = ws.cell(row=r, column=1).value
        if level_val is None:
            break
        try:
            level = int(level_val)
        except (ValueError, TypeError):
            break

        rewards.append({
            "level": level,
            "미래":  cell_str(ws.cell(row=r, column=2).value),
            "고대":  cell_str(ws.cell(row=r, column=3).value),
            "차원":  cell_str(ws.cell(row=r, column=4).value),
            "아카식": cell_str(ws.cell(row=r, column=5).value),
            "거울":  cell_str(ws.cell(row=r, column=6).value),
        })

    # --- Scarecrow: 뿔레 허수아비 (cols 7,8,9) and 변신수 허수아비 (cols 11,12,13) ---
    # hp_rule from row 4 (1-indexed)
    bbule_hp_rule = cell_str(ws.cell(row=4, column=7).value)
    transform_hp_rule = cell_str(ws.cell(row=4, column=11).value)

    bbule_levels = []
    transform_levels = []

    for r in range(7, 157):
        # 뿔레 허수아비
        lv_val = ws.cell(row=r, column=7).value
        if lv_val is not None and cell_str(lv_val) != "":
            bbule_levels.append({
                "level": cell_str(lv_val),
                "hp":    cell_str(ws.cell(row=r, column=8).value),
                "reward": cell_str(ws.cell(row=r, column=9).value),
            })

        # 변신수 허수아비
        lv_val2 = ws.cell(row=r, column=11).value
        if lv_val2 is not None and cell_str(lv_val2) != "":
            transform_levels.append({
                "level": cell_str(lv_val2),
                "hp":    cell_str(ws.cell(row=r, column=12).value),
                "reward": cell_str(ws.cell(row=r, column=13).value),
            })

    output = {
        "invaders": {
            "info": "각 스테이지 클리어 시 도전 가능",
            "types": invader_types,
            "rewards": rewards,
        },
        "scarecrows": {
            "bbule": {
                "name": "뿔레 허수아비",
                "hpRule": bbule_hp_rule,
                "levels": bbule_levels,
            },
            "transform": {
                "name": "변신수 허수아비",
                "hpRule": transform_hp_rule,
                "levels": transform_levels,
            },
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"  invader rewards: {len(rewards)} levels")
    print(f"  뿔레 허수아비 levels: {len(bbule_levels)}")
    print(f"  변신수 허수아비 levels: {len(transform_levels)}")


if __name__ == "__main__":
    main()
