#!/usr/bin/env bash
# implementation Step 0 init 완료 판정 (A4 의미 재정의, v0.34.0)
#
# 종료 코드:
#   0 — init 완료 (작업 진행)
#   2 — init 미완료 (차단)
#
# 판정 로직 (decisions/hn_init_gate_redesign.md ADR):
#   - docs/guides/project_kickoff.md 부재 → 차단
#   - docs/guides/project_kickoff.md status: sample 단독 → 차단
#   - 그 외 → 통과
#
# CLAUDE.md `## 환경` drift는 차단 사유 아님 (다운스트림 자율).
#
# SKILL.md Step 0가 본 스크립트를 직접 호출하지 않더라도, 회귀 테스트와
# 다운스트림 자가 점검 용도로 분리 보관.

set -e

KICKOFF="docs/guides/project_kickoff.md"

if [ ! -f "$KICKOFF" ]; then
  echo "init 미완료: $KICKOFF 부재" >&2
  exit 2
fi

# status: sample 검사 (정확 매칭 + YAML 인라인 주석 허용)
# 매칭: "status: sample"·"status:sample"·"status: sample # comment"·"status: sample  "
# 미매칭: "status: completed"·"status: in-progress"
if grep -qE "^status:[[:space:]]*sample([[:space:]]+#.*)?[[:space:]]*$" "$KICKOFF"; then
  echo "init 미완료: $KICKOFF가 sample 상태" >&2
  exit 2
fi

exit 0
