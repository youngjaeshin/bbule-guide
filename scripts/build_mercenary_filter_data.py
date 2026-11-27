#!/usr/bin/env python3
"""Build a search index from the accepted mercenary effects and reviewed conditions."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'web/data_mercenaries.json'
DESTINATION = ROOT / 'web/data_mercenary_filters.json'
REVIEW = ROOT / 'mercenary_composition_review.json'
FAMILIES = {
    'pure_physical': {'label': '퓨어 물리', 'description': '마법·카오스 부재, 카오스 부재, 마법 부재, 물리 데미지 최대 등 퓨어 물리 편성에서 성립하는 조건'},
    'pure_mixed': {'label': '퓨어 혼합', 'description': '카오스 데미지 없음 또는 혼합 용병만 공격하는 조건. 카오스 부재 조건은 물리 편성에서도 성립할 수 있습니다.'},
    'pure_chaos': {'label': '퓨어 카오스', 'description': '물리·마법 데미지 부재 조건. X 젤다의 개별 부재 조건과 추가 참전 조건도 포함합니다.'},
    'trinity': {'label': '트리니티 전용', 'description': '물리·마법·카오스 데미지가 모두 있는 조건'},
}
STAT_LABELS = [
    ('약화 효과 감소', '약화 효과 감소', ['약화 감소', '약화']),
    ('둔화 효과 감소', '둔화 효과 감소', ['둔화 감소', '둔화']),
    ('봉인 무효화 확률', '봉인 무효화 확률 증가', ['봉무', '봉인 무효화']),
    ('치명타 확률 증폭', '치명타 확률 증폭', []),
    ('치명타 확률', '치명타 확률 증가', ['치확']),
    ('치명타 딜레이 감소', '치명타 딜레이 감소', []),
    ('치명타 배수 증폭', '치명타 배수 증폭', []),
    ('치명타 배수', '치명타 배수 증가', []),
    ('클릭 크리티컬 확률', '클릭 크리티컬 확률 증가', []),
    ('클릭 크리티컬 배수', '클릭 크리티컬 배수 증가', []),
    ('피해 면제 효과 감소', '피해 면제 효과 감소', ['피면 감소', '피면']),
    ('무력화 효과 감소', '무력화 효과 감소', ['무력화 감소']),
    ('공격 무효화 관통', '공격 무효화 관통', ['무관']),
    ('방어막 효과 감소', '방어막 효과 감소', []),
    ('반사 확률 감소', '반사 확률 감소', ['반사 감소']),
    ('흡수 확률 감소', '흡수 확률 감소', ['흡수 감소']),
    ('부활 확률 감소', '부활 확률 감소', ['부활 감소']),
    ('회피 확률 감소', '적 회피 확률 감소', ['회피 감소']),
    ('피격 지속시간 감소', '피격 지속시간 감소', ['피지감']),
    ('공포 극복 확률', '공포 극복 확률 증가', ['공포 극복']),
    ('봉인될 확률 감소', '봉인될 확률 감소', []),
    ('피격 회피 확률', '피격 회피 확률 증가', []),
    ('강타 확률', '강타 확률 증가', []),
    ('강타 배수 증폭', '강타 배수 증폭', []),
    ('강타 배수', '강타 배수 증가', []),
    ('더블 어택 확률 증폭', '더블 어택 확률 증폭', []),
    ('더블 어택 확률', '더블 어택 확률 증가', []),
    ('연타 확률', '연타 확률 증가', []),
    ('연타 데미지 증폭', '연타 데미지 증폭', []),
    ('연타 데미지', '연타 데미지 증가', []),
    ('연타 간격 감소', '연타 간격 감소', []),
    ('행운 확률', '행운 확률 증가', []),
    ('행운 배수 증폭', '행운 배수 증폭', []),
    ('행운 배수', '행운 배수 증가', []),
    ('선제 공격 확률', '선제 공격 확률 증가', []),
    ('즉시 공격 속도', '즉시 공격 속도 증가', []),
    ('즉시 공격 데미지 증폭', '즉시 공격 데미지 증폭', []),
    ('즉시 공격 데미지', '즉시 공격 데미지 증가', []),
    ('즉시 공격 확률', '즉시 공격 확률 증가', []),
    ('공격 속도', '공격 속도 증가', ['공속']),
    ('저항력 무시', '저항력 무시 증가', []),
    ('아티팩트 효과 증폭', '아티팩트 효과 증폭', []),
    ('쥬얼 효과 증폭', '쥬얼 효과 증폭', ['주얼 효과 증폭']),
    ('소울 클릭 확률', '소울 클릭 확률 증가', []),
    ('소울 클릭 배수 증폭', '소울 클릭 배수 증폭', []),
    ('소울 클릭 배수', '소울 클릭 배수 증가', []),
    ('추가 클릭 데미지 증폭', '추가 클릭 데미지 증폭', []),
    ('추가 클릭 데미지', '추가 클릭 데미지 증가', []),
    ('추가 클릭 확률', '추가 클릭 확률 증가', []),
    ('최종 데미지', '최종 데미지 증가', []),
    ('성장 데미지', '성장 데미지 증가', []),
    ('베이스 데미지', '베이스 데미지 증가', []),
    ('추가 데미지', '추가 데미지 증가', []),
    ('클릭 데미지', '클릭 데미지 증가', []),
    ('데미지', '데미지 증가', []),
]
CONDITION_PREFIX = re.compile(
    r'^(.+?(?:때|참전시|장착시|착용시|배치시|보유시|고용시|구매시|공격시|피격시|회피시|발동 시))'
)


def compact(text):
    return re.sub(r'[\s,，·ㆍ]', '', text)


def composition(effect, mercenary, slot, effect_index, reviewed_effects):
    reviewed = reviewed_effects.get((mercenary['id'], slot, effect_index))
    if reviewed is None:
        return '', '', []
    assert effect['description'] == reviewed['expected_description'], (mercenary['id'], slot, effect_index)
    assert effect.get('type_code') == reviewed['type_code'], (mercenary['id'], slot, effect_index)
    return reviewed['rule_id'], reviewed['condition'], reviewed['profiles']


def effect_target(text, names):
    if re.search(r'모든\s*용병의', text):
        return 'all'
    if re.search(r'모든\s*.+?\s*용병의|(?:종족|가문|지역|개성|종교|성별).+?용병의', text):
        return 'group'
    if text.startswith('적'):
        return 'enemy'
    if any(text.startswith(name + '의') or text.startswith(name + '와') for name in names):
        return 'named'
    if re.search(r'획득|드랍|드롭|골드|명성|슬롯|모집|지급', text):
        return 'account'
    return 'self'


def clean_effect_name(text, names):
    text = re.sub(r'^영구적으로\s*', '', text).strip()
    text = CONDITION_PREFIX.sub('', text).strip(' )')
    text = re.sub(r'^(?:종족|가문|지역|개성|종교|성별).+?용병의\s*', '', text)
    text = re.sub(r'^모든\s*(?:.*?)용병의\s*', '', text)
    text = re.sub(r'^적(?:들의)?\s*', '', text)
    named_prefix = re.match(r'^(.+?)의\s+', text)
    if named_prefix and any(named_prefix[1].startswith(name) for name in names):
        text = text[named_prefix.end():]
    return text.strip()


def effect_kind(effect, names):
    cleaned = clean_effect_name(effect.get('type_name', ''), names)
    normalized = compact(cleaned)
    aliases = {'적약화감소': '약화효과감소', '약화감소': '약화효과감소',
               '적둔화감소': '둔화효과감소', '둔화감소': '둔화효과감소'}
    normalized = aliases.get(normalized, normalized)
    if normalized == '약화둔화효과감소':
        return [('stat:약화효과감소', '약화 효과 감소', ['약화', '약화 감소']),
                ('stat:둔화효과감소', '둔화 효과 감소', ['둔화', '둔화 감소'])]
    for stat, label, search_aliases in sorted(STAT_LABELS, key=lambda row: -len(compact(row[0]))):
        token = compact(stat)
        if normalized == token or normalized.startswith(token + '+'):
            return [('stat:' + token, label, search_aliases + [stat])]
    return [('type:' + effect['type_name'], effect['type_name'], [])]


def main():
    source_bytes = SOURCE.read_bytes()
    mercenaries = json.loads(source_bytes)
    review = json.loads(REVIEW.read_text(encoding='utf-8'))
    reviewed_effects = {(row['id'], effect['slot'], effect['index']): effect
                        for row in review['mercenaries'] for effect in row['effects']}
    names = sorted({row['name'] for row in mercenaries}, key=len, reverse=True)
    catalogue = {}
    index = {}
    family_members = {family: set() for family in FAMILIES}
    counts = Counter()
    for mercenary in mercenaries:
        entries = []
        for skill in mercenary['skills']:
            for effect_index, effect in enumerate(skill.get('effectsResolved', [])):
                rule_id, composition_text, families = composition(
                    effect, mercenary, skill['slot'], effect_index, reviewed_effects)
                raw_name = effect['type_name']
                condition_match = CONDITION_PREFIX.match(effect['description'])
                condition = (composition_text or effect.get('condition')
                             or (condition_match[1] if condition_match else ''))
                target_text = re.sub(r'^영구적으로\s*', '', raw_name)
                target_text = CONDITION_PREFIX.sub('', target_text).strip(' )')
                value = effect.get('value')
                beneficial = value is None or value >= 0 or effect.get('operation') == 'disable'
                kinds = effect_kind(effect, names)
                for kind, label, aliases in kinds:
                    catalogue.setdefault(kind, {'id': kind, 'label': label, 'aliases': aliases, 'mercenaries': set()})
                    if beneficial:
                        catalogue[kind]['mercenaries'].add(mercenary['id'])
                entries.append({'slot': skill['slot'], 'index': effect_index, 'kinds': [kind[0] for kind in kinds],
                                'target': effect_target(target_text, names), 'condition': condition,
                                'families': families, 'rule': rule_id, 'beneficial': beneficial})
                counts['effects'] += 1
                for family in families:
                    family_members[family].add(mercenary['id'])
                    counts[family] += 1
        index[str(mercenary['id'])] = entries
    for family, members in family_members.items():
        FAMILIES[family]['mercenaries'] = len(members)
        FAMILIES[family]['effects'] = counts[family]
    for item in catalogue.values():
        item['mercenaries'] = len(item['mercenaries'])
    result = {'schema_version': 2, 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
              'mercenary_count': len(mercenaries), 'effect_count': counts['effects'],
              'reviewed_mercenaries': review['reviewed_mercenaries'],
              'reviewed_skills': review['reviewed_skills'],
              'families': FAMILIES,
              'catalogue': sorted(catalogue.values(), key=lambda row: row['label']),
              'mercenaries': index}
    DESTINATION.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(json.dumps({'mercenaries': len(index), 'effects': counts['effects'],
                      'effect_kinds': len(catalogue), 'families': FAMILIES}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
