---
title: eval harness false positive 보정
domain: harness
c: "다운스트림 /eval --harness가 헤더형 CPS 매핑과 eval 자기 진단 스크립트를 사용자 조치 버그처럼 보고"
problem: P9
s: [S6, S9]
tags: [eval, cps, false-positive]
status: completed
created: 2026-05-20
updated: 2026-05-20
---

# eval harness false positive 보정

## CPS Rationale

- C -> P: eval 경고가 실제 조치 대상과 자기 진단 잡음을 섞어 다운스트림 판단을 오염시켰다.
- P -> S: S9는 오염된 진단 신호를 단독 증거로 쓰지 않게 하고, S6는 수정 효과를 현재 wave에서 실측하게 한다.
- S -> AC: 헤더형 CPS 파서와 자기 진단 제외 필터를 테스트·실행 결과로 닫는다.

**Acceptance Criteria**:
- [x] Goal: S6·S9 기준으로 `/eval --harness` false positive 2건을 코드와 회귀 테스트로 보정한다.
  검증:
    review: skip
    tests: `python -m pytest .claude/scripts/tests/ -q`
    실측: `python .claude/scripts/eval_cps_integrity.py`에서 Solution→Problem mapping 100%, `python .claude/scripts/eval_harness.py`에서 자기 진단 스크립트 2개 제외 확인
- [x] `.claude/scripts/eval_cps_integrity.py`가 `### S# (for P#)` 헤더형 Solution 매핑을 파싱한다. ✅
- [x] `.claude/scripts/eval_harness.py`가 `eval_harness.py`·`eval_cps_integrity.py` 자체를 silent exception 사용자 조치 후보에서 제외한다. ✅
- [x] `.claude/scripts/tests/test_eval_harness.py`에 두 false positive 회귀 테스트가 추가된다. ✅

## 결정 사항

- CPS 갱신: 없음. 기존 P9·S9와 P6·S6의 진단 오염·검증 책임 문제를 코드로 보강한다.
