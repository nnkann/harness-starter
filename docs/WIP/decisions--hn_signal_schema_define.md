---
title: signal_* memory 파일 스키마 정의 (memory.md 보강)
domain: harness
problem: P11
s: [S11]
tags: [signal-schema, memory, ssot]
relates-to:
  - path: docs/decisions/hn_claude_dir_audit.md
    rel: caused-by
status: in-progress
created: 2026-05-18
updated: 2026-05-18
---

# signal_* memory 파일 스키마 정의

## Goal

`.claude/memory/signal_*.md` 파일이 7개 누적됐는데 memory.md에 스키마
정의 없음. 암묵적 컨벤션 → P11(동형 패턴 잠복) 직격.

**Acceptance Criteria**:
- [ ] Goal: S11 충족 — signal_* 파일 frontmatter 스키마(signal·domain·keywords·strength·candidate_p) memory.md에 SSOT 박제. 7개 파일 정합 확인 ✅
  검증:
    tests: 없음
    실측: 7개 signal_* 파일 frontmatter가 새 스키마와 정합. pre-check이 신규 signal_* 추가 시 스키마 검증 (선택적)
- [ ] 7개 파일 frontmatter 패턴 추출 → 공통 필드 식별
- [ ] memory.md "signal_* 파일 스키마" 섹션 신설 ✅
- [ ] signal_defense_success.md drift (운용 로그) — 본문 형식이 스키마와 정합한지 재점검

## 메모

- 본 wave에서 signal_defense_success.md 본문이 운용 로그(날짜+이벤트 append)로 drift 확인
- eval_harness.py:165-168이 본 형식에 의존 → 스키마에 "본문 — 운용 로그 누적 가능" 명시 필요
