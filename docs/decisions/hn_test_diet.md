---
title: 테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거
domain: harness
tags: [test, diet, ac, trigger, downstream]
problem: P6
s: [S6]
relates-to:
  - path: decisions/hn_karpathy_principles.md
    rel: caused-by
status: completed
created: 2026-04-30
updated: 2026-04-30
---

# 테스트 다이어트 + 트리거 좁힘

## 배경

`docs/decisions/hn_karpathy_principles.md` Task 6에서 "신호 테스트 제거 →
다운스트림 상속 문제 해소 ✅"로 처리됨. 그러나 실측 결과:

- `test_pre_commit.py` = 671줄, 40 테스트 (869줄·56개 → 671줄·40개로 줄긴 했음)
- **여전히 다운스트림에 그대로 복사** (`h-setup.sh`가 `.claude/scripts/*` 전부 복사)
- 매 커밋마다 16초 — 이번 세션 6 커밋 = 96초 누적
- AC 기반 시스템이 검증할 수 있는 영역까지 자동 테스트가 중복 검증

**Task 6 AC가 잘못 짜였다.** AC 항목이 "신호 테스트 제거"로 좁혀져 있어서
그것만 하면 ✅ 되는 구조. Goal과 어긋난 작업이 ✅ 처리되는 구멍.

### 사용자 핵심 지적

> "AC에서 해결할 수 없는 원천적으로 검사해야 하는 게 들어가 있다면 이해,
>  그것도 아주 중요한 몇 개. 39개를 매 커밋마다 돌리는 건 미친 짓."

> "지금 있는 기본 테스트 중에 AC 요구사항이 있다면 처리하는 방향도 나쁘진 않다.
>  다만 이건 요청이 있을 때만, 무조건적인 건 없어."

AC 기반 시스템 도입의 함의:
- **자동 테스트는 원칙적으로 줄어야 한다**
- **무조건적 매 커밋 실행은 없다.** AC가 테스트를 요구하면 그때 실행
- 회귀 가드는 CI·`eval --deep` 같은 별도 트리거로 분리

## 실측 데이터 (2026-04-30)

### 테스트 분류

| 클래스 | 개수 | 시간 | 검증 대상 | AC로 대체 가능? |
|--------|------|------|-----------|----------------|
| `TestEnoentPattern` | 12 | <0.1s | 린터 ENOENT 정규식 매칭 | ❌ 회귀 가드 (1회/일이면 충분) |
| `TestIntegRelatesTo` | 8 | ~3s | `relates-to:` 경로 검증 | ✅ docs_ops.py 라이브 코드가 함 |
| `TestStageBasic` | 4 | <0.1s | stage 결정 룰 | ✅ AC가 stage 명시 |
| `TestIntegMoveCommit` | 4 | ~2.1s | rename 처리 | ✅ AC가 rename 명시 |
| `TestIntegDeadLink` | 4 | ~1.8s | dead link 검사 | ✅ docs_ops.py 라이브 |
| `TestWipSyncAbbrMatch` | 3 | ~3.5s | abbr 매칭 | ✅ AC가 명시 |
| `TestSecretScan` | 3 | <0.1s | 시크릿 패턴 강도 | ❌ 진짜 자동 검증 가치 |
| `TestCompletedGate` | 2 | <0.1s | 차단 룰 정확성 | ❌ 룰 자체 회귀 가드 |

**합계**: 40 테스트, ~14.5초 (setup 포함). 통합 테스트 16개가 ~10초 차지.

### 트리거 재정의

**무조건 매 커밋 = 0개**. 시크릿 스캔조차 `install-secret-stan-hook.sh`
pre-commit hook과 중복 — 거기에 위임.

**AC가 테스트를 명시 요구 시**: 해당 영역 marker 테스트 실행
(예: AC에 "stage 결정 회귀 체크" → `@pytest.mark.stage` 실행)

**별도 트리거**: `eval --deep`, CI, 사용자 명시 요청 (`/test`)

## 목표

- 매 커밋 부담 16초 → 1초 이하
- 다운스트림에 무관한 테스트 상속 차단
- AC 기반 시스템과 중복 검증 영역 제거

## 작업 목록

### 1. 무조건 트리거 제거 + 영역별 marker 도입
> kind: refactor

**영향 파일**: `.claude/scripts/test_pre_commit.py`, `.claude/skills/commit/SKILL.md`, `.claude/rules/self-verify.md`, `.claude/skills/harness-dev/SKILL.md`

**변경 내용**:

A. `test_pre_commit.py`에 영역별 pytest marker 부여:
- `@pytest.mark.secret` (3) — 시크릿 스캔
- `@pytest.mark.gate` (2) — 차단 룰
- `@pytest.mark.stage` (4) — stage 결정
- `@pytest.mark.docs_ops` (16) — dead link/relates-to/move/wip-sync
- `@pytest.mark.enoent` (12) — 린터 ENOENT 정규식

B. **commit 흐름에서 무조건 pytest 제거**:
- SKILL.md "스크립트 변경 시 pytest 필수" 룰 삭제
- self-verify.md "스크립트 연동 변경 시 반드시 실행" → "AC가 테스트 요구 시 실행"으로 변경
- harness-dev/SKILL.md 체크리스트의 "pytest 통과" 항목 → "AC가 요구하면 pytest"로 변경

C. AC에서 테스트 요청하는 표준 표현 정의 (`docs.md`에):
```markdown
**Acceptance Criteria**:
- [ ] 영향 범위: pre_commit_check.py — pytest -m stage 회귀 체크
```
→ review/self-verify가 이 패턴 보면 marker 추출해 실행

D. 사용자 명시 트리거: `pytest`·`pytest -m <marker>` 직접 실행만. 자동 호출 어디에도 없음.

**Acceptance Criteria**:
- [x] Goal: commit 흐름 어디에도 무조건 pytest 호출 없음 ✅
- [x] test_pre_commit.py 40개 테스트 모두 영역별 marker 부여 (secret 3 + gate 2 + stage 8 + enoent 12 + docs_ops 15) ✅
- [x] commit/SKILL.md에는 원래 pytest 직접 실행 없음 (work-verify 워크플로우 위임) — 변경 불필요 확인 ✅
- [x] self-verify.md "테스트 판단" 섹션 — 트리거 매트릭스 + marker 목록 + "무조건 매 커밋 pytest는 없다" 원칙 명시 ✅
- [x] harness-dev/SKILL.md 체크리스트 동일 변경 (라인 145) ✅
- [x] implementation/SKILL.md "테스트 스위트" 항목도 동일 변경 (라인 299) ✅
- [x] docs.md AC 포맷에 "pytest -m <marker> 회귀 체크" 표현 명문화 ✅
- [x] 영향 범위: self-verify.md·harness-dev/SKILL.md·implementation/SKILL.md — `pytest -m gate` 회귀 체크 (실측 0.6초, 기존 무조건 16초 대비 -96%) ✅

---

### 2. 다운스트림 격리 — test_pre_commit.py 미복사
> kind: feature

**영향 파일**: `h-setup.sh`, `.claude/HARNESS.json`, `docs/harness/MIGRATIONS.md`

**현재 동작**:
```bash
# h-setup.sh
for f in "$SCRIPT_DIR/.claude/scripts/"*; do
  copy_if_new "$f" "$TARGET/.claude/scripts/$(basename "$f")"
```
→ `test_pre_commit.py` 671줄이 다운스트림에 그대로 복사. 다운스트림은 이걸 안 돌리지만 git 추적·읽기 부담.

**변경 내용**:

A. `h-setup.sh`에 starter 전용 파일 제외 목록 추가:
```bash
STARTER_ONLY_FILES="test_pre_commit.py"
for f in "$SCRIPT_DIR/.claude/scripts/"*; do
  bn=$(basename "$f")
  echo "$STARTER_ONLY_FILES" | grep -qw "$bn" && continue
  copy_if_new "$f" "$TARGET/.claude/scripts/$(basename "$f")"
```

B. 기존 다운스트림 cleanup: `harness-upgrade` 시 `test_pre_commit.py` 발견되면 사용자 확인 후 삭제 (또는 starter_skills처럼 자동 삭제)

C. starter 전용 파일 컨벤션 명문화: `naming.md` 또는 `harness-dev/SKILL.md`에 "test_*.py 는 starter 전용" 룰 추가

**Acceptance Criteria**:
- [x] Goal: 다운스트림에 test_pre_commit.py·conftest.py가 복사되지 않음 (신규 설치·upgrade 모두) ✅
- [x] h-setup.sh에 STARTER_ONLY_SCRIPTS 제외 로직 추가 (두 곳: upgrade 263줄, 신규 설치 499줄) ✅
- [x] upgrade 경로에 기존 다운스트림 cleanup 동작 추가 (rm + 알림) ✅
- [x] MIGRATIONS.md에 다운스트림 영향 명시 (Task 8 일괄 커밋에서 처리) ✅
- [x] 영향 범위: h-setup.sh — 다운스트림 격리 회귀 체크. 단순 bash 로직이라 pytest marker 없음, 수동 검증 (격리 후 다운스트림에 파일 없는지 확인) ✅

---

### 3. hn_karpathy_principles.md "거짓 ✅" 정정
> kind: docs

**영향 파일**: `docs/decisions/hn_karpathy_principles.md`

**변경 내용**:

`결정 사항` 섹션의 "다운스트림 상속 문제 해소 ✅" 표현을 정정.
실제로는 신호 테스트만 제거됐고 다운스트림 상속은 미해결 상태였음을
명시. 본 WIP(`hn_test_diet.md`)로 후속 처리한다는 포인터 추가.

**Acceptance Criteria**:
- [x] decisions/hn_karpathy_principles.md "결정 사항" 섹션에서 "다운스트림 56개 테스트 상속 문제 해소" 표현 삭제 ✅
- [x] hn_test_diet.md를 후속 작업 포인터로 명시 ("거짓 ✅ 정정" 항목 추가) ✅
- [x] frontmatter status는 completed 유지 ✅

---

## 결정 사항

- **marker 5종**: `secret`(3) / `gate`(2) / `stage`(8) / `enoent`(12) / `docs_ops`(15) — 클래스 단위 부여. `conftest.py` 신설로 marker 등록.
- **AC 트리거 표현**: `- [ ] 영향 범위: <파일> — pytest -m <marker> 회귀 체크` 표준 형식. self-verify.md "트리거 매트릭스" SSOT, docs.md "AC 포맷"에 명문화.
- **무조건 매 커밋 pytest 폐기**: self-verify.md 라인 7·24·46, harness-dev/SKILL.md 라인 145, implementation/SKILL.md 라인 299 — 모두 "AC가 요구 시" 트리거로 변경. commit/SKILL.md는 원래 pytest 직접 실행 안 함(work-verify 위임) 재확인.
- **다운스트림 격리**: `STARTER_ONLY_SCRIPTS="test_pre_commit.py conftest.py"`. h-setup.sh 두 경로(upgrade·신규 설치) 모두 제외 + upgrade는 기존 cleanup도 수행.
- **거짓 ✅ 정정**: hn_karpathy_principles.md "결정 사항"에서 "다운스트림 56개 테스트 상속 문제 해소" 문장 삭제, 본 WIP 후속 포인터 추가.

## 실측 데이터 (2026-04-30)

| 시나리오 | 시간 | 비고 |
|----------|------|------|
| AC가 marker 명시 (`-m gate`) | 0.6초 | 회귀 가드 가치 있는 변경에서만 |
| AC가 테스트 요구 안 함 | 0초 | 일상 변경의 기본값 |
| 사용자 명시 전체 (`pytest`) | 21초 | CI / `eval --deep` / 사용자 요청 한정 |

매 커밋 16초(이전) → 0초(일상) / 0.6초(AC 명시) — **사실상 100% 절감**.

## 메모

- 실측: `pytest --durations=15` 통합 테스트 16개가 시간의 ~70% 차지
- 진짜 회귀 가드 가치 있는 것 — TestEnoentPattern (12개): 한 번 짜면 안 깨지는 정규식. 매 커밋 X, eval --deep 또는 CI에서 충분
- 시크릿 스캔과 install-secret-scan-hook.sh 중복 검토는 작업 1 진행 중 부수 작업
- 사용자 원칙: **"무조건적인 건 없어. 요청이 있을 때만."** — AC 기반 시스템과 정합
