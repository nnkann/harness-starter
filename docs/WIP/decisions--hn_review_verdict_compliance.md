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
status: in-progress
created: 2026-05-02
updated: 2026-05-02
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
- [x] Goal: 본 세션 4 누락 케이스 패턴 특정 (분석 서술 → 결론 verdict 순? 또는 verdict 누락 후 본문만?)
  검증:
    review: skip
    tests: 없음
    실측: 본 세션 transcript에서 4/4 모두 "분석 본문 먼저 출력 → 1차 재호출에 verdict 헤더 부착" 패턴 일관 관찰
- [x] 패턴 결론: review 에이전트가 reasoning과 출력을 분리 안 함 — 분석 사고를 본문에 leak. verdict는 결론부 후반에 출현

### 2. prompt 재설계 (prefill 패턴)

**Acceptance Criteria**:
- [x] Goal: commit/SKILL.md prompt 마지막 줄을 `## 리뷰 결과 / verdict: `로 끝내 prefill 효과. 모델이 다음 토큰부터 verdict 값 강제 출력
  검증:
    review: review
    tests: 없음 (운용 검증)
    실측: 본 wave 이후 5 commit 연속 1패스 성공 추적 — 자동 검증 불가, 운용에서 확인
- [x] commit/SKILL.md "지시" 블록 끝에 "출력 형식 — 절대 규칙" 섹션 추가. prompt 자체가 `verdict: `로 끝나도록 재배치

### 3. review.md 구조 정리

**Acceptance Criteria**:
- [x] Goal: 상단 헤더 박스를 더 강하게 — 자주 나오는 실수 명시 + "분석은 reasoning에서, 출력은 결론부터" 행동 가이드
  검증:
    review: review
    tests: 없음
    실측: review.md line 10~ 강화 확인
- [x] 두 군데 분산 메시지 정리 — 상단 헤더는 행동 가이드, line 201 SSOT는 형식 정의 (역할 분리)

## 결정 사항

- **prefill 패턴 채택**: commit/SKILL.md prompt 마지막 줄을 `## 리뷰 결과 / verdict: `로
  끝내 모델 다음 토큰을 verdict 값으로 강제. Anthropic prefill 권장 패턴 활용.
  → 반영: commit/SKILL.md "## 출력 형식 — 절대 규칙" 섹션 + prompt 끝 `verdict: ` prefill
- **review.md 헤더 강화**: 자주 나오는 실수 명시(분석 머릿말·"AC 항목 검증한다") +
  "분석은 reasoning에서, 출력은 결론부터" 행동 가이드. 두 군데 분산 메시지의
  역할 분리 — 상단(line 10~)은 행동 가이드, line 201은 형식 SSOT.
  → 반영: review.md 상단 인용 박스 확장
- **자동 검증 불가 영역 정직 고지**: prefill 효과는 운용에서 5 commit 1패스
  성공률로 측정. 본 wave에서 자동 검증 불가 — 다음 commit부터 추적
- CPS 갱신: 없음 (S2 메커니즘 강화 — 충족 기준 변경 X, prompt 패턴 개선)

## 메모

- 본 세션 4 commit (v0.29.2·v0.30.0·v0.30.1·v0.30.2) 모두 verdict 누락 → 1차 재호출 통과 패턴 100% 일관
- 영향: 매번 review 재호출 1회 비용 (tool call 1~2 + 시간 5~10초 + prompt 토큰)
- 차단으로 이어진 적 없음 — 1차 재호출이 작동. 단 비용 누적 부담
- prefill 패턴 근거: Anthropic API에서 assistant 메시지 prefill로 응답 시작
  토큰 강제하는 표준 기법. sub-agent prompt에서도 마지막 줄이 다음 응답
  시작점에 영향 — 실측 필요하나 강한 prior
- 작은 변경 — review.md 인용 박스 1개·commit/SKILL.md "지시" 블록 1개 수정
  (15~20줄). 작업 규모 small
