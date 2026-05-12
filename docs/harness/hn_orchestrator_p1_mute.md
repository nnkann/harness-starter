---
title: orchestrator P1 신호 stdout mute (false positive 100% 차단)
domain: harness
problem: P9
solution-ref:
  - S9 — "주관 격리 + 다층 검증 (부분)"
tags: [orchestrator, p1, mute, false-positive]
relates-to:
  - path: WIP/decisions--hn_system_diagnosis.md
    rel: implements
status: completed
created: 2026-05-12
updated: 2026-05-12
---

# orchestrator P1 신호 stdout mute

진단 wave 1 — D 옵션. 본 세션 P1 false positive 100% (모든 stale)이라
context 노이즈 + 사용자·Claude 자가 점검 부담. P9·detect·signal·Gemini는
그대로 유지. p_id=P1 신호의 stdout 출력만 차단.

## 사전 준비

- 읽을 문서: `decisions/hn_system_diagnosis.md` (진단 frame), `harness/hn_perf_baseline.md` (hook overhead baseline)
- 이전 산출물: 진단 frame 박제 commit
- MAP 참조: orchestrator.py P9 메커니즘 본체

## 목표

P1 신호 stdout 출력 차단. 다음 그대로 유지:
- P9 critical exit 2
- P1 detect 로직 (`detect_p1_same_file`) — signal_*.md 누적 가능
- Phase1 (Gemini 트리거) 신호 출력
- session_signal.json 백그라운드 측정

## 작업 목록

### 1. P1 stdout mute + 회귀 가드

**영향 파일**:
- `.claude/scripts/orchestrator.py` (main 함수 출력부, 1~5줄)
- `.claude/scripts/tests/test_orchestrator.py` (회귀 가드 추가)

**구현 방향**:
```python
# 현재: new_signals 전체 stdout 출력
# 변경: stdout용 P1 제외. detect·dedupe·save_signal은 그대로
output_signals = [s for s in new_signals if s.get("p_id") != "P1"]
if not output_signals:
    return 0
critical_now = has_critical(new_signals)  # 전체로 판정 (P9 critical은 유지)
emit_output(output_signals, block=critical_now)
```

**Acceptance Criteria**:

- [x] Goal: orchestrator.py P1 신호(동일 파일 연속 수정)의 stdout INFO 출력 mute. P9 critical (exit 2)·detect 로직·signal 누적·Gemini 트리거는 그대로 유지. 본 세션 같은 의도된 wave 일관 변경에서 false positive 0. ✅
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_orchestrator.py -q
    실측: PreToolUse hook 1회 실행 시 stdout에 P1 INFO 0건 (이전: 매번 1~4건)
- [x] orchestrator.py P1 신호 stdout 출력부 mute (main 함수 5줄 — output_signals 필터링). ✅
- [x] P9 critical exit 2 동작 회귀 가드 (기존 18 passed 그대로).
- [x] P1 detect 로직 유지 — signal_*.md 누적 가능 (백그라운드 측정).
- [x] 본 wave 진행 중 INFO 신호 출력 0건 실측 (P1 강제 발화 4회 stdout 빈 출력 확인 + `test_p1_signal_muted_from_stdout` 회귀 가드 통과).

## 결정 사항

- p_id="P1" 필터링으로 mute. p_id="P9" CRITICAL과 p_id="Phase1" (Gemini)
  은 출력 유지.
- detect 로직·dedupe·session_signal 백그라운드 저장 모두 유지 — 단지
  stdout 출력 단계에서만 P1 제외.
- 회귀 가드 1건 추가: `test_p1_signal_muted_from_stdout` — P1 임계 4회
  호출 후 stdout 빈 출력 + session_signal에 P1 누적 양쪽 검증.
- CPS 갱신: 없음. P9·S9 메커니즘 본체 변경 아님 (출력 필터링만).

## 메모

- 실측 결과:
  - 4회 강제 P1 발화: stdout 모두 비어있음 (mute 이전: 매번 INFO JSON 출력)
  - pytest test_orchestrator.py: 19 passed (+1 P1 mute 회귀), 1 skipped
  - session_signal.json에 P1 누적은 그대로 — 백그라운드 측정 유지
- 본 변경 직후부터 본 wave commit·tool call에서 INFO P1 신호 stdout
  출력 0건 (이전: 매 tool call 1~4건).
- 사용자 진단 #1·#9·#10 root cause 일부 해소. session_signal stale
  dedupe·wave 경계 인식은 별 wave 후보 (본 wave는 stdout mute만).
- 진단 WIP wave 1 항목 [x] 마킹 예정 (commit 시 함께 처리).
