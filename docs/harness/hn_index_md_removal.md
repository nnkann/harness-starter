---
title: docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거
domain: harness
tags: [docs, ssot, simplification, index-removal]
relates-to:
  - path: harness/hn_simplification.md
    rel: extends
  - path: decisions/hn_frontmatter_graph_spec.md
    rel: supersedes
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# docs/INDEX.md 폐기

## 증상

2026-04-20 세션에서 사용자가 "INDEX는 이 지경인데 아무런 피드백이 없는
거 보면 이거 사용도 안 하고 있는 거 아니야?"라고 지적. 실제로 INDEX가
관리되지 않은 상태로 방치됨:

- `harness (40)`·`meta (1)` 카운트만 있고 도메인 구분이 사실상 없음
  (거의 모든 문서가 domain: harness)
- "WIP 문서 포함 안 함" 규칙이 있는데도 **진입 포인터** 역할이라 선언
- 실제 Claude 탐색 경로는 **clusters/harness.md 직행** → INDEX 스킵

## 원인

`INDEX → clusters → 본문`이라는 3단 탐색을 설계했으나:

1. **도메인 수가 2개뿐** — 다운스트림 프로젝트가 아닌 harness-starter
   자체는 단일 도메인 성격이라 "어느 clusters를 볼지" 분기 가치 없음.
2. **clusters가 이미 INDEX 역할 수행** — 문서 목록 + 관계 맵을 다 들고
   있음. INDEX는 단순 포인터로 전락.
3. **SSOT 이중화** — 문서 수·도메인 목록이 INDEX와 naming.md(도메인
   목록) 두 곳에 있어 드리프트 필연.

결과: 아무도 안 보는 파일 → 아무도 갱신 안 함 → 카운트 오류 누적 →
정보 오염 소스.

## 결정

**INDEX.md 폐기. clusters/{domain}.md를 진입점 SSOT로.**

- 도메인 목록 SSOT는 `.claude/rules/naming.md` "도메인 목록".
- 탐색 경로: `clusters/{domain}.md → 본문 Read` (2단).
- 문서 수 카운트는 카운트할 필요가 있을 때 `ls docs/{folder}/ | wc -l`
  동적 계산. 정적 기록 유지 안 함.

## 변경 범위

1. `docs/INDEX.md` 파일 삭제.
2. INDEX 참조 14곳 정리:
   - `.claude/rules/docs.md`: 폴더 구조 + 탐색 흐름 2단으로 재정의.
   - `.claude/rules/internal-first.md`: docs/ 우선순위 포인터 갱신.
   - `.claude/rules/staging.md`: S5 면제 메타 리스트에서 INDEX.md 제거.
   - `.claude/scripts/pre-commit-check.sh`: REPEAT_EXEMPT_REGEX·META
     awk 패턴에서 INDEX.md 제거.
   - `.claude/skills/commit/SKILL.md`: "메타 파일 자동 병합" 리스트에서
     INDEX.md 제거. "commit 처리 결과 박기" 대상에서도 제거.
   - `.claude/scripts/docs_ops.py`: Step 3(INDEX 갱신) 제거.
     나머지 INDEX 언급 전부 clusters로.
   - `.claude/skills/harness-init/SKILL.md`: INDEX 초기 생성 단계 제거.
   - `.claude/skills/harness-adopt/SKILL.md`: 5g 단계·출력 형식·강제
     완료 체크 리스트에서 INDEX 제거.
   - `.claude/skills/harness-upgrade/SKILL.md`: docs-manager 호출 블록
     에서 INDEX 제거.
   - `.claude/skills/write-doc/SKILL.md`: Step 2 탐색 경로·Step 6 이동
     후 처리 리스트 정리.
   - `.claude/agents/doc-finder.md`: 탐색 절차에서 INDEX 제거.
   - `.claude/agents/risk-analyst.md`·`codebase-analyst.md`: 탐색 순서
     에서 INDEX 제거.
   - `.claude/agents/review.md`: 정합성 체크에서 INDEX 제거.
   - `.claude/scripts/test-pre-commit.sh`: T4·T17 케이스가 INDEX.md를
     사용하고 있어 clusters/harness.md로 교체.

## 단순화 정신

`hn_simplification.md`의 "더 추가가 아니라 더 빼기"를
관리되지 않는 SSOT 제거로 확장 적용.
