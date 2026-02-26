"""
extract_all.py - Unified extraction script for 뿔레 전쟁 클리커 BGDatabase.

Reads bgdb_clean.bin and outputs 9 JSON files:
    creatures.json
    mercenary_skills.json
    random_merc_skills.json
    sub_slot_troops.json
    enemies.json
    equipment.json
    commanders_full.json
    artifacts.json
    mercenaries_by_grade.json

Usage:
    python3 extract_all.py
    python3 extract_all.py --bin /path/to/bgdb_clean.bin --out /path/to/output/dir
"""

import json
import re
import struct
import sys
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — import bgdb_utils from same directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from bgdb_utils import (
    load_binary,
    parse_int32_field,
    parse_float32_field,
    parse_bool_field,
    parse_rank_field,
    parse_kokr_strings,
    parse_name_map,
    get_table_strings,
    _field_data_region,
    build_localization,
    loc_text,
    KOKR_OFF,
    NAME_MAP_OFF,
)
from enhancement_multipliers import get_enhancement_multiplier

# ---------------------------------------------------------------------------
# Corrected mainType → effect mapping (calibrated from xlsx cross-reference)
# Format: mainType: (effect_name, value_format, display_ratio)
#   value_format: 'pct' = percentage, 'abs' = absolute number
#   display_ratio: binary_mainEffect × ratio = 0강 display value
# ---------------------------------------------------------------------------
MAINTYPE_TO_EFFECT = {
    # ── xlsx-verified (61 types) ──
    # Format: mainType: (effect_name, value_format, display_ratio)
    #   'pct' = multiply by 100 and append "%" (0.315 → "31.5%")
    #   'raw' = show decimal as-is (배수/multiplier types only)
    #   'int' = show as integer (absolute count types)
    0: ('데미지', 'pct', 4.5),
    90: ('데미지', 'pct', 1.0),  # binary stores at 1/1000 scale vs code 0; pre-scaled in resolve
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
    17: ('강타 배수', 'raw', 0.5),          # 배수: show as decimal (e.g. 0.05)
    20: ('모든 용병의 강타 확률', 'pct', 1.0),
    21: ('모든 용병의 강타 배수', 'raw', 1.0),  # 배수: show as decimal
    24: ('소울 클릭 확률', 'pct', 1.0),
    25: ('클릭 크리티컬 배수', 'raw', 1.0),     # 배수: show as decimal
    26: ('베이스 데미지', 'pct', 3.0),
    28: ('적들의 부활 감소', 'pct', 1.0),
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
    53: ('모든 용병의 행운 배수', 'raw', 1.0),   # 배수: show as decimal
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
    77: ('더블어택 확률', 'pct', 1.0),           # ratio 1.0: DB value is already 0-1 fraction
    87: ('치명타 확률', 'pct', 1.0),
    88: ('치명타 배수', 'raw', 0.5),
    89: ('모용 치명타 배수', 'raw', 0.5),
    197: ('모든 트리니티 용병의 강타배수', 'raw', 1.0),
    264: ('최종 데미지', 'pct', 1.0),
    314: ('적 방어막 효과 감소', 'pct', 1.0),
    315: ('적 부활 확률 감소', 'pct', 1.0),
    538: ('적 피해 면제 효과 감소', 'pct', 1.0),
    539: ('적 반사 효과 감소', 'pct', 1.0),
    # ── non-xlsx types (default pct unless multiplier/count type) ──
    18: ('연타 확률', 'pct', 1.0),
    19: ('모든 용병의 연타 확률', 'pct', 1.0),
    22: ('자동 클릭 확률', 'pct', 1.0),
    23: ('자동 클릭 속도', 'pct', 1.0),
    27: ('추가 클릭 확률', 'pct', 1.0),
    64: ('모든 용병의 연타 데미지', 'pct', 1.0),
    71: ('루비 드랍 확률', 'pct', 1.25),    # 블러드 루비: apk=0.04, xlsx=5% → ratio=1.25
    72: ('토파즈 드랍 확률', 'pct', 1.25),  # 썬 토파즈: apk=0.04, xlsx=5% → ratio=1.25
    73: ('사파이어 드랍 확률', 'pct', 1.25), # 오션 사파이어: apk=0.04, xlsx=5% → ratio=1.25
    74: ('에메랄드 드랍 확률', 'pct', 1.25), # 에버그린 에메랄드: apk=0.04, xlsx=5% → ratio=1.25
    75: ('자수정 드랍 확률', 'pct', 1.25),  # 새벽녘 자수정: apk=0.04, xlsx=5% → ratio=1.25
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

# Build name→format lookup from MAINTYPE_TO_EFFECT for consistent formatting.
# This allows artifact effects (which use ART_TYPE_TO_EFFECT for names) to get
# correct format even when their aType code differs from equipment mainType code.
NAME_TO_FORMAT: dict = {}
for _mt_code, (_mt_name, _mt_fmt, _mt_ratio) in MAINTYPE_TO_EFFECT.items():
    if _mt_name not in NAME_TO_FORMAT:
        NAME_TO_FORMAT[_mt_name] = _mt_fmt
# Add common name patterns not in MAINTYPE_TO_EFFECT
NAME_TO_FORMAT.update({
    '성장 데미지': 'raw',
    '클릭 성장 데미지': 'raw',
    '모든 용병의 클릭 성장 데미지': 'raw',
    '데미지 중첩': 'pct',
    '흡수 확률': 'pct',
    '선제공격 확률': 'pct',
    '축복 확률': 'pct',
    '저주 확률': 'pct',
    '봉인 확률': 'pct',
    '공포 확률': 'pct',
    '즉사 확률': 'pct',
    '방어막 확률': 'pct',
    '반사 확률': 'pct',
    '둔화 확률': 'pct',
    '약화 확률': 'pct',
    '부활 확률': 'pct',
    '피해 면제': 'pct',
    '절대명중 확률': 'pct',
    '입자 확률': 'pct',
    '즉시 공격': 'pct',
    '조각확': 'pct',
    '모용공극': 'pct',
    '소울번 확률': 'pct',
    '토큰 획득 확률': 'pct',
    '회복 데미지 증가': 'pct',
    '피격시 데미지 증가': 'pct',
    '즉시 공격 속도': 'pct',
    '즉시 공격 확률': 'pct',
    '즉시 공격 데미지': 'pct',
    '방어력 감소': 'pct',
    '치명타 딜레이 감소': 'pct',
    '피격 회피 확률': 'pct',
    '연타 배수': 'raw',
    '모든 용병의 소환 속도': 'pct',
    '연타 데미지': 'pct',
    '모든 용병의 연타 데미지': 'pct',
    '추클뎀': 'pct',
    '모용 추클뎀': 'pct',
})

# ---------------------------------------------------------------------------
# Artifact-specific type → effect name mapping (419 codes, built from APK+xlsx
# cross-reference with shift+1 offset correction).
# Only maps code → name string; value formatting uses the same logic as
# resolve_effects (pct/raw/int inferred from name keywords).
# Loaded from artifact_code_mapping.json at runtime.
# ---------------------------------------------------------------------------
def _load_art_type_mapping() -> dict:
    """Load artifact code→name mapping from artifact_code_mapping.json."""
    _here = Path(__file__).parent
    _path = _here / 'artifact_code_mapping.json'
    if _path.exists():
        with open(_path, encoding='utf-8') as _f:
            raw = json.load(_f)
        return {int(k): v for k, v in raw.items()}
    return {}

ART_TYPE_TO_EFFECT = _load_art_type_mapping()

# ---------------------------------------------------------------------------
# sec code → Korean effect template mapping (894 codes from BansheeGz DB)
# Used as fallback when ART_TYPE_TO_EFFECT doesn't have a code.
# ---------------------------------------------------------------------------
def _load_sec_mapping() -> dict:
    """Load sec code→Korean text mapping from sec_korean_mapping.json."""
    _here = Path(__file__).parent
    _path = _here / 'sec_korean_mapping.json'
    if _path.exists():
        with open(_path, encoding='utf-8') as _f:
            return json.load(_f)
    return {}

SEC_KOREAN_MAP = _load_sec_mapping()

# ---------------------------------------------------------------------------
# Table row counts
# ---------------------------------------------------------------------------
CREATURE_ROWS  = 539
ITEM_ROWS      = 1320
ENEMY_ROWS     = 387
BOSS_ROWS      = 110
STAGE_ROWS     = 500
EQUIP_ROWS     = 533
CMD_ROWS       = 35
SPEC_ROWS      = 35
ART_ROWS       = 557

# Damage scaling (raw DB value → game display value)
RAW_TO_GAME_DAMAGE = 4.0
RAW_TO_GAME_CLICK = 0.7

# Grade normalization
GRADE_NORMALIZE = {'Z': 'H'}

# ---------------------------------------------------------------------------
# Name-map slice starts (zero-based index into the name_map entries list)
# ---------------------------------------------------------------------------
CREATURE_MAP_START = 0
ITEM_MAP_START     = 539
ENEMY_MAP_START    = 1859
BOSS_MAP_START     = 2246
STAGE_MAP_START    = 2356
EQUIP_MAP_START    = 2856
CMD_MAP_START      = 3389
SPEC_MAP_START     = 3424
ART_MAP_START      = 3459

# ---------------------------------------------------------------------------
# Field offsets — creatureBase (539 rows)
# ---------------------------------------------------------------------------
CREATURE_FIELDS = {
    'index':            9070,
    'model':           11292,
    'rank':            13514,   # special rank encoding
    'attackType':      18434,
    'canG':            20661,   # bool
    'canAwaken':       21265,   # bool
    'skill0':          21874,
    'skill1':          24097,
    'skill2':          26320,
    'skill3':          28543,
    'skill4':          30766,
    'damageUp':        32989,
    'damage':          35214,
    'damageClickUp':   37437,
    'damageClick':     39667,
    'attackCooldown':  41895,   # float32
    'damageUpG':       44126,
    'damageG':         46352,
    'damageClickUpG':  48576,
    'damageClickG':    50807,
    'attackCooldownG': 53036,   # float32
    'exclusiveID0':    55268,
    'exclusiveID1':    57497,
    'exclusiveID2':    59726,
    'effectAttack':    61955,
    'requireOrb':      64184,
    'requireParticle': 66411,
    'typeRaceTop':     68643,
    'typeRace':        70871,
    'typeLocation':    73096,
    'typeGender':      75325,
    'typeIndividuality': 77552,
    'typeHouse':       79786,
    'typeReligion':    82012,
}

# ---------------------------------------------------------------------------
# Field offsets — itemBase (1320 rows)
# ---------------------------------------------------------------------------
ITEM_FIELDS = {
    'name':        105434,
    'index':       105503,
    'icon':        110849,
    'priceFactor': 116194,
    'passiveType': 121546,
    'type0':       126898,
    'effect0':     132244,
    'type1':       137592,
    'effect1':     142938,
    'type2':       148286,
    'effect2':     153632,
    'randomValue': 158980,
}

# ---------------------------------------------------------------------------
# Field offsets — enemy (387 rows)
# ---------------------------------------------------------------------------
ENEMY_FIELDS = {
    'name':           170596,
    'model':          170665,
    'factorHp':       172279,
    'resistPhysical': 173896,
    'resistMagical':  175519,
    'factorGold':     177141,
    'color':          178760,
    'isRunaway':      180374,
    'resistClick':    180831,
    'effectAttach':   182451,
    'block':          184072,
    'alpha':          185686,
    'cooldown':       187300,
    'chanceAttackAll':188917,
    'isMirroring':    190541,
}
ENEMY_BOOL_FIELDS  = {'isRunaway', 'isMirroring'}
ENEMY_FLOAT_FIELDS = {
    'factorHp', 'resistPhysical', 'resistMagical', 'factorGold',
    'resistClick', 'block', 'alpha', 'cooldown', 'chanceAttackAll',
}

# ---------------------------------------------------------------------------
# Field offsets — boss (110 rows)  [extracted but not output]
# ---------------------------------------------------------------------------
BOSS_FIELDS = {
    'name':           192831,
    'model':          192900,
    'resistPhysical': 193406,
    'resistMagical':  193921,
    'color':          194435,
    'coin':           194941,
    'resistClick':    195446,
    'effectAttach':   195958,
    'factorHp':       196471,
    'factorGold':     196980,
    'medal':          197491,
    'block':          197997,
    'alpha':          198503,
    'cooldown':       199009,
    'chanceAttackAll':199518,
    'isMirroring':    200034,
    'essence':        200216,
}

# ---------------------------------------------------------------------------
# Field offsets — equipment (533 rows)
# ---------------------------------------------------------------------------
EQUIP_FIELDS = {
    'name':          245888,
    'index':         245957,
    'icon':          248155,
    'mainType':      250352,
    'mainEffect':    252553,   # float32
    'mainEffectG':   254756,
    'rank':          256960,   # special rank encoding
    'hero0':         261826,
    'hero1':         264035,
    'hero2':         266244,
    'hero3':         268453,
    'hero4':         270662,
    'hero5':         272871,
    'specEffect':    275080,   # float32
    'isAvailableG':  277290,   # bool
    'cantPowerUp':   277896,   # bool
}

# ---------------------------------------------------------------------------
# Field offsets — commander (35 rows)
# ---------------------------------------------------------------------------
CMD_FIELDS = {
    'name':    279137,
    'index':   279206,
    'rarity':  279412,
    'icon':    279619,
    'gender':  279824,
    'statStr': 280031,
    'statInt': 280239,
    'statLuck':280447,
    'statChar':280656,
}

# ---------------------------------------------------------------------------
# Field offsets — commanderSpecialty (35 rows)
# ---------------------------------------------------------------------------
SPEC_FIELDS = {
    'name':        281510,
    'index':       281579,
    'icon':        281785,
    'targetIndex': 281990,
    'target':      282202,
    'type':        282409,   # nested string
    'effect':      283082,   # plain float32
}

# ---------------------------------------------------------------------------
# Field offsets — artifact (557 rows)
# ---------------------------------------------------------------------------
ART_FIELDS = {
    'name':     292276,
    'index':    292345,
    'icon':     294639,
    'rank':     296932,
    'dropTable':299225,
    'part':     301523,
    'set':      303816,
    'aType':    306108,   # nested int32
    'aEffect':  317958,   # nested float32
}


# ===========================================================================
# Helper — float32 bit-cast from int32
# ===========================================================================

def parse_grade_codes(data: bytes, rank_field_off: int, next_field_off: int, row_count: int) -> list:
    """Parse grade letter codes from the rank field region.

    The rank column region contains a run of uppercase ASCII letters (E, C, A, S, G, X, Z, etc.)
    where each letter is the grade code for one creature row.
    Z is normalized to H.
    """
    region = data[rank_field_off:next_field_off]
    best = None
    for m in re.finditer(rb'[A-Z]{100,}', region):
        s = m.group(0)
        if len(s) < row_count:
            continue
        if best is None or abs(len(s) - row_count) < abs(len(best) - row_count):
            best = s
            if len(s) == row_count:
                break
    if best is None:
        return ['?' for _ in range(row_count)]
    codes = best[:row_count].decode('ascii', errors='ignore')
    return [GRADE_NORMALIZE.get(c, c) for c in codes]


def int_to_float(val: int) -> float:
    """Reinterpret an int32 bit-pattern as IEEE-754 float32."""
    return struct.unpack('f', struct.pack('i', val))[0]


def format_effect_value(val: float, fmt: str = 'raw') -> str:
    """Format an effect value for display.

    fmt='raw': show decimal as-is (0.315, 0.06)
    fmt='pct': percentage display (0.018 → "1.8%")
    fmt='int': integer display (1800, 3)
    fmt='abs': legacy absolute number (+240)
    """
    if val == 0.0:
        return ''
    if fmt == 'pct':
        pct = val * 100
        if abs(pct - round(pct)) < 0.01:
            return f"{int(round(pct))}%"
        # Use enough decimals: 1.25% not 1.2%, 0.15% not 0.1%
        if abs(pct * 10 - round(pct * 10)) < 0.01:
            return f"{pct:.1f}%"
        return f"{pct:.2f}%"
    if fmt == 'int':
        return str(int(round(val)))
    if fmt == 'abs':
        ival = int(val)
        return f"+{ival}" if val == ival else f"+{val:.1f}"
    # 'raw': smart decimal formatting
    if val == int(val) and abs(val) >= 1:
        return str(int(val))
    # Remove trailing zeros but keep meaningful precision
    s = f"{val:.6f}".rstrip('0').rstrip('.')
    return s


def resolve_effects(types: list, effects: list, key_to_id: dict, ko_map: dict) -> list:
    """Resolve effect type codes + values into readable descriptions.

    For localized templates with {0} placeholders, the value is substituted
    into the template.  The clean type_name strips {0}/{1} markers.
    """
    result = []
    for t, e in zip(types, effects):
        if t == 0 and e == 0.0:
            continue
        # Try our calibrated mapping first
        mapping = MAINTYPE_TO_EFFECT.get(t)
        if mapping:
            ename, efmt, _ = mapping
            template = ename
        else:
            template = (loc_text(key_to_id, ko_map, f'sec{t}') or f'효과{t}').replace('\n', ' ').replace('\r', '')
            # Detect format from template context
            if '배수' in template:
                efmt = 'raw'
            elif '데미지' in template and abs(e) >= 100:
                efmt = 'int'
            elif any(kw in template for kw in ('확률', '속도', '데미지', '감소', '증폭')):
                efmt = 'pct'
            else:
                efmt = 'raw'
        val_str = format_effect_value(e, efmt)
        # Handle {0}/{1} template placeholders
        if '{0}' in template:
            desc = template.replace('{0}', val_str).replace('{1}', '').strip()
            clean_name = re.sub(r'\s*\{[0-9]\}', '', template).strip()
        else:
            desc = f"{template} {val_str}".strip() if val_str else template
            clean_name = template
        result.append({
            'type_code': t,
            'type_name': clean_name,
            'value': round(e, 6),
            'value_display': val_str,
            'description': desc,
        })
    return result


def resolve_artifact_effects(types: list, effects: list) -> list:
    """Resolve artifact effect type codes + values.

    Name priority:  MAINTYPE_TO_EFFECT (verified) > ART_TYPE_TO_EFFECT (partial) > '코드 N'
    Format priority: MAINTYPE_TO_EFFECT > NAME_TO_FORMAT > keyword heuristic
    Artifacts do NOT use display_ratio; raw DB values are formatted directly.
    """
    result = []
    for t, e in zip(types, effects):
        if t == 0 and e == 0.0:
            continue
        # code 90: binary stores 데미지 at 1/1000 scale vs code 0
        if t == 90:
            e = e * 1000
        # 1) Name: MAINTYPE_TO_EFFECT (verified) takes priority over ART_TYPE_TO_EFFECT
        main_mapping = MAINTYPE_TO_EFFECT.get(t)
        if main_mapping:
            template = main_mapping[0]
            efmt = main_mapping[1]
        else:
            ename = ART_TYPE_TO_EFFECT.get(t)
            template = ename if ename else f'코드 {t}'
            # 2) Format: NAME_TO_FORMAT > stripped NAME_TO_FORMAT > keyword heuristic
            # Strip prefix like "[세트] ", "(아티 장착시) " for lookup
            import re as _re
            stripped = _re.sub(r'^[\[\(][^\]\)]*[\]\)]\s*', '', template)
            if template in NAME_TO_FORMAT:
                efmt = NAME_TO_FORMAT[template]
            elif stripped in NAME_TO_FORMAT:
                efmt = NAME_TO_FORMAT[stripped]
            elif '배수' in template and '증폭' not in template:
                efmt = 'raw'
            elif '성장' in template:
                efmt = 'raw'
            elif '레벨' in template:
                efmt = 'int'
            elif any(kw in template for kw in ('확률', '속도', '데미지', '감소', '증폭', '획득', '저장', '증가', '추클뎀', '중첩', '관통', '체감')):
                efmt = 'pct'
            else:
                efmt = 'raw'

        val_str = format_effect_value(e, efmt)
        desc = f"{template} {val_str}".strip() if val_str else template
        result.append({
            'type_code': t,
            'type_name': template,
            'value': round(e, 6),
            'value_display': val_str,
            'description': desc,
        })
    return result


# ===========================================================================
# Nested array parsers (from fix_array_fields.py)
# ===========================================================================

def _parse_nested_index_table(raw: bytes, row_count: int):
    """Return (entries, data_section) for a BGDatabase nested-array block."""
    entries = []
    for i in range(row_count):
        entry_off = 4 + i * 8
        row_idx = struct.unpack_from('<I', raw, entry_off)[0]
        byte_off = struct.unpack_from('<I', raw, entry_off + 4)[0]
        entries.append((row_idx, byte_off))
    data_section_start = 4 + row_count * 8
    data_section = raw[data_section_start:]
    return entries, data_section


def _nested_row_slices(entries: list, data_section_len: int) -> dict:
    """Return {row_idx: (start, end)} byte slices within data_section."""
    sorted_entries = sorted(entries, key=lambda x: x[1])
    slices = {}
    for i, (ridx, boff) in enumerate(sorted_entries):
        bend = sorted_entries[i + 1][1] if i + 1 < len(sorted_entries) else data_section_len
        slices[ridx] = (boff, bend)
    return slices


def parse_nested_int32(data: bytes, field_off: int) -> list:
    """Parse a nested int32[] field -> list[list[int]], one list per row."""
    _, data_size, actual_start = _field_data_region(data, field_off)
    raw = data[actual_start: actual_start + data_size]
    row_count = struct.unpack_from('<I', raw, 0)[0]
    entries, ds = _parse_nested_index_table(raw, row_count)
    slices = _nested_row_slices(entries, len(ds))
    result = []
    for row_idx in range(row_count):
        if row_idx not in slices:
            result.append([])
            continue
        s, e = slices[row_idx]
        chunk = ds[s:e]
        vals = [struct.unpack_from('<i', chunk, j * 4)[0] for j in range(len(chunk) // 4)]
        result.append(vals)
    return result


def parse_nested_float32(data: bytes, field_off: int) -> list:
    """Parse a nested float32[] field -> list[list[float]], one list per row."""
    _, data_size, actual_start = _field_data_region(data, field_off)
    raw = data[actual_start: actual_start + data_size]
    row_count = struct.unpack_from('<I', raw, 0)[0]
    entries, ds = _parse_nested_index_table(raw, row_count)
    slices = _nested_row_slices(entries, len(ds))
    result = []
    for row_idx in range(row_count):
        if row_idx not in slices:
            result.append([])
            continue
        s, e = slices[row_idx]
        chunk = ds[s:e]
        vals = [struct.unpack_from('<f', chunk, j * 4)[0] for j in range(len(chunk) // 4)]
        result.append(vals)
    return result


def parse_nested_string(data: bytes, field_off: int) -> list:
    """Parse a nested string field -> list[str], one string per row."""
    _, data_size, actual_start = _field_data_region(data, field_off)
    raw = data[actual_start: actual_start + data_size]
    row_count = struct.unpack_from('<I', raw, 0)[0]
    entries, ds = _parse_nested_index_table(raw, row_count)
    slices = _nested_row_slices(entries, len(ds))
    result = []
    for row_idx in range(row_count):
        if row_idx not in slices:
            result.append('')
            continue
        s, e = slices[row_idx]
        result.append(ds[s:e].decode('utf-8', errors='replace'))
    return result


def parse_plain_float32(data: bytes, field_off: int) -> list:
    """Parse a plain scalar float32 field -> list[float]."""
    _, data_size, actual_start = _field_data_region(data, field_off)
    count = data_size // 4
    return [struct.unpack_from('<f', data, actual_start + i * 4)[0] for i in range(count)]


# ===========================================================================
# Creature string assignment (from extract_bgdb.py)
# ===========================================================================

def _extract_name_from_story(story: str) -> str:
    s = story.strip()
    if not s:
        return ''
    m = re.match(r'^[\s]*(\S+?)(?:의|은|는|이|가|을|를|와|과|에게|께서|로|으로)\s', s)
    if m:
        return m.group(1)
    tokens = s.split()
    return tokens[0] if tokens else ''


def assign_creature_strings(name_map_entries: list, strings: dict) -> list:
    """Assign name/class_name/story for each creature row.

    name_map_entries: flat list of (row_id, str_id) from parse_name_map().
    The first CREATURE_ROWS entries (indices 0..538) correspond to creatures.
    """
    # Build dict: row_index (0-based position in creature slice) -> str_id
    creature_map = {}
    for pos in range(CREATURE_ROWS):
        if pos < len(name_map_entries):
            _row_id, str_id = name_map_entries[pos]
            creature_map[pos] = str_id

    results = []
    for i in range(CREATURE_ROWS):
        if i not in creature_map:
            results.append({'name': '', 'class_name': '', 'story': ''})
            continue

        mapped_sid = creature_map[i]

        if i == 0:
            class_name = strings.get(0, '').strip()
            story = strings.get(1, '').strip()
            name = _extract_name_from_story(story)
        else:
            prev = strings.get(mapped_sid - 1, '')
            prev_stripped = prev.strip()
            mapped_str = strings.get(mapped_sid, '').strip()
            next_str = strings.get(mapped_sid + 1, '').strip()

            if len(prev_stripped) > 50:
                # Case A: prev is a long story -> mapped_sid is the NAME
                name = mapped_str
                class_name = next_str
                story_candidate = strings.get(mapped_sid + 2, '').strip()
                story = prev_stripped if len(prev_stripped) > len(story_candidate) else story_candidate
            elif len(prev_stripped) > 0:
                # Case B: prev is short -> mapped_sid is the CLASS, prev is the NAME
                raw_name = prev_stripped
                raw_class = mapped_str
                if len(raw_name) > 15:
                    name = raw_class
                    class_name = ''
                    story = next_str
                else:
                    name = raw_name
                    class_name = raw_class
                    story = next_str
            else:
                # No prev string: mapped_sid is the name
                name = mapped_str
                class_name = next_str
                story = strings.get(mapped_sid + 2, '').strip()

        results.append({'name': name, 'class_name': class_name, 'story': story})

    return results


# ===========================================================================
# Phase 1-3: Raw extraction of all tables
# ===========================================================================

def extract_creatures(data: bytes, name_map: list, strings: dict,
                      key_to_id: dict, ko_map: dict) -> list:
    print("  [creatureBase] Parsing fields...", flush=True)
    f = CREATURE_FIELDS
    index_vals         = parse_int32_field(data, f['index'])
    model_vals         = parse_int32_field(data, f['model'])
    rank_vals          = parse_rank_field(data, f['rank'], CREATURE_ROWS)
    attack_type_vals   = parse_int32_field(data, f['attackType'])
    can_g_vals         = parse_bool_field(data, f['canG'])
    can_awaken_vals    = parse_bool_field(data, f['canAwaken'])
    skill0_vals        = parse_int32_field(data, f['skill0'])
    skill1_vals        = parse_int32_field(data, f['skill1'])
    skill2_vals        = parse_int32_field(data, f['skill2'])
    skill3_vals        = parse_int32_field(data, f['skill3'])
    skill4_vals        = parse_int32_field(data, f['skill4'])
    damage_up_vals     = parse_int32_field(data, f['damageUp'])
    damage_vals        = parse_int32_field(data, f['damage'])
    dmg_clk_up_vals    = parse_int32_field(data, f['damageClickUp'])
    dmg_clk_vals       = parse_int32_field(data, f['damageClick'])
    atk_cd_vals        = parse_float32_field(data, f['attackCooldown'])
    damage_up_g_vals   = parse_int32_field(data, f['damageUpG'])
    damage_g_vals      = parse_int32_field(data, f['damageG'])
    dmg_clk_up_g_vals  = parse_int32_field(data, f['damageClickUpG'])
    dmg_clk_g_vals     = parse_int32_field(data, f['damageClickG'])
    atk_cd_g_vals      = parse_float32_field(data, f['attackCooldownG'])
    excl_id0_vals      = parse_int32_field(data, f['exclusiveID0'])
    excl_id1_vals      = parse_int32_field(data, f['exclusiveID1'])
    excl_id2_vals      = parse_int32_field(data, f['exclusiveID2'])
    effect_atk_vals    = parse_int32_field(data, f['effectAttack'])
    req_orb_vals       = parse_int32_field(data, f['requireOrb'])
    req_part_vals      = parse_int32_field(data, f['requireParticle'])
    type_race_top_vals = parse_int32_field(data, f['typeRaceTop'])
    type_race_vals     = parse_int32_field(data, f['typeRace'])
    type_loc_vals      = parse_int32_field(data, f['typeLocation'])
    type_gen_vals      = parse_int32_field(data, f['typeGender'])
    type_ind_vals      = parse_int32_field(data, f['typeIndividuality'])
    type_house_vals    = parse_int32_field(data, f['typeHouse'])
    type_rel_vals      = parse_int32_field(data, f['typeReligion'])

    # Parse grade codes from rank field region
    grade_codes = parse_grade_codes(data, f['rank'], f['attackType'], CREATURE_ROWS)

    def _loc(key):
        return loc_text(key_to_id, ko_map, key) or ''

    creatures = []
    for i in range(CREATURE_ROWS):
        hero_id = index_vals[i]

        # Localization-based name resolution
        name = _loc(f'hn{hero_id}')
        subtitle = _loc(f'hc{hero_id}')
        subtitle_grade = _loc(f'hcg{hero_id}')
        story = _loc(f'hs{hero_id}')

        # Fallback: extract name from story if hn key missing
        if not name and story:
            m = re.match(r'([가-힣A-Za-z0-9 _-]+?)의', story)
            if m:
                name = m.group(1).strip()

        # Skill resolution via localization keys
        skill_ids = [skill0_vals[i], skill1_vals[i], skill2_vals[i],
                     skill3_vals[i], skill4_vals[i]]
        skills = []
        for slot, sid in enumerate(skill_ids, start=1):
            skills.append({
                'slot': slot,
                'id': sid,
                'name': _loc(f'sn{sid}'),
                'description': _loc(f'ss{sid}'),
            })

        # Type label resolution via localization keys
        type_race_code = type_race_vals[i]
        type_loc_code = type_loc_vals[i]
        type_gen_code = type_gen_vals[i]
        type_house_code = type_house_vals[i]
        type_rel_code = type_rel_vals[i]
        type_ind_code = type_ind_vals[i]
        type_race_top_code = type_race_top_vals[i]

        # Damage scaling
        raw_dmg = damage_vals[i]
        raw_dmg_up = damage_up_vals[i]
        raw_click = dmg_clk_vals[i]
        raw_click_up = dmg_clk_up_vals[i]
        raw_dmg_g = damage_g_vals[i]
        raw_dmg_up_g = damage_up_g_vals[i]
        raw_click_g = dmg_clk_g_vals[i]
        raw_click_up_g = dmg_clk_up_g_vals[i]
        cd = round(atk_cd_vals[i], 2) if atk_cd_vals[i] > 0 else 0.0
        cd_g = round(atk_cd_g_vals[i], 6)

        base_damage = round(raw_dmg * RAW_TO_GAME_DAMAGE, 1)
        growth_damage = round(raw_dmg_up * RAW_TO_GAME_DAMAGE, 1)
        base_click = round(raw_click * RAW_TO_GAME_CLICK, 1)
        growth_click = round(raw_click_up * RAW_TO_GAME_CLICK, 1)

        # Attack type label
        ATTACK_TYPE_MAP = {0: '물리', 1: '마법', 2: '혼합', 3: '카오스', 6: '트리니티'}

        creatures.append({
            'hero_id': hero_id,
            'name': name,
            'grade': grade_codes[i],
            'subtitle': subtitle,
            'subtitle_grade': subtitle_grade,
            'story': story,
            'model': model_vals[i],
            'rank': rank_vals[i],
            'attackType': attack_type_vals[i],
            'attackType_kr': ATTACK_TYPE_MAP.get(attack_type_vals[i], '없음'),
            'canG': can_g_vals[i],
            'canAwaken': can_awaken_vals[i],
            'skills': skills,
            'damage_raw': {
                'damage': raw_dmg, 'damageUp': raw_dmg_up,
                'damageClick': raw_click, 'damageClickUp': raw_click_up,
            },
            'damageG_raw': {
                'damageG': raw_dmg_g, 'damageUpG': raw_dmg_up_g,
                'damageClickG': raw_click_g, 'damageClickUpG': raw_click_up_g,
            },
            'attackCooldown': cd,
            'attackCooldownG': cd_g,
            'sheet_stats': {
                'base_dps': round(base_damage / cd, 1) if cd else None,
                'attack_cooldown': cd,
                'growth_dps': round(growth_damage / cd, 1) if cd else None,
                'base_click_damage': base_click,
                'base_damage': base_damage,
                'growth_click_damage': growth_click,
                'growth_damage': growth_damage,
            },
            'exclusiveIDs': [excl_id0_vals[i], excl_id1_vals[i], excl_id2_vals[i]],
            'effectAttack': effect_atk_vals[i],
            'requireOrb': req_orb_vals[i],
            'requireParticle': req_part_vals[i],
            'types': {
                'race_top_code': type_race_top_code,
                'race_top': _loc(f'RaceTop{type_race_top_code}'),
                'race_code': type_race_code,
                'race': _loc(f'Race{type_race_code}'),
                'location_code': type_loc_code,
                'location': _loc(f'Location{type_loc_code}'),
                'gender_code': type_gen_code,
                'gender': _loc(f'Gender{type_gen_code}'),
                'house_code': type_house_code,
                'house': _loc(f'House{type_house_code}'),
                'religion_code': type_rel_code,
                'religion': _loc(f'Religion{type_rel_code}'),
                'individuality_code': type_ind_code,
                'individuality': _loc(f'Individuality{type_ind_code}'),
            },
        })
    print(f"  [creatureBase] {len(creatures)} rows extracted.")
    return creatures


def extract_items(data: bytes, name_map: list, strings: dict,
                   key_to_id: dict, ko_map: dict) -> list:
    print("  [itemBase] Parsing fields...", flush=True)
    f = ITEM_FIELDS
    index_vals   = parse_int32_field(data, f['index'])
    icon_vals    = parse_int32_field(data, f['icon'])
    pf_vals      = parse_int32_field(data, f['priceFactor'])
    pt_vals      = parse_int32_field(data, f['passiveType'])
    t0_vals      = parse_int32_field(data, f['type0'])
    e0_vals      = parse_int32_field(data, f['effect0'])
    t1_vals      = parse_int32_field(data, f['type1'])
    e1_vals      = parse_int32_field(data, f['effect1'])
    t2_vals      = parse_int32_field(data, f['type2'])
    e2_vals      = parse_int32_field(data, f['effect2'])
    rv_vals      = parse_int32_field(data, f['randomValue'])

    def _loc(key):
        return loc_text(key_to_id, ko_map, key) or ''

    items = []
    for i in range(ITEM_ROWS):
        idx = index_vals[i]
        types_raw = [t0_vals[i], t1_vals[i], t2_vals[i]]
        effects_raw = [
            round(int_to_float(e0_vals[i]), 6),
            round(int_to_float(e1_vals[i]), 6),
            round(int_to_float(e2_vals[i]), 6),
        ]

        # Resolve skill name via localization (sn{index})
        skill_name = _loc(f'sn{idx}')
        skill_desc = _loc(f'ss{idx}')

        # Resolve effect descriptions via sec{type} templates
        effects_resolved = resolve_effects(types_raw, effects_raw,
                                           key_to_id, ko_map)

        items.append({
            'index':       idx,
            'name':        skill_name,
            'description': skill_desc,
            'icon':        icon_vals[i],
            'priceFactor': round(int_to_float(pf_vals[i]), 6),
            'passiveType': pt_vals[i],
            'types':       types_raw,
            'effects':     effects_raw,
            'effects_resolved': effects_resolved,
            'randomValue': rv_vals[i],
        })
    print(f"  [itemBase] {len(items)} rows extracted.")
    return items


def extract_enemies(data: bytes, name_map: list, strings: dict) -> list:
    print("  [enemy] Parsing fields...", flush=True)
    f = ENEMY_FIELDS
    row_strings = get_table_strings(name_map, strings, ENEMY_MAP_START, ENEMY_ROWS, default_stride=5)

    model_vals    = parse_int32_field(data, f['model'])
    factorhp_vals = [round(v, 6) for v in parse_float32_field(data, f['factorHp'])]
    resphys_vals  = [round(v, 6) for v in parse_float32_field(data, f['resistPhysical'])]
    resmag_vals   = [round(v, 6) for v in parse_float32_field(data, f['resistMagical'])]
    factorgold    = [round(v, 6) for v in parse_float32_field(data, f['factorGold'])]
    color_vals    = parse_int32_field(data, f['color'])
    isrunaway     = parse_bool_field(data, f['isRunaway'])
    resclick      = [round(v, 6) for v in parse_float32_field(data, f['resistClick'])]
    effectattach  = parse_int32_field(data, f['effectAttach'])
    block_vals    = [round(v, 6) for v in parse_float32_field(data, f['block'])]
    alpha_vals    = [round(v, 6) for v in parse_float32_field(data, f['alpha'])]
    cooldown_vals = [round(v, 6) for v in parse_float32_field(data, f['cooldown'])]
    chanceatk     = [round(v, 6) for v in parse_float32_field(data, f['chanceAttackAll'])]
    ismirroring   = parse_bool_field(data, f['isMirroring'])

    def _g(lst, i, d=None):
        return lst[i] if i < len(lst) else d

    enemies = []
    for i in range(ENEMY_ROWS):
        enemies.append({
            'strings':        row_strings[i] if i < len(row_strings) else [],
            'model':          _g(model_vals, i, 0),
            'factorHp':       _g(factorhp_vals, i, 0.0),
            'resistPhysical': _g(resphys_vals, i, 0.0),
            'resistMagical':  _g(resmag_vals, i, 0.0),
            'factorGold':     _g(factorgold, i, 0.0),
            'color':          _g(color_vals, i, 0),
            'isRunaway':      bool(_g(isrunaway, i, False)),
            'resistClick':    _g(resclick, i, 0.0),
            'effectAttach':   _g(effectattach, i, 0),
            'block':          _g(block_vals, i, 0.0),
            'alpha':          _g(alpha_vals, i, 0.0),
            'cooldown':       _g(cooldown_vals, i, 0.0),
            'chanceAttackAll':_g(chanceatk, i, 0.0),
            'isMirroring':    bool(_g(ismirroring, i, False)),
        })
    print(f"  [enemy] {len(enemies)} rows extracted.")
    return enemies


def extract_bosses(data: bytes, key_to_id: dict, ko_map: dict) -> list:
    """보스 110개 추출 (이름, 저항, 배율, 보상 등)"""
    print("  [boss] Parsing fields...", flush=True)
    f = BOSS_FIELDS

    FLOAT_FIELDS = {'resistPhysical', 'resistMagical', 'resistClick',
                    'factorHp', 'factorGold', 'block', 'alpha',
                    'cooldown', 'chanceAttackAll', 'essence'}

    parsed = {}
    for fname, foff in f.items():
        if fname == 'isMirroring':
            parsed[fname] = parse_bool_field(data, foff)
        elif fname in FLOAT_FIELDS:
            parsed[fname] = [round(v, 6) for v in parse_float32_field(data, foff)]
        else:
            parsed[fname] = parse_int32_field(data, foff)

    def _g(field, i, d=None):
        lst = parsed.get(field, [])
        return lst[i] if i < len(lst) else d

    bosses = []
    for i in range(BOSS_ROWS):
        # Resolve boss name via bn{index} localization
        name = loc_text(key_to_id, ko_map, f'bn{i}') or ''

        bosses.append({
            'index':           i,
            'name':            name,
            'model':           _g('model', i, 0),
            'resistPhysical':  _g('resistPhysical', i, 1.0),
            'resistMagical':   _g('resistMagical', i, 1.0),
            'resistClick':     _g('resistClick', i, 1.0),
            'factorHp':        _g('factorHp', i, 1.0),
            'factorGold':      _g('factorGold', i, 1.0),
            'coin':            _g('coin', i, 0),
            'medal':           _g('medal', i, 0),
            'essence':         _g('essence', i, 0.0),
            'block':           _g('block', i, 0.0),
            'cooldown':        _g('cooldown', i, 0.0),
            'chanceAttackAll': _g('chanceAttackAll', i, 0.0),
            'isMirroring':     bool(_g('isMirroring', i, False)),
            'color':           _g('color', i, 0),
            'effectAttach':    _g('effectAttach', i, 0),
            'alpha':           _g('alpha', i, 0.0),
        })
    print(f"  [boss] {len(bosses)} rows extracted.")
    return bosses


def extract_equipment(data: bytes, name_map: list, strings: dict,
                       key_to_id: dict, ko_map: dict) -> list:
    print("  [equipment] Parsing fields...", flush=True)
    f = EQUIP_FIELDS

    index_vals  = parse_int32_field(data, f['index'])
    icon_vals   = parse_int32_field(data, f['icon'])
    maintype    = parse_int32_field(data, f['mainType'])
    maineff     = parse_float32_field(data, f['mainEffect'])
    maineffg    = parse_int32_field(data, f['mainEffectG'])
    rank_vals   = parse_rank_field(data, f['rank'], EQUIP_ROWS)
    hero0       = parse_int32_field(data, f['hero0'])
    hero1       = parse_int32_field(data, f['hero1'])
    hero2       = parse_int32_field(data, f['hero2'])
    hero3       = parse_int32_field(data, f['hero3'])
    hero4       = parse_int32_field(data, f['hero4'])
    hero5       = parse_int32_field(data, f['hero5'])
    speceff     = parse_float32_field(data, f['specEffect'])
    availg      = parse_bool_field(data, f['isAvailableG'])
    cantpu      = parse_bool_field(data, f['cantPowerUp'])

    # Parse grade codes from rank field region
    grade_codes = parse_grade_codes(data, f['rank'], f['hero0'], EQUIP_ROWS)

    def _g(lst, i, d=0):
        return lst[i] if i < len(lst) else d

    def _loc(key):
        return loc_text(key_to_id, ko_map, key) or ''

    equipment = []
    for i in range(EQUIP_ROWS):
        idx = _g(index_vals, i)
        mt = _g(maintype, i)
        me = round(_g(maineff, i, 0.0), 6)

        # Resolve name via in{index} localization
        name = _loc(f'in{idx}')

        # Resolve main effect type from calibrated mapping
        mapping = MAINTYPE_TO_EFFECT.get(mt)
        if mapping:
            main_type_name, val_fmt, display_ratio = mapping
        else:
            main_type_name = _loc(f'sec{mt}') if mt is not None else ''
            val_fmt = 'raw'
            display_ratio = 1.0

        # Compute 0강 display value
        display_val = me * display_ratio
        main_val_str = format_effect_value(display_val, val_fmt)
        main_desc = f"{main_type_name} {main_val_str}".strip() if main_type_name and main_val_str else main_type_name

        # 0강/20강 formatted strings
        is_cant_pu = bool(_g(cantpu, i, False))
        effect_0 = f"{main_type_name} {main_val_str}" if main_type_name and main_val_str else ''
        if is_cant_pu or not main_val_str:
            effect_20 = ''
        else:
            # Item-specific 20강/0강 multipliers extracted from xlsx 장비도감.
            # Rules (in priority order):
            #   1. ENHANCEMENT_OVERRIDES: 15 individual items with unique ratios
            #   2. ENHANCEMENT_X4_ITEMS: all mainType=0 (데미지) items + 2 클릭 데미지 items → ×4.0
            #   3. mainType == 0 fallback → ×4.0  (catches any mt=0 items not in the name set)
            #   4. Default → ×6.0
            # S→G upgradeable items always use ×6 (confirmed via xlsx)
            if bool(_g(availg, i, False)):
                enh_mult = 6.0
            else:
                enh_mult = get_enhancement_multiplier(name, mt)
            val_20 = display_val * enh_mult
            effect_20 = f"{main_type_name} {format_effect_value(val_20, val_fmt)}"

        # S→G upgrade: decode mainEffectG as float32 and compute G-grade values
        is_avail_g = bool(_g(availg, i, False))
        effect_0_g = ''
        effect_20_g = ''
        if is_avail_g:
            raw_g = _g(maineffg, i, 0)
            if raw_g and raw_g != 0:
                try:
                    me_g = struct.unpack('f', struct.pack('I', raw_g & 0xFFFFFFFF))[0]
                    display_val_g = me_g * display_ratio
                    val_str_g = format_effect_value(display_val_g, val_fmt)
                    effect_0_g = f"{main_type_name} {val_str_g}" if main_type_name and val_str_g else ''
                    # G-grade always uses ×6 enhancement
                    val_20_g = display_val_g * 6.0
                    effect_20_g = f"{main_type_name} {format_effect_value(val_20_g, val_fmt)}" if main_type_name else ''
                except (struct.error, OverflowError):
                    pass

        equipment.append({
            'index':           idx,
            'name':            name,
            'grade':           grade_codes[i],
            'icon':            _g(icon_vals, i),
            'mainType':        mt,
            'mainType_name':   main_type_name,
            'mainEffect':      me,
            'mainEffect_display': round(display_val, 6),
            'mainEffect_desc': main_desc,
            'effect_0':        effect_0,
            'effect_20':       effect_20,
            'effect_0_g':      effect_0_g,
            'effect_20_g':     effect_20_g,
            'mainEffectG':     _g(maineffg, i),
            'rank':            _g(rank_vals, i),
            'specializedHero': [
                _g(hero0, i), _g(hero1, i), _g(hero2, i),
                _g(hero3, i), _g(hero4, i), _g(hero5, i),
            ],
            'specializedEffect': round(_g(speceff, i, 0.0), 6),
            'isAvailableG':    bool(_g(availg, i, False)),
            'cantPowerUp':     is_cant_pu,
        })
    print(f"  [equipment] {len(equipment)} rows extracted.")
    return equipment


def extract_commanders(data: bytes, name_map: list, strings: dict) -> list:
    print("  [commander] Parsing fields...", flush=True)
    f = CMD_FIELDS
    cmd_strings = get_table_strings(name_map, strings, CMD_MAP_START, CMD_ROWS, default_stride=6)

    index_vals    = parse_int32_field(data, f['index'])
    rarity_vals   = parse_int32_field(data, f['rarity'])
    icon_vals     = parse_int32_field(data, f['icon'])
    gender_vals   = parse_int32_field(data, f['gender'])
    statstr_vals  = parse_int32_field(data, f['statStr'])
    statint_vals  = parse_int32_field(data, f['statInt'])
    statluck_vals = parse_int32_field(data, f['statLuck'])
    statchar_vals = parse_int32_field(data, f['statChar'])

    commanders = []
    for i in range(CMD_ROWS):
        commanders.append({
            'index':    index_vals[i]    if i < len(index_vals)    else None,
            'strings':  cmd_strings[i]   if i < len(cmd_strings)   else [],
            'rarity':   rarity_vals[i]   if i < len(rarity_vals)   else None,
            'icon':     icon_vals[i]     if i < len(icon_vals)     else None,
            'gender':   gender_vals[i]   if i < len(gender_vals)   else None,
            'statStr':  statstr_vals[i]  if i < len(statstr_vals)  else None,
            'statInt':  statint_vals[i]  if i < len(statint_vals)  else None,
            'statLuck': statluck_vals[i] if i < len(statluck_vals) else None,
            'statChar': statchar_vals[i] if i < len(statchar_vals) else None,
        })
    print(f"  [commander] {len(commanders)} rows extracted.")
    return commanders


def extract_specialties(data: bytes, name_map: list, strings: dict) -> list:
    print("  [commanderSpecialty] Parsing fields...", flush=True)
    f = SPEC_FIELDS
    spec_strings = get_table_strings(name_map, strings, SPEC_MAP_START, SPEC_ROWS, default_stride=6)

    index_vals       = parse_int32_field(data, f['index'])
    icon_vals        = parse_int32_field(data, f['icon'])
    targetindex_vals = parse_int32_field(data, f['targetIndex'])
    target_vals      = parse_int32_field(data, f['target'])

    # Phase 2 array fields
    type_rows    = parse_nested_string(data, f['type'])    # list[str]
    effect_vals  = parse_plain_float32(data, f['effect'])  # list[float]

    specialties = []
    for i in range(SPEC_ROWS):
        specialties.append({
            'index':       index_vals[i]       if i < len(index_vals)       else None,
            'strings':     spec_strings[i]     if i < len(spec_strings)     else [],
            'icon':        icon_vals[i]        if i < len(icon_vals)        else None,
            'targetIndex': targetindex_vals[i] if i < len(targetindex_vals) else None,
            'target':      target_vals[i]      if i < len(target_vals)      else None,
            'type':        type_rows[i]        if i < len(type_rows)        else '',
            'effect':      round(effect_vals[i], 6) if i < len(effect_vals) else 0.0,
        })
    print(f"  [commanderSpecialty] {len(specialties)} rows extracted.")
    return specialties


def extract_artifacts(data: bytes, name_map: list, strings: dict,
                       key_to_id: dict, ko_map: dict) -> list:
    print("  [artifact] Parsing fields...", flush=True)
    f = ART_FIELDS

    index_vals     = parse_int32_field(data, f['index'])
    icon_vals      = parse_int32_field(data, f['icon'])
    rank_vals      = parse_int32_field(data, f['rank'])
    droptable_vals = parse_int32_field(data, f['dropTable'])
    part_vals      = parse_int32_field(data, f['part'])
    set_vals       = parse_int32_field(data, f['set'])

    # Phase 2 nested array fields
    atype_rows   = parse_nested_int32(data, f['aType'])     # list[list[int]]
    aeffect_rows = parse_nested_float32(data, f['aEffect'])  # list[list[float]]

    # Part label mapping (confirmed: 0=무기, 1=투구, 2=갑옷, 3=보조)
    PART_LABELS = {0: '무기', 1: '투구', 2: '갑옷', 3: '보조'}
    # Rank → grade mapping (E D C B A S G X H O P Q 유료)
    RANK_TO_GRADE = {0:'E', 1:'D', 2:'C', 3:'B', 4:'A', 5:'S', 6:'G', 7:'X', 8:'H', 9:'O', 10:'P', 11:'Q', 15:'유료'}

    def _g(lst, i, d=None):
        return lst[i] if i < len(lst) else d

    def _loc(key):
        return loc_text(key_to_id, ko_map, key) or ''

    artifacts = []
    for i in range(ART_ROWS):
        idx = _g(index_vals, i, 0)
        set_id = _g(set_vals, i, 0)
        part_code = _g(part_vals, i, 0)

        # Resolve name via an{index} localization
        name = _loc(f'an{idx}')

        # Resolve set name via anSet{set_id}
        set_name = _loc(f'anSet{set_id}') if set_id else ''

        # Shift+1 offset correction: artifact at position i uses BOTH aType AND
        # aEffect from position i-1.  Verified by cross-referencing APK data with
        # xlsx reference (56% main-value match with both shifted vs 8% type-only).
        # Artifact at i=0 has no previous row, so use empty arrays.
        if i >= 1:
            atypes = atype_rows[i - 1] if (i - 1) < len(atype_rows) else []
            aeffects = [round(v, 6) for v in (aeffect_rows[i - 1] if (i - 1) < len(aeffect_rows) else [])]
        else:
            atypes = []
            aeffects = []
        # Grade D/C/B (rank 1,2,3) store effect values at 2× in the binary.
        # Verified by cross-referencing with xlsx: 84% of D-grade, 73% of C-grade,
        # 74% of B-grade values are exactly 2× the reference.
        rank_code = _g(rank_vals, i, 0)
        if rank_code in (1, 2, 3):  # D, C, B
            aeffects = [round(v / 2.0, 6) for v in aeffects]

        # Use artifact-specific mapping (ART_TYPE_TO_EFFECT) instead of equipment mapping
        effects_resolved = resolve_artifact_effects(atypes, aeffects)

        artifacts.append({
            'index':     idx,
            'name':      name,
            'set_id':    set_id,
            'set_name':  set_name,
            'icon':      _g(icon_vals, i, None),
            'rank':      rank_code,
            'grade':     RANK_TO_GRADE.get(rank_code, f'?{rank_code}'),
            'dropTable': _g(droptable_vals, i, None),
            'part':      part_code,
            'part_name': PART_LABELS.get(part_code, f'부위{part_code}'),
            'aType':     atypes,
            'aEffect':   aeffects,
            'effects_resolved': effects_resolved,
        })
    print(f"  [artifact] {len(artifacts)} rows extracted.")
    return artifacts


# ===========================================================================
# Phase 4: Build cross-reference lookups
# ===========================================================================

def build_creature_lookup(creatures: list) -> dict:
    """hero_id -> Korean name"""
    return {c['hero_id']: c['name'] for c in creatures}


def build_item_lookup(items: list) -> dict:
    """index -> Korean short name.

    The name_map base_sid for itemBase alternates between pointing directly
    to the short name or to a long description (with the short name at sid+1).
    Heuristic: if strings[0] is long (>30 chars) then strings[1] is the name,
    otherwise strings[0] is the name.
    """
    lookup = {}
    for it in items:
        idx = it['index']
        strs = it['strings']
        if not strs:
            lookup[idx] = ''
        elif len(strs[0]) > 30:
            # strings[0] is a long description; name is at strings[1]
            lookup[idx] = strs[1].strip() if len(strs) > 1 else ''
        else:
            lookup[idx] = strs[0].strip()
    return lookup


def build_equipment_lookup(equipment: list) -> dict:
    """index -> Korean name"""
    return {eq['index']: eq['name'] for eq in equipment}


# ===========================================================================
# Phase 5: Enrich & Cross-Reference
# ===========================================================================

def enrich_creatures(creatures: list, equip_lookup: dict) -> list:
    """Add exclusive_names via equipment cross-reference."""
    for c in creatures:
        c['exclusive_names'] = [equip_lookup.get(eid, '') for eid in c['exclusiveIDs']]
    return creatures


def build_mercenaries_by_grade(creatures: list) -> dict:
    """Build the user-facing mercenaries_by_grade.json output.

    Each creature becomes a record with Korean field names:
    이름, 등급, 부제, 스킬[], 종족, 가문, 지역, 성별, 종교, 개성,
    데미지타입, 기본DPS, 공격쿨다운, 성장DPS, 기본클릭데미지, 기본데미지, 성장클릭데미지, 성장데미지
    """
    records = []
    for c in creatures:
        types = c['types']
        stats = c['sheet_stats']

        skill_list = []
        for sk in c['skills']:
            skill_list.append({
                'slot': sk['slot'],
                '이름': sk['name'] or '없음',
                '설명': sk['description'] or '',
            })

        records.append({
            '이름': c['name'] or 'UNKNOWN',
            '등급': c['grade'],
            '부제': c['subtitle'] or '',
            '스킬': skill_list,
            '종족': types.get('race') or '없음',
            '가문': types.get('house') or '없음',
            '지역': types.get('location') or '없음',
            '성별': types.get('gender') or '없음',
            '종교': types.get('religion') or '없음',
            '개성': types.get('individuality') or '없음',
            '데미지타입': c['attackType_kr'] or '없음',
            '기본 DPS': stats['base_dps'],
            '공격 쿨다운': stats['attack_cooldown'],
            '성장 DPS': stats['growth_dps'],
            '기본 클릭 데미지': stats['base_click_damage'],
            '기본 데미지': stats['base_damage'],
            '성장 클릭 데미지': stats['growth_click_damage'],
            '성장 데미지': stats['growth_damage'],
            'hero_id': c['hero_id'],
            'model_id': c['model'],
        })

    return {
        'meta': {
            'record_rule': '같은 이름이라도 등급별 독립 객체',
            'grade_normalization': {'Z': 'H'},
            'damage_scaling': f'base/growth_damage = raw*{RAW_TO_GAME_DAMAGE}, click = raw*{RAW_TO_GAME_CLICK}',
            'count': len(records),
        },
        'records': records,
    }


def split_items(items: list) -> tuple:
    """Split itemBase into three groups based on passiveType and randomValue."""
    mercenary_skills   = []
    random_merc_skills = []
    sub_slot_troops    = []

    for it in items:
        pt = it['passiveType']
        rv = it['randomValue']
        if pt == 0 and rv == 0:
            mercenary_skills.append(it)
        elif pt == 0 and rv > 0:
            random_merc_skills.append(it)
        else:  # pt > 0
            sub_slot_troops.append(it)

    return mercenary_skills, random_merc_skills, sub_slot_troops


def enrich_equipment(equipment: list, creature_lookup: dict) -> list:
    """Add specialized_names by resolving specializedHero IDs to creature names."""
    for eq in equipment:
        eq['specialized_names'] = [
            creature_lookup.get(h, '') for h in eq['specializedHero']
        ]
    return equipment


def enrich_premium_artifacts(artifacts: list) -> list:
    """Replace premium (유료) artifact effects with user-verified data.

    Loads premium_effects.json (generated by premium_effects.py) which contains
    authoritative effect data for all 32 premium artifacts, including main effects,
    보조옵션, and set/condition effects.
    """
    prem_path = Path(__file__).parent / 'premium_effects.json'
    if not prem_path.exists():
        print("  [premium] premium_effects.json not found, skipping")
        return artifacts

    with open(prem_path, 'r', encoding='utf-8') as f:
        prem_data = json.load(f)

    count = 0
    for art in artifacts:
        if art.get('grade') != '유료':
            continue
        effects_list = prem_data.get(art['name'])
        if not effects_list:
            continue

        new_effects = []
        for eff in effects_list:
            entry = {
                'type_code': -3 if eff.get('is_sub') else -1,
                'type_name': eff['description'].split(' ')[0] if ' ' in eff['description'] else eff['description'],
                'value': 0,
                'value_display': eff.get('value_display', ''),
                'description': eff['description'],
            }
            if eff.get('is_sub'):
                entry['is_sub'] = True
            new_effects.append(entry)

        art['effects_resolved'] = new_effects
        count += 1

    print(f"  [premium] Enriched {count} premium artifacts from premium_effects.json")
    return artifacts


def load_commander_excel_names(additional_strings_path: Path) -> list:
    """Load verified commander Korean names from additional_strings.json.

    Returns a list of dicts with 'name' and 'grade' keys, positionally
    ordered to match the 35 commanders sorted by their extraction order.
    The spreadsheet has 34 entries (34/35 verified correct).

    Parameters
    ----------
    additional_strings_path : Path
        Path to additional_strings.json.

    Returns
    -------
    list[dict]
        List of {'name': str, 'grade': str} entries, length <= 35.
        Missing entries return {'name': '', 'grade': ''}.
    """
    if not additional_strings_path.exists():
        print(f"  WARNING: {additional_strings_path} not found, skipping commander names.")
        return []
    try:
        with open(additional_strings_path, encoding='utf-8') as fh:
            add = json.load(fh)
        entries = add['tables']['commanders']['entries']
        print(f"  Loaded {len(entries)} commander names from additional_strings.json")
        return entries
    except Exception as exc:
        print(f"  WARNING: Could not load commander names: {exc}")
        return []


def build_commanders_full(commanders: list, specialties: list,
                          excel_names: list) -> dict:
    """Merge commanders with their specialties and apply Excel Korean names.

    specialty.targetIndex == commander.index -> belongs to that commander.
    specialty.targetIndex == -1 -> global specialty.

    Parameters
    ----------
    commanders : list
        Raw commander records (35 rows, strings=[]).
    specialties : list
        Raw commanderSpecialty records (35 rows).
    excel_names : list
        Positionally ordered names from additional_strings.json.
        Entry i maps to commanders[i] in extraction order (by position, not index).
    """
    # Apply Excel names positionally (commanders are in extraction order 0..34)
    for pos, cmd in enumerate(commanders):
        if pos < len(excel_names):
            entry = excel_names[pos]
            cmd['name_ko'] = entry.get('name', '')
            cmd['grade']   = entry.get('grade', '')
        else:
            cmd['name_ko'] = ''
            cmd['grade']   = ''

    # Build map: commander index -> specialty list
    cmd_index_to_specs = {}
    global_specs = []

    for spec in specialties:
        ti = spec['targetIndex']
        if ti == -1:
            global_specs.append(spec)
        else:
            cmd_index_to_specs.setdefault(ti, []).append(spec)

    enriched_commanders = []
    for cmd in commanders:
        cidx = cmd['index']
        cmd_copy = dict(cmd)
        cmd_copy['specialties'] = cmd_index_to_specs.get(cidx, [])
        enriched_commanders.append(cmd_copy)

    return {
        'commanders': enriched_commanders,
        'global_specialties': global_specs,
    }


# ===========================================================================
# Phase 6: Save output files
# ===========================================================================

def save_json(obj, path: Path) -> None:
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


# ===========================================================================
# Phase 7: Print summary
# ===========================================================================

def print_summary(label: str, data: list, path: Path) -> None:
    size = path.stat().st_size
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Rows: {len(data)}  |  File size: {size:,} bytes  ({size/1024:.1f} KB)")
    print(f"  Path: {path}")
    print(f"  First 3 rows (truncated):")
    for i, row in enumerate(data[:3]):
        # Truncate long strings for readability
        display = {}
        for k, v in row.items():
            if isinstance(v, list) and len(v) > 8:
                display[k] = v[:8] + ['...']
            elif isinstance(v, str) and len(v) > 80:
                display[k] = v[:80] + '...'
            elif isinstance(v, dict):
                display[k] = v
            else:
                display[k] = v
        print(f"    [{i}] {json.dumps(display, ensure_ascii=False)[:200]}")


def print_summary_dict(label: str, data: dict, path: Path) -> None:
    size = path.stat().st_size
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  File size: {size:,} bytes  ({size/1024:.1f} KB)")
    print(f"  Path: {path}")
    cmds = data.get('commanders', [])
    gspecs = data.get('global_specialties', [])
    print(f"  Commanders: {len(cmds)}  |  Global specialties: {len(gspecs)}")
    for i, cmd in enumerate(cmds[:3]):
        print(f"    commander[{i}] index={cmd.get('index')} "
              f"strings={cmd.get('strings', [])[:2]} "
              f"rarity={cmd.get('rarity')} "
              f"specialties_count={len(cmd.get('specialties', []))}")


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description='Extract all BGDatabase tables to JSON')
    parser.add_argument('--bin', default=str(Path(__file__).parent / 'bgdb_clean.bin'),
                        help='Path to bgdb_clean.bin')
    parser.add_argument('--out', default=str(Path(__file__).parent),
                        help='Output directory')
    args = parser.parse_args()

    bin_path = Path(args.bin)
    out_dir  = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading binary: {bin_path}", flush=True)
    data = load_binary(bin_path)
    print(f"  File size: {len(data):,} bytes")

    print("\nParsing koKR string table...", flush=True)
    strings = parse_kokr_strings(data)
    print(f"  {len(strings)} strings loaded (max sid={max(strings) if strings else 0})")

    print("Parsing name_map...", flush=True)
    name_map = parse_name_map(data)
    print(f"  {len(name_map)} entries loaded")

    print("Building localization lookup...", flush=True)
    key_to_id, ko_map = build_localization(data)
    print(f"  {len(key_to_id)} localization keys, {len(ko_map)} Korean strings")

    # -----------------------------------------------------------------------
    # Phase 1+2+3: Raw extraction of all tables
    # -----------------------------------------------------------------------
    print("\n--- Phase 1-3: Raw Extraction ---", flush=True)

    creatures   = extract_creatures(data, name_map, strings, key_to_id, ko_map)
    items       = extract_items(data, name_map, strings, key_to_id, ko_map)
    enemies     = extract_enemies(data, name_map, strings)
    bosses      = extract_bosses(data, key_to_id, ko_map)
    equipment   = extract_equipment(data, name_map, strings, key_to_id, ko_map)
    commanders  = extract_commanders(data, name_map, strings)
    specialties = extract_specialties(data, name_map, strings)
    artifacts   = extract_artifacts(data, name_map, strings, key_to_id, ko_map)

    # -----------------------------------------------------------------------
    # Phase 4: Build lookups
    # -----------------------------------------------------------------------
    print("\n--- Phase 4: Building cross-reference lookups ---", flush=True)
    creature_lookup = build_creature_lookup(creatures)
    equip_lookup    = build_equipment_lookup(equipment)
    print(f"  creature_lookup: {len(creature_lookup)} entries")
    print(f"  equip_lookup:    {len(equip_lookup)} entries")

    # -----------------------------------------------------------------------
    # Phase 5: Enrich
    # -----------------------------------------------------------------------
    print("\n--- Phase 5: Enriching & cross-referencing ---", flush=True)

    # Enrich creatures with exclusive_names
    creatures = enrich_creatures(creatures, equip_lookup)

    # Split itemBase into three output groups
    mercenary_skills, random_merc_skills, sub_slot_troops = split_items(items)
    print(f"  mercenary_skills:   {len(mercenary_skills)}")
    print(f"  random_merc_skills: {len(random_merc_skills)}")
    print(f"  sub_slot_troops:    {len(sub_slot_troops)}")

    # Enrich equipment with specialized_names
    equipment = enrich_equipment(equipment, creature_lookup)

    # Enrich premium (유료) artifacts with xlsx paired effects
    artifacts = enrich_premium_artifacts(artifacts)

    # Load verified Excel commander names (only commanders use Excel data per spec)
    add_strings_path = Path(args.bin).parent / 'additional_strings.json'
    excel_names = load_commander_excel_names(add_strings_path)

    # Merge commanders + specialties (with Excel Korean names applied)
    commanders_full = build_commanders_full(commanders, specialties, excel_names)

    # -----------------------------------------------------------------------
    # Phase 6: Save output files
    # -----------------------------------------------------------------------
    print("\n--- Phase 6: Saving output files ---", flush=True)

    p_creatures   = out_dir / 'creatures.json'
    p_merc        = out_dir / 'mercenary_skills.json'
    p_rand        = out_dir / 'random_merc_skills.json'
    p_sub         = out_dir / 'sub_slot_troops.json'
    p_enemies     = out_dir / 'enemies.json'
    p_bosses      = out_dir / 'bosses.json'
    p_equipment   = out_dir / 'equipment.json'
    p_commanders  = out_dir / 'commanders_full.json'
    p_artifacts   = out_dir / 'artifacts.json'

    save_json(creatures,          p_creatures)
    save_json(mercenary_skills,   p_merc)
    save_json(random_merc_skills, p_rand)
    save_json(sub_slot_troops,    p_sub)
    save_json(enemies,            p_enemies)
    save_json(bosses,             p_bosses)
    save_json(equipment,          p_equipment)
    save_json(commanders_full,    p_commanders)
    save_json(artifacts,          p_artifacts)

    # Build and save mercenaries_by_grade.json
    merc_by_grade = build_mercenaries_by_grade(creatures)
    p_merc_grade = out_dir / 'mercenaries_by_grade.json'
    save_json(merc_by_grade, p_merc_grade)

    print("  All files written.")

    # -----------------------------------------------------------------------
    # Phase 7: Summary
    # -----------------------------------------------------------------------
    print("\n\n========== EXTRACTION SUMMARY ==========")

    print_summary("creatures.json",          creatures,          p_creatures)
    print_summary("mercenary_skills.json",   mercenary_skills,   p_merc)
    print_summary("random_merc_skills.json", random_merc_skills, p_rand)
    print_summary("sub_slot_troops.json",    sub_slot_troops,    p_sub)
    print_summary("enemies.json",            enemies,            p_enemies)
    print_summary("bosses.json",             bosses,             p_bosses)
    print_summary("equipment.json",          equipment,          p_equipment)
    print_summary_dict("commanders_full.json", commanders_full,  p_commanders)
    print_summary("artifacts.json",          artifacts,          p_artifacts)

    # mercenaries_by_grade summary (dict structure, not a plain list)
    mg_size = p_merc_grade.stat().st_size
    print(f"\n{'='*60}")
    print(f"  mercenaries_by_grade.json")
    print(f"  Records: {merc_by_grade['meta']['count']}  |  File size: {mg_size:,} bytes  ({mg_size/1024:.1f} KB)")
    print(f"  Path: {p_merc_grade}")
    for i, rec in enumerate(merc_by_grade['records'][:3]):
        print(f"    [{i}] {rec.get('이름')} ({rec.get('등급')}) - {rec.get('부제', '')}")

    print(f"\n{'='*60}")
    print("Done. All 9 files written to:", out_dir)


if __name__ == '__main__':
    main()
