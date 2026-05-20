---
title: 버전 범프 opt-in 갭 복구
domain: harness
c: "eval harness 버그 수정 커밋이 버전 범프 없이 push되어 다운스트림 harness-upgrade 경로에서 적용 신호가 사라질 수 있음"
problem: P3
s: [S3, S6, S9]
tags: [versioning, migration, release]
status: completed
created: 2026-05-20
updated: 2026-05-20
---

# 버전 범프 opt-in 갭 복구

## CPS Rationale

- C -> P: starter 스크립트 수정이 버전·MIGRATIONS 없이 배포되면 다운스트림이 조용히 놓친다.
- P -> S: S3는 다운스트림 사일런트 페일을 버전·마이그레이션 채널로 막고, S6·S9는 완료 증거와 진단 오염을 분리한다.
- S -> AC: opt-in 범프 계약을 테스트하고 v0.52.1 배포 문서를 실제로 남긴다.

**Acceptance Criteria**:
- [x] Goal: S3·S6·S9 기준으로 스크립트 패치의 버전 범프 누락을 재발 방지하고 v0.52.1 배포 경로에 태운다.
  검증:
    review: skip
    tests: `python -m pytest .claude/scripts/tests/test_harness_version_bump.py -q`
    실측: 회귀 테스트가 scripts 수정 staged 상태에서 `HARNESS_BUMP=patch`의 patch 제안을 검증하고, 현재 staged 상태에서는 `HARNESS_BUMP=patch python .claude/scripts/harness_version_bump.py`가 `이미 범프됨: 0.52.1`을 출력한다. commit Step 4·`.claude/HARNESS.json`·README·MIGRATIONS가 v0.52.1을 표시한다.
- [x] `harness_version_bump.py`의 주석상 계약인 `HARNESS_BUMP=patch`가 실제 코드와 테스트로 동작한다. ✅
- [x] `commit` Step 4 SSOT와 active `.agents` mirror가 scripts 수정 opt-in 범프 절차를 명시한다.
- [x] v0.52.1 섹션이 `docs/harness/MIGRATIONS.md`에 추가된다. ✅
- [x] README와 `.claude/HARNESS.json` 현재 버전이 v0.52.1로 갱신된다. ✅

## 결정 사항

- CPS 갱신: 없음. 기존 S3 릴리즈 채널과 S6/S9 검증·오염 방어를 구현으로 보강한다.
