---
title: P11 첫 누적 case — dead reference 일괄 정비 + 구조적 재발 방지
domain: harness
problem: [P7, P11]
s: [S5, S6, S9]
tags: [dead-reference, p11, eval-harness, harness-dev]
relates-to:
  - path: decisions/hn_harness_73pct_cut.md
    rel: extends
status: completed
created: 2026-05-16
updated: 2026-05-16
---

# P11 첫 누적 case — dead reference 일괄 정비

## 0. 박제 — 다운스트림이 발견한 본질

StageLink가 v0.47.4 → v0.47.8 upgrade 후 dead reference 정비 wave 중
`harness-upgrade SKILL.md L580` 1건 보고. starter 본인이 권장 grep을
돌린 결과 **README에 6건 추가** 잠복 발견.

= **P11(동형 패턴 잠복 — 1차 발견 시 다른 위치 후보 자동 탐색 부재) 직격
사례**. P11 신규 등록(v0.47.6) 후 **첫 누적 case 박제**.

## 1. Goal

starter 본문의 폐기 파일 dead reference 7건 일괄 정비 + 구조적 재발 방지
2축(eval_harness 검사·harness-dev 절차) 신설.

## 2. 발견 데이터

`git grep` 결과 dead reference 7건 (예시 인용/박제 표현 제외):

| 위치 | 패턴 | 처리 |
|---|---|---|
| harness-upgrade/SKILL.md:580 | `.claude/rules/anti-defer.md` | placeholder `<deprecated-rule>.md` |
| harness-upgrade/SKILL.md:581 | `.claude/scripts/orchestrator.py` | placeholder `<deprecated-script>.py` |
| README.md:47 | self-verify "pipeline-design 체크리스트 연계" | 줄 제거 (pipeline-design 폐기) |
| README.md:56 | external-experts.md 트리 | 줄 제거 |
| README.md:57 | pipeline-design.md 트리 | 줄 제거 |
| README.md:58 | staging.md 트리 | 줄 제거 |
| README.md:68 | doc-health/ 스킬 트리 | 줄 제거 |
| README.md:70 | check-existing/ 스킬 트리 | 줄 제거 |
| README.md:221 | rules/staging.md 참조 | review 분기 박제로 교체 |

총 9 라인 (L580-581 + README 7곳).

## 3. 구조적 재발 방지

**B1. eval_harness.py dead reference 검사 추가**:
- 폐기 파일 SSOT: archived 폴더 + git log "폐기·삭제" 키워드 grep으로 폐기 파일명 수집
- starter 본문(skills·agents·rules·README) 전수 grep으로 dead 참조 검출
- 박제 표현(`폐기 흡수`·`스킬 폐기`)은 false positive — 면제 패턴

**B2. harness-dev SKILL.md 절차 추가**:
- 폐기 파일 발생 시 본문 예시 grep + 갱신 체크리스트
- 폐기 commit이 starter 본문 정비 동반 의무화

## 4. Acceptance Criteria

**Acceptance Criteria**:
- [x] Goal: P7·P11 dead reference 일괄 정비 — S5·S6·S9 cascade 충족.
  - dead reference 7건 정비
  - eval_harness.py dead-ref 검사 추가
  - harness-dev SKILL.md 절차 추가
  검증:
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: git grep으로 dead reference 0건 재확인
- [x] L580-581 placeholder 교체 (`<deprecated-rule>.md`·`<deprecated-script>.py`)
- [x] README 7개 dead reference 정리 (rules 트리 3건·skills 트리 2건·연계 안내 1건·review 분기 1건)
- [x] eval_harness.py dead-ref 검사 함수 추가 + test 3건 (17 passed)
- [x] harness-dev SKILL.md 폐기 절차 추가 (Step P1~P5)
- [x] 최종 git grep 재확인 0건 (박제 표현 면제 정상)

## 5. 동반 관찰 (CPS case 박제 후 별 wave)

다운스트림 보고에 동반된 3건 — 본 wave 분량 큼이라 별 wave:
1. AC 헤더 `##` vs `**bold**` auto-fix 부재
2. `docs_ops.py move` 라우팅 태그 접두사 강제 — naming.md "라우팅 태그 폐기" 박제와 표면적 모순
3. WIP move 후 pre-check P#/S# 추출 불가 — 추적성 라인 수동 박제

→ 본 wave 종료 시 CPS case로 박제 (`docs/cps/cp_dead_ref_p11_first_case.md`).
