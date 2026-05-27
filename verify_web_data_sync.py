#!/usr/bin/env python3
"""Verify generated web JSON and inline index.html data stay in sync."""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "web" / "index.html"

GRADE_ORDER = ["E", "D", "C", "B", "A", "S", "G", "X", "H", "O", "P", "Q", "유료"]

DATASETS = [
    {
        "label": "equipment",
        "sources": [
            ("output", ROOT / "output" / "equipment.json"),
            ("web", ROOT / "web" / "data_equipment.json"),
        ],
        "inline_const": "EQUIP_DATA",
        "effect_paths": [
            ("effect_type",),
            ("mainType_name",),
        ],
    },
    {
        "label": "artifacts",
        "sources": [
            ("output", ROOT / "output" / "artifacts.json"),
            ("root", ROOT / "artifacts.json"),
            ("web", ROOT / "web" / "data_artifacts.json"),
        ],
        "inline_const": "ART_DATA",
        "effect_paths": [
            ("effects_resolved", "*", "type_name"),
        ],
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_inline_const(name):
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(rf"const\s+{re.escape(name)}\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        raise RuntimeError(f"{name} not found in {INDEX_HTML}")
    return json.loads(match.group(1))


def grade_counts(rows):
    counts = Counter(row.get("grade", "") for row in rows)
    return {grade: counts[grade] for grade in GRADE_ORDER if counts[grade]}


def names_by_grade(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get("grade", ""), set()).add(row.get("name", ""))
    return grouped


def extract_values(row, path):
    if not path:
        yield row
        return
    head, *tail = path
    if head == "*":
        if isinstance(row, list):
            for item in row:
                yield from extract_values(item, tuple(tail))
        return
    if isinstance(row, dict) and head in row:
        yield from extract_values(row[head], tuple(tail))


def unresolved_codes(rows, effect_paths):
    found = []
    for row in rows:
        for path in effect_paths:
            for value in extract_values(row, path):
                if isinstance(value, str) and value.startswith("코드 "):
                    found.append((row.get("grade"), row.get("name"), value))
    return found


def portrait_warnings(rows):
    missing = [row for row in rows if not row.get("portrait")]
    counts = Counter(row.get("grade", "") for row in missing)
    return {grade: counts[grade] for grade in GRADE_ORDER if counts[grade]}, len(missing)


def compare_dataset(spec, strict_codes=False):
    errors = []
    warnings = []
    label = spec["label"]
    loaded = [(name, load_json(path)) for name, path in spec["sources"]]
    loaded.append(("index", load_inline_const(spec["inline_const"])))

    print(f"\n[{label}]")
    for name, rows in loaded:
        print(f"  {name:6} total={len(rows):3} grades={grade_counts(rows)}")

    reference_name, reference_rows = loaded[0]
    reference_groups = names_by_grade(reference_rows)
    for name, rows in loaded[1:]:
        groups = names_by_grade(rows)
        grades = set(reference_groups) | set(groups)
        for grade in sorted(grades, key=lambda g: GRADE_ORDER.index(g) if g in GRADE_ORDER else 99):
            missing = sorted(reference_groups.get(grade, set()) - groups.get(grade, set()))
            extra = sorted(groups.get(grade, set()) - reference_groups.get(grade, set()))
            if missing or extra:
                errors.append(
                    f"{label}: {name} differs from {reference_name} for grade {grade}: "
                    f"missing={missing}, extra={extra}"
                )

    unresolved = unresolved_codes(reference_rows, spec["effect_paths"])
    if unresolved:
        sample = ", ".join(f"{grade}/{name}: {code}" for grade, name, code in unresolved[:10])
        message = f"{label}: unresolved effect codes {len(unresolved)} found; sample: {sample}"
        if strict_codes:
            errors.append(message)
        else:
            warnings.append(message)

    for name, rows in loaded:
        if name not in {"web", "index"}:
            continue
        portrait_by_grade, portrait_total = portrait_warnings(rows)
        if portrait_total:
            warnings.append(f"{label}: {name} missing portraits={portrait_total} by grade={portrait_by_grade}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-codes", action="store_true", help="fail on unresolved '코드 N' effect names")
    args = parser.parse_args()

    all_errors = []
    all_warnings = []
    for spec in DATASETS:
        errors, warnings = compare_dataset(spec, strict_codes=args.strict_codes)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    if all_warnings:
        print("\nWarnings:")
        for warning in all_warnings:
            print(f"  - {warning}")

    if all_errors:
        print("\nErrors:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("\nOK: web JSON and inline index.html data are synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
