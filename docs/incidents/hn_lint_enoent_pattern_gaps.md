---
title: v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭
domain: harness
tags: [upstream-feedback, pre-commit-check, lint, enoent, false-positive, no-speculation]
symptom-keywords:
  - ENOENT 패턴 오탐
  - No such file or directory ESLint import
  - Cannot find module ESLint crash
  - exec eslint not found Alpine
  - 린터 rule 위반 warn 격하
  - zsh command not found 형식
  - MIGRATIONS 단정 표현
status: completed
created: 2026-04-22
updated: 2026-04-22
---

# v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭

## 배경

v0.18.3 (`370c4cc`)의 `pre-commit-check.sh` 린터 단계에 ENOENT 구분
분기가 추가됨. 도구 실종 → warn+skip, rule 위반 → 차단. 다운스트림
repo(`<프로젝트 사례>`)에서 `0.18.0 → 0.18.3` 연속 업그레이드 커밋
review 시 아래 2건이 warn으로 지적됨.

MIGRATIONS.md v0.18.3 "회귀 위험" 섹션이 "실제 ESLint·Ruff 출력과 겹치지
않음"이라 단언했으나 근거가 없어 `rules/no-speculation.md` 위반. 다운
스트림 review 에이전트가 upstream 단정을 **역으로 검증**해 갭을 발견.

## 증상 1 — 패턴 오탐 가능성

### v0.18.3 패턴

```bash
grep -qE "is not recognized as an internal or external command|command not found|No such file or directory|Cannot find module|ENOENT"
```

### 오탐 시나리오

| 패턴 | 오탐 시나리오 | 결과 |
|---|---|---|
| `No such file or directory` | ESLint `import/no-unresolved` rule이 존재하지 않는 import 경로 감지 시 crash: `Error: ENOENT: no such file or directory, open '/path/import.ts'` | rule 위반 warn+skip으로 격하 |
| `Cannot find module` | Node.js `require()`/`import`가 ESLint 플러그인 미설치로 crash-exit: `Error: Cannot find module 'eslint-plugin-xyz'` | 플러그인 설정 에러 warn+skip |
| `ENOENT` | 위 두 케이스의 syscall 에러 메시지에 ENOENT 포함 → 이중 매칭 | 확실한 오탐 |

## 증상 2 — OS별 실종 메시지 커버리지 갭

| 환경 | 실제 출력 | v0.18.3 매칭 | v0.18.4 매칭 |
|---|---|:---:|:---:|
| Windows cmd/PowerShell | `'eslint' is not recognized as an internal or external command` | ✅ | ✅ |
| Bash 일반 | `bash: eslint: command not found` | ✅ | ✅ |
| **macOS zsh** | `zsh: command not found: eslint` | ⚠ 애매 | ✅ |
| Windows Git Bash | `bash: eslint: command not found` | ✅ | ✅ |
| Alpine/BusyBox | `exec: eslint: not found` | ❌ 미커버 | ✅ |
| Dash/POSIX sh | `sh: 5: eslint: not found` | ❌ 미커버 | ✅ |
| pnpm 고유 | `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL` | ❌ 미커버 | ✅ |

**zsh 형식 실측 발견 (v0.18.4 T33.3)**: 다운스트림 제보는 `: command not
found$`가 zsh 형식을 커버한다고 가정했으나, zsh 실제 출력은 `command not
found: <명령>` (명령이 끝). `$` 고정 패턴이 실패. T33.3 회귀 테스트가
실행 시 FAIL → 패턴을 보완(`command not found: <명령>$` 추가) 후 PASS.

**다운스트림 제안 검증의 한계 사례** — 제안도 실측 없이 단정했던 부분
이 있음. T33·T34 회귀 테스트가 이를 잡아냄.

## v0.18.4 해결

### A. 패턴 정교화

```bash
# shell이 "명령 자체를 못 찾음"을 알리는 고유 형식만 매칭
grep -qE "\
is not recognized as an internal or external command|\
: command not found$|\
command not found: [a-zA-Z0-9_./+-]+$|\
^exec: [^:]+: not found$|\
^sh: [0-9]+: [^:]+: not found$|\
ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL"
```

**변경**:
- 제거: `No such file or directory`, `Cannot find module`, `ENOENT` —
  ESLint 내부 crash와 구분 불가
- 추가: zsh 전용(`command not found: X$`), Alpine(`exec: X: not found$`),
  Dash(`sh: N: X: not found$`), pnpm(`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`)

### B. T33·T34 회귀 테스트 신설

`test-pre-commit.sh`에 12 케이스 추가:
- T33: 7가지 shell별 실종 형식 → 매칭 기대 (Windows cmd / bash / zsh /
  sh / Alpine / Dash / pnpm)
- T34: 5가지 ESLint crash·rule 위반 → **미매칭** 기대 (import resolver
  ENOENT / 플러그인 missing / rule 위반 / node trace / syntax error)

패턴 SSOT를 `ENOENT_PATTERN` 변수로 분리해 `pre-commit-check.sh`와 동기화.

### C. no-speculation.md 보강

`rules/no-speculation.md`에 "MIGRATIONS.md 회귀 위험 섹션 작성 원칙"
추가. "겹치지 않음" 같은 단정 금지, 검증 범위 명시 강제.

## `Cannot find module` 정책

**block 유지** (v0.18.4 결정):
- ESLint 플러그인 미설치는 도구 실종과 **다른 층**. 린터는 실행됐지만
  설정이 불완전 → rule 위반처럼 다운스트림이 해결해야 할 상태
- warn 격하는 **실수 은폐**. `eslint-plugin-xyz` 누락을 warn만 내면
  다운스트림이 린트가 실제로 돌지 않는 걸 모름
- "도구 실종"은 shell이 바이너리를 찾지 못한 ENOENT만. 그 외는 lint
  실패로 분류

## 재발 방지

### 인프라 차원

- **T33·T34 회귀 테스트 상시 유지**: 패턴 SSOT가 변경되면 즉시 실측
  검증. 이번 zsh 형식 갭이 이 방식으로 발견됨
- **OS별 fixture 확장**: 향후 다른 shell·에러 형식 추가 시 T33에 한 줄
  추가로 회귀 방지

### 행동 차원

- **no-speculation.md "MIGRATIONS 작성 원칙"** 명문화 (v0.18.4)
- review 에이전트가 MIGRATIONS.md "회귀 위험" 섹션의 보편 단정 표현
  (`"겹치지 않음"`·`"영향 없음"`)을 자동 경고 (`review.md`의 계약 축
  체크리스트에 암묵 포함)

## 이번 사례에서 배운 것

### 다운스트림 review가 upstream 문서를 역으로 검증한 사례

- 다운스트림이 upgrade 받으며 review deep 실행 → MIGRATIONS.md 단정이
  자기 환경과 맞지 않음을 감지 → warn으로 지적
- upstream은 격리 환경에서만 검증하므로 OS 커버리지 갭을 볼 수 없음.
  **다운스트림 review가 실질적 QA 역할**을 함
- 이 루프를 명시적으로 인정하고 no-speculation.md에 문서화

### 제안 자체도 실측 검증 대상

- 다운스트림 제안 A안도 zsh 형식에서 실패 — 제안자가 실측 안 한 부분
- T33·T34 회귀 테스트가 이를 즉시 잡음. "제안을 믿고 그대로 반영" 대신
  **실측 테스트로 검증**한 것이 옳았음
- upstream도 제안을 받더라도 testable·measurable 조각으로 쪼개 검증해야

## 변경 이력

- 2026-04-22 (v0.18.3): 린터 도구 실종 구분 분기 최초 추가. 패턴은 "ESLint
  출력과 겹치지 않음" 단정하에 설계. 실측 없음
- 2026-04-22 (v0.18.4): 다운스트림 review 지적으로 오탐·커버리지 갭 발견.
  패턴 정교화 + T33·T34 회귀 테스트 신설 + no-speculation.md 보강
