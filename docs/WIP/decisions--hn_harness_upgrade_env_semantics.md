---
title: HARNESS_UPGRADE 환경변수 의미 일관화
domain: harness
tags: [upgrade, env-var, ssot, governance]
relates-to:
  - path: harness/hn_upstream_anomalies.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# HARNESS_UPGRADE 환경변수 의미 일관화

`hn_upstream_anomalies.md` C 항목에서 분리. A(secret 우회)가 코드 면제로
해결돼 본 issue는 "환경변수가 어디까지 우회하는가"의 의미 정의·SSOT 부재
문제로 한정.

## 증상

`HARNESS_UPGRADE=1`이 일부 차단 경로만 우회하는 비대칭 동작.

| 차단 경로 | HARNESS_UPGRADE=1 동작 |
|-----------|------------------------|
| review stage (`recommended_stage`) | `skip`으로 강제 ✅ |
| secret line-confirmed (`s1_level`) | 우회 안 함 (sys.exit 2) |
| 거대 커밋 경고 / split 권장 | 동작 미확인 — 검증 필요 |
| WIP completed 잔재 차단 | 동작 미확인 — 검증 필요 |

## 원인

환경변수 도입 시 "review만 skip한다"는 좁은 의도였으나, 다운스트림이
starter 콘텐츠를 mirror하는 시나리오에서 다른 차단 경로도 의미상 우회
대상이 됨. 정의가 코드 곳곳에 흩어져 SSOT 부재.

## 작업 목록

### 1. 현재 동작 실측

> kind: chore

`HARNESS_UPGRADE=1` 분기를 `pre_commit_check.py`·`docs_ops.py`·`staging.md`·
`bash-guard.sh`·`commit/SKILL.md`에서 grep으로 전수 추출. 각 분기의 실제
동작·의도를 정리.

**Acceptance Criteria**:
- [ ] `HARNESS_UPGRADE` 사용 위치 전수 목록 (파일·라인·분기 동작)
- [ ] 위 표 4개 경로 + 추가 발견된 경로 모두 실측 결과 기록

### 2. 의미 정의 결정

> kind: feature

두 옵션 중 하나 선택:

- **옵션 A**: `HARNESS_UPGRADE=1` 의미를 명시적으로 좁힘 — "review skip만",
  나머지는 case-by-case. SSOT는 `pre_commit_check.py` 상단 주석 또는
  `staging.md` 1개 섹션.
- **옵션 B**: `HARNESS_UPGRADE` 폐기. review skip은 다른 메커니즘으로 대체
  (예: `staging.md` 룰 0번 별도 신호).

**Acceptance Criteria**:
- [ ] Goal: 어디까지 우회하는가의 SSOT가 1곳에 정의됨
- [ ] 옵션 결정 근거 (advisor 호출 권장 — Reversibility 프레임)
- [ ] 영향 범위: pre_commit_check.py·commit/SKILL.md·staging.md — `pytest -m stage` 회귀 체크

### 3. 코드·문서 반영

> kind: refactor

Step 2 결정에 따라 코드·문서 정리.

**Acceptance Criteria**:
- [ ] SSOT 1곳에 정의 + 다른 위치는 SSOT 참조
- [ ] 영향 범위: pre_commit_check.py — `pytest -m "secret or stage"` 회귀 체크

## 결정 사항

(작업하면서 채움)

## 메모

- 우선순위 낮음 — B·D·E·F 해결로 핵심 다운스트림 마찰 해소됨.
- v0.28.6 기준 분기 시작.
