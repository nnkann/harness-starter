---
title: 자가 발화 의존 규칙의 일반 실패 — P8 등록 + debug-guard.sh 확장
domain: harness
problem: P8
solution-ref:
  - S8 — "강제 트리거 우선 + 자가 의존 보조"
tags: [bit, self-invocation, downstream, debug-guard, hook]
relates-to:
  - path: decisions/hn_eval_harness_cli_lsp_drift.md
    rel: caused-by
status: completed
created: 2026-05-10
updated: 2026-05-10
---

# 자가 발화 의존 규칙의 일반 실패

## 사전 준비
- 읽을 문서:
  - `.claude/rules/bug-interrupt.md` (BIT 트리거 정의)
  - `.claude/scripts/debug-guard.sh` (UserPromptSubmit hook — 패턴 확인 필요)
  - `.claude/HARNESS_MAP.md` `## CPS` + Rules 섹션 (P# 추가 위치)
  - `docs/guides/project_kickoff.md` Problems 섹션 (P8 추가 위치)
  - `docs/decisions/hn_bug_interrupt_triage.md` (BIT 설계 의도 — debug-specialist 인용)
- 이전 산출물:
  - 본 wave 모체: `WIP/decisions--hn_eval_harness_cli_lsp_drift.md` `## 발견된 스코프 외 이슈` 섹션
  - debug-specialist 진단 (2026-05-10) — 원문 본 WIP `## 메모`에 보존
- MAP 참조: HARNESS_MAP `## CPS` 테이블에 P8 행 추가 필요

## 목표

**핵심 명제**:
> 규칙·스킬·문서가 "Claude가 알아서 발화·준수한다"는 자가 의존 메커니즘에
> 의존하면, 다운스트림에서 사실상 비활성된다. 강제 트리거(hook·pre-tool
> 차단·UserPromptSubmit) 없는 규칙은 starter에서 가시성 착시로 작동한 듯
> 보이지만 실제로는 사용자·Claude가 그 규칙을 "떠올리는 빈도"에 비례할 뿐
> 메커니즘이 작동하는 게 아니다.

**증상 3종 통합**:
1. 다운스트림 write-doc 스킬 우회 (스킬 발화 자가 의존)
2. CLAUDE.md 명시 사항 무시 (텍스트 규칙 자가 준수)
3. BIT(bug-interrupt) 다운스트림 발화 0건 — LSP "에러 무지하게 나는" 상태에서도 (자가 발화 실패의 결정적 증거)

**본 wave 스코프**:
- Phase 1: P8 신규 등록 (CPS Problems 섹션 + HARNESS_MAP 갱신)
- Phase 2: debug-guard.sh 확장 (BIT 트리거 키워드 추가) — 가장 가벼운 개입,
  3개 증상 중 BIT 미발화에 직접 효과
- Phase 3: 회귀 가드 + MIGRATIONS

**스코프 외 (별 wave 후보)**:
- write-doc 스킬 우회 강제 트리거 (PreToolUse Write hook 등) — 메커니즘 복잡
- CLAUDE.md 무시 패턴의 메커니즘 보강 (구조 자체 재설계 필요)
- Solution 메커니즘 자체 변경 (owner 승인 필수)

## 작업 목록

### Phase 1. CPS P8 등록 + HARNESS_MAP 갱신

**사전 준비**:
- docs.md "CPS 변경 권한" 표: Problem 추가는 Claude 단독 가능 (BIT Q3 경로
  또는 implementation Step 0). 본 wave는 후자.
- Solution 정의는 owner 승인 필수 — Phase 1에서 Solution은 1차 초안만,
  최종 메커니즘 변경 동반 시 owner 알림.

**영향 파일**:
- `docs/guides/project_kickoff.md` (Problems 섹션 + Solutions 섹션)
- `.claude/HARNESS_MAP.md` (CPS 테이블 P8 행 추가, defends-by·served-by
  컬럼 갱신)

**Acceptance Criteria**:
- [x] Goal: P8 "자가 발화 의존 규칙의 일반 실패"가 CPS Problems 섹션에
      등록되고 HARNESS_MAP CPS 테이블에 반영됨
  검증:
    review: review-deep
    tests: 없음 (CPS 본문 변경 — 박제 검증은 다음 commit pre-check이 수행)
    실측: project_kickoff.md Problems 섹션에 P8 정의 확인 + HARNESS_MAP
      grep "P8" hit 1+
- [x] P8 정의 본문: 증상·영향·승격 상태 3 섹션 (P1~P7 형식 답습)
- [x] Solution S8 1차 초안: "강제 트리거(hook 우선) + 자가 의존 보조"
      방향 명시. 충족 기준 정의는 owner 승인 후 확정 — 본 wave는 1차 초안
      만 박제, 충족 기준은 별도 wave에서 owner 합의 후
- [x] HARNESS_MAP CPS 테이블 P8 행: defends-by 컬럼은 본 wave Phase 2의
      debug-guard.sh 확장 반영, served-by 컬럼은 debug-guard.sh 명시
- [x] 다운스트림 보고서·BIT 미발화 실측 사례를 Solution 충족 기준 검증
      근거로 본문 인용

### Phase 2. debug-guard.sh 확장 — BIT 트리거 키워드 추가

**사전 준비**:
- debug-guard.sh 본문 확인 (debug-specialist 미열람 — 본 Phase에서 Read)
- 기존 키워드 패턴 + 신규 추가 패턴 정합 확인
- 출력 메시지에 BIT Q1/Q2/Q3 블록 형식 안내 추가 (rules/bug-interrupt.md
  "판단 블록 형식" 답습)

**영향 파일**:
- `.claude/scripts/debug-guard.sh`
- `.claude/scripts/test-debug-guard.sh` 또는 `tests/test_debug_guard.py`
  (회귀 가드 — 기존 패턴 확인 후 결정)

**Acceptance Criteria**:
- [x] Goal: 사용자 발화에 "버그·이상·왜 안 돼·이거 깨졌네·에러 무지하게·
      이상하게·이거 왜·작동 안 함" 류 키워드가 감지되면 debug-guard.sh가
      기존 debug-specialist 안내 + BIT Q1/Q2/Q3 블록 적용 안내를 함께 출력
  검증:
    review: review
    tests: bash .claude/scripts/test-debug-guard.sh (기존 테스트 패턴 답습)
    실측: 픽스처 발화 5종(BIT 트리거 키워드 포함/미포함)에서 정확히 분기
      출력 확인
- [x] 키워드 패턴: 기존 debug-guard.sh 패턴과 OR 조합. 정규식 token
      기반(공백 포함 매칭 회피 — hooks.md 금지 패턴 준수)
- [x] 출력 메시지: "BIT 적용 — 발견 즉시 Q1/Q2/Q3 판단 블록 작성 후 진행"
      한 줄 + rules/bug-interrupt.md 경로 명시
- [x] 기존 debug-specialist 호출 안내와 충돌 없음 (둘 다 출력 가능)
- [x] hooks.md "argument-constraint 패턴 금지" 위반 없음 — matcher가 아닌
      hook 스크립트 본문에서 토큰 검사

### Phase 3. 회귀 가드 + MIGRATIONS + bug-interrupt.md 보완

**사전 준비**:
- bug-interrupt.md 본문에 "강제 트리거 보완" 절 추가 (자가 발화만으로는
  불충분하다는 메커니즘 한계 명시)
- MIGRATIONS.md 회귀 위험 섹션: no-speculation.md 단정 표현 금지

**영향 파일**:
- `.claude/rules/bug-interrupt.md` (강제 트리거 절 추가)
- `docs/harness/MIGRATIONS.md` (본 버전 섹션)
- `.claude/scripts/tests/` 또는 `test-debug-guard.sh` (회귀 가드)

**Acceptance Criteria**:
- [x] Goal: bug-interrupt.md에 강제 트리거 보완(debug-guard.sh 키워드 감지)
      메커니즘 명시 + MIGRATIONS 다운스트림 영향 안내 + 회귀 가드 테스트
      통과
  검증:
    review: review
    tests: bash .claude/scripts/test-debug-guard.sh
    실측: harness-upgrade 시나리오에서 다운스트림 debug-guard.sh 자동
      교체 확인 (수동 액션 없음 — h-setup.sh가 scripts/ 전체 복사)
- [x] bug-interrupt.md 신규 절: "## 강제 트리거 (debug-guard.sh)" — 자가
      발화 한계 + 키워드 감지 보강 메커니즘 1줄 + 키워드 목록은 SSOT를
      debug-guard.sh로 위임 (룰에 박지 않음)
- [x] MIGRATIONS.md 본 버전 섹션: 자동 적용 (h-setup.sh가 scripts/ 복사) +
      수동 적용 없음. 회귀 위험은 측정 범위 명시 (Windows + Git Bash 환경
      한정 검증)
- [x] 회귀 가드 테스트: 기존 BIT 트리거 키워드 + 신규 키워드 모두 검출,
      false-positive 케이스(일반 발화) 미검출 확인

## 결정 사항

### Phase 3 완료 (2026-05-10)

- **bug-interrupt.md "## 강제 트리거 (debug-guard.sh)" 절 신설**: "기존
  rules와의 관계" 직전에 배치. 자가 발화 한계 명시 + hook 보강 메커니즘
  + 키워드 SSOT를 debug-guard.sh로 위임 (룰에 박지 않음 — 사전 변경 시
  hook 1곳만 갱신). hook 한계도 명시 (Q1/Q2/Q3 작성·CPS 매칭 의무는 자가
  인지 영역으로 잔존).
  → 반영: `.claude/rules/bug-interrupt.md`
- **MIGRATIONS.md v0.39.0 항목 추가** (minor — 신규 회귀 가드 스크립트): P8 신설 + 키워드 사전 17개 + 회귀
  가드 22/22 + bug-interrupt.md 절 + HARNESS_MAP P8 행 — 본 wave 전체 변경
  요약. 자동 적용(h-setup.sh가 scripts/ 복사). 회귀 위험은 측정 범위
  (Windows + Git Bash) 명시 + Linux/macOS 미테스트 명시 (no-speculation.md
  "단정 표현 금지" 준수).
  → 반영: `docs/harness/MIGRATIONS.md`
- **CPS 갱신**: 없음 (Phase 1에서 P8/S8 등록 완료)

### Phase 2 완료 (2026-05-10)

- **debug-guard.sh 키워드 사전 단일화**: 자연어 추측 패턴("이거 왜 안돼" 등)
  전면 제거. 키워드 사전 17개 — 한국어 `에러|버그|실패|오류|크래시|충돌`,
  영어 `error|bug|fail|exception|panic|crash|traceback|stacktrace|regression|
  broken|conflict`. 제외: `예외`(exception 영문판으로 충분), `망가`(자연어),
  `반복`(false-positive 큼), `원인`(증상 키워드와 동행하므로 단독 트리거
  불필요 — "원인 분석해줘"류 false-positive 회피). hit 시 debug-specialist
  안내 + BIT Q1/Q2/Q3 안내 둘 다 출력.
  → 반영: `.claude/scripts/debug-guard.sh`
- **인과 흐름 명시 (2026-05-10 사용자 정정)**: 원인 → 증상(버그·충돌·에러)
  → BIT 트리거. "원인" 자체는 분석 요청일 수 있어 트리거 영역 아님. 진짜
  버그 맥락이면 증상 키워드가 동행해서 잡힘.
- **회귀 가드 신설**: `.claude/scripts/test-debug-guard.sh`. 키워드 사전 정확
  매칭 케이스만(자연어 픽스처 금지). hit 17 / miss 5 = 22/22 통과. M5는
  "원인 분석해줘" false-positive 가드.
  → 반영: `.claude/scripts/test-debug-guard.sh`
- **사용자 피드백 반영 (2026-05-10)**: 1차 시도에서 자연어 패턴("이상하게|
  왜 안|작동 안|깨졌|이거 왜" 등) 추가 + 픽스처도 자연어로 작성 → 사용자
  지적("관련어만 넣어도 충분, 자연어 추측 금지") → no-speculation.md "추측
  단정형 금지" 위반 인정. 키워드 사전 단일화로 재작성.
- **CPS 갱신**: 없음 (Phase 1에서 P8/S8 등록 완료, Phase 2는 S8 1차 보강
  메커니즘 구현 — 충족 기준 변경 없음)

### Phase 1 완료 (2026-05-10)

- **P8 정의 등록**: `docs/guides/project_kickoff.md` line 128 "P8. 자가 발화
  의존 규칙의 일반 실패". 증상·실측 사례·영향·구조적 불균형·승격 상태 박제.
  → 반영: project_kickoff.md
- **S8 1차 초안 등록**: project_kickoff.md line 281 "S8 (for P8): 강제 트리거
  우선 + 자가 의존 보조 [1차 초안]". 충족 기준 확정은 owner 승인 후 명시.
  cascade 영향 검토 전까지 본 Solution 인용은 `(부분)` 마커 권장 명시.
  → 반영: project_kickoff.md
- **HARNESS_MAP CPS 테이블 P8 행**: line 65. defends-by=bug-interrupt(강제
  트리거 보강 진행 중), served-by=debug-guard.sh(BIT 트리거 키워드 확장
  진행 중). ⚠️ S8 1차 초안 마커.
  → 반영: HARNESS_MAP.md
- **실행 흐름 분리**: P8 자체 등록 + S8 1차 초안은 Claude 단독 판단(docs.md
  CPS 변경 권한). S8 충족 기준 확정 + cascade 영향 검토는 owner 승인 후
  별도 흐름 — 본 wave Phase 2(debug-guard.sh 확장)는 1차 초안 보강이라
  단독 진행 가능
- **CPS 갱신**: P8 신설 + S8 1차 초안. project_kickoff.md `## 메모`에
  "P8은 2026-05-10 다운스트림 LSP 결함 BIT 미발화 실측 기반" 박제

## 메모

- **실행 순서**: 1번째 (선행). 선행 조건: 없음.
  - 모체 wave(`decisions--hn_eval_harness_cli_lsp_drift.md`)와는 독립.
  - 본 wave가 가벼운 개입 + 즉시 효과 — 모체 wave 진행 전에 끝내면 다음
    작업부터 BIT 트리거 보강 작동.

- **BIT 발화 실패 결정적 증거 (사용자 실측, 2026-05-10)**: 다운스트림에서
  LSP stale dist 결함 발생, "에러 무지하게 나는" 상태에서도 BIT 한 번도
  발화 안 함. Q3=YES 명백한 케이스(조용한 실패 + 다운스트림 전파 + 자동
  발견 어려움)에서 메커니즘 0 작동.

- **debug-specialist 진단 원문 보존 (2026-05-10)**:

  > 원인 판정 (특정 성공): BIT는 자가 발화 의존 규칙이고, 강제 트리거
  > (hook·pre-tool 차단)가 없다.
  >
  > - rules/bug-interrupt.md:14~17: "스코프 외 버그·이슈를 발견한 즉시
  >   이 규칙을 적용한다" — 발견 자체를 Claude가 자각해야 시작됨.
  > - HARNESS_MAP.md:81 enforced-by=review (커밋 시점, 사후). 작업 중
  >   강제 메커니즘 0.
  > - session-start.py already reads the recorded sections, but does not induce discovery.
  >
  > 구조적 불균형: P1을 defends하는 다른 규칙(no-speculation,
  > internal-first)은 hook(debug-guard.sh UserPromptSubmit) 강제력이
  > 있는데, BIT만 강제력 0.

- **세 증상 통합 인식**: write-doc 우회 + CLAUDE.md 무시 + BIT 미발화 모두
  자가 의존 메커니즘 실패의 변종. 본 wave는 그중 BIT만 처리(가장 가벼운
  개입). 나머지 두 증상은 P8 본문에 같은 P 정의 안에 박제하되 Solution
  메커니즘은 별 wave 후보로 메모.

- **CPS 변경 권한**: P8 추가는 Claude 단독 (BIT Q3 경로 + implementation
  Step 0 매칭 결과). Solution S8 충족 기준 정의는 owner 승인 필수 —
  Phase 1에서 1차 초안만 박제, 충족 기준 확정은 owner 합의 후 별 wave.

- **본 wave가 자기 사례 검증**: 본 wave가 도입하는 debug-guard.sh 확장이
  작동하면, 다음에 사용자가 "에러" 키워드 발화 시 BIT 안내가 자동 출력 →
  자가 발화 의존 → 강제 트리거 의존으로 전환. 작동 확인은 운용에서.

- **본 wave Solution 충족 기준 1차 초안 (S8)**:
  - 자가 발화 의존 규칙(BIT 등) 미발화 패턴 다운스트림에서 발생 시 강제
    트리거(hook)가 보강 안내 출력
  - debug-guard.sh가 기존 debug-specialist 트리거 + BIT 트리거 둘 다 커버
  - 다운스트림 운용에서 BIT 발화 빈도 측정 가능 (signal 파일 또는 로그)
  - **owner 승인 필요**: 위 3개 모두 본 wave에서 1차 초안. 최종 충족 기준
    합의 + cascade 영향 검토 후 확정.

## 발견된 스코프 외 이슈

- commit 흐름 자체가 P8 자기증명 (사용자 발화 의존 + 텍스트 규칙 자가 준수 패턴) — 본 wave commit 진행 중 5건 발생: (1) wip-sync 자동 move 미작동 — AC 자가 마킹 의존, (2) status `completed` 자동 전환 부재 — implementation Step 4 텍스트 규칙 자가 준수, (3) README 갱신 누락 + MIGRATIONS 헤더 추측 — 메모리 자가 회상 의존. 3건 모두 `/commit` 발화 단일 트리거에 직렬 연결된 메커니즘이 사용자 발화 자체에 의존. 발견: commit 흐름 진행 중 사용자 지적("문서 완료처리는 왜 안하지?") | P#: P8 (변종 — starter 자기 적용 사례)
- P8 정의 본문이 starter 자기 적용을 누락 — `project_kickoff.md` line 132 주문장 "다운스트림에서 사실들 비활성된다"가 starter를 암묵적으로 예외 프레이밍. 본 wave 진행 중 5건 자기증명이 실측인데 P8 본문에 0건 반영. 발견: debug-specialist 진단 (2026-05-10) | P#: P8 (정의 보강 — starter 자기 적용 명시)
- 선행 사례 박제만으로 안 잡힘 — `docs/incidents/hn_commit_process_gaps.md` (2026-04-27) 2주 전 박제됐는데 동일 5건 패턴 재발. incident 문서 자가 회상 의존이 작동 안 함. 발견: debug-specialist 선행 사례 탐색 결과 | P#: P8 (변종 — incident 회상 의존)
