---
title: P11 결정적 게이트 승격 + FR 양식 동형 후보 위치 + eval_cps_integrity P11 카운트 버그
domain: harness
problem: [P6, P8, P11]
s: [S6, S8, S9]
tags: [p11, pre-check, gate-promotion, feedback-report, eval-cps]
relates-to:
  - path: decisions/hn_dead_ref_p11_first_case.md
    rel: extends
status: completed
created: 2026-05-16
updated: 2026-05-16
---

# P11 결정적 게이트 승격 wave

## 0. 박제 — 다운스트림 v0.47.9 운용 보고

StageLink v0.47.9 적용 후 자체 측정 결과 + 3건 FR 제출:

- **FR-X11** (low, 성공 보고): v0.47.9 항목 9 첫 호출에서 7건 검출 — 도구 ROI 100%
- **FR-X10** (medium): FR 양식에 "동형 후보 위치" 서브섹션 추가
- **FR-X12** (medium): 절차 자체의 P11 유발 — 결정적 게이트 승격 (옵션 B 권장)

starter eval 발견 부패:
- eval_cps_integrity P11 카운트 0건 보고 (실측 5건 인용) — list 형식 + 두자리수 정규식 누락 합산

## 1. Goal

P11(동형 패턴 잠복) 본질을 자가 발화 의존(harness-dev Step P)에서 결정적
게이트(pre-check) 로 승격 + 채널 양식 보강 + 측정 도구 정정.

## 2. 3축 처리

**A. pre-check 게이트 승격** (FR-X12 옵션 B):
- staged diff에 폐기 파일 패턴 검출 시 `eval_harness.py section_dead_reference`
  자동 호출
- 1건 이상이면 commit 차단 + 정비 안내
- 다운스트림이 도구 실행을 잊어도 결정적 차단 (P8 자가 발화 의존 해소)
- 사상: v0.47.7 commit_finalize wrapper 흡수와 동일 — "LLM 책임 → 도구 책임"

**B. FR 양식 동형 후보 위치 서브섹션** (FR-X10):
- MIGRATIONS.md `## Feedback Reports` 포맷 SSOT에 추가
- 다운스트림이 1차 발견 시 starter가 동형 grep 대상에 자동 합류
- 선택적 서브섹션 (P11 인지 시만 작성)

**C. eval_cps_integrity P11 카운트 버그**:
- L164 `re.match(r"^P\d+$", ...)` — frontmatter problem 'str' 형식만 처리.
  list 형식 (`[P7, P11]`) 미처리
- L127-130 정규식 `\b(P\d)\b` — 한 자리수만, P10·P11 매칭 불가
- 두 버그 합산이 P11 0건 결과 (실측 5건 인용)

## 3. Acceptance Criteria

**Acceptance Criteria**:
- [x] Goal: P11 결정적 게이트 승격 — S6·S8·S9 cascade 충족.
  - A. pre-check 게이트 + test
  - B. FR 양식 갱신
  - C. eval_cps_integrity 패치 + test
  검증:
    tests: pytest .claude/scripts/tests/ -q
    실측: eval_harness 항목 9 P11 카운트 5건 표시 + pre-check이 dead ref staged 시 차단
- [x] pre_commit_check.py에 dead ref 게이트 함수 신설 + 호출 통합 (§3.6 신규)
- [x] dead ref scan_dead_reference_paths 함수 분리 + test 3건 (정상 검출·박제 면제·전체 스캔)
- [x] MIGRATIONS.md FR 양식에 "동형 후보 위치" 서브섹션 박제 (선택적)
- [x] eval_cps_integrity.py: list 형식 처리 (L162-171) + 정규식 4건 `P\d+` 확장
- [x] test_eval_harness.py에 P11/P10 카운트 회귀 + frontmatter list 케이스 2건 신규
- [x] 최종 eval --harness 재실행 — P11 5건 ✓ dead ref 0건 ✓ pre-check 통과 ✓ (22 passed)

## 결정 사항

- FR-X12 옵션 B 채택 (pre-check 게이트 승격). 옵션 A 자가 발화 의존 잔존 회피
- test_pre_commit fixture 통합 테스트는 ROI 낮음(WSL 경로 환경 이슈 + 본 wave 무관) — scan 함수 단위 test로 충분
- v0.47.10 patch 범프

## 메모

- 동반 관찰 (CPS case에 박제됨, 다음 wave 후보):
  - AC 헤더 `##` vs `**bold**` auto-fix 부재
  - docs_ops.py move 라우팅 태그 접두사 강제
  - WIP move 후 pre-check P#/S# 추출 시점
- pre-check `wip_problem` 출력이 list 첫 항목만 잡힘 (frontmatter list 인식 별개) — 본 wave는 staged 게이트만 처리. 출력 포맷 list 지원은 별 wave
