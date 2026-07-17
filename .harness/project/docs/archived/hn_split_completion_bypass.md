---
title: split-completion 우회 메커니즘 박제 (P12·S12)
domain: harness
problem: P12
s: [S12]
tags: [specification-gaming, reward-hacking, wip-discipline]
status: completed
created: 2026-05-18
updated: 2026-05-18
---

# split-completion 우회 메커니즘 박제 (P12·S12)

## Goal

S12 박제 — 다운스트림에서 다회 발생한 "sub-task 분리로 본 WIP completed
위장" 메커니즘을 starter `decisions/`에 일반 원칙으로 박는다. 메타 원칙
(강제 최소화)도 본 결정 본문에 한정 박제 (rule 승격은 사전 추상화로
판단해 유보 — codex·gemini 의견 합의).

**Acceptance Criteria**:
- [x] Goal: S12 박제 — split-completion 메커니즘 + 강제 최소화 메타 원칙을 단일 decision SSOT로 정착시킨다 (코드 게이트·rule 분리는 별 wave / 사례 누적 후)
  검증:
    tests: 없음
    실측: python .claude/scripts/pre_commit_check.py 통과 + grep으로 P12·S12 본문 인용 없이 번호 등장 확인
- [x] `docs/decisions/hn_split_completion_bypass.md` 본문 작성 — 메커니즘·외부 분류·메타 원칙·방어 원칙 통합. 다운스트림 고유 사례명·WIP 이름 박제 금지 (code-ssot.md "사례명 starter 본문 인용 금지" 준수)
- [x] `docs/guides/project_kickoff.md` P12·S12 등록 — Problem 표·Solution 표·P12 본문 섹션 3곳 모두 갱신

## 결정 사항

- D 채택 (codex·gemini 합의 + 사용자 승인): rule 파일 분리 안 함. 메타 원칙은 decision 본문에 흡수. 인벤토리 표는 만들지 않음 (사전 추상화 회피)
- 향후 3사례 누적 시 rule 승격 검토 (code-ssot.md "3+ reference rule" 자연 발현 대기)

## 메모

- 별 wave 후보: `.claude/rules/code-ssot.md` (P11 rule) 박제 시점 정합성 점검 — 본 wave가 적용한 "사전 추상화 회피" 기준이 code-ssot.md 자체에 적용됐는지 (3+ reference rule이 자기 박제에 사용됐는지, derived pointer 패턴이 도메인 무관 메타 원칙인지) 재검토
- 별 wave 후보: `.claude/` + `.claude/memory/` 전수 동형 패턴·사전 추상화 의심 점검 (사용자 지적)
- 별 wave 후보: 코드 게이트 (pre-check split-bypass 경고·verify-relates 양방향 caused-by) — 본 결정은 박제만, 도구는 별
- 외부 의견 합의: codex(D)·gemini(B) 모두 rule 분리 거부. D 채택 (인벤토리 보류). 다운스트림 보고서 원본은 본 wave에 인용되지 않음 (starter 본문 오염 회피)
