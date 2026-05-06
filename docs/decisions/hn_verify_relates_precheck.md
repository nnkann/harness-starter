---
title: verify-relates pre-check 통합 — 커밋 시 relates-to 전수 검사
domain: harness
problem: P3
solution-ref:
  - S3 — "downstream-readiness.sh — 적용 후 누락 자가 진단"
tags: [pre-check, verify-relates, dead-link, relates-to]
relates-to:
  - path: decisions/hn_downstream_amplification.md
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# verify-relates pre-check 통합

## 사전 준비
- 읽을 문서:
  - `.claude/scripts/pre_commit_check.py` 3.5단계 (dead link 증분 검사, 라인 410~548)
  - `.claude/scripts/docs_ops.py` `cmd_verify_relates` (라인 524~540)
  - `.claude/scripts/tests/test_pre_commit.py` TestIntegRelatesTo (T36 계열)
- 이전 산출물:
  - 다운스트림 v0.34.1 검증에서 relates-to dead link 7건 발견
  - debug-specialist 진단: 원인 H3(박제 ref) 확정, 섹션 C 전수화가 근본 해결
  - `verify-relates` 실행 비용 측정: 0.133s (starter docs ~140개)

## 목표

현재 pre-check 3.5단계 섹션 C는 **staged 파일 자신의 relates-to**만 검사.
"파일 이동 시 다른 파일의 relates-to가 깨지는지"는 안 봄.
→ `docs_ops.py verify-relates`를 pre-check에서 전수 실행해 커밋 시 즉시 차단.

## 작업 목록

### 1. pre-check 3.5단계에 verify-relates 전수 호출 추가

**영향 파일**: `.claude/scripts/pre_commit_check.py`

**Acceptance Criteria**:
- [x] Goal: 커밋 시 relates-to 깨진 ref가 있으면 차단
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: `python3 .claude/scripts/docs_ops.py verify-relates` 결과 0건인 상태에서 pre-check 통과, 깨진 ref 인위 생성 후 pre-check 차단 확인
- [x] `cmd_verify_relates` 호출 후 오류 있으면 `err()` + exit 2
- [x] 기존 섹션 C(staged 파일 관련 개별 검사)는 제거 — verify-relates 전수가 흡수
- [x] 회귀 테스트 1개 이상

### 2. 다운스트림 영향 명시 (MIGRATIONS.md)

**Acceptance Criteria**:
- [x] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시 ✅
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬

## 결정 사항

### 2026-05-02 — 섹션 C 제거 + verify-relates 전수로 통합

현재 섹션 C는 staged 파일 자신의 relates-to만 검사. verify-relates 전수로
대체하면 섹션 C가 하던 일을 포함해 전체 dead relates-to를 한 번에 잡음.
섹션 C는 중복이 되므로 제거.

`cmd_verify_relates`를 subprocess로 호출하지 않고 **import해서 직접 호출**.
이유: pre_commit_check.py가 이미 docs_ops 모듈을 import해서 쓰고 있음.

**반영 위치**:
- `.claude/scripts/pre_commit_check.py` — 섹션 C 제거 + verify-relates 호출 추가
- `.claude/scripts/tests/test_pre_commit.py` — T36 계열 회귀 테스트 갱신

**CPS 갱신**: 없음 — S3 5중 방어에 실질적 추가, 충족 기준 본문은 무변경

## 메모

### 기존 섹션 C 제거 판단

섹션 C가 하는 일: staged 파일의 frontmatter relates-to path가 존재하는지 확인.
verify-relates가 하는 일: docs/ 전체 모든 파일의 relates-to path가 존재하는지 확인.
→ verify-relates가 섹션 C의 슈퍼셋. 섹션 C는 staged 파일만이라 범위 더 좁음.
→ 섹션 C 제거해도 회귀 없음. verify-relates가 더 넓게 커버.

### cmd_verify_relates 반환값 확인

```python
def cmd_verify_relates() -> int:
    ...
    print(f"\n결과: 미연결 relates-to {errors} 건")
    return errors  # 오류 건수 반환
```

반환값이 0이면 통과, 0 초과면 차단. stdout에 오류 내용 출력됨.
pre_commit_check.py에서 `_docs_ops.cmd_verify_relates()` 호출 후 반환값 체크.
