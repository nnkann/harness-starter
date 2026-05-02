---
title: review 에이전트 verdict 헤더 형식 준수율 — 100% 누락 패턴
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [review, verdict, format, compliance]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# review verdict 형식 100% 누락

## 사전 준비
- 읽을 문서: `.claude/agents/review.md` (line 10~15 헤더 + line 201~ "출력 형식" SSOT), `.claude/skills/commit/SKILL.md` (review 호출 prompt 조립부)
- 이전 산출물: 본 세션 v0.29.2·v0.30.0·v0.30.1 commit 3건 — 모두 verdict 누락 → 1차 재호출로 회복

## 목표
review 에이전트 응답 첫 2줄 `## 리뷰 결과\nverdict: X` 형식 1패스 준수율
0% → 90% 이상. 매번 1차 재호출 비용 누적 + 차단 위험.

## 현재 상황 분석 (본 세션 실측)

review.md에 강제는 충분:
- frontmatter 직후 line 10~15: 인용 박스로 "응답 첫 2줄 무조건"
- line 158~160: maxTurns·verdict 필수
- line 201~: "## 출력 형식 (SSOT)" 전체 템플릿

commit/SKILL.md prompt 끝에도 명시. 그럼에도 100% 누락.

원인 가설:
1. review가 **분석 자유 서술 본문을 먼저 출력**하는 경향 (chain-of-thought
   leak) — 첫 토큰부터 헤더가 나오게 강제 안 됨
2. 강제 메시지가 review.md 두 군데 분산 (line 10·201) — 일관성 떨어짐
3. commit prompt의 "지시" 블록이 다른 지시(파일 Read·git diff)와 섞여
   verdict 형식 우선순위가 묻힘

## 작업 목록

### 1. 원인 진단

**Acceptance Criteria**:
- [ ] Goal: 본 세션 3 누락 케이스 transcript 분석으로 review 응답 패턴 특정 (분석 서술 → 결론 verdict 순? 또는 verdict 누락 후 본문만?)
  검증:
    review: skip
    tests: 없음
    실측: 없음
  **(작업 착수 시 채움)**
- [ ] git log에서 `[review-form-warn]` 태그 빈도 측정 (전체 commit 대비)

### 2. prompt 재설계

**Acceptance Criteria**:
- [ ] Goal: review prompt 마지막 줄을 `verdict: ` 만 박은 prefill 형태로
  실험. 첫 토큰이 verdict 값이 되도록 강제
  검증:
    review: review
    tests: 없음
    실측: 본 wave 이후 5 commit 연속 1패스 성공 추적
  **(작업 착수 시 채움)**
- [ ] 또는 commit/SKILL.md "지시" 블록 끝에 "verdict 헤더 누락 시 자동 차단" 명시

### 3. review.md 구조 정리

**Acceptance Criteria**:
- [ ] Goal: 형식 강제 메시지를 1곳(line 10~15)에 통합. 중복 제거
  검증:
    review: review
    tests: 없음
    실측: 없음
  **(작업 착수 시 채움)**

## 결정 사항
(작업하면서 채움)

## 메모
- 본 세션 3 commit (v0.29.2·v0.30.0·v0.30.1) 모두 verdict 누락 → 1차 재호출 통과 패턴 일관
- 영향: 매번 review 재호출 1회 비용 (tool call 1~2 + 시간 5~10초)
- 차단으로 이어진 적 없음 — 1차 재호출이 작동. 단 prompt 토큰·시간 누적 부담
- 우선순위: 매번 마찰이지만 동작 자체는 회복됨 — Phase 2-A 후속 wave와 함께 진행 가능
