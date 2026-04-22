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
