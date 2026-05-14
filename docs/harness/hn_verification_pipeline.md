---

title: 검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제
domain: harness
tags: [skill, harness-dev, commit, implementation, ac, cps, migration]
problem: P2
s: [S2]
status: completed
created: 2026-04-28
---

# 검증 파이프라인 강화

## 사전 준비
- 읽을 문서:
  - `docs/harness/hn_migrations_version_gap.md` — Task 1(harness-dev 버전 범프 절차) SSOT
  - `docs/guides/project_kickoff.md` — P6/S6 해결 기준
  - `.claude/skills/commit/SKILL.md` — Step 4 현재 내용
  - `.claude/skills/harness-dev/SKILL.md` — Step 5/6 현재 내용
  - `.claude/skills/implementation/SKILL.md` — Step 2.5/4 현재 내용
- 이전 산출물: 없음

## 목표
- CPS 연결: P6 "검증망 스킵 패턴" → S6 해결 기준 충족
  - "SKILL.md 변경 커밋에 pytest 실행 기록"
  - "SKILL.md 절차 변경 시 MIGRATIONS.md 해당 버전 섹션 동반"
  - "WIP AC 완료 후 CPS Solution 항목 갱신 여부 명시적 확인"

## 작업 목록

### 1. migration-log.md 경로 수정
> kind: bug

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`, `docs/harness/MIGRATIONS.md`

**문제**: `migration-log.md`가 경로 없이 기술돼 다운스트림 루트에 생성됨. `docs/harness/` 하위가 맞음.
**→ 완료** (이미 수정됨)

**Acceptance Criteria**:
- [x] `grep "migration-log" .claude/skills/harness-upgrade/SKILL.md` 결과에 `docs/harness/migration-log.md` 만 존재
- [x] `grep "migration-log" docs/harness/MIGRATIONS.md` 동일 확인

### 1.5. MIGRATIONS.md 구조 재설계 — 현재 버전 1개만 유지
> kind: refactor

**영향 파일**: `docs/harness/MIGRATIONS.md`, `.claude/skills/harness-upgrade/SKILL.md`

**결정**: MIGRATIONS.md = 현재 적용 대상 버전 섹션 1개만. 업그레이드 완료 시 harness-upgrade가 해당 섹션 삭제. 히스토리는 git log가 SSOT. 기존 v0.8~v0.25 섹션 전부 제거.

**Acceptance Criteria**:
- [ ] MIGRATIONS.md에 v0.8~v0.25 섹션 없음
- [ ] MIGRATIONS.md 상단 설명에 "현재 버전 섹션 1개만 유지" 명시
- [ ] harness-upgrade SKILL.md Step 10에 "업그레이드 완료 후 해당 버전 섹션 삭제" 추가
- [ ] v0.26.1 섹션 추가 (현재 최신 — 이번 누락분)

### 2. commit Step 4 → harness-dev MIGRATIONS.md 자동 호출 트리거 추가
> kind: feature

**영향 파일**: `.claude/skills/commit/SKILL.md`

**문제**: 버전 범프 확정 후 MIGRATIONS.md 섹션 작성이 수동. harness-dev Step 5의 MIGRATIONS.md 작성 절차가 자동으로 트리거되지 않음.

**수정 방향**: commit Step 4 "버전을 올릴 때" 항목에 harness-dev Step 5 절차 실행 지시 추가.

**Acceptance Criteria**:
- [ ] commit SKILL.md Step 4에 버전 범프 확정 후 MIGRATIONS.md 섹션 작성 지시 존재
- [ ] staged diff를 기반으로 변경 내용·자동/수동 분류·검증 명령 작성 명시

### 3. implementation Step 2.5 AC 검증 강제화
> kind: feature

**영향 파일**: `.claude/skills/implementation/SKILL.md`

**문제**: "테스트 스위트가 있으면 반드시 실행" 문구가 있지만 실제로 건너뜀. 강제 차단 문구 부재.

**수정**: Step 2.5에 AC 검증 미실행 시 명시적 차단 문구 + 자동화 불가 항목 처리 원칙 강화.

**Acceptance Criteria**:
- [ ] Step 2.5에 "테스트 스위트 실행 결과를 사용자에게 제시하지 않으면 완료 선언 금지" 명시
- [ ] "자동화 불가 항목 → 운용 확인 필요 명시" 의무 문구 존재

### 4. implementation Step 4 CPS 갱신 강제화
> kind: feature

**영향 파일**: `.claude/skills/implementation/SKILL.md`

**문제**: "변경 없음이면 건너뜀"이 묵시적 생략으로 이어짐. WIP ## 결정 사항에 CPS 갱신 여부가 명기되지 않음.

**수정**: Step 4에 "CPS 갱신: 없음"도 명시 의무 추가.

**Acceptance Criteria**:
- [ ] Step 4에 "CPS 갱신 없음도 WIP ## 결정 사항에 명시" 문구 존재

## 결정 사항
- migration-log.md 경로: `docs/harness/migration-log.md` (다운스트림 소유이나 docs/harness/ 위치)
- commit Step 4 트리거: harness-dev를 별도 호출하는 게 아니라 Step 4 절차 안에 MIGRATIONS.md 작성 지시를 직접 포함 (harness-dev는 스킬 추가·삭제 전용, commit은 모든 버전 범프 담당)

## 메모
- CPS 갱신: S6 방어 체계 구현 진행 중 — 이 작업 완료 시 S6 해결 기준 2/3 충족
