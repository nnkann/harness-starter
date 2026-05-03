---
title: PRD 레이어 보강 — User Needs 섹션·milestones 샘플·harness-init 권고
domain: harness
problem: P3
solution-ref:
  - S3 — "MIGRATIONS.md — upstream 소유 지시 문서 (부분)"
tags: [prd, milestones, harness-init, cps]
status: completed
created: 2026-05-03
updated: 2026-05-03
---

# PRD 레이어 보강

## 사전 준비
- 읽을 문서: `docs/guides/project_kickoff_sample.md`, `.claude/skills/harness-init/SKILL.md`
- doc-finder fast scan: milestones, prd, user-needs 키워드 → 없음

## 목표
- 결정 A: CPS 샘플에 User Needs 섹션 추가 (선택적, pre-check 무변경)
- 결정 B: milestones_sample.md 신규 생성 (선택적 활성화용 샘플)
- 결정 D: harness-init 권고 안내 추가 (강제 아님)

## 작업 목록

### 1. milestones_sample.md 신규 생성

**영향 파일**: `docs/guides/milestones_sample.md` (신규)

**Acceptance Criteria**:
- [x] Goal: 에픽 = 사용자 가치 묶음 원칙과 backlog/in-progress/done 구조가 담긴 샘플이 존재한다
  검증:
    review: skip
    tests: 없음
    실측: 없음 (문서 신규 생성)

### 2. project_kickoff_sample.md User Needs 섹션 추가

**영향 파일**: `docs/guides/project_kickoff_sample.md`

**Acceptance Criteria**:
- [x] Goal: ## Context 아래 ## User Needs 섹션이 추가되고 비어 있어도 pre-check이 통과한다
  검증:
    review: skip
    tests: python3 -m pytest .claude/scripts/tests/ -q -k "sample or kickoff" 또는 없음
    실측: python3 .claude/scripts/pre_commit_check.py로 sample 파일 차단 없음 확인

### 3. harness-init SKILL.md 템플릿 + 권고 추가

**영향 파일**: `.claude/skills/harness-init/SKILL.md`

**Acceptance Criteria**:
- [x] Goal: Step 7 CPS 템플릿에 User Needs 반영, Step 8 이후 규모 권고 1단락 추가
  검증:
    review: skip
    tests: 없음
    실측: 없음 (문서 갱신 — Claude 행동 변화는 운용에서 확인 필요)

## 결정 사항
- milestones_sample.md는 `docs/guides/`에 위치. docs.md 폴더 규칙상 guides/ = "어떻게 하나?" 적합
- sample 파일이라 abbr 없이 `milestones_sample.md` (전역 마스터 파일명 패턴)
- CPS 갱신: 없음

## 메모
- advisor 결정(2026-05-03): 결정 B는 two-way, 결정 A도 two-way, 결정 D는 권고만
- BMAD 에픽 원칙 직접 차용: "Database Setup 같은 기술 레이어명 에픽 = FAILURE"
