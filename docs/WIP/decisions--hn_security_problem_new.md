---
title: starter CPS 보안 P# 신설 검토 (threat-analyst 정합 회복)
domain: cps
problem: P10
s: [S10]
tags: [security, cps-extension, threat-analyst-mapping]
relates-to:
  - path: docs/decisions/hn_claude_dir_audit.md
    rel: caused-by
status: in-progress
created: 2026-05-18
---

# starter CPS 보안 P# 신설 검토

## Goal

starter CPS Problems 표에 보안 P# 부재. threat-analyst·security.md가
S3(다운스트림 사일런트 페일)에 억지 매핑된 정합 약점 해소.

**Acceptance Criteria**:
- [ ] Goal: S10 catch-all → P13(또는 보안 영역 P#) 신설 검토 후 결정. 신설 시 P12 게이트(cp_{slug}.md 동반 staging) 작동 확인
  검증:
    tests: 없음
    실측: 신설 결정 시 project_kickoff.md Problems 표 + Solutions 표 + 본문 섹션 + cp_security_p13.md 동반 staging → pre-check 통과
- [ ] 외부 의견(codex·gemini) 수렴 — 보안 P# 신설 정당성 + 정의 1줄
- [ ] 결정 박제 — 신설 또는 보류 결론 + 근거

## 메모

- P10 catch-all 박는 조건: P1~P9 검토 후 안 맞을 때만. 보안은 어디에도 안 맞음 → P10 정합. **하지만 본 wave 본질은 catch-all 도피 아니라 신규 P# 신설 검토**
- 신설 시 cascade 영향: threat-analyst·security.md·skills 일부 serves: 갱신
- 본 wave 진입 시 P11/P12 wave 박제 흐름 학습 데이터 활용
