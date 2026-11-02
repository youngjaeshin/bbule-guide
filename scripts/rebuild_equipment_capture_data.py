#!/usr/bin/env python3
"""Apply reviewed equipment only, preserving all other completed datasets."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from equipment_capture_overrides import apply_capture_overrides


def main():
    rows=json.loads((ROOT/'output/equipment.json').read_text(encoding='utf-8'))
    rows=apply_capture_overrides(rows)
    text=json.dumps(rows,ensure_ascii=False,indent=2)+'\n'
    for path in [ROOT/'equipment.json',ROOT/'output/equipment.json']:
        path.write_text(text,encoding='utf-8')
    print(f'Rebuilt {len(rows)} equipment entries with independent0/20 values.')


if __name__=='__main__':main()
