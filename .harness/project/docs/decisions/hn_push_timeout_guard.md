---
title: push 타임아웃 재발 방지
domain: harness
problem: P7
s: [S6, S7]
tags: [commit, push, regression]
status: completed
created: 2026-05-20
updated: 2026-05-20
---

# push 타임아웃 재발 방지

Goal: commit Step 8이 Windows/Codex 환경에서 `bash -lc` 경유 push로 Git Credential Manager 대기에 빠지지 않게 한다.

## AC

**Acceptance Criteria**:
- [x] Goal: S6/S7 기준으로 push 명령이 비대화형 env와 shell별 실행 형태를 명시한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q`
    실측: active `.agents/skills/commit`과 배포용 `.claude/skills/commit`의 Step 8 확인
- [x] active Codex 스킬(`.agents`)과 배포용 스킬(`.claude`) 모두 PowerShell 기본 push 경로를 갖는다.
- [x] `bash -lc`로 push를 감싸지 말라는 금지 문구가 Step 8에 남는다.
- [x] 회귀 테스트가 두 스킬 문서의 push 계약을 함께 검사한다.

## 결정 사항

- 새 push 스크립트는 만들지 않는다. 안전 조회 dispatcher 규칙상 push를 safe_command에 넣지 않고, commit Step 8 절차 SSOT만 고정한다.
- 완료: `.claude/skills/commit`과 `.agents/skills/commit` Step 8에 PowerShell 기본 push, Bash 대체 push, `bash -lc` 금지 문구를 반영했다.
- CPS 갱신: 없음. S6/S7의 검증·출력 계약을 commit 절차에 반영한다.

## 메모

- 실측: `git ls-remote`와 dry-run push는 성공했지만, `bash -lc 'HARNESS_DEV=1 git push origin main'` 형태가 Git for Windows/GCM 하위 프로세스 대기로 타임아웃됐다.
- 테스트: `python -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q` → 3 passed.
