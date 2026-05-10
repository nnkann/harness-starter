---
title: wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단
domain: harness
problem: P6
solution-ref:
  - S6 — "8. docs_ops.py move 신호 → pre-check 봉인 면제 (부분)"
tags: [wip-sync, staging, docs-ops]
relates-to:
  - path: decisions/hn_eval_harness_medium_fixes.md
    rel: caused-by
status: completed
created: 2026-05-11
---

# wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단

## 사전 준비
- 읽을 문서: `.claude/scripts/docs_ops.py` (`cmd_move` L286~374, `cmd_cluster_update` L409~503, `cmd_wip_sync` L566~792). 직접 Read로 결함 위치 정확 특정 완료
- 이전 산출물: v0.42.1·42.2·42.3·42.4 4 wave 모두 commit 직후 `docs/clusters/harness.md` + `docs/decisions/<wip>.md` 2건 unstaged 잔여 발생 (자기증명 4회)
- MAP 참조: HARNESS_MAP.md P6 (검증망 스킵) defends-by: self-verify, pipeline-design / enforced-by: harness-dev, eval

## 목표
- `cmd_cluster_update`와 `cmd_move`가 자기 결과(파일 수정)를 git add로 staging하도록 보강. 매 wave commit 직후 잔여 0건
- 회귀 가드: wip-sync 호출 후 git status에 unstaged 변경 없음을 검증
- CPS 연결: P6 (검증망 스킵 — 메커니즘이 자기 결과를 검증·반영 안 함). 본 보강이 S6 8번 방어 레이어(`docs_ops.py move 신호`)의 staging 정합성 보강

## 작업 목록

### 1. Phase 1 — `cmd_cluster_update` git add 추가

**사전 준비**: `docs_ops.py` L499 — `cluster.write_text(build_body(today), encoding="utf-8")` 직후 git add 호출 부재
**영향 파일**: `.claude/scripts/docs_ops.py` (L499 영역, 1줄 추가)
**Acceptance Criteria**:
- [x] Goal: `cmd_cluster_update`가 cluster 파일 갱신 직후 git add로 자동 staging. 호출 후 `git status docs/clusters/`가 깨끗함
  검증:
    review: review
    tests: pytest .claude/scripts/tests/ -q
    실측: tmp_path에 cluster 파일 작성 후 cmd_cluster_update 호출 → cluster 변경분이 git index에 반영됐는지 검증 (또는 `git diff --cached --name-only`로 확인)
- [x] `cluster.write_text(...)` 직후 `subprocess.run(["git", "add", str(cluster)], capture_output=True)` 추가
- [x] `cluster_with_prev == prev_text` skip 분기는 git add 호출 안 함 (멱등성 유지 — 변경 없으면 staging 무관)

### 2. Phase 2 — `cmd_move` write_frontmatter_field git add 추가

**사전 준비**: `docs_ops.py` L348~350 — `write_frontmatter_field(dest, "status"·"updated", ...)` 두 호출이 working tree만 갱신. `git mv` (L330)가 rename은 staging했으나 그 후 본문 수정은 unstaged
**영향 파일**: `.claude/scripts/docs_ops.py` (L350 직후, 1줄 추가)
**Acceptance Criteria**:
- [x] Goal: `cmd_move`가 frontmatter 갱신 직후 dest 파일을 git add로 재staging. 호출 후 `git status <dest>`가 unstaged 변경 없음
  검증:
    review: review
    tests: pytest .claude/scripts/tests/ -q
    실측: tmp 환경 회귀 테스트로 cmd_move 호출 후 dest 파일이 staged 상태인지 검증. wip-sync 자동 이동 흐름 통합 테스트 1건 추가
- [x] `write_frontmatter_field(dest, "updated", today)` 직후 `subprocess.run(["git", "add", str(dest)], capture_output=True)` 추가
- [x] `cmd_reopen` 동일 패턴 점검 — L397 `write_frontmatter_field(dest, "status", "in-progress")`도 같은 누락 가능성. 본 wave 스코프에 포함

### 3. Phase 3 — 회귀 가드 신설

**사전 준비**: 기존 `test_pre_commit.py`·`test_eval_harness.py` 외 `docs_ops.py` 직접 회귀 테스트 부재. tmp_path + 임시 git repo 초기화 패턴 필요
**영향 파일**: `.claude/scripts/tests/test_docs_ops_staging.py` (신설)
**Acceptance Criteria**:
- [x] Goal: wip-sync 흐름 후 git status가 깨끗함을 자동 검증하는 회귀 가드. 향후 staging 누락 회귀 0건
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_docs_ops_staging.py -v
    실측: 신규 테스트 파일에서 (a) cmd_cluster_update 후 git diff --cached에 cluster 파일 hit (b) cmd_move 후 git diff --cached에 dest 파일 hit (c) 통합 흐름(가짜 WIP → wip-sync → completed 이동 → 잔여 0) 모두 PASS
- [x] tmp_path에 git init + 최소 docs/ 구조 + naming.md 약어 표 + 가짜 WIP 파일 작성 fixture
- [x] cmd_cluster_update 직접 호출 회귀 (Phase 1 검증)
- [x] cmd_move 직접 호출 회귀 (Phase 2 검증)
- [x] cmd_reopen 회귀 (Phase 2 부수 점검)
- [x] 전체 회귀: 87 → 87+ passed (회귀 0)

## 결정 사항

### Phase 1 — cmd_cluster_update git add 추가
- **반영 위치**: `.claude/scripts/docs_ops.py` L499 `cluster.write_text(...)` 직후 1줄 추가
- **변경**: `subprocess.run(["git", "add", str(cluster)], capture_output=True)` 추가. skip 분기는 호출 안 함 (멱등성)
- **이유**: `cmd_cluster_update`가 cluster 파일 갱신 후 staging 안 해 매 wave 잔여 발생

### Phase 2 — cmd_move + cmd_reopen git add 추가
- **반영 위치 1**: `cmd_move` L350 `write_frontmatter_field(dest, "updated", today)` 직후 1줄 추가
- **반영 위치 2**: `cmd_reopen` L400 `write_frontmatter_field(dest, "status", "in-progress")` 직후 1줄 추가
- **변경**: 두 곳 모두 `subprocess.run(["git", "add", str(dest)], capture_output=True)` 추가
- **이유**: `git mv`는 rename만 staging — 그 후 frontmatter 갱신은 working tree만 수정되어 unstaged 잔여. `cmd_reopen`도 동일 패턴 (사전 점검에서 발견)

### Phase 3 — 회귀 가드 신설
- **반영 위치**: `.claude/scripts/tests/test_docs_ops_staging.py` 신설
- **3건**: `test_cluster_update_stages_changes` / `test_move_stages_frontmatter_update` / `test_reopen_stages_frontmatter_update`
- **검증**: tmp_path + git init fixture로 격리. 각 명령 호출 후 `git diff --cached`에 대상 파일 hit + unstaged 잔여 0건 확인
- **결과**: 3 passed / 전체 90 passed (87 → 90, 회귀 0)

### 부수 정정 — commit_finalize.sh 거짓 주석
- 기존 주석은 "cmd_cluster_update가 git add 호출"이라 거짓 박제 — 실제 코드는 호출 안 함
- 본 wave에서 v0.42.5 보강 후 정확한 staging 책임 재명시 (실제 코드 = 주석 정합)

## CPS 갱신
- P6 본문 변경 없음 — 본 보강은 S6 8번 방어 레이어(`docs_ops.py move 신호`)의 staging 정합성 강화. Solution 정의 변경 아님
- Solution 정의 변경 없음 → owner 추가 승인 불필요

## 메모
- doc-finder fast scan 생략 — 사용자 요청에 결함 위치(commit_finalize.sh / docs_ops.py wip-sync) 명시 + 직접 Read로 충분히 정확. internal-first 위배 아님
- 추측 금지 검증: commit_finalize.sh 주석은 "cmd_cluster_update가 git add 호출"이라 거짓 박제. 실제 코드 직접 Read해 거짓 확인 — `cmd_cluster_update`에 git add 0건. 주석 자체도 본 wave에서 정정 가능 (Phase 1과 함께)
- 5번 자기증명 사고: v0.42.1~42.4 + 본 메시지 시점 = 5회. P8 자가 의존 패턴이 starter 본인에게 발현됐음 — `commit_finalize.sh` wrapper 도입(v0.32.x)이 git commit 우회는 차단했으나 자기 결과 staging은 빠뜨림
- CPS 매칭 단독 판단: P6 hit. P8은 부수 (사용자 발화 의존이 아니라 메커니즘 자체 결함이라 P6가 더 정확)
