# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

모바일 게임 "대용병시대 뿔레전쟁" APK에서 추출한 게임 데이터를 싱글페이지 웹 가이드로 제공하는 프로젝트.
- 레포: `youngjaeshin/bbule-guide`
- 배포: https://bbule-guide.vercel.app (GitHub 연동 자동 배포)
- 게임 버전: v.1863 TEST_8

## Data Pipeline

```
bwc1863_TEST_8.apk
  → bgdb_clean.bin (BGDatabase binary, 2.7MB)
  → extract_all.py (바이너리 파싱 + 효과코드 해석)
  → output/*.json (creatures, equipment, artifacts 등 9개)
  → build_*_data.py (이미지 매칭 + 효과 매핑 + 웹 최적화)
  → web/data_*.json + web/index.html (inline DATA)
```

## Build & Deploy Commands

```bash
# 권장: 추출 → 웹 빌드 → 버전 표기 → 검증
python3 scripts/update_game_data.py --bin bgdb_clean.bin --game-version "v.1863 TEST_8" --guide-version v0.3 --apk-name bwc1863_TEST_8.apk

# 1. 바이너리 → JSON 추출 (9개 파일 생성)
python3 extract_all.py
python3 extract_all.py --bin /path/to/bgdb_clean.bin --out /output/dir

# 2. 웹 데이터 빌드 (각각 독립 실행 가능)
python3 build_mercenary_data.py  # → web/data_mercenaries.json + index.html MERC_DATA
python3 regenerate_rmskills.py   # → web/data_random_merc.json + index.html RMSKILL_DATA
python3 build_artifact_data.py    # → web/data_artifacts.json + index.html ART_DATA 인라인 업데이트
python3 build_equipment_data.py   # → web/data_equipment.json (icon 기반 이미지 매칭)
python3 build_simulator_data.py   # → web/data_simulator.json
python3 build_commander_tab.py    # → 지휘관 탭 (34 용병 + XP 레벨업 표)
python3 build_scarecrow_invader.py # → 허수아비/침략자 탭

# 3. 배포 (Vercel production은 main, preview는 master)
git push origin HEAD:master
git push origin HEAD:main
```

## Binary Parsing Rules (CRITICAL)

- **아티팩트 shift+1**: `artifact[i]`의 aType/aEffect는 `row[i-1]`에서 가져옴
- **장비는 shift 없음**: equipment 효과는 동일 인덱스에서 직접 읽음
- **Field header**: `[4B name_len][name][31B header][4B data_size][data][22B separator]`
- **Nested arrays**: `[4B row_count][4B vals_per_row][row_count × vals_per_row × 4B data]`
- **String tables**: `detect_offsets()`로 자동 감지. v.1863 TEST_8 기준 koKR offset 639581, name_map offset 493111

### String Table Ranges (name_map 기준)
| 테이블 | 범위 | 개수 |
|--------|------|------|
| creatureBase | 0–550 | 551 |
| itemBase | 551–1917 | 1367 |
| enemy | 1918–2304 | 387 |
| boss | 2305–2414 | 110 |
| stage | 2415–2914 | 500 |
| item/equip | 2915–3455 | 541 |
| commander | 3456–3490 | 35 |
| cmdSpecialty | 3491–3525 | 35 |
| artifact | 3526–4082 | 557 |

## Effect Code System

- 용병 스킬, 장비, 아티팩트는 효과 코드 namespace가 다르다. 같은 숫자라도 의미가 다를 수 있으므로 매핑을 섞지 않는다.
- 용병 스킬: `sec_korean_mapping.json` + `resolve_skill_effects()` (`extract_all.py`)
- 장비: `MAINTYPE_TO_EFFECT` (`extract_all.py`)
- 아티팩트: `artifact_code_mapping.json` + `artifact_overrides.json`
- `artifact_code_mapping.json`은 아티팩트 전용이지만 일부 항목은 추론/수동 보정 기반이므로 전역 아티팩트 의미로 승격하기 전에 충돌 여부를 확인한다.
- `enum_mappings.json`: legacy/xlsx cross-reference 보조 자료
- `premium_effects.json`: 유료 아티팩트 32개 verified 데이터
- 효과값 포맷: `pct` (×100+%), `raw` (배수), `int` (정수), `abs` (절대값)
- **코드 90** = "모든 용병의 치명타 확률" (데미지 아님, ×1000 스케일링 없음)
- **유료 전용 코드**: 1000번대 (1064=데미지, 1065=추가데미지 등) — 일반 코드와 같은 이름이어도 정상
- **세트/조건부 코드**: 400~600번대에 "(세트완성시)", "(장착시)" 접두사로 구분

## Image Matching Rules (Validated)

**아티팩트** (100% 매칭):
- `icon` 필드 → `web/images/artifact/{icon}.png`
- 557개 중 37개는 New 버전이 원본과 icon 공유
- 아낙수나문 유료 4종(idx 505~508)은 icon=0 임시매핑

**장비** (아이콘 기반 매칭):
- `icon` 필드 → `web/images/equip-icon/{icon}.png` (padStart(3,'0'))
- **idx ≠ icon** — 장비는 순서가 다름, 반드시 icon 기준으로 이미지 매칭
- 누락 이미지는 `verify_web_data_sync.py` 경고에서 등급별로 확인

## Web Architecture (web/index.html)

싱글페이지 SPA, ~39,000줄. 모든 JS/CSS/DATA 인라인.

**인라인 데이터 상수**: `EQUIP_DATA`, `ART_DATA`, `RMSKILL_DATA`, `MERC_DATA` 등이 index.html 내에 직접 포함.

**인라인 동기화 주의**: MERC_DATA 라인 매칭 시 `const MERC_DATA = [` (공백 있음). `startswith('const MERC_DATA=')` (공백 없음)으로 매칭하면 실패. **반드시 `line.strip().startswith('const MERC_DATA')`로 매칭**.

### Tab 상태
| Tab | Data Source | Status |
|-----|------------|--------|
| 용병 | data_mercenaries.json | Active |
| 장비 | data_equipment.json | Active |
| 아티팩트 | ART_DATA (inline) | Active |
| 용어 | data_glossary.json (5 서브탭, 117항목) | Active |
| 건의게시판 | localStorage | Active |
| 랜덤용병 | RMSKILL_DATA (inline, 265스킬) | Disabled |
| 보조슬롯 | data_subslot.json | Disabled |
| 허수&침략자 | data_scarecrow_invader.json | Disabled |
| 지휘관 | data_commanders.json | Disabled |

### UI 패턴
- 등급 필터: 멀티셀렉트 토글 (`new Set()` 기반), 높은 등급 우선 정렬 (P→O→H→...→E)
- 검색: 드롭다운 스코프 (통합/이름/효과) + 텍스트 입력
- CSS 변수: 13개 그레이드 색상 (E, D, C, B, A, S, G, H, O, P, X, Q, paid)

## Cafe Scraper (cafe_scraper/)

네이버 카페 "클리커 정산" 게시판에서 스크린샷 DPS 값을 추출하여 랭킹표를 생성.

```bash
python pipeline.py fetch   # Step 1: 글 메타 + 이미지 URL 수집
python pipeline.py crop    # Step 2: 상단 HUD 크롭 (8% height × 55% width, 4배 확대)
# Step 3: 비전 에이전트로 DPS 읽기 (AGENT_INSTRUCTIONS.md 참조)
python pipeline.py rank    # Step 4: 최종 랭킹 생성
```

- **DPS 합산 규칙**: "DPS"라고 표시된 모든 값을 합산 (물리/마법/카오스/즉시공격/신성/클릭/추가클릭/자동클릭)
- **비전 모델**: Sonnet 필수 (Haiku는 경→억 오독, 숫자 탈락 문제)
- **한국어 숫자**: 만(10⁴), 억(10⁸), 조(10¹²), 경(10¹⁶)

## Development Notes

- 한국어 사용 (코드 변수명은 영어)
- APK 바이너리가 정본 (ground truth), 엑셀 데이터는 구버전 참고용
- `web/index.html` 수정 시 인라인 데이터/JS 위치 주의 (39K줄 단일 파일)
