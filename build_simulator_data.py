"""
build_simulator_data.py
=======================
output/creatures.json + output/*_skills.json → web/data_simulator.json + inline SIM_DATA

용병 시뮬레이터용 JSON 생성 스크립트.
- 각 용병의 기본/성장 스탯, 스킬 효과, 패시브, 타입, 전용장비 정보를 포함.
- 스킬은 mercenary_skills/random_merc_skills/sub_slot_troops의 effects_resolved를 참조.
- 슬롯5 스킬이 패시브 (모든 용병이 5슬롯 보유).
- 출력: grade 우선순위 정렬 (P→O→H→X→G→S→A→B→C→D→E), compact JSON.
"""

import json
import os
import re

GRADE_ORDER = ['P', 'O', 'H', 'X', 'G', 'S', 'A', 'B', 'C', 'D', 'E']

INPUT_CREATURES = os.path.join(os.path.dirname(__file__), 'output', 'creatures.json')
INPUT_SKILL_FILES = [
    os.path.join(os.path.dirname(__file__), 'output', 'mercenary_skills.json'),
    os.path.join(os.path.dirname(__file__), 'output', 'random_merc_skills.json'),
    os.path.join(os.path.dirname(__file__), 'output', 'sub_slot_troops.json'),
]
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), 'web', 'data_simulator.json')
INDEX_HTML = os.path.join(os.path.dirname(__file__), 'web', 'index.html')


def load_json(path: str) -> object:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def build_skill_map(skills: list) -> dict:
    """스킬 리스트를 index 기준 딕셔너리로 변환."""
    result = {}
    for s in skills:
        result.setdefault(s['index'], s)
    return result


def simplify_effects(effects_resolved: list) -> list:
    """effects_resolved → simulator용 간소화 포맷."""
    result = []
    for e in effects_resolved:
        result.append({
            'type_code': e['type_code'],
            'type_name': e['type_name'],
            'value': e['value'],
            'display': e['value_display'],
        })
    return result


def build_creature_entry(creature: dict, skill_map: dict) -> dict:
    """creatures.json 항목 하나를 simulator JSON 항목으로 변환."""
    ss = creature.get('sheet_stats', {})
    dgr = creature.get('damageG_raw', {})

    # 스킬 처리 (슬롯 5 = 패시브)
    skills_out = []
    passive_name = ''
    passive_effects = []

    raw_skills = creature.get('skills', [])
    # 슬롯 번호 오름차순 정렬
    raw_skills_sorted = sorted(raw_skills, key=lambda s: s['slot'])

    for skill in raw_skills_sorted:
        slot = skill['slot']
        sid = skill['id']
        skill_data = skill_map.get(sid)

        if skill_data:
            effects = simplify_effects(skill_data.get('effects_resolved', []))
        else:
            effects = []

        skill_entry = {
            'slot': slot,
            'id': sid,
            'name': skill['name'],
            'effects': effects,
        }

        if slot == 5:
            # 패시브
            passive_name = skill['name']
            passive_effects = effects
        else:
            skills_out.append(skill_entry)

    # 전용장비 (exclusiveIDs에서 -1 제거)
    exclusive_equip = [eid for eid in creature.get('exclusiveIDs', []) if eid != -1]

    # 타입
    types_raw = creature.get('types', {})
    types_out = {
        'race': types_raw.get('race', ''),
        'location': types_raw.get('location', ''),
        'gender': types_raw.get('gender', ''),
        'house': types_raw.get('house', ''),
        'religion': types_raw.get('religion', ''),
        'individuality': types_raw.get('individuality', ''),
    }

    grade = creature.get('grade', '')
    name = creature.get('name', '')

    return {
        'id': creature.get('hero_id', 0),
        'name': name,
        'grade': grade,
        'subtitle': creature.get('subtitle', ''),
        'damageType': creature.get('attackType_kr', '물리'),
        'baseDamage': ss.get('base_damage', 0.0),
        'growthDamage': ss.get('growth_damage', 0.0),
        'baseClickDamage': ss.get('base_click_damage', 0.0),
        'growthClickDamage': ss.get('growth_click_damage', 0.0),
        'attackCooldown': creature.get('attackCooldown', 0.0),
        'canG': creature.get('canG', False),
        'canAwaken': creature.get('canAwaken', False),
        'gStats': {
            'damageG': dgr.get('damageG', 0),
            'damageUpG': dgr.get('damageUpG', 0),
            'damageClickG': dgr.get('damageClickG', 0),
            'damageClickUpG': dgr.get('damageClickUpG', 0),
            'attackCooldownG': creature.get('attackCooldownG', 0.0),
        },
        'skills': skills_out,
        'passive': passive_name,
        'passiveEffects': passive_effects,
        'types': types_out,
        'exclusiveEquip': exclusive_equip,
        'portrait': f'{grade}_{name}.png',
    }


def replace_inline_sim_data(entries: list) -> None:
    """web/index.html의 SIM_DATA 상수를 최신 simulator 데이터로 교체."""
    if not os.path.exists(INDEX_HTML):
        return
    with open(INDEX_HTML, encoding='utf-8') as f:
        html = f.read()
    compact = json.dumps(entries, ensure_ascii=False, separators=(',', ':'))
    new_html, count = re.subn(
        r'const SIM_DATA\s*=\s*(\[.*?\]);',
        lambda _match: f'const SIM_DATA = {compact};',
        html,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise SystemExit('SIM_DATA block not found in web/index.html')
    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'  Updated SIM_DATA in {INDEX_HTML}')


def main():
    print(f'Reading {INPUT_CREATURES} ...')
    creatures = load_json(INPUT_CREATURES)
    print(f'  {len(creatures)} creatures loaded')

    skills = []
    for path in INPUT_SKILL_FILES:
        print(f'Reading {path} ...')
        part = load_json(path)
        skills.extend(part)
        print(f'  {len(part)} skills loaded')

    skill_map = build_skill_map(skills)

    # 변환
    entries = []
    missing_skill_ids = set()
    for creature in creatures:
        for skill in creature.get('skills', []):
            sid = skill['id']
            if sid not in skill_map:
                missing_skill_ids.add(sid)
        entries.append(build_creature_entry(creature, skill_map))

    # grade 우선순위 정렬
    grade_rank = {g: i for i, g in enumerate(GRADE_ORDER)}
    entries.sort(key=lambda e: (grade_rank.get(e['grade'], 99), e['name']))

    # 출력
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    output_str = json.dumps(entries, ensure_ascii=False, separators=(',', ':'))
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        f.write(output_str)
    replace_inline_sim_data(entries)

    size_kb = os.path.getsize(OUTPUT_JSON) / 1024
    print(f'\n완료: {OUTPUT_JSON}')
    print(f'  항목 수: {len(entries)}')
    print(f'  파일 크기: {size_kb:.1f} KB')
    if missing_skill_ids:
        print(f'  경고: skill_map에 없는 스킬 ID {len(missing_skill_ids)}개 (빈 effects로 처리)')


if __name__ == '__main__':
    main()
