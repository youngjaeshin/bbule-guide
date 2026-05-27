# APK Update Playbook

This is the repeatable workflow used for the v.1863 TEST_8 / Guide v0.3 update.

## Source Of Truth

- APK and extracted raw folders are source artifacts. Keep them local and ignored.
- `bgdb_clean.bin` is the parsed game database input for `extract_all.py`.
- `output/*.json` is the canonical extracted data committed for the guide.
- `web/data_*.json` and inline constants in `web/index.html` are the deployed data.
- Manual mappings live in `artifact_code_mapping.json`, `artifact_overrides.json`, `premium_effects.json`, and the override tables in `build_mercenary_data.py`.

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
- `scripts/update_game_data.py` runs `python3 scripts/audit_mercenary_skill_refresh.py` during verification. Run it manually with `--strict` only after mercenary skill mappings are calibrated.
- If artifact codes are unknown, update `artifact_code_mapping.json` first. Use `artifact_overrides.json` for per-artifact slot fixes.
- Use `premium_effects.json` for verified paid artifact effects.
- Keep plain multipliers as raw numbers: `강타 배수 +0.4`, `행운 배수 +0.8`, `소울 클릭 배수 +1.0`.
- Use percent only for probability, damage percent, debuffs, and explicit `증폭` effects.
- Do not divide B/C/D artifact values by 2. v1863 values are already display scale.
- For artifact code overlaps, prefer artifact-specific meanings when listed in `artifact_code_mapping.json`.

## Mercenary Skill Caveat

Current `build_mercenary_data.py` preserves existing web skill text when a mercenary skill has the same slot/name. That avoids known bad APK candidate effects from the current resolver, but it also means same-name skill balance changes can be missed.

Do not treat mercenary skill effects as fully APK-refreshed until this is fixed. The correct long-term direction is:

1. Calibrate the mercenary skill effect-code mapping separately from equipment/artifacts.
2. Switch same-name skills to APK-extracted effect text by default.
3. Keep only explicit, named manual overrides for extraction gaps.
4. Use `scripts/audit_mercenary_skill_refresh.py` to list same-name skills where the APK candidate differs from current web text. After calibration, run `python3 scripts/update_game_data.py --strict-mercenary-skills ...` so this cannot regress silently.

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
