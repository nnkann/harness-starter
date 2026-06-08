---
title: HARNESS_UPGRADE 환경변수 의미 일관화
domain: harness
tags: [upgrade, env-var, ssot, governance]
problem: P3
s: [S3]
relates-to:
  - path: harness/hn_upstream_anomalies.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
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
- [x] `HARNESS_UPGRADE` 사용 위치 전수 목록 (파일·라인·분기 동작)
- [x] 위 표 4개 경로 + 추가 발견된 경로 모두 실측 결과 기록 — 활성 분기는 `pre_commit_check.py:108·549` 단 1곳 (recommended_stage="skip"). 나머지는 모두 호출 사용처

### 2. 의미 정의 결정

> kind: feature

두 옵션 중 하나 선택:

- **옵션 A**: `HARNESS_UPGRADE=1` 의미를 명시적으로 좁힘 — "review skip만",
  나머지는 case-by-case. SSOT는 `pre_commit_check.py` 상단 주석 또는
  `staging.md` 1개 섹션.
- **옵션 B**: `HARNESS_UPGRADE` 폐기. review skip은 다른 메커니즘으로 대체
  (예: `staging.md` 룰 0번 별도 신호). //이건 하네스에서만 사용하는건데 의미도 불명하고 불편하기만 함. 삭제해

**Acceptance Criteria**:
- [x] Goal: 어디까지 우회하는가의 SSOT가 1곳에 정의됨 — commit 스킬 `--no-review` 단일 경로로 통합
- [x] 옵션 결정 근거 — 사용자 주석으로 옵션 B 직접 결정 (advisor 호출 생략)
- [x] 영향 범위: pre_commit_check.py·commit/SKILL.md·staging.md — `pytest -m stage` 회귀 체크 8/8 통과

### 3. 코드·문서 반영

> kind: refactor

Step 2 결정에 따라 코드·문서 정리.

**Acceptance Criteria**:
- [x] SSOT 1곳에 정의 + 다른 위치는 SSOT 참조 — staging.md에 폐기 안내 블록 추가, 회고적 기록은 보존
- [x] 영향 범위: pre_commit_check.py — `pytest -m "secret or stage"` 회귀 체크 12/12 통과

## 결정 사항

### 2026-05-02 — 옵션 B 채택 (전면 폐기)

- **결정**: `HARNESS_UPGRADE` 환경변수 폐기. review skip은 commit 스킬의
  기존 `--no-review` 플래그로 대체. 추가 환경변수 도입 안 함.
- **근거**: 사용자 주석 — "하네스에서만 사용하는데 의미도 불명하고
  불편하기만 함." 의미 불명한 박제 비용 > 수정 작업 비용.
- **반영 위치**:
  - `.claude/scripts/pre_commit_check.py` L108·L549 — 환경변수 정의·룰 0 분기 제거
  - `.claude/settings.json` — `Bash(HARNESS_UPGRADE=1 bash *)` 권한 제거
  - `.claude/rules/staging.md` — 1단계 룰 0 제거 + 폐기 안내 블록
  - `.claude/skills/harness-upgrade/SKILL.md` Step 10·관계 표 — `HARNESS_UPGRADE=1 git commit` → `/commit --no-review`
- **회고적 기록 보존**: `README.md` v0.26.9 변경 이력, `MIGRATIONS.md`
  L398, `docs/harness/hn_upstream_anomalies.md` 본문은 당시 상태이므로
  그대로 유지. 회고 변경 금지.

CPS 갱신: 없음 (운영 룰 정밀화).

## 검증

- `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
- `from pre_commit_check import ENOENT_PATTERNS` import OK (sys.exit 없음)
- `pytest -m "secret or stage"` 12/12 통과
- `grep HARNESS_UPGRADE` 활성 코드 0건 (회고적 기록만 5건)

## 메모

- B·D·E·F 해결 wave(v0.28.6) 직후 별 wave로 분리됐으나, 변경 범위가
  크지 않아 같은 세션에서 즉시 진행.
- 옵션 A(의미를 좁힘)는 advisor 호출 없이 폐기 — 추가 환경변수 의미
  유지 자체가 사용자 발화의 핵심 불만이므로 옵션 A는 본질적 해결 아님.
- 다운스트림 영향: 이전 업그레이드에서 `HARNESS_UPGRADE=1` 사용 흔적이
  있어도 staging.md 룰 0 제거 + pre_commit_check.py 분기 제거로 자연 무시.
  남아 있는 alias·script가 있다면 사용자 직접 정리 검토.
