---
title: harness-adopt 레거시 문서 정비 지원 — doc-health 진단 플로우
domain: harness
problem: P3
solution-ref:
  - S3 — "다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨 (부분)"
tags: [harness-adopt, doc-health, legacy, abbr, frontmatter]
relates-to:
  - path: decisions/hn_adopt_without_init_guard.md
    rel: extends
  - path: decisions/hn_downstream_amplification.md
    rel: references
status: completed
created: 2026-05-04
updated: 2026-05-04
---

# harness-adopt 레거시 문서 정비 지원

## 배경

StageLink 다운스트림 실측 (2026-05-04): 하네스 도입 이전 문서 240개+를
하루에 수동으로 정비. 정비 전에는 탐색 체인이 완전히 무력화된 상태였음.

- abbr 없는 파일 230개+ → `ls docs/**/*co_*` 같은 cluster 탐색 0건
- CPS frontmatter 없는 파일 233개 → eval --harness P/S 분포 분석 불가
- archived 없이 SSOT 혼재 → grep 결과 오염

**결론**: harness-adopt이 `.claude/` 이식은 해주지만, 기존 docs/ 레거시
문서 정비는 다운스트림에 완전히 위임됨. 진입 비용이 크다.

## 목표

harness-adopt 스킬 또는 별도 "doc-health" 진단 스킬을 통해 레거시 문서
정비를 가이드·반자동화한다.

CPS 연결: P3 — 하네스 이식 후 docs/ 레거시 오염으로 탐색 체인·CPS 체계가
무력화되는 사일런트 페일.

## 작업 목록

### 1. 설계 결정 — harness-adopt 내장 vs 별도 스킬

**Acceptance Criteria**:
- [x] Goal: 접근법 결정 + 근거 기록
  검증:
    review: skip
    tests: 없음
    실측: 없음

### 2. doc-health 스킬 신설 (SKILL.md 작성)

**Acceptance Criteria**:
- [x] Goal: SKILL.md 초안 + 3단계 정비 플로우 정의 ✅
  검증:
    review: self
    tests: 없음
    실측: StageLink 정비 흐름 재현 가능한지 수동 확인

**정비 3단계 (실측 기반)**:

1. **진단** — eval --harness 호출 (진단 결과 재사용)
   - abbr 없는 파일 목록
   - CPS frontmatter 없는 파일 목록

2. **SSOT 선별 + archived** (인터랙티브)
   - 도메인별 문서 목록 제시 → 사용자가 keep/archive 결정
   - 결정 후 `docs_ops.py move` 자동 실행

3. **rename + frontmatter 추가** (반자동)
   - abbr 없는 파일 → naming.md 기준 rename 제안
   - CPS frontmatter 없는 파일 → problem/solution-ref 1차 제안 (사용자 확인 후 적용)

### 3. eval --harness 연결 — 진단 후 doc-health 호출 권장

**Acceptance Criteria**:
- [x] Goal: eval --harness 결과에 문제 발견 시 "doc-health 실행 권장" 안내 추가
  검증:
    review: self
    tests: 없음
    실측: eval --harness 실행 후 안내 문구 확인

### 4. harness-adopt 연결

**Acceptance Criteria**:
- [x] Goal: harness-adopt 종료 흐름에 doc-health 안내 추가
  검증:
    review: self
    tests: 없음
    실측: 없음

## 결정 사항

**B + C 조합 채택**:
- **B**: 독립 `doc-health` 스킬 신설 — 단일 책임, 이미 이식된 프로젝트도 언제든 실행 가능
- **C 연결**: eval --harness가 진단 후 문제 발견 시 doc-health 호출 권장 안내
- harness-adopt 종료 시도 doc-health 안내 추가

**근거**: eval은 read-only 리포트 역할 유지. 정비 실행은 doc-health가 담당.
진단(eval) → 정비(doc-health) 흐름이 명확히 분리됨.

## 메모

- 실측 케이스: StageLink, 2026-05-04. 정비 규모·효과는 project memory 참조
  (`project_downstream_legacy_doc_cleanup.md`)
- eval --harness가 이미 abbr 없는 파일·CPS 누락을 일부 감지 → 진단 단계 재사용 가능
- 정비 자동화의 한계: SSOT 선별(archived 결정)은 사람이 해야 함. 스킬은 가이드·반자동화만
