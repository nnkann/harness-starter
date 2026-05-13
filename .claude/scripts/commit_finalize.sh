#!/usr/bin/env bash
# commit_finalize.sh — wip-sync + git commit 단일 흐름 wrapper.
#
# 배경: SKILL.md Step 7.5는 "git commit 직전 wip-sync" SSOT인데 Claude가
# git commit 먼저 호출 → wip-sync → 별 이동 commit 패턴 반복 위반. 흐름
# 자체를 자동화해 위반 불가능하게 만든다 (메커니즘 차단).
#
# 사용법:
#   commit_finalize.sh -m "<title>" -m "<body>"
#
# 환경 변수:
#   VERDICT=pass|warn|block|""  — review 결과. block이면 wip-sync skip
#                                  (커밋 자체는 진행 — 호출자가 차단 판단)
#   HARNESS_DEV=1                — bash-guard.sh 통과용 (호출자가 설정)
#
# 동작:
#   1. VERDICT != block 이면 staged 파일 추출 → docs_ops.py wip-sync 실행
#   2. wip-sync가 변경한 파일 자동 git add (move·cluster·역참조 갱신 포함)
#   3. git commit "$@" 단일 호출
#
# 산출물: 1 commit (wip 이동·cluster 갱신·역참조 갱신 모두 포함)

set -euo pipefail

if [ -z "${HARNESS_DEV:-}" ]; then
  echo "❌ HARNESS_DEV=1 prefix 필수 (bash-guard.sh 통과)" >&2
  exit 2
fi

if [ "$#" -eq 0 ]; then
  echo "사용법: HARNESS_DEV=1 commit_finalize.sh -m \"<title>\" [-m \"<body>\"]" >&2
  exit 1
fi

VERDICT="${VERDICT:-}"

# 1. wip-sync (block이 아닐 때만)
#    docs_ops.py wip-sync 내부 staging 책임 (v0.42.5 보강):
#      - ✅ 마킹된 WIP: cmd_wip_sync L753에서 write_text 후 git add
#      - move (AC 모두 [x]): cmd_move가 (a) git mv로 rename staging
#                            + (b) v0.42.5 신규 — frontmatter 갱신 후 dest 재staging
#      - cluster-update: cmd_cluster_update가 v0.42.5 신규 — cluster.write 후 git add
#      - 역참조 갱신: _rewrite_relates_to L281에서 갱신 파일별 git add
#    → 외부 git add 불필요. wrapper는 단순 호출만.
if [ "$VERDICT" != "block" ]; then
  STAGED_FILES=$(git diff --cached --name-only | tr '\n' ' ')
  if [ -n "$STAGED_FILES" ]; then
    # Phase 4 (hn_harness_recovery_v0_41_baseline, 2026-05-13):
    # wip-sync 조건부 실행. staged에 docs/WIP/·docs/clusters/ 변경이 있을 때만
    # 호출. 매 commit ALWAYS 호출은 docs 외 변경에서 noop subprocess 누적.
    NEEDS_WIP_SYNC=$(echo "$STAGED_FILES" | tr ' ' '\n' | grep -cE '^docs/(WIP|clusters)/' || true)
    if [ "$NEEDS_WIP_SYNC" -gt 0 ]; then
      python3 .claude/scripts/docs_ops.py wip-sync $STAGED_FILES 2>&1 || true
    fi
  fi
fi

# 2. git commit
git commit "$@"
