---
title: Codex 하네스 approval/hook 정책 검토
domain: harness
problem: [P4, P5, P7]
s: [S4, S5, S7]
tags: [codex, approval, hook, sandbox, workflow]
status: completed
created: 2026-05-17
updated: 2026-05-17
relates-to:
  - path: harness/hn_codex_port.md
    rel: extends
  - path: .claude/rules/hooks.md
    rel: references
  - path: incidents/hn_bash_n_flag_overblock.md
    rel: references
  - path: incidents/hn_matcher_false_block.md
    rel: references
---

# Codex 하네스 approval/hook 정책 검토

## Context

현재 Codex 하네스는 hook 자체가 비어 있고(`.codex/hooks.json` = `{"hooks": {}}`),
별도 `.codex/config.toml`도 없어 approval 정책은 Codex CLI 기본값
("untrusted" — sandbox 외 모든 명령 명시 승인)에 의존한다.

이 구조는 false positive 사고
(`bash_n_flag_overblock`·`matcher_false_block_and_readme_overwrite`)
재발 위험을 0으로 유지하지만, 다음 두 흐름에서 작업 마찰이 크다.

- 문서 작성·검토 흐름: `rg`·`git status`·`docs_ops.py list`·cluster scan
  같은 **읽기 전용 조회**마다 승인 요청 발생
- "정말 위험한 승인"이 잡음 속에 묻혀 안전장치 신뢰도 저하

목표는 안전성 유지 + 위험도 기반 분류로 흐름을 회복하는 것이다.

## 분류

### 1. 항상 허용 후보 (read-only, 부작용 없음)

| 명령 | 근거 |
|------|------|
| `rg ...` | 검색 전용, 파일 수정 없음 |
| `Get-Content` / `cat` | 읽기 전용 |
| `git status` / `git diff` / `git log` / `git show` | 워킹 트리 읽기 |
| `docs_ops.py` 조회 서브커맨드 (`list`·`show`·`cps list/show/stats`·`verify-relates`) | dry-run 검증 |
| `pre_commit_check.py` | exit code만 반환, 파일 변경 없음 |

### 2. 조건부 허용 후보 (산출물 발생)

| 명령 | 조건 |
|------|------|
| `pytest <path>` | `.pytest_cache/`·`__pycache__/` 생성 — `.gitignore` 확인 후 prefix 허용 |
| formatter (`black`·`ruff format`·`ruff check --fix`) | 파일 수정 — `.claude/**`·`.codex/**`·`.agents/**` 경로 제외 필터 필요 |
| build / lint (다운스트림) | starter는 N/A. 다운스트림 분기 결정 |

### 3. 계속 승인 필요 (위험)

- 파일 삭제·이동: `rm`·`mv`·`git rm`·`Remove-Item`
- 커밋·푸시·되돌리기: `git commit`·`git push`·`git reset --hard`·`git rebase`
- hook/설정 변경: `.codex/hooks.json`·`.claude/settings.json`·`.codex/config.toml`
- 설정성 파일 수정: `.claude/**`·`.codex/**`·`.agents/**`·`AGENTS.md`·`CLAUDE.md`
- 의존성 설치: `pip install`·`npm install`·`uv add`
- 네트워크: `curl`·`wget`·`gh`·`git fetch/pull/push`
- 파일 이동·생성하는 docs_ops: `move`·`reopen`·`cluster-update --write`

## Local Verification

2026-05-17 로컬 확인 결과:

- `codex --help`는 `--ask-for-approval untrusted|on-request|never` 모드만 노출한다.
- `~/.codex/config.toml`에는 `projects.*.trust_level`, `windows.sandbox`, `hooks.state`, `features`, `memories`만 존재한다.
- 로컬 config와 CLI help 어디에서도 `approval_policy.always_allow` 같은 명령별 whitelist 스키마가 확인되지 않았다.
- Codex tool escalation은 요청 시 `prefix_rule`을 제안할 수 있고, 사용자가 UI에서 해당 prefix를 지속 승인하는 흐름은 확인된다.

따라서 `.codex/config.toml`을 신설해 명령별 allowlist를 넣는 안은 현재 보류한다. 확인되지 않은 스키마를 적용하면 승인 마찰을 줄이지 못하고, 오히려 새 설정 표면만 만든다.

## Decision Candidate

**즉시 적용안**: repo 설정 파일을 만들지 않고, `.claude/scripts/safe_command.py` dispatcher를 통해 안전한 조회·검증 명령만 좁은 prefix로 지속 승인한다.

dispatcher 위치는 호출 대상(`docs_ops.py`·`pre_commit_check.py`)과 같은 `.claude/scripts/` 영역. 명령 자체는 런타임 중립이라 Codex뿐 아니라 Claude 워크플로에서도 사용 가능. `.codex/`는 Codex CLI 직접 설정만 남긴다.

구현 위치:

- `.claude/scripts/safe_command.py`
- `.claude/scripts/tests/test_safe_command.py`
- `AGENTS.md` "Codex 안전 조회/검증"

dispatcher 허용 명령:

- `status`, `diff`, `log`, `show`
- `rg`, `read`
- `docs-list`, `docs-show`, `docs-validate`
- `cps-list`, `cps-show`, `cps-stats`
- `verify-relates`, `precheck`

조건부 prefix:

- `python -m pytest .claude/scripts/tests/`는 dispatcher 밖에서 별도 승인 여부를 결정한다.

`.codex/hooks.json`은 빈 상태 유지. hook은 추가하지 않는다. `.claude/rules/hooks.md`의 argument-constraint 금지 원칙은 `settings.json` hooks.matcher 한정이므로, Codex app의 prefix approval과는 별도 영역이다.

**보류안**: `.codex/config.toml` 신설. Codex CLI 또는 공식 문서에서 명령별 allowlist 스키마가 확인될 때만 재검토한다.

## 선결 검증 — Codex CLI 스키마

적용 전 필수 확인:

- Codex CLI 최신 버전의 명령별 approval allowlist 지원 여부
- 지원한다면 `.codex/config.toml` 또는 `~/.codex/config.toml`의 정확한 스펙
- 화이트리스트 패턴이 토큰 단위 검증인지, 단순 prefix 매칭인지
  (후자라면 `rg ... | xargs rm` 같은 파이프 우회 가능성 확인)
- 프로젝트 `.codex/config.toml`이 `~/.codex/config.toml`을 override하는 방식

권장: 공식 문서 또는 `codex --help`/릴리스 노트로 스키마 확정. 확인 전 설정 파일 적용 금지.

## 위험과 완화

| 위험 | 완화 |
|------|------|
| `rg` prefix 승인이 파이프(`\| xargs rm`)를 통과시킬 수 있음 | Codex 승인기가 shell segment 단위로 평가하는지 확인. 의심되면 지속 승인하지 않음 |
| `docs_ops.py` 전체 prefix가 write 서브커맨드까지 허용할 수 있음 | 가능하면 `docs_ops.py list/show/cps/verify-relates`만 개별 승인. 전체 prefix는 보류 |
| `pytest`가 starter 외 경로에서 conftest 부작용 일으킴 | starter는 `.claude/scripts/tests/`로 한정 |
| Codex CLI 버전 차이로 설정 키 이름이 다름 | 설정 파일 적용 전 공식 문서 확인 필수. 추정 적용 금지 |
| `.codex/config.toml` 자체가 새 hook-fragility 표면 | 현재는 신설하지 않음. 스키마 확인 후에도 rollback 쉬운 단일 파일로만 도입 |
| Claude 동작 영향 | Codex app prefix approval은 Claude 설정과 분리. `.claude/settings.json`은 변경하지 않음 |

## Open Questions

- Codex CLI가 명령별 approval allowlist 설정을 지원하는가?
- `pytest` prefix 허용 시 `.pytest_cache/` 등 산출물 발생 OK인가, 명시 승인 유지인가
- `docs_ops.py` prefix approval 입도 — 서브커맨드별 분리 vs 전체 prefix 허용 후 write 분기는 스킬 경유 차단
- `.codex/config.toml` 신설은 현재 보류. 스키마 확인 후에도 첫 도입 1회는 사용자 명시 승인 필요
- 본 결정과 `hn_runtime_ssot_generation.md` Phase 0 audit의 wave 결합 여부 (SSOT cascade 정합성)

## Acceptance Criteria

- [x] Goal: Codex 하네스 approval 정책의 위험도 기반 분류를 검토 가능한 형태로 박제한다.
  검증:
    tests: 문서 검토.
    실측: 사용자가 "항상 허용 / 조건부 / 강승인" 3분류와 safe-command dispatcher 적용안을 판단할 수 있다.
- [x] S5: 안전한 조회·검증 명령 허용 목록을 명시해 문서·검토 흐름 마찰을 줄인다.
  검증:
    tests: `python -m pytest .claude/scripts/tests/test_safe_command.py -q`
    실측: `rg`·`git status`·`docs_ops.py` 조회·`pre_commit_check.py`가 자동 허용 후보로 분류된다.
- [x] P4: hook argument-constraint 금지 원칙(`.claude/rules/hooks.md`)과의 경계를 명확히 한다.
  검증:
    tests: 문서 검토.
    실측: `settings.json` hooks.matcher와 Codex app prefix approval의 영역이 분리됐음을 설명한다.
- [x] P7: Codex CLI 스키마 검증을 선결 조건으로 명시해 추정 적용을 차단한다.
  검증:
    tests: 문서 검토.
    실측: Open Questions에 명령별 allowlist 지원 여부 확인 항목이 포함되고, 설정 파일 도입은 보류된다.
