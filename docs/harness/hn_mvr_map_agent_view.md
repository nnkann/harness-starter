---
title: MVR 매핑 + HARNESS_MAP 에이전트 관점 개선
domain: harness
problem: P5
solution-ref:
  - S5 — "MVR(Minimum Viable Rules) (부분)"
tags: [mvr, harness-map, context, p5, p7]
relates-to:
  - path: harness/MIGRATIONS.md
    rel: references
status: completed
created: 2026-05-06
updated: 2026-05-06
---

# MVR 매핑 + HARNESS_MAP 에이전트 관점 개선

## 사전 준비
- 읽을 문서: .claude/HARNESS_MAP.md (현재 구조 확인 완료)
- 이전 산출물: Wave A 완료 (v0.38.1)
- MAP 참조: P5 served-by 없음(방향 전환), P7 served-by eval_cps_integrity.py

## 목표

1. HARNESS_MAP에 **작업유형별 MVR(최소 필수 규칙셋)** 섹션 추가
   - 에이전트가 전체 MAP을 읽지 않고 "지금 내 작업에 필요한 Rules 3개"만 골라낼 수 있도록
   - P5(컨텍스트 팽창)와 P7(관계 불투명)의 역설적 충돌 해소
2. MAP 상단 "읽는 법"에 **에이전트 진입점 가이드** 추가
   - "지도 전체를 읽지 마라. 작업유형 → MVR 섹션만 보라"

CPS 연결: S5 "압축 전략" + P7 미완독 회피 패턴 해소

## 작업 목록

### Phase 1. HARNESS_MAP — MVR 섹션 추가

**영향 파일**: .claude/HARNESS_MAP.md

**주의사항**:
- MVR은 "최소"이므로 각 유형당 Rules 3개 이하로 제한. 4개 이상이면 MVR이 아님.
- 작업유형은 에이전트가 실제 발화하는 맥락 기준 (구현·커밋·디버그·문서 등). 추상 분류 금지.
- Layer 번호·테이블 구조는 기존 MAP 스타일 유지. 새 포맷 도입 금지.

**Acceptance Criteria**:
- [x] Goal: HARNESS_MAP에 `## MVR (작업유형별 최소 필수 규칙셋)` 섹션이 추가되어, 에이전트가 작업유형을 보고 읽어야 할 Rules 목록을 즉시 확인할 수 있다
  검증:
    review: review
    tests: 없음
    실측: HARNESS_MAP.md 열어서 ## MVR 섹션 + 작업유형별 Rules 목록 확인

### Phase 2. MAP 상단 에이전트 진입점 가이드 추가

**영향 파일**: .claude/HARNESS_MAP.md

**주의사항**:
- 기존 "읽는 법" 섹션을 대체하지 말고 앞에 "에이전트 진입점" 블록 추가.
- "MAP 전체를 읽지 마라"는 지시를 명시. 현재 하향 경로 설명은 유지.

**Acceptance Criteria**:
- [x] Goal: MAP 최상단에 "작업 전: MVR 섹션만 → 문제 발생: 역추적 절차만" 2줄 요약이 있어, 에이전트가 MAP 전체를 읽지 않고도 진입점을 찾을 수 있다
  검증:
    review: self
    tests: 없음
    실측: HARNESS_MAP.md 첫 10줄에서 MVR 진입 안내 확인

## 결정 사항
- MVR 섹션을 HARNESS_MAP 하단(역추적 절차 앞)에 배치. 이유: 역추적은 문제 발생 시용이므로 평상시 진입점인 MVR이 앞에 오는 게 자연스러움. → 반영: .claude/HARNESS_MAP.md
- 작업유형 7개 확정 (구현·커밋·디버그·문서·eval·harness-dev·설정변경). 각 2~3개 Rules. → 반영: .claude/HARNESS_MAP.md ## MVR
- CPS S5 승격 상태 갱신 (MVR 구현 완료 명시). → 반영: docs/guides/project_kickoff.md
- CPS 갱신: S5 승격 상태 갱신 완료.

## 메모
- doc-finder: MVR 관련 기존 구현 문서 없음. CPS에 방향만 언급됨.
- 작업유형 초안 (에이전트 실제 발화 패턴 기준):
  구현(implementation) / 커밋(commit) / 디버그(debug) / 문서 작성(write-doc) / eval / 하네스 개발(harness-dev)
- CPS 갱신: S5에 "MVR" 용어 등장했으나 S7은 CPS에 없음 → frontmatter 수정 필요
