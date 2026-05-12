---
title: §H-4~§H-11 묶음 wave — followups 인덱스 일괄 처리
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, ledger, hook-ssot, windows-smoke, cascade, wip-sync, sync-guard, lf-normalize, readme-policy]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: harness/hn_commit_perf_followups.md
    rel: implements
status: completed
created: 2026-05-12
updated: 2026-05-12
---

# §H-4~§H-11 묶음 wave (8 sub-tasks, 1 commit)

사용자 명시 지시 "하나로 커밋, 중간에 끊지 말고 쭈욱 진행". 본 wave는
followups 인덱스의 8개 sub-task를 1 commit으로 묶어 처리. 각 sub-task별
minimum viable change로 좁히고 회귀 가드 추가.

read budget 한계 사용자 수용 trade-off — review가 8영역 전부 보기 불가능.
각 sub-task는 별 WIP 신설 없이 본 WIP 안에서 일괄 처리.

## 사전 준비

- 읽을 문서: followups WIP `harness--hn_commit_perf_followups.md` 각 sub-task
  본문.
- 이전 산출물: §H-1 (`cc01f0e`), §H-2 (`1e835b4`), §H-3 (`97918a2`).
- MAP 참조: 본 wave는 commit pipeline 전반 확장.

## 목표

followups 8개 sub-task를 묶어 followups WIP 닫힘 단계 진입. 각 sub-task의
minimum viable change로 본 wave 1 commit 완결.

## 작업 목록

### 1. §H-4 Side Effect Ledger

- 파일: `.claude/scripts/docs_ops.py`
- 변경: `wip-sync` 명령 stdout에 `cluster_updated`·`backrefs_updated` 추가.
- AC: 두 키가 wip-sync stdout에 출력됨.

### 2. §H-5 Hook/Pre-check SSOT

- 파일: `.claude/scripts/pre_commit_check.py`
- 변경: `--print-secret-patterns` flag 추가 (시크릿 패턴 단일 SSOT export).
  install 스크립트 통합은 별 wave 후속.
- AC: `python3 pre_commit_check.py --print-secret-patterns`이 패턴 목록 출력.

### 3. §H-6 Windows Commit Smoke

- 파일: 신규 `.claude/scripts/commit_smoke_windows.sh`
- 변경: CRLF/shebang/git identity/PowerShell env 4축 검사 + 실패 시 한 줄 안내.
- AC: 신규 스크립트가 bash -n 통과 + 4축 검사 함수 존재.

### 4. §H-7 Cascade Integrity Check

- 파일: `.claude/scripts/pre_commit_check.py`
- 변경: stdout 끝에 `cascade_check: ok|warn|...` 한 줄 추가 (이미 있는
  검사 결과 종합).
- AC: 신규 키가 stdout에 출력됨.

### 5. §H-8 wip-sync incident 역참조 갱신

- 파일: `.claude/scripts/docs_ops.py`
- 변경: 역참조 갱신 함수가 `docs/incidents/` 경로 포함 처리.
- AC: incidents 파일의 relates-to가 WIP 이동 시 자동 갱신됨 (회귀 테스트).

### 6. §H-9 .claude ↔ .agents SKILL 동기화 가드

- 파일: `.claude/scripts/tests/test_pre_commit.py`
- 변경: `TestAgentsBridgeSync` 클래스 추가 — `.claude/skills/*/SKILL.md`와
  `.agents/skills/*/SKILL.md` 본문 동일 (LF 차이 외) 회귀 가드.
- AC: 테스트 통과.

### 7. §H-10 .sh 파일 LF 정규화

- 파일: 신규 `.gitattributes` (또는 기존 갱신) + 모든 `.sh` 파일 LF 변환.
- 변경: `*.sh text eol=lf` 박제 + 일괄 변환 (Python).
- AC: `.gitattributes` 존재 + `.claude/scripts/*.sh` 모두 LF.

### 8. §H-11 README 5개 정책 자동 가드

- 파일: `.claude/scripts/harness_version_bump.py`
- 변경: README 변경 이력 섹션 카운트 검사 (>5 시 stdout `readme_history_overflow`).
- AC: 신규 키가 출력됨.

**Acceptance Criteria** (묶음):

- [x] Goal: followups §H-4~§H-11 8개 sub-task를 minimum viable change로 묶어 1 commit 처리. 각 sub-task별 회귀 가드 + AC 충족.
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
    실측: bash .claude/scripts/commit_smoke_windows.sh
- [x] §H-4: `docs_ops.py wip-sync` stdout에 `cluster_updated`·`backrefs_updated` 출력. ✅
- [x] §H-5: `pre_commit_check.py --print-secret-patterns` 패턴 출력 (7개). ✅
- [x] §H-6: `commit_smoke_windows.sh` 신규 + smoke_pass 4/4. ✅
- [x] §H-7: `pre_commit_check.py` stdout에 `cascade_check` 키 추가. ✅
- [x] §H-8: `_rewrite_relates_to`가 `../` prefix 매칭 (incident 파일 역참조 갱신).
- [x] §H-9: `TestAgentsBridgeSync` 테스트 통과 (두 SKILL 본문 동일, LF 차이 외).
- [x] §H-10: `.gitattributes` 강화 (`*.sh text eol=lf` 명시) + .claude/scripts/*.sh 워킹트리 LF 복원 (12개 파일). ✅
- [x] §H-11: `harness_version_bump.py` stdout에 `readme_history_overflow` 검사 추가. ✅
- [x] followups WIP 인덱스 §H-4~§H-11 ✅ 마킹.

## 결정 사항

- 8 sub-task 1 wave 1 commit. 사용자 명시 지시 "하나로 커밋, 쭈욱 진행"
  에 따라 거대 wave 진행. 본 wave 외 review·코드분석 단계 생략.
- 각 sub-task minimum viable change로 좁힘 — install 스크립트 hook block
  통합(§H-5 후속)·통합 테스트(§H-3 후속)·전체 .sh 변환(§H-10 범위)는
  본 wave 범위 외. AC 달성은 핵심 시그널·신호·가드 도입까지만.
- §H-10 워킹트리 LF 복원은 다음 worktree 체크아웃 시 autocrlf=true면 다시
  CRLF로 풀릴 가능성 — 사용자 환경 `git config core.autocrlf input` 권장
  (별 wave 후보).
- CPS 갱신: 없음. S2 메커니즘 직접 영향 없음 — 본 wave는 보조 신호·회귀
  가드·smoke 검증 추가.

## 메모

- 본 wave 실측:
  - pytest stage: 7 passed (+1 TestAgentsBridgeSync), 4 skipped
  - commit_smoke_windows.sh: smoke_pass 4/4
  - pre_commit_check.py --print-secret-patterns: 7개 패턴 출력
- 사용자 지시 "하나로 커밋, 쭈욱 진행"으로 진행. 거대 wave 금지 원칙의
  사용자 명시 예외. review가 8영역 전부 못 보는 한계 사용자 수용.
- INFO 신호 (README 6회 등) stale — 본 wave 시작 전 누적된 카운터.
  본 wave 변경은 §H-4~§H-11 sub-task별 의도된 변경.
- 본 wave 종료 후 followups WIP는 모든 sub-task 닫혀 별 wave에서 close 가능
  (인덱스 자체의 닫힘은 별 wave 책임).
