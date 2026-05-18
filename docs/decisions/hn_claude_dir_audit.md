---
title: .claude/ 전수 점검 — 강제 최소화·사전 추상화 회피 원칙 자기 적용
domain: harness
problem: P11
s: [S11]
tags: [claude-dir-audit, pre-abstraction, dead-rule, memory-index]
status: completed
created: 2026-05-18
updated: 2026-05-18
---

# .claude/ 전수 점검 — 강제 최소화·사전 추상화 회피 원칙 자기 적용

## Goal

P12 wave에서 합의한 "강제 최소화 + 사전 추상화 회피" 원칙을 `.claude/`
하위에 자기 적용. 사용자 지적("쓸데없는 것들 눈에 띈다") 직격 영역
(memory·rules·skills·agents) 전수 점검 후 즉시 회수.

**Acceptance Criteria**:
- [x] Goal: S11 충족 — `.claude/memory/`·`.claude/rules/`·`.claude/skills/`·`.claude/agents/`의 잔재 4건을 3개 의견(analyst+codex+gemini) 합의 회수
  검증:
    tests: 없음
    실측: 회수 후 git status·grep으로 dead reference 0건, MEMORY.md 인덱스 ↔ 실제 파일 수 정합, skills serves: 12개 추가 확인
- [x] codebase-analyst + codex + gemini 3개 의견 종합 — 회수 후보 4건 합의, guard 스크립트 점검은 별 wave 분리 결정
- [x] signal_defense_success.md 통합·회수 ~~진행~~ → **유지 결정 (재검토)**. 본문 직접 확인 결과 의미가 stop_hook_audit.log와 직교 — bash-guard 차단 8건 기록(P4 방어 활성 신호) vs stop hook A·B·C hit 110건. 통합 시 의미 손실. 별 wave 후보: signal 스키마 정의 부재 (memory.md에 signal_* 포맷 명시 없음)
- [x] skills 12개 frontmatter `serves: S#` 보강 — docs.md "하네스 구성요소 메타데이터" SSOT 위반 해소. S# 매핑 정합 검증 (사용자 명시): 10개 ✅ + 2개 ⚠️ (advisor·harness-dev) 별 wave 후보
- [x] MEMORY.md 인덱스 6개 누락 등록 — signal_* 파일 인덱스 동기화 (signal_defense_success도 등록 — 유지 결정)
- [x] `.claude/rules/memory.md` "누적 감사 로그" 섹션 신설 + stop_hook_audit.log 명시 — gitignore 정합 박제 + memory.md SSOT 갱신

## P12 자가 점검 (사용자 명시 요청)

본 wave가 P12 영역 — "별 wave 분리"가 정당한가 자기 적용 검증:

| P12 3문항 | 본 wave 5번 (guard 점검) 분리 판정 |
|----------|----------------------------------|
| 분리 사유가 "본 wave 안 끝낼 수 없는 정당 사유"인가? | ✅ guard는 차단 코드 영역 — 코드 동작 변경, 본 wave "잔재 정리" 범위 밖 |
| 진짜 완료가 비싸서 외형만 충족하는가? | ❌ 본 wave 4건은 결정적 검증 가능 AC (dead reference 0건·serves 12개·인덱스 6개). 외형 우회 없음 |
| 분리한 sub-task를 "분리됨" 산문으로 차단 검사 우회하는가? | ❌ 별 wave는 신규 WIP `decisions--hn_guard_scripts_audit.md`로 명시. 본 WIP AC에는 4건 결정적 항목만 |

**자가 점검 결과**: 본 wave 분리 정당. P12 회상 다리(decision 박제) 적용
경로 정상 — 외부 의견 3개로 검증 + 본 wave AC에 산문 우회 없음.

추가 확인 — pre-check §3.7 게이트 자기 반응:
- 본 wave가 P# 신설 없음 (P11 기존 매핑) → 게이트 미발동이 정상
- 만약 본 wave가 P# 신설했다면 cp_{slug}.md 동반 staging 차단 작동
- 즉 게이트는 "신설 시"만 발동. 본 wave 영향 0건

## 결정 사항

3개 의견(codebase-analyst + codex + gemini) 합의로 본 wave 회수 4건
확정. 5번째 (guard 스크립트 점검)은 별 wave 분리 — 차단 행동 코드는
P12 3문항 정밀 점검 필요.

| 후보 | analyst | codex | gemini | 결정 |
|------|---------|-------|--------|------|
| signal_defense_success.md 운용 로그 drift | 통합 | **1순위** | 3순위 | **유지** (의미 직교 — 본문 확인 후 재검토) |
| skills 12개 serves: 누락 | 보강 | 2순위 | **1순위** | 본 wave |
| MEMORY.md 인덱스 6개 누락 | 등록 | 3순위 | 2순위 | 본 wave |
| stop_hook_audit.log memory.md 미등재 | 확인 | 추가 점검 | — | 본 wave |
| **guard 스크립트 4개 차단 규칙 점검** | — | — | **신규 1순위** | **별 wave** |

## 메모

### codebase-analyst 응답 원문 (요약 금지)

1순위 정비 대상은 memory/ signal_* 6개 MEMORY.md 인덱스 누락. session-start.py:208이 glob 직접 읽으므로 기능 살아있음 — 사람 탐색 경로만 깨짐.

추가 후보: signal_defense_success.md 운용 로그 변질 (날짜+이벤트 append 8건, stop_hook_audit.log와 의미 중복), skills 12개 serves: 누락 (implementation만 있음 — docs.md "하네스 구성요소 메타데이터" 의무 위반), stop_hook_audit.log memory.md 동적 snapshot 목록(session-*.txt 3개)에 명시 없음.

기존 패턴: memory.md에 signal_* 파일 스키마(signal·domain·strength·candidate_p) 정의 없음 — 암묵적 컨벤션. eval_harness.py:165-168이 signal_defense_success.md를 이름으로 직접 참조 (회수 시 스크립트 함께 수정).

사각지대: stop_hook_audit.log git 추적 여부 미확인. skills S# 매핑이 kickoff Solutions 표와 정합하는지 미확인. harness-adopt/SKILL.md 550줄 본문 미독.

### codex 응답 원문

1순위: signal_defense_success.md 회수/통합. 근거: signal이 로그로 drift, stop_hook_audit.log와 역할 중복. 행동: 로그는 audit로 이전, signal은 원칙만 남김/삭제.

2순위: skills serves: 갱신. 근거: 명시 규칙 위반. 행동: 12개 메타데이터 보강.

3순위: MEMORY.md 인덱스 갱신. 근거: 기능은 생존, 사람 경로만 깨짐.

추가 점검: git ls-files stop_hook_audit.log, skills 본문 강제 규칙, kickoff S 매핑. 잔재 정의: 단일 사례 rule화, 중복 SSOT, 차단성 문구.

### gemini 응답 원문

우선순위 및 행동:
1. Skills 메타데이터(serves:) 보강 — docs.md(SSOT) 위반 해소. 모든 skill에 명시하여 구성요소 가시성 확보.
2. MEMORY.md 인덱스 동기화 — 누락된 signal_* 6종 등록. 인간-에이전트 간 탐색 정합성 및 SSOT 관리 체계 복구.
3. 운용 로그 통합 — 로그로 변질된 signal_defense_success.md를 stop_hook_audit.log로 통합 후 삭제. 의미 중복 및 관리 비용 제거.

누락/의심 영역:
- 사각지대: kickoff 솔루션 매핑과 실제 구현 간의 Dead link, .claude/scripts에 방치된 노후 로직의 Skill 이관 여부 확인.
- 추가 의심: P12(강제 최소화) 관점에서 write-guard.sh 등에 하드코딩된 과도한 차단 규칙이 "청산해야 할 잔재" 1순위임.

### 사실 확인 (gitignore + guard 스크립트)

```
$ git ls-files .claude/memory/stop_hook_audit.log → (없음, gitignore 정상)
$ git check-ignore -v .claude/memory/stop_hook_audit.log → .gitignore:7 hit
$ ls .claude/scripts/*guard* → bash-guard.sh, post-compact-guard.py, stop-guard.py, write-guard.sh, test-bash-guard.sh
```

stop_hook_audit.log gitignore 정합. guard 스크립트 4개 + 1개 테스트 — gemini 신규 의심 영역 확인됨.

### 별 wave 후보 — guard 스크립트 차단 규칙 점검

gemini "P12 관점 1순위 청산 대상"으로 지목. 본 wave 분리 근거:
- guard 스크립트는 차단 행동 코드 (rule 박제와 다름)
- P12 3문항 (정답 1개·false positive·우회 비용) 정밀 점검 필요
- 본 wave는 "잔재 정리" 명시 — 코드 동작 변경은 별 wave 정합

신규 WIP: `decisions--hn_guard_scripts_audit.md` 별 wave 진입 시 신설.

### 기타 별 wave 후보 (사각지대)

- kickoff Solutions 표와 실제 구현 dead link 점검
- .claude/scripts/ 방치 노후 로직 Skill 이관 여부
- harness-adopt/SKILL.md 550줄 본문 사전 추상화 점검

### skills + agents serves: 다중 매핑 최종 (사용자 명시 요청)

사용자 지적: "정합이 S#이지만 여러개 매칭 가능. 그렇게 보완하라고 넣은건데 굳이 하나만 매칭해서 한계 만드네"
→ 단일 매핑 고집 폐기. 본질 정합 1~2개 다중 매핑 적극 적용 (S10 catch-all "혼용 시 본질 신호 희석" 경고는 유지 — 3개+ 묶음은 피함).

**최종 매핑 (skills 13개 + agents 9개)**:

| 영역 | 본질 매핑 | 의미 |
|------|----------|------|
| advisor (skill+agent) | S1, S8 | 추측 차단 + 강제 트리거 (의사결정 프레임 = 추측 차단 메커니즘) |
| codebase-analyst | S1, S6 | 추측 차단 + 검증 |
| commit | S6, S9 | 검증망 게이트 + 다층 검증 |
| coding-convention | S6 | rules 검증망 |
| cps-check | S9 | CPS 정합 |
| debug-specialist | S1 | 추측→관찰·재현 |
| doc-finder | S5, S7 | 빠른 조회 + wiki 그래프 인덱스 |
| eval | S6, S7 | 검증 + wiki 그래프 품질 점검 |
| harness-adopt | S3, S9 | 다운스트림 cascade + CPS 매핑 |
| harness-dev | S3, S6 | starter→다운스트림 cascade + 메타 일관성 |
| harness-init | S6, S9 | rules 초기화 + CPS 초기 박제 |
| harness-sync | S3 | 다운스트림 환경 동기화 |
| harness-upgrade | S3, S9 | 다운스트림 cascade + CPS 정합 검증 |
| implementation | S1, S6 | 기존 유지 |
| naming-convention | S6 | naming rule 검증망 |
| performance-analyst | S2 | review 인접 |
| researcher | S5 | 외부 자료 압축 |
| review | S2 | review 본체 |
| risk-analyst | S6 | 내부 검증 |
| threat-analyst | S3 | 보안 cascade (P# 부재로 한계 — 별 wave 후보) |
| write-doc | S7, S9 | wiki 그래프 + frontmatter 강제 |

**잔존 한계 (별 wave 후보 유지)**:
- threat-analyst S3 — starter CPS에 보안 P# 부재. 신설 시 P# 게이트(cp_{slug}.md 동반 staging) 트리거되는 큰 변경이라 별 wave
