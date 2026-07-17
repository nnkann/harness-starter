---
title: AI 이후 하네스 방향 정렬 계획
domain: harness
c: "AI 하네스 7요소 논의 이후, 현재 하네스를 더 가볍고 검증 중심인 다중 프로젝트 운영 도구로 정렬해야 한다."
problem: [P5, P6, P7, P11]
s: [S5, S6, S7, S9, S11]
tags: [context, cps, eval-harness, dispatcher, orchestration]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: extends
  - path: harness/hn_simplification.md
    rel: extends
  - path: decisions/hn_typed_ac_contract.md
    rel: extends
  - path: decisions/hn_eval_cps_integrity.md
    rel: extends
  - path: decisions/hn_git_subtree_policy.md
    rel: supersedes
status: completed
created: 2026-06-03
updated: 2026-06-06
---

# AI 이후 하네스 방향 정렬 계획

## 배경

AI 하네스 논의의 핵심은 모델 자체보다 모델을 둘러싼 컨텍스트, 도구,
오케스트레이션, 상태, 검증, 비용 판단이 품질을 가른다는 점이다.

현재 `harness-starter`는 범용 agent runtime이 아니라 코딩 에이전트의
추측 실행, 거짓 완료, 컨텍스트 팽창, 다운스트림 실패를 줄이는 운영
하네스다. 따라서 방향은 실행 플랫폼 확장이 아니라 다음 네 가지로 좁힌다.

1. 컨텍스트는 압축하고, 반복 지식은 skill 또는 agent로 이동한다.
2. 오케스트레이션은 `planning -> document -> implementation -> test -> commit`
   기본 흐름을 유지하되, CPS가 끼워 넣을 단계와 반복 여부를 결정한다.
3. 검증 불변식은 모델 성능으로 대체하지 않는다.
4. 다중 프로젝트 운용에 맞지 않는 절대 규칙, 특히 worktree 금지는 폐기한다.
5. sandbox는 사용하되, 권한 문제가 모두 해결된 뒤에만 실행 기본값으로 삼는다.

## CPS Rationale

- C -> P: 하네스가 프로젝트 수 증가와 모델 성능 변화에 맞춰 가벼워지지 않으면 P5 컨텍스트 팽창, P7 계약 불투명, P11 동형 drift가 누적된다. 검증 흐름을 약화하면 P6 거짓 완료가 재발한다.
- P -> S: S5는 컨텍스트 최소화, S6은 검증 책임 고정, S7은 소유권과 출력 계약 명시, S9는 주관 격리와 다층 검증, S11은 동형 규칙 drift 정리를 담당한다.
- S -> AC: AC는 worktree 금지 폐기, 컨텍스트 이동 기준, CPS 흐름 결정권, eval/pre-check/dispatcher 강화가 각각 문서와 후속 구현 단위로 닫히는지 확인한다.

## 결정

### 1. worktree 금지 규칙 폐기

기존 결정은 단일 프로젝트, Windows/Git Bash, worktree 잔여 관리 부담을 전제로
했다. 현재는 프로젝트 수가 많아져 독립 작업 공간의 가치가 커졌고, blanket
ban은 하네스의 현실 적합성을 떨어뜨린다.

새 원칙:
- `git worktree` 자체를 금지하지 않는다.
- 금지는 "무단 생성"이 아니라 "소유권·정리·변경 보존 계약 없는 생성"으로 좁힌다.
- agent isolation이 worktree를 쓰는 경우, 프로젝트 binding과 정리 책임을 문서화한다.
- 기존 `git subtree` 정책과 worktree 정책을 분리한다.

정리 대상:
- `AGENTS.md` / `CLAUDE.md` 절대 규칙의 worktree 금지 문구.
- `.claude/skills/harness-upgrade/SKILL.md` Step 0.1의 "금지 위반 잔여 정리" 표현.
- `bash-guard.sh`의 `git worktree add` 차단 여부.
- 과거 문서의 현재 정책 참조. completed 문서는 본문 변경 대신 새 결정문에서 supersede한다.

### 1.5. sandbox는 permission-ready 조건부로 사용

sandbox 자체의 가치는 인정한다. 단, sandbox가 기본 실행 환경이 되려면 권한
문제가 모두 해결되어 있어야 한다.

조건:
- 필요한 파일 읽기/쓰기 권한이 명확하다.
- 테스트·빌드·검증이 sandbox 안에서 실제로 실행된다.
- 네트워크·자격 증명·외부 도구 접근이 필요한 작업은 권한 게이트와 실패
  보고 방식이 정해져 있다.
- 권한 문제로 검증이 빠진 경우, sandbox 실행을 완료 증거로 포장하지 않는다.

따라서 sandbox는 "사용 가능하면 좋은 격리 환경"이지, 권한 문제가 남아 있는
상태에서 검증 불변식을 대체하는 근거가 아니다.

### 2. 컨텍스트 압축과 skill/agent 이전

컨텍스트 경량화 기준:
- 매 세션 상시 주입되는 규칙은 최소 불변식만 남긴다.
- 절차 지식은 skill로 이동한다.
- 독립 판단 축은 specialist agent로 이동한다.
- repo 전체 탐색 결과는 prompt에 덤프하지 않고 CPS packet, already-read, expected-output으로 전달한다.

우선 정리 후보:
- 긴 SKILL.md의 후반부 절차 중 호출 시점에만 필요한 내용.
- `implementation`의 specialist routing 세부 설명.
- `commit`의 review prompt 구성 세부.
- `eval --harness`의 레거시 정비 안내와 실제 검사 항목 분리.

### 3. CPS가 흐름을 결정한다

기본 흐름은 다음으로 고정한다.

```text
planning -> document -> implementation -> test -> commit
```

CPS의 역할:
- C는 단일 컨텍스트 기준점이다. "왜 지금 이 문제가 발생했는가"를 붙잡고,
  그 안에 어떤 P#들이 함께 드러나는지, 과거 어떤 S#들이 이미 시도됐는지,
  왜 이번에는 다른 실행 흐름이 필요한지 판단하게 한다.
- 사실상의 C는 task와 일대일로 매칭한다. 즉 `task = 이번에 다루는 단일 C`로
  보고, 하나의 완료 판단으로 닫히는 작업은 하나의 C 안에 복수 P#/S#/AC를 담는다.
- P#는 무엇을 더 관찰해야 하는지 결정한다.
- S#는 어떤 실행 단계와 검증 단계를 추가해야 하는지 결정한다.
- C는 항상 단일로 선택하지만, 복수 P#/S#를 가질 수 있다. 복수 P#/S#는
  C가 넓다는 뜻이 아니라 한 맥락 안에서 문제 차원과 해결 기준이 여러 개라는 뜻이다.
- C는 다른 C와의 연결도 가져야 한다. 같은 실패가 반복되는지, 이전 C의
  해결책이 이번 C에서 부작용을 냈는지, 새 C가 과거 C를 supersede하는지
  `relates-to`와 `docs/cps/cp_*.md` case로 추적한다.
- 예외 기준은 완료 판단과 산출물이다. 한 사용자 요청 안에서도 서로 다른 완료
  기준과 산출물이 생기면 task를 나누고 C도 나눈다. 반대로 같은 요청에서
  시작했고 하나의 완료 판단으로 닫히면 C는 하나로 유지한다.
- 복수 P#는 문제 차원 증가로 보고 specialist 호출 폭을 결정한다.
- 복수 S#는 해결 기준 증가로 보고 반복 검증과 단계 분리를 결정한다.

오케스트레이션은 안정화된 현재 흐름을 유지하되, 새 분기를 추가할 때는
다음 질문을 통과해야 한다.

1. 이 분기가 어떤 C에서 필요해졌는가?
2. 이 C는 과거 어떤 C와 이어지는가?
3. 이 분기가 어떤 P#를 줄이는가?
4. 이 분기가 어떤 S#의 해결 기준을 증명하는가?
5. 매 작업마다 필요한가, 특정 flow에서만 필요한가?
6. skill/agent로 lazy load할 수 있는가?

### 4. 검증 불변식은 유지한다

대체 불가 항목:
- AC의 `Goal` / typed AC / `검증.review` / `검증.tests` / `검증.실측`.
- CPS frontmatter `problem` / `s`.
- pre-check의 staged WIP, typed AC, relates-to, secret gate.
- `/commit` wrapper와 review 선택권.
- `/eval --harness`의 누적 drift 관측.

강화 방향:
- `/eval --harness`가 policy drift, dead rule, obsolete ban, skill bloat 후보를 보고한다.
- CPS/AC 자동 검증이 "번호 존재"를 넘어 흐름-AC 연결 누락을 더 잘 드러낸다.
- `safe_command.py`는 조회·검증 dispatcher로 유지하되, 프로젝트 증가에 맞춰 read-only UX를 개선한다.

## 구현 계획

### Phase 1. worktree 정책 폐기 정리

산출물:
- 새 결정문 또는 기존 `hn_git_subtree_policy.md` supersede 문서.
- `AGENTS.md` / `CLAUDE.md` 절대 규칙 수정.
- `harness-upgrade`의 잔여 worktree 처리 문구 수정.
- 필요 시 `bash-guard.sh` 차단을 허용 또는 승인 게이트로 완화.

검증:
- `rg -n "worktree|워크트리" AGENTS.md CLAUDE.md .claude docs -g '*.md'`에서 현재 정책과 충돌하는 active 문구가 남지 않는다.
- completed 과거 문서는 supersede 관계로만 남고 현재 규칙처럼 읽히지 않는다.

### Phase 1.5. sandbox permission-ready 조건 반영

산출물:
- `AGENTS.md` / `CLAUDE.md`에 sandbox 사용 조건을 추가한다.
- 검증 불변식 문맥에 "권한 문제로 실행되지 않은 sandbox 검증은 완료 증거가
  아니다"를 명시한다.

검증:
- active 규칙에서 sandbox가 permission-ready 조건 없이 완료 증거로 쓰이지 않는다.

### Phase 2. 컨텍스트 압축 inventory

산출물:
- 상시 주입, skill lazy-load, specialist 위임, archive 후보를 나눈 inventory.
- 긴 skill별 "항상 필요한 핵심"과 "호출 후 필요한 세부" 분리안.

inventory:

| 분류 | 남길 위치 | 기준 | 후보 |
|------|-----------|------|------|
| 상시 주입 | `AGENTS.md` / `CLAUDE.md` | 언어, 검증 불변식, 진입점, 금지·권한 계약 | AC/CPS 최소 계약, commit 경유, sandbox permission-ready, worktree 계약 |
| skill lazy-load | `.claude/skills/*/SKILL.md` | 특정 명령을 실행할 때만 필요한 절차 | harness-upgrade merge 절차, commit review prompt 세부, eval 레거시 정비 안내 |
| specialist 위임 | `.claude/agents/*` 또는 deferred tool | 독립 판단 축·반대 논거·성능·보안 | risk/threat/performance/research 판단, 복수 P# 충돌 종합 |
| script 결정화 | `.claude/scripts/*.py|*.sh` | LLM 해석 없이 결정적으로 검사 가능 | policy drift, dispatcher drift, path contract, typed AC gate |
| archive/history | `docs/archived` / MIGRATIONS archive | 현재 정책이 아닌 과거 사건·근거 | worktree blanket ban 과거 incident, 폐기된 eval 모드, 구 hook matcher |

긴 skill 정리 기준:
- "언제 호출할지"와 "입출력 계약"은 skill 앞쪽에 남긴다.
- 실제 병합·검증·리포트 세부는 필요할 때 읽는 하위 섹션으로 둔다.
- 코드로 결정 가능한 검사는 skill 본문에 두지 않고 script + test로 이동한다.
- specialist에게 넘길 때는 전체 문서 대신 `C`, `problem`, `s`, `flow`, `AC`,
  `already-read`, `question`, `expected-output`만 전달한다.

검증:
- spawn 또는 specialist 전달 prompt가 전체 문서 덤프 대신 CPS packet 중심으로 구성된다.
- SKILL.md 본문 증가는 새 규칙 추가가 아니라 기존 절차 이동 또는 삭제를 동반한다.

### Phase 3. CPS flow contract 강화

산출물:
- `planning -> document -> implementation -> test -> commit` 흐름을 기준 흐름으로 명시.
- C를 단일 컨텍스트 기준점으로 정의하고, C -> 복수 P/S -> AC 연결 규칙을 명시.
- task와 C의 일대일 매칭을 기본값으로 두고, 서로 다른 완료 기준과 산출물이
  생길 때만 task/C를 분리한다는 예외 기준을 명시.
- C 간 연결 규칙을 정리한다. 같은 반복 실패, 이전 해결책의 부작용, supersede
  관계는 `relates-to`와 `docs/cps/cp_*.md` case로 남긴다.
- reverse-solution, reverse-evidence, resume, interrupt가 이 흐름 어디에 끼는지 정리.
- CPS가 반복 여부와 specialist 호출 폭을 결정한다는 계약을 implementation mirror에 반영.

검증:
- 새 flow 추가 시 C/P/S/AC 연결과 관련 C 연결이 WIP에 남는다.
- flow 분기 추가가 특정 P#/S# 없이 절차 누적으로만 생기지 않는다.

### Phase 4. 검증 불변식 강화

산출물:
- `/eval --harness` 강화 항목: obsolete rule, skill bloat, policy drift, CPS/AC 연결 약화, dispatcher command drift.
- CPS/AC 자동 검증 강화 후보 목록: flow label 누락, typed AC와 실행 단계 불일치, `검증.실측`의 완료 증거성 부족.
- `safe_command.py` 개선 후보 목록: read-only 명령의 좁은 확장, command별 stdout schema, path guard 유지.

검증:
- eval/pre-check/safe dispatcher 개선은 각각 좁은 테스트 파일 또는 실측 명령을 가진다.
- 자동 검증 불가 항목은 완료 증거로 포장하지 않고 운용 검증으로 분리한다.

**Acceptance Criteria**:
- [x] Goal: AI 이후 하네스 방향을 컨텍스트 경량화, CPS 중심 흐름, 검증 불변식, worktree 정책 폐기, sandbox permission-ready 조건 중심으로 정렬한다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q -k "policy_drift or dispatcher_drift"` + `bash .claude/scripts/test-bash-guard.sh`
    실측: `rg -n "task = 이번에 다루는 단일 C|완료 판단과 산출물|C는 단일 컨텍스트|다른 C|sandbox|permission-ready|worktree|워크트리|eval --harness|safe_command|planning -> document -> implementation -> test -> commit" docs/WIP/harness--hn_harness_after_ai_alignment.md`
- [x] Problem AC (P5): 컨텍스트 압축 기준이 상시 주입, skill lazy-load, specialist 위임, archive 후보로 분리된다.
- [x] Problem AC (P6): 검증 불변식이 모델 성능이나 오케스트레이션 변경으로 대체되지 않는 항목으로 명시된다.
- [x] Problem AC (P7): planning/document/implementation/test/commit 흐름에서 task와 C의 일대일 기본값, C의 단일 컨텍스트 역할, CPS의 결정권, 각 단계의 출력 계약이 드러난다.
- [x] Guardrail AC (P11/S11): worktree 금지 폐기와 관련된 active 문구 정리 범위가 한 문서에만 머물지 않고 AGENTS, CLAUDE, skill, guard, decision을 함께 탐색한다.
- [x] Solution AC (S5/S7): 컨텍스트 경량화가 단순 삭제가 아니라 skill/agent 이전과 CPS packet 전달 방식으로 이어진다.
- [x] Solution AC (S6/S9): eval --harness, CPS/AC 자동 검증, safe dispatcher 개선이 각각 실측 가능한 후속 구현 단위로 나뉜다.
- [x] Verification AC (S11): 후속 구현 전 C/P/S/AC, sandbox 조건, worktree 정책 drift를 `rg`와 eval로 탐색하는 명령이 계획에 포함되어 있다.

## 결정 사항

- sandbox는 permission-ready 조건에서만 완료 증거로 쓰도록 `AGENTS.md`와
  `CLAUDE.md`에 반영했다.
- worktree blanket ban을 폐기하고, 소유권·정리 책임·변경 보존 계약 기반
  정책으로 `AGENTS.md`, `CLAUDE.md`, `harness-upgrade`, `bash-guard`를 갱신했다.
- `docs/WIP/decisions--hn_worktree_policy.md`를 추가해 기존
  `hn_git_subtree_policy.md`의 worktree 차단 판단을 supersede했다.
- C/task 일대일 계약과 완료 기준·산출물 기반 분리 예외를 CPS SSOT와
  implementation mirror에 반영했다.
- 컨텍스트 압축 inventory를 상시 주입, skill lazy-load, specialist 위임,
  script 결정화, archive/history로 분류했다.
- `safe_command.py eval-harness`를 추가하고, `eval_harness.py`에
  policy/dispatcher drift 관측을 추가했다.

## 실측

- `python3 -m py_compile .claude/scripts/eval_harness.py .claude/scripts/safe_command.py .claude/scripts/pre_commit_check.py` 통과.
- `python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q -k "policy_drift or dispatcher_drift"` → 4 passed.
- `python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q` → 49 passed.
- `python3 -m pytest .claude/scripts/tests/test_pre_commit.py -q` → 115 passed, 4 skipped.
- `bash .claude/scripts/test-bash-guard.sh` → 19 passed, 0 failed.
- `python .claude/scripts/safe_command.py eval-harness` → path contract 0건, policy drift 0건, dispatcher drift 0건.
- `python .claude/scripts/safe_command.py docs-validate docs/WIP/harness--hn_harness_after_ai_alignment.md docs/WIP/decisions--hn_worktree_policy.md` → 오류 0, 기존 archived 날짜 suffix 경고 2건.
- `python .claude/scripts/safe_command.py verify-relates` → 미연결 0건.
- `python .claude/scripts/safe_command.py precheck` → `pre_check_passed: true`.

## 메모

- 이 문서는 작업 계획이다. 실제 규칙 삭제와 스크립트 변경은 `/implementation`
  흐름에서 별도 WIP/AC로 실행한다.
- `docs/decisions/hn_git_subtree_policy.md`는 당시 판단으로는 유효했지만, 현재
  다중 프로젝트 운용 조건에서는 worktree blanket ban을 유지하는 근거로 쓰지 않는다.
- 과거 incident의 worktree 차단 기록은 역사로 유지한다. 현재 정책은 새 결정문이
  supersede한다.
