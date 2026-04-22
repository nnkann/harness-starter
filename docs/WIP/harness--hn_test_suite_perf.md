---
title: test-pre-commit.sh 스위트 성능 최적화
domain: harness
tags: [test, perf, infra]
status: pending
created: 2026-04-22
---

# test-pre-commit.sh 스위트 성능 최적화

현재 전체 실행 시간 **2m31초** (Windows Git Bash, 업스트림 리포). 64 케이스.
목표: 45~60초 수준으로 단축.

## 왜

- 회귀 테스트를 자주 돌릴수록 품질 방어선이 강해지는데, 2m31초는 심리적
  장벽이 됨 → 개발 중 스위트를 생략하게 됨
- 실제 v0.20.1·0.20.2 커밋 과정에서 전체 스위트 돌릴 때마다 세션이
  마비됨. 사용자 불만 실측 발생

## 현황 진단 (2026-04-22)

### 비용 구조

전체 2m31초 = `user 1m1초` + `sys 1m24초` + 대기. Windows `fork`·`fs`
오버헤드가 `sys` 지배. 케이스당 평균 ~2.4초.

지배적 비용:
1. **T0 setup**: `git clone -q . "$TEST_DIR/repo"` (전체 repo 복사). 수 초
2. **매 케이스 `reset()` + git add**: 64 × (git reset + git clean + git add)
   = 파일 I/O 폭증
3. **매 케이스 pre-check 1회**: 업스트림 실측 ~1.2초 × 64 ≈ 77초 이론 하한

## 최적화 옵션

### A. 쉬운 것 (효과 큼, 위험 낮음)

1. **clone 경량화 or 제거** — 전체 repo clone 대신 `git init + 필요 파일
   cp` 또는 `--depth=1 --no-tags`. 예상 절감 10~20초
2. **병렬 실행** — bash `&` + `wait` or `xargs -P 4`. pre-check 케이스
   상호 독립. 워커별 tmp 디렉토리 분리 필요. 예상 절감 50%+ (2m → 1m)
3. **reset() 최적화** — `git reset + git clean` 대신 `rm -rf work/*` +
   최소 `git add`. 예상 절감 10~20%

### B. 중간 (효과 큼, 위험 중간)

4. **pre-check 자체 최적화** — 내부에 `task-groups.sh`·`docs-ops.sh` 호출
   파이프라인 있음. 프로파일링으로 핫스팟 찾으면 20~30% 단축 가능성. 단
   변경 범위 큼, 별도 audit 필요

### C. 어려움 (효과 불확실)

5. **케이스 공유 fixture** — reset 없이 그룹 순차 실행. 격리성 깨질 위험

## 제안 진행 순서

1. A-1 (clone 경량화) 먼저 — 변경 범위 작고 효과 명확
2. A-2 (병렬화) — 효과 크지만 워커 격리 설계 필요. 단독 커밋
3. 나머지는 측정 후 필요 시

## 영향 파일

- `.claude/scripts/test-pre-commit.sh`

## 검증 기준

- 전체 스위트 45~60초 수준 도달
- 64/64 통과 유지
- 병렬 시 case 순서 뒤섞여도 FAIL 없음 (격리성)

## 관련

- 배경: v0.20.2 커밋 과정 (task-groups.sh awk fork fix 중 사용자가 전체
  스위트 2m39초 실행 관찰하고 불만 표명)
- `docs/WIP/harness--hn_commit_process_audit.md` 실측 대기 #13/#16/#18
  은 commit 스킬 성능이며 본 주제와 다름
