---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-04-28
---

# 다운스트림 마이그레이션 가이드

`harness-upgrade` 스킬이 각 버전 업그레이드 시 이 문서를 읽어 다운스트림에
표시한다. **upstream 소유 — 다운스트림은 읽기만.**

**최신 5개 버전 본문만 유지** (v0.30.1 정책). 6번째 이전 버전은
`MIGRATIONS-archive.md`로 자동 이동 — `harness_version_bump.py --archive`가
이동 처리. 더 오래된 업그레이드 추적은 archive 또는 git log
(`git log --oneline --grep "(v0\."`).

다운스트림은 자기 환경 마지막 upgrade 이후 누적된 버전을 읽으면 된다.
5개 본문 기준 약 1~2개월 분량. 그보다 오래 누적된 다운스트림은 archive
참조.

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

---

## v0.34.0 — implementation init 게이트 의미 재정의 (A4)

### 변경 파일

- `.claude/skills/implementation/SKILL.md` 라인 69~85 — Step 0 게이트 로직 재서술
- `.claude/scripts/check_init_done.sh` (신설) — 판정 로직 추출 (회귀 테스트 가능 + 다운스트림 자가 점검 용도)
- `.claude/scripts/tests/test_pre_commit.py` — TestInitGate 5 케이스 신규 추가

### 다운스트림 영향

implementation Step 0의 init 미완료 감지 로직이 변경됨.

**이전 (v0.33.x까지)**:
- CLAUDE.md `## 환경`의 `패키지 매니저:` 키 1개만 검사
- 비어있으면 차단
- 다운스트림 baseline 측정에서 false-block 입증 (15~19s 헛돔)

**v0.34.0 (A4 의미 재정의)**:
- `docs/guides/project_kickoff.md` 부재 OR `status: sample` 단독 → 차단
- CLAUDE.md `## 환경` drift는 차단 사유 아님 (다운스트림 자율)

**다운스트림 자유도 회복**:
- C++/CMake처럼 `패키지 매니저:` 키가 N/A인 환경도 정상 통과
- 다운스트림이 자기 양식·언어로 CLAUDE.md `## 환경` 채울 자유 확보

**여전히 차단되는 케이스 (의도)**:
- `harness-adopt` 끝났지만 `harness-init` 안 돈 다운스트림 (sample만 존재)
- `project_kickoff.md` 자체가 없는 신규 프로젝트

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

`harness-init` 정상 완료한 다운스트림은 영향 없음. `harness-adopt`만 돌고
`harness-init` 미실행한 다운스트림은 본 v0.34.0부터 implementation Step 0
가 차단됨 — `/harness-init` 실행 후 작업 진행.

### 검증

- `pytest -m gate` (TestInitGate 6/6 신규 통과 — 인라인 주석 케이스 포함)
- pytest 전체 64 passed (기존 58 + 신규 6, 회귀 0)
- starter `check_init_done.sh` 비용 측정: 5회 평균 ~0.07s (max 0.15s) —
  ≤2s 게이트 27x 여유
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다른 다운스트림
  환경(POSIX bash·다른 CPS 위치) 재발 시 본 incident 갱신 필요

### 결정 근거

`docs/decisions/hn_init_gate_redesign.md` (이동 후) — advisor 4 대안
weighted matrix 평가 결과 A4 채택 (96점 / A1 82 / A3 62 / A2 40).

---

## v0.33.1 — SEALED 면제 (MIGRATIONS류 자기 운영 파일)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — `SEALED_PATH_EXEMPT` 추가 (MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md 3개 path 화이트리스트)
- `.claude/scripts/tests/test_pre_commit.py` — T42.5 회귀 테스트 추가

### 다운스트림 영향

v0.32.0 (약속 박제 보호)에서 도입한 SEALED(completed 봉인) 룰이 starter
자기 운영 누적 파일을 면제하지 않아, 다운스트림이 `harness-upgrade`로
v0.33.0을 fetch한 직후 `/commit` 시 MIGRATIONS.md가 차단되는 결함이
발견됨 (incident 2026-05-02 다운스트림 보고).

본 fix로 MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md는
SEALED 검사에서 면제. 다운스트림 정상 흐름 복귀.

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

### 검증

- pytest -m gate (T42.5 신규 포함, 11/11 통과)
- pytest 전체 58 passed (기존 57 + 신규 1, 회귀 0)
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다운스트림 환경
  재발 시 본 incident 갱신 필요

---

## v0.33.0 — commit_finalize wrapper (wip-sync + git commit 단일 흐름)

### 변경 파일

- `.claude/scripts/commit_finalize.sh` (신설) — wip-sync → git commit 단일 흐름 wrapper
- `.claude/skills/commit/SKILL.md` Step 7.5·8·커밋 메시지 작성 — wrapper 호출 1줄로 단순화
- `.claude/scripts/tests/test_pre_commit.py` — TestCommitFinalize 3 케이스 신설

### 변경 내용

자기증명 사고 (2026-05-02): SKILL.md SSOT는 "git commit **직전** wip-sync"
명시했으나 Claude가 git commit 먼저 호출 → wip-sync → 별 이동 commit
패턴 반복. 8 commit 중 3건 위반 (37.5%).

자율 신뢰만으로는 부족 → 메커니즘 차단으로 전환:

- `git commit` 직접 호출 금지. wrapper 경유 의무
- wrapper 내부: VERDICT != block 이면 wip-sync 호출 → wip 이동·cluster·
  역참조 갱신 모두 staging → `git commit "$@"` 단일 호출
- 결과: 1 wave = 1 commit. 별 이동 commit 사라짐

### 적용 방법

자동. harness-upgrade 후 commit 흐름 자동 변경.

호출 형식:
```bash
VERDICT="$VERDICT" HARNESS_DEV=1 \
  bash .claude/scripts/commit_finalize.sh \
    -m "feat: [제목]" -m "[본문]"
```

### 검증

```bash
pytest -m gate  # TestCommitFinalize 3 케이스
```

회귀 위험: TestCommitFinalize 3/3 통과 (HARNESS_DEV 차단·simple commit·
block skip wip-sync). 본 commit 자체가 자기증명 — wrapper 사용해 commit.

---

## v0.32.0 — 약속 박제 보호 (completed 봉인 + anti-defer 룰)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 게이트 신설 (3.5번 섹션). status: completed 문서 본문 무단 변경 시 exit 2 차단
- `.claude/rules/anti-defer.md` (신설) — 미루기 회피 사유 블랙리스트 + 사용자 명시 처리 지시 우선 규칙
- `.claude/agents/review.md` — 검증 루프 7번 "wave scope 무단 확장 감지" 추가
- `CLAUDE.md` — 절대 규칙에 anti-defer + completed 봉인 명시
- `.claude/scripts/tests/test_pre_commit.py` — TestCompletedSeal 5 케이스 신설
- `docs/decisions/hn_session_test_results.md` (reopen) — 우선순위 5 측정 결과 누적 후 재 completed 처리
- `docs/WIP/decisions--hn_promise_protection.md` (신설) — 본 wave WIP

### 변경 내용

**자기증명 사고 (2026-05-02)**: v0.31.2 commit 후 완료된 wave WIP를 같은 세션에서 무단 확장 시도 → "최악 패턴" 사고. 다음 시스템 보호 메커니즘 신설:

1. **completed 봉인 게이트 (메커니즘)**: status: completed 문서 본문 변경을 pre-check이 차단. 변경하려면 `docs_ops.py reopen`으로 in-progress 전환 의무. `## 변경 이력` 섹션·updated/status 필드·rename은 면제.

2. **anti-defer 룰 (자율 신뢰 보강)**: "측정 후·다음 세션·데이터 누적 필요" 같은 미루기 회피 사유의 사용자 승인 없는 단독 사용 금지. 별 wave 분리는 정상 흐름이지만 처리 시점이 "후속"이면 미루기로 간주.

3. **review 자동 감지**: review.md 검증 루프에 wave scope 무단 확장 감지 추가.

**자기증명 검증**: 본 commit 작성 중 우선순위 5 측정을 `decisions/hn_session_test_results.md` (completed)에 직접 수정 → 본 게이트가 즉시 차단 → reopen 절차 거쳐 정상 처리. 메커니즘 정확 작동.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음. 다운스트림이 completed 문서 수정 시 `docs_ops.py reopen` 절차 의무.

### 검증

```bash
pytest -m gate
```

회귀 위험: TestCompletedSeal 5/5 통과. 본 commit이 자기증명 — 봉인 게이트가 본 작업 자체를 차단해 reopen 절차 거치게 함.

---

## v0.31.2 — commit/SKILL.md Step 7 staging.md SSOT link로 단순화

### 변경 파일

- `.claude/skills/commit/SKILL.md` — Step 7 Stage 결정 우선순위·Stage별 행동·거대 커밋 정책 본문 재진술 제거 → staging.md SSOT 참조 한 단락
- `docs/WIP/decisions--hn_rule_skill_ssot_apply.md` (신설) — Task 2 wave WIP

### 변경 내용

`hn_rule_skill_ssot.md` Task 1 측정 결과 핫스팟 1순위(commit × staging)
처리. SKILL.md 본문에 staging.md의 Stage 정의·플래그 우선순위·충돌 처리·
거대 커밋 정책이 일부 인라인되어 있던 것을 SSOT 참조로 단순화.

스킬 ~30줄 → ~5줄. staging.md 갱신 시 SKILL.md 동기화 누락 위험 제거.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음.

### 검증

```bash
pytest -m stage
```

회귀 위험: 본 변경은 SKILL.md 본문만 — Claude가 staging.md를 follow하는지 운용에서 확인 필요. 본 commit 자체가 자기증명 (Step 7 흐름이 정상 작동했음).

