---
title: Codex 포팅 재동기화
domain: harness
problem: P3
s: [S3]
tags: [codex, port, downstream]
relates-to: []
status: completed
created: 2026-05-17
updated: 2026-05-17
---

# Codex 포팅 재동기화

## 사전 준비
- 읽을 문서: `docs/guides/project_kickoff.md`, `.claude/rules/docs.md`, `.claude/rules/naming.md`
- 이전 산출물: `.agents/skills/*`, `.codex/agents/*`, `.codex/hooks.json`
- MAP 참조: 없음 (`.claude/HARNESS_MAP.md` 부재 확인)

## 목표
- 최신 Claude 중심 하네스 표면을 Codex가 읽는 `AGENTS.md`와 `.agents/skills`로 재동기화한다.
- 오래된 Codex bridge 산출물은 삭제 또는 재생성해 silent fail을 줄인다.

## 작업 목록
### 1. Codex 표면 재생성

**사전 준비**: Claude/Codex 키워드 스캔, 루트 지침 diff, bridge 테스트 확인.
**영향 파일**: `AGENTS.md`, `.agents/skills/**`, `.codex/**`, `.claude/scripts/tests/test_codex_agents.py`, 필요 시 `README.md`·`h-setup.sh`.
**Acceptance Criteria**:
- [x] Goal: S3 기준으로 최신 하네스 변경이 Codex 표면에 누락 없이 반영된다.
  검증:
    tests: `python3 -m pytest .claude/scripts/tests/test_codex_agents.py -q`
    실측: `rg -n "HARNESS_MAP|orchestrator.py|debug-guard.sh|CLAUDE.md" AGENTS.md .agents .codex .claude/scripts/tests/test_codex_agents.py`에서 의도치 않은 stale 참조가 없어야 한다.
- [x] `AGENTS.md`는 최신 루트 지침의 내용과 대응하되 Codex 진입 파일명으로 변환된다. ✅
- [x] `.agents/skills`는 최신 `.claude/skills`를 기준으로 재생성되고, Codex 실행 맥락에 맞게 `AGENTS.md` 참조로 바뀐다. ✅
- [x] `.codex`의 이전 bridge는 최신 agent/settings 기준으로 재생성되어 존재하지 않는 스크립트를 호출하지 않는다.

## 결정 사항
- P3/S3 매칭: Codex 표면이 최신 본체와 어긋나면 다운스트림/런타임에서 조용히 실패하므로 silent fail 방어로 처리한다.
- Codex 진입점은 `AGENTS.md`로 두되, Claude 호환·비교용 `CLAUDE.md`는 보존한다.
- `.claude/` 본체는 Claude Code용으로 보존하고, Codex 런타임 표면만 `.agents/skills`와 `.codex/*`로 재생성했다.
- `h-setup.sh`는 `CLAUDE.md`와 `.claude/**`를 계속 배포하면서, `AGENTS.md`·`.agents/skills`·`.codex` bridge도 함께 배포한다.
- 전체 테스트 중 Windows Git Bash가 `git clone --shared` alternates 경로를 해석하지 못해 `TestCommitFinalize`가 실패했으므로, Windows에서는 일반 clone을 쓰도록 테스트 helper를 좁게 수정했다.
- CPS 갱신: 없음.

## 메모
- doc-finder fast scan 대체: `rg`로 Codex/Claude/AGENTS/.codex/.agents 키워드 스캔 완료.
- `.claude/HARNESS_MAP.md`는 현재 파일이 없어 기존 AGENTS.md의 참조가 stale 상태.
- 검증:
  - `python -m pytest .claude/scripts/tests/test_codex_agents.py -q` → 29 passed, 5 warnings.
  - `bash -n h-setup.sh` → 통과.
  - `rg -n -uu "HARNESS_MAP|orchestrator\\.py|debug-guard\\.sh|CLAUDE\\.md" AGENTS.md .agents .codex .claude/scripts/tests/test_codex_agents.py` → hit 없음.
  - `python -m pytest .claude/scripts/tests/ -q` → 174 passed, 4 skipped, 5 warnings.
  - `python .claude/scripts/pre_commit_check.py` → pre_check_passed: true.
