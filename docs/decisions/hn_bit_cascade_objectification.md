---
title: BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소
domain: harness
problem: P1
solution-ref:
  - S1 — "규칙 + 자동 차단 + 우회 장치"
tags: [bit, cascade, cps, ac, objectification, self-dependency, p9-candidate]
relates-to:
  - path: decisions/hn_p8_starter_self_application.md
    rel: extends
  - path: decisions/hn_gemini_delegation_pipeline.md
    rel: references
  - path: decisions/hn_cps_entry_signal_layering.md
    rel: caused-by
status: completed
created: 2026-05-11
updated: 2026-05-11
---

# BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소

## 배경

`gemini_delegation_pipeline` 결정이 의미 신호 기반 자동 트리거를 도입하려는데,
그 신호들 중 일부가 **Claude 자가 발화에 의존** → 자동 트리거 자체가
P1·P8 패턴 재현 위험. 닭-계란 문제 해소가 선제 필요했으나, 본 결정에서
**닭-계란 재구성**(아래 "결정" 섹션)으로 평행 진행 가능성 확보.

### 닭-계란 재구성 (Gemini 외부 시각 반영)

이전 가정: "BIT 객관화 완료 후 Gemini 파이프라인 진행" → **지나치게 보수적**.
모든 신호 객관화를 기다리면 `gemini_delegation_pipeline` 전체 좌초 위험.

새 의존 그래프:

```
[Phase 1] 객관 신호 기반 Gemini 트리거 (즉시 가능)
   - CPS Solution 메커니즘 변경 staged (diff grep)
   - review verdict warn + deep (review·pre-check 결과)
   || 병렬 진행
[Phase 2] BIT/CPS cascade 객관화 (본 결정)
   ↓
[Phase 3] 의미 신호 기반 Gemini 트리거 (Phase 2 완료 후)
   - CPS Problem NEW 플래그
   - BIT Q3 + NEW
```

`gemini_delegation_pipeline`은 Phase 1로 즉시 진행 가능. 본 결정 완료를 기다리지 않음.

### 4개 사건의 cascade 신뢰성 현황

| 사건 | cascade 신뢰성 | Phase |
|------|--------------|-------|
| CPS Problem NEW 플래그 | ⚠️ Claude가 NEW 플래그를 박았는지 자체가 자가 발화 | Phase 3 (본 결정 후) |
| CPS Solution 메커니즘 변경 staged | ✅ diff grep으로 객관 detect | Phase 1 (즉시) |
| BIT Q3 + NEW | ❌ BIT 판단 블록·NEW 플래그 둘 다 자가 발화 의존 | Phase 3 (본 결정 후) |
| review verdict warn + deep | ✅ review 응답·pre-check 결과 객관 detect | Phase 1 (즉시) |

### BIT 근본 문제

BIT (Bug Interrupt Triage) 규칙은 작업 도중 스코프 외 버그 발견 시
Q1/Q2/Q3 판단·NEW 플래그 표기·CPS Problem 등록을 강제한다. 그러나:

1. **BIT 판단 블록 작성 자체가 자가 발화** — `debug-guard.sh`는 "안내만"
   출력. 강제 검증 없음. Claude가 무시해도 후속 차단 없음
2. **NEW 플래그 박기도 자가 발화** — implementation Step 0가 P# 매칭 시
   본문에 NEW 마커를 박을 책임 부담. 누락해도 후속 검증 없음
3. **BIT Q3 → CPS P# 등록 cascade 단절** — Q3 hit으로 NEW 플래그가
   박혔어도 CPS Problems 섹션 실제 등록은 다음 implementation Step 0
   타이밍에 의존. cascade가 즉시 닫히지 않음

이 세 단계가 모두 자가 발화 의존 → 누구나 한 곳에서 발화 누락하면 cascade
전체가 끊김. **P1·P8이 BIT 영역에서 구체화된 형태**.

### 사용자가 결정 못 한 진짜 이유 (Gemini 외부 시각)

> "내가 Claude에게 '객관적으로 행동해'라고 말하는 것 자체가 주관적인 명령"

4개 후보 모두 "Claude가 자기 자신을 감시·기록·해석"하는 구조 → 인식
주체와 행위 주체가 분리되지 않음. 후보 3은 자기 모순의 절정 — 룰 파일이
물리적으로 존재해도 해석·적용 주체가 Claude면 객관 신호 아님.

해소 원칙: **주관(발화)과 격리된 물리적 증거(Status/Diff/File)만 트리거로**.
이게 본 결정의 진짜 메타 원칙이고, P9 후보 근거.

## P9 신규 등록 후보 — "정보 오염의 관성 (Information Inertia)"

P1/P8 보강이 아닌 **신규 메타 Problem** 가치. CPS에 다음 3개 항목을
세트로 등록 (Context 보강 + P9 정의 + S9 정의).

### Context 보강 (project_kickoff.md "## Context" 섹션 추가 문단)

```markdown
**LLM 신호의 본질적 한계**: Claude의 자가 발화·자가 보고·자가 해석은
컨텍스트 편향에 노출됨. 한 번 '정상'으로 판단된 문맥에서 후속 모순이
그 '정상'에 맞춰 왜곡 → 자가 발화에 의존하는 신호는 시스템 자동화
트리거로 부적합. 자동 트리거는 주관(발화)과 격리된 물리적 증거
(Status / Diff / File / Frontmatter 매칭)만 사용해야 안정 cascade가
가능.
```

### P9. 정보 오염의 관성 (Information Inertia)

**증상**: LLM이 한 번 '정상'이라고 판단한 문맥 속에서 이후 발생하는
모순을 그 '정상'에 맞춰 왜곡. 자가 발화 신호(BIT 판단·NEW 플래그·CPS
P# 매칭 표기)가 컨텍스트 편향으로 오염되어 자동 트리거의 신뢰성을
파괴.

**영향**:
- 자동 트리거가 자가 발화 신호에 의존 시 cascade 단절 누락
- BIT Q3 → NEW 플래그 → CPS P# 등록 흐름의 어느 한 곳 누락이
  후속 자동화 전체를 무력화
- P1/P8이 개별 행위의 실수라면 P9는 시스템 구조의 결함

**진입 조건** (객관 신호 — `cps_entry_signal_layering` Layer 1 원칙 적용):
- WIP frontmatter `problem` 필드와 CPS Problems 목록 매칭 실패
- `## 발견된 스코프 외 이슈` 섹션에 P# 매칭 항목이 CPS Problems에 미등록
- BIT trigger 신호 발생(debug-guard.sh 키워드 hit) 후 응답에 `[BIT 판단]`
  블록 부재
- 자동 트리거 hook·스크립트가 자가 발화 신호(Claude 응답 본문 해석)에
  의존하는 패턴

**승격 상태**: 본 결정으로 P9 신설. S9 정의(아래)는 owner 승인 후 등록.

### S9 (for P9). 주관 격리 + 다층 검증

**메커니즘** (진입 조건별 해소 경로 — 도구 frontmatter `serves: S9,
trigger: ...`로 Layer 2 cascade):

- **메타 원칙 박제** — `rules/cps-ac-cascade.md` 신설. 자동 트리거는 객관
  detect 가능 신호만 사용. 자가 발화 의존 트리거 금지 명시. (선언 layer)
- **Workflow 강제** — implementation·write-doc 스킬이 진입 조건 1·3을
  스킬 단계에서 강제. BIT trigger 검사·NEW 플래그·CPS Problems 등록을
  '판단'에서 'UI/UX'로 치환. (절차 layer)
- **Gatekeeper 검증** — pre_commit_check.py가 진입 조건 1·2를 결과 무결성
  검증. frontmatter ↔ CPS 매칭 객관 detect. 누락 시 [차단]·[경고]. (상태 layer)

**해결 기준**:
- BIT Q3 hit → `[BIT 판단]` 블록 작성률 100% (객관 detect: 응답 본문 grep)
- NEW 플래그 표기 → CPS Problems 등록까지 cascade 닫힘률 100% (객관 detect:
  pre-check frontmatter ↔ CPS 매칭)
- WIP frontmatter `problem` 필드 ↔ CPS Problems 매칭률 100%
- 매칭 누락 시 commit 차단 또는 명시 경고

**제약**:
- 인식 실패 (Perception Gap) 영역은 P1 본체 — Claude가 버그를 정상
  동작으로 추측하면 어떤 메커니즘도 트리거 안 됨
- Workflow 강제는 Expert Bypass 가능 (스킬 우회 시 무력화) → Gatekeeper
  검증이 결과 무결성으로 보강
- Physical Lock (도구 레벨 차단) 후보 — 마찰 큼. Phase 2·3 운영 데이터
  확보 후 재검토

**진입 도구**: Layer 2 도구 frontmatter `serves: S9, trigger: ...` 자동
수집. HARNESS_MAP 역생성이 P9 → 도구 매핑 자동 박제
(`cps_entry_signal_layering` 결정 4단계).

### CPS 등록 권한

- Context 보강·P9 추가: **Claude 단독 권한** (docs.md "CPS 변경 권한" —
  Problem 추가는 BIT Q3 또는 implementation Step 0 판단으로 가능)
- S9 정의: **프로젝트 owner 승인 필요** (cascade 영향 큼)

본 결정 합의 시 P9 + Context 보강은 즉시 등록. S9 정의는 본 결정
구현 단계에서 owner 승인 후 등록.

## 선택지 (5개 — Gemini 의견 반영 후보 5 추가)

### 후보 1 — Stop/SubagentStop hook으로 BIT 블록 검증 (발화 단계 교정)

Claude 응답 종료 직전 hook이 응답 본문 검증:
- 사용자 발화·tool 결과에 BIT trigger 키워드 hit 있었는데
- Claude 응답에 BIT 판단 블록 없으면 → 차단·재진입 또는 [경고]

**P1/P8 해소 본질**: 의도적 누락은 막음. 인식 실패(버그를 버그로 인지 못함)는 못 막음.
trigger 키워드 외형 metric 의존 → P8 변종 (Claude가 단어 피해 발화하면 무력화).

장점: 자가 발화 → 강제 검증, 기존 debug-guard.sh 패턴 확장
단점: 외형 metric 한계, 오탐 가능

### 후보 2 — pre_commit_check.py가 BIT cascade 검증 (상태 단계 교정) ★ 권고

commit 직전 staged WIP 본문 검증:
- `## 발견된 스코프 외 이슈` 섹션 항목의 P# 매칭이 CPS Problems와 일치
- NEW 플래그 박혔는데 CPS Problems 실제 등록 없으면 → [차단]
- WIP frontmatter `problem` 필드 vs CPS Problems 매칭 검증

**P1/P8 해소 본질**: 발화는 안 믿고 글(WIP·코드)만 믿겠다는 선언.
cascade '끝단'을 잠그는 효과 가장 강력. 작업 도중 이탈은 못 막지만
결과 무결성 강제.

장점: 객관 detect (diff grep + frontmatter), 기존 인프라 재사용
단점: 작업 도중 cascade 단절 즉시 감지 못 함

### 후보 3 — 메타 원칙 rules 박제 (규범 단계 정의, 선언 한정)

별 룰 파일 신설: `.claude/rules/cps-ac-cascade.md`
- 메타 원칙: "자동 트리거는 객관 detect 가능 신호만 사용"
- BIT Q3·NEW 플래그·CPS P# 등록의 cascade 의무

**P1/P8 해소 본질**: 해소 메커니즘이 아니라 설계 가이드라인. 룰 자체의
해석·적용 주체가 Claude면 자기 모순(자가 발화 의존 회귀).

→ **단독 채택 비추**. 후보 2·4·5의 정당화 선언으로만 박제.

### 후보 4 — implementation·BIT 강제 통합 (절차 단계 강제) ★ 권고

implementation 스킬 Step 0가 BIT Q3 자동 적용:
- 사용자 발화 직후 BIT trigger 검사
- hit 시 BIT 판단 블록 강제 작성 (스킬 단계 강제)
- NEW 플래그·CPS Problems 등록을 같은 Step에서 처리

**P1/P8 해소 본질**: '판단'을 'UI/UX'로 치환. 자율성 박탈 → 실수 방지.

장점: cascade 즉시 닫힘 (Q3 → NEW → CPS 한 흐름)
단점: **Expert Bypass** — 스킬 우회 시 무력화. 급한 Claude가 Edit/Write
직접 호출 → P8 변종 재현

### 후보 5 — Physical Lock (툴 레벨 물리적 제약) — Gemini 제안

BIT 상황 감지 시 `.claude/BIT_LOCK` 파일 생성:
- 락 존재 시 `Edit`·`Write` 등 수정 툴 차단
- 해제 유일 경로: implementation 스킬 통해 BIT 블록 작성·WIP 기록하여
  물리적 무결성 증명

**P1/P8 해소 본질**: Claude 의지·발화와 무관한 툴 레벨 제어. 인식
주체와 행위 주체 분리. P9 "주관과 격리된 물리적 증거" 원칙 정합.

장점: 자가 발화·스킬 우회 모두 차단. 가장 강력
단점:
- 일상 작업 흐름 마찰 큼 (모든 수정 차단)
- BIT 상황 감지 자체의 외형 metric 한계 (락 트리거가 키워드 의존이면 후보 1과 동일 문제)
- 락 해제 메커니즘 설계 부담

## 결정

**채택 조합**: **후보 4 (Workflow) + 후보 2 (Gatekeeper) + 후보 3 (선언)**

근거:
- 후보 4: '정답으로 가는 쉬운 길' 제공 (생산성)
- 후보 2: '오답인 상태로는 문을 나갈 수 없게' 차단 (무결성)
- 후보 3: 메타 원칙 선언으로 미래 자동 트리거 설계 시 적용 가능

**후보 5 (Physical Lock) — 보류**:
- 가장 강력하지만 마찰 큼
- BIT 감지 자체의 외형 metric 한계가 후보 1과 같음
- Phase 2·3 운영 데이터 확보 후 재검토. 일상 cascade 누락이 후보 4+2
  조합으로 0건 보장되지 않으면 그때 도입

**후보 1 (Stop hook) — 폐기**:
- 외형 metric 한계 (debug-guard 문제 재현)
- 후보 2가 결과 검증으로 cascade '끝단' 닫음 → 발화 단계 검증 중복

### 구현 순서

1. **후보 3 (선언) 먼저** — `.claude/rules/cps-ac-cascade.md` 신설
   - 메타 원칙: 객관 detect 가능 신호만 자동 트리거에 사용
   - 자가 발화 의존 트리거 금지 명시
   - 후보 2·4 구현의 정당화 근거

2. **후보 2 (Gatekeeper)** — `pre_commit_check.py` 확장
   - WIP `## 발견된 스코프 외 이슈` 섹션 항목 P# 매칭 검증
   - frontmatter `problem` ↔ CPS Problems 매칭 검증
   - 매칭 누락 시 [차단] 또는 [경고]

3. **후보 4 (Workflow)** — `implementation/SKILL.md` Step 0 확장
   - BIT trigger 검사 자동화 (debug-guard 키워드 SSOT 재사용)
   - hit 시 BIT 판단 블록 강제 작성 절차
   - NEW 플래그·CPS Problems 등록 흐름 통합

4. **P9 CPS 등록** — `docs/guides/project_kickoff.md` Problems 섹션
   - P9. 정보 오염의 관성 (Information Inertia)
   - Solution 정의는 owner 승인 필요 (별 트랙)

## 검증 기준

본 결정 구현 후 다음이 객관 검증 가능해야 함:

- BIT Q3 hit → `[BIT 판단]` 블록 작성률 100% (후보 4 강제)
- NEW 플래그 표기 → CPS Problems 등록까지 cascade 닫힘률 100% (후보 4 강제)
- WIP frontmatter `problem` 필드 ↔ CPS Problems 매칭률 100% (후보 2 검증)
- 매칭 누락 시 commit 차단 또는 명시 경고 (후보 2 차단)
- pytest 회귀 가드 신설 (cascade 검증 로직 자체)

## 관련 결정

- `decisions/hn_p8_starter_self_application.md` (extends) — commit 흐름·
  세션 시작 강제 트리거 보강. 본 결정은 그 위에 "트리거 신호 자체의
  객관성" 메타 층 추가
- `WIP/decisions--hn_gemini_delegation_pipeline.md` (references) — 닭-계란
  재구성으로 동결 해제. Phase 1 객관 신호 트리거는 본 결정과 평행 진행

## 사각지대

- BIT trigger 키워드 정의 자체의 외형 metric 한계 (`debug-guard.sh`
  키워드 SSOT가 같은 문제 잠재) — 후보 5 도입 시 동일 한계
- WIP 없는 흐름의 BIT cascade — 일상 프롬프트에서 BIT Q3 hit 시 어디에
  기록할지 (WIP 없으면 cascade 진입점 부재) → 후보 4 Step 0가 WIP 강제
  생성하는 방향 검토 필요
- **인식 실패 (Perception Gap)** — Claude가 버그를 보고도 "정상 동작"이라
  추측(P1) 시 어떤 후보도 트리거 안 됨. 본 결정 외 별 영역 (P1 본체)
- 다층 검증의 false positive 누적 (후보 4 + 후보 2 동시 경고 시 사용자
  체감 마찰) → 후보 2는 차단, 후보 4는 절차 강제로 역할 분리 필수
- **키워드 오염** — Claude가 BIT trigger 키워드를 회피하여 발화 → 후보 4
  자동 검사 무력화. 후보 2 결과 검증으로 완전 차단

## 변경 이력

- 2026-05-11 — 최초 작성. 4개 선택지 미결 상태
- 2026-05-11 — Gemini 외부 시각 반영. 후보 5 (Physical Lock) 추가, P9
  "정보 오염의 관성" 신규 후보 명시, 닭-계란 재구성으로 Phase 분리,
  결정 진전 (후보 4+2+3 조합 채택, 후보 5 보류, 후보 1 폐기)

## 메모

본 결정 합의 후 구현 순서:
1. `cps-ac-cascade.md` rule 신설 (선언)
2. `pre_commit_check.py` 확장 (Gatekeeper)
3. `implementation/SKILL.md` Step 0 + `write-doc/SKILL.md` Step 3 확장
   (Workflow) — write-doc도 frontmatter `problem` 필드 작성 시점이라
   후보 4 진입점. 두 스킬 모두 확장 대상
4. P9 CPS 등록 (Context 보강 + P9 정의 즉시, S9 정의 owner 승인 후)

### Workflow 진입점 흐름 (시각화)

```
[사용자 발화]
   ↓
implementation Step 0 (작업 발화 직후 BIT trigger 검사)
   또는
write-doc Step 3 (WIP frontmatter `problem` 필드 작성 시점)
   ↓
[후보 4 — Workflow 강제]
   - frontmatter `problem` ↔ CPS Problems 매칭 검증
   - 매칭 실패 → NEW 플래그 강제 → BIT 판단 블록 강제
   - Q3 hit + NEW → CPS Problems 즉시 등록
   - 본문 `## 발견된 스코프 외 이슈` 섹션 강제
   ↓
[작업 진행]
   ↓
[후보 2 — Gatekeeper 검증 (pre-commit)]
   - 결과 무결성 검증
   - cascade 단절 시 [차단]·[경고]
   ↓
[commit 통과] → cascade 객관화된 신호 확보
   ↓
[Phase 3 — Gemini 의미 신호 트리거 가능]
```

### 다음 단계

본 결정 합의 후:
1. `gemini_delegation_pipeline` WIP 동결 해제 — Phase 1 객관 신호
   트리거 (Solution 변경·review verdict warn+deep)는 본 결정과 평행
   진행 가능
2. 본 결정 구현 — 위 구현 순서 4단계
3. Phase 3 진입 — `gemini_delegation_pipeline` Phase 3 (BIT Q3·NEW
   플래그 의미 신호 트리거) 본 결정 완료 후 활성화

`gemini_delegation_pipeline` WIP는 Phase 1 객관 신호 트리거로 평행 진행 가능.
