---

title: eval 기본 모드 보고 구조 개선
domain: harness
tags: [eval, skill, reporting, memory]
problem: P6
s: [S6]
relates-to: []
status: completed
created: 2026-04-29
updated: 2026-04-30
---

# eval 기본 모드 보고 구조 개선

## 사전 준비
- 읽을 문서: `.claude/skills/eval/SKILL.md` (기본 모드 절차 섹션)
- 이전 산출물: 없음
- doc-finder fast scan: `docs/harness/hn_eval_advisor_migration.md` (완료, 다른 측면), `docs/guides/hn_eval_security_patch_port.md` (완료, 다른 측면) — SSOT 충돌 없음

## 목표
- eval 기본 모드 보고 구조를 flat 목록 → 거시/미시(단기블로커/장기부채) + 다음행동 계층으로 재구성
- eval 완료 시 `.claude/memory/project_eval_last.md` 덮어쓰기 저장 + MEMORY.md 인덱스 갱신
- 대화 출력은 거시 요약 + 단기 블로커만 간결하게, 상세는 memory로
- CPS 연결: 하네스 자체 품질 개선 (harness-starter CPS Solution)

## 작업 목록

### 1. eval SKILL.md 기본 모드 절차 개선
> kind: feature

**영향 파일**: `.claude/skills/eval/SKILL.md`

**변경 내용**:
- `/eval` 기본 모드 "4. 보고" 앞에 "4. 분류" 단계 추가
- 보고 형식을 거시/미시/다음행동 계층으로 교체
- "5. 저장" 단계 추가 (memory 덮어쓰기)

**Acceptance Criteria**:
- [ ] SKILL.md 기본 모드 절차에 분류(4) + 저장(5) 단계 추가됨
- [ ] 보고 형식 예시가 거시/미시/다음행동 구조로 명시됨
- [ ] memory 저장 절차(파일명·형식·MEMORY.md 갱신)가 명시됨
- [ ] 린터 에러 0 (`python3 .claude/scripts/pre_commit_check.py`)

## 결정 사항
- eval 기본 모드 절차를 1→2→3→4(분류)→5(보고)→6(저장) 6단계로 확장
- 대화 출력은 거시+단기블로커만 표시, 전체 상세는 `project_eval_last.md`에 덮어쓰기 저장
- memory 저장은 결과 0건이어도 항상 실행 (eval 실행 자체가 기록 가치)

## 메모
- CPS 갱신: 없음 (harness 내부 품질 개선, CPS Problem/Solution 변경 없음)
- 변경 파일: `.claude/skills/eval/SKILL.md` (기본 모드 절차 섹션)
