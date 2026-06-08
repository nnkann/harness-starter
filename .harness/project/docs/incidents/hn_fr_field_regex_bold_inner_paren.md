---
title: FR 필드 정규식 — bold 마커 내부 괄호 보강어 미인식 회귀
domain: harness
problem: P3
solution-ref:
  - S3 — "구조로 규격화 (부분)"
tags: [eval, feedback-report, regex, v0.42.4-regression]
symptom-keywords:
  - 약점 (부분 작동)
  - FR-007
  - _field_present
  - bold 괄호 보강어
status: completed
created: 2026-05-11
updated: 2026-05-11
---

# FR 필드 정규식 — bold 마커 내부 괄호 보강어 미인식 회귀

## 사전 준비
- 읽을 문서: `.claude/scripts/eval_cps_integrity.py:449` `_field_present`, `.claude/scripts/tests/test_eval_harness.py:230`
- 이전 산출물: v0.42.4 (3양식 양면 매칭 도입, FR-007 응답)
- MAP 참조: CPS P3 / S3 항목 4 (피드백 포맷 규격화)

## 목표
- 다운스트림 실측 양식 `**약점 (부분 작동)**:` 같은 bold 마커 **내부 괄호 보강어**를 `_field_present`가 인식하도록 정규식 확장
- 회귀 테스트로 양식 고정
- v0.42.4가 닫지 못한 양식 갭 봉합

CPS 연결: S3 항목 4 "피드백 포맷 규격화" 충족 — 검증 도구가 다운스트림이 실제로 쓰는 양식을 인식해야 채널이 작동

## 작업 목록

### 1. _field_present 정규식 확장 + 회귀 테스트

**사전 준비**: 현재 정규식 `\*\*{name}\*\*\s*:` — bold 닫는 `**` 직전에 공백·괄호·추가 텍스트 허용 안 함
**영향 파일**:
- `.claude/scripts/eval_cps_integrity.py:449-452`
- `.claude/scripts/tests/test_eval_harness.py` (회귀 케이스 추가)

**Acceptance Criteria**:
- [x] Goal: `**약점 (부분 작동)**:` 양식이 `_field_present("약점", ...)`에서 True 반환
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: test_eval_harness.py 14/14 통과 + 전체 92 passed/4 skipped
- [x] 새 회귀 테스트 케이스 추가 (bold 내부 괄호 보강어 — 4필드 모두 보강어 변형)
- [x] 기존 양식(`**약점**:`, `약점:`, `(약점:`) 모두 통과 — 회귀 없음 (FR-001/005/006/007 케이스 통과)
- [x] 양식이 아닌 단순 텍스트는 여전히 미매칭 — false-positive 가드 테스트 추가 (FR-011 케이스)

## 결정 사항
- 정규식 패턴 확정: `\*\*{name}(?:\s+\([^)]*\))?\*\*\s*:` — 필드명 뒤 선택적 1단 괄호 그룹 허용 → 반영: `eval_cps_integrity.py:451-456`
- 중첩 괄호는 지원 안 함 (`[^)]*` — `)` 미포함). 단순 1단 보강어만 허용해 정규식 복잡도 제한
- CPS 갱신: 없음 (S3 메커니즘 자체 변경 아님 — 메커니즘 갭 보강)

## 메모
- v0.42.4 변경 의도: 3양식(bold·plain·헤더 인라인) 양면 매칭. 하지만 bold 양식은 `**X**:` 닫는 마커 직전을 좁게 정의해 `**X (...)**:` 변형을 못 잡음
- 다운스트림 실측: `**약점 (부분 작동)**:` (FR 작성자가 필드명에 보강어 추가하는 자연스러운 양식)
- 패치 버전: v0.42.6 후보 (정규식 보강만, semver patch)
- review 강도: `review` 선언 — Solution 메커니즘 보강이지만 변경 범위 좁음 (정규식 1줄 + 회귀 테스트 2개)
