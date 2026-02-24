#!/usr/bin/env python3
"""
Regenerate all 265 random mercenary skill data using corrected type code mapping.

User-confirmed corrections (values include 1.3x bonus):
- 마법의투쟁(7): type4=마법 용병 데미지(×300), type29=마법 용병 강타 배수(raw)
- 탈모(4): type9=공격 속도(×100), type7=추가 데미지(raw_int, ×2)
- 노쓰페라투쓰의위압(9): type20=강타 확률(×100), type26=강타 배수(raw), type107=피격 지속시간 감소(×100)
- 영혼흡수(5): type40=소울 클릭 확률(×100)
- 광분(5): type32=연타 확률(×100)
- 불신(5): type20=강타 확률(×100), type53=카오스 취약성(×100)
- 자유인의의지(7): type43=추가 클릭 확률(×100), type122=추가 클릭 데미지(×100)
- 재물신 관우의 부적(4): type46=골드 획득량(×100)
- 전사들의열정(8): type11=물리 용병 공격 속도(×100), type22=물리 용병 강타 확률(×100)
- 넝쿨채찍: type7=추가 데미지(raw_int,×2), type421=[식물]용병수×% 데미지, type422=[식물]용병수×% 클릭데미지
"""

import json
import re
import math
import sys

# ============================================================
# STEP 1: Build the comprehensive type mapping
# ============================================================

# Start with full mapping - combining existing mapping + user corrections + effects_resolved names
# User-confirmed values take priority over effects_resolved guesses

TYPE_MAPPING = {
    # --- User-confirmed from cross-referencing APK data vs in-game display ---

    # type 1: 데미지 (pct, ×150)
    # Verified: multiple skills
    1: {"effect_name": "데미지", "format": "pct", "base_multiplier": 150.0, "has_random_bonus": True},

    # type 2: 모든 용병 데미지 (pct, ×300)
    2: {"effect_name": "모든 용병 데미지", "format": "pct", "base_multiplier": 300.0, "has_random_bonus": True},

    # type 3: 클릭 데미지 (pct, ×200) - from effects_resolved
    3: {"effect_name": "클릭 데미지", "format": "pct", "base_multiplier": 200.0, "has_random_bonus": True},

    # type 4: 마법 용병 데미지 (pct, ×300)
    # Confirmed: 마법의 투쟁 - 0.45 * 300 * 1.3 = 175.5 ✓
    4: {"effect_name": "마법 용병 데미지", "format": "pct", "base_multiplier": 300.0, "has_random_bonus": True},

    # type 6: 공격 속도 (pct, ×100) - from effects_resolved
    6: {"effect_name": "공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 7: 추가 데미지 (raw integer, ×2)
    # Confirmed: 탈모 - 6000*2*1.3=15600 ✓, 넝쿨채찍 - 5000*2*1.3=13000 ✓
    7: {"effect_name": "추가 데미지", "format": "raw_int", "base_multiplier": 2.0, "has_random_bonus": True},

    # type 8: 골드 획득량 (pct, ×100) - from effects_resolved
    8: {"effect_name": "골드 획득량", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 9: 공격 속도 (pct, ×100)
    # Confirmed: 탈모 - 0.25*100*1.3=32.5 ✓
    9: {"effect_name": "공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 10: 모든 용병 공격 속도 (pct, ×100) - penalty, no bonus
    10: {"effect_name": "모든 용병 공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": False},

    # type 11: 물리 용병 공격 속도 (pct, ×100)
    # Confirmed: 전사들의 열정 - 0.06*100*1.3=7.8 ✓
    11: {"effect_name": "물리 용병 공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 12: 클릭 저항력 감소 (pct, ×100) - from effects_resolved
    12: {"effect_name": "클릭 저항력 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 14: 클릭 크리티컬 확률 (pct, ×100) - from effects_resolved
    14: {"effect_name": "클릭 크리티컬 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 15: 클릭 데미지 (pct, ×200)
    15: {"effect_name": "클릭 데미지", "format": "pct", "base_multiplier": 200.0, "has_random_bonus": True},

    # type 16: 모든 용병 클릭 데미지 (pct, ×200)
    16: {"effect_name": "모든 용병 클릭 데미지", "format": "pct", "base_multiplier": 200.0, "has_random_bonus": True},

    # type 17: 모든 용병 베이스 데미지 (pct, ×300)
    17: {"effect_name": "모든 용병 베이스 데미지", "format": "pct", "base_multiplier": 300.0, "has_random_bonus": True},

    # type 18: 최대 레벨 (raw)
    18: {"effect_name": "최대 레벨", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 19: 모든 용병 최대 레벨 (raw)
    19: {"effect_name": "모든 용병 최대 레벨", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 20: 강타 확률 (pct, ×100)
    # Confirmed: 노쓰페라투쓰 - 0.1*100*1.3=13 ✓, 불신 - 0.06*100*1.3=7.8 ✓
    20: {"effect_name": "강타 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 21: 모든 용병 강타 확률 (pct, ×100)
    21: {"effect_name": "모든 용병 강타 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 22: 물리 용병 강타 확률 (pct, ×100)
    # Confirmed: 전사들의 열정 - 0.006*100*1.3=0.78 ✓
    22: {"effect_name": "물리 용병 강타 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 23: 자동 클릭 속도 (pct, ×100) - from effects_resolved
    23: {"effect_name": "자동 클릭 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 26: 강타 배수 (raw)
    # Confirmed: 노쓰페라투쓰 - 1.5*1.3=1.95 ✓
    26: {"effect_name": "강타 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 27: 추가 클릭 확률 (pct, ×100)
    27: {"effect_name": "추가 클릭 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 28: 공격 무효화 관통 (pct, ×100)
    28: {"effect_name": "공격 무효화 관통", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 29: 마법 용병 강타 배수 (raw)
    # Confirmed: 마법의 투쟁 - 0.15*1.3=0.195 ✓
    29: {"effect_name": "마법 용병 강타 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 30: 최대 레벨 (raw) - from effects_resolved
    30: {"effect_name": "최대 레벨", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 32: 연타 확률 (pct, ×100)
    # Confirmed: 광분 - 0.08*100*1.3=10.4 ✓
    32: {"effect_name": "연타 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 38: 클릭 크리티컬 확률 (pct, ×100)
    38: {"effect_name": "클릭 크리티컬 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 39: 클릭 크리티컬 배수 (raw)
    39: {"effect_name": "클릭 크리티컬 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 40: 소울 클릭 확률 (pct, ×100)
    # Confirmed: 영혼 흡수 - 0.025*100*1.3=3.25 ✓
    40: {"effect_name": "소울 클릭 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 41: 자동 클릭 확률 (pct, ×100)
    41: {"effect_name": "자동 클릭 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 42: 자동 클릭 속도 (pct, ×100)
    42: {"effect_name": "자동 클릭 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 43: 추가 클릭 확률 (pct, ×100)
    # Confirmed: 자유인의 의지 - 0.55*100*1.3=71.5 ✓
    43: {"effect_name": "추가 클릭 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 46: 골드 획득량 (pct, ×100)
    # Confirmed: 재물신 관우의 부적 - 0.36*100*1.3=46.8 ✓
    46: {"effect_name": "골드 획득량", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 47: 회피 확률 감소 (pct, ×100)
    47: {"effect_name": "회피 확률 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 48: 아이템 획득 확률 (pct, ×100)
    48: {"effect_name": "아이템 획득 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 49: 명성 (pct, ×100)
    49: {"effect_name": "명성", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 51: 물리 저항력 감소 (pct, ×100)
    51: {"effect_name": "물리 저항력 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 52: 마법 저항력 감소 (pct, ×100)
    52: {"effect_name": "마법 저항력 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 53: 카오스 취약성 (pct, ×100)
    # Confirmed: 불신 - 0.015*100*1.3=1.95 ✓
    53: {"effect_name": "카오스 취약성", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 54: 모든 용병 최종 데미지 (pct, ×100)
    54: {"effect_name": "모든 용병 최종 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 55: 모든 용병 성장 데미지 (pct, ×100)
    55: {"effect_name": "모든 용병 성장 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 56: 공격 무효화 관통 (pct, ×100)
    56: {"effect_name": "공격 무효화 관통", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 78: 칼라무쉬 용병 베이스 데미지 (pct, ×100)
    78: {"effect_name": "[칼라무쉬] 용병 베이스 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 84: 베이스 데미지 (pct, ×300)
    84: {"effect_name": "베이스 데미지", "format": "pct", "base_multiplier": 300.0, "has_random_bonus": True},

    # type 95: 신성 데미지 (pct, ×100)
    95: {"effect_name": "신성 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 102: 소울 클릭 배수 (raw)
    102: {"effect_name": "소울 클릭 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 107: 피격 지속시간 감소 (pct, ×100)
    # Confirmed: 노쓰페라투쓰 - 0.35*100*1.3≈45.5 (user says 45.9, rounding)
    107: {"effect_name": "피격 지속시간 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 108: 모든 용병 피격 지속시간 감소 (pct, ×100)
    108: {"effect_name": "모든 용병 피격 지속시간 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 109: 뿔레정수 획득 확률 (pct, ×100)
    109: {"effect_name": "뿔레정수 획득 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 112: 회피 확률 감소 (pct, ×100)
    112: {"effect_name": "회피 확률 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 114: 순수 데미지 (pct, ×100)
    114: {"effect_name": "순수 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 122: 추가 클릭 데미지 (pct, ×100)
    # Confirmed: 자유인의 의지 - 0.15*100*1.3=19.5 ✓
    122: {"effect_name": "추가 클릭 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 124: 데미지 편차 (pct, ×100)
    124: {"effect_name": "데미지 편차", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 137: 행운 확률 (pct, ×100)
    137: {"effect_name": "행운 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 138: 모든 용병 행운 확률 (pct, ×100)
    138: {"effect_name": "모든 용병 행운 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 140: 모든 용병 행운 배수 (raw)
    140: {"effect_name": "모든 용병 행운 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 151: 보이 참전시 골드 저장량 (pct, ×100)
    151: {"effect_name": "보이 참전시 골드 저장량", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 169: 모든 용병 신성 데미지 (pct, ×100)
    169: {"effect_name": "모든 용병 신성 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 175: 공포 극복 확률 (pct, ×100)
    175: {"effect_name": "공포 극복 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 176: 피격 회피 확률 (pct, ×100)
    176: {"effect_name": "피격 회피 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 177: 모든 용병 공격 속도 (pct, ×100)
    177: {"effect_name": "모든 용병 공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 196: 모든 트리니티 용병 강타 확률 (pct, ×100)
    196: {"effect_name": "[트리니티] 용병 강타 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 197: 모든 트리니티 용병 강타 배수 (raw)
    197: {"effect_name": "[트리니티] 용병 강타 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 218: 칼라무쉬 용병 데미지 (pct, ×100)
    218: {"effect_name": "[칼라무쉬] 용병 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 219: [동물뼈 언데드] 용병수×추가데미지 (special)
    219: {"effect_name": "[동물뼈 언데드] 용병 수 × 추가 데미지", "format": "special_count", "base_multiplier": 2.0, "has_random_bonus": True},

    # type 250: 더블 어택 확률 (pct, ×100)
    250: {"effect_name": "더블 어택 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 253: 흡수 확률 감소 (pct, ×100)
    253: {"effect_name": "흡수 확률 감소", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 255: 연타 데미지 (pct, ×100)
    255: {"effect_name": "연타 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 257: 뿔레 오브 드랍 확률 (pct, ×100)
    257: {"effect_name": "뿔레 오브 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 258: 아군 피격 보호 확률 (pct, ×100)
    258: {"effect_name": "아군 피격 보호 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 295: 루비 드랍 확률 (pct, ×100)
    295: {"effect_name": "루비 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 296: 토파즈 드랍 확률 (pct, ×100)
    296: {"effect_name": "토파즈 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 297: 사파이어 드랍 확률 (pct, ×100)
    297: {"effect_name": "사파이어 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 298: 에머랄드 드랍 확률 (pct, ×100)
    298: {"effect_name": "에머랄드 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 299: 자수정 드랍 확률 (pct, ×100)
    299: {"effect_name": "자수정 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 300: 아티팩트 드랍 확률 (pct, ×100)
    300: {"effect_name": "아티팩트 드랍 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 309: 모든 용병 치명타 배수 (raw)
    309: {"effect_name": "모든 용병 치명타 배수", "format": "raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 368: 모든 용병 추가 클릭 데미지 (pct, ×100)
    368: {"effect_name": "모든 용병 추가 클릭 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 375: 자동 클릭 데미지 (pct, ×100)
    375: {"effect_name": "자동 클릭 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 421: [식물] 용병수×데미지 (special_count_pct)
    # Confirmed: 넝쿨채찍 - 0.4*100*1.3=52 ✓
    421: {"effect_name": "[식물] 용병 수 × 데미지", "format": "special_count_pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 422: [식물] 용병수×클릭 데미지 (special_count_pct)
    # Confirmed: 넝쿨채찍 - 0.4*100*1.3=52 ✓
    422: {"effect_name": "[식물] 용병 수 × 클릭 데미지", "format": "special_count_pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 431: 모든 용병 추가 클릭 확률 (pct, ×100)
    431: {"effect_name": "모든 용병 추가 클릭 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 475: [동물뼈 언데드] 용병수×베이스데미지 (special_count_pct)
    475: {"effect_name": "[동물뼈 언데드] 용병 수 × 베이스 데미지", "format": "special_count_pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 495: [퍼루나] 용병수×데미지 (special_count_pct)
    495: {"effect_name": "[퍼루나] 용병 수 × 데미지", "format": "special_count_pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 591: 회피시 데미지 증가 (pct, ×100)
    591: {"effect_name": "회피시 데미지 증가", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 635: [언데드] 용병수×강타배수 (special_count_raw)
    635: {"effect_name": "[언데드] 용병 수 × 강타 배수", "format": "special_count_raw", "base_multiplier": 1.0, "has_random_bonus": True},

    # type 1000: 추가 데미지 증폭 (pct, ×100)
    1000: {"effect_name": "추가 데미지 증폭", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1013: 모든 물리 용병 성장 데미지 (pct, ×100)
    1013: {"effect_name": "물리 용병 성장 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1014: 모든 마법 용병 성장 데미지 (pct, ×100)
    1014: {"effect_name": "마법 용병 성장 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1016: 모든 카오스 용병 성장 데미지 (pct, ×100)
    1016: {"effect_name": "카오스 용병 성장 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1022: 모든 카오스 용병 강타 배수 증폭 (pct, ×100)
    1022: {"effect_name": "카오스 용병 강타 배수 증폭", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1171: 즉시 공격 확률 (pct, ×100)
    1171: {"effect_name": "즉시 공격 확률", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1172: 즉시 공격 데미지 (pct, ×100)
    1172: {"effect_name": "즉시 공격 데미지", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},

    # type 1173: 즉시 공격 속도 (pct, ×100)
    1173: {"effect_name": "즉시 공격 속도", "format": "pct", "base_multiplier": 100.0, "has_random_bonus": True},
}


def format_value(value, fmt, base_multiplier, has_random_bonus):
    """Calculate display value and format it as a string (base values, no 1.3x bonus)."""

    if fmt == "pct":
        # Percentage: value * base_multiplier (base value, 1x)
        display = value * base_multiplier
        # Format: remove trailing zeros, add %
        return format_pct(display)

    elif fmt == "raw":
        # Raw multiplier: base value (1x)
        display = value * base_multiplier
        return format_raw(display)

    elif fmt == "raw_int":
        # Raw integer (like 추가 데미지): value * base_multiplier (base value, 1x)
        display = value * base_multiplier
        return format_int(display)

    elif fmt in ("special_count_pct",):
        # [종족] 용병수 × X%: value * base_multiplier (base value, 1x)
        display = value * base_multiplier
        return format_pct(display)

    elif fmt in ("special_count_raw",):
        # [종족] 용병수 × raw: base value (1x)
        display = value * base_multiplier
        return format_raw(display)

    else:
        # Fallback
        display = value * (base_multiplier or 100.0)
        return format_pct(display)


def format_pct(val):
    """Format a percentage value nicely."""
    # Round to avoid floating point artifacts
    val = round(val, 4)
    if val == int(val):
        return f"{int(val)}%"
    elif round(val, 1) == val:
        return f"{val:.1f}%"
    elif round(val, 2) == val:
        return f"{val:.2f}%"
    else:
        # Up to 3 decimal places, strip trailing zeros
        s = f"{val:.3f}".rstrip('0').rstrip('.')
        return f"{s}%"


def format_raw(val):
    """Format a raw (non-percentage) value."""
    val = round(val, 4)
    if val == int(val):
        return str(int(val))
    elif round(val, 1) == val:
        return f"{val:.1f}"
    elif round(val, 2) == val:
        return f"{val:.2f}"
    else:
        return f"{val:.3f}".rstrip('0').rstrip('.')


def format_int(val):
    """Format an integer value with comma separators."""
    val = round(val)
    return f"{val:,}"


def compute_effect(type_code, raw_value):
    """Compute the display effect string for a given type code and raw APK value."""
    if type_code == 0 and raw_value == 0.0:
        return None  # Empty slot

    mapping = TYPE_MAPPING.get(type_code)
    if mapping is None:
        # Try to format as generic percentage
        display = raw_value * 100
        return f"알 수 없는 효과 (type:{type_code}) {format_pct(display)}"

    effect_name = mapping["effect_name"]
    fmt = mapping["format"]
    base_multiplier = mapping["base_multiplier"]
    has_random_bonus = mapping["has_random_bonus"]

    formatted_value = format_value(raw_value, fmt, base_multiplier, has_random_bonus)

    # For special count types, format differently
    if fmt == "special_count_pct":
        return f"{effect_name} {formatted_value}"
    elif fmt == "special_count_raw":
        return f"{effect_name} {formatted_value}"
    elif fmt == "raw_int":
        return f"{effect_name} {formatted_value}"
    else:
        return f"{effect_name} {formatted_value}"


# ============================================================
# STEP 2: Load skills and apply mapping
# ============================================================

print("=" * 60)
print("STEP 1: Loading data...")
print("=" * 60)

with open('/Users/shin542/Desktop/Code/bbule/random_merc_skills.json', 'r', encoding='utf-8') as f:
    skills = json.load(f)

print(f"  Loaded {len(skills)} skills from random_merc_skills.json")
print(f"  Type mapping has {len(TYPE_MAPPING)} entries")

# ============================================================
# STEP 3: Generate output
# ============================================================

print()
print("=" * 60)
print("STEP 2: Applying mapping to all skills...")
print("=" * 60)

output_skills = []
all_mapped = 0
some_unmapped = 0
unmapped_skills = []
unmapped_type_counts = {}

for skill in skills:
    types = skill["types"]
    effects = skill["effects"]
    grade = skill.get("randomValue", 0)

    effect_strings = []
    has_unmapped = False

    for i in range(3):
        tc = types[i]
        ev = effects[i]

        if tc == 0 and ev == 0.0:
            continue  # Empty slot

        effect_str = compute_effect(tc, ev)
        if effect_str is not None:
            effect_strings.append(effect_str)
            if "알 수 없는 효과" in effect_str:
                has_unmapped = True
                unmapped_type_counts[tc] = unmapped_type_counts.get(tc, 0) + 1

    if has_unmapped:
        some_unmapped += 1
        unmapped_skills.append(skill["name"])
    else:
        all_mapped += 1

    entry = {
        "index": skill["index"],
        "name": skill["name"],
        "desc": skill["description"],
        "icon": skill["icon"],
        "grade": grade,
        "effects": effect_strings
    }
    output_skills.append(entry)

# Sort by grade DESC, then name ASC
output_skills.sort(key=lambda x: (-x["grade"], x["name"]))

print(f"  Processed {len(output_skills)} skills")
print(f"  All effects mapped: {all_mapped}")
print(f"  Some unmapped effects: {some_unmapped}")

# ============================================================
# STEP 4: Save output JSON
# ============================================================

print()
print("=" * 60)
print("STEP 3: Saving output files...")
print("=" * 60)

output_path = '/Users/shin542/Desktop/Code/bbule/web/data_random_merc.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_skills, f, ensure_ascii=False, indent=2)
print(f"  Saved {output_path}")

# ============================================================
# STEP 5: Update index.html RMSKILL_DATA
# ============================================================

print()
print("=" * 60)
print("STEP 4: Updating index.html RMSKILL_DATA...")
print("=" * 60)

html_path = '/Users/shin542/Desktop/Code/bbule/web/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html_lines = f.readlines()

# Find the line with RMSKILL_DATA
rmskill_line_idx = None
for i, line in enumerate(html_lines):
    if line.strip().startswith('const RMSKILL_DATA='):
        rmskill_line_idx = i
        break

if rmskill_line_idx is None:
    print("  ERROR: Could not find 'const RMSKILL_DATA=' in index.html")
    sys.exit(1)

# Build minified JSON (no source field)
minified = json.dumps(output_skills, ensure_ascii=False, separators=(',', ':'))
new_line = f"const RMSKILL_DATA={minified};\n"

html_lines[rmskill_line_idx] = new_line

with open(html_path, 'w', encoding='utf-8') as f:
    f.writelines(html_lines)

print(f"  Updated line {rmskill_line_idx + 1} in index.html")
print(f"  RMSKILL_DATA size: {len(new_line):,} characters")

# ============================================================
# STEP 6: Save updated mapping
# ============================================================

print()
print("=" * 60)
print("STEP 5: Saving updated type mapping...")
print("=" * 60)

# Convert to the original format
mapping_output = {
    "meta": {
        "description": "Random mercenary skill type code -> effect name mapping (CORRECTED)",
        "source": "User-confirmed in-game values cross-referenced with APK data",
        "total_type_codes": len(TYPE_MAPPING),
        "scaling_formula": {
            "pct": "display_pct = apk_val * base_multiplier * (1.3 if has_random_bonus)",
            "raw": "display_val = apk_val * base_multiplier * (1.3 if has_random_bonus)",
            "raw_int": "display_int = round(apk_val * base_multiplier * (1.3 if has_random_bonus))",
            "special_count_pct": "[종족] 용병 수 × (apk_val * base_multiplier * 1.3)%",
            "special_count_raw": "[종족] 용병 수 × (apk_val * base_multiplier * 1.3)",
            "note": "30% random mercenary slot bonus (×1.3) applied to all positive effects"
        }
    },
    "type_mapping": {}
}

for tc in sorted(TYPE_MAPPING.keys()):
    m = TYPE_MAPPING[tc]
    mapping_output["type_mapping"][str(tc)] = {
        "effect_name": m["effect_name"],
        "format": m["format"],
        "base_multiplier": m["base_multiplier"],
        "has_random_bonus": m["has_random_bonus"]
    }

mapping_path = '/Users/shin542/Desktop/Code/bbule/random_merc_type_mapping.json'
with open(mapping_path, 'w', encoding='utf-8') as f:
    json.dump(mapping_output, f, ensure_ascii=False, indent=2)
print(f"  Saved {mapping_path}")

# ============================================================
# STEP 7: Print statistics
# ============================================================

print()
print("=" * 60)
print("STATISTICS")
print("=" * 60)

# Collect all type codes actually used in the data
all_types_in_data = set()
for skill in skills:
    for t in skill["types"]:
        if t != 0:
            all_types_in_data.add(t)

mapped_types = set(TYPE_MAPPING.keys())
unmapped_types_in_data = all_types_in_data - mapped_types

print(f"  Total skills: {len(skills)}")
print(f"  Skills with all effects mapped: {all_mapped}")
print(f"  Skills with some unmapped effects: {some_unmapped}")
if unmapped_skills:
    print(f"    Unmapped skills: {unmapped_skills}")
print()
print(f"  Unique type codes in data: {len(all_types_in_data)}")
print(f"  Mapped type codes: {len(mapped_types & all_types_in_data)}")
print(f"  Unmapped type codes: {len(unmapped_types_in_data)}")
if unmapped_types_in_data:
    print(f"    Unmapped codes with frequency:")
    for tc in sorted(unmapped_types_in_data):
        freq = unmapped_type_counts.get(tc, 0)
        print(f"      type {tc}: {freq} occurrences")

print()
print("DONE!")
