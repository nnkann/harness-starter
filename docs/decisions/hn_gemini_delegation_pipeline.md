---
title: Gemini CLI subagent 위임 파이프라인 설계
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회"
tags: [gemini, delegation, subagent, pipeline, brainstorm]
relates-to:
  - path: decisions/hn_bit_cascade_objectification.md
    rel: caused-by
  - path: decisions/hn_cps_entry_signal_layering.md
    rel: caused-by
status: completed
created: 2026-05-11
updated: 2026-05-11
---

# Gemini CLI subagent 위임 파이프라인 설계

## 배경

harness-starter 4개 subagent (researcher / review / risk-analyst / threat-analyst)가
Sonnet 기반이라 "다른 모델의 시각"이 부재. Claude 자가 흐름은 echo chamber —
같은 모델이 만든 결정을 같은 모델이 비판하면 같은 blind spot 공유.
//gemini cli가 설치되지 않은 상태에선 자동으로 기본 상태가 작동하도록 설계. cli가 있는지 확인하고 셋업. 다운스트림에도 적용하는 것이 좋을 것 같음.
검증된 환경:
- `gemini-cli 0.41.2` 이미 설치, OAuth 인증 완료 (`~/.gemini/oauth_creds.json`)
- API 키 미사용 → **추가 비용 0** (OAuth quota만 소모)
- 실측: rule 파일 비평 위임에서 의미 있는 7개 영역 약점 지적 반환
- 다운스트림 영향 0 절대 조건 — user-scope 격리 필수

도입 의도:
- "딴지 거는 외부 시각"을 harness 흐름에 자동 통합
- 사용자가 명시 호출을 잊어도 의미 있는 순간에 자동 개입
- 단, `debug-guard.sh`처럼 키워드만 보고 의미 무관 발화하는 "바보 에이전트"
  패턴은 절대 회피

## 핵심 원칙 — 외형 metric 금지

debug-guard.sh가 거슬리는 본질: "버그"라는 단어가 떠도 Q1/Q2/Q3 적용
대상인지는 의미를 봐야 알 수 있는데, 단어만 보고 발화. 사용자가 이미
의미 판단 끝낸 발화에도 똑같이 떠서 잡음. //이참에 클로드가 가치 판단을 하는 형태로 (표시 없음)로 변경하는 것도 고려해 볼만함. 

Gemini 위임 트리거가 같은 함정에 빠지면 안 됨:

| 금지 (외형 metric) | 권장 (의미 신호) |
|------------------|---------------|
| 발화 길이 (`> 30자`) | CPS Problem 매칭 결과 (`NEW` 플래그) |
| 키워드 grep (`"리팩토" 포함`) | AC frontmatter `검증.review` 선언 |
| 파일 수·줄 수 | `recommended_stage`·`solution-ref` `(부분)` 마커 |
| 매 발화마다 발산 | Claude 자가 흐름의 객관 사건만 |

harness는 이미 **CPS·AC라는 의미 기반 인프라**를 가짐. 그 위에 외형
분류 hook을 얹으면 `staging.md`가 폐기한 패턴 재현 + P8 (자가 발화
의존 규칙의 일반 실패) 자기증명.
//cps에도 이 내용에 대한 보강이 있는게 좋을 것 같은데?
## 선택지

### 후보 1 — 단일 통합 (pre-commit only)
//기능상 동작은 여기가 맞는 거라고 판단이 드나, 단점에 언급한 대로 시점이 뒤라서 걱정됨. 그리고 초기 빠른 결정과 판단에는 도움이 못 될 것으로 생각하니 아쉬움.
```
모든 4개 트리거 → pre_commit_check.py가 의미 신호 추출
                ↓ trigger hit
                gemini_devil 호출 (background &)
                ↓
                결과를 .claude/memory/gemini-devil-{trigger}.md 저장
                ↓ pre-check 출력에 "Gemini 의견: <path>" 한 줄 추가
                ↓
commit 스킬이 review와 병렬로 Gemini 결과 첨부
사용자가 차단/주의/참고 판단
```

장점:
- hook point 1개, 의미 신호 인프라(pre_commit_check.py) 재사용
- 실패 격리 쉬움 (commit 시점이라 작업 도중 중단 없음)
- 4개 트리거 사건 모두 commit 직전에 신호 확보 가능

단점:
- 시점이 commit 직전 — **발산 가치 큰 정의 단계(작업 시작 직후) 놓침**
- 발산 결과 반영 시 commit 차단 비용 (이미 작성한 WIP·코드 되돌림)

### 후보 2 — 2단계 분리 (발산 + 적용)

```
[발산 단계 — WIP 작성 직후]
implementation 스킬 안에서 명시 호출 (hook 아님, 스킬 내부 분기)
  ↓ 트리거 신호 hit (NEW 플래그, Solution 변경, BIT Q3)
  gemini-devil 호출 → 결과를 WIP에 "## 외부 시각" 섹션으로 추가
  사용자 검토 후 작업 진행
//이렇게 되면 write-doc 스킬 이후 발화해서 검증하는 단계가 될텐데 이것도 나쁘진 않음. 다만 일상적 프롬프트에선 발화가 안 되지 않을까? 이게 단점이 될듯함.(보완 필요)
[적용 단계 — commit 직전]
pre_commit_check.py + commit 스킬
  ↓ 트리거 신호 hit (review warn + deep, Solution 변경)
  gemini-devil 호출 → 결과를 review와 병렬 첨부
```

장점:
- 발산·적용 가치 모두 살림
- 발산 결과가 WIP에 영속 (사후 추적 가능)
- 작업 시작 직후 정의 발산 → 코드 작성 전 의견 반영 쉬움

단점:
- 진입점 2개 (implementation·commit) — 일관성 관리 부담 //이건 정말 안하고 싶음.
- WIP 본문 오염 가능성 ("## 외부 시각" 섹션 누적)

## 6개 설계 질문 (미결)

진도 나가기 전 합의 필요.

### Q1. 발화 주체

| 옵션 | 함의 |
|------|------|
| A) 자동 hook (Claude Code hook system) | "잊지 않음" 보장. 단 의미 판단을 hook 코드가 해야 함 |
| B) Claude 자가 호출 (룰 기반) | 의미 판단 정확. 단 Claude가 룰 무시·망각 가능 (debug-guard 문제 재현) |
| C) 사용자 명시 (`/ask-gemini`) | 가장 가벼움. 단 자동화 가치 0 |

핵심 트레이드오프: **의미 판단 정확도 ↔ 망각 보장**

### Q2. 트리거 위치 (hook event)

Claude Code hook 종류:
- `UserPromptSubmit` — debug-guard 패턴
- `PreToolUse` / `PostToolUse` — 도구 호출 전후
- `SubagentStop` — subagent 응답 직후
- `Stop` — Claude 응답 종료 직전
- `pre-commit` (git hook) — pre_commit_check.py 트리거

4개 트리거 사건 매핑:

| 트리거 사건 | 적합한 hook event |
|------------|-----------------|
| CPS Problem NEW 플래그 | PostToolUse (WIP 작성 직후) 또는 pre-commit |
| CPS Solution 메커니즘 변경 staged | pre-commit |
| BIT Q3 + NEW | PostToolUse (WIP 갱신 직후) |
| review verdict warn + deep | SubagentStop (review 종료 직후) |

문제:
- PostToolUse·SubagentStop은 어떤 도구·어떤 agent였는지 식별 부담
- pre-commit 통합은 시점 늦음

### Q3. 시점 — 발산 가치 vs 적용 가치

| 시점 | 발산 가치 | 적용 가치 | 비고 |
|------|---------|---------|------|
| 작업 시작 (Step 0) | ★★★★★ | ★★★ | 의미 신호 약함 (AC 미작성) |
| WIP 작성 직후 | ★★★★ | ★★★★ | PostToolUse 식별 부담 |
| 구현 도중 | ★★ | ★★ | 트리거 신호 약함 |
| commit 직전 (pre-commit) | ★★ | ★★★★★ | 모든 신호 확보, 반영 비용 큼 |
| review 직후 | ★★★ | ★★★★ | SubagentStop 식별 부담 |

### Q4. 컨텍스트 — Gemini에게 무엇을 넘기는가

| 트리거 사건 | 필요 컨텍스트 |
|------------|--------------|
| CPS NEW 플래그 | 사용자 발화 + 기존 CPS Problems 전체 + WIP 초안 |
| Solution 변경 | CPS Solution 본문 + staged diff + 관련 incidents/ |
| BIT Q3 + NEW | BIT 판단 블록 + 발견 컨텍스트 + 기존 P# 목록 |
| review warn + deep | WIP AC + staged diff + review verdict 본문 |

기술 제약: Gemini CLI 1M 컨텍스트 한도는 크지만 argv/stdin shell 제한
있음. 큰 컨텍스트는 임시 파일 경유 (`gemini -p "$(cat /tmp/ctx.md)"`) 필요.

### Q5. 응답 처리

| 옵션 | 함의 |
|------|------|
| A) stdout → Claude 컨텍스트 자동 주입 | 즉시 효과, 매번 토큰 소모 |
| B) 파일 저장 → Claude lazy Read | Claude가 Read 호출 안 하면 무용 |
| C) WIP 본문 "## 외부 시각" 섹션 | 영속·검토 가능, WIP 오염 |
| D) 사용자 stderr 알림 | 사용자 개입 가능, 발화 마찰 |
| E) commit log 본문 첨부 | 사후 audit, 작업 도중 무용 |

조합 가능: 발산 단계 A+C, 적용 단계 D+E.

### Q6. 실패 처리 (timeout·quota·무용 응답)

| 옵션 | 함의 |
|------|------|
| A) 조용히 skip (exit 0) | 자동화 보조 역할, 실패가 진행 막지 않음 |
| B) stderr 경고 후 진행 | 사용자 인지 가능 |
| C) Claude에게 "Gemini 실패" 신호 주입 | 자체 판단 유도 |
| D) 사용자 알림 + 재시도 | 마찰 큼 |

OAuth quota:
- Gemini 2.5 Pro 무료 tier 일 한도 미실측 (~1000회/일 추정)
- 4개 트리거 × 세션 1~2회 × 일 5~10 세션 = 일 20~80회 → 한도 내
- 단 트리거 정밀하지 않으면 빠르게 소모

## 4개 트리거 사건 (확정 후보)

위 모든 설계 위에서 발화될 사건. 사용자 발화 직후가 **아님** — Claude
자가 흐름 안의 객관 사건만.

| 사건 | 의미 신호 | 발산 가치 |
|------|----------|---------|
| **CPS Problem NEW 플래그** | implementation Step 0가 P# 매칭 못 함 | ★★★★★ |
| **CPS Solution 메커니즘 변경 staged** | Solution 본문 자체 변경 (cascade 영향) | ★★★★★ |
| **BIT Q3 hit + NEW 플래그** | 스코프 외 이슈가 새 영역 | ★★★★ |
| **review verdict warn + stage deep** | 회색지대 + 회귀 위험 영역 동시 hit | ★★★★ |

빈도 추정: 세션당 0~2회. debug-guard처럼 "매번 거슬림" 아님 — 사건 알림 수준.

## 트리거 안 됨 (의도적 제외)

- 사용자 발화 직후 (사용자가 1차 필터)
- 단순 작업 (`검증.review: skip|self`)
- 기존 P# 명확 매칭
- AC frontmatter 누락 (pre-check이 이미 차단 — Gemini 역할 없음)

## 결정 — Phase 분리 채택 (BIT cascade·orchestrator MVI 후속)

본 wave 진행 중 BIT cascade + cps_entry_signal_layering + orchestrator MVI
시리즈가 메타 cascade 완성. Gemini 1차 외부 시각의 닭-계란 재구성 권고
정합 — Phase 분리로 평행 진행.

### Phase 구조

```
Phase 1 — 객관 신호 트리거 (즉시 가능, 본 wave에서 1단 구현)
  - Solution 변경 staged (diff grep)
  - (보류) review verdict warn + deep — PostToolUse hook 별 wave 필요

Phase 2 — BIT/CPS cascade 객관화 (완료 — orchestrator MVI)
  - PreToolUse hook + orchestrator.py
  - P1·P9 detect + Exit 2 강제 중단

Phase 3 — 의미 신호 트리거 (Phase 2 위에서 가능)
  - CPS Problem NEW 플래그 (orchestrator P9 detect 부분 충족)
  - BIT Q3 + NEW (별 후속 wave)
```

### Q1~Q6 결론 (본 wave 합의)

- **Q1 발화 주체**: 자동 hook (orchestrator.py가 진입점). 사용자·Claude
  자가 호출 모두 불필요
- **Q2 트리거 위치**: PreToolUse (Phase 1·2). PostToolUse·SubagentStop은
  Phase 3 후보
- **Q3 시점**: 도구 호출 직전 (PreToolUse). 빠른 객관 detect
- **Q4 컨텍스트**: orchestrator가 staged diff + frontmatter 직접 Read.
  Gemini에게 임시 파일 경유로 전달 (CLI argv 제한 회피)
- **Q5 응답 처리**: stdout `additionalContext` 주입 + session_signal.json
  파일 쓰기 (이중 안전장치, orchestrator MVI 패턴 답습)
- **Q6 실패 처리**: 조용히 skip (exit 0). Gemini CLI 없거나 timeout 시
  무영향 — 다운스트림 격리 (graceful degradation)

### Phase 1 본 wave 구현 범위

orchestrator.py에 P10 추가 (또는 별 detect 함수):
- **Solution 변경 staged 신호** — `git diff --cached docs/guides/project_kickoff.md`
  의 `## Solutions` 섹션 변경 detect
- hit 시 Gemini 의견 background 호출 → 결과 `.claude/memory/gemini-solution-review.md`
- stdout INFO 신호로 사용자 알림 (Critical 아님 — 권고)

review verdict warn + deep 트리거는 PostToolUse hook 추가가 필요해
별 wave 후보.

## 사각지대

- Gemini CLI 비결정성 (temperature·seed 미실측) — A/B 비교 노이즈 가능
- Gemini의 starter 컨텍스트 접근 (CLI 모드 파일 Read 권한 격리 정도)
- OAuth quota 실측 부재 — 일 한도 정확한 값 미확인
- gemini CLI 미설치 환경 — graceful skip 필수 (다운스트림 cascade 영향 0 보장)
- Solution 변경 detect의 false-positive — Solutions 섹션 외 변경도 grep hit 가능. 정밀화 필요

## 작업

### 1. Phase 분리 결정 박제 + Phase 1 Gemini Solution review 구현

**Acceptance Criteria**:
- [x] Goal: orchestrator.py가 Solution 변경 staged 시 Gemini 호출 트리거 → 결과를 사용자에게 알림 ✅
  검증:
    review: review
    tests: pytest -m orchestrator
    실측: 본 commit 자체가 실측 (Solution 미변경이라 트리거 없어야)
- [x] orchestrator.py에 `detect_solution_change` 함수 추가 — staged diff grep ✅
- [x] gemini CLI 존재 확인 + 미설치 시 skip (graceful) ✅
- [x] Gemini 호출은 background (non-blocking) — orchestrator hook 자체는 지연 없이 반환 ✅
- [x] 결과는 `.claude/memory/gemini-solution-review.md` 저장 + session_signal.json INFO 신호 ✅
- [x] 회귀 가드 — Solution 변경 시뮬 시 detect 작동·미변경 시 skip (10/10 통과) ✅
- [x] 본 WIP completed 전환 + Phase 분리 결정 박제 ✅

## 관련 결정

- `decisions/hn_bit_cascade_objectification.md` (caused-by) — BIT cascade
  객관화 + P9 신설. 본 결정 Phase 2 충족
- `decisions/hn_cps_entry_signal_layering.md` (caused-by) — 3층 책임 분리
  메타 원칙
- `decisions/hn_orchestrator_mechanism.md` (extends) — orchestrator MVI.
  본 결정 Phase 1은 orchestrator 확장

## 메모

본 wave Phase 1만. Phase 3 (BIT Q3 자동 트리거)·PostToolUse hook 기반
review verdict 트리거는 별 wave 후보. `-gem` agent 4개 신설 (user-scope)
는 별 트랙 — 본 자동 트리거와 중복 가능성 있어 본 wave 후 가치 재평가.
