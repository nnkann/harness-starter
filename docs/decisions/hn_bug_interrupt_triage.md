---
title: BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계
domain: harness
problem: P1
solution-ref:
  - S1 — "같은 파일을 근거 없이 3회 이상 수정하는 패턴이 세션당 0건"
tags: [bug-triage, interrupt, ac, cps, rules, living-harness]
relates-to:
  - path: decisions/hn_promise_protection.md
    rel: extends
  - path: decisions/hn_rules_metadata.md
    rel: references
status: in-progress
created: 2026-05-05
updated: 2026-05-05
---

# BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계

## 배경

다운스트림 작업 중 Claude가 스코프 외 버그를 발견하는 케이스가 빈번하다.
현재는 판단 기준이 없어 두 가지 실패 모드가 반복된다:

1. **무시 후 추적 소실**: "현재 wave 완료 후 처리"로 미뤘다가 완료 처리 시
   버그가 기록 없이 사라짐 — anti-defer.md 위반 패턴의 변형
2. **무분별 scope creep**: 판단 기준 없이 현재 wave를 확장하거나 중단 →
   작업 흐름 파괴

두 극단의 원인은 같다: **"중단할 것인가, 기록하고 속행할 것인가"의 기준이
없다.**

### 핵심 실패 패턴 (관찰)

- 발견 → 구두 메모("나중에 처리") → 현재 wave 완료 처리 → 버그 소실
- 발견 → 즉시 처리 시도 → 현재 wave 확장 → coding.md Surgical 위반
- 발견 → 아주 나중에 다른 wave에서 증상으로 재발견 → 원인 추적 비용 증가

### 기존 규칙과의 갭

| 기존 규칙 | 커버 | 갭 |
|----------|------|----|
| anti-defer.md | 미루기 차단 | 스코프 외 버그 발견 **시점의 즉각 판단** 기준 없음 |
| no-speculation.md | 추측 수정 차단 | 발견한 버그의 **중요도 판단** 절차 없음 |
| self-verify.md | 완료 전 AC 검증 | 작업 **도중** 스코프 외 이슈 처리 없음 |
| security.md | 보안 게이트 | 일반 버그 판단 기준 없음 |

### 하네스 단방향 구조의 근본 문제

현재 하네스는 단방향이다: 작업 → WIP → commit → 문서화. 발견된 이슈가
다음 작업에 자동으로 피드백되지 않는다.

BIT는 이 구조를 **순환 루프**로 전환하는 첫 번째 연결 고리다:

```
작업 중 발견
    ↓
BIT 판단 (Q1/Q2/Q3)
    ↓ Q3 hit — CPS P# 즉시 매칭
WIP "## 발견된 스코프 외 이슈" 기록 (P# 포함)
    ↓ 세션 시작마다
session-start.sh 감지 → 사용자 알림
    ↓ 다음 implementation
Step 0에서 플래그된 이슈 자동 인식 → CPS 신규 P# 승격 또는 기존 P# 연결
    ↓ CPS 업데이트
solution-ref 재인용 → cluster 갱신
    ↓
다음 작업이 더 풍부한 유산 위에서 시작  ← 루프
```

**핵심**: Q3 기록 시점에 CPS P# 매칭을 즉시 수행한다. 개수를 기다리지
않는다. 이슈 1개가 새 P#이면 바로 플래그 — BIT의 중요도 판단이 이미
그 결론을 냈기 때문이다.

---

## 선택지

### 옵션 A: 기존 rules 확장 (anti-defer.md + self-verify.md)
- 장점: rules 파일 수 증가 없음, 중복 회피
- 단점: "발견 시점의 즉각 판단"이라는 타이밍이 기존 rules와 다름.
  anti-defer는 "이미 미루기로 결정된 후", self-verify는 "완료 직전" — 발견
  순간의 판단 절차를 담기 어려움

### 옵션 B: 수치 scoring 시스템 (DREAD/MoSCoW 변형)
- 장점: 정량화, 일관성
- 단점: AI 판단에서 수치 합산은 설명 불가. 임계값 설정 근거 없음.
  세션마다 다른 점수 → audit 불가

### 옵션 C: 결정 트리 신규 rules 파일 (채택)
- 장점: "발견 순간" 전용 판단 절차. AC+CPS를 판단 기준 SSOT로 명시.
  결정 트리는 수치 합산보다 AI 판단 일관성·설명 가능성이 높음(외부 연구
  다수 확인)
- 단점: 9번째 rules 파일 — context 부담 우려. advisor 지적.
  완화: 판단 기준을 독립 정의 않고 AC+CPS+security.md를 명시 참조

---

## 결정

**옵션 C 채택 — rules/bug-interrupt.md 신설 + implementation SKILL Step 연결**

판단 기준의 SSOT는 새로 만들지 않는다:
- Q1 기준 → `rules/security.md` "회복 불가능한 외부 영향" 정의
- Q2 기준 → **현재 wave의 AC** (Goal + 검증 묶음)
- Q3 기준 → **현재 wave의 CPS P#** (어느 Problem에 영향, 다운스트림 전파)

이로써 BIT는 독립 판단 기준을 갖지 않고, "AC+CPS를 인터럽트 시점에 적용하는
절차"가 된다.

---

## BIT 시스템 명세

### 3단계 결정 트리

스코프 외 버그를 발견한 즉시 실행:

```
Q1: 이 버그가 조용히 merged되면 최악의 경우
    데이터 손상·보안·인증·시크릿 노출이 발생하는가?
    (security.md "절대 금지" 범위 참조)

  YES → 즉시 현재 wave 중단 + 사용자 알림
         "Q1 트리거: [근거 한 줄]. 현재 wave를 중단합니다."
  NO  → Q2

Q2: 이 버그가 현재 wave AC의 전제를 파괴하는가?
    (현재 WIP의 AC Goal·검증 묶음을 직접 읽어 판단)
    "이 버그가 있으면 AC 체크박스가 거짓 통과되는 이유: ___"
    — 이유를 채울 수 없으면 NO

  YES → wave 중단 또는 AC 재정의 + 사용자 합의 요청
         "Q2 트리거: [AC 항목] 전제가 파괴됨. 중단 또는 AC 재정의?"
  NO  → Q3

Q3: 이 버그가 나중에 자동으로 발견되기 어려운가?
    (조용한 실패 / 다운스트림 전파 / 재현 어려움)

  YES → WIP 즉시 기록 + CPS P# 즉시 매칭 + 현재 wave 속행
         현재 WIP 파일 하단 "## 발견된 스코프 외 이슈" 섹션에 추가:
         - 버그 설명 (1~2줄)
         - 발견 컨텍스트 (어느 Step, 어느 파일)
         - CPS P# 매칭 결과:
             기존 P# 해당: `problem: P#` 명시
             해당 없음: `problem: NEW — "[버그 핵심어]"` 플래그
                        → 다음 implementation Step 0에서 자동 인식 대상
                        → owner 확인 후 CPS 신규 P# 등록
  NO  → 무시 가능
         "Q3=NO: [이유]. 이 버그는 나중에 자연히 발견됨."

CPS P# 매칭 판단 기준:
  - project_kickoff.md Problems 섹션을 직접 Read
  - 버그가 기존 Problem의 "증상" 또는 "영향"에 해당하면 그 P#
  - 어느 P#에도 해당하지 않으면 NEW 플래그
  - 매칭이 모호하면 가장 가까운 P# + "부분" 표시
```

### 판단 근거 명시 강제

각 Q의 YES 판단은 반드시 **근거 한 줄**이 있어야 한다. 없으면 판단 자체를
재실행한다.

```
판단 블록 형식:
  Q1: YES|NO — [근거]
  Q2: YES|NO — [근거 또는 "이유 없음 → NO 강제"]
  Q3: YES|NO — [근거]
  결정: STOP|REDEFINE|NOTE|IGNORE
```

### Q1 인플레이션 방지 (advisor 지적 반영)

Q1 정의를 좁게 유지한다. YES가 되려면 다음 중 하나가 반드시 참이어야 한다:
- DB write/delete 경로에 직접 영향
- 인증·권한 검사 우회 가능성
- 외부 시스템으로 데이터 유출 경로
- 시크릿 평문 노출

내부 회귀·UI 버그·테스트 실패는 Q1 대상 아님 → Q2로 이동.

세션당 Q1=YES가 2회 초과하면 calibration 경고:
> "Q1=YES가 이번 세션 3회째입니다. 정의 좁히기 재확인 필요."

### 도메인 컨텍스트 (가중치 대신 분기 재정의)

수치 가중치 대신 조건부 분기 재정의:
- 변경 파일이 auth/, security/, migration/ 경로 → Q1 YES 전제로 시작
  (위 Yes 조건 중 하나라도 해당하는지 먼저 적극 검토)
- 버그가 공개 API 경계 또는 다운스트림 직접 사용 경로 → Q3 YES로 강제

---

## 구현 위치 — 순환 루프 3계층

### Layer 1 — 발견 즉시 (BIT 핵심)

**rules/bug-interrupt.md (신설)**
- 원칙 + Q1/Q2/Q3 결정 트리
- Q1 인플레이션 방지 정의 (4개 조건)
- 도메인 컨텍스트 분기 재정의
- Q3 CPS P# 즉시 매칭 절차

**implementation/SKILL.md (연결)**
- 작업 진행 중 어느 Step에서든 스코프 외 이슈 발견 시 bug-interrupt.md 적용
- rules 파일이므로 implementation 외 경로(직접 수정 등)에서도 동작

**WIP 파일 템플릿 (확장)**
- "## 발견된 스코프 외 이슈" 섹션 표준화
- 항목 형식: `- [버그 설명] | 발견: [Step/파일] | P#: [P# 또는 NEW—"핵심어"]`

### Layer 2 — 세션 경계 (session-start.sh 확장)

현재 session-start.sh가 WIP 파일을 이미 순회함(L39~58). 확장 추가:
- WIP 파일에 "## 발견된 스코프 외 이슈" 섹션이 있으면 세션 시작 시 알림
- `problem: NEW` 플래그가 있으면 "CPS 신규 P# 검토 필요" 강조 표시
- cluster 파일 최종 수정 시각 vs 최근 docs/ 변경 비교 → stale 경고

구현 난이도: 낮음 (기존 awk 순회 로직 확장)

### Layer 3 — 주기 갱신 (CPS + cluster)

**implementation Step 0 자동 인식 (기존 로직 활용)**
- `problem: NEW` 플래그가 있는 WIP 섹션을 Step 0 CPS 매칭 대상에 포함
- 매칭 결과: 기존 P# 발견 → 플래그 교체 / 해당 없음 → owner 확인 후 신규 P# 등록

**CPS 업데이트 권한 (BIT 맥락 명확화)**

| 행동 | 권한 | 이유 |
|------|------|------|
| Q3 → 기존 P# 연결 | Claude 단독 | 버그 사실 확인, 판단 완료 |
| Q3 → 신규 P# 추가 | Claude 단독 | Problem 추가는 원래도 단독 가능 |
| 신규 P#에 Solution 정의 | owner 승인 | cascade 영향 — 연결 문서 solution-ref 무효화 가능 |
| 기존 Solution 충족 기준 변경 | owner 승인 | cascade 영향 큼 |

"owner 승인"이 필요한 경계는 **Solution 정의/변경 시점**이다. P# 추가 자체는
버그의 존재라는 사실을 기록하는 것이며, 승인이 흐름을 끊을 이유가 없다.
BIT가 이미 Q1/Q2/Q3로 중요도 판단을 완료했으므로, P# 매칭·추가는 그 판단의
자연스러운 귀결이다.

**eval --harness 확장**
- `problem: NEW` 플래그 미처리 건 집계 → 보고
- solution-ref 박제 의심 건 누적 → CPS 갱신 권고

**cluster 자동 연동**
- CPS project_kickoff.md가 staged될 때 → cluster-update 자동 트리거
- pre_commit_check.py: CPS staged + solution-ref 미갱신 파일 → 경고 격상

---

## 예상 효과

1. **추적 소실 차단**: Q3 트리거로 발견 즉시 WIP 기록 → anti-defer.md
   "기록 없는 미루기" 패턴 차단
2. **AC 거짓 통과 방지**: Q2가 현재 AC를 직접 읽어 전제 파괴 검토
3. **보안 cascade 차단**: Q1 좁은 정의 + 도메인 분기로 critical 자동 escalation
4. **판단 근거 박제**: 빈칸 강제로 "아마 괜찮겠지" 추측 차단
5. **CPS 자연 갱신**: Q3+CPS 즉시 매칭으로 발견 이슈가 하네스 Problem 목록에
   자동 피드백 → CPS가 실제 작업 경험을 반영하며 살아있는 문서로 진화
6. **유산 활용 루프 완성**: 단방향(작업→문서) → 순환(작업→발견→CPS→다음작업)

## 예상 위험 및 완화

| 위험 | 완화 |
|------|------|
| Q1 인플레이션 (가장 큰 실패 모드) | Q1 정의 4개 조건으로 좁힘 + 세션당 2회 상한 경고 |
| scope creep 합법화 | Q3 결과는 "현재 wave 확장" 아닌 "WIP 섹션 기록"만 |
| 판단 비일관성 | 판단 기준 SSOT를 AC+CPS+security.md로 외부화 |
| rules 누적 피로 | 독립 기준 없음 — 기존 rules 참조 전용 |
| 알림 노이즈 | Q1 2회 상한으로 "양치기 소년" 방지 |

## 뒤집힐 조건 (advisor 지정)

1. Q1=YES 비율이 세션당 평균 2회 초과 → 인플레이션 — 시스템 재설계
2. BIT 도입 후에도 별 wave 분리 패턴이 유지 안 됨 → 중복 메커니즘 — 폐기
3. 다운스트림에서 도메인 분기 재정의가 SSOT 분열 유발 → 분기 부분만 폐기

## 사후 검증 계획

6개월 후 (2026-11-05 기준):
- Q1=YES 판정의 실제 critical 비율 incidents/ 추적
- BIT 없이 소실됐을 버그 수 추정 (WIP "발견된 스코프 외 이슈" 섹션 집계)
- rules 파일 수 대비 context 부담 실측

## 작업 목록

### Phase 1 — rules/bug-interrupt.md 신설

**Acceptance Criteria**:
- [x] Goal: BIT 시스템 핵심 규칙 파일 작성 및 기존 rules/스킬과 연결
  검증:
    review: self
    tests: 없음
    실측: rules/bug-interrupt.md 존재 + Q1/Q2/Q3 결정 트리 + CPS P# 매칭 절차 포함 확인

- [x] rules/bug-interrupt.md 생성 — Q1/Q2/Q3 결정 트리, 판단 블록 형식, Q1 인플레이션 방지, 도메인 분기 재정의, Q3 WIP 기록 + CPS P# 즉시 매칭 절차, 순환 루프 연결 다이어그램 포함 ✅
- [x] implementation/SKILL.md Step 3에 "스코프 외 버그 발견 시 bug-interrupt.md 적용" 참조 추가 ✅
- [x] docs.md CPS 변경 권한 표 — "Problem 추가: Claude 단독 (BIT Q3 경로 포함)" 명시 ✅

## 구현 순서

```
Phase 1 (완료 2026-05-05):
  ✅ rules/bug-interrupt.md 신설 (BIT 핵심 — Layer 1)
  ✅ implementation/SKILL.md Step 3에 BIT 참조 추가
  ✅ docs.md CPS 변경 권한 표 BIT 경로 명시
    ↓
Phase 2 (단기): session-start.sh 이슈 섹션 감지 추가 (Layer 2)
                implementation SKILL.md Step 0.8 기록 의무 1줄
    ↓
Phase 3 (중기): eval --harness "problem: NEW 미처리 집계" 추가 (Layer 3)
                pre_commit_check.py CPS empty 경고 추가
    ↓
Phase 4 (장기): CPS staged → cluster-update 자동 트리거
                implementation Step 0 NEW 플래그 자동 인식
```

## 메모

- 리서처 조사: RULERS 논문(arXiv:2601.08654) — 판단 근거 명시 강제가
  소형 모델도 대형 모델과 판단 일관성 수렴시킴. 빈칸 강제 설계 근거.
- advisor 권고: "신규 files 대신 기존 확장" — 반론: 발견 시점 타이밍이 다름.
  타협: 독립 기준 없이 기존 rules 참조 전용으로 context 부담 최소화.
- 외부 연구: LLM 에이전트가 스코프 외 발견에 주의 분산되는 것 자체가
  실증된 실패 모드 (arXiv 2411.10213).
- 누적 트리거 방식 폐기: "3건 누적 후 CPS 승격" 초안은 BIT 목적(즉각 판단)과
  모순. Q3 기록 시점에 CPS P# 즉시 매칭으로 대체 (2026-05-05 수정).
