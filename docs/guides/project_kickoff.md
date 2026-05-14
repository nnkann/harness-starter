---
title: harness-starter CPS — C 판단 프롬프트
domain: harness
tags: [cps, kickoff]
status: in-progress
created: 2026-04-20
updated: 2026-05-14
---

# harness-starter CPS (C 판단 프롬프트)

> **자라지 않음**. 새 작업이 들어오면 C(맥락) 판단을 위한 짧은 감각 도구.
> wave별 case 박제는 `docs/cps/cp_{slug}.md` + git history.
> 자세히: `docs/decisions/hn_harness_73pct_cut.md` §S-1.
> 압축 전 491줄 본문: `docs/archived/hn_kickoff_pre_73pct_cut.md`.

## Context (이 프로젝트는 무엇인가)

AI 코딩 에이전트(Claude Code) 행동을 **빠르게 도와주는** 도구 모음.
통제 강제 폐기, 결정적 게이트 + 사용자 가속만 유지. 다운스트림은 이식·
업그레이드해서 사용. 단일 관리자(nnkann), Windows + Git Bash, 실험 단계.

## Problems (해결해야 할 핵심 — 자라는 목록)

| ID | 1줄 요약 |
|----|---------|
| P1 | LLM 추측 수정 반복 |
| P2 | review 과잉 비용 |
| P3 | 다운스트림 사일런트 페일 |
| P4 | 광역 hook 매처 fragility |
| P5 | MCP·플러그인 컨텍스트 팽창 |
| P6 | 검증망 스킵 패턴 |
| P7 | 시스템 구성 요소 간 관계 불투명 |
| P8 | 자가 발화 의존 규칙의 일반 실패 |
| P9 | 정보 오염의 관성 |

> 추가는 `python .claude/scripts/docs_ops.py cps add "1줄"`. 새 P# 자유.
> 정의·증상·진입조건 본문: `docs/archived/hn_kickoff_pre_73pct_cut.md`.

## Solutions (자라는 목록)

| ID | 대상 P# | 1줄 메커니즘 |
|----|---------|------------|
| S1 | P1 | 규칙 + 자동 차단 + 우회 장치 |
| S2 | P2 | 패턴 → 행동 매핑 + hard 상한 |
| S3 | P3 | 5중 방어 |
| S4 | P4 | 단일 hook + 금지 규칙 |
| S5 | P5 | 압축 + 최소화 |
| S6 | P6 | 4중 방어 |
| S7 | P7 | (정의 진화 중) |
| S8 | P8 | 강제 트리거 우선 + 자가 의존 보조 |
| S9 | P9 | 주관 격리 + 다층 검증 |

## CPS 사용 흐름

1. 새 작업 발화 → C(맥락) 1줄 추출
2. 위 표에서 P# 매칭 (단일/중복/신규)
3. S 결정
4. implementation Step 2 정합 substep (자동) — C·P·S 어긋남 감지
5. 확정 후 cascade — implementation → test → /commit
6. /commit 시 `docs/cps/cp_{slug}.md` 박제 (frontmatter c·tags·p·s·result)

## 빠른 조회

```
python .claude/scripts/docs_ops.py cps list           # P# 1줄 요약
python .claude/scripts/docs_ops.py cps show P8        # P# 정의 + 관련 case
python .claude/scripts/docs_ops.py cps cases --p P8   # P8 관련 case
python .claude/scripts/docs_ops.py cps stats          # P# 분포
python .claude/scripts/docs_ops.py cps add "1줄"      # 새 P# 등록
```

## 운영 원칙

- 매칭 강제 없음. 자라는 시스템 — 다음 wave가 새 P# 자유 추가
- frontmatter 인용 50자 박제 검사 폐기 (번호만)
- kickoff 자라지 않음 — 정련은 옵트인 (연 1회 정도)
- `/cps-check` 옵트인 — 사용자 명시 호출 시 정합 검사 단독 실행
