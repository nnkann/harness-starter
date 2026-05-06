---
title: 침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계
domain: harness
problem: P4
solution-ref:
  - S4 — "단일 hook + 금지 규칙 (부분)"
  - S3 — "5중 방어 (부분)"
tags: [defense, signal, harness-upgrade, internalization, p4, p3]
relates-to:
  - path: harness/MIGRATIONS.md
    rel: references
status: completed
created: 2026-05-06
updated: 2026-05-06
---

# 침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계

## 사전 준비
- 읽을 문서: .claude/skills/harness-upgrade/SKILL.md (Step 10 완료 처리), .claude/scripts/bash-guard.sh (차단 경로)
- 이전 산출물: Wave A (피드백 채널), Wave B (MVR)
- MAP 참조: P4 defends-by: hooks / enforced-by: bash-guard.sh | P3 served-by: harness-upgrade

## 목표

1. **방어 가시화**: bash-guard.sh 차단 발생 시 `.claude/memory/signal_defense_success.md`에 짧게 기록
   - "이 규칙이 살아있다"는 데이터 축적
   - eval --harness가 기록 존재 여부로 방어 활성 상태 확인 가능
2. **지식 내면화**: harness-upgrade Step 10 완료 직전에 "이번 업그레이드로 강화된 방어 기전 설명" 단계 추가
   - 에이전트가 직접 설명하는 과정에서 지식이 내면화됨
   - 다운스트림 사용자가 "왜 이런 제약이 있는지" 이해하게 됨

CPS 연결: S4 "차단 성공 기록 레이어" + S3 "5중 방어 + 지식 전파"

## 작업 목록

### Phase 1. bash-guard.sh — 차단 시 signal 기록

**영향 파일**: .claude/scripts/bash-guard.sh

**주의사항**:
- signal 파일 Write는 stdout/stderr 오염 없이 background에서 조용히 실행해야 함. bash-guard.sh exit 2 직전에 추가.
- signal 파일 format은 memory.md "신호 파일" SSOT 준수. 빠른 append 방식 사용.
- 차단 유형별 기록 (--no-verify / -n / worktree / eval간접실행 / git commit직접). "왜 차단됐는가"가 데이터 가치.
- bash-guard.sh 자체가 hook이므로 파일 I/O 실패해도 차단 자체는 유지 (exit 2 보장).

**Acceptance Criteria**:
- [x] Goal: bash-guard.sh가 차단(exit 2) 시 `.claude/memory/signal_defense_success.md`에 차단 유형·날짜를 append하고, eval --harness가 이 파일을 읽어 "방어 활성" 상태를 보고한다
  검증:
    review: review
    tests: bash .claude/scripts/test-bash-guard.sh (기존 23케이스 회귀)
    실측: echo '{"tool_input":{"command":"git commit -m test"}}' | bash .claude/scripts/bash-guard.sh; cat .claude/memory/signal_defense_success.md

### Phase 2. harness-upgrade — 방어 기전 설명 단계

**영향 파일**: .claude/skills/harness-upgrade/SKILL.md (Step 10 완료 처리 섹션)

**주의사항**:
- Step 10 완료 보고 직전(커밋 직후)에 삽입. 커밋 흐름을 방해하지 않도록 "완료 보고" 다음에 별도 섹션으로.
- 설명 대상: 이번 업그레이드에서 변경된 .claude/rules/*.md, .claude/scripts/, agents/review.md 중 방어 기전 관련 항목만.
- "설명"은 1~3줄 핵심만. 장문 금지. MIGRATIONS.md 변경 내용에서 추출.
- 자동화 불가 검증: Claude 행동 변화는 운용에서 확인 필요.

**Acceptance Criteria**:
- [x] Goal: harness-upgrade Step 10 완료 직후 "이번 업그레이드로 강화된 방어 기전" 요약 설명 단계가 추가되어, 다운스트림 사용자가 새 방어 기전의 Why를 이해할 수 있다
  검증:
    review: self
    tests: 없음
    실측: SKILL.md Step 10 완료 처리 섹션에서 "방어 기전 설명" 단계 확인 (자동화 불가 — 운용에서 확인 필요)

### Phase 3. eval --harness — 방어 활성 기록 검증 항목 추가

**영향 파일**: .claude/skills/eval/SKILL.md

**주의사항**:
- signal_defense_success.md 존재 여부만 확인. 내용 파싱까지 하지 않음 (단순성 우선).
- "없음"이 반드시 문제는 아님 (방어가 한 번도 트리거 안 됐을 수 있음). 정보 제공만.

**Acceptance Criteria**:
- [x] Goal: eval --harness 보고에 "방어 활성 기록" 항목이 추가되어, signal_defense_success.md 존재 여부와 최근 기록을 표시한다
  검증:
    review: self
    tests: 없음
    실측: eval --harness 보고 형식에서 "방어 활성 기록" 항목 확인

## 결정 사항
- bash-guard.sh _record_defense() 함수: background append (`&`), 실패 시 2>/dev/null 무시 — hook 실행시간·exit code 영향 없음. → 반영: .claude/scripts/bash-guard.sh
- harness-upgrade Step 10 6번 단계: What이 아니라 Why 포함 강제. MIGRATIONS.md에서 추출. 없으면 "없음" 한 줄. → 반영: .claude/skills/harness-upgrade/SKILL.md
- eval --harness 항목 6번(방어 활성 기록) → 기존 6번(피드백 리포트)은 7번으로 번호 이동. → 반영: .claude/skills/eval/SKILL.md
- CPS S4 승격 상태 갱신: "추가 방어 레이어 (v0.38.3)" 명시. → 반영: docs/guides/project_kickoff.md
- CPS 갱신: S4 승격 상태 갱신 완료.

## 메모
- doc-finder: signal_defense_success.md 기존 파일 없음. 새로 생성.
- bash-guard.sh에 I/O 추가 시 hook 실행 시간 증가 우려 → background append로 최소화.
- CPS 갱신: S4 "추가 방어 레이어" 구현 완료 시 승격 상태 갱신 예정.
