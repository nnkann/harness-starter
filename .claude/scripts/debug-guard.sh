#!/usr/bin/env bash
# UserPromptSubmit hook — 버그/에러/원인 키워드 감지 시 debug-specialist 강제 주입
# jq 없이 동작하도록 python3으로 JSON 파싱

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || echo "")

# 키워드 없으면 조용히 통과
if ! echo "$PROMPT" | grep -qiE "에러|버그|오류|원인|error|bug"; then
  exit 0
fi

echo "⚠️ [debug-guard] 버그·에러·원인 키워드가 감지됐다. 직접 수정하지 말고 debug-specialist 에이전트를 먼저 호출하라. 에이전트 호출 없이 코드 수정으로 바로 진행하는 것은 규칙 위반이다."
exit 0
