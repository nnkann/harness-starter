---
name: commit
description: 작업 잔여물 정리, 계획 문서 완료 처리, 변경 사항 분석 후 커밋+푸시. review 강도는 staging 자동 판정 + `--quick`/`--deep`/`--no-review` 플래그로 제어. `/commit` 또는 "커밋해줘" 요청 시 사용.
---

# /commit 스킬

커밋 과정에서 작업 잔여물을 정리하고, 계획 문서를 완료 처리하며,
작업 중 얻은 컨텍스트를 Git 히스토리에 보존한다.

## 고유 책임 (이 스킬만 하는 것)

1. 플래그 결정 (--quick/--deep/--no-review)
2. 작업 잔여물 정리 (WIP completed 이동·clusters 갱신 트리거)
3. pre-check 호출 + 결과 해석 (차단·재시도 판정)
4. review 호출 조립 (호출자 self-containment 유지)
5. 커밋 메시지 작성 + git log 추적성 라인 기록
6. push 실행

## 위임 대상 (여기서 하지 않는 것)

| 영역 | 위임 |
|------|------|
| diff 단위 회귀·계약·스코프 검증 | review |
| 문서 이동·clusters 정합성 실행 | `.claude/scripts/docs_ops.py` |
| 누적 드리프트·전체 코드베이스 분석 | eval |
| 시크릿 1차 차단 | `.claude/scripts/pre_commit_check.py` + gitleaks |

## 핸드오프 계약 (상속)

핸드오프 계약 SSOT는 `.claude/skills/implementation/SKILL.md` "## 핸드오프
계약" 섹션 상속. commit 축 구체화:

| 축 | 내용 |
|----|------|
| Pass (implementation→나) | WIP 파일 경로 · status · CPS 갱신 여부 |
| Pass (pre-check→나) | `wip_problem` · `wip_solution_ref` · `ac_review` · `ac_tests` · `ac_actual` · `recommended_stage` · `s1_level` (스키마 SSOT: `pre_commit_check.py`) |
| Pass (나→review) | 아래 "review 호출" 섹션이 이 Pass 블록을 조립한다 (self-containment) |
| Preserve | pre-check stage·wip_problem·wip_solution_ref·ac_review 원본 (재계산 금지) · 사용자 플래그 |
| Signal risk | ⛔ pre-check 3회 연속 차단·시크릿 line-confirmed · ⚠️ stage 격상 사유 · 🔍 검증 흔적 |
| Record | commit log `🔍 review: <stage> \| problem: P# \| solution-ref: S#` 한 줄 (Stage 0 포함) |

**self-containment 원칙**: commit은 호출자로서 스스로 prompt를 조립한다.
review.md는 입력 계약(무엇을 받는가)만 보유하며, commit이 그 계약을
내재화된 템플릿으로 충족한다. 호출자가 피호출자 파일을 Read해야 prompt
를 조립할 수 있다면 설계 오류 (Anthropic Agent Skills 권장).

| 사용법 | 설명 |
|--------|------|
| `/commit` | staging 자동 판정으로 review stage 결정 (skip/micro/standard/deep). |
| `/commit --no-review` | 리뷰 스킵 (커밋 메시지에 `[skip-review]` 태그 포함). Step 1~6 공통 단계(버전 체크 포함)는 그대로 실행. |
| `/commit --quick` | review stage 1(micro) 강제. 자동 분류 무시. |
| `/commit --deep` | review stage 3(deep) 강제. 자동 분류 무시. |

> **light/strict 모드 폐기 (audit #2·9, 2026-04-22)**: CLAUDE.md `하네스
> 강도` 필드 + `--light`·`--strict` 플래그 제거. staging이
> `skip/micro/standard/deep` 4단계 + `recommended_stage` 판정으로 강도
> 조절을 이미 완비. light(위험도 hit 시 review) = staging의 `skip/standard`
> 판정과 동일. strict(항상 review)는 `--deep`으로 대체.

## 리뷰는 스킬이 Agent tool로 직접 호출한다

코드 리뷰는 이 스킬이 `Agent` tool로 review 서브에이전트(`.claude/agents/review.md`)를
직접 호출한다. hook은 쓰지 않는다. 호출 여부·강도는 **staging 자동 판정**
(pre-check stdout `recommended_stage`) + 플래그 오버라이드로 결정 —
`rules/staging.md` SSOT.

### 호출 방법

스테이징 + Step 4 버전 체크 후 `git commit` 직전에 호출한다.

**핵심 원칙: review는 WIP AC를 먼저 읽고, 필요한 파일만 직접 Read한다.**
diff 전체를 prompt에 박지 않는다. AC가 검증 범위를 선언하므로 review가
스스로 관련 파일을 Read해서 확인하는 구조다.

```
Agent tool 호출
  subagent_type: "review"
  prompt: 아래 블록 5개를 그대로 포함
    1. ## 이번 커밋의 목적 (1~2줄)
    2. ## 연관 WIP 문서 (경로 또는 "없음") — AC 전문 포함
    3. ## 전제 컨텍스트 (review가 알아야 할 배경 사실)
    4. ## pre-check 결과 (wip_kind·has_impact_scope·recommended_stage·s1_level·already_verified)
    5. ## 지시
```

### 연관 WIP 문서 블록 (AC 전문 포함 — 핵심)

review는 WIP AC를 검증 기준으로 삼는다. **WIP 파일 경로만이 아니라 AC 전문을
이 블록에 직접 박는다**:

```bash
WIP_PATH="docs/WIP/decisions--hn_foo.md"
WIP_AC=$(grep -A 20 "Acceptance Criteria" "$WIP_PATH" 2>/dev/null | head -20)
```

### 전제 컨텍스트 블록 (필수 — review 오판 방지)

- `is_starter: true|false` — `.claude/HARNESS.json`에서 읽음
- 변경이 의존하는 기존 파일·구조 (Claude가 알지만 AC에 안 나타나는 사실)
- 최근 관련 커밋 SHA + 한 줄 요약 (필요 시)

```bash
IS_STARTER=$(grep -o '"is_starter":[[:space:]]*\(true\|false\)' .claude/HARNESS.json 2>/dev/null | grep -oE '(true|false)')
[ -z "$IS_STARTER" ] && IS_STARTER="false"
```

### prompt 예시

```
## 이번 커밋의 목적
<1~2줄>

## 연관 WIP 문서
경로: docs/WIP/decisions--hn_foo.md

Acceptance Criteria:
- [ ] Goal: 이 작업의 납득 기준 1줄
- [ ] 세부 조건 1
- [ ] 영향 범위: staging.md — AC kind 기반 규칙 회귀 체크

## 전제 컨텍스트
- is_starter: true
- <배경 사실>

## pre-check 결과
already_verified: lint todo_fixme test_location wip_cleanup
wip_kind: refactor
has_impact_scope: true
recommended_stage: deep
s1_level:

## 지시
WIP AC를 검증 기준으로 삼아라. AC 항목을 하나씩 확인하고,
`영향 범위:` 항목이 있으면 해당 파일을 Read해서 회귀 체크.
diff가 필요하면 `git diff --cached`를 직접 실행해서 확인해도 된다.

응답 첫 2줄은 무조건 다음 형식으로 시작 (분석 요약·서론 금지):
## 리뷰 결과
verdict: pass | warn | block
나머지 형식은 review.md "## 출력 형식" SSOT.
```

review 에이전트는 AC를 기준으로 필요한 파일을 Read/Glob/Grep으로 확인하고,
필요 시 `git diff --cached`를 직접 실행한다. AC가 검증 스코프를 선언하므로
diff 전체를 미리 전달하지 않는다.

### 응답 처리 (review.md SSOT 출력 파싱)

review 응답의 **첫 2줄**이 다음 형태여야 한다 (review.md "## 출력 형식"
SSOT):

```
## 리뷰 결과
verdict: pass | warn | block
```

**정상 경로**: `verdict:` 값으로 분기:
- `verdict: block` → 커밋 차단. [차단] 섹션을 사용자에게 전달, 수정 후 재시도.
- `verdict: warn` → 경고 표시 후 진행. [주의] 섹션을 커밋 메시지에 요약.
- `verdict: pass` → 그대로 진행.

**verdict 누락 시 (폼 위반)**: 다음 순서로 처리. 내용만 보고 임의 판정 금지.

1. **1차 재호출**: 같은 입력을 review에 재전달하며 "이전 응답에 verdict
   헤더가 누락됐다. review.md '## 출력 형식' SSOT 따라 첫 2줄 `## 리뷰
   결과` + `verdict: X`로 시작해 다시 응답하라" 명시.
2. **재호출도 누락**: 사용자에게 보고 + 진행 여부 확인. 내용이 명확히
   pass면 사용자 승인 받고 진행 가능. block·warn이면 반드시 재수정.
3. 이 케이스를 commit 메시지 본문에 `[review-form-warn]` 태그로 기록해
   추적 가능하게 한다.

### 투명성

- 스킬 메시지로 "🔍 review 에이전트 호출 중..." 한 줄 선행 알림
- 응답 수신 후 "✅ 리뷰 통과" 또는 "⚠️ 리뷰 경고: ..." 또는 "🚫 리뷰 차단: ..." 요약

---

## 공통 단계 (light + strict)

> **Step 0 린터 조기 체크 폐기 (audit #1, 2026-04-22)**: 린트는 Step 5
> 전체 pre-check에서만 실행. Step 1~4(잔여물·WIP·스테이징·버전)는 1초
> 이하로 조기 종료 이점 미미. 린트 실패 시 staged 유지 → 사용자가 수정
> 후 재커밋하면 기존 staged + 수정분 함께 커밋. `--lint-only` 모드 제거됨.

> **work-verify 워크플로우**: commit 스킬은 pytest·린터를 직접 실행하지 않는다.
> 테스트는 구현 완료 시점(work-verify)에서 이미 통과됐어야 한다.
> commit 스킬의 역할은 staged 상태의 커밋 가능 여부(commit-check)와 diff 안전성(review)이다.
> `self-verify.md` "## 검증 워크플로우" 참조.

### 1. 작업 잔여물 정리

커밋 전 임시 파일이 포함되지 않도록 정리한다.

- 현재 컨텍스트에서 알 수 있는 임시 파일을 찾아 확인한다.
  (예: 루트의 test-*.mjs, debug/ 내 일회성 스크립트 등)
- 용도가 끝난 파일은 삭제한다.
- 테스트/디버그 스크립트로 인한 좀비 프로세스가 남아있는지 확인한다.
- 사용자가 남겨두길 명시한 파일은 제외한다.

> **prior_session_files 경고 (Step 5 pre-check 후 확인)**:
> pre-check stdout의 `prior_session_files` 값이 `none`이 아니면 사용자에게
> 1줄 환기: "이전 세션 잔여 의심: <파일 목록>. 현재 작업과 별도 커밋이
> 맞는지 확인." 사용자가 "같이 커밋"이라 답하면 그대로 진행. 강제 분리 없음.

### 2. 계획 문서 이동 (사용자 명시 요청만)

docs/WIP/ status 변경·이동은 **사용자가 명시 요청한 경우에만** 수행.

> **자동 매칭 + ✅ 표시는 Step 7 review pass 직후로 이동 (audit #3,
> 2026-04-22)**. review block 시 수정·재staging 사이클에서 ✅ 덮어쓰기
> 방지. review pass = staged 확정 최종 상태 → 이 시점이 올바름.

#### 2.1. 명시 요청 처리 (사용자가 직접 말한 경우만)

사용자가 "WIP 정리해줘", "이거 completed로 옮겨줘", "잔여를 분리해줘"
같이 **명시적으로** 요청한 경우에만 다음 동작 수행:

| 사용자 요청 | 동작 |
|------------|------|
| "completed로 이동" | `python3 .claude/scripts/docs_ops.py move <WIP파일>` — status=completed, 파일 이동, 차단 키워드 검사 + **역참조 dead link 자동 갱신** 수행. 이후 `python3 .claude/scripts/docs_ops.py cluster-update`로 clusters 갱신. **`git mv` 직접 사용 금지 — 역참조 갱신이 누락됨** |
| "부분 완료, 잔여 분리" | (a) 잔여를 `<원래이름>_followup.md`로 신설, `relates-to: rel: extends` (b) 원본은 `docs_ops.py move` 호출 |
| "abandoned로 보내" | (a) status → abandoned (b) archived/로 수동 이동 |

사용자가 안 물으면 안 한다.

#### 2.1.1. archived 이동 시 CPS grep 자동 실행

"abandoned로 보내" 요청으로 archived 이동이 발생하면, 이동 직후 CPS 파일에서
해당 파일명을 자동으로 grep해 결과를 출력한다. 질문하지 않고 흐름을 계속한다.

```bash
# archived 이동한 파일명 (확장자 제외)
ARCHIVED_SLUG=$(basename "<이동한파일>" .md)

# CPS 파일 자동 탐색 (project_kickoff.md 또는 tags: cps 포함 파일)
CPS_FILE=$(grep -rl "tags:.*cps" docs/ 2>/dev/null | head -1)

if [ -n "$CPS_FILE" ]; then
  GREP_RESULT=$(grep -n "$ARCHIVED_SLUG" "$CPS_FILE" 2>/dev/null)
  if [ -n "$GREP_RESULT" ]; then
    echo "→ CPS 언급 확인됨 ($CPS_FILE):"
    echo "$GREP_RESULT"
    echo "→ CPS ssot: 링크 갱신이 필요할 수 있습니다 (계속 진행)"
  fi
fi
```

언급 없으면 출력 없이 통과. 언급 있으면 해당 라인을 보여주고 흐름 계속.

#### 2.2. 이동 시 파일명 규칙

파일명 형식: `{대상폴더}--{abbr}_{slug}.md` (SSOT: `.claude/rules/naming.md` "파일명 — WIP")

`--` 앞의 접두사로 이동 대상을 결정하고, **이동 시 접두사(`{대상폴더}--`)를 제거**한다.
**날짜 suffix 전면 금지** — 발생 시점은 프론트매터 `created` + git history.

| 접두사 | 이동 대상 | 이동 후 파일명 |
|--------|----------|---------------|
| `decisions--` | docs/decisions/ | 접두사 제거 |
| `guides--` | docs/guides/ | 접두사 제거 |
| `incidents--` | docs/incidents/ | 접두사 제거 |
| `harness--` | docs/harness/ | 접두사 제거 |
| 접두사 없음 또는 판단 불가 | 사용자에게 질문 | — |

예시: `docs/WIP/decisions--hn_api_design.md` → `docs/decisions/hn_api_design.md`

#### 2.3. 차단 조건 (docs.md 규칙)

**SSOT**: `.claude/rules/docs.md` "## completed 전환 차단" 섹션. status를
completed로 전환할 때 키워드 hit 시 [c] 차단. 키워드 목록·예외 규칙은
rules/docs.md 참조.

→ 차단 시 사용자에게 [p] 분리 권장 (잔여를 별도 WIP로 옮기면 해제).

#### 2.4. 제약

- 계획 문서 이동 요청이 없으면 이 단계 전체 스킵
- 이동 대상은 docs/ 규칙에 정의된 폴더만 허용 (decisions, guides, incidents, harness, archived). 새 폴더 금지
- 이동·갱신은 `python3 .claude/scripts/docs_ops.py` 서브커맨드로 처리
  (audit #10, 2026-04-22 — docs-manager 스킬 폐기, 332줄 → 스크립트화)
- **자동 status 변경·이동 금지** — 사용자가 명시 요청한 경우에만 (잘못된 자동 판단으로 정보 손실 위험)

### 3. 스테이징

`git status`로 변경 파일 확인 후, 특별한 제외 요청 없으면 `git add .`

**메타 파일 자동 병합 (분리 커밋 차단)**:

Step 4(버전 체크)에서 버전 범프가 있었거나, 본 커밋의 변경으로 인해 다음 메타
파일이 함께 갱신되어야 한다면 **본 커밋에 자동 포함**한다 (분리 커밋 만들지
마라):

- `.claude/HARNESS.json` (버전 범프 시)
- `docs/clusters/*.md` (문서 추가·이동 시)

이유: 이 메타 파일을 별도 커밋으로 분리하면 review가 두 번 돌고, 두
번째 커밋은 의미 있는 검증이 불가능 (버전 1자리 변경에 6카테고리 검증).
0d047a5 이후 면제 리스트가 도입되어 분리할 이유가 사라졌다.

### 4. 하네스 버전 체크 + 연동 갱신 (harness-starter 전용 — audit #4, 2026-04-22)

> **`is_starter: true`인 업스트림에서만 실행.** 다운스트림은 이 Step 전체를 건너뛴다.

`HARNESS.json`의 `is_starter` 값을 먼저 확인한다:

```bash
python3 -c "import json; d=json.load(open('.claude/HARNESS.json')); print(d.get('is_starter', False))"
```

- `False` (다운스트림) → **Step 5로 즉시 진행. 아래 내용 실행하지 않는다.**
- `True` (업스트림) → 계속:

> **Step 3 이후 실행 필수** — 스크립트가 staged 파일을 읽어 범프 타입을 결정한다.
> 스테이징 전에 실행하면 항상 "staged 없음"으로 오판. (2026-04-28 누락 원인)

```bash
python3 .claude/scripts/harness_version_bump.py
```

업스트림은 stdout에 `version_bump: minor|patch|none` + 근거를 출력.

**버전 범프 기준** (스크립트 내장):

| 변경 유형 | 범프 | 예시 |
|-----------|------|------|
| 스킬/에이전트/규칙 **신설** 또는 폴더 구조 변경 | minor | 에이전트 추가, docs/ 리팩토링 |
| 기존 스킬/스크립트/규칙 **로직 수정**, 버그 수정 | patch | pre-commit 조건 추가, 경로 오류 수정 |
| 문서·주석·오타만 | none | README 업데이트, 프론트매터 수정 |

**`version_bump: none`** → Step 5로 진행.

**`version_bump: patch|minor`** → 사용자 확인 후 아래 5개를 **한 번에** 처리:

1. **HARNESS.json** — `version` 필드를 `next_version` 값으로 갱신
2. **MIGRATIONS.md** — `docs/harness/MIGRATIONS.md` 상단(기존 섹션 위)에 새 버전 섹션 삽입.
   포맷 SSOT는 MIGRATIONS.md 상단 "## 포맷" 섹션:
   - 변경 내용: staged diff에서 다운스트림 영향 변경 추출
   - 적용 방법: 자동/수동 분류. 수동 없으면 `없음` 명시 (생략 금지)
   - 검증: 확인 명령어 (생략 가능)
3. **MIGRATIONS archive 자동화** — 새 섹션 추가 후 즉시 실행:
   ```bash
   python3 .claude/scripts/harness_version_bump.py --archive
   ```
   본문 6개째부터 `MIGRATIONS-archive.md`로 자동 이동. 5개 이하면 멱등성
   유지(이동 안 함). 매번 호출 — staged 추가 후 자동 archive로 본문 비대화
   방지 (v0.30.1 정책).
4. **README.md** — 상단 `현재 버전: **vX.Y.Z**` 번호 갱신 + 변경 이력 섹션
   상단에 항목 추가. **최신 5개만 유지** — 6번째 섹션 추가 시 가장 오래된
   섹션 삭제 (수동, archive로 안 옮김 — README 변경 이력은 git log + MIGRATIONS-archive로 충분).
5. **git add** — `HARNESS.json`, `MIGRATIONS.md`, `MIGRATIONS-archive.md`(있으면), `README.md` 일괄 스테이징

> **과거 `docs/harness/promotion-log.md` 폐기 (v0.20.7)**: git log가 유일 SSOT.

**스크립트 제안이 애매하거나 사용자 의도와 다르면** 사용자에게 묻는다.
자의적으로 올리지 않는다.

### 5. pre-check (정적 검사 + AC + CPS 추출)

**목적**: 비싼 LLM 리뷰 전에 값싼 정적 검사 + AC·CPS 메타데이터 추출.

**책임**:
1. 정적 게이트: 린터·TODO·dead link·시크릿·WIP 잔여물
2. **frontmatter 검증**: staged WIP·decisions·incidents·guides에 `problem`·
   `solution-ref` 누락 시 차단
3. **CPS 인용 박제 감지**: `solution-ref` 인용을 CPS 본문과 grep — 미매칭 시 경고
4. **AC 추출**: Goal·검증 묶음(`review`·`tests`·`실측`) 파싱. 누락 시 차단
5. **stage 결정**: `검증.review` 값 그대로 stage 매핑 (또는 룰 1·4 격상)

**sub-커밋 예외**: `HARNESS_SPLIT_SUB=1` 환경에서는 pre-check을 재실행하지
않는다. 부모 커밋의 `PRE_CHECK_OUTPUT` 변수를 그대로 이어받아 사용한다.

```bash
PRE_CHECK_OUTPUT=$(python3 .claude/scripts/pre_commit_check.py)
```

stdout 출력 형식 (key: value):
```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
diff_stats: files=N,+A,-D
wip_problem: P#                                   # frontmatter problem 인용
wip_solution_ref: S# — "..."; S# — "..."          # frontmatter solution-ref list (";" 구분)
ac_review: skip|self|review|review-deep           # AC 검증.review 값
ac_tests: <pytest 명령 또는 "없음">                # AC 검증.tests 값
ac_actual: <명령 또는 "없음">                      # AC 검증.실측 값
recommended_stage: skip|micro|standard|deep       # stage 판단 (ac_review 매핑 또는 격상)
s1_level: ""|file-only|line-confirmed             # 시크릿 강도
```

폐기된 출력 (호환성):
- `wip_kind` (외형 라벨)
- `has_impact_scope` (외형 metric)

- **exit 2 (차단)**: stderr 메시지를 사용자에게 전달. 문제 수정 후
  스테이징(Step 3)부터 재시도.
- **exit 0 (통과)**: 5.3단계로 진행.

> `--no-verify` 차단은 bash-guard.sh에서 유지.

### 5.3. AC 검증 묶음 자동 실행 (Phase 2-A)

pre-check stdout에서 `ac_tests`·`ac_actual` 값을 추출해 화이트리스트 기반
자동 실행. 작성자가 AC `검증.tests`·`검증.실측`에 자가 선언한 명령은
회귀 가드이므로 통과 의무 — 실패 시 commit 차단.

**sub-커밋 예외**: `HARNESS_SPLIT_SUB=1`이면 부모 커밋에서 이미 실행됐으므로
재실행하지 않는다 (Step 5의 PRE_CHECK_OUTPUT 재사용 원칙과 동일).

#### 변수 추출

```bash
if [ -z "$HARNESS_SPLIT_SUB" ]; then
  AC_TESTS=$(echo "$PRE_CHECK_OUTPUT" | sed -n 's/^ac_tests: //p')
  AC_ACTUAL=$(echo "$PRE_CHECK_OUTPUT" | sed -n 's/^ac_actual: //p')
fi
```

`pre-check` 출력 규약:
- `ac_tests: none` (또는 `ac_actual: none`) — staged WIP 없거나 AC `검증.tests` 값이 `없음`
- `ac_tests: pytest -m stage` 등 — 작성자가 선언한 명령 원문

#### 화이트리스트 (정규식 SSOT)

```
^(pytest|bash -n|python -m|grep)\b
```

- `pytest ...` (markers·경로 포함)
- `bash -n <path>` (구문 검사)
- `python -m <module> ...`
- `grep ...`

화이트리스트 외 명령(`rm -rf`·`curl`·임의 실행 파일 등)은 자동 실행 금지 —
보안. 가이드만 출력하고 사용자 승인 후 수동 실행.

#### 분기 로직 (ac_tests·ac_actual 동일 처리)

```bash
run_ac_check() {
  local label="$1"
  local cmd="$2"
  case "$cmd" in
    ""|none|"없음")
      echo "  $label: 없음 (작성자 선언)"
      return 0
      ;;
    pytest*|"bash -n "*|"python -m "*|grep*)
      echo "🔍 $label 자동 실행: $cmd"
      if eval "$cmd"; then
        echo "  ✅ $label 통과"
        return 0
      else
        echo "  🚫 $label 실패 — commit 차단"
        return 1
      fi
      ;;
    *)
      echo "⚠ $label 화이트리스트 외 명령: $cmd"
      echo "  자동 실행 skip. 사용자 승인 후 수동 실행 권장."
      echo "  화이트리스트: pytest | bash -n | python -m | grep"
      return 0
      ;;
  esac
}

if [ -z "$HARNESS_SPLIT_SUB" ]; then
  run_ac_check "tests" "$AC_TESTS" || exit 1
  run_ac_check "실측"  "$AC_ACTUAL" || exit 1
fi
```

#### 실패 시 처리

- 화이트리스트 명령이 비-0 exit → commit 차단, stderr 그대로 사용자에게 전달
- 사용자는 (a) 코드 수정 후 재커밋, 또는 (b) AC를 정밀화해 재선언

#### 화이트리스트 외 케이스

자동 실행하지 않고 가이드만 출력. 작성자가 수동 검증 후 재커밋. commit log
`🔍 review:` 라인의 자가 보고 시스템(staging.md)이 사후 audit 대상으로
표시함.

### 5.5. 커밋 분리 판정 (audit #18 — 글로벌 원칙, 1 커밋 = 1 논리 단위)

pre-check stdout의 `split_action_recommended` 값으로 분기:

- **`sub`**: 현재 sub-커밋 진행 중 (`HARNESS_SPLIT_SUB=1`). Step 6으로 진행
- **`single`**: 분리 불필요 (단일 그룹). Step 6으로 진행
- **`split`**: 분리 필요. 아래 흐름 실행

#### split 흐름

```bash
bash .claude/scripts/split-commit.sh
```

- 스크립트가 전체 staged를 비우고 **첫 그룹만 다시 stage**
- `.claude/memory/split-plan.txt`에 남은 그룹 목록 저장
- commit 스킬은 **첫 그룹만으로** Step 6·7·7.5·8(커밋)·9(푸시 제외) 수행
  - 커밋 시 **`HARNESS_SPLIT_SUB=1 HARNESS_DEV=1` prefix 필수**
  - sub-커밋은 **pre-check 재실행 금지** — 부모 커밋의 `PRE_CHECK_OUTPUT` 변수를
    그대로 재사용. 린터·신호·분리 판정은 이미 완료됐다
  - sub-커밋의 review stage는 그룹 성격(`split_group_N_name`)으로 결정:
    - `char:doc` → Stage 0 (skip) 강제. 자연어 문서에 LLM review 불필요
    - `char:exec` / `char:agent-rule` / `char:skill` / `wip:*` → 부모의
      `recommended_stage` 그대로 사용 (재판정 없음)
- 첫 sub-커밋 완료 후 **다시 `/commit` 호출** → split-commit.sh가 다음 그룹 stage
- `split-plan.txt`가 비면 분리 종료

#### 우회

- 사용자가 명시적으로 "분리 안 하고 통째로" 요청 시에만 `single` 경로 사용
- 자동으로 "이번엔 분리 안 해도 되겠다" 판단 **금지** — 원칙 위반
- 분리 불가 케이스 (rename-only 대량 변경 등)는 pre-check이 이미 `single`
  판정 (단일 그룹으로 귀결)

### 6. 변경 내역 분석

`git diff --cached`로 스테이징된 변경 내역을 읽고,
어떤 파일에서 어떤 로직이 어떻게 수정되었는지 파악한다.

### 7. 리뷰 (Stage 분기 — `.claude/rules/staging.md` 참조)

pre-check stdout의 `recommended_stage` 값에 따라 분기. `--no-review`/
`--quick`/`--deep` 플래그가 있으면 자동 분류 오버라이드.

#### Stage 결정 우선순위

```
1. --no-review → Stage 0 (skip), 메시지에 [skip-review] 태그
2. --quick     → Stage 1 (micro) 강제
3. --deep      → Stage 3 (deep) 강제
4. recommended_stage (pre-check 결과)
```

**충돌 처리**: 둘 이상 동시 입력 시 **번호가 낮은 쪽이 우선**. 예:
`--no-review --deep` → `--no-review` 이김 (1번). `--quick --deep` →
`--quick` 이김 (2번 vs 3번). 사용자에게 충돌 사실 1줄 알림:
> 🔧 플래그 충돌: --no-review와 --deep 동시 입력 → --no-review 우선 (우선순위 1 < 3)

#### Stage별 행동

Stage별 시간·tool·행동 정의는 **`staging.md` "## Stage" 섹션 SSOT** 참조.
이 스킬은 stage 값을 받아 review를 호출하는 역할만 한다.

요약 (상세는 staging.md):
- **Stage 0 (skip)**: review 호출 안 함. 커밋 메시지에 `🔍 review: skip` 한 줄
- **Stage 1 (micro)**: review 호출, `recommended_stage: micro` 명시. S3 신규 파일 모드
- **Stage 2 (standard)**: review 호출, `recommended_stage: standard` 명시
- **Stage 3 (deep)**: review 호출, `recommended_stage: deep` 명시

**거대 커밋 정책** — `staging.md` "거대 커밋 정책" 섹션 SSOT 참조.

#### 호출 시점·선행 조건

- **호출 시점**: Step 6(변경 내역 분석) 후 커밋 메시지 작성 전.
- **선행 조건**: Step 5 pre-check이 통과해야 호출한다. pre-check이 실패하면
  리뷰는 건너뛴다 (어차피 커밋 못 함).

> **test-strategist 병렬 호출 폐기 (audit #7·#15, 2026-04-22)**: 114초
> 실측 대비 효용 부족으로 에이전트 자체·자동 호출 로직·pre-check 신호
> (`needs_test_strategist`·`test_targets`·`new_func_lines_b64`) 전부 제거.
> 테스트 판단은 필요 시 Claude가 직접 grep·Read로 확인.

#### 응답 처리

review의 첫 줄 `verdict:` 값으로 분기 (review.md "## 출력 형식" SSOT):

- **`verdict: block`**: 커밋 진행하지 말고 [차단] 섹션을 사용자에게 전달. 수정 후 재시도.
- **`verdict: warn`**: 진행하되 [주의] 섹션을 커밋 메시지에 요약 반영.
- **`verdict: pass`**: 그대로 다음 단계로.
- **verdict 누락**: review 규격 미준수. 재호출 또는 사용자 확인. 임의 해석 금지.

### 7.5. WIP 진척도 자동 갱신 (audit #3, 2026-04-22 / 구현 2026-04-25)

**실행 시점**: review `verdict: pass` 직후, `git commit` 직전.
`verdict: block`·`warn` 경로에서는 실행 안 함. Stage 0 skip도 스킵.

**구현**: `docs_ops.py wip-sync` 호출.

```bash
STAGED_FILES=$(git diff --cached --name-only | tr '\n' ' ')
if [ -n "$STAGED_FILES" ]; then
  python3 .claude/scripts/docs_ops.py wip-sync $STAGED_FILES 2>&1
fi
```

**동작** (docs_ops.py wip-sync 내부):

1. staged 파일 경로·basename이 언급된 WIP 체크리스트 항목에 ✅ 추가
2. 갱신된 WIP의 frontmatter `updated` 오늘 날짜로 갱신 + `git add`
3. 해당 WIP의 모든 체크리스트 항목이 ✅이면 `docs_ops.py move` 자동 실행
   - 차단 키워드 있으면 이동 skip + stderr 경고
   - 이동 성공 시 `cluster-update` 자동 호출
4. stdout: `wip_sync_matched: N`, `wip_sync_moved: N`

**원칙**:
- 매칭 안 되면 변경 없음. stdout 수치로만 인지
- 이 단계의 staged 추가는 review 재호출 유발 안 함

**위치 근거**: Step 2로는 review block 시 ✅ 덮어쓰기 발생. review pass
직후가 "staged 확정된 최종 상태".

#### git log 추적성 (모든 stage 공통)

커밋 메시지 본문에 자동 포함 (위치: 본문 끝, 푸터 직전):
```
🔍 review: <stage> | problem: P# | solution-ref: S#
```

Stage 0(skip)도 반드시 한 줄 남긴다. 사후 회고 가능해야 함
(`git log --grep "review: skip"`).

#### 사용자 노출

stage 결정 직후 한 줄로 알림:
> 🔍 review stage: standard (kind: refactor, 영향 범위: 없음)

사용자가 부적절하다 판단하면 다음 커밋에 `--quick`/`--deep` 플래그.

---

## 커밋 메시지 작성

Conventional Commits 규약 준수 (feat:, fix:, refactor: 등).

> **강제 경유 규약 (audit #8, 2026-04-22 / v0.20.5 업데이트)**: `bash-guard.sh`
> 검증 4가 `git commit` 직접 호출을 차단한다. **반드시 `HARNESS_DEV=1`
> prefix를 앞에 붙여 실행**해야 통과. prefix 누락 시 bash-guard가 exit 2.
>
> 과거 `HARNESS_COMMIT_SKILL=1` prefix가 별도 이스케이프로 존재했으나
> v0.20.5에서 폐기. Claude가 스킬을 우회하고 수동으로 prefix 붙이는 경로
> 원천 차단 목적. 이스케이프 경로는 `HARNESS_DEV=1` 단일.

### 기본 포맷

커밋 본문에 핵심 변경 요약을 포함한다:
- 무엇이 바뀌었는가 (1~3줄)
- 연관 문서 경로 (있으면)

```bash
HARNESS_DEV=1 git commit -m "feat: [제목]" -m "[본문]"
```

### downstream 한 줄 (scripts/** 또는 agents/rules/settings 변경 시)

staged 파일에 `.claude/scripts/**`, `.claude/agents/**`, `.claude/rules/**`,
`.claude/settings.json`이 포함된 경우, 커밋 본문 끝(🔍 review 라인 직전)에 한 줄 추가한다:

```
downstream: <harness-upgrade 시 주의할 점 1줄>
```

**예시**:
```
downstream: harness-upgrade 후 pre-check 재실행 권장
downstream: bash-guard.sh 경로 변경 — upgrade 후 hook 설정 확인 필요
downstream: SKILL.md 인터페이스 변경 — commit 흐름 검토 필요
```

**규칙**:
- 내용은 자유 형식. 차단 조건 아님 (없어도 커밋 진행)
- `git log --grep "downstream:"` 으로 다운스트림 영향 변경 이력 조회 가능
- S2/scripts 이외 변경에는 추가하지 않는다 (남발 방지)

### 확장 포맷 (deep stage 또는 중요 결정 커밋)

아래 조건 중 하나 이상이면 본문에 `[📝 주요 참고 사항]` 섹션 추가:
- staging `recommended_stage: deep`
- review가 [주의]·[참고] 보고
- 아키텍처·설계 결정 포함
- 까다로운 버그의 원인과 해결 방식

섹션 내용:
- 이번 작업의 아키텍처/설계 결정
- 까다로운 버그의 원인과 해결 방식
- 추후 주의할 점, 남은 기술 부채
- 연관 문서 경로 (예: `📄 상세: docs/incidents/auth-token-fix.md`)
- 리뷰 에이전트가 보고한 주의/참고 이슈 (있으면)

---

## 푸시

기본 브랜치로 `git push`. **완료 후 요약 제공 + push 결과 반드시 포함.**

### starter 분기 (필수 — 누락 시 다운스트림이 변경 못 봄)

`.claude/HARNESS.json`의 `is_starter: true`면 git pre-push hook이 일반
push를 차단한다. **반드시 `HARNESS_DEV=1 git push` 사용:**

```bash
IS_STARTER=$(grep -oE '"is_starter"[[:space:]]*:[[:space:]]*(true|false)' .claude/HARNESS.json | grep -oE '(true|false)')
if [ "$IS_STARTER" = "true" ]; then
  HARNESS_DEV=1 git push origin main
else
  git push origin main
fi
```

이 단계를 빼면 starter 변경이 GitHub에 반영 안 됨 → 다운스트림이 fetch
해도 못 봄 (incident `hn_starter_push_skipped` 참조).

### 세션 snapshot 정리 (push 성공 후)

push 성공 직후 session-* 파일 제거:

```bash
rm -f .claude/memory/session-*.txt .claude/memory/split-plan.txt
```

라이프사이클: 재commit 시 pre-check 재실행이 기본. hook 전달용 파일만
유지. 성공 후 cleanup. `rules/memory.md` "## 동적 snapshot" 섹션 SSOT.

### 요약에 다음을 포함:
- 커밋 SHA + 메시지 1줄
- 변경 stat (파일 수, +/- 라인)
- **리뷰 결과**: "✅ 리뷰 통과" / "⚠️ 리뷰 경고: ..." / "🚫 리뷰 차단: ..." / "리뷰 스킵 (`--no-review`)"
- (선택) push 결과 (origin/main 업데이트 SHA)

---

## 주의

- `--no-verify` 사용 금지 (`bash-guard.sh` hook에서 차단됨).
- docs/WIP/에 completed/abandoned 파일이 남아있으면 안 된다.
- 커밋 메시지는 한국어.
- 리뷰 차단 시 `--no-review`로 우회하지 마라. 지적 사항을 실제로 수정한 후 재시도.
