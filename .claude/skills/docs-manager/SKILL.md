---
name: docs-manager
description: >-
  docs/ 구조 정합성을 유지하는 스킬. 프론트매터 검증, INDEX.md/clusters
  갱신, 관계 맵 정합성 확인, 문서 이동 실행, CPS 문서 갱신을 수행한다.
  TRIGGER when: (1) commit 스킬의 문서 이동 단계,
  (2) write-doc 스킬이 새 문서 생성 후 INDEX/clusters 갱신,
  (3) harness-init/adopt가 docs/ 초기 구조 생성,
  (4) harness-upgrade 후 문서 규칙 변경 정합성 검증,
  (5) implementation Step 4(Context 업데이트)에서 CPS 문서 갱신,
  (6) 사용자가 "문서 정합성 검사" 요청.
  SKIP: (1) 단순 문서 검색·요약 (→ doc-finder 에이전트),
  (2) 문서 본문 직접 작성 (→ write-doc 스킬),
  (3) docs/ 외 파일 관리.
---

# /docs-manager 스킬

docs/ 폴더의 정합성·구조·관계 맵을 관리한다. Edit/Write 권한이 필요한
작업이 있어 에이전트가 아닌 스킬로 동작한다 (책임 명확·단계별 사용자
확인 가능).

## 사용법

| 사용법 | 설명 |
|--------|------|
| `/docs-manager` | 전체 정합성 검증 (검증 모드) |
| `/docs-manager --move <WIP 파일>` | 단일 문서 이동 + 갱신 |
| `/docs-manager --validate` | 프론트매터·관계 맵만 검증 (수정 없음) |
| `/docs-manager --refresh-index` | INDEX.md/clusters 재생성 |

호출자 스킬(commit, write-doc, harness-init 등)이 내부적으로 호출하는
경우가 다수다.

## 호출자 전달 규약 (정보 흐름 누수 #3·#5·#11 해소)

호출자는 docs-manager 호출 시 **무엇을·왜·어디서**를 prompt에 명시하라.
명시하지 않으면 docs-manager가 docs/ 전수 스캔으로 폴백 (느림).

```
## docs-manager 호출 입력
trigger: <어떤 시점에·왜 호출했는가>
   예: "commit 스킬 Step 2.2 — 사용자가 'completed로 이동' 요청"
       "harness-upgrade Step 9 — Step 4·5에서 docs/ 파일 변경됨"
       "write-doc Step 6 — 새 문서 생성 직후 INDEX 갱신"
       "사용자가 '/docs-manager' 직접 실행 — 전체 헬스체크"

intent: validate | update-index | move-document | full-refresh
   - validate: 프론트매터·관계 맵 정합성만 (수정 없음)
   - update-index: INDEX/clusters 갱신 (신규·이동된 파일 반영)
   - move-document: WIP → 대상 폴더 이동 + 후속 갱신
   - full-refresh: INDEX/clusters 재생성 (최초 또는 대규모 정리)

scope: focused | full
   - focused: files에 명시된 파일만 처리 (호출자가 무엇을 건드렸는지 안다)
   - full: docs/ 전수 스캔 (정합성 헬스체크. 호출자가 모르는 변경까지 검사)

files:
  - <경로>:
      action: created | updated | moved | deleted
      domain: <name>     (호출자가 알면 — docs-manager가 frontmatter 재파싱 절약)
      status: <state>    (호출자가 알면)
      moved_from: <경로> (action=moved일 때)

context:
  prior_steps: <이번 호출까지의 호출자 처리 내역>
     예: "Step 4에서 .claude/rules/* 7개 덮어쓰기 완료, Step 5에서
          docs/guides/ 3개 신규 이식, INDEX.md는 아직 미갱신"
  reason_for_scope: <왜 focused 또는 full인지>
     예: "focused — 변경 파일이 명확. 다른 docs/는 이전 commit에서 이미 검증됨"
       또는 "full — adopt 후 docs/ 전수 검증 필요. 처음 보는 파일 다수"
```

### 왜 trigger·intent·context까지 박는가

`scope`/`files`만 있으면 docs-manager가 "무엇을 할지"는 알지만 "왜 지금
이게 호출됐는지"를 모름. 결과:
- 검증 우선순위 결정 못 함 (정합성 위반 발견 시 자동 수정할지·보고만 할지)
- 호출자의 다음 단계 모름 (이번 갱신이 다른 변경의 일부인지·독립인지)
- 같은 정보를 docs-manager가 frontmatter Read로 재확보 → 누수 재발

`trigger`+`intent`+`context.prior_steps`가 있으면:
- docs-manager가 호출 맥락을 이해해 적절한 강도로 처리
- 이미 호출자가 한 일을 재실행 안 함 (예: 호출자가 frontmatter 추가 완료 → docs-manager는 재검증만)
- 발견한 문제를 호출자의 후속 단계와 연결해 보고

### 호출자별 전형 패턴

| 호출자 | trigger | intent | scope | 비고 |
|--------|---------|--------|-------|------|
| commit Step 2 | "WIP 이동 (사용자 명시 요청)" | move-document | focused | WIP 파일 1개 |
| write-doc Step 6 | "새 문서 생성 직후" | update-index | focused | 방금 만든 파일 1개 |
| harness-upgrade Step 9 | "Step 4·5에서 docs 규칙 변경" | validate | focused | 변경 파일 N개 |
| harness-init/adopt 초기 | "최초 INDEX 생성" | full-refresh | full | INDEX·clusters 자체 없음 |
| 사용자 직접 `/docs-manager` | "사용자 헬스체크 요청" | validate | full | 전수 검사 |

### 폴백

규약을 안 따르면 docs-manager는 자동으로 `scope: full` + `intent: validate`
폴백하고 호출자에게 경고 1회 출력 (강제 X — 호환성 유지).

## Step 1. 프론트매터 검증

**처리 범위**: 위 "호출자 전달 규약"의 `scope`로 결정.
- `scope: focused`: `files`에 나열된 파일만 검증
- `scope: full`: docs/ 하위 모든 .md 파일(WIP/ 포함) 전수 검증

다음 검증 규칙은 두 모드 공통:

| 필드 | 규칙 |
|------|------|
| title | 필수. 비어있으면 안 됨 |
| domain | 필수. naming.md "도메인 목록 > 확정"에 있어야 함 |
| tags | 최대 5개 |
| relates-to | path가 실제 존재하는 파일이어야 함. rel은 6종만 허용 |
| status | 필수. pending/in-progress/completed/abandoned/sample 중 하나 |
| created | 필수. YYYY-MM-DD 형식 |

incidents/ 추가 필수: `symptom-keywords` (재발 검색용 고유명사 리스트).

위반 발견 시 사용자에게 보고. 자동 수정은 명백한 경우에만 (예: 누락된
`updated` 필드를 오늘 날짜로 채움).

## Step 2. 문서 이동 실행 (--move 또는 commit 스킬에서 호출)

WIP에서 대상 폴더로 문서를 이동한다:

1. **이동 전 차단 검사**: status를 `completed`로 전환할 때 본문에 차단
   키워드가 있으면 이동 차단. **이 검사는 우회 금지**.

   실행 절차 (순서대로):
   ```bash
   # 1. 본문 추출 (frontmatter + "처리 결과"·"## 원본" 이후 회고 섹션 제외)
   BODY=$(awk '
     /^---$/{c++; next}
     c<2{next}
     /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
     !skip
   ' <WIP파일>)

   # 2. 차단 키워드 검사 (대소문자 무관, 인용·완료 표시 제외)
   #    - "## 후속" 같은 헤더는 진짜 미결
   #    - "후속 작업: ✅ 처리됨" 같이 ✅·완료 동반은 제외
   echo "$BODY" | grep -nE -- '(TODO|FIXME)' \
     | grep -vE '(✅|완료|처리됨|done)'
   echo "$BODY" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)'
   echo "$BODY" | grep -nE '^\s*[-*0-9.]+\s.*(후속|미결|미결정|추후|나중에|별도로).*$' \
     | grep -vE '(✅|완료|처리됨|done)'
   ```

   해석:
   - `## 후속` 같은 진짜 헤더 → 차단
   - `- 후속: TODO ...` 같은 미결 항목 줄 → 차단 (✅·완료 표시 없으면)
   - 제목·메타 인용("`harness--..._followup` 후속 항목" 같은 설명) → 통과
   - "처리 결과"·"원본" 섹션 본문은 회고용이므로 제외

   매칭 있으면:
   - 어느 줄이 어떤 키워드를 포함하는지 사용자에게 보고
   - 둘 중 하나로 진행:
     - (a) 잔여를 별도 WIP로 분리 (`harness--<원래이름>_followup_<YYMMDD>.md`),
       원본은 completed로 이동, `relates-to: rel: caused-by`로 연결
     - (b) 본문에서 차단 키워드를 정말로 제거 후 재시도 (실제 해결됐다면)
   - 사용자 명시 우회 요청 없으면 (a)·(b) 외 다른 진행 금지.

   실측 사례: 2026-04-19 search_and_completion_gaps WIP가 본문에 "후속"
   키워드 6개 남긴 채 completed로 이동됐다가 잔여 4개 후속 WIP를 사후
   분리해야 했음. 이 검사가 자동화되면 처음부터 막힘.
2. 파일명 접두사(`{대상폴더}--`)로 이동 대상 결정.
3. `git mv`로 이동 (접두사 제거).
4. 프론트매터: `status` → completed/abandoned, `updated` → 오늘.
5. relates-to.path 경로 갱신 (자기 자신 + 자신을 참조하는 다른 문서).
6. **관계 제안**: 같은 도메인의 기존 문서와 관계가 있는지 확인:
   - incidents/ → decisions/에 같은 영역의 결정이 있으면 `caused-by`
     또는 `conflicts-with` 제안
   - decisions/ → 기존 decisions/에 같은 주제가 있으면 `supersedes`
     또는 `extends` 제안
   - guides/ → decisions/에 근거 문서가 있으면 `implements` 제안
   - 제안이지 강제가 아님. 자명하지 않으면 건너뜀.
7. clusters/{domain}.md에 추가.
8. INDEX.md 문서 수 갱신.

## Step 3. INDEX.md 갱신

docs/INDEX.md를 현재 문서 상태에 맞게 갱신한다:
- 도메인별 문서 수 카운트
- clusters/ 포인터 확인
- WIP 문서는 포함하지 않음

## Step 4. clusters/ 갱신

docs/clusters/{domain}.md를 갱신한다:
- 해당 도메인의 모든 문서 목록 (WIP 제외)
- 관계 맵 (relates-to 기반)
- 새 domain이 추가되었으면 cluster 파일 생성 (naming.md 도메인 목록에
  먼저 등록되어야 함)

## Step 5. 관계 맵 정합성

relates-to의 path가 실제 파일 위치와 일치하는지 확인한다:
- 문서가 이동되었으면 모든 relates-to 경로를 갱신
- 삭제된 문서를 가리키는 relates-to가 있으면 보고
- 양방향 관계 확인 (A→B가 있으면 B에서 A를 참조하는 게 자연스러운지
  제안)

## Step 6. CPS 문서 갱신 (implementation Step 4에서 호출)

CPS 문서(`docs/guides/project_kickoff_*.md`)를 갱신한다:

| 변경 유형 | 행동 |
|-----------|------|
| Context 전제 변경 | Context 섹션 갱신 |
| 새 Problem 발견 | Problem 섹션에 추가, 번호 부여 |
| Solution 방향 변경 | Solution 섹션 갱신, 변경 이유 기록 |
| 새 도메인 추가 | 도메인 목록 섹션 + naming.md 동기화 |

갱신 시 CPS 문서의 `updated` 프론트매터를 갱신한다.

## 출력 형식

### 검증 모드
```
## docs 정합성 검증

✅ 프론트매터: N개 문서 정상
⚠️ 프론트매터 오류:
  - decisions/foo.md: domain "xyz"가 naming.md에 없음
  - guides/bar.md: relates-to path "old/path.md" 존재하지 않음

✅ INDEX.md: 정상
⚠️ clusters/: harness.md에 누락된 문서 1개
  - decisions/harness_improvement_260408.md

수정이 필요한 항목: N개
```

### 이동 모드
```
## 문서 이동 완료

이동됨:
  WIP/decisions--api_design_260416.md → decisions/api_design_260416.md

갱신됨:
  - 프론트매터: status → completed, updated → 2026-04-19
  - clusters/auth.md: 문서 추가
  - INDEX.md: auth 도메인 문서 수 갱신
  - 관계 제안: decisions/old_api_decision.md (supersedes 후보)
```

## 주의

- 사용자 확인 없이 문서를 삭제하지 않는다.
- naming.md에 없는 domain을 임의로 만들지 않는다. 사용자에게 질문.
- WIP 문서의 relates-to가 비어 있는 것은 정상 (작업 중).
- completed 전환 차단 조건은 docs.md 규칙을 따른다.
- 답변은 한국어.
