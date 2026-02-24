"""
fix_artifact_type_names.py

Compares artifact_code_mapping.json (artifact-specific, CORRECT)
with the MAINTYPE_TO_EFFECT dict (generic, WRONG for some artifact codes),
finds all differing codes, then:

1. Prints the differences
2. Fixes effects_resolved in artifacts.json for all affected artifacts
3. Saves fixed artifacts.json
   (build_artifact_data.py is then called to rebuild data_artifacts.json and index.html)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Step 1: Load both mappings
# ---------------------------------------------------------------------------

# The CORRECT artifact-specific mapping
art_mapping_path = HERE / 'artifact_code_mapping.json'
with open(art_mapping_path, encoding='utf-8') as f:
    raw_art = json.load(f)
# Keys are strings in the JSON; convert to int
ART_CODE_MAP = {int(k): v for k, v in raw_art.items()}

# The generic MAINTYPE_TO_EFFECT dict (from extract_all.py)
# Only the name portion matters for comparison (index 0 of the tuple).
MAINTYPE_TO_EFFECT = {
    0: ('데미지', 'pct', 4.5),
    1: ('추가 데미지', 'int', 3.0),
    2: ('모든 용병의 데미지', 'pct', 5.0),
    3: ('클릭 데미지', 'pct', 4.5),
    5: ('모든 용병의 클릭 데미지', 'pct', 3.0),
    6: ('공격 속도', 'pct', 1.0),
    7: ('모든 용병의 공격 속도', 'pct', 1.0),
    8: ('골드 획득량', 'pct', 1.0),
    9: ('적들의 물리 저항력 감소', 'pct', 1.0),
    10: ('적들의 마법 저항력 감소', 'pct', 1.0),
    11: ('적들의 최대 체력 감소', 'pct', 1.0),
    12: ('적들의 클릭 저항력 감소', 'pct', 1.0),
    13: ('골드 저장량', 'pct', 1.0),
    14: ('클릭 크리티컬 확률', 'pct', 1.0),
    15: ('아이템 획득 확률', 'pct', 1.0),
    16: ('강타 확률', 'pct', 1.0),
    17: ('강타 배수', 'raw', 0.5),
    20: ('모든 용병의 강타 확률', 'pct', 1.0),
    21: ('모든 용병의 강타 배수', 'raw', 1.0),
    24: ('소울 클릭 확률', 'pct', 1.0),
    25: ('클릭 크리티컬 배수', 'raw', 1.0),
    26: ('베이스 데미지', 'pct', 3.0),
    28: ('공격 무효화 관통', 'pct', 1.0),
    29: ('모든 용병의 최대 레벨', 'int', 1.0),
    30: ('최대 레벨', 'int', 1.0),
    31: ('적들의 카오스 취약성', 'pct', 1.0),
    32: ('모든 용병의 레벨업 및 스킬학습 비용감소', 'pct', 1.0),
    33: ('모든 용병의 베이스 데미지', 'pct', 3.0),
    34: ('모든 혼합 용병의 공격 속도', 'pct', 1.0),
    35: ('모든 용병의 추가 데미지', 'int', 2.5),
    36: ('소울번', 'pct', 1.0),
    39: ('신성 데미지', 'int', 2.0),
    40: ('물리 최종 데미지', 'pct', 0.316),
    41: ('마법 최종 데미지', 'pct', 0.316),
    42: ('카오스 최종 데미지', 'pct', 0.316),
    43: ('소울 클릭배수', 'pct', 1.0),
    45: ('모든 용병의 피격 지속시간 감소', 'pct', 1.0),
    46: ('뿔레정수 획득 확률', 'pct', 1.0),
    47: ('적들의 회피 확률 감소', 'pct', 1.0),
    48: ('순수 데미지', 'int', 1.0),
    49: ('침략자에게 추가 데미지', 'pct', 1.0),
    52: ('모든 용병의 행운 확률', 'pct', 1.0),
    53: ('모든 용병의 행운 배수', 'raw', 1.0),
    54: ('모든 용병의 최종 데미지', 'pct', 0.327),
    55: ('모든 용병의 성장 데미지', 'raw', 2.552),
    56: ('뿔레 조각 드랍 확률', 'pct', 1.0),
    57: ('모든 용병의 공포 극복 확률', 'pct', 1.0),
    59: ('모든 용병의 클릭 성장 데미지', 'raw', 0.7),
    60: ('모든 용병의 시작 레벨', 'int', 1.0),
    62: ('적 흡수 확률 감소', 'pct', 1.0),
    65: ('뿔레오브 획득 확률', 'pct', 1.0),
    66: ('피격 보호 확률', 'pct', 1.0),
    67: ('적 약화 감소', 'pct', 1.0),
    68: ('적 둔화 감소', 'pct', 1.0),
    69: ('뿔레토큰획득 확률', 'pct', 1.0),
    70: ('쥬얼 드랍 확률', 'pct', 1.0),
    76: ('아티팩트 드랍률 증가', 'pct', 1.0),
    77: ('더블어택 확률', 'pct', 1.0),
    87: ('치명타 확률', 'pct', 1.0),
    88: ('치명타 배수', 'raw', 0.5),
    89: ('모용 치명타 배수', 'raw', 0.5),
    197: ('모든 트리니티 용병의 강타배수', 'raw', 1.0),
    264: ('최종 데미지', 'pct', 1.0),
    314: ('적 방어막 효과 감소', 'pct', 1.0),
    315: ('적 부활 확률 감소', 'pct', 1.0),
    538: ('적 피해 면제 효과 감소', 'pct', 1.0),
    539: ('적 반사 효과 감소', 'pct', 1.0),
    18: ('연타 확률', 'pct', 1.0),
    19: ('모든 용병의 연타 확률', 'pct', 1.0),
    22: ('자동 클릭 확률', 'pct', 1.0),
    23: ('자동 클릭 속도', 'pct', 1.0),
    27: ('추가 클릭 확률', 'pct', 1.0),
    64: ('모든 용병의 연타 데미지', 'pct', 1.0),
    71: ('루비 드랍 확률', 'pct', 1.25),
    72: ('토파즈 드랍 확률', 'pct', 1.25),
    73: ('사파이어 드랍 확률', 'pct', 1.25),
    74: ('에메랄드 드랍 확률', 'pct', 1.25),
    75: ('자수정 드랍 확률', 'pct', 1.25),
    368: ('모든 용병의 추가 클릭 데미지', 'pct', 1.0),
    375: ('자동 클릭 데미지', 'pct', 1.0),
    431: ('모든 용병의 추가 클릭 확률', 'pct', 1.0),
    1013: ('모든 물리용병의 성장 데미지', 'pct', 1.0),
    1014: ('모든 마법용병의 성장 데미지', 'pct', 1.0),
    1015: ('모든 혼합용병의 성장 데미지', 'pct', 1.0),
    1019: ('물리 강타배수 증폭', 'raw', 1.0),
    1020: ('마법 강타배수 증폭', 'raw', 1.0),
    1021: ('혼합 강타배수 증폭', 'raw', 1.0),
    1168: ('모든 용병의 연타 간격 감소', 'pct', 0.8),
    1169: ('모든 용병의 연타 데미지 증폭', 'pct', 1.0),
    1171: ('즉시 공격 확률', 'pct', 1.0),
    1172: ('즉시 공격 데미지', 'pct', 1.0),
    1173: ('즉시 공격 속도', 'pct', 1.0),
}

# ---------------------------------------------------------------------------
# Step 2: Find codes where artifact mapping DIFFERS from generic mapping
# ---------------------------------------------------------------------------

print("=" * 70)
print("STEP 1: Finding differing type codes")
print("=" * 70)

generic_codes = set(MAINTYPE_TO_EFFECT.keys())
artifact_codes = set(ART_CODE_MAP.keys())

# Only codes in BOTH but with different names
differing_codes = {}  # code -> (generic_name, artifact_name)

for code in sorted(generic_codes & artifact_codes):
    generic_name = MAINTYPE_TO_EFFECT[code][0]
    artifact_name = ART_CODE_MAP[code]
    if generic_name != artifact_name:
        differing_codes[code] = (generic_name, artifact_name)

print(f"\nCodes in BOTH mappings but with DIFFERENT names: {len(differing_codes)}")
print()
for code, (gname, aname) in sorted(differing_codes.items()):
    print(f"  Code {code:4d}:")
    print(f"    Generic  : {gname}")
    print(f"    Artifact : {aname}")
    print()

if not differing_codes:
    print("No differences found. Nothing to fix.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# Value format helper
# ---------------------------------------------------------------------------

def format_effect_value(val: float, fmt: str = 'raw') -> str:
    if val == 0.0:
        return ''
    if fmt == 'pct':
        pct = val * 100
        if abs(pct - round(pct)) < 0.01:
            return f"{int(round(pct))}%"
        if abs(pct * 10 - round(pct * 10)) < 0.01:
            return f"{pct:.1f}%"
        return f"{pct:.2f}%"
    if fmt == 'int':
        return str(int(round(val)))
    if fmt == 'abs':
        ival = int(val)
        return f"+{ival}" if val == ival else f"+{val:.1f}"
    # 'raw'
    if val == int(val) and abs(val) >= 1:
        return str(int(val))
    s = f"{val:.6f}".rstrip('0').rstrip('.')
    return s


def infer_format(name: str) -> str:
    """Infer value format from the artifact-correct effect name.

    Per task spec:
    - '배수' in name (and NOT '증폭') -> 'raw'
    - '확률' or '데미지' in name       -> 'pct'
    - default                          -> 'pct'
    """
    if '배수' in name and '증폭' not in name:
        return 'raw'
    if '성장' in name:
        return 'raw'
    if any(kw in name for kw in ('확률', '속도', '데미지', '감소', '증폭',
                                  '획득', '저장', '증가', '관통', '중첩', '체감')):
        return 'pct'
    return 'raw'


# ---------------------------------------------------------------------------
# Step 3: Fix artifacts.json
# ---------------------------------------------------------------------------

print("=" * 70)
print("STEP 2: Fixing artifacts.json")
print("=" * 70)

artifacts_path = HERE / 'artifacts.json'
with open(artifacts_path, encoding='utf-8') as f:
    artifacts = json.load(f)

fixed_count = 0
affected_artifact_count = 0

for art in artifacts:
    art_was_fixed = False
    for eff in art.get('effects_resolved', []):
        code = eff.get('type_code')
        if code in differing_codes:
            _, correct_name = differing_codes[code]
            val = eff.get('value', 0.0)
            fmt = infer_format(correct_name)
            val_str = format_effect_value(val, fmt)
            old_name = eff['type_name']
            eff['type_name'] = correct_name
            eff['value_display'] = val_str
            eff['description'] = (f"{correct_name} {val_str}".strip()
                                   if val_str else correct_name)
            fixed_count += 1
            art_was_fixed = True
            print(f"  [{art['name']}] code {code}: '{old_name}' -> '{correct_name}' "
                  f"(val={val}, fmt={fmt}, display={val_str})")
    if art_was_fixed:
        affected_artifact_count += 1

print(f"\n  Fixed {fixed_count} effect entries across {affected_artifact_count} artifacts")

with open(artifacts_path, 'w', encoding='utf-8') as f:
    json.dump(artifacts, f, ensure_ascii=False, indent=2)
print(f"  Saved: {artifacts_path}")

# ---------------------------------------------------------------------------
# Step 4: Rebuild data_artifacts.json + index.html via build_artifact_data.py
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("STEP 3: Running build_artifact_data.py to rebuild web files")
print("=" * 70)

build_script = HERE / 'build_artifact_data.py'
result = subprocess.run(
    [sys.executable, str(build_script)],
    capture_output=True, text=True
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
if result.returncode != 0:
    print(f"ERROR: build_artifact_data.py exited with code {result.returncode}")
    sys.exit(1)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
print(f"\nSummary:")
print(f"  Differing type codes found : {len(differing_codes)}")
print(f"  Effect entries fixed       : {fixed_count}")
print(f"  Artifacts affected         : {affected_artifact_count}")
