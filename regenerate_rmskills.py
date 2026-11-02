#!/usr/bin/env python3
"""Build random skills with reviewed catalogue screenshots taking precedence.

Capture values are already the right-hand catalogue values. Never apply an
equipped-skill multiplier or reinterpret itemBase sec as artifact/equipment IDs.
Uncaptured future entries use the decoded APK effects as existing information.
"""
import copy
import json
import re
from pathlib import Path

from random_skill_capture_overrides import apply_reviewed_capture

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'output/random_merc_skills.json'
OUTPUT=ROOT/'web/data_random_merc.json'
HTML=ROOT/'web/index.html'


def main():
    raw=json.loads(SOURCE.read_text(encoding='utf-8'))
    result=[]
    for skill in raw:
        decoded=copy.deepcopy(skill.get('effects_resolved',[]))
        for effect in decoded:effect.setdefault('namespace','mercenary_sec')
        entry={'index':skill['index'],'name':skill['name'],
               'desc':skill.get('description',''),'icon':skill.get('icon'),
               'grade':skill.get('randomValue',0),
               'effects':[e['description'] for e in decoded],
               'effectsResolved':decoded}
        result.append(apply_reviewed_capture(entry))
    result.sort(key=lambda entry:(-entry['grade'],entry['name']))
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    html=HTML.read_text(encoding='utf-8')
    compact=json.dumps(result,ensure_ascii=False,separators=(',',':'))
    pattern=r'const\s+RMSKILL_DATA\s*=\s*\[.*?\];'
    html,count=re.subn(pattern,lambda _: 'const RMSKILL_DATA='+compact+';',html,count=1,flags=re.S)
    if count!=1:raise RuntimeError('RMSKILL_DATA was not found')
    HTML.write_text(html,encoding='utf-8')
    print(f'Built {len(result)} random skills; screenshot-backed {sum(bool(e.get("captureEvidence")) for e in result)}; icons {sum(bool(e.get("portrait")) for e in result)}.')


if __name__=='__main__':main()
