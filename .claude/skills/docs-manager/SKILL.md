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

## Step 1. 프론트매터 검증

docs/ 하위 모든 .md 파일(WIP/ 포함)의 프론트매터를 검증한다:

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
   키워드(`TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`,
   `별도로`)가 있으면 이동 차단.
   - 별도 WIP로 분리할지 사용자에게 묻고, 분리되면 `caused-by` 관계로 연결.
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
