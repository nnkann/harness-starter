---
title: pre-commit-check.sh 자체 성능 최적화
domain: harness
tags: [pre-check, perf, profiling]
status: pending
created: 2026-04-22
updated: 2026-04-23
---

# pre-commit-check.sh 자체 성능 최적화

test-pre-commit 스위트 2m31초는 **증상**. 근본 원인은 **pre-check 1회가
1.2초**. 64번 순차 실행이라 이론 하한 ~77초.

## 왜 병렬화가 답이 아닌가

- 병렬화는 "64번 돌아야 하는 이유"를 피하는 우회. 증상 치료
- 총 CPU 시간은 그대로, 워커별 tmp·결과 집계·격리 검증 부담만 추가
- **근본 해결**: pre-check 1회를 1.2초 → 0.3초로 줄이면 스위트는 자동
  으로 2m → 30초. 매 커밋 체감도 동반 개선

## 목표

- **pre-check 1회 < 0.5초** (업스트림 리포 실측, Windows Git Bash)
- 결과: 스위트 전체 1분 이하 자동 달성

## 접근

### 1. 프로파일링

```bash
# bash -x 또는 EPOCHREALTIME 기반 측정
PS4='+ $EPOCHREALTIME ' bash -x .claude/scripts/pre-commit-check.sh 2>prof.log
# gap 큰 구간 top 10 추출
```

과거 v0.20.2 task-groups.sh 프로파일링 경험 참조: `for wip in ...; do awk`
파일당 fork 패턴이 1.5초 차지. 동일 패턴이 pre-check 본체나 호출 스크
립트(`task-groups.sh`·`docs-ops.sh`)에 더 있을 가능성.

### 2. 의심 핫스팟 (프로파일링 전 가설)

- `task-groups.sh` 호출 — v0.20.2에서 awk fork 1.5→0.3초 개선했지만 여전히
  0.3초 차지. 통합 awk로 1회 fork 수준까지 가능한가
- `docs-ops.sh extract_abbrs` — awk로 naming.md 스캔. pre-check에서 호출
  되는지 확인 필요
- dead link 검사 Step 3.5 (v0.18.6 신설) — `grep -rn --include='*.md' ...
  docs .claude` 가 전체 docs 스캔. staged 파일 없어도 매번 돈다면 낭비
- STAGED_DIFF / STAGED_NUMSTAT / STAGED_NAME_STATUS 3회 git 호출 — 이미
  v0.13.2에서 22→3회로 줄임. 더 줄일 여지 있나
- S10 반복 카운트 `git log -5 --name-only` — 매번 git 호출

### 3. 구조적 후보

- **"변경 없으면 건너뛰기"** — pre-check 전체를 STAGED_FILES 검사 전
  early exit 할 수 있는 블록이 있는가
- **캐싱** — v0.19.0에서 tree-hash 캐싱 폐기됐지만, 스위트 내부에서는
  같은 repo 상태에서 64번 돌기에 case별 fixture 변경만 반영하면 됨. 단
  pre-check 자체 캐싱보다 test 쪽 fixture 최적화가 안전

## 진행 조건

- **프로파일링 결과 없이 착수 금지**. no-speculation 원칙
- 핫스팟 top 3가 명확해지면 각 fix 1커밋씩

## 영향 파일 (프로파일링 후 결정)

- 주: `.claude/scripts/pre-commit-check.sh`
- 보조: `.claude/scripts/task-groups.sh`, `.claude/scripts/docs-ops.sh`

## 검증 기준

- pre-check 1회 < 0.5초 (업스트림 5회 측정 평균, 체감 아님)
- 기능 회귀 0 (test-pre-commit 64/64 유지)
- test-bash-guard 18/18 유지
