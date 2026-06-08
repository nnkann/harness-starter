---

title: review staging 재조정 — scripts/agents 이진 판정
domain: harness
tags: [staging, review, rules, tokens]
problem: P2
s: [S2]
status: completed
created: 2026-04-21
updated: 2026-04-21
---

# review staging 재조정 — scripts/agents 이진 판정

## 배경

사용자 체감: `/commit` 시 review deep 호출이 과다 → 토큰·시간 낭비.

## 실측 (git log 기반, staging 도입 후 52 커밋 + 이전 샘플 20)

### 현 분포 (업스트림)

| stage | 횟수 | 비율 |
|---|---|---|
| skip | 27 | 52% |
| deep | 22 | 42% |
| micro | 2 | 4% |
| standard | **0** | **0%** |

**Standard 사용률 0%** — 4단계 중 1단계가 완전히 놀고 있음.

### 이상 분포 (사용자 목표)

review 돌리는 커밋 중: **deep 20% / standard 50% / micro 30%**

### 편향 확인

위 실측은 **하네스-starter 자체 개편 시기** 샘플. `.claude/*` 수정 비중
높음. 다운스트림은 `src/*`·`tests/*` 주력이라 기존 staging.md 룰 1~16이
잘 작동. 본 재조정은 **업스트림이 자주 치는 `.claude/scripts/agents/
hooks/settings/rules/skills/docs`** 대응 룰을 단순화하는 것.

### deep 22건 전수 분류

| 주 카테고리 | 건수 | 실측 warn | 현 stage | 적정 stage |
|---|---|---|---|---|
| scripts 실행 로직 | 10 | 2 | deep | deep |
| agents 판정 기준 | 3 | 0 | deep | deep |
| skills 본문 | 3 | 1 | deep | **standard** |
| rules 본문 재구성 | 2 | 1 | deep | **standard** |
| docs 일반 변경 | 3 | 1 | deep | **standard** |
| docs rename 대량 | 1 | 0 | deep | **bulk** |

**deep 22건 중 9건(41%)이 standard 이하로 내려가도 됨.** 단 review는
신호→카테고리 매핑상 standard에서도 warn 잡음 (깊이만 얕음).

## 결정 — 4줄 룰 최상위 판정

### 룰 (전면 대체, 5줄)

```
1. .claude/scripts/** OR .claude/agents/** OR .claude/hooks/** OR settings.json
                                                            → deep
2. S1 line-confirmed OR S14 OR S8(export 시그니처)          → deep
3. docs/** rename ≥30% OR 파일 ≥20                          → bulk
4. S5(메타 단독) OR WIP cleanup 단독                         → skip
5. (나머지)                                                 → standard
```

기존 staging.md 룰 1~16은 **전면 폐기**. 이유:
- 업스트림+다운스트림 모두 위 5줄로 커버
- 룰 14~16 (`S9(normal) + 규모`)은 "나머지 → standard"로 흡수
- 17룰 공존 시 어느 게 먼저 hit하는지 추적 어려움 + 복잡도
- 사용자 수동 오버라이드(`--quick`·`--deep`·`--bulk`·`--no-review`)는 그대로 작동

### 설계 철학

- **stage = 검사 넓이 + 분석 심도의 양축 증가**. review.md 현 구조 유지
  (신호 → 카테고리 매핑, stage별 심도 차이)
- **standard도 카테고리에 포함된 warn은 잡음**. 놓침 아님, 심도 차이
- **규모 임계 없음** — 줄 수·파일 수 기준 폐기. "scripts 한 줄도 위험"
  (실측 `ec85c790` 13줄 수정이 warn 1건 잡음)
- **이진 판정** — 경로 기반, 줄 수·파일 수 연산 없음. 단순·명확

### 전면 대체 근거

기존 staging.md 룰 1~16을 **유지하지 않음**:
- 17룰 공존 시 우선순위 추적·디버깅 어려움 (실제 사용자 피드백: 현
  staging 판정 결과 설명 불가)
- 룰 14~16 (`S9(normal) + 규모`)은 "나머지 → standard"로 자연 흡수
- 룰 1~13은 업스트림 4줄 룰이 우선 hit하므로 실질 미발동
- 단순성이 운영 신뢰성보다 가치 큼 (사용자가 왜 deep인지 즉시 추론 가능)

안전성 보존은:
- S1·S14·S8 같은 **위험 신호는 룰 2에 명시 포함**
- 수동 오버라이드(`--deep`·`--bulk`·`--no-review`) 유지
- review.md 불변 → stage별 검증 심도는 그대로

### 예상 분포 (업스트림 22 deep 재판정)

| 신 판정 | 건수 | 비율 |
|---|---|---|
| deep | 12 | 55% |
| standard | 9 | 41% |
| bulk | 1 | 4% |

**review 돌리는 24건 중: deep 50% / standard 38% / micro 8% / bulk 4%**

이상 분포(20/50/30)와 거리 있지만 **업스트림 특성상 scripts 수정 빈도
높아서 자연스러움**. 다운스트림에선 4줄 룰 1·2 거의 미hit → deep 비율
훨씬 낮아짐.

### 토큰 비용 절감 (업스트림 기준)

- 현재: 42% deep × 1.0 + 4% micro × 0.1 ≈ 0.42 단위
- 신: 23% deep × 1.0 + 17% standard × 0.3 ≈ 0.28 단위
- **약 33% 절감**

다운스트림 추정: 60~70% 절감 (scripts/agents 거의 안 건드림 → deep 드물)

## 실행 계획

1. ✅ 본 WIP (결정 SSOT)
2. `.claude/rules/staging.md` — 4줄 룰을 Stage 결정 1단계 최상위에 추가.
   기존 1~16은 폴백으로 번호만 조정
3. `.claude/scripts/pre-commit-check.sh` — RECOMMENDED_STAGE 계산에 4줄
   룰 선행 조건 추가. 미hit 시 기존 로직 폴백
4. `.claude/scripts/test-pre-commit.sh` — 신 룰 회귀 테스트 12케이스:

   | # | 케이스 | 기대 stage |
   |---|---|---|
   | T21 | scripts 단독 변경 | deep |
   | T22 | agents 단독 변경 | deep |
   | T23 | hooks 단독 변경 | deep |
   | T24 | settings.json 단독 | deep |
   | T25 | rules 단독 (룰 1 miss) | **standard** |
   | T26 | skills 단독 (룰 1 miss) | **standard** |
   | T27 | CLAUDE.md 단독 | **standard** |
   | T28 | docs 일반 변경 | **standard** |
   | T29 | docs rename 25+ 파일 | **bulk** |
   | T30 | S5 메타 단독 (promotion-log만) | **skip** |
   | T31 | src/* + scripts/* 혼합 | deep (1번 우선) |
   | T32 | rules + docs + src 혼합 (룰 1 miss) | standard |
5. `docs/harness/MIGRATIONS.md` — v0.17.0 섹션 (자동 적용·왜·수동 액션
   불필요·검증·회귀 위험)
6. `docs/harness/promotion-log.md` — v0.17.0 이력
7. `.claude/HARNESS.json` — 0.16.1 → 0.17.0 (minor — 신 룰 도입, 기존
   호환)
8. 실측 22건 시뮬레이션으로 예상 분포 재검증
9. 커밋 + 푸시
10. `docs/clusters/harness.md` 신규 WIP/decisions 반영

## 회귀 위험

- **다운스트림 이상 없음** — 4줄 룰이 `.claude/*` 변경 기반이라 다운스트림
  일반 개발(`src/*`)에선 거의 미hit. 기존 룰 1~16이 그대로 작동
- **standard 경고 놓침 가능성** — review.md 구조상 신호 hit 카테고리는
  standard에서도 잡음. 3관점 심층 분석이 필요한 경고만 놓칠 수 있음.
  실측 warn 6건은 모두 grep·Read 1회 수준 → standard 커버
- **사용자 `--deep` 수동 오버라이드 가능** — 애매한 케이스는 명시적
  격상 경로 유지

## 검증

1. `test-pre-commit.sh` 전수 통과
2. 신 룰 회귀 테스트 6~8건 통과
3. 실측 22건 시뮬레이션 — 분포 예상치 ±10% 이내 일치
4. 다음 10 커밋에서 stage·warn 관찰 (사후 검증)

## 다운스트림 영향

- 4줄 룰 자체는 `.claude/*` 경로 기반이라 다운스트림 그대로 받음
- 다운스트림이 `.claude/scripts/`에 자기 스크립트 추가했으면 그것도
  deep 대상 (합리적)
- 기존 룰 폴백 유지로 `src/*` 판정 로직 불변

## 메모

### 제외한 축들 (분석 중 폐기)

- **규모 임계** (≤50줄, ≤300줄 등): 실측상 같은 규모에서 warn 유발 vs
  없음이 구분 안 됨. 한 줄 수정도 위험 있음
- **syntactic vs semantic**: rename 0% 커밋이 90% 이상으로 편향. 판정
  신호로 가치 없음 (docs rename 대량만 예외, 룰 3으로 흡수)
- **rolling window 학습** (최근 10 커밋 pass율): staging 도입 후 안정화
  시기 11 커밋뿐, 학습 데이터 부족
- **abbr 기반 판정**: S9 critical이 이미 같은 역할 수행
- **review.md 재설계**: 현 구조(신호→카테고리, stage별 심도)가 옳음

### 학습

- 업스트림 편향 데이터로 다운스트림 영향 추정 금지
- 실측 데이터는 **통계+중앙값+구간+각 사례 내용**까지 가공해야 의미 도출
- stage 축은 "얼마나 많이 보고 얼마나 깊이 보는가" — 한 축(깊이만 or
  넓이만)으로 환원 금지
- 룰 단순성 vs 놓침 가능성 트레이드오프는 실측 데이터로 확인하고 사용자
  판단에 맡기기
