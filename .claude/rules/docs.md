# Docs 규칙

## 폴더 구조

```
docs/
├── INDEX.md        ← 도메인 목록 + 진입 포인터 (경량)
├── clusters/       ← 도메인별 상세 인덱스 (문서 목록 + 관계 맵)
├── WIP/            ← 작업 중. 여기 파일 있으면 할 일 있다.
├── decisions/      ← 결정과 그 근거. "왜 X를 선택했나?"
├── guides/         ← 방법과 패턴. "X를 어떻게 하나?"
├── incidents/      ← 문제와 해결. "X가 왜 깨졌고 어떻게 고쳤나?"
├── harness/        ← 하네스 자체 이력 (승격 로그 등)
└── archived/       ← 중단, 참조 불필요, 대체된 문서
```

### 폴더 판단 기준

| 폴더 | 핵심 질문 | 전형적 내용 | 예시 |
|------|----------|------------|------|
| `decisions/` | "왜 이렇게 했나?" | 기술 선택, 아키텍처 결정, 트레이드오프, CPS | 스택 선택, DB 마이그레이션 결정, 설계 변경 |
| `guides/` | "어떻게 하나?" | 구현 패턴, 셋업 절차, 사용 가이드 | 업그레이드 전파 방법, API 사용법, 배포 절차 |
| `incidents/` | "무엇이 왜 깨졌나?" | 버그 원인, 장애 분석, 회고 | 인증 토큰 만료 버그, 배포 실패 원인 |
| `harness/` | 하네스 자체 변경 | 승격/강등 로그, 하네스 개선 이력 | 규칙 승격, 스크립트 변경 이력 |
| `archived/` | 더 이상 유효하지 않음 | 중단된 작업, 대체된 결정 | — |

**모호할 때**: "이 문서를 누가 왜 다시 열까?"로 판단.
- 새 결정을 내릴 때 근거를 찾으러 → `decisions/`
- 같은 작업을 다시 할 때 방법을 찾으러 → `guides/`
- 비슷한 문제가 재발했을 때 원인을 찾으러 → `incidents/`

## 프론트매터

모든 docs/ 문서는 YAML 프론트매터 필수.

```yaml
---
title: 문서 제목                      # 필수
domain: harness                       # 필수. naming.md 도메인 목록에서 선택
tags: [keyword1, keyword2]            # 선택. 최대 5개
relates-to:                           # 선택
  - path: decisions/other_doc.md
    rel: extends                      # extends|caused-by|implements|supersedes|references|conflicts-with
status: completed                     # 필수. pending|in-progress|completed|abandoned|sample
created: 2026-04-16                   # 필수
updated: 2026-04-16                   # 선택
---
```

- **domain**: naming.md "도메인 목록 > 확정"이 single source of truth. 없는 domain은 사용자에게 확인
- **relates-to**: rel은 6종만 허용. 새 타입은 스펙 문서에 추가 후 사용
- **폴더 = 문서의 성격, domain = 문서의 의미**. 이중 분류

## INDEX.md + clusters/

**INDEX.md**는 도메인 목록과 진입 포인터만 유지한다 (경량, 고정 크기).
**clusters/{domain}.md**에 해당 도메인의 문서 목록 + 관계 맵을 유지한다.

```
탐색 흐름:
INDEX.md (어떤 도메인?) → clusters/해당.md (어떤 문서?) → 본문 Read
```

- Claude는 문서 탐색이 필요할 때 INDEX.md를 먼저 읽고, 관련 domain의 cluster 파일로 진입
- commit 스킬이 문서 이동 시 해당 cluster 파일 + INDEX.md 문서 수 갱신
- WIP 문서는 INDEX.md/clusters에 포함하지 않음 (완료 후 이동 시 추가)

## 문서 탐색

### 언제 탐색하는가

다음 상황에서 docs-lookup 에이전트를 호출하거나, 직접 INDEX.md → clusters/ → 본문 순으로 탐색한다:

| 트리거 | 예시 |
|--------|------|
| 사용자가 "왜 이렇게 했지?" 류의 질문 | "왜 Redis를 선택했어?", "이 설계의 근거가 뭐야?" |
| 사용자가 "어떻게 하지?" 류의 질문 | "배포는 어떻게 해?", "업그레이드 절차가 뭐야?" |
| 사용자가 "전에 이런 적 있었나?" 류의 질문 | "비슷한 버그 있었어?", "이거 해본 적 있어?" |
| 새 작업 시작 전 맥락 파악 | implementation 스킬 Step 0에서 관련 문서 확인 |
| 결정이 필요할 때 선례 확인 | 기술 선택, 아키텍처 변경 전 |

### 탐색하지 않는 경우

- 코드 수정만 하는 단순 작업 (타이포 수정, 변수명 변경 등)
- 사용자가 이미 구체적인 파일을 지정한 경우
- git log로 충분한 질문 (최근 변경 이력 등)

### 탐색 절차

```
1. docs/INDEX.md 읽기 → 관련 도메인 식별
2. clusters/{domain}.md 읽기 → 관련 문서 + 관계 맵 확인
3. 관련 문서 본문 Read (보통 1~3개)
4. relates-to 포인터로 연관 문서 1홉 추가 탐색 (필요 시)
```

문서가 10개 이하면 직접 탐색해도 충분하다.
문서가 많거나 도메인이 불확실하면 docs-lookup 에이전트에 위임한다.

## 규칙

### 문서 생성
- 작업 시작 전 docs/WIP/에 문서를 먼저 만든다 (implementation 스킬 참조).
- WIP 파일명: `{대상폴더}--{작업내용}_{YYMMDD}.md`. `--`는 라우팅 태그.
- 대상폴더: decisions, guides, incidents, harness 중 하나.
- 프론트매터 포함 필수. `relates-to`는 작업 중이라 비어도 됨.

### 문서 이동
- 완료/중단된 문서는 docs/WIP/에 남기지 않는다.
- 이동은 commit 스킬이 처리한다. 수동으로 이동하지 마라.
- 이동 시 `{대상폴더}--` 접두사를 제거한다. 최종 파일명은 `{작업내용}_{YYMMDD}.md`.
- 이동 대상은 위 구조에 정의된 폴더만 허용. **새 하위 폴더를 만들지 마라.**
- 이동 시: status → completed/abandoned, updated 갱신, clusters/{domain}.md에 추가

### 금지
- docs/ 외의 위치에 문서를 만들지 마라 (README.md, CHANGELOG.md 등 루트 표준 파일 제외).
- docs/ 하위에 임의 폴더를 만들지 마라. 위 구조에 맞는 폴더만 사용.
- 새 폴더가 필요하면 사용자에게 먼저 확인.
- naming.md에 없는 domain을 프론트매터에 쓰지 마라.
