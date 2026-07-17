---
title: 버전 범프 스테이징 계약 보강
domain: harness
problem: P6
s: [S6, S7]
tags: [version-bump, commit, regression]
status: completed
created: 2026-05-20
updated: 2026-05-20
---

# 버전 범프 스테이징 계약 보강

Goal: `harness_version_bump.py`가 스테이징 전 핵심 변경을 `none`으로만 숨기거나, 지원하지 않는 CLI 인자를 조용히 무시하지 않게 한다.

## AC

**Acceptance Criteria**:
- [x] Goal: S6/S7 기준으로 staged 변경이 없을 때 핵심 변경을 숨기지 않고, unsupported CLI 인자를 조용히 삼키지 않는다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_harness_version_bump.py -q`
    실측: `python .claude/scripts/harness_version_bump.py`, `python .claude/scripts/harness_version_bump.py --apply patch`, `python -m py_compile .claude/scripts/harness_version_bump.py`, `git diff --check`
- [x] staged 변경이 없더라도 unstaged/untracked 핵심 변경이 있으면 `stage_required: true`와 예상 범프를 출력한다.
- [x] 지원하지 않는 인자는 정상 체크로 폴백하지 않고 usage와 함께 실패한다.
- [x] 중복 절차 문구는 `commit` Step 4에 통합하고, `harness-dev`에는 SSOT 참조만 남긴다.

## 결정 사항

- 기존 SSOT(`harness_version_bump.py`, commit/harness-dev 스킬)를 갱신한다. 새 SSOT는 만들지 않는다.
- 완료: 절차 상세는 `commit` Step 4로 통합했고, `harness-dev`의 중복 템플릿은 `MIGRATIONS.md` SSOT 참조로 축소했다.
- CPS 갱신: 없음. 기존 S6/S7의 완료 증거·출력 계약을 구현으로 보강한다.

## 메모

- 사용자 지적: 버전 범프 `none` 출력이 실제 patch 필요성을 가려 downstream upgrade 취소로 이어질 수 있다.
- 테스트: `python -m pytest .claude/scripts/tests/test_harness_version_bump.py -q` → 4 passed.
- 실측: 기본 실행 → `stage_required: true`, `pending_bump: patch`.
- 실측: `--apply patch` → unsupported arg + usage 출력, non-zero 실패.
- 실측: `python -m py_compile .claude/scripts/harness_version_bump.py` 통과.
- 실측: `git diff --check` 통과. CRLF 정규화 warning만 출력.
