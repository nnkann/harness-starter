---
title: pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단
domain: harness
tags: [pre-check, secret-scan, false-positive, regex-gap]
symptom-keywords:
  - "🚫 pre-check 차단 — 시크릿 line-confirmed"
  - "s1_level"
  - "S1_LINE_EXEMPT"
  - "threat-analyst.md"
status: completed
created: 2026-05-01
updated: 2026-05-01
---

# pre-check 시크릿 line 면제 갭

## 증상

다운스트림에서 `/commit` 또는 pre-commit hook 실행 시:

```
🚫 pre-check 차단 — 시크릿 line-confirmed (s1_level)

  hit 위치 (검증 결과 모두 false positive):
    .claude/agents/threat-analyst.md:766-767  ← 시크릿 패턴 설명문 + grep 명령
    .claude/scripts/pre_commit_check.py:1683  ← 정규식 정의 (이건 면제됨)
    .claude/scripts/test_pre_commit.py:2664   ← 테스트 픽스처 (이건 면제됨)
```

`.claude/agents/threat-analyst.md`가 시크릿 패턴 SSOT를 설명용으로 인용한
줄에서 `S1_LINE_PAT`이 매치 → line-confirmed 차단.

## 원인

[pre_commit_check.py:425](../../.claude/scripts/pre_commit_check.py#L425):

```python
S1_LINE_EXEMPT = re.compile(r"^\.claude/scripts/")
```

차단용 line 스캔 면제가 `^\.claude/scripts/`만 cover. `S1_EXEMPT`(file-only
경고용)는 `\.md$|^docs/`로 넓게 걸려 있는데 line 면제는 좁아 일관성 깨짐.

같은 패턴을 SSOT로 문서화하는 다른 `.claude/` 위치 전부 무방비:

- `.claude/agents/threat-analyst.md` ← 다운스트림 신고 위치
- `.claude/rules/security.md` ← 시크릿 룰 정의
- `.claude/skills/eval/SKILL.md` ← 시크릿 스캔 절차
- `.claude/memory/feedback_eval_secret_scan.md` ← 과거 피드백

upstream 0.28.1까지 같은 룰. starter 자체에서도 threat-analyst.md를 수정하면
재현 (단, 현재는 staged 상태가 아니라 발현 안 됐을 뿐).

## 해결

`S1_LINE_EXEMPT` 확장:

```python
S1_LINE_EXEMPT = re.compile(r"^\.claude/(scripts|agents|rules|skills|memory)/")
```

`.claude/` 하위 하네스 내부 문서·패턴 SSOT 위치를 line 면제. 사용자 코드
(`src/`, `app/`)·문서(`docs/`)는 여전히 line 스캔 적용 — 면제 범위는
**하네스가 자기 패턴을 문서화하는 위치**로 한정.

## 작업 목록

### 1. S1_LINE_EXEMPT 확장 + 회귀 테스트
> kind: bug

**영향 파일**: `.claude/scripts/pre_commit_check.py:425`,
`.claude/scripts/test_pre_commit.py` (`TestSecretScan`)

**Acceptance Criteria**:
- [x] Goal: `.claude/agents/*.md` 같은 패턴 SSOT 문서가 시크릿 패턴을 인용한 줄에서 line-confirmed 차단되지 않는다
- [x] `S1_LINE_EXEMPT` 정규식이 `^\.claude/(scripts|agents|rules|skills|memory)/`로 확장됨
- [x] `TestSecretScan`에 면제 회귀 테스트 1건 추가 (`.claude/agents/foo.md`에 시크릿 패턴 인용 줄 추가 → 차단 안 됨)
- [x] `src/`·`docs/` 등 비-하네스 경로는 여전히 차단됨 (기존 `test_line_confirmed_blocks` 통과)
- [x] 영향 범위: pre_commit_check.py — `pytest -m secret` 회귀 체크

## 결정 사항

- 면제 범위는 `.claude/(scripts|agents|rules|skills|memory)/`로 한정. `docs/`는
  포함 안 함 — 사용자가 paste 사고로 진짜 시크릿을 docs에 넣을 가능성을
  잡기 위함. 하네스 내부 문서는 패턴 인용 의도가 명확하므로 면제 안전.
- 정규식을 더 엄격하게 만드는(payload 요구) 대안은 회피 — 진짜 시크릿
  형식 다양성 때문에 false negative 위험.

## 같은 카테고리 갭 전수 조사

`pre_commit_check.py`의 다른 정규식이 같은 패턴(`^\.claude/scripts/`만
면제, 다른 `.claude/` 하위 누락)을 가졌는지 검토:

| 정규식 | 면제 패턴 | 갭? |
|--------|----------|----|
| `S1_LINE_EXEMPT` (line 425) | `^\.claude/scripts/` → 본 fix로 확장 | 해결 |
| `SKIP_TODO` (line 213) | `\.md$\|^\.claude/scripts/` 광역 | 없음 (`.md`로 cover) |
| `S1_EXEMPT` (line 417) | `\.md$\|^docs/` 광역 | 없음 (file-only는 광역) |
| `ENOENT_PATTERNS`·`stale_pat`·`UPSTREAM_PAT`·`META_M_PAT` | 면제 아닌 포함 매칭 | 카테고리 무관 |

`.claude/hooks/`는 본 starter에 부재. `.claude/agents/rules/skills/memory/`는
모두 `.md` 파일만 → `\.md$` 면제로 자동 cover. 결론: 시크릿 line scan만
좁은 면제를 썼던 단일 갭. 본 fix로 카테고리 종결.

## 메모

- doc-finder fast scan: 없음 (S1_LINE_EXEMPT 자체 결정 SSOT 없음)
- 유사 사고 사료: `hn_lint_enoent_pattern_gaps.md`(린터 정규식 갭),
  `hn_bash_n_flag_overblock.md`(매처 오탐). 본 사고는 시크릿 영역의
  동일 패턴 — 정규식 면제 범위 누락.
- CPS 갱신: 없음 (harness-starter는 CPS 부재 — `status: sample`만 존재)
- 회귀 검증: `pytest -m secret` 4/4 통과 (`test_harness_doc_line_exempt` 신규).
- 별개 환경 이슈: `pytest -m docs_ops` 다수 fail은 본 변경 전(git stash)
  에도 동일 발생 → 본 작업 차단 사유 아님. 별도 추적 필요.

## 추가 발견 — docs_ops.py move untracked WIP fallback 갭

본 incident 처리 중 `docs_ops.py move`로 untracked WIP를 이동하려다
`add=0 rm=128` returncode 1 발견. 같은 fix wave에 묶어 처리.

**원인**: [docs_ops.py:322-330](../../.claude/scripts/docs_ops.py#L322) 의
fallback 흐름이 `git mv` 실패 후 `shutil.move` + `git add dest` +
`git rm --cached src`를 무조건 실행. **untracked 파일은 인덱스에 없어
`git rm --cached`가 항상 returncode 128**로 실패 → cmd_move가 status·
역참조 갱신 전에 returncode 1 반환.

**구조적 영향**: WIP를 git add 없이 working tree에 만들고 곧바로
`docs_ops.py move`로 이동하는 모든 흐름이 매번 실패. implementation
스킬이 만든 신규 WIP를 commit 스킬 Step 2에서 이동할 때 그 흐름과 정확히
일치 → 흐름의 잠재 결함.

**해결**: `git mv` 실패 시 `git ls-files --error-unmatch <src>`로 src가
인덱스에 있을 때만 `git rm --cached` 시도. untracked는 skip.

**검증**: 임시 git repo에서 untracked WIP move → returncode 0, dest 이동·
staged·`status: completed` 갱신 모두 통과. 회귀 테스트 추가:
[test_pre_commit.py](../../.claude/scripts/test_pre_commit.py) `TestMoveUntrackedWip::test_untracked_move_succeeds` (`pytest -m docs_ops`).

**환경 한계 메모**: 본 sandbox에서 pytest 직접 실행은 별개 Windows
환경 결함(`pre_commit_check.py` import가 staged diff cp949 디코딩 실패 →
`stdout=None` 또는 module-level main 로직이 sys.exit(2))으로 막혀
`PYTHONIOENCODING=utf-8` + 임시 repo subprocess 우회로 검증. 이
환경 결함은 dead-link 회귀 15건 fail의 동일 원인으로 보임 — 별도 추적.
