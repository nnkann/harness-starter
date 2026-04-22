---
title: review staging 후속 — 신호 정밀화 + 5커밋 측정 + S1 오탐 보정
domain: harness
tags: [staging, review, performance, measurement]
relates-to:
  - path: ../harness/hn_commit_review_staging.md
    rel: extends
  - path: WIP/harness--hn_commit_process_audit.md
    rel: references
status: in-progress
created: 2026-04-19
updated: 2026-04-22
---

> **SSOT 이관 (2026-04-22)**: 미결 항목의 결정·실측·추적은 상위 감사
> 문서 `WIP/harness--hn_commit_process_audit.md`가 담당. 본 문서는
> 2026-04-19 완료분(S1 오탐·S6 완화) 이력 + 설계 맥락 보존용.
>
> - 5커밋 측정 + 체감 임계 + 세션 누적 4건 실측 → audit 항목 #13 보강
> - S8 정밀화·S6 자동화·폭증 게이트 → audit 항목 #17
> - 커밋 분리 전략(거대 + 글로벌 원칙 정정) → audit 항목 #18

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

#### S8 export 검출 정밀화 → **audit #17 이관**
#### S6 문서 + 줄 ≤ 5 → Stage 0 자동화 → **audit #17 이관**

### 7단계. 5커밋 측정 → **audit #13 보강으로 이관**

측정 스키마(p50/p90/p100·체감 임계) + 세션 누적 4건 실측 테이블은
audit #13 보강 섹션으로 이관. 본 섹션은 설계 맥락 보존용 골격만 유지.

### 폭증 차단 게이트 → **audit #17 이관**

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

### 2026-04-22 — 경과시간 체감 축 + 세션 누적 4건 실측 → **audit #13 보강 이관**

v0.18.4~v0.18.7 커밋 실측 테이블, 측정 스키마(p50/p90/p100·체감 임계),
해결책 설계 공간(A/B/C/D), `.claude/scripts/**` 5줄 룰 재검토 근거 전부
audit 항목 #13 보강 섹션으로 이관. 실측 5건 누적 후 결정은 audit에서.

### 2026-04-22 — 거대 커밋 분리 전략 + 글로벌 원칙 정정 → **audit #18 이관**

bulk 폐기 후속으로 작성된 분리 축(A~H)·속도 최적화·구조적 요소
(`HARNESS_SPLIT_SUB`·stdout 스키마·`split-commit.sh`)·1회 판정 정정은
audit 항목 #18로 이관. 설계 공간 전체 보존.
