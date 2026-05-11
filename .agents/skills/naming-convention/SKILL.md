---
name: naming-convention
description: 네이밍 컨벤션 설정 및 관리. 아키텍처별 폴더 규칙 분기, 파일/함수/메소드 규칙을 .claude/rules/naming.md에 정의. 새 도메인 등록도 여기서.
---

# 네이밍 컨벤션

프로젝트의 네이밍 규칙을 정의하거나 업데이트한다.
결과물은 항상 .claude/rules/naming.md에 기록한다.

## 핵심 원칙: 상위가 하위를 지배한다

폴더명 → 파일명 → 클래스/함수명 → 메소드명 순으로 결정된다.
상위 이름이 바뀌면 하위 전체가 따라 바뀐다.

예시:
  auth/                        ← 폴더가 도메인을 결정
    auth_page.tsx              ← 파일명이 폴더에서 파생
      export function AuthPage ← 클래스명이 파일명에서 파생
        handleAuthLogin()      ← 메소드명이 도메인+동작으로 결정

폴더명이 가장 신중해야 한다. 나머지는 따라온다.

## 초기 설정 흐름

### 0. 아키텍처 확인 (가장 먼저)

harness-init 스킬에서 아키텍처가 이미 결정되었으면 그대로 사용한다.
결정 안 됐으면 사용자에게 확인한다. 아키텍처에 따라 폴더 규칙이 달라진다.

아키텍처가 결정되면 → 아래 해당 섹션의 폴더 규칙을 naming.md에 기록한다.

---

## 아키텍처별 폴더 규칙

> 아래는 각 아키텍처의 **폴더 구조만** 다루며,
> 파일명·클래스명·메소드명 등은 아키텍처와 무관하게 공통 규칙을 따른다.

### flat (소규모: 도메인 1~3개)

```
src/
├── accounts/              ← 도메인 폴더 (복수형)
│   ├── accounts_api.ts
│   └── account_card.tsx
├── payments/
└── shared/                ← 도메인 간 공유 코드 (비대해지면 경고)
tests/
docs/
```

규칙:
- src/ 바로 아래에 도메인 폴더. 중간 폴더 없음.
- 도메인 내 최대 1뎁스 (파일만, 하위 폴더 지양).
- shared/는 2개 이상 도메인이 쓰는 코드만. 1개 도메인만 쓰면 해당 도메인으로 이동.

언제 졸업하나:
- 도메인 4개 이상 → feature-based 전환 검토.

### feature-based (중규모: 도메인 3~5개)

```
src/
├── features/
│   ├── accounts/          ← 도메인 폴더
│   │   ├── components/    ← 도메인 내 하위 분류 (최대 1뎁스)
│   │   ├── hooks/
│   │   └── accounts_api.ts
│   └── payments/
├── shared/                ← 크로스 도메인 유틸, 타입, UI 기반
tests/
docs/
```

규칙:
- features/ 아래에 도메인 폴더.
- 도메인 내 최대 2뎁스 (components/, hooks/ 같은 역할별 하위 허용).
- shared/는 엄격하게 관리. 도메인 로직 금지, 순수 유틸/타입/공통 UI만.

언제 졸업하나:
- 배포 단위가 나뉘어야 할 때 → monorepo 전환 검토.
- 백엔드 레이어 분리가 필요할 때 → layered 전환 검토.

### layered (대규모, 백엔드 중심)

```
src/
├── domain/                ← 비즈니스 엔터티, 규칙
│   ├── accounts/
│   └── payments/
├── application/           ← 유스케이스, 서비스
│   ├── accounts/
│   └── payments/
├── infrastructure/        ← DB, 외부 API, 파일시스템
│   ├── accounts/
│   └── payments/
├── presentation/          ← 컨트롤러, 뷰, DTO
│   ├── accounts/
│   └── payments/
tests/
docs/
```

규칙:
- 1단계 = 레이어, 2단계 = 도메인. 레이어가 도메인보다 상위.
- 의존성 방향: presentation → application → domain ← infrastructure.
- domain/은 외부 의존성 금지 (프레임워크, DB 등 import 불가).
- 레이어 내 도메인 폴더 이름은 전체 레이어에서 동일하게 유지.

### monorepo (다중 배포 단위)

```
packages/
├── web/                   ← 배포 단위 (각각 독립 프로젝트처럼)
│   └── src/
├── api/
│   └── src/
├── shared/                ← 공유 패키지
│   └── src/
```

규칙:
- packages/ 아래 배포 단위별 폴더.
- 각 패키지 내부는 규모에 따라 flat 또는 feature-based 적용.
- shared/는 독립 패키지로 관리. 버전 또는 의존성 명시.
- 패키지 간 순환 의존 금지.

---

## 공통 규칙 (아키텍처 무관)

### 폴더명
- 도메인 폴더: 복수형 snake_case (accounts/, payments/)
- 기능 폴더: 단수형 (config/, test/)
- 그룹핑 목적의 중간 폴더 금지

### 계획 문서 (docs/WIP/)

**SSOT**: `.claude/rules/naming.md` "파일명 — WIP". 요약:

패턴: `{대상폴더}--{abbr}_{slug}.md`
- `{대상폴더}--`: 완료 시 이동할 docs/ 하위 폴더명. `--`는 라우팅 구분자.
- `abbr`: naming.md "도메인 약어" 표의 값 (도메인당 1개)
- `slug`: snake_case 의미명. 주제 자체 (세분화는 `tags:` 프론트매터)
- **날짜 suffix 전면 금지**. 발생 시점은 프론트매터 `created` + git history
- 이동 시 `{대상폴더}--` 접두사가 제거된다.

유효한 접두사: `decisions--`, `guides--`, `incidents--`, `harness--`

예시 (WIP → 이동 후):
- `decisions--hn_auth_stack.md` → `docs/decisions/hn_auth_stack.md`
- `guides--hn_payment_api.md` → `docs/guides/hn_payment_api.md`
- `incidents--hn_token_refresh.md` → `docs/incidents/hn_token_refresh.md`

전역 마스터 문서(도메인 횡단)는 abbr 생략: `{대상폴더}--{slug}.md`.

### 파일명/클래스/함수/메소드

이전 대화에서 합의한 규칙이 있으면 그대로 사용.
없으면 사용자에게 케이스(snake_case/kebab-case 등)와
서픽스 패턴을 확인한 후 naming.md에 기록.

### 도메인 목록

naming.md에 도메인 섹션을 만든다:

확정된 도메인: (확인된 것만)
후보: (경계 불명확, 추후 확정)

## 도메인 추가 시

1. naming.md 도메인 목록에 추가
2. 해당 도메인 폴더 + 타입 파일 껍데기 생성
3. 기존 도메인과 경계가 겹치면 먼저 사용자에게 보고

## 주의
- 위 제안은 기본값이지 강제가 아니다. 사용자의 선택을 우선.
- naming.md는 성장하는 문서다. 처음에 완벽하지 않아도 된다.
- naming.md 업데이트 후 기존 파일과 불일치가 있으면 보고하라.
- "언제 졸업하나"는 참고용 가이드다. 강제 전환이 아니다.
