---
title: guard 스크립트 4개 차단 규칙 P12 3문항 점검
domain: harness
problem: P12
s: [S12]
tags: [guard-scripts, force-minimization, p12-three-questions]
relates-to:
  - path: docs/decisions/hn_split_completion_bypass.md
    rel: extends
status: in-progress
created: 2026-05-18
---

# guard 스크립트 4개 차단 규칙 P12 3문항 점검

## Goal

gemini 점검에서 "P12(강제 최소화) 관점 1순위 청산 대상"으로 지목된 guard
스크립트 4개의 차단 규칙을 P12 3문항으로 정밀 검토. 결정적 정합성·
되돌릴 수 없는 사고 영역 아닌 차단은 경고로 전환.

**Acceptance Criteria**:
- [ ] Goal: S12 충족 — `bash-guard.sh`·`write-guard.sh`·`stop-guard.py`·`post-compact-guard.py` 4개 스크립트 차단 규칙 각 항목을 P12 3문항으로 검토하고, 차단 부적합 항목은 경고로 전환 또는 폐기
  검증:
    tests: 없음 (코드 변경 시 회귀 테스트 추가)
    실측: 각 스크립트 차단 규칙별로 (a) 정답 1개 영역인가 (b) false positive 시 정당 작업 차단되는가 (c) 차단 우회 비용 0인가 결정
- [ ] 4개 스크립트 차단 규칙 인벤토리 작성 — 어떤 패턴을 차단하는지 본문 grep으로 추출
- [ ] 각 규칙 P12 3문항 통과 여부 판정 → 차단 유지·경고 전환·폐기 분류
- [ ] 변경 필요 항목 구현 + 회귀 테스트

## 메모

- 원본 지목: codex/gemini 의견 (decisions/hn_claude_dir_audit 본 wave 결과)
- 진입 조건: 본 wave가 차단 행동 코드 영역이라 코드 변경 동반. 점검만으로도 별 wave 가치
