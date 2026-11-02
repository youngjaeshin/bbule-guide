#!/usr/bin/env python3
"""Update only commander identities/portraits, retaining current guide facts."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_commander_tab import apply_commander_portraits


def main():
    path = ROOT / 'web/index.html'
    html = path.read_text(encoding='utf-8')
    pattern = r'const\s+MERC_INFO\s*=\s*(\[.*?\]);'
    match = re.search(pattern, html, re.S)
    if not match:
        raise RuntimeError('Missing MERC_INFO')
    rows = apply_commander_portraits(json.loads(match[1]))
    value = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
    html = re.sub(pattern, lambda _: 'const MERC_INFO=' + value + ';', html, count=1, flags=re.S)
    path.write_text(html, encoding='utf-8')
    print(f'Commander portraits: {sum(bool(row.get("portrait")) for row in rows)}/{len(rows)}')


if __name__ == '__main__':
    main()
