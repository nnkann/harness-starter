# 네이밍 규칙

<!-- naming-convention 스킬 실행 후 채워진다 -->

## 왜 — 파일명이 곧 인덱스다

**이 규칙 덕분에 가능한 것** (전에 폐기된 `INDEX.md`의 역할을 파일명
체계가 흡수):

- `ls docs/**/{abbr}_*` → 그 도메인의 모든 문서를 **즉시 목록화**
- `grep -r "hn_memory"` → 주제 관련 문서·참조 **한 번에 발견**
- 파일명 `hn_memory.md`만 봐도 **도메인(harness) + 주제(memory)** 확정.
  문서 열지 않고도 성격 파악 가능
- cluster 파일(`clusters/{domain}.md`)은 `docs_ops.py`가 파일명 abbr을
  파싱해 **자동 생성·갱신**. 수동 인덱스 관리 불필요
- 날짜 suffix 폐기로 **주제 = 파일 1:1 대응**. 같은 주제 검색 시 여러
  날짜 파일 중 최신 찾는 수고 없음
- 다운스트림이 앞에 불투명 prefix(`m3-`, `s12-`)를 붙여도 **abbr만
  직교 파싱**되어 cluster 매핑이 유지됨

핵심 가치: **파일명 → 도메인 → cluster** 체인이 자동화되어, 문서 찾기·
맥락 파악·연관 문서 탐색이 grep/ls만으로 끝난다. LLM이 전체 프로젝트
문서 구조를 파일명만으로 추론할 수 있다.

관련 결정: `docs/harness/hn_index_md_removal.md` (INDEX.md 폐기 배경),
`docs/decisions/hn_doc_naming.md` (본 네이밍 규칙 결정).

## 도메인 목록
확정: harness, meta
후보:

## 도메인 등급 (review staging)

`/commit` 시 review 강도 자동 결정용. `.claude/rules/staging.md` 참조.

- **critical** (변경 시 무조건 deep): harness
- **normal** (크기 기준 분기): (없음)
- **meta** (skip 검토): meta

다운스트림 프로젝트는 자기 도메인을 추가:
```
- critical: payment, auth, infra, migration, security
- normal:   api, data, ui
- meta:     docs, changelog
```

이 섹션이 비어 있으면 staging.md의 S9 신호 무시 (S7 일반 코드로 폴백).

## 도메인 약어 (abbr) — SSOT

파일명 prefix 및 cluster 자동 매핑용. 위 "도메인 목록 > 확정"의 **각
도메인마다 약어 1개가 등록**돼야 한다. 누락 시 `docs_ops.py`가 경고.

### 약어 규칙

- **길이**: 2~3자 소문자
- **문자**: 영문 소문자만 (숫자·기호 금지)
- **도메인당 1개** (다중 약어 금지)
- **충돌 금지**: 기존 약어와 겹치면 거부 — 약어 또는 도메인 이름 재검토
- **해석 가능성**: 원 이름의 첫 자·자음 조합 선호 (`harness → hn`,
  `migration → mg`). 의미 없는 약어(`x1`) 금지

### 표 (본 프로젝트 시드)

| 도메인 (full) | 약어 (abbr) | cluster 파일 |
|---------------|-------------|--------------|
| harness | hn | `docs/clusters/harness.md` |
| meta | mt | `docs/clusters/meta.md` |

다운스트림은 `harness-init`·`harness-adopt`에서 자기 도메인을 "도메인
목록 > 확정"에 추가할 때 **이 표에도 약어를 함께 등록**한다.

참고 — 다운스트림 확장 예시:
```
payment      → pm   → clusters/payment.md
auth         → au   → clusters/auth.md
api          → ap   → clusters/api.md
ui           → ui   → clusters/ui.md
infra        → if   → clusters/infra.md
migration    → mg   → clusters/migration.md
```

## 경로 → 도메인 매핑 (선택, 코드 영역용)

`docs/` 외 코드 파일의 도메인을 추출하기 위한 경로 매핑. 정의 안 하면
프론트매터·WIP 접두사로만 추출.

예시 (다운스트림 프로젝트):
```
src/payment/**     → payment
src/auth/**        → auth
src/api/**         → api
infra/**           → infra
migrations/**      → migration
```

업스트림 기본값: 생략. 다운스트림은 자기 프로젝트의 코드 폴더에 맞춰
위 예시를 참고해 경로 매핑을 추가 권장 (없으면 S9 도메인 등급 신호가
폴더 구조 기반 추출 경로를 잃음).

실제 매핑 (`docs_ops.py`·`pre_commit_check.py`가 파싱하는 영역):
```
```

## 폴더명

- `docs/` 하위: `.claude/rules/docs.md` "폴더 구조" SSOT 참조
- 새 하위 폴더 금지 (docs.md "금지" 섹션)

## 파일명 — 문서

### 기본 형식

```
{abbr}_{slug}.md                  모든 폴더 (decisions/guides/harness/incidents)
{slug}.md                         전역 마스터 문서 (abbr 없음, 도메인 횡단)
```

- `abbr`: 위 "도메인 약어" 표의 값 (도메인당 1개)
- `slug`: snake_case 의미명 (영문 소문자 + 숫자 + `_`)
- **날짜 suffix 전면 금지**. 발생 시점 추적은 프론트매터 `created`
  + git history가 담당

### 마스터 문서 — abbr 부착 판단

| 성격 | 예시 | abbr |
|------|------|------|
| 단일 도메인 내 마스터/truth | `hn_harness_overview.md` | ✅ 부착 |
| 전 도메인 횡단·프로젝트 전역 | `project_kickoff.md`, `MIGRATIONS.md` | ❌ 생략 |

판단 기준: **"이 문서가 어느 한 도메인의 소유인가?"**
- 예 → abbr 부착, 그 도메인 cluster에 등록
- 아니면 → abbr 생략, 프론트매터 `domain:`으로 cluster 결정하거나 복수
  cluster 등록

### 금지 — 날짜 suffix (전 폴더)

같은 주제가 갱신되면 **같은 파일을 갱신**한다. 날짜로 새 파일을 만들면
SSOT가 분열.

```
❌ decisions/hn_memory_260420.md + decisions/hn_memory_260521.md
✅ decisions/hn_memory.md          (누적 갱신, ## 변경 이력 섹션)

❌ incidents/hn_bash_overblock_260419.md
✅ incidents/hn_bash_overblock.md  (발생 시점은 프론트매터 created)
```

본문 갱신 시 중요한 전환점만 `## 변경 이력` 섹션에 기록. 세세한 버전
추적은 git history가 담당.

**incidents도 동일**. `symptom-keywords` + 프론트매터 `created`가 재조회
그립 역할을 하므로 파일명에 날짜 불필요. 같은 사건의 follow-up은 본문
갱신.

**진짜 superseded 예외**: 옛 결정이 본질적으로 다른 새 결정으로 완전
대체되면 옛 파일은 `archived/`로 이동 + 새 파일 생성. 같은 주제의 진화는
분기 금지.

## 파일명 — WIP

```
{대상폴더}--{abbr}_{slug}.md              모든 대상 폴더
```

- `{대상폴더}--`: WIP 라우팅 태그 (decisions / guides / incidents / harness)
  `commit` 시 `docs_ops.py move`가 제거하고 본 폴더로 이동
- 나머지는 위 "파일명 — 문서"와 동일 (날짜 suffix 없음)

이동 결과:
```
WIP/decisions--hn_memory.md          → decisions/hn_memory.md
WIP/incidents--hn_leak.md            → incidents/hn_leak.md
```

## Cluster 자동 매핑 — 직교 파싱 규칙

`docs_ops.py`가 파일명을 파싱해 cluster를 결정한다. **abbr이 파일명 어느
위치에 있어도 인식**하는 직교 규칙으로, 다운스트림이 앞에 불투명 prefix
(마일스톤 `m3-`, Sprint `s12-`, 레거시 `_p2_` 등)를 붙여도 매핑 성공.

### 파싱 절차

1. naming.md 약어 표에서 등록된 abbr 목록 수집 → `[hn, mt, ...]`
2. 파일명에서 패턴 `(^|[_-])(<abbr>)_` 검색 (여러 매치면 **가장 앞쪽** 사용)
3. 매치되면 해당 abbr에 대응하는 cluster에 등록
4. 매치 없으면 프론트매터 `domain:`으로 폴백 (전역 마스터 문서 처리)

### 동작 예

```
decisions/hn_memory.md              → abbr=hn → clusters/harness.md
incidents/hn_leak_260421.md         → abbr=hn → clusters/harness.md
WIP/m3-hn_t04_redesign.md           → abbr=hn (불투명 prefix 통과)
WIP/decisions--hn_memory.md         → abbr=hn (라우팅 태그 통과)
WIP/_p2_cs_polygon.md               → abbr=cs (레거시 prefix 통과)
guides/project_kickoff.md           → 프론트매터 domain 폴백
```

### 엣지 케이스 — 첫 매치 정책

여러 abbr이 파일명에 나타나면 **가장 앞쪽 매치 사용**. slug에 우연히
다른 abbr이 들어간 경우 방어.

```
m3-hn_t04_mt_review.md              → abbr=hn (hn이 앞, mt는 slug 일부)
WIP/decisions--hn_mt_comparison.md  → abbr=hn (라우팅 태그 뒤 첫 abbr)
```

### 엣지 케이스 — 라우팅 태그 + 불투명 prefix 조합

`{폴더}--` 라우팅 태그는 파싱에서 투명하게 통과. 태그 뒤 첫 세그먼트
부터 abbr 검색.

```
WIP/decisions--hn_memory.md                 → hn
WIP/harness--m3-hn_t04_foo.md               → hn (라우팅 + 불투명 둘 다 통과)
WIP/incidents--hn_leak_260421.md            → hn (라우팅 + 날짜 suffix)
```

### 의미 해석 원칙

업스트림은 **abbr만 추출**한다. 다운스트림이 `m{N}-`을 Phase로 쓰든
Milestone로 쓰든 Sprint로 쓰든 **의미 해석은 다운스트림 소관**. 업스트림
파싱은 그 prefix를 건드리지 않는다.

다운스트림이 자기 문법을 정의하려면 이 파일 하단에 `### 파일명 — 확장
(프로젝트 고유)` 하위 섹션을 추가. `harness-upgrade`는 업스트림 소유
섹션만 덮어쓰므로 충돌 없음.

## 클래스/함수/메소드

<!-- coding-convention 스킬 실행 후 채워진다 -->
