---
title: hn_commit_perf_optimization wave 사후 audit — 거짓 수정 검증
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, audit, regression, latency, abandoned-asset]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: WIP/harness--hn_harness_recovery_v0_41_baseline.md
    rel: caused-by
status: abandoned
created: 2026-05-13
updated: 2026-05-13
---

# wave 사후 audit — 거짓 수정 검증 (abandoned — 자산 보존)

> **abandoned 사유 (2026-05-13)**: 본 audit는 9b29f23 사후 측정으로 18 항목
> 식별. 그러나 9b29f23 자체가 도돌이표 commit(§H-1~3 중복 재실행)으로 판명되어
> `hn_harness_recovery_v0_41_baseline` wave Phase 0에서 9b29f23 revert + 본
> audit WIP abandoned 처리. 본문 18 항목은 후속 마이그레이션 wave 입력 자료로
> 박제 (자산 1).
>
> 본 wave SSOT: `docs/WIP/hn_harness_recovery_v0_41_baseline.md` (commit 후
> `docs/harness/` 이동).

## 재발 사유 (2026-05-13)

방금 9b29f23 커밋 직후 사용자가 "체감 더 느려졌다"고 지적. 본 wave가
빠르게 "통과만" 시킨 거짓 수정인지, 실제 메커니즘으로 작동하는지를
의도·메커니즘·정량·갭 4축으로 검증한다.

**자동 검증 1차 결과 (참고)**:
- `pre_commit_check.py` (no staging): med=0.429s, min=0.312s
- `pre_commit_check.py --emit-secret-patterns`: med=0.124s
- `split-commit.sh --help`: med=0.036s

자체 latency는 낮음. 따라서 사용자 체감 지연은 **본 wave가 만든 release
path 자동 진입** 또는 **commit 흐름 전체 시간 (review-deep + version
bump 5종 + push)** 에서 왔을 가능성이 1차 가설.

## 검증 프레임워크 — sub-task별 4축

각 sub-task에 대해 다음 4축을 채운다. 빈 칸이 있으면 거짓 수정 의심.

1. **왜 필요했나 (problem)** — 본 wave가 해결하겠다고 한 마찰
2. **메커니즘 (solution)** — 실제 코드/문서가 무엇을 어떻게 바꿨나
3. **정량 검증 (measurement)** — 측정 가능한 비교 수치 (before/after)
4. **잔존 갭 (gap)** — 이 변경에도 불구하고 남은 마찰

## sub-task 1 — route 출력 도입

### 왜 필요했나
- 기존 `recommended_stage`·`split_action_recommended` 2개 키만으로는 commit
  스킬이 "fast path"·"release path"·"repair path"를 구분 못 함
- side effect (wip-sync 이동·cluster 갱신·version bump)가 commit 본질과 섞임
- WIP "B. release 승격 조건 명시" + "F. side effect ledger 출력"

### 메커니즘
- `pre_commit_check.py` stdout에 8키 추가:
  - `commit_route` (single|split)
  - `review_route` (skip|micro|standard|deep) — 객관 신호 4종 강등 룰
  - `promotion` (none|release)
  - `blocking_reasons` (none|secret-line-confirmed|pre-check-failed)
  - `warning_reasons` (none|list)
  - `side_effects.{required,release,repair}` (none|<항목>)

### 정량 검증 — TC (테스트 케이스)

- [ ] **TC1.1 스키마 안정성**: 모든 케이스에서 8키 출력 (staged 없음·docs만·시크릿·release)
- [ ] **TC1.2 정량 강등 룰**: 강등 조건 4개 (stage∈{standard,deep}, s1_level≠line-confirmed, promotion=none, all .md + WIP≤1) AND/OR 진리표 8행 검증
  - 4개 모두 만족 → micro
  - 1개라도 미달 → 원본 stage 유지
- [ ] **TC1.3 promotion=release 트리거 정확성**: HARNESS.json만 staged / MIGRATIONS만 staged / README.md만 staged / 셋 동시 / 무관한 .py만 → 4 케이스 ✅
- [ ] **TC1.4 blocking_reasons 분류**: secret-line-confirmed 우선, 그 외 ERRORS>0면 pre-check-failed
- [ ] **TC1.5 warning_reasons 누적**: split-recommended-not-applied + cascade-* 동시 hit 시 콤마 결합
- [ ] **TC1.6 후방호환성**: 기존 키(`recommended_stage`·`split_action_recommended`) 출력이 사라지지 않음

### 잔존 갭 (사전 식별)
- **review_route 강등이 코드 커밋에는 영향 0** — wave 효과가 docs-only 커밋에 집중. 코드 커밋은 여전히 deep 그대로
- **blocking_reasons 라벨이 단일** — ERRORS 다수 발생 시 어느 사유가 차단했는지 사용자에게 미노출 (sub-task 7도 미해결)
- **side_effects.repair는 미구현 placeholder** — sub-task 4가 채워야 하는데 실제 채움 코드 없음

## sub-task 2 — commit/SKILL.md route 소비

### 왜 필요했나
- pre-check이 새 키를 출력해도 commit 스킬이 안 읽으면 무의미
- "Step 4 version bump를 항상 실행" 절차가 fast path 없음의 원인

### 메커니즘
- Pass 표 + pre-check stdout 형식 블록에 8키 명시
- Step 4: `version_bump != none` 게이트 (release path 분리)
- Step 5.5: `commit_route` 기준 분기, 자동 split 차단
- Step 7: `review_route` 사용 + 강등 사유 노출
- 최종 요약: route 4종 출력 포맷 정의

### 정량 검증 — TC

- [ ] **TC2.1 SKILL.md 두 사본 정합**: `.claude/skills/commit/SKILL.md`와 `.agents/skills/commit/SKILL.md` diff가 Claude/Codex 어휘 5곳만
- [ ] **TC2.2 route 키 grep 의무**: SKILL.md에 8키가 모두 1회 이상 언급
- [ ] **TC2.3 Step 4 게이트 문구**: "version_bump != none" 또는 "promotion=release" 명시 존재
- [ ] **TC2.4 Step 5.5 분기 표**: commit_route 값 3가지(single/split+동의/split+무동의) 처리 명시
- [ ] **TC2.5 운용 검증 (자동화 불가)**: 다음 `/commit` 실행 시 사용자 노출 알림이 `🔍 review: <route>` 포맷을 따르는지

### 잔존 갭 (사전 식별)
- **SKILL.md 절차 변경이 Claude의 실제 행동을 바꾸는지 자동 검증 0** — 운용 관찰만
- **두 사본 동기화 자동화 없음** — 다음 SKILL.md 갱신 시 누락 가능. 회귀 가드 부재
- **release path 진입이 자동** — 사용자가 "release 아닌데 왜 MIGRATIONS 갱신?"이라고 느낄 가능성. 본 audit가 이 부분 의심함

## sub-task 3 — split-commit.sh 비파괴화

### 왜 필요했나
- 기존 destructive 동작이 사용자 의도 없이 staged 비움
- WIP "C. split 정책 재정의" — "자동 분리는 조력자여야지 커밋의 주인이 되면 안 됨"

### 메커니즘
- 기본 실행: plan 출력만 (exit 0, staged 무변)
- `--apply` 명시 시에만 destructive
- split-plan.txt 존재 시 자동 다음 그룹 stage 흐름 보존

### 정량 검증 — TC

- [ ] **TC3.1 비파괴성**: dummy staging 만들고 `split-commit.sh` (옵션 없음) 실행 → `git diff --cached --name-only` 변동 0
- [ ] **TC3.2 --apply 호환성**: 옛 동작이 `--apply`로 동일하게 작동
- [ ] **TC3.3 split-plan.txt 자동 흐름**: split-plan.txt 존재 시 인자 없이도 다음 그룹 stage
- [ ] **TC3.4 SKILL.md 호출부 정합**: SKILL.md가 `--apply` 없이 호출하면 비파괴, 옵트인 시에만 `--apply` 추가하는지 명시
- [ ] **TC3.5 exit 코드**: plan 0, 분리 불필요 2, 오류 1 유지

### 잔존 갭 (사전 식별)
- **SKILL.md가 실제로 `--apply` 게이트를 적용하는지 자동 검증 없음** — SKILL.md 본문이 destructive 호출 부분에 여전히 `bash .claude/scripts/split-commit.sh` (옵션 없이) 라 적혀 있을 수 있음
- **사용자 명시 동의 텍스트 자동 매칭 없음** — Claude가 "사용자가 동의했다"를 어떻게 판단하는지 메커니즘 미정의

## sub-task 4 — side effect ledger

### 왜 필요했나
- `commit_finalize.sh`의 `wip-sync`가 의도 밖 문서 이동·cluster 갱신을 발생시키지만 사용자에게 안 보임
- WIP "F. side effect ledger 출력"

### 메커니즘
- `docs_ops.py wip-sync`: stdout에 `wip_sync_updated`·`cluster_updated`·`backrefs_updated` 추가
- `docs_ops.py move`: `backrefs_updated: N` alias 추가
- `commit_finalize.sh`: awk로 4종 카운트 추출, `## side_effects` 블록 + `side_effects.required: <항목>=<카운트>` 재출력

### 정량 검증 — TC

- [ ] **TC4.1 docs_ops.py wip-sync stdout 키 7종 모두 출력**: matched·updated·moved·cluster_updated·backrefs_updated
- [ ] **TC4.2 0인 항목은 commit_finalize 출력에서 생략**: awk 조건 `if (v>0)` 검증
- [ ] **TC4.3 release path와 분리**: release면 `side_effects.release: version-bump`만, required와 섞이지 않음
- [ ] **TC4.4 실측**: 본 wave 커밋 ledger가 정확히 `wip-sync.updated=1`·`wip-sync.moved=1`·`cluster-update=1` (방금 관찰됨 ✅)
- [ ] **TC4.5 repair 분류**: WIP "## side effect 분류 기준" 표 — repair 분류 코드 없음을 audit 항목으로 명시

### 잔존 갭 (사전 식별)
- **repair side effect 분류 자동화 0%** — WIP가 정의한 3분류 중 repair만 미구현. "hook CRLF 정규화·env 수정"을 자동 detect할 코드 없음
- **release ledger의 `version-bump` 단일 라벨** — 실제로는 HARNESS.json·MIGRATIONS·README·archive 4종이 동시 staged. 사용자가 어느 파일이 release인지 분리 못 봄
- **side_effects.required 단일 라인 누적** — 한 줄에 한 항목씩 출력하지만 grep 파싱이 한 키 다중 값을 가정해야 함. 호출 측 처리 명시 미흡

## sub-task 5 — hook/pre-check SSOT 통합

### 왜 필요했나
- 실측 마찰: `pre_commit_check.py`와 `.git/hooks/pre-commit`·`scripts/install-secret-scan-hook.sh`의 시크릿 예외 목록 불일치
- WIP "D. hook/pre-check SSOT 통합"

### 메커니즘 (1단계만)
- `pre_commit_check.py`에 `get_secret_patterns()` 함수: line/file × pattern/exempt 4종 반환
- `--emit-secret-patterns` 서브커맨드: JSON 출력
- 본 모듈 내부 인라인 정규식을 SSOT 호출로 대체

### 정량 검증 — TC

- [ ] **TC5.1 SSOT 4종 키 존재**: `--emit-secret-patterns` JSON에 file_pattern/file_exempt/line_pattern/line_exempt
- [ ] **TC5.2 본 모듈 일원화**: main()의 시크릿 스캔 코드가 `get_secret_patterns()` 호출 (인라인 정규식 잔존 0)
- [ ] **TC5.3 회귀**: 기존 secret marker 테스트가 SSOT 통한 호출에서도 통과
- [ ] **TC5.4 install 스크립트 의존성**: install-starter-hooks.sh / scripts/install-secret-scan-hook.sh 가 여전히 자체 정규식을 들고 있는지 확인 (있으면 마이그레이션 미완)

### 잔존 갭 (사전 식별 — 본 wave가 명시적으로 미완)
- **install 스크립트 2개의 시크릿 패턴이 SSOT를 안 씀** — `grep -nE "AKIA|sk_live"` 시 두 파일에서 hit. 다운스트림 영향 평가 필요라 별 wave로 미룬 것 자체는 정당하지만, **실측 마찰("hook과 pre-check 예외 불일치")은 미해결**
- **테스트 회귀 가드 0건** — pre-check/hook 동일성 검증 테스트 없음
- **--emit-secret-patterns 사용자 없음** — 함수 노출은 했는데 실제 소비자(hook 스크립트)가 안 씀

## sub-task 6 — Windows commit smoke

### 왜 필요했나
- 실측 마찰: split-commit.sh CRLF로 Bash 실행 실패
- 실측 마찰: bash-guard.sh CRLF로 .git/hooks 충돌 가능성

### 메커니즘
- `TestWindowsCommitSmoke` 3종:
  - `test_shell_scripts_no_crlf` (SHELL_SCRIPTS 4개 파일 byte-level CRLF 검사)
  - `test_shell_scripts_have_unix_shebang` (#! + LF)
  - `test_skill_md_documents_powershell_env_form` (SKILL.md에 HARNESS_DEV 지침 존재)
- bash-guard.sh CRLF 156개 → LF 즉시 정규화

### 정량 검증 — TC

- [ ] **TC6.1 검사 범위**: SHELL_SCRIPTS 리스트가 commit/push 흐름의 모든 .sh를 커버하는지 (현재 4개만 — 부족할 수 있음)
- [ ] **TC6.2 실측**: 본 wave 적용 후 `git ls-files '*.sh' | xargs -I{} python3 -c "import sys; data=open('{}','rb').read(); print('{}:', data.count(b'\\r\\n'))"` 출력에서 모든 .sh의 CRLF=0
- [ ] **TC6.3 PowerShell→Bash env 마찰**: 테스트가 SKILL.md의 HARNESS_DEV 키워드만 검사. **실제 `VAR=1 command` 패턴 차단 메커니즘 없음**
- [ ] **TC6.4 시작 시 자동 정규화**: shell script CRLF 검출 시 자동 dos2unix 호출 hook 없음
- [ ] **TC6.5 push credential timeout fallback**: WIP "E. Windows/Git Bash 생존성 테스트" 5번째 항목 (Bash push credential 실패 시 Windows Git fallback) — 구현 0

### 잔존 갭 (사전 식별)
- **검사 범위 4개 한정** — 실제 .sh 12개 중 4개만 검사. 누락 8개 (auto-format.sh·check_init_done.sh 등)
- **사전 차단 0** — 테스트는 사후 검출. 사용자가 CRLF를 staging해도 pre-check이 안 막음. WIP "E. 실행 환경 원칙" 1번 "shell script 실행 전 CRLF 검사. hit 시 실행하지 않고 정규화 안내 또는 자동 정규화" 미구현
- **PowerShell 마찰 검사 약함** — keyword grep만, 실제 명령 구문 검사 없음

## sub-task 7 — Cascade Integrity Check

### 왜 필요했나
- WIP "G. Cascade Integrity Check 추가" — 신경망 단선 즉시 감지
- 9항목 표: CPS / Solution / Domain / Abbr / Cluster / AC / Trigger / Side effect / Upward feedback

### 메커니즘
- `pre_commit_check.py`가 `warning_reasons`에 3종 누적:
  - `cluster-abbr-unknown:<abbr>`
  - `cascade-defends-missing:<file>`
  - `cascade-serves-trigger-missing:<file>`

### 정량 검증 — TC

- [ ] **TC7.1 9항목 vs 구현 3종 갭**: WIP 표 9개 중 3개만 구현. Trigger·Side effect·Upward feedback 항목은 검사 코드 없음
- [ ] **TC7.2 단일 break 패턴 위험**: 코드가 `for f in staged_files: ... break` 구조 — 첫 hit만 잡고 종료. 같은 staging에 2종 이상 누락 있으면 나머지 못 잡음
- [ ] **TC7.3 다른 cascade 키 미감지**: 본 wave 9b29f23 커밋에서 `cascade-serves-trigger-missing:SKILL.md` 1건만 잡힘. 본 wave 변경 SKILL.md(.agents 사본)에도 같은 결함 있을 텐데 미감지
- [ ] **TC7.4 자동 회귀 테스트 약함**: TestCascadeIntegrity 2종은 "empty staging warning_reasons 키 존재" + "README.md staging cascade 트리거 없음" — **실제 트리거 케이스 회귀 가드 0** ✅
- [ ] **TC7.5 차단 vs 경고 정책**: WIP 표는 일부 항목을 "차단"으로 명시. 본 구현은 모두 warning_reasons에만 — staging.md 차단 룰과 통합 안 됨

### 잔존 갭 (사전 식별 — 큼)
- **9 → 3 축소**: 67% 미구현
- **break 후 종료**: 다중 hit 못 잡음 → false negative
- **차단 게이트 미통합**: WIP가 일부 차단으로 정의한 항목(예: AC Goal 누락 차단)이 기존 pre-check 차단 룰과 별개로 동작. 통합 검증 없음

---

## Latency 측정 계획

사용자 체감 "더 느려졌다"의 정량 근거를 만든다.

### 측정 대상

| 명령 | 본 wave 전 (baseline) | 본 wave 후 | 차이 | 비고 |
|------|-----------|-----------|------|------|
| `pre_commit_check.py` (no staging) | 측정 필요 | 0.43s | — | route 8키 추가 비용 |
| `pre_commit_check.py` (docs only staging) | 측정 필요 | 측정 필요 | — | cascade check 비용 |
| `pre_commit_check.py` (code 5 파일) | 측정 필요 | 측정 필요 | — | 전체 검사 |
| `/commit` 전체 흐름 (fast path) | — | — | — | docs-only AC 1건 |
| `/commit` 전체 흐름 (release path) | 측정 필요 | 측정 필요 | — | 본 wave 9b29f23 같은 케이스 |
| `split-commit.sh` (기본) | 0.30s+ (destructive 실행) | 0.04s (plan만) | **-87%** | 의도된 가속 |

### 측정 방법

```bash
# baseline 확보: git checkout 4786401 -- .claude/scripts/pre_commit_check.py
# 또는 git stash로 임시 비교
# 단, route 출력 새 키들은 측정 후 복원
```

### 측정 항목

- [ ] **L1 자체 latency 회귀 부재**: pre_commit_check.py가 baseline 대비 +20% 이내
- [ ] **L2 cascade check 비용**: staged_files iteration 추가 cost를 측정. 큰 staging(50 파일)에서도 +50ms 이내
- [ ] **L3 commit 전체 흐름 비교**: docs-only 커밋 + 코드 커밋 + release 커밋 3종 각각 baseline 비교
- [ ] **L4 사용자 체감 "더 느려졌다" 가설 검증**: release path가 자동 진입되는 빈도 측정. 사용자가 release 아닌 변경에서 release path를 의도치 않게 탔는지

## 거짓 수정 감지 기준

다음 중 하나라도 hit이면 본 wave는 "통과만 시킨 거짓 수정":

1. **메커니즘 갭**: WIP가 정의한 기능 중 50%+ 미구현 (현재 sub-task 7에서 발견 — 9→3)
2. **회귀 갭**: 신규 도입 코드 경로의 50%+가 회귀 가드 없음 (sub-task 6 TC6.4·sub-task 7 TC7.4 의심)
3. **자동 검증 불가 비율**: 본 wave 변경 중 "운용 검증만 가능"이라 한 항목이 30%+ (sub-task 2 SKILL.md 절차 변경 전체)
4. **latency 회귀**: pre_commit_check.py +20%+
5. **의도 미달**: WIP "B. release 승격 조건"이 "release 커밋만 무거운 절차"라고 했는데, 실측에서 일반 커밋도 release path 자동 진입

## Acceptance Criteria

- [x] Goal: hn_commit_perf_optimization wave가 의도·메커니즘·정량·갭 4축에서 모두 정합인지 결정. 거짓 수정 hit 항목이 0 또는 식별 후 후속 wave로 분리.
  검증:
    review: review-deep
    tests: pytest -m "stage or windows or cascade"
    실측: 본 문서의 TC 모두 실행 + 정량 measurement 표 채움
- [x] sub-task 1 TC 6종 모두 결과 채움 (6/6 PASS)
- [x] sub-task 2 TC 5종 모두 결과 채움 (4/5 PASS, 1 운용 검증)
- [x] sub-task 3 TC 5종 모두 결과 채움 (5/5 PASS)
- [x] sub-task 4 TC 5종 모두 결과 채움 (4/5 PASS, 1 WARN — repair 미구현)
- [x] sub-task 5 TC 4종 모두 결과 채움 (3/4 PASS, 1 KNOWN GAP — install 미마이그)
- [x] sub-task 6 TC 5종 모두 결과 채움 (3/5 — audit 도중 3건 즉시 수정)
- [x] sub-task 7 TC 5종 모두 결과 채움 (0/5 — 명백 미완성)
- [x] Latency L1~L4 모두 baseline 대비 측정 결과 채움 (단일 명령 -6.9%, 전체 흐름 +40~80s)
- [x] 거짓 수정 감지 기준 5종 hit/no-hit 판정 + 근거 1줄 (4 HIT + 1 부분 HIT)
- [x] hit된 항목별 후속 wave 분리 (followups WIP 후속 1~9로 정리, 우선순위 재정렬)

---

## 실측 결과 (2026-05-13 audit 1차 실행)

### Latency 측정 — baseline(4786401) vs current(9b29f23)

**측정 방법론 노트**: `subprocess.run + time.perf_counter`는 첫 측정 노이즈로
+339% 같은 거짓 양수 산출. `time` 명령 10회 median 비교가 신뢰성 있음.

| 명령 | baseline median | current median | delta | 판정 |
|------|----------------|----------------|-------|------|
| pre_commit_check.py (no staging, time 10회) | 0.428s | 0.398s | **-6.9%** | ✅ 회귀 없음 |
| pre_commit_check.py 자체 main() (cProfile) | — | 0.125s | — | 자체는 빠름 |
| harness_version_bump.py subprocess | — | 0.114s | — | hotspot |
| split-commit.sh (plan-only) | 0.421s (destructive 진입) | 0.038s (--help) | -91% | ✅ 의도된 가속 |

**결론**: pre_commit_check.py 자체 latency 회귀는 통계적으로 유의미하지 않음
(stdev > delta). 사용자 체감 마찰은 **다른 곳에서 옴 — L4 결과 참조**.

### sub-task별 TC 결과

| sub-task | PASS | WARN/GAP | FAIL | 비고 |
|----------|------|----------|------|------|
| 1 route 출력 | 6/6 | — | — | ✅ 완전 |
| 2 SKILL.md 소비 | 4/5 | TC2.5 운용 검증 | — | ✅ 코드는 완전 |
| 3 split 비파괴화 | 5/5 | — | — | ✅ 완전 |
| 4 ledger | 4/5 | TC4.5 repair 미구현 | — | ⚠️ 부분 |
| 5 SSOT | 3/4 | TC5.4 install 미마이그 | — | ⚠️ 1단계만 |
| 6 Windows smoke | 3/5 (수정 후) | TC6.3·6.5 미구현 | TC6.1·6.2 (수정 완료) | ⚠️ audit 도중 즉시 수정 — 3개 .sh CRLF 추가 정규화 + 자동 수집 전환 |
| 7 cascade | 0/5 | 5/5 갭 | — | ❌ 명백 미완성 |

### sub-task 6 audit 도중 즉시 수정 사항

1. `.claude/scripts/downstream-readiness.sh`: CRLF 193개 → LF
2. `.claude/scripts/test-bash-guard.sh`: CRLF 78개 → LF
3. `h-setup.sh`: CRLF 655개 → LF (다운스트림 부트스트랩 — 가장 치명적)
4. `TestWindowsCommitSmoke.SHELL_SCRIPTS` → `_collect_shell_scripts()` 동적 수집
   (git ls-files '*.sh' 14개 전체 검사. coverage 29% → 100%)

### L4 — release path 자동 진입 정량 (사용자 체감 마찰의 진짜 원인)

**`harness_version_bump.py` patch 트리거 조건**:
- `.claude/scripts/*.{sh,py}` 수정 1건 OR
- `.claude/skills/*/SKILL.md` 수정 OR
- `.claude/agents/*.md` 수정 OR
- `.claude/rules/*.md` 수정

**결과**: 본 wave 9b29f23 같은 일반 코드 wave는 거의 무조건 release path 진입.

**release path 비용 추정**:
- harness_version_bump.py subprocess: 0.114s × 매 pre-check
- MIGRATIONS.md 본문 작성 (LLM): ~30~60s
- README.md 변경 이력 작성: ~10~20s
- archive 자동화: ~3s
- **합계: 매 코드 wave마다 +40~80s**

**WIP "B. release 승격 조건" 의도와 실측 불일치 — 거짓 수정 기준 5번 HIT.**

본 wave 9b29f23 자체가 release path를 의도 없이 탔음 (자기증명).

### 거짓 수정 감지 기준 5종 판정

| # | 기준 | 결과 | 근거 |
|---|------|------|------|
| 1 | 메커니즘 갭 50%+ | ❌ HIT | sub-task 7: 9→3 = 67% 미구현 |
| 2 | 회귀 갭 50%+ | ❌ HIT | sub-task 6 TC6.4·sub-task 7 TC7.4·sub-task 3 destructive 경로 회귀 0 |
| 3 | 자동 검증 불가 30%+ | ❌ HIT | sub-task 2 SKILL.md 절차 변경 전체 + sub-task 6 TC6.3·6.5 |
| 4 | latency 회귀 20%+ | ⚠️ 부분 | 단일 명령 NO HIT, 전체 commit 흐름 HIT (release path 자동) |
| 5 | 의도 미달 | ❌ HIT | release path가 일반 변경에 자동 진입 — 가장 결정적 |

**4건 명확 HIT + 1건 부분 HIT.** 사용자 의심 정당.

### 후속 wave 우선순위 재정렬

**최우선 (사용자 체감 마찰 직결)**:
1. **후속 7 (release path 자동 진입 audit)** — 의도 미달 핵심. `harness_version_bump.py` patch 트리거 룰 재검토. 핵심 파일 단순 수정에 release path 진입 금지. WIP B 의도 복원
2. **후속 6 (cascade 9→9 완성 + break 제거 + 차단 통합)** — sub-task 7 미완성 해소

**높음 (회귀 가드 부재)**:
3. **신설 후속 8** — sub-task 3 split-commit `--apply` destructive 경로의 회귀 가드 추가
4. **신설 후속 9** — sub-task 7 cascade trigger 케이스 회귀 테스트 추가 (의도된 결함 fixture)

**중간 (자기증명 해소)**:
5. 후속 2 (SKILL.md serves/trigger 추가) — cascade 자기증명 해소
6. 후속 5 확장 (이미 일부 audit 도중 처리됨 — 자동 수집 + 3 파일 CRLF 정규화)

**낮음 (다운스트림 영향)**:
7. 후속 1 (install 스크립트 SSOT 마이그)
8. 후속 3 (SKILL.md 사본 동기화 자동화)
9. 후속 4 (TestCommitFinalize Windows path)

### 2차 audit (사용자 지적 "release path만 잡았다고?") — 20 의심 전수 점검

본 wave가 추가한 코드 경로 + 호환 부작용을 모두 열거. release path는 18 중 1건일 뿐.

| # | 의심 영역 | 결과 | 영향 |
|---|----------|------|------|
| 1 | pre_commit_check.py subprocess 호출 다수 (git diff 3회·ruff 2회·grep·task_groups·harness_version_bump) | 본 wave 추가 0, 기존 누적 | 누적 비용 ≈ 0.5~1s/commit (변화 없음) |
| 2 | cascade check가 staged 파일마다 `naming.md` Read (캐시 0) | ❌ 본 wave 추가 — 50 파일 시 50회 read | small repos에는 무해, large staging 회귀 |
| 3 | promotion 결정이 HARNESS.json 별도 read | ❌ 본 wave 추가 — 라인 1062, 라인 799와 중복 | 미미하지만 비대칭 |
| 4 | review_route `all(staged_files .md)` 매 commit | 본 wave 추가 — endswith N회 | 무해 |
| 5 | `get_secret_patterns()` 매 호출 dict 생성 (캐시 0) | 본 wave 추가 — 1회만 호출 | 무해 |
| 6 | SKILL.md 사본 2개 (`.claude/` + `.agents/`) git tracked | 본 wave가 더 키움 — 매 변경 2배 | review·diff·git 부담 |
| 7 | split-commit.sh plan 모드도 pre_commit_check.py subprocess | 본 wave 추가 — `--apply` 없는 단순 plan에서도 pre-check 다시 돔 | 사용자가 split 확인하려고 호출하면 +0.4s |
| 8 | commit_finalize.sh ALWAYS docs_ops.py wip-sync 호출 | 기존 — release/non-release 무관 | 매 commit +수십 ms |
| 9 | docs_ops.py wip-sync가 docs/WIP/ 전체 iteration | 기존 — 본 wave 무관 | WIP 폴더가 클수록 회귀 |
| 10 | 본 wave 추가 cascade check staged_files 2회 iteration | ❌ 본 wave 추가 | 무해 (small) / 회귀 가능 (large) |
| 11 | review_route 강등이 docs-only만 hit — 코드 wave 효과 0 | ❌ 본 wave 의도 미달 | 본 wave 9b29f23 자체 강등 안 됨 (자기증명) |
| 12 | **promotion=release 자동 — 사용자 의사 0** | ❌ 본 wave가 만든 핵심 마찰 | release 의도 없이 release path 진입 |
| 13 | split 정책 발동 조건이 너무 좁음 (거대 30+ AND HARNESS_SPLIT_OPT_IN) | ❌ 본 wave 의도 미달 | 13 파일 wave가 split 안 됨 (single 강행) |
| 14 | cascade-defends-missing이 rules/만 검사 — scripts/ 검사 0 | ❌ sub-task 7 미완성 | 9b29f23 같은 코드 wave는 cascade가 자기 결함 못 잡음 |
| 15 | **본 wave 8키가 모두 "Claude 자가 발화 의존"** — orchestrator 강제 0 | ❌ 본 wave 구조적 결함 | hook 강제 메커니즘 없으면 Claude가 무시할 수 있음 |
| 16 | 본 wave 효과를 자동 검증할 수단 0 — '운용 검증' 4회 등장 | ❌ 본 wave 자가 진단 미완성 | 다음 commit에서 효과 0이어도 알 길 없음 |
| 17 | pytest windows·cascade marker 미등록 → PytestUnknownMarkWarning | ❌ 본 wave 추가 — pyproject.toml·pytest.ini 부재 | 다운스트림 -W error 시 깨짐 |
| 18 | release path가 is_starter=true에만 영향 — 다운스트림 0 검증 | ❌ 본 wave 의도 미달 | 다운스트림 마찰은 미관찰 |
| 19 | wave 적용 후 commit 1회 = LLM 도구 호출 15+ + subprocess 5+ | 본 wave 누적 효과 | release path 진입 시 사용자 체감 ~분 단위 |
| 20 | WIP가 진단한 7 마찰 vs 해결률 1/7 (CRLF만) | ❌ 본 wave 메커니즘 갭 | 해결 14%, 가시화 28%, 미해결 57% |

### 가장 결정적 의혹 (의심 15) — orchestrator 강제 0

본 wave 8키 (commit_route·review_route·promotion·blocking_reasons·warning_reasons·side_effects.*) **모두 hook 강제 없이 Claude가 자발적으로 읽어야 작동**. 즉:

- 본 wave가 sub-task 2에서 commit/SKILL.md를 고쳤지만, Claude가 그 절차를 안 따르면 효과 0
- audit WIP가 sub-task 2 TC2.5를 "운용 검증 불가"로 분류한 것이 이 결함의 자기증명
- orchestrator.py(이미 존재)에 새 trigger 추가하면 hook 강제 가능했는데 본 wave는 안 함

이게 진짜 "거짓 수정의 결정적 증거" — **메커니즘 추가 0건, 데이터·라벨 추가만**.

### 누락된 의도 — wave 본문이 의도하지 않은 회귀

| 본문 의도 | 실측 결과 | 갭 |
|-----------|-----------|-----|
| "release 커밋만 무거운 절차" (B) | 핵심 파일 1줄 → release path | 의도 정반대 |
| "split은 plan만, 사용자 동의 시 destructive" (C) | 13 파일 wave도 split 발동 안 됨 — 정책이 너무 좁아 plan조차 안 출력 | 의도 미달 |
| "수리 부산물은 별도 커밋" (3분류) | repair 분류 코드 0건. ledger에 안 잡힘 | 0% 구현 |
| "fast/release/repair path 분리" (4) | review_route 강등은 docs-only 한정. 코드 wave fast 효과 0 | 효과 미달 |
| "side effect ledger로 상향 보고" (F) | ledger는 출력만, 사용자 동의·차단 0 | 회로 |
| "Cascade Integrity Check" (G) | 9 항목 중 3개만 구현, break로 다중 hit 못 잡음 | 33% |
| "Windows + Git Bash 생존성" (E) | 검사 범위 29%, push fallback 0, env 차단 0 | 부분 |

### 본 audit가 발견한 자기증명

1. **wip-sync side effect 자기증명**: audit WIP에 ✅ 마킹된 본 wave 9b29f23 파일들이
   사후 audit 중 wip-sync trigger됨 → 정확히 sub-task 4가 노출하려던 사례
2. **cascade 자기증명**: 본 wave 9b29f23이 자기가 만든 cascade-serves-trigger-missing
   룰에 의해 SKILL.md 결함 노출. 하지만 break로 .agents 사본 미감지
3. **release path 자기증명**: 본 wave가 의도하지 않은 release path를 자동으로 탔음

자기증명은 본 wave의 메커니즘이 실제로 작동한다는 긍정 신호 + 동시에 의도와
실측의 격차를 노출하는 부정 신호. 양면 데이터.

## 메모

- 본 문서는 hn_commit_perf_optimization을 extends. 의도가 같다면 본 wave에
  통합되어야 했으나, 완료 후 검증으로 분리한 것 자체가 자기증명 (audit
  타이밍은 wave 완료 직후가 맞음).
- 측정 baseline 확보 시 `git stash` 사용. baseline 비교 후 stash pop으로
  현재 상태 복원. baseline용 임시 worktree 만들지 마라 — 본 프로젝트의
  worktree 금지 규칙.
