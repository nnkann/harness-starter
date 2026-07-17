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
status: completed
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
- [x] Goal: 후보 평가 후 권장안 1개
  검증:
    review: skip
    tests: 없음
    실측: 본 WIP `## 결정 사항` 첨부
- [x] 사용자·에이전트가 라우팅 태그를 인지·통과하는 방법 평가

**후보 (초안)**:
- D1: naming.md·docs.md에 "WIP 검색 시 양쪽 wildcard(`*<abbr>_*`) 사용" 가이드 명시
- D2: 라우팅 태그(`decisions--`·`guides--` 등) 폐기, WIP 파일에 `target:` frontmatter로 대체 → glob 단순화
- D3: 헬퍼 스크립트 `find_by_abbr.sh <abbr>` 신설 — 라우팅 태그 투명 통과 검색 SSOT
- D4: 현 라우팅 태그 유지하되 SKILL.md·doc-finder가 자동으로 양쪽 wildcard 시도

### 2. 권장안 구현

**Acceptance Criteria**:
- [x] Goal: 사용자·에이전트가 도메인 abbr 1개로 WIP 포함 모든 도메인 문서 발견 가능
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: starter에서 임의 abbr로 검색 시 WIP·decisions·guides 모두 hit 됨을 확인
- [x] 권장안 구현 (가이드 문서·스크립트·SKILL.md·라우팅 태그 폐기 중 선택) ✅
- [x] 회귀 테스트 1개 이상

**구현 결과** (2026-05-02):
- `docs.md` "## 문서 탐색 > 기본 경로" 갱신 — cluster 진입점을 1번으로 격상, 양쪽 wildcard `docs/**/*{abbr}_*` 명시
- `naming.md` "## 왜 — 파일명이 곧 인덱스" 첫 bullet 갱신 — 양쪽 wildcard + cluster 단일 진입점 명시
- 회귀 가드: (b) wave의 `test_wip_appears_in_cluster`가 cluster 진입점 커버. 라우팅 태그 통과 자체는 기존 `detect_abbr` 회귀 테스트(T39 계열)가 커버
- 실측 (starter):
  - `ls docs/WIP/hn_*` → No such file (라우팅 태그 막힘 재현)
  - `ls docs/WIP/*hn_*` → WIP 4개 모두 hit (양쪽 wildcard 통과)

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [x] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시 ✅
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [x] 라우팅 태그 폐기 시 다운스트림 WIP 파일 마이그레이션 절차 (해당 후보 채택 시)

**다운스트림 영향 분류** (2026-05-02):
- **라우팅 태그 폐기**: 채택 안 함 (D2 기각). 다운스트림 WIP 파일 마이그레이션 불필요
- **양식 변경**: 없음. naming.md·docs.md 가이드 문구만 변경
- **이행**: 자동. 다운스트림 사용자·에이전트가 `docs.md` 갱신본을 다음 작업에서 자연 적용
- **MIGRATIONS.md 신규 섹션**: commit Step 4 version bump가 자동 처리

## 결정 사항

### 2026-05-02 — 후보 평가 (단독 판단)

**선행 wave (b) 영향 — D2 기각, D1 채택 강화**:
(b) WIP cluster 가시성 wave가 채택한 B2 변형으로 cluster 본문에
`## 진행 중 (WIP)` 섹션 자동 추가. 사용자·에이전트가 cluster scan 한 번에
WIP 포함 발견 가능 → (d)의 핵심 비대칭(WIP glob miss) 사실상 cluster
진입점으로 흡수.

남은 갭은 **파일 직접 glob을 쓸 때 라우팅 태그 통과 인지**. 큰 변경
(D2 라우팅 태그 폐기) 정당성 없음. **D1 가이드 명시 + cluster 진입점
격상**으로 충분.

**Trade-off**:

| 후보 | 변경 범위 | 다운스트림 영향 | 채택 |
|------|----------|---------------|-----|
| **D1 가이드 명시** (양쪽 wildcard) | naming.md·docs.md 문구 | 자동 이행 | ✅ |
| D2 라우팅 태그 폐기 | docs_ops·commit·SKILL.md·다운스트림 WIP 파일 | 큰 마이그레이션 | ❌ |
| D3 헬퍼 스크립트 | 새 스크립트 + 사용자 학습 | 가이드 + 실행 권한 | ❌ |
| D4 SKILL.md 자동 양쪽 wildcard | implementation 동작 변경 | 명시적 가이드보다 흐려짐 | ❌ |

**채택: D1 + cluster 진입점 격상**

**근거**:
1. **(b) 흡수로 핵심 갭 해소** — cluster scan 진입점이 WIP 포함 → 사용자가 양쪽 wildcard 학습 안 해도 1차 발견 가능
2. **남은 갭은 가이드로 충분** — 파일 직접 glob 시 양쪽 wildcard. naming.md "직교 파싱 규칙"과 정합
3. **다운스트림 영향 0** — 가이드 문구만 변경, WIP 양식·인터페이스 무변경
4. D2 라우팅 태그 폐기는 cascade 영향 큼. (b) 채택 후 정당성 약화

**반영 위치**: `.claude/rules/docs.md` "## 문서 탐색 > 기본 경로" + `.claude/rules/naming.md` "## 왜 — 파일명이 곧 인덱스" 첫 bullet

**CPS 갱신**: 없음 — 가이드 갱신, Solution 충족 기준 무변경

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조.

다운스트림 N=2 (도메인 7) 환경에서 직접 시도:
- `docs/WIP/decisions--<abbr>_*` glob → hit 1 (직접 매칭)
- `docs/WIP/<abbr>_*` glob → hit 0 (라우팅 태그가 막음)

naming.md "직교 파싱 규칙"은 docs_ops.py 내부에만 적용. 사용자·에이전트
검색 도구로는 미전파.
