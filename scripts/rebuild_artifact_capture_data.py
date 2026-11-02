#!/usr/bin/env python3
"""Rebuild artifact outputs only; completed mercenary data is left untouched."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from artifact_capture_metadata import apply_capture_metadata
from extract_all import resolve_artifact_effects, apply_artifact_overrides


def main():
    rows=json.loads((ROOT/'output/artifacts.json').read_text(encoding='utf-8'))
    rows=[r for r in rows if r.get('indexSource')!='guide_local_capture']
    for row in rows:
        if row['grade']=='유료':
            continue  # No readable effect screenshot: retain the existing data.
        effects=resolve_artifact_effects(row['aType'],row['aEffect'])
        row['effects_resolved']=apply_artifact_overrides(row['index'],effects)
    rows=apply_capture_metadata(rows)
    text=json.dumps(rows,ensure_ascii=False,indent=2)+'\n'
    for path in [ROOT/'artifacts.json',ROOT/'output/artifacts.json']:
        path.write_text(text,encoding='utf-8')
    print(f'Rebuilt {len(rows)} artifacts; premium effect data retained.')


if __name__=='__main__':main()
