---
title: git subtree/worktree 정책 재검토
domain: harness
c: "StageLink 규모가 커지면서 git subtree가 필요할 수 있다는 요청이 들어왔고, 현재 하네스는 worktree를 절대 차단하지만 subtree 차단 여부는 별도 확인이 필요하다."
problem: [P3, P7]
s: [S3, S7]
tags: [git, subtree, worktree, downstream]
relates-to:
  - path: ../harness/hn_upstream_anomalies.md
    rel: references
status: completed
created: 2026-05-26
updated: 2026-06-01
---

# git subtree/worktree 정책 재검토

## 현재 확인

harness-starter와 StageLink의 현재 코드/문서 검색 기준으로 **명시적인 `git subtree` 차단은 발견되지 않았다**.
실제 강제 차단은 `git worktree add`다.

- `CLAUDE.md` / `AGENTS.md`: worktree 생성 금지.
- `.claude/scripts/bash-guard.sh`: `git worktree add` exit 2 차단. `list/remove/prune`은 허용.
- `.claude/skills/harness-upgrade/SKILL.md`: 기존 worktree 잔여 자동 정리.
- `docs/harness/hn_upstream_anomalies.md`: worktree 정책-실태 불일치의 근거 문서.

따라서 이번 wave의 첫 판단은 “subtree 차단 해제”가 아니라 **subtree와 worktree를 혼동하지 않도록 정책을 분리**하는 것이다.

## 정책 후보

### A. subtree도 가급적 회피, 필요 시 명시 승인

- 기본값: monorepo 내부 직접 코드 또는 package manager workspace를 우선한다.
- 허용 조건: 외부 repo 일부를 vendor처럼 장기 추적해야 하고, submodule보다 subtree가 운영상 단순할 때.
- 필수 기록: prefix path, upstream remote/ref, pull/push 방향, conflict owner, update cadence.
- 검증: subtree로 들어온 코드가 pre-check와 downstream-readiness의 대상/비대상 중 어디에 속하는지 문서화한다.

### B. subtree 적극 활용으로 전환

StageLink가 커져 external component sync가 반복 작업이 되면 B로 전환한다.
이 경우 하네스는 subtree를 금지하지 않고, 오히려 표준 절차를 제공해야 한다.

필요 도구:

- `docs/guides/hn_git_subtree.md` 또는 skill에 subtree add/pull/split 절차 추가.
- `bash-guard.sh`는 `git subtree`를 차단하지 않되, destructive command와 직접 commit 우회만 계속 차단.
- migration guide에 downstream이 subtree prefix를 `.claude/HARNESS.json` 또는 project manifest에 등록하도록 안내.

## 현재 판단

즉시 “전면 폐기/적극 활용”로 뛰기보다는 **A: subtree는 금지하지 않고 가급적 회피 + 필요 시 명시 승인**으로 시작한다.
이유는 현재 하네스가 차단하는 것은 subtree가 아니라 worktree이며, subtree 사용 사례가 아직 StageLink에서 실측 inventory로 확인되지 않았기 때문이다.

다만 StageLink에서 다음 중 하나가 확인되면 B로 전환한다.

1. 같은 외부 코드/문서 묶음을 2회 이상 수동 복사한다.
2. upstream 일부를 downstream 안에 vendor로 유지해야 한다.
3. submodule이 배포/CI/agent 작업에서 지속적으로 실패한다.
4. subtree prefix의 ownership과 update cadence를 manifest로 안정적으로 표현할 수 있다.

**Acceptance Criteria**:

- [x] Goal: S3/S7 기준으로 subtree와 worktree 정책을 분리하고 StageLink 규모에서 subtree 허용 판단 기준을 남긴다.
  검증:
    review: self
    tests: `python3 .claude/scripts/docs_ops.py validate`; `python3 .claude/scripts/docs_ops.py verify-relates`; `bash -n .claude/scripts/bash-guard.sh`
    실측: `git subtree` 차단 근거는 발견되지 않고, `git worktree add` 차단 근거만 확인된다.
- [x] S7: 현재 차단 대상이 `git worktree add`임을 문서화한다.
- [x] S3: downstream 규모 증가 시 subtree를 허용/활용할 전환 조건을 문서화한다.
- [x] StageLink에서 실제 subtree 후보(prefix, upstream, update cadence)를 inventory 한다.
- [x] subtree 후보가 1개 이상 실측되기 전에는 하네스 guide 또는 skill에 표준 절차를 추가하지 않는다.
- [x] subtree 정책은 `git subtree` 금지가 아니라 `git worktree add` 금지와 분리해 기록한다.

## 정리 결과

2026-06-01 재확인 기준, StageLink repo에서 `git subtree` 사용 흔적은 정책으로
승격할 만큼 확인되지 않았다. 문서/manifest 검색에서는 subtree 후보 prefix나
upstream/update cadence가 나오지 않았고, `git log --grep=subtree`는
`test: add subtree drift harness` 1건만 보였다. 이는 실제 `git subtree`
운영 계약이 아니라 drift 검증 성격의 기록으로 본다.

따라서 현재 정책은 완료 상태로 닫는다.

- 하네스가 금지하는 것은 `git worktree add`다.
- `git subtree`는 금지하지 않는다.
- 실제 subtree 후보가 생기면 새 guide/skill부터 만들지 말고 prefix, upstream,
  update cadence, owner를 먼저 inventory한다.
- 후보가 1개 이상 반복 실측될 때만 subtree 표준 절차를 별도 WIP로 연다.
