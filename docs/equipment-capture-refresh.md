# 장비 도감 캡처 반영

2026-11-02 게임 화면에서 확보한 E~H 장비 544개를 기준으로 검증했다. `output/equipment_reconciliation/20261102/`에 고정 대조 목록, 원본 판독 기록, 수정 목록, 검증 결과를 저장한다.

## 원본과 재생성

- 원본: `output/item_codex_capture/20261102/index.json`과 원본 카드/페이지 PNG.
- 적용 자료: `equipment_capture_overrides.json`.
- 적용 함수: `equipment_capture_overrides.py`의 `apply_capture_overrides`.
- 장비 효과 번호 근거: `equipment_effect_metadata.json`.
- 재생성: `python3 scripts/rebuild_equipment_capture_data.py` 후 `python3 build_equipment_data.py`.
- 전체 APK 추출 시에도 `extract_all.py`에서 장비 캡처 보정을 적용한다.
- 검증: `python3 scripts/verify_equipment_capture_refresh.py`, `python3 verify_web_data_sync.py`.

캡처가 읽히면 캡처를 우선하고, 캡처로 확인할 수 없는 기존 정보는 기존 출처를 표시해 보존한다. 게임 번호를 알 수 없는 신규 3개는 가이드 내부 음수 ID를 사용하며 `gameIndex`, `mainType`은 null이다. 나중에 APK에 같은 등급·이름이 들어오면 새 항목을 중복 추가하지 않는다.

## 독립적인 강화 값

각 항목은 `effect_0_value`, `effect_20_value`, `coefficient_0`, `coefficient_20`, `effect_unit`과 `enhancement['0']`, `enhancement['20']`에 값을 독립 저장한다. 퍼센트의 표시 값과 계산용 계수는 구분한다.

0강은 화면 주효과에서 빨간 강화 증가량을 뺀 값이다. 예를 들어 낡은 단창은 216%-180%=36%이며, 20강은 216%이다. 전용 라꽈 1666%는 별도 효과로 저장한다.

20강 출처는 다음과 같이 구분한다.

- `screen`: 실제 +20 화면 186개.
- `calculated_from_screen_0`: 캡처로 확인한 0강 ×6으로 계산한 349개. +20 직접 촬영으로 취급하지 않는다.
- `legacy_non_enhanceable_flag`: 기존 자료의 강화 불가 9개. 캡처만으로 강화 불가가 새로 확인된 것은 아니다. 20강 수치는 null이다.

0~20의 모든 중간 단계 강화 공식을 검증한 작업은 아니다. UI의 `equipMainValue`는 0강·20강과 캡처에 직접 나타난 단계 값을 우선 사용하며, 그 밖의 단계는 기존 근사식을 유지한다. 별도 승급 화면이 없는 S→G 미리보기 29개는 기존 값을 그대로 보존하고 `gUpgradeSource`로 구분했다.

## 전용 효과와 효과 번호

`specializedHeroes`는 화면에 나타난 대표 용병 이름과 정확한 퍼센트를 저장한다. 전용 표기 장비는 347개다. 진화형 등을 포함한 기존 APK 적용 대상 ID는 원본 `specializedHero`와 웹의 `legacySpecializedTargets`에 따로 보존했다. 대표 이름만 보인다는 이유로 진화형 적용 ID를 삭제하지 않는다.

장비 `mainType` 93종은 장비 스크린샷 근거로 확인했다. 용병 `sec`와 아티팩트 `aType`은 별개다. 신규 3개의 공식 번호는 미확인이므로 번호를 추정해서 채우지 않는다. 신규 3개는 같은 효과의 명시적 문자열 키를 사용한다.

## 이미지

기존 실제 연결 이미지 533개를 원본과 대조했다. 기존 PNG 1,447개는 모두 SHA-256 동일성을 확인해 보존했다. 이미지가 없던 기존 8개와 신규 3개만 원본 카드에서 크롭했다. 새 11개는 원본 좌표 `[2,1,82,75]`의 80×74 픽셀을 그대로 사용한다. 출처와 해시는 `portrait_additions.json`에 기록했다.

웹에서는 `image` 경로를 우선한다. 기존 `portrait`가 비어 있어도 `equip-icon` 이미지가 있으면 이미지 누락으로 분류하지 않는다. 목록, 상세, 시뮬레이터 장비 선택이 같은 경로 함수를 사용한다.
