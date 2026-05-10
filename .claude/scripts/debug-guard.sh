#!/usr/bin/env bash
# UserPromptSubmit hook
# 버그/에러/실패/오류 관련어 감지 시:
#  - debug-specialist 호출 강제 안내
#  - BIT(bug-interrupt) Q1/Q2/Q3 블록 적용 안내
# 자가 발화 의존(rules/bug-interrupt.md) 규칙의 강제 트리거 보강 — P8/S8.
# jq 없이 동작하도록 python3으로 JSON 파싱.

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || echo "")

if [ -z "$PROMPT" ]; then
  exit 0
fi

# 키워드 사전: 에러·버그·실패·오류·원인 (한/영)
if ! echo "$PROMPT" | grep -qiE "에러|버그|실패|오류|크래시|충돌|error|bug|fail|exception|panic|crash|traceback|stacktrace|regression|broken|conflict"; then
  exit 0
fi

echo "⚠️ [debug-guard] 버그·에러·실패·오류·충돌 키워드가 감지됐다. 직접 수정하지 말고 debug-specialist 에이전트를 먼저 호출하라. 에이전트 호출 없이 코드 수정으로 바로 진행하는 것은 규칙 위반이다."
echo "⚠️ [debug-guard/BIT] 발견 즉시 .claude/rules/bug-interrupt.md 의 Q1/Q2/Q3 판단 블록을 작성하고 진행하라. 자가 발화에 의존한 미발화 패턴(P8)을 차단하기 위한 강제 트리거다."
exit 0
