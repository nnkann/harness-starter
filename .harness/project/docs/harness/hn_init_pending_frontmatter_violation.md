---
title: harness-init pending placeholder frontmatter violation
domain: harness
c: "h-setup.sh가 docs/WIP/harness_init_pending.md를 생성할 때 정식 YAML frontmatter 없이 '> status: pending' 형식의 규약 미준수 WIP 문서를 만든다"
problem: [P7, P9]
s: [S7, S9]
tags: [init, docs, downstream]
relates-to:
  - path: ../guides/project_kickoff.md
    rel: references
  - path: ../decisions/hn_improvement.md
    rel: references
  - path: harness/hn_downstream_cps_forced_mapping.md
    rel: references
status: completed
created: 2026-06-04
updated: 2026-06-06
---

# harness-init pending placeholder frontmatter violation

## 관찰

`h-setup.sh`는 신규 downstream에 하네스 파일을 설치한 뒤 `docs/WIP/harness_init_pending.md` placeholder를 생성한다. 현재 생성 본문은 다음 형태다.

```markdown
> status: pending

# 하네스 초기화 대기 중
```

이는 `.claude/rules/docs.md`의 WIP 문서 frontmatter 규약과 맞지 않는다. `docs/WIP/`에 들어가는 문서라면 최소한 `title`, `domain`, `problem`, `s`, `tags`, `status`, `created`를 가진 YAML frontmatter를 가져야 한다.

## 영향

- 하네스가 downstream에 첫 문서부터 규약 위반 예시를 배포한다.
- 사용자는 "하네스 초기화 대기 중" 문서를 보고 쓸모없고 이상한 문서라고 판단한다.
- `docs_ops.py validate`는 fallback 또는 예외 경로 때문에 이 placeholder를 놓칠 수 있지만, 의미상 문서 규약 위반은 남는다.
- placeholder가 칸반에 sync된 뒤 init 완료로 파일이 삭제되어도 stale 카드가 남을 수 있다.

## CPS Rationale

- C → P7: 하네스가 생성한 문서의 출력 계약이 문서 규칙과 다르다. 사용자는 이 파일이 제품 WIP인지, 하네스 상태 표식인지, 삭제 대상인지 구분하기 어렵다.
- C → P9: fallback 형식이 작동한다는 이유로 정식 frontmatter 위반이 정상처럼 남는다. 이는 라벨/관측을 품질 증거로 오인하는 정보 오염이다.
- P → S7: placeholder라도 WIP에 놓인다면 소유권과 출력 계약을 정식 frontmatter로 드러내야 한다.
- P → S9: 설치 스크립트 산출물이 문서 규약을 만족하는지 테스트로 검증해야 하며, fallback 통과를 완료 증거로 삼지 않아야 한다.
- S → AC: AC는 `h-setup.sh` 생성 placeholder가 정식 frontmatter를 갖고, init 완료 후 해당 placeholder의 stale kanban task 처리까지 확인해야 한다.

## 제안

### A. placeholder를 정식 WIP 문서로 생성

`h-setup.sh`의 `harness_init_pending.md` 생성 블록을 YAML frontmatter로 바꾼다.

필수 방향:

- `domain: meta` 또는 `domain: harness` 중 downstream 규약에 맞는 값을 선택한다.
- `problem`/`s`는 downstream CPS가 아직 없으므로 예외 설계가 필요하다.
- 예외 설계가 없다면 이 파일을 `docs/WIP/`가 아닌 하네스 상태 경로로 옮기는 편이 낫다.

### B. placeholder 위치 재검토

이 파일이 실제 작업 문서가 아니라 상태 표식이라면 `docs/WIP/`에 두는 것 자체가 부적절할 수 있다. 후보:

- `.harness/state/init_pending.md`
- `.harness/status/init_pending.json`
- `docs/WIP/`에는 정식 작업 문서만 생성

### C. init 완료 후 stale kanban task archive

`harness-init`이 placeholder를 삭제하면 WIP sync가 해당 source task를 자동 archive하거나 stale로 표시해야 한다.

**Acceptance Criteria**:
- [x] Goal: 신규 downstream에 생성되는 init pending 산출물이 하네스 문서 규약을 위반하지 않는다.
  검증:
    review: self
    tests: `python3 .claude/scripts/docs_ops.py validate`
    실측: validate 오류 0, 기존 archived 파일명 경고 2건.
- [x] Problem AC (P7): `harness_init_pending.md`를 유지한다면 정식 frontmatter 또는 명시적 예외 규칙이 정의된다.
- [x] Solution AC (S7): 상태 표식이라면 `docs/WIP/` 밖으로 이동하는 설계가 결정된다.
- [x] Verification AC (S9): `h-setup.sh` 테스트가 placeholder frontmatter 또는 상태 파일 위치를 검증한다. ✅
- [x] Guardrail AC (P9/S9): init 완료 후 placeholder 삭제 시 kanban stale task가 archive되는 경로를 확인한다.

## 구현 결과

- `harness_init_pending.md`는 기존 결정 `docs/decisions/hn_improvement.md`의 A안에 따라 `docs/WIP/`에 유지한다.
- `h-setup.sh` 생성 블록이 정식 YAML frontmatter를 쓴다: `title`, `domain`, `c`, `problem`, `s`, `tags`, `status`, `created`.
- `.claude/scripts/tests/test_h_setup_runtime_metadata.py`가 placeholder frontmatter와 `> status: pending` 미포함을 검증한다.
- `rg -n "kanban|Hermes|archive|stale" .claude/scripts .claude/skills .agents/skills .harness -S` 확인 결과, starter repo 안에는 init 완료 후 Hermes kanban task를 archive하는 구현 경로가 없다. `harness-init` skill도 `harness_init_pending.md` 삭제를 명시하지 않는다. stale task archive는 Hermes-managed external board 경계로 남는다.

## 검증

- tests: `bash -n h-setup.sh` PASS.
- tests: `python3 -m py_compile .claude/scripts/safe_command.py` PASS.
- tests: `python3 .claude/scripts/safe_command.py precheck` PASS (`pre_check_passed: true`; 기존 완료/중단 WIP cleanup 경고 3건은 본 변경 전 worktree 상태).
- tests: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q` 실행 불가. `/Users/kann/projects/hermes-agent/venv/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/bin/python3` 모두 `No module named pytest`.
- 실측: `git diff -- h-setup.sh .claude/scripts/tests/test_h_setup_runtime_metadata.py`에서 placeholder frontmatter 생성과 회귀 assertion 추가 확인.

## 메모

이 문제는 downstream `Ai-prompter`에서 init 후 stale 카드로 재노출됐다. 파일 자체는 삭제됐지만, 카드가 남으면서 사용자가 placeholder의 품질 문제를 다시 발견했다.
