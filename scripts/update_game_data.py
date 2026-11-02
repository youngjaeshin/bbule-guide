#!/usr/bin/env python3
"""Run the repeatable game-data update pipeline.

Default behavior is local and reversible: extract, rebuild web data, update
version labels, and verify. Add --commit and --push explicitly when publishing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]

BUILD_STEPS = [
    ("artifact web data", [sys.executable, "build_artifact_data.py"]),
    ("equipment web data", [sys.executable, "build_equipment_data.py"]),
    ("mercenary web data", [sys.executable, "build_mercenary_data.py"]),
    ("random mercenary skills", [sys.executable, "regenerate_rmskills.py"]),
    ("sub-slot mercenary skills", [sys.executable, "build_subslot_data.py"]),
    ("simulator data", [sys.executable, "build_simulator_data.py"]),
]

PY_COMPILE_TARGETS = [
    "extract_all.py",
    "build_artifact_data.py",
    "build_equipment_data.py",
    "build_mercenary_data.py",
    "build_subslot_data.py",
    "build_simulator_data.py",
    "build_scarecrow_invader.py",
    "build_commander_tab.py",
    "mercenary_capture_overrides.py",
    "artifact_capture_metadata.py",
    "random_skill_capture_overrides.py",
    "equipment_capture_overrides.py",
    "regenerate_rmskills.py",
    "verify_web_data_sync.py",
    "bgdb_utils.py",
    "premium_effects.py",
    "scripts/audit_mercenary_skill_refresh.py",
    "scripts/update_game_data.py",
]

COMMIT_PATHS = [
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/apk-update-playbook.md",
    "docs/mercenary-capture-refresh.md",
    "docs/artifact-capture-refresh.md",
    "docs/random-skill-capture-refresh.md",
    "docs/equipment-capture-refresh.md",
    "docs/commander-portraits.md",
    "scripts/audit_mercenary_skill_refresh.py",
    "scripts/update_game_data.py",
    "additional_strings.json",
    "artifact_code_mapping.json",
    "artifact_overrides.json",
    "artifact_effect_metadata.json",
    "artifact_capture_manifest.json",
    "artifact_capture_metadata.py",
    "artifacts.json",
    "bgdb_utils.py",
    "build_artifact_data.py",
    "build_equipment_data.py",
    "build_mercenary_data.py",
    "build_subslot_data.py",
    "build_simulator_data.py",
    "mercenary_capture_overrides.py",
    "mercenary_capture_overrides.json",
    "mercenary_capture_portraits.json",
    "mercenary_card_portraits.json",
    "enhancement_multipliers.py",
    "equipment_capture_overrides.py",
    "equipment_capture_overrides.json",
    "equipment_effect_metadata.json",
    "kahina_invader_rewards.json",
    "build_scarecrow_invader.py",
    "build_commander_tab.py",
    "commander_portraits.json",
    "scripts/rebuild_commander_portraits.py",
    "web/images/commander",
    "extract_all.py",
    "output/artifacts.json",
    "output/bosses.json",
    "output/creatures.json",
    "output/enemies.json",
    "output/equipment.json",
    "output/mercenaries_by_grade.json",
    "output/mercenary_skills.json",
    "output/random_merc_skills.json",
    "output/sub_slot_troops.json",
    "premium_effects.json",
    "premium_effects.py",
    "random_merc_type_mapping.json",
    "regenerate_rmskills.py",
    "random_skill_capture_overrides.py",
    "random_skill_capture_overrides.json",
    "sec_korean_mapping.json",
    "verify_web_data_sync.py",
    "web/data_artifacts.json",
    "web/data_equipment.json",
    "web/data_scarecrow_invader.json",
    "web/data_mercenaries.json",
    "web/data_random_merc.json",
    "web/images/random_skill",
    "web/data_subslot.json",
    "web/data_simulator.json",
    "web/index.html",
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, check=check)


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text)
    if count:
        path.write_text(new_text, encoding="utf-8")


def update_versions(game_version: str | None, guide_version: str | None, apk_name: str | None) -> None:
    today = dt.date.today().isoformat()
    readme = ROOT / "README.md"
    claude = ROOT / "CLAUDE.md"
    index = ROOT / "web" / "index.html"

    if game_version:
        replace_once(readme, r"\*\*게임 버전\*\*: .*", f"**게임 버전**: {game_version}")
        replace_once(readme, r"\*\*Game Version\*\*: .*", f"**Game Version**: {game_version}")
        replace_once(claude, r"- 게임 버전: .*", f"- 게임 버전: {game_version}")
    if guide_version:
        replace_once(readme, r"\*\*가이드 버전\*\*: .*", f"**가이드 버전**: {guide_version}")
        replace_once(readme, r"\*\*Guide Version\*\*: .*", f"**Guide Version**: {guide_version}")
    if apk_name:
        replace_once(readme, r"APK \([^)]*\.apk\)", f"APK ({apk_name})")
        replace_once(claude, r"bwc\d+_TEST_\d+\.apk", apk_name)

    replace_once(readme, r"\*\*Last Updated\*\*: .*", f"**Last Updated**: {today}")

    if game_version or guide_version:
        text = index.read_text(encoding="utf-8")
        current_game = game_version or re.search(r'Game ([^<|"\n]+)', text).group(1).strip()
        current_guide = guide_version or re.search(r"Guide (v[\d.]+)", text).group(1)
        label = f"Guide {current_guide} · Game {current_game}"
        text = re.sub(r'Guide v[\d.]+ · Game [^<|"\n]+', label, text)
        index.write_text(text, encoding="utf-8")


def extract_data(bin_path: Path, out_dir: Path) -> None:
    if not bin_path.exists():
        raise SystemExit(f"BGDatabase binary not found: {bin_path}")
    run([sys.executable, "extract_all.py", "--bin", str(bin_path), "--out", str(out_dir)])


def sync_legacy_files() -> None:
    """Keep tracked legacy root artifacts.json aligned with output."""
    src = ROOT / "output" / "artifacts.json"
    dst = ROOT / "artifacts.json"
    if src.exists():
        shutil.copy2(src, dst)
        print(f"Synced {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}", flush=True)


def verify(strict_codes: bool, strict_mercenary_skills: bool) -> None:
    verify_cmd = [sys.executable, "verify_web_data_sync.py"]
    if strict_codes:
        verify_cmd.append("--strict-codes")
    run(verify_cmd)
    audit_cmd = [
        sys.executable,
        "scripts/audit_mercenary_skill_refresh.py",
        "--limit",
        "20",
        "--json-output",
        "output/mercenary_skill_audit_report.json",
    ]
    if strict_mercenary_skills:
        audit_cmd.extend(["--strict", "--strict-unresolved", "--strict-ambiguous"])
    run(audit_cmd)
    run([sys.executable, "-m", "py_compile", *PY_COMPILE_TARGETS])


def git_commit(game_version: str | None, guide_version: str | None) -> None:
    existing = [p for p in COMMIT_PATHS if (ROOT / p).exists()]
    merc_data = ROOT / "web" / "data_mercenaries.json"
    if merc_data.exists():
        portraits = {
            row.get("portrait")
            for row in json.loads(merc_data.read_text(encoding="utf-8"))
            if row.get("portrait")
        }
        existing.extend(
            str((Path("web") / "images" / "mercenary" / name))
            for name in sorted(portraits)
            if (ROOT / "web" / "images" / "mercenary" / name).exists()
        )
    equipment_data = ROOT / "web" / "data_equipment.json"
    if equipment_data.exists():
        for row in json.loads(equipment_data.read_text(encoding="utf-8")):
            image = row.get("image")
            if image and image.startswith("images/"):
                path = (ROOT / "web" / image).resolve()
                if path.is_relative_to(ROOT / "web" / "images") and path.is_file():
                    existing.append(str(path.relative_to(ROOT)))
    artifact_data = ROOT / "web" / "data_artifacts.json"
    if artifact_data.exists():
        for row in json.loads(artifact_data.read_text(encoding="utf-8")):
            if row.get("portrait"):
                path = (ROOT / "web/images/artifact" / row["portrait"]).resolve()
                if path.is_relative_to(ROOT / "web/images/artifact") and path.is_file():
                    existing.append(str(path.relative_to(ROOT)))
    run(["git", "add", "--", *dict.fromkeys(existing)])
    version = game_version or "latest game data"
    guide = guide_version or "current guide"
    title = f"feat: {version} 데이터를 {guide} 가이드에 반영"
    body = (
        "Regenerated APK-derived output and web inline data, then recorded the "
        "mapping and verification scripts needed for the next repeatable update."
    )
    trailers = "\n".join([
        "Constraint: Production Vercel deployment follows origin/main; origin/master is also kept in sync",
        "Rejected: Commit APK/raw extraction folders | they are source artifacts and remain ignored",
        "Confidence: high",
        "Scope-risk: moderate",
        "Tested: python3 scripts/update_game_data.py verification pipeline",
        "Not-tested: Manual browser QA beyond generated-data and live-version checks",
        "Co-authored-by: OmX <omx@oh-my-codex.dev>",
    ])
    run(["git", "commit", "-m", title, "-m", body, "-m", trailers])


def push_branches() -> None:
    run(["git", "push", "origin", "HEAD:master"])
    run(["git", "push", "origin", "HEAD:main"])


def check_live(url: str, game_version: str | None, guide_version: str | None) -> None:
    if not (game_version or guide_version):
        return
    expected_parts = [p for p in [guide_version, game_version] if p]
    for attempt in range(1, 9):
        try:
            html = urlopen(url, timeout=20).read().decode("utf-8", "replace")
        except Exception as exc:
            print(f"Live check attempt {attempt}: {exc}")
            time.sleep(15)
            continue
        if all(part in html for part in expected_parts):
            print(f"Live check OK: {url}")
            return
        print(f"Live check attempt {attempt}: waiting for {expected_parts}")
        time.sleep(15)
    raise SystemExit(f"Live check failed: {url} did not contain {expected_parts}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", default="bgdb_clean.bin", help="Path to bgdb_clean.bin")
    parser.add_argument("--out", default="output", help="Extraction output directory")
    parser.add_argument("--skip-extract", action="store_true", help="Reuse current output/*.json")
    parser.add_argument("--game-version", help='Example: "v.1863 TEST_8"')
    parser.add_argument("--guide-version", help="Example: v0.3")
    parser.add_argument("--apk-name", help="Example: bwc1863_TEST_8.apk")
    parser.add_argument("--strict-codes", action="store_true", help="Fail on unresolved artifact codes")
    parser.add_argument(
        "--strict-mercenary-skills",
        action="store_true",
        help="Fail when same-name mercenary skills hide different APK candidate effects",
    )
    parser.add_argument("--commit", action="store_true", help="Commit the allowlisted update files")
    parser.add_argument("--push", action="store_true", help="Push HEAD to origin/master and origin/main")
    parser.add_argument("--check-live", action="store_true", help="Poll the production URL for version labels")
    parser.add_argument("--url", default="https://bbule-guide.vercel.app", help="Production URL to check")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.push and not args.commit:
        raise SystemExit("--push requires --commit")

    if not args.skip_extract:
        extract_data((ROOT / args.bin).resolve(), ROOT / args.out)

    sync_legacy_files()
    for _label, cmd in BUILD_STEPS:
        run(cmd)
    update_versions(args.game_version, args.guide_version, args.apk_name)
    verify(strict_codes=args.strict_codes, strict_mercenary_skills=args.strict_mercenary_skills)

    if args.commit:
        git_commit(args.game_version, args.guide_version)
    if args.push:
        push_branches()
    if args.check_live:
        check_live(args.url, args.game_version, args.guide_version)

    print("\nUpdate pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
