---
title: pytest 효율과 회귀 라우팅 재정렬
domain: harness
c: "전체 pytest 기본값 회귀 + memory/reminder 기반 회귀 환기 약화"
problem: [P6, P8, P9, P11]
s: [S6, S8, S9, S11]
tags: [pytest, regression, memory-system, reminder, test-diet]
relates-to:
  - path: decisions/hn_test_diet.md
    rel: references
  - path: cps/cp_problem_boundary_refinement.md
    rel: caused-by
status: completed
created: 2026-05-19
updated: 2026-05-19
---

## Context

이번 CPS 정련 wave에서 전체 pytest를 실행했을 때, 검증 대상보다 비용과
노이즈가 더 크게 드러났다.

- 전체 pytest는 약 60초대까지 커졌다.
- `TestCommitFinalize` 2건은 Windows/Git Bash alternates 경로 문제로 실패했다.
- 부분 실행(`-k "not TestCommitFinalize"`)도 wave 검증으로는 여전히 무겁다.
- 기존 `docs/decisions/hn_test_diet.md`는 이미 "전체 pytest는 CI·eval·사용자
  명시 요청 한정, 일상 검증은 AC marker/path 중심" 원칙을 세웠다.

동시에 회귀 테스트는 memory/reminder와 연결되어야 한다. 과거 회귀가 문서에
박제되어 있어도, 현재 C에서 어떤 marker/path를 떠올려야 하는지 자동 환기되지
않으면 P8이 재발한다. 반대로 stale signal이나 count를 근거로 테스트 범위를
넓히면 P9 정보 오염이 된다.

## 판단

이 작업은 CPS P# 보강 문서 안에 둘 수 없다. pytest 효율과 회귀 라우팅은 실제
테스트 분포를 측정하고, `TestCommitFinalize` 실패 원인을 분리하며, memory/reminder
출력 계약까지 조정해야 닫힌다. 따라서 별도 wave로 분리한다.

Gemini CLI 검토(2026-05-19)는 이 wave의 본질이 "전체 pytest를 다시 끝까지
돌려 비효율을 증명"하는 것이 아니라, **AC가 요구한 marker/path만 실행하는
라우팅 원칙을 복원**하는 것이라고 봤다. 다만 `TestCommitFinalize`의 Windows/Git
Bash fixture 실패는 사용자의 "이번에 문제 해결" 지시에 따라 이번 wave 안에서
수정한다.

### C-P-S 매핑

| C | Primary P | 보조 P | S |
|---|-----------|--------|---|
| 전체 pytest가 wave 검증 기본값처럼 재등장 | P6 | P9 | S6, S9 |
| 과거 회귀 기록이 현재 marker 선택으로 이어지지 않음 | P8 | P6 | S8, S6 |
| PASS/FAIL/count/stale signal이 검증 범위를 오염 | P9 | P8 | S9, S8 |
| 느린 통합 fixture·환경 의존 테스트가 여러 케이스에 잠복 | P11 | P6 | S11, S6 |

**Acceptance Criteria**:

- [x] Goal: pytest 실행 기본값을 `AC가 요구한 marker/path`로 되돌리고, 전체
  pytest는 CI·eval·사용자 명시 요청 한정임을 현재 테스트 분포로 재확인한다.
  검증:
    review: self
    tests: marker별 pytest 측정 (gate/docs_ops/stage/enoent/secret/tag/review/eval)
    실측: marker별 실행 시간과 실패/skip 결과를 본문 `## 실측`에 기록.
      전체 pytest는 사용자 interrupt로 중단되어 결과로 쓰지 않음.
- [x] `hn_test_diet.md`의 2026-04-30 원칙과 2026-05-19 현재 실측 차이를
  비교한다.
- [x] `TestCommitFinalize` 실패가 실제 회귀인지 Windows/Git Bash fixture 문제인지
  분리하고, fixture 문제는 이번 wave에서 수정한다.
- [x] session-start/stop-guard 변경용 빠른 단위 테스트 또는 marker 후보를
  정한다.
- [x] memory/reminder 신호가 회귀 테스트 marker 선택을 돕는 최소 계약을
  정의한다. 단, memory count나 stale signal을 테스트 필요성의 단독 근거로
  쓰지 않는다.

## 실측

전체 pytest는 2026-05-19 측정 시 사용자 interrupt로 중단되어 결과로 쓰지
않는다. Gemini 검토에 따라 전체 실행 완료를 AC로 삼지 않는다.

| marker | 결과 | elapsed | 의미 |
|--------|------|---------|------|
| `gate` (수정 전) | 36 passed, 2 failed, 157 deselected | 25.48s | `TestCommitFinalize` 2건이 Windows/Git Bash alternates 경로 문제로 실패 |
| `gate` (수정 후) | 38 passed, 157 deselected | 29.39s | `finalize_repo`만 non-shared clone으로 바꿔 Windows/Git Bash alternates 문제 해소 |
| `docs_ops` | 39 passed, 156 deselected | 31.01s | marker 실행이어도 통합 fixture가 많아 무겁다 |
| `stage` | 2 passed, 4 skipped, 189 deselected | 1.54s | 빠른 stage 라우팅 후보 |
| `enoent` | 13 passed, 182 deselected | 1.05s | 빠른 정규식 회귀 가드 |
| `secret` | 5 passed, 190 deselected | 2.66s | 시크릿 패턴 회귀 가드 |
| `tag` | 33 passed, 162 deselected | 2.59s | 빠른 tag 정규화 회귀 가드 |
| `review` | 6 passed, 189 deselected | 1.90s | review verdict 파서 회귀 가드 |
| `eval` | 26 passed, 169 deselected | 3.11s | eval/docs_ops 일부 fixture 포함 |
| `orchestrator` | 29 passed, 166 deselected | 0.80s | marker 등록 후 warning 없이 통과 |

공통 경고였던 `pytest.mark.orchestrator` 미등록 warning 5건은 marker taxonomy
정합 문제이므로 `conftest.py`에 `orchestrator` marker를 등록해 해소한다.

### TestCommitFinalize 해결

`gate` marker 실패 2건이 있었다.

- `TestCommitFinalize::test_simple_commit_passes`
- `TestCommitFinalize::test_block_skips_wip_sync`

실패 원인은 동일하다.

```text
unable to normalize alternate object path:
.../.git/objects/D:\Work\Claude.AI\harness-starter/.git/objects
fatal: could not parse HEAD
```

이는 commit wrapper 동작 자체보다 Windows 임시 repo + Git Bash + alternates 경로
fixture 결합 문제였다. `test_pre_commit.py`의 `_clone_repo()`에 `shared` 옵션을
추가하고, `finalize_repo` fixture만 `shared=False`로 독립 clone을 쓰게 바꿨다.
다른 fixture는 기존 `--shared` 빠른 clone을 유지한다.

## 결정

1. 전체 pytest는 이 wave의 필수 실측이 아니다. CI·eval·사용자 명시 요청
   한정이라는 `hn_test_diet.md` 원칙을 유지한다.
2. marker도 무조건 빠르지 않다. `docs_ops` 31초, `gate` 29초처럼 통합 fixture가
   섞인 marker는 AC에 명시될 때만 실행한다.
3. session-start/stop-guard 변경에는 현재 전용 marker가 없다. 이 종류의 변경은
   우선 `eval` 또는 좁은 파일 단위 테스트를 후보로 삼고, 별도 빠른 단위 테스트
   신설은 실제 코드 변경 wave에서 판단한다.
4. memory/reminder의 최소 계약은 "실행 강제"가 아니라 "AC 작성 시 marker/path
   후보를 환기"다. 환기된 신호는 현재 코드·문서·git log와 재확인된 뒤에만
   AC `tests` 또는 `실측`에 들어간다.

## 측정 명령

```bash
python -m pytest .claude/scripts/tests/ -q -m gate --durations=10
python -m pytest .claude/scripts/tests/ -q -m docs_ops --durations=10
python -m pytest .claude/scripts/tests/ -q -m stage --durations=10
python -m pytest .claude/scripts/tests/ -q -m enoent --durations=10
python -m pytest .claude/scripts/tests/ -q -m secret --durations=10
python -m pytest .claude/scripts/tests/ -q -m tag --durations=10
python -m pytest .claude/scripts/tests/ -q -m review --durations=10
python -m pytest .claude/scripts/tests/ -q -m eval --durations=10
python -m pytest .claude/scripts/tests/ -q -m orchestrator --durations=10
```

## 범위 밖

- 이번 wave에서는 테스트 최적화 구현을 바로 하지 않는다.
- 전체 pytest 실패를 숨기지 않는다. 단, 실패를 본 변경의 검증 증거로도 쓰지
  않는다.
- memory/reminder는 테스트 선택 보조 신호일 뿐, 실행 범위의 단독 근거가 아니다.
