---
title: review 에이전트 maxTurns 소진 시 verdict 누락
domain: harness
tags: [review, maxturns, bulk-commit, agent-spec, incident]
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
updated: 2026-04-21
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

### 즉시 (본 커밋 이후)

1. `--bulk` 플래그 신설 — 거대 업그레이드 시 review 건너뛰되 **정량
   가드로 대체**. 가드 실패 시 즉시 차단
2. 가드 항목 (전부 통과해야 커밋 허용):
   - 테스트 3종 (test-pre-commit / test-bash-guard / downstream-readiness)
   - dead link 0 (docs·rules·skills 내 마크다운 링크)
   - 날짜 suffix 잔재 0 (`_YYMMDD\.md$` archived 제외)
   - 변경 파일이 실제로 존재 (rename 누락 감지)
3. `--bulk` 사용 시 커밋 메시지에 `[bulk]` 태그 + `🔍 review: skip-bulk`
   로그 강제

### 자동 감지 (경고만, 강제 안 함)

pre-check이 `files > 30 or diff_lines > 1500` 이면 stderr에
"대규모 변경 감지. `/commit --bulk` 고려하세요" 한 줄 출력. 자동 적용은
안 함 (오탐 시 실제로 review 필요한 커밋이 skip될 위험).

### 이후 재발 시

가드가 실패하면 에러 메시지에 **어느 가드가 왜 실패했는지 + 대응책**
명시. 사용자가 원인 확인 후 수정 → 재시도.

## 재발 방지

- `.claude/rules/staging.md` — `--bulk` Stage 추가 (Stage 0 skip과 별개.
  verdict 대신 guards 통과 기록)
- `.claude/skills/commit/SKILL.md` — Step 7에 `--bulk` 분기 + 가드 실행
  로직
- `.claude/scripts/bulk-commit-guards.sh` 신설 — 가드 4종 통합 실행
- `.claude/scripts/pre-commit-check.sh` — 대규모 감지 경고 추가

상세는 `docs/decisions/hn_doc_naming.md` 참조 (본 incident의 원인 커밋)
및 `docs/harness/MIGRATIONS.md` v0.16.1 섹션.

## 메모

본 incident는 사용자가 "거대 업그레이드는 review 패스가 맞지 않냐"고
지적하며 발견. Claude가 처음에 "maxTurns 상한 접근은 정상 paused"라고
변명한 것은 틀렸음 (스펙상 중단 시에도 verdict 출력 의무). 사용자 지적
정당. 본 문서는 그 합리화를 취소하고 실제 원인을 기록한다.
