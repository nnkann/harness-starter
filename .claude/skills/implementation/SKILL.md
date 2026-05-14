---
name: implementation
description: >-
  작업 오케스트레이터(라우터). CPS 대조 → 규모 판정 → specialist 라우팅 → WIP 관리 → 실행 흐름 조율.
  분석·탐색·검증은 specialist에 위임하고, 이 스킬은 "언제 누구를 부를지"만 결정한다.
  TRIGGER when: (1) 사용자가 기능 구현·버그 수정·리팩토링 등 코드 작업 요청 ("~해줘", "~만들어", "~고쳐", "~추가해"),
  (2) 직전 턴에 구체 계획이 제시된 상태에서 승인 표현 ("진행해줘", "이대로", "OK", "ㅇㅇ", "시작해", "해보자", "고"),
  (3) 직전 작업이 implementation 영역이었어도 후속 작업 트리거는 재발화.
  SKIP: 단순 질문·설명, 문서만 수정(→ write-doc), 단일 settings.json 키-값 토글(스킬/스크립트 로직 수정은 포함 아님),
  커밋 요청(→ commit), 1줄 타이포 수정.
---

# Implementation

작업 오케스트레이터. 지휘자처럼 직접 연주하지 않고 누구를 언제 부를지 결정한다.
완료 처리·이동은 commit 스킬이 담당한다.

## 고유 책임 (이 스킬만 하는 것)

1. 트리거 시점 판단 — "지금이 작업 시작 시점"
2. 라우팅 — 작업에 어떤 specialist가 필요한가
3. WIP 문서 관리 — 작업 추적 단위
4. CPS 매핑 — 작업 ↔ Problem 연결 (갱신은 `docs_ops.py` 또는 write-doc)
5. 실행 흐름 조율 — Step 진행·escalate·완료 신호

## 위임 대상 (여기서 하지 않는 것)

| 영역 | 위임 |
|------|------|
| 문서 탐색 | doc-finder |
| 내부 코드 분석·패턴 영향 | codebase-analyst |
| 외부 자료·라이브러리 조사 | researcher |
| 접근법 비교·권고 종합 | advisor |
| 위험·반대 논거 | risk-analyst |
| 성능 분석 | performance-analyst |
| 중복 함수 확인 | check-existing 스킬 |
| 커밋 전 검증 | review (커밋 시점) |
| 문서 정합성 | `.claude/scripts/docs_ops.py` |

**판단·분석·검증 로직을 이 문서에 박지 마라.** 라우터는 라우팅만 한다.

## 핸드오프 계약 (SSOT)

implementation은 작업의 **진입점·CPS 허브·오케스트레이터**다. 따라서 하네스
전체의 핸드오프 계약 정의가 이 스킬에서 시작된다. 하류 스킬(commit·review·
eval·write-doc 등)은 본 계약의 축·기호·Record 위치를 **그대로 상속**하며
각자의 축 값만 구체화한다.

역할 분리만으로는 정보가 사라진다. 아래 계약을 호출 체인 끝까지 유지.

| 축 | 내용 |
|----|------|
| Pass (사용자→나) | 작업 요청 원문(고유명사 포함) · 승인 표현 · 직전 턴의 계획 |
| Pass (나→specialist) | 작업 단위 · CPS Problem 참조 · 규모 판정 결과 · 이미 확인된 내부 자료(중복 탐색 방지) |
| Pass (나→commit) | WIP 파일 경로 · status · `## 결정 사항`·`## 메모` 내용 · CPS 갱신 여부 |
| Preserve | 사용자 원문 고유명사(doc-finder 검색 키) · CPS Problem 연결 · specialist 응답 원문(요약 금지) · 위험 신호 원본 |
| Signal risk | ⛔ 차단(init 미완료·3회 시도 실패·복구 불가) · ⚠️ 경고(위험 hit·large 규모) · 🔍 추적(specialist 호출 기록·WIP 갱신) |
| Record | WIP `## 결정 사항`(결정+반영 위치) · `## 메모`(specialist 결과·CPS 갱신) · 이후 commit이 log로 영속화 |

**엄수:**
- Pass에 없는 정보를 specialist가 추측하게 두지 마라 — 재질의 또는 본인 확인 후 전달
- specialist 응답을 요약해서 WIP에 넣지 마라 — 원문 보존, 근거 유실 방지
- 3기호는 스킬 간 공통 — 다른 기호 사용 금지

## 흐름

### Step 0. CPS 대조 + Problem 매칭 (작업 시작 전)

먼저 harness-init이 완료되었는지 확인한다.

**init 미완료 감지** (v0.34.0 — A4 의미 재정의):

다음 두 케이스 중 하나면 init 안 돈 신규 프로젝트다. **작업을 시작하지
않고 차단한다:**

1. `docs/guides/project_kickoff.md` 부재
2. `docs/guides/project_kickoff.md`의 frontmatter `status: sample`

> `docs/guides/project_kickoff_sample.md`는 harness-adopt 배포물 일부로
> 정상 환경에서도 존재할 수 있다. 차단 판정에 사용하지 않는다.
> 실 kickoff(`project_kickoff.md`) 자체의 존재·status가 SSOT.

판정 로직 SSOT: `.claude/scripts/check_init_done.sh` (회귀 테스트 가능,
다운스트림 자가 점검 용도).

> ⛔ 하네스 초기화가 완료되지 않았습니다. CPS와 기술 스택 없이는 작업을 시작할 수 없습니다.
>
> - 신규 프로젝트: `/harness-init` 실행
> - 기존 프로젝트에 하네스 이식: `/harness-adopt` → `/harness-init` 순서로 실행

이 게이트는 건너뛸 수 없다. init/adopt를 완료해야 implementation이 동작한다.

> **CLAUDE.md `## 환경` drift는 차단 사유 아님** — 다운스트림이 자기
> 양식·언어로 채울 자유가 있다 (C++/CMake처럼 `패키지 매니저:` 키 N/A
> 케이스). drift 단독으로는 차단하지 않는다. v0.33.x까지의 단일 키
> 검사는 baseline 측정에서 false-block + 15~19s 헛돔으로 입증됨
> (`docs/decisions/hn_init_gate_redesign.md` ADR).

**init 완료 상태:**
docs/guides/에 CPS 문서(`project_kickoff.md`)를 Read.
`status: sample`인 문서는 예제이므로 무시한다.

#### Problem 매칭 (필수)

작업 발화 → 의도 1줄 추출 → CPS Problem(P1~P6 또는 다운스트림 정의)에 매칭.

**매칭 진입점**: 먼저 `.claude/HARNESS_MAP.md` CPS 테이블(1줄 요약)에서 후보 확인.
테이블로 특정 불가 시에만 `docs/guides/project_kickoff.md` 전체 Read.

| 매칭 결과 | 행동 |
|---------|------|
| **hit** (의미 거리 가까움) | Problem ID 확정. WIP frontmatter `problem: P#`에 박음 |
| **miss + 병합 후보** | 의미 거리 가까움이지만 정확 매칭 없음 → 기존 Problem 본문 확장. write-doc 위임. **단독 판단** |
| **miss + 추가 후보** | 의미 거리 멀고 새 영역 → 신규 Problem 등록. write-doc 위임. **단독 판단** |
| **Solution 충족 기준 변경** | 프로젝트 owner 승인 필수. 추측 금지 |
| **BIT NEW 플래그** | WIP `## 발견된 스코프 외 이슈`의 `P#: NEW — "..."` 항목을 P# 등록 후보로 자동 인식. 작업 발화와 별개로 각 NEW 항목을 위 매칭 표에 적용해 처리한다. P# 추가는 Claude 단독 판단 가능 (docs.md "CPS 변경 권한" 참조) |

판단 근거 1줄을 WIP `## 메모`에 기록.

#### Solution 인용 (필수, 번호만)

매칭된 Problem의 Solution을 번호로 인용 (50자 박제 폐기 — 2026-05-14):

```yaml
problem: P3
s: [S2, S6]                       # Solution 번호 list (인라인)
```

여러 Solution 다루면 list 항목 추가. 형식 SSOT: `.claude/rules/docs.md` "## CPS 인용".

#### CPS 정합 substep (확정 전 — 자동)

C·P·S 매칭 직후 결정적 grep으로 정합 측정:

1. C 키워드 추출 (WIP `## 목표` 또는 작업 발화)
2. P# 정의를 `docs_ops.py cps show P#`로 가져옴
3. S# 정의를 kickoff 표에서 grep
4. **3축 교집합 비율**:
   - C·P 키워드 교집합 비율
   - P·S 키워드 교집합 비율
   - C·S 키워드 교집합 비율
5. **임계값 0.3** (wave 누적되며 좁혀나감)
6. 임계 미달 1줄 알림 — "C·S 정합 약함" 등

**어긋남 후속 행동**: 감지·알림만. **자동 후보 발굴 없음**.
사용자/Claude 판단:
- C 재정의 → WIP 본문 수정
- 새 P# → `docs_ops.py cps add "1줄"`
- 무시 → 진행

자가 발화 의존 회피 — 자동 후보 제안은 본 wave 안 박음. 다음 wave 영역.
옵트인 단독 호출: `/cps-check`.

#### doc-finder 호출 (선택)

작업 키워드로 기존 자산 확인 — Step 0.3에서 처리.

CPS Problem 연결이 불명확하면 사용자에게 질문하라. 추측 금지.

### Step 0.3. 기존 자산 확인 (doc-finder fast scan — skip 금지)

CPS 대조 직후 doc-finder에 작업 키워드를 넘겨 fast scan 실행.

```
doc-finder fast scan 요청 내용:
  - 키워드: 작업 발화의 핵심 개념어 2~3개
  - 탐색: 파일명·태그 Grep만 (본문 Read 없음, tool calls 3회 이내)
  - 반환: hit 파일 경로 목록 또는 "없음"
```

hit 있으면 → deep scan으로 전환해 핵심 요약 확인.
hit 없으면 → "없음" 즉시 기록 후 종료.

결과를 WIP `## 사전 준비`의 "읽을 문서:" 항목에 기록.
탐색 사실 자체가 기록 대상 — hit 없어도 "doc-finder fast scan: 없음" 명시.

### Step 0.5. 접근법 검증 (선택)

작업의 접근법이 정리되면 사용자에게 묻는다:

> "이 접근법을 검증할까요? [Y/n]"

**Y 선택 시**: advisor 스킬의 리서치 + 코드분석 에이전트 2개를 병렬 호출한다.
- 리서치: "이 접근법에 대한 공식 문서, 업계 사례, 알려진 문제점"
- 코드분석: "현재 코드베이스에서 이 접근법이 기존 패턴과 충돌하는지"
- 결과를 Step 1에서 만드는 WIP 문서의 `## 메모`에 자동 기록

**N 선택 시 또는 무응답**: 건너뛰고 Step 1로 진행한다.

이 단계는 **작업 규모가 클 때**만 의미 있다. 파일 1~2개 수정하는 작업에는 제안하지 않는다.

### Step 0.7. 규모·위험도 분기 (specialist 호출 강도 결정)

사용자 발화 + 예상 변경 범위로 판정. 이후 Step 2.5의 specialist 호출
강도 결정에만 사용. **WIP 생성 여부는 Step 0.8이 담당.**

| 규모 | 기준 | specialist 호출 |
|------|------|-----------------|
| micro | 단일 파일, <20줄, 리스크 낮음 | 없음 (commit이 검증) |
| small | 단일 파일 20~100줄 또는 다중 파일 <3개 | doc-finder 1회 |
| medium | 3~10 파일 또는 1 파일 <300줄 구조 변경 | doc-finder + codebase-analyst, 위험도 hit 시 risk-analyst |
| large | 10+ 파일 또는 핵심 구조 변경 | advisor 필수 (PM이 specialist pool 오케스트레이션) |

**위험도 hit 신호**: 공개 API 변경, 인증/보안 경로, DB 마이그레이션, 되돌리기
어려운 결정, 핵심 설정(CLAUDE.md/rules/settings.json) 구조 변경.

### Step 0.8. SSOT 우선·분리 판단 (WIP 생성 여부 결정)

**`.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" SSOT 적용.**

의무 절차 (docs.md에서 상세):
1. **3단계 탐색** — cluster 스캔 → 키워드 grep → 후보 본문 Read.
   감사 문서·decisions/·상위 WIP를 놓치지 않기 위한 필수 절차.
2. **두 질문** — SSOT 존재 / 분리 필요성
3. **실패 모드 체크리스트** — 5개 중 하나라도 해당하면 재실행

요약:

1. **이 결정·계획의 SSOT가 이미 있는가?**
   - 있으면 거기를 갱신 (필요 시 completed → in-progress 재개,
     `rules/docs.md` "완료 문서 재개" 참조). **같은 내용 새 WIP 복제 금지**.
2. **분리가 필요한가?** — `rules/docs.md` 판단 기준 적용. 단순 지표 금지.

**분리 필요 시**: Step 1로 진행 (새 WIP 생성).
**분리 불필요 시**: WIP 없이 바로 Step 2.5(실행 흐름). 실행 결과는 상류
SSOT 갱신 또는 commit 메시지에 기록.
**탐색 결과 기록 의무**: "분리 불필요" 판정 시에도 doc-finder 탐색 결과·
CPS 매칭 근거를 상류 SSOT `## 메모`에 기록한다. 기록 위치 없으면 commit
메시지 본문에 `[doc-finder: 결과 요약]` 인라인. 묵시적 소실 금지.

**large 규모라도 SSOT 재갱신이면 새 WIP 생성 안 함**. advisor 응답은 그
SSOT 문서의 `## 메모`에 기록.

### Step 0.9. 여러 WIP 간 실행 순서 결정 (WIP 2개 이상일 때만)

분리 판단 후 WIP가 2개 이상이면:

1. 의존성 맵 작성 — 어떤 WIP가 다른 WIP의 결과물을 전제로 쓰는가
2. 순서 결정 (Phase 간 실행 순서 원칙 적용)
3. 각 WIP의 `## 메모`에 "실행 순서: N번째, 선행 조건: <WIP명 또는 없음>" 기록
4. 사용자에게 순서 제시

단일 WIP이면 이 단계 skip.

### Step 1. 문서 생성 (Step 0.8이 "분리 필요" 판정한 경우만)

**Step 0.8에서 "분리 불필요" 또는 "기존 SSOT 재개"로 판정됐으면 이 단계
스킵**. 기존 SSOT 문서를 `docs/WIP/`로 되돌린 뒤 `status: in-progress`로
재개 (`rules/docs.md` "완료 문서 재개" 참조) 또는 WIP 없이 바로 Step 2.5.

분리 필요 시 docs/WIP/에 문서를 만든다.

**파일명** (SSOT: `.claude/rules/naming.md` "파일명 — WIP"):

```
{대상폴더}--{abbr}_{slug}.md              모든 대상 폴더
```

- `{대상폴더}--`: WIP 라우팅 태그 (decisions / guides / incidents / harness).
  commit 시 `docs_ops.py move`가 제거하고 본 폴더로 이동
- `abbr`: naming.md "도메인 약어" 표의 값 (도메인당 1개)
- `slug`: snake_case 의미명. 주제 자체 (세분화는 `tags:` 프론트매터로)
- **날짜 suffix 전면 금지** (incidents 포함). 발생 시점은 프론트매터
  `created` + git history가 담당. 같은 주제는 같은 파일 갱신 (`## 변경 이력`
  섹션 누적)

예시 (WIP → 이동 후):
- `decisions--hn_auth_stack.md` → `docs/decisions/hn_auth_stack.md`
- `incidents--hn_token_refresh.md` → `docs/incidents/hn_token_refresh.md`
- `guides--hn_payment_api.md` → `docs/guides/hn_payment_api.md`

전역 마스터 문서(도메인 횡단)는 abbr 생략: `{대상폴더}--{slug}.md`.
예: `guides--project_kickoff.md`.

문서 구조:
```markdown
---
title: {작업 제목}
domain: {CPS 도메인 또는 harness/meta}
problem: P{번호}                  # 필수 (CPS 인용)
solution-ref:                     # 필수 (CPS 인용, list)
  - S{번호} — "{원문 또는 substring + (부분)}"
tags: []
relates-to: []
status: pending
created: {YYYY-MM-DD}
---

# {작업 제목}

## 사전 준비
- 읽을 문서: (경로 목록 또는 "없음")
- 이전 산출물: (이전 Phase 결과물 또는 "없음")
- MAP 참조: (HARNESS_MAP.md에서 확인한 Rules/Skills/Agents 행 또는 "없음")

## 목표
- 이 작업에서 결정하거나 만들 것
- CPS 연결: frontmatter `problem`·`solution-ref` 인용 충족 기준의 어느 측면을 충족하는가

## 작업 목록
### 1. {Phase 제목}

**사전 준비**: ...
**영향 파일**: ...
**Acceptance Criteria**:
- [ ] Goal: {1줄 — 이 작업이 충족하려는 것}
  검증:
    tests: <pytest 명령 또는 "없음">
    실측: <구체 명령·조건 또는 "운용 검증">
- [ ] {충족 기준 1}
- [ ] {충족 기준 2}

## 결정 사항
(작업하면서 채움)

## 메모
(작업 중 발견한 것, 변경 이유 등)
```

- domain·problem·s는 필수. 누락 시 commit 차단.
- frontmatter SSOT: `.claude/rules/docs.md` "## CPS 인용".
- AC SSOT: `.claude/rules/docs.md` "## AC 포맷".
- Goal·tests·실측 3필드 필수. `검증.review` 5단계 자가 선언 폐기 (2026-05-14 §S-2) — review 호출은 `/commit --review`/`--no-review`.

문서가 먼저 존재해야 작업을 시작한다.

#### `폐기` (호환성 — 코드에서 더 이상 읽지 않음)

- WIP task `> kind:` 마커
- AC `영향 범위:` 항목

기존 문서 잔재는 동작 무관.

### Step 2. 작업 시작: 상태 변경

`status: pending` → `status: in-progress`로 변경한다.

### Phase 설계 원칙 (Step 2.5 진입 전 적용)

**6대 원칙:**

1. **자기완결성** — 각 Phase는 이전 대화 참조 없이 실행 가능해야 한다.
   `## 사전 준비`에 필요한 모든 맥락을 기록.

2. **사전 준비 명시** — 읽어야 할 문서 경로·이전 Phase 산출물을 반드시 기록.
   비어도 되지만 "없음"으로 명시 (묵시적 생략 금지).

3. **하나의 Phase = 하나의 레이어/모듈** — 한 Phase에서 여러 레이어(UI + API + DB)를
   동시에 건드리지 않는다. 영향 파일이 서로 다른 도메인이면 분리.

4. **실행 가능한 AC** — 추상 서술 금지. Claude가 직접 실행하거나 사람이
   화면으로 확인할 수 있는 조건만. AC 없는 Phase는 완료 선언 불가.

5. **Scope 최소화** — 단일 파일 5줄 이하 변경은 같은 도메인 Phase에 묶음.
   Phase가 길어지면 분리 신호.

6. **구체적 주의사항** — "조심해라" 금지. "X를 하지 마라. 이유는 Y다" 형식.
   Phase 본문에 직접 박는다.

**Phase 간 실행 순서:**

1. **의존성 우선** — 다른 Phase가 전제로 쓰는 것을 먼저.
2. **위험도 높은 것 먼저** — 되돌리기 어려운 변경(설정·공개 API)을 앞에.
3. **검증 빠른 것 먼저** — AC 실행이 빠른 Phase를 앞에. 막힘 조기 감지.

### Step 2.5. 실행 흐름 (라우팅만)

코드 수정은 메인 Claude가 수행. 이 스킬이 하는 일:

1. **작업 단위 분해** — TodoWrite로 단위 목록 관리
2. **단위별 specialist 트리거 판단**:
   - 새 함수·모듈 직전 → check-existing 스킬
   - 외부 라이브러리 도입 직전 → researcher
   - 기존 패턴 영향 의심 → codebase-analyst
   - 위험 결정 직전 → risk-analyst
   - 성능 민감 변경 → performance-analyst
3. **Phase(작업 단위) 완료 직후 AC 실행 — 필수, 생략 불가**
   - **자동화 가능 AC**: Bash로 실행하고 결과를 사용자에게 제시. 실행 기록 없이 "완료" 선언 금지.
   - **자동화 불가 AC** (Claude 행동·UI 동작·운용 효과): "자동 검증 불가 — 운용에서 확인 필요" 명시 의무. 커버되는 범위와 안 되는 범위를 구분해서 제시.
   - **테스트 스위트**: AC가 명시 요구할 때만 실행 (`영향 범위:` 항목에 `pytest -m <marker>` 표현). 무조건 매 변경 실행 금지. 회귀 가드 가치 있는 변경이면 AC에 marker를 명시. self-verify.md "트리거 매트릭스" SSOT.
   - **AC 미통과 → "완료" 선언 금지.** 즉시 원인 파악 후 재수정.
4. **단위 완료 시 WIP 갱신** — `## 결정 사항` / `## 메모`에 기록. specialist
   응답은 **원문 보존** (요약 금지 — 근거 유실). 핸드오프 계약의 Preserve·
   Record 축 준수.

**판단 원칙**: specialist SKIP 조건에 해당하면 호출하지 마라. 남발 금지.

### Step 3. 작업 중: 기록

- `## 결정 사항`: 결정 + 이유 + 반영 위치 (예: "→ 반영: CLAUDE.md ## 환경")
- `## 메모`: 발견·변경 이유·specialist 응답 원문
- 핸드오프 계약의 Record 축 준수

**스코프 외 버그 발견 시**: 어느 Step에서든 스코프 외 이슈를 발견하면
즉시 `.claude/rules/bug-interrupt.md` 적용. "나중에 처리" 금지.

### Step 4. 작업 완료 + CPS Context 업데이트

`status: in-progress` → `status: completed`로 변경한다.

**CPS Context 업데이트 (사이클 완성):**
작업 결과가 기존 CPS에 영향을 주는지 확인한다:

| 상황 | 행동 |
|------|------|
| 새 Problem을 발견했다 | CPS 문서의 Problem 섹션에 추가 |
| 기존 Solution이 바뀌었다 | CPS 문서의 Solution 섹션 갱신 |
| Context가 달라졌다 (전제 변경) | CPS 문서의 Context 섹션 갱신 |
| 새 도메인이 생겼다 | CPS 도메인 목록 + naming.md에 추가 |
| 변경 없음 | **WIP `## 결정 사항`에 "CPS 갱신: 없음" 명시** (묵시적 생략 금지) |

CPS 문서를 갱신했으면 WIP 문서의 `## 메모`에 "CPS 갱신: [변경 내용]"을 기록한다.

**설계 재편 감지 (Task 완료 외 CPS 갱신 트리거):**

Task 완료가 아니더라도 아래 이벤트가 발생하면 CPS `ssot:` 링크와 `current:` 라인을 갱신한다:

| 이벤트 | 확인 항목 |
|--------|----------|
| Task 역할 재정의 (draft 번호 올라감) | CPS Solution의 해당 항목 `ssot:` 링크 + 설명 갱신 |
| Task WIP 파일 archived로 이동 | CPS `ssot:` 링크에서 해당 경로 제거 또는 갱신 |
| 다른 Task가 현재 Task 기능을 흡수 | 흡수된 Task의 CPS Solution 항목 삭제 또는 병합 |

이 이벤트는 implementation 완료 흐름 밖에서 발생하므로 **사용자가 직접 판단**해야 한다.
설계 재편 시 이 체크리스트를 확인하라는 알림을 WIP 메모에 남긴다:
`## 메모: 설계 재편 — CPS ssot:/current: 갱신 확인 필요`

이후는 commit 스킬이 처리한다 (커밋 시 WIP 파일명의 `{대상폴더}--` 접두사 기준으로 docs/{decisions,guides,incidents,harness}/ 중 해당 폴더로 이동).

## 실패·escalate 흐름

AC 미달성 시 escalate 흐름 (`no-speculation.md` 준수):

막힘 유형 분류 → 에이전트 즉시 위임:

| 막힘 유형 | 에이전트 | 조건 |
|----------|---------|------|
| 에러·테스트 실패 (원인 불명) | debug-specialist | 1회 실패 즉시 |
| 접근법 자체가 막막할 때 | advisor | 방향이 보이지 않을 때 |
| 에이전트 위임 후에도 미해결 | 사용자 보고 | — |

**"3회 규칙" 재정의** (삭제 아님):
- 기존: "같은 접근법 3회 실패 → specialist 호출"
- 변경: "에이전트 위임 사이클(위임→시도→실패) 3회 → 사용자 보고"

**사용자 보고**: 추측으로 넘어가지 말고 현재 상태·시도 내역·막힌 지점을
보고. "이걸로 될까요?"로 검증 책임 떠넘기기 금지.

**중단**: 복구 불가 판단 시 WIP status `in-progress` → `abandoned`,
`## 메모`에 중단 사유 기록. commit 스킬이 archived/로 이동.

## 상태 값

| 상태 | 의미 |
|------|------|
| pending | 계획만 잡음. 아직 시작 안 함. |
| in-progress | 작업 진행 중. |
| completed | 작업 완료. 커밋 시 이동 대상. |
| abandoned | 중단. 커밋 시 archived/로 이동. |

## docs/WIP/ 규칙

- 이 폴더에 파일이 있다 = 할 일이 있다.
- completed/abandoned 파일이 남아있으면 안 된다 (commit이 정리).
- 문서는 결정·이유·반영 위치만 기록. 본문 50줄 이내 권장. 장문 금지.
