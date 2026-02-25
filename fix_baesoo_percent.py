#!/usr/bin/env python3
"""
fix_baesoo_percent.py

Task 1: Fix "배수" values in data_mercenaries.json
  - Convert raw decimal multipliers after "배수 +" to percentage strings
  - e.g. "강타 배수 +0.08" → "강타 배수 +8%"

Task 2: Update inline MERC_DATA in web/index.html
  - Replace the multi-line const MERC_DATA=[...]; block with
    a single-line version using the updated JSON.
"""

import re
import json
import os

MERC_JSON = "/Users/shin542/Desktop/Code/bbule/web/data_mercenaries.json"
INDEX_HTML = "/Users/shin542/Desktop/Code/bbule/web/index.html"

# ──────────────────────────────────────────────
# Task 1: Fix 배수 values
# ──────────────────────────────────────────────

def format_pct(val: float) -> str:
    """Format val*100 as integer or minimal-decimal string."""
    pct = val * 100
    if abs(pct - round(pct)) < 1e-9:
        return f"{int(round(pct))}%"
    else:
        # Remove trailing zeros
        return f"{pct:.10g}%"

def replace_baesoo(match) -> str:
    prefix = match.group(1)   # e.g. "배수 " or "배수 증폭 "
    sign   = match.group(2)   # "+" or "-"
    num    = match.group(3)   # numeric string
    try:
        val = float(num)
    except ValueError:
        return match.group(0)  # leave unchanged if can't parse
    pct_str = format_pct(val)
    return f"{prefix}{sign}{pct_str}"

# Pattern: (배수 optionally followed by 증폭 with optional spaces)(+/-)(number)
# Handles: 배수 +0.08, 배수 증폭 +0.04, 배수 +1, 배수 +0.9, 배수 +0.012
PATTERN = re.compile(r'(배수\s*(?:증폭\s*)?)([+-])([\d]+\.?[\d]*)')

print("=" * 60)
print("Task 1: Fixing 배수 values in data_mercenaries.json")
print("=" * 60)

with open(MERC_JSON, "r", encoding="utf-8") as f:
    original_text = f.read()

examples_shown = 0
replacements = 0

def replace_and_track(match):
    global replacements, examples_shown
    original = match.group(0)
    result = replace_baesoo(match)
    if result != original:
        replacements += 1
        if examples_shown < 10:
            print(f"  Before: ...{original}...")
            print(f"  After:  ...{result}...")
            print()
            examples_shown += 1
    return result

fixed_text = PATTERN.sub(replace_and_track, original_text)

print(f"Total replacements made: {replacements}")

# Validate JSON
try:
    data = json.loads(fixed_text)
    print(f"JSON validation: OK ({len(data)} mercenaries)")
except json.JSONDecodeError as e:
    print(f"ERROR: JSON invalid after replacement: {e}")
    exit(1)

with open(MERC_JSON, "w", encoding="utf-8") as f:
    f.write(fixed_text)

print(f"Written: {MERC_JSON}")

# ──────────────────────────────────────────────
# Task 2: Update MERC_DATA in index.html
# ──────────────────────────────────────────────

print()
print("=" * 60)
print("Task 2: Updating MERC_DATA in web/index.html")
print("=" * 60)

# Minified JSON (compact, no extra spaces)
merc_json_minified = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

with open(INDEX_HTML, "r", encoding="utf-8") as f:
    html_text = f.read()

# Find the MERC_DATA block: starts with "const MERC_DATA=[" and ends with "];"
# The block may span many lines (it's a big JSON array).
# Strategy: find the start marker, then find the matching closing ];\n

start_marker = "const MERC_DATA=["
start_idx = html_text.find(start_marker)
if start_idx == -1:
    # Try alternate spacing
    start_marker = "const MERC_DATA = ["
    start_idx = html_text.find(start_marker)

if start_idx == -1:
    print("ERROR: Could not find 'const MERC_DATA=' in index.html")
    exit(1)

# Find the end: we need to find the closing ]; of this const
# Walk forward counting brackets
bracket_depth = 0
i = start_idx + len(start_marker) - 1  # position of the opening [
found_end = False
for j in range(i, len(html_text)):
    ch = html_text[j]
    if ch == '[':
        bracket_depth += 1
    elif ch == ']':
        bracket_depth -= 1
        if bracket_depth == 0:
            # j is the closing ], next should be ;
            end_idx = j + 1  # position after ]
            # skip optional ;
            if end_idx < len(html_text) and html_text[end_idx] == ';':
                end_idx += 1
            found_end = True
            break

if not found_end:
    print("ERROR: Could not find end of MERC_DATA block")
    exit(1)

old_block = html_text[start_idx:end_idx]
new_block = f"const MERC_DATA={merc_json_minified};"

print(f"Old MERC_DATA block length: {len(old_block):,} chars")
print(f"New MERC_DATA block length: {len(new_block):,} chars")

new_html = html_text[:start_idx] + new_block + html_text[end_idx:]

with open(INDEX_HTML, "w", encoding="utf-8") as f:
    f.write(new_html)

print(f"Written: {INDEX_HTML}")

# Verify the replacement
verify_idx = new_html.find("const MERC_DATA=")
verify_end = new_html.find(";", verify_idx)
snippet = new_html[verify_idx:verify_idx+80]
print(f"Verification snippet: {snippet}...")

print()
print("Done.")
