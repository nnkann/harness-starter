---
title: 문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙
domain: harness
tags: [naming, docs, upstream-rule, rule]
relates-to:
  - path: decisions/hn_memory.md
    rel: references
  - path: harness/hn_index_md_removal.md
    rel: extends
  - path: decisions/hn_frontmatter_graph_spec.md
    rel: supersedes
status: completed
created: 2026-04-21
updated: 2026-04-21
---

# 문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙

## 배경

다운스트림(Issen)에서 네이밍 개편 결정이 먼저 나왔고, 여기서 발견된
문제는 모든 다운스트림 프로젝트에 공통이라 업스트림(harness-starter)에
범용 규칙으로 반영한다. 다운스트림 결정문은 **재료**로 참고하되, 업스트림
관점에서 다시 판단한다.

## 왜 — 이 변경으로 얻는 것

핵심 가치: **파일명이 곧 인덱스**. 전에 폐기된 `INDEX.md`의 역할을 파일명
체계가 흡수한다.

### 검색·탐색 파워

| 행동 | 전 (구 네이밍) | 후 (신 네이밍) |
|------|----------------|----------------|
| "harness 도메인 문서 전부" | clusters/harness.md 파일 열어 목록 훑기 | `ls docs/**/hn_*` 한 줄 |
| "memory 관련 결정 어디에 있지?" | 프론트매터 `domain:` grep + 내용 읽기 | `ls docs/**/*memory*` 즉시 |
| 파일 하나 열 때 성격 파악 | 파일 열고 프론트매터 확인 | 파일명 `hn_memory.md`만으로 domain + 주제 확정 |
| 같은 주제의 과거 논의 | 날짜 suffix 파일 여러 개 중 최신 찾기 | 주제 = 파일 1:1 — 바로 그 파일 |
| cluster 갱신 | 수동 인덱스 관리 | docs-manager가 파일명 abbr 파싱해 자동 |

### LLM 관점

- 새 세션에서 프로젝트 문서 구조 파악 시 파일명 목록만으로 전체 도메인·
  주제 맵 추론 가능. Read 횟수 감소
- 작업 맥락에서 관련 문서 찾기 → `Glob` + abbr prefix 하나로 끝.
  frontmatter 읽기 단계 생략
- 새 문서 생성 시 파일명 규칙 자체가 "어느 도메인인가?" 강제 → 분류
  누락 방지

### INDEX.md 폐기와의 연결

`docs/harness/hn_index_md_removal.md`는 "도메인 2개 구조에서 INDEX
진입 포인터 역할이 무의미, 관리 드리프트만" 이라 폐기. 그 공백을 채우는
것이 본 결정:
- INDEX → clusters (도메인별 인덱스)
- clusters → 파일명 abbr (자동 매핑, 인덱스가 파일명 자체에 내장)

결과: 수동 인덱스 관리 0, 파일명만 올바르면 탐색 자동화 유지.

### 다운스트림이 발견한 문제 (업스트림에도 그대로 적용)

1. **도메인 정보 부재** — 파일명만으로 어느 cluster에 속하는지 모름.
   `docs-manager`가 매번 프론트매터 `domain:`을 읽어야 cluster 등록 가능.
2. **날짜 suffix로 인한 SSOT 분열** — `hn_memory_260420.md`가 또
   갱신되면 `hn_memory_260521.md` 같은 분기 유혹. SSOT 둘로 쪼개짐.
3. **cluster 자동 매핑 부재** — 현재 매핑은 수동. 파일명 규칙이 있으면
   자동화 가능.

**업스트림에서는 제외**:
- 마일스톤 prefix `m{N}-{abbr}_t{NN}_` — 프로젝트별 개발 단계 구조에
  의존. 하네스 범용 아님. **단, 업스트림 파싱 규칙을 직교하게 설계**해서
  다운스트림이 앞에 어떤 prefix를 붙이든 cluster 자동 매핑이 동작하게
  한다 (아래 결정 D의 파싱 규칙 참조). 다운스트림은 자기 `naming.md`의
  확장 섹션에 자기 규칙을 추가하면 되고, harness-upgrade는 업스트림 소유
  섹션만 덮어쓴다
- 업스트림 자체 파일 일괄 마이그레이션 — 업스트림은 신규 파일부터 새
  규칙 적용, 기존 파일은 갱신 시점에 점진 이동. 다운스트림이 일괄 이동을
  선택하는 것은 **다운스트림의 자율**. 업스트림은 스크립트 제공 안 함

## 결정

### A. 도메인 약어 (abbr) SSOT 신설

`naming.md`의 "도메인 목록 > 확정"에 있는 모든 도메인은 여기에 2~3자
소문자 약어가 함께 등록돼야 한다.

**약어 규칙**:
- 길이: 2~3자 소문자
- 문자: 영문 소문자만 (숫자·기호 금지)
- 도메인당 1개 (다중 약어 금지)
- 충돌 금지
- 해석 가능한 약어 (원 이름 첫 자·자음 조합 선호)

**하네스 기본 시드**:

| 도메인 | abbr | cluster |
|--------|------|---------|
| harness | hn | clusters/harness.md |
| meta | mt | clusters/meta.md |

다운스트림은 `harness-init`·`harness-adopt`에서 자기 도메인을 확정 목록에
추가할 때 이 약어 표도 함께 갱신. 누락 시 `docs-manager`가 경고.

### B. 파일명 패턴 (업스트림 범용)

```
{abbr}_{slug}.md                  모든 폴더 (decisions/guides/harness/incidents)
{slug}.md                         전역 마스터 문서 (abbr 없음, 도메인 횡단)
```

**날짜 suffix 전면 금지** (incidents 포함). 발생 시점은 프론트매터
`created` + git history가 담당. (초안에는 incidents만 예외였으나 2026-04-21
실제 적용 시 원칙 철저 통일 결정.)

**마스터 문서 정의**:
- **abbr 부착**: 단일 도메인 내의 마스터/truth 문서 (예: 그 도메인의
  핵심 가이드). cluster는 해당 도메인 하나에만 속함
- **abbr 생략**: 전 도메인 횡단 또는 프로젝트 전역 인덱스 (예:
  `project_kickoff.md`, `MIGRATIONS.md`). cluster는 프론트매터
  `domain:`으로 결정하거나 복수 cluster에 등록

판단 기준: "이 문서가 어느 한 도메인의 소유인가?" 예 → abbr 부착.
아니면(여러 도메인의 진입점·프로젝트 전체 메타) → abbr 생략.

**WIP 라우팅 태그는 유지**:
```
{대상폴더}--{abbr}_{slug}.md              모든 대상 폴더
```

`commit` 스킬이 `{대상폴더}--` 접두사를 제거하고 해당 폴더로 이동. 기존
라우팅 태그 메커니즘 그대로.

### C. 날짜 suffix 폐기 + 통합 원칙

같은 주제는 **같은 파일 갱신**. 날짜로 새 파일을 만들면 SSOT 분열.

```
❌ decisions/hn_memory_260420.md + decisions/hn_memory_260521.md
✅ decisions/hn_memory.md (누적 갱신, ## 변경 이력 섹션)
```

**예외**:
- **진짜 superseded** — 옛 결정이 본질적으로 다른 새 결정으로 완전
  대체되면 옛 파일은 `archived/`로 이동, 새 파일 생성 허용. 같은 주제의
  진화는 분기 금지
- incidents도 예외 없음. `symptom-keywords` + 프론트매터 `created`가
  재조회 그립 역할을 하므로 파일명 날짜 불필요 (원칙 통일)

### D. cluster 자동 매핑

`docs-manager`가 파일명을 파싱해 cluster 결정. **abbr이 파일명 어느
위치에 있어도 인식**하는 직교 규칙으로, 다운스트림이 앞에 불투명 prefix
(마일스톤 `m3-`, Sprint `s12-` 등)를 붙여도 자동 매핑이 동작.

**파싱 규칙** (docs-manager Step 3 구현):
```
1. naming.md 약어 표에서 등록된 abbr 목록 수집 → [hn, mt, ...]
2. 파일명에서 패턴 `(^|[_-])(<abbr>)_` 검색 (첫 매치 사용)
3. 매치되면 해당 abbr에 대응하는 cluster에 등록
4. 매치 없으면 프론트매터 `domain:`으로 폴백 (마스터/전역 문서 처리)
```

동작 예:
```
decisions/hn_memory.md              → abbr=hn → clusters/harness.md
incidents/hn_leak_260421.md         → abbr=hn → clusters/harness.md
WIP/m3-hn_t04_redesign.md           → abbr=hn (불투명 prefix 통과)
WIP/decisions--hn_memory.md         → abbr=hn (라우팅 태그 통과)
guides/project_kickoff.md           → abbr 없음 → 프론트매터 domain 폴백
```

**엣지 케이스 — 첫 매치 정책**:
파일명에 여러 abbr이 등장하면 **가장 앞쪽 매치**를 사용. abbr 조합이
slug에 우연히 나타나는 경우를 방어하는 간단한 규칙.

```
m3-hn_t04_mt_review.md              → abbr=hn  (hn이 앞, mt는 slug의 일부로 무시)
WIP/decisions--hn_mt_comparison.md  → abbr=hn  (라우팅 태그 뒤 첫 abbr)
cs_hn_integration.md                → abbr=cs  (경계 케이스 — 정말 "cs"가 주 도메인일 때만 이런 이름을 써야 함)
```

**엣지 케이스 — 라우팅 태그와 조합**:
WIP 라우팅 태그 `{폴더}--`는 파싱에서 투명하게 통과. 라우팅 태그 뒤의
첫 세그먼트부터 abbr 검색.

```
WIP/decisions--hn_memory.md         → hn
WIP/harness--m3-hn_t04_foo.md       → hn (라우팅 통과 + 불투명 prefix 통과)
WIP/incidents--hn_leak.md           → hn (incidents 라우팅, 날짜 suffix 없음)
```

**불투명 prefix의 의미 해석은 업스트림이 하지 않는다**. 다운스트림이
`m{N}-`이 Phase인지 Milestone인지 Sprint인지 정의하든, 업스트림 파싱은
그것을 건드리지 않고 abbr만 뽑는다.

**약어 충돌 검사**: docs-manager `--validate`가 naming.md 약어 표를 파싱해:
- 중복 약어 검출 (예: 두 도메인이 같은 약어 등록)
- 도메인 목록과 약어 표의 1:1 대응 검증 (약어 누락된 도메인 경고)
- 파일명 prefix가 등록된 abbr 중 어느 것과도 매치 안 되면 경고

### E. 마이그레이션 정책 — 업스트림은 일괄, 다운스트림은 자율

**업스트림 정책** (2026-04-21 최종 적용): 이번 변경 시점에 40개 파일
**일괄 rename + 본문 참조 173건 치환**. 이유:
- 초안은 "점진 이동"이었으나 사용자 판단으로 "지금 아니면 못 한다" +
  옛·신 혼재가 오히려 혼란
- 전역 마스터(`promotion-log.md`·`MIGRATIONS.md`·`project_kickoff.md`)는
  abbr 없이 유지
- `archived/`는 건드리지 않음 (역사 보존)

**다운스트림 정책**: 일괄 이동 vs 점진 이동은 **다운스트림 선택**. 업스트림
은 강제하지 않고, 스크립트도 제공하지 않는다. 이유:
- 자동 이동은 `relates-to` path·본문 내 마크다운 링크를 대량 파괴
- 다운스트림마다 참조 구조가 달라 범용 스크립트가 안전하지 않음
- 옛 이름과 새 이름 공존은 업스트림 파싱 규칙상 문제없음 (결정 D 참조)

**공존 가이드** (MIGRATIONS.md에 포함):
- grep 시 두 패턴 모두 검색 (옛: `_\d{6}\.md`, 신: `{abbr}_`)
- cluster 자동 매핑은 신·구 모두 성공 (구 파일도 `{abbr}_` prefix가
  있었다면 파싱 성공)
- 옛 날짜 suffix 파일을 그대로 두는 것은 허용. 새 파일만 신 규칙 준수

### F. write-doc / docs-manager 스킬 변경

| 스킬 | 변경 |
|------|------|
| write-doc Step 1 | 도메인 확인 시 abbr도 함께 검증 (naming.md 약어 표에 있는지). 누락 시 사용자에게 abbr 입력 요청 |
| write-doc Step 3 | 파일명 생성을 `{abbr}_{slug}.md` 형식으로. 날짜 suffix 전면 금지 (incidents 포함) |
| docs-manager Step 3 | cluster 매핑 시 파일명에서 abbr 검색 (직교 파싱 규칙), 없으면 프론트매터 `domain:` 폴백 |
| docs-manager --validate | 약어 중복·도메인-약어 1:1 대응 검사 |

### G. harness/ 폴더 처리 — 업스트림·다운스트림 대칭

업스트림과 다운스트림 모두 `harness/` 폴더는 **점진 이동**. 이유:
- 다운스트림이 업스트림 `harness/` 파일 이름을 임의 개명하면 harness-
  upgrade 3-way merge에서 reference 깨짐
- harness-upgrade 화이트리스트가 `harness/` 파일을 업스트림 소유로 관리
  하므로 다운스트림은 받는 쪽

다운스트림은 자기 harness/ 파일(업스트림에서 받지 않은 로컬 이력)만
자율로 관리.

## 실행 결과 (2026-04-21 완료)

1. ✅ 본 WIP 문서 작성 (결정 SSOT)
2. ✅ `.claude/rules/naming.md` — "왜 — 파일명이 곧 인덱스다", 도메인 약어
   SSOT, 파일명 섹션, Cluster 자동 매핑 직교 파싱 규칙 + 엣지 케이스
3. ✅ `.claude/rules/docs.md` — "핵심 원칙" 최상단 추가, 문서 탐색
   재구성(`ls`/`grep` 1차), 파일명 규칙·주제 분할 기준, 금지 목록 강화
4. ✅ `.claude/skills/write-doc/SKILL.md` — Step 1 abbr 검증·입력 요청,
   Step 3 파일명 신 형식, 날짜 suffix 거부
5. ✅ `.claude/scripts/docs_ops.py` — Step 3 직교 파싱,
   `--validate`에 약어·날짜suffix 검사
6. ✅ `docs/harness/MIGRATIONS.md` — v0.16.0 섹션 (자동 적용·왜·수동 액션·
   옵션 A/B/C·검증·회귀 위험)
7. ✅ `.claude/HARNESS.json` — 0.15.0 → 0.16.0
8. ✅ 업스트림 파일 40개 일괄 rename + 본문 참조 173건 치환
9. ✅ `docs/clusters/harness.md` 재생성 (폴더별 분류 + 전역 마스터 구분)
10. ✅ 본 문서 completed 전환 → `decisions/hn_doc_naming.md`로 이동

## 다운스트림 피드백 반영 (2026-04-21)

다운스트림에서 제기된 충돌·건의 반영 결과:

| 항목 | 처리 |
|------|------|
| 충돌 1 (마이그레이션 정책) | ✅ 결정 E — 업스트림 점진 / 다운스트림 자율 명시 |
| 충돌 2 (마일스톤 prefix 정식 편입 요구) | ❌ 거부 — 파일명 문법 2분기·upgrade 복잡도 증가. 대신 결정 D의 직교 파싱으로 다운스트림이 자유롭게 확장 가능 |
| 충돌 3 (harness/ 비대칭) | ✅ 결정 G — 양쪽 모두 점진 이동으로 대칭 |
| 건의 1 (약어 충돌 검사 자동화) | ✅ 결정 D + F — docs-manager --validate |
| 건의 2 (마스터 문서 정의 명확화) | ✅ 결정 B — 단일 도메인 마스터/전역 마스터 구분 |
| 건의 3 (옛 prefix 공존 가이드) | ✅ 결정 E 공존 가이드 + MIGRATIONS.md |
| 건의 4 (incidents abbr 강제 재검토) | ⚠️ 유지 — abbr 강제. 필요 도메인은 naming.md에 추가(ci/if 등) |
| 건의 5 (본 문서 셀프-적용) | ❌ 결정 전이라 셀프-적용 불가. completed 이동 시 신 규칙 적용 |

**핵심 반박**: 마일스톤 prefix를 선택적 확장으로 정식 편입하면 관리 부재
로 이어진다. 업스트림이 의미 정의 없이 문법만 허용하면 다운스트림마다
해석이 달라짐. 대신 **abbr이 어디 있어도 파싱**(결정 D)하는 직교 규칙으로
다운스트림이 앞에 무엇을 붙이든 cluster 매핑이 동작. 다운스트림은 자기
확장 섹션에 자기 문법을 정의하고, harness-upgrade는 업스트림 소유 섹션만
덮어쓰므로 충돌 없음.

## 회귀 위험

- **기존 파일 이름 혼재 기간** — 업스트림도 `_260420` suffix 파일 다수
  존재. 새 규칙과 공존하나, 사용자·LLM 모두 당분간 두 패턴 동시 노출
- **cluster 자동 매핑 오류** — 약어 prefix 우선 규칙이 마스터 문서를
  잘못 분류할 수 있음 (예: `mt_*`를 meta에 넣어야 할지 관례상 애매)
  → 마스터 문서는 abbr 없이 `{slug}.md`로 명시
- **다운스트림 충격** — 기존 다운스트림이 약어 표가 비어 있으면 `docs-
  manager` 경고 쏟아짐. MIGRATIONS.md 수동 액션으로 명시

## 메모

### 이 문서의 형식 자체에 대해

본 문서 파일명은 **신 규칙 발효 전**이므로 구 형식
(`harness--doc_naming_overhaul_260421.md`)으로 작성됐다. completed 이동
시 신 규칙에 맞춰 `decisions/hn_doc_naming.md`로 이동 (날짜 suffix 제거,
abbr `hn` 추가).

### 참조

- 원본 다운스트림 결정 (참고만): Issen 프로젝트 로컬 WIP
- 영향받는 파일:
  - `.claude/rules/naming.md`
  - `.claude/rules/docs.md`
  - `.claude/skills/write-doc/SKILL.md`
  - `.claude/scripts/docs_ops.py`
  - `docs/harness/MIGRATIONS.md`
  - `.claude/HARNESS.json`
