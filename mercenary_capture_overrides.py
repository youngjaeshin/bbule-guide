"""Explicitly reviewed live-capture corrections, scoped to a hero and skill slot.

Values are the base *display* coefficients (after APK decoding, before the
in-game skill-effect boost). They must not pass through APK multipliers again.
Permanent collection bonuses and the fifth combat skill are separate scopes.
"""
import copy
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def registry():
    path = ROOT / 'mercenary_capture_overrides.json'
    if not path.exists():
        return {'mercenaries': {}}
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def portrait_registry():
    name=registry().get('portrait_manifest')
    if not name:
        return {}
    path=ROOT/name
    if not path.is_file():
        raise FileNotFoundError(f'Captured portrait manifest is required: {path}')
    return {row['key']: row['portrait'] for row in json.loads(path.read_text(encoding='utf-8'))}


def verified_entry(hero_id):
    return registry().get('mercenaries', {}).get(str(hero_id), {})


def verified_skill(hero_id, slot):
    entry = verified_entry(hero_id)
    skill = entry.get('skills', {}).get(str(slot))
    if not skill:
        return None
    resolved = copy.deepcopy(skill['effects'])
    return {'name': skill['name'], 'desc': skill.get('description', ''),
            'effects': [e['description'] for e in resolved],
            'effects_resolved': resolved, 'source': 'reviewed_live_codex_capture',
            'capture_evidence': skill.get('evidence', entry['evidence']), 'verified_capture': True}


def hire_effect_text(bonus):
    description=bonus['description']
    if '영구적으로' in description:return description
    condition=bonus.get('condition')
    if condition and description.startswith(condition):
        return condition+' 영구적으로 '+description[len(condition):].lstrip()
    return '영구적으로 '+description


def with_hire_passives(source, hero_id, slot):
    """Keep permanent effects in their original skill as well as the index.

The two views reference the same effect; this is deliberate presentation, not
two contributions to combat calculations.
"""
    bonuses = [e for e in verified_entry(hero_id).get('permanent_effects', [])
               if e.get('source_slot') == slot]
    if not bonuses:
        return source
    result = copy.deepcopy(source)
    result['capture_passives_only'] = not bool(source.get('effects'))
    result.setdefault('effects', [])
    result.setdefault('effects_resolved', [])
    for bonus in bonuses:
        resolved = copy.deepcopy(bonus)
        resolved.setdefault('evidence', verified_entry(hero_id).get('evidence'))
        description = hire_effect_text(resolved)
        resolved['description'] = description
        if description not in result['effects']:
            result['effects'].append(description)
            result['effects_resolved'].append(resolved)
    return result


def portrait_for(grade, name, fallback=''):
    return portrait_registry().get(f'{grade}/{name}', fallback)


def apply_mercenary_metadata(entry):
    verified = verified_entry(entry['id'])
    entry['portrait'] = portrait_for(entry['grade'], entry['name'], entry.get('portrait', ''))
    if 'permanent_effects' in verified:
        effects = copy.deepcopy(verified['permanent_effects'])
        for effect in effects:
            effect.setdefault('evidence', copy.deepcopy(verified['evidence']))
        entry['permanentEffects'] = effects
        entry['passives'] = effects
        entry['passive'] = ' / '.join(e['description'] for e in effects) or None
    if verified:
        entry['captureEvidence'] = copy.deepcopy(verified['evidence'])
    if verified.get('base_capture_evidence'):
        entry['baseCaptureEvidence'] = copy.deepcopy(verified['base_capture_evidence'])
    return entry


def new_mercenaries():
    """Guide-local negative IDs never claim to be APK hero or skill IDs."""
    result = copy.deepcopy(registry().get('new_mercenaries', []))
    for entry in result:
        entry['portrait'] = portrait_for(entry['grade'], entry['name'])
        for number, bonus in enumerate(entry.get('permanentEffects', []), 1):
            bonus.setdefault('effect_key', f"capture:{entry['grade']}/{entry['name']}:{bonus.get('source_slot',1)}:passive:{number}")
            bonus.setdefault('mapping_status', 'verified_existing_code' if bonus.get('type_code') is not None else 'game_code_pending')
        entry['passives'] = copy.deepcopy(entry.get('permanentEffects', []))
        for skill in entry['skills']:
            for effect in skill['effectsResolved']:
                effect.setdefault('scope', 'skill')
                effect.setdefault('source_slot', skill['slot'])
        for bonus in entry.get('permanentEffects', []):
            slot = bonus.get('source_slot', 1)
            skill = next(s for s in entry['skills'] if s['slot']==slot)
            item = copy.deepcopy(bonus)
            item['description'] = hire_effect_text(item)
            skill['effectsResolved'].append(item)
            skill['효과'] = ' / '.join(e['description'] for e in skill['effectsResolved'])
            skill['표시'] = skill['이름'] + ' / ' + skill['효과']
    return result


def new_simulator_entries():
    result = []
    for entry in new_mercenaries():
        skills = []
        passive_effects = []
        passive_name = ''
        pending = []
        for skill in entry['skills']:
            resolved = []
            for effect in skill['effectsResolved']:
                if effect.get('scope') in ('permanent_hire','permanent_collection'):
                    continue
                if effect.get('type_code') is None or effect.get('value') is None:
                    pending.append({'slot': skill['slot'], **effect})
                else:
                    resolved.append({'type_code':effect['type_code'], 'type_name':effect['type_name'],
                                     'value':effect['value'], 'display':effect['value_display']})
            if skill['slot'] == 5:
                passive_name = skill['이름']; passive_effects = resolved
            else:
                skills.append({'slot':skill['slot'], 'id':None, 'name':skill['이름'], 'effects':resolved})
        result.append({k: entry[k] for k in ('id','name','grade','subtitle','damageType','baseDamage',
                       'growthDamage','baseClickDamage','growthClickDamage','attackCooldown','canG','canAwaken','portrait')})
        result[-1].update({'gameId':None, 'idSource':'guide_local_capture', 'gStats':{}, 'skills':skills,
                          'passive':passive_name,'passiveEffects':passive_effects,
                          'fifthSkill':passive_name,'fifthSkillEffects':passive_effects,
                          'permanentEffects':entry.get('permanentEffects',[]),
                          'passives':entry.get('permanentEffects',[]),
                          'unmappedEffects':pending, 'mappingStatus':'partial' if pending else 'complete',
                          'types':{k:entry[k] for k in ('race','house','location','gender','religion','individuality')},
                          'exclusiveEquip':[], 'captureEvidence':entry['captureEvidence']})
    return result
