---
title: P8 starter 자기 적용 + commit 흐름 강제 트리거 보강
domain: harness
problem: P8
solution-ref:
  - S8 — "강제 트리거 우선 + 자가 의존 보조"
tags: [p8, starter, commit-flow, self-dependency, force-trigger, hook]
relates-to:
  - path: decisions/hn_self_invocation_failure.md
    rel: caused-by
status: in-progress
created: 2026-05-10
---

# P8 starter 자기 적용 + commit 흐름 강제 트리거 보강

## 사전 준비

- 읽을 문서:
  - `docs/decisions/hn_self_invocation_failure.md` (모체 wave — P8/S8 1차 등록 + debug-guard.sh 1차 보강)
  - `docs/incidents/hn_commit_process_gaps.md` (2026-04-27 — 거의 동일한 5건 패턴 선행 박제. incident 회상 의존 실패의 결정적 증거)
  - `docs/guides/project_kickoff.md` line 128~162 (P8 정의 본문 — starter 자기 적용 누락)
  - `.claude/skills/implementation/SKILL.md` "Step 4" (status 전환 텍스트 규칙 자가 준수 위치)
  - `.claude/skills/commit/SKILL.md` "Step 7.5·8" (wip-sync 자동 move 트리거 조건)
  - `.claude/scripts/commit_finalize.sh` (line 44~49 — wip-sync 호출 분기)
  - `.claude/scripts/docs_ops.py` (line 745~777 — cmd_move 트리거 조건)
- 이전 산출물:
  - 모체 wave: `decisions/hn_self_invocation_failure.md` `## 발견된 스코프 외 이슈` 섹션 (별 wave 후보 3건 박제)
  - debug-specialist 진단 (2026-05-10) — 본 wave 진행 중 commit 흐름 5건 자기증명 사례 분석. 원문은 모체 wave `## 메모`에 보존
- MAP 참조: HARNESS_MAP `## CPS` 테이블 P8 행 (defends-by·served-by 컬럼은 본 wave 결과로 갱신 예정)

## 배경

모체 wave(`hn_self_invocation_failure.md`)가 P8을 "자가 발화 의존 규칙의
일반 실패"로 정의하고 debug-guard.sh BIT 강제 트리거를 1차 보강했다. 그런데
**모체 wave commit 흐름 진행 중에 P8 자기증명 5건이 발생**:

| # | 증상 | P8 변종? | 의존 위치 |
|---|------|---------|----------|
| 1 | wip-sync 자동 move 미작동 | **예** | `/commit` 발화 + AC 자가 마킹 |
| 2 | status `completed` 자동 전환 부재 | **예** | implementation Step 4 텍스트 규칙 자가 준수 |
| 3 | solution-ref placeholder 박제 | **아님** | pre-check 박제 검증이 정상 차단 |
| 4 | relates-to 약식 경로 | **아님** | pre-check verify-relates가 정상 차단 |
| 5 | README 갱신 누락 + MIGRATIONS 헤더 추측 | **예** | `/commit` 발화 + 메모리 자가 회상 |

**3건이 P8 변종 — 메커니즘 관점에서 분류**.

debug-specialist 진단(모체 wave `## 메모` 보존):
> 근본 원인 1줄: 하네스의 모든 "완료 처리" 메커니즘(status 전환·wip-sync·
> README 갱신·MIGRATIONS)이 `/commit` 발화 단일 트리거에 직렬 연결돼 있고,
> `/commit` 자체가 사용자 발화 의존(자가 발화 메커니즘) — 즉 P8 정의가
> BIT·스킬 발화·CLAUDE.md만 예시로 들었지 **`/commit` 발화 자체가 같은
> 카테고리**라는 자기 적용을 누락했다.

추가 결정적 증거:
- `docs/incidents/hn_commit_process_gaps.md` (2026-04-27, 14일 전) — 거의
  동일한 5건 패턴이 이미 박제됨. line 60: "commit 스킬을 호출하는 행위
  자체가 '이미 완료됐다'는 암묵적 신호로 작동해, AC 체크 단계가 생략됐다."
- 2주 전 박제 → 오늘 동일 재발 = **incident 박제만으로 안 잡힘**

## 선택지

### 별 wave 후보 3건 — 작업 단위 분해

**1. P8 정의 본문에 starter 자기 적용 명시**
- `project_kickoff.md` line 132 주문장이 "다운스트림에서 사실상 비활성된다"로 시작 → starter 암묵적 예외 프레이밍
- 본 wave 진행 중 5건 자기증명이 실측인데 P8 본문에 0건 반영
- 보강 방향: P8 본문에 "starter 자기 적용" 절 추가. `/commit` 발화 의존을 BIT·write-doc 우회와 같은 카테고리로 분류

**2. commit 흐름 강제 트리거 메커니즘 보강**
- 현재: `/commit` → `commit_finalize.sh` → `wip-sync` 단일 직렬 체인. 사용자 발화 안 하면 메커니즘 0건 작동
- 보강 후보:
  - (A) Phase 종료 시 PostToolUse hook으로 status·AC·README 자동 강제 트리거
  - (B) implementation 스킬 종료 시 stop-hook이 "지금 `/commit` 호출 안 하면 메커니즘 0 작동" 강제 알림
  - (C) AC 체크박스 마킹을 work-verify 시점에 자동화 (현재는 수동)
  - 트레이드오프: hook fragility(P4 학습) vs 자가 의존 차단

**3. incident 박제 회상 의존 실패 진단·보강**
- `hn_commit_process_gaps.md` 2주 전 박제됐는데 회상 안 됨
- session-start.py 메모리 신호 매칭이 `commit` 영역에서 작동 안 하는지 별 진단 필요
- 보강 후보: signal 파일 트리거 조건 점검 + 도메인 매칭 키워드 보완

### 작업 묶음 판정

3건 모두 **P8 자기 적용**이라는 같은 근본 원인 공유. 단일 wave로 묶는 것이
정합. 하지만 Solution 메커니즘 자체 변경(2번)은 owner 승인 필수
(docs.md "CPS 변경 권한") — Phase 분리:

- **Phase 1: P8 정의 본문 갱신** (Claude 단독 가능 — 사실 박제)
- **Phase 2: incident 회상 의존 진단** (debug-specialist + signal 매칭 점검 — 진단만, 메커니즘 변경 없음)
- **Phase 3: 강제 트리거 메커니즘 설계 + owner 합의** (Solution 메커니즘 변경 — owner 승인 필수)

## 결정

**작업 단위**: 단일 wave (`hn_p8_starter_self_application.md`), 3 Phase 분할.

**Phase별 권한·리스크**:
- Phase 1: Claude 단독 (CPS 사실 박제 — Problem 본문 확장은 권한 표 SSOT에 따라 Claude 단독)
- Phase 2: debug-specialist 호출 (진단 작업)
- Phase 3: owner 승인 필수 (Solution 메커니즘 변경 — 강제 트리거 도입은 cascade 영향 큼. P4 hook fragility 학습도 검토 동반)

**스코프 외 (별 wave 후보)**:
- write-doc 스킬 우회 강제 트리거 (모체 wave에서도 별 wave로 인정한 항목 — P8 변종 다른 영역)
- CLAUDE.md 무시 패턴 메커니즘 보강 (구조 자체 재설계 필요)

## 작업 목록

### Phase 1. P8 정의 본문에 starter 자기 적용 명시

**사전 준비**:
- `project_kickoff.md` line 128~162 (P8 정의 본문) Read
- 본 wave commit(`docs/decisions/hn_self_invocation_failure.md`) 참조 — 자기증명 5건 기록 위치
- docs.md "CPS 변경 권한" 표: Problem 본문 확장은 Claude 단독

**영향 파일**:
- `docs/guides/project_kickoff.md` (P8 본문 + Solutions 섹션 메모)
- `.claude/HARNESS_MAP.md` (P8 행 비고 또는 starter 자기 적용 마커 — 필요 시)

**Acceptance Criteria**:
- [x] Goal: P8 정의 본문에 "starter 자기 적용" 절이 추가되어 다운스트림 한정 프레이밍 해소
  검증:
    review: review
    tests: 없음 (CPS 본문 변경 — 박제 검증은 commit pre-check)
    실측: project_kickoff.md P8 섹션에 "starter 자기 적용" 절 grep hit
- [x] starter 자기증명 사례 박제: 본 wave 모체 commit(`hn_self_invocation_failure.md`) 진행 중 5건 자기증명을 P8 본문에 인용
- [x] `/commit` 발화 의존이 BIT·write-doc 우회와 같은 카테고리임을 명시
- [x] 기존 line 132 "다운스트림에서 사실상 비활성된다" 주문장은 유지(다운스트림 사례 부정 아님), starter도 포함되도록 범위만 확장

### Phase 2. incident 회상 의존 실패 진단

**사전 준비**:
- `hn_commit_process_gaps.md` (2026-04-27) 본문 Read
- `.claude/scripts/session-start.py` 메모리 신호 매칭 로직 Read
- `.claude/memory/signal_*.md` 파일 목록 + 본문 점검
- `rules/memory.md` "## 신호 파일 (signal_*.md)" 섹션 참조

**영향 파일**:
- (진단 단계 — 코드 수정 없음. 메모만 기록)
- `docs/decisions/hn_self_invocation_failure.md` 또는 본 WIP `## 메모`에 진단 결과 박제

**Acceptance Criteria**:
- [ ] Goal: `hn_commit_process_gaps.md` (2주 전 박제)가 본 wave 진행 중 회상 안 된 메커니즘 원인 특정
  검증:
    review: self
    tests: 없음 (진단 작업)
    실측: 본 WIP `## 메모`에 debug-specialist 진단 결과 + 메커니즘 위치 line 인용
- [ ] session-start.py 메모리 신호 매칭이 commit 영역에서 작동했는지/안 했는지 확인
- [ ] 작동 안 했으면 원인 (signal 파일 부재? 도메인 매칭 누락? strength 임계?)
- [ ] 보강 방향 1줄 (Phase 3에서 처리할 후보로 등록)

### Phase 3. 강제 트리거 메커니즘 설계 + owner 합의

**사전 준비 (owner 승인 필요)**:
- 본 Phase는 Solution S8 메커니즘 자체 변경 → owner 승인 필수
- Phase 1·2 결과를 owner에게 보고한 뒤 Phase 3 진입 합의

**영향 파일** (Phase 3 진입 시 결정):
- `.claude/scripts/` (PostToolUse·stop-hook 신설 후보)
- `.claude/settings.json` (hook 등록)
- `rules/staging.md` 또는 `rules/bug-interrupt.md` (강제 트리거 SSOT 갱신)
- 다운스트림 영향: MIGRATIONS.md (cascade 영향 안내)

**Acceptance Criteria** (1차 초안 — Phase 3 진입 전 owner 합의로 확정):
- [ ] Goal: commit 흐름 자가 의존 3 변종(`/commit` 발화·AC 자가 마킹·메모리 자가 회상) 중 하나 이상이 강제 트리거로 전환
  검증:
    review: review-deep
    tests: (메커니즘 도입 시 회귀 가드 신설 — Phase 3 진입 시 결정)
    실측: starter 본인의 다음 commit에서 자기증명 0건
- [ ] owner 승인 절차 통과 (P4 hook fragility 학습 + cascade 영향 검토)
- [ ] 다운스트림 영향 안내 (MIGRATIONS.md)

## 결정 사항

### Phase 1 완료 (2026-05-10)

- **P8 본문 "starter 자기 적용 (2026-05-10 자기증명)" 절 추가**: 본문
  "영향" 절과 "구조적 불균형" 절 사이에 삽입. 모체 wave commit 흐름 진행
  중 발생한 3건 자기증명(wip-sync 자동 move 미작동·status 자동 전환 부재
  ·README 갱신 누락 + 메모리 자가 회상 의존) 인용.
  → 반영: `docs/guides/project_kickoff.md` line 153~166
- **`/commit` 발화 의존을 P8 변종으로 명시**: BIT·write-doc 우회·CLAUDE.md
  무시와 같은 카테고리. 사용자 자각 의존 단일 발화 트리거는 모두 자가
  의존 — starter 예외 아님.
  → 반영: `docs/guides/project_kickoff.md` line 167~170
- **선행 사례 회상 의존도 같은 패턴 박제**: `hn_commit_process_gaps.md`
  (2026-04-27, 14일 전)가 거의 동일한 5건 패턴 박제했으나 재발한 사실을
  P8 본문에 반영. incident 박제 자체도 자가 회상 의존이므로 starter
  본인이 자기 증례 회상 안 함을 명시.
  → 반영: `docs/guides/project_kickoff.md` line 172~174
- **구조적 불균형 절 갱신**: 강제력 0인 규칙 목록에 `/commit` 발화 추가
  (BIT·스킬 발화·CLAUDE.md 준수와 병기).
  → 반영: `docs/guides/project_kickoff.md` line 178
- **승격 상태 + 관련 사례 문서 절 갱신**: 1차 보강 완료(v0.39.0) 명시 +
  starter 자기 적용 사례 박제 명시 + 강제 트리거 메커니즘 보강이 owner
  승인 필수임 명시. 본 WIP + 선행 사례 incident 등록.
  → 반영: `docs/guides/project_kickoff.md` line 180~190
- **CPS 갱신**: P8 Problem 본문 확장. Solution S8 메커니즘은 변경 없음 —
  owner 승인 필요 영역. docs.md "CPS 변경 권한" 표 준수.

### Phase 2 (다음 세션)

- 본 세션 스코프 외. 새 세션에서 진행.

### Phase 3 (owner 승인 필수)

- 본 세션 스코프 외. owner 합의 후 진입.

## 메모

- **본 wave 자체가 P8 자기증명 검증대**: 본 wave 진행 중에 같은 패턴이 또
  나오면 메커니즘이 1차 보강(debug-guard.sh)으로 충분치 않다는 추가 증거.
  반대로 자기증명 0건이면 1차 보강이 작동했다는 약한 증거(자기증명을 의식
  하면서 진행한 효과일 수도 있어 강한 증거 아님).

- **owner 승인 경계 명확**: Phase 1(사실 박제)·Phase 2(진단)는 Claude
  단독. Phase 3(메커니즘 변경)만 owner 승인. docs.md "CPS 변경 권한" 표
  + S8 1차 초안의 cascade 회피 마커 정신 답습.

- **모체 wave commit 잔여물**: 모체 wave commit에 동행 commit된 모체 wave
  자체 WIP(`decisions--hn_eval_harness_cli_lsp_drift.md`)는 별 진행 중.
  본 wave와 직접 관련 없음.
