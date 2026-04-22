# Docs 규칙

## 핵심 원칙 — 파일명이 곧 인덱스

문서 시스템은 **파일명 → 도메인 → cluster** 체인으로 자동 탐색된다.
별도 인덱스 파일(과거 `INDEX.md`) 없이 **파일명 규약 + abbr 표 + cluster
자동 매핑**으로 진입점을 대체한다.

탐색 공식:
```
파일명 prefix (abbr)    →  naming.md "도메인 약어" 표  →  domain
파일명 slug             →  주제 식별 (grep 대상)
프론트매터 tags         →  세분화 분류 (skill·agent·rule 등)
clusters/{domain}.md    →  도메인 진입점 (`docs-ops.sh`가 자동 갱신)
```

따라서 `ls docs/**/hn_*`·`grep -r "memory"`만으로 원하는 문서를 찾을 수
있어야 하며, 그렇지 못하면 파일명·약어 등록·cluster 중 어딘가가 규칙
위반 상태다. 이 원칙을 유지하기 위한 구체 규칙이 아래에 있다.

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
- **rel**: 6종만. 새 타입은 스펙 문서 추가 후 사용
- **폴더 = 성격, domain = 의미** (이중 분류)

### WIP task 블록 `kind:` 마커 (선택, 커밋 분리용)

WIP 문서 내 각 task 블록(`### N.` 또는 `### #N.` 헤더)의 바로 다음 줄에
다음 한 줄 선언을 추가할 수 있다. 없으면 기본 `feature`.

```markdown
### 12. pre-check relates-to 확장
> kind: bug

**현 상태**: ...
```

- **kind 값**: `bug`·`feature`·`refactor`·`docs`·`chore`
- 용도: `task-groups.sh`가 staged 파일을 WIP 단위로 묶은 뒤, kind 별로
  서브 그룹화. `bug`는 별도 커밋으로 분리되어 나중에 `git log --grep=fix`
  로 추적 용이
- audit·decisions 문서 내 task 전부에 마커를 붙일 필요는 없음. 성격이
  명확히 다른 task에만 선택적으로 부착

### incidents/ 전용

```yaml
symptom-keywords:     # 필수. 증상 유발 고유명사·식별자
  - <제품/업체/기능명>
  - <엔티티-ID>
```

tags는 기술 분류, **재발 시 사용자가 입에 올릴 단어**는 symptom-keywords.
미래의 Claude가 "전에 이런 적 있었나?"의 grep 첫 타겟. write-doc 스킬이
incident 생성 시 빈 필드면 재질의.

**오염 면제 범위 (좁게 해석)**:
- `symptom-keywords` **필드 자체만** 다운스트림 고유명사 허용 (검색 키
  목적).
- **본문에는 placeholder 사용**: `<제품명>`·`<업체명>`·`<엔티티-ID>` 등.
  사고 인용이 불가피하면 주석으로 근거 명시.
- incident 외 폴더(`archived/`·`harness/`·`guides/`·`decisions/`)는 **면제
  없음**. 다운스트림 실명 노출 시 review가 [주의] 이상으로 지적.
- 본 리포가 public이면 history 재작성 불가하므로 처음부터 placeholder
  필수. 관련 incident: `docs/incidents/hn_downstream_name_leak.md`.

## clusters/

```
탐색: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

- clusters/{domain}.md: 도메인별 문서 목록 + 관계 맵. **진입점 SSOT**.
- 도메인 목록은 `.claude/rules/naming.md`의 "도메인 목록"이 유일한 SSOT.
  (INDEX.md는 2026-04-20 폐기 — 도메인 2개 구조에서 진입 포인터 역할이
  무의미해 관리 드리프트만 발생. 자세한 근거는 `docs/harness/hn_index_md_removal.md`)
- WIP는 clusters 미포함 (완료 후 이동 시 추가)
- commit 스킬이 문서 이동 시 clusters만 갱신

### 자동 매핑 (파일명 abbr → cluster)

`docs-ops.sh`가 파일명을 파싱해 cluster를 자동 결정한다. SSOT는
`naming.md` "Cluster 자동 매핑" 섹션. 요약:

- 파일명에 등록된 abbr이 있으면 → 그 도메인 cluster에 등록
  (불투명 prefix·라우팅 태그 통과, 여러 abbr 있으면 첫 매치)
- abbr 없는 전역 마스터 (`project_kickoff.md`·`MIGRATIONS.md` 등) →
  프론트매터 `domain:`으로 폴백
- 약어 누락·중복은 `docs-ops.sh validate`가 감지

## 문서 탐색

### 기본 경로 (파일명·cluster 1차)

```
1. 도메인 짐작되면        → ls docs/**/{abbr}_*    (예: hn_*)
2. 주제 키워드 있으면      → ls docs/**/*{keyword}* (예: *memory*, *staging*)
3. 위 둘 결합 가능         → ls docs/**/hn_*memory*
4. cluster 진입점         → cat docs/clusters/{domain}.md
5. tags 세분화 필요       → grep -l "tags:.*skill" docs/
```

파일명이 규칙을 따르면 1~4로 끝난다.

### 깊은 탐색 (1차 실패 시)

고유명사·사용자 원문 키워드가 파일명에 안 들어가는 경우가 있다. 이럴
때는 `docs/guides/hn_doc_search_protocol.md`의 절차:
- 사용자 원문 고유명사로 Glob
- 제목/태그 grep
- 본문 grep
- 3단계 모두 거친 뒤에만 "없다" 결론

IDE 컨텍스트는 힌트일 뿐, 사용자 원문 기준으로 검색한다.

## SSOT 우선 + 분리 판단 (단순 지표 금지)

새 문서·WIP 생성 전에 **항상** 아래 절차를 거친다. 스킬 발동 여부 무관
— Write tool로 `docs/` 하위 파일을 만들기 직전이면 예외 없이 적용.

### 3단계 탐색 (생략 금지)

1. **cluster 스캔** — `docs/clusters/{domain}.md` Read. 제목·tags로
   후보 선별
2. **키워드 grep** — 요청 원문에서 핵심 개념어 2~3개 추출, `docs/**/*.md`
   본문 grep. hit 파일 전부 열거
3. **후보 Read** — cluster·grep hit된 후보는 본문 Read. 제목만 보고
   "다른 주제" 단정 금지

hit 0건만이 "새로 만들어도 된다"의 전제. hit 있으면 아래 두 질문으로.

### 두 질문

1. **이 결정·계획이 기록될 SSOT가 이미 있는가?**
   - 있으면 거기를 갱신 (필요 시 `status: completed` → `in-progress` 재개)
   - 없으면 새로 만들되, 다른 문서에 같은 내용이 생기지 않도록
2. **분리가 정말 필요한가? (판단)**

### 실패 모드 체크리스트

아래 중 하나라도 해당하면 탐색이 부실한 것. 처음부터 다시:

- [ ] cluster만 봤다 (grep·본문 Read 안 함)
- [ ] 제목에 매칭 단어 없다고 "다른 주제"로 판단했다
- [ ] 사용자에게 "새로 만들까요, 갱신할까요?"를 **동격** 선택지로 제시했다
- [ ] hit 문서가 `completed`라 "끝난 거니까 새로 만든다"고 판단했다
- [ ] "일단 새 WIP 쓰고 나중에 병합"하기로 했다

**기본값은 기존 SSOT 갱신**. 새 파일은 분리 근거를 제시할 때만.

**분리해야 할 때** (판단 기준 — 지표 아님):
- 결정이 여러 단계로 나뉘어 별도 실행·검증 필요
- 실행 결과가 원래 결정을 뒤집을 수 있는 실측 데이터 생성 (예: advisor
  판정으로 계획 반전)
- 결정 자체가 향후 독립 참조 가치 (ADR급)
- 작업 흐름 중단·재개를 위해 진행 상태 보존 필요

**분리하지 말아야 할 때**:
- 상류 SSOT에 범위·결정 다 있고 **실행만** 남은 경우
- 중간 결과가 상류 문서 갱신으로 흡수 가능한 경우
- 본 작업이 다른 커밋과 함께 묶이는 게 맥락상 자연스러운 경우

**단순 지표로 판단 금지**: "파일 3개 이상이면 WIP 생성" 같은 기계적 규칙
금지. 규모·도메인 flag 만으로 분기하지 말 것.

**완료된 문서 재개**: SSOT를 다시 쓰려면 `docs/X/` → `docs/WIP/` 되돌린 뒤
`status: completed` → `in-progress`. 같은 내용을 새 WIP로 복제하지 마라.

## 파일명 (SSOT: naming.md "파일명 — 문서" 섹션)

요약:
```
{abbr}_{slug}.md                  모든 폴더 (decisions/guides/harness/incidents)
{slug}.md                         전역 마스터 문서 (abbr 없음, 도메인 횡단)
```

- `abbr`: `naming.md` "도메인 약어" 표의 값 (도메인당 1개)
- `slug`: snake_case 의미명 — **주제 자체**. 세분화(어느 skill·rule·agent인지)는
  파일명이 아니라 `tags:` 프론트매터로 표현 (단일 도메인 유지, 탐색 유연성 확보)
- **날짜 suffix 전면 금지** — incidents 포함. 같은 주제는 같은 파일을
  갱신. 발생 시점은 프론트매터 `created` + git history가 담당.
  주요 전환점은 본문 `## 변경 이력` 섹션에 기록
- 전역 마스터 vs 단일 도메인 마스터 판단 기준은 `naming.md` 참조

### 왜 이 형식인가 (운영 관점)

- **파일명만으로 도메인 즉시 확정** → Read 안 해도 cluster 확정, `docs-ops.sh`
  가 프론트매터 재파싱 없이 매핑 가능
- **주제 = 파일 1:1** → `grep -r "memory"` 한 번에 관련 논의 전부 모임.
  여러 날짜 파일 중 최신 찾는 수고 없음
- **abbr prefix** → `ls docs/**/hn_*`로 도메인 전체 리스트업 1초
- **tags 세분화** → 같은 도메인 안에서 `skill`·`agent`·`rule`·`hook` 등 태그로
  관심사 필터링. 도메인을 여러 개로 쪼개지 않고도 축 분리 가능

### 주제 분할 규칙

한 파일이 여러 주제를 다루면 grep이 실패한다. 분할 기준:
- 결정 근거가 독립적이고 서로 다른 문제를 다루면 **분할** (`hn_staging_governance.md`
  + `hn_staging_followup.md`)
- 같은 결정의 후속 실행·측정은 **본문 누적** (`## 변경 이력` 섹션)
- 동일 주제 재결정은 같은 파일 갱신. 완전 superseded만 `archived/` + 새 파일

## 문서 생성

생성 흐름 (write-doc·implementation 스킬이 강제):

```
1. 폴더 결정 (decisions / guides / incidents / harness)
2. domain 조회 + abbr 조회 (naming.md "도메인 약어" 표)
   └ abbr 누락 시 사용자에게 입력 요청 + naming.md 약어 표 갱신
3. 기존 문서 탐색 (같은 주제 있으면 갱신 유도, 분리 판단)
4. 파일명 생성: {대상폴더}--{abbr}_{slug}.md
5. 프론트매터 작성: title / domain / tags / status / created
6. 본문 작성
```

- 코드 작업과 함께 → implementation 스킬이 docs/WIP/에 계획 문서 생성
  (단, 위 SSOT 우선·분리 판단 선행)
- 문서만 단독 → write-doc 스킬이 폴더·프론트매터·파일명 강제
- WIP 파일명: `{대상폴더}--{abbr}_{slug}.md`
  - `--`는 라우팅 태그. `{대상폴더}`: decisions, guides, incidents, harness
- 프론트매터 필수. `relates-to`는 작업 중 비어도 됨

## 문서 이동

- 완료/중단 문서는 docs/WIP/에 남기지 않음
- 이동은 commit 스킬 처리. 수동 이동 금지
- 이동 시 `{대상폴더}--` 접두사 제거 → `{abbr}_{slug}.md`
- 위 구조 폴더만 허용. **새 하위 폴더 만들지 마라**
- 이동 시: status → completed/abandoned, updated 갱신, clusters/{domain}.md에 추가
  - cluster는 파일명 abbr을 `naming.md` "Cluster 자동 매핑" 규칙으로
    결정. abbr 없는 전역 마스터는 프론트매터 `domain:`으로 폴백

### 완료 문서 재개 (역방향 이동)

completed로 이동된 SSOT 문서에 후속 실행 결과를 기록해야 하면:
1. `git mv docs/{폴더}/{abbr}_{slug}.md docs/WIP/{원래접두사}--{abbr}_{slug}.md`
2. 프론트매터 `status: completed` → `in-progress`
3. 작업 완료 시 다시 completed 전환 + 원래 폴더로 이동 (commit 스킬)

이 경로를 쓰는 이유: 같은 내용을 새 WIP로 복제하면 SSOT가 둘이 됨.
한 문서가 살아 있다가 완료되는 수명주기를 유지.

## completed 전환 차단

본문에 다음 키워드 남아 있으면 차단 (대소문자 무관):
`TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`, `별도로`

차단 시 선택:
1. 미결 항목을 별도 WIP로 분리 (권장). 원본 completed 이동, 새 WIP는 `rel: caused-by` 연결
2. 해결 완료라면 키워드 제거 후 재시도

commit 스킬이 검사. 수동 completed 전환 금지.

## 금지

- docs/ 외 위치 문서 생성 (README/CHANGELOG 등 루트 표준 파일 제외)
- docs/ 하위 임의 폴더 생성 (위 구조만 허용)
- 새 폴더가 필요하면 사용자에게 먼저 확인
- naming.md에 없는 domain 사용
- naming.md "도메인 약어" 표에 없는 abbr 사용 (abbr 먼저 등록)
- 파일명 날짜 suffix (incidents 포함). 발생 시점은 프론트매터 `created`
- 주제 여럿을 한 파일에 뭉치기 (grep 실패 → 탐색 체인 깨짐)
