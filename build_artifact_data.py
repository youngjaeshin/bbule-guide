#!/usr/bin/env python3
"""
Build artifact data for the web app.

1. Reads artifacts.json (557 entries)
2. Matches portraits from web/images/artifact/ (base images only, no _2/_3/_4 variants)
3. Writes compact JSON to web/data_artifacts.json
4. Updates const ART_DATA = [...] in web/index.html
"""

import re
import json
import os

ARTIFACTS_JSON = '/Users/shin542/Desktop/Code/bbule/artifacts.json'
ARTIFACT_IMG_DIR = '/Users/shin542/Desktop/Code/bbule/web/images/artifact/'
OUTPUT_JSON = '/Users/shin542/Desktop/Code/bbule/web/data_artifacts.json'
INDEX_HTML = '/Users/shin542/Desktop/Code/bbule/web/index.html'

# Fields to include in output (exclude aType, aEffect)
KEEP_FIELDS = [
    'index', 'name', 'set_id', 'set_name', 'icon', 'rank', 'grade',
    'dropTable', 'part', 'part_name', 'effects_resolved',
]

# --- Explicit image aliases for name mismatches ---
IMAGE_ALIASES = {
    '데쓰나이트 클레이모어': '데쓰나이트 클레이 모어.png',
}

# --- Step 1: Build set of base portrait images ---
all_images = set(os.listdir(ARTIFACT_IMG_DIR))
base_images = set()
for img in all_images:
    if img.endswith('.png'):
        name = img[:-4]  # strip .png
        if not re.search(r'_[234]$', name):
            base_images.add(img)

# Build normalized lookup (collapse double spaces etc.)
norm_to_img = {}
for img in base_images:
    norm = re.sub(r'\s+', ' ', img.strip())
    if norm != img:
        norm_to_img[norm] = img

print(f"Total images in artifact dir: {len(all_images)}")
print(f"Base images (no _2/_3/_4 variants): {len(base_images)}")
print(f"Space-normalized aliases: {len(norm_to_img)}")

# --- Step 2: Read and process artifacts.json ---
with open(ARTIFACTS_JSON, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

print(f"Loaded {len(raw_data)} artifacts from artifacts.json")

matched = 0
unmatched = []
output_data = []

for entry in raw_data:
    # Build output entry with only desired fields
    out = {k: entry[k] for k in KEEP_FIELDS if k in entry}

    # Match portrait: exact → space-normalized → explicit alias
    img_filename = f"{entry['name']}.png"
    if img_filename in base_images:
        out['portrait'] = img_filename
        matched += 1
    elif img_filename in norm_to_img:
        out['portrait'] = norm_to_img[img_filename]
        matched += 1
    elif entry['name'] in IMAGE_ALIASES:
        out['portrait'] = IMAGE_ALIASES[entry['name']]
        matched += 1
    else:
        out['portrait'] = ''
        unmatched.append(entry['name'])

    output_data.append(out)

print(f"Portraits matched: {matched}/{len(output_data)}")
print(f"Unmatched ({len(unmatched)}):")
for u in unmatched[:20]:
    print(f"  - {u}")
if len(unmatched) > 20:
    print(f"  ... and {len(unmatched) - 20} more")

# --- Step 3: Write compact JSON to web/data_artifacts.json ---
compact_json = json.dumps(output_data, ensure_ascii=False, separators=(',', ':'))

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    f.write(compact_json)

print(f"\nWrote {len(output_data)} entries to {OUTPUT_JSON}")

# --- Step 4: Update const ART_DATA = [...] in index.html ---
with open(INDEX_HTML, 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'(const ART_DATA = )(\[.*?\])(;)', content, re.DOTALL)
if not match:
    print("ERROR: ART_DATA not found in index.html!")
    exit(1)

print(f"ART_DATA block found at position {match.start()}")

prefix = match.group(1)
suffix = match.group(3)

old_block = match.group(0)
new_block = prefix + compact_json + suffix

if old_block == new_block:
    print("WARNING: No change detected (block identical).")
else:
    content = content.replace(old_block, new_block, 1)
    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: index.html ART_DATA updated.")

# --- Step 5: Verify ---
with open(INDEX_HTML, 'r', encoding='utf-8') as f:
    verify_content = f.read()

verify_match = re.search(r'const ART_DATA = (\[.*?\]);', verify_content, re.DOTALL)
if verify_match:
    verify_data = json.loads(verify_match.group(1))
    portraits_set = sum(1 for e in verify_data if e.get('portrait', '') != '')
    print(f"\nVERIFICATION: {portraits_set}/{len(verify_data)} entries have portrait in index.html")
else:
    print("VERIFICATION ERROR: ART_DATA not found after update")

# --- Step 6: Spot-check specific items ---
print("\n--- Spot checks ---")
check_names = ['골든 스워드', '가계부', '미들랜드 헬름']
by_name = {e['name']: e for e in output_data}

for name in check_names:
    item = by_name.get(name)
    if item:
        print(f"\n[{name}]")
        print(f"  index={item['index']}, grade={item['grade']}, part_name={item['part_name']}")
        print(f"  portrait='{item['portrait']}'")
        for eff in item.get('effects_resolved', []):
            print(f"  effect: {eff['description']}")
    else:
        print(f"NOT FOUND: {name}")
