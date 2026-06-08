---
title: frontmatter parser drift between docs validate and LiveOps sync
domain: harness
c: "Ai-prompter WIP title에 따옴표 없는 콜론이 있어 YAML 파서는 실패했지만 docs_ops.py validate는 통과했고 LiveOps sync는 c를 missing으로 처리함"
problem: [P7, P9, P11]
s: [S7, S9, S11]
tags: [docs, frontmatter, sync]
relates-to:
  - path: .claude/rules/docs.md
    rel: references
  - path: ../guides/project_kickoff.md
    rel: references
  - path: harness/hn_downstream_cps_forced_mapping.md
    rel: references
status: completed
created: 2026-06-04
---

# frontmatter parser drift between docs validate and LiveOps sync

## 관찰

`/Users/kann/projects/Ai-prompter/docs/WIP/guides--mt_harness_adapter_boundary.md`의 frontmatter가 다음 형태였다.

```yaml
title: Repo 구조 정리: 제품 구조와 하네스 adapter 경계
```

제목 값 안에 콜론이 있지만 따옴표가 없어 `yaml.safe_load`는 실패했다. 그러나 `docs_ops.py validate`는 단순 line parser로 title/domain/status/created만 확인해 통과했다. 이후 LiveOps WIP sync는 YAML 실패 시 frontmatter를 `{}`로 처리했고, 칸반 카드에는 `CPS C: (missing)`이 들어갔다.

## 영향

- 형식 검증 통과와 실제 runtime parser 성공이 갈라졌다.
- 칸반 카드에는 C가 없는 것처럼 표시되어 사용자가 다시 문제를 발견했다.
- frontmatter parser가 여러 곳에 흩어져 있어 같은 문서를 서로 다르게 해석한다.
- YAML parse 실패가 hard fail이 아니라 silent fallback이라 P9 정보 오염으로 이어진다.

## CPS Rationale

- C → P7: 문서 출력 계약이 도구별로 다르게 해석되어 C 필드가 사라졌다.
- C → P9: `validate` 통과를 품질 증거로 잘못 받아들였고, LiveOps parser 실패는 조용히 묻혔다.
- C → P11: frontmatter 파싱 로직이 `docs_ops.py`와 `hermes_cli.wip_sync`에 다른 방식으로 존재한다.
- P → S7: frontmatter 계약은 한 곳에서 정의되고, 각 runtime이 같은 의미로 읽어야 한다.
- P → S9: YAML parse 실패는 경고가 아니라 차단 또는 명시적 sync 오류가 되어야 한다.
- P → S11: frontmatter parser는 SSOT화하거나 최소한 동일 테스트 fixture를 공유해야 한다.

## 제안

- `docs_ops.py validate`가 YAML frontmatter를 실제로 parse하고 실패 시 오류로 처리한다.
- `hermes_cli.wip_sync`가 YAML parse 실패 시 `{}`로 silent fallback하지 않고 source와 오류를 보고한다.
- frontmatter parser fixture에 "따옴표 없는 콜론 title" 사례를 추가한다.
- WIP sync는 `c`가 missing이면 카드 생성 전에 경고 또는 todo_hold reason에 parse failure를 남긴다.

## LiveOps WIP sync validation behavior

권위 있는 문서 규칙은 `.claude/rules/docs.md`의 "프론트매터", "CPS 인용",
"AC 포맷" 섹션이다. Hermes LiveOps WIP sync는 이 규칙 전체를 복제하지
않고, todo 생성 전 최소 실행 계약만 확인한다. 현재 `hermes_cli/wip_sync.py`
기준으로 WIP 문서는 YAML frontmatter 파싱 성공, `title`, CPS `c`/`problem`/`s`,
`status`, 본문 Acceptance Criteria가 있어야 한다.

유효한 예:

```markdown
---
title: Triage sync behavior
c: "Triage entry must become a compliant WIP-backed todo"
problem: P7
s: [S7]
tags: [triage, wip-sync]
status: in-progress
created: 2026-06-05
---

# Triage sync behavior

**Acceptance Criteria**:
- [ ] Goal: valid WIP creates a held todo with source context.
```

예상 응답: Hermes가 board task를 생성하고, 미완료 WIP는 `todo_hold` 이벤트가
붙은 `todo`로 둔다. 자동 ready 승격은 하지 않는다.

무효한 예:

```markdown
---
title: Missing CPS and AC
problem: P7
status: in-progress
---

# Missing CPS and AC
```

예상 응답: Hermes가 todo를 만들지 않고 sync 결과를 `task_id="(invalid)"`,
`strategy="invalid-wip"`, `status="todo-hold"`로 보고한다. `changed` 메시지는
`blocked-invalid-wip`로 시작하고 `missing CPS c/context`, `missing CPS s`,
`missing Acceptance Criteria`처럼 누락 항목을 이름으로 밝힌다.

**Acceptance Criteria**:
- [x] Goal: docs validate와 LiveOps sync가 같은 frontmatter를 같은 의미로 해석한다.
- [x] Contract: `docs_ops.py validate`에서 YAML parse 실패가 silent `{}` fallback으로 사라지지 않는다.
- [x] Contract: `hermes_cli.wip_sync`에서 YAML parse 실패가 silent `{}` fallback으로 사라지지 않는다.
- [x] Contract: frontmatter parser 테스트에 colon-containing title fixture가 추가된다.
- [x] Verification: `docs_ops.py validate`, `verify-relates`, `eval_harness.py`가 관련 fixture를 통과한다.
- [x] Verification: Ai-prompter WIP 사례가 재현 테스트로 남는다.
- [x] Verification: Triage todo 생성 전 validation behavior가 rule SSOT와 Hermes 응답 형태를 함께 설명한다.

## 구현 결과

- `.claude/scripts/docs_ops.py`: frontmatter 파서를 실제 YAML parser 기반으로 교체하고,
  `validate`가 parse 실패를 오류로 계산하게 했다.
- `.claude/scripts/docs_ops.py wip-sync`: invalid WIP frontmatter를 자동 매칭에서
  skip하고 stderr에 parse 실패와 source path를 출력한다.
- `.claude/scripts/tests/test_docs_ops_staging.py`: 따옴표 없는 콜론 title fixture를
  `validate`와 `wip-sync` 양쪽에 추가했다.
- `/Users/kann/projects/hermes-agent/hermes_cli/wip_sync.py`: 현재 working copy에서
  YAML parse 실패를 `invalid-wip`으로 차단하고 새 todo 카드 생성을 건너뛰는
  동작을 확인했다.
- Hermes `hermes_cli/wip_sync.py`: invalid WIP를 `blocked-invalid-wip` 결과로
  보고하고 todo를 생성하지 않는다. 에러 메시지는 invalid YAML, missing CPS
  c/context, missing CPS problem/s, missing status, missing Acceptance Criteria
  같은 누락 항목을 이름으로 밝힌다.

## 결정 사항

- CPS 갱신: 없음. 기존 P7/P9/P11과 S7/S9/S11 범위 안에서 parser drift와
  silent fallback을 차단했다.
- `hermes_cli.wip_sync` 본체는 `/Users/kann/projects/hermes-agent`의 현재
  working copy에 이미 존재하는 미추적 파일 기준으로 확인했다. 이 repo는
  writable root 밖이므로 본 작업에서는 harness-starter WIP에 완료 증거만 남긴다.

## 실측

- `python3 -m py_compile .claude/scripts/docs_ops.py .claude/scripts/tests/test_docs_ops_staging.py` → 통과.
- 임시 repo 재현: `title: Repo 구조 정리: 제품 구조와 하네스 adapter 경계`가
  `docs validate`에서 `frontmatter YAML parse 실패`로 exit 1.
- 임시 repo 재현: 같은 WIP가 `wip-sync`에서 `자동 sync skip` stderr를 출력하고
  silent fallback으로 처리되지 않음.
- `python3 .claude/scripts/safe_command.py docs-validate` → 오류 0, 기존 날짜 suffix 경고 2.
- `python3 .claude/scripts/safe_command.py verify-relates` → 미연결 0건.
- `python3 .claude/scripts/safe_command.py eval-harness` → exit 0.
- `python3 -m pytest ...` → 실행 불가. 현재 `python3`가
  `/Users/kann/projects/hermes-agent/venv/bin/python3`이고 pytest 미설치.
- `uv run pytest tests/hermes_cli/test_wip_sync.py -q` → sandbox 밖 uv cache 접근
  승인이 거절되어 실행 불가.
- 직접 호출 검증: 따옴표 없는 콜론 title WIP가
  `task_id="(invalid)"`, `strategy="invalid-wip"`,
  `changed=["blocked-invalid-wip: invalid frontmatter YAML: ..."]`로 반환되고
  silent `(missing)` C 카드로 생성되지 않음.
- 2026-06-05 직접 호출 재검증: `/Users/kann/projects/hermes-agent`를
  `sys.path`에 추가하고 임시 root + `dry_run=True`로 실행한 결과
  `SyncResult(task_id='(invalid)', status='todo-hold', strategy='invalid-wip')`.
- `/Users/kann/projects/hermes-agent/tests/hermes_cli/test_wip_sync.py` 확인:
  invalid frontmatter와 missing CPS/AC 케이스가 `task_id == "(invalid)"`,
  `strategy == "invalid-wip"`, `blocked-invalid-wip` 메시지, task 미생성을 검증한다.
