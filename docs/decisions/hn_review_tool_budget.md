---

title: review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분
domain: harness
tags: [review, agent, tool-budget, tokens]
problem: P2
s: [S2]
status: completed
created: 2026-04-21
updated: 2026-04-25
---

# review 에이전트 tool call 예산 재설계

## 배경

사용자 지적 (2026-04-21):
1. **"6번 상한이지 기본 아니다"** — deep이면 무조건 5~6회 쓰는 게 아님.
   현재 review.md L286~291 "Stage 모드별 행동" 표가 이 구분을 명시 안 함
2. **기본·알파 구조의 내용 부재** — 내가 "기본 2회 + 알파"라고 수치만 제안했지,
   "2회가 무엇을 검사하는 2회인가"·"알파 trigger 기준이 뭔가"를 설명 못 함
3. **앞단 조기 중단 부재** — 초기 관점에서 명백한 문제가 안 나오면 거기서
   멈춰야 함 (tool 더 써도 소용없음)
4. **tool call 수는 유동적이어야** — 고정 1회 매핑은 기계적. 어떤 검사는
   0회(diff만 보고 판단), 어떤 건 2~3회 필요

## 실측 근거 (warn 6건 분석)

| SHA | warn 내용 | 발동 관점 | 실제 필요 tool |
|---|---|---|---|
| f879396e | ALLOWLIST 오탐 3건 | 계약 (기존 결정 위반) | Grep 1 |
| 042621ea | warn 1 (무효) | — | — |
| 74ab7c2d | rules 다이어트 분리 범위 | 스코프 (WIP vs 실제 diff) | Read 1 |
| 99f77cf3 | harness-upgrade dead link | 계약 (rules 참조 무결성) | Glob 1 |
| ec85c790 | S15 면제 누락 | 계약 (staging.md 일관성) | Read 1 |
| e0f33e49 | Phase 1·2 범위 확장 필요 | 스코프 (후속 항목 식별) | Read 1 |

### 발동 빈도

- **계약** (decisions·규칙 위반): 3/6건
- **스코프** (WIP·목적 대비 실제 범위): 2/6건
- **회귀** (동작 변경·공개 심볼): **0/6건**

회귀 관점은 **기본 검사에서 거의 발동 안 함** — 신호 S7·S8(공개 심볼
변경) hit 시에만 의미 있음. 현재 review.md L156-161도 이미 회귀는
"공개 심볼 변경(1번 패턴)이 커버"라고 축소돼 있음.

## 재설계 방향

### 원칙 1: 검사 축 재정의 (무엇을 2회 보는가)

review의 본질적 질문 2가지:

1. **"이 변경이 기존 계약을 어기나?"** (계약 축)
   - 기존 decisions/incidents와 모순 없는가
   - rules 규정 준수 여부
   - 참조 무결성 (dead link·dead ref)
   - 실측 50%의 warn이 여기서 발동

2. **"이 변경이 의도한 범위를 지키나?"** (스코프 축)
   - WIP 문서에 없던 변경이 포함됐는가
   - 목표 대비 과대·과소 변경
   - 커밋 목적과 diff 일관성
   - 실측 33%의 warn이 여기서 발동

**회귀 축은 기본에서 제외** — 신호 hit 시에만 추가 (아래 원칙 3)

### 원칙 2: 조기 중단 (앞단에서 문제 없으면 멈춤)

현재 review.md는 "카테고리 전체 훑기"가 기본. 결과적으로 **초기에 이미 충분히
깨끗해도 계속 도구 호출**. 개선:

```
Step 1: 계약 검사 → 문제 없음 + 신호 hit 없음 → 즉시 verdict: pass
Step 2: 스코프 검사 → 문제 없음 + 스코프 이탈 조짐 없음 → pass 가능
Step 3: 신호별 추가 검사 (알파) — 필요할 때만
```

**"문제 없음" 판정 기준**:
- diff만 읽고 판단 가능한 수준의 증거가 pass 쪽
- 파일 열어봐야 확신할 수 있는 의심점이 없음
- prompt의 "전제 컨텍스트" + pre-check 결과로 설명 가능

### 원칙 3: 알파 trigger — 신호별 구체 조건

알파 발동은 **"이 신호가 실제로 이 tool을 필요로 하는가"**로 결정.
신호 hit만으로 자동 발동 아님.

| 신호 | 알파 tool | 발동 조건 (이것이 있을 때만) |
|---|---|---|
| S1 line-confirmed | 시크릿 패턴 grep 1회 | pre-check이 이미 line 감지했으면 **스킵** (중복) |
| S2 핵심설정 | 호출자 영향 grep 1회 | 수정된 파일을 **다른 스크립트가 참조**하면 발동 |
| S3 신규파일 | 프론트매터 Read 1회 | 신규 파일이 docs/ 하위 md면 발동 |
| S6 문서 | cluster 정합성 grep 1회 | 이동·생성된 문서 있으면. 단순 내용 수정은 스킵 |
| S7·S8 | 회귀 (테스트 Glob 1회) | 공개 심볼·export 변경이 diff에 실제 보이면 |
| S9 critical | 도메인 incidents grep 1회 | 현 변경과 **주제 겹침** 추정 시만 |
| S10 3회 | git log 1회 | 반복 수정 영역이 **왜 반복인지** diff로 설명 안 되면 |
| S14 migration | 롤백 시나리오 Read 1회 | migration 파일 diff에 drop·rename 있으면 |
| S15 manifest | 의존성 보안 grep 1회 | 버전 major 변경·신규 의존성만 |

**공통**: 알파는 **1회에 1 신호 1 tool이 목표**지만, 필요 시 0회(스킵)
또는 2회(복잡한 신호) 유동적. 고정 매핑 아님.

### 원칙 4: tool call 유동 배분

Stage 재정의:

```
micro:
  - 계약 Step 1만 (조기 중단 가능)
  - diff 자체가 깨끗하면 0회 verdict: pass
  - 신호 hit 있어도 알파 중 가장 우선순위 1개만
  - 목표 0~1회, 상한 2회

standard:
  - 계약 + 스코프 둘 다 (각각 조기 중단 가능)
  - hit 신호별 알파 중 "필요 조건 충족"한 것만 실행
  - 목표 1~3회, 상한 4회

deep:
  - 계약 + 스코프 + 신호별 알파 전체
  - 추가로 "회귀 심층" (공개 심볼의 호출자 영향·3관점 교차)
  - 목표 3~5회, 상한 6회 (maxTurns hard cap)
```

**핵심 차이 (기존 대비)**:
- stage별 **목표 tool call 수가 범위**로 정의 (0~1, 1~3, 3~5)
- **조기 중단 허용**: 앞단에서 pass 판정 나오면 그대로 종료
- **알파는 신호 + 발동 조건 둘 다 hit**할 때만 실행

### 원칙 5: maxTurns 소진 시 처리 (기존 spec 보완)

현재 L185 "6회로 부족하면 [주의] 보고 + 경계 표 참조"는 모호. 명확화:

- **5회 사용 후에도 검증 더 필요하면**: 남은 1회는 **verdict 출력 여유분**
  으로 보존. 추가 tool 호출 금지
- **6회 hit 예상 시**: 직전에 지금까지 발견한 것 기준으로 verdict 내고 종료
- **verdict 없이 종료 금지** — incident `hn_review_maxturns_verdict_miss`
  에서 확인된 실패 모드. 6회 상한 초과 == 에이전트 스펙 위반

## 재설계 후 review.md 수정 범위

### 수정 대상

1. L156~162 "3관점" 섹션
   - "회귀·계약·스코프"를 **"계약·스코프 (회귀는 S7·S8 hit 시 추가)"**
     로 재구성
   - 각 관점의 조기 중단 조건 명시

2. L260~280 "신호 ↔ 검증 카테고리 매핑"
   - 각 신호에 **발동 조건** 열 추가
   - tool call 수를 **"최대"**로 명시 (고정 아님)

3. L282~293 "Stage 모드별 행동"
   - tool call 목표를 **범위**로 표기 (0~1, 1~3, 3~5)
   - 조기 중단 허용 명시

4. L183~187 "한도" 섹션
   - maxTurns 6 소진 시 verdict 출력 의무 재강조
   - 5회 이후 여유 1회 보존 원칙

5. L417~ "출력 형식" 섹션
   - 조기 중단 시 verdict 응답 구조 명시

### 수정 안 할 것

- "검증 루프 1~9번 패턴" (L45~162)
   - 이 9개 패턴은 유지. 다만 발동 조건이 조기 중단·알파 trigger로 연결됨
- "도구 선택 원칙" (L164~173)
- "낭비 금지" (L175~181)

## 실행 계획

1. ✅ 본 WIP 문서
2. ✅ `.claude/agents/review.md` 3관점 재구성 (2축 검사 + 회귀 알파)
3. ✅ review.md 신호 매핑에 발동 조건 열 추가 (v0.17.1)
4. ✅ review.md Stage 표 재작성 (tool call 범위 + 조기 중단)
5. ✅ review.md 한도 섹션 보완 (5회 여유 1회 보존)
6. ✅ review.md 출력 형식 조기 중단 응답 명시
7. ✅ `docs/harness/MIGRATIONS.md` v0.17.1 섹션 (이전 세션 완료)
8. ~~`docs/harness/promotion-log.md` v0.17.1 이력~~ (v0.20.7 폐기)
9. ✅ `.claude/HARNESS.json` 버전 범프 (커밋마다 patch 자동)
10. ✅ review.md:240 드리프트 수정 (4줄 → SSOT 포인터)
11. ✅ commit/SKILL.md split 동적 키 명시 + REVIEW_PRECHECK allowlist 추가
12. 본 WIP completed → `decisions/hn_review_tool_budget.md`

## 검증 방법

**실측 22 deep 건 시뮬레이션** — 각 커밋의 신호 조합·pre-check 결과 기준
으로 신 review 로직이 몇 회 tool call을 쓸지 추정:

| 현재 구성 | 예상 (신 로직) |
|---|---|
| scripts 수정 (S2·S9·S10·S7) | 기본 2 + 알파(S2·S10) 2 (S9 incident 스킵, S7 공개 심볼 없음) = **4회** |
| agents 수정 (S9·S7) | 기본 2 + 알파 0~1 (S9 겹침 적음, S7 공개 심볼 없음) = **2~3회** |
| rules 수정 (S2·S6·S9) | 기본 2 + 알파(S6 cluster·S9) 2 = **4회** |
| docs 일반 (S6·S9) | 기본 2 + 알파(S6) 1 = **3회** |
| **조기 중단 적용 시** | 절반 커밋이 계약 pass → 스코프 pass → **2회에서 verdict: pass** |

기대 효과:
- 현재 평균 ~5회 → 신 평균 ~3회 (40% 절감)
- maxTurns 소진 빈도 0 (조기 중단 + 여유 1회)
- warn 놓침 없음 (실측 6건 모두 계약·스코프 축에 포함)

## 회귀 위험

- **조기 중단이 너무 공격적**: 계약 pass만 보고 스코프 안 봐서 놓치는
  경우. 완화책: stage별 **필수 실행 단계**를 고정하고 (micro=계약만,
  standard=계약+스코프, deep=계약+스코프+알파) 그 이후에만 "추가 의심점
  없음"으로 조기 종료. 필수 단계를 건너뛰는 중단은 금지
- **알파 발동 조건이 복잡**: 각 신호별 조건을 에이전트가 실수로 해석
  할 위험. 완화: 조건을 **diff·pre-check 필드 기준**으로만 정의 (주관
  판단 배제)
- **tool call 유동 배분이 예측 불가**: 평균 3회지만 실제 커밋마다 1~5회
  편차. 완화: 각 stage별 **목표 범위 + 상한**을 명시해 예측 가능성 확보

## 질문 — 확정 (2026-04-21)

1. **기본 2회 축 정의**: **"계약·스코프" 확정**. 회귀는 S7·S8 hit 시
   알파로 이동 (실측 warn 6/6이 계약·스코프 축에 포함됨)
2. **조기 중단 허용 범위**: **C. 모든 stage에서 허용**. stage는 "검증
   심도의 상한"이지 "tool 호출 하한"이 아님. 중단 조건은 stage 불문 동일:
   - **micro**: 계약 Step 1 후 pass + 신호별 알파 조건 미hit → 종료
   - **standard**: 계약 + 스코프 둘 다 실행 후 pass + hit 신호 알파 조건
     실제로는 해당 없음 확인 → 종료
   - **deep**: 계약 + 스코프 + 해당 신호 알파 실행 후 추가 의심점 없음 →
     종료 (회귀 심층·호출자 교차를 형식적으로 돌리지 않음)
   - **공통 금지**: 의심점 있는데 tool 호출 아까워서 중단. 이건 조기 중단
     아니라 검증 회피. "더 보낼 게 없다"이지 "귀찮다"가 아님
3. **알파 발동 조건 표**: **제안 그대로 확정**. 실측상 더 좁힐 근거 없음.
   운영 중 오탐·미탐 발생 시 개별 신호 단위로 재조정
4. **tool call 상한 (maxTurns)**: **6 유지**. 조기 중단 + 5회 이후 여유
   1회(verdict 출력 보존)로 충분. 실측상 5회 초과 필요 케이스 없었음

## 메모

### 이번 세션에서 도달한 축

- "deep이 무조건 5~6회"는 오해 — 상한이지 기본 아님
- 기본 검사 = 계약 + 스코프 (회귀는 신호 hit 시)
- tool call은 유동, 고정 매핑 아님
- 조기 중단이 없으면 불필요한 도구 호출 누적
- 알파는 "신호 hit + 발동 조건 둘 다"일 때만

### 분리된 작업

- **staging.md 재조정** (v0.17.0) — 별도 WIP `hn_review_staging_rebalance.md`
- **review.md 재설계** (v0.17.1) — 본 WIP
- 두 커밋 분리하되 같은 세션에서 수정 가능

### 세션 컨텍스트

- 2026-04-21 세션에서 사용자 "컨텍스트 차고 있으니 WIP 먼저 만들고 세션
  정리" 요청으로 본 문서 작성
- 다음 세션에서 staging.md 재조정(v0.17.0) → review.md 재설계(v0.17.1)
  순으로 진행

## review prompt 입력 계약 구조화 (2026-04-23)

### 발견 배경

다운스트림에서 review verdict 누락 재발. 원인 추적 결과 "입력 비대 +
출력 토큰 한도 도달"로 확정 (상세: `docs/incidents/hn_review_maxturns_verdict_miss.md`
"2026-04-23 다운스트림 재발" 섹션). 입력 비대의 구조적 원인을 분석한 결과
두 가지 추가 결함 발견.

### 발견 1: split 시 동적 키 누출

`split_action_recommended: split`일 때 pre-check stdout에 `split_group_N_name`,
`split_group_N_files` 동적 키가 추가 출력된다. commit 스킬이
`PRE_CHECK_OUTPUT` 전체 변수를 보관하므로, split 커밋에서는 이 키들도
review prompt에 함께 박힌다.

v0.20.15 수정(4개 내부용 명시 제외)으로도 이 경로는 차단되지 않는다 — bash
필터링이 없고 텍스트 지시만 있기 때문. 따라서 split 커밋에서는 여전히 불필요
한 그룹 상세 정보(파일 목록 등)가 review에 들어간다.

### 발견 2: review.md 소비 계약 드리프트

`review.md:240`의 `(4줄 key:value)` 표현이 실제 10 keys 전달과 불일치.
구버전 표현이 남아 있는 문서 드리프트.

더 근본적 문제: review prompt 입력 계약이 **두 파일에 분산**돼 있다.
- `commit/SKILL.md` — "무엇을 어떻게 박는가" (보내는 쪽)
- `review.md` — "어떤 블록을 기대하는가" (받는 쪽)

두 문서 사이에 동기화 메커니즘이 없다. 한쪽이 갱신되면 다른 쪽이
드리프트한다. pre-check에 새 key가 추가될 때마다 수동으로 두 곳을 동시
갱신해야 하는 부담이 있으며, 이번처럼 한 곳만 갱신하면 계약이 깨진다.

### 대책

**즉시 (텍스트 강화):** //이걸 하나로 통합할 수 없나?
1. review.md:240 "(4줄 key:value)" → "(10 keys — commit/SKILL.md 입력 계약
   섹션이 SSOT)" 로 수정. 숫자를 박지 않고 SSOT 포인터로 대체
2. commit/SKILL.md 입력 계약 섹션에 "split 시 동적 키(split_group_N_*)도
   포함하지 마라" 명시 추가

**구조적 (bash 필터링):**
3. commit 스킬의 review prompt 조립 시 `PRE_CHECK_OUTPUT` 전체를 박는 대신
   허용목록(allowlist) grep으로 10 keys만 추출해 변수에 별도 저장:
   ```bash
   REVIEW_PRECHECK=$(echo "$PRE_CHECK_OUTPUT" | grep -E \
     "^(already_verified|risk_factors|diff_stats|signals|domains|\
   domain_grades|multi_domain|repeat_count|recommended_stage|s1_level):")
   ```
   이렇게 하면 pre-check에 key가 추가돼도 명시적 허용 전에는 review에
   들어가지 않는다.

**SSOT 단일화:**
4. review prompt 입력 계약의 SSOT를 `commit/SKILL.md` "## 호출 방법 →
   Agent tool 호출 → prompt 블록" 섹션으로 확정. review.md는 "어떤 블록이
   오는지"만 기술하고 key 목록은 commit/SKILL.md를 참조하도록 연결.

### 우선순위

| 대책 | 비용 | 효과 | 우선순위 |
|------|------|------|---------|
| 1. review.md:240 드리프트 수정 | 1줄 | 오해 방지 | 즉시 |
| 2. split 동적 키 명시 | 2줄 | 누출 방지 | 즉시 |
| 3. bash 필터링 도입 | 5줄 | 구조적 차단 | 다음 커밋 |
| 4. SSOT 단일화 | 문서 재작성 | 드리프트 근절 | 중기 |

대책 1·2는 문서 수정만이므로 즉시 반영. 3은 다음 commit/SKILL.md 수정
시 함께. 4는 commit-review 핸드오프 계약 재정비 시 포함.
