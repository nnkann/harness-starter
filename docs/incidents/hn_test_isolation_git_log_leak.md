---
title: test-pre-commit.sh T13 격리 실패 — 원인 부분 확정 (진행 중)
domain: harness
tags: [testing, isolation, regression]
symptom-keywords:
  - T13.1 repeat_count 다운스트림 격리 실패
  - 수동 재현 exit 0 스위트 내부 exit 2
  - T1~T12 누적 상태 T13 영향
  - docs/WIP/test--scenario_*.md
  - 44/45 T13.1만 실패
  - TEST_DEBUG=1
relates-to:
  - path: decisions/hn_review_staging_rebalance.md
    rel: caused-by
status: in-progress
created: 2026-04-22
updated: 2026-04-22
---

# test-pre-commit.sh T13 격리 실패 — 원인 부분 확정 (진행 중)

## 증상

업스트림 v0.18.0 병합 후 다운스트림 repo(`<프로젝트 사례>`)에서
`test-pre-commit.sh` 45 케이스 중 **T13.1만 실패** (44/45). 격리 clone
(`/tmp/upstream-check`)에서는 45/45 통과. 테스트 스크립트 자체가 병합된
내용은 업스트림과 동일.

## 진행 상황 (2026-04-22)

### 확인된 사실

- 스위트 내부 T13 → `exit 2`
- **수동 재현** (reset → 동일 steps → pre-check 직접 호출) → `exit 0`
- 유일한 차이: 스위트가 T1~T12 동안 누적시킨 repo 상태
- `reset()` 함수는 `git reset HEAD . && git clean -fdq`만 수행 →
  **이전 테스트가 만든 prep 커밋과 git log는 그대로 남음**

### 최초 가설 (v0.18.1에서 fix 시도) — 한 측면만 해결

최초 진단: **고정 파일명 `docs/WIP/test--scenario_260419.md`가 다운스트림
repo 히스토리와 교차 오염 → `git log -5 <file>` S10 카운트가 예상 범위
이탈 → exit 2**.

v0.18.1에서 파일명을 PID + 에포크로 unique화 (A안). 하지만 **다운스트림
재검증 결과: fix 적용 후에도 여전히 T13.1 exit 2 지속**.

### 가설의 한계 — 원인 미확정 자인

- unique 파일명이면 **git history 교차 자체가 불가능**. 그런데도 실패
  지속 → 교차가 exit 2의 직접 원인이 **아닐 가능성** 높음
- A안은 "고정 경로 교차 가능성"은 봉쇄했지만 **다운스트림 실제 실패의
  원인은 미해결**
- 최초 가설이 그럴듯한 설명이었던 탓에 관찰 없이 고정시킨 분석 실수

### 정정된 상태 — 원인 미확정

**현재 시점에서 exit 2의 확정 원인은 밝혀지지 않음**. 이유는 스위트
내부 T13 분기가 `output=$(bash .claude/scripts/pre-commit-check.sh 2>&1)`
로 stderr 캡처만 하고 출력하지 않음 → **사용자 가시 stderr가 없어 exit
2 사유 파악 불가**.

## 재진단 프로토콜 (v0.18.2 도입)

### TEST_DEBUG=1 디버그 훅

`test-pre-commit.sh` T13·T19·T20 등 **출력 캡처 FAIL 분기**에 옵트인
디버그 출력 추가. 평상시 결과는 변화 없음, 재현 시에만:

```bash
TEST_DEBUG=1 bash .claude/scripts/test-pre-commit.sh 2>&1 \
  | sed -n '/\[T13\]/,/\[T14\]/p'
```

FAIL 분기에서 캡처된 `$output`을 `[pre-check 출력]` 헤더와 함께 stderr
사유까지 보여줌. 이 결과로 exit 2 직접 원인 특정 가능.

### 다운스트림 재실행 절차

```bash
cd <downstream-repo>
# v0.18.2 upgrade 받은 뒤
TEST_DEBUG=1 bash .claude/scripts/test-pre-commit.sh 2>&1 \
  | sed -n '/\[T13\]/,/\[T14\]/p'
```

나오는 stderr 라인 (`❌ ...` 등)이 exit 2 이유. 그걸 본 incident에 반영
후 실제 fix를 v0.18.3에 반영.

## 잠정 유지 결정

### A. 테스트 파일명 unique화 (유지)

v0.18.1의 파일명 unique화는 **고정 경로 교차 가능성은 봉쇄**함. 다운스트림
실제 실패의 원인이 아닐 수 있지만, **경로 교차 리스크 자체는 현실이므로
유지할 가치 있음**.

### (철회) B. 운영 pre-check 면제 정규식

`pre-commit-check.sh` `REPEAT_EXEMPT_REGEX`에 `^docs/WIP/test--scenario_.*
\.md$`를 추가하려 했으나, **T13.2의 `repeat_count: max=2` 체크가 exempt로
0이 되어 깨짐**. 회귀 의미 자체가 붕괴 → 철회.

## 교훈 (과정 자체에 대한)

- **관찰 없이 "그럴듯한 설명"을 확정하면 안 된다.** 초기 가설(git log
  교차)이 그럴듯했던 탓에 `unique 파일명이면 교차 불가능`이라는 단순
  반증을 놓침. `rules/no-speculation.md` 위반
- **incident를 "원인 확정"으로 적기 전에 재현 테스트를 검증**해야 함.
  v0.18.1 fix는 upstream 격리 45/45를 근거로 삼았지만 **다운스트림에서
  실제로 해결됐는지 확인하지 않고 merge·push**
- **테스트 스크립트의 FAIL 분기가 정보를 버리면 진단이 불가능**. 출력
  캡처는 PASS 경로만 최적화하면 안 되고 FAIL 경로도 재현성을 보존해야

## 변경 이력

- 2026-04-22 (v0.18.1): 최초 진단 `git log 교차`를 원인으로 확정, 파일명
  unique화로 fix 시도. **실제로는 한 측면만 해결**, 다운스트림에서 T13.1
  여전히 exit 2
- 2026-04-22 (v0.18.2): **원인 미확정 자인**. 재진단 프로토콜(TEST_DEBUG=1)
  도입. A안 유지 근거 정정 (실제 원인 해결 아닌 별개 리스크 봉쇄).
