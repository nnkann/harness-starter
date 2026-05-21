---
reminder: agy CLI 결과 회수는 자동화하지 말고 수동 handoff로 운영
domain: harness
keywords: [agy, antigravity, cli, manual-handoff, stdout, automation]
strength: medium
candidate_p: P6
kv_group: harness/P6/ssot-validation
status: active
source: user
owner: codex
last_validated: 2026-05-21
---

`agy --print`는 사용자 VS Code 터미널에서 직접 실행하면 화면 응답은 온다.
하지만 Codex child process, Python/PowerShell bridge, stdout redirect,
PowerShell transcript 방식은 응답 본문 회수에 실패했다.

운영 원칙:

1. Codex가 agy용 명령어를 완성해서 제시한다.
2. 사용자가 VS Code 터미널에서 직접 실행한다.
3. 사용자가 agy 터미널 답변을 Codex 대화에 붙여준다.
4. Codex는 붙여준 답변을 근거로 판단·수정·커밋을 진행한다.

기본 명령:

```powershell
agy --dangerously-skip-permissions --print-timeout 10m --print "질문"
```

긴 프롬프트는 PowerShell here-string으로 제공한다.
