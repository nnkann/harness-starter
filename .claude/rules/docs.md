# Docs 규칙

defends: P7

## 핵심 원칙 — 파일명·tag·domain이 wiki 그래프를 형성

**파일명 → domain → cluster** 체인으로 자동 탐색, **tag**가 cluster 간 간선
역할. `ls docs/**/hn_*`·`grep -r "memory"`·cluster 본문 tag 백링크로 원하는
문서를 찾을 수 있어야 한다.

## 폴더 구조

```
docs/
├── clusters/       ← domain별 노드 인덱스 + tag 간선 (SSOT 진입점)
├── WIP/            ← 작업 중. 파일 있으면 할 일 있다.
├── cps/            ← CPS case 박제 (wave별 1건, cp_{slug}.md)
├── decisions/      ← "왜 X를 선택했나?"
├── guides/         ← "X를 어떻게 하나?"
├── incidents/      ← "X가 왜 깨졌고 어떻게 고쳤나?"
├── harness/        ← 하네스 자체 이력 (승격 로그 등)
└── archived/       ← 중단·대체된 문서
```

폴더 판단: "이 문서를 누가 왜 다시 열까?"
- wave case (C·P·S 박제) → `cps/`
- 새 결정 근거 → `decisions/`
- 같은 작업 방법 → `guides/`
- 비슷한 문제 원인 → `incidents/`
- 하네스 자체 변경 이력 → `harness/`

## 프론트매터 — wiki 그래프 모델

`docs/`는 단순 폴더 인덱스가 아니라 **그래프**. 본문이 흩어져 있어도
frontmatter 필드가 노드·간선 역할로 연결망을 형성. wiki와 같음.

| 구성요소 | 필드 | 역할 |
|---------|------|------|
| **노드 zone** | `domain` | 변경 전파 범위 (harness·meta·cps) |
| **노드 무게** | review 등급 (domain 부가 속성) | 검증 강도 (critical/normal/meta) |
| **간선 (edge)** | `tags` | cluster를 잇는 의미 연결망 — cross-domain |
| **명시적 link** | `relates-to` | 방향성 link (extends·supersedes 등) |

> "그래프 모델"은 **개념 참고**일 뿐 새 도구 도입 아님. 이미 frontmatter에
> 있던 것을 wiki 관점으로 이름 붙인 것.

### 형식

```yaml
---
title: 문서 제목                # 필수
domain: harness                 # 필수. naming.md 도메인 목록에서 선택
problem: [P2, P5]               # 필수 (CPS 인용). 번호만. 단일 P# 또는 list
s: [S2, S6]                     # 필수 (CPS 인용). 번호만
tags: [keyword1, keyword2]      # 선택. 영문 소문자+하이픈+숫자만, 최대 5개
relates-to:                     # 선택
  - path: decisions/other.md
    rel: extends                # extends|caused-by|references|supersedes (4종)
status: completed               # 필수. pending|in-progress|completed|abandoned|sample
created: 2026-04-16             # 필수
updated: 2026-04-16             # 선택
---
```

- **domain**: naming.md "도메인 목록 > 확정"이 SSOT
- **problem·s**: CPS 인용 (아래 "## CPS 인용" SSOT)
- **tags**: 정규식 `^[a-z0-9][a-z0-9-]*[a-z0-9]$`. naming.md "tag 정책" SSOT
- **rel**: 4종만 — `extends`·`caused-by`·`references`·`supersedes`. 새 타입은 스펙 문서 추가 후 사용. (v0.47.5 §C: `implements`·`precedes`·`conflicts-with` 폐기 — 의미 겹침 또는 사용 0)
- **폴더 = 성격, domain = 의미** (이중 분류)

### CPS 면제

`docs/guides/project_kickoff.md`(CPS 자체)는 `problem`·`s` 면제.
pre-check이 면제 처리.

## 하네스 구성요소 메타데이터 (rules·skills·agents)

rules·skills·agents 파일 상단에 선언:

### `defends:` — 규칙 파일 전용

```
defends: P#
```

이 규칙이 지키는 CPS Problem ID. 규칙 파일 본문 2번째 줄(제목 다음)에 선언.
여러 Problem에 걸치면 주된 1개. 해당 Problem 없으면 CPS에 새 P# 등록 후 인용.

### `serves:` — skills·agents 파일 전용

```
serves: S#
```

이 스킬·에이전트가 충족하는 CPS Solution ID. 여러 Solution이면 쉼표 구분.

## CPS 인용 (frontmatter `problem`·`s`)

CPS = `docs/guides/project_kickoff.md`(C 판단 프롬프트) + `docs/cps/cp_{slug}.md`
(wave case 박제). 인용은 **번호만**:

```yaml
problem: P3                       # 단일 P# 또는 list
s: [S2, S6]                       # Solution 번호 list
```

**원칙**:
- 매칭 강제 없음. 자라는 시스템
- 50자 substring 박제 검사 폐기 (2026-05-14)
- pre-check은 P#/S# 번호 존재만 확인 (본문 매칭 안 함)
- Solution 본문 변경은 cascade 영향 — 다음 wave에서 의식적으로 추적

자세히: `docs/decisions/hn_harness_73pct_cut.md` §S-1.

## AC (Acceptance Criteria) 포맷

WIP task 블록의 AC:

```markdown
**Acceptance Criteria**:
- [ ] Goal: <1줄 — 이 작업이 충족하려는 것>
  검증:
    tests: <pytest 명령 또는 "없음">
    실측: <구체 명령·조건 또는 "운용 검증">
- [ ] (충족 기준 1)
- [ ] (충족 기준 2)
```

**필수 필드**: `Goal`·`검증.tests`·`검증.실측` 3개. 누락 시 commit 차단.

**체크박스 형식 강제** (v0.47.4 §S-8): AC 섹션은 반드시 `- [ ]` 또는
`- [x]` 체크박스 형식. 자유 텍스트 AC 금지. pre-check이 체크박스 부재 시 차단.

이유: 결정적 완료 판정 게이트(`docs_ops.py move`의 빈 체크박스 감지)가
작동하려면 체크박스 형식 필수. 자유 텍스트 AC는 "완료/미완료" 신호가 없어
완료 게이트 자체를 우회.

**S# 인용 강제** (v0.47.4 §S-9): frontmatter `s:`의 **각 S# 번호가 AC
섹션 안에 1개 이상 등장** 필수. pre-check이 미인용 S# 있으면 차단.

- AC `Goal` 또는 충족 기준 항목 안에 S# 번호 등장하면 OK
- **substring 본문 인용 금지** (§S-1 함정 회피) — 번호 매칭만
- 작성 시 kickoff `## Solutions` 표 "해결 기준" 컬럼을 SSOT로 참조해 AC
  `검증.실측`이 그 기준에 부합하도록 작성. 단 본문 substring은 박제 X
- 자기 변경 면제: wave가 `kickoff·cps_master·docs/cps/*` staged면 게이트 skip

**P10·S10 사용** (catch-all, **엄격 기준**):
- 박는 조건: P1~P9 각각 검토 후 **어디에도 명확히 안 맞을 때만**
- 부적합 패턴: "잘 모르겠음·귀찮음·빠르게 넘기고 싶음" — 이 경우 멈추고
  P1~P9 재검토. P10은 도피처 아님
- 의심 근거 1줄 박제 의무 (단순 "안 맞음" 금지) + 가장 가까운 P#·S# 후보
  동반 권장 (pre-check이 ℹ️ 안내, 차단 X)
- 혼용 시 본질 신호 희석 — wave 본질이 학습 데이터인데 noise로 변질

### 검증 묶음 — 각 키 의미

| 키 | 값 | 의미 |
|----|----|----|
| `tests` | `pytest -m <marker>` 또는 `pytest <path>` | implementation Phase 완료 직후 자동 실행 |
| `tests` | `없음` | 회귀 가드 불필요 (작성자 선언) |
| `실측` | 구체 명령 또는 조건 | 충족 확인 절차 |
| `실측` | `운용 검증` | 자동 검증 불가, 사용자 1~3 세션 판정 |

AC 검증 자동 실행 위치는 **implementation 종료 단계**. commit 스킬은 사실
게이트 + review 분기만.

### review 호출 정책

- 기본: `/commit --review` — review agent 1회 호출, verdict 강제 없음
- 옵트아웃: `/commit --no-review`
- 보안 게이트: 시크릿 line-confirmed 감지 시 review 강제
- 추세: TDD 강화 기본, review는 보안·아키텍처 결정처럼 테스트로 못 잡는
  영역만 옵트인

### incidents/ 전용

```yaml
symptom-keywords:     # 필수. 증상 유발 고유명사·식별자
  - <제품/업체/기능명>
  - <엔티티-ID>
```

tags는 기술 분류, **재발 시 사용자가 입에 올릴 단어**는 symptom-keywords.

**오염 면제**: `symptom-keywords` 필드만 다운스트림 고유명사 허용.
본문은 placeholder(`<제품명>`) 사용. incident 외 폴더는 면제 없음.

## clusters/

cluster 파일 = domain 노드 인덱스 + tag 간선 인덱스. `docs_ops.py
cluster-update` 자동 생성:

```markdown
## 문서 (domain 멤버)

- decisions/hn_memory.md
- ...

## tag 분포 (간선)

- review (18건) | commit (13건) | hook (8건) | ...

## tag별 문서 (백링크)

### review
- decisions/hn_review_tool_budget.md
- decisions/hn_review_staging_rebalance.md
- ...
```

- **진입점 SSOT**. cluster scan = 본문 분산을 wiki로 잇는 메타 인덱스
- domain 목록 SSOT: `.claude/rules/naming.md` "도메인 목록"
- WIP는 cluster 본문에 별도 섹션 (완료 후 ## 문서로 이동)
- commit 스킬이 문서 이동 시 cluster 갱신
- meta cluster는 sample·template zone — 멤버 적음이 정상

## 문서 탐색

### 기본 경로

```
1. cluster 진입점 (권장)   → cat docs/clusters/{domain}.md
                            (## 문서 + ## tag별 문서 둘 다)
2. 도메인 + abbr 통과     → ls docs/**/*{abbr}_*
3. 주제 키워드 있으면     → ls docs/**/*{keyword}*
4. tags 세분화 필요       → grep -l "tags:.*review" docs/
```

cluster scan(1번)으로 시작 권장 — domain 멤버 + tag 백링크 한 번에 발견.

### 깊은 탐색 (1차 실패 시)

Glob → 제목/tag grep → 본문 grep 순. 3단계 모두 거친 뒤에만 "없다" 결론.
상세: `docs/guides/hn_doc_search_protocol.md`

## SSOT 우선 + 분리 판단

`docs/` 하위 파일 만들기 직전이면 예외 없이 아래 절차 적용.

### 3단계 탐색 (생략 금지)

1. **cluster 스캔** — `docs/clusters/{domain}.md` Read. 제목·tag로 후보 선별
2. **키워드 grep** — `docs/**/*.md` 본문 grep. hit 파일 전부 열거
3. **후보 Read** — cluster·grep hit된 후보 본문 Read

hit 0건만이 "새로 만들어도 된다"의 전제. hit 있으면 두 질문:

1. SSOT가 이미 있는가? → 있으면 갱신
2. 분리가 정말 필요한가? → 별도 실행·검증 / ADR급 독립 참조 / 진행 상태
   보존 필요할 때만

**기본값은 기존 SSOT 갱신**. 새 파일은 분리 근거가 있을 때만.

**완료된 문서 재개**: `docs_ops.py reopen`. 같은 내용을 새 WIP로 복제 금지.

### 실패 모드 (재실행)

- cluster만 봤다 (grep·본문 Read 안 함)
- 제목 불일치로 "다른 주제" 단정
- "새로 만들까, 갱신할까?" 동격 제시
- completed라 새로 만든다고 판단

## 파일명 (SSOT: naming.md)

```
{abbr}_{slug}.md                  모든 폴더
{slug}.md                         전역 마스터 문서 (abbr 없음)
```

- `abbr`: `naming.md` "도메인 약어" 표의 값
- `slug`: snake_case 의미명
- **날짜 suffix 전면 금지**. 발생 시점은 `created` + git history

### 주제 분할 규칙

- 독립 문제·결정 근거가 다르면 **분할**
- 같은 결정의 후속·측정은 **본문 누적** (`## 변경 이력` 섹션)
- 완전 superseded만 `archived/` + 새 파일

## 문서 생성

생성 흐름 (write-doc·implementation 스킬이 강제):

```
1. 폴더 결정 (decisions / guides / incidents / harness / cps)
2. domain + abbr 조회 (naming.md)
3. 기존 문서 탐색 (같은 주제 있으면 갱신 유도)
4. 파일명: {abbr}_{slug}.md
5. 프론트매터: title / domain / problem / s / tags / status / created
6. 본문 작성
```

- 코드 작업과 함께 → implementation 스킬
- 문서만 단독 → write-doc 스킬

## 문서 이동

- 완료/중단 문서는 docs/WIP/에 남기지 않음. 이동은 commit 스킬
- 이동 시 status → completed/abandoned, updated 갱신, cluster 갱신
- 위 구조 폴더만 허용. **새 하위 폴더 만들지 마라**

### 완료 문서 재개

```
python .claude/scripts/docs_ops.py reopen docs/{폴더}/{abbr}_{slug}.md
```

(status → in-progress, WIP 이동, updated 갱신, cluster dead link 제거 일괄)

## completed 전환 차단

본문에 다음 **명령형 패턴**이 있으면 차단:

- `TODO:` / `FIXME:` (콜론 포함, 대소문자 무관)
- 빈 체크박스 `- [ ]` 또는 `* [ ]`
- 섹션 헤더 미결 키워드: `## 후속`, `## 미결`, `### 추후` 등
  (`후속`/`미결`/`미결정`/`추후`/`나중에`/`별도로`가 헤더 시작에 올 때)

> **회고적 서술은 차단 안 함.** "Task X 후속 처리 완료" 같은 회고 표현은
> 통과. 같은 라인에 ✅·완료·처리됨·done이 있으면 자동 면제.

> **코드블록 안 면제.** ``` ``` `` 또는 `~~~`로 감싼 코드블록 안의 빈
> 체크박스·TODO·미결 헤더는 차단 면제.

차단 시:
1. 미결 항목을 별도 WIP로 분리. 새 WIP는 `rel: caused-by` 연결
2. 해결 완료라면 빈 체크박스를 [x]로 채우거나 TODO/FIXME 줄 제거 후 재시도

## 금지

- docs/ 외 위치 문서 생성 (README/CHANGELOG 등 루트 표준 파일 제외)
- docs/ 하위 임의 폴더 생성
- naming.md에 없는 domain·abbr 사용
- 파일명 날짜 suffix
- 주제 여럿을 한 파일에 뭉치기 (grep 실패 → 탐색 체인 깨짐)
- tags 정규식 위반 (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`). 한글 tag 금지
