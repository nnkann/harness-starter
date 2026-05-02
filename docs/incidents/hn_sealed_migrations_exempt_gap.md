---
title: pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [pre-check, sealed, false-block, regex-gap, migrations]
symptom-keywords:
  - "completed 문서 본문 무단 변경 감지"
  - "docs/harness/MIGRATIONS.md"
  - "SEALED_PATH_EXEMPT"
  - "harness-upgrade 후 차단"
relates-to:
  - path: incidents/hn_secret_line_exempt_gap.md
    rel: extends
  - path: decisions/hn_promise_protection.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# pre-check SEALED 면제 갭

## 증상

다운스트림이 `harness-upgrade`로 v0.33.0 fetch한 직후 `/commit` 시:

```
🚫 pre-check 차단 — completed 문서 본문 무단 변경 감지: docs/harness/MIGRATIONS.md
```

`docs_ops.py reopen` → `move` 사이클로 우회 시도해도 같은 경로라 git이
M으로 재등록 → 무한 루프. `## 변경 이력` 면제도 본문 전체 교체라 미충족.

## 근본 원인

v0.32.0 (2117b2c) 약속 박제 보호 도입 시 `SEALED_FOLDERS`에 `docs/harness/`
포함했으나 **starter 자기 운영 누적 파일 면제 누락**:

- `docs/harness/MIGRATIONS.md` — 매 버전 범프 시 본문 누적
- `docs/harness/MIGRATIONS-archive.md` — 6번째 섹션 자동 이동
- `docs/harness/migration-log.md` — 다운스트림 upgrade 기록

이 3개는 **운영상 정기적으로 본문 갱신이 정상 흐름**인데 SEALED 룰이
일반 completed 문서로 처리해 차단.

`pre_commit_check.py:578` 면제 패턴 `^##\s*변경\s*이력\s*$`은 MIGRATIONS.md
의 누적 패턴(`## vX.Y.Z` 버전 헤더)을 인식 못 함.

## 영향 범위

- v0.32.0 이후 다운스트림 모두 — `harness-upgrade`로 v0.33.0 이상 fetch
  시도하면 commit 차단
- starter 자체에서는 v0.33.0 commit이 어떻게 통과했는지 별도 의문 (raw
  `git commit` 직접 호출 가능성, 진단과 무관)
- `reopen` 모델 자체가 MIGRATIONS류와 부정합 — 운영상 항상 `docs/harness/`에
  있어야 하고 다음 upgrade에서 같은 경로로 덮어써짐

## 해결 (v0.33.1)

**옵션 A 채택** — path 화이트리스트:

```python
SEALED_PATH_EXEMPT = (
    "docs/harness/MIGRATIONS.md",
    "docs/harness/MIGRATIONS-archive.md",
    "docs/harness/migration-log.md",
)
if path in SEALED_PATH_EXEMPT:
    continue
```

옵션 B (헤더 패턴 `## v\d+\.\d+` 추가)는 다른 completed 문서의 우연
헤더가 우회 통로가 될 위험이라 기각.

회귀 테스트: `test_pre_commit.py::TestCompletedSeal::test_migrations_md_exempt`
(T42.5). pytest 58 passed (기존 57 + 신규 1).

## 다운스트림 1회 우회 (v0.33.1 fetch 전)

```bash
git stash push -- docs/harness/MIGRATIONS.md
# 본 wave commit 진행
# /harness-upgrade 로 v0.33.1 fetch
git stash pop
# upgrade가 더 최신 본문으로 덮었으면 충돌 → stash drop이 정합
```

다운스트림 실측 검증 (2026-05-02): 3/3 통과. stash drop으로 충돌 해소,
정상 흐름 복귀.

## 재발 방지

**SEALED류 룰 도입 시 starter 자기 운영 파일 영향 검토 의무**:

다운스트림 차단을 일으킬 수 있는 게이트 (시크릿·SEALED·dead link·
todo_fixme 등) 신설 시 starter 자기 영역의 운영 파일을 먼저 식별:

- `docs/harness/MIGRATIONS.md` — 매 버전 누적
- `docs/harness/MIGRATIONS-archive.md` — 자동 archive
- `docs/harness/migration-log.md` — 다운스트림 기록
- `README.md` — 변경 이력 5개 유지 (루트라 SEALED_FOLDERS 영향 없음)
- `.claude/HARNESS.json` — 매 commit 버전 갱신

위 파일 중 게이트가 차단할 가능성이 있는 것은 path 화이트리스트로 면제
선언. 형제 사례: `incidents/hn_secret_line_exempt_gap.md` — agents/threat-analyst.md를
시크릿 패턴 설명문 때문에 차단했던 동일 패턴.

## 관련

- `decisions/hn_promise_protection.md` — v0.32.0 SEALED 룰 도입 결정
- `incidents/hn_secret_line_exempt_gap.md` — 같은 패턴 (게이트 면제 갭)
- `.claude/scripts/pre_commit_check.py` SEALED_PATH_EXEMPT — 본 fix
- `.claude/scripts/tests/test_pre_commit.py::test_migrations_md_exempt` — T42.5
