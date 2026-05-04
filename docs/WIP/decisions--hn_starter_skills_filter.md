---
title: starter_skills 필터링 미구현 — harness-upgrade 폴더 복사 제외 + harness-dev 등록
domain: harness
problem: P3
solution-ref:
  - S3 — "다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨 (부분)"
tags: [harness-upgrade, starter_skills, harness-dev, isolation]
relates-to:
  - path: decisions/hn_starter_skill_isolation.md
    rel: extends
status: in-progress
created: 2026-05-04
---

# starter_skills 필터링 미구현

## 배경

`hn_starter_skill_isolation.md` Phase 2가 미구현 상태.

현재 `starter_skills` 필드는 HARNESS.json 값 동기화 메타데이터로만 기능하고,
harness-upgrade의 실제 스킬 폴더 복사 시 필터링이 없다. `ADDED` 파일(신규 스킬
폴더 포함)은 starter_skills 등록 여부와 무관하게 다운스트림에 전달된다.

버그 2개:
1. HARNESS.json `starter_skills`에 `harness-dev` 누락 (`"harness-init,harness-adopt"`만)
2. harness-upgrade에 `starter_skills` 폴더 복사 제외 로직 없음 (Phase 2 미구현)

## 목표

- `starter_skills`에 `harness-dev` 추가
- harness-upgrade ADDED 처리 시 `starter_skills` 목록의 스킬 폴더를 다운스트림에 전달하지 않음

## 작업 목록

### 1. HARNESS.json starter_skills에 harness-dev 추가

**영향 파일**: `.claude/HARNESS.json`

**Acceptance Criteria**:
- [x] Goal: `starter_skills` 값이 `"harness-init,harness-adopt,harness-dev"`
  검증:
    review: skip
    tests: 없음
    실측: HARNESS.json 값 확인

### 2. harness-upgrade SKILL.md — ADDED 처리에 starter_skills 필터 추가

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`

**Acceptance Criteria**:
- [x] Goal: ADDED 파일 중 `.claude/skills/{starter_skills}/` 경로는 다운스트림 전달 제외
  검증:
    review: self
    tests: 없음
    실측: 없음 (절차 문서 변경 — 운용 검증)

**구현 방향**:
- harness-upgrade Step에서 ADDED 파일 처리 시 `starter_skills` 목록을 읽어
  해당 스킬 폴더를 "사용자 전용" 분류에 추가하거나 별도 제외 로직 삽입
- 폴백: `starter_skills` 키 없으면 `"harness-init,harness-adopt,harness-dev"` 하드코딩

### 3. MIGRATIONS.md 안내 추가

**영향 파일**: `docs/harness/MIGRATIONS.md`

**Acceptance Criteria**:
- [x] Goal: 기존 다운스트림에 이미 전달된 starter 스킬 폴더 정리 안내 추가
  검증:
    review: skip
    tests: 없음
    실측: 없음

**내용**: "선택적 정리: `.claude/skills/harness-init/`, `harness-adopt/`, `harness-dev/` 삭제 가능"

## 메모

- `harness-sync`는 공용 유지 — 다운스트림도 클론 후 환경 동기화에 사용
- `hn_starter_skill_isolation.md`에 Phase 2 설계 상세 있음 (폴백 로직 포함)
- 선행 WIP `decisions--hn_adopt_legacy_doc_health.md` 완료 후 진행
