---
title: implementation init check 게이트 정밀화 — 환경 양식 drift 비용 제거
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [implementation, init-check, gate-redesign, drift]
relates-to:
  - path: decisions/hn_downstream_amplification.md
    rel: extends
  - path: incidents/hn_sealed_migrations_exempt_gap.md
    rel: references
status: in-progress
created: 2026-05-02
updated: 2026-05-02
---

# implementation init check 게이트 정밀화

## 사전 준비
- 읽을 문서:
  - `.claude/skills/implementation/SKILL.md` Step 0 (현행 게이트 로직, 라인 69~85)
  - `decisions/hn_downstream_amplification.md` `## 메모` (3환경 baseline)
  - `.claude/scripts/pre_commit_check.py` SEALED_PATH_EXEMPT (형제 패턴)
- 이전 산출물: hn_downstream_amplification Phase 4-A 결론 (3환경 baseline + 5개 병목 식별)

## 목표
implementation Step 0의 init check 게이트가 다운스트림 환경 양식 drift에서
헛돌면서 15~19s 비용만 소비하는 문제 해결. 게이트 의미를 재정의해
"진짜 init 미실행" 케이스만 차단하고, drift 통과·캐시·또는 폐기 중
선택. 양식 강제 vs 다운스트림 자유도 trade-off는 advisor 결정.

## 작업 목록

### 1. advisor 호출 (대안 4개 weighted matrix 평가) — 선행

**Acceptance Criteria**:
- [ ] Goal: A1·A2·A3·A4 4개 대안에 대해 advisor가 trade-off + 권장안 + 뒤집힐 조건 명시
  검증:
    review: skip
    tests: 없음 (의사결정 작업)
    실측: advisor 응답 본 WIP `## 결정 사항` 첨부
- [ ] 각 대안의 다운스트림 영향·starter 자기 영향·cascade 평가
- [ ] adopt-without-init(병목 (e))과의 의미 분리 명확화
- [ ] 권장안 1개 + 폐기 후보 명시

**대안 4개**:
- **A1**: 게이트 폐기 (drift 비용 0, 검증 0)
- **A2**: 게이트 정밀화 (`## 환경` 모든 키 채워짐 + project_kickoff.md 존재 + status != sample)
- **A3**: 1회 통과 후 캐시 (`.claude/.init_verified` flag, 재실행 skip)
- **A4**: 의미 재정의 — drift 감지가 아니라 "init 안 돈 신규 프로젝트만 차단"
  (CPS sample 존재 + 실 kickoff 부재만 차단)

### 2. 권장안 구현

**Acceptance Criteria**:
- [ ] Goal: starter init check wall ≤2s (현재 4.85s) + 다운스트림 drift 환경에서 15~19s → 차단 또는 통과 명확
  검증:
    review: review-deep
    tests: pytest -m stage
    실측: starter `/implementation` 발화로 Step 0 wall 재측정 (목표 ≤2s)
- [ ] `.claude/skills/implementation/SKILL.md` Step 0 게이트 로직 갱신
- [ ] starter 자기 영향 검토 (incident hn_sealed_migrations_exempt_gap 형제 패턴 회피)
- [ ] 회귀 테스트 1개 이상 (init 안 돈 케이스 차단·init 완료 통과·drift 케이스 권장안에 따른 동작)

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [ ] Goal: MIGRATIONS.md에 다운스트림 영향 1줄 + 적용 방법 명시
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬 또는 다운스트림 1건 fetch 보고
- [ ] 양식 변경이 필요한 다운스트림은 명시 (예: `## 환경` 키 추가)
- [ ] 자동 적용 vs 수동 적용 분류

## 결정 사항
(advisor 호출 후 채움)

## 메모

### 현행 게이트 (재현 — 본 WIP 신설 전 상태)

위치: `.claude/skills/implementation/SKILL.md` 라인 69~85

```
init 미완료 감지:
CLAUDE.md `## 환경`의 `패키지 매니저:` 값이 비어있으면 init이 완료되지 않은 것이다.
이 경우 작업을 시작하지 않고 차단한다.
```

**결함 요약**:
- 단일 키(`패키지 매니저:`)만 검사
- 다운스트림이 양식을 안 따르면 (C++/CMake처럼 키 자체가 N/A) 차단도 통과도 못 함
- 3환경 baseline에서 starter 4.85s vs 다운스트림 15~19s, 3~4x 차이로 입증
- 실효성 0이면서 비용은 그대로 소비

### baseline 출처

`decisions/hn_downstream_amplification.md` `## 메모` 참조 — 3환경
baseline 수치 + drift 유무 비교 표.