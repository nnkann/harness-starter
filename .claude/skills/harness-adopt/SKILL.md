---
name: harness-adopt
description: 기존 프로젝트에 하네스를 이식한다. .claude/ 충돌 감지·병합, docs/ 재분류, 프론트매터 추가를 대화형으로 진행. "기존 프로젝트에 하네스 적용", "하네스 이식", "harness-adopt" 요청 시 사용.
---

# harness-adopt 스킬

기존 프로젝트에 하네스를 이식하는 대화형 흐름.
harness-init이 **빈 프로젝트 초기화**라면, harness-adopt는 **기존 프로젝트 병합**이다.

## 전제

- 하네스 스타터의 파일들이 이미 프로젝트에 복사되어 있거나, 복사할 준비가 되어 있다.
- 기존 프로젝트에 `.claude/`, `docs/`, `CLAUDE.md` 중 하나 이상이 이미 존재할 수 있다.
- 이 스킬은 **파괴적 작업을 하지 않는다.** 기존 파일을 삭제하지 않고, 병합하거나 이름을 바꾼다.
- 모든 병합 결과는 사용자 확인 후 적용한다.

## 핵심 원칙

1. **기존 것을 존중한다.** 기존 설정/문서를 하네스가 덮어쓰지 않는다.
2. **대화형으로 진행한다.** 자동 적용 없음. 매 단계 확인.
3. **필수 단계는 건너뛸 수 없다.** docs 재분류와 프론트매터 추가는 하네스가 동작하기 위한 전제 조건이다.

## 필수 vs 선택

| 단계 | 필수/선택 | 이유 |
|------|----------|------|
| Step 1. 현황 스캔 | **필수** | 모든 단계의 전제 |
| Step 2. CLAUDE.md 병합 | **필수** | 하네스 규칙의 진입점 |
| Step 3. settings.json 병합 | **필수** | hooks 없으면 강제력 없음 |
| Step 4. rules/scripts/skills 복사 | **필수** | 스킬·규칙이 없으면 하네스가 아님 |
| Step 5. docs/ 재분류 | **필수** | 프론트매터 + 폴더 구조 없으면 문서 체계 불능 |
| Step 6. 완료 리포트 | 자동 | — |

**"일부만 적용"은 허용하지 않는다.** 하네스는 부분 적용 시 정합성이 깨진다.
단, 각 단계 내에서 개별 항목(예: 특정 문서의 분류)은 사용자와 대화하며 결정한다.

## 흐름

### Step 1. 현황 스캔

기존 프로젝트의 상태를 스캔하여 충돌 지점을 리포트한다.

**스캔 대상:**

| 대상 | 확인 사항 |
|------|----------|
| `CLAUDE.md` | 존재 여부, 내용 규모 |
| `.claude/settings.json` | 존재 여부, 기존 hooks/permissions |
| `.claude/rules/` | 기존 규칙 파일 목록 |
| `.claude/skills/` | 기존 스킬 목록 |
| `.claude/scripts/` | 기존 스크립트 목록 |
| `docs/` | 존재 여부, 파일 수, 하위 폴더 구조, 프론트매터 유무 |

**출력 형식:**

```
## 현황 스캔 결과

### .claude/ 영역
| 항목 | 상태 | 충돌 |
|------|------|------|
| CLAUDE.md | 기존 파일 있음 (42줄) | 🔶 병합 필요 |
| settings.json | 기존 파일 있음 (hooks 3개) | 🔶 병합 필요 |
| rules/ | 2개 파일 | 🔶 이름 충돌 1개 |
| skills/ | 없음 | ✅ 충돌 없음 |
| scripts/ | 없음 | ✅ 충돌 없음 |

### docs/ 영역
| 항목 | 상태 |
|------|------|
| docs/ 존재 | 예, 15개 파일 |
| 하위 폴더 | guides/, api/ (비표준 2개) |
| 프론트매터 | 3/15 있음, 12/15 없음 |
| 하네스 구조 대비 | 재분류 필요 |

Step 2부터 순서대로 진행합니다.
```

모든 단계를 순서대로 진행한다. 건너뛰기 불가.

---

### Step 2. CLAUDE.md 병합

기존 CLAUDE.md와 하네스 템플릿을 병합한다.

**전략: 기존 내용 보존 + 하네스 구조 추가**

1. 기존 CLAUDE.md를 읽는다.
2. 하네스 템플릿의 각 섹션을 대조한다:

| 하네스 섹션 | 기존에 있으면 | 기존에 없으면 |
|-------------|-------------|-------------|
| `## 언어` | 기존 값 유지 | 추가 제안 |
| `## 절대 규칙` | 기존 규칙 + 하네스 규칙 합집합 | 하네스 규칙 추가 |
| `## 환경` | 기존 값으로 하네스 빈 칸 채움 | 빈 칸으로 추가 (harness-init에서 채움) |
| `## 구조` | 기존 값 유지, 하네스 규칙 보완 | 하네스 기본값 추가 |
| `<important>` 블록 | 기존 것 유지 + 하네스 것 추가 | 하네스 것 추가 |

3. 병합 결과를 diff로 보여주고 사용자 확인을 받는다.
4. 확인 후 적용.

**기존 CLAUDE.md가 없으면**: 하네스 템플릿을 그대로 복사한다.

---

### Step 3. settings.json 병합

기존 settings.json과 하네스 settings.json을 병합한다.

**병합 규칙:**

| 영역 | 전략 |
|------|------|
| `permissions.allow` | 합집합 (기존 + 하네스). 중복 제거. |
| `hooks` (같은 이벤트) | 배열 concat. **기존 hooks를 앞에**, 하네스 hooks를 뒤에. |
| `hooks` (새 이벤트) | 하네스 것 추가. |

**주의:**
- 기존 hooks와 하네스 hooks가 같은 matcher를 가지면 충돌 가능. 사용자에게 보여주고 선택하게 한다.
- `PreToolUse`의 `git commit` 관련 hooks는 하네스의 핵심이므로, 기존에 비슷한 것이 있으면 통합 방안을 제안한다.

```
## settings.json 병합 계획

추가될 hooks:
  + SessionStart: session-start.sh
  + Stop: stop-guard.sh
  + PostCompact: post-compact-guard.sh
  + PostToolUse(Write|Edit): auto-format.sh
  + PreToolUse(git commit --no-verify): 차단 hook
  + PreToolUse(git commit): pre-commit-check.sh + 테스트 커버리지 에이전트
  + PreToolUse(Write): write-guard.sh

⚠️ 충돌:
  기존 PreToolUse(git commit) hook 발견 — 통합 필요

추가될 permissions:
  + Edit(/.claude/skills/commit/**)
  + Edit(/.claude/skills/harness-init/**)
  + Bash(bash -n h-setup.sh)

진행할까요? [Y/n]
```

**기존 settings.json이 없으면**: 하네스 것을 그대로 복사한다.

---

### Step 4. rules/·scripts/·skills/ 복사

충돌이 적은 영역. 대부분 하네스 것을 추가하면 된다.

**rules/ 처리:**

1. 기존 rules/ 파일 목록을 확인한다.
2. 하네스 rules 파일과 이름이 같은 것이 있으면:
   - 내용을 diff로 보여준다.
   - 선택지: (a) 기존 유지 + 하네스 내용 append, (b) 하네스 것으로 교체, (c) 기존 유지
3. 이름이 다른 기존 rules는 그대로 유지.
4. 하네스 전용 rules (self-verify.md, docs.md 등)는 추가.

**scripts/ 처리:**
- 기존 scripts/가 없으면 하네스 것을 전체 복사.
- 기존 scripts/가 있으면 같은 이름만 diff 비교 후 사용자 선택.

**skills/ 처리:**
- 기존 skills/가 없으면 하네스 것을 전체 복사.
- 동명 스킬이 있으면 diff 비교 후 사용자 선택.

---

### Step 5. docs/ 재분류

기존 문서를 하네스 폴더 구조로 재분류한다. **가장 복잡한 단계.**

#### 5a. 기존 문서 인벤토리

docs/ 하위 모든 .md 파일을 스캔한다:

```
## docs/ 인벤토리

총 15개 문서 발견

| # | 파일 | 프론트매터 | 내용 요약 (첫 3줄) |
|---|------|-----------|------------------|
| 1 | docs/api-guide.md | ❌ 없음 | API 사용 가이드... |
| 2 | docs/architecture.md | ❌ 없음 | 시스템 아키텍처 설명... |
| 3 | docs/auth-decision.md | ✅ 있음 | JWT 인증 선택 근거... |
| ... | ... | ... | ... |
```

#### 5b. 문서 정리 (triage)

분류와 프론트매터 작업 전에 **불필요한 문서를 먼저 걸러낸다.**
문서가 많을수록 이 단계가 중요하다. 정리하지 않으면 이후 단계에서 불필요한 작업이 배로 늘어난다.

각 문서에 대해 다음을 판단한다:

| 판정 | 기준 | 처리 |
|------|------|------|
| **유지** | 현재 유효하고, 누군가 다시 참조할 문서 | 다음 단계로 진행 |
| **보관** | 더 이상 유효하지 않지만 이력 가치 있음 | `archived/`로 직행 (프론트매터 최소만) |
| **삭제 후보** | 중복, 빈 파일, 자동 생성물, 임시 메모 | 사용자 확인 후 삭제 |

```
## 문서 정리 (triage)

총 25개 문서 중:

유지 (15개): 다음 단계에서 분류 + 프론트매터 처리
  1. docs/api-guide.md — API 사용 가이드
  2. docs/architecture.md — 시스템 아키텍처
  ...

보관 → archived/ (5개): 프론트매터 최소 추가 후 이동
  16. docs/old-setup-guide.md — 이전 스택 기준, 현재와 불일치
  17. docs/v1-api-spec.md — v2로 대체됨
  ...

삭제 후보 (5개): 확인 후 삭제
  21. docs/temp-notes.md — 빈 파일
  22. docs/test.md — 테스트용 더미
  23. docs/api-guide-copy.md — #1과 중복
  ...

삭제 후보를 확인해주세요. 유지할 문서가 있으면 번호로 알려주세요.
```

**보관 문서는 최소 프론트매터만 추가한다** (title, domain: meta, status: abandoned). 내용을 자세히 분류할 필요 없다.
**삭제는 사용자 확인 필수.** "삭제해도 될 것 같다"는 판단은 Claude가 하되, 실행은 사용자가 승인해야 한다.

정리가 끝나면 "유지" 판정 문서만 이후 단계로 넘긴다.

#### 5c. 폴더 분류 제안

각 문서의 내용을 읽고, 하네스 폴더 기준에 따라 분류를 제안한다.

**분류 기준** (docs.md 규칙에서):
- "왜 이렇게 했나?" → `decisions/`
- "어떻게 하나?" → `guides/`
- "무엇이 왜 깨졌나?" → `incidents/`
- 하네스 자체 변경 → `harness/`
- 더 이상 유효하지 않음 → `archived/`

```
## 분류 제안

| # | 현재 경로 | → 제안 폴더 | 이유 |
|---|----------|------------|------|
| 1 | docs/api-guide.md | guides/ | 사용 방법 설명 |
| 2 | docs/architecture.md | decisions/ | 아키텍처 결정 근거 포함 |
| 3 | docs/auth-decision.md | decisions/ | 기술 선택 근거 |
| 4 | docs/old-setup.md | archived/ | 현재 스택과 불일치 |
| ... | ... | ... | ... |

⚠️ 판단 불확실:
  - docs/notes.md — 내용이 혼합됨. 직접 확인 필요.

수정할 항목이 있으면 번호로 알려주세요. 없으면 진행합니다.
```

**사용자가 수정을 요청하면** 해당 항목만 변경하고 다시 보여준다.
**사용자가 확인하면** 다음 단계로.

#### 5d. 도메인 매핑

각 문서에 할당할 domain을 결정한다.

1. naming.md의 "도메인 목록 > 확정"을 읽는다.
2. 기존 문서의 내용에서 도메인을 추론한다.
3. 기존 도메인 목록에 없는 도메인이 필요하면 **사용자에게 추가 여부를 묻는다.**

```
## 도메인 매핑

현재 확정 도메인: harness, meta

기존 문서에서 추론된 도메인:
  - auth (3개 문서) — ❓ 도메인 목록에 없음
  - payment (2개 문서) — ❓ 도메인 목록에 없음
  - harness (1개 문서) — ✅ 있음

도메인 추가가 필요합니다:
  (1) auth, payment을 확정 도메인에 추가
  (2) 직접 도메인 목록 지정
  (3) 모두 meta로 일단 매핑 (나중에 분류)
```

사용자 선택에 따라 naming.md 도메인 목록을 갱신한다.

#### 5e. 프론트매터 추가

프론트매터가 없는 문서에 프론트매터를 생성한다. **건너뛸 수 없다.**
프론트매터가 없으면 하네스의 문서 체계(INDEX, clusters, relates-to)가 동작하지 않는다.

각 문서에 대해:
1. 내용을 읽고 프론트매터 초안을 생성한다.
2. 사용자에게 보여준다:

```
## 프론트매터 추가: docs/api-guide.md

제안:
---
title: API 사용 가이드
domain: payment
tags: [api, rest]
relates-to: []
status: completed
created: 2026-03-15     ← git log에서 추출한 최초 커밋 날짜
updated: 2026-04-10     ← git log에서 추출한 최근 수정 날짜
---

[적용 / 수정 / 건너뛰기]
```

**날짜 추출 방법:**
- `git log --follow --format="%ai" -- <file>` 로 최초/최근 커밋 날짜를 가져온다.
- git 이력이 없으면 파일 시스템 날짜를 사용한다.
- 어느 쪽이든 사용자가 확인하게 한다.

**relates-to는 빈 배열로 시작.** 재분류 후 관계가 명확해지면 채운다.

**규모별 처리 전략:**

| 문서 수 | 전략 | 이유 |
|---------|------|------|
| 1~5개 | 개별 확인 | 부담 없음. 하나씩 보여주고 확인 |
| 6~15개 | 배치 제안 + 예외 확인 | 전체 프론트매터를 테이블로 한 번에 보여주고, 수정이 필요한 것만 개별 처리 |
| 16개+ | 도메인별 배치 | 도메인 단위로 끊어서 처리. 한 도메인 완료 → 다음 도메인. 컨텍스트 과부하 방지 |

배치 모드에서도 **적용 전 전체 목록을 한 번 보여준다.** 사용자가 최종 승인해야 적용.

#### 5f. 파일 이동 실행

확인된 분류에 따라 문서를 이동한다.

1. `git mv`로 이동. 접두사 제거 등 파일명 정규화 포함.
2. 기존 비표준 하위 폴더(예: `docs/api/`)가 비게 되면 삭제 여부를 묻는다.
3. 이동 결과 리포트:

```
## 이동 완료

| 이전 경로 | → 이후 경로 |
|----------|------------|
| docs/api-guide.md | docs/guides/api_guide_260315.md |
| docs/architecture.md | docs/decisions/architecture_260301.md |
| ... | ... |

삭제 가능한 빈 폴더:
  - docs/api/ (비어 있음) — 삭제할까요? [Y/n]
```

**파일명 정규화:**
- 기존 파일명이 하네스 네이밍 규칙과 다를 수 있다 (kebab-case → snake_case 등).
- 파일명 변환을 제안하되 강제하지 않는다.
- 날짜 접미사(`_YYMMDD`)가 없으면 git log 최초 커밋 날짜로 추가를 제안한다.

#### 5g. INDEX.md + clusters/ 생성

재분류가 끝나면 docs-manager 에이전트에게 위임한다:
- docs/INDEX.md 생성 (도메인별 문서 수 + clusters/ 포인터)
- docs/clusters/{domain}.md 생성 (문서 목록 + 관계 맵)

---

### Step 6. adopt 완료 마커 생성

검증 게이트 통과 후, `.claude/.harness_adopted` 마커 파일을 생성한다.
이 마커는 harness-init의 Step 0 게이트가 "adopt 완료된 기존 프로젝트"를 인식하는 데 사용된다.

```bash
cat > .claude/.harness_adopted <<EOF
adopted_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
harness_version: $(cat .claude/HARNESS_VERSION)
EOF
```

`.gitignore`에 추가 권고 (머신별 상태가 아니라 프로젝트 상태이므로 커밋해도 됨).

### Step 7. 완료 리포트

```
## harness-adopt 완료

### .claude/ 병합
  - CLAUDE.md: 병합됨 (기존 42줄 → 68줄)
  - settings.json: hooks 6개 추가, permissions 3개 추가
  - rules/: 5개 추가, 1개 병합
  - skills/: 10개 추가
  - scripts/: 6개 추가

### docs/ 재분류
  - 이동: 12개 문서
  - 프론트매터 추가: 12개
  - 도메인 추가: auth, payment
  - 건너뜀: 3개 (사용자 선택)

### 다음 할 일
  1. `harness-init` 실행 — CPS 정리 + 환경 빈 칸 채우기
     (기존 프로젝트라도 CPS 정리는 권장)
  2. relates-to 관계 채우기 — 문서 간 연결
  3. coding-convention / naming-convention 스킬로 규칙 세분화
```

## harness-init과의 관계

```
harness-adopt → 구조 이식 (파일/설정/문서)
    ↓
harness-init → 내용 채우기 (CPS, 스택, 환경)
```

adopt는 **그릇을 옮기는 것**, init은 **그릇을 채우는 것**.
기존 프로젝트에서는 adopt → init 순서로 실행한다.
adopt 없이 init만 실행하면 기존 설정과 충돌한다. init은 adopt 완료를 전제로 동작한다.

## 완료 검증 게이트

Step 6 리포트 전에 다음을 모두 확인한다. **하나라도 실패하면 adopt 미완료로 간주하고 완료 처리하지 않는다.**

| 검증 항목 | 확인 방법 |
|----------|----------|
| CLAUDE.md에 하네스 절대 규칙 존재 | `## 절대 규칙` 섹션 + `<important>` 블록 확인 |
| settings.json에 하네스 핵심 hooks 존재 | PreToolUse(git commit), Stop, SessionStart 최소 3개 |
| rules/ 핵심 파일 존재 | self-verify.md, docs.md, naming.md 최소 3개 |
| skills/ 핵심 스킬 존재 | commit, implementation 최소 2개 |
| docs/ 하위 구조 존재 | decisions/, guides/, incidents/, WIP/, clusters/ 폴더 |
| docs/ 모든 .md에 프론트매터 존재 | WIP/ 포함. title, domain, status 필수 필드 |
| INDEX.md 존재 | docs/INDEX.md |

실패 항목이 있으면:
> ⚠️ adopt 미완료 — 다음 항목이 아직 처리되지 않았습니다:
>   - [실패 항목]
>
> 해당 단계로 돌아가서 완료해야 합니다.

## 주의

- 기존 파일을 삭제하지 않는다. 이동하거나 이름을 바꾼다.
- 사용자 확인 없이 파일을 수정하지 않는다.
- git으로 추적 중인 파일은 `git mv`로 이동한다 (이력 보존).
- 이 스킬은 **1회성**이 아니다. 하네스 업그레이드 후 재실행할 수 있다.
- 3회 시도해도 병합이 안 되는 충돌은 사용자에게 보고. 임의 판단 금지.
