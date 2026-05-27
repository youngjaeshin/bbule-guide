# Repository Guidelines

## Project Structure & Module Organization
This repository builds a static web guide from extracted game data. Root Python scripts are the data pipeline: `extract_all.py` parses `bgdb_clean.bin`, `build_*_data.py` transforms JSON for the site, and `fix_*.py` / `debug_*.py` scripts are targeted utilities. Shared binary parsing helpers live in `bgdb_utils.py`.

Generated extraction output goes in `output/`. The deployed static app lives in `web/`: `web/index.html` is the single-page app, `web/data_*.json` is browser-loaded data, and `web/images/` stores icons. `cafe_scraper/` is an optional ranking-data pipeline.

## Build, Test, and Development Commands
- `python3 scripts/update_game_data.py --bin bgdb_clean.bin --game-version "v.xxxx TEST_n" --guide-version v0.x`: run the standard extract, rebuild, version-label, and verification pipeline.
- `python3 extract_all.py`: parse `bgdb_clean.bin` into `output/*.json`.
- `python3 extract_all.py --bin /path/to/bgdb_clean.bin --out output`: run extraction with explicit paths.
- `python3 build_artifact_data.py`: rebuild artifact web data and inline `ART_DATA`.
- `python3 build_equipment_data.py`: rebuild equipment web data, icon mappings, and inline `EQUIP_DATA`.
- `python3 build_mercenary_data.py`: rebuild mercenary web data and inline `MERC_DATA`.
- `python3 regenerate_rmskills.py`: rebuild random mercenary skill data and inline `RMSKILL_DATA`.
- `python3 build_commander_tab.py`: rebuild commander tab data.
- `python3 build_scarecrow_invader.py`: rebuild scarecrow/invader data.
- `python3 verify_web_data_sync.py`: verify root/output/web JSON and inline `index.html` data stay synchronized.
- `python3 scripts/audit_mercenary_skill_refresh.py`: report same-name mercenary skills where current web text masks APK candidate effects; `scripts/update_game_data.py` runs this during verification.
- `python3 -m http.server 8000 --directory web`: serve the static site locally at `http://localhost:8000`.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation, descriptive snake_case names, and small script-level functions. Keep source and generated paths explicit near the top of scripts. Prefer stable JSON key ordering where practical. Use English for code identifiers; keep game-facing Korean strings unchanged.

For `web/index.html`, avoid broad rewrites. It is a large inline SPA, so update only the needed data constant or UI section. When matching inline data constants, tolerate spacing, for example `line.strip().startswith('const MERC_DATA')`.

## Testing Guidelines
There is no formal test framework yet. Before committing data-pipeline changes, run the relevant build script and `python3 verify_web_data_sync.py`; this catches stale inline constants such as `EQUIP_DATA` or `ART_DATA`. Use `python3 -m py_compile script_name.py` for changed Python files, and run `python3 verify_enums.py` when enum or effect mappings change.

## Commit & Pull Request Guidelines
Recent history uses concise Conventional Commit prefixes, usually `feat:` for data/version additions and `fix:` for corrections, followed by a specific summary. Example: `fix: artifact code mapping correction`.

Pull requests should describe the data source or game version, list regenerated files, and include verification commands. For UI-visible changes, attach screenshots or note the local URL checked. Do not commit `__pycache__/`, `.DS_Store`, or temporary scraper backups.

For releases, keep `origin/main` and `origin/master` on the same commit. Vercel production follows `main`; `master` may only create preview deployments.

Known limitation: mercenary skill effects are not yet safe to overwrite from APK candidates when the slot/name is unchanged. Same-name skills can still have balance changes, so the next extraction pass must calibrate mercenary skill effect-code mapping before switching to APK-first skill effects. After calibration, use `--strict-mercenary-skills` in `scripts/update_game_data.py`.

## Security & Configuration Tips
Treat APK extracts, binary databases, and scraped screenshots as source artifacts. Do not add credentials, browser cookies, or private cafe access tokens to the repository.
