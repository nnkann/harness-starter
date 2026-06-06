---
title: worktree 정책 재정의
domain: harness
c: "프로젝트 수가 많아지면서 worktree blanket ban이 현실 적합성을 잃고, 독립 작업 공간은 소유권과 정리 계약으로 관리하는 편이 낫다."
problem: [P5, P7, P11]
s: [S5, S7, S11]
tags: [git, worktree, policy, isolation]
relates-to:
  - path: decisions/hn_git_subtree_policy.md
    rel: supersedes
  - path: harness/hn_upstream_anomalies.md
    rel: references
  - path: harness/hn_harness_after_ai_alignment.md
    rel: references
status: completed
created: 2026-06-03
updated: 2026-06-06
---

# worktree 정책 재정의

## CPS Rationale

- C -> P: 다중 프로젝트 운용에서는 worktree 자체보다 무소유·무정리 worktree가 P5/P7/P11을 만든다.
- P -> S: S5는 불필요한 blanket ban 제거, S7은 소유권·출력 계약 명시, S11은 active 규칙 drift 정리를 요구한다.
- S -> AC: AC는 active 문구가 "생성 금지"에서 "계약 없는 생성 금지"로 바뀌고, bash guard가 worktree add를 막지 않는지 확인한다.

## 결정

`git worktree` 자체를 금지하지 않는다.

현재 정책:
- worktree 생성은 허용한다.
- 생성 전 owner, 목적, 정리 조건, 변경 보존 방식을 명시한다.
- agent isolation이 worktree를 쓰면 repo binding과 permission boundary를 확인한다.
- 경로 binding이나 권한이 불명확하면 생성하지 않는다.
- clean한 임시 worktree는 자동 정리할 수 있고, dirty worktree는 자동 삭제하지 않는다.

이 결정은 `docs/decisions/hn_git_subtree_policy.md`의 "현재 차단 대상은 worktree add" 판단을 supersede한다. 그 문서는 당시 상태 기록으로 남긴다.

**Acceptance Criteria**:
- [x] Goal: worktree 정책이 blanket ban이 아니라 소유권·정리·권한 계약으로 재정의된다.
  검증:
    review: self
    tests: `bash .claude/scripts/test-bash-guard.sh`
    실측: `rg -n "worktree 생성 금지|git worktree add 금지|isolation: \"worktree\" 사용 금지" AGENTS.md CLAUDE.md .claude docs -g '*.md'`
- [x] Problem AC (P5): worktree 자체 차단으로 인한 운영 마찰을 제거한다.
- [x] Problem AC (P7): worktree 생성 조건이 owner, 목적, 정리 조건, 변경 보존 방식으로 드러난다.
- [x] Guardrail AC (P11/S11): active 규칙과 hook이 과거 blanket ban을 계속 강제하지 않는다.
- [x] Solution AC (S5/S7/S11): `bash-guard.sh`는 worktree add를 차단하지 않고, `harness-upgrade`는 잔여 worktree를 계약 점검 대상으로 다룬다.
- [x] Verification AC (S11): 과거 completed 문서는 supersede 관계로 남기고 active 문구만 현재 정책으로 정리한다.

## 결정 사항

- `AGENTS.md`와 `CLAUDE.md`의 worktree blanket ban을 소유권·정리 책임·변경 보존 계약으로 교체했다.
- `bash-guard.sh`의 `git worktree add` 차단을 제거하고 회귀 테스트에 허용 케이스를 추가했다.
- `harness-upgrade` Step 0.1을 금지 위반 정리가 아니라 worktree 잔여 계약 점검으로 바꿨다.
- completed 문서는 직접 수정하지 않고 이 WIP가 `hn_git_subtree_policy.md`를 supersede한다.

## 실측

- `bash .claude/scripts/test-bash-guard.sh` → 19 passed, 0 failed.
- `python .claude/scripts/safe_command.py eval-harness` → policy drift 0건, dispatcher drift 0건.
- `rg -n "worktree 생성 금지|git worktree add 금지|isolation: \"worktree\" 사용 금지" AGENTS.md CLAUDE.md .claude docs -g '*.md'` → active 정책 파일의 충돌 문구 0건. 출력 4건은 이 WIP의 검증 명령 2건과 과거 기록(`hn_upstream_anomalies.md`, `hn_git_subtree_policy.md`) 2건이다.

## 메모

- `docs/harness/hn_upstream_anomalies.md`의 worktree 항목은 과거 incident다.
- archive/MIGRATIONS archive의 worktree 금지 표현은 history로 유지한다.
