---
title: 스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용
domain: harness
tags: [skill, agent, routing, orchestration, audit]
relates-to:
  - path: harness/hn_implementation_router.md
    rel: extends
  - path: WIP/harness--hn_info_flow_leak_phase3.md
    rel: references
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# 스킬·에이전트 역할 분담 감사

## 배경

implementation 스킬을 "라우터"로 재정의하는 작업(2026-04-20 완료, 229줄)에서
적용한 원칙을 다른 스킬·에이전트에도 확장하기 위한 codebase-analyst 전수 감사.

### 5가지 원칙 (분리 + 전달·유지)

**분리 축 (역할 경계):**
1. **고유 책임 / 위임 대상 표** — 서두에 역할 경계 명문화
2. **TRIGGER/SKIP 재설계** — 승인 표현·연속 작업 재발화·모호 SKIP 정밀화
3. **비대화 차단** — 판단·분석·검증 로직을 내재화하지 말고 specialist에 위임
4. **중복 제거** — 같은 호출 규약·경계 선언을 두 파일에 쓰지 않음

**전달·유지 축 (정보 흐름 — 사용자 지적으로 추가):**
5. **핸드오프 계약** — 스킬·에이전트가 분리되는 순간 "무엇을 다음 단계에
   넘기는가 / 무엇을 끝까지 유지하는가"를 명시. 분리만 하고 전달 규약이
   없으면 정보 흐름 누수가 재발 (Phase 1·2에서 실측된 문제).

원칙 5의 구성 요소:
- **What to pass**: 다음 단계가 판단하려면 반드시 있어야 할 입력 (diff·
  HARNESS.json·CPS 참조·이전 결정 인용 등)
- **What to preserve**: 호출 체인 내내 유지해야 할 불변량 (위험 신호·
  사용자 원문 고유명사·승격 상태 등)
- **How to signal risk**: 위험·제약·예외를 다음 단계에 어떻게 강조할지
  (⛔ 차단 · ⚠️ 경고 · 🔍 추적 신호 3단계)
- **Where to record**: 체인 끝에서 기록이 남는 위치 (WIP `## 메모`,
  commit log `🔍 review:` 라인, CPS 갱신 등)

### 왜 이게 핵심인가

역할 분리만 하면 각 조각은 깔끔해지지만, 전체 흐름에서 **정보가 사라진다**:
- commit에서 review로 넘길 때 위험 신호 누락 → review가 스코프 오판
- eval 4관점이 "이미 확인된 영역"을 모르면 중복 스캔
- implementation이 doc-finder 결과를 WIP에 박지 않으면 다음 세션 유실

Phase 1·2에서 이미 "정보 흐름 누수"로 분류된 문제. 본 감사는 분리(1~4)
와 동시에 전달(5)을 강제해야 재발 방지.

감사 결과: **3대 과잉 후보 발견** (commit 566줄, eval 508줄, harness-adopt
498줄). implementation 패턴의 "고유 책임 / 위임 대상 표"가 이 3개 모두에
즉시 유용. 단, 원칙 5(핸드오프 계약)도 **각 대상에 반드시 적용** — 분리가
전달 누락을 낳지 않도록.

## 선택지

### 옵션 A. P0 3개 순차 처리 (commit → eval → harness-adopt)

**장점**: 큰 수정이지만 핫 패스부터 효과 확실. 한 세션에 다 들어갈 수도.
**단점**: 세션 길이·컨텍스트 부담. 중간 실측 기회 없이 3개 연속.

### 옵션 B. commit + review 쌍만 먼저

**장점**: 두 파일 사이 호출 규약 중복이 가장 리스크 크고 매 커밋마다 도는
핫 패스. 수정 후 실측 가능.
**단점**: eval·harness-adopt 개선이 지연됨.

### 옵션 C. 저비용 P1부터 (advisor 슬림화 + review 경계 통합)

**장점**: 빠르게 끝나고 패턴 검증 용도로 안전.
**단점**: 가장 큰 영향(commit 566줄)은 계속 남음.

## 결정 (P0~P2 모두 포괄 — 순차 실행)

**전체 작업 범위를 본 문서에 확정하고, 개별 실행은 별도 WIP로 파생**.
순서는 위험·효과 비율로 B → 옵션 A 나머지 → C 잔여 → P2.

### P0. 즉시 처리

#### P0-1. commit/SKILL.md (566줄) — review·test-strategist 호출 규약 중복

**문제:**
- L56-162: review 호출 규약(diff 박기, HARNESS.json 박기, prompt 예시)을
  SKILL.md 본문에 하드코딩. `review.md` L162-195가 같은 규약을 "입력 블록"
  으로 반복 → **수정 시 양쪽 동기화 필요**.
- L419-476: test-strategist 병렬 호출 prompt 템플릿·`base64 -d` 예시가
  스킬 안에 있음.

**권고:**
- review/test-strategist에 넘길 블록 *구조*만 남기고 세부 prompt 예시는
  review.md / test-strategist.md "## 입력" 섹션 포인터로 대체
- "고유 책임 / 위임 대상 표"를 서두에 삽입 → 호출 규약 중복 차단
- L83-199를 1/3로 축소 목표

**핸드오프 계약 (원칙 5):**
- Pass: `diff (base64)` · `HARNESS.json` · `pre-check signals` · `stage`
  · `CPS 참조`
- Preserve: S1·S2·S9 위험 신호 원본 (review가 카테고리 매핑에 그대로 사용)
  · 도메인 등급 · 연속 수정 이력(S10)
- Signal risk: stage 3(deep) 자동 격상 사유를 review에 명시 전달
  (예: `"S9:critical + S2 동반"` 문자열)
- Record: commit log `🔍 review: <stage> | signals | domains` 한 줄
  — 현행 `staging.md` 규정 유지. Stage 0(skip)도 한 줄 남긴다

**예상 효과**: 566 → ~400줄. SSOT 원칙 확보.

#### P0-2. eval/SKILL.md (508줄) — `--deep` 4관점 에이전트 내재화

**문제:**
- L396-432: `--deep` 4관점(파괴자·트렌드·비용·외부공격자) prompt 구성
  가이드가 eval.md 본문에 있음. 이 에이전트들은 별도 파일 없이 eval이
  임시 생성 → **specialist 시스템 우회**.
- L383-393: "4개 Agent 병렬 호출"이라면서 advisor.md의 orchestration
  절차와 사실상 동일한 흐름을 eval 내부에서 중복 구현.

**권고:**
- 4관점을 별도 named agent로 분리 (`.claude/agents/destroyer.md`,
  `trend-analyst.md`, `cost-analyst.md`, `external-attacker.md`) 또는
  advisor 호출로 대체
- 분리 시 eval은 "Step 3: 병렬 호출 — [에이전트 호출 + Step 0/1 결과 박기]"
  로 단축
- L318-432를 포인터+요약으로 대체

**핸드오프 계약 (원칙 5):**
- Pass: `Step 0 스캔 결과` · `Step 1 격차 목록` · `이미 확인된 영역 제외
  리스트` (중복 스캔 방지)
- Preserve: 사용자가 지정한 scope(--harness/--surface/--deep 플래그와
  암묵 범위) · 시크릿 힌트는 서브에이전트에 **전달 금지** (외부공격자
  에이전트가 오남용 가능)
- Signal risk: 4관점 중 하나라도 "차단급 발견" 시 eval 최종 리포트
  맨 위에 ⛔로 격상. 경고급은 ⚠️
- Record: eval은 전용 문서 안 만들고 발견을 사용자에게 직접 보고. 조치가
  필요하면 사용자가 별도 WIP 경로로 진행 (eval 자체는 읽기 전용 건강 검진)

**예상 효과**: 508 → ~400줄 (~100줄 절감). 4관점 재사용 가능.

#### P0-3. harness-adopt/SKILL.md (498줄) — specialist 미호출

**문제:**
- Step 5d/5e (L279-344): 기존 문서 내용 읽고 도메인 추론·프론트매터 초안
  생성·규모별 전략 분기를 스킬이 모두 내재화. codebase-analyst·doc-finder
  활용 여지 있는데 직접 처리.
- Step 5b triage (L199-237): 문서 분류 판단(유지/보관/삭제) 하드코딩.

**주의**: 대화형 대규모 이식 흐름이라 단계 분해 어렵고 specialist 추가
시 라운드트립 비용 큼. **강행 전 실측 필요**.

**권고:**
- "고유 책임 / 위임 대상 표" 서두 삽입이 최우선 — 줄 수 자체보다 **책임
  경계 명시**가 핵심
- 도메인 추론은 직접, 기존 docs 참조는 doc-finder 위임 등 경계 명문화
- 줄 수 감축은 실측 후 판단

**핸드오프 계약 (원칙 5):**
- Pass: 기존 프로젝트 루트 경로 · 발견한 기존 `.claude/` 충돌 목록 ·
  docs 재분류 triage 결과 · 프론트매터 추가 필요 파일 리스트
- Preserve: 사용자 승인 받은 도메인 목록 (추론 결과 아님, 확정된 것) ·
  기존 프로젝트의 원본 파일 백업 경로 · 이식 전 상태 스냅샷
- Signal risk: 기존 README/CLAUDE.md 덮어쓰기 위험은 ⛔로 차단 후 사용자
  명시 승인 필요 (downstream-readiness에서 이미 사고 이력)
- Record: adopt 완료 후 `docs/harness/adopt-session_{YYMMDD}.md`에 결정
  기록 — 다음 harness-upgrade가 참조 가능하도록

### P1. 곧

#### P1-1. advisor — SKILL.md(86줄) vs agent.md(166줄) 중복 제거

**문제:**
- SKILL.md L28-29에서 "얇은 래퍼"임을 자인. 실제 로직은 에이전트에 있음.
- SKILL.md L62-74 "언제 사용하는가 / 사용하지 않는가"가 agents/advisor.md
  description TRIGGER/SKIP(L6-17)과 **내용 중복**.

**권고:**
- description TRIGGER/SKIP을 SSOT로 확정 → SKILL.md "언제 사용" 섹션 제거
- 스킬 본문 = "Step 1~3 + 핵심 원칙" 5줄로 축소

**핸드오프 계약 (원칙 5):**
- Pass: 호출자(implementation 등)가 판단 대상 · 검토할 선택지 · 현재
  컨텍스트(CPS 참조·기존 결정)를 명시적으로 전달
- Preserve: advisor 에이전트가 specialist pool에서 고른 조합 근거 →
  사용자에게 "왜 이 3개를 부르는가" 투명하게 제시
- Signal risk: 결정이 되돌리기 어려운 경우(DB 마이그·공개 API) advisor
  응답에 ⚠️로 강조, 호출자가 WIP `## 메모`에 전문 기록 의무
- Record: advisor 응답 원문을 WIP에 보존 (요약본만 남기면 근거 유실)

- **예상 효과**: 86 → ~40줄

#### P1-2. review.md (432줄) — "~는 eval로 위임" 선언 6회 반복

**문제:**
- L13-17 스코프 선언 + L268-270, L311, L364-366, L374-375, L382-384,
  L391-392에서 동일 경계를 6번 반복.

**권고:**
- 맨 위 "## 작동 모델" 아래 "이 경계 외는 모두 eval로 위임" **한 줄**로
  통합
- implementation 패턴의 "위임 대상 표" 형식 그대로 적용

**핸드오프 계약 (원칙 5):**
- Pass: commit에서 받은 diff·signals·stage·domains 블록 그대로 수용
  (파생 가공 금지 — commit이 SSOT)
- Preserve: 스코프 경계(이번 diff만). 경계 외 발견은 **차단 아님**,
  "eval 권고" 꼬리표로 결과 리포트에 병기
- Signal risk: Stage 3(deep)에서 차단 사유는 ⛔, 권고는 ⚠️, 관찰 기록은
  🔍로 구분 — commit이 이 기호를 그대로 사용자에게 표시
- Record: review 결과는 commit이 받아서 커밋 log `🔍 review:` 라인으로
  영속화. review 자체는 문서 생성 안 함

- **예상 효과**: 432 → ~400줄 (~30줄 절감)

### P2. 관찰 대상 (본 세션 실행 범위 밖)

| 대상 | 줄수 | 문제 | 권고 |
|------|------|------|------|
| harness-init/SKILL.md | 383 | L152-155 "Context7 MCP" 언급이 `internal-first.md` 금지 규칙과 충돌 가능 | `hn_external_research_patterns.md` 포인터로 대체 |
| write-doc/SKILL.md | 193 | Step 2(L58-64) 관련 문서 탐색을 직접 INDEX→clusters로 수행 | doc-finder 위임 전환 |
| naming-convention | 176 | 콤팩트·책임 명확 | 현상 유지 |
| coding-convention | 144 | 콤팩트·책임 명확 | 현상 유지 |
| check-existing | 35 | **가장 타이트. implementation 패턴의 귀감** | 참조 기준 |
| harness-sync | 147 | 단독 흐름, specialist 불필요 | 현상 유지 |

### 사각지대 (이번 감사 미포함)

- `agents/test-strategist.md`, `performance-analyst.md`, `researcher.md`,
  `risk-analyst.md` (85~112줄) — shallow-read만. specialist 간 overlap
  검증 필요
- `commit`이 test-strategist 병렬 호출 시 쓰는 `new_func_lines_b64` 키가
  `pre-commit-check.sh` stdout 스키마에 실제로 존재하는지 교차 검증 미실시

## 재사용 기회

- `.claude/skills/implementation/SKILL.md` L18-41 (고유 책임 / 위임 대상 표)
  → commit, eval, review, harness-adopt 서두 이식 가능
- `.claude/skills/check-existing/SKILL.md` 전체 (35줄) → "30초 안에
  확인·보고·진행" 밀도 기준

## 핸드오프 계약 템플릿 (모든 파생 WIP에서 재사용)

**SSOT**: 핸드오프 계약의 정의는 [implementation/SKILL.md](.claude/skills/implementation/SKILL.md)
"## 핸드오프 계약" 섹션에 위치한다. implementation이 작업 진입점·CPS
허브·오케스트레이터이기 때문이다. 하류 스킬(commit·review·eval·write-doc
등)은 본 정의의 축(Pass/Preserve/Signal risk/Record)과 위험 기호(⛔/⚠️/🔍)를
**그대로 상속**한다.

각 스킬·에이전트 재작성 시 서두에 다음 표를 명시 (축·기호는 SSOT 고정,
내용만 각자 구체화):

```markdown
## 핸드오프 계약

| 축 | 내용 |
|----|------|
| Pass (상류→나) | 내가 판단하려면 반드시 필요한 입력 |
| Pass (나→하류) | 다음 단계에 넘길 최소 패키지 |
| Preserve | 호출 체인 끝까지 유지할 불변량 |
| Signal risk | ⛔ 차단 / ⚠️ 경고 / 🔍 추적 신호 — 어떤 상황에 어느 기호 |
| Record | 체인 끝에서 기록이 남는 위치 (WIP·commit log·CPS 등) |
```

**엄수:**
- "다음 단계가 알아서 추측" 금지 — Pass에 없으면 호출 체인이 깨진 것
- Preserve 불변량이 도중에 가공되면 정보 손실 — 원본 보존
- 3단계 기호는 스킬 간 공통 — 각자 다른 기호 쓰지 말 것

## 실행 순서 (결정)

**전제**: 핸드오프 계약 SSOT는 implementation 스킬에 이미 정의됨
(2026-04-20, 240줄). 하류 스킬은 축·기호를 상속하고 내용만 구체화.
SSOT 스킬 자체에 계약이 없으면 하류 전체가 공중에 뜨므로, 하류 작업
전에 SSOT 상태를 항상 확인.

1. ✅ **P0-1 commit + P1-2 review** — 2026-04-20 완료 (커밋 f28f849)
   - 별도 WIP: `harness/hn_commit_review_handoff.md`
   - advisor 실측 판정으로 D3(호출 규약 포인터화)가 안티패턴 판명 → 취소
   - self-containment 원칙 보존. review.md eval 위임 화살표 10→0
2. ✅ **P0-2 eval** — 2026-04-20 완료 (커밋 0d1514d)
   - 옵션 B 채택 (advisor 대체). threat-analyst 신설(외부공격자).
   - 감사 원 권고(옵션 C 현행 유지)를 사용자 통찰로 뒤집음:
     "codebase-analyst는 있으니 threat만 추가하면 된다" — 4→1 신설
   - 품질 보강: specialist 공통 자가평가 + researcher 업계 탑 인물
   - 별도 WIP: `harness/hn_eval_advisor_migration.md`
   - 연쇄: advisor 판단 엔진 전면 재설계 (171→337줄, 프레임 6개 + 6단계
     Orchestration). 별도 WIP: `harness/hn_advisor_decision_framework.md`
3. ✅ **P0-3 harness-adopt** — 2026-04-20 완료 (본 커밋)
   - 서두 3 섹션 이식 (고유 책임 / 위임 대상 / 핸드오프 계약 상속)
   - 498 → 542줄 (+44, 감사 목표 "경계 명문화 우선" 충족)
   - 본문 Step 1~9 변경 없음. 줄수 감축은 실측 후 재평가로 보류
   - **별도 WIP 생성하지 않음**: 감사 문서(본 문서)가 SSOT. 중복 기록
     금지 원칙 적용
4. ✅ **P1-1 advisor 슬림화** — 2026-04-20 완료 (본 커밋)
   - skills/advisor/SKILL.md 79 → 43줄 (감사 목표 ~40 달성)
   - "흐름" Step 1~3 나열 제거 (에이전트 SSOT로 위임)
   - "핵심 원칙" 5줄 제거 (에이전트 "권한 경계"·"Scaling Rule" 중복)
   - 서두 문장 단축
5. **P2** — 실측 누적 후 재평가

## 메모

- 실측 지표(Phase 3 WIP와 공유):
  - SKILL.md/agent.md 총 줄 수 (현재 대비 감축률)
  - 같은 호출 규약이 2곳 이상에 중복 존재하는 파일 수 (목표: 0)
  - "고유 책임 / 위임 대상 표" 삽입된 스킬 수 / 전체 스킬 수
  - **"핸드오프 계약" 표 삽입된 스킬 수 / 전체 스킬 수** (원칙 5 적용률)
  - 호출 체인 내 Pass 누락으로 인한 재질의·추측 발생 횟수 (목표: 0)
- CPS 영향: P1(LLM 추측 수정)·P5(컨텍스트 팽창)에 간접 기여. 스킬 비대화
  감소 → 각 스킬 로드 시 컨텍스트 절감.
- 본 문서는 **결정만** 기록. 실행은 각 단계별 WIP가 담당하되,
  감사 범위가 이미 확정된 단순 이식(P0-3·P1-1 같은)은 별도 WIP 없이
  본 문서에 실행 결과 직접 기록. **SSOT 중복 금지 원칙**.

### 실측 결과 요약 (2026-04-20 전 단계 완료)

| 단계 | 대상 | 변경 전 | 변경 후 | 비고 |
|------|------|--------|--------|------|
| P0-1 | commit/SKILL.md | 566 | 598 | 핸드오프 계약 + test-strategist prompt 압축 |
| P1-2 | review.md | 432 | 445 | 경계 표 SSOT + 반복 위임 10→0 |
| P0-2 | eval/SKILL.md | 508 | 458 | 4관점 인라인 → advisor 호출 |
| - | advisor.md | 171 | 337 | 판단 엔진 재설계 (프레임 6 + 6단계) |
| - | threat-analyst.md | - | 189 | 신규 (외부 공격면) |
| - | 5 specialist + threat | - | +13×6 | 자가평가 블록 일괄 이식 |
| - | researcher.md | - | +34 | 업계 탑 인물 + external-experts 캐시 |
| P0-3 | harness-adopt/SKILL.md | 498 | 542 | 서두 3 섹션 이식 |
| P1-1 | advisor/SKILL.md | 79 | 43 | 중복 제거 |
| 추가 | rules/docs.md | 106 | 143 | "SSOT 우선 + 분리 판단" + "완료 문서 재개" 섹션 신설 |
| 추가 | implementation/SKILL.md | 245 | 267 | Step 0.8 분기 신설, Step 0.7에서 WIP 열 제거, Step 1 조건부 |
| 추가 | docs-manager/SKILL.md | 263 | 271 | `--reopen` 모드 + Step 2.5 완료 재개 |

**핵심 달성:**
- 호출 규약 2파일 중복 0건
- 핸드오프 계약 SSOT 상속: implementation·commit·review·test-strategist·
  threat-analyst·harness-adopt 6 파일
- advisor 판단 엔진화 (단순 조합 기계 탈출)
- **SSOT 우선·분리 판단 원칙 규칙화**: 이번 세션에서 "harness-adopt
  이식용 WIP를 감사 문서와 중복 생성"한 실수를 규칙으로 코드화.
  rules/docs.md·implementation Step 0.8·docs-manager --reopen 3곳에
  반영. 다음 세션 재발 방지.
- eval 4관점 → 4 specialist 1:1 매핑 (threat-analyst 신설로 대칭 완성)
