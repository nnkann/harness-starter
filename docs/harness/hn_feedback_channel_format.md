---
title: 다운스트림 피드백 채널 포맷 규격화 + eval --harness 테스트
domain: harness
problem: P3
solution-ref:
  - S3 — "migration-log.md (부분)"
  - S6 — "review 카테고리 8 (부분)"
tags: [feedback, eval, migration-log, downstream]
relates-to:
  - path: harness/MIGRATIONS.md
    rel: extends
status: completed
created: 2026-05-06
updated: 2026-05-06
---

# 다운스트림 피드백 채널 포맷 규격화 + eval --harness 테스트

## 사전 준비
- 읽을 문서: docs/harness/MIGRATIONS.md (migration-log.md 포맷 섹션), .claude/skills/eval/SKILL.md (--harness 절차)
- 이전 산출물: 없음
- MAP 참조: P3 served-by harness-upgrade, downstream-readiness.sh / P6 served-by eval

## 목표

1. 다운스트림이 업스트림에 보내는 피드백 메시지의 **포맷을 규격화** — "관점 + 약점 + 실천" 구조 기반
2. `harness-upgrade` 완료 후 **`eval --harness`로 규격 준수 여부 검증** 가능하게
3. migration-log.md에 feedback_report 섹션 추가 (다운스트림 작성 규격)
4. eval --harness 항목 6번으로 "피드백 리포트 포맷 검사" 추가

CPS 연결: S3 "migration-log.md 이상 소견 기록 → upstream 전달" + S6 "검증망 강화"

## 작업 목록

### Phase 1. 피드백 포맷 규격 정의 (MIGRATIONS.md 확장)

**사전 준비**: docs/harness/MIGRATIONS.md의 migration-log.md 관련 섹션 확인 완료
**영향 파일**: docs/harness/MIGRATIONS.md

**Acceptance Criteria**:
- [x] Goal: migration-log.md에 `## Feedback Reports` 섹션 포맷이 정의되어, 다운스트림이 규격에 맞게 작성할 수 있다
  검증:
    review: self
    tests: 없음
    실측: MIGRATIONS.md 열어서 ## Feedback Reports 섹션 확인

### Phase 2. eval --harness 피드백 포맷 검증 항목 추가

**사전 준비**: .claude/skills/eval/SKILL.md "점검 항목" 섹션
**영향 파일**: .claude/skills/eval/SKILL.md

**Acceptance Criteria**:
- [x] Goal: `eval --harness` 실행 시 migration-log.md의 feedback_report 포맷 규격 준수 여부를 검증하는 항목 6번이 추가된다
  검증:
    review: review
    tests: 없음
    실측: eval --harness 보고 형식 예시에 "피드백 리포트" 항목 포함 확인

### Phase 3. eval_cps_integrity.py 피드백 검증 로직 추가

**사전 준비**: .claude/scripts/eval_cps_integrity.py 구조 확인
**영향 파일**: .claude/scripts/eval_cps_integrity.py, .claude/scripts/tests/test_pre_commit.py

**Acceptance Criteria**:
- [x] Goal: `eval_cps_integrity.py`가 migration-log.md의 feedback_report 섹션 포맷을 검증하고 결과를 출력한다
  검증:
    review: review
    tests: python3 -m pytest .claude/scripts/tests/ -q -k feedback
    실측: python3 .claude/scripts/eval_cps_integrity.py 실행 후 feedback 항목 출력 확인

## 결정 사항
- bash-guard.sh 간접 실행 차단 추가 (검증 4): eval/sh -c/bash -c 패턴 + 역슬래시 정규화. BIT Q1=YES 판단으로 즉시 처리. → 반영: .claude/scripts/bash-guard.sh
- CPS 갱신 완료: P4 운용 약점·P5 구조적 원인·P7 미완독 패턴·S3 피드백 규격·S4 예정 레이어·S5 MVR 방향 전환. → 반영: docs/guides/project_kickoff.md
- HARNESS_MAP P4/P5 row 갱신 완료 → 반영: .claude/HARNESS_MAP.md
- CPS 갱신: 없음 (이미 위에서 갱신됨)

## 메모
- doc-finder fast scan: migration-log.md 포맷이 MIGRATIONS.md에 부분 정의됨 (충돌·수동결정·이상소견·수동적용결과 4개 섹션). feedback_report 섹션은 없음.
- eval --harness 스크립트: eval_cps_integrity.py만 존재. 피드백 포맷 검증 로직 없음.
- 피드백 포맷 기반: 사용자가 보내온 "관점 + 약점 + 실천" 구조가 역방향 피드백의 실제 사례. 이를 규격화.

## 발견된 스코프 외 이슈

- bash-guard.sh 역슬래시 이스케이프(`git\ commit`) + 간접 실행(eval/sh -c) 우회 취약점 | 발견: 사용자 피드백 보고 | P#: P3 (다운스트림 방어선 무력화 경로) → 즉시 수정 완료
- 박제 감지 Alarm Fatigue — 잦은 경고가 "오탐 학습" 유발, 진짜 오류 은폐 | 발견: 사용자 피드백 | P#: P1 (추측 수정 반복 — 경고 무시 패턴)
- review 에이전트 미완독 증명 허점 — 규칙 수정 직후 세션에서 구 캐시로 리뷰 | 발견: 사용자 피드백 | P#: P6 (검증망 스킵)
- completed 봉인 `## 변경 이력` 우회 — 핵심 결정 슬그머니 변경 가능 | 발견: 사용자 피드백 | P#: P3/P6 복합
