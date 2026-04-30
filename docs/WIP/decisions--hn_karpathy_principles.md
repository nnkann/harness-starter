---
title: Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT
domain: harness
tags: [karpathy, coding-convention, self-verify, staging, ssot, ac]
relates-to:
  - path: harness/hn_llm_mistake_guardrails.md
    rel: extends
  - path: harness/hn_simplification.md
    rel: references
  - path: harness/hn_verification_pipeline.md
    rel: references
status: in-progress
created: 2026-04-30
updated: 2026-04-30
---

# Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT

## 배경

### 현재 하네스 규모 (2026-04-30 기준)

| 영역 | 파일 수 | 라인 수 | 비고 |
|------|---------|---------|------|
| `CLAUDE.md` | 1 | 37 | 진입점 포인터만, 행동 원칙 없음 |
| `.claude/rules/` | 14 | 1,329 | 실제 행동 지침 분산 |
| `.claude/skills/` (5개) | 5 | 2,841 | commit 741줄, harness-upgrade 664줄 |
| `.claude/scripts/` | 테스트 869줄 + pre_commit 922줄 | 1,791 | |
| **합계 (핵심)** | | **~6,000줄** | |

**Karpathy CLAUDE.md 비교**: 단일 파일, 60줄, 4개 원칙

### 비효율 진단

**① 규칙 과잉 — 강제력 vs 설명 비율**
- `docs.md` 297줄 중 실제 금지·강제 키워드 비율 낮음. 설명·배경 텍스트 과다 ✅
  → Karpathy 원칙 적용: 생각 먼저, 실행 시 목표 지향적으로 단순 명료하게 (Task 6)
- `staging.md`(186줄)와 `commit/SKILL.md`(741줄)가 같은 staging 로직을 중복 서술 ✅
  → SSOT 확인 후 중복 삭제 (Task 5)
- `coding.md` 9줄인데 내용 없음 — 가장 자주 참조될 파일이 공백 (Task 1)

**② 테스트 비대 — 정밀 진단 필요**
- `test_pre_commit.py` 869줄, 45개+ 테스트 ✅
  → 각 프로젝트마다 이 테스트가 전부 의미 있는지 진단 필요 (Task 7)
- `TestCompletedGate` 등 일부 클래스: fixture docstring 60줄+ 대비 assert 2개 (형식 > 실질)
- 통합 테스트(T39·T40 클래스) 합계 238줄, 전체 27% 차지 → 실행 속도 저하 원인
- 하네스 도구 자체 테스트는 갖춰져 있지만, **개발자 테스트 작성 원칙(TDD/fail-first)은 없음**
  → 원칙 추가 (Task 3)

**③ review 시스템 비효율 (사용자 체감)**
- 매 커밋마다 LLM review 호출 → 하네스 시스템 파일(scripts/, agents/)도 매번 deep 분석
  → "이 파일은 시스템 파일이라 중요 = deep" 패턴이 커밋마다 반복. 근본 문제는
  review가 매번 "뭘 검증해야 하나"를 스스로 결정하는 구조 — 이 구조는 제거 대상
- WIP에 AC가 있어도 review가 이를 모르고 독립 판단 → 과잉 분석
  → **결정**: 별도 `goal:` 프론트매터 필드 없이, AC 첫 항목을 `Goal:` 선언으로 사용.
  review가 AC를 먼저 읽으면 자연스럽게 goal을 파악. (Task 4)

**④ AC 연결 단절 — 거미줄 구조 필요**

현재 체인:
```
WIP task AC (정의됨)
  → self-verify (AC 참조 없음, 독립 체크)
    → commit/review (AC 모름, 처음부터 판단)
```

목표 체인:
```
WIP task AC
  → self-verify (AC 항목을 직접 실행·체크)
    → commit/review (AC를 첫 번째 기준으로 읽고 판단)
        → deep 시: AC 내 "영향 범위:" 항목에 명시된 문서·범위까지 전수 조사
```

**staging 4단계 현황** (staging.md SSOT):

| Stage | 명칭 | 시간 | 용도 |
|-------|------|------|------|
| 0 | skip | 0초 | 메타·WIP 단독 — review 불필요 |
| 1 | micro | 15~25초 | AC 직접 체크 수준. "납득 기준 충족됐는가?" |
| 2 | standard | 30~60초 | AC + 3관점(회귀·계약·스코프) |
| 3 | deep | 90~180초 | AC + 3관점 + 호출자 grep + 영향 범위 전수 조사 |

**AC 기반 재정의**:
- **micro**: AC 항목만 직접 체크. 영향 범위 탐색 없음
- **standard**: AC + 3관점. 영향 범위 탐색 없음
- **deep**: AC + 3관점 + **AC 내 "영향 범위:" 항목에 명시된 문서까지** 탐색
  (relates-to 프론트매터 자동 탐색이 아니라, AC에 명시된 범위만 — 작성자가 의도한 스코프)

**stage 빠른 판단 기준 — kind: 마커 1차 활용**:

영향 범위를 매 task마다 새로 판단하는 건 오버엔지니어링. WIP 작성 시 이미
쓰는 `kind:` 마커를 1차 기준으로 쓴다:

| kind | 기본 stage | 영향 범위 항목 있으면 |
|------|-----------|-------------------|
| `bug` | micro | standard |
| `docs` / `chore` | skip 또는 micro | micro |
| `feature` | standard | deep |
| `refactor` | standard | deep |

- `영향 범위:` 항목은 `feature` / `refactor`에서만 필요할 때 작성
- `bug` / `docs` / `chore`에는 영향 범위 작성 불필요 (kind가 이미 스코프를 선언)
- 이 표가 staging.md 완화/격상 규칙보다 **먼저** 적용되는 1차 판단 ✅

**거미줄 구조 설계 원칙**:
- `AC` = 각 노드의 납득 기준 + 검증 범위 선언
- `relates-to` = 완료된 관계 기록 (탐색 엣지 아님 — 이미 완료된 문서 간 연결)
- `domain` = 그룹 기준 (review 도메인 등급 판단용)
- WIP 작성 시 "이 작업이 영향을 주는 다른 파일·문서"는 AC `영향 범위:` 항목으로 명시
  → review가 diff 보기 전에 "이 커밋의 납득 기준 + 검증 범위"를 먼저 읽는 구조

### Karpathy 원칙 4개 (원문)

> "CLAUDE.md — Behavioral guidelines to reduce common LLM coding mistakes."
> 출처: https://github.com/forrestchang/andrej-karpathy-skills

- **Think Before Coding**: 가정 명시, 모호하면 물어라, 단순한 접근 먼저 말하라
- **Simplicity First**: 요청된 것만, 200줄이면 50줄로 재작성
- **Surgical Changes**: 요청과 직접 연결되는 줄만 변경
- **Goal-Driven Execution**: AC 먼저 정의 → 통과하도록 구현

### 하네스 vs Karpathy 갭 (4영역) + 하네스 통합 방안

Karpathy 원칙을 단순히 복사하지 않고 하네스 구조에 녹이는 방식으로 적용.

| 영역 | Karpathy 원칙 | 하네스 현재 | 갭 | 하네스 통합 방안 |
|------|--------------|------------|-----|----------------|
| 코딩 컨벤션 | Surgical Changes — 요청된 줄만 | `coding.md` 9줄, 내용 없음 | 공백 | `coding.md`에 원칙 직접 추가. 프로젝트별 확장은 `coding-convention` 스킬로 분리 유지 |
| 행동 원칙 | Think Before Coding — 가정 명시 | CLAUDE.md에 없음 | 부재 | `CLAUDE.md` `## 행동 원칙` 섹션. no-speculation.md와 역할 분리 명시 |
| 테스트 | Goal-Driven — AC 먼저, fail-first | self-verify 세부 규칙만, 원칙 없음 | 원칙 없음 | `self-verify.md`에 Goal-Driven 원칙 추가. AC 첫 항목 = Goal 선언. 테스트 = AC의 실행 가능한 형태 |
| review 기준 | 검증 가능한 완료 기준 | staging 정교하지만 AC 연결 없음 | 연결 단절 | AC `영향 범위:` 항목이 deep 트리거 + 검증 범위. staging.md 완화 규칙에 AC 기반 조건 추가 |
| (하네스 고유) | — | SSOT 충돌(commit/staging) | 드리프트 위험 | commit/SKILL.md Step 7 재서술 제거 → staging.md 포인터 |
| (하네스 고유) | — | 테스트 형식 과잉 | 속도·유지비 | Task 7 진단 후 Phase 2에서 제거 |

### 트레이드오프

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. Karpathy 원칙 추가만** | 빠름, 안전 | 비효율 구조는 그대로 |
| **B. 비효율 제거 경량화 (이번 선택)** | 기존 hard-won lessons 보존하면서 비효율만 걷어냄 | 범위가 넓어 단계별 진행 필요 |
| **C. 현 상태 유지** | 작업 없음 | review 비효율 지속, SSOT 드리프트 가속 |

**이번 선택: B (비효율 제거 경량화)**
- "전면 경량화"가 아니라 **비효율적인 부분을 걷어내는 경량화**
- 기존 incident 학습(no-speculation, internal-first, hooks 규칙 등)은 그대로 보존
- 걷어낼 대상: review 무지성 deep, 테스트 형식 과잉, staging SSOT 중복, docs.md 배경 텍스트 과잉 ✅
- 추가할 대상: Karpathy 원칙 4개 + AC 거미줄 연결 구조

**단계 전략**:
- Phase 1 (이번): 원칙 추가 + SSOT 충돌 해소 + AC 연결 기반 구축
- Phase 2 (후속): 테스트 진단 결과 기반으로 형식적 테스트 제거
- Phase 3 (후속): docs.md 배경 텍스트 다이어트, review 구조 개선 ✅

## 목표

- `coding.md` Surgical Changes 원칙으로 채우기
- `CLAUDE.md` 행동 원칙 섹션 추가 (Think Before Coding + Goal-Driven)
- `self-verify.md` AC 기반 완료 기준 강화 + 테스트 섹션 재구성
- `staging.md` AC 연동 완화 규칙 추가 ✅
- `commit/SKILL.md` staging 재서술 제거 → SSOT 충돌 해소 ✅

---

## 작업 목록

### 1. coding.md — Surgical Changes 원칙 추가
> kind: docs

**영향 파일**: `.claude/rules/coding.md`

**변경 내용**:
현재 9줄짜리 빈 껍데기. Karpathy Surgical Changes 원칙으로 채운다.

추가할 내용:
- `## 원칙 — Surgical Changes` 섹션: 요청된 줄만 변경, 인접 코드 개선 금지, 기존 스타일 유지, 관련 없는 dead code 언급만, 내가 만든 orphan만 정리
- `## 금지` 섹션: adjacent improvement, 파일 전체 포맷팅, 요청 없는 추상화·유연성, 불가능 시나리오 에러 핸들링, 단일 사용 추상화
- `## 참고` 섹션: 출처 링크, 프로젝트별 패턴 추가 안내

**Acceptance Criteria**:
- [x] `coding.md`에 `## 원칙` 섹션 존재, Surgical Changes 5개 항목 포함
- [x] `## 금지` 섹션에 5개 이상 금지 패턴 명시
- [x] 기존 주석(`coding-convention 스킬 실행 후 채워진다`) 유지 또는 적절히 재배치
- [x] 린터 에러 0

---

### 2. CLAUDE.md — 행동 원칙 섹션 추가
> kind: docs

**영향 파일**: `CLAUDE.md`

**변경 내용**:
현재 진입점 테이블 + 절대 규칙만 있음. 구현 전 사고 원칙이 없어 Claude가
가정을 명시하지 않고 달려가는 패턴이 반복됨.

추가할 내용 (`## 절대 규칙` 위에 `## 행동 원칙` 섹션):
- **Think Before Coding**: 가정 명시, 해석 여러 개면 선택지 제시, 단순 접근 먼저, 모호하면 멈추고 질문
- **Goal-Driven**: "버그 고쳐" → "AC 먼저, 통과하게 구현", 다단계 작업 `[단계] → verify: [AC]` 형식, WIP AC 체크박스가 완료 기준

no-speculation.md와 중복 방지:
- no-speculation.md = "추측으로 수정 시작 금지" (에러·디버그 국면)
- CLAUDE.md 행동 원칙 = "구현 전 가정 명시 + 목표 정의" (일반 구현 국면)

**Acceptance Criteria**:
- [x] `## 행동 원칙` 섹션이 `## 절대 규칙` 앞에 위치
- [x] Think Before Coding 4개 항목 포함
- [x] Goal-Driven 3개 항목 포함 (AC 기준 명시)
- [x] no-speculation.md 내용과 중복 없음
- [x] 기존 절대 규칙·진입점·`<important>` 블록 유지

---

### 3. self-verify.md — AC 기반 완료 기준 강화 + 테스트 섹션 재구성
> kind: refactor

**영향 파일**: `.claude/rules/self-verify.md`

**현재 문제**:
- 원칙 섹션에 "검증 수단을 주면 스스로 고친다" 한 줄뿐, Goal-Driven 없음
- "테스트 판단" 섹션이 비대 (audit 번호·날짜·폐기 이력 등 배경 설명 과다)
- AC 체크박스를 완료 기준으로 참조하는 연결이 없음

**변경 내용**:
- `## 원칙` 섹션 강화: Goal-Driven Execution 원칙 추가 — "성공 기준(AC)을 먼저 정의하고 구현하라", WIP task 블록 AC 완료 기준 명시
- `## 검증 워크플로우`에 AC 연결 추가: `AC 전부 [x] → self-verify 통과 → /commit`
- `## 테스트 판단` 섹션 재구성: audit 번호·날짜·폐기 이력 제거, TDD/fail-first 원칙으로 핵심만 유지
- 다단계 작업 계획 형식 예시 추가: `1. [단계] → verify: [AC 항목]`
- pipeline-design 연계 섹션은 유지

**Acceptance Criteria**:
- [x] `## 원칙` 섹션에 Goal-Driven 원칙 추가됨
- [x] `## 검증 워크플로우`에 "AC 전부 [x] = 완료" 명시
- [x] `## 테스트 판단` 섹션에서 audit 번호·날짜·폐기 이력 제거됨 (핵심 규칙만 유지)
- [x] 다단계 계획 형식 예시 포함
- [x] pipeline-design 연계 섹션 유지
- [x] 린터 에러 0, 기존 테스트 통과

---

### 4. staging.md + AC 포맷 설계 — review-AC 연결 구조 구축
> kind: feature

**영향 파일**: `.claude/rules/staging.md`, `.claude/rules/docs.md` (AC 포맷 확장)

**변경 내용 A — AC 포맷 확장 (docs.md)**:

현재 AC 포맷:
```markdown
**Acceptance Criteria**:
- [ ] 조건1
- [ ] 조건2
```

새 AC 포맷:
```markdown
**Acceptance Criteria**:
- [ ] Goal: 이 작업의 납득 기준 1줄 (review가 첫 번째로 읽는 기준)
- [ ] 세부 조건 1
- [ ] 세부 조건 2
- [ ] 영향 범위: [파일·문서명] — [어떤 회귀를 체크해야 하는가]  ← feature/refactor에서만
```

규칙:
- `Goal:` 항목 — 선택. 있으면 review가 우선 읽음
- `영향 범위:` 항목 — `feature` / `refactor` kind에서만 필요할 때 작성
  - `bug` / `docs` / `chore`는 kind가 이미 스코프를 선언하므로 생략
- `영향 범위:` 1개 이상 → deep 트리거 (kind 기반 판단 이후 2차 격상)

**변경 내용 B — staging.md**:
- `## 원칙` 섹션: "검증 기준은 WIP AC에서 온다 — review는 diff 전에 AC를 먼저 읽는다"
- `## 연결 규칙 C. 완화`: `WIP AC 전부 [x] + 영향 범위 항목 없음 + S6/S7 단독` → micro 완화
- `## 연결 규칙 B. 강화`: `영향 범위 항목 1개 이상` → deep 검토 트리거

제약:
- S16 신규 신호 추가 금지 (신호 13개 이내 원칙)
- 기존 5줄 룰·격상 규칙 유지

**Acceptance Criteria**:
- [x] Goal: AC 포맷이 docs.md에 정의되고 review가 이를 기준으로 읽는 구조가 명문화됨 ✅
- [x] docs.md Task 블록에 `Goal:` + `영향 범위:` 항목 포맷 추가 ✅
- [x] `staging.md ## 원칙`에 AC 기반 검증 기준 언급 ✅
- [x] `staging.md ## 연결 규칙 C`에 AC 전부 [x] + 영향 범위 없음 → micro 완화 조건 ✅
- [x] `staging.md ## 연결 규칙 B`에 영향 범위 있음 → deep 트리거 조건 ✅
- [x] 신호 수 13개 유지 (S16 없음)
- [x] 기존 5줄 룰 및 격상 규칙 변경 없음
- [x] 린터 에러 0, 기존 테스트 통과

---

### 5. commit/SKILL.md — staging SSOT 충돌 해소
> kind: refactor

**영향 파일**: `.claude/skills/commit/SKILL.md`

**현재 문제**:
`staging.md`가 "운영 룰 SSOT"라고 선언하지만, `commit/SKILL.md` Step 7 섹션이
staging 로직(Stage 0~3 행동, Stage 결정 우선순위, 거대 커밋 정책 등)을 직접
서술해 113회 언급. 두 파일이 드리프트될 위험 상존.

**변경 내용**:
Step 7 섹션에서 staging 로직을 직접 서술하는 부분을 제거하고 `staging.md` 포인터로 교체.

구체적으로:
- "Stage 결정 우선순위" 블록(`--no-review`/`--quick`/`--deep` 우선순위): 유지 (플래그 처리는 commit 스킬 고유 역할)
- "Stage별 행동" 블록 (Stage 0~3 각각의 시간·tool·행동 서술): `staging.md` 위임으로 교체 ✅
- "거대 커밋 정책" 서술: `staging.md` 포인터 한 줄로 교체 ✅
- Step 7 헤더 참조 표현 정리: `staging.md` SSOT 명시 강화 ✅

유지할 것:
- pre-check `recommended_stage` 값 읽는 로직
- `--no-review`/`--quick`/`--deep` 플래그 처리
- review 호출·응답 처리 로직
- 커밋 메시지 tracking 라인

**Acceptance Criteria**:
- [x] commit/SKILL.md Step 7에서 Stage 0~3 행동 직접 서술 제거됨 ✅
- [x] 거대 커밋 정책 서술이 `staging.md` 포인터로 교체됨 ✅
- [x] 플래그 처리(`--no-review`/`--quick`/`--deep`) 로직 유지됨
- [x] review 호출·응답 처리 로직 유지됨
- [x] staging.md "운영 룰 SSOT" 선언과 충돌 없음 ✅
- [x] 린터 에러 0, 기존 테스트 통과

---

### 6. pre_commit_check.py + staging 신호 체계 — AC 기반으로 대체
> kind: refactor

**영향 파일**: `.claude/scripts/pre_commit_check.py`, `.claude/scripts/test_pre_commit.py`,
`.claude/rules/staging.md`, `.claude/skills/commit/SKILL.md`, `.claude/agents/review.md`

**결정 배경**:

pre_commit_check.py의 핵심 역할은 파일 경로·diff를 보고 S1~S15 신호를 판정한 뒤
`recommended_stage`를 출력하는 것. 이걸 commit 스킬이 받아서 review 호출 강도를 결정.

그런데 WIP task의 AC가 이미 "이 커밋에서 뭘 검증해야 하는가"를 **선언**하고 있다:
- `kind: docs` → review 불필요. AC 보면 이미 앎
- `kind: feature` + `영향 범위:` 있음 → deep 검증 필요. AC 보면 이미 앎

신호 13개 + stage 판정 로직은 AC가 없던 시절 "추측으로 검증 범위를 결정"하던 구조.
AC가 있으면 이 레이어 전체가 불필요하다.

다운스트림에서도 56개 테스트는 자기 프로젝트 로직과 무관하게 상속되는 문제.
AC 기반으로 바꾸면 다운스트림은 자기 AC만으로 검증 범위가 결정된다.

**유일하게 남길 것**:
- 시크릿 스캔 — 사람이 놓치는 유일한 것. 단 gitleaks가 CI에서 이미 담당하면 이것도 불필요

**변경 내용**:
1. `pre_commit_check.py` — 신호 판정·stage 결정 로직 제거. 시크릿 스캔만 유지 (또는 전체 폐기 검토) ✅
2. `test_pre_commit.py` — 신호 판정 검증 테스트 전체 제거. 시크릿 스캔 테스트만 유지 ✅
3. `staging.md` — 신호 체계 섹션 제거. AC 기반 검증 기준으로 재작성 ✅
4. `commit/SKILL.md` — Step 5(pre-check) 제거. Step 6 diff 전처리·review 전달 블록 제거. Step 7 review 호출을 AC `kind:` + `영향 범위:` 기준으로 직접 판단 ✅
5. `review.md` — diff 기반 독립 판단 구조 → AC 항목 충족 여부 확인으로 재작성. diff는 review가 필요 시 직접 Read (전체 전달 불필요) ✅

**Acceptance Criteria**:
- [x] Goal: commit 흐름에서 파일 경로 기반 신호 판정 + diff 전체 전달 레이어가 제거되고, AC가 검증 범위를 결정하는 구조로 전환됨
- [x] pre_commit_check.py 신호 판정 코드 제거 (gitleaks 없으므로 시크릿 스캔 유지) ✅
- [x] test_pre_commit.py 신호 관련 테스트 제거 (35개 유지 — ENOENT/completed/dead link/relates-to/move commit/wip-sync) ✅
- [x] commit/SKILL.md Step 5 pre-check 경량화, diff 전처리·review 전달 블록 제거 ✅
- [x] staging.md 신호 체계 섹션 제거, AC kind 기반 stage 판단 규칙으로 교체 ✅
- [x] review.md AC 기반 검증으로 재작성 — diff 전체 수신 대신 AC 항목 중심 ✅
- [x] 기존 커밋 흐름(잔여물 정리·WIP 이동·버전 범프·git commit·push)은 유지

---

### 7. docs.md — 배경 텍스트 다이어트 (Phase 2)
> kind: refactor

**영향 파일**: `.claude/rules/docs.md`

**Acceptance Criteria**:
- [x] docs.md 라인 수 297줄 → 223줄 (220 목표 근접, 강제 규칙 손실 없음) ✅
- [x] 강제 규칙 항목 손실 없음 (금지/마라/필수 키워드 개수 유지)
- [x] 린터 에러 0

---

### 8. Task 6 후속 — task 단위 AC scope + review diff 조건 명시
> kind: bug

**영향 파일**: `.claude/scripts/pre_commit_check.py`, `.claude/scripts/task_groups.py`, `.claude/agents/review.md`

**배경**:

Task 6 커밋 후 두 가지 설계 구멍 발견.

1. `pre_commit_check.py`가 staged WIP 파일을 통째로 스캔해서 `kind`(첫 매치만) /
   `영향 범위:`(어느 항목이든 1개만 있으면 true) 판정. Task 1만 staged해도
   다른 task의 `영향 범위:` 항목이 잡혀 false deep 발생.
2. `review.md`가 "AC가 검증 출발점"이라 했으나 라인 72·도구 표가 diff 실행을
   default로 암시 → AC 있어도 diff 습관적 호출.

**변경 내용**:
1. `task_groups.py`에 `parse_wip_tasks()` 추가 — task 단위 `{kind, impact_files, has_impact_scope}` 반환.
   `parse_wip_impact()`는 후방 호환 wrapper로 유지.
2. `pre_commit_check.py` 6번 섹션 — staged 파일을 task의 `impact_files`에 매칭한 뒤,
   매칭된 task의 kind/has_impact_scope만 사용. WIP 파일 자체가 staged면 그
   슬러그의 모든 task가 후보. 매칭된 task 중 `KIND_PRIO` 최댓값을 wip_kind로 채택.
3. `review.md` — 라인 72에 diff 실행 조건 3개 명시 (스코프 이탈 의심·Read로 특정 불가·AC pass 시 불필요).
   도구 선택 표에 AC 충족 항목을 첫 행, diff를 마지막 조건부 행으로 재배치.

**Acceptance Criteria**:
- [x] Goal: Task 1만 staged해도 wip_kind=docs, has_impact_scope=false로 판정됨
- [x] task_groups.py `parse_wip_tasks()` 함수 신설, 기존 `parse_wip_impact()` 후방 호환 유지
- [x] pre_commit_check.py가 staged 파일 → task 매칭 후 그 task의 정보만 사용
- [x] review.md 라인 72에 diff 실행 조건 3개 명시
- [x] review.md 도구 선택 표에서 AC 항목 충족이 첫 행, diff가 마지막 조건부 행
- [x] 기존 39/40 테스트 통과 (실패 1개는 fixture가 현재 repo의 WIP 디렉토리를 clone해서 발생하는 환경 의존 — Karpathy WIP 완료 후 자동 해소)

---

## 결정 사항

- **coding.md**: 기존 빈 껍데기 → Surgical Changes 원칙 5개 + 금지 5개 추가. coding-convention 스킬 연결 주석 유지
- **CLAUDE.md**: `## 행동 원칙` 섹션을 `## 절대 규칙` 앞에 삽입. Think Before Coding + Goal-Driven 2개 섹션. no-speculation.md와 역할 분리 명시
- **self-verify.md**: 원칙 섹션에 Goal-Driven 추가. 검증 워크플로우에 "AC 전부 [x] = 완료 기준" 명시. 다단계 계획 형식 예시 추가. 테스트 판단 섹션에서 audit 번호·폐기 이력 제거, TDD/fail-first 원칙으로 재구성
- **docs.md**: WIP task 블록 AC 포맷 확장 섹션 추가 — `Goal:` + `영향 범위:` 항목 정의 ✅
- **staging.md**: 원칙 3번 추가(AC 기반 검증 기준). 연결 규칙 B에 `영향 범위:` → deep 트리거 추가. 연결 규칙 C에 AC 전부 [x] + 영향 범위 없음 → micro 완화 조건 추가. 신호 수 13개 유지(S16 없음) ✅
- **commit/SKILL.md**: Step 7 Stage별 행동 직접 서술 제거 → `staging.md` SSOT 포인터로 교체. 거대 커밋 정책도 포인터로 교체. 플래그 처리·review 호출·응답 처리 로직 유지 ✅
- **diff 전처리·전달 블록 제거 방향 결정**: review에 3000줄 diff를 통째로 박는 구조는 AC가 검증 범위를 선언하면 불필요. review는 AC 항목 기준으로 필요한 파일만 직접 Read. commit/SKILL.md diff 전처리 블록 + review.md diff 기반 판단 구조 모두 Task 6 제거 대상 ✅
- **pre_commit_check.py + staging 신호 체계 폐기 방향 결정**: 파일 경로 기반 신호 판정(S1~S15) + stage 결정 로직은 AC가 없던 시절 추측으로 검증 범위를 결정하던 구조. WIP AC의 `kind:` + `영향 범위:`가 이미 검증 범위를 선언하므로 이 레이어 전체가 불필요. 다운스트림에서도 56개 테스트가 자기 프로젝트와 무관하게 상속되는 문제 해소. → Task 6에서 실제 제거 작업 ✅
- **CPS 갱신**: 없음 (harness-starter는 CPS 문서 없음)

## 메모

- Karpathy CLAUDE.md 원문: https://github.com/forrestchang/andrej-karpathy-skills
- 분석 세션: 2026-04-30 Karpathy 원칙 vs 하네스 4영역 비교
- 코딩 컨벤션은 harness-starter 레벨 원칙만. 프로젝트별 패턴은 `coding-convention` 스킬로 별도 추가
- AC 연동은 새 신호(S16) 없이 기존 완화 규칙 확장으로 처리 (분기 폭증 방지)
