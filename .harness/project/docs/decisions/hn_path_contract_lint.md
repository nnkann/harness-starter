---
title: path contract lint + 검증 도구 가용성 게이트
domain: harness
c: "LSP/정적검사가 작동했다면 코드 경로 drift는 자주 잡혀야 하는데, 최근 하네스·다운스트림에서 사람의 rg 사후 발견에 의존했다."
problem: [P6, P11]
s: [S6, S11]
tags: [lint, lsp, path-contract, pre-check, drift]
relates-to:
  - path: decisions/hn_eval_harness_cli_lsp_drift.md
    rel: extends
  - path: decisions/hn_dead_ref_p11_first_case.md
    rel: references
  - path: decisions/hn_code_ssot_rule.md
    rel: references
status: completed
created: 2026-05-21
updated: 2026-05-21
---

# path contract lint + 검증 도구 가용성 게이트

## 문제

이번 reminder memory 작업에서 `.claude/memory/reminders/` 구조를 만들었지만
README 구조도, MIGRATIONS frontmatter, `CLAUDE.md`/`AGENTS.md`, `.claude`와
`.agents` skill mirror, `downstream-readiness.sh`의 낡은 hook·memory 경로가
여러 번 뒤늦게 발견됐다.

이 결함은 두 종류가 섞여 있다.

1. **코드/LSP 영역**: import, 함수명, 타입, 미사용 정의, shell syntax.
2. **문자열 계약 영역**: 문서·스킬·스크립트 안의 경로 문자열
   (`session-start.sh`, `signal_defense_success.md`, `.claude/memory/reminder_*.md`).

LSP는 2번을 안정적으로 잡지 못한다. 반대로 1번은 LSP·linter가 더 자주 잡아야
정상인데, 현재 starter 환경에서는 `ruff`, `pyright`, `mypy`, `shellcheck`가 모두
없어 pre-check가 조용히 약해진다.

## CPS Rationale

- C -> P: 검증 도구 부재와 path string drift가 완료 후 사용자 지적으로 발견됐다.
  이는 P6(검증 책임 우회)와 P11(동형 패턴 잠복)에 동시에 걸린다.
- P -> S: S6은 도구 실종·자동 검증 불가를 완료 증거로 포장하지 않게 만들고,
  S11은 첫 발견 시 동형 후보 위치를 자동 탐색하게 만든다.
- S -> AC: AC는 도구 가용성 보고와 path contract lint가 pre-check/eval/readiness
  중 어느 층에서 동작할지 결정하고, 회귀 테스트로 고정해야 한다.

## 기존 자산

- `docs/decisions/hn_eval_harness_cli_lsp_drift.md`
  - 이미 검증 도구가 `src`를 보도록 정렬하는 진단을 다룬다.
  - 하지만 "도구가 설치되어 있는가"와 "문자열 경로 계약이 실제 파일과 맞는가"는
    별도 축이다.
- `docs/decisions/hn_dead_ref_p11_first_case.md`
  - 폐기 파일명 패턴을 hardcoded dead reference로 잡는 선례.
  - 현재 `_DEAD_REF_PATTERNS`는 등록된 폐기 패턴만 잡으므로 살아있는 경로 계약
    전수 검사는 아니다.
- `.claude/scripts/downstream-readiness.sh`
  - 다운스트림 적용 누락 진단 채널.
  - 현재는 특정 hook·stdout·review 카테고리 몇 개를 정적으로 grep한다.

## 결정 방향

### 1. LSP/linter 가용성은 skip이 아니라 관측한다

도구가 없을 수는 있다. 하지만 없으면 "검증했다"가 아니라 "해당 방어선 없음"으로
보고해야 한다.

후보 출력:

```text
tool_availability:
  ruff: missing
  pyright: missing
  mypy: missing
  shellcheck: missing
```

starter 기본값은 설치 강제하지 않는다. 대신 `eval --harness`와
`downstream-readiness.sh`가 도구 부재를 명시하고, pre-check는 변경 범위에 따라
최소 내장 검사를 수행한다.

### 2. 기본 내장 검사는 의존성 없이 실행한다

외부 도구 없이도 실행 가능한 검사는 pre-check에 넣을 수 있다.

- staged `.py`가 있으면 `python -m py_compile <staged py>`
- staged `.sh`가 있으면 `bash -n <staged sh>`
- staged 하네스 문서·스킬·루트 지침이 있으면 path contract lint

### 3. path contract lint는 LSP와 별도다

문자열 경로를 추출해 실제 파일 존재 여부 또는 legacy 허용 여부와 대조한다.

대상:

- `CLAUDE.md`, `AGENTS.md`, `README.md`
- `.claude/rules/**/*.md`
- `.claude/skills/**/*.md`, `.agents/skills/**/*.md`
- `.claude/scripts/**/*.{py,sh}`
- `docs/harness/MIGRATIONS.md`

초기 검사 대상 패턴:

- `.claude/scripts/<name>.py|.sh`
- `.claude/memory/<name>.md`
- `.claude/memory/reminders/<name>.md`
- `docs/<folder>/<name>.md`

예외:

- `docs/harness/MIGRATIONS-archive.md`, completed decisions/incidents 안의 역사 설명
- "legacy", "폐기", "archive", "마이그레이션", "이전" 같은 박제 표현이 같은 줄에
  있는 경우
- 명시 허용 fallback: 루트 `.claude/memory/reminder_*.md`, `.claude/memory/signal_*.md`

### 4. 게이트 배치

| 층 | 역할 |
|----|------|
| pre-check | staged 파일에 한정한 결정적 차단. 새 stale path를 만들면 차단 |
| eval --harness | repo 전체 보고. archive/history 면제와 false positive 튜닝 |
| downstream-readiness | 다운스트림 설치/업그레이드 후 핵심 hook·도구 가용성 요약 |

**Acceptance Criteria**:

- [x] Goal: S6 기준으로 LSP/linter 도구 부재가 "검증 완료"로 오인되지 않게
  `eval --harness` 또는 `downstream-readiness.sh`에 tool availability 보고를 추가한다.
  검증:
    review: self
    tests: `bash .claude/scripts/downstream-readiness.sh`
    실측: 현재 환경에서 `ruff`·`pyright`·`mypy`·`shellcheck` 중 없는 도구가 skip이 아니라 관측 값으로 출력된다.
- [x] Goal: S6 기준으로 staged Python/Shell 변경에 대해 의존성 없는 syntax 검사를 pre-check에 추가한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_pre_commit.py -q`
    실측: staged `.py` 문법 오류와 staged `.sh` 문법 오류 fixture가 pre-check exit 2로 차단된다.
- [x] Goal: S11 기준으로 path contract lint를 추가해 하네스 경로 문자열 drift의 동형 후보를 자동 탐색한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_eval_harness.py -q`
    실측: `session-start.sh` 같은 현재 부재 경로가 살아있는 안내 문맥에서 검출되고, MIGRATIONS archive/history 문맥은 면제된다.
- [x] Goal: S6·S11 기준으로 pre-check와 eval의 책임을 분리한다.
  검증:
    review: self
    tests: `python .claude/scripts/pre_commit_check.py`와 `python .claude/scripts/eval_harness.py`
    실측: staged 변경은 pre-check가 차단하고, 전체 repo drift는 eval이 warning/report로 출력한다.
- [x] Goal: S6 기준으로 README/MIGRATIONS/루트 지침에 새 검증 계층을 문서화한다.
  검증:
    review: self
    tests: `python .claude/scripts/harness_version_bump.py`
    실측: 필요한 경우 patch bump가 제안되고, MIGRATIONS에 downstream 수동 확인 항목이 포함된다.

## 메모

- 구현 반영: `pre_commit_check.py` staged syntax 검사 + path contract staged 게이트,
  `eval_harness.py` tool availability/path contract 보고, `downstream-readiness.sh`
  검증 도구 관측을 추가했다.
- 문서 반영: README, MIGRATIONS, CLAUDE.md, AGENTS.md에 새 검증 계층과 v0.52.5를 반영했다.
- path contract lint 실측에서 잡힌 stale path도 함께 정리했다:
  `docs/harness/hn_simplification.md`, `docs/harness/hn_debug_specialist.md`,
  `docs/harness/hn_upstream_anomalies.md`.
- `ruff`·`pyright`·`mypy`·`shellcheck` 설치를 starter 기본 의존성으로 강제하지 않는다.
  먼저 "없음을 관측"하고, 다운스트림별 opt-in/권장 설치는 별도 판단한다.
- LSP 자체를 CLI에서 직접 실행하는 것은 환경 의존이 커서 1차 목표가 아니다.
  1차 목표는 도구 부재를 보이게 하고, LSP가 못 보는 path string drift를 결정적
  lint로 보강하는 것이다.
