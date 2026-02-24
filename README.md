# 대용병시대 뿔레전쟁 가이드

> 모바일 게임 "대용병시대 뿔레전쟁"의 게임 데이터를 웹 가이드로 제공합니다.
> APK 바이너리에서 추출한 데이터를 구조화하여 빠른 검색과 필터링이 가능합니다.

**배포 URL**: https://bbule-guide.vercel.app
**게임 버전**: v.1853 TEST_11
**가이드 버전**: v0.2

---

## 주요 기능

### 1. 용병 탭 (Mercenaries)
- 539개 용병 데이터
- 등급별 필터링 (E~P, X, Q, 유료)
- 이름/효과 검색
- 스킬 정보 및 능력치 조회

### 2. 장비 탭 (Equipment)
- 533개 장비 데이터
- 아이콘 기반 시각화 (95.5% 매칭)
- 등급별 다중 선택 필터
- 효과 코드 자동 해석
- 강화 배수 계산

### 3. 아티팩트 탭 (Artifacts)
- 557개 아티팩트 데이터
- 100% 이미지 매칭
- 효과 코드 (419개) 자동 해석
- 유료 아티팩트 32개 검증 데이터
- New/Original 버전 구분

### 4. 용어 탭 (Glossary)
- 117개 용어 정의
- 5개 서브탭 분류
  - 등급 설명
  - 능력치 용어
  - 효과 설명
  - 아이템 유형
  - 기타

### 5. 건의게시판 (Suggestions)
- 게시글 작성 및 조회
- localStorage 기반 클라이언트 저장
- 평점/추천 시스템

---

## 데이터 파이프라인

```
APK (bwc1853_TEST_11.apk)
   ↓
bgdb_clean.bin (BGDatabase 바이너리, 2.7MB)
   ↓
extract_all.py (바이너리 파싱 + 효과 코드 해석)
   ↓
output/*.json (9개 구조화 JSON 파일)
   ├─ creatures.json (539 용병)
   ├─ equipment.json (533 장비)
   ├─ artifacts.json (557 아티팩트)
   ├─ commanders.json (35 지휘관)
   ├─ enemies.json (387 적)
   ├─ bosses.json (110 보스)
   ├─ stages.json (500 스테이지)
   ├─ random_merc_skills.json (265 랜덤용병 스킬)
   └─ scarecrow_invader.json (허수아비/침략자)
   ↓
build_*_data.py (이미지 매칭 + 웹 최적화)
   ↓
web/index.html (싱글페이지 SPA, 모든 JS/CSS/DATA 인라인)
   ↓
Vercel 자동 배포
```

### 효과 코드 시스템

| 파일 | 용도 | 개수 |
|------|------|------|
| `artifact_code_mapping.json` | 아티팩트 효과 코드 | 419개 |
| `enum_mappings.json` | 장비/스킬 효과 코드 | 61개 |
| `premium_effects.json` | 유료 아티팩트 검증 | 32개 |

효과값 포맷:
- `pct`: 퍼센트 (×100+%)
- `raw`: 배수
- `int`: 정수
- `abs`: 절대값

---

## 사용 방법

### 1. 데이터 추출 (바이너리 → JSON)

```bash
# 기본 실행
python3 extract_all.py

# 커스텀 경로 지정
python3 extract_all.py --bin /path/to/bgdb_clean.bin --out /path/to/output
```

필수 파일: `bgdb_clean.bin` (APK 내부)

### 2. 웹 데이터 빌드 (JSON → 인라인 HTML)

각 스크립트는 독립적으로 실행 가능합니다.

```bash
# 아티팩트 빌드 (icon 기반 이미지 매칭)
python3 build_artifact_data.py
# → web/data_artifacts.json + index.html ART_DATA 업데이트

# 장비 빌드
python3 build_equipment_data.py
# → web/data_equipment.json (icon 필드 사용)

# 지휘관 탭 빌드
python3 build_commander_tab.py
# → web/data_commanders.json + index.html 업데이트

# 허수아비/침략자 빌드
python3 build_scarecrow_invader.py
# → web/data_scarecrow_invader.json
```

### 3. 배포 (Vercel)

```bash
# 로컬 변경사항 커밋
git add web/
git commit -m "Update game data v.1853 TEST_11"

# GitHub 푸시 (Vercel 자동 배포)
git push origin master
```

> **배포 자동화**: `youngjaeshin/bbule-guide` GitHub 레포에서 master 브랜치 푸시 시 Vercel에서 자동 배포됩니다.

---

## 기술 스택

### Frontend
- **HTML5 + CSS3 + JavaScript** (순수 바닐라)
- **싱글페이지 애플리케이션 (SPA)**
- **반응형 디자인** (모바일/태블릿/데스크톱)
- **CSS 변수 기반 테마** (13개 그레이드 색상)

### Backend & Data
- **Python 3** (데이터 추출 및 처리)
- **바이너리 파싱** (BGDatabase 형식)
- **JSON** (구조화 데이터)

### Deployment
- **Vercel** (호스팅 및 CI/CD)
- **GitHub** (소스 코드 관리)

### UI/UX 특징
- 탭 기반 네비게이션
- 다중 필터링 (등급, 검색 범위)
- 텍스트 검색 (이름/효과)
- 그레이드별 색상 코딩
- 로컬 스토리지 기반 건의게시판

---

## 프로젝트 구조

```
bbule/
├── README.md                          # 이 파일
├── CLAUDE.md                          # Claude Code 프로젝트 가이드
│
├── extract_all.py                     # 핵심: APK 바이너리 → JSON 추출
├── bgdb_utils.py                      # 바이너리 파싱 유틸리티
│
├── build_artifact_data.py             # 아티팩트 웹 데이터 생성
├── build_equipment_data.py            # 장비 웹 데이터 생성
├── build_commander_tab.py             # 지휘관 탭 생성
├── build_scarecrow_invader.py         # 허수아비/침략자 탭 생성
│
├── artifact_code_mapping.json         # 아티팩트 효과 코드 (419개)
├── enum_mappings.json                 # 장비/스킬 효과 코드 (61개)
├── premium_effects.json               # 유료 아티팩트 검증 데이터 (32개)
│
├── web/
│   ├── index.html                     # 메인 싱글페이지 (~39,000줄)
│   ├── .gitignore
│   ├── data_mercenaries.json          # 539 용병
│   ├── data_equipment.json            # 533 장비
│   ├── data_commanders.json           # 35 지휘관
│   ├── data_subslot.json              # 보조슬롯
│   ├── data_stages.json               # 500 스테이지
│   ├── data_glossary.json             # 117 용어
│   ├── data_scarecrow_invader.json    # 허수아비/침략자
│   └── images/
│       ├── artifact/                  # 아티팩트 아이콘 (517개)
│       └── equip-icon/                # 장비 아이콘 (509개)
│
├── output/                            # extract_all.py 산출물 (임시)
│   ├── creatures.json
│   ├── equipment.json
│   ├── artifacts.json
│   └── ...
│
├── cafe_scraper/                      # 네이버 카페 스크래퍼 (선택)
│   └── pipeline.py
│
└── [기타 유틸리티 스크립트]
```

---

## 바이너리 파싱 규칙

> 주의: APK 바이너리 형식은 매우 구체적입니다. 데이터 추출 시 반드시 다음 규칙을 따릅니다.

### 필드 구조

```
[4B name_len][name][31B header][4B data_size][data][22B separator]
```

### 배열 형식 (중첩 배열)

```
[4B row_count][4B vals_per_row][row_count × vals_per_row × 4B data]
```

### 아티팩트 shift+1 규칙 (중요)

**artifact[i]의 aType과 aEffect는 row[i-1]에서 가져옵니다.**

```python
# 예: 557개 아티팩트
for i, art in enumerate(artifacts):
    if i == 0:
        continue  # 첫 번째는 스킵
    art['aType'] = art_type_rows[i - 1]
    art['aEffect'] = art_effect_rows[i - 1]
```

### 장비는 shift 없음

**equipment의 효과는 동일 인덱스에서 직접 읽습니다.**

```python
for i, equip in enumerate(equipment):
    equip['effect'] = effect_rows[i]
```

### 문자열 테이블 범위 (name_map 기준)

| 테이블 | 범위 | 개수 |
|--------|------|------|
| creatureBase | 0–538 | 539 |
| itemBase | 539–1858 | 1,320 |
| enemy | 1859–2245 | 387 |
| boss | 2246–2355 | 110 |
| stage | 2356–2855 | 500 |
| item/equip | 2856–3388 | 533 |
| commander | 3389–3423 | 35 |
| artifact | 3459–4015 | 557 |

---

## 이미지 매칭

### 아티팩트 (100% 매칭)

```
icon 필드 값 → web/images/artifact/{icon}.png
```

- 557개 중 37개는 New 버전이 원본과 icon 공유
- 아낙수나문 유료 4종(idx 505~508)은 icon=0 임시매핑

### 장비 (95.5% 매칭, 509/533)

```
icon 필드 값 → web/images/equip-icon/{icon:03d}.png
```

> **주의**: idx ≠ icon. 장비는 순서가 다르므로 반드시 icon 필드로 이미지 매칭합니다.

- 24개 누락: icon 139, 184, 185, 201, 282~306 (신규 장비)

---

## 웹 탭 상태

| 탭 | 데이터 소스 | 상태 |
|---|---|---|
| **용병** | `data_mercenaries.json` | Active ✓ |
| **장비** | `data_equipment.json` | Active ✓ |
| **아티팩트** | `ART_DATA` (인라인) | Active ✓ |
| **용어** | `data_glossary.json` | Active ✓ |
| **건의게시판** | localStorage | Active ✓ |
| 랜덤용병 | `RMSKILL_DATA` (인라인) | Disabled |
| 보조슬롯 | `data_subslot.json` | Disabled |
| 허수아비&침략자 | `data_scarecrow_invader.json` | Disabled |
| 지휘관 | `data_commanders.json` | Disabled |

---

## 개발 가이드

### 코드 스타일

- 한국어 주석 가능
- 변수명은 영어 (의미 명확한 이름)
- 물리량 변수명: `vp` (음파속도), `vph` (수평성분), `rho` (밀도) 등

### APK 업데이트 시

1. 새 APK에서 `bgdb_clean.bin` 추출
2. `python3 extract_all.py` 실행
3. `build_*_data.py` 스크립트 순차 실행
4. `web/index.html` 확인 및 배포

### 로컬 테스트

```bash
# 로컬 웹 서버 실행
python3 -m http.server 8000 --directory web

# 브라우저에서 접속
# http://localhost:8000
```

---

## 주의사항

### 데이터 정본

**APK 바이너리 (bgdb_clean.bin)가 정본입니다.**
엑셀 데이터는 구버전이므로 참고용으로만 사용합니다.

### 단일 파일 HTML

`web/index.html`은 약 39,000줄의 단일 파일입니다.
- 모든 JS/CSS/DATA가 인라인으로 포함됨
- 수정 시 라인 위치 주의
- 외부 의존성 없음

### 이미지 경로

아티팩트와 장비 이미지는 `web/images/` 디렉토리에 별도 저장됩니다.
- 추출 후 이미지 파일도 함께 복사 필요
- 누락된 이미지는 기본 아이콘으로 표시

---

## 피드백 및 기여

게임 가이드 개선 사항이 있으시면 웹 사이트의 **건의게시판**에서 제안할 수 있습니다.

소스 코드 기여는 GitHub 이슈 또는 풀 리퀘스트로 부탁드립니다.

---

## 라이선스

이 프로젝트는 교육 및 게임 커뮤니티 지원 목적입니다.
게임 "대용병시대 뿔레전쟁"의 저작권은 원개발사에 있습니다.

---

**Last Updated**: 2026-02-25
**Game Version**: v.1853 TEST_11
**Guide Version**: v0.2
