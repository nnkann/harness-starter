---
title: test-pre-commit 스위트 성능 — 잔여 구조 재설계
domain: harness
tags: [pre-check, test, perf, structure]
status: in-progress
created: 2026-04-22
updated: 2026-04-25
---

# test-pre-commit 스위트 성능 — 잔여 구조 재설계

2026-04-23 세션에서 단순 최적화(-40%)를 달성했으나, 남은 구간은 구조
재설계 없이는 의미 있는 개선이 어렵다. 본 WIP는 **다음 착수 조건과
방향만** 기록. 즉시 작업 대상 아님.

## 현재 실측 (2026-04-23 기준)

- **스위트 전체**: 91초 (date 명령 측정, Windows Git Bash 업스트림 repo)
- **pre-check 호출**: 42회 (run_case 50 - 캐시 히트 5 + 특수 2)
- **호출당 평균**: 2129ms (tmp clone 환경, 업스트림 리포 내 직접 실행의 ~2배)

**시간 분해**:
| 구간 | 비중 |
|------|------|
| pre-check 42회 실행 | ~90초 (99%) |
| reset / fixture 셋업 / 로그 출력 | ~1초 |

→ 스위트 시간의 99%가 pre-check 실행. 나머지 구간 최적화는 측정 noise
수준.

## 이번 세션 처리 완료 (2026-04-23)

| 버전 | 내용 | 실측 |
|------|------|------|
| v0.20.8 | task-groups 할당 루프 awk 통합 (파일당 fork 제거) | 151s → 124s |
| v0.20.9 | test-pre-commit fixture 캐시 (다중 key run_case 재실행 제거) | 124s → 98s |
| v0.20.10 | tmp → 리포 내 sandbox 디렉토리 | 98s → 91s |

**합계 -60초 (-40%)**. git history 조회: `git log --grep "(v0\.20\.(8\|9\|10))"`

## 롤백 (효과 없거나 diminishing)

- **pre-check NAME_STATUS 3 awk → 1 awk 통합**: 측정상 차이 없음
- **메타 흡수 2 awk → 1 awk NR==FNR 트릭**: 측정상 차이 없음
- **DOC_DOMAINS xargs 통합 + 등급 매핑 case 패턴**: 스위트 91초→91초
  (개별 pre-check은 noise 수준). 복잡도만 증가

공통 원인: pre-check 1회 2.1초 중 **고정 오버헤드**(bash 시작·git 3회 호출·
lint 감지)가 큼. 내부 awk·grep 호출 한두 개 줄여도 총합에서 묻힘.

## 남은 방향 (구조 재설계 필요)

### 1. 공유 fixture — 가장 효과 큰 방향

현재 reset × 45 = pre-check × 45. **T 케이스 여러 개가 같은 fixture를
공유하면 pre-check 1회만 실행**하고 여러 key 검증 가능.

- 예: T5~T10 모두 "S8 export 검출" 테스트 → 각자 fixture 만들지 말고 한
  fixture에서 여러 케이스 검증
- pre-check 호출 42 → ~15회까지 감소 가능
- **예상**: 91초 → 40~50초

**위험**: 테스트 간 의존성 생김, fixture 설계 난이도 상승. 실측 실패 시
격리 회복 어려움.

### 2. pre-check 자체 "테스트 모드" — diminishing 아님

pre-check 내부에 `TEST_MODE=1` 같은 환경변수 → lint 호출 skip, CLAUDE.md
파싱 skip, 외부 자료 조회 skip. 회귀 검증에 필요 없는 부분만 제거.

- **예상 절감**: pre-check 1회 2.1초 → 1.2초 수준
- **위험**: "테스트 때만 다른 경로" = 실제 환경 검증 못 함. pre-check
  자체 변경 시 테스트 모드와 실 모드 모두 확인 필요

### 3. 병렬화

이전에 사용자가 지적한 대로 증상 우회. 단, 공유 fixture와 결합하면
의미 있을 수 있음 (격리된 독립 그룹만 병렬).

## 착수 조건

- ~~스위트 시간이 **체감 장벽**이 될 때만. 현재 91초는 개발 중 1~2회 돌릴
  만한 수준~~ **→ 2026-04-25 체감 장벽 도달 확인. 케이스 67개로 증가 후
  사용자 "신경질 난다" 지적. 착수 조건 충족.**
- 프로파일링 재실행으로 2.1초가 여전히 유효한지 확인 (환경·OS·fs 변경
  가능성)
- 공유 fixture 재설계는 **전체 T 케이스 맵 작성** 선행 — 어느 T끼리 묶일
  수 있나

## 2026-04-25 재분석 (케이스 67개 기준)

performance-analyst 에이전트 실측:

| 항목 | 값 |
|------|-----|
| pre-check 실행 횟수 | ~44회 (reset → 캐시 미스) |
| no-staged 1회 | 1,356ms |
| staged 있을 때 1회 | 1,985ms (+task-groups.sh 629ms) |
| **추정 합계** | **68,000~94,000ms (1분 8초~1분 34초)** |
| git commit prep | 11회 × 300ms = 3,300ms |
| git clone sandbox | 990ms (고정) |
| reset() 47회 | ~2,350ms |

**핵심**: 스위트 시간의 99%가 pre-check 반복 실행 — 2023-04-23 분석과 동일.
T39 케이스 3개 추가로 ~44회로 증가 (이전 42회).

**신규 발견**: `task-groups.sh`가 staged 있을 때마다 호출됨 (+629ms/회).
테스트 환경에서 `HARNESS_SPLIT_SUB=1` 또는 별도 환경변수로 스킵 가능 여부
검토 필요.

**Windows Defender 개입** 가능성: bash fork + 파일 쓰기마다 50~200ms 추가.
측정값이 이를 이미 포함한 수치인지 환경 확인 필요.

## 2026-04-25 코드 구조 분석 (codebase-analyst, 68케이스 기준)

### 불합리한 공정 — 즉시 개선 가능

| 항목 | 위치 | 낭비 | 예상 절감 |
|------|------|------|---------|
| T4 이중 reset | L145-163 | git add 후 run_case 없이 즉시 reset — setup 비용만 소모 | ~0.3초 |
| T21-T24 통합 | L450-480 | `.claude/scripts·agents·hooks·settings.json` 각각 독립 실행. 모두 `deep` 결과 동일 → 1회 가능 | ~3.6초 |
| T25-T27 통합 | 동일 패턴 | `rules·skills·CLAUDE.md` 각각 독립 실행. 모두 `standard` → 1회 가능 | ~2.4초 |
| T13 이중 실행 | L273-291 | 같은 staged에서 pre-check 2회. T13.1이 PRECHECK_CACHE 미기록 → T13.2에서 재실행 | ~1.4초 |

**소계**: 즉시 개선만으로 **~7.7초** 절감 가능 (reset 5회 제거).

### new_func_lines 잔재 — 없음

`new_func_lines_b64` key는 pre-commit-check.sh에서 완전 제거 확인 (test-strategist 폐기, audit #7·#15). test-pre-commit.sh에도 없음. SKILL.md에 "제거됐다"는 언급만 잔존.

### T 케이스 번호 공백

T11·T12·T20·T29 — 주석만 남음. 성능 무관하지만 번호 맵 혼란 유발.

### T33·T34 ENOENT_PATTERN 드리프트 위험

L583-585의 `ENOENT_PATTERN`이 pre-commit-check.sh와 별도로 하드코딩. 패턴 변경 시 양쪽 수동 동기화 필요. 성능 무관, 유지보수 위험.

### 공유 fixture 가능 그룹 (구조 재설계 시)

| 그룹 | 케이스 | 통합 시 절약 |
|------|-------|------------|
| S8 양성 | T6·T8·T9 | 2회 |
| S8 음성 | T5·T7·T10 | 2회 |
| S5 skip | T4·T30 | 1회 |
| T36 통과 계열 | T36.1·T36.3·T36.4·T36.6·T36.7 | 구조 다름, 부분만 가능 |
| T39 skip 계열 | T39.1·T39.2·T39.4 | 2회 |

공유 fixture 전체 적용 시 44회 → ~15회, 추가 **~40초** 절감 가능 (단, fixture 설계 복잡도 상승).

## 2026-04-25 즉시 개선 적용 결과

fixture 통합 (T4·T5/T7/T10·T6/T8/T9·T13·T21-T24·T25-T27·T39.1/2/4):
- reset 횟수: 47 → 39회
- **실측: 139초 → 111초 (-28초, -20%)**
- 68/68 통과 유지

---

## 근본 재설계 (2026-04-25 확정)

### 문제 진단

현재 구조의 핵심 낭비:

| 항목 | 현재 | 비용 |
|------|------|------|
| pre-check 1회 | git diff 3회 + git log 1회 + task-groups.sh | 1,350ms |
| task-groups.sh | staged 있을 때 매번 호출 | +600ms/회 |
| git clone sandbox | 스위트 시작 시 1회 | 1,000ms |
| reset() × 39 | git reset + git clean | ~2,000ms |
| **총계** | | **~111초** |

테스트가 실제로 검증하는 것: `STAGED_NAME_STATUS`·`STAGED_DIFF_U0` 등을 입력으로 받는 **신호 감지·stage 판정 로직** (순수 텍스트 처리).

그런데 현재 테스트는 그 입력을 만들기 위해 **실제 git repo + staged 상태 + pre-check 전체 파이프라인**을 태운다. git log(S10)·task-groups.sh(split)는 대부분의 케이스에서 검증 대상조차 아닌데 매번 돌아간다.

### 재설계 방향: 입력 주입 (Input Injection)

pre-commit-check.sh의 git 입력 수집 부분을 **환경변수 폴백**으로 감싼다:

```bash
# 현재
STAGED_NAME_STATUS=$(git diff --cached --name-status 2>/dev/null)
STAGED_NUMSTAT=$(git diff --cached --numstat 2>/dev/null)
STAGED_DIFF_U0=$(git diff --cached -U0 2>/dev/null)

# 변경 후
STAGED_NAME_STATUS="${_TEST_NAME_STATUS:-$(git diff --cached --name-status 2>/dev/null)}"
STAGED_NUMSTAT="${_TEST_NUMSTAT:-$(git diff --cached --numstat 2>/dev/null)}"
STAGED_DIFF_U0="${_TEST_DIFF_U0:-$(git diff --cached -U0 2>/dev/null)}"
```

`TEST_MODE=1`이면 git log(S10)·task-groups.sh(split)도 skip:

```bash
# git log S10 (L375)
if [ "${TEST_MODE:-0}" = "1" ]; then
  RECENT_FILES=""
else
  RECENT_FILES=$(git log -${REPEAT_RANGE} --name-only --format= 2>/dev/null ...)
fi

# task-groups.sh (L757)
if [ "${TEST_MODE:-0}" != "1" ] && [ -x .claude/scripts/task-groups.sh ]; then
  GROUP_ASSIGN=$(bash .claude/scripts/task-groups.sh ...)
fi
```

테스트는 git clone·staged 상태 대신 변수만 주입:

```bash
# 현재 테스트 케이스
reset
mkdir -p src
echo "export function getUser() {}" > src/api.ts
git add src/api.ts
run_case "T6.1 export → S8 hit" "signals" "S8" must_match

# 변경 후
_TEST_NAME_STATUS="M src/api.ts" \
_TEST_DIFF_U0="+export function getUser() {}" \
TEST_MODE=1 \
run_case "T6.1 export → S8 hit" "signals" "S8" must_match
```

`run_case` 내부에서 환경변수를 설정하고 pre-check을 호출하는 구조.

### 예상 효과

| 항목 | 현재 | 재설계 후 | 절감 |
|------|------|---------|------|
| pre-check 1회 (TEST_MODE) | 1,350ms | ~150ms (git 0회·task-groups 0회) | -1,200ms |
| pre-check 39회 합계 | ~53,000ms | ~5,850ms | -47,000ms |
| git clone sandbox | 1,000ms | 0ms (불필요) | -1,000ms |
| reset() | ~2,000ms | 0ms (불필요) | -2,000ms |
| **예상 총계** | **111초** | **<10초** | **-101초 (-91%)** |

**검증 기준 (재설계 완료 시)**:
- 스위트 < 10초 (목표)
- 68/68 통과 유지
- git log·task-groups 경로(S10·split)는 별도 통합 테스트로 분리 보존

### 단계적 실행 계획

1. pre-commit-check.sh: `_TEST_NAME_STATUS`·`_TEST_NUMSTAT`·`_TEST_DIFF_U0` 환경변수 폴백 추가 ✅
2. pre-commit-check.sh: `TEST_MODE=1` 시 git log·task-groups.sh skip ✅
3. test-pre-commit.sh: `run_case`를 변수 주입 방식으로 전환. git clone·sandbox 제거 ✅
4. S10·split 검증 케이스(T13·T39.4)는 실제 git 경로 유지 (통합 테스트 구간으로 분리)
5. 실측 시간 측정 + 검증 기준 대조

### 위험

- pre-commit-check.sh 변경이 실 운영 경로에 영향 없어야 함 — 환경변수 미설정 시 기존 동작 그대로 ✅
- `_TEST_*` 변수 미설정 케이스에서 git 명령이 정상 동작하는지 확인 필요
- T14·T15·T33·T34는 pre-check 호출 없는 인라인 로직 — 현행 유지

## 2026-04-25 재설계 실행 결과

### 구현 내용

- `pre-commit-check.sh`: `_TEST_NAME_STATUS`·`_TEST_NUMSTAT`·`_TEST_DIFF_U0` 환경변수 폴백 추가. `TEST_MODE=1` 시 git log·task-groups.sh skip. ✅
- `test-pre-commit.sh`: 단위 테스트 구간(변수 주입) + 통합 테스트 구간(실제 git) 분리. ✅

### 실측

| 항목 | 예상 | 실측 |
|------|------|------|
| 단위 pre-check 1회 | ~150ms | **~2,000ms** |
| 스위트 전체 | <10초 | **102초** |
| 68/68 통과 | ✅ | ✅ |

### 예상값 미달 원인

**Windows Git Bash fork 오버헤드**가 근본 원인. `TEST_MODE=1`로 git 4회·task-groups.sh를 제거해도 pre-check 내부에 awk·grep·sed·sort 등 subprocess가 수십 번 fork됨. Windows에서 각 fork가 50~150ms → 합산 ~1,500ms 고정 오버헤드.

- Linux/macOS 동일 스크립트: ~50ms
- Windows Git Bash: ~2,000ms (40배 차이)

통합 테스트 구간(T13·T35·T36·T38·T39)도 git repo + git 명령 ~20회 → ~80초.

### 남은 병목

| 구간 | 시간 | 제거 방법 |
|------|------|---------|
| 단위 pre-check 39회 | ~78초 | pre-check을 Python/Node로 재작성 |
| 통합 테스트 git | ~24초 | dead link·S10 검증 최소화 또는 별도 스크립트 분리 |

### 근본 해결 방향 — 확정: Python 완전 재작성

bash subprocess fork 오버헤드는 Windows 환경에서 스크립트 수준으로 해결 불가.

**실측 기반 Python 비용 (2026-04-25)**:

| 항목 | 값 |
|------|-----|
| `python3` 프로세스 시작 | 76ms |
| git subprocess 1회 | 13ms |
| 순수 신호 로직 | 0.002ms (무시) |

**방향별 예상**:

| 방향 | 1회 | 스위트 68케이스 | 비고 |
|------|-----|----------------|------|
| Python 완전 재작성 | ~120ms (시작76 + git×3 39) | **~8초** | 드리프트 없음, 실 운영도 빠름 |
| 하이브리드 (테스트만 Python) | <1ms (시작 1회 공유) | **<1초** | bash/Python 드리프트 위험 |
| WSL | ~50ms | ~5초 | WSL 설치 필요, 사용 안 함 |

**채택: Python 완전 재작성**. 하이브리드가 더 빠르지만 bash·Python 두 구현 드리프트 시 테스트가 거짓 통과 — 유지보수 부채가 더 크다. 완전 재작성 시 실 운영도 8초 → ~120ms/커밋으로 빨라지는 부가 효과.

재작성 범위:
- `pre-commit-check.sh` → `pre_commit_check.py` (신호 감지 + stage 결정)
- git 호출(numstat·name-status·diff·log)은 Python subprocess 유지
- bash-guard·hook·commit 스킬 호출 구조는 그대로
- 기존 `.sh`는 fallback 또는 제거 (결정 미완)

## 2026-04-25 (C) fork 최소화 시도 결과

### 적용 내용

top 3 fork 감소 타겟:

1. **S10 루프** (L399-430): `while + grep-cFx` N×1 forks → awk 1패스 hash 조회 + sentinel 분리
2. **S9 섹션** (L556-603): `while read + grep + sed` 루프 → awk getline 1패스 + 연관 배열 등급 조회
3. **룰 3 이동 커밋 감지** (L717-720): `grep -c + grep -v + wc -l + grep -c` (8 forks) → awk 1패스

### 실측

| 항목 | 이전 | 이후 |
|------|------|------|
| pre-check 1회 | 1,414ms | **1,414ms** (변화 없음) |
| 스위트 전체 | 102초 | **80초** |
| 68/68 통과 | ✅ | ✅ |

### 원인 분석

스위트 시간은 22초 감소했으나 **단일 pre-check 호출 시간은 변화 없음**.

프로파일링(`PS4='$(date +%s%3N) '` trace) 결과:
- 모든 라인 (bash `[`, 변수 할당 포함)이 **85~155ms** baseline 가짐
- `grep -qiE` 185ms가 가장 큰 단일 호출
- fork 제거가 효과 없는 이유: bash 인터프리터 자체 오버헤드 (라인 실행 비용) + Windows Git Bash 환경 = 로직 최소화해도 하한 존재

즉, awk로 fork를 줄여도 **bash가 그 라인을 실행하는 비용 85ms 자체가 없어지지 않음**.

### 결론

(C) fork 최소화는 스위트 전체 시간에서 22초를 절감했으나(테스트 반복 실행 내 누적 효과) pre-check 단위 시간 개선은 없음. bash 인터프리터 오버헤드가 진짜 하한.

**추가 bash 최적화로 얻을 수 있는 최대**: 5~10초 추가 절감 (diminishing returns 구간).

### 근본 해결 방향 (재확인)

1. **WSL (A)**: 기존 bash 스크립트 그대로, Linux에서 실행. fork 50ms → 스위트 ~10초 예상.
2. **Python 재작성**: fork 0, 스위트 ~1초. 재작성 비용이 문제.

## Python 완전 재작성 설계 (2026-04-25 확정)

### 재작성 범위

**병목은 `pre-commit-check.sh` 단 하나** — 커밋마다 1회, 테스트에서 68회 호출.
나머지 스크립트(`bash-guard.sh`, `docs-ops.sh`, `split-commit.sh` 등)는 커밋당 1~2회로
오버헤드가 문제되지 않으므로 **그대로 유지**.

```
재작성:  pre-commit-check.sh  →  pre_commit_check.py
전환:    test-pre-commit.sh   →  test_pre_commit.py   (pytest)
유지:    bash-guard.sh, docs-ops.sh, split-commit.sh,
         harness-version-bump.sh, task-groups.sh 등 전부
```

### 파일 구조

```
.claude/scripts/
├── pre_commit_check.py      ← 신규 (신호 감지 + stage 결정 — 전체 로직)
├── pre-commit-check.sh      ← 래퍼만 남김 (py 호출 위임)
└── test_pre_commit.py       ← 신규 (pytest 기반 테스트)
```

`pre-commit-check.sh` 최종 형태:
```bash
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/pre_commit_check.py" "$@"
```

bash 로직 전부 `pre_commit_check.py`로 이전. 래퍼 외 `.sh` 내용은 삭제.

### 입력 (pre_commit_check.py)

Python subprocess로 git 호출:
```python
name_status = run(["git", "diff", "--cached", "--name-status"])
numstat     = run(["git", "diff", "--cached", "--numstat"])
diff_u0     = run(["git", "diff", "--cached", "-U0"])
recent_files = run(["git", "log", f"-{REPEAT_RANGE}", "--name-only", "--format="])
```

환경변수 폴백 유지 (`_TEST_NAME_STATUS` 등) — 통합 테스트용.

### 출력 (stdout 스키마 — 기존과 동일 유지)

```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: ...
diff_stats: files=N,+A,-D
signals: S1,S2,...
domains: harness
domain_grades: critical
multi_domain: false
repeat_count: max=N
recommended_stage: skip|micro|standard|deep
s1_level: |file-only|line-confirmed
split_plan: N
split_action_recommended: single|split|sub
prior_session_files: ...
```

commit 스킬·hook이 stdout을 파싱하므로 **키·순서·형식 변경 금지**.

### 테스트 전환 (test-pre-commit.sh → test_pre_commit.py)

```python
# pytest 기반, 변수 주입으로 git 불필요
def run_check(name_status="", numstat="", diff_u0="", **env):
    result = subprocess.run(
        ["python3", "pre_commit_check.py"],
        env={**os.environ, "_TEST_NAME_STATUS": name_status,
             "_TEST_NUMSTAT": numstat, "_TEST_DIFF_U0": diff_u0,
             "TEST_MODE": "1", **env},
        capture_output=True, text=True
    )
    return parse_output(result.stdout)

def test_s8_export_hit():
    out = run_check(
        name_status="M\tsrc/api.ts",
        diff_u0="diff --git a/src/api.ts b/src/api.ts\n+export function getUser() {}"
    )
    assert "S8" in out["signals"]
```

git clone·sandbox·reset 전부 제거. `python3` 시작 1회 76ms + 로직 0ms = 케이스당 ~80ms.

### 실행 계획

- [ ] 1. `pre_commit_check.py` 작성 — 신호 감지(S1~S15) + stage 결정
- [ ] 2. stdout 스키마 동등성 검증 — 기존 `.sh`와 동일 출력 확인
- [ ] 3. `test_pre_commit.py` 작성 — 68케이스 pytest 전환
- [ ] 4. `pre-commit-check.sh` → py 위임 래퍼로 교체
- [ ] 5. `test-pre-commit.sh` 제거 (또는 보존 여부 결정)
- [ ] 6. 스위트 시간 측정 + 검증 기준 대조

### 예상 검증 기준

| 항목 | 현재 | 목표 |
|------|------|------|
| 스위트 전체 | 80초 | **< 10초** |
| 케이스 | 68/68 | 68/68 유지 |
| pre-check 1회 | 1,414ms | ~120ms |
| stdout 스키마 | bash | Python (동일 포맷) |

## 영향 파일

- 주: `.claude/scripts/test-pre-commit.sh` (구조) ✅ → `test_pre_commit.py`로 전환 예정
- 보조: `.claude/scripts/pre-commit-check.sh` (입력 주입 폴백·TEST_MODE, fork 최소화) ✅ → py 래퍼로 교체 예정
- 신규: `.claude/scripts/pre_commit_check.py`
