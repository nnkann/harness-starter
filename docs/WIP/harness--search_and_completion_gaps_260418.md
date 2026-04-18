---
title: 하네스 구멍 정리 — 검색/완료 규칙 + 리뷰 hook 설계 실패 분석
domain: harness
tags: [search, ide-context, incident-doc, completion-gate, hook-architecture, review-agent]
status: in-progress
created: 2026-04-18
updated: 2026-04-19
---

# 하네스 구멍 정리 + 리뷰 hook 재설계

## 이 문서는

2026-04-18 ~ 2026-04-19 세션의 **검증된 팩트**와 **다음 세션 진입점**.
추측 없이 실제 테스트/문서로 확인된 것만 기록.

## Part A: 검색·문서 규칙 (반영 완료, 커밋 08bdfdc)

### 반영된 rules/docs.md 변경

| 구멍 | 내용 | 상태 |
|------|------|------|
| 1. IDE 컨텍스트 오신뢰 | `<ide_opened_file>` 경로는 존재 확인 후 사용 | ✅ rules 반영 |
| 2. incident symptom-keywords 누락 | incidents/ 전용 필드 추가 | ✅ rules 반영 (스킬 수정 남음) |
| 3. completed 미결 묻힘 | 본문 미결 패턴 시 WIP 분리 강제 | ✅ rules 반영 (스킬 수정 남음) |
| 4. 검색 실패 escalation 부재 | 3단계 검색 + docs-lookup 위임 | ✅ rules 반영 |

### 남은 후속 (스킬 수정)

- write-doc 스킬: incident 생성 시 `symptom-keywords` 재질의
- commit 스킬: completed 전환 시 본문 미결 패턴 차단

## Part B: 리뷰 hook 설계 실패 분석 (이번 세션 핵심)

### 검증된 팩트 (Context7 공식 문서 + 직접 테스트)

| 항목 | 결과 | 근거 |
|------|------|------|
| prompt hook은 single-turn | ❌ 도구 불가 | Context7: "single-turn LLM evaluations" |
| prompt hook `$ARGUMENTS` 내용 | tool_input.command만 | 직접 테스트 PATH-B (커밋 d439d77) |
| command hook → prompt hook 데이터 전달 | ❌ 안 됨 | PATH-B 테스트에서 additionalContext 미전달 |
| agent hook 발화 (VSCode) | ❌ 발화 안 됨 | 단독 테스트에서 ok:false 지시에도 통과 |
| agent hook 도구 접근 (이론) | ✅ 가능 | Context7: "multi-turn tool access up to 50 turns" |
| claude CLI (v2.1.112) | ✅ 설치됨 | `which claude` 확인 |
| claude -p 헤드리스 호출 | ✅ 작동 | 직접 테스트 |

### 과거 진단 오류 정정

| 주장 | 사실 |
|------|------|
| "prompt hook $ARGUMENTS 주입 방식 재검토 필요" (4/18 WIP) | **허위**. $ARGUMENTS는 설계대로 hook input JSON 주입. 문제는 그 JSON에 diff가 없는 것 |
| "v0.9에서 리뷰 hook 발화 봤음" (사용자 기억) | v0.9.2~v1.2.0은 matcher 문법 오류로 hook 전체 무력. 사용자가 본 것은 **commit 스킬 내부 Agent 호출**(20d2127 시점). v0.9.2에서 스킬→hook 이관 후 사실상 작동 안 했음 |
| "VSCode 확장에서 agent hook 미동작" (v1.2.3 커밋 메시지) | **재확인됨**. 이번 세션 단독 테스트에서 agent hook의 ok:false 응답이 무시됨 |

### 남은 유일한 현실적 구조 = command hook + claude CLI

prompt/agent type hook 모두 이 환경(VSCode Claude Code Extension)에서 리뷰
기능으로 못 씀이 확정. 남은 경로:

```
command hook (셸 스크립트)
  ↓
  git diff --cached 확보
  위험도 판단 (pre-commit-check.sh 기존 로직 재활용)
  필요 시 claude -p --allowedTools "Read,Grep" 로 리뷰 요청
  ↓
  exit 0 (허용) 또는 exit 2 (차단)
```

### 현재 settings.json 상태 (이 세션 커밋 후)

- prompt/agent type hook **전부 제거**
- command hook(pre-commit-check.sh)만 유지
- **리뷰 없음 상태** — 다음 세션에서 claude -p 통합 구현 필요

## 다음 세션 진입점

### 즉시 시작할 일: command hook + claude -p 리뷰 통합

**설계 원칙**: 책임 분리
- **command hook 역할**: diff 확보, 위험도 판단, strict/light 분기, claude CLI 호출, exit code 결정
- **claude CLI(LLM) 역할**: diff 텍스트만 받아 회귀/계약/스코프 관점 JSON 응답

**구현 스케치 (다음 세션에서 검증)**:

```bash
# .claude/scripts/pre-commit-review.sh (신규)
DIFF=$(git diff --cached)
STAT=$(git diff --cached --numstat)
HARNESS_LEVEL=$(grep -m1 '하네스 강도:' CLAUDE.md | sed 's/.*:\s*//')

# 위험도 판단 (기존 pre-commit-check.sh 로직 재활용)
NEEDS_REVIEW=0
[ "$HARNESS_LEVEL" = "strict" ] && NEEDS_REVIEW=1
# ... light 조건들 ...

if [ "$NEEDS_REVIEW" = "1" ]; then
  RESULT=$(echo "$DIFF" | claude -p "$(cat .claude/prompts/review.md)" \
    --allowedTools "Read,Grep,Glob" \
    --output-format json)
  # JSON 파싱해서 ok:false면 exit 2
fi

exit 0
```

### 검증 필요 사항

1. `claude -p` 안에서 Bash는 허용 가능한지 (`--allowedTools "Bash,Read,Grep,Glob"`)
2. `--output-format json` 응답 포맷 (schema 확인 필요)
3. 호출 지연 — 커밋마다 LLM 호출은 체감 느림. 위험도 게이트로 필터링 필수
4. stagelink에도 동일 구조 배포 (harness-upgrade 경유)

### 절대 하지 말 것 (이 세션의 교훈)

- prompt hook이나 agent hook으로 리뷰 기능 부활시키려는 시도 금지. 둘 다 막혔음
- "$ARGUMENTS 어떻게 주입할까" 고민 금지. 안 됨
- 즉시 구현 점프 금지. 위 "검증 필요 사항"부터 하나씩 테스트

## 커밋 이력 (이 세션)

- `08bdfdc` (4/18) 검색/완료 규칙 + prompt hook matcher 보완 v1.3.0 [skip-review]
- `7579867` (4/19) 리뷰 prompt에 도구 사용 지시 추가 — 실패 테스트
- `d439d77` (4/19) command→prompt 데이터 전달 경로 PATH-B 확인
- `cf36f57` (4/19) agent type 발화 검증 테스트 (덮여서 무효)
- `eee83c4` (4/19) agent type 단독 — 미발화 확정
- (이 커밋) 실험 흔적 정리 + 핸드오프 문서 갱신

## 우선순위

| 우선순위 | 항목 | 범위 |
|---------|------|------|
| P0 | command hook + claude -p 리뷰 통합 | 이 레포 pre-commit-review.sh 신규 |
| P0 | stagelink에 동일 구조 전파 | harness-upgrade |
| P1 | write-doc 스킬 symptom-keywords 재질의 | 별도 WIP |
| P1 | commit 스킬 completed 전환 시 본문 미결 패턴 차단 | 별도 WIP |
| P2 | promotion-log/이 WIP의 허위 진단 기록 완전 정리 | 문서 작업 |
