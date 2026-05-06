# HARNESS_MAP.md — 하네스 신경망 허브

> **하향 경로(작업 전)**: CPS + 관련 Rules 섹션을 읽는다. 모든 작업이 통과.
> **상향 경로(문제 발생 시)**: 아래 "역추적 절차"를 따른다. MAP 전체 Read 불필요.

## 유기체 구조

```
하향 (동맥) — 작업 전 항상 통과
  CPS → Rules → Skills/Agents → Scripts
  "무엇을 지켜야 하는가"를 내려보내는 경로.
  작업 전 CPS + 해당 Rules 섹션만 읽으면 충분.

상향 (정맥) — 문제 발생 시 필요한 경로만 거슬러 올라감
  증상 → Problem → defends-by → enforced-by
  전부 거칠 필요 없음. 증상에서 출발해 관련 노드만 탐색.

CPS (뇌)
  목적·기준을 정의하는 판단 중추.
  decisions/·incidents/ 문서에 축적된 성공·실패가 여기로 귀환해
  Problem·Solution 정의를 갱신한다. 같은 실수가 반복되면 CPS가
  그 기억을 흡수하지 못한 것 — 새 Problem 등록 또는 Solution 보완.

HARNESS_MAP.md (대혈관)
  하향 신호(CPS→기관)의 주요 혈관 지도.
  상향 역추적은 MAP 전체가 아닌 절차 기반으로 필요한 노드만 탐색.

docs/ — decisions/·incidents/·guides/ (미세혈관)
  대혈관이 전달하지 못하는 프로젝트 고유 맥락을 채운다.
  업스트림이 설계한 혈관망에 다운스트림이 자기 조직을 붙이는 것.
  이 문서들 없이는 유기체가 starter 수준에 머문다.
```

---

## 읽는 법

- `defends`: 이 규칙이 지키는 CPS Problem
- `defends-by`: 이 Problem을 지키는 규칙들 (역방향)
- `serves`: 이 도구가 충족하는 CPS Solution
- `serves-by`: 이 Solution을 충족하는 도구들 (역방향)
- `enforced-by`: 이 규칙을 실행하는 도구
- `enforced-by-inverse`: 이 도구가 실행하는 규칙들

---

## CPS (왜 — 최상위)

원본: `docs/guides/project_kickoff.md`

| Problem | 정의 1줄 | defends-by (규칙) | served-by (도구) |
|---------|---------|-----------------|----------------|
| P1 | LLM 추측 수정 반복 | no-speculation, internal-first, bug-interrupt, coding, external-experts | implementation, eval, debug-specialist |
| P2 | review 과잉 비용 | staging | commit, review |
| P3 | 다운스트림 사일런트 페일 | (규칙 없음 — 프로세스 방어) | harness-upgrade, downstream-readiness.sh |
| P4 | hook 매처 fragility ⚠️ 차단 성공 기록 없음 | hooks | bash-guard.sh |
| P5 | MCP·플러그인 + 업스트림 발 문서 팽창 (P7과 역설적 충돌) | (규칙 없음 — S5 MVR 전략으로 방향 전환) | — |
| P6 | 검증망 스킵 | self-verify, pipeline-design | harness-dev, eval |
| P7 | 구성요소 관계 불투명 | docs, naming, memory, anti-defer | eval_cps_integrity.py, (HARNESS_MAP.md 자체) |

---

## Rules (무엇을 지켜야 하는가)

### Layer 0 — 원칙 (모든 행동에 적용)

| 규칙 | 역할 1줄 | defends | enforced-by | 원본 |
|-----|---------|---------|------------|------|
| no-speculation | 관찰 먼저, 추측 금지 | P1 | review, debug-guard.sh | rules/no-speculation.md |
| anti-defer | 명시 지시는 즉시 처리 | P7 | review | rules/anti-defer.md |

### Layer 1 — 절차 (특정 흐름에 적용)

| 규칙 | 역할 1줄 | defends | parent | children | enforced-by | 원본 |
|-----|---------|---------|--------|---------|------------|------|
| bug-interrupt | 발견 즉시 판단 (Q1/Q2/Q3) | P1 | no-speculation | — | review | rules/bug-interrupt.md |
| internal-first | 내부 자료 우선 | P1 | no-speculation | external-experts | review | rules/internal-first.md |
| self-verify | 완료 전 AC 검증 | P6 | — | — | pre_commit_check.py | rules/self-verify.md |
| staging | review 강도 자동 결정 | P2 | — | — | pre_commit_check.py | rules/staging.md |

### Layer 2 — 도메인 (특정 영역에 적용)

| 규칙 | 역할 1줄 | defends | enforced-by | 원본 |
|-----|---------|---------|------------|------|
| hooks | hook 매처 fragility 방지 | P4 | bash-guard.sh, review | rules/hooks.md |
| pipeline-design | 단계 설계 7항목 체크 | P6 | review | rules/pipeline-design.md |
| coding | surgical changes 원칙 | P1 | review | rules/coding.md |
| security | 시크릿 노출 방지 (다운스트림 선택) | P3 | pre_commit_check.py | rules/security.md |

### Layer 3 — 관리 (시스템 유지에 적용)

| 규칙 | 역할 1줄 | defends | enforced-by | 원본 |
|-----|---------|---------|------------|------|
| docs | 문서 체계 유지 | P7 | pre_commit_check.py, docs_ops.py | rules/docs.md |
| naming | 네이밍·cluster 체계 | P7 | docs_ops.py | rules/naming.md |
| memory | 세션 간 지식 유지 | P7 | stop-guard.sh | rules/memory.md |
| external-experts | 외부 전문가 참조 캐시 | P1 | researcher | rules/external-experts.md |

### 규칙 간 참조 맵

```
no-speculation → (parent) bug-interrupt, internal-first
internal-first → (children) external-experts
```

*수동 편집 금지. 규칙 파일 본문의 parent/children 관계 기준.*

---

## Skills (사용자가 어떻게 트리거하는가)

| 스킬 | 역할 1줄 | serves | 위임 대상 | 원본 |
|-----|---------|--------|---------|-----|
| implementation | 작업 오케스트레이터·CPS 허브 | S1, S6 | codebase-analyst, researcher, advisor, review | skills/implementation/SKILL.md |
| commit | 검증 게이트·문서 이동 | S2, S6 | pre_commit_check.py, review, commit_finalize.sh | skills/commit/SKILL.md |
| write-doc | 문서 단독 생성 | S5 | docs_ops.py | skills/write-doc/SKILL.md |
| eval | 주기적 건강 진단 | S1, S6 | eval_cps_integrity.py, advisor(--deep) | skills/eval/SKILL.md |
| advisor | 기술 결정 종합 | S1 | researcher, codebase-analyst, risk-analyst | skills/advisor/SKILL.md |
| harness-init | 신규 프로젝트 환경 구성 | S3 | check_init_done.sh | skills/harness-init/SKILL.md |
| harness-upgrade | 다운스트림 업그레이드 | S3 | harness_version_bump.py, downstream-readiness.sh | skills/harness-upgrade/SKILL.md |
| harness-adopt | 기존 프로젝트 이식 | S3 | docs_ops.py | skills/harness-adopt/SKILL.md |
| harness-sync | 환경 동기화 | S3 | install-starter-hooks.sh | skills/harness-sync/SKILL.md |
| harness-dev | starter 개발 전용 | S6 | harness_version_bump.py | skills/harness-dev/SKILL.md |
| doc-health | 레거시 문서 정비 | S3 | docs_ops.py, eval_cps_integrity.py | skills/doc-health/SKILL.md |
| check-existing | 중복 함수 확인 | S1 | Grep, codebase-analyst | skills/check-existing/SKILL.md |
| coding-convention | 코딩 컨벤션 관리 | S1 | — | skills/coding-convention/SKILL.md |
| naming-convention | 네이밍 컨벤션 관리 | S5 | — | skills/naming-convention/SKILL.md |

---

## Agents (Claude가 무엇에 위임하는가)

| 에이전트 | 역할 1줄 | serves | 위임 주체 | 원본 |
|---------|---------|--------|---------|-----|
| advisor | 기술 결정·스택 선택 종합 | S1 | implementation, eval | agents/advisor.md |
| codebase-analyst | 내부 코드 분석·패턴 | S1 | implementation, commit | agents/codebase-analyst.md |
| researcher | 외부 자료 조사 | S1 | implementation, advisor | agents/researcher.md |
| doc-finder | 내부 문서 탐색 | S1 | implementation, write-doc | agents/doc-finder.md |
| review | 커밋 전 변경 검증 | S2 | commit | agents/review.md |
| debug-specialist | 에러·예상 외 동작 진단 | S1 | 에러 1회 불명 시 자동 | agents/debug-specialist.md |
| risk-analyst | 위험·반대 논거 | S6 | advisor, commit | agents/risk-analyst.md |
| threat-analyst | 외부 공격면 검토 | S3 | eval --deep | agents/threat-analyst.md |
| performance-analyst | 성능 병목 분석 | S2 | implementation | agents/performance-analyst.md |

---

## Scripts (자동화가 무엇을 실행하는가)

### 자동 트리거 (hooks)

| 스크립트 | hook 이벤트 | 역할 1줄 | enforced-by-inverse |
|---------|-----------|---------|-------------------|
| session-start.py | SessionStart | 세션 초기 상태·WIP 알림 | coding, naming, self-verify, internal-first (환기) |
| debug-guard.sh | UserPromptSubmit | 에러 키워드 감지 | no-speculation |
| stop-guard.sh | Stop | 세션 종료 memory 환기 | memory |
| post-compact-guard.sh | PostCompact | 컴팩션 후 컨텍스트 복원 | coding, naming, self-verify (환기) |
| write-guard.sh | PreToolUse(Write) | docs/ WIP 직접 Write 차단 | docs |
| bash-guard.sh | PreToolUse(Bash) | argument-constraint 패턴 차단 | hooks |
| auto-format.sh | PostToolUse | 포맷 자동 적용 | coding |

### 수동 호출 (스킬이 실행)

| 스크립트 | 호출 스킬 | 역할 1줄 | enforced-by-inverse |
|---------|---------|---------|-------------------|
| pre_commit_check.py | commit | AC·CPS·staged 검증 + stage 결정 | self-verify, staging |
| docs_ops.py | commit, write-doc, doc-health | 문서 이동·cluster 갱신·reopen | docs, naming |
| eval_cps_integrity.py | eval, harness-dev | defends/serves 정합성 감사 + MAP 단절 감지 | docs, naming, memory, anti-defer (P7 방어) |
| harness_version_bump.py | harness-dev, commit | 버전 범프 | — |
| commit_finalize.sh | commit | git commit 래퍼 | — |
| split-commit.sh | commit | 커밋 분할 | — |
| extract_review_verdict.py | commit | review verdict 파싱 | — |
| task_groups.py | commit | 파일 그룹 분류 | — |
| downstream-readiness.sh | harness-upgrade | 업그레이드 후 누락 진단 | — |
| install-starter-hooks.sh | harness-sync | hooks 설치 | — |
| check_init_done.sh | implementation, harness-init | init 완료 여부 | — |
| validate-settings.sh | harness-upgrade | settings.json 검증 | — |
| test-bash-guard.sh | harness-dev | bash-guard 회귀 테스트 | hooks |

---

## Domains & Clusters (탐색 진입점)

| 도메인 | abbr | cluster 파일 | 주요 문서 유형 |
|-------|------|------------|-------------|
| harness | hn | docs/clusters/harness.md | 하네스 자체 설계·결정·이력 |
| meta | mt | docs/clusters/meta.md | 프로젝트 전역 문서 |

CPS 진입점: `docs/guides/project_kickoff.md`

---

## 역추적 절차 (상향 경로 — 필요한 노드만)

**트리거**: BIT Q3=YES (스코프 외 버그 발견) 또는 문제 사후 분석.
MAP 전체를 읽지 않는다. 발생 위치에서 출발해 관련 경로만 거슬러 올라간다.

```
Step 1. 발생 위치 → MAP에서 해당 구성요소 찾기
   어느 파일·스킬·스크립트에서 발생했는가
   → MAP의 Rules/Skills/Agents/Scripts 테이블에서 해당 행 찾기
   → defends 컬럼 → Problem 특정 (CPS 전체 Read 불필요)

Step 2. Problem → 해당 Rules만 Read
   CPS 테이블 defends-by 컬럼의 규칙 이름 확인
   → 그 규칙 파일만 Read (나머지 규칙 Read 금지)

Step 3. Rule → 실행 도구만 확인
   enforced-by 컬럼 확인
   → 해당 스크립트·에이전트만 확인

Step 4. 실패 지점 특정 + BIT 기록
   도구 로그·git history → 원인 특정
   → BIT Q3=YES이면 WIP "## 발견된 스코프 외 이슈"에 P# 기록
   → NEW이면 다음 implementation Step 0에서 CPS 등록 후보로 인식
```

**BIT와 연계**: `rules/bug-interrupt.md` Q3 hit 시 이 절차가 P# 매칭 방법.
발생 위치가 MAP에 없으면 `docs/guides/project_kickoff.md` Problems 섹션으로 폴백.

개선할 때:

```
1. 새 규칙/도구 추가
   → CPS 섹션에서 어떤 Problem을 defends하는지 판단
   → Layer 0~3 중 위치 결정
   → defends-by 업데이트

2. eval_cps_integrity.py가 관계 그래프 단절 자동 감지
   → `python3 .claude/scripts/eval_cps_integrity.py` 실행 후 "관계 그래프 점검" 섹션 확인
```
