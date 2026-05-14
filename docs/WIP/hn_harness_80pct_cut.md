---
title: 하네스 73% 삭감 설계 — 통제에서 가속으로
domain: harness
problem: [P2, P5, P6, P7, P8, P9]
s: [S2, S5, S6, S8, S9]
tags: [redesign, simplify, philosophy-shift, fast-help, adr]
relates-to:
  - path: archived/hn_harness_recovery_v0_41_baseline.md
    rel: extends
  - path: decisions/hn_orchestrator_mechanism.md
    rel: supersedes
status: in-progress
created: 2026-05-14
updated: 2026-05-15
---

# 하네스 73% 삭감 설계 (ADR)

## 0. 결정 박제

본 문서 위치: `docs/decisions/hn_harness_73pct_cut.md` (ADR).
실행 절차 가이드는 별도 분리.

**관점**: "잘하게 만든다"(통제) 폐기. "빠르게 도와준다"(가속) 채택.

**핵심 원칙**:
- 영역별 순서로 진행. **각 영역 안에선 폐기·신설·갱신 즉시 완료**. 다른 영역으로 미루지 않음
- 영역 완료 시 사용자 1차 체감 → 다음 영역
- 실행 단계 HIL 최소 — 문제 발생 시 처리 후 자체 재검증
- rules 폐기·축약 전 본문 전체 Read 의무
- 자동 검증 단언 금지 — 사용자 운용 판정이 통과 게이트
- v0.41 baseline 회복 wave는 archived. 본 wave가 후속이자 73% 삭감 박제

**Step 명명 원칙**: 모든 Step은 정수만 (Step 1, 2, 3...). 소수점 금지 —
중간 단계 착각 유발.

## 1. 현 하네스 실측 (4구간)

### 1.1 Task 도출 — 사용자 발화 → 작업 단위 확정까지

현 흐름은 implementation Step 0~0.9(소수점 7개)이 발화부터 첫 코드 수정
사이에 7가지 메타 처리를 강제: SessionStart hook (1만 토큰+) · CPS Problem
매칭 · doc-finder fast scan · advisor 검증 질문 · 규모 분기 · SSOT 5체크리스트 ·
WIP frontmatter 9필드. 평균 8~12 tool call.

#### 병목 분류

| # | 병목 | 분류 | 처리 |
|---|------|------|------|
| T1 | 8~12 tool call 메타 처리 | 통제 | 절차 통합 → 2~3 tool call 목표 |
| T2 | CPS Problem 매칭 형식만 강제 | 재설계 | CPS는 자라는 시스템으로 |
| T3 | doc-finder "skip 금지" 강제 | 가속 자산 | 강제만 풀고 자동 흐름으로 |
| T4 | SSOT 분리 판단 5체크리스트 | 가속 자산 | 5체크 → 4단계 압축 |
| T5 | AC `검증.review` 5단계 자가 선언 | 통제 | AC 자체 유지, 5단계만 폐기 |
| T6 | WIP 라우팅 태그 `{대상폴더}--` | 통제 | 폐기, 처음부터 `abbr_slug` |

#### T2 — CPS는 자라는 시스템 (사용자 본질 정의)

> "어떤 프로젝트라도 범용적으로 사용자가 글을 넣으면 그게 무슨 맥락인지
> 판단하고(C), 문제나 방법을 찾으며(P), 수정하거나 구현(S)을 하지.
> 특정 problem에 매칭하는 게 중요한게 아니고, 말 그대로 지식을 쌓고
> 현명해 지는 시스템이여야 해."

매칭이 본질 아님. **지식 누적 + 빠른 감각**이 본질. 매칭 강제 = 본질 왜곡.

상세 설계는 §S-1.

#### T3 — doc-finder + frontmatter 자산 유지

탐색 행위 유지. frontmatter + abbr + cluster 자동매핑은 두 달 작업의 가장
실감 자산 (사용자 평가). "skip 금지 강제"만 풀고 메인 Claude Grep 자동 흐름으로.

#### T4 — SSOT 탐색 본능 유지

> "SSOT를 먼저 찾는 버릇은 이 하네스를 쓰면서 좋았던 것. 유일하게 긍정적
> 이었던 부분. 정말 미친듯이 느려도 참아낼 수 있는 부분."

5체크 형식만 4단계로 압축: cluster 스캔 → 키워드 grep → 후보 Read → 갱신 vs 신규 판단.

#### T5 — AC 본질 유지, `검증.review` 5단계만 폐기

- (a) AC 자체 = task 완료 기준. 유지가 당연
- (b) `검증.review` 5단계 자가 선언 = LLM 자가 선언이라 분류 무의미

폐기 대상은 (b)만. (a)는 `Goal:` · `tests:` · `실측:` 3필드 유지.

#### T6 — 라우팅 태그 폐기

WIP 생성부터 `{abbr}_{slug}` 명명. 이동 시 폴더만 결정.

#### 가속 잔존 가치 (구간 1)

- `docs/WIP/` 디렉토리
- `naming.md` abbr 표 + 파일명 grep 체인 (가장 실감 자산)
- doc-finder + frontmatter 페어
- SSOT 탐색 본능

### 1.2 Task 구현 — 작업 단위 → 코드 변경까지

현 흐름은 implementation Step 2.5의 Phase 6원칙 + specialist 5종 라우팅 +
check-existing 강제 + AC 자동 실행 + WIP `## 결정 사항`·`## 메모` 갱신.

#### 병목 분류

| # | 병목 | 분류 | 처리 |
|---|------|------|------|
| I1 | Phase 6원칙 | 통제 | 2원칙으로 압축 |
| I2 | specialist 5종 라우팅 매트릭스 | 통제 | description SSOT 재설계 |
| I3 | check-existing 스킬 강제 | 통제 | 스킬 폐기 + LSP/Grep 자동화 |
| I4 | WIP `## 결정 사항` 형식 | 통제 | 자유 형식 |
| I5 | specialist 응답 원문 보존 강제 | 통제 | 핵심만 인용 |
| I6 | Phase별 AC 자동 실행 | 위치 오류 | commit → implementation 위치 이동 |

#### I1 — 첫 선언 2원칙

첫 선언 시점에 진짜 필요한 건:
1. 무엇을 한다 (Goal 1줄)
2. 어떻게 검증할지 (test 또는 실측)

자기완결성·1레이어·구체주의는 사후 review가 잡음.

#### I2 — specialist 유도의 본질

에이전트 description을 30자 이내 트리거 1문장으로 압축. 라우팅 매트릭스 폐기.
description은 시스템 프롬프트에 항상 깔리므로 SKILL.md 본문보다 강함.

#### I3 — check-existing은 LSP·Grep으로

VSCode LSP 활용 + 코드 수정 직전 `Grep "def {함수명}"` 1회. 스킬 폐기.

#### I6 — AC 검증 위치 이동

AC 검증 → implementation 종료 (Phase 완료 직후).
회귀 marker → implementation에서 돌고 commit은 결과 확인만.
pre-check은 사실 게이트만.

#### TodoWrite 분해 위치

TodoWrite 단독 (WIP `## 작업 목록` 폐기). 분해 기준: "한 번에 검증 가능한
최소 단위" 1줄 원칙.

#### pytest 사용 패턴 audit

- AC가 명시 요구할 때만 실행 (실제로는 매번 돌림이 문제)
- marker 8개 중 사용 빈도 측정 후 진짜 가치 있는 3~4개만 남김
- pytest 실패 시 처리 룰 명확화

#### 가속 잔존 가치 (구간 2)

- TodoWrite로 단위 분해
- pytest marker (호출 시점·개수 정리 후)

### 1.3 버그 대처 — 에러·실패 → 진단·해결

v0.27.0(debug-guard) → v0.36(BIT) → v0.43(orchestrator) = 자가발화 강제 시도
누적. 본 사고의 결정적 시간선.

본 wave 실행 1단계 = researcher 호출. gstack 등 외부 사례 사전 조사 후
하네스의 어느 단계에 유기적으로 연결할지 결정.

조사 키워드: agentic debugging frameworks · LLM error recovery patterns ·
gstack · git-based debugging stacks.

#### 병목 분류

| # | 병목 | 분류 | 처리 |
|---|------|------|------|
| B1 | bug-interrupt.md 3Q 판단 블록 | 조사 후 결정 | researcher 결과 후 |
| B2 | debug-specialist 4단계 절차 | 조사 후 결정 | researcher 결과 후 |
| B3 | "1회 실패 즉시 에이전트" 트리거 | 조사 후 결정 | researcher 결과 후 |
| B4 | CPS P# 즉시 매칭 (Q3=YES) | 통제 | 폐기 |
| B5 | 동일 수정 2회 감지 git log 기반 | 조사 후 결정 | researcher 결과 후 |
| B6 | debug-guard.sh hook | 통제 | 폐기 확정 |

#### 확정 유지

- Gemini cli 통합 (사용자 평가 긍정)
- `git log` 선행 사례 패턴
- debug-specialist 부보조 위치

### 1.4 Task 종료·기록 — 완료 → 커밋

현 흐름은 commit SKILL.md 729줄 7-Step + pre_commit_check.py 1060줄.

#### 병목 분류

| # | 병목 | 분류 | 처리 |
|---|------|------|------|
| C1 | pre_commit_check 다축 검증 | 위치 오류 | AC·회귀를 implementation으로 이동 |
| C2 | Stage 5단계 + 5단 결정 룰 | 통제 | 폐기 |
| C3 | CPS 인용 박제 검사 | 통제 | 폐기 (CPS 영역에서 처리) |
| C4 | split 발동 | 통제 | 폐기 |
| C5 | review verdict 단어 추출 | 위치 재설계 | TDD 강화 기본 + review 옵트인 |
| C6 | wip-sync 매 commit | 시점 오류 | move 시점에 1파일만 |
| C7 | version_bump 자동 트리거 | 가속 자산 | 유지 (다운스트림 필수) |

#### C1 — 위치 정합화

- AC 검증 = implementation 단계
- 회귀 테스트 = implementation 단계
- review = commit 단계 (전체 시스템 관점)
- 사실 게이트 = commit 단계

pre-check은 사실 게이트 + review 트리거만. 300줄 목표.

#### C5 — TDD 강화 기본 + review 옵트인

- 기본: TDD (테스트 통과 = 사실, 결정적)
- 옵트인: 보안·아키텍처 결정처럼 테스트로 못 잡는 영역만 review

#### C6 — wip-sync 시점 이동

cluster 갱신 자체는 가속 가치 있음 (유지). 단 매 commit 전수 재계산 폐기 →
`docs_ops.py move` 시점에 그 1파일만.

#### 가속 잔존 가치 (구간 4)

- pre_commit_check.py 시크릿 line-confirmed · dead link · completed 봉인
- docs_ops.py move
- commit_finalize.sh (59줄)
- harness_version_bump.py
- HARNESS.json + CPS

## 2. 카테고리 분류

| 카테고리 | 정의 | 항목 |
|---------|------|------|
| **통제(폐기)** | LLM 자가 발화 의존 + 위치 오류 + 형식 강제 | T1·T5(검증.review)·T6·I1·I2·I3·I4·I5·I6(이동)·B4·B6·C1(이동)·C2·C3·C4·C5(verdict) |
| **가속(유지·강화)** | 결정적 검사·grep 체인·디렉토리 SSOT | WIP 폴더·abbr 명명·pytest marker(정리)·시크릿·dead link·docs_ops move·git log grep·doc-finder+frontmatter·SSOT 탐색·HARNESS.json+CPS·Gemini cli·version_bump |
| **재설계(폐기 아님)** | 자라야 하는 시스템 / 사용 인터페이스 부족 | T2(CPS)·T3·T4·B 그룹(researcher 조사 후) |

## 3. 영역별 실행 순서 (각 영역 안에선 폐기·신설·갱신 즉시 완료)

```
영역 1: CPS (§S-1)                     [완료 e998278]
영역 2: AC + staging (§S-2)             [완료 e998278]
영역 3: B 그룹 (§S-3)                   [완료 본 commit]
영역 4: 스킬 슬림화 (§S-4)              [완료 본 commit]
영역 5: rules 본문 처리 (§S-5)          [완료 본 commit, §S-7 박제 흡수]
영역 6: 스크립트 슬림화 (§S-6)          [완료 본 commit, §S-7 빌더 흡수]
영역 7: Wiki 그래프 모델 (§S-7)         [완료 본 commit, §S-5·§S-6 분산]
   ↓ 사용자 운용 1~3 세션 → wave completed
```

영역 미루기 금지. 영역 안 폐기·신설·갱신 동시 처리.

**§S-7 (Wiki 그래프 모델)**: 본 wave 안에서 발견된 본질. 독립 영역 아닌
§S-5·§S-6 안에 흡수해 동시 처리 (rules 박제 + 빌더 신설). 실제 자산 생성
(by-tag cluster 30개·problem 인용 보강 등)은 별 wave.

## S-1. CPS 영역 (자라는 시스템 + CPS 도메인 신설)

**defends**: P7 (구성 요소 관계 불투명), P9 (정보 오염 관성), P8 (자가 발화 의존)
**serves**: S9 (주관 격리 + 다층 검증 — 50자 박제 검사 폐기, 번호만)


### 본질 정의

CPS는 카탈로그가 아니라 **자라는 지각 시스템**.
- C(Context) — 글이 들어오면 무슨 맥락인지 빠르게 판단 (상식·패턴 영역)
- P(Problem) — 문제·방법을 찾음
- S(Solution) — 수정·구현

매칭이 본질 아님. 지식 누적 + 빠른 감각이 본질.

### 판단 비순차 + Cascade 순차

C·P·S는 그래프이지 화살표가 아님. 정합도 점수로 흔들림:
- P 발견 → 기존 C 재정의
- S 시도 → P 재정의
- S 성공 → 새 C 생성

길이 제약 없음. 짧을수록 좋지만 강제 X.

판단 확정 후는 단방향:
```
CPS 판단 (비순차) → 정합 substep → 확정 → implementation → test → /commit
```

### 박제 구조

- **kickoff** (`docs/guides/project_kickoff.md`) = C 판단 프롬프트
  - 자라지 않음, 5~10줄
  - 정련 옵트인 (연 1회 정도)
- **case 파일** (`docs/cps/cp_{slug}.md`) = wave마다 1건
  - WIP `cp_{slug}.md` 시작 → /commit 시 `docs/cps/` 이동
  - frontmatter에 C·P·S·tags·result·commit 박힘
  - 본문 자유 (없어도 됨)
- **git history** = 박제 SSOT, 자라남
- **별도 인덱스 신설 안 함** — cluster + grep이 인덱스 역할

### CPS 도메인 신설

| 도메인 | abbr | cluster |
|--------|------|---------|
| harness | hn | clusters/harness.md |
| meta | mt | clusters/meta.md |
| **cps** | **cp** | **clusters/cps.md** (자동) |

도메인 등급: cps는 meta급 (skip 검토).

case 파일 frontmatter:

```yaml
---
title: hook 무력화 wave
domain: cps
c: 도돌이표 commit 반복 — hook이 LLM 행동 강제 못함 박제
tags: [hook, orchestrator, recovery]
p: [P8]
s: [S8]
result: abandoned
commit: 2a5fcd0
wave: v0.46.2 baseline 회복
status: completed
created: 2026-05-13
---
```

### 정합 substep (implementation Step 2 박힘)

```
C·P 키워드 교집합 비율 결정적 측정
P·S 키워드 교집합 비율 결정적 측정
C·S 키워드 교집합 비율 결정적 측정
→ 임계 미달 시 1줄 알림 ("C·S 정합 약함")
→ 사용자/Claude 판단 (재정의·새 P#·무시)
→ 확정 후 implementation Step 3로
```

- 임계값 **과하게 시작** (0.3 정도) → wave 누적되며 좁혀나감
- 어긋남 신호 = 감지만. **자동 발굴 본 wave 안 박음**
- LLM 의미 보강 안 박음 — 결정적 grep만

### `/cps-check` 스킬 (옵트인)

- 사용자 명시 호출 시 정합 substep 단독 실행
- 의견 개진 형태로 결과 출력
- 호출 강제 없음
- 30~50줄

### `docs_ops.py cps` 명령

- `cps list` → P# 1줄 요약
- `cps add "1줄"` → 새 P# 자동 부여, kickoff에 append
- `cps cases [--p P3] [--tag hook] [--recent 30]` → cluster + frontmatter grep
- `cps show P3` → P# 정의 + 관련 case 최근 N건
- `cps stats` → P# 분포·정합도 평균·신규 P# 빈도

### CPS 영역 파일 변경 (즉시 완료)

**파일 자체 삭제 1개**:
- `.claude/HARNESS_MAP.md` (CPS cascade 표 — CPS와 운명 같음. git rm)

**부분 수정 4개**:
- `.claude/rules/docs.md` → "CPS 인용" 섹션만 삭제 (50자·(부분)·normalize 룰)
- `.claude/scripts/pre_commit_check.py` → CPS 인용 박제 substring 검사 함수만 삭제 (~150줄)
- `.claude/rules/naming.md` → 도메인 표에 `cps / cp / clusters/cps.md` 1줄 추가. 도메인 등급에 cps meta급
- `docs/guides/project_kickoff.md` → 본문 5~10줄 압축, C 판단 프롬프트 형태

**신설 3개**:
- `docs/cps/` 폴더
- `docs/clusters/cps.md` (자동 생성, docs_ops.py가 첫 case 들어올 때 생성)
- `.claude/skills/cps-check/SKILL.md` (30~50줄)

**implementation Step 2에 정합 substep만 박음** (전체 Step 재정렬은 §S-4 영역)

**기존 case 후보 마이그레이션**: **신규만 `docs/cps/`로**. 기존 decisions·incidents는 그대로 (점진 이주는 다음 wave 자연 흐름에서).

**`docs/cps/` 하위 폴더 안 만듦**: 평평하게 `docs/cps/cp_{slug}.md`. 날짜는 frontmatter `created`.

**kickoff 압축**: Claude 초안 → 사용자 수정.

### 기존 WIP frontmatter 마이그레이션

기존 WIP의 `solution-ref: - S2 — "50자 인용 (부분)"` → `s: [S2, S6]` 번호만.
`problem: P#` 그대로 유지. `pre_commit_check.py`의 형식 검사도 번호만 검사.

## S-2. AC 영역

**defends**: P2 (review 과잉 비용), P6 (검증망 스킵 패턴)
**serves**: S2 (패턴 → 행동 매핑 — staging.md 폐기, --review/--no-review 2단계), S6 (4중 방어 — AC 검증 위치 implementation 종료로 이동)

(영역 1 완료 후 진행. 본 wave 안에서 순서대로)

- AC `Goal:` 유지 강화 (1줄, 필수)
- AC `tests:` 유지
- AC `실측:` 유지
- AC `검증.review` 5단계 자가 선언 폐기
- AC 4필드 추출은 implementation 종료 단계로 위치 이동 (C1 정합화)
- staging.md (141줄) 폐기 — Stage 5단계 룰 전체
- review 호출은 `/commit --review`/`--no-review` 2단계

## S-3. B 그룹 (researcher + Gemini cli 이중 검증 완료)

**defends**: P1 (LLM 추측 수정 반복), P8 (자가 발화 의존 규칙의 일반 실패)
**serves**: S8 (강제 트리거 우선 + 자가 의존 보조)

조사 결과는 본문 `## 메모` §S-3 외부 사례 조사 섹션 참조.

확정 결정 (researcher + Gemini cli 이중 검증):
- bug-interrupt.md Q1/Q2/Q3 형식 **전체 폐기** (자가 발화 속성 자체가 문제)
- debug-specialist 절차 4단계 → **1~2단계 압축** (외부 사례 일관)
- 동일 수정 2회 감지 **git log 기반 유지** (hook 강제력 0 실측, git log는 결정적)
- "1회 실패 즉시 에이전트" 트리거 → **결정적 신호 시만 트리거** (test 실패·exit code)

확정 폐기 (조사 무관):
- bug-interrupt.md CPS P# 즉시 매칭 부분 (B4)
- debug-guard.sh 파일 (B6)

확정 유지 (조사 무관):
- Gemini cli 통합
- `git log` 선행 사례 패턴
- debug-specialist 부보조 위치

## S-4. 스킬 슬림화

**defends**: P5 (MCP·플러그인 컨텍스트 팽창), P8 (자가 발화 의존)
**serves**: S5 (압축 + 최소화)


- `implementation/SKILL.md`: 445줄 → 80줄
  - Step 0~0.9 소수 → 정수 1~6 재정렬
  - Step 1: CPS 판단 (C·P·S 비순차)
  - Step 2: CPS 정합 substep (§S-1에서 박힘)
  - Step 3: doc-finder 자동 흐름 + SSOT 4단계
  - Step 4: WIP 생성 (`{abbr}_{slug}.md`, 2원칙)
  - Step 5: 실행 + AC 검증 + TodoWrite
  - Step 6: 완료 + status 갱신 + cluster 추가
  - Phase 6원칙 폐기, specialist 라우팅 매트릭스 폐기
- `commit/SKILL.md`: 729줄 → 120줄
  - Step 4(version_bump) 유지
  - AC 자동 실행·split·verdict 추출 폐기
  - pre_commit_check + review 분기 + git commit + push
- `write-doc/SKILL.md`: 248줄 → 60줄
  - 6종 템플릿 폐기
- `eval/SKILL.md` (664줄) + `doc-health/SKILL.md` (213줄) → 통합 ~250줄
  - doc-health → `eval --harness` 흡수
  - eval 4관점 병렬 에이전트 폐기
  - 유지 모드: `--quick` + `--harness`

## S-5. rules 본문 전수 Read 후 처리

**defends**: P5 (컨텍스트 팽창), P7 (구성 요소 관계 불투명), P8 (자가 발화 의존)
**serves**: S5, S8
**§S-7 흡수**: docs.md "프론트매터" 섹션에 wiki 그래프 모델 박제 + naming.md tag normalize 정책 신설


각 rule 본문 100% Read → 폐기/축약 근거 명시 → 사용자 컨펌 → 실행.

| rule | 현 라인 | 처리 | 사유 |
|------|--------|------|------|
| anti-defer.md | 70 | 폐기 후보 | 미루기 자가 점검 의존 |
| bug-interrupt.md | 170 | 조사 후 결정 | §S-3 |
| coding.md | 28 | 유지 | Surgical Changes 행동 직접 |
| docs.md | 484 | 부분 삭감 | CPS 섹션(§S-1)·AC 섹션(§S-2)·staging 의존부 폐기. 폴더·파일명·차단 패턴 유지 |
| external-experts.md | 81 | 폐기 후보 | researcher 캐시 가치 < 갱신 비용 |
| hooks.md | 56 | 유지 | argument-constraint 차단 결정적 |
| internal-first.md | 38 | 30줄 축약 | 우선순위 5단계만 |
| memory.md | 133 | 40줄 축약 | session-* 3파일 정의만 |
| naming.md | 250 | 유지 | grep 체인 가속 핵심 |
| no-speculation.md | 93 | 30줄 축약 | 첫 행동 3원칙만 |
| pipeline-design.md | 116 | 폐기 후보 | 7항목 자가 점검 의존 |
| security.md | 49 | 유지 | 절대 금지 4항목 결정적 |
| self-verify.md | 141 | 40줄 축약 | AC + pytest marker 기본만 |
| staging.md | 141 | 폐기 (§S-2) | Stage 5단계 룰 전체 |

rules 총 1,839줄 → ~450줄 예상 (76% 삭감).

## S-6. 스크립트 슬림화

**defends**: P5 (컨텍스트 팽창), P6 (검증망 스킵 패턴), P7 (관계 불투명)
**serves**: S5, S6
**§S-7 흡수**: docs_ops.py cluster-update 폴백 버그 수정 + `cluster build-tags` 명령 신설 + cluster 폴더 `by-domain/`·`by-tag/` 마이그레이션


- `pre_commit_check.py`: 1060줄 → 300줄
  - 시크릿 line-confirmed · dead link · completed 봉인 · 빈 체크박스 · 거대 커밋 경고
  - CPS 인용 박제(§S-1) · AC 4필드 자동 실행(§S-2) · stage 결정 · split 판정 폐기
- `orchestrator.py` (696줄) 전면 삭제 — hook 무력화 이후 사용 0
- `docs_ops.py`: 849줄 → 500줄
  - move · reopen · wip-sync 핵심
  - 새 명령 `cps list/add/cases/show/stats` (§S-1)
- `commit_finalize.sh` (59줄) 유지
- `harness_version_bump.py` 유지 (C7)

scripts 총 ~2,664줄 → ~860줄 (68% 삭감).

## S-7. Wiki 그래프 모델 (cluster 재정의)

**defends**: P7 (구성 요소 관계 불투명), P9 (정보 오염 관성)
**serves**: S9 (주관 격리 + 다층 검증)

> 2026-05-14 본 wave 안에서 발견된 핵심 본질. 사용자 발화: "wiki처럼
> 이어지는 거네 — 원래 이걸 원했던 건데 이제야 찾아냈군."

### 본질 — cluster는 그래프 노드, tag는 간선

`docs/`는 단순 폴더 인덱스가 아니라 **그래프**. 본문은 흩어져 있어도
frontmatter 필드가 노드·간선 역할로 연결망을 형성. wiki와 같음.

> "그래프 모델"은 **개념 참고**일 뿐 새 도구·새 의존성 도입 아님.
> wiki·Roam·Obsidian이 동일 구조 위에 작동 — 이미 frontmatter에 다 있던
> 것을 그래프로 이름 붙인 것뿐.

| 구성요소 | 필드 | 역할 |
|---------|------|------|
| **노드 zone** | `domain` | 변경 전파 범위 (harness/meta/cps) |
| **노드 무게** | review 등급 (domain 부가 속성) | 검증 강도 (critical/normal/meta) |
| **간선 (edge)** | `tags` | cluster를 잇는 의미 연결망 — cross-domain |
| **명시적 link** | `relates-to` | 방향성 link (extends·supersedes 등) |

**핵심**: cluster를 잇는 게 tag. domain은 노드 속성. 간선이 없으면 그래프가
아니라 분리된 점들. 현 상태가 정확히 점들 — harness cluster 116개 평평한
리스트. tag가 활용되면 wiki로 작동.

### 폴더 분리 폐기 — 본문 분산 + 메타 인덱스만 추가

wiki는 본문이 흩어져도 작동. 폴더 분리는 과한 형식화. **현 폴더 구조
(decisions·guides·incidents·harness) 유지**하되, cluster 파일이 단일
메타 인덱스로 노드 멤버 + tag 간선을 동시 표현.

```
docs/clusters/                ← 현 구조 유지 (폴더 분리 X)
├── harness.md                ← domain 멤버 + tag 분포 + tag별 백링크
├── meta.md
└── cps.md
```

각 cluster 파일 구조 (`docs_ops.py cluster-update` 자동 생성):

```markdown
## 문서 (domain 멤버)

- decisions/hn_memory.md
- decisions/hn_doc_naming.md
- ...

## tag 분포 (간선)

- review (18건) | commit (13건) | downstream (13건) | ...

## tag별 문서 (백링크)

### review
- decisions/hn_review_staging.md
- decisions/hn_review_v080_benchmark.md
- ...

### commit
- ...
```

→ 사용자 VSCode에서 `#review` 검색 또는 `## review` anchor 클릭 시 점프.
LLM 자동화 0 — 자가 발화 의존 안 함.

### domain 4역할 분리

| 역할 | 현재 위치 | 본 wave 후 |
|------|----------|----------|
| 정합성 게이트 | pre_commit_check.py:197 | 유지 |
| cluster 인덱스 | docs_ops.py:435 | 유지 (단, tag 분포·백링크 섹션 추가) |
| 코드 경로 매핑 | docs_ops.py:60 | 유지 (review staging 신호) |
| review 전파 강도 | naming.md "도메인 등급" | 유지 |

### tag normalize — pre-check 결정적 차단

> "약한 강제"는 자가 발화 의존이라 본 wave의 P8 폐기 명제와 자기 모순.
> 결정적 게이트만 의미 있음.

**정규식**:
```
^[a-z0-9][a-z0-9-]*[a-z0-9]$
```

- 영문 소문자 + 숫자 + 하이픈만
- 시작·끝은 영숫자 (하이픈 시작·끝 금지)
- **한글 금지** (grep·anchor 호환성, 다운스트림 cascade, 변형 분산)

**pre-check 동작**:
- staged 문서 frontmatter `tags` 검사 → 위반 시 commit 차단
- 위반 tag명 + 권장 형식 제안 출력 (예: `Harness_Upgrade` → `harness-upgrade`)

**한글 사용 경로**:
- `title:`·본문은 한글 자유 (제약 0)
- `tags:`만 영문 강제 — 검색·자동화 표준 + 다운스트림 영어 프로젝트 정합

### meta cluster 재정의

- 빈 상태가 **정상** — sample·template zone, 멤버 적음이 의도
- docs_ops.py cluster-update 폴백 버그 수정 (frontmatter `domain: meta`
  인식 → cluster 자동 등록)
- 본문: "sample·template 카탈로그. 멤버 적음이 정상"

### cps 도메인 후속

case 누적 0건 — meta와 같은 패턴. 운용 5+ wave 후 재평가. 그때까지
빈 상태 정상 (sample zone과 동일 논리).

### 본 wave 흡수 작업

| 작업 | 위치 |
|------|------|
| docs.md "프론트매터" 섹션에 wiki 그래프 모델 박제 | §S-5 흡수 |
| naming.md에 tag 정규식 + 한글 금지 박제 | §S-5 흡수 |
| pre_commit_check.py에 tag 형식 차단 게이트 추가 | §S-6 흡수 |
| docs_ops.py cluster-update에 tag 분포·백링크 섹션 추가 | §S-6 흡수 |
| docs_ops.py cluster-update 폴백 버그 수정 (sample 자동 등록) | §S-6 흡수 |

### 별 wave 분리 (분량·검토 큼)

| 작업 | 사유 |
|------|------|
| problem 인용률 39% 보강 (118개 문서) | 분량 큼, 사람 검토 필요 |
| 기존 위반 tag 일제 normalize | pre-check 차단 후 점진 정비 자연 흐름 |
| relates-to 사용 빈도 측정 후 폐기 검토 | 운용 데이터 누적 후 |

## 단기 결과 예상

```
구성            현재      단기 후    삭감
─────────────────────────────────────────
skills/         5,124줄   ~1,100줄   78%
agents/         1,583줄   ~600줄     62%
rules/          1,839줄   ~450줄     76%
scripts/        2,664줄   ~860줄     68%
─────────────────────────────────────────
총              11,073    ~3,010     73%
```

사용자 체감:
- 발화 → 작업 시작까지 tool call 8~12회 → 2~3회
- pre-commit 검사 10~30초 → 2~5초
- WIP 생성 5분 → 1분 이내

## 4. 중기 (1~3개월, 가속 도구 강화)

- WIP 폴더 = 작업 메모장 (frontmatter 권장만, 필수 `problem: P#`)
- 탐색 가속: `_INDEX.md` 신설, doc-finder 명시 호출 시 강력
- 결정적 게이트: CI gitleaks 의무화, pytest marker 사용 빈도 측정 후 3~4개
- CPS 자라는 시스템 정착: 매 wave 새 P# 후보 1줄, 다음 wave 검토
- specialist description SSOT 정착: 9개 에이전트 30자 트리거 통일
- 사용자 검증 인프라: `git log --since` 결정적 명령, WIP "사용자 확인" 섹션
- 다운스트림 cascade 최소화: harness-upgrade opt-in 패치만

## 5. 장기 (3개월+, LLM 발전 흡수)

**전제**: 현 세대 LLM이 긴 룰셋 일관 적용 불가. 모델 발전이 한계를 풀면
일부 통제 도구는 다시 박을 수 있음. 단 지금 박는 룰은 휘발됨이 실측.

| 신호 | 행동 |
|------|------|
| Claude N+1에서 "긴 시스템 프롬프트 일관 준수" 실측 개선 | rules/ 일부 복원 검토 |
| Anthropic hook stdout → LLM 전달 보증 | PreToolUse 강제 게이트 재도입 검토 |
| "Claude 절차 통과 토큰" 메커니즘 등장 | BIT 자가 발화 룰 재설계 가능 |
| 다운스트림 누적 5개+ 동일 패턴 박제 요청 | 룰 재추가 후보 |

회수 경로: git history + `docs/archived/` 보존.

신뢰 회복: 짧은 페어 작업 사이클, 약속하지 않은 것 강제하지 않기, 결정적
게이트 사용자 직접 검증, 모델 한계 정직 표시.

## 6. 단·중·장 하나의 맥락

> 하네스를 Claude 통제 장치에서 사용자 가속 도구로 역전한다. 단기에 통제
> 항목 즉시 폐기 + 핵심 자산(CPS·doc-finder·SSOT 탐색·Gemini cli) 재설계,
> 중기에 가속 도구 사용자 관점 극대화, 장기에 LLM 발전이 통제 영역을
> 결정적 검증 가능 영역으로 바꿔주는 순간만 골라 흡수한다.

## 7. 사용자 합의 박제

| 결정 | 사용자 명시 | 본문 반영 |
|------|------------|-----------|
| 삭감 비율 | 73% (재설계 비용 반영) | §단기 결과 |
| CPS 본질 | 자라는 지각 시스템, 매칭 강제 = 본질 왜곡 | §S-1 |
| CPS 박제 위치 | /commit + git history. kickoff은 자라지 않음 | §S-1 |
| 매칭 로그 | 박제 안 함 (마지막 결정만) | §S-1 |
| 정합도 점수 | 임의 설정·과하게 시작 → 좁혀나감 | §S-1 |
| LLM 의미 보강 | 본 wave 안 박음, 운용 데이터 후 옵트인 | §S-1 |
| C 태그 | WIP frontmatter tags 상속 | §S-1 |
| 어긋남 신호 | 감지·1줄 알림만. 자동 발굴 다음 wave | §S-1 |
| cps_index 정합 | 체크 안 함, 깨지면 rebuild | §S-1 |
| reverse_impact | 폐기 (학습 필요 시 별도 처리) | §S-1 |
| 인덱싱 구조 | cluster + grep이 인덱스 역할 (별도 신설 안 함) | §S-1 |
| CPS 도메인 | abbr `cp`, naming.md/docs.md 갱신 | §S-1 |
| 영역 순서 | 영역 안 폐기·신설·갱신 즉시 완료. 영역 미루기 금지 | §3 |
| Step 명명 | 정수만 (소수점 금지) | §0 |
| rules 본문 전수 Read | 폐기·축약 전 의무 | §S-5 |
| eval·doc-health | 합치기 (doc-health → eval --harness 흡수) | §S-4 |
| wave 분할 | 끊김 없이, HIL 최소 | §0 |
| 본 문서 위치 | ADR (decisions/) | §0 |
| Wiki 그래프 모델 | 개념 참고만 (새 도구 도입 아님). domain=zone, tag=edge, review=속성, relates-to=link | §S-7 |
| cluster 폴더 분리 | 폐기 (현 구조 유지). cluster 파일에 tag 분포·백링크 섹션 추가 | §S-7 |
| tag 형식 | pre-check 결정적 차단 (^[a-z0-9][a-z0-9-]*[a-z0-9]$). 약한 강제 폐기 | §S-7 |
| tag 한글 | 폐기 (영문 소문자 + 하이픈 + 숫자만). title·본문은 한글 자유 | §S-7 |
| meta cluster | 빈 상태 정상 (sample zone, review 면제) | §S-7 |
| frontmatter cascade 보강 | problem [P2,P5,P6,P7,P8,P9] / s [S2,S5,S6,S8,S9] | frontmatter |

## 8. 실행 절차

**Step 1 — researcher + Gemini cli 이중 검증** [완료 2026-05-14]
- 키워드: agentic debugging frameworks, LLM error recovery, gstack
- 결과를 본 WIP `## 메모` §S-3 외부 사례 조사에 박음
- 사용자 컨펌 1회 완료

**Step 2 — §S-3 결정 + §S-7 본질 발견** [완료 2026-05-14]
- §S-3 4가지 결정 박제 (Q1/Q2/Q3 폐기·debug-specialist 압축·git log 유지·결정적 트리거)
- §S-7 신설 — wiki 그래프 모델 (domain=zone, tag=edge)
- frontmatter cascade 보강 (problem 1→6개, s 2→5개)

**Step 3 — rules 본문 전수 Read** (§S-5 처리 절차)
- 각 rule Read → 폐기/축약 근거 명시
- 사용자 컨펌 1회

**Step 4 — 영역별 실행** (§S-3 → §S-4 → §S-5 (§S-7 박제) → §S-6 (§S-7 빌더))
- 각 영역 폐기·신설·갱신 즉시 완료
- 영역 완료 시 사용자 1차 체감 → 다음 영역
- 영역 안 HIL 없음. 문제 발생 시 자체 재검증

**Step 5 — 운용 1~3 세션**
- 사용자 직접 사용
- 체감 OK 판정 시 본 wave completed

**Acceptance Criteria**:
- [ ] Goal: 하네스 73% 삭감 — 통제 항목 폐기 + CPS·AC·B 그룹·스킬·rules·스크립트 6영역 순서 처리, 사용자 운용 1~3 세션 체감 OK 판정으로 wave 통과.
  검증:
    tests: 없음
    실측: 운용 검증

## 메모

- 본 wave 채택 시 다음 wave 단일 작업: "통제 항목 폐기 + 가속 자산 강화 +
  CPS 재설계" — 분할 금지
- v0.41 baseline 회복 wave archived. 본 wave가 후속이자 73% 삭감 결정 박제
- 자동 검증 단언 금지 — 사용자 운용 판정만이 통과 게이트

### §S-3 외부 사례 조사 (2026-05-14, researcher + Gemini cli 이중 검증)

**공통 결론 — 업계 수렴점**: LLM 자가 발화 의존 → **결정적 트리거 + 고정 사다리**로
전환. "LLM이 진단·복구를 판단하되, 어떤 단계로 진행할지는 코드 경로가 강제한다"
는 책임 분리가 표준.

**1. agentic debugging frameworks**

- **Graph Harness** (arxiv 2604.11378, 2025-04): 실행·계획·회복 3레이어 분리.
  회복은 LLM이 진단하되 행동(retry → patch → replan)은 **고정된 에스컬레이션
  사다리**가 실행. 하위 단계 소진 전 상위 단계 진입을 코드 수준 차단.
- **OpenHands (OpenDevin)**: Event Stream Architecture. 에러를 typed
  `ErrorObservation` 객체로 박아 LLM이 "실패했냐"고 묻지 않고 tool exit code·
  stderr·linter JSON으로 결정. **Action Hashing** — 직전 N턴 액션 해시 비교,
  매치 시 "Loop Detected" 시스템 프롬프트 주입.

**2. LLM error recovery**

- **SelfHeal** (arxiv 2604.17699, 2025-04): fix-pattern 실측 분류. 동일 수정
  반복 = "stagnation" 신호로 별도 분류.
- **2025 실무 패턴 수렴점**: ① 에러 재시도가능/불가능 코드 분류 ② 재시도 소진
  시 자동 에스컬레이션 ③ 에스컬레이션 기준을 에이전트 코드 작성 전 정의.
- **Hierarchical Delegation**: 단일 에이전트 재시도 X. 결정적 실패 신호 시
  Router가 Debug Specialist/Reviewer role로 위임. **Verify-after-Act hook** —
  `npm test`·`ruff` 실패 시 세션 자동 branch/lock.
- **State-Diff 감지**: `git diff --exit-code` — exit 0(변경 없음) 시 "Empty
  Edit" 카운터 증가, 임계 시 강제 replan.

**3. gstack / git-based**

- **`gstack` (Garry Tan)** 실재 확인 — Claude Code workflow wrapper. role-based
  slash command(`/review`, `/qa`). Commit-as-Checkpoint 패턴 (매 tool 실행 또는
  agent turn을 hidden branch에 커밋, 실패 시 `git reset`으로 known good state
  복귀 — git tree를 물리적 undo stack으로).
- `git bisect run`: 스크립트 종료 코드(0/non-0)로 결정적 분류, 자가 발화 없이
  반복 감지.
- 출처: github.com/garrytan/gstack, git-scm.com/docs/git-bisect

**4. 본 §S-3 결정에 주는 시사점 (3가지)**

1. **자가 발화 → 시스템 인터셉터 전환** (업계 표준)
   - BIT Q1/Q2/Q3 자가 발화 블록 → hook이 non-zero exit code·empty diff 잡아
     debug-specialist role-switch 강제
   - **§S-3 결정 후보**: Q1/Q2/Q3 형식 **전체 폐기** (축약도 아님 — 자가 발화
     속성 자체가 문제)
2. **결정적 Loop Detection** (Action Hashing 패턴)
   - 동일 file-edit hash 2회 반복 → 메인 Claude가 자가 검토 강제
   - **§S-3 결정 후보**: 동일 수정 2회 감지를 **git log 기반 유지** (세션 내
     카운터는 hook 의존 — 본 하네스에서 hook 강제력 0 실측됨). git log는
     post-commit 시점이지만 결정적
3. **에스컬레이션 사다리 사전 정의**
   - debug-specialist 호출 조건을 사전 코드화 (WIP frontmatter 또는 pre-check
     레벨)
   - **§S-3 결정 후보**: debug-specialist 4단계 → **1~2단계 압축** (외부 사례
     일관). 4단계는 자가 발화 의존 흔적

### §S-3 결정 (사용자 컨펌 완료)

| 항목 | 현재 | 결정 | defends | 근거 |
|------|------|------|---------|------|
| Q1/Q2/Q3 형식 | bug-interrupt.md 170줄 | **전체 폐기** | P8 | 자가 발화 속성 자체가 문제 (OpenHands·Graph Harness 공통) |
| debug-specialist 절차 | 4단계 | **1~2단계 압축** | P8 | 외부 사례 일관 |
| 동일 수정 2회 감지 | git log 기반 (session-start.sh) | **git log 유지** | P1, P8 | hook 강제력 0 실측, git log는 결정적 |
| "1회 실패 즉시 에이전트" | 트리거 | **결정적 신호 시만 트리거** (test 실패·exit code) | P8 | Verify-after-Act hook 패턴 |

확정 폐기 (조사 무관): B4 CPS P# 즉시 매칭, B6 debug-guard.sh
확정 유지 (조사 무관): Gemini cli 통합, git log 선행 사례, debug-specialist 부보조 위치

### §S-7 신설 — Wiki 그래프 모델 (cluster 재정의)

**본 wave 안에서 발견된 핵심 본질** (2026-05-14 사용자 발화: "wiki처럼
이어지는 거네 — 원래 이걸 원했던 건데 이제야 찾아냈군"):

`docs/clusters/`는 단순 폴더 인덱스가 아니라 **그래프 노드**. frontmatter
필드는 그래프 구성요소:

| 구성요소 | 필드 | 역할 |
|---------|------|------|
| **노드 zone** | `domain` | 변경 전파 범위 (harness/meta/cps 3개) |
| **노드 무게** | review 등급 (domain에 박힌 속성) | 검증 강도 (critical/normal/meta) |
| **간선 (edge)** | `tags` | cluster를 잇는 의미 연결망 — cross-domain |
| **명시적 link** | `relates-to` | 방향성 link (extends·supersedes 등) |

**핵심 깨달음**: cluster를 잇는 게 tag. domain은 노드 속성일 뿐. 간선이 없으면
그래프가 아니라 분리된 점들. 현 상태가 정확히 그것 — harness cluster 116개
평평한 점. tag가 활용되면 wiki로 작동.

#### domain 4역할 분리 (현재 다중 의미 필드 → 단일 의미)

| 역할 | 현재 위치 | 본 wave 후 |
|------|----------|----------|
| 정합성 게이트 | pre_commit_check.py:197 | 유지 |
| cluster 인덱스 | docs_ops.py:435 | **tag cluster로 이관** (간선 본질) |
| 코드 경로 매핑 | docs_ops.py:60 path_to_domain | 유지 (review staging 신호) |
| review 전파 강도 | naming.md "도메인 등급" | 유지 |

#### 새 cluster 폴더 구조

```
docs/clusters/
├── by-domain/                       ← 노드 zone (3개, 범위)
│   ├── harness.md  (변경 전파 — 다운스트림)
│   ├── meta.md     (sample·template — 전파 안 됨, review 면제)
│   └── cps.md      (wave case 박제)
└── by-tag/                          ← 간선 (자동, 빈도 5+)
    ├── review.md (18건 자동 집계)
    ├── commit.md (13건)
    ├── downstream.md (13건)
    ├── cps.md (12건 — by-domain/cps와 별개, tag 기반)
    ├── hook.md (8건)
    └── ... (자동 승격)
```

#### tag normalize 정책 (약한 강제)

- **소문자 + 하이픈** 형태만 (`harness-upgrade` 통일, `harness_upgrade`·`HarnessUpgrade` 금지)
- 사전 등록 없음 — 자유 추가 OK
- 빈도 5+ tag만 by-tag cluster 자동 승격 (노이즈 자연 필터링)

#### meta cluster 재정의

- 빈 상태가 **정상** — sample·template zone, 멤버 적음이 의도
- docs_ops.py cluster-update 폴백 버그 수정 (frontmatter `domain: meta`
  인식 → cluster 자동 등록)
- 본문: "sample·template 카탈로그. 멤버 적음이 정상"

#### §S-7 본 wave 흡수 작업 (빌더만 신설, 자산 생성은 별 wave)

| 작업 | 위치 |
|------|------|
| docs.md "프론트매터" 섹션에 그래프 모델 박제 | §S-5 흡수 |
| naming.md에 tag normalize 정책 신설 | §S-5 흡수 |
| docs_ops.py cluster-update 폴백 버그 수정 (sample 자동 등록) | §S-6 흡수 |
| `docs_ops.py cluster build-tags` 명령 신설 | §S-6 흡수 |
| cluster 폴더 `by-domain/`·`by-tag/` 구조 마이그레이션 | §S-6 흡수 |
| problem 인용률 39% 보강 (118개 문서) | **별 wave** |
| by-tag cluster 30개 초기 생성·검토 | **별 wave** (사람 검토 필요) |
| relates-to 사용 빈도 측정 후 폐기 검토 | **별 wave** |

#### CPS 도메인 후속

cps 도메인 case 누적 0건 — meta와 같은 패턴 의심. 운용 5+ wave 후
재평가. **그때까지 빈 상태 정상** (sample zone과 동일 논리).

## 변경 이력

- 2026-05-14 생성: 통제 항목 폐기 안 1차 초안 (80% 삭감)
- 2026-05-14 사용자 검토 1차 반영:
  - T2 CPS 폐기 → 재설계 (자라는 시스템)
  - T3 doc-finder → 유지 (긍정 자산)
  - T4 SSOT 탐색 → 유지 (가장 긍정적 자산)
  - T5 AC → 본질 유지, `검증.review` 5단계만 폐기
  - T6 라우팅 태그 → 폐기 확정
  - B 그룹 → researcher 조사 후
  - C1 다축 검증 → 위치 이동
  - C5 review → TDD 강화 + 옵트인
  - C6 wip-sync → 시점 이동
  - C7 version_bump → 유지 확정
  - eval·doc-health → 합치기
  - Step 정수 재정렬
  - ADR 위치 확정
  - 삭감 80% → 73%
- 2026-05-14 CPS 재설계 합의 박제:
  - CPS 본질 (자라는 지각 시스템, 매칭 강제 = 본질 왜곡)
  - 판단 비순차 + Cascade 순차
  - kickoff 자라지 않음 + case 파일 + git history SSOT
  - CPS 도메인 신설 (abbr `cp`)
  - 정합 substep (결정적 + 과한 임계 시작)
  - 어긋남 감지·1줄 알림만 (자동 발굴 다음 wave)
  - LLM 의미 보강 옵트인
  - C 태그 = WIP frontmatter tags 상속
  - `/cps-check` 옵트인 스킬
  - cluster + grep이 인덱스 역할 (별도 인덱스 신설 안 함)
  - reverse_impact·매칭 로그 폐기
- 2026-05-14 영역별 책임 분리 + 주석 반영 정리:
  - 본 wave 영역 6개로 순서 분리 (CPS → AC → B → 스킬 → rules → 스크립트)
  - 각 영역 안 폐기·신설·갱신 즉시 완료, 다른 영역 미루기 금지
  - CPS 영역 파일 변경 명시: 삭제 1 / 부분 수정 4 / 신설 3
  - Step 명명 정수만 원칙 박제
  - 사용자 합의 18건 §7 표로 통합 박제
  - 사용자 주석 본문 반영 후 제거
- 2026-05-14 §S-3 결정 + §S-7 신설:
  - researcher + Gemini cli 이중 검증으로 §S-3 4결정 박제
    (Q1/Q2/Q3 폐기·debug-specialist 압축·git log 유지·결정적 트리거)
  - frontmatter cascade 보강 (problem 1→6개, s 2→5개)
  - 각 §S-1·§S-2·§S-3·§S-4·§S-5·§S-6에 defends/serves 헤더 추가
- 2026-05-15 §S-3·§S-4·§S-5·§S-6·§S-7 일괄 박제 commit:
  - §S-3: bug-interrupt.md 폐기, debug-specialist 4→1~2단계 압축, git log
    유지, 결정적 신호 트리거
  - §S-4: implementation·commit·write-doc·eval 슬림화, doc-health·
    check-existing 스킬 폐기, eval --surface·--deep·4관점 병렬 폐기,
    harness-upgrade Step 9.3 폐기, 잔존 참조 정리 (review·researcher·
    advisor·codebase-analyst)
  - §S-5: anti-defer·bug-interrupt·external-experts·pipeline-design 폐기,
    internal-first·memory·no-speculation·self-verify 축약, docs.md 부분 삭감
    (구성요소 메타데이터 trigger·Layer·enforced-by 폐기), §S-7 박제 흡수
    (docs.md wiki 그래프 모델·naming.md tag 정책)
  - §S-6: orchestrator.py 전면 삭제 (696줄), debug-guard.sh 폐기,
    pre_commit_check.py tag 정규식 게이트 + split 발동 폐기,
    docs_ops.py cluster-update tag 백링크 (2건+ 임계) + meta 폴백 수정,
    eval_cps_integrity.py HARNESS_MAP 점검 + BIT NEW 폐기 + 사전 회귀 해소,
    session-start·stop-guard BIT 출력 폐기, test_pre_commit tag marker 18
    케이스 신설
  - §S-7: wiki 그래프 모델 본질 정착. domain=zone, tag=edge. cluster
    본문에 tag 분포·백링크 (2건+ 임계). meta cluster sample 자동 등록.
    cps case 박제 첫 등록 (본 wave 자체)
- 2026-05-14 Wiki 그래프 모델 본질 발견 (§S-7 신설):
  - meta cluster·domain 방치 진단 → 도메인 4역할 분화 + tag = cross-domain
    edge 본질 추출
  - 사용자 발화 "wiki처럼 이어지는 거" = 그래프 모델 합의
  - 사용자 피드백 3건 반영:
    - A1: 그래프 모델은 개념 참고만 (새 도구 도입 아님)
    - A2: 폴더 분리(by-domain/·by-tag/) 폐기, 본문 분산 + cluster 메타 인덱스
      에 tag 분포·백링크 섹션 추가
    - A3: 약한 강제 폐기 → pre-check 결정적 차단 (영문 소문자 + 하이픈 +
      숫자, 한글 금지). title·본문은 한글 자유
