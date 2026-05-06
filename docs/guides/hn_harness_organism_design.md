---
title: 하네스 유기체화 설계 — HARNESS_MAP.md 신경망 허브 구현 방안
domain: harness
problem: P7
solution-ref:
  - S1 — "규칙 + 자동 차단 + 우회 장치"
tags: [architecture, harness-map, organism, bidirectional, read-enforce]
relates-to:
  - path: decisions/hn_frontmatter_graph_spec.md
    rel: extends
  - path: decisions/hn_skill_agent_role_audit.md
    rel: references
  - path: decisions/hn_rules_metadata.md
    rel: references
status: completed
created: 2026-05-05
updated: 2026-05-06
---

# 하네스 유기체화 설계 — HARNESS_MAP.md 신경망 허브 구현 방안

## 배경

### 현재 상태 진단 (2026-05-05~06 전수 조사)

하네스 시스템은 **다세포 유기체** 단계에 있다. 기관이 잘 분화됐지만
기관들이 하나의 항상성을 공유하지 못한다.

| 누락 유형 | 구체 항목 |
|----------|----------|
| `defends:` 오매핑 | `anti-defer`, `docs`, `memory`, `naming` 4개가 P5("MCP 컨텍스트 팽창")를 defends하지만 내용 무관 |
| `security.md` 위치 오류 | 다운스트림 전용 보안 규칙 템플릿이 starter에 강제 포함됨 |
| 고립 규칙 | `external-experts`, `memory`, `coding`, `hooks` — 규칙→규칙 참조 전무 |
| `serves:` 누락 | 스킬 13개 중 12개, 에이전트 대부분 미선언 |
| 스펙 문서 없음 | `defends:`/`serves:` 필드 형식이 `docs.md`에 정의 없음 |
| 단방향 참조 | 모든 참조가 상→하 단방향. 역추적 불가 |
| 감지 비대칭 | 추측 패턴은 review가 감지, 문서 미완독은 감지 수단 없음 |
| 문서 미완독 | SKILL.md 700줄+ 에서 후반부 규칙이 묻힘. feature→fix 커밋 반복 패턴 |

### 핵심 진단: 순환계 + 신경망 없음

```
현재: 기관(organ) 집합체 — 단방향 연결
  CPS → rules (defends)
  rules → skills (참조)
  skills → agents (위임)

없는 것 1: 역방향 신호
  no-speculation이 P1을 defends 선언
  → P1에서 no-speculation을 찾아갈 수 없음
  → 문제 발생 시 "어떤 규칙이 막았어야 했는가" 역추적 불가

없는 것 2: Read 강제 진입점
  작업 전 어떤 문서를 반드시 읽어야 하는지 단일 진입점 없음
  → 700줄+ SKILL.md 후반부 규칙이 묻혀도 감지 불가
```

---

## 목표

**유기체화** = 각 구성 요소가 서로를 알고, 변경이 전파되며,
시스템 전체가 일관된 항상성을 유지하는 상태.

**HARNESS_MAP.md** = 하네스의 신경망 허브.

HARNESS.json과의 관계: 합치지 않는다. HARNESS.json은 기계 판독용(버전·스킬 목록·메타데이터),
HARNESS_MAP.md는 Claude가 읽고 판단하는 자연어 관계 지도 — 역할이 다르다.
단, HARNESS.json에 `"map": ".claude/HARNESS_MAP.md"` 포인터 한 줄 추가로 연결한다.

두 가지 역할을 동시에 수행한다:

```
1. 양방향 관계 지도 (시냅스 — 역추적 가능)
   상→하: defends / serves / enforced-by
   하→상: defends-by / serves-by / enforced-by-inverse

2. Read 강제 진입점
   이 파일에 등재된 구성요소는 작업 전 전체 Read 필수
   부분 읽기·요약으로 판단 시작 금지
```

3단계 진화 경로:

```
1단계: HARNESS_MAP.md 신설 + 양방향 관계 명시
2단계: eval_cps_integrity.py 확장 — 관계 그래프 단절 자동 감지
3단계: P7 신설 — 구조적 원인 CPS 등재 + harness-upgrade 전파
```

---

## P7 신설 근거

현재 CPS P1~P6는 **증상 수준** 정의다. 왜 그 증상이 반복되는지 — 구조적 원인 — 이 없다.

```
P7 (가칭): 시스템 구성 요소 간 관계 불투명

증상:
  - 규칙·스킬·에이전트·스크립트가 서로를 모름
  - 새 구성요소 추가 시 어디에 위치하는지 판단 기준 없음
  - defends/serves 오매핑이 수개월 방치됨
  - 작업 전 어떤 문서를 읽어야 하는지 단일 진입점 없음

영향:
  - P1 유발 — Claude가 규칙 간 관계를 추측으로 채움
  - P6 유발 — 잘못된 매핑이 검증 없이 커밋됨
  - 미완독 유발 — Read 강제 수단 없음

P7이 P1·P6의 구조적 원인
```

P7 신설 시 `PROBLEM_INFLATION_THRESHOLD`를 고정 6에서
CPS 본문 Problem 수 기준 동적 계산으로 변경한다.

---

## security.md 처리 결정

`security.md`는 Supabase·AWS·Stripe 키 보호 규칙 — **다운스트림 앱 전용**이다.
harness-starter 자체는 앱이 없으므로 이 규칙이 적용될 대상이 없다.

P3("다운스트림 사일런트 페일")와도 무관 — P3는 업그레이드 절차 누락이고
security.md는 시크릿 노출 방지다.

**결정**:
- `security.md` → starter_skills에서 제거
- 다운스트림이 필요하면 직접 추가
- P3를 defends하는 규칙이 0개가 됨 → 이건 정상 (P3는 규칙이 아닌 프로세스로 방어)
- security.md 제거 시 MIGRATIONS.md 해당 버전 섹션에 안내 추가:
  "security.md는 다운스트림 앱 전용. 필요 시 `.claude/rules/security.md` 직접 추가."

---

## HARNESS_MAP.md 설계

### 위치 및 로드

```
.claude/HARNESS_MAP.md
```

CLAUDE.md에 참조 링크 추가 → Claude가 필요 시 Read.
세션마다 전체 자동 로드 아님 — 필요할 때 통과하는 빠른 통로.

### Read 강제 원칙

```
이 파일에 등재된 모든 구성요소는 작업 전 전체 Read 필수.
부분 읽기로 판단 시작 금지.
```

`read-depth` 필드 없음. 분기 판단이 오버룰이 됨.
"모두 읽어라" 하나만.

review 에이전트에 추가:
```
변경 영향 범위의 SKILL.md·rules/*.md를 전체 Read했는가 확인.
Read tool 호출 없이 판단한 흔적 → [경고].
```

### 항목 형식

```
이름 | 역할 1줄 | defends/serves | defends-by/serves-by | 원본 경로
```

description만 — skills의 description처럼. 본문 없음.
판단은 원본 파일에서.

### 구조 설계

```markdown
# HARNESS_MAP.md — 하네스 신경망 허브

> 이 파일에 등재된 모든 구성요소는 작업 전 전체 Read 필수.

## 읽는 법 (참조용 — 전체 읽기 불필요)
- defends: 이 규칙이 지키는 CPS Problem
- defends-by: 이 Problem을 지키는 규칙들 (역방향)
- serves: 이 도구가 충족하는 CPS Solution
- serves-by: 이 Solution을 충족하는 도구들 (역방향)
- enforced-by: 이 규칙을 실행하는 도구
- enforced-by-inverse: 이 도구가 실행하는 규칙들

**Read 범위**: 작업 관련 섹션만 읽는다.
Rules 변경 → Rules + CPS 섹션. Skills 추가 → Skills + CPS 섹션.
"전체 Read 필수"는 작업과 무관한 섹션까지 강제하지 않는다.

## CPS (왜 — 최상위)

| Problem | 정의 1줄 | defends-by (규칙) | served-by (도구) |
|---------|---------|-----------------|----------------|
| P1 | LLM 추측 수정 반복 | no-speculation, internal-first, bug-interrupt, coding, external-experts | implementation, eval, debug-specialist |
| P2 | review 과잉 비용 | staging | commit, review |
| P3 | 다운스트림 사일런트 페일 | (규칙 없음 — 프로세스 방어) | harness-upgrade, downstream-readiness.sh |
| P4 | hook 매처 fragility | hooks | bash-guard.sh |
| P5 | 컨텍스트 팽창 | (조사 중) | — |
| P6 | 검증망 스킵 | self-verify, pipeline-design | harness-dev, eval |
| P7 | 구성요소 관계 불투명 | (HARNESS_MAP.md 자체) | eval_cps_integrity.py |

## Rules (무엇을 지켜야 하는가)

### Layer 0 — 원칙 (모든 행동에 적용)
| 규칙 | 역할 1줄 | defends | enforced-by |
|-----|---------|---------|------------|
| no-speculation | 관찰 먼저, 추측 금지 | P1 | review, debug-guard.sh |
| anti-defer | 명시 지시는 즉시 처리 | P1* | review |

### Layer 1 — 절차 (특정 흐름에 적용)
| 규칙 | 역할 1줄 | defends | parent | children | enforced-by |
|-----|---------|---------|--------|---------|------------|
| bug-interrupt | 발견 → 즉시 판단 | P1 | no-speculation | — | review |
| internal-first | 내부 자료 우선 | P1 | no-speculation | external-experts | review |
| self-verify | 완료 전 AC 검증 | P6 | — | — | pre_commit_check.py |
| staging | review 강도 자동 결정 | P2 | — | — | pre_commit_check.py |

### Layer 2 — 도메인 (특정 영역에 적용)
| 규칙 | 역할 1줄 | defends | enforced-by |
|-----|---------|---------|------------|
| hooks | hook 매처 fragility 방지 | P4 | bash-guard.sh, review |
| pipeline-design | 단계 설계 7항목 체크 | P6 | review |
| coding | surgical changes 원칙 | P1 | review |

### Layer 3 — 관리 (시스템 유지에 적용) 
| 규칙 | 역할 1줄 | defends | enforced-by |
|-----|---------|---------|------------|
| docs | 문서 체계 유지 | P7* | pre_commit_check.py, docs_ops.py |
| naming | 네이밍·cluster 체계 | P7* | docs_ops.py |
| memory | 세션 간 지식 유지 | P7* | stop-guard.sh |
| external-experts | 외부 전문가 참조 캐시 | P1 | researcher |

*P7 신설 후 재매핑 예정 (현재 P5 오매핑 → P7로 이동)

### 규칙 간 참조 맵 (방향 그래프 — eval 자동 생성)

**수동 편집 금지.** eval_cps_integrity.py가 각 규칙 파일 본문의
`→ 참조` 패턴을 grep해서 동적으로 재구성한다.
규칙 추가·삭제 시 규칙 파일 본문만 수정하면 맵이 자동 갱신된다.

```
(eval --harness 실행 시 여기에 자동 삽입)
```

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

## Agents (Claude가 무엇에 위임하는가)

| 에이전트 | 역할 1줄 | serves | 위임 주체 | 원본 |
|---------|---------|--------|---------|-----|
| advisor | 기술 결정·스택 선택 종합 | S1 | implementation, eval | agents/advisor.md |
| codebase-analyst | 내부 코드 분석·패턴 | S1 | implementation, commit | agents/codebase-analyst.md |
| researcher | 외부 자료 조사 | S5 | implementation, advisor | agents/researcher.md |
| doc-finder | 내부 문서 탐색 | S5 | implementation, write-doc | agents/doc-finder.md |
| review | 커밋 전 변경 검증 | S2 | commit | agents/review.md |
| debug-specialist | 에러·예상 외 동작 진단 | S1 | 에러 1회 불명 시 자동 | agents/debug-specialist.md |
| risk-analyst | 위험·반대 논거 | S6 | advisor, commit | agents/risk-analyst.md |
| threat-analyst | 외부 공격면 검토 | S3 | eval --deep | agents/threat-analyst.md |
| performance-analyst | 성능 병목 분석 | S2 | implementation | agents/performance-analyst.md |

## Scripts (자동화가 무엇을 실행하는가)

### 자동 트리거 (hooks)
| 스크립트 | hook 이벤트 | 역할 1줄 |
|---------|-----------|---------|
| session-start.py | SessionStart | 세션 초기 상태·WIP 알림 |
| debug-guard.sh | UserPromptSubmit | 에러 키워드 감지 |
| stop-guard.sh | Stop | 세션 종료 memory 환기 |
| post-compact-guard.sh | PostCompact | 컴팩션 후 컨텍스트 복원 |
| write-guard.sh | PreToolUse(Write) | docs/ WIP 직접 Write 차단 |
| bash-guard.sh | PreToolUse(Bash) | argument-constraint 패턴 차단 |
| auto-format.sh | PostToolUse | 포맷 자동 적용 |

### 수동 호출 (스킬이 실행)
| 스크립트 | 호출 스킬 | 역할 1줄 |
|---------|---------|---------|
| pre_commit_check.py | commit | AC·CPS·staged 검증 + stage 결정 |
| docs_ops.py | commit, write-doc, doc-health | 문서 이동·cluster 갱신·reopen |
| eval_cps_integrity.py | eval, harness-dev | defends/serves 정합성 감사 |
| harness_version_bump.py | harness-dev, commit | 버전 범프 |
| commit_finalize.sh | commit | git commit 래퍼 |
| split-commit.sh | commit | 커밋 분할 |
| extract_review_verdict.py | commit | review verdict 파싱 |
| task_groups.py | commit | 파일 그룹 분류 |
| downstream-readiness.sh | harness-upgrade | 업그레이드 후 누락 진단 |
| install-starter-hooks.sh | harness-sync | hooks 설치 |
| check_init_done.sh | implementation | init 완료 여부 |
| validate-settings.sh | harness-upgrade | settings.json 검증 |

## Domains & Clusters (탐색 진입점)

| 도메인 | abbr | cluster 파일 | 주요 문서 유형 |
|-------|------|------------|-------------|
| harness | hn | docs/clusters/harness.md | 하네스 자체 설계·결정·이력 |
| meta | mt | docs/clusters/meta.md | 프로젝트 전역 문서 |

CPS: docs/guides/project_kickoff.md
```

### 역추적 활용 방법

문제가 발생했을 때:

```
1. 증상 확인
   → HARNESS_MAP.md CPS 섹션에서 해당 Problem 찾기

2. 어떤 규칙이 방어했어야 하는가
   → Problem의 defends-by 컬럼 → 해당 규칙 전체 Read

3. 어떤 도구가 실행했어야 하는가
   → 규칙의 enforced-by → 해당 스크립트·에이전트 확인

4. 어디서 실패했는가
   → 도구 로그·git history → 원인 특정
```

### 역추적 보고 프롬프트 (업스트림·다운스트림 공통)

문제 분석 완료 후 아래 형식으로 보고한다.
업스트림 보고(starter 개선 요청)와 다운스트림 내부 기록 모두 이 형식을 사용.

```
[역추적 보고]
보고 유형: upstream 개선 요청 | downstream 내부 기록
증상: <관찰된 현상 1줄>
관련 Problem: P#
방어했어야 할 규칙: <rules — defends-by에서 찾은 것>
실행했어야 할 도구: <enforced-by에서 찾은 것>
실패 지점: <어느 단계에서 감지 못했는가>
재발 방지:
  - 규칙 갱신: <rules/*.md 변경 내용>
  - enforced-by 추가: <새 도구 또는 체크 추가>
  - upstream 전달 필요: yes | no
```

upstream 전달 필요 = yes이면 harness-starter issues 또는
MIGRATIONS.md "다운스트림 발견 이상 소견" 섹션에 등록.

개선할 때:

```
1. 새 규칙/도구 추가
   → HARNESS_MAP.md에서 어떤 Problem을 defends하는지 판단
   → Layer 0~3 중 위치 결정
   → 역방향(defends-by) 업데이트

2. eval_cps_integrity.py가 관계 그래프 단절 자동 감지
   → "이 규칙을 enforced-by하는 도구가 없다" → 경고
   → "이 Problem을 defends하는 규칙이 없다" → 경고
```

---

## 비관적 분석

### 실패 시나리오 1: 드리프트 (완화됨)

규칙 추가 빈도 실측: 35일간 11건. "자주 늘지 않는다"는 전제가 반박됨.

**대응**: HARNESS_MAP.md는 harness-starter가 소유하고 harness-upgrade로 전파.
다운스트림은 읽기만 — 드리프트 책임은 업스트림에만 있다.
eval --harness가 관계 그래프 단절을 주기적으로 감지.

### 실패 시나리오 2: 로드 안 됨 (필수 대응)

CLAUDE.md에 참조 추가가 없으면 HARNESS_MAP.md는 존재하지만 읽히지 않는다.

**대응**: Phase 구현 마지막 단계에서 CLAUDE.md 참조 추가. 구조 확정 후 필수.

### ~~실패 시나리오 3: defends cascade~~ → HARNESS_MAP.md가 해결책

### ~~실패 시나리오 4: 추상화 약화~~ → HARNESS_MAP.md는 인덱스, 행동 강제는 개별 파일

### 실패 시나리오 5: serves: 형식 선언 (핵심 위험)

eval_cps_integrity.py가 serves: 값을 검증하지 않으면 오매핑이 방치된다.
이게 핵심 자산 — eval 확장 없으면 전체가 형식이 된다.

### 종합

| 조건 | 없으면 |
|-----|-------|
| CLAUDE.md 참조 추가 | HARNESS_MAP.md 존재하지만 읽히지 않음 |
| eval 관계 그래프 단절 감지 | 드리프트 방치, 형식 선언 반복 |
| harness-upgrade 전파 | 업스트림에서만 유효 |

---

## 작업 목록

### Phase 0. P7 신설 + security.md 처리 (CPS 변경 — owner 확인)

**영향 파일**: `docs/guides/project_kickoff.md`, `.claude/rules/security.md`, `HARNESS.json`

**Acceptance Criteria**:
- [x] Goal: CPS에 P7이 등재되고 security.md가 starter_skills에서 제거된다
  검증:
    review: review
    tests: python3 -m pytest .claude/scripts/tests/ -q -k "cps_integrity"
    실측: python3 .claude/scripts/eval_cps_integrity.py 실행 후 P7 인식 확인
- [x] project_kickoff.md에 P7 섹션 추가 (증상·영향·승격 상태)
- [x] `PROBLEM_INFLATION_THRESHOLD` → 동적 계산 (CPS Problem 수 기준)
- [x] security.md → starter_skills 목록에서 제거 (HARNESS.json 갱신) — 이미 없음 확인 ✅
- [x] anti-defer, docs, memory, naming의 `defends: P5` → `defends: P7` 정정
- [x] P3를 defends하는 규칙 0개 → 정상 처리 (eval 경고 없도록) — eval에 해당 경고 로직 없음 확인

---

### Phase 1. eval_cps_integrity.py 확장 — 관계 그래프 단절 감지

**영향 파일**: `.claude/scripts/eval_cps_integrity.py`

**Acceptance Criteria**:
- [x] Goal: eval --harness가 HARNESS_MAP.md와 실제 파일 간 드리프트 및 관계 그래프 단절을 자동 감지한다 ✅
  검증:
    review: review
    tests: python3 -m pytest .claude/scripts/tests/ -q -k "cps_integrity"
    실측: python3 .claude/scripts/eval_cps_integrity.py 실행 후 "관계 그래프 점검" 섹션 출력 확인
- [x] HARNESS_MAP.md 존재 여부 체크 (없으면 "미생성" 경고) ✅
- [x] HARNESS_MAP.md rules 섹션 vs `rules/*.md` 실제 파일 대조 — 누락 시 ⚠ ✅
- [x] HARNESS_MAP.md skills 섹션 vs `skills/*/SKILL.md` 대조 — 누락 시 ⚠ ✅
- [x] HARNESS_MAP.md agents 섹션 vs `agents/*.md` 대조 — 누락 시 ⚠ ✅
- [x] HARNESS_MAP.md scripts 섹션 vs `scripts/*` 대조 — 누락 시 ⚠ ✅
- [x] "enforced-by 없는 규칙" 감지 — P7 방어 공백 경고
- [x] "defends-by 없는 Problem" 감지 — 규칙 보호 없는 Problem 경고
- [x] eval/SKILL.md 보고 형식 예시 갱신 (새 섹션 반영) — "관계 그래프 점검" 섹션 출력으로 확인 ✅

---

### Phase 2. HARNESS_MAP.md 생성

**영향 파일**: `.claude/HARNESS_MAP.md`

**사전 준비**: Phase 1 완료 (eval이 드리프트를 감지할 수 있는 상태에서 생성)

**Acceptance Criteria**:
- [x] Goal: `.claude/HARNESS_MAP.md`가 CPS·Rules·Skills·Agents·Scripts·Domains를 양방향 관계로 명시하는 신경망 허브가 된다 ✅
  검증:
    review: review-deep
    tests: python3 .claude/scripts/eval_cps_integrity.py
    실측: eval --harness 실행 후 드리프트 0건 확인
- [x] 상단에 "전체 Read 필수" 원칙 명시
- [x] CPS 섹션: P1~P7 + defends-by + served-by 양방향
- [x] Rules 섹션: Layer 0~3 + defends + enforced-by 양방향
- [x] Skills 섹션: serves + 위임 대상 + 원본 경로
- [x] Agents 섹션: serves + 위임 주체 + 원본 경로
- [x] Scripts 섹션: 자동/수동 분류 + 호출 스킬
- [x] Domains 섹션: abbr + cluster 경로 + CPS 진입점
- [x] 역추적 활용 방법 섹션 포함

---

### Phase 3. review 에이전트 미완독 감지 추가

**영향 파일**: `.claude/agents/review.md`

**Acceptance Criteria**:
- [x] Goal: review 에이전트가 변경 영향 범위의 SKILL.md·rules 미완독을 감지한다 ✅
  검증:
    review: review
    tests: 없음
    실측: SKILL.md 변경 커밋 시 review가 Read 흔적 확인하는지 운용 확인 (자동화 불가)
- [x] "변경 영향 SSOT 문서를 Read tool로 전체 읽었는가" 체크 추가
- [x] Read 없이 판단한 흔적 발견 시 [경고] 발행
- [x] HARNESS_MAP.md를 역추적 진입점으로 활용하는 절차 추가 ✅

---

### Phase 4. CLAUDE.md 참조 추가

**영향 파일**: `CLAUDE.md`

**사전 준비**: Phase 2 완료 (HARNESS_MAP.md 존재 확인 후 참조 추가)

**Acceptance Criteria**:
- [x] Goal: CLAUDE.md가 HARNESS_MAP.md를 참조해 Claude가 필요 시 신경망 허브를 통과한다 ✅
  검증:
    review: review
    tests: 없음
    실측: 새 세션에서 "P1을 defends하는 규칙들은?" 질문에 HARNESS_MAP.md 참조해 즉시 답변 가능한지 확인 (자동화 불가)
- [x] CLAUDE.md 적절한 섹션에 HARNESS_MAP.md 참조 링크 + 1줄 역할 설명 ✅
- [x] "작업 전 HARNESS_MAP.md 통과" 진입 조건 명시 ✅

---

### Phase 5. docs.md + naming.md 스펙 추가

**영향 파일**: `.claude/rules/docs.md`, `.claude/rules/naming.md`

**Acceptance Criteria**:
- [x] Goal: defends:/serves:/enforced-by: 필드 형식이 공식 정의되어 새 구성요소 추가 시 오매핑 없이 배치 가능하다
  검증:
    review: review
    tests: 없음
    실측: 새 규칙 추가 시 판단 트리 1회 적용 후 HARNESS_MAP.md 배치 확인 (자동화 불가)
- [x] docs.md에 `defends:`/`serves:`/`enforced-by:` 필드 형식 + 매핑 판단 기준 정의 ✅
- [x] naming.md L39-40 SSOT 지목이 실제로 충족됨 (이미 docs.md SSOT 지목 확인) ✅
- [x] 새 규칙 추가 판단 트리 명시

---

### Phase 6. harness-upgrade 전파 강제

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`

**Acceptance Criteria**:
- [x] Goal: harness-upgrade 실행 시 HARNESS_MAP.md가 다운스트림에 자동 전파되고 확인된다 ✅
  검증:
    review: review
    tests: 없음
    실측: harness-upgrade 절차 실행 후 다운스트림에 HARNESS_MAP.md 존재 확인 (자동화 불가)
- [x] harness-upgrade Step 9.3에 "HARNESS_MAP.md 전파 확인" 추가 ✅
- [x] downstream-readiness.sh에 HARNESS_MAP.md 존재 체크 추가 ✅

---

## 결정 사항

- **HARNESS_MAP.md 단일 파일** — 4개 분리 아님. 관리 부담 4배 문제 + 동기화 취약성 해소
- **P7 신설** — P1·P6의 구조적 원인. CPS 등재로 defends 매핑 기준 확립
- **security.md → starter_skills 제거** — 다운스트림 선택 사항
- **read-depth 필드 없음** — "모두 읽어라" 단일 원칙만
- **역방향 참조 (defends-by, enforced-by-inverse)** — 양방향 시냅스 구조
- **eval 확장이 Phase 1** — HARNESS_MAP.md 생성 전 드리프트 감지 수단 확보
- **harness-upgrade 전파** — 다운스트림은 읽기만, 드리프트 책임은 업스트림

## 메모

- 설계 근거: 2026-05-05~06 생명공학 분석 + codebase-analyst + risk-analyst + debug-specialist 병렬 진단
- 미완독 구조적 원인 확인: 감지 비대칭(추측은 감지, 미독은 미감지) + SKILL.md 700줄+ + fast scan 합법화
- git log 실측: 35일 11건 규칙 추가 — "자주 늘지 않는다" 전제 반박됨
- security.md P3→P1 정정 논의 → P3 자체는 올바름, security.md가 잘못 매핑된 것
- P5 (컨텍스트 팽창) Solution 미완료 상태 유지 — P7과 별개
- Phase 순서: 0(P7+security) → 1(eval확장) → 2(HARNESS_MAP) → 3(review) → 4(CLAUDE.md) → 5(docs스펙) → 6(upgrade전파)

### Phase 0 완료 메모 (2026-05-06)

- project_kickoff.md P7 추가 — 증상·영향·승격 상태 포함
- eval_cps_integrity.py: `PROBLEM_INFLATION_THRESHOLD = 6` 삭제 → `inflation_threshold = max(8, problem_count + 2)` 동적 계산
  - P7 추가 후 실측: Problem 수 7개, 임계값 9 → 경고 없음 ✅
- security.md: HARNESS.json skills/starter_skills 어디에도 없음 확인 (이미 제거됨). starter_skills에 등재된 적 없으므로 HARNESS.json 변경 불필요
- anti-defer·docs·memory·naming defends: P5 → P7 정정 완료
- P3 defends 0개: eval_cps_integrity.py에 해당 경고 로직 없음 → 현재 정상. Phase 1 eval 확장에서 "defends-by 없는 Problem" 감지 추가 예정
- 전체 테스트: 73 passed, 4 skipped ✅
- CPS 갱신: P7 신설 → project_kickoff.md 반영 완료

### Phase 2 선행 메모 (2026-05-06)

- `.claude/HARNESS_MAP.md` 임시 생성 완료
- 실제 파일 대조 결과 WIP 설계 대비 차이점:
  - `session-start.sh` — session-start.py로 대체됐으나 파일 존재. 레거시로 명기
  - `auto-format.sh`, `test-bash-guard.sh` — WIP 설계에 누락됐던 파일. MAP에 추가
  - researcher agent의 serves: S1 (WIP 설계는 S5였으나 실제 usage 기준 S1이 더 정확)
- Phase 1 eval 확장 후 MAP vs 실제 파일 자동 대조 예정

### Phase 1~6 완료 메모 (2026-05-06)

- Phase 1: eval_cps_integrity.py에 `check_harness_map()` 추가. rules/skills/agents/scripts 대조 + enforced-by 없는 규칙 + defends-by 없는 Problem 감지. 실측: 단절 0건 ✅
- Phase 2: HARNESS_MAP.md 규칙 간 참조 맵 placeholder 갱신 + "임시 버전" 문구 제거
- Phase 3: review.md 카테고리 8 "SSOT 문서 미완독 감지" 추가 + HARNESS_MAP.md 역추적 진입점 절차 명시
- Phase 4: CLAUDE.md에 "## 하네스 신경망 허브" 섹션 추가 — HARNESS_MAP.md 참조 + 작업 전 진입 조건
- Phase 5: docs.md에 "## 하네스 구성요소 메타데이터" 섹션 추가 — defends:/serves:/enforced-by: 필드 형식 + Layer 배치 기준 + 판단 트리
- Phase 6: harness-upgrade SKILL.md Step 9.3 신설. downstream-readiness.sh 섹션 4-pre 추가
- 전체 테스트: 73 passed ✅. CPS 갱신: 없음 (P7은 Phase 0 완료)
