#!/usr/bin/env python3
"""Check the published capture refresh without requiring private screenshots."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def main():
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    decoder = json.JSONDecoder()

    def inline(name):
        match = re.search(r'const\s+' + name + r'\s*=\s*', html)
        assert match, name
        return decoder.raw_decode(html[match.end():])[0]

    datasets = {'MERC_DATA': 'web/data_mercenaries.json', 'ART_DATA': 'web/data_artifacts.json',
                'EQUIP_DATA': 'web/data_equipment.json', 'RMSKILL_DATA': 'web/data_random_merc.json',
                'SIM_DATA': 'web/data_simulator.json', 'SUBSLOT_DATA': 'web/data_subslot.json',
                'GL_DATA': 'web/data_glossary.json', 'SI_DATA': 'web/data_scarecrow_invader.json'}
    for name, relative in datasets.items():
        assert inline(name) == read(relative), name + ' source/inline mismatch'
    mercs, artifacts, equipment, skills = [inline(name) for name in ['MERC_DATA', 'ART_DATA', 'EQUIP_DATA', 'RMSKILL_DATA']]
    assert len(mercs) == 556 and sum(len(m['skills']) for m in mercs) == 2780
    assert len(artifacts) == 561 and len(equipment) == 544 and len(skills) == 267
    assert read('artifacts.json') == read('output/artifacts.json')
    assert len(inline('MERC_INFO')) == 35
    assert Counter(row['grade'] for row in inline('MERC_INFO')) == {'평범함': 13, '훌륭함': 12, '영웅': 10}
    assert next(row for row in inline('MERC_INFO') if row['name'] == '실러캔스')['grade'] == '훌륭함'
    images = set()

    def image(relative):
        path = ROOT / 'web' / relative
        assert path.resolve().is_relative_to((ROOT / 'web/images').resolve()), relative
        assert path.is_file(), relative
        assert path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', relative
        images.add(relative)

    for row in mercs:
        image('images/mercenary/' + row['portrait'])
    for row in artifacts:
        assert row['effects_resolved']
        image('images/artifact/' + row['portrait'])
        if row.get('icon') is not None and row['icon'] >= 0:
            image('images/artifact/' + str(row['icon']) + '.png')
    for row in equipment:
        image(row['image'])
        assert 'effect_0_value' in row and 'effect_20_value' in row
        if not row.get('gUpgradeVerified'):
            assert not row.get('effect_0_g') and not row.get('effect_20_g')
            assert not row.get('is_upgradeable')
    for row in skills:
        image('images/random_skill/' + row['portrait'])
    for row in inline('MERC_INFO'):
        image(row['portrait'])
    sources = Counter(e['effect_20_source'] for e in equipment)
    assert sources == {'screen': 186, 'calculated_from_screen_0': 349, 'legacy_non_enhanceable_flag': 9}
    spear = next(e for e in equipment if e['name'] == '낡은 단창')
    assert spear['effect_0_value'] == 36 and spear['effect_20_value'] == 216
    by_name = {a['name']: a for a in artifacts}
    assert by_name['아너드 랜스']['effects_resolved'][1]['value_display'] == '4.2'
    assert [e['value_display'] for e in by_name['세라핌 숄더 패드']['effects_resolved']][-2:] == ['4.8%', '6%']
    assert [e['value_display'] for e in by_name['볼보레타 실크 클록']['effects_resolved']] == ['7%', '6%', '1%', '3.3%', '9%']
    assert [e['value_display'] for e in by_name['슬레이어 크라운']['effects_resolved']] == ['9%', '0.6%', '4%', '6%']
    for name in ['볼보레타 실크 클록', '슬레이어 크라운', '아낙수나문 머미 캣', '템페스트 건틀릿']:
        assert by_name[name]['captureEvidence']['source_type'] == 'community_screenshot'
    invaders = inline('SI_DATA')['invaders']
    assert len(invaders['kahinaRewards']['buffs']) == 30
    assert len(invaders['kahinaRewards']['effects']) == 15
    assert '<col style="width:56px"><col span="7">' in html and '#si-inv-table{table-layout:fixed;' in html
    awakening = next(s for s in inline('GL_DATA')['game_systems'] if s['name'] == '각성')
    assert [(r['color'], r['min']) for r in awakening['awakening_colors']][-3:] == [('입자', 25000), ('어비', 45000), ('최종', 75000)]
    result = {'status': 'PASS', 'mercenaries': 556, 'mercenary_skills': 2780, 'artifacts': 561,
              'equipment': 544, 'random_skills': 267, 'commander_portraits': 35,
              'referenced_images': len(images), 'kahina_buffs': 30, 'kahina_effects': 15,
              'awakening_thresholds': [25000, 45000, 75000], 'source_inline_sync': True}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
