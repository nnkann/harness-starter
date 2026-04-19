---
title: review staging 후속 — 신호 정밀화 + 5커밋 측정 + S1 오탐 보정
domain: harness
tags: [staging, review, performance, measurement]
relates-to:
  - path: ../harness/commit_review_staging_260419.md
    rel: extends
status: pending
created: 2026-04-19
---

# review staging 후속

원본 WIP `harness--commit_review_staging_260419.md`의 잔여 6·7단계.

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
