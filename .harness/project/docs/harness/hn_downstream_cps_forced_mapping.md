---
title: Downstream CPS forced mapping report
domain: harness
c: "Ai-prompter downstream WIP 작성 중 기존 CPS에 없는 repo adapter boundary 문제를 P2/S2에 잘못 매핑하고, 사용자 지적 후 P4/S4를 추가함"
problem: [P7, P9]
s: [S7, S9]
tags: [downstream, cps, init]
relates-to:
  - path: ../guides/project_kickoff.md
    rel: references
  - path: harness/hn_downstream_adapter_sprawl.md
    rel: references
status: completed
created: 2026-06-04
updated: 2026-06-06
---

# Downstream CPS forced mapping report

## 관찰

`/Users/kann/projects/Ai-prompter`에서 downstream repo 구조 정리 WIP를 만들 때, 실제 문제는 "제품 구조와 하네스 runtime adapter 구조가 구분되지 않음"이었다. 당시 `docs/guides/project_kickoff.md`에는 이 문제에 대응하는 P/S가 없었다.

정상 절차는 다음이어야 했다.

1. 기존 P/S에 정확히 맞는지 확인한다.
2. 맞지 않으면 downstream CPS에 새 P/S를 추가한다.
3. WIP frontmatter와 본문 `C → P → S → AC`를 새 P/S에 맞춘다.
4. 그 사실을 upstream 학습 후보로 보고한다.

실제 처리에서는 처음에 `problem: P2`, `s: [S2]`로 잘못 매핑했다. P2/S2는 자체 크롤러/서버/스토리지 운영 부담과 Supabase/R2 저장 계약에 관한 항목이므로, runtime adapter boundary 문제와 직접 대응하지 않는다. 사용자가 "CPS missing이고 문서 규약도 못 지킨 문서"라고 지적한 뒤 downstream CPS에 P4/S4를 추가해 수정했다.

## 영향

- 하네스가 의도한 "신규 현상은 새 P/S로 학습" 루프가 우회됐다.
- `docs_ops.py validate`는 통과했지만, 의미상 CPS 매핑 오류는 잡지 못했다.
- downstream WIP가 칸반에 올라간 뒤에야 사용자가 의미 오류를 발견했다.
- "기존 번호에 끼워 맞추기"가 반복되면 downstream 실측이 upstream 학습 데이터로 축적되지 않는다.

## CPS Rationale

- C → P7: downstream 문서 작성자가 P/S 소유권과 출력 계약을 올바르게 드러내지 못했다. 이는 시스템 관계와 출력 계약이 불투명해지는 P7에 해당한다.
- C → P9: `validate` 통과와 frontmatter 존재를 품질 증거로 오인해, 의미상 잘못된 P/S 매핑이 오염된 상태로 남을 뻔했다. 이는 라벨/자가 선언을 단독 증거로 쓰는 P9에 해당한다.
- P → S7: 새 downstream 현상은 문서에 소유권과 계약을 드러내야 한다. "어떤 P/S가 이 현상을 책임지는가"가 문서 본문에 설명돼야 한다.
- P → S9: 문서 검증은 번호 존재뿐 아니라 C-P-S-AC 의미 연결을 사람이 확인해야 하며, 신규 현상은 기존 번호에 흡수할지 새 번호를 만들지 명시해야 한다.
- S → AC: AC는 downstream WIP 작성 시 기존 P/S 불일치 신호가 있으면 새 P/S 추가 또는 P10/owner-action 박제를 요구하고, validate 통과만으로 완료 선언하지 않도록 해야 한다.

## 제안

### A. harness-init/implementation 문서 작성 흐름에 신규 P/S 판단 gate 추가

WIP frontmatter 작성 전 다음 질문을 명시한다.

- 이 C는 기존 P/S 해결 기준과 직접 대응하는가?
- 대응하지 않으면 downstream CPS에 새 P/S를 추가했는가?
- 새 P/S 추가가 부담스러워 임시로 기존 P/S에 붙이고 있지는 않은가?

### B. validate 이후 의미 검토 체크를 task AC에 요구

`docs_ops.py validate`는 형식 검증이다. downstream WIP 생성 직후에는 다음 self-check가 별도로 필요하다.

- `C → P` 설명이 본문에 있는가?
- `P → S` 설명이 본문에 있는가?
- 각 AC가 `S#` 해결 기준을 실제로 증명하는가?

### C. upstream 학습 후보 자동 보고 기준

downstream에서 새 P/S가 추가되면, 이 사실을 upstream 학습 후보로 남길지 판단해야 한다. 특히 하네스 설치/adapter/문서 규약 자체에서 나온 P/S는 upstream 보고 대상으로 본다.

**Acceptance Criteria**:
- [x] Goal: downstream WIP 작성 중 기존 CPS에 없는 현상을 기존 P/S에 강제로 붙이는 패턴을 줄인다.
- [x] Contract: WIP 생성 흐름에 "기존 P/S 불일치 시 새 P/S 추가 또는 owner-action 박제" 기준이 명시된다.
- [x] Contract: `validate` 통과와 의미상 CPS 정합성을 구분하는 문구가 추가된다.
- [x] Verification: 관련 skill/rule 변경 시 `docs_ops.py validate`, `verify-relates`, `eval_harness.py`를 실행한다.
- [x] Verification: Ai-prompter 사례가 downstream learning 후보로 추적 가능하다.

## 메모

이 보고서는 `harness--hn_downstream_adapter_sprawl.md`의 후속 관찰이다. adapter sprawl 자체가 P7 문제였고, 그 문제를 downstream 문서로 옮기는 과정에서 CPS 신규 추가 절차를 한 번 더 어겼다.

2026-06-05 처리: `.claude/skills/implementation/SKILL.md`,
`.agents/skills/implementation/SKILL.md`, `.claude/rules/docs.md`에 CPS miss를
기존 번호에 강제 매핑하지 않는 gate와 `docs_ops.py validate`의 형식 검증
한계를 명시했다. Ai-prompter 사례는 본 WIP의 C/P/S/AC와 메모로 downstream
learning 후보 추적 근거를 보존한다.
