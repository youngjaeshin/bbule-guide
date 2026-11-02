"""Reviewed random-skill catalogue facts; independent of equipped skill boosts."""
import copy
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def clean_effect(text):
    text=re.sub(r'(?<=[\d.])\s+(?=[\d.])','',text)
    text=re.sub(r'\s+%','%',text).strip().rstrip(',').strip()
    for word in ['모든','용병','확률','데미지','공격','크리티컬','마법','물리','혼합',
                 '카오스','트리니티','베이스','클릭','소울','추가','피격','회피','저항력',
                 '감소','무효화','관통','성장','지속시간','최대','레벨','저장량','획득','아티팩트']:
        text=re.sub(r'\s*'.join(word),word,text)
    for phrase in ['공격 무효화 관통','피격 지속시간','클릭 크리티컬','소울 클릭',
                   '골드 저장량','골드 획득량','즉시 공격','신성 데미지','순수 데미지','베이스 데미지']:
        text=re.sub(r'\s*'.join(phrase.replace(' ','')),phrase,text)
    return re.sub(r'\s+',' ',text).strip()


def parse_effect(text, type_code, raw_value, slot):
    text=clean_effect(text)
    hit=re.search(r'([+-]?\d+(?:\.\d+)?)(%)?$',text)
    result={'namespace':'mercenary_sec','type_code':type_code,'source_slot':slot,
            'raw_value':raw_value,'description':text,'source_context':'right_hand_random_skill_catalogue'}
    if hit:
        number=float(hit[1]);unit=hit[2] or ''
        result.update(type_name=text[:hit.start()].strip(),value=number/100 if unit=='%' else number,
                      value_display=hit[1]+unit,format='pct' if unit else 'raw')
        label=result['type_name']
        condition=re.match(r'^(종족|지역|개성)이\s*(.+?)인\s*용병',label)
        if condition:
            kinds={'종족':'race_count','지역':'region_count','개성':'personality_count'}
            result['condition']={'kind':kinds[condition[1]],'value':condition[2].strip(),
                                 'operator':'per_mercenary','expression':label}
    elif '불가' in text:
        result.update(type_name=text,value=None,value_display='',operation='disable',format='restriction')
    else:
        raise ValueError(f'Unparsed reviewed random skill effect: {text}')
    return result


@lru_cache(maxsize=1)
def registry():
    path=ROOT/'random_skill_capture_overrides.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'skills':{}}


def apply_reviewed_capture(entry):
    patch=registry().get('skills',{}).get(str(entry['index']))
    if patch:
        for field in ('name','aliases','grade','effects','effectsResolved','portrait','captureEvidence'):
            if field in patch:entry[field]=copy.deepcopy(patch[field])
    return entry
