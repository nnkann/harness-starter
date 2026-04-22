---
title: 프론트매터 그래프 스펙 설계
domain: harness
tags: [frontmatter, graph, docs-structure, historical]
relates-to:
  - path: harness/hn_index_md_removal.md
    rel: references
  - path: decisions/hn_doc_naming.md
    rel: references
status: completed
created: 2026-04-16
updated: 2026-04-21
---

> **역사적 맥락 (2026-04-21 갱신):** 본 문서는 프론트매터 + `INDEX.md`
> 기반 탐색을 제안한 **2026-04-16 설계**다. 이후:
> - 2026-04-20 `INDEX.md` 폐기 (`docs/harness/hn_index_md_removal.md`)
>   — 도메인 2개 구조에서 진입 포인터 관리 드리프트만 발생
> - 2026-04-21 파일명 abbr 체계 + `clusters/{domain}.md` 자동 매핑 도입
>   (`docs/decisions/hn_doc_naming.md`)
>
> 현재 운영 규칙은 `.claude/rules/docs.md`·`naming.md`. 본 문서의
> **프론트매터 스키마·관계 타입**은 여전히 유효하나, **`INDEX.md` 섹션
> (§6 "INDEX.md 구조", §7 "탐색 흐름")**은 clusters + 파일명 규약으로
> 대체됐다.

# 프론트매터 그래프 스펙 설계

## 목표
- docs/ 문서에 구조화된 YAML 프론트매터를 도입하여 문서 간 관계를 명시적으로 표현
- Claude가 전체 문서를 읽지 않고 INDEX.md → 프론트매터 → 본문 순으로 점진적 탐색 가능
- Graphify의 클러스터 개념을 폴더와 독립된 의미 기반 그룹으로 구현
- 향후 온톨로지 확장의 데이터 기반 마련

## 배경

### 현재 상태
- 문서 헤더: `> status: completed` 한 줄만 존재
- 문서 탐색: Claude가 `Glob + Read` 조합으로 전체를 읽거나, 파일명 추측으로 검색
- 관계 표현: 없음. 폴더가 유일한 분류 기준

### 문제
1. 폴더는 생애주기(WIP → setup/history)를 표현하지, 의미(인증, 성능, 하네스)를 표현하지 않음
2. 관련 문서가 다른 폴더에 흩어지면 연결 고리 없음
3. 문서가 늘어날수록 Claude의 전체 탐색 비용 증가

### 해결 방향
Graphify의 "뉴런형 지식 그래프"에서 영감. 단, 외부 도구(AST 파서, 벡터 DB) 없이 **마크다운 프론트매터 자체가 그래프 노드** 역할.

---

## 설계

### 1. 프론트매터 스키마

```yaml
---
title: 문서 제목
domain: auth                          # 주 도메인 (1개, 필수)
tags: [jwt, session, redis]           # 키워드 (0~5개, 선택)
relates-to:                           # 관련 문서 포인터 (선택)
  - path: setup/project_kickoff_sample.md
    rel: extends                      # 관계 타입
  - path: history/auth_migration.md
    rel: caused-by
status: completed                     # 기존 status 흡수
created: 2026-04-14
updated: 2026-04-14
---
```

### 2. 필드 정의

| 필드 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `title` | O | string | 문서 제목. 검색/인덱스용 |
| `domain` | O | string | 주 도메인. CPS의 도메인 목록에서 선택, 또는 `harness`, `meta` |
| `tags` | - | string[] | 세부 키워드. 최대 5개. 자유 태그 허용 |
| `relates-to` | - | object[] | 관련 문서. `path` + `rel` 쌍 |
| `status` | O | enum | pending, in-progress, completed, abandoned, sample |
| `created` | O | date | 생성일 (YYYY-MM-DD) |
| `updated` | - | date | 최종 수정일 |

### 3. 관계 타입 (rel)

온톨로지 확장을 대비해 관계 타입을 제한된 어휘로 정의:

| rel | 의미 | 방향성 | 예시 |
|-----|------|--------|------|
| `extends` | A가 B를 확장/발전 | A → B | 업그레이드 문서 → 원본 설계 |
| `caused-by` | A의 원인이 B | A → B | 버그 수정 → 버그 발생 이력 |
| `implements` | A가 B를 구현 | A → B | 구현 가이드 → CPS/설계 결정 |
| `supersedes` | A가 B를 대체 | A → B | 새 설계 → 이전 설계 |
| `references` | A가 B를 참조 (약한 연결) | A → B | 분석 문서 → 참고 자료 |
| `conflicts-with` | A와 B가 충돌 | A ↔ B | 상충하는 두 설계 결정 |

**규칙**: 위 6개만 허용. 새 타입이 필요하면 이 문서에 추가 후 사용.

### 4. domain 어휘

프로젝트 초기화(harness-init) 전:
- `harness` — 하네스 자체에 대한 문서
- `meta` — 프로젝트 관리, 의사결정 프로세스

프로젝트 초기화 후:
- CPS의 도메인 목록에서 추가 (예: `auth`, `task`, `payment`)
- naming.md의 "도메인 목록 > 확정"과 동기화

### 5. 클러스터 (domain 기반 그룹)

폴더와 독립적으로 **같은 domain을 공유하는 문서가 하나의 클러스터**:

```
클러스터 "harness":
  ├── docs/harness/promotion-log.md
  ├── docs/decisions/hn_upgrade.md
  ├── docs/guides/hn_upgrade_propagation.md
  └── docs/decisions/hn_gap_analysis.md

클러스터 "meta":
  └── docs/guides/project_kickoff_sample.md
```

폴더는 문서의 **성격**(왜/어떻게/무엇이 깨졌나), domain은 문서의 **의미**를 담당. 이중 분류.

### 6. INDEX.md 구조

`docs/INDEX.md`에 모든 문서의 프론트매터 요약을 자동 유지:

```markdown
# 문서 인덱스

> 이 파일은 docs/ 내 모든 문서의 프론트매터 요약이다.
> Claude는 세션 시작 시 이 파일만 읽고, 필요한 문서를 선택적으로 탐색한다.

## 도메인별

### harness
- [업그레이드 계획](hn_upgrade.md) — tags: memory, hook, skill
- [업그레이드 전파](../guides/hn_upgrade_propagation.md) — tags: upgrade, script
- [적합성 분석](hn_gap_analysis.md) — tags: gap-analysis, verification

### meta
- [프로젝트 출범 샘플](../guides/project_kickoff_sample.md) — tags: cps, stack — status: sample

## 관계 맵 (주요)
- hn_upgrade --extends--> promotion-log
- hn_gap_analysis --references--> hn_upgrade
- hn_upgrade_propagation --implements--> hn_upgrade
```

### 7. Claude의 탐색 흐름

```
세션 시작
  │
  ├─ docs/INDEX.md 읽기 (자동 또는 필요 시)
  │   └─ 도메인별 문서 목록 + 태그 + 관계 맵 확인
  │
  ├─ 작업과 관련된 domain 식별
  │   └─ 해당 클러스터의 문서만 Read
  │
  └─ relates-to 포인터 따라 연관 문서 탐색
      └─ 필요한 깊이까지만 (보통 1~2 홉)
```

**비교**:
| | 현재 | 프론트매터 그래프 적용 후 |
|---|---|---|
| 문서 10개일 때 | 전부 읽어도 괜찮음 | 차이 미미 |
| 문서 50개일 때 | 전부 읽기 비현실적 | INDEX.md(1회) + 관련 문서(2~3개) |
| 관련 문서 찾기 | Glob → 파일명 추측 → 하나씩 Read | INDEX.md의 domain/tags로 즉시 식별 |

---

## 기존 규칙과의 통합

### docs.md 변경사항

1. **프론트매터 필수화**: 모든 docs/ 문서는 YAML 프론트매터 필수
2. **status 이동**: `> status: xxx` 인라인 → 프론트매터의 `status` 필드로
3. **WIP 문서**: 프론트매터 포함하되 `relates-to`는 선택 (작업 중이라 관계가 불확실할 수 있음)
4. **INDEX.md 갱신**: commit 스킬이 문서 이동 시 INDEX.md도 함께 갱신

### implementation 스킬 변경사항

Step 1 문서 생성 시 프론트매터 템플릿 포함:

```markdown
---
title: {작업 제목}
domain: {CPS 도메인 또는 harness/meta}
tags: []
relates-to: []
status: pending
created: {YYYY-MM-DD}
---

# {작업 제목}

## 목표
...
```

### commit 스킬 변경사항

문서 이동 시:
1. 프론트매터의 `status` 갱신 (completed/abandoned)
2. `updated` 필드 갱신
3. INDEX.md에 항목 추가/갱신

---

## 적용 계획

### Phase 0: 실제 프로젝트 도입 가이드

이 스타터를 클론한 프로젝트에서 프론트매터 그래프를 도입하는 3가지 시나리오:

#### 시나리오 A: 신규 프로젝트 (harness-init부터 시작)

가장 자연스러운 경로. harness-init 흐름에 통합.

```
harness-init Step 7 (결정 기록)
  │
  ├─ project_kickoff 문서에 프론트매터 자동 포함
  │   domain: meta, tags: [cps, stack]
  │
  ├─ docs/INDEX.md 초기 생성
  │   첫 번째 엔트리 = project_kickoff
  │
  └─ Step 8 (첫 작업 문서)
      domain: CPS에서 선택한 도메인
      relates-to: [{path: guides/project_kickoff.md, rel: implements}]
```

**변경 대상**: harness-init SKILL.md Step 7 템플릿에 프론트매터 추가

#### 시나리오 B: 기존 프로젝트의 하네스 업그레이드 (harness-upgrade)

이전 폴더 구조로 문서가 쌓여 있는 프로젝트. 폴더 마이그레이션 + 프론트매터 도입이 동시에 필요.

##### B-1. 이전 폴더 감지 및 매핑

upgrade 스킬이 docs/ 구조를 스캔해서 이전 폴더를 감지한다:

| 이전 폴더 | 매핑 대상 | 판단 근거 |
|-----------|----------|----------|
| `plans/`, `planning/` | `decisions/` | "왜 이렇게 했나?" — 계획/결정 |
| `development/` | `decisions/` 또는 `guides/` | 문서 성격에 따라 분배 |
| `setup/` | `guides/` | "어떻게 하나?" — 절차/가이드 |
| `history/` | 문서별 분배 | 성격에 따라 `decisions/`, `guides/`, `incidents/`로 |
| `bugs/`, `issues/`, `postmortem/` | `incidents/` | "무엇이 왜 깨졌나?" |
| `archive/` | `archived/` | 이름만 통일 |
| `reference/`, `notes/` | 문서별 분배 | 성격에 따라 판단 |

**감지만 하고 자동 이동하지 않는다.** 사용자에게 매핑 제안을 보여주고 승인받는다.

##### B-2. 문서별 분류 판단

`history/`처럼 성격이 혼재된 폴더는 문서별로 판단해야 한다:

```
판단 기준: "이 문서를 누가 왜 다시 열까?"

→ 새 결정을 내릴 때 근거를 찾으러     → decisions/
→ 같은 작업을 다시 할 때 방법을 찾으러 → guides/
→ 비슷한 문제가 재발했을 때 원인을 찾으러 → incidents/
→ 더 이상 유효하지 않음              → archived/
```

Claude가 각 문서의 제목 + 첫 단락을 읽고 분류 초안을 생성한다.
사용자가 초안을 검수하고 수정한다.

##### B-3. 프론트매터 일괄 도입

```
1. docs/ 하위 .md 파일 목록 수집 (WIP/ 제외)
2. 각 파일에서 기존 메타정보 추출:
   - `> status: xxx` 인라인 → status 필드
   - 첫 번째 `# 제목` → title 필드
   - git log --follow로 생성일 추출 → created 필드
   - 파일 위치 + 내용 첫 단락 → domain 추론
3. 프론트매터 초안 생성 → 사용자 검수
4. relates-to는 빈 배열로 시작, 점진적으로 채움
5. INDEX.md + clusters/ 자동 생성
```

##### B-4. 삭제 대상 처리

마이그레이션 중 발견될 수 있는 삭제 대상:

| 대상 | 처리 |
|------|------|
| 빈 폴더 (.gitkeep만 있는) | 규칙에 없는 폴더면 삭제 제안 |
| 중복 문서 (같은 내용, 다른 위치) | 사용자에게 어느 것을 남길지 질문 |
| 임시 파일 (draft-, temp-, untitled-) | `archived/`로 이동 또는 삭제 제안 |
| `> status:` 인라인 (마이그레이션 후) | 프론트매터로 이관 후 인라인 삭제 |

##### B-5. 안전 장치

- **dry-run 모드**: 실제 이동 전에 전체 계획을 보여주고 승인받는다
- **git mv 사용**: 히스토리 보존. cp + rm 하지 않는다
- **롤백 가능**: 커밋 전까지 `git checkout -- docs/`로 원복 가능
- **WIP 문서 보존**: WIP/ 폴더의 문서는 이동하지 않는다

**핵심**: 완벽한 자동화보다 "스캔 → 초안 → 검수 → 적용" 패턴이 현실적.

#### 시나리오 C: 이 스타터 자체 (지금)

harness-starter의 기존 6개 문서에 즉시 적용.
폴더 리팩토링(development/, setup/ → decisions/, guides/)과 동시 진행:

| 현재 위치 | 이동 대상 | domain | 예상 관계 |
|-----------|----------|--------|----------|
| harness/promotion-log.md | harness/ (유지) | harness | - |
| harness/hn_improvement.md | decisions/ | harness | references: promotion-log |
| development/hn_upgrade.md | decisions/ | harness | extends: promotion-log |
| development/hn_upgrade_propagation.md | guides/ | harness | implements: hn_upgrade |
| development/hn_gap_analysis.md | decisions/ | harness | references: hn_upgrade |
| setup/project_kickoff_sample.md | guides/ | meta | - (sample) |

#### domain 어휘 거버넌스

domain은 자유 태그가 아니라 **통제된 어휘**다. 누가, 언제 추가하는가:

| 시점 | 누가 | 행위 |
|------|------|------|
| harness-init | Claude + 사용자 | CPS 도메인 → naming.md + domain 어휘에 등록 |
| 작업 중 새 도메인 필요 | 사용자 | naming.md "도메인 목록 > 확정"에 추가 후 사용 |
| 문서 작성 시 | Claude | naming.md의 확정 목록에서만 선택. 없으면 사용자에게 질문 |

**동기화 지점**: naming.md의 "도메인 목록 > 확정"이 **single source of truth**.
프론트매터의 domain 값은 여기에 있는 것만 허용.

### Phase 1: 스펙 확정 + 폴더 리팩토링 + 기존 문서 마이그레이션
- 이 문서의 스펙을 확정
- docs/ 폴더 구조를 docs.md 규칙에 맞게 리팩토링:
  - `development/` → 문서 성격에 따라 `decisions/` 또는 `guides/`로 이동
  - `setup/` → `guides/`로 이동
  - `clusters/`, `decisions/`, `guides/`, `incidents/`, `archived/` 폴더 생성
  - 비게 된 `development/`, `setup/` 폴더 삭제
- 기존 6개 문서 프론트매터 완비 (이미 적용됨)
- 프론트매터 내 `relates-to.path` 경로를 이동 후 경로로 갱신
- docs/INDEX.md 경로 갱신 + clusters/ 도입

### Phase 2: 규칙 반영 + 탐색 인프라
- docs.md에 프론트매터 필수 규칙 추가
- docs.md에 문서 탐색 트리거 규칙 추가 (언제/어떻게 탐색하는가)
- `.claude/agents/doc-finder.md` 에이전트 생성 (클러스터 기반 빠른 검색. v1.5.0에서 docs-lookup → doc-finder로 rename)
- `.claude/agents/` 폴더를 하네스 기본 구성에 포함 (h-setup.sh 대상)
- implementation 스킬의 Step 1 템플릿에 프론트매터 포함
- harness-init 스킬의 Step 7 템플릿에 프론트매터 포함
- commit 스킬에 INDEX.md 갱신 로직 추가

### Phase 3: 관계 타입 확장 (온톨로지 대비)
- 실제 프로젝트에서 사용하며 관계 타입 부족 여부 확인
- 필요 시 새 rel 타입 추가 (이 문서에서 관리)
- graph.json 자동 생성 검토 (도메인별 클러스터 시각화)

---

## 결정 사항

- 프론트매터 스키마: 위 7개 필드로 확정
- 관계 타입: 6개로 시작 (extends, caused-by, implements, supersedes, references, conflicts-with)
- domain 어휘: harness, meta를 기본값으로. CPS 도메인과 동기화
- INDEX.md: docs/ 루트에 위치. commit 스킬이 관리
- 기존 `> status:` 인라인 형식 → 프론트매터로 이관

## 메모

- Graphify는 AST + Leiden 클러스터링을 사용하지만, 우리는 수동 domain 태깅으로 대체. 문서 수가 수백 개 미만이면 이쪽이 더 정확하고 유지보수 비용 낮음
- 온톨로지 확장 시 rel 타입이 RDF의 predicate 역할을 하게 됨. 지금부터 어휘를 제한해두면 마이그레이션 비용 절약
- INDEX.md의 "관계 맵" 섹션은 전체 그래프의 edge list와 동일. 이것만 파싱해도 그래프 구조 복원 가능
