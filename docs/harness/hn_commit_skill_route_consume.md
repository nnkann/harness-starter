---
title: commit SKILL이 route 출력 소비 — §H-2
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, skill, route]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: WIP/harness--hn_commit_perf_followups.md
    rel: implements
status: completed
created: 2026-05-12
updated: 2026-05-12
---

# commit SKILL이 route 출력 소비 (§H-2)

`harness--hn_commit_perf_optimization.md` §A~§I 원칙 SSOT 상속. §H-2 본문
정의는 `WIP/harness--hn_commit_perf_followups.md`의 "§H-2 commit 스킬
route 소비" 섹션. 본 WIP는 그 sub-task의 실행 단위.

## 사전 준비

- 읽을 문서:
  - `docs/harness/hn_commit_perf_optimization.md` §A·§B·§C·§H §I (원칙)
  - `docs/WIP/harness--hn_commit_perf_followups.md` §H-2 (sub-task 정의)
  - `.claude/skills/commit/SKILL.md` (수정 대상 SSOT)
  - `.agents/skills/commit/SKILL.md` (Codex 브리지 — 본문 동일 유지)
- 이전 산출물: `cc01f0e` (§H-1 pre_commit_check route 출력 freeze)
- MAP 참조: 본 wave에선 commit 스킬이 enforced-by로 staging.md 규칙 참조

## 목표

§H-1에서 freeze한 4축 6키 stdout (commit_route/review_route/promotion/
side_effects.*) 을 commit SKILL이 실제로 읽고 분기하도록 본문 재작성.
SKILL은 자연어 절차이므로 회귀 가드는 텍스트 grep + 운용 검증 묶음으로
처리.

CPS 연결: S2 "review tool call 평균 ≤4회"의 메커니즘 — route 기반 분기로
일반 docs/단일 WIP 커밋이 release path 비용을 더 이상 떠안지 않게 함
(fast-by-default 원칙, §A 본문).

## 작업 목록

### 1. SKILL.md 본문 재작성 (3축)

**사전 준비**: `.claude/skills/commit/SKILL.md` Step 4·5.5·7 본문 확인.
**영향 파일**:
- `.claude/skills/commit/SKILL.md` (SSOT, CRLF 유지)
- `.agents/skills/commit/SKILL.md` (Codex 브리지, LF 유지)

**변경 축**:

| 축 | 현재 | 본 wave |
|----|------|---------|
| Step 4 version bump | is_starter=true이면 매 커밋 실행 | `promotion=release`일 때만 실행. is_starter=false 또는 promotion=none이면 skip |
| Step 7 review 호출 | `recommended_stage` 사용 | `review_route` 1차, `recommended_stage`는 호환성 폴백 |
| Step 5.5 split 분기 | `split_action_recommended` 단독 | `commit_route` 1차 (single|sub), `split_action_recommended`는 보조 |
| ledger 표시 | 없음 | Step 8 push 직전 요약에 `side_effects.required/release/repair` 출력 |

**Acceptance Criteria**:

- [x] Goal: commit SKILL이 §H-1 4축 6키를 명시 소비. Step 4·5.5·7·요약 4개 영역이 새 출력을 1차 신호로 사용 (recommended_stage·split_action_recommended·is_starter 단독 분기 제거).
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
    실측: grep -n "review_route\|commit_route\|promotion\b\|side_effects" .claude/skills/commit/SKILL.md
- [x] Step 4 (버전 체크) 본문이 `promotion=release` 조건부로 명시 재작성. is_starter=true 단독으로 매 커밋 실행하지 않음.
- [x] Step 7 (리뷰) 본문이 `review_route` 값을 1차 신호로 사용. recommended_stage는 호환성 폴백 위치에 명시.
- [x] Step 5.5 (분리 판정) 본문이 `commit_route` 값을 1차 분기. split_action_recommended는 보조.
- [x] Step 8 push 전 요약에 `side_effects.required/release/repair` ledger 출력 절차 명시.
- [x] `.agents/skills/commit/SKILL.md`도 동일 본문 동기화 (LF 유지). ✅
- [x] followups 인덱스에 "§H-2 ... → 본 wave에서 완료" 마킹.

## 결정 사항

- SKILL.md SSOT는 `.claude/skills/commit/SKILL.md` (CRLF). `.agents/skills/
  commit/SKILL.md` (LF)는 Codex 브리지로 본문 동일 유지. 동기화는 본 wave에서
  Python으로 1회 처리 — 자동 sync 메커니즘은 별 wave 후보.
- Step 4의 is_starter 단독 분기를 promotion=release로 좁힘. `promotion=repair`는
  본 wave 범위 외 (§H-5 활성화) — 현재는 none과 동일 취급으로 안전 폴백.
- CPS 갱신: 없음. S2 메커니즘은 "review tool call 평균 ≤4회" — 본 wave는
  SKILL 본문 분기 변경이지 review 호출 횟수 자체 변경 아님. 효과는 fast
  path 진입 빈도 증가 (release path 비용 분리)로 평균 비용 감소 — 측정은
  운용 누적 후 별 wave.

## 메모

- 본 wave 실측: 4축 키 6개가 SKILL.md 본문에 모두 박힘 (grep 21건 hit).
  TestRouteOutput 3건 + TestStageBasic 2건 = 5 passed (§H-1 회귀 가드
  유지).
- 자동 검증 불가 영역 명시: SKILL.md는 자연어 절차 — Claude가 새 분기를
  실제로 따르는지는 본 커밋의 commit 스킬 실행 결과 + 다음 커밋부터의
  운용에서 확인. 본 wave는 SKILL 본문 정합·grep·테스트까지만 자동 검증.
- INFO 신호 (SKILL.md 4회·followups 3회) 자가 점검: Step 4 → 5.5 → 7 →
  Step 8(요약) → .agents 동기화 → followups 인덱스 마킹. 모두 §H-2 의도된
  일관 연쇄. 추측 수정 아님.
