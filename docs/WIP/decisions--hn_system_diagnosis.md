---
title: 하네스 시스템 진단 frame — 13축 health check
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [diagnosis, health-check, orchestrator, cascade]
relates-to:
  - path: harness/hn_perf_baseline.md
    rel: extends
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
status: in-progress
created: 2026-05-12
updated: 2026-05-12
---

# 하네스 시스템 진단 frame

§H wave (v0.44.1~v0.46.0) 마감 직후 사용자가 정확히 짚은 시스템 health
check frame을 박제. 본 문서는 향후 단축 wave마다 참조될 SSOT — 진단
영역·실측 결과·root cause·다음 wave 우선순위.

## 배경

§H 시리즈로 commit 파이프라인을 fast/release path 분리·SKILL이 route 소비
·split 비파괴화·8 sub-task 묶음까지 닫았으나, baseline 측정 직후 다음 wave
결정에서 "어디부터·왜·진짜 효용 있나"가 불명확했다. 1회 측정·hook 10회
반복 같은 추측 방향이 사용자 지적("승질난다")으로 차단됐고, 진짜 진단
frame이 정의됐다.

## 진단 frame — 13축 health check

### 사용자 제기 10축

| # | 진단 항목 | 실측 결과 (2026-05-12) |
|---|----------|------------------------|
| 1 | orchestrator 신호가 commit 말단까지 정확? 왜곡·소실? | ❌ **단절**. `session_signal.json` stale 7개 누적, dedupe 없음, commit 후 reset 없음. commit log에 신호 박제 안 됨 |
| 2 | 명령 cascade 단계별 충족 | ⚠ implementation→commit→wip-sync→docs_ops→cluster 흐름은 동작. 단, 단계 간 신호 전달은 commit 스킬 stdout key:value로만 휘발. 외부 추적 불가 |
| 3 | CPS cluster 이전 작업 참고도 | ❌ 본 세션 `clusters/harness.md` 직접 Read 0회. 작업 진입점에서 cluster scan 명시되어 있지만 실제는 P# 매칭(skim)만 |
| 4 | hook 10회 반복 병목 | ✅ 미친짓 인정. 본 세션 데이터로 역산하면 충분 |
| 5 | 역추적 빠른 시스템 | ❌ 없음. `measure_commit_latency.py`가 1차지만 단계별 분해 없음. git author/committer date 차이 미활용 |
| 6 | frontmatter 효용성 | ⚠ `problem`·`solution-ref`는 pre-check 차단으로 효용 강제. `tags`는 본 세션 활용 0회. `relates-to`는 §H-8 매칭에만 사용 |
| 7 | 에이전트·스킬 개입·개선 효과 | implementation 5회 / commit 5회 / review 5회. **doc-finder·codebase-analyst·researcher·advisor·risk-analyst·performance-analyst = 0회**. review만 효용 명확 (verdict 5/5 catch) |
| 8 | 에이전트·스킬 추가 병목 | ⚠ commit/SKILL.md 770줄·implementation/SKILL.md 350+줄이 매 호출 context로 들어감. 5 wave × 2 스킬 × ~5000 토큰 = 50k+ 토큰 본문 반복 |
| 9 | 자잘한 경고 무시 | ❌ INFO 신호 매번 stale로 무시. commit log stage 값 정합(`deep-unavailable`/`standard-self`)도 자잘한 경고로 묻혔음 |
| 10 | 불필요 경고 | ❌ INFO false positive 100%. session-start 반복 신호도 본 세션 시작 시 모두 stale |

### Claude 추가 후보 3축

| # | 진단 항목 | 실측 |
|---|----------|------|
| A | review verdict 룰 위반 | 본 wave 1건 — review가 "승인"만 출력, pass/warn/block 단어 누락. extract_review_verdict.py 추출 실패 → 재호출 1회 룰 회피 (추측 pass 진행). 룰 자체 우회 누적 가능 |
| B | measure_commit_latency.py 자기 작성 도구만 측정 | git author/committer 시간 차·파일 mtime 미활용. 사용자 지적한 "역산"을 도구 자체가 안 함 |
| C | session-start 신호 vs orchestrator 신호 중복 | 둘 다 stale 신호 출력. 분리·중복·통합 가능성 미설계 |

## Root Cause — 단일 결함

**`session_signal.json` 메커니즘이 cascade를 끊고 있음**. orchestrator 추가
시 "wave 경계·dedupe·reset" 설계가 빠진 상태.

```
session_id: 2026-05-11T22:01:47   (어제 시작, 본 세션 reset 없음)
counter.tool_use_count: 70         (실제 200+ — 부정확)
last_modified_files: 같은 파일 7회 반복 (README), 6회 (followups) — dedupe 없음
active_signals: 7개 모두 stale     (본 wave 완료 후에도 잔존)
```

이 1개 결함이 사용자 진단 #1·#9·#10의 공통 root cause. 고치면 자동 해결.

## AC

**Acceptance Criteria**:

- [x] Goal: 13축 진단 frame 박제 + 다음 wave 4건 우선순위 결정 + 4 wave 모두 실행 완료될 때까지 본 WIP 마스터 인덱스로 유지. closed 조건은 4 wave 모두 완료.
  검증:
    review: skip
    tests: 없음
    실측: 없음
- [x] 진단 13축 항목 + 본 세션 실측 결과 표 박제.
- [x] Root cause 식별 (session_signal.json stale 누적).
- [x] 다음 wave 우선순위 4건 박제.
- [x] 폐기 후보 (hook 10회 반복·bash-guard 단독 단축) 명시.
- [x] 다음 wave 1 — orchestrator P1 stdout mute 완료 (D 옵션, 재설계 폐기 — false positive 100% 차단). 추가 dedupe/wave 경계 인식은 별 wave 후보.
- [ ] 다음 wave 2 — latency 단계별 역산 완료.
- [ ] 다음 wave 3 — cluster 진입 강제 완료.
- [ ] 다음 wave 4 — SKILL.md 본문 다이어트 완료. (폐기 박제 정리 부분 완료 `db28b79` — 본격 다이어트 별 wave) ✅

## 결정 — 다음 wave 우선순위

| 우선 | wave | 사용자 진단 매핑 |
|------|------|------------------|
| **1** | **orchestrator session_signal cascade 재설계** — wave 경계·dedupe·reset 메커니즘 추가 | #1·#9·#10 (단일 root cause) |
| 2 | latency 단계별 역산 — `measure_commit_latency.py` 확장. git author/committer date·파일 mtime·commit_finalize timestamp 박제 활용 | #5·B |
| 3 | cluster 진입 강제 — implementation Step 0.3 doc-finder fast scan이 실제로 cluster 본문 Read하는지 회귀 가드 | #3·#6 |
| 4 | SKILL.md 본문 다이어트 — context 비용 감소. commit/implementation 본문 압축 또는 분할 | #7·#8 |

### 폐기된 후보

- 각 hook 10회 반복 측정 — 사용자 지적 "미친짓". 본 세션 데이터로 역산
  가능
- bash-guard 단독 단축 — 1회 측정 + 추정 누적으로 우선순위 단정한 추측.
  실제 hook 발화 카운트 없이는 우선순위 결정 불가

## 메모

- 본 진단은 2026-05-12 사용자 지적("여지껏 데이터로 충분하게 결정한 건
  가?")으로 시작됨. baseline 측정 직후 단축 wave를 추측 시작하려던 흐름
  차단.
- 사용자가 진단 frame을 직접 적어준 사건 자체가 별 incident 후보 —
  "Claude가 좁은 wave 사고에 갇혀 시스템 전반 진단을 못 한 패턴". signal
  파일 또는 memory 박제 후보.
- 본 문서 닫힘 후 첫 wave는 우선순위 1 (orchestrator cascade 재설계).
  나머지 3개는 별 wave.
