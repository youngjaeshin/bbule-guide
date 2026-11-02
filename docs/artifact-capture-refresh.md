# 아티팩트 캡처 대조와 재생성

효과 출처 우선순위는 읽을 수 있는 직접 캡처, 기존 정보, 미확인 순서다.
미획득 `????` 화면은 이름과 미획득 상태만 증명한다. 그 화면으로 기존
효과를 지우거나 확인됐다고 표시하지 않는다. 유료 아낙수나문 상점 캡처는
이미지 근거이며, 그 화면에 없는 효과는 기존 자료를 유지한다.

`output/artifact_codex_capture/20261102_full`의 원본525개 중 효과가 보이는
464개·1,459줄을 검토했다. 검토 결정과 최초 비교표는
`output/artifact_reconciliation/20261102`에 있다. 배율 역산은 사용하지 않는다.
쥬라식 스톤의 가이드 계수는 사용자가 지정한20%를 사용한다.

아티팩트 효과는 `artifact_code_mapping.json` 및
`artifact_effect_metadata.json`의 **artifact aType** 네임스페이스를 따른다.
검증된452개 번호의 전체 효과 이름, 조건, 표시 형식, 캡처 근거를 기록했다.
장비mainType이나 용병sec의 같은 숫자를 가져오지 않는다.
세트 완성·아티팩트 장착·개성·종족·지역·성별·종교·가문·용병·데미지 타입
조건은 일반 아티팩트aType의 의미이며, 일반 능력치 번호로 대체하지 않는다.

`artifact_overrides.json`은 개별 수치·슬롯 교정과 실제 누락 효과에만 쓴다.
한 줄에 두 효과가 있는 다섯 사례는 각 능력치의 검증된 아티팩트 번호와
`source_slot`/`source_component`로 연결해 둘 다 보존했다.
H New미개한 엑스반도의 최종 데미지는 개별 슬롯을54로 교정했으며,
전역19(모든 용병의 연타 확률)의 뜻을 바꾸지 않았다.

`artifact_capture_manifest.json`은 출처·이름 별칭·이미지를 담당한다.
여포 갑옷/투구는 기존 뤼부 항목의 ID를 유지하며 기존 이름을 별칭으로 남긴다.
기존 정보가 없는 Q4개는 가이드용 음수index를 사용하고
`gameIndex: null`, 빈 효과 목록을 보존한다. 게임 번호나 효과를 추정하지 않는다.

기존 이미지1,309개는 바꾸지 않았다. 아낙수나문4종의517~520.png만 원본
크기로 크롭했다. 이름 이미지가 없어도 기존 번호 이미지가 있으면 재사용한다.
신규 미획득Q4종은 실루엣만 있으므로 실제 이미지가 없는 상태로 남겼다.

일반 재생성:

```sh
python3 scripts/rebuild_artifact_capture_data.py
python3 build_artifact_data.py
python3 verify_web_data_sync.py
```

전체APK 갱신의 `extract_artifacts()`도 같은 아티팩트 전용 해석기와
확정 메타데이터를 적용한다. 캡처 결정 자체를 바꿀 때만
`scripts/apply_reviewed_artifact_captures.py`를 먼저 실행한다.

원본을 가진 작업 공간의 검증:

```sh
python3 scripts/verify_artifact_capture_refresh.py
python3 scripts/reconcile_artifact_captures.py
```

전용 검증기는1,459줄의 효과·수치·단위·조건·번호, 원본 해시,
기존 이미지 보존, 크롭의 픽셀 동일성, 타 데이터 상수 보존을 확인한다.
기존 `verify_enums.py`는 루트creatures의 과거index 스키마를 요구해
`KeyError: index`로 실패한다. 이 도구로 아티팩트aType을 검증하지 않는다.

시뮬레이터의 조건 평가가 지원되지 않는 조건부 효과와 수식은 구조화해
보존하고, 무조건 적용되는 능력치로 합산하지 않는다.

## 2026-11-02 카페 이미지 보완

사용자가 제공한 별도 게임 사진은 `community_screenshot` 출처로 구분한다. 직접 촬영한 게임 캡처와 합치지 않는다. `output/artifact_option_inference/20261102/`에 원본, 색상 관측, 적용 전 기준 및 검증을 보관한다.

최상 기준은 에메랄드·도감의100%이다. 효과명 색의 순서는 에메랄드100%, 분홍95%, 검정90%, 주황85%, 보라80%, 빨강75%, 노랑70%, 파랑65%, 녹색60%, 흰색55%로 기록했다. 녹색 숫자와 조건문의 고정색은 판정 대상이 아니다. 상급 P 옵션은 제외한다. 아너드 랜스4.41은 사용자 확인에 따라 P 옵션으로 분류했고, 도감4.2를 유지한다. 이 사례를 노랑70%로 잘못 읽었던 분석은 폐기했다.

누락 Q4종에 효과21개와 이미지4개를 추가했다. 볼보레타·슬레이어는 `community_color_inferred`, 머미 캣·템페스트는 `community_codex_verified`로 표시한다. 세라핌 숄더 패드의 조건부3040/3041은 사용자 제공 도감에 따라4.8%/6%로 교정했다. 기존 아티팩트11종에는 추가 사진의 검증 근거를 연결했다. 보조 옵션과 P 옵션의 상한은 가이드 기준에 포함하지 않는다.

신규4종은 기존 가이드 식별자를 유지하며 공식 게임 ID와 세트 ID를 추정하지 않는다. 기존 장비·용병 번호를 가져오지 않는다. 공식 aType이 없는 효과9종은 `artifact_guide_effect` 네임스페이스의 음수 번호로 구분했다. 이 번호는 게임 공식 aType이 아니다. 조건과 공식은 효과 설명과 별도로 보존한다.

재생성은 기존과 같이 `python3 scripts/rebuild_artifact_capture_data.py`, `python3 build_artifact_data.py`이다. 추가 자료는 루트 매니페스트·오버라이드·메타데이터에 저장되어 재생성 시 유지된다. 추가 검증은 `python3 scripts/verify_community_artifact_sources.py`로 실행한다. 과거 작업의 고정 대상 검사 결과를 새로운 작업의 완료 결과로 덮어쓰지 않는다.
