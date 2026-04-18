---
title: 하네스 구멍 정리 + 리뷰 구조 재확정
domain: harness
tags: [search, ide-context, incident-doc, completion-gate, review-agent]
status: in-progress
created: 2026-04-18
updated: 2026-04-18
---

# 하네스 구멍 정리 + 리뷰 구조 재확정

## Part A: 검색·문서 규칙 (반영 완료, 커밋 08bdfdc)

| 구멍 | 내용 | 상태 |
|------|------|------|
| 1. IDE 컨텍스트 오신뢰 | `<ide_opened_file>` 경로는 존재 확인 후 사용 | ✅ rules 반영 |
| 2. incident symptom-keywords 누락 | incidents/ 전용 필드 추가 | ✅ rules 반영 (스킬 수정 남음) |
| 3. completed 미결 묻힘 | 본문 미결 패턴 시 WIP 분리 강제 | ✅ rules 반영 (스킬 수정 남음) |
| 4. 검색 실패 escalation 부재 | 3단계 검색 + docs-lookup 위임 | ✅ rules 반영 |

### 남은 후속 (별도 WIP)

- write-doc 스킬: incident 생성 시 `symptom-keywords` 재질의
- commit 스킬: completed 전환 시 본문 미결 패턴 차단

## Part B: 리뷰 구조 — hook 포기, Agent tool 복원

### 확정된 결론

**리뷰는 hook이 아니라 commit 스킬 내부에서 Agent tool로 review 에이전트를 직접
호출하는 구조로 간다.** 이 구조는 공식 Claude Agent SDK가 보장하는 경로이고,
실제로 이 세션에서 호출 테스트로 정상 발화·응답 확인.

이전 "hook 기반 리뷰" 설계(v0.9.2에서 도입)는 이틀간 hook 미로를 만든 원인.
되돌린다.

### 검증된 팩트

| 항목 | 결과 | 근거 |
|------|------|------|
| Agent tool로 review 에이전트 호출 | ✅ 정상 발화·응답 | 이 세션 실제 호출, JSON 응답 수신 |
| review 에이전트가 Bash/Read/Glob/Grep 사용 | ✅ 작동 | review.md의 tools 필드에 정의, 호출 시 실행 확인 |
| prompt type hook은 single-turn, 도구 불가 | ❌ 리뷰 부적합 | 공식 문서 |
| prompt hook `$ARGUMENTS`에는 tool_input.command만 | diff 없음 | 직접 테스트 |
| command hook → prompt hook 간 데이터 전달 경로 | ❌ 없음 | 직접 테스트 |
| agent type hook은 PostToolUse 용으로 설계 | PreToolUse에서 부적합 | 공식 SDK 문서 |

### 설계 방향

```
commit 스킬 실행 (strict 모드 또는 --strict)
  ↓
  작업 잔여물 정리, 계획 문서 완료 처리
  ↓
  Agent tool 호출 (subagent_type: "review", prompt: diff + 맥락)
  ↓
  review 에이전트가 스스로:
    - Bash로 git diff --cached 확인
    - 3관점(회귀/계약/스코프) 검증
    - JSON 반환 {"ok": true/false, "block": bool, "warnings": [...]}
  ↓
  block: true면 차단, warnings만 있으면 커밋 메시지에 반영 후 진행
  ↓
  git commit + push
```

**PreToolUse hook은 기본 안전장치만 유지**: `pre-commit-check.sh` (린터, TODO/FIXME
검사, --no-verify 차단). 리뷰 로직은 전부 스킬 내부로.

### 반영 범위

| 파일 | 변경 |
|------|------|
| `.claude/skills/commit/SKILL.md` | "리뷰는 hook이 처리한다" 섹션 → "strict 모드면 Agent tool로 review 호출" 섹션 교체 |
| `.claude/settings.json` | 변경 없음 (이미 hook 제거됨, 커밋 1d165a3) |
| `.claude/agents/review.md` | 변경 없음 (이미 존재) |

## Part C: 다운스트림 전파 (별도 작업, 이 레포 범위 외)

하네스 스타터의 변경이 다운스트림 프로젝트에 반영되려면 harness-upgrade
경로로 전파 필요. 이 WIP는 harness-starter 범용 문서이므로 다운스트림 프로젝트
고유 고유명사는 기록하지 않는다.

## 우선순위

| 우선순위 | 항목 | 범위 |
|---------|------|------|
| P0 | commit 스킬 SKILL.md에 Agent tool 호출 단계 추가 | 이 레포, 이 세션에서 |
| P1 | write-doc 스킬 symptom-keywords 재질의 | 별도 WIP |
| P1 | commit 스킬 completed 전환 시 본문 미결 패턴 차단 | 별도 WIP |
| P2 | 이 WIP 승격 시 "이번 세션" 표현 날짜로 구체화 | 승격 시점 |
