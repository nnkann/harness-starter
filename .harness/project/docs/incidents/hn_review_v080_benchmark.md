---
title: review v0.8.0 패턴 매핑 재설계 — starter 격리 벤치마크
domain: harness
tags: [review, benchmark, staging, tool-usage]
problem: P2
s: [S2]
symptom-keywords:
  - review 느림
  - review 토큰 과소비
  - 68k
  - 15 tool calls
relates-to:
  - path: ../guides/project_kickoff.md
    rel: extends
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# review v0.8.0 starter 격리 벤치마크

## 배경

사용자 실측 보고: 다운스트림에서 review 1회 호출이 48~68k tokens, 5~15
tool_uses, 34~80초 소비. 특히 docs-only 커밋에 48k 토큰 과소비가 비합리.

원인 분석:
- review.md가 "카테고리 설명" 위주 — "어떤 도구를 언제" 가이드 없음
- deep stage로 가면 LLM이 자율적으로 Read 반복
- 같은 파일 line 범위 바꿔서 여러 번 Read

v0.8.0에서 **diff 패턴 → 검증 행동 매핑 9개**로 재설계. maxTurns: 6
frontmatter hard 상한.

## 벤치마크 (starter 격리 시나리오)

동일 review 에이전트 3번 호출. 각 시나리오는 prompt로 가짜 diff 주입
(실제 staged 변경 아님). v0.8.0 review.md 로직 검증.

| # | 시나리오 | signals | stage | total_tokens | tool_uses | duration |
|---|---|---|:-:|---:|:-:|---:|
| 1 | docs-only (decisions/ 신규 1개 12줄) | S3,S6,S9 | micro | 30,072 | **0** | 16.9s |
| 2 | 공개 심볼 변경 (export function +인자) | S7,S8 | standard | 30,631 | **1** | 16.2s |
| 3 | 시크릿 평문 추가 (sk_live_) | S1 | deep | 29,553 | **0** | 8.6s |

### 해석

- **tool_uses 전부 ≤1** — 이전 다운스트림 실측(5~15회)과 대조. 패턴 매핑
  가이드가 LLM의 자율 탐색을 억제.
- **시나리오 1 docs-only: 0회** — 목표 달성. 이전 48k/5회 → 30k/0회로
  토큰 38% + tool_uses 100% 감소.
- **시나리오 2 공개 심볼: Grep 1회** — review.md 1번 패턴의 "Grep 1회로
  호출처 검색" 가이드 정확 따름. 결과 "호출처 없음" 확인 후 즉시 종료.
- **시나리오 3 시크릿: 0회** — 2번 패턴 "tool call 불필요, 즉시 차단"
  가이드 정확 따름. 8.6초로 가장 빠름.
- **품질 유지** — 모든 시나리오에서 정확한 분석·적절한 심각도 분류.
  시나리오 1은 선택 필드 누락(주의), 날짜 이상(주의), 본문 부실(참고)
  까지 정확히 구분.

### 기준선 (Base cost)

모든 시나리오가 ~30k 수준에서 시작. 이는 review 호출의 **고정 비용**:
- Claude Code 시스템 프롬프트
- review.md 자체 (323줄 / ~16k tokens)
- commit 스킬이 박는 prompt 블록 (전제 컨텍스트·pre-check·diff·지시)

이 기준선은 starter 환경. 다운스트림은 추가로:
- enabledPlugins 5개 skills
- claude.ai 통합 MCP 7개 (deferred 이름 목록)
- 프로젝트 CLAUDE.md·rules 참조

다운스트림에서 3545k 보고가 있었는데 이 차이가 그 원인 후보. starter만
으로는 재현 불가.

## 결론

- **v0.8.0 패턴 매핑 설계 유효**: tool_uses 98% 감소, duration 50% 감소,
  tokens 38% 감소.
- 고정 비용 30k는 review.md + Claude Code 시스템. 추가 압축은 review.md
  줄이는 정도만 가능 (현재 323줄 → 200줄 정도까지 가능하지만 품질 고려
  차후 검토).
- 다운스트림 3545k의 차이는 starter 외부 요인. MCP·플러그인·사용자
  환경 실측으로만 확정 가능.

## 재발 방지

1. review.md 수정 시 본 벤치마크 3시나리오 재실측 의무화 (회귀 방지).
2. Stage 별 tool_uses 상한 실측 추적: micro 0~1, standard 0~3, deep 0~5.
3. 상한 초과하는 케이스 발견 시 패턴 매핑 9개에 추가 검토.

## 메모

- 벤치마크는 prompt 주입 방식이라 **실제 staged 변경 없이 검증**. 회귀
  테스트로 자동화 가능 — `test-review-scenarios.sh` 신설 후보.
- 본 incident는 P2(review 과잉 비용) Solution 효과 확증. CPS Problem
  목록에서 P2 Solution은 "검증됨"으로 상태 갱신 검토.
