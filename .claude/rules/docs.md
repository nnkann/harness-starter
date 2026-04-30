# Docs 규칙

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

task 헤더 바로 다음 줄에 선언. 없으면 기본 `feature`.

```markdown
### 12. pre-check relates-to 확장
> kind: bug
```

- **kind 값**: `bug`·`feature`·`refactor`·`docs`·`chore`
- 성격이 명확히 다른 task에만 선택적으로 부착

### WIP task 블록 Acceptance Criteria 포맷

```markdown
**Acceptance Criteria**:
- [ ] Goal: 이 작업의 납득 기준 1줄 (review가 첫 번째로 읽는 기준)
- [ ] 세부 조건 1
- [ ] 세부 조건 2
- [ ] 영향 범위: [파일·문서명] — [어떤 회귀를 체크해야 하는가]  ← feature/refactor에서만
```

규칙:
- `Goal:` 항목 — 선택. 있으면 review가 diff 전에 우선 읽음
- `영향 범위:` 항목 — `feature` / `refactor` kind에서만 필요할 때 작성.
  `bug` / `docs` / `chore`는 kind가 이미 스코프를 선언하므로 생략
- `영향 범위:` 항목 1개 이상 → staging deep 트리거 (kind 기반 판단 이후 2차 격상)

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

1. `git mv docs/{폴더}/{abbr}_{slug}.md docs/WIP/{원래접두사}--{abbr}_{slug}.md`
2. `status: completed` → `in-progress`
3. 완료 시 commit 스킬이 원래 폴더로 이동

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
