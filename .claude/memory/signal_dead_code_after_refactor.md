---
signal: 리팩토링 후 dead code(미사용 함수 정의) 잔존 반복
domain: harness
keywords: [refactor, dead code, 미사용, 함수 정의]
strength: medium
candidate_p: P6
---

함수 호출을 제거할 때 정의도 함께 제거 안 함. grep만으로 dead code 추적
시도하면 잔재 누락 — LSP "find references"가 1차 수단.

**선행 사례**: `docs/incidents/hn_commit_process_gaps.md` 원인 #3
(`extract_abbrs`·`detect_abbr` 잔존, 2026-04-27).

**재발 방지**: 리팩토링 직후 LSP find references → grep 보완 순.
