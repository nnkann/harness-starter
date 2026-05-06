---
signal: 커밋 요청 시 /commit 스킬 대신 commit_finalize.sh 직접 호출 반복
domain: harness
keywords: [commit, commit_finalize, 우회]
strength: strong
candidate_p: P6
---

WIP 없거나 review stage 불명확할 때 스킬 대신 직접 호출로 넘어가는 패턴.

**합법 경로**: commit/SKILL.md 내부에서 `HARNESS_DEV=1 bash commit_finalize.sh` 호출 — 스킬이 wrapper를 호출하는 것.
**금지 경로**: 스킬 밖에서 `bash .claude/scripts/commit_finalize.sh` 직접 호출 — CLAUDE.md 절대 규칙 위반.

WIP 없어도 `/commit --no-review`로 스킬 경유. 스킬이 버전 범프·MIGRATIONS·pre-check·wip-sync를 처리한다.
