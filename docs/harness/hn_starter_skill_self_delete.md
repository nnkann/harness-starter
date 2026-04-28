---
title: starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정
domain: harness
tags: [skill, starter, harness-init, harness-adopt, harness-upgrade]
relates-to:
  - path: decisions/hn_starter_skill_isolation.md
    rel: implements
status: completed
created: 2026-04-28
updated: 2026-04-28
---

# starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정

## 사전 준비
- 읽을 문서: `docs/decisions/hn_starter_skill_isolation.md` (B안 결정 SSOT)
- 이전 산출물: 없음

## 목표
- harness-init·adopt 완료 시 자기 자신을 삭제 (1회성 스킬 → 실행 후 소멸)
- harness-upgrade가 HARNESS.json 병합 시 `starter_skills` 키 누락 버그 수정
- MIGRATIONS.md v0.26 수동 적용 항목 갱신

## 작업 목록

### 1. harness-init SKILL.md — 완료 시 자기 삭제
> kind: feature

**영향 파일**: `.claude/skills/harness-init/SKILL.md`
**Acceptance Criteria**:
- [ ] Step 8c 완료 처리에 `rm -rf .claude/skills/harness-init` 추가됨

### 2. harness-adopt SKILL.md — 완료 시 자기 삭제
> kind: feature

**영향 파일**: `.claude/skills/harness-adopt/SKILL.md`
**Acceptance Criteria**:
- [ ] Step 8 완료 리포트에 `rm -rf .claude/skills/harness-adopt` 추가됨

### 3. harness-upgrade — starter_skills 병합 버그 수정
> kind: bug

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`
**Acceptance Criteria**:
- [ ] Step 10 HARNESS.json 갱신에 `starter_skills` 키 동기화 명시
- [ ] `starter_skills` 없는 구버전 다운스트림 대비 하드코딩 폴백 명시

### 4. MIGRATIONS.md v0.26 갱신
> kind: docs

**영향 파일**: `docs/harness/MIGRATIONS.md`
**Acceptance Criteria**:
- [ ] 수동 적용 항목에서 "삭제" 항목이 "자동 삭제"로 변경됨

## 결정 사항

- harness-init·adopt는 완료 직후 자기 자신을 `rm -rf`로 삭제
- 필요 시 harness-upgrade로 upstream에서 재수신 가능
- starter_skills 없는 구버전 HARNESS.json 폴백: `harness-init,harness-adopt,harness-dev` 하드코딩

## 메모
- 다운스트림 `starter_skills: None` 버그 보고 (2026-04-28)
- `hn_starter_skill_isolation.md` Phase 2~3 미실행이 원인
