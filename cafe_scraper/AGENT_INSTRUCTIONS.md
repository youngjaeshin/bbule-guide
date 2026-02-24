# 비전 에이전트 DPS 추출 지침서

## 개요
네이버 카페 "대용병시대 뿔레전쟁" 클리커 정산 게시판의 스크린샷에서 DPS 값을 읽는 작업.

## 파이프라인 순서

### 1. 데이터 수집 (pipeline.py fetch)
```bash
cd /Users/shin542/Desktop/Code/bbule/cafe_scraper
python pipeline.py fetch
```
- 네이버 카페 API로 글 목록 + 이미지 URL 수집
- 출력: `data/articles_all.json`

### 2. 이미지 크롭 (pipeline.py crop)
```bash
python pipeline.py crop
```
- 모든 이미지 다운로드 → `images/raw/`
- 상단 DPS 영역 크롭 + 4x 확대 → `images/dps_crops/`
- 크롭 설정: 상단 8%, 좌측 55%, 4배 확대

### 3. 비전 에이전트로 DPS 읽기

#### 에이전트 호출 방식
```
Task(
  subagent_type="oh-my-claudecode:vision",
  description="Read DPS bar: {article_ids}",
  prompt=VISION_PROMPT_TEMPLATE  # 아래 참조
)
```

#### 병렬 처리
- 2건씩 묶어서 비전 에이전트 호출
- 152건 → 76개 에이전트 (또는 3건씩 → ~50개)
- 5개씩 병렬로 총 ~15라운드

#### 비전 에이전트 프롬프트 (검증 완료)

```
You are reading CROPPED TOP BAR images from a mobile game "대용병시대 뿔레전쟁".
The crops show the HUD/status bar at the top of the screen.

## YOUR TASK
Read ALL values that have "DPS" in their label. Examples of labels you might see:
- 물리 DPS (Physical DPS)
- 마법 DPS (Magic DPS)
- 카오스 DPS (Chaos DPS)
- 공격 DPS (Attack DPS - combined total)
- 클릭 DPS (Click DPS)
- 즉시 공격 DPS (Instant Attack DPS)
- 신성 DPS (Holy DPS)
- 추가클릭 DPS (Additional Click DPS)
- 자동클릭 DPS (Auto Click DPS)
- Total DPS / 총 DPS

## RULES
1. Read EVERY image provided (img1, img2, img3)
2. Report the EXACT text shown, including Korean number units (만=10K, 억=100M, 조=1T, 경=10P)
3. If the DPS bar is NOT visible in an image, say "NO DPS BAR"
4. Pick the CLEAREST image with DPS values for your final answer
5. Do NOT read individual mercenary stats - only the TOP BAR HUD values

## IMAGES

Article {ARTICLE_ID} ({NICK}):
- {CROP_DIR}/{ARTICLE_ID}_img1_dps.png
- {CROP_DIR}/{ARTICLE_ID}_img2_dps.png
- {CROP_DIR}/{ARTICLE_ID}_img3_dps.png

## OUTPUT FORMAT (STRICT)
{ARTICLE_ID}:
  img1: [list all DPS labels and values, or "NO DPS BAR"]
  img2: [same]
  img3: [same]
  BEST: [label1=value1, label2=value2, ...] from img[N]
```

### 4. DPS 결과 취합

비전 에이전트 결과를 JSON으로 정리:
```json
[
  {
    "article_id": 140198,
    "dps_items": {
      "물리 DPS": "163,474",
      "마법 DPS": "187,906",
      "카오스 DPS": "185,650"
    }
  }
]
```

저장: `data/dps_readings.json`

### 5. 랭킹 생성
```bash
python pipeline.py rank --input data/dps_readings.json
```

## DPS 합산 규칙

**"DPS"라고 표시된 모든 값을 합산한다.**

포함:
- 물리 DPS, 마법 DPS, 카오스 DPS
- 공격 DPS, 즉시 공격 DPS, 신성 DPS
- 클릭 DPS, 추가클릭 DPS, 자동클릭 DPS
- Total DPS (이미 합산된 값인 경우 이것만 사용)

불포함:
- 클릭 기대값 (DPS가 아님)
- 클릭 크리티컬 (퍼센트)
- 소울 클릭 (퍼센트)

## 한국어 숫자 단위

| 단위 | 값 | 예시 |
|------|-----|------|
| 만 | 10,000 | 163만 = 1,630,000 |
| 억 | 100,000,000 | 5억 = 500,000,000 |
| 조 | 1,000,000,000,000 | 1조 = 1T |
| 경 | 10,000,000,000,000,000 | 1경 = 10P |

복합 표기: `14조 2273억` = 14,227,300,000,000

## 제목 메타데이터 형식

```
2월/닉네임/덱타입/색단/각성수(메인+서브1+서브2)/비고
```

필드:
- **닉네임**: 유저 닉네임
- **덱타입**: 잡덱, 즉공덱, 추클덱, 마법, 카오스, 크릴겐, 베멜덱, 트리니티 등
- **색단**: 없는색, 노랑, 빨강단, 보라단, 주황단, 입자, 검은색 등
- **각성수**: 총합(메인+서브1+서브2) - DPS가 아님!
- **비고**: 추가 메모 (엑시, 베멜H 등)

⚠️ 각성수 ≠ DPS. 각성수는 제목에서, DPS는 이미지에서 추출.

## 토큰 비용 추정

- 비전 에이전트 1회: ~45K 토큰 (이미지 3장 + 응답)
- 2건/에이전트 → 76회 호출 → ~3.4M 토큰
- 3건/에이전트 → ~51회 호출 → ~2.3M 토큰
