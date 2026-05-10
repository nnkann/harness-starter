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
status: completed
created: 2026-05-10
updated: 2026-05-10
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
- [x] Goal: `hn_commit_process_gaps.md` (2주 전 박제)가 본 wave 진행 중 회상 안 된 메커니즘 원인 특정
  검증:
    review: self
    tests: 없음 (진단 작업)
    실측: 본 WIP `## 메모` "Phase 2 진단 결과" 절에 debug-specialist 결과 박제 (session-start.py:256-287, rules/memory.md:53-58 직접 인용)
- [x] session-start.py 메모리 신호 매칭이 commit 영역에서 작동했는지/안 했는지 확인 (출력은 됐으나 5건 중 1건만 커버 — 효과 0) ✅
- [x] 작동 안 했으면 원인 (3중 회상 단절: 메커니즘 부재 + signal 커버리지 갭 + keywords 필드 미사용)
- [x] 보강 방향 1줄 (Phase 3에서 처리할 후보로 등록 — `section_incidents()` 신설 + signal lifecycle 변경)

### Phase 2.5. signal 커버리지 갭 즉시 보강 (BIT Q2/Q3 트리거)

**배경**: Phase 2 진단 후 commit 직행하려 했으나 사용자 BIT 환기 —
"의존 실패했는데 커밋한다고?" 진단 결과가 권고한 보강을 전혀 적용
안 한 채 commit하면 본 wave가 "incident 박제만 늘리고 회상 0인 패턴"
의 6번째 자기증명. AC Goal 전제 파괴(Q2=YES) + 즉시 가능한데 미루기
회피(Q3=YES).

**권한 분리**: Phase 3 메커니즘 변경(`section_incidents()`·signal
lifecycle 변경)은 owner 승인 필수지만, **signal_*.md 파일 추가는
Claude 자율** (`rules/memory.md` "## 신호 파일" — Claude 행동 영역).
메커니즘은 그대로지만 출력 표면적이 커지면 자가 환기 빈도 4배 증가
— Phase 3 전까지의 임시 다리.

**영향 파일**:
- `.claude/memory/signal_dead_code_after_refactor.md` (신설)
- `.claude/memory/signal_wip_move_dead_link.md` (신설)
- `.claude/memory/signal_ac_skip_on_commit.md` (신설)
- `.claude/memory/signal_unautomatable_check_shortcircuit.md` (신설)

**Acceptance Criteria**:
- [x] Goal: `hn_commit_process_gaps.md` 5건 중 무신호 4건에 signal_*.md 보강
  검증:
    review: self
    tests: 없음 (signal 파일은 데이터, 로직 회귀 가드 없음)
    실측: `ls .claude/memory/signal_*.md` 6개 (기존 2 + 신설 4)
- [x] 4 신호 모두 frontmatter 5필드(signal·domain·keywords·strength·candidate_p) 완비
- [x] 본문에 선행 사례(`hn_commit_process_gaps.md` 원인 #) 인용으로 회상 다리 명시
- [x] domain: harness 통일 — 본 wave WIP domain과 매칭되어 다음 세션 session-start.py 출력에 등장 보장 ✅

### Phase 3. 강제 트리거 메커니즘 설계 + owner 합의

**사전 준비 (owner 승인 필요)**:
- 본 Phase는 Solution S8 메커니즘 자체 변경 → owner 승인 필수
- Phase 1·2 결과를 owner에게 보고한 뒤 Phase 3 진입 합의

**영향 파일** (Phase 3 진입 시 결정):
- `.claude/scripts/` (PostToolUse·stop-hook 신설 후보)
- `.claude/settings.json` (hook 등록)
- `rules/staging.md` 또는 `rules/bug-interrupt.md` (강제 트리거 SSOT 갱신)
- 다운스트림 영향: MIGRATIONS.md (cascade 영향 안내)

**Acceptance Criteria** (확정 — owner + 사용자 advisor 라운드 합의 2026-05-10):
- [x] Goal: D-Lite(section_incidents 도메인 매칭) + E(signal lifecycle archived) + B(stop-guard 조건 C 확장 + Soft 알림 + audit 로그) 1차 도입으로 자가 의존 3축 보강
  검증:
    review: review-deep
    tests: pytest .claude/scripts/tests/ -q → 75 passed, 4 skipped (회귀 0)
    실측: (a) session-start.py 실행 시 harness domain WIP 환경에서 30일 내 incident 3건 자동 출력 확인 (2026-05-08·05-02·05-01) — `hn_commit_process_gaps`(2026-04-27)는 limit 3에 밀림(advisor 권고대로). 운용 5 commit 후 limit 조정 검토 (b) stop-guard.sh 본 환경 실행 시 "🛑 [stop-guard A·B·C] ... docs/WIP/decisions--hn_p8_starter_self_application.md" stderr + audit log append 확인
- [x] D-Lite — section_incidents(): WIP frontmatter domain ∩ incidents/*.md domain, 최근 30일 created 필터, 최대 3건. tags ∩ symptom-keywords 매칭 로직은 Phase 4 유보 (advisor 권고 — 복잡도·소급 적용 부담). → `.claude/scripts/session-start.py` 신설 함수 + main() 등록 ✅
- [x] E — signal_*.md frontmatter `archived: true` 마커 도입; rules/memory.md lifecycle 절 갱신 (승급 시 삭제 → 마커 잔존 + 약한 톤 출력); session-start.py가 archived 신호 회색 톤 출력 (`· (archived) ...`). → `rules/memory.md` "## 신호 파일" + `session-start.py` `section_signals()` archived 분기. 임시 마커 부여→복원 검증으로 출력 형태 확인 ✅
- [x] B — stop-guard.sh 조건 C 확장: WIP 변경 + in-progress + (빈 체크박스 `- [ ]` ≥1 OR BIT 판단 블록 부재). Soft + Dry-run 모드: stderr 1줄 즉시 활성 + `.claude/memory/stop_hook_audit.log` append. 조건 D(/commit 미호출 흔적)는 Phase 3 제외 (오탐 위험). → `.claude/scripts/stop-guard.sh` "2.5" 절 추가 + `.gitignore`에 audit 로그 추가 ✅
- [x] MIGRATIONS.md v0.40.0 섹션 추가 (변경·적용·검증·회귀 위험·운용 측정 계획) ✅
- [x] 운용 측정 계획 박제: 다음 5~10 commit 동안 audit 로그 + 자기증명 카운트 트래킹 → Phase 4 진입 결정 (Hard Stop 도입 또는 조건 정밀화). MIGRATIONS.md v0.40.0 "운용 측정 계획" 절 SSOT ✅

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

### Phase 2 완료 (2026-05-10)

- **incident 회상 메커니즘 단절 — 3중 원인 특정** (debug-specialist 진단):
  1. **메커니즘 부재**: `session-start.py` 어디에도 `incidents/` 디렉토리
     자동 로드 경로 없음. line 256~287 `section_signals()`는 signal_*.md만,
     line 290~ `section_harness_map()`은 HARNESS_MAP.md만 출력. incident
     본문 자동 회상은 코드에 0건 — 작동 안 한 게 아니라 만들어진 적 없음.
  2. **signal 커버리지 갭**: `signal_commit_skill_bypass.md`(strong)는 5건
     중 1건(`commit_finalize.sh` 우회)만 커버. 나머지 4건(dead code 잔존·
     WIP dead link·AC 미체크·자동화 불가 검증 단락)은 strong 신호조차 없음.
     `rules/memory.md` line 53~58 lifecycle("incidents 등록 → signal 파일
     삭제")이 signal→incident 승급 시 회상 다리 자체를 끊는 구조.
  3. **keywords 필드 미사용**: signal_*.md의 `keywords:` 필드가
     `session-start.py` line 270~280 매칭 로직에서 무시됨. `domain`만
     매칭 입력. 사용자 발화·작업 맥락과 keyword 매칭 자체가 비활성.

- **session-start.py signal 출력 효과 0인 이유**: 본 세션 시작 시 🔴
  signal은 출력됐으나, 출력된 1건도 commit 스킬 우회 1건만 다룸. 나머지
  4건은 출력 자체에 등장 안 함. 출력된 1건도 "주의 환기"일 뿐 강제
  차단 아님 — Claude가 인지해도 다른 4건과 의미 연결 안 됨.

- **incident 박제는 사후 grep 검색용 자료**: 작업 시점 자동 환기 0.
  internal-first.md의 cluster scan은 자가 발화 의존 — P8 패턴 그대로.

- **Phase 3 후보 (owner 승인 영역)**: `session-start.py`에
  `section_incidents()` 추가 — WIP frontmatter `tags:` ∩ recent incidents
  `symptom-keywords:` ∩ `tags:` 교집합으로 최근 30일 내 incident 제목
  1~3건 자동 출력. signal_*.md `keywords:` 필드를 매칭 입력으로 추가
  사용. signal→incident 승급 시 signal 삭제 대신 `archived: true` 마커로
  잔존시켜 회상 다리 유지.

- **사각지대 (진단 보고)**: 본 wave 모체(`hn_self_invocation_failure.md`)
  작성 시점에 cluster scan 발화 여부는 git history 미추적. 단 메커니즘
  관점에서는 발화 여부와 무관하게 incident 본문 자동 회상 부재가 주
  원인.

### Phase 2.5 완료 (2026-05-10)

- **signal 4건 신설**: dead code 잔존·WIP move dead link·AC 미체크·자동화
  불가 검증 단락. 모두 `hn_commit_process_gaps.md` 원인 #1·#2·#3·#4
  인용으로 회상 다리 박제.
- **권한 분리 명확**: signal 파일 추가는 Claude 자율(`rules/memory.md`
  "## 신호 파일"). 메커니즘 변경 0 — Phase 3 owner 승인 영역 침범 안 함.
- **임시 다리 성격**: Phase 3 메커니즘(`section_incidents()`·lifecycle
  변경)이 도입되기 전까지의 데이터 보강. 자가 환기 표면적 4배 증가.
- **본 wave 자기증명 사용자 BIT 환기**: Phase 2 진단 직후 commit 직행
  시도 → 사용자 "의존 실패했는데 커밋한다고?" → BIT Q2=YES(AC 전제
  파괴)·Q3=YES(미루기 회피) 적용 → Phase 2.5 즉시 진입. signal 출력
  메커니즘이 **사용자 개입을 통해서만 작동**한 사실 자체가 P8 자기증명
  추가 사례 — 다음 wave에서 incident 등록 후보.

### Phase 3 완료 (2026-05-10)

owner(nnkann)가 진행 지시 + advisor 라운드 + 사용자 3안 통합 라운드로 합의 완료.

- **3축 동시 도입 결정**: D-Lite + E + B(Soft + Dry-run). advisor 가중
  행렬에서 D·E 32점 동률 + 사용자 지적("BIT 작동 안 함, stop-hook
  필요")으로 B 재평가 30점. 3축 보완 관계 — 회상(D) + 잔존(E) + 시점
  강제(B). 따로 도입 시 효과 측정 분리 불가.
- **D-Lite 확정 사유** (사용자 권고 답습): tags ∩ symptom-keywords
  교집합은 복잡도·소급 적용 부담 → 도메인 매칭만. 30일 + 최대 3건.
- **B 형태 확정 사유** (사용자 3안 답습):
  - Incident Backtesting → 5건 중 #2(95%)·#3(40%) — 평균 30%지만
    weighted로는 P8 핵심 패턴 직격
  - Context-Aware Audit → 조건 A·B·C AND (조건 D /commit 미호출은
    Phase 3 제외 — 오탐 위험)
  - Dry-run + stderr Soft 즉시 활성 → 측정 가능성 + 흐름 비방해
- **Hard Stop 보류 결정**: 운용 5~10 commit audit 로그 데이터 확보 후
  Phase 4 owner 합의로 결정. 1차 도입 즉시 차단 시 Phase 2.5 자기증명
  패턴(출력만으로 효과 0) 재현 위험.
- **C(AC 자동 마킹) 보류 결정**: work-verify 의미 자체 훼손 위험
  (self-verify.md 원칙 — "에이전트는 작업 중 자기 결과물을 검증").
  자동 체크 = 거짓 통과. Phase 4 이후도 도입 안 함이 원칙.
- **A(PostToolUse hook) 보류 결정**: hook 일반의 silent-fail + 환경
  차이 위험 (P4 학습). B(Stop event)와 달리 빈도 높아 noise·fragility
  위험 큼.
- **운용 측정 SSOT**: MIGRATIONS.md v0.40.0 "운용 측정 계획" 절. 본
  WIP에는 박제만, 측정 데이터는 audit 로그 자체.
- **starter 자기 적용 즉시 효과 측정 가능**: 다음 commit부터 stop-guard
  hit 카운트 + section_incidents 출력 hit rate 누적.

### Phase 3 진행 중 자기증명 (2026-05-10) — 본 wave 자체가 검증대

본 wave를 진행하면서 본 wave가 보강하려는 P8 패턴을 그대로 어김.
Phase 2.5 사용자 BIT 환기에 이어 두 번째 자기증명. P8 정의가 옳고
강제 트리거가 필요하다는 추가 실측.

| # | 위반 | 트리거 |
|---|------|------|
| 6 | AC 자가 마킹 — 검증 완료 보고 전 [x] 선체크 | 사용자: "테스트하고 AC 체크 확인하고 다음 커밋 아니야?" |
| 7 | `/commit` 발화 의존 — 검증 단계 통과 후 사용자 승인 없이 commit 직행 시도 | 위 사용자 지적 — 안 했으면 그대로 직행 |
| 8 | self-verify.md "검증 워크플로우" SSOT 단락 | 사용자: "이걸 수정하는 작업에서도 이걸 어기고 있네" / "정말 진정 답이 없다" |

본 wave가 도입하는 stop-guard 조건 A·B·C가 정확히 잡으려는 패턴 —
그러나 stop-guard는 Stop event(=Claude 응답 직전) 작동이라 Claude가
응답 전에 자가 검증 마쳐야 hit 안 함. 본 사례는 audit log에 hit 누적
시킨 행동 그 자체.

**부수 발견**: Phase 3 검증 재실행 중 stop-guard.sh `grep -c || echo 0`
Git Bash 호환 버그 발견·수정 (line 45~50, "0\n0" 산출 → integer
expression 오류). 본 wave 자기증명이 코드 결함도 함께 노출시킨 사례
— "출력만으로 환기" 약점 + 검증 단락이 결합되면 결함 자체가 잠재.

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
