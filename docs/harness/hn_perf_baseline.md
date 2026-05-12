---
title: 퍼포먼스 baseline 측정 — 5영역 1 wave
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [performance, measurement, baseline]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
status: completed
created: 2026-05-12
updated: 2026-05-12
---

# 퍼포먼스 baseline 측정 wave (5영역)

사용자 명시 지시 "전부 다". 5영역 (A·B·C·D·E)을 1 wave 1 commit으로
묶어 baseline 측정. 영역별 단축은 baseline 데이터 보고 후 별 wave.

## 사전 준비

- 읽을 문서: `docs/harness/hn_commit_perf_optimization.md` §B/§I (release
  path 분리·판정식).
- 이전 산출물: §H-1~§H-11 완료 (`cc01f0e`~`8fc9e7a`).
- MAP 참조: hook/scripts/skill 전반.

## 목표

5영역 baseline 박제:
- (A) §H 운용 효과 — commit latency 인프라 + 본 세션 5 commit baseline
- (B) /eval --harness 시간
- (C) hook overhead (orchestrator·debug-guard·bash-guard·write-guard)
- (D) review agent latency (운용 누적 안내)
- (E) 사용자 지정 — 본 wave 미지목, baseline 데이터 보고 후 결정

## 작업 목록

### 1. 측정 + 인프라 신설

**영향 파일**:
- 신규 `.claude/scripts/measure_commit_latency.py` — git log → commit별
  stage·problem·solution-ref·간격 추출
- 측정 결과는 본 WIP `## 메모`에 박제

**Acceptance Criteria**:

- [x] Goal: 5영역 baseline을 1 wave 1 commit에 박제. 단축 wave는 baseline 보고 후.
  검증:
    review: review
    tests: 없음
    실측: python3 .claude/scripts/measure_commit_latency.py 15
- [x] (A) `measure_commit_latency.py` 신규 + 본 세션 15 commit baseline 출력 + 본 WIP에 결과 박제. ✅
- [x] (B) `eval_harness.py` 실행 시간 측정 + 결과 박제 (278ms).
- [x] (C) 4 hook 각각 time 측정 + 결과 박제.
- [x] (D) review agent latency — 본 세션 4 review duration_ms 평균 박제 (17s).
- [x] (E) baseline 데이터 보고 — 별 wave 후보 본문에 명시.

## 결정 사항

- 본 wave는 baseline 측정만. 영역별 단축은 별 wave (사용자 결정).
- 측정 인프라 `measure_commit_latency.py`만 영구 자산 — 다른 영역은 본
  WIP 메모로 박제.
- CPS 갱신: 없음. 측정으로 S2 효과 baseline 박제. 메커니즘 변경 없음.

## 메모

### (A) commit latency baseline (최근 15 commit, 2026-05-11~12)

```
stage 분포: deep 3 / deep-unavailable 1 / skip 3 / standard 5 / standard-self 3
problem 분포: P2 8 / P9 4 / none 3
간격 평균: 127분 (세션 휴식 포함), 최소 22s, 최대 53590s
```

§H wave 4개 (`cc01f0e`~`db402bd`): 모두 `standard` stage, P2/S2.
17:00~18:07 1시간 7분에 4 commit (평균 16분/commit).

**stage 이상 값 발견**: `deep-unavailable`·`standard-self` — `review_route`
나 `recommended_stage` 외 자유 입력값이 commit log에 들어감. SKILL의 자가
보고 시스템 + 작성자 자유 표기 결과. 정합 정리는 별 wave.

### (B) eval_harness.py 실행 시간

```
real    0m0.278s
user    0m0.015s
sys     0m0.015s
출력 45 lines
```

278ms — 빠름. 단축 우선순위 낮음.

### (C) hook overhead (PreToolUse 매 호출)

| Hook | real time | trigger 빈도 |
|------|-----------|--------------|
| orchestrator (PreToolUse 전 hook) | 209ms | 매 tool call (Bash/Edit/Write/Read 등) |
| debug-guard (UserPromptSubmit) | 244ms | 매 사용자 발화 |
| bash-guard (Bash 직전) | 349ms | 매 Bash tool 호출 |
| write-guard (Write/Edit 직전) | 101ms | 매 Write/Edit tool 호출 |

**누적 추정** (본 세션 200+ tool call 가정):
- orchestrator: 200 × 209ms = ~42초
- bash-guard: Bash 호출 ~80회 × 349ms = ~28초
- write-guard: Write/Edit ~50회 × 101ms = ~5초
- 합계: ~75초 hook 누적 latency

orchestrator + bash-guard = Bash 매 호출 558ms hook 부담. 가장 큰 단축
후보.

### (D) review agent latency

본 세션 4 review 호출 duration_ms (Agent tool 결과 메타):

| Wave | Stage | duration_ms |
|------|-------|-------------|
| §H-1 | standard | 13,730 |
| §H-2 | standard | 25,555 |
| §H-3 | standard | 15,985 |
| §H-4~11 묶음 | standard | 15,650 |

평균: 17,730ms (~17.7s). 모두 read budget 3회 이내 준수.

운용 누적 안내: review 시간은 Agent tool 결과 메타에 있지만 git log에는
박제되지 않음. 별 wave 후보 — `🔍 review:` 라인에 duration_ms 포함.

### (E) 별 wave 후보 (사용자 결정 대상)

baseline 데이터 기반 단축 우선순위:

1. **bash-guard latency** (349ms × 매 Bash) — 가장 큰 누적. bash 스크립트
   파싱·jq·token 분리. 단축 후보: Python 재작성 또는 정규식 사전 compile.
2. **orchestrator latency** (209ms × 매 tool call) — Python import 비용.
   단축 후보: import lazy 또는 가벼운 entry point.
3. **commit log stage 값 정합** — `deep-unavailable`/`standard-self` 같은
   자유 표기 표준화. `🔍 review:` 라인 schema 강제.
4. **review duration_ms 박제** — git log에 review 시간 포함으로 사후
   audit 가능.

§H 운용 효과 측정 본격화는 다음 5~10 commit 누적 후. 본 baseline이
비교 기준점.
