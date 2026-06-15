# APK Update Playbook

This is the repeatable workflow used for the v.1863 TEST_8 / Guide v0.3 update.

## Source Of Truth

- APK and extracted raw folders are source artifacts. Keep them local and ignored.
- `bgdb_clean.bin` is the parsed game database input for `extract_all.py`.
- `output/*.json` is the canonical extracted data committed for the guide.
- `web/data_*.json` and inline constants in `web/index.html` are the deployed data.
- Effect-code namespaces are separate: mercenary skills use `sec_korean_mapping.json`, equipment uses `MAINTYPE_TO_EFFECT` in `extract_all.py`, and artifacts use artifact `aType` mappings plus `artifact_overrides.json`.
- Do not blindly reuse one namespace in another. In particular, itemBase skill codes such as `7` are `sec7` skill templates, not equipment `mainType=7`.
- Manual mappings live in `sec_korean_mapping.json`, `artifact_code_mapping.json`, `artifact_overrides.json`, `premium_effects.json`, and the override tables in `build_mercenary_data.py`. `artifact_code_mapping.json` is artifact-scoped but partially inferred, so conflicting entries must be verified before becoming global artifact meanings.

## Standard Update Command

After extracting `bgdb_clean.bin` from the new APK:

```bash
python3 scripts/update_game_data.py \
  --bin bgdb_clean.bin \
  --game-version "v.1863 TEST_8" \
  --guide-version v0.3 \
  --apk-name bwc1863_TEST_8.apk
```

When the generated data is reviewed and ready to publish:

```bash
python3 scripts/update_game_data.py \
  --skip-extract \
  --game-version "v.1863 TEST_8" \
  --guide-version v0.3 \
  --commit \
  --push \
  --check-live
```

`--push` updates both `origin/master` and `origin/main`. Vercel production follows `main`; pushing only `master` creates preview deployments.

## Manual Review Checklist

- Check `python3 verify_web_data_sync.py` warnings. Missing portraits may be acceptable; unresolved `코드 N` entries need review.
- `scripts/update_game_data.py` runs `python3 scripts/audit_mercenary_skill_refresh.py` during verification. Use `--strict-mercenary-skills` when publishing so same-name mercenary skill changes cannot be missed.
- If artifact codes are unknown, update `artifact_code_mapping.json` first. Use `artifact_overrides.json` for per-artifact slot fixes.
- Use `premium_effects.json` for verified paid artifact effects.
- Keep plain multipliers as raw numbers: `강타 배수 +0.4`, `행운 배수 +0.8`, `소울 클릭 배수 +1.0`.
- Use percent only for probability, damage percent, debuffs, and explicit `증폭` effects.
- Do not divide B/C/D artifact values by 2. v1863 values are already display scale.
- For artifact code overlaps, prefer verified artifact meanings. If a value in `artifact_code_mapping.json` conflicts with current verified output, fix the artifact mapping or add a per-item `artifact_overrides.json` entry instead of applying it blindly.

## Mercenary Skill Rules

`build_mercenary_data.py` must use APK-extracted skill effects even when a mercenary skill has the same slot/name as the previous guide. Skill names can stay the same while effect type or value changes, such as `에밀리 / 저항력 약화의 문양` changing to physical and magical resistance reduction.

Keep these rules intact:

1. Resolve mercenary skills with `sec` mappings, not equipment `mainType` mappings.
2. Prefer `output/mercenary_skills.json`, `output/sub_slot_troops.json`, and `output/random_merc_skills.json` over legacy web data.
3. Keep old web skill text only when APK output has no candidate effect text.
4. Run `python3 scripts/audit_mercenary_skill_refresh.py --strict`; the expected masked-difference count is zero.

### Mercenary Skill Display Multipliers

Some mercenary skill `sec` values are stored in APK raw scale and need the
game's skill display multipliers before they are shown or used by the simulator.
These are skill-only multipliers and must stay separate from equipment
`MAINTYPE_TO_EFFECT` ratios, which are already calibrated.

Reference screenshot: `docs/mercenary-skill-multiplier-constants.png`.

Current verified skill display multipliers:

- Personal damage skill: `x1.5`
- All/type damage skill: `x3`
- Personal click damage skill: `x2`
- All/type click damage skill: `x2`
- Personal additional damage skill: `x2`
- All/type additional damage skill: `x2`
- Holy damage skill: `x1.5`
- Base damage skill: `x3`

When adding new `sec` damage-like codes, decide whether they belong to one of
these skill multiplier sets in `extract_all.py`. Do not apply these to final
damage, growth damage, damage amplification, extra click damage, critical/lucky
damage, or equipment/artifact effects unless verified separately in game.

## Files To Commit

Commit generated guide data and the scripts/mappings that reproduce it:

- `output/*.json`
- `web/data_*.json`
- `web/index.html`
- new used portraits under `web/images/mercenary/`
- `artifact_code_mapping.json`, `artifact_overrides.json`, `premium_effects.json`
- changed Python pipeline scripts and `verify_web_data_sync.py`
- docs that explain the update

Do not commit APKs, `bgdb_clean.bin`, `apk/extracted/`, raw screenshots, crop folders, `.DS_Store`, `.vercel/`, or cafe credentials.

## Deployment Verification

After push, confirm both branches point to the release commit:

```bash
git ls-remote origin refs/heads/main refs/heads/master
```

Then check live HTML for the expected label:

```bash
curl -sL https://bbule-guide.vercel.app | rg "Guide v0.3|Game v.1863"
```

If the live site still shows the old version, inspect GitHub deployment statuses. A preview deployment means `master` was updated but `main` was not.
