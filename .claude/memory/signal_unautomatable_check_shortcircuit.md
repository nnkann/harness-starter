---
signal: 자동화 불가 검증을 자동화한 것처럼 포장하는 단락 패턴
domain: harness
keywords: [self-verify, 검증, 테스트 통과, 완료 선언, Claude 행동]
strength: medium
candidate_p: P6
---

"테스트 통과 = 기능 동작 확인" 등식을 검증 없이 적용. 테스트가 커버
하는 축(예: pre-commit 로직)과 변경한 축(예: 규칙 텍스트 → Claude
행동)이 다른데 그 불일치 확인 없이 "검증됐습니다"로 단락.

**올바른 표현**: "테스트 X/X 통과 — 로직 검증 완료. Claude 행동 변화는
운용에서 확인 필요" — self-verify.md "## 자동화 불가 검증 처리 원칙"
SSOT.

**선행 사례**: `docs/incidents/hn_commit_process_gaps.md` 원인 #1
(test_pre_commit.py 54/54 통과로 규칙 텍스트 효과 단정, 2026-04-27).
