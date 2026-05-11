---
title: 오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI
domain: harness
problem: P9
solution-ref:
  - S9 — "주관 격리 + 다층 검증"
tags: [orchestrator, cascade, execution, hook, p9, mvi, pre-tool-use]
relates-to:
  - path: decisions/hn_cps_entry_signal_layering.md
    rel: caused-by
  - path: decisions/hn_bit_cascade_objectification.md
    rel: caused-by
  - path: decisions/hn_p8_starter_self_application.md
    rel: extends
status: completed
created: 2026-05-11
updated: 2026-05-11
---

# 오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI

## 배경

### 사용자 발견 (2026-05-11)

`cps_entry_signal_layering` + `bit_cascade_objectification` + P9·S9 신설
직후 사용자가 짚음:

> "지금보면 아주 따로 놀고 있는데"
> "오케스트라를 지금 누가 맡고 있지?"

선언상 implementation 스킬이 오케스트라이지만 자가 발화 의존 → P8 영역.
모든 정의(Layer 1 진입 조건·BIT Q1/Q2/Q3·HARNESS_MAP CPS 테이블)가
정적, 매 작업마다 자동 매칭·도구 발화 cascade 부재. **진짜 지휘자는 사용자**.

### 두 외부 시각 위임 결론

**Gemini 메타 위임 1차**: "설계도를 찢고 스크립트를 짜라. orchestrator.py가
실제 파일로 존재하고 pre_tool_use에 걸리는 순간에만 본 결정은 의미."

**researcher 자료 조사**: Anthropic 공식 orchestrator-workers 패턴,
Praetorian 8계층 결정론적 오케스트레이션, MemGPT/Letta sleep-time compute,
arXiv:2503.13657 "Ignored other agent's input" 실패 모드, Claude Code
hooks reference + Issue #13912 (UserPromptSubmit stdout 불안정).

**Gemini 메타 위임 2차** (구체 코드 방향): PreToolUse hook + orchestrator.py
단 하나로 시작. P1·P9 두 개만 결정론적 판정. 약 250줄. Exit 2 강제 중단
허용 — "어설픈 잔소리는 Claude가 무시함" (적극 추천).

## 결정 (합의 완료)

### 핵심 원칙 — Deterministic Signal Injection

> LLM은 비결정론적 커널, 런타임은 결정론적
> (Praetorian: "the LLM as a nondeterministic kernel process wrapped
> in a deterministic runtime environment")

오케스트레이터는 **물리적 코드**로 존재. hook이 커널 권한으로 LLM
이전에 작동. LLM 의지 무관 강제.

### MVI 단위

1. **`scripts/orchestrator.py`** (~150~200줄) — 신호 detect 엔진
2. **`.claude/session_signal.json`** — 단기 인지 메모리
3. **PreToolUse hook 등록** (`.claude/settings.json`) — 강제 진입점

### 진입점 결정 — PreToolUse

| 후보 | 의미 | 채택 여부 |
|------|------|---------|
| SessionStart | 세션 시작 1회 | ❌ — 진행 중 신호 못 잡음 |
| UserPromptSubmit | 발화 직후 | ❌ — Issue #13912 stdout 불안정 |
| **PreToolUse** | 도구 호출 직전 | ✅ — "생각 마쳤을 때" 커널 개입 |
| PostToolUse | 도구 결과 후 | ❌ — 이미 늦음 |
| Stop | 응답 종료 | ❌ — 사후 |

PreToolUse가 유일하게 **실시간 통제 수단**.

### 최소 P 범위 — P1·P9 두 개

| P | 결정론적 판정 가능? | 채택 |
|---|------------------|------|
| P1 (LLM 추측 수정) | ✅ — `consecutive_errors` 카운터·파일 수정 횟수 grep | YES |
| P2 (review 과잉) | ⚠️ — review tool call 추적 필요 (인프라 추가) | 후속 |
| P3 (다운스트림 사일런트) | ⚠️ — 다운스트림 환경 의존 | 후속 |
| P4 (hook fragility) | ⚠️ — settings.json grep | 후속 |
| P5 (컨텍스트 팽창) | ❌ — 토큰 측정 인프라 부재 | 후속 |
| P6 (검증망 스킵) | ⚠️ — pre-check 통합 | 후속 |
| P7 (관계 불투명) | ⚠️ — eval_cps_integrity 통합 | 후속 |
| P8 (자가 발화) | ⚠️ — rules 본문 grep | 후속 |
| **P9 (정보 오염)** | ✅ — WIP frontmatter ↔ 작업 파일 매칭 | YES |

P1·P9는 파일 시스템·상태 파일만으로 결정론적 판정 가능. P2~P8은 맥락 의존
오탐 위험 → 후속 wave.

### Exit 2 강제 중단 — 채택

> **"P9 위반 시 Exit 2 (강제 중단) 허용한다."**

근거:
- Gemini 메타 권고: "어설픈 잔소리는 Claude가 무시함"
- Praetorian 8계층 모델: "모든 도메인 PASS될 때까지 exit 차단"
- arXiv:2503.13657: "Ignored other agent's input"이 핵심 실패 모드 →
  커널 강제만이 무시 차단

심각도 분기:
- **Critical (Exit 2)**: P9 cascade 깨짐 (WIP problem ↔ 작업 파일 불일치).
  Claude가 WIP 고치기 전까지 작업 진행 0
- **Info (Exit 0)**: P1 경고 (에러 카운터 누적). 컨텍스트 주입만, 진행 가능

### 상태 파일 스키마

`.claude/session_signal.json`:

```json
{
  "session_id": "2026-05-11T14:30:00Z",
  "active_signals": [
    {
      "p_id": "P9",
      "severity": "CRITICAL",
      "message": "WIP/task_01.md problem 필드와 현재 수정 중 src/main.py 매칭 실패",
      "action_required": "WIP 갱신 또는 작업 대상 수정",
      "detected_at": "2026-05-11T14:30:00Z"
    }
  ],
  "counter": {
    "consecutive_errors": 0,
    "tool_use_count": 0,
    "last_modified_files": []
  },
  "last_updated": "2026-05-11T14:30:00Z"
}
```

라이프사이클:
- **생성**: orchestrator.py가 파일 부재 시 자동 생성
- **갱신**: 매 PreToolUse hook에서 orchestrator.py가 쓰기
- **삭제**: 명시적 삭제 안 함. `session_id` 다르면 무시
- **gitignore**: `.claude/session_signal.json` 추가

### 이중 안전장치 — stdout + 파일 쓰기 병행

Issue #13912 대비:
- `additionalContext` JSON stdout (공식 메커니즘, 불안정 가능)
- `.claude/session_signal.json` 파일 쓰기 (자가 안정)

Claude가 어느 한쪽 못 봐도 다른 쪽 보장.

### 다운스트림 cascade

| 구성요소 | 소유 | cascade 메커니즘 |
|---------|-----|-----------------|
| `scripts/orchestrator.py` | 업스트림 starter | harness-sync 배포 |
| `.claude/settings.json` hook 등록 | 업스트림 starter | harness-upgrade 동기화 |
| `P_DEFINITIONS.json` (P 신호 정의) | 다운스트림 확장 가능 | 본체 코드 무변경, 정의만 추가 |
| `.claude/session_signal.json` | 다운스트림 런타임 | 자동 생성, gitignore |

다운스트림이 자기 P 신호 추가 시 `P_DEFINITIONS.json`만 수정. orchestrator.py
본체 안 건드림 → 업스트림 업그레이드 영향 0.

## 구현 계획

### Phase 1 (본 wave) — MVI 박제

1. `scripts/orchestrator.py` 작성 (P1·P9 detect 로직, ~200줄)
2. `.claude/session_signal.json` 스키마 정의 + 초기 파일
3. `.claude/settings.json`에 PreToolUse hook 등록
4. `.gitignore`에 session_signal.json 추가
5. `test_orchestrator.py` 기본 회귀 (pytest 통합)
6. CPS Layer 2: orchestrator.py·hook의 `defends` + `trigger` frontmatter

### Phase 2 (후속 wave) — P 확장

- P4·P6·P7·P8 detect 로직 추가
- `P_DEFINITIONS.json` 도입 (다운스트림 확장 인터페이스)
- HARNESS_MAP 자동 역생성 통합

### Phase 3 (후속 wave) — 검증·튜닝

- 3개월 운영 후 무시율·오탐률 측정
- 폐기 신호 도달 시 후퇴 (단순화)

## 폐기 신호 (3개월 후)

- Claude 무시율 > 70% (시그널 발화했는데 작업 방향 안 바뀜)
- orchestrator.py 컨텍스트 토큰 비용 > 혜택
- false-positive 사용자 불만 누적

도달 시 본 결정 후퇴 — 시그널 단순화 또는 폐기.

## 관련 결정

- `cps_entry_signal_layering` (caused-by) — Layer 1·2·3 분리. 본 결정이
  Layer 간 연결 메커니즘 (실측 구현)
- `bit_cascade_objectification` (caused-by) — BIT Q1/Q2/Q3 + P9 신설.
  본 결정이 P9 → 도구 발화 cascade 실현
- `hn_p8_starter_self_application` (extends) — commit 흐름 강제 트리거.
  본 결정은 모든 작업 흐름 강제 트리거 메타 결정

## 사각지대

- **orchestrator.py 자체 자가 발화 의존 (재귀 P9)** — 진입점 PreToolUse가
  hook 강제라 LLM 의지 무관 작동. 재귀 차단됨
- **hook 실행 지연** — Gemini 폐기 신호 "2초 초과" 기준. 본 MVI는 파일
  I/O + frontmatter grep만이라 지연 미미 예상. 측정 필요
- **false-positive 마찰** — Critical은 Exit 2로 강제 중단 → 오탐 시
  사용자 작업 완전 차단. P9 detect 정확도 회귀 가드 필수
- **"부동의 인지" 거짓말** — Claude가 "고칠게요"라 말하고 안 고침.
  orchestrator.py는 파일 상태만 신뢰 (LLM 발화 무관)
- **stdout 불안정 (Issue #13912)** — 파일 쓰기 이중 안전장치로 보강

## 작업

### 1. 오케스트레이터 MVI 박제

**Acceptance Criteria**:
- [x] Goal: PreToolUse hook + orchestrator.py가 P1·P9 객관 신호 detect하고 강제 중단·컨텍스트 주입을 통해 cascade를 작동시킨다 ✅
  검증:
    review: review-deep
    tests: pytest -m orchestrator
    실측: python3 -m py_compile .claude/scripts/orchestrator.py + PreToolUse hook 한 차례 실제 호출 후 session_signal.json 생성 확인
- [x] scripts/orchestrator.py 작성 — stdin JSON 파싱, P1·P9 detect, stdout additionalContext, 파일 쓰기, exit code 분기 ✅
- [x] .claude/session_signal.json 자동 생성 메커니즘 (orchestrator 첫 실행 시)
- [x] .claude/settings.json PreToolUse hook 등록 (matcher 없음, 모든 도구) ✅
- [x] .gitignore에 session_signal.json 추가 ✅
- [x] test_orchestrator.py 회귀 가드 5 케이스 ✅
- [x] orchestrator.py·docs.md trigger 스키마 정의 (Layer 2 frontmatter) ✅

### 2. P1 신호 stale 누적 해소 (review 경고 2 대응)

직전 wave 직후 실측 — orchestrator.py 자기 수정·README 수정마다 P1 INFO
신호가 count 변화별로 별도 누적되어 PreToolUse 컨텍스트에 stale 신호 3건
이상 동시 출력. session 길어질수록 노이즈 증폭.

원인: `deduplicate_signals`가 `(p_id, message)` 키 사용 — count 변화 시
message 문자열 달라져 새 식별자로 인식 → upsert 안 됨.

해소: 신호에 `key` 필드 (예: `"P1:{file_path}"`) 추가. `_signal_key()`
가 `key`를 식별자로 우선 사용 → 같은 key는 교체(upsert). `key` 없으면
기존 `(p_id, message)` fallback 유지 (P9 등 정적 신호 호환).

**Acceptance Criteria**:
- [x] Goal: P1 신호가 count 변화 시 기존 신호를 교체하여 stale 누적 0건
  검증:
    review: review
    tests: pytest -m orchestrator
    실측: stale active_signals 0건 확인 (session_signal.json 검사)
- [x] `_signal_key()` 헬퍼 + `deduplicate_signals` upsert 동작 ✅
- [x] `detect_p1_same_file`에 `key: "P1:{fpath}"` 발급 ✅
- [x] 기존 stale 신호 정리 (session_signal.json reset) ✅
- [x] 회귀 가드 2건 신설 (upsert·dedup fallback) — 7/7 통과 ✅

review 경고 1 (harness-init false-positive)은 잘못된 시나리오로 판명 —
다운스트림은 harness-init을 실행 안 함 (업스트림 CPS가 그대로 전파).
revert 완료.

## 변경 이력

- 2026-05-11 — MVI 1차 박제 (8e1578c). P1·P9 detect + PreToolUse hook
- 2026-05-11 — Task 2 (P1 upsert stale 해소). review 경고 2 대응. review
  경고 1 (harness-init false-positive)은 시나리오 오인으로 판명 → revert

## 메모

본 wave는 Phase 1 MVI만. Phase 2·3은 후속 wave (별 WIP 신설).

본 결정은 본 시리즈 (cps_entry_signal_layering + bit_cascade + P9 신설 +
오케스트레이터) 최종 단계. 정의에서 멈추지 않고 실측 코드 박제까지 도달.
"설계도 찢고 스크립트 짜라"는 Gemini 권고 정합.
