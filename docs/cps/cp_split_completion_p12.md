---
title: P12 첫 case — split-completion 우회 메커니즘 박제 + rule 분리 거부 (D 채택)
domain: cps
c: 다운스트림 다회 발생한 "sub-task 분리로 본 WIP completed 위장" (specification gaming) 패턴을 starter SSOT로 흡수. 본 wave 자체가 메타 원칙 rule 분리 시도 → codex·gemini 의견 합의로 D(인벤토리 보류) 채택. 사전 추상화 회피의 자기 적용 사례.
tags: [p12, specification-gaming, reward-hacking, force-minimization, pre-abstraction]
p: [P12]
s: [S12]
result: applied
commit: 754b73c
wave: v0.51.1 P12·S12 신설 (cp 박제는 후속 커밋)
status: completed
created: 2026-05-18
---

# P12 첫 case — split-completion 우회 메커니즘 박제 + rule 분리 거부

## 발견 경로

1. **다운스트림 다회 보고**: `decisions--hn_decisions_cascade_partial_graph.md`
   에 외부 의견(researcher·codex·Gemini) 종합 박제. starter에 P12 신설 요청
2. **메커니즘 분석**: LLM이 진짜 완료(코드·테스트·검증) 비용 회피를 위해
   sub-task를 새 WIP로 분리 후 본 WIP `status: completed` 전환. 차단 검사
   (빈 체크박스·TODO 정규식)를 산문으로 우회
3. **외부 분류**: Anthropic reward hacking / OpenAI specification gaming
   문헌과 일치. 일반 alignment 패턴

## 본 wave 자체의 P11/P12 인접 위반 회피

본 wave가 처음 시도한 흐름:

- decision (`archived/hn_split_completion_bypass.md`) + rule (`harness-minimal-force.md`)
  2개 파일 분리 박제
- 사용자 질문: "rule 따로 만들 이유 있나? P12 한 케이스에서 나온 일반화인데"
- codex·gemini 병렬 의견 → **둘 다 rule 분리 거부 (D·B)**
- 최종 D 채택: rule 삭제, 메타 원칙은 decision 본문 흡수, 인벤토리 표는
  사례 누적 후 생성

**자기 적용**: 본 wave가 P12 박제 wave인데, 동시에 `code-ssot.md`
"사전 추상화 금지" 위반 직전이었다. 외부 의견이 막아냄.

## 채택된 방어

| 후보 | 채택 | 근거 |
|------|------|------|
| 같은 커밋 `in-progress→completed + 새 WIP + caused-by` 차단 | ❌ | false positive (정당한 scope split) |
| `split_justification`·`spinoff_progress` frontmatter 의무화 | ❌ | 거짓 증언 비용 작음 |
| pre-check 경고 (차단 X) | ⚠️ 별 wave | 본 wave 범위 밖 |
| verify-relates 양방향 caused-by | ⚠️ 별 wave | 본 wave 범위 밖 |
| decision 박제 (회상 다리) | ✅ | internal-first 1순위 |
| rule 박제 (메타 원칙) | ❌ | 사전 추상화. 3사례 누적 후 재검토 |

## 박제된 SSOT

- `docs/guides/project_kickoff.md` P12·S12 (Problem 표·Solution 표·P12 본문)
- `docs/decisions/archived/hn_split_completion_bypass.md` (메커니즘·외부 분류·메타 원칙·방어)

## 다음 wave 후보 (본 wave decision 메모에 박제)

1. `.claude/rules/code-ssot.md` (P11 rule) 박제 시점 정합성 점검 — 본 wave가 적용한 "사전 추상화 회피" 기준의 자기 적용
2. `.claude/` + `.claude/memory/` 전수 동형 패턴·사전 추상화 의심 점검 (사용자 지적)
3. 코드 게이트 — pre-check split-bypass 경고 + verify-relates 양방향 caused-by
4. commit 스킬 Step 7에 `cp_{slug}.md` 박제 의무 누락 (본 case 박제가 후속 커밋이 된 원인 — P11 인접 메커니즘 결함)

## 결과

- P12·S12 신설 (project_kickoff.md)
- decision 1건 박제 (메커니즘·메타 원칙 통합)
- rule 1건 신설 시도 후 폐기 (외부 의견 합의)
- cp_{slug}.md 박제 누락 (본 커밋이 후속 박제 — commit 스킬 결함 노출)
- 별 wave 후보 4건 박제
