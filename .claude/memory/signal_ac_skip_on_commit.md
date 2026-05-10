---
signal: /commit 호출이 "이미 완료" 암묵적 신호로 작동해 AC 체크박스 갱신 생략
domain: harness
keywords: [commit, AC, 체크박스, self-verify, Phase 완료]
strength: strong
candidate_p: P8
---

수정 후 테스트·AC 체크 없이 `/commit` 직행. commit 스킬 호출 행위
자체가 "완료됐다"는 암묵 신호로 작동 — implementation Step 2.5 "Phase
완료 직후 AC 실행" + self-verify.md 동시 위반.

**올바른 흐름**: 수정 → 테스트/린터 → AC 체크박스 [x] → /commit 호출
→ review는 2차.

**선행 사례**: `docs/incidents/hn_commit_process_gaps.md` 원인 #2
(`05a40a2` split 리팩토링, 2026-04-27). 본 wave Phase 1·2도 동일
패턴 — `/commit` 발화 의존이 P8 변종.
