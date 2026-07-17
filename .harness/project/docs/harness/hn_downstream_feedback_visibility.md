---
title: downstream feedback visibility + bootstrap gate 보강
domain: harness
problem: P3
s: [S3, S7, S8, S9]
tags: [downstream, cron, feedback, bootstrap]
status: completed
created: 2026-06-02
updated: 2026-06-02
---

# downstream feedback visibility + bootstrap gate 보강

## CPS Rationale

- C -> P: cron은 돌지만 수용 후보가 처리됐는지 보이지 않고, 신규 프로젝트가 `.claude/HARNESS.json` 없이 registry에 들어가도 bootstrap 안내가 약해 P3/P7이 발생한다.
- P -> S: S3/S7은 downstream 적용 누락과 출력 의미를 드러내고, S8/S9는 cron report를 재확인 가능한 상태 신호로 남긴다.
- S -> AC: 리포트가 후보 age와 bootstrap owner-action을 출력하고, 신규 설치 문서가 HARNESS 정의 파일 우선 흐름을 명시하면 silent fail을 줄인다.

## 구현 계획

1. Hermes learning-check 출력에 후보 상태(`new/existing/aging`)와 bootstrap 누락 owner-action을 추가한다.
2. 신규 프로젝트 문서·placeholder에 `.claude/HARNESS.json` 생성 후 domain 분류를 하도록 안내한다.
3. h-setup 회귀 테스트로 신규 설치 시 HARNESS.json과 초기화 placeholder가 함께 생기는지 확인한다.

## Acceptance Criteria

- [x] Goal: downstream guardian report가 수용 후보의 반복 상태와 bootstrap 누락을 사용자가 판단 가능한 owner-action으로 보여준다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
    실측: `python3 /Users/kann/.hermes/scripts/harness_downstream_learning_check.py --force-report` 출력에 `ai-prompter` bootstrap 안내와 candidate 상태가 표시된다.
- [x] Problem AC (P3): `.claude/HARNESS.json` 없는 harness-downstream registry 항목이 단순 reject가 아니라 설치/초기화 누락 owner-action으로 분류된다.
- [x] Solution AC (S3/S7): 신규 프로젝트 흐름이 `h-setup.sh`로 HARNESS 정의 파일 생성 후 `/harness-init` 도메인 분류로 이어진다고 README와 placeholder에 명시된다.
- [x] Behavior AC (S8/S9): 반복 Feedback Report가 이전과 같은 신호인지, aging 후보인지 출력되어 오래된 memory-signal이 사실처럼 방치되지 않는다.

## 결정 사항

- Hermes local guardian `harness_downstream_learning_check.py`가 `.claude/HARNESS.json` 없는 registry 항목을 `reject`가 아니라 `owner-action`으로 분류한다. 이유: Hermes config가 `type: harness-downstream`이라고 선언한 이상, 누락은 "비하네스"가 아니라 bootstrap 미완료 상태다.
- 반복 신호에는 local state 기반 `[new]`, `[existing Nd]`, `[aging Nd]` 라벨을 붙인다. 이유: 조용한 cron은 유지하되, 강제/주간 리포트에서 후보가 방치 중인지 판단 가능해야 한다.
- 신규 설치 HARNESS.json에 `is_starter=false`를 추가한다. 이유: downstream-readiness가 기대하는 하네스 정의 파일의 핵심 필드가 설치 직후부터 존재해야 한다.
- README·MIGRATIONS·h-setup placeholder에 HARNESS 정의 파일 생성 후 `/harness-init` 도메인 목록·약어·등급 분류로 이어지는 흐름을 명시한다.
- CPS 갱신: 없음. 기존 P3/P7/P8/P9 및 S3/S7/S8/S9 계약 안에서 처리했다.

## 메모

- 사용자 관찰: `ai-prompter`가 harness-downstream registry에 있지만 `.claude/HARNESS.json`이 없다. 신규 프로젝트는 하네스 정의 파일이 먼저 있어야 하며 그 다음 도메인 분류로 유도해야 한다.
- 검증: `python3 -m py_compile /Users/kann/.hermes/scripts/harness_downstream_learning_check.py` 통과.
- 검증: `bash -n h-setup.sh` 통과.
- 검증: `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q` → 2 passed.
- 실측: `python3 /Users/kann/.hermes/scripts/harness_downstream_learning_check.py --force-report`에서 `ai-prompter`가 `[new] bootstrap missing: .claude/HARNESS.json 없음 — harness-starter의 h-setup.sh를 먼저 실행한 뒤 /harness-init으로 도메인 분류 필요` owner-action으로 표시됨.
