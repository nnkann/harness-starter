---
title: review staging 후속 — 신호 정밀화 + 5커밋 측정 + S1 오탐 보정
domain: harness
tags: [staging, review, performance, measurement]
relates-to:
  - path: ../harness/hn_commit_review_staging.md
    rel: extends
status: in-progress
created: 2026-04-19
updated: 2026-04-22
---

# review staging 후속

## 처리 결과 (2026-04-19)

P1(S1 오탐 보정) + S6 완화 자동화 처리:

1. **S1 2단계 분리** — `s1_level=line-confirmed`(실제 시크릿) vs
   `file-only`(파일명만)로 분리. file-only는 standard로 완화.
   테스트·docs·example·`-helper.`/`-utils.` 파일은 면제.
2. **S6 ≤5줄 → Stage 0** — pre-check이 자동으로 skip 결정.
3. **stdout 13 keys** — `s1_level` 추가.
4. **staging.md** Stage 결정 우선순위·신호 정의 표 동기화.

잔여(S8 정밀화·5커밋 측정·폭증 게이트)는 별도 WIP 분리:
`docs/WIP/harness--hn_staging_remaining.md`.

---

## 원본

원본 WIP `harness--hn_commit_review_staging.md`의 잔여 6·7단계.

## 완료된 것 (커밋 84ad413)

- 1단계: rules/staging.md 신설 (단일 진실)
- 2단계: naming.md 도메인 등급 + 경로 매핑 섹션
- 3단계: commit Step 4 자동 병합
- 4단계: pre-commit-check.sh 13개 신호 감지 + stdout 6 keys 추가
- 5단계: commit Step 7 stage 분기 + review.md 신호별 매핑

## 잔여 작업

### 6단계. 신호 정밀화

#### S1 파일명 오탐 보정 (즉시)

현재 `auth/token/secret/key/credential/password/.env` 파일명 단어만 hit해도
S1 → Stage 3 deep 강제. 안전 방향 오탐이지만 의외 deep 사유 추적 어려움.

개선:
- 라인 패턴(시크릿 값) 신뢰도가 충분히 높아지면 파일명 패턴을 좁힘
- `auth-helper.ts` 같은 일반 보조 파일 면제 패턴 추가
- 또는 파일명만 hit이면 Stage 2로, 라인 패턴까지 hit이면 Stage 3로 분리

#### S8 export 검출 정밀화

현재 휴리스틱 (`grep -E '^[+-].*export'`) — 문자열·주석에도 잡힘.
언어별 시그니처(TypeScript export·Python def·Go func) 분리 검토.

#### S6 문서 + 줄 ≤ 5 → Stage 0 자동화

현재 staging.md "C. 완화"에 명시됐지만 pre-check.sh에서 미구현.

### 7단계. 5커밋 측정

다음 5번 커밋의:
- review 시간 평균
- tool_uses 평균
- 입력 토큰 평균
- Stage별 분포 (skip/micro/standard/deep 빈도)

목표: 평균 시간 60% 절감 (60s → 24s 수준).

### 폭증 차단 게이트 코드 강제 (장기)

현재 staging.md "신호 추가 4질문"·"연결 규칙 5케이스"는 텍스트 규범.
pre-check이 신호 수 13 초과 시 경고 로직 추가 검토 (1인 운영이면 후순위).

## 우선순위

- P1: S1 오탐 보정 (사용자 체감 즉시)
- P2: 5커밋 측정 (효과 검증 데이터)
- P3: S8 정밀화·S6 완화 자동화
- P4: 폭증 게이트 코드화

## 의존성

5커밋 측정은 staging 시스템이 동작하는 정상 사용 흐름 필요.
다른 작업 진행하면서 자연스럽게 데이터 누적.

## 검증

- 보정 후 S1 오탐이 실제 줄어드는지
- 측정 결과가 60% 절감 목표에 부합하는지

## 변경 이력

### 2026-04-22 — 경과시간 체감 축 추가 (v0.18.4 발화)

v0.18.4 커밋 (`f597b77`) review 시 사용자 피드백:
> "아...진짜 리뷰 더럽게 느리네. 신경질 날 정도인데?"

실측:
- diff 실질: 정규식 문자열 교체 + 회귀 테스트 12 케이스 + 문서
- staging: deep (5줄 룰 1번 — `.claude/scripts/**`)
- review: **4 tool_uses, ~30초, 58k tokens, verdict: pass** (실질 이슈 0)

**기존 지표(tool call 수)는 이미 정상 범위**:
- `hn_review_tool_budget.md` 설계상 deep 목표 3~5회 / 상한 6회
- 4회 사용은 상한 내 절약된 값. 조기 중단도 부분적으로 작동 중

**하지만 사용자 체감 = 경과시간**:
- tool_uses 4회여도 각 호출 간 처리·토큰 입출력이 30초 쌓음
- 기존 "60% 절감 목표"는 지표 불명확. 시간·tool_uses·토큰 중 무엇?
- 사용자 인내 임계 관찰 필요

### 새 측정 항목 (7단계 보강)

기존 "5커밋 측정" 항목을 다음으로 구체화:

| 지표 | 기존 | 보강 |
|------|------|------|
| review 시간 | 평균 | **p50·p90·p100, 커밋별 기록** |
| tool_uses | 평균 | 평균 + stage별 분포 |
| 입력 토큰 | 평균 | 평균 + prompt 크기와의 상관 |
| Stage 분포 | 빈도 | 빈도 + 각 stage의 p90 경과시간 |
| **체감 임계** | (없음) | 사용자 불만 발화 시점의 실측 값 기록 |

**체감 임계 측정**: 사용자가 "느리다"고 발화한 커밋의 경과시간을 기록해
**허용 상한**을 데이터로 확보. 추측 말고 관찰.

### 해결책 설계 공간 (측정 완료 후 결정)

측정 전 섣부른 구현 금지. 선택지 스케치만:

- **A**: `.claude/scripts/**` deep 강제 완화 — 회귀 테스트 동반 + 테스트
  녹색이면 standard 격하. 리스크: 회귀 테스트 커버리지 가정 과신
- **B**: deep 내부 조기 중단 더 공격적으로 — tool_budget 원칙 2 강화.
  "계약 Step 1에서 신호별 알파 미hit이면 즉시 pass". 리스크: 놓침
- **C**: review 병렬화 — tool 호출 간 대기 시간을 줄이는 방향. 리스크:
  에이전트 스펙 외 영역
- **D**: 사용자 수동 `--quick` 남발 방치 — 측정 결과가 "이 정도 시간은
  허용 범위"로 나오면 개선 불필요

### 선행 조건

1. commit 스킬에 stage별 경과시간 로그 기록 기능 (hn_commit_perf_optimization.md §4 "시간 리포팅"이 이미 제안됨 — 활용)
2. 다음 5~10 커밋 측정 누적
3. 사용자 불만 재발 시점 기록

### 상위 SSOT 재확인

- `hn_review_staging_rebalance.md` (v0.17.0): 5줄 룰 근거 — `.claude/scripts/**` deep 강제는 의도. 이번 불만만으로 뒤집지 않음
- `hn_review_tool_budget.md` (v0.17.1): 조기 중단·알파 발동 조건 설계. 체감 속도 개선의 1차 경로는 이쪽 튜닝
- `hn_commit_perf_optimization.md` §4: 시간 리포팅 구현 제안 (미완)

v0.18.4 체감 이슈는 이 세 SSOT의 교차 영역. 본 WIP가 관찰·측정
담당, 해결책은 측정 결과에 따라 위 SSOT 중 하나에 귀속.

---

### 2026-04-22 추가 실측 (세션 누적 4건)

bulk 폐기 세션에서 이번 커밋 4건의 review 실측:

| 커밋 | signals | stage | 실측 | 판정 |
|------|---------|-------|------|------|
| v0.18.4 | S2,S9,S10,S7 | deep | 4 calls, ~30초, pass | 과잉 (실질 이슈 0) |
| v0.18.5 | S2,S9,S10,S7 | deep | 7 calls, ~60초, block→pass | 값어치 (cluster dead link) |
| v0.18.6 | S2,S9,S10,S7 | deep | 재호출 포함 80초+, warn | 과잉 (참고 1건) |
| v0.18.7 | S9,S10,S7 | deep | 1 call, ~27초, pass | 과잉 (문자열 drift fix) |

**4/4 중 3건 deep 과잉 (75%)**. 유일한 값어치 건(v0.18.5)이 잡은 것
(cluster dead link)은 v0.18.6에서 pre-check Step 3.5로 이식됨 → 이후
deep이 잡을 실질 이슈 추가 감소 예상.

**공통 패턴**: `.claude/scripts/**` 수정 → 5줄 룰 1번으로 무조건 deep.
S10 max=5 격상이 겹쳐 룰 1 miss 커밋도 deep 강제.

**hn_review_staging_rebalance.md (v0.17.0)의 근거 재검토**:
- 22 deep 중 scripts 10건·warn 2건으로 "scripts는 deep 유지" 결정
- 이번 4건은 모두 scripts 변경, 실측 warn 1건 (25%). 당시 20%와 비슷
- 단 **이번 warn은 pre-check Step 3.5로 이미 이식됨** → 남은 deep의 값어치
  더 낮아질 예측

5건 누적(현재 4건 + 다음 1건) 후 해결책 A/B/C/D 결정.

---

### 거대 커밋 분리 전략 (2026-04-22 bulk 폐기 후속)

#### 배경

bulk 스테이지 폐기(2026-04-22)로 "거대 커밋은 스코프 분리" 원칙만 남음.
staging.md에 한 줄 권고뿐, **어떻게 분리할지 무설계**. 과거 bulk의 실질
목적(빠른 검증·체감 속도)을 **분리 전략으로 계승**해야 함.

사용자 제안 (세션 2026-04-22):
1. 1차 축: **파일 경로 카테고리**
2. 카테고리 안에서 임계 초과 시 재분리
3. 임계 이하는 **내용별 묶음**으로 분리 커밋
4. 최고 목표: **빠른 분리 + 빠른 커밋** (과거 bulk 목적 계승)

사용자 추가 (같은 세션):
- **H. 한 문서 안의 여러 변경 단위 분리**: 같은 파일이어도 hunk별 독립
  주제면 분리 커밋 가능 (`git add -p` 식)

#### 설계 공간 (실측 전 스케치 — 결정 금지)

##### A. 분리 축 정의

- **1차**: `naming.md` "경로 → 도메인 매핑" 재활용 (이미 SSOT 존재)
- **폴백**: 도메인 매핑 없는 파일은 **폴더 1단계** 경로 prefix로 그룹화
- **경로 경계 깊이**: 1단계 기본 (`.claude/scripts/`·`src/payment/`).
  2단계 이상 세분화는 실측 후 결정

##### B. 임계·재분리 조건

- 1차 그룹 안에서 **파일 N개 초과 시 재분리**. N 초안: 10 (실측 대기)
- 재분리 축: subject 키워드·diff 패턴·또는 사용자 힌트
- 전체 커밋이 임계 미만이면 **내용별 묶음** 그대로 커밋

##### C. "내용별 묶음" 기준

가장 모호한 축. 초안:
- 같은 **subject 키워드** (feat/fix/refactor 동일 + 대상 주제 동일)
- **diff hunk 패턴 유사성** (같은 함수·모듈에 대한 변경)
- 애매하면 사용자 확인 1회 (대화형)

##### D. 한 파일 안 hunk 분리 (사용자 추가 H)

- 같은 파일이어도 **독립 주제 hunk**면 `git add -p` 식으로 분리
- 예: 같은 `staging.md` 수정 안에 "bulk 제거" + "5줄 룰 문구 다듬기"
  → 별도 커밋 2개
- 판단 기준: hunk 간 **의미론적 거리** (코드 블록·섹션·함수 경계)
- 실제 구현: `git add -p` 자동화 or Claude가 각 hunk 검토

##### E. 속도 최적화 (bulk의 실질 목적 계승)

분리로 N배 커밋되면 review도 N배 → **체감 더 나빠질 위험**. 방어:

- 분리된 각 sub-커밋은 **review stage 자동 재판정**. 사이즈 작아지면
  자연스럽게 standard → skip까지 내려감
- **위험 카테고리만 review 유지** (예: `.claude/scripts/` sub-커밋은
  standard, `docs/` sub-커밋은 skip)
- **review 병렬 호출 가능성** 탐색 (에이전트 스펙 확인 필요)
- **커밋 메시지 초안 자동 생성**: 카테고리 + 주요 diff 요약으로. 사용자
  검토만 — 수동 작성 시간 제거

##### F. 구현 위치

- **pre-check**이 거대 감지 → 경고만 (현재 상태)
- **commit 스킬 내부**에 "분리 계획 Step" 신설 — Claude가 분리안 제시,
  사용자 승인, 자동 커밋 N회 실행
- **implementation 스킬**이 작업 중 거대해지는 걸 감지하고 **선제 분리
  유도** (커밋 전에 미리 알림)

##### G. 예외·실패 경로

- **rename-only 대량 커밋**: 원자적. 분리 불가 → 예외. 대신 review skip·
  pre-check dead link 이식(v0.18.6)으로 방어
- **의존성 있는 변경**: 파일 간 순서 어긋나면 빌드/테스트 깨짐 → 분리 전
  각 sub-staging에 대해 pre-check·빌드 통과 확인. 실패 시 롤백
- **사용자가 "통째로 가고 싶다" 판단**: 수동 오버라이드 유지 (`--no-split`
  같은 플래그?)

##### H. etc — 추가 축

위 7 + H 외에 실측 중 발견할 수 있는 축들을 기록 공간으로 남김:
- 관련 파일 간 의존 그래프 분석 (import·require 관계)
- 테스트 파일 + 대상 소스 파일은 **같이** 묶기 (분리 금지)
- 시크릿·보안 변경은 **단독 커밋** (강제 분리)
- 리뷰어별 관심사 카테고리 (다운스트림 확장)

#### 필요한 판단 (사용자 확인 대기)

이 설계 중 우선순위:

1. **E. 속도 최적화**가 최고 목표. 이게 실패하면 분리 자체가 무의미.
   먼저 실측 필요
2. **A·B 자동화 수준**: 완전 자동 vs 사용자 확인 대화형. 트레이드오프
   명확 — 자동은 빠르지만 오분류 위험
3. **C "내용별 묶음"의 주관성**: 휴리스틱 규칙 vs LLM 판단. 규칙이면
   빠르고 예측 가능, LLM이면 정확하지만 비용
4. **D hunk 분리**는 구현 복잡도 큼. 파일 단위 분리 먼저 정립 후
   확장 검토

#### 선행 조건

- 실측 5건 누적 (staging rebalance 재평가)
- commit 스킬에 stage별 경과시간 로그 (`hn_commit_perf_optimization.md` §4)
- 거대 커밋 발생 케이스 관찰 (언제·왜 거대해지는지 패턴)

#### 상위 SSOT

- `hn_review_staging_rebalance.md` — 5줄 룰 원칙 (분리 축과 정합 필요)
- `hn_review_tool_budget.md` — review 예산. 분리된 sub-커밋 각각에 적용
- `docs/incidents/hn_review_maxturns_verdict_miss.md` — bulk 폐기 근거
- `hn_commit_perf_optimization.md` — 시간 리포팅 제안 (미완)

분리 전략은 이 4개 교차 영역. 실측 누적 후 결정 문서(`decisions/`)로
승격 검토.

---

### 2026-04-22 정정 — 분리 판정은 1회, 글로벌 원칙

앞선 "거대 커밋 분리 전략" 섹션의 프레이밍 오류 정정.

#### 관점 전환

분리는 **거대 커밋 전용이 아니라 모든 커밋에 적용되는 글로벌 원칙**.
bulk 폐기와 함께 그 방향(정량 처리)이 전체로 확장됨.

- 섹션 제목 "거대 커밋 분리 전략" → **"커밋 분리 전략"**으로 재해석
- "거대 감지 시 경고" → **매 커밋 분리 기회 제시**
- 목적 "거대 커밋 제어" → **원자적 커밋 강제** (1 커밋 = 1 논리 단위)

#### 판정은 1회만 (오해 정정)

**틀린 전제**: "매 커밋마다 빠르게 분리 판정 돌려야"
**정정**: 분리 판정은 **커밋 시도 시작 시점 1회만**. 분리로 나눠진
sub-커밋은 이미 분리된 상태 → 다시 판정할 이유 없음.

```
사용자 커밋 시도
  ↓
pre-check (분리 판정 포함) — 1회만
  ↓
분리 필요? → sub-staging 재구성 → N개 sub-커밋
              각 sub-커밋의 pre-check은 "분리 판정 SKIP 모드"
              (lint·TODO·dead link 등 기본 검사만)
분리 불필요? → 그대로 커밋
```

#### 필요한 구조적 요소 (과잉 설계 제거 후)

속도 빠듯한 예산은 불필요. 대신:

1. **sub-커밋 신호**: `split-commit.sh` 같은 실행 스크립트가 sub-커밋
   호출 시 환경변수(예: `HARNESS_SPLIT_SUB=1`)로 "이미 분리됨" 표시.
   pre-check이 이 플래그 감지 시 분리 판정 블록 전체 스킵
2. **stdout 스키마**: pre-check이 분리 계획을 stdout으로 출력.
   `split_plan`·`split_group_N`·`split_action_recommended` 등 key 추가
3. **실행 스크립트**: `split-commit.sh` — pre-check stdout 읽어 `git reset`
   + 그룹별 `git add` + commit 반복. pre-check은 판정만, 실행은 여기

#### 실제 제약 (재정의)

- **속도**: 1회만 도는 판정이라 빠듯한 예산 불필요. 일반 pre-check 수준
  (~수 초)이면 충분
- **정확성·예측 가능성**: 1회로 끝나야 하므로 오판 시 분리 전체가 틀림.
  **규칙 기반 결정**이 LLM보다 안전 (같은 입력 → 같은 출력 보장)
- **절대 원칙**: pre-check 원래 기능을 깨뜨리지 않음. 분리 판정은
  **추가 블록**이지 대체 아님

#### 앞선 섹션과의 관계

섹션 "거대 커밋 분리 전략" (lines 178~)은 **프레이밍 오류로 폐기**.
다음 작업에서 제목부터 재작성 필요:
- 제목: "커밋 분리 전략 (글로벌)"
- A·B: 거대 여부 임계 제거. 항상 판정
- F: staging/pre-check 영역 (사용자 지적 반영). commit 스킬 아님
- 새로 추가: sub-커밋 신호 (`HARNESS_SPLIT_SUB`)
- 새로 추가: bulk 폐기와의 관계 — "대체가 아니라 원칙 확장"

재작성은 **단독 커밋**으로. 본 커밋은 정정 사실 기록만.
