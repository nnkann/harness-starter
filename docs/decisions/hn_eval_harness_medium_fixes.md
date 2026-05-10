---
title: eval --harness medium 결과 정비 (5-4 Feedback Reports 인식 + 5-5 self-verify 모호성)
domain: harness
problem: P7
solution-ref:
  - S6 — "self-verify.md SKIP 조건 명확화 (부분)"
  - S6 — "review 카테고리 8 — 기존 SKILL.md·rules 실질 변경도 CPS 갱신 감지 (부분)"
tags: [eval, feedback-reports, self-verify, cps-integrity]
relates-to:
  - path: decisions/hn_upgrade_silent_fail_guards.md
    rel: extends
status: completed
created: 2026-05-10
updated: 2026-05-10
---

# eval --harness medium 결과 정비

## 사전 준비
- 읽을 문서: `.claude/scripts/eval_cps_integrity.py` L385~445 (Feedback Reports 검증 로직). `docs/decisions/hn_eval_cps_integrity.md` (검증 결정 사료). `.claude/rules/self-verify.md` L48~50.
- 이전 산출물: 다운스트림 v0.42.1 적용 후 측정된 eval --harness 결과 — 항목 7(피드백 리포트)에서 "없음 ✅" 오출력 (실제 6건 존재)
- MAP 참조: HARNESS_MAP.md CPS 테이블 P7 행 (defends-by: docs, naming, memory, anti-defer / enforced-by: eval_cps_integrity.py, HARNESS_MAP.md 자체)

## 목표
- 5-4: eval_cps_integrity.py가 다운스트림 양식의 `### Feedback Reports` (버전 섹션 내 서브헤더)를 인식하도록 정규식 보강. v0.42.1 Phase 4의 수신 채널 무력화 차단
- 5-5: self-verify.md "가능하면" 모호성을 구체 기준으로 정밀화 — UI/frontend 변경에서 dev 서버 검증을 필수로 강화
- CPS 연결: P7 (구성요소 관계 불투명 — 검증 로직이 다운스트림 양식 변화를 못 따라가는 정합성 결함 + rules 모호성)

## 작업 목록

### 1. Phase 1 — 5-4 Feedback Reports 정규식 양면 매칭 보강

**사전 준비**: `.claude/scripts/eval_cps_integrity.py` L405~445 (`check_feedback_reports` 함수). 현재 정규식 `r"## Feedback Reports(.*?)(?=^## |\Z)"`은 top-level 헤더만 매칭. 다운스트림이 버전 섹션 안에 `### Feedback Reports` 서브헤더로 작성하면 미인식
**영향 파일**: `.claude/scripts/eval_cps_integrity.py`
**Acceptance Criteria**:
- [x] Goal: `## Feedback Reports`(top-level) + `### Feedback Reports`(버전 섹션 내 서브헤더) 양쪽 양식 모두 인식. 다운스트림이 어느 양식을 써도 FR 항목 검출
  검증:
    review: review-deep
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: 다운스트림 양식 시뮬레이션 — 버전 섹션 안에 `### Feedback Reports` + 그 아래 `#### FR-001` 형태로 작성한 임시 migration-log.md를 함수에 통과시켰을 때 FR 항목이 검출됨
- [x] `### Feedback Reports`(버전 섹션 서브헤더) 매칭 추가. `re.findall`로 모든 출현 누적
- [x] FR 항목 헤더 레벨도 양면 — `### FR-NNN` 또는 `#### FR-NNN` 둘 다 인식
- [x] 회귀 가드: 기존 `## Feedback Reports` (top-level) 양식 처리 그대로 유지 (test_eval_harness.py 통과) ✅
- [x] 회귀 가드 신규: 버전 섹션 내 `### Feedback Reports` 양식 검증 케이스 추가 (test_eval_harness.py 또는 별 테스트 파일) ✅

### 2. Phase 2 — 5-5 self-verify.md "가능하면" 정밀화

**사전 준비**: `.claude/rules/self-verify.md` L48~50. 현재 "**가능하면:** dev 서버 부팅, 변경 기능 실제 동작."
**영향 파일**: `.claude/rules/self-verify.md`
**Acceptance Criteria**:
- [x] Goal: "가능하면" 모호성 제거. UI/frontend 변경 시 dev 서버 검증을 필수로, 그 외는 선택으로 명시
  검증:
    review: review
    tests: 없음
    실측: `grep -nE "가능하면|UI|frontend" .claude/rules/self-verify.md` 결과에 새 기준 명시 라인 hit
- [x] "가능하면" 단어를 명확한 트리거 조건으로 교체 — UI/frontend 코드 변경 시 필수, 백엔드·CLI·문서는 선택
- [x] 라인 수 1~3줄 이내 변경 (rules 모호성 제거 1건)

### 3. Phase 3 — FR-007 후속: 필드 매칭 정규식 다양성 확보 (v0.42.4)

**사전 준비**: 다운스트림 v0.42.3 적용 후 측정 FR-007 — `check_feedback_reports`의 헤더 양면 매칭은 정상 작동(6건 검출)했으나 필드 substring 검사가 단순 `**심각도**` 마커만 잡음. 다운스트림 양식이 헤더 인라인 `(심각도: medium — ...)` 형태면 검출 후 6건 모두 "⚠ 심각도 없음" 오경보
**영향 파일**: `.claude/scripts/eval_cps_integrity.py` (L439·L453 영역) + `.claude/scripts/tests/test_eval_harness.py` (회귀 가드 1건 추가)
**Acceptance Criteria**:
- [x] Goal: 4 필수 필드(관점·약점·실천·심각도) 매칭이 3 양식 모두 인식 — bold 마커 (`**관점**:`) + plain (`관점:`) + 헤더 인라인 (`(심각도: ...)`). 다운스트림 v0.42.3 측정의 6건 오경보가 0건으로 해소
  검증:
    review: review-deep
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: 헤더 인라인 양식 회귀 케이스(`#### FR-NNN (... 심각도: medium ...)`) 추가 후 통과 확인. 기존 11건 + 신규 1건 = 12 passed
- [x] `required_fields`를 substring 검사 → 정규식 검사로 교체. 각 필드명에 대해 `(?:\*\*FIELD\*\*\s*:|FIELD\s*:|\(\s*FIELD\s*:)` 양면 패턴
- [x] 4 필드 동일 패턴 적용 (관점·약점·실천·심각도)
- [x] 회귀 가드 1건 추가: 헤더 인라인 `(심각도: medium)` 양식만 사용하는 FR이 정상 검출되는지 (`FR-NNN ✅` 반환)
- [x] 기존 11건 회귀 유지 (bold 마커 + plain 양식 호환)

## 결정 사항

### Phase 1 (5-4) — Feedback Reports 정규식 양면 매칭 보강
- **반영 위치**: `.claude/scripts/eval_cps_integrity.py` `check_feedback_reports` (L405~) — 정규식 1줄 → finditer 양면 매칭 + FR ID 중복 방지 set
- **양면 지원**: `## Feedback Reports` (top-level) + `### Feedback Reports` (버전 섹션 내 서브헤더). FR 헤더 레벨도 `### FR-NNN` + `#### FR-NNN` 양면
- **회귀 가드 신설**: test_eval_harness.py에 4건 추가 — top-level 양식 / 버전 섹션 서브헤더 양식 / 필수 필드 누락 / 파일 부재 None 반환. 11/11 통과
- **이유**: 다운스트림이 버전 섹션 안에 `### Feedback Reports` 서브헤더 양식 사용 시 구버전 정규식이 미인식 → "없음 ✅" 오출력으로 v0.42.1 Phase 4 수신 채널 무력화. 양식 통일 강제보다 양면 허용이 다운스트림 자율성 보존에 정합

### Phase 3 (FR-007) — 필드 매칭 정규식 다양성 확보 (v0.42.4)
- **반영 위치**: `.claude/scripts/eval_cps_integrity.py` `check_feedback_reports` (L436~) — `required_fields`를 substring 검사 → 정규식 검사 헬퍼(`_field_present`)로 교체
- **3 양식 양면 매칭**: bold 마커(`**필드**:`) + plain(`필드:`) + 헤더 인라인(`(필드:`). 한국어 단어 경계는 `(?<![\w가-힣])` lookbehind로 처리 — 부분 단어 매칭 방지
- **회귀 가드 신설**: `test_feedback_reports_inline_header_severity` 추가. `#### FR-NNN ... (심각도: medium — ...)` 헤더 인라인만 있고 본문에 `**심각도**:` 별도 라인 없는 케이스도 `FR-NNN ✅` 검출. 12 passed (기존 11 + 신규 1)
- **이유**: 다운스트림 v0.42.3 측정에서 6건 모두 검출은 됐으나 "⚠ 심각도 없음" 오경보. v0.42.3 헤더 양면 매칭으로 검출 자체는 성공했으나 필드 substring 검사가 좁아 신뢰도 저하 → 다운스트림 자율성 보존 + 가이드 양식 호환 동시 충족

### Phase 2 (5-5) — self-verify.md "가능하면" 정밀화
- **반영 위치**: `.claude/rules/self-verify.md` L50 (1줄 → 8줄)
- **변경**: "가능하면 dev 서버 부팅" 모호 표현 제거 → "UI/frontend 변경 시 필수" + "그 외 선택" 명확 트리거
- **이유**: UI 변경은 코드 통과 ≠ 사용자 경험 통과인 영역 — 모호 표현이 SKIP 허용으로 작동했음. CLAUDE.md "UI 또는 frontend 변경" 원칙과 정합

## 변경 이력

### v0.42.4 (2026-05-10) — Phase 3 추가 (FR-007 후속)
- 다운스트림 v0.42.3 적용 후 6건 검출 + "⚠ 심각도 없음" 오경보 수신
- `required_fields` substring 검사 → 3 양식 양면 정규식 검사로 교체
- 헤더 인라인 양식 회귀 가드 추가 (12 passed)

### v0.42.3 (2026-05-10) — 초기 wave (Phase 1 + Phase 2)
- Phase 1: Feedback Reports 헤더 양면 매칭 (`##` + `###`) + FR 헤더 양면 (`###` + `####`) + ID 중복 방지
- Phase 2: self-verify.md "가능하면" 모호성 → UI/frontend 트리거 명확화

## CPS 갱신
- P7 본문 변경 없음 (구성요소 관계 정합성 회복 — 검증 로직이 양식 변화를 따라가는 정합 강화). S6 메커니즘 자체 변경 아님
- Phase 3도 동일 — Solution 정의 변경 없음. 본 보강 자체의 정확도 결함 수정
- Solution 정의 변경 없음 → owner 추가 승인 불필요

## 메모
- 사용자 보고 high 3건 중 5-2(HARNESS_MAP 단절)·5-1(dead links)·5-3(잘못된 S 인용)은 모두 다운스트림 측정 결과로 starter 처리 영역 아님. medium 5-6(coding.md "적절한 하위")도 starter coding.md에 해당 문구 부재 — 다운스트림 자체 룰. 본 wave는 5-4 + 5-5만 처리
- 5-4 결함 진단: `eval_cps_integrity.py:423` 정규식이 `## Feedback Reports` (top-level) 만 매칭. 다운스트림 양식이 버전 섹션 안 `### Feedback Reports` 서브헤더면 미인식 → "없음 ✅" 오출력. v0.42.1 Phase 4의 수신 채널 자체가 무력화되는 결함
- CPS 매칭: 사용자가 P7 제시 — 정확. eval_cps_integrity.py는 P7 enforced-by. 5-4는 P8(자가 발화 의존 차단) 메커니즘 무효화 측면도 있으나 Solution 정의 변경 아니므로 단일 P# 박제로 충분 (P7 주, P8 부수 본문 언급)
- doc-finder: hn_eval_cps_integrity.md(검증 결정 사료), eval_harness.py(진입점), pre_commit_check.py(self-verify AC 추출) 식별. 본문 직접 Read로 정확한 위치 특정
- Solution 인용 S6는 (부분) 처리 — self-verify.md SKIP 조건 명확화는 5-5 정밀화와 정합. 5-4는 review 카테고리 8(검증 도구 정렬) 영역과 인접하나 직접 인용보다 (부분) 마커가 안전
