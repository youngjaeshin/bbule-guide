"""Apply reviewed artifact identities and provenance without mixing effect enums."""
import copy
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def manifest():
    path=ROOT/'artifact_capture_manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def apply_capture_metadata(artifacts):
    data=manifest();entries=data.get('artifacts',{})
    for artifact in artifacts:
        patch=entries.get(str(artifact['index']))
        if patch:
            for field in ('name','aliases','captureEvidence','captureStatus','sourceRecords','portrait','imageEvidence','optionEvidence','sourceConflicts','optionExceptions'):
                if field in patch:artifact[field]=copy.deepcopy(patch[field])
        else:
            artifact.setdefault('captureStatus','no_direct_effect_capture')
            artifact.setdefault('sourceRecords',[{'source_type':'legacy_guide','source_scope':'effects_not_independently_rechecked'}])
    existing={a['index'] for a in artifacts}
    identities={(a['grade'],a['name']) for a in artifacts}
    artifacts.extend(copy.deepcopy(a) for a in data.get('new_artifacts',[])
                     if a['index'] not in existing and (a['grade'],a['name']) not in identities)
    return artifacts
