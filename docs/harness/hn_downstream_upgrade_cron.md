---
title: downstream harness upgrade cron 보강
domain: harness
c: "하네스 변경 유무를 크론이 확인하고 하위 다운스트림에 적용 후보를 자동으로 드러내야 한다."
problem: P3
s: [S3, S7, S8, S9]
tags: [downstream, cron, upgrade, hermes]
status: completed
created: 2026-06-03
updated: 2026-06-06
---

# downstream harness upgrade cron 보강

## CPS Rationale

- C -> P: downstream이 upstream 변경을 놓치면 하네스 개선이 적용되지 않은 채 조용히 지나가 P3가 발생한다.
- P -> S: S3는 버전/업그레이드 누락을 드러내고, S7/S8/S9는 cron report의 의미와 적용 경계를 분리한다.
- S -> AC: daily cron이 upstream 변경 가능성을 출력하고 executor 적용 경계를 문서화하면 silent fail을 줄인다.

## 구현 계획

1. Hermes daily script가 각 downstream의 current version/ref와 upstream version/ref를 비교해 `harness-upgrade` 신호를 낸다.
2. dirty tree, remote 누락, ref 최신 상태를 owner-action/upgrade-ready/none으로 분류한다.
3. 하네스 문서와 Hermes guardian skill에 daily 감지와 executor 적용 경계를 맞춘다.

**Acceptance Criteria**:
- [x] Goal: downstream guardian가 하네스 upstream 변경 유무와 적용 가능 상태를 보고한다.
  검증:
    review: self
    tests: `python3 -m py_compile /Users/kann/.hermes/scripts/harness_downstream_learning_check.py`; `python3 /Users/kann/.hermes/scripts/harness_downstream_learning_check.py --force-report`; `python3 .claude/scripts/safe_command.py docs-validate docs/WIP/harness--hn_downstream_upgrade_cron.md`
    실측: `--force-report`가 `### Harness upgrade` 표에 `current/upstream/action/reason`을 출력한다.
- [x] Problem AC (P3): downstream이 upstream보다 뒤처진 경우 `owner_actions` 또는 `signals`에 묻히지 않고 `harness_upgrade`로 분리된다.
- [x] Solution AC (S3/S7): version/ref 비교 기준과 적용 경계가 guardian skill 또는 하네스 문서에 명시된다.
- [x] Guardrail AC (S8/S9): 자동 루틴은 commit/push를 하지 않고, dirty tree·remote 누락·충돌 가능성은 owner-action으로 멈춘다.

## 결정 사항

- Hermes local guardian `/Users/kann/.hermes/scripts/harness_downstream_learning_check.py`에 `harness_upgrade` 필드를 추가했다. 각 downstream의 `.claude/HARNESS.json` `version`/`installed_from_ref`와 `harness-upstream/main`의 `.claude/HARNESS.json`/ref를 비교한다.
- daily cron은 read-only로 유지한다. 변경 적용은 `manual-upgrade-ready` 상태를 보고한 뒤 기존 executor 또는 사용자의 명시 요청으로만 진행하며, commit/push는 하지 않는다.
- 최신 상태이면 dirty tree여도 `harness_upgrade.action=none`으로 출력한다. 이유: 적용할 하네스 변경이 없는데 dirty 상태를 upgrade blocker처럼 보이면 P9 정보 오염이 된다.
- CPS 갱신: 없음. 기존 P3/P7/P8/P9 및 S3/S7/S8/S9 계약 안에서 처리했다.

## 메모

- 사용자 요청: "하네스의 변경 유무를 체크해서 하위 다운스트림에 자동 적용해주는 크론"을 원하며, 기존 하네스 헬스체크와 병합 가능.
- 검증: `python3 -m py_compile /Users/kann/.hermes/scripts/harness_downstream_learning_check.py` 통과.
- 검증: `python .claude/scripts/safe_command.py docs-validate docs/WIP/harness--hn_downstream_upgrade_cron.md` → 오류 0, 기존 archived 날짜 suffix 경고 2건.
- 실측: `python3 /Users/kann/.hermes/scripts/harness_downstream_learning_check.py --force-report`에서 `stagelink`와 `issen`이 `0.55.0 / b8a760f6` ↔ `0.55.0 / b8a760f6`, `action=none`, `reason=up-to-date`로 출력됨.
