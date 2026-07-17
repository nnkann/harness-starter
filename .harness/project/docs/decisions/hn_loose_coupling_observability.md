---
title: 느슨한 결합 관측 지표 전수 감사 계획
domain: harness
c: "FR-011 처리 중 단일 카운트 기반 권고와 starter/downstream fixture drift가 연속 발견됨"
problem: [P7, P9, P11]
s: [S7, S9, S11]
tags: [observability, eval, downstream, drift, audit]
status: completed
created: 2026-05-20
updated: 2026-05-20
relates-to:
  - path: incidents/hn_downstream_pytest_fixture_leak.md
    rel: caused-by
  - path: decisions/hn_pytest_regression_routing.md
    rel: references
  - path: decisions/hn_verify_relates_precheck.md
    rel: references
---

# 느슨한 결합 관측 지표 전수 감사 계획

## 배경

v0.51.6과 v0.51.7에서 자잘해 보이던 버그가 연속으로 드러났다.

- 다운스트림 `harness-upgrade` 뒤 starter 테스트가 다운스트림 `is_starter: false`
  정책과 프로젝트별 CPS 문서 형식을 물려받아 false failure를 냈다.
- `eval --harness` CPS 무결성 항목이 `problem:` primary 인용 0건만으로 장기
  Problem 폐기·병합 권고를 강하게 해석할 수 있었다.
- `write-doc`/`implementation` 문서가 한때 WIP 라우팅 태그 폐기를 말했지만,
  `docs_ops.py move`는 `incidents--` 같은 접두사를 요구했다. 이번 작업에서
  스킬 문서를 도구 계약에 맞췄다.

공통점은 단일 파일 버그가 아니라, 느슨하게 결합된 관측 지표와 문서 규칙이 서로
다른 SSOT를 보고 있다는 점이다. 지금 전수 조사하지 않으면 나중에는 다운스트림
환경·장기 WIP·warn-only 정책 안에서 재발해도 발견되기 어렵다.

## CPS Rationale

- C → P: 관측 지표가 단일 카운트나 현재 repo 상태만 보고 결론을 내리면 P9 정보
  오염이 생긴다. 정책의 실제 소유 위치와 출력 계약이 흐려지는 것은 P7이며,
  같은 형태의 drift가 여러 파일에 잠복하는 것은 P11이다.
- P → S: S7은 지표 출력의 의미와 소유권을 드러내고, S9는 단일 신호를 판단
  baseline으로 쓰지 않게 하며, S11은 동형 후보 위치를 전수 탐색하게 한다.
- S → AC: AC는 grep 기반 전수 목록, 분류표, 보강 테스트, 주기 관찰 항목 추가로
  위 세 Solution이 실제로 작동하는지 증명한다.

## 범위

감사 대상:

- `.claude/scripts/eval_*.py`
- `.claude/scripts/pre_commit_check.py`
- `.claude/scripts/docs_ops.py`
- `.claude/skills/harness-upgrade/SKILL.md`
- `.claude/skills/write-doc/SKILL.md`
- `.claude/skills/implementation/SKILL.md`
- `.claude/skills/commit/SKILL.md`
- 관련 테스트: `.claude/scripts/tests/test_*.py`

검색 키워드:

- `0건`, `폐기`, `병합`, `권고`, `정체`, `warn-only`
- `is_starter`, `downstream`, `starter`
- `problem`, `s`, `solution-ref`
- `docs/WIP`, `project_kickoff`, `MIGRATIONS`, `migration-log`

## 감사 분류

각 발견 항목은 아래 네 부류 중 하나로 분류한다.

| 분류 | 의미 | 처리 |
|------|------|------|
| 단일 지표 결론 | 하나의 count/status만 보고 폐기·정체·성공을 말함 | 보조 신호와 조건 추가 |
| 환경 분기 누락 | starter/downstream 또는 local/upstream 상태를 fixture가 암묵 상속 | fixture에서 명시 고정 |
| 문서-도구 drift | 규칙 문서와 실제 스크립트 요구사항 불일치 | SSOT 결정 후 한쪽 갱신 |
| 주기 관찰 부재 | 지금은 통과하지만 장기 drift 감지 지점 없음 | `eval --harness` 관찰 항목 추가 |
| 토큰 다이어트 | 같은 검증·스캔·라우팅이 의미 없이 반복됨 | batch 처리 또는 관찰 후보 출력 |

## Acceptance Criteria

- [x] Goal: S7·S9·S11 — 느슨한 결합 관측 지표가 단일 신호로 오판하지 않도록 전수
  감사하고, 주기 관찰 지점을 남긴다.
  검증:
    review: self
    tests: 타깃 pytest만 기본. 전체 pytest는 이미 1회 실측 완료했으며 반복 실행 금지
    실측: 201 passed, 4 skipped; `verify-relates` 0건; `pre_commit_check.py` pass
- [x] `eval/pre-check/docs_ops/harness-upgrade`의 권고·폐기·0건·warn-only 출력 전수
  목록을 작성한다.
- [x] 각 출력이 참조하는 SSOT와 보조 신호 유무를 표로 분류한다.
- [x] 단일 지표 결론 1건 이상 발견 시, 보조 신호 또는 문구 완화를 적용하고
  회귀 테스트를 추가한다.
- [x] starter/downstream 분기 테스트가 현재 repo 상태를 암묵 상속하는지 확인하고,
  필요한 fixture를 명시 모드로 고정한다.
- [x] `write-doc`/`implementation`의 WIP 파일명 규칙과 `docs_ops.py move` 요구사항
  drift를 결정한다.
- [x] 문서 생성 요청이더라도 코드·테스트 감사/개선을 앞둔 계획 문서는
  `implementation`으로 라우팅하도록 스킬 진입 조건을 보강한다.
- [x] Gemini 외부 검토에서 제안된 테스트 매트릭스를 반영해 각 케이스의 fixture,
  기대 결과, false positive/false negative 위험을 명시한다.
- [x] `eval --harness`에 주기 관찰 항목을 추가하거나, 추가하지 않는다면 이유를
  본문에 남긴다.
- [x] 불필요한 반복 실행·복잡한 라우팅·중복 스캔 후보를 확인하고, 즉시 줄일 수
  있는 항목은 반영한다.
- [x] 검증 자체의 반복 비용을 점검하고, 전체 스위트 반복 실행을 피하는 기준을
  implementation 스킬에 남긴다.
- [x] CPS P#↔S# 결합도를 확인하고, orphan Problem·unmapped Solution·dangling P#
  상태가 `eval --harness`에서 보이도록 한다.
- [x] 오류·미흡 발견이 C 보강/회귀 후보로 이어지는지 확인하고, silent exception이
  조용히 묻히지 않도록 `eval --harness` 관측 항목을 추가한다.

## 조사 로그

작성 시점에 이미 확인된 후보:

- `eval_cps_integrity.py`: FR-011로 1차 보강 완료. 다른 `0건` 출력도 같은 기준으로
  재검토 필요.
- `docs_ops.py move`: WIP 이동 시 `{폴더}--` 접두사를 요구한다.
- `write-doc`·`implementation`·`commit`: `{대상폴더}--{abbr}_{slug}.md` 계약으로
  보정했다.
- `pre_commit_check.py`: `is_starter`에 따라 dead reference와 `relates-to`를 차단
  또는 warn-only 처리한다.
- `write-doc` vs `implementation`: 본 WIP 생성 시 "계획 문서부터"라는 발화를
  write-doc으로 처리했으나, 실제로는 코드·테스트 감사의 시작점이라
  implementation 라우팅이 맞다는 사용자 피드백이 있었다.

## 전수 목록 + SSOT 분류

| 대상 | 관측 출력·동작 | SSOT | 보조 신호 | 조치 |
|------|----------------|------|-----------|------|
| `eval_cps_integrity.py` | `primary 인용 0건 Problem`, 폐기·병합 권고 | `docs/guides/project_kickoff.md` CPS | related `S#`, `solution-ref`/`s`, WIP 언급 | 단일 `problem:` 카운트 결론 금지, 메타 테스트 추가 |
| `pre_commit_check.py` | `relates-to` 미연결 차단/warn-only | `.claude/HARNESS.json` `is_starter` + `docs_ops.py verify-relates` | starter/downstream fixture | downstream docs/rules warn-only 테스트 추가, cleanup `finally` 보강 |
| `docs_ops.py wip-sync` | 자동 WIP 매칭·이동, `cluster-update` | `.claude/rules/naming.md`, WIP frontmatter `problem` | staged abbr, staged WIP `problem`, 완료 체크박스 | WIP glob 1회 재사용, cluster-update batch 1회 |
| `docs_ops.py move` | `{대상폴더}--` 접두사 요구 | `.claude/rules/naming.md` "파일명 — WIP" | 스킬 문서 계약 테스트 | `implementation`·`write-doc`·`commit` 문서 보정 |
| `implementation`/`write-doc` | "먼저 계획 문서" 라우팅 | 각 `SKILL.md` trigger/skip | 후속 코드·테스트·스크립트 변경 의도 | implementation 라우팅으로 고정, 계약 테스트 추가 |
| `eval_harness.py` | 느슨한 결합·토큰 다이어트 관측 | `eval --harness` CLI 백엔드 | drift hit, 반복 스캔 횟수 | 별도 섹션으로 주기 출력 |
| `harness-upgrade` | downstream이 upstream starter 테스트/정책을 물려받는 상황 | `.claude/HARNESS.json`, upgrade 후 downstream 실행 맥락 | `is_starter: false`, 다운스트림 CPS 형식 | upstream 테스트 fixture가 환경을 명시 고정하도록 보강 |
| CPS P↔S 결합도 | P#에 S#가 없거나 S#가 없는 P#를 가리키는 상태 | `project_kickoff.md` Problems/Solutions 표 | 굵은 P10/S10 표기, orphan/unmapped/dangling 분리 | `eval_cps_integrity.py`에 결합도 섹션 추가 |
| C 보강·회귀 루프 | 오류·미흡이 C 재정의나 회귀 후보로 드러나지 않음 | WIP `c:` 또는 `## CPS Rationale`, `.claude/scripts/*.py` 예외 처리 | C 신호 누락, `except Exception: pass/continue` | `eval_harness.py`에 관측 섹션 추가 |

## 외부 검토: Gemini

2026-05-20에 Gemini CLI를 읽기 전용 plan 모드로 호출해 테스트 설계 조언을 받았다.
핵심 권고는 다음과 같다.

| 영역 | 보강 테스트 | Fixture | 기대 결과 | 위험 |
|------|-------------|---------|-----------|------|
| 환경 분기 | relates-to starter/downstream 분리 | `is_starter: true/false`를 명시한 임시 HARNESS | starter는 차단, downstream은 warn-only | 다운스트림 정상 변경 차단 또는 starter 제약 누락 |
| 문서 형태 | CPS table/body 양쪽 파싱 | starter 표형 CPS와 StageLink 본문형 CPS | 표가 없어도 다운스트림 문서가 fixture 손상으로 오판되지 않음 | 프로젝트별 CPS를 레거시 파서가 실패 처리 |
| 보조 신호 | Problem primary 0 + Solution/WIP 신호 | `problem:` 0건, `solution-ref` 또는 `s` 1건, WIP 언급 | 강한 폐기 권고 대신 보류·경계 재정의 문구 | 장기 Problem 조기 폐기 권고 |
| 라우팅 | 계획 문서 뒤 코드 작업 의도 | "먼저 계획 문서, 이후 테스트 보강" 발화 예시 | `implementation` 라우팅 | `write-doc` 키워드 과매칭 |
| 문서-도구 drift | `docs_ops.py move`와 스킬 파일명 규칙 비교 | 접두사 없는 WIP명과 현재 스킬 문서 | 요구사항 불일치 시 실패 | 문서는 가능하다고 하나 도구가 차단 |

추가 메타 테스트 아이디어:

- Signal Mute & Assertion Analysis: primary count를 0으로 고정하고 secondary signal만
  남긴 fixture에서 결과가 `drop/delete`류의 파괴적 결론으로 가지 않는지 검증한다.
- 다운스트림 fixture는 `tests/fixtures/starter/`, `tests/fixtures/downstream/`로
  물리 분리하고, pytest marker 또는 전용 tmp_path 복사로 실제 repo 상태를 상속하지
  않게 한다.

## 결정 사항

- 라우팅 결정: 코드·테스트·스크립트·룰 개선을 앞둔 "먼저 계획 문서" 요청은
  `implementation`으로 라우팅한다. 반영 위치:
  `.claude/skills/implementation/SKILL.md`, `.claude/skills/write-doc/SKILL.md`,
  `.claude/scripts/tests/test_skill_routing_contract.py`.
- WIP 파일명 결정: 현재 SSOT는 `docs_ops.py move`의 `{대상폴더}--{abbr}_{slug}.md`
  요구사항이다. `implementation`·`write-doc`·`commit` 스킬 문서를 이 계약에
  맞췄고, 라우팅 계약 테스트로 drift를 차단한다.
- 테스트 보강:
  - `test_eval_harness.py`: primary problem 인용을 0으로 mute하고 `s: [S#]`
    보조 신호만 남기는 메타 테스트 추가.
  - `test_pre_commit.py`: downstream `docs/` broken `relates-to` warn-only
    테스트 추가, downstream fixture cleanup을 `finally`로 보강.
  - `test_skill_routing_contract.py`: 계획 문서 라우팅과 WIP 파일명 계약 테스트 추가.
- 주기 관찰: `eval_harness.py`에 `## 느슨한 결합 관측` 섹션을 추가해 스킬 라우팅과
  WIP 파일명 계약 drift를 정기 출력한다.
- CPS 결합도: `eval_cps_integrity.py`에 `### CPS P↔S 결합도`를 추가했다.
  현재 `Problem→Solution coverage: 100%`, `Solution→Problem mapping: 100%`다.
  굵은 표기된 `**P10**`/`**S10**`도 파싱하도록 보강했다.
- C 보강·회귀 루프: `eval_harness.py`에 `## C 보강·회귀 루프 관측`을 추가했다.
  현재 WIP C 신호 누락은 0건이지만, silent exception 후보는 25건으로 드러났다.
  이는 “에러가 조용히 씹힐 수 있다”는 사용자 지적이 실제 위험 신호였음을 의미한다.
  이번 범위에서는 먼저 관측을 결정화했고, 다음 조치는 후보별 intentional skip과
  진짜 swallow를 분류해 warning/return reason으로 바꾸는 것이다.
- CPS 반영: silent exception과 C 보강 루프는 신규 P#/S#가 아니라 P6·P7·P9의
  교차 사례로 판단했다. `project_kickoff.md`의 S6·S7·S9 해결 기준에
  silent exception, skip/warn/pass 의미, 타깃 테스트 기준을 반영했다.
- 토큰 다이어트:
  - `docs_ops.py wip-sync`는 여러 WIP를 자동 이동할 때마다 `cluster-update`를
    반복 실행할 수 있었다. 이동 루프 뒤 1회 batch 실행으로 줄였다.
  - `docs_ops.py wip-sync`는 abbr 매칭 준비와 fallback 후보 선정에서 WIP 목록을
    각각 glob할 수 있었다. WIP 목록을 한 번만 만들고 재사용하도록 줄였다.
  - `eval_cps_integrity.py`는 `docs/` 전체를 main scan, Solution ref count,
    WIP signal count로 나눠 훑고 있었다. main scan에서 `solution-ref`/`s`
    카운트까지 함께 누적하도록 바꿔 docs 전체 스캔을 2회에서 1회로 줄였다.
    WIP signal count는 `docs/WIP` 좁은 범위라 별도 유지한다.
  - `write-doc`/`implementation` 라우팅은 계획 문서 뒤 코드·테스트 작업이면
    `implementation`으로 정리해 route 왕복을 줄였다.
  - 검증 루프도 다이어트 대상이다. 이번 작업 중 같은 논리 배치에서 전체 스위트를
    반복 실행한 것은 과했다. `implementation` Step 5와 `eval` 스킬에 "pytest
    기본값은 단일 파일·test id·좁은 marker, 전체 스위트는 사용자 명시 또는
    릴리즈/커밋 직전 고위험 공유 코어 변경의 최종 1회" 원칙을 추가했다.

## 실측

- `python -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q`
  → 2 passed
- `python -m pytest .claude/scripts/tests/test_eval_harness.py -q -m eval`
  → 29 passed
- `python -m pytest .claude/scripts/tests/test_pre_commit.py -q -m docs_ops`
  → 33 passed, 80 deselected
- `python -m pytest .claude/scripts/tests/ -q`
  → 201 passed, 4 skipped
- `python .claude/scripts/eval_harness.py`
  → `스킬 라우팅·WIP 파일명 계약 drift 0건 ✅`,
  `eval_cps_integrity docs 전체 스캔: 1회`,
  `docs_ops wip-sync WIP glob: 1회`,
  `남은 후보 0건 ✅`
- `python -m pytest .claude/scripts/tests/test_docs_ops_staging.py -q`
  → 4 passed
- `python -m pytest .claude/scripts/tests/test_eval_harness.py::test_solution_problem_map_from_kickoff_table .claude/scripts/tests/test_eval_harness.py::test_cps_solution_coupling_detects_orphan_and_dangling -q`
  → 2 passed
- `python .claude/scripts/eval_harness.py`
  → `CPS P↔S 결합도`: `Problem→Solution coverage: 100% ✅`,
  `Solution→Problem mapping: 100% ✅`
- `python -m pytest .claude/scripts/tests/test_eval_harness.py::test_c_reinforcement_observability_detects_missing_c_and_silent_exception -q`
  → 1 passed
- `python .claude/scripts/eval_harness.py`
  → `WIP C 신호 누락 0건 ✅`, `silent exception 후보 25건`
- `python .claude/scripts/safe_command.py verify-relates`
  → 미연결 relates-to 0건
- `python .claude/scripts/pre_commit_check.py`
  → pre_check_passed: true

## 결정 결과

- `eval --harness` 관찰 항목은 기존 CPS 무결성 항목 안에 섞지 않고 별도 섹션으로 둔다.
  이유: CPS 판단과 라우팅·토큰 다이어트 관측은 소유 신호가 달라, 한 섹션에 섞으면
  다시 단일 지표 오판이 생길 수 있다.
- 다운스트림 feedback report 자동 추적 필드는 이번 범위에서 추가하지 않는다.
  이유: `migration-log.md`는 다운스트림 전용이고, upstream은 `FR-011`처럼 반영 시
  테스트·WIP 기록으로 승격하는 흐름이 더 명확하다.
