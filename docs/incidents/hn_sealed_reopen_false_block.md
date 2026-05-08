---
title: pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단
domain: harness
problem: P6
solution-ref:
  - S6 — "docs_ops.py move 신호 → pre-check 봉인 면제"
tags: [pre-check, sealed, false-block, reopen, move]
symptom-keywords:
  - "completed 문서 본문 무단 변경 감지"
  - "reopen→move 정상 절차"
  - "M\\tdecisions/"
relates-to:
  - path: incidents/hn_sealed_migrations_exempt_gap.md
    rel: extends
  - path: decisions/hn_sealed_link_exempt.md
    rel: extends
status: completed
created: 2026-05-08
updated: 2026-05-08
---

# pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단

## 증상

```
docs_ops.py reopen docs/decisions/foo.md
# → docs/WIP/decisions--foo.md 이동, status=in-progress
# WIP 본문 수정 후
docs_ops.py move docs/WIP/decisions--foo.md
# → docs/decisions/foo.md 이동, status=completed
git add docs/
python3 .claude/scripts/pre_commit_check.py
# ❌ "completed 문서 본문 무단 변경 감지" 차단
```

`## 변경 이력` 섹션 아래에만 추가하면 통과하지만, 본문 중간 수정 시 차단.

## 근본 원인 (실측 확인)

`reopen`과 `move` 모두 `git mv` + `write_frontmatter_field` 후 **`git add`를 호출하지 않는다.**

결과적으로 git은 rename 두 번이 상쇄돼 **원본 파일의 수정(M)** 으로 처리한다:

```
git diff --cached --name-status
M    decisions/foo.md    ← rename 상쇄, 수정만 남음
```

`pre_commit_check.py:538`은 `status_char not in ("M",)` 조건으로 rename(R)·삭제(D)·추가(A)를 면제하지만, 이 경로에서 최종 status_char가 M이 되므로 면제 미적용.

실측 재현 (임시 git 저장소):
```
name-status: 'M\tdecisions/foo.md\n'
```

## 선행 사례

- `hn_sealed_migrations_exempt_gap.md` — path 화이트리스트 방식
- `hn_sealed_link_exempt.md` — hunk 내 삭제 여부로 교체 vs 순수 추가 판별

## 해결 방향

`M` 파일이 reopen→move 정상 절차를 거쳤는지 판별하는 방법:

**옵션 A: docs_ops.py move가 완료 후 세션 파일에 경로 기록, pre-check이 대조**
- 장점: 명시적 추적, false positive 없음
- 단점: 세션 파일 의존, docs_ops.py + pre-check 양쪽 수정 필요, `git add` 없이 file I/O 추가

**옵션 B: git log에서 rename 체인 추적**
- `git log --diff-filter=R --follow --name-status -1 -- <path>` 로 직전 rename 이력 확인
- 단점: 느림, 인덱스(staged) 기준 아니라 커밋 이력 기준 — 아직 커밋 안 된 상태에선 동작 안 함

**옵션 C: sealed 보호 로직에 status 체크 추가**
- pre-check이 파일 현재 상태를 읽을 때 `status: completed`를 확인함
- `git diff --cached` diff에서 `status: in-progress → status: completed` 변경이 포함돼 있으면 → reopen→move 경로 → 면제
- 장점: 외부 파일 의존 없음, diff만으로 판단 가능
- 단점: 악의적 우회 가능성 (status 필드만 바꿔서 본문 무단 변경) — 단, completed 봉인의 위협 모델은 Claude 실수이지 악의적 공격이 아님

**채택: 옵션 A (세션 파일)** — `docs_ops.py move`가 완료 시 `session-moved-docs.txt`에 경로 기록, pre-check이 대조해 면제.

옵션 C(diff에 +status: completed 검사)는 기각:
- base(HEAD): `decisions/foo.md`의 `status: completed`
- staged 최종: `status: completed` (동일)
- → status 필드는 diff에 변화 없음(context line). `-U0`이라 미표시.
- 실측 확인: `diff --cached -U0 --` 출력에 `+status:` 라인 없음.

옵션 A 근거:
1. `docs_ops.py move`만이 이 경로를 만들 수 있음 (Claude 규칙 강제)
2. 세션 파일은 commit 성공 시 자동 삭제 → 다음 세션 오염 없음
3. `memory.md` "확장 금지" 규칙 갱신 (2→3개)으로 정합

## 작업 목록

### 1. pre_commit_check.py 면제 로직 추가

**영향 파일**: `.claude/scripts/pre_commit_check.py`

**Acceptance Criteria**:
- [x] Goal: `session-moved-docs.txt` 경로 대조로 reopen→move 경유 파일 봉인 면제
  검증:
    review: self
    tests: pytest -m gate
    실측: T42.9(reopen→move 면제) + T42.10(무단 변경 여전히 차단) 통과

### 2. 회귀 테스트 추가

**영향 파일**: `.claude/scripts/tests/test_pre_commit.py`

**Acceptance Criteria**:
- [x] Goal: T42.9(reopen→move 면제) + T42.10(세션 파일 없으면 차단) 테스트 추가
  검증:
    review: self
    tests: pytest -m gate
    실측: gate 테스트 전체 통과

### 3. CPS S6 박제 인용 정정 (post-finalize, 2026-05-08)

**영향 파일**: `docs/guides/project_kickoff.md`, 본 WIP frontmatter

**Acceptance Criteria**:
- [x] Goal: CPS S6에 8번째 방어 레이어 추가 + frontmatter `solution-ref` 인용을 새 항목 substring으로 정정
  검증:
    review: self
    tests: 없음
    실측: PYTHONIOENCODING=utf-8 python .claude/scripts/eval_cps_integrity.py 결과 박제 의심 0건

## 결정 사항

- 옵션 A 채택 — `docs_ops.py move` → `session-moved-docs.txt` 기록 → pre-check 대조
  - 반영: `docs_ops.py:341-348` (세션 파일 write), `pre_commit_check.py:553-559` (면제 판정)
- `memory.md` session 파일 목록 2→3개 갱신
- CPS 갱신: S6에 8번째 방어 레이어 추가 — "docs_ops.py move 신호 → pre-check 봉인 면제" (v0.38.4 사고가 S6 메커니즘 보강 사례. 2026-05-08 eval --harness 박제 의심 보고로 추적)

## 변경 이력

- 2026-05-08 (v0.38.4 후속, post-finalize): eval --harness가 S6 인용 박제 의심 보고
  → CPS S6에 8번째 방어 레이어 추가, frontmatter `solution-ref` 인용을 새 항목 substring으로 정정.
  본문 무변경 — frontmatter + ## 결정 사항 갱신만.

## 메모

- doc-finder fast scan: hn_sealed_link_exempt.md, hn_sealed_migrations_exempt_gap.md hit
- 실측 재현: 임시 git 저장소에서 `M\tdecisions/foo.md` 확인 (rename 상쇄 실증)
- 옵션 C(diff `+status: completed`) 시도 → 기각: base·staged 모두 completed라 diff에 변화 없음 (실측 확인)
- 옵션 A 구현 후 T42.9 + T42.10 포함 gate 22 passed
- 버그 리포트 재현표: 2026-05-08 / docs/decisions/ad_stats_redesign.md / 5단계 작업 목록 추가 / ## 변경 이력으로 이동 우회
