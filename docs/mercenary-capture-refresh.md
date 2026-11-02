# 용병 도감 캡처 대조

용병 스킬은 `mercenary_capture_overrides.json`의 검토된 캡처 정보를 먼저 적용하고, 나머지는 기존 APK 추출 경로를 따른다. 원본 바이너리나 과거 캡처를 수정하지 않는다. 효과 값은 APK 원시값이 아니라 **스킬 증가를 제외한 화면의 기본 계수**이며, APK 표시 배수를 다시 곱하지 않는다.

## 근거와 저장 위치

- 최초 원본: `output/mercenary_codex_capture/20261101` (556명).
- 증가 제외 확인본: `output/mercenary_codex_capture/20261102_unboosted_review`. 체크 해제 화면을 별도로 보존한다. 수집 중 자동 환생으로 화면이 어두워지면 기다린 뒤 촬영한다.
- 대조·검토 기록: `output/mercenary_reconciliation/20261102`. OCR 후보, 직접 확인한 결정, 보류 항목과 검증 결과를 구분한다. OCR 초안을 확정 데이터로 자동 승격하지 않는다.
- 게시용 크롭 명세: `mercenary_capture_portraits.json`. 원본 카드의 동일한 영역을 192×192로 만들고, 파일명·크롭 좌표·원본 및 결과 해시를 남긴다.

증가 포함 캡처는 체크 상태나 `+1`/`+2` 표시만으로 배율을 확정하지 않는다. 여러 효과의 역산 일치를 확인하며 쥬얼로 생기는 1.31, 1.33, 1.363 등의 배율도 별도로 기록한다. 가능하면 새 증가 제외 캡처를 우선한다. 빨간 불이익·금지·상한을 양수 효과와 함께 일괄 나누지 않는다. 특히 표시 간 차이가 있는 경우 실제 증가 제외 수치를 직접 확인하고 양쪽 원본을 보존한다.

## 스킬과 고용 패시브

`영구적으로`라는 문구와 파란색 수치로 표시되는 효과를 고용 패시브로 기록한다. 모든 슬롯을 확인한다. 스킬 설명에는 패시브 효과도 그대로 남기고, 용병의 `passives` 배열에도 같은 효과를 연결한다. 각 패시브에는 `source_slot`, 적용 조건, 수치와 근거를 저장한다. 예를 들어 자르는 1·2번 슬롯에서 패시브가 하나씩 나오며, P 프리츠의 패시브는 2번 슬롯에 있다.

시뮬레이터의 기존 `passive` / `passiveEffects` 필드는 예전 형식을 위한 **5번째 스킬 별칭**이다. 명확한 이름인 `fifthSkill` / `fifthSkillEffects`도 제공한다. 고용 패시브는 `passives` / `permanentEffects`에 따로 있고, 스킬 내 원문에 함께 표시되어도 전투 스킬 효과 배열에 중복 합산하지 않는다.

## 효과 코드

용병 `sec` 코드만 사용한다. 다른 도감의 번호를 재사용하지 않는다. 특정 개성·장비·지역·용병 수·리더·피해 타입 조건은 효과의 일부이다. 조건을 지운 일반 효과 번호로 연결하지 않는다.

공식 번호를 확인하지 못하면 `type_code: null`과 `effect_key`를 사용해 문구·계수·조건을 보존한다. 임의의 게임 번호는 만들지 않으며, 숫자 계산에서는 제외하고 `unmappedEffects`에 남긴다. 새 용병의 음수 `id`는 가이드용 식별자이고, 미확인 게임 ID는 `gameId: null`이다. `sec1178`은 실제 APK의 `쥬얼 효과 증폭`과 게임 화면을 함께 확인해 기존 번호로 연결했다.

## 재생성과 검증

일반 재빌드는 확정 레지스트리와 크롭 명세만 필요하다.

```sh
python3 build_mercenary_data.py
python3 build_simulator_data.py
python3 scripts/audit_mercenary_skill_refresh.py --strict --strict-unresolved --strict-ambiguous
python3 verify_web_data_sync.py
```

원본 캡처가 있는 작업 공간에서는 추가 검증을 수행한다.

```sh
python3 scripts/verify_mercenary_capture_refresh.py
python3 scripts/audit_mercenary_capture_alignment.py
```

검토 결정 파일을 수정했을 때만 다음 순서로 확정 레지스트리를 갱신한다. 일반 빌드는 OCR 대조표를 읽지 않는다.

```sh
python3 scripts/apply_reviewed_mercenary_captures.py
python3 scripts/apply_reviewed_mercenary_passives.py
python3 scripts/apply_unboosted_mercenary_confirmations.py
```

`verify_enums.py`는 오래된 루트 creature 구조로 종족·가문 등을 재구축하는 유틸이다. 현재 데이터에서는 `index` 필드가 없어 실패하므로, 이번 용병 효과 코드 및 캡처 검증에는 위 전용 검증기를 사용한다.

## 종료된 최종 검토

2026-11-02 최종 고정 목록 559개를 모두 처리했다. 기존 값 유지 533개,
수정 26개, 판단 보류 및 미처리 0개이다. 최초 자동 대조 2,221개와 이
추가 확인 목록을 구분한다. 별도 역방향 점검 10개도 원본을 읽어 기존
값을 확인했다. 세부 결과는 작업 폴더의 `최종검토결과.md`,
`final_review_decisions.json`, `review_progress.json`에 있다.

진행률은 `scripts/track_mercenary_review.py`로 고정 목록에 대해 집계한다.
`prepare_final_mercenary_review.py`는 기존 그룹 번호와 검토 근거를
덮어쓰지 않는다. 이 완료 목록을 새 자동 후보로 다시 확장하지 않는다.
공식 sec 번호 미확정 항목은 `effect_code_backlog.json`에 문구·조건·별도
식별자를 남겼다. X 알렉산드라의 영구 용병 슬롯 추가는 화면에 수량이
없으므로 수치를 추정하지 않고 원문과 `value: null`을 보존했다.
