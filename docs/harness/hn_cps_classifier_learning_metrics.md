---
title: CPS 분류 판정기와 학습 지표 보강
domain: harness
c: "사용자: C/P/S별 범위·규합·반복 문제 해결 정합성을 정량 테스트하고, 재발 억제뿐 아니라 신규 케이스 발굴·적응도 학습 효과로 봐야 한다."
problem: [P6, P7, P8, P9, P11]
s: [S6, S7, S8, S9, S11]
tags: [cps, eval, classification, learning, downstream]
status: completed
created: 2026-05-31
updated: 2026-06-01
---

# CPS 분류 판정기와 학습 지표 보강

## CPS Rationale

- C -> P: CPS 번호 존재만 확인하면 retired P#, 과도한 P10, 반복 case 편중,
  downstream adapter 누락 같은 분류·학습 신호가 보이지 않아 P6/P7/P8/P9/P11이 재발한다.
- P -> S: S6은 검증 책임, S7은 출력 계약, S8은 신호 상태화, S9는 오염 방지,
  S11은 동형·반복 후보 탐색을 정량 지표로 드러낸다.
- S -> AC: AC는 eval 출력과 테스트가 case catalog, 정의 밖 P/S, 반복 Problem,
  runtime adapter skill 누락을 잡는지로 검증한다.

## 구현 계획

1. P12로 남은 case frontmatter를 현재 SSOT인 P11/S11로 정정한다.
2. `eval_cps_integrity.py`에 CPS case catalog 정량 지표를 추가한다.
3. `downstream-readiness.sh`가 `.claude`와 `.agents` 핵심 skill 존재를 검사하게 한다.
4. 회귀 테스트로 undefined case ref와 Codex commit skill 누락을 고정한다.

**Acceptance Criteria**:

- [x] Goal: S6/S7/S8/S9/S11 기준으로 CPS 분류 판정기가 scope, aggregation,
  recurrence, adaptation 신호를 정량 출력하고 downstream commit skill 누락을 readiness가 잡는다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_eval_harness.py .claude/scripts/tests/test_downstream_readiness.py -q`
    실측: 테스트 49 passed. `python .claude/scripts/eval_harness.py`가 case catalog와 정의 밖 case ref 0건을 출력. starter readiness 누락 0건, StageLink workdir에서 새 readiness 실행 시 Codex surface 누락 4건 검출.
- [x] P12 historical case의 frontmatter가 P11/S11을 가리키고 `docs_ops.py cps stats`에 정의 밖 P12가 나오지 않는다.
- [x] eval CPS 보고에 case catalog, case coverage, 반복 Problem, P10 case, 정의 밖 case ref가 출력된다.
- [x] Codex adapter가 있는 downstream에서 `.agents/skills/commit/SKILL.md`가 없으면 readiness가 누락으로 실패한다. ✅

## 결정 사항

- P12·S12는 현행 CPS 정의가 아니라 P11·S11에 흡수된 역사 라벨로 처리한다.
- 학습 효과는 재발 억제만이 아니라 case catalog coverage와 신규/정의 밖 case 발견 신호를 함께 본다.
- current CPS 진전 proxy에서는 `docs/archived/`를 제외한다. archive의 retired P#는 역사 박제이지 현재 Problem 활성 신호가 아니다.
- Codex adapter가 감지되면 `AGENTS.md`와 `.agents/skills/{commit,implementation,harness-upgrade}/SKILL.md`를 readiness hard issue로 본다.
- CPS 갱신: 없음. P12 정정은 신규 P#가 아니라 P11/S11 흡수 반영이다.

## 메모

- StageLink 실측: `/Users/kann/projects/stagelink`에는 `.claude/skills/commit/SKILL.md`는 있으나
  `AGENTS.md`와 `.agents/skills/commit/SKILL.md`가 없고, HARNESS.json도 `runtime_stack`/`runtime_adapters`
  이전 형식이다. Codex 계열에서 `/commit` skill discovery가 실패할 수 있는데 기존
  `downstream-readiness.sh`는 누락 0건으로 통과했다.
