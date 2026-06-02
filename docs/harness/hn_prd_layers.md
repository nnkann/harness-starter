---
title: PRD 레이어 보강 — User Needs 섹션·milestones 샘플·harness-init 권고
domain: harness
problem: P3
s: [S3, S6, S7]
tags: [prd, milestones, harness-init, cps]
status: completed
created: 2026-05-03
updated: 2026-06-02
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

### 0. PRD 기반 harness-init 초안 모드 추가

**영향 파일**: `.claude/skills/harness-init/SKILL.md`, `.agents/skills/harness-init/SKILL.md`, `README.md`

**Acceptance Criteria**:
- [x] Goal: PRD가 이미 있는 프로젝트에서 `/harness-init`이 안전하게 초기 초안을 제안한다
  검증:
    review: self
    tests: python .claude/scripts/safe_command.py precheck
    실측: `.claude/skills/harness-init/SKILL.md`와 `.agents/skills/harness-init/SKILL.md`에 Step 0.5가 있고 README 신규 프로젝트 흐름에 PRD 초안 안내가 존재한다
- [x] Problem AC (P3): `h-setup.sh` 책임을 늘리지 않고 downstream에 전달되는 init 절차만 갱신한다 ✅
- [x] Solution AC (S3): 배포 대상 스킬 파일 2곳과 README 안내가 같은 행동 계약을 가리킨다
- [x] Solution AC (S6): PRD 추출 결과는 초안이며 자동 확정 금지와 사용자 확인 게이트가 명시된다
- [x] Solution AC (S7): PRD 후보 탐색, 다중 후보 처리, 산출 초안 항목의 소유권이 Step 0.5에 드러난다
- [x] Guardrail AC (P3/S6): PRD 후보가 여러 개이면 자동 선택하지 않고, PRD가 없으면 기존 Step 1로 진행한다
- [x] Verification AC (S6): precheck와 실측 grep으로 변경 파일의 절차 반영을 확인한다

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
- 2026-06-02: `/advisor` 검증 결과에 따라 `h-setup.sh --from-prd` 대신 `/harness-init` Step 0.5를 추가. 이유: h-setup은 복사/설치 책임을 유지하고, PRD 해석은 init의 사용자 확인 흐름에 태우는 편이 P3/S6 리스크를 줄인다.
- 2026-06-02: `.claude/skills`와 `.agents/skills` 양쪽에 같은 Step 0.5를 반영. 이유: h-setup이 두 런타임 스킬 브리지를 모두 배포한다.
- 2026-06-02: README 신규 프로젝트 흐름에는 한 줄 안내만 추가. 절차 SSOT는 `harness-init` 스킬 본문이다.
- milestones_sample.md는 `docs/guides/`에 위치. docs.md 폴더 규칙상 guides/ = "어떻게 하나?" 적합
- sample 파일이라 abbr 없이 `milestones_sample.md` (전역 마스터 파일명 패턴)
- CPS 갱신: 없음

## 메모
- advisor 결과(2026-06-02): 권고안은 “PRD → harness-init 답변 초안 → 기존 init 흐름으로 검증/확정”. h-setup 변경과 완전 자동 생성은 각각 책임 비대화·silent override 위험으로 제외.
- advisor 결정(2026-05-03): 결정 B는 two-way, 결정 A도 two-way, 결정 D는 권고만
- BMAD 에픽 원칙 직접 차용: "Database Setup 같은 기술 레이어명 에픽 = FAILURE"
