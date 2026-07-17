---
title: completed 봉인 — 본문 마크다운 링크 경로 교체 면제
domain: harness
problem: P3
solution-ref:
  - S3 — "다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨 (부분)"
tags: [pre-check, sealed, dead-link, exempt]
relates-to:
  - path: incidents/hn_sealed_migrations_exempt_gap.md
    rel: extends
  - path: decisions/hn_promise_protection.md
    rel: caused-by
status: completed
created: 2026-05-04
updated: 2026-05-04
---

# completed 봉인 — 본문 마크다운 링크 경로 교체 면제

## 사전 준비

- 읽을 문서:
  - `docs/incidents/hn_sealed_migrations_exempt_gap.md` — 동일 패턴 선례 (MIGRATIONS.md 면제)
  - `.claude/scripts/pre_commit_check.py:576` — 봉인 로직
- 이전 산출물: 없음

## 목표

archived로 이동한 파일을 참조하는 completed 문서의 링크 경로 수정 시
"completed 봉인 위반"으로 차단되는 문제를 해결한다.

CPS 연결: P3 — 정당한 유지보수 작업(dead link 복구)이 봉인에 막혀
다운스트림에서 dead link가 방치됨. S3 5중 방어의 "정상 흐름 보장" 측면.

## 작업 목록

### 1. pre_commit_check.py 면제 로직 추가

**영향 파일**: `.claude/scripts/pre_commit_check.py`

**Acceptance Criteria**:
- [x] Goal: 본문 마크다운 링크 경로 교체(삭제+추가 쌍)는 봉인 면제
  검증:
    review: self
    tests: pytest -m gate
    실측: T42.7(링크 교체 면제) + T42.8(순수 추가 차단) 통과

### 2. 회귀 테스트 추가

**영향 파일**: `.claude/scripts/tests/test_pre_commit.py`

**Acceptance Criteria**:
- [x] Goal: T42.7(교체 면제) + T42.8(순수 추가 차단) 테스트 추가
  검증:
    review: self
    tests: pytest -m gate
    실측: 20 passed 확인

## 결정 사항

- **접근법**: 옵션 3 채택 — hunk 내 `-` 라인 존재 여부로 "교체 vs 순수 추가" 판별
  - 근거: diff만으로 판단 가능, docs_ops.py move 수정 불필요, 가장 단순
  - 반영 위치: `pre_commit_check.py:619` `hunk_has_deletion` 플래그 + 링크 패턴 면제
- **CPS 갱신**: 없음 — P3 기존 범위 내 면제 갭 보완

## 메모

- 선례: `hn_sealed_migrations_exempt_gap.md` — path 화이트리스트 방식(옵션 A)
  이번엔 패턴 매칭 방식 채택 (경로 목록 관리 없이 본문 링크 전체 커버)
- 순수 추가(삭제 없는 링크 줄 추가)는 여전히 차단됨 — 의도적 설계
- pytest gate 20 passed (T42.7 + T42.8 신규 포함)
