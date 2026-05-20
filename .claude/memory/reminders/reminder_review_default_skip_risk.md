---
reminder: review 기본 skip 정책이 하네스 자체 rules/skills/scripts 변경의 누락을 통과시킬 수 있음
domain: harness
keywords: [review, commit, default-skip, rules, skills, scripts, harness]
strength: weak
candidate_p: P8
kv_group: harness/P8/review-commit
status: active
source: user
owner: human
last_validated: 2026-05-20
---

# review default skip 재검토 리마인더

## 관찰

v0.52.1~v0.52.2 후속 흐름에서 문서/WIP 누락, 버전 범프 누락, SSOT 선확인
누락이 사용자 지적으로 연쇄 발견됐다. 현재 `/commit` 기본값은 review off이고,
`--review` 또는 deep/secret gate에서만 review가 호출된다.

## 회상 조건

- `.claude/rules/**`, `.claude/skills/**`, `.agents/skills/**`,
  `.claude/scripts/**`, `.codex/**`, `AGENTS.md`, `CLAUDE.md` 변경 커밋
- WIP/AC, 버전 범프, SSOT 통합 여부가 함께 걸리는 하네스 자체 변경
- 사용자가 "review 삭제?", "기본 review", "검토 없이 커밋"을 언급

## 현재 판단

사실 단정 금지. 이 reminder는 review 기본값을 즉시 바꾸라는 명령이 아니라,
다음 관련 wave에서 현재 정책(`/commit` 기본 review off)이 충분한지
재확인하라는 상태 파일이다.

## 후보 조치

- 하네스 자체 rules/skills/scripts 변경은 `--review` 기본 권장 또는 강제 조건 재검토
- `recommended_stage: deep` 조건이 현재 pre-check에서 충분히 산출되는지 확인
- review 비용과 누락 방지 효과를 최근 커밋 사례로 비교
