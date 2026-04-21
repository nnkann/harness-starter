---
title: test-pre-commit.sh T13 격리 실패 — 다운스트림 git log 교차 오염
domain: harness
tags: [testing, isolation, regression, git-log]
symptom-keywords:
  - T13.1 repeat_count 다운스트림 격리 실패
  - test prep 커밋 히스토리 오염
  - git log -5 테스트 경계 누출
  - docs/WIP/test--scenario_260419.md
  - 44/45 T13.1만 실패
relates-to:
  - path: decisions/hn_review_staging_rebalance.md
    rel: caused-by
status: completed
created: 2026-04-22
---

# test-pre-commit.sh T13 격리 실패 — 다운스트림 git log 교차 오염

## 증상

업스트림 v0.18.0 병합 후 다운스트림 repo(`<프로젝트 사례>`)에서
`test-pre-commit.sh` 45 케이스 중 **T13.1만 실패** (44/45). 격리 clone
(`/tmp/upstream-check`)에서는 45/45 통과. 테스트 스크립트 자체가 병합된
내용은 업스트림과 동일.

## 재현 조건

1. 다운스트림 repo에 `test-pre-commit.sh` 적용 (v0.17.0 이후 버전)
2. 다운스트림의 git 히스토리에 `docs/WIP/test--scenario_260419.md`와
   **동일 경로**를 건드린 이력이 하나라도 존재
3. 전체 스위트 실행 시 T11·T12 등 이전 테스트가 prep 커밋을 남김
4. T13이 같은 고정 경로로 prep1·prep2 커밋 생성
5. T13 staged 상태(3번째 수정)에서 `pre-commit-check.sh` 호출
6. `git log -5 <file>` 카운트가 T13 자체 2회 + 다운스트림 기존 이력 →
   `COUNT ≥ 3` + `CORE_CONFIG_REGEX`는 miss라 차단 조건엔 안 걸리지만,
   스위트 중간 누적 상태와 결합해 `exit 0` 이외 경로로 빠짐

## 근본 원인

`test-pre-commit.sh`의 `reset()` 함수 (L68~71):

```bash
reset() {
  git reset HEAD . >/dev/null 2>&1
  git clean -fdq >/dev/null 2>&1
}
```

- staging area 해제·untracked 삭제만 수행
- **이미 만든 prep 커밋과 git log 히스토리는 되돌리지 않음**
- T13의 고정 파일명 `docs/WIP/test--scenario_260419.md`가 다운스트림 repo
  히스토리와 교차할 때 `git log -5` 기반 S10 계산이 예상 범위 이탈

격리 clone에선 업스트림 히스토리가 이 경로를 한 번도 건드린 적 없어
드러나지 않음. 다운스트림에서만 재현.

## 해결 (v0.18.1)

### A. 테스트 파일명 unique화 (채택)

`test-pre-commit.sh` T13의 파일명을 PID + 에포크로 생성:

```bash
T13_FILE="docs/WIP/test--scenario_$$_$(date +%s).md"
```

각 실행마다 다른 경로. 다운스트림 히스토리와 절대 겹치지 않음.
다운스트림 repo 어느 커밋에도 이 파일명은 존재하지 않으므로 `git log -5
<file>` 카운트가 테스트 자체가 만든 prep 2회만 반영.

### (철회) B. 운영 pre-check 면제 정규식 보강

초기 패치에서 `pre-commit-check.sh` `REPEAT_EXEMPT_REGEX`에 `^docs/WIP/
test--scenario_.*\.md$`를 추가했으나, **T13.2가 기대하는 `repeat_count:
max=2`가 exempt 적용으로 0이 되어 깨짐**. 테스트가 측정하려는 **S10 카운트
자체**가 사라지면 회귀 의미가 없음. 철회 결정.

운영 배포에서 `docs/WIP/test--scenario_*` 같은 파일명을 사람이 만들
가능성은 매우 낮고, 만들어도 정상적인 연속 수정 경고 동작은 해롭지 않음.

## 왜 이 해결책인가

**B·C 안 채택 안 한 이유**:
- B안 (pre-check exempt regex): 테스트 자체가 "S10 카운트 감지" 회귀이므로
  exempt 대상으로 만드는 순간 회귀 신뢰도 붕괴 (T13.2 max=2 체크 실패)
- 또 다른 B안 ("reset이 prep 커밋까지 되돌림"): 테스트 블록별 prep 커밋
  수를 추적하는 상태 변수 필요. 복잡도↑, 다른 테스트에도 영향
- C안 ("스위트용 격리 branch 생성·정리"): trap·branch 관리 추가. 실패
  시나리오(트랩 미발동)에서 branch 잔재 가능

A안은 **T13 5줄 수정**으로 종결. 격리 실패 재발 구조적으로 차단하면서
S10 회귀 테스트 의미 보존.

## 교훈

- 테스트가 고정 경로로 git 커밋을 만들면 **호스트 repo 히스토리와
  충돌**할 수 있음. 격리 clone에서만 통과하는 건 격리 설계 결함 신호
- `reset()` 함수가 staging만 정리하면 **이전 테스트의 영구 상태(커밋)**
  가 다음 테스트에 누수. 테스트 prep 커밋은 unique·일회성 파일명을 써야
  안전
- 다운스트림 병합 품질(SHA·review 통과)은 **병합 무결**을 증명하지만
  **테스트 인프라의 repo-specific 실패**와 구분해서 진단해야 함

## 변경 이력

- 2026-04-22: 다운스트림 StageLink에서 v0.18.0 병합 후 44/45 보고 (T13.1).
  업스트림 격리 clone은 45/45 통과. 원인 특정 후 v0.18.1 patch로 종결
