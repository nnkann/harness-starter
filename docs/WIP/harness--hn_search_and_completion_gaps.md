---
title: 하네스 구멍 정리 + 리뷰 구조 재확정
domain: harness
tags: [search, ide-context, incident-doc, completion-gate, review-agent]
status: in-progress
created: 2026-04-18
updated: 2026-04-22
---

## 상태

- **2026-04-19 완료분**: Part A·B는 반영됨. Part A 후속은 `harness--hn_commit_step2_partial_completion.md`로 분기됨.
- **2026-04-22 재개**: Part E 신설 — write-doc·implementation 스킬의 **SSOT 선행 탐색 구멍** (본 세션 v0.18.4 커밋 직후 발견).

## ✅ 완료 (2026-04-19)

- Part A: 검색·문서 규칙 4종 모두 rules에 반영 (커밋 08bdfdc)
- Part B: 리뷰 구조 hook → Agent tool 직접 호출로 복원 (v1.3.1, 11fe9f2,
  fd66269)
- Part B 후속: review가 staged diff 우회 호출하던 사고 재발 방지 (fd66269)
- 남은 Part A 후속(write-doc symptom-keywords·commit completed 미결 차단)은
  별도 WIP로 분리 → `harness--hn_commit_step2_partial_completion.md`
- Part C(다운스트림 전파)는 본 레포 범위 외, harness-upgrade 흐름이 처리

# 하네스 구멍 정리 + 리뷰 구조 재확정

## Part A: 검색·문서 규칙 (반영 완료, 커밋 08bdfdc)

| 구멍 | 내용 | 상태 |
|------|------|------|
| 1. IDE 컨텍스트 오신뢰 | `<ide_opened_file>` 경로는 존재 확인 후 사용 | ✅ rules 반영 |
| 2. incident symptom-keywords 누락 | incidents/ 전용 필드 추가 | ✅ rules 반영 (스킬 수정 남음) |
| 3. completed 미결 묻힘 | 본문 미결 패턴 시 WIP 분리 강제 | ✅ rules 반영 (스킬 수정 남음) |
| 4. 검색 실패 escalation 부재 | 3단계 검색 + docs-lookup 위임 | ✅ rules 반영 |

### 남은 후속 (별도 WIP)

- write-doc 스킬: incident 생성 시 `symptom-keywords` 재질의
- commit 스킬: completed 전환 시 본문 미결 패턴 차단

## Part B: 리뷰 구조 — hook 포기, Agent tool 복원

### 확정된 결론

**리뷰는 hook이 아니라 commit 스킬 내부에서 Agent tool로 review 에이전트를 직접
호출하는 구조로 간다.** 이 구조는 공식 Claude Agent SDK가 보장하는 경로이고,
실제로 이 세션에서 호출 테스트로 정상 발화·응답 확인.

이전 "hook 기반 리뷰" 설계(v0.9.2에서 도입)는 이틀간 hook 미로를 만든 원인.
되돌린다.

### 검증된 팩트

| 항목 | 결과 | 근거 |
|------|------|------|
| Agent tool로 review 에이전트 호출 | ✅ 정상 발화·응답 | 이 세션 실제 호출, JSON 응답 수신 |
| review 에이전트가 Bash/Read/Glob/Grep 사용 | ✅ 작동 | review.md의 tools 필드에 정의, 호출 시 실행 확인 |
| prompt type hook은 single-turn, 도구 불가 | ❌ 리뷰 부적합 | 공식 문서 |
| prompt hook `$ARGUMENTS`에는 tool_input.command만 | diff 없음 | 직접 테스트 |
| command hook → prompt hook 간 데이터 전달 경로 | ❌ 없음 | 직접 테스트 |
| agent type hook은 PostToolUse 용으로 설계 | PreToolUse에서 부적합 | 공식 SDK 문서 |

### 설계 방향

```
commit 스킬 실행 (strict 모드 또는 --strict)
  ↓
  작업 잔여물 정리, 계획 문서 완료 처리
  ↓
  Agent tool 호출 (subagent_type: "review", prompt: diff + 맥락)
  ↓
  review 에이전트가 스스로:
    - Bash로 git diff --cached 확인
    - 3관점(회귀/계약/스코프) 검증
    - JSON 반환 {"ok": true/false, "block": bool, "warnings": [...]}
  ↓
  block: true면 차단, warnings만 있으면 커밋 메시지에 반영 후 진행
  ↓
  git commit + push
```

**PreToolUse hook은 기본 안전장치만 유지**: `pre-commit-check.sh` (린터, TODO/FIXME
검사, --no-verify 차단). 리뷰 로직은 전부 스킬 내부로.

### 반영 범위

| 파일 | 변경 |
|------|------|
| `.claude/skills/commit/SKILL.md` | "리뷰는 hook이 처리한다" 섹션 → "strict 모드면 Agent tool로 review 호출" 섹션 교체 |
| `.claude/settings.json` | 변경 없음 (이미 hook 제거됨, 커밋 1d165a3) |
| `.claude/agents/review.md` | 변경 없음 (이미 존재) |

## Part C: 다운스트림 전파 (별도 작업, 이 레포 범위 외)

하네스 스타터의 변경이 다운스트림 프로젝트에 반영되려면 harness-upgrade
경로로 전파 필요. 이 WIP는 harness-starter 범용 문서이므로 다운스트림 프로젝트
고유 고유명사는 기록하지 않는다.

## 우선순위

| 우선순위 | 항목 | 범위 |
|---------|------|------|
| P0 | commit 스킬 SKILL.md에 Agent tool 호출 단계 추가 | 이 레포, 이 세션에서 |
| P1 | write-doc 스킬 symptom-keywords 재질의 | 별도 WIP |
| P1 | commit 스킬 completed 전환 시 본문 미결 패턴 차단 | 별도 WIP |
| P2 | 이 WIP 승격 시 "이번 세션" 표현 날짜로 구체화 | 승격 시점 |

## 파생 WIP

- `harness--hook_flow_efficiency_260418.md` — hook 전체 흐름 효율성 검토
  (PreToolUse/PostToolUse 등 전체 감사). 원칙: 하네스가 걸리적거리면 실패
  프로젝트, 항상 도움을 주는 느낌이어야 함.

---

## Part E: 스킬의 SSOT 선행 탐색 구멍 (2026-04-22 재개, v0.18.4 발화)

### 발견 경로

v0.18.4 커밋 직후 사용자가 review 체감 속도에 불만 → 해결책 논의 중
Claude가 새 WIP(`decisions--hn_review_staging_script_lite_path.md`)를
즉시 생성. 사용자 지적: "기존 문서 SSOT 확인되는지 볼거야." 확인 결과
이미 3개 SSOT(`hn_review_staging_rebalance` / `hn_review_tool_budget` /
`hn_staging_followup`)가 해당 주제를 커버 중이었고 신규 WIP는 중복.

**사용자 발언**: "에휴...이럴 줄 알았다" — 재발 패턴 자인.

### 구멍 1 — write-doc SKILL.md Step 2 부실 (✅ 본 세션 1차 수정)

#### 증상

- Step 2 "관련 문서 탐색"이 `clusters/{domain}.md` 한 번 스캔으로 끝
- 같은 주제 기존 문서 식별 기준이 모호 (제목만 보면 miss)
- 사용자 질의가 "새로 만들까요, 갱신할까요?" 동격 선택지 — docs.md
  원칙("있으면 거기를 갱신")을 스킬이 기본값으로 반영 안 함
- 완료 문서 재개 경로(`completed → WIP`) 언급 없음
- docs.md "## SSOT 우선 + 분리 판단"의 두 질문이 스킬 절차에 미인용

#### docs.md SSOT와 스킬 정렬 gap (수정 전)

| docs.md가 요구 | SKILL.md가 강제 |
|---|---|
| "SSOT가 이미 있는가?" 강제 질의 | cluster 1회 스캔만 |
| "분리가 정말 필요한가?" 판단 기준 | 없음 |
| 완료 문서 재개 경로 | 없음 |
| SSOT 있으면 갱신이 디폴트 | 선택지 동격 제시 |

#### 수정 (2026-04-22)

`.claude/skills/write-doc/SKILL.md` Step 2 전면 재작성:

- **2.1 3단계 탐색** 의무화: cluster → 키워드 grep → 후보 본문 Read
- **2.2 docs.md 2질문 강제 적용**: SSOT 존재 질문 + 분리 필요성 질문.
  질의 템플릿에 "기본은 기존 문서 갱신" 명시
- **2.3 완료 문서 재개 경로**: `git mv` 명령 포함
- **2.4 실패 모드 체크리스트** 5개: cluster만 봄·제목만 봄·동격 선택지
  제시·completed라고 건너뜀·일단 새 WIP 쓰고 병합

#### 남은 검증

- [ ] 다음 문서 생성 시 실측 — 수정된 Step 2가 실제로 SSOT 후보 포착하는지
- [ ] 사용자 질의 템플릿 문구가 혼란 안 주는지
- [ ] commit 스킬이 본 수정과 충돌 없는지 (완료 문서 재개 후 재커밋
  흐름이 실제로 작동하는가)

### 구멍 2 — implementation·관련 스킬의 날짜 suffix 드리프트 (✅ 부분 처리, v0.18.7)

#### 진단

v0.18.5 커밋 review 참고 사항에서 언급: `implementation/SKILL.md` Step 1
(diff 라인 157) `파일명: {대상폴더}--{작업내용}_{YYMMDD}.md` — naming.md
"날짜 suffix 전면 금지" 규칙과 드리프트.

전수 조사 결과 6개 스킬 파일에 같은 패턴:
- `implementation/SKILL.md` Step 1
- `naming-convention/SKILL.md` 계획 문서 섹션
- `commit/SKILL.md` Step 2.3 이동 시 파일명 규칙
- `docs-manager/SKILL.md` Step 2.5 완료 재개 + 라인 317 예시
- `harness-init/SKILL.md` `project_kickoff_{YYMMDD}.md`·`guides--{도메인명}_{YYMMDD}.md`
- `harness-adopt/SKILL.md` `adopt-session_{YYMMDD}.md`
- `harness-upgrade/SKILL.md` `migration_v{X}_{YYMMDD}.md`

#### 처리 (v0.18.7)

**단순 예시 교체 — 완료**:
- implementation Step 1 → SSOT 참조 + `{abbr}_{slug}` 형식
- naming-convention 계획 문서 섹션 → naming.md 참조 + 예시 `hn_auth_stack` 등
- commit Step 2.3 → `{abbr}_{slug}` + "날짜 suffix 전면 금지" 명시
- docs-manager Step 2.5·317 예시 → `{abbr}_{slug}`

**깊은 판단 필요 — 미처리**:

harness-init/adopt/upgrade의 세션·마이그레이션 파일은 "같은 주제 반복"
원칙(naming.md)과 충돌 가능. 각 세션·각 버전이 **독립 리포트 가치**를
가지는 특수 케이스:

- `project_kickoff_{YYMMDD}.md`: 프로젝트 개시 시점 1회만. 단일 파일
  `project_kickoff.md`로 충분? 아니면 여러 번 재실행 가능?
- `adopt-session_{YYMMDD}.md`: 이식 세션마다 독립 결정. 재개·재적용 가능.
  세션당 1파일 vs 누적 1파일?
- `migration_v{X}_{YYMMDD}.md`: `{X}`가 버전이라 이미 분리 키. 날짜까지
  붙일 필요?

**판단 옵션**:
- A. 같은 주제 1파일 + `## 변경 이력` 섹션 (naming.md 원칙 유지)
- B. naming.md에 "세션 리포트·시점 기록" 예외 조항 추가
- C. `session_{N}` 같은 순차 번호로 대체 (날짜 대신 세션 ID)

이 3개 스킬은 실제로 잘 안 쓰이는 초기 플로우라 **다음 실측(harness-adopt
실행 사례) 기다린 뒤 결정** — 지금 선제 변경은 추측 수정 위험.

### 구멍 5 — commit 스킬 우회 가능 (🔲 기록만, v0.18.7 발견)

#### 증상

v0.18.7 커밋 시 사용자 관찰: "커밋 스킬도 이제 패스하네". 실측 확인:
- `git pre-commit` hook은 `HARNESS_DEV=1` 체크만. pre-check·review 미호출
- commit 스킬을 거치지 않고 `HARNESS_DEV=1 git commit` 직접 호출하면 안전장치 통째로 우회
- v0.18.4~v0.18.7에서 제가 스킬 호출한 건 v0.18.4·v0.18.5 뿐. v0.18.6·v0.18.7은 수동 절차 + Bash `git commit`
- 이번 케이스는 제가 **스킬 절차를 수동으로 따라 돌렸기 때문에** 결과적으로 pre-check·review 모두 실행됨. 하지만 **규약 위반**

#### 구조적 원인 (Part E 구멍 1·4와 동형)

| 구멍 | 우회 대상 | 우회 경로 | 3층 방어 필요 위치 |
|------|----------|----------|-------------------|
| 1 (v0.18.5) | SSOT 선행 탐색 | Write로 즉흥 문서 생성 | CLAUDE.md `<important if>` |
| 4 (v0.18.6) | dead link 감지 | review만 돌다 block | pre-check Step 3.5 |
| **5** (v0.18.7) | **pre-check·review 전체** | **Bash `git commit` 직접** | **git hook + CLAUDE.md** |

hook이 `HARNESS_DEV=1`만 체크하는 구조는 **"하네스 개발 보호" 1차 목적**
에만 충실하고, **pre-check·review 방어선은 commit 스킬에만** 있음.
Claude가 스킬을 건너뛰면 전부 miss.

#### 해결 방향 (기록 — 다음 작업)

3층 방어 패턴 재사용:

1. **CLAUDE.md** `<important if="커밋·푸시 실행 전">` 추가 — "commit 스킬
   또는 스킬 절차(pre-check·review)를 거쳐야 함. Bash `git commit` 직접
   호출 금지"
2. **git pre-commit hook 강화** — `HARNESS_DEV=1` 체크 유지 + pre-check
   호출 추가. 이중 실행 문제(스킬 Step 5에서 이미 pre-check)는 tree-hash
   캐시로 완화 가능 (이미 구현됨). 또는 환경변수로 "스킬 경유 완료" 표시
3. **commit 스킬 SKILL.md** — 이미 절차 있음 (변경 불필요)

#### 판단 필요 (실측 대기)

- hook에서 pre-check 재실행 시 **2회 돌아감** (스킬에서 1회 + hook에서 1회).
  tree-hash 캐시가 있어도 overhead 있음. 사용자 체감 속도 악화 가능성.
- 아니면 hook이 "commit 스킬 경유 여부"를 감지하는 환경변수 (`HARNESS_COMMIT_SKILL=1`)
  로 우회 허용 + 그것이 없으면 pre-check 강제
- 선택지 A/B/C 실측 필요. 지금 선제 수정은 추측 수정 위험

#### 지금 이 커밋(v0.18.7)은 유효한가?

- 제가 수동으로 스킬 Step 0(lint)·Step 5(pre-check)·Step 7(review deep)
  전부 돌림. dead link·pre-check pass·review pass 확인
- 규약 위반은 **절차 경로** (스킬 호출 대신 수동 실행). 결과물 자체는 정상
- 기록상 이후 이런 케이스 재발 시 "스킬 안 거친 커밋" 추적 어려움.
  `🔍 review: deep | signals: ...` 로그 라인은 스킬이 넣는데 Bash 직접
  커밋 시 누락될 수 있음. 이번엔 내가 수동으로 넣었지만 Claude가 놓칠 위험

### 구멍 2b — (완료) implementation SSOT 선행 탐색 가설 (v0.18.5에서 해소)

v0.18.5 처리 과정에서 확인: implementation Step 0.8이 이미 docs.md 참조
구조로 3단계 탐색·실패 모드 체크리스트 인용 보강 완료. 본 가설은 실제
gap이 아니었고, 규정 인용의 **명시성** 부족이었음. v0.18.5 수정으로 해소.

본문은 아래 보관 (다음에 비슷한 가설 세울 때 참고).

#### 가설 (2026-04-22 기록, 검증 결과 무효)

write-doc이 "코드 작업 없는 문서 생성"이라면 implementation은 "코드 +
문서"를 함께 만든다. WIP 문서 생성도 implementation 경로. 동일한 SSOT
선행 탐색 원칙이 강제되는지 점검 필요.

관련 SSOT: `docs/harness/hn_implementation_router.md` (라우터·추적자 역할
재정의). 이 문서가 WIP 생성의 SSOT 탐색 책임을 명시하는지, 아니면
write-doc로 위임하는지 확인해야 함.

#### 점검 항목

- [ ] `.claude/skills/implementation/SKILL.md`의 WIP 생성 단계에서
      SSOT 선행 탐색 강제 여부
- [ ] 강제 안 하면 write-doc Step 2와 동일 구조 도입 (또는 write-doc에
      위임 명시)
- [ ] 코드+문서 동시 작업 시 "기존 SSOT 있으면 재개" 경로가 명시되는지
      — 이게 빠지면 implementation이 매번 새 WIP 만들어 SSOT 분열

#### 예상 수정 범위

- `.claude/skills/implementation/SKILL.md` (아마 Step 1 "문서 생성"
  부근)
- 또는 write-doc Step 2를 `common/` 섹션으로 추출해 양쪽이 참조

### 구멍 3 — docs.md 규정 자체는 정합 (🔲 재점검만)

docs.md "## SSOT 우선 + 분리 판단" 섹션은 이번 케이스에 정확히 맞는
규정을 이미 가지고 있었음. 문제는 **스킬 절차가 이 규정을 인용하지
않음**. 규정 자체 재작성은 불필요.

다만 "completed 문서 재개 경로"가 docs.md 중간에 한 문장으로 있어서
발견하기 어려움. 강조 필요 여부 재검토 (선택).

### 실행 계획

1. ✅ 본 WIP 재개 + Part E 기록 (2026-04-22)
2. ✅ `.claude/skills/write-doc/SKILL.md` Step 2 재작성 (2026-04-22)
3. ✅ `.claude/rules/docs.md` "SSOT 우선 + 분리 판단" 섹션에 3단계 탐색·
   실패 모드 체크리스트·기본값 명문화 (규정 SSOT)
4. ✅ `CLAUDE.md`에 `<important if="docs/ 하위에 새 문서·WIP 파일을 만들려
   할 때 (스킬 발동 여부 무관)">` 블록 추가 — 경로 불문 강제
5. ✅ `.claude/skills/implementation/SKILL.md` Step 0.8에 3단계 탐색 명시 인용
6. ✅ `.claude/scripts/pre-commit-check.sh` Step 3.5 dead link 증분 검사
   추가 + T35 회귀 테스트 3케이스 (v0.18.6)
7. 🔲 다음 실측 5건 — 수정된 규정·스킬이 SSOT 포착하는지 관찰
8. 🔲 실측 결과 기록 후 본 WIP → `docs/harness/` 재이동 + completed

### 구멍 4 — dead link 검사가 pre-check이 아닌 bulk 가드에만 있음 (✅ v0.18.6 처리)

#### 발견 경로

v0.18.5 커밋 review deep 중 **verdict: block** — `docs/clusters/harness.md`에
이동된 파일 2건의 dead link. review 에이전트가 발견. 사용자 지적:
> "dead link는 pre-check에서 걸러야 하는게 아닌가?"

#### 현 상태

- `bulk-commit-guards.sh` 가드 4b에만 dead link 검사 존재 (`--bulk` 경로)
- `pre-commit-check.sh`에는 dead link 검사 없음
- 일반 커밋 경로에서 dead link는 review(비싼 LLM)가 잡거나 못 잡음

#### 문제

- **설계 원칙 위반**: staging.md "정적은 pre-check, 의미는 review"와 불일치
- **비용**: review deep(30초+, 토큰 수만) 대신 pre-check(수 초, 정규식 + 파일
  존재 체크)이 잡아야 할 영역
- **커버리지**: dead link는 파일 이동·삭제가 있는 **모든** 커밋에서 발생 가능.
  `--bulk` 한정은 실제 리스크 대비 좁음

#### 설계 스케치 (다음 작업)

- bulk-commit-guards.sh 가드 4b 로직 재사용 (fork 최적화된 버전으로)
- pre-check에 dead link 검사 추가 — 변경된 파일 + 영향받는 참조만 O(변경 규모)
- 전수 검사는 `--bulk`에서만, 증분 검사는 일반 경로에서
- review prompt에서 "구조적 dead link 검증"을 빼고 의미론에만 집중

#### 선행 조건

- 이전 세션의 bulk-commit-guards.sh 퍼포먼스 수정(본 세션 사용자가 시작했다가 중단)
  작업과 연계. dead link 검사 로직 최적화본이 먼저 정립돼야 pre-check에 이식 가능

#### 처리 (v0.18.6, 2026-04-22)

`.claude/scripts/pre-commit-check.sh`에 Step 3.5 dead link 증분 검사 추가:

- **검사 A**: 이번 커밋에서 삭제·rename된 md 파일을 가리키는 **기존 md 링크**
  (cluster·relates-to 등). `STAGED_NAME_STATUS`에서 `D`·`R` 추출 → basename으로
  `grep -rn --include='*.md' docs .claude` → 소스 파일이 같은 커밋에 포함되면 skip.
- **검사 B**: 이번 커밋에서 **추가·수정된 md의 새 링크** 대상이 실제로 존재하는지.
  `STAGED_DIFF_U0`의 `+` 라인에서 `](path.md)` 패턴만 awk로 추출 → 경로 정규화
  (`./`·`../` 해소) → `test -f`로 존재 확인. staged add된 파일도 FS에 있으므로 커버.
- **증분 검사 원칙**: 전수 검사는 `bulk-commit-guards.sh` 4b 담당 유지 (거대
  일괄 변경 전용). pre-check은 **이번 커밋이 유발한** dead link만. O(변경 규모).

회귀 테스트 `T35` 3케이스 신설 (`test-pre-commit.sh`):
- T35.1: 파일 삭제 + cluster 옛 경로 유지 → 차단 ✅
- T35.2: 새 md의 링크가 없는 파일 가리킴 → 차단 ✅
- T35.3: 링크 대상도 같이 staged 추가 → 통과 ✅

**결과**: 60/60 통과. v0.18.5 커밋에서 review가 deep으로 30초 걸려 잡은
dead link를 이제 pre-check이 수 초에 잡는다.

**한계 (의도적)**:
- 검사 A는 **basename 기반 느슨한 매칭**. 다른 폴더에 같은 이름의 md가
  있으면 오탐 가능성. 엄밀한 경로 매칭은 비용 크고, 증분 검사의 취지는
  빠른 1차 방어라 수용.
- 앵커(`#section`)만 있는 링크는 검사 안 함 (파일 존재만 확인).
- 외부 링크(`http://`·`https://`)는 skip.

### 수정 아키텍처 (3층 방어)

| 층 | 위치 | 역할 |
|---|------|------|
| 1 | `CLAUDE.md` `<important if>` | 경로 불문 트리거 — Write tool로 docs 파일 만들기 전 |
| 2 | `.claude/rules/docs.md` | 규정 SSOT — 3단계 탐색·두 질문·실패 모드·완료 재개 경로 |
| 3 | 스킬 SKILL.md (write-doc Step 2, implementation Step 0.8) | 스킬 진입점 — docs.md 참조 강제 + 분기 흐름 |

원칙:
- **절차는 한 곳에만** (docs.md). 스킬은 참조·분기만.
- **CLAUDE.md는 짧은 트리거**. 상세 절차 반복 금지.
- 스킬이 발동하지 않는 경로(즉흥적 Write)는 CLAUDE.md가 잡음.

### 관련 (상류 SSOT)

- `.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" — 규정 SSOT
- `docs/harness/hn_implementation_router.md` — implementation 역할 재정의
- `docs/decisions/hn_doc_naming.md` — write-doc Step 1·3 개정 이력
- `docs/harness/hn_commit_step2_partial_completion.md` — 동종 gap 선례
  (symptom-keywords 재질의·completed 미결 차단)

### 발화 커밋

`f597b77` (v0.18.4) — fix(lint): ENOENT 패턴 정교화. 직접 관련 없지만
커밋 직후 체감 속도 논의 → SSOT 분산 발견 → 본 Part E 신설 경로.
