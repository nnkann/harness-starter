---
title: Glob 라우팅 태그 통과 — 사용자·에이전트 검색 비대칭 해소
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [glob, routing-tag, naming, search]
relates-to:
  - path: decisions/hn_downstream_amplification.md
    rel: extends
status: in-progress
created: 2026-05-02
updated: 2026-05-02
---

# Glob 라우팅 태그 통과

## 사전 준비
- 읽을 문서:
  - `docs/decisions/hn_downstream_amplification.md` `## 메모` ((d) 발견 근거)
  - `.claude/rules/naming.md` "Cluster 자동 매핑 — 직교 파싱 규칙" + "파일명 — WIP"
  - `.claude/scripts/docs_ops.py` abbr 추출 정규식
  - `.claude/skills/implementation/SKILL.md` SSOT 3단계 keyword grep
  - `.claude/skills/doc-finder` 가 있다면 fast scan glob 패턴
- 이전 산출물: amplification wave Phase 4-A — (d) `<abbr>_*` glob hit 0,
  `decisions--<abbr>_*` 직접 매칭만 hit. 다운스트림 N=2 baseline에서 부분
  실패 명시 확인

## 목표
docs_ops.py abbr 추출 정규식 `(^|[_-])(<abbr>)_`은 라우팅 태그(`decisions--`)
를 투명 통과하지만, **사용자·에이전트의 단순 glob**(`<abbr>_*`)은 통과
못 함. 같은 의도의 두 도구가 비대칭 결과를 산출하는 결함 해소.

## 작업 목록

### 1. 후보 평가

**Acceptance Criteria**:
- [ ] Goal: 후보 평가 후 권장안 1개
  검증:
    review: skip
    tests: 없음
    실측: 본 WIP `## 결정 사항` 첨부
- [ ] 사용자·에이전트가 라우팅 태그를 인지·통과하는 방법 평가

**후보 (초안)**:
- D1: naming.md·docs.md에 "WIP 검색 시 양쪽 wildcard(`*<abbr>_*`) 사용" 가이드 명시
- D2: 라우팅 태그(`decisions--`·`guides--` 등) 폐기, WIP 파일에 `target:` frontmatter로 대체 → glob 단순화
- D3: 헬퍼 스크립트 `find_by_abbr.sh <abbr>` 신설 — 라우팅 태그 투명 통과 검색 SSOT
- D4: 현 라우팅 태그 유지하되 SKILL.md·doc-finder가 자동으로 양쪽 wildcard 시도

### 2. 권장안 구현

**Acceptance Criteria**:
- [ ] Goal: 사용자·에이전트가 도메인 abbr 1개로 WIP 포함 모든 도메인 문서 발견 가능
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: starter에서 임의 abbr로 검색 시 WIP·decisions·guides 모두 hit 됨을 확인
- [ ] 권장안 구현 (가이드 문서·스크립트·SKILL.md·라우팅 태그 폐기 중 선택)
- [ ] 회귀 테스트 1개 이상

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [ ] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [ ] 라우팅 태그 폐기 시 다운스트림 WIP 파일 마이그레이션 절차 (해당 후보 채택 시)

## 결정 사항
(후보 평가 후 채움)

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조.

다운스트림 N=2 (도메인 7) 환경에서 직접 시도:
- `docs/WIP/decisions--<abbr>_*` glob → hit 1 (직접 매칭)
- `docs/WIP/<abbr>_*` glob → hit 0 (라우팅 태그가 막음)

naming.md "직교 파싱 규칙"은 docs_ops.py 내부에만 적용. 사용자·에이전트
검색 도구로는 미전파.
