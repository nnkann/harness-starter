---
title: commit 흐름 자동화 — wip-sync + git commit wrapper
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [commit, wip-sync, automation, atomic]
relates-to:
  - path: decisions/hn_promise_protection.md
    rel: extends
status: pending
created: 2026-05-02
updated: 2026-05-02
---

# commit 흐름 자동화 — wrapper

## 사전 준비
- 읽을 문서: `.claude/skills/commit/SKILL.md` Step 7.5·8, `.claude/scripts/docs_ops.py` cmd_wip_sync
- 자기증명 사례: 본 세션 e87690c·befed6a·4a3c215 — git commit 먼저 → wip-sync → 별 이동 commit 패턴 3회 반복

## 목표

`git commit`을 직접 호출하면 wip-sync(자동 이동·cluster 갱신·역참조 갱신)
가 commit 후로 밀려 별 이동 commit이 생긴다. SKILL.md SSOT는 "git commit
**직전**"이라 명시했지만 Claude가 반복 위반.

흐름 자체를 자동화 — Claude가 wrapper 1회 호출 → wrapper 내부에서 wip-sync
→ 자동 이동·cluster·역참조 갱신 staged → git commit 한 번에. 메커니즘
차단 (위반 불가능).

## 작업

**Acceptance Criteria**:
- [x] Goal: commit_finalize wrapper 신설. wip-sync → git add → git commit 한 흐름
  검증:
    review: review
    tests: pytest -m gate
    실측: 본 commit 자기증명 — wrapper 사용해 commit + 이동이 단일 commit으로 처리
- [x] `.claude/scripts/commit_finalize.sh` 신설 (또는 docs_ops.py 서브커맨드) ✅
- [x] commit/SKILL.md Step 7.5·8 통합 — wrapper 호출 1줄로 단순화 ✅
- [x] HARNESS_DEV=1 prefix 호환 (기존 bash-guard.sh 정합)
- [x] verdict 변수 처리: block 아닌 경우만 진행

## 결정 사항
(작업하면서 채움)

## 메모
- wrapper 위치: `.claude/scripts/commit_finalize.sh` (bash-guard.sh와 같은 결)
- 입력: VERDICT (env), 커밋 메시지 (-m 인자)
- 출력: 단일 commit (wip-sync 결과 포함)
- 본 세션에서 8 commit 중 3 commit이 이동 분리 → 위반율 37.5%. 메커니즘 차단으로 0%
