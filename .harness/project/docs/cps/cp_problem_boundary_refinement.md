---
title: CPS P# 정련 — 신규 P# 0개 + C-P-S-AC 연결 계약 보강
domain: cps
c: "memory count 오해 + 닫히지 않는 AC + reminder/test-skip 재발 신호"
problem: [P6, P7, P8, P9, P11]
s: [S6, S7, S8, S9, S11]
tags: [cps-redesign, memory-system, reminder, false-completion, ac, regression]
status: completed
created: 2026-05-19
updated: 2026-05-19
---

## Context

다운스트림(StageLink) 2026-05-16~05-19 세션에서 두 결함이 함께 드러났다.

1. `session-start.py section_memory()`가 memory 본문이 아니라
   "메모리 N개 항목 로드됨" count 신호만 노출했고, LLM이 이를 실제 본문
   로드처럼 baseline으로 삼았다.
2. WIP AC에 "30일 후", "외부 파이프라인 가동 후", "별 wave"처럼 현재
   wave 안에서 닫을 수 없는 조건이 섞였다.

초기 WIP는 이 사건을 P12~P15 신설로 풀려고 했지만, owner 검토 결과 논점은
P# 증가가 아니라 기존 P#의 작동 경계와 C-P-S-AC 연결 약화였다. 특히 과거
P12·S12는 v0.51.4에서 폐기되어 P11에 흡수됐으므로 번호 재사용은 금지한다.

## 판단

신규 P#는 만들지 않는다. 이번 사건은 기존 P# 조합으로 설명 가능하며,
필요한 것은 P6/P7/P8/P9/P11의 정의 보강과 C-P-S-AC 연결 계약 명시다.

### 관련 C와 P# 매핑

| C | Primary P | 보조 P | 이유 |
|---|-----------|--------|------|
| memory count만 보고 실제 본문이 있는 것처럼 판단 | P9 | P7, P8 | count/label이 baseline을 오염. 출력 계약 불투명과 reminder 의존이 보조 원인 |
| memory stale·valid-until 부재 | P9 | P8 | 오래된 신호가 정정 없이 남고, 적시 환기가 실패 |
| 미룬 항목이 재호출되지 않음 | P8 | P6, P11 | reminder 의존 실패. AC/검증으로 미루면 P6, 별 WIP 쪼개기 회피면 P11 |
| AC에 30일 후·외부 가동 후·별 wave 조건 혼입 | P6 | P8 | 현재 wave 검증 책임을 미래/외부 조건으로 넘김 |
| 테스트 미실행 또는 무관한 테스트 통과를 완료 증거로 사용 | P6 | P9 | 거짓 완료. PASS 라벨이 실제 작동 증거처럼 오염 |
| 같은 구조 문제를 sub-task로 쪼개 본 WIP completed 위장 | P11 | P6 | 동형 후보 미탐색과 specification gaming |

### 회귀 기록과 memory/reminder 연결

회귀 관련 기록은 이미 있다. 다만 세 곳에 흩어져 있어 C+P에 따른 S 선택으로
이어지는 연결고리가 약하다.

| 기록 | 현재 역할 | 약한 지점 |
|------|-----------|-----------|
| `.claude/rules/self-verify.md` "버그 수정 → 회귀 테스트 먼저" | 회귀 테스트의 실행 원칙 | 어떤 과거 회귀를 떠올려야 하는지는 알려주지 않음 |
| `.claude/rules/memory.md` `signal_*.md` lifecycle | 반복 패턴 reminder | count/stale/keywords 미사용 문제가 있으면 P9 오염 또는 P8 누락으로 변함 |
| `docs/decisions/hn_test_diet.md` | pytest marker 기반 회귀 라우팅 | 전체 pytest 재실행이 다시 기본값처럼 쓰이는 drift를 막는 환기가 약함 |
| `docs/decisions/hn_p8_starter_self_application.md` | incident 회상 실패와 signal 보강 사례 | "박제됨"과 "작업 시점에 자동 환기됨" 사이가 여전히 분리됨 |

따라서 회귀는 단일 P가 아니라 C에 따라 다른 S로 풀어야 한다.

- C가 "버그 수정"이면 P6/S6: 현재 wave에서 재현 또는 회귀 테스트를 먼저
  닫는다.
- C가 "예전에 같은 사고가 있었는데 떠올리지 못함"이면 P8/S8: memory나
  incident가 작업 시점에 환기되는지 본다.
- C가 "오래된 PASS·count·signal을 사실처럼 사용"이면 P9/S9: stale 여부와
  검증 상태를 분리하고, 회귀 테스트 또는 재오염 방지 실측을 AC에 둔다.
- C가 "비슷한 회귀가 여러 파일/테스트군에 잠복"이면 P11/S11: 한 테스트만
  고치지 말고 같은 구조 후보를 찾는다.

memory/reminder의 역할은 "회귀가 있었음"을 증거로 삼는 것이 아니라, 현재
C에서 다시 확인해야 할 과거 패턴을 떠올리게 하는 것이다. 따라서 회귀 신호는
다음 3단계를 통과해야 한다.

1. **환기**: signal·incident·audit 로그가 현재 C와 가까운 후보를 보여준다.
2. **재확인**: 현재 코드·문서·git log와 맞는지 확인해 stale 여부를 가른다.
3. **검증 선택**: 맞는 경우에만 AC의 `tests` 또는 `실측` 범위에 반영한다.

이 3단계 중 1단계만 있고 2·3단계가 없으면 P9 오염이다. 반대로 과거 회귀가
문서에 있는데 1단계에서 전혀 떠오르지 않으면 P8 누락이다. 같은 패턴이 여러
파일·훅·테스트군에 걸쳐 있으면 P11로 보고 후보 위치를 같이 찾는다.

### P# 보강안

- **P6 — 검증 책임 우회와 거짓 완료**: 테스트를 실행하지 않거나, 무관한
  테스트 통과를 증거로 삼거나, 자동 검증 불가·미래 조건을 완료처럼 포장해
  현재 wave의 검증 책임을 회피한다. 테스트 환경·도구 존재·검증 대상 정합을
  확인하지 않아 PASS/WARN/SKIP 의미가 왜곡되는 경우도 포함한다.
- **P7 — 시스템 관계·소유권·출력 계약 불투명**: 문서·규칙·스크립트·cluster·
  frontmatter 사이의 의존뿐 아니라 upstream/downstream 소유권, owner 승인권,
  hook/stdout/status 출력 의미 계약이 불투명해 변경 영향과 책임 경계가 흐려진다.
- **P8 — 자가 발화·memory·reminder 의존 실패**: 시스템이 강제하거나 노출해야
  할 위험 신호를 LLM의 기억, session-start 알림, stop-guard 환기, "나중에
  기억하겠지"에 맡겨 누락된다.
- **P9 — 정보 오염의 관성**: 잘못된 라벨·count·PASS·자가 선언·오래된 memory가
  정정되지 않고 후속 작업의 baseline으로 굳어진다.
- **P11 — 동형 패턴 잠복**: 같은 구조적 문제가 여러 위치/작업으로 쪼개져 한
  곳만 고치고 나머지가 남는다. 본 WIP completed를 sub-task 분리로 위장하는
  specification gaming도 포함한다.

## CPS Rationale

- C → P: 이번 사건의 날것 C는 memory count 오해, 닫히지 않는 AC, reminder
  실패, 테스트/완료 의미 오판이다. 모두 기존 P6/P7/P8/P9/P11 조합으로
  설명되며 새 P#가 필요하다는 증거는 없다.
- P → S: S6은 검증 책임과 완료 판정을 닫고, S7은 관계·소유권·출력 계약을
  드러내며, S8은 reminder 의존을 강제 트리거로 바꾸고, S9는 오염된 주관
  신호를 객관 검증으로 격리하며, S11은 동형 후보와 쪼개기 회피를 잡는다.
- S → AC: AC는 신규 P# 신설이 아니라 kickoff의 P# 정의 보강, C-P-S-AC 계약
  추가, P12~P15 신설안 제거, 그리고 실제 사례 매핑이 문서에 반영됐는지로
  검증한다.

**Acceptance Criteria**:
- [x] Goal: S6·S7·S8·S9·S11 — CPS P# 체계가 신규 P# 0개 원칙을 유지하면서
  memory/reminder/test-skip/false-completion/defer 사례를 기존 P6/P7/P8/P9/P11에
  정확히 매핑한다.
  검증:
    review: self
    tests: 없음
    실측: `python .claude/scripts/safe_command.py verify-relates` 통과. 본 WIP,
      `docs/guides/project_kickoff.md`, `.claude/rules/self-verify.md`,
      `.claude/rules/memory.md`가 P12~P15 신설 없이 위 사례를 설명한다.
- [x] kickoff Problems 표가 P6/P7/P8/P9/P11의 보강된 경계를 반영한다.
- [x] kickoff Solutions 표가 S6/S7/S8/S9/S11의 해결 기준을 보강된 P#와 정합하게 반영한다.
- [x] kickoff `## CPS 사용 흐름`에 C-P-S-AC 연결 계약이 추가된다.
- [x] `.claude/rules/docs.md`에 `c:` frontmatter 권장과 `## CPS Rationale` 형식이 추가된다.
- [x] `.claude/rules/self-verify.md`가 `tests: 없음`·자동 검증 불가·닫히지 않는 AC를 완료 증거로 포장하지 않도록 보강된다.
- [x] `.claude/rules/memory.md`가 memory/reminder 신호를 P8 기준으로 재정렬하고 stale/count 단독 출력 위험을 명시한다.
- [x] `.claude/rules/memory.md`가 회귀 신호의 3단계(환기→재확인→검증 선택)를 명시하고, stale signal을 테스트 범위의 단독 근거로 쓰지 않도록 한다.
- [x] `.claude/rules/self-verify.md`가 회귀 테스트 판단 시 memory/reminder를 보조 신호로만 사용하고, 현재 코드·문서 재확인 없이는 AC tests에 반영하지 않도록 한다.
- [x] kickoff S9와 self-verify가 P9 primary 작업의 기본값을 회귀 테스트 또는 재오염 방지 실측으로 둔다.
- [x] `.claude/rules/code-ssot.md`가 새 PR 성격은 새 WIP, 문서 구현 중 파생 수정은 같은 C·Goal·AC면 같은 wave, AC가 달라져 별도 실측이 필요하면 별도 wave 1개 허용 원칙을 담는다.
- [x] 본 WIP에서 P12~P15 신설·P9 archived·대형 구현 wave 계획을 제거하고,
  신규 P# 0개 + 기존 P# 보강 결정으로 대체한다.
- [x] P12 번호 재사용 금지 근거(v0.51.4 폐기·P11 흡수)가 본문에 남는다.

## 범위 정리

이번 wave 안에서 count 단독 출력, stale signal 의미, 닫히지 않는 AC, P9
회귀 가드 기본값, 새 PR/WIP 분리 원칙은 문서 계약으로 정리했다. 실제 pytest
효율과 marker 라우팅 재정렬은 본 CPS 정련 wave의 AC로 닫을 수 없으므로
별도 WIP `docs/WIP/hn_pytest_regression_routing.md`로 분리했다.

### wave 분리 원칙

새 PR 성격의 작업은 새 WIP를 만든다. 문서 구현 중 파생된 수정은 같은 C·Goal·AC
안에서 닫을 수 있으면 같은 wave로 처리한다. 다만 AC 자체가 달라져 별도 실측이
필요하거나, 합치면 본 wave의 완료 기준을 흐리는 경우에는 별도 wave를 1개까지
허용한다.

## 변경 이력

- 2026-05-19 정정: P12~P15 대량 신설안 폐기. 사용자 판단과 Gemini/Codex
  검토를 반영해 신규 P# 0개, 기존 P6/P7/P8/P9/P11 보강, C-P-S-AC 연결
  계약 추가 방향으로 재작성.
