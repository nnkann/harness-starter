---
title: Downstream runtime adapter sprawl report
domain: harness
c: "Ai-prompter PRD 기반 harness-init 후 .claude/.codex/.agents/.harness가 동시에 노출되어 제품 구조와 하네스 adapter 구조가 혼동됨"
problem: P7
s: [S7]
tags: [downstream, init, adapters]
relates-to:
  - path: ../guides/project_kickoff.md
    rel: references
status: completed
created: 2026-06-04
updated: 2026-06-06
---

# Downstream runtime adapter sprawl report

## 관찰

`/Users/kann/projects/Ai-prompter`에 PRD 기반 `harness-init`을 진행한 뒤, downstream repo 루트에 다음 하네스 런타임 adapter 구조가 동시에 노출됐다.

- `.claude/agents`, `.claude/skills`, `.claude/scripts`, `.claude/rules`
- `.codex/agents`, `.codex/hooks.json`
- `.agents/skills`
- `.harness/hermes`, `.harness/project`
- `AGENTS.md`, `CLAUDE.md`

사용자 반응은 명확했다. "에이전트가 밖에 있고, Claude에 에이전트 있고, Codex에 에이전트 있는 구조가 제대로 된 것이냐"는 질문이 나왔다. 즉 downstream 사용자에게는 이것이 제품 아키텍처인지 하네스 런타임 adapter인지 구분되지 않는다.

## 영향

- 신규 downstream에서 제품 코드보다 하네스 메타 구조가 더 크게 보인다.
- PRD 기반 설계 검토 중 제품 구조와 하네스 운영 구조가 섞여 보인다.
- 2~3인 소규모 서버리스 프로젝트에는 `minimal` 프로파일도 과하게 느껴질 수 있다.
- `runtime_stack: hermes-codex-agy`가 기록되어도 어떤 디렉터리가 필수이고 어떤 디렉터리가 adapter mirror인지 사용자에게 드러나지 않는다.
- downstream 정리 시 `.claude`, `.codex`, `.agents` 중 무엇을 삭제해도 되는지 판단 근거가 부족하다.

## CPS Rationale

- C → P: downstream 사용자가 파일 소유권과 출력 계약을 구분하지 못했다. 이는 P7의 "시스템 관계·소유권·출력 계약 불투명"에 해당한다.
- P → S: S7은 owner, output contract, upstream/downstream 의미를 문서나 규칙에 드러내는 해결책이다. 이번 문제는 설치 결과물의 역할 설명과 선택권을 명시해야 줄어든다.
- S → AC: AC는 설치 프로파일/adapter 선택지 또는 설치 후 안내 문서가 downstream 사용자의 구조 혼동을 줄였는지 확인해야 한다.

## 제안

### A. 설치 시 runtime adapter 선택지 제공

`h-setup.sh`에 명시적 adapter 선택을 추가한다.

예시:

```bash
bash h-setup.sh --profile minimal --runtime codex .
bash h-setup.sh --profile minimal --runtime hermes-codex .
bash h-setup.sh --profile minimal --runtime claude .
```

`runtime_stack` 기본값을 계속 `hermes-codex-agy`로 둘 수는 있지만, downstream 신규 설치는 "내가 실제로 쓸 runtime"을 선택할 수 있어야 한다.

### B. adapter mirror 역할을 README/CLAUDE/AGENTS에 명시

설치 후 생성되는 루트 문서에 다음 구분을 명시한다.

- 제품 코드: `src/`, `docs/PRD.md`, `docs/guides/project_kickoff.md`, `docs/WIP/*`
- 하네스 adapter: `.claude/`, `.codex/`, `.agents/`, `.harness/`
- 삭제/비활성 기준: 사용하지 않는 runtime adapter는 upstream 정책에 따라 제거 또는 skip 설치 가능

### C. `minimal` 프로파일 재검토

현재 `minimal`은 기능 수는 줄였지만 runtime adapter 표면은 여전히 넓다. "기능 minimal"과 "runtime surface minimal"을 분리해야 한다.

후보:

- `minimal`: 단일 runtime만 설치
- `standard`: Hermes + Codex
- `full`: Hermes + Codex + Claude + Agy + tests

### D. downstream 임시 대응 가이드

upstream 수정 전 downstream에서는 삭제보다 문서상 분리부터 권장한다.

- `project_kickoff.md`에 "하네스 adapter 디렉터리는 제품 아키텍처가 아니다"를 명시한다.
- 실제 사용할 runtime을 정한 뒤 나머지 adapter 정리는 별도 WIP로 진행한다.
- 무작정 `.claude` 또는 `.agents`를 삭제하지 않는다. 현재 hooks/scripts/skills 연결이 어디에서 참조되는지 먼저 확인한다.

## 구현 계획

1. `h-setup.sh`의 프로파일 설명과 셋업 출력에 `minimal`은 기능 minimal이며 runtime adapter 표면은 별도라는 계약을 추가한다.
2. 다운스트림에 그대로 복사되는 `CLAUDE.md`/`AGENTS.md`에 runtime adapter 표면 표를 추가한다.
3. 신규 설치 회귀 테스트에서 `AGENTS.md`에 제품 구조와 adapter 구조의 구분, `minimal` 정의가 남는지 확인한다.

**Acceptance Criteria**:
- [x] Goal: 신규 downstream 사용자가 제품 구조와 하네스 runtime adapter 구조를 구분할 수 있다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
    실측: 신규 설치 대상의 `AGENTS.md`에 `Runtime Adapter 표면` 표와 "제품 아키텍처가 아니라 agent runtime adapter" 문구가 남는 것을 `test_h_setup_runtime_metadata.py`에서 확인했다.
- [x] Problem AC (P7): `h-setup.sh` 또는 설치 문서에 runtime adapter 선택/역할 설명이 추가된다. ✅
  검증:
    review: self
    tests: `bash -n h-setup.sh`
    실측: `h-setup.sh` 사용 설명과 셋업 출력이 `.claude/.agents/.codex/CLAUDE.md/AGENTS.md`를 하네스 runtime 표면으로 설명한다.
- [x] Solution AC (S7): `minimal` 프로파일이 기능 minimal인지 runtime surface minimal인지 명확히 정의된다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
    실측: `h-setup.sh` 주석과 다운스트림 `AGENTS.md` 모두 `minimal`을 기능 minimal로 정의한다.
- [x] Verification AC (S7): 신규 downstream 설치 예시에서 루트 디렉터리 설명이 README/CLAUDE/AGENTS 중 하나에 남는다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
    실측: 테스트가 신규 설치 후 `AGENTS.md`의 adapter 역할 표를 직접 assert한다.
- [x] Verification AC (S7): `python3 .claude/scripts/docs_ops.py validate`가 통과한다. ✅
  검증:
    review: self
    tests: `python3 .claude/scripts/docs_ops.py validate`
    실측: validate 오류 0, 기존 archived 파일명 경고 2건.

## 메모

이 보고서는 downstream `Ai-prompter`에서 발생한 사용자 혼동을 upstream 개선 후보로 박제한다. 이번 wave에서는 runtime 선택 CLI까지 확장하지 않고, 설치 산출물에 adapter 역할과 `minimal`의 의미를 명시하는 범위로 닫았다.
