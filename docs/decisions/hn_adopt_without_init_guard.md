---
title: adopt-without-init 다운스트림 능동 유도 — harness-init 자동 트리거
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [harness-adopt, harness-init, guard, cps]
relates-to:
  - path: decisions/hn_downstream_amplification.md
    rel: extends
  - path: decisions/hn_init_gate_redesign.md
    rel: extends
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# adopt-without-init 다운스트림 유도

## 사전 준비
- 읽을 문서:
  - `docs/decisions/hn_downstream_amplification.md` `## 메모` ((e) 발견 근거)
  - `docs/decisions/hn_init_gate_redesign.md` (a) 결정 — 본 wave가 "능동 유도" 대응
  - `.claude/skills/harness-adopt/SKILL.md` 종료 흐름
  - `.claude/skills/harness-init/SKILL.md` 진입 조건
- 이전 산출물:
  - amplification (e) — N=2 baseline에서 "harness-adopt 끝났지만 harness-init 미실행" 다운스트림 발견
  - (a) v0.34.0 init 게이트 A4 — adopt-without-init 다운스트림은 implementation Step 0에서 차단됨 (수동 차단)

## 목표
(a)는 implementation 진입 시점의 **수동 차단** 게이트. 본 wave는
`harness-adopt` 끝난 시점에 **능동 유도** — init 권유 또는 자동 호출.
(a)와 (e)는 보완 관계, advisor 결정 사항에 명시됨.

## 작업 목록

### 1. 후보 평가

**Acceptance Criteria**:
- [x] Goal: 후보 평가 후 권장안 1개
  검증:
    review: skip
    tests: 없음
    실측: 본 WIP `## 결정 사항` 첨부
- [x] 다운스트림 자율 vs 강제 트리거 trade-off 평가

**후보 (초안)**:
- E1: harness-adopt 종료 시 "init 진행하시겠습니까? [Y/n]" 대화형 권유
- E2: harness-adopt 종료 시 자동 harness-init 트리거 (옵트아웃 가능)
- E3: harness-adopt 본문에 "다음 단계: harness-init 필수" 1줄 강조 + 종료 메시지
- E4: implementation 차단 메시지에 "어떻게 init 실행하는지" 한 줄 추가하고 본 wave 폐기 (a) 메시지로 충분 판단

### 2. 권장안 구현

**Acceptance Criteria**:
- [x] Goal: adopt 직후 init 미실행으로 차단되는 다운스트림 비율 0
  검증:
    review: review
    tests: 없음 (대화형 흐름이라 자동화 곤란)
    실측: starter에서 harness-adopt 시뮬 후 권장안 동작 확인
- [x] 권장안 구현 (skill 갱신·메시지 강화·자동 트리거 중 선택)

**구현 결과** (2026-05-02):
- `harness-adopt/SKILL.md` Step 8 완료 리포트의 "다음 할 일" 섹션 강화:
  - ⚠️ 강조 박스 추가 — `/harness-init` 미실행 시 implementation 차단됨을 명시
  - "(권장)" → "(필수, 즉시)"로 격상
  - adopt 책임 한계 명시 ("adopt는 구조 이식만 — Problem/Solution/Context는 init이 채웁니다")
- 자동 검증 불가 (대화형 흐름 + 사용자 행동) — 운용에서 확인 필요
- (a) v0.34.0 차단 메시지 + 본 wave의 사전 강조 메시지가 보완 — 사용자가 adopt 직후 init 안 돌려도 implementation 진입 시점에 안내 받음

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [x] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시 ✅
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [x] 기존 adopt 완료 + init 미완료 다운스트림은 어떻게 마이그레이션되는지 분류

**다운스트림 영향 분류** (2026-05-02):
- **양식 변경**: 없음. harness-adopt SKILL.md 본문만 변경 (다운스트림은 adopt 후 SKILL.md 자기 삭제, harness-upgrade로 재수신 시 새 본문 적용)
- **이행 — 신규 adopt**: 자동. 강조 메시지 노출 후 `/harness-init` 즉시 실행
- **이행 — 기존 adopt 완료 + init 미완료 다운스트림**: 본 wave의 사전 안내 미수혜 (이미 SKILL.md 자기 삭제됨). 그러나 (a) v0.34.0 차단 메시지가 implementation 첫 호출 시 안내 → 사후 보완. 마이그레이션 작업 불필요
- **MIGRATIONS.md 신규 섹션**: commit Step 4 version bump가 자동 처리

**CPS 갱신**: 없음 — adopt → init 흐름의 안내 강화, Problem/Solution 변경 없음

## 결정 사항

### 2026-05-02 — 후보 평가 (단독 판단)

**Trade-off**:

| 후보 | 자율성 침해 | 효과 | 다운스트림 영향 | 채택 |
|------|----------|----|---------------|-----|
| E1 대화형 권유 prompt | 약 — adopt가 본래 자동 흐름인데 추가 stop point | 명확한 의사 확인 | adopt 흐름 변경 | ❌ |
| E2 자동 init 트리거 (옵트아웃) | 강 — 사용자 자율 침해 | 차단율 0 | 큰 흐름 변경 | ❌ |
| **E3 메시지 강화** | 없음 | 사후 안내(a 메시지)와 보완 | 본문만 변경 | ✅ |
| E4 본 wave 폐기 (a로 충분) | — | (a) 차단 시점이 늦음 — 사용자가 implementation 첫 호출까지 모름 | 0 | ❌ |

**채택: E3 메시지 강화**

**근거**:
1. **자율성 보존** — adopt 자동 흐름 깨지 않음. 사용자가 init 실행 시점 결정
2. **(a) v0.34.0과 보완** — adopt 종료 시점 사전 안내 + implementation 진입 시점 사후 차단. 이중 안전망
3. **우선순위 5에 비례** — 큰 변경(E2) 정당성 약함. 1건 발견 사례에 자율 침해 trade-off 무거움
4. **다운스트림 영향 0** — SKILL.md 본문만 변경. 다운스트림 인터페이스·양식 무변경

**반영 위치**: `.claude/skills/harness-adopt/SKILL.md` Step 8 "다음 할 일" 섹션

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조 — 다운스트림
N=2 (도메인 7) 환경에서 발견. CPS sample만 존재 → Problem 매칭 불가,
init 게이트가 본래 차단해야 했으나 v0.33.x drift 검사로는 통과.

### (a)와의 의미 분리 (advisor 결정 사항 인용)
- (a) A4: 수동 차단 게이트 — implementation 진입 시점에 init 안 돈
  상태면 차단
- (e): 능동 유도 흐름 — `harness-adopt` 끝난 시점에 init 권유·자동 호출
- 보완 관계. A4가 (e) 흡수 X.

### 우선순위
amplification 결정 사항: (e) "신규 발견 (N=2). starter 자기 영향 검토
의무 사례 (incident hn_sealed_migrations_exempt_gap 형제 패턴). 우선순위 5".

(b)·(c)·(d) 대비 우선순위 낮음. v0.34.0 (a) 차단 메시지가 이미 init
실행 안내를 포함하므로 (E4) "본 wave 폐기" 가능성도 평가 후보.
