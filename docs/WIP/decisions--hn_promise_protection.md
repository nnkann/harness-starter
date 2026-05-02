---
title: 약속 박제 보호 — completed 봉인 + 미루기 차단 룰
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [rules, completed, promise, protection, anti-defer]
relates-to:
  - path: WIP/decisions--hn_session_test_results.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# 약속 박제 보호 — completed 봉인 + 미루기 차단

## 사전 준비
- 읽을 문서: `.claude/rules/docs.md` "## completed 전환 차단", `.claude/scripts/pre_commit_check.py`
- 자기증명 사례: 본 세션 v0.31.2 commit 후 wave WIP completed 상태에서 핫스팟 2~5로 무단 확장 시도 → 사용자 "최악 패턴" 지적

## 목표

세 가지 시스템 보호 메커니즘 신설로 "wave 봉인 무단 확장"·"미루기 회피 사유 생성" 패턴 차단.

## 작업

### 1. completed 문서 보호 게이트

**Acceptance Criteria**:
- [x] Goal: `status: completed` 문서 본문 변경을 pre-check이 차단 (reopen 명령으로만 in-progress 전환 가능)
  검증:
    review: review
    tests: pytest -m gate
    실측: completed 문서 임의 수정 후 pre-check이 exit 2 차단 확인
- [x] pre_commit_check.py에 completed 본문 변경 감지 로직 추가
- [x] 회귀 테스트 신설 (TestCompletedSeal 또는 기존 gate 클래스 확장)

### 2. 미루기 차단 룰 (anti-defer)

**Acceptance Criteria**:
- [x] Goal: `.claude/rules/anti-defer.md` 신설. "미루기 회피 사유" 패턴 명시 + 사용자 명시 처리 지시 우선 규칙
  검증:
    review: review
    tests: 없음 (룰 텍스트)
    실측: 본 룰 위반 패턴 감지 시 review가 [주의] 보고
- [x] 미루기 사유 블랙리스트 명시 ("측정 후·다음 세션·데이터 누적 필요" 등 사용자 승인 없는 단독 사용 금지)
- [x] wave 정의를 미루기 도구로 사용 금지 명시
- [x] CLAUDE.md `## 진입점` 표에 anti-defer 규칙 추가

### 3. review 자동 감지 — wave scope 무단 확장

**Acceptance Criteria**:
- [x] Goal: review.md에 "직전 commit 메시지·WIP의 명시 범위 밖 변경" 감지 항목 추가
  검증:
    review: self
    tests: 없음 (룰 텍스트)
    실측: 본 wave가 자기증명 — 본 commit이 wave scope 위반 없는지 review가 확인
- [x] review.md "## 검증 루프"에 "wave scope 일치 검사" 단계 추가
- [x] 위반 시 [주의] 보고 (차단 아님 — 자율 신뢰 영역)

## 결정 사항

(작업하면서 채움)

## 메모

- 본 세션 자기증명 사례:
  - v0.31.2 Phase 1 commit 후 사용자 "다음 wave로 미루지 마" 지적 → 내가 wave 무단 확장으로 과반응 → 사용자 "최악 패턴" 재지적
  - "별 wave 분리 = 정상 흐름"과 "미루기 = 문제"를 합쳐서 해석한 결함
- 사용자 정정: **핫스팟 발견 즉시 별 wave로 처리는 정상**. **미루기는 회피**. 두 사안 분리해야
- Claude 자율 신뢰 영역 (anti-defer 룰)은 review 감지로 보강. 메커니즘 차단 (completed 봉인)은 pre-check으로 강제
