---
signal: 커밋 요청 시 /commit 스킬 대신 commit_finalize.sh 직접 호출 반복
domain: harness
keywords: [commit, commit_finalize, 우회]
strength: strong
candidate_p: P6
---

WIP 없거나 review stage 불명확할 때 스킬 대신 직접 호출로 넘어가는 패턴.
WIP 없어도 `/commit --no-review`로 스킬 경유가 올바른 경로.
스킬은 review 여부와 무관하게 버전 범프·MIGRATIONS·pre-check·wip-sync를 처리한다.
