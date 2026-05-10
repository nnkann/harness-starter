---
signal: WIP 이동 시 역참조 relates-to dead link 생성 반복
domain: harness
keywords: [WIP, move, dead link, relates-to, git mv]
strength: medium
candidate_p: P6
---

WIP completed 전환 시 다른 문서의 `relates-to` 경로가 옛 `WIP/`
경로를 가리킨 채 잔존. pre-check이 차단하지만 **이동 시점에 자동
갱신**이 정답.

**합법 경로**: `python .claude/scripts/docs_ops.py move <파일>` —
`_rewrite_relates_to()`가 역참조 자동 갱신.
**금지 경로**: `git mv` 직접 사용 — 역참조 안 따라감.

**선행 사례**: `docs/incidents/hn_commit_process_gaps.md` 원인 #4
(`hn_split_diff_delivery.md` 이동 시 dead link, 2026-04-27).
