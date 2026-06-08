---
title: 다운스트림 pytest fixture가 starter 정책과 프로젝트 CPS 형식을 물려받은 사고
domain: harness
c: "다운스트림 harness-upgrade 직후 upstream 테스트 7건 실패 — is_starter:false와 프로젝트별 CPS 형식이 starter 테스트 기대와 충돌"
problem: [P6, P9, P11]
s: [S6, S9, S11]
tags: [downstream, testing, fixture, false-positive, upgrade]
status: completed
created: 2026-05-19
updated: 2026-05-19
symptom-keywords:
  - harness-upgrade
  - pytest 7 failed
  - is_starter false
  - TestCpsAddTableInsert
  - relates-to warn-only
relates-to:
  - path: decisions/hn_pytest_regression_routing.md
    rel: references
  - path: decisions/hn_verify_relates_precheck.md
    rel: references
  - path: incidents/hn_starter_push_skipped.md
    rel: references
---

# 다운스트림 pytest fixture leak

## 증상

다운스트림 프로젝트에서 `harness-upgrade`로 v0.51.5 적용 후 upstream 테스트를
실행하자 7건이 실패했다.

- `relates-to` 계열 6건: broken reference가 차단되어야 한다고 기대했지만 실제
  출력은 `pre_check_passed: true`
- `TestCpsAddTableInsert` 1건: `기존 P# 표 없음 — fixture 손상`

실패는 v0.51.5 Python 문법 오류나 실제 하네스 동작 오류가 아니었다. 테스트
fixture가 다운스트림 환경의 `is_starter: false` 정책과 프로젝트별
`project_kickoff.md` 형식을 그대로 물려받은 것이 원인이었다.

## 원인

`pre_commit_check.py`의 `relates-to` 전수 검사는 starter와 다운스트림을 다르게
취급한다.

- starter: broken `relates-to` 차단
- downstream: warn-only

그런데 `test_pre_commit.py`의 통합 sandbox는 테스트 의도를 명시하지 않고 현재
repo의 `.claude/HARNESS.json`을 물려받았다. 다운스트림에서 테스트가 실행되면
`is_starter: false`가 유지되어 starter 차단 기대 테스트가 warn-only 경로를 탔다.

`TestCpsAddTableInsert`도 starter의 Problems 표를 전제로 했다. 다운스트림의
`project_kickoff.md`가 프로젝트 전용 본문형 CPS 문서이면 기존 P# 표를 찾지 못해
fixture 손상으로 실패했다.

T45.6 실패는 독립 원인이 아니었다. 앞선 T45.4가 assert에서 멈추면서
module-scoped sandbox에 broken rule 파일을 남기고, 다음 테스트가 오염된 상태를
물려받은 cascading failure였다.

## 조치

v0.51.6에서 테스트 fixture를 격리했다.

- 통합 sandbox 생성 직후 `is_starter: true`를 명시해 starter 차단 기대 테스트의
  기준을 고정했다.
- 다운스트림 warn-only 케이스는 테스트 내부에서만 `is_starter: false`로 전환하고
  cleanup에서 다시 starter 모드로 복원했다.
- `TestCpsAddTableInsert`는 실제 다운스트림 `project_kickoff.md`에 의존하지 않고
  starter형 synthetic kickoff fixture를 작성한 뒤 `cps add`를 검증한다.
- `docs_ops.py`에 남아 있던 잘못된 미래 버전 표기를 정정했다.

## 검증

- `python -m pytest .claude/scripts/tests/ -q` → `191 passed, 4 skipped`
- 다운스트림형 재현 fixture (`is_starter:false` + 프로젝트별 CPS 형식)에서 관련
  5개 테스트 재실행 → `5 passed`
- `python .claude/scripts/safe_command.py verify-relates` → 미연결 0건
- `python .claude/scripts/pre_commit_check.py` → `pre_check_passed: true`

## 재발 방지

starter 정책을 검증하는 테스트는 repo의 현재 `HARNESS.json`을 암묵적으로 믿지
않는다. 테스트 fixture가 starter/downstream 정책을 직접 세팅해야 한다.

프로젝트별 문서 형식에 독립적인 도구 테스트는 실제 downstream 문서를 fixture로
쓰지 않는다. 검증하려는 형식을 synthetic fixture로 고정한다.
