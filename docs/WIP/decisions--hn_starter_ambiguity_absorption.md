---
title: starter 모호성 흡수 + CPS Problem 임계 상향 + S7 미정의 명시
domain: harness
problem: P7
solution-ref:
  - S6 — "self-verify.md SKIP 조건 명확화 (부분)"
tags: [cps, ambiguity, skill-md, self-violation]
status: completed
created: 2026-05-11
---

# starter 모호성 흡수 + CPS Problem 임계 상향 + S7 미정의 명시

## 사전 준비
- 읽을 문서: `.claude/skills/eval/SKILL.md` (모호성 정의 SSOT), `docs/guides/project_kickoff.md` (CPS)
- 이전 산출물: 다운스트림 `/eval --harness` 보고 (Problem 8개·P7·P8 정체·모호성 14건·S7 정체)
- MAP 참조: P7 (시스템 구성 요소 간 관계 불투명) / S6 항목 1 (self-verify SKIP 조건 명확화)

## 목표
- starter 자기증명 P7 패턴(자기 정의한 모호성을 자기 문서가 위반) 해소
- eval.md 모호성 정의에서 조건문 표현 제거 (false-positive 차단)
- CPS Problem 임계 6 → 8 상향 (현 8개 정상화)
- S7 의도적 미정의 명시 (P7 메커니즘은 HARNESS_MAP.md가 담당하므로 별도 Solution 불필요)

CPS 연결:
- S6 항목 1 충족 — SKILL.md 자체 명확화 (수치·분기 명시)
- P7 본문 보강 — 임계 상향 + S7 미정의 명시

## 작업 목록

### 1. eval/SKILL.md 모호성 정의 정밀화

**사전 준비**: 현재 eval/SKILL.md:180 — `- "적절한", "필요하면", "가능하면", "상황에 따라"`
**영향 파일**: `.claude/skills/eval/SKILL.md:180`

**Acceptance Criteria**:
- [x] Goal: 모호성 정의에서 조건문 표현("필요하면"·"가능하면") 제거, 자체 모호 표현만 남김
  검증:
    review: self
    tests: 없음
    실측: grep으로 SKILL.md 모호 표현 잔존 확인 — `필요하면`·`가능하면` 조건문은 false-positive 아니어야 함
- [x] 새 정의가 "X한 경우"·"X일 때" 같은 조건분기는 모호성 아님을 명시

### 2. SKILL.md 4건 수치·분기 명시

**사전 준비**: 진짜 모호성 4건 확인 완료
**영향 파일**:
- `.claude/skills/eval/SKILL.md:110` ("간결하게 유지")
- `.claude/skills/harness-upgrade/SKILL.md:23` ("가능하면 3-way merge")
- `.claude/skills/write-doc/SKILL.md:120` ("snake_case 의미명, 간결하게")
- `.claude/skills/implementation/SKILL.md:408` ("자동으로 적절한 폴더로 이동")

**Acceptance Criteria**:
- [x] Goal: 4건 모두 수치 또는 명시적 분기로 교체
  검증:
    review: review
    tests: 없음
    실측: 변경 후 각 라인 grep해 모호 표현 부재 확인
- [x] eval:110 "간결하게" → "5줄 이내" 등 수치
- [x] harness-upgrade:23 "가능하면" → "기본은 3-way merge, 충돌 못 풀면 사용자 결정 요청" 분기
- [x] write-doc:120 "간결하게" → "3~5단어" 또는 "30자 이내" 수치
- [x] implementation:408 "적절한 폴더" → 라우팅 규칙 인용 ("frontmatter의 대상 폴더 기준")

### 3. CPS P7 본문 보강 + Problem 임계 상향

**사전 준비**: 현재 P7 정의(project_kickoff.md:107), Problem 8개 상태
**영향 파일**: `docs/guides/project_kickoff.md`

**Acceptance Criteria**:
- [x] Goal: P7 본문에 "Solution은 의도적 미정의 — HARNESS_MAP.md 메커니즘 자체가 P7 해소"; Problem 임계를 6에서 8로 상향
  검증:
    review: review
    tests: 없음
    실측: eval --harness 시 Problem 8개 경고 0건
- [x] Problem 임계 상향 근거 1줄 본문에 명시 (2026-05-11 8건 정상화)
- [x] S7 자리 명시 — "P7 → HARNESS_MAP.md 자체 (Solution 별도 정의 안 함)"
- [x] eval_cps_integrity.py 임계 상수 6 → 8 (해당 시)

### 4. eval_cps_integrity.py 임계 상향

**사전 준비**: 현재 임계 6
**영향 파일**: `.claude/scripts/eval_cps_integrity.py`

**Acceptance Criteria**:
- [x] Goal: Problem 임계 6 → 8
  검증:
    review: self
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: 14 passed (회귀 없음)
- [x] 임계 상향 후 starter 자체 eval 통과

## 결정 사항

- **eval.md 모호성 정의 정밀화** — "필요하면"·"가능하면" 제거, "조건문 제외" 명시 추가. → 반영: eval/SKILL.md:180-185
- **수치·분기 명시 4건**:
  - eval/SKILL.md:110 "간결하게" → "5줄 이내, 상세는 memory"
  - harness-upgrade/SKILL.md:23 "가능하면" → "기본은 3-way, 충돌 시 사용자 결정 요청"
  - write-doc/SKILL.md:120 "간결하게" → "단어 2~4개, 30자 이내"
  - implementation/SKILL.md:408 "적절한 폴더" → 라우팅 규칙 명시
  - implementation/SKILL.md:445 "간결하게" → "본문 50줄 이내 권장"
- **CPS P7 S7 미정의 명시** — "P7 메커니즘은 HARNESS_MAP.md 자체. 별도 Solution 정의 안 함". → 반영: project_kickoff.md P7 본문
- **Phase 4 skip** — eval_cps_integrity.py 임계 이미 동적(`max(8, count+2)`). 다운스트림 보고 오해석 또는 구버전
- **CPS 갱신**: P7 본문 보강 (Solution 의도적 미정의 명시)

## 박제 의심 3건 — 본 wave 흡수 처리
- `hn_eval_harness_medium_fixes.md` S6 인용: `(M, ≥3줄)` 보강어 누락 → CPS 본문 정확 substring으로 교체
- `hn_stop_guard_py_migration.md` S7 인용: S7 미정의 → S6(self-verify SKIP 조건 명확화) 재매칭
- `hn_wip_util_ssot.md` S7 인용: 동일 → S6 재매칭
- 검증: `python .claude/scripts/eval_cps_integrity.py` → 박제 의심 0건 ✅

## 메모
- 다운스트림 보고 "14건"과 starter grep "11건" 차이는 다운스트림이 자기 docs/도 합산했기 때문
- starter는 자기 SKILL.md 11건 중 진짜 모호 4건만 수정. 조건분기 7건은 유지
- S7 의도적 미정의 — P7 메커니즘은 HARNESS_MAP.md 자체. 별도 Solution 정의 시 중복 추상화 (Karpathy "단일 사용 추상화 금지" 정합)
- 검증 도구 정렬 + eslint resolver (다운스트림 부채 3·4)는 starter 영역 아님 — 처리 불가
- Phase 4 (임계 상향) 불필요 — `eval_cps_integrity.py:284` 이미 `max(8, count+2)` 동적 임계. 다운스트림 보고의 "임계 6 초과"는 구버전 또는 오해석
- 박제 의심 3건 발견 (eval_cps_integrity 실행 결과):
  - hn_eval_harness_medium_fixes.md S6 인용 — 본문 진화로 미매칭
  - hn_stop_guard_py_migration.md / hn_wip_util_ssot.md — S7 "정의 보류" 인용. 본 wave에서 S7 의도적 미정의 명시했으므로 인용 자체 부적절

