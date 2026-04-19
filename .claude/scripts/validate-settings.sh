#!/bin/bash
# settings.json validation — Claude Code 재로드 시 schema 에러 방지.
#
# 배경: Claude Code가 settings.json 로드 중 schema error 만나면 응답으로
# 전체 schema를 덤프 (~20k tokens). 이번 세션에서 2번 발생해 40k 허비.
# settings.json 수정 후 Claude Code가 재로드하기 전에 본 스크립트로 1차
# 검증 → 실패 시 롤백 유도.
#
# 검증 항목 (최소):
# 1. JSON 파싱 가능
# 2. hooks 최상위 객체
# 3. 각 hook 이벤트 배열
# 4. 각 배열 원소가 matcher + hooks 필드 보유
# 5. hooks 배열 원소가 type + command (or prompt) 보유
# 6. 알려진 이벤트 이름만 사용 (SessionStart·Stop·PostCompact·
#    PreToolUse·PostToolUse·UserPromptSubmit·SessionEnd·SubagentStop 등)
# 7. matcher 값이 문자열 (정규식 또는 tool 이름)
#
# 공식 스키마 변경 시 본 스크립트도 갱신 필요.
#
# 사용: bash .claude/scripts/validate-settings.sh [path]
# 종료: 0=유효, 1=문제 있음 (stderr에 첫 에러 출력)

set -u
PATH_JSON="${1:-.claude/settings.json}"

if [ ! -f "$PATH_JSON" ]; then
  echo "[OK] settings.json 없음 — 검증 불필요"
  exit 0
fi

# 1. JSON 파싱
if command -v python3 >/dev/null 2>&1; then
  PARSE=$(python3 -c "
import json, sys
try:
    with open('$PATH_JSON') as f:
        data = json.load(f)
    print('OK')
except json.JSONDecodeError as e:
    print(f'JSON 파싱 실패: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
  if [ "$PARSE" != "OK" ]; then
    echo "[FAIL] $PARSE" >&2
    exit 1
  fi
else
  # python3 없으면 node 시도
  if command -v node >/dev/null 2>&1; then
    node -e "JSON.parse(require('fs').readFileSync('$PATH_JSON','utf8'))" 2>/dev/null || {
      echo "[FAIL] JSON 파싱 실패 (node)" >&2
      exit 1
    }
  else
    echo "[WARN] python3/node 없음 — JSON 검증 생략" >&2
  fi
fi

# 2. 알려진 이벤트 이름 확인 — python3 기반
export PATH_JSON
python3 <<'PYEOF'
import json, sys, os

path = os.environ['PATH_JSON']
with open(path) as f:
    data = json.load(f)

known_events = {
    'SessionStart', 'SessionEnd', 'Stop', 'SubagentStop',
    'PreToolUse', 'PostToolUse', 'PostCompact', 'PreCompact',
    'UserPromptSubmit', 'Notification',
}
valid_types = {'command', 'prompt', 'agent'}

errors = []
warnings = []

# hooks 섹션
hooks = data.get('hooks', {})
if not isinstance(hooks, dict):
    errors.append(f"hooks는 객체여야 함 (현재: {type(hooks).__name__})")
else:
    for event, arr in hooks.items():
        if event not in known_events:
            warnings.append(f"알 수 없는 이벤트: {event} (공식 이벤트: {sorted(known_events)})")
        if not isinstance(arr, list):
            errors.append(f"hooks.{event}는 배열이어야 함")
            continue
        for i, entry in enumerate(arr):
            if not isinstance(entry, dict):
                errors.append(f"hooks.{event}[{i}]는 객체여야 함")
                continue
            if 'matcher' not in entry:
                errors.append(f"hooks.{event}[{i}] matcher 필드 누락")
            elif not isinstance(entry['matcher'], str):
                errors.append(f"hooks.{event}[{i}].matcher는 문자열이어야 함")
            inner = entry.get('hooks')
            if not isinstance(inner, list):
                errors.append(f"hooks.{event}[{i}].hooks는 배열이어야 함")
                continue
            for j, h in enumerate(inner):
                if not isinstance(h, dict):
                    errors.append(f"hooks.{event}[{i}].hooks[{j}]는 객체여야 함")
                    continue
                t = h.get('type')
                if t not in valid_types:
                    errors.append(f"hooks.{event}[{i}].hooks[{j}].type 이상 값: {t} (허용: {sorted(valid_types)})")
                if t == 'command' and 'command' not in h:
                    errors.append(f"hooks.{event}[{i}].hooks[{j}] command 필드 누락 (type=command)")
                if t == 'prompt' and 'prompt' not in h:
                    errors.append(f"hooks.{event}[{i}].hooks[{j}] prompt 필드 누락 (type=prompt)")

if errors:
    print("[FAIL]", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)

if warnings:
    print("[WARN]", file=sys.stderr)
    for w in warnings:
        print(f"  - {w}", file=sys.stderr)

print("[OK] settings.json 검증 통과")
PYEOF
