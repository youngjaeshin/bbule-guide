# 랜덤용병 스킬 캡처 대조

오른쪽 랜덤용병 스킬도감의 직접 캡처 값을 우선합니다. 왼쪽 장착·각성
스킬 값으로 대체하거나 일괄 1.3을 곱하거나 나누지 않습니다. 캡처에 없는
설명은 기존 APK 정보에서 유지합니다.

원본은 `output/random_skill_codex_capture/20261102_full`에 보존했습니다.
1~9등급 267개, 31개 페이지이며, 이름의 +/++와 모든 효과를 직접 판독했습니다.
검토 결정과 결과는 `output/random_skill_reconciliation/20261102`에 있습니다.

`random_skill_capture_overrides.json`에는 267개 스킬, 효과 462개, 계수·단위·
번호·조건·원본 해시·아이콘을 기록했습니다. 우르간의 방패는 원본의 + 하나를
사용하고 기존 index176과 옛 ++ 이름을 별칭으로 보존합니다. 별도 신규
스킬 누락은 없었습니다.

번호는 itemBase의 **mercenary_sec** 네임스페이스입니다. 기존 추측표에 섞인
장비·아티팩트 번호의 뜻을 재사용하지 않습니다. `random_merc_type_mapping.json`은
실사용 94개 sec의 뜻과 표시 형식을 기록합니다. 예를 들어 27은 모든 용병의
강타 배수이며, 추가 클릭 확률로 해석하지 않습니다.

성장·순수·신성 데미지의 절대값과 퍼센트를 실제 도감 단위대로 보존합니다.
불가 표시의 내부 음수는 -500%로 출력하지 않고 disable로 구분합니다.

죽음의 낙인은 첫 저장 프레임이 전투 이펙트에 가렸습니다. 같은 페이지의
보존된 0001.png에서 가려지지 않은 효과를 확인해 근거로 연결했습니다.
가려진 원본도 그대로 보존했습니다.

아이콘 267개를 source_id별로 원본에서 크롭해 `web/images/random_skill`에
저장했습니다. 기존 `web/images/skill`의 1,086개 파일은 바꾸지 않았습니다.
목록과 상세창의 큰 등급 숫자를 이미지로 교체하고 작은 등급 배지는 유지했습니다.

일반 재생성:

```sh
python3 regenerate_rmskills.py
```

검토 결정 파일을 수정했을 때만 먼저 실행:

```sh
python3 scripts/apply_reviewed_random_skill_captures.py
```

원본이 있는 작업 공간의 검증:

```sh
python3 scripts/verify_random_skill_capture_refresh.py
python3 scripts/reconcile_random_skill_captures.py
python3 verify_web_data_sync.py
```

전용 검증기는 전체 267개와 효과 462개, sec 번호·단위·부호·원본 해시,
267개 크롭의 픽셀 동일성, 기존 이미지 보존, RMSKILL_DATA 동기화와
다른 데이터 상수의 보존을 확인합니다.

기존 verify_web_data_sync.py는 장비·아티팩트 대상이므로 랜덤 스킬 전용
검사를 대신하지 않습니다. verify_enums.py는 과거 creatures[index]
스키마를 요구해 KeyError가 발생하는 별도 유틸입니다.
