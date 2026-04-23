---
title: review 에이전트 maxTurns 소진 시 verdict 누락
domain: harness
tags: [review, maxturns, agent-spec, incident]
symptom-keywords:
  - review verdict 누락
  - agentId 리턴 중단
  - maxTurns 초과
  - 거대 커밋 review 실패
  - SendMessage 재호출
relates-to:
  - path: decisions/hn_doc_naming.md
    rel: caused-by
status: completed
created: 2026-04-21
updated: 2026-04-22
---

# review 에이전트 maxTurns 소진 시 verdict 누락

## 증상

v0.16.0 커밋(파일 61개, +1080/-223) 시 review 에이전트 호출이 `## 리뷰
결과` / `verdict:` 헤더 없이 **중간 진행 발화만 남기고 agentId 리턴**.

```
... (검증 진행 발화 8 tool_uses)
write-doc SKILL.md에서 "날짜 suffix는 incidents만" 표현이 결정문과
충돌하는지 검증한다. ...
agentId: a7830ae974205d174 (SendMessage로 계속)
```

commit 스킬의 verdict 파싱이 실패 → 1차 재호출(SendMessage)로 verdict
강제 요구 → 이때 비로소 `verdict: block` 내놓음.

## 원인

### 1. maxTurns 상한과 diff 규모 불일치

- `.claude/agents/review.md` frontmatter `maxTurns: 6` (hard 상한)
- 본 커밋 diff: 2353줄, 파일 61개
- review가 전수 검증 위해 Read 8회 소진 → 6 상한 초과 지점에서 자동 중단
- 중단 시 verdict 출력 의무(스펙 L469 "모든 tool 호출·검증 완료 후 **반드시
  위 형식으로 출력하고 종료**. 중간 진행 발화를 최종 응답으로 삼지 마라")
  미이행

### 2. review 스펙이 "turn 소진 시 강제 verdict"를 명확히 강제 안 함

L188 "6회로 부족하면 [주의] 보고 + 경계 표 참조"만 있고, 에이전트가 이를
준수 안 할 때의 가드가 없음. 결과적으로 에이전트 자율에 의존.

### 3. 거대 업그레이드는 review 설계 영역 밖

review는 **diff 단위 회귀·계약·스코프 검증** 도구 (staging.md). 파일 40+
일괄 rename + 참조 173건 치환 같은 의도 설계 작업은:
- 사람이 맥락·계획 가지고 진행
- grep·테스트·dead link 검사로 **정량 검증** 가능
- review가 아무리 잘 돌아도 "이 rename 매핑이 의도에 맞는가"는 판단 불가

즉 거대 업그레이드에 review를 돌리는 건 **도구 오용**.

## 해결

### 2026-04-22 재해석 (현재 유효)

거대 커밋은 **스코프를 나눠 작은 커밋 여러 개로 분리**한다. 스크립트
우회 경로를 만들지 않는다.

- pre-check이 `files > 30 or diff_lines > 1500` 감지 시 stderr에 "스코프
  분리 권장" 경고. 자동 분기·우회 플래그 없음. 사용자가 판단
- review maxTurns 예산 문제는 `docs/decisions/hn_review_tool_budget.md`
  의 조기 중단·알파 발동 설계에서 해결. review 자체가 거대 diff에 견디도록

### 과거 해법 (v0.16.1~v0.18.7 — 2026-04-22 폐기)

v0.16.1에서 `--bulk` 플래그 + 정량 가드 4종 도입. 2026-04-22 폐기:

- 가드 4종 중 거대 커밋 특유 위험을 잡는 건 dead link 하나뿐이었고,
  그건 pre-check Step 3.5(v0.18.6)에 이미 이식됨
- 나머지 3종(테스트 스위트·downstream-readiness·날짜 suffix)은 거대
  여부와 무관한 일상 정합성. bulk 전용일 이유 없음. bulk 가드 실행이
  Windows Git Bash에서 1분+ 걸리는 원인이기도 했음
- "review maxTurns 터지니까 우회"는 거대 커밋을 정당화하는 역방향 설계.
  답은 커밋을 쪼개는 것

관련 변경 (2026-04-22):
- `.claude/rules/staging.md` — bulk 스테이지·룰 3(docs rename ≥30% → bulk)·
  룰 F(--bulk 강제) 제거
- `.claude/skills/commit/SKILL.md` — --bulk 플래그·Stage bulk 섹션 제거
- `.claude/scripts/pre-commit-check.sh` — bulk 판정 분기 제거, 거대 변경
  경고 메시지를 "스코프 분리 권장"으로 재작성
- `.claude/scripts/bulk-commit-guards.sh` 파일 삭제
- `.claude/scripts/test-pre-commit.sh` T29(docs rename → bulk) 케이스 제거

## 재발 방지

- `docs/decisions/hn_review_tool_budget.md` — review 에이전트 조기 중단·
  알파 발동 설계로 거대 diff에서도 verdict 출력 의무 준수
- 거대 커밋 자체를 안 만드는 습관 — pre-check 경고가 체감 신호

## 메모

본 incident는 사용자가 "거대 업그레이드는 review 패스가 맞지 않냐"고
지적하며 발견. Claude가 처음에 "maxTurns 상한 접근은 정상 paused"라고
변명한 것은 틀렸음 (스펙상 중단 시에도 verdict 출력 의무). 사용자 지적
정당.

**2026-04-22 재해석**: 당시 해법(`--bulk` + 정량 가드)도 근본적으로 오판
이었음. 거대 커밋의 답은 **분리**이지 우회 경로가 아니다. 가드 4종 중
3종이 거대 여부 무관한 정합성 검사였고, bulk 전용일 이유가 없었으며,
가드 자체가 수십 초~수 분 걸려 존재 의의를 무너뜨렸다. 사용자가 "이따위
설계", "커밋을 나눠서 하면 훨씬 낫다"고 지적하며 폐기 결정. 원인 진단
(§원인)은 여전히 유효, 해법(§해결)만 재해석.
