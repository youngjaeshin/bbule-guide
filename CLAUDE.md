# bbule - 대용병시대 뿔레전쟁 웹 가이드

## Project Overview
모바일 게임 "대용병시대 뿔레전쟁" APK에서 추출한 게임 데이터를 웹 가이드로 제공하는 프로젝트.

## Architecture

### Data Pipeline
```
APK (bwc1853_TEST_11.apk)
  → bgdb_clean.bin (BGDatabase binary)
  → extract_all.py (Python extractor)
  → output/*.json (structured JSON)
  → build_*_data.py (web data builders)
  → web/data_*.json + web/index.html (inline DATA)
```

### Key Files
- `extract_all.py` - 핵심 추출기. BGDatabase 바이너리 파싱, 효과 코드 해석, JSON 출력
- `build_artifact_data.py` - artifacts.json → web/data_artifacts.json + ART_DATA inline
- `build_equipment_data.py` - equipment.json → web/data_equipment.json
- `web/index.html` - 싱글페이지 웹 가이드 (모든 JS/CSS 인라인)
- `artifact_code_mapping.json` - 아티팩트 효과 코드 419개 매핑

### Binary Parsing Rules (CRITICAL)
- **아티팩트 shift+1**: artifact[i]의 aType과 aEffect는 모두 row[i-1]에서 가져옴
- **장비는 shift 없음**: equipment의 효과는 동일 인덱스에서 직접 읽음
- **Field header**: [4B name_len][name][31B header][4B data_size][data][22B separator]
- **Nested arrays**: [4B row_count][4B vals_per_row][row_count * vals_per_row * 4B data]

### Effect Code System
- `artifact_code_mapping.json`: 아티팩트 전용 코드 (0=데미지, 1=추가데미지, ...)
- `enum_mappings.json`: 장비/스킬 전용 코드
- 효과값 포맷: 'pct' (×100+%), 'raw' (배수), 'int' (정수), 'abs' (절대값)

### Web Tabs (index.html)
| Tab | Data Source | Status |
|-----|------------|--------|
| 용병 | data_mercenaries.json | Active |
| 장비 | data_equipment.json | Active |
| 아티팩트 | ART_DATA (inline) | Active |
| 랜덤용병 | RMSKILL_DATA (inline) | Disabled |
| 보조슬롯 | data_subslot.json | Disabled |
| 허수&침략자 | inline JSON | Disabled |
| 지휘관 | data_commanders.json | Disabled |
| 용어 | - | Disabled |

## Development Notes
- 한국어 사용 (코드 변수명은 영어)
- 엑셀 데이터는 구버전이므로 참고용으로만 사용
- APK 바이너리가 정본 (ground truth)
