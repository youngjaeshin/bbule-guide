"""Reviewed equipment facts with independent +0/+20 endpoints and provenance."""
import copy
import json
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def registry():
    path=ROOT/'equipment_capture_overrides.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'equipment':{}}


def apply_capture_overrides(items):
    data=registry()
    for item in items:
        patch=data.get('equipment',{}).get(str(item['index']))
        if patch:
            item.setdefault('apkSpecializedEffect',item.get('specializedEffect'))
            item.update(copy.deepcopy(patch))
    ids={item['index'] for item in items};identities={(item['grade'],item['name']) for item in items}
    items.extend(copy.deepcopy(item) for item in data.get('new_equipment',[])
                 if item['index'] not in ids and (item['grade'],item['name']) not in identities)
    return items
