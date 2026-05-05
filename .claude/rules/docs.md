# Docs 규칙

defends: P7

## 핵심 원칙 — 파일명이 곧 인덱스

**파일명 → 도메인 → cluster** 체인으로 자동 탐색된다.
`ls docs/**/hn_*`·`grep -r "memory"`만으로 원하는 문서를 찾을 수 있어야 한다.

## 폴더 구조

```
docs/
├── clusters/       ← 도메인별 인덱스 (SSOT — 진입점)
├── WIP/            ← 작업 중. 파일 있으면 할 일 있다.
├── decisions/      ← "왜 X를 선택했나?"
├── guides/         ← "X를 어떻게 하나?"
├── incidents/      ← "X가 왜 깨졌고 어떻게 고쳤나?"
├── harness/        ← 하네스 자체 이력 (승격 로그 등)
└── archived/       ← 중단·대체된 문서
```

폴더 판단: "이 문서를 누가 왜 다시 열까?"
- 새 결정 근거 → `decisions/`
- 같은 작업 방법 → `guides/`
- 비슷한 문제 원인 → `incidents/`
- 하네스 자체 변경 이력 → `harness/`

## 프론트매터

```yaml
---
title: 문서 제목                # 필수
domain: harness                 # 필수. naming.md 도메인 목록에서 선택
problem: P2                     # 필수 (CPS 인용). project_kickoff.md의 Problem ID
solution-ref:                   # 필수 (CPS 인용, list)
  - S2 — "review tool call 평균 ≤4회"
tags: [keyword1, keyword2]      # 선택. 최대 5개
relates-to:                     # 선택
  - path: decisions/other.md
    rel: extends                # extends|caused-by|implements|supersedes|references|conflicts-with
status: completed               # 필수. pending|in-progress|completed|abandoned|sample
created: 2026-04-16             # 필수
updated: 2026-04-16             # 선택
---
```

- **domain**: naming.md "도메인 목록 > 확정"이 SSOT
- **problem·solution-ref**: CPS 인용 (아래 "## CPS 인용" 섹션 SSOT)
- **rel**: 6종만. 새 타입은 스펙 문서 추가 후 사용
- **폴더 = 성격, domain = 의미** (이중 분류)

### CPS 면제

`docs/guides/project_kickoff.md`(CPS 자체)는 `problem`·`solution-ref` 면제.
CPS는 마스터이므로 자기 자신 인용 무의미. pre-check이 면제.

## 하네스 구성요소 메타데이터 (rules·skills·agents 파일 상단)

rules·skills·agents 파일 상단에 선언하는 관계 필드. **HARNESS_MAP.md의 양방향 관계 지도와 정합**해야 한다.

### `defends:` — 규칙 파일 전용

```
defends: P#
```

이 규칙이 지키는 CPS Problem ID. 규칙 파일 본문 2번째 줄(제목 다음)에 선언.

**매핑 판단 트리 (새 규칙 추가 시)**:

```
1. 이 규칙이 없으면 어떤 증상이 반복되는가?
   → 그 증상이 CPS의 어느 Problem 정의와 일치하는가?
   → 일치하면 → defends: P#

2. 여러 Problem에 걸치면?
   → 주된 Problem 1개만. 부수는 본문에서 언급.

3. 어느 Problem에도 해당 없으면?
   → CPS에 새 Problem 등록 후 defends: P# (docs.md "CPS 변경 권한" 참조)
```

**Layer 배치 기준** (HARNESS_MAP.md Rules 섹션):
- Layer 0: 모든 행동에 적용되는 원칙 (no-speculation, anti-defer)
- Layer 1: 특정 흐름에 적용되는 절차 (bug-interrupt, self-verify 등)
- Layer 2: 특정 도메인 영역에 적용 (hooks, coding, pipeline-design)
- Layer 3: 시스템 유지 관리 (docs, naming, memory, external-experts)

### `serves:` — skills·agents 파일 전용

```
serves: S#
```

이 스킬·에이전트가 충족하는 CPS Solution ID. 파일 frontmatter에 선언.

**매핑 판단 트리**:

```
1. 이 도구가 해결하는 Problem은 무엇인가?
   → 그 Problem의 Solution이 S#
   → serves: S#

2. 여러 Solution에 걸치면?
   → 쉼표 구분: serves: S1, S6
```

### `enforced-by:` — rules 파일 전용 (HARNESS_MAP.md 기록용)

규칙을 실제로 실행·감지하는 도구. rules 파일 본문에 직접 선언하지 않고
**HARNESS_MAP.md Rules 섹션의 enforced-by 컬럼**에만 기록한다.

규칙 파일 본문에 "이 규칙을 누가 enforces하는가"가 명시됐으면 HARNESS_MAP.md와 정합 확인.

## CPS 인용 (frontmatter `problem`·`solution-ref`)

CPS = `docs/guides/project_kickoff.md`가 마스터. 다른 모든 문서가 단방향 인용.
CPS는 누구도 인용 안 함.

### `problem:` 형식

단일 값. CPS Problem ID (예: `P1`·`P2`·...). 작업 의도가 다루는 Problem 1개.

작업이 여러 Problem 다루면 **주된 Problem 1개만** 명시. 부수 Problem은 본문에서 언급.

### `solution-ref:` 형식 (list)

작업이 충족하려는 Solution 충족 기준을 인용. **list 형식 필수** — 한 문서에 여러 task가 있는 경우 task별 인용 분리.

```yaml
solution-ref:
  - S2 — "<원문 그대로 또는 50자 이내 핵심 substring>"
  - S2 — "<다른 충족 기준>"
  - S6 — "<여러 Solution 동시 다룰 때>"
```

**인용 규칙**:

1. **50자 이내**: 원문 그대로 인용
   ```yaml
   - S2 — "review tool call 평균 ≤4회"
   ```

2. **50자 초과**: `(부분)` 마커 강제 + 핵심 substring만
   ```yaml
   - S2 — "review tool call 평균 ≤4회 (micro: 0~2, standard: 1~4, deep: 3~6) (부분)"
   ```

3. **부분 마커 어휘**: `(부분)` 단일 keyword. `(요약)`·`(일부)` 사용 금지.

### Normalize 규칙 (인용 비교 시)

pre-check이 박제 감지할 때 인용을 CPS 본문과 비교 — normalize 후 substring 매칭:

- 공백 통일: 연속 공백 → 단일 공백
- 줄바꿈 제거: `\n` → 공백
- backtick 제거: `` ` `` → ""

### 박제 감지 (pre-check 책임)

commit 시점에 staged 문서의 frontmatter `solution-ref` 인용을 CPS 본문과 grep:

- 인용 (50자 이내, 부분 마커 없음) → 원문 그대로 매칭. 미매칭 → 경고
- 인용 (50자 초과, `(부분)` 마커) → substring 매칭. 미매칭 → 경고
- 차단 아님 — Solution 본문이 의도적으로 진화했을 수 있음. 작성자 판단

### CPS 변경 권한

| 변경 | 권한 |
|------|------|
| Problem 추가/병합 | Claude 단독 (implementation Step 0 또는 BIT Q3 경로) |
| Solution 충족 기준 갱신 | 프로젝트 owner 승인 필수 (cascade 영향 큼) |
| Solution 메커니즘 자체 변경 | 프로젝트 owner 승인 필수 |

Problem 추가는 버그·이슈의 존재라는 **사실 기록**이다. BIT Q1/Q2/Q3 또는
implementation Step 0에서 판단 근거가 이미 완료된 상태이므로 승인이 흐름을
끊을 이유가 없다. Solution 정의/변경만 cascade 영향이 있어 owner 개입이 필요하다.

`프로젝트 owner`: 본 프로젝트는 nnkann. 다운스트림은 자체 정의 (CLAUDE.md 또는 init).

## AC (Acceptance Criteria) 포맷 — Goal + 검증 묶음 SSOT

WIP task 블록의 AC는 다음 통합 형식:

```markdown
**Acceptance Criteria**:
- [ ] Goal: <1줄 — 이 작업이 충족하려는 것>
  검증:
    review: skip | self | review | review-deep
    tests: <pytest 명령 또는 "없음">
    실측: <구체 명령·조건 또는 "없음">
- [ ] (충족 기준 1)
- [ ] (충족 기준 2)
```

**필수 필드**: `Goal`·`검증.review`·`검증.tests`·`검증.실측` 4개. 누락 시 commit 차단.

### 검증 묶음 — 각 키 의미

| 키 | 값 | 의미 |
|----|----|----|
| `review` | `skip` | review 호출 안 함. 작성자 자가 보고 |
| `review` | `self` | review 호출. AC 직접 체크만 (tool call 0~2) |
| `review` | `review` | review 호출. AC + 계약·스코프 (tool call 1~4) |
| `review` | `review-deep` | review 호출. AC + 2축 + Solution 충족 기준 회귀 (tool call 3~5) |
| `tests` | `pytest -m <marker>` 또는 `pytest <path>` | 자동 실행. 화이트리스트(pytest·bash -n·python -m·grep) 외는 가이드만 |
| `tests` | `없음` | 회귀 가드 불필요 (작성자 선언) |
| `실측` | 구체 명령 또는 조건 | 충족 확인 절차 |
| `실측` | `없음` | 자동 검증 불가, 운용 검증만 |

### 폐기된 마커 (호환성 — 코드에서 더 이상 읽지 않음)

- WIP task `> kind:` 마커
- AC `영향 범위:` 항목

기존 문서에 남아 있어도 동작 무관. 신규 문서는 위 통합 형식만.

### 작성자 거짓 선언 대책

`검증.review: skip` 마킹했는데 회귀 발생:
- commit log에 `🔍 review: skip | declared-by: author` 기록
- eval --deep이 사후 audit
- 반복 시 incident → rules에 "이 영역 review 필수" 추가

자가 보고 시스템. 보안 게이트(시크릿 line-confirmed)만 작성자 선언 무시.

### incidents/ 전용

```yaml
symptom-keywords:     # 필수. 증상 유발 고유명사·식별자
  - <제품/업체/기능명>
  - <엔티티-ID>
```

tags는 기술 분류, **재발 시 사용자가 입에 올릴 단어**는 symptom-keywords. write-doc 스킬이 빈 필드면 재질의.

**오염 면제 범위**: `symptom-keywords` 필드 자체만 다운스트림 고유명사 허용.
본문은 placeholder(`<제품명>` 등) 사용. incident 외 폴더는 면제 없음.
관련: `docs/incidents/hn_downstream_name_leak.md`

## clusters/

```
탐색: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

- clusters/{domain}.md: 도메인별 문서 목록 + 관계 맵. **진입점 SSOT**.
- 도메인 목록 SSOT: `.claude/rules/naming.md` "도메인 목록"
- WIP는 clusters 미포함 (완료 후 이동 시 추가)
- commit 스킬이 문서 이동 시 clusters 갱신
- `docs_ops.py`가 파일명 abbr을 파싱해 cluster를 자동 결정 (`naming.md` "Cluster 자동 매핑" SSOT)

## 문서 탐색

### 기본 경로 (cluster 1차 — completed + WIP 단일 진입점)

```
1. cluster 진입점 (권장)   → cat docs/clusters/{domain}.md
                            (`## 문서` + `## 진행 중 (WIP)` 섹션 모두 포함)
2. 도메인 + 라우팅 태그 통과 → ls docs/**/*{abbr}_*  (양쪽 wildcard 필수)
                            (단순 `{abbr}_*`는 WIP 라우팅 태그 `decisions--`에 막힘)
3. 주제 키워드 있으면        → ls docs/**/*{keyword}* (예: *memory*, *staging*)
4. 위 둘 결합 가능           → ls docs/**/*hn_*memory*
5. tags 세분화 필요         → grep -l "tags:.*skill" docs/
```

cluster scan(1번)으로 시작하면 completed + 진행 중 WIP를 한 번에 발견.
파일 직접 glob(2번)이 필요할 땐 양쪽 wildcard 필수 — 라우팅 태그 통과
규칙은 `naming.md` "Cluster 자동 매핑 — 직교 파싱 규칙" 참조.

### 깊은 탐색 (1차 실패 시)

Glob → 제목/태그 grep → 본문 grep 순으로. 3단계 모두 거친 뒤에만 "없다" 결론.
상세: `docs/guides/hn_doc_search_protocol.md`

## SSOT 우선 + 분리 판단 (단순 지표 금지)

`docs/` 하위 파일을 만들기 직전이면 예외 없이 아래 절차 적용.

### 3단계 탐색 (생략 금지)

1. **cluster 스캔** — `docs/clusters/{domain}.md` Read. 제목·tags로
   후보 선별
2. **키워드 grep** — 요청 원문에서 핵심 개념어 2~3개 추출, `docs/**/*.md`
   본문 grep. hit 파일 전부 열거
3. **후보 Read** — cluster·grep hit된 후보는 본문 Read. 제목만 보고
   "다른 주제" 단정 금지

hit 0건만이 "새로 만들어도 된다"의 전제. hit 있으면 아래 두 질문으로.

### 두 질문

1. **SSOT가 이미 있는가?** — 있으면 갱신 (필요 시 재개). 없으면 신규 생성.
2. **분리가 정말 필요한가?**

### 실패 모드 (이 중 하나면 탐색 재실행)

- cluster만 봤다 (grep·본문 Read 안 함)
- 제목 불일치로 "다른 주제" 단정
- "새로 만들까, 갱신할까?" 동격 제시
- completed라 새로 만든다고 판단
- "일단 새 WIP 쓰고 나중에 병합"

**기본값은 기존 SSOT 갱신**. 새 파일은 분리 근거가 있을 때만.

**분리 기준**: 별도 실행·검증 필요 / ADR급 독립 참조 가치 / 진행 상태 보존 필요.
그 외는 기존 SSOT 갱신이 기본. "파일 수" 같은 단순 지표로 분기 금지.

**완료된 문서 재개**: `docs/X/` → `docs/WIP/` 되돌린 뒤 `status: completed` → `in-progress`.
같은 내용을 새 WIP로 복제하지 마라.

## 파일명 (SSOT: naming.md "파일명 — 문서" 섹션)

요약:
```
{abbr}_{slug}.md                  모든 폴더 (decisions/guides/harness/incidents)
{slug}.md                         전역 마스터 문서 (abbr 없음, 도메인 횡단)
```

- `abbr`: `naming.md` "도메인 약어" 표의 값
- `slug`: snake_case 의미명. 세분화는 `tags:` 프론트매터로
- **날짜 suffix 전면 금지**. 발생 시점은 `created` + git history. 전환점은 `## 변경 이력` 섹션
- 전역 마스터 vs 단일 도메인 마스터 기준: `naming.md` 참조

### 주제 분할 규칙

- 독립 문제·결정 근거가 다르면 **분할**
- 같은 결정의 후속·측정은 **본문 누적** (`## 변경 이력` 섹션)
- 완전 superseded만 `archived/` + 새 파일

## 문서 생성

생성 흐름 (write-doc·implementation 스킬이 강제):

```
1. 폴더 결정 (decisions / guides / incidents / harness)
2. domain + abbr 조회 (naming.md) — abbr 누락 시 사용자 확인 + 표 갱신
3. 기존 문서 탐색 (같은 주제 있으면 갱신 유도)
4. 파일명: {대상폴더}--{abbr}_{slug}.md
5. 프론트매터: title / domain / tags / status / created
6. 본문 작성
```

- 코드 작업과 함께 → implementation 스킬
- 문서만 단독 → write-doc 스킬
- `--`는 라우팅 태그. commit 스킬이 이동 시 제거

## 문서 이동

- 완료/중단 문서는 docs/WIP/에 남기지 않음. 이동은 commit 스킬. 수동 이동 금지
- 이동 시 `{대상폴더}--` 접두사 제거, status → completed/abandoned, updated 갱신, cluster 추가
- 위 구조 폴더만 허용. **새 하위 폴더 만들지 마라**

### 완료 문서 재개 (역방향 이동)

1. `python .claude/scripts/docs_ops.py reopen docs/{폴더}/{abbr}_{slug}.md`
   (status → in-progress, WIP 이동, updated 갱신, cluster dead link 제거를 한 번에 처리)
2. 완료 시 commit 스킬이 원래 폴더로 이동

## completed 전환 차단

본문에 다음 **명령형 패턴**이 있으면 차단:

- `TODO:` / `FIXME:` (콜론 포함, 대소문자 무관)
- 빈 체크박스 `- [ ]` 또는 `* [ ]`
- 섹션 헤더의 미결 키워드: `## 후속`, `## 미결`, `### 추후` 등
  (`후속`/`미결`/`미결정`/`추후`/`나중에`/`별도로`가 헤더 시작에 올 때)

> **회고적 서술은 차단 안 함.** 본문에 "Task X 후속 처리 완료" 같은
> 회고 표현이 있어도 통과. 차단 대상은 "지금 미결 항목이 남아 있다"는
> 명령형 신호만. 같은 라인에 ✅·완료·처리됨·done이 있으면 자동 면제.

> **코드블록 안 면제.** ``` ``` `` 또는 `~~~`로 감싼 코드블록 안의 빈 체크박스·
> TODO·미결 헤더는 진짜 미완료가 아니라 포맷 예시·문법 설명이므로 차단 면제.

차단 시 선택:
1. 미결 항목을 별도 WIP로 분리. 원본 completed 이동, 새 WIP는 `rel: caused-by` 연결
2. 해결 완료라면 빈 체크박스를 [x]로 채우거나 TODO/FIXME 줄 제거 후 재시도

commit 스킬이 검사. 수동 completed 전환 금지.

## 금지

- docs/ 외 위치 문서 생성 (README/CHANGELOG 등 루트 표준 파일 제외)
- docs/ 하위 임의 폴더 생성 (위 구조만 허용)
- 새 폴더가 필요하면 사용자에게 먼저 확인
- naming.md에 없는 domain 사용
- naming.md "도메인 약어" 표에 없는 abbr 사용 (abbr 먼저 등록)
- 파일명 날짜 suffix (incidents 포함). 발생 시점은 프론트매터 `created`
- 주제 여럿을 한 파일에 뭉치기 (grep 실패 → 탐색 체인 깨짐)
