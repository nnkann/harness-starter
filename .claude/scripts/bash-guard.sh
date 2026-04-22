#!/bin/bash
# PreToolUse Bash hook — jq로 명령 파싱 후 정밀 검증.
#
# 공식 문서 인용:
# > "Bash permission patterns that try to constrain command arguments are
# >  fragile. ... For more reliable URL filtering, consider: Use PreToolUse
# >  hooks: implement a hook that validates URLs in Bash commands ..."
#
# 단일 hook이 모든 검증을 담당. matcher 패턴은 Bash tool name만 매칭.
# 광역 와일드카드 매처(Bash(* X *))는 substring/glob 동작이 fragile해서
# 우연 매칭 + 우연 통과가 모두 발생. 본 스크립트로 통일.
#
# 종료 코드:
#   0 = 통과
#   2 = 차단 (stderr 메시지를 Claude에게 보냄)

# stdin: PreToolUse hook JSON
INPUT=$(cat)

# jq가 있으면 사용, 없으면 grep으로 fallback
if command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
else
  # fallback: 단순 grep (정확하지 않을 수 있음)
  COMMAND=$(echo "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/^"command"[[:space:]]*:[[:space:]]*"//;s/"$//')
fi

# 빈 명령은 통과
[ -z "$COMMAND" ] && exit 0

# ─────────────────────────────────────────────
# 검증 1: --no-verify 플래그 (commit/push hook 우회)
# bash 내장 [[ =~ ]] 사용 — echo|grep 대비 ~10ms 절감 (매 Bash 호출마다)
# ─────────────────────────────────────────────
if [[ $COMMAND =~ (^|[[:space:]])--no-verify([[:space:]]|$) ]]; then
  echo "❌ --no-verify 금지 (pre-commit/pre-push hook 우회)." >&2
  exit 2
fi

# ─────────────────────────────────────────────
# 검증 2: git commit -n (--no-verify의 short form)
# 토큰 분리 주의: eval "TOKENS=($COMMAND)"는 금지 — $COMMAND 안의
# $(...)나 백틱이 실제 실행되어 hook이 임의 명령 실행 경로가 됨.
# ─────────────────────────────────────────────
if [[ $COMMAND =~ ^[[:space:]]*git[[:space:]]+commit([[:space:]]|$) ]]; then
  # quoted 영역 제거 후 -n 토큰 검사 (sed는 $COMMAND 평가 안전 — 외부 실행 없음)
  UNQUOTED=$(echo "$COMMAND" | sed -E 's/"[^"]*"//g; s/'"'"'[^'"'"']*'"'"'//g')
  if [[ $UNQUOTED =~ (^|[[:space:]])-n([[:space:]]|$) ]]; then
    echo "❌ git commit -n 금지 (verify 우회). bash -n 같은 다른 -n은 영향 없음." >&2
    exit 2
  fi
fi

# ─────────────────────────────────────────────
# 검증 3: .claude/tmp/ 잔재 재발 방지
# hn_memory.md — tmp 개념 폐기. .claude/memory/ 흡수.
# Claude가 수동 실행으로 잔재 파일 생성하는 경로 차단.
# ─────────────────────────────────────────────
if [[ $COMMAND =~ \.claude/tmp/ ]]; then
  echo "❌ .claude/tmp/ 는 폐기됨. 세션 snapshot은 .claude/memory/session-* 사용." >&2
  echo "   근거: docs/decisions/hn_memory.md" >&2
  exit 2
fi

# ─────────────────────────────────────────────
# 검증 4: `git commit` 직접 호출 차단 — commit 스킬 강제 경유 (audit #8)
#
# 이유: pre-check·review·진척도 갱신·추적 라인이 모두 commit 스킬에 있음.
#       Bash `git commit` 직접 호출은 이 방어선 전체를 우회.
# 경유 표시: commit 스킬이 최종 커밋 시 `HARNESS_COMMIT_SKILL=1` prefix 세팅.
# 이스케이프: `HARNESS_DEV=1` (기존 업스트림 push 가드와 동일 규약).
#
# `git commit --help`·`git commit -v` 읽기 전용 호출은 `COMMAND` 안에 해당
# 옵션이 있으면 통과시킴 (도움말·dry-view는 커밋 생성 안 함).
# ─────────────────────────────────────────────
if [[ $COMMAND =~ ^[[:space:]]*git[[:space:]]+commit([[:space:]]|$) ]]; then
  # 읽기 전용 옵션은 통과
  if [[ $COMMAND =~ (^|[[:space:]])(--help|--dry-run|-h)([[:space:]]|$) ]]; then
    exit 0
  fi
  # 이스케이프 해치 (HARNESS_DEV=1 또는 HARNESS_COMMIT_SKILL=1 prefix)
  if [[ $COMMAND =~ (^|[[:space:]])HARNESS_(DEV|COMMIT_SKILL)=1([[:space:]]|$) ]]; then
    exit 0
  fi
  # 그 외 git commit 직접 호출 → 차단
  echo "❌ git commit 직접 호출 금지 (audit #8)." >&2
  echo "   → commit 스킬 사용: /commit  또는  Skill tool에서 commit 호출" >&2
  echo "   이스케이프(긴급): HARNESS_DEV=1 git commit -m ..." >&2
  echo "   근거: 스킬 우회 시 pre-check·review·진척도 갱신·추적 라인 누락" >&2
  exit 2
fi

exit 0
