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

### incidents/ 전용 필드

incidents/ 문서는 다음 필드를 **반드시** 포함한다. 증상이 재발했을 때
키워드로 찾을 수 있어야 하기 때문이다.

```yaml
symptom-keywords:     # 필수. 증상을 유발한 고유명사·식별자
  - <제품/업체/기능명>
  - <엔티티-ID>
```

- tags는 기술 분류(status-transition, auth-error 등). **재발 시 사용자가
  입에 올릴 단어**는 symptom-keywords에 넣는다.
- 미래의 Claude가 "전에 이런 적 있었나?"를 물을 때 grep의 첫 타겟이 된다.
- write-doc 스킬이 incident 생성 시 이 필드가 비면 재질의한다.

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

다음 상황에서 doc-finder 에이전트를 호출하거나, 직접 INDEX.md → clusters/ → 본문 순으로 탐색한다:

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
문서가 많거나 도메인이 불확실하면 doc-finder 에이전트에 위임한다.

### IDE 컨텍스트는 힌트다, 진실이 아니다

`<ide_opened_file>`, `<ide_selection>` 등 IDE가 내려주는 파일 경로는 실제
존재 여부와 무관하다. 직전에 닫힌 파일, 다른 워크스페이스 파일, 미저장
파일도 올 수 있다.

- IDE 경로를 검색 키로 쓰기 전에 **Read 또는 Glob으로 존재 확인**.
- 없으면 그 경로·그 파일명은 **버리고** 사용자 원문 키워드로 재검색.
- IDE 파일명 단어만으로 "없다"고 결론내리지 마라. 그 파일명은 사용자가 친
  키워드가 아닐 수 있다.

### "없습니다"는 3단계 이후에만 가능

사용자 질문에 해당하는 문서가 없다고 말하기 전, 다음 3단계를 모두 거쳐야
한다. 하나라도 생략하면 "없다"고 말하지 마라.

```
1. 파일명 Glob        → Glob "**/*<keyword>*.md"
2. 제목/태그 grep     → Grep "title:.*<keyword>|tags:.*<keyword>" docs/
3. 본문 grep (필수)   → Grep -i "<keyword>" docs/ --include="*.md"
```

사용자 원문에서 **고유명사**(공연명, 아티스트, 업체, ID, 제품명)를 추출해
키워드로 쓴다. IDE가 준 파일명 단어가 아니다.

### 검색 실패 escalation

3단계를 다 돌렸는데 비었으면 바로 "없다"로 끝내지 말고 escalate:

```
3단계 모두 빔
  → doc-finder 에이전트에 위임 (사용자 원문 + 추측 키워드 전달)
    → 에이전트도 빔
      → 사용자에게 키워드/범위 재질의
```

"열심히 찾았는데 없다"를 증명할 책임은 Claude에게 있다. 사용자에게 떠넘기기
전에 위 단계를 다 밟았는지 확인.

## 규칙

### 문서 생성
- 코드 작업과 함께 → implementation 스킬이 docs/WIP/에 계획 문서를 만든다.
- 문서만 단독 생성 → write-doc 스킬이 폴더 판단, 프론트매터, 파일명을 강제한다.
- WIP 파일명: `{대상폴더}--{작업내용}_{YYMMDD}.md`. `--`는 라우팅 태그.
- 대상폴더: decisions, guides, incidents, harness 중 하나.
- 프론트매터 포함 필수. `relates-to`는 작업 중이라 비어도 됨.

### 문서 이동
- 완료/중단된 문서는 docs/WIP/에 남기지 않는다.
- 이동은 commit 스킬이 처리한다. 수동으로 이동하지 마라.
- 이동 시 `{대상폴더}--` 접두사를 제거한다. 최종 파일명은 `{작업내용}_{YYMMDD}.md`.
- 이동 대상은 위 구조에 정의된 폴더만 허용. **새 하위 폴더를 만들지 마라.**
- 이동 시: status → completed/abandoned, updated 갱신, clusters/{domain}.md에 추가

### completed 전환 차단 조건

status를 completed로 전환할 때, 본문에 다음 패턴이 남아 있으면 차단한다.
"증상은 해결했지만 정책·설계가 미결"인 경우를 completed로 묻어버리는 것을
막기 위함이다.

차단 키워드(대소문자 무관): `TODO`, `FIXME`, `후속`, `미결`, `미결정`,
`추후`, `나중에`, `별도로`.

차단되면 두 가지 중 선택:

1. 본문의 미결 항목을 **별도 WIP 문서로 분리** (권장). 원 문서는 completed로
   이동, 새 WIP는 `relates-to: rel: caused-by`로 연결.
2. 해결 완료라면 키워드를 제거하고 재시도.

commit 스킬이 이 조건을 검사한다. 수동으로 completed 전환하지 마라.

### 금지
- docs/ 외의 위치에 문서를 만들지 마라 (README.md, CHANGELOG.md 등 루트 표준 파일 제외).
- docs/ 하위에 임의 폴더를 만들지 마라. 위 구조에 맞는 폴더만 사용.
- 새 폴더가 필요하면 사용자에게 먼저 확인.
- naming.md에 없는 domain을 프론트매터에 쓰지 마라.
