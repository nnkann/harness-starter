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
| Pass (pre-check→나) | `signals` · `recommended_stage` · `s1_level` (스키마 SSOT는 `pre_commit_check.py`) |
| Pass (나→review) | 아래 "review 호출" 섹션이 이 Pass 블록을 조립한다 (self-containment) |
| Preserve | pre-check signals·stage·domains 원본 (재계산·재가공 금지) · 사용자 플래그(--no-review/--quick/--deep) |
| Signal risk | ⛔ pre-check 3회 연속 차단·시크릿 line-confirmed · ⚠️ stage 격상 사유·위험도 게이트 hit · 🔍 검증 흔적 |
| Record | commit log `🔍 review: <stage> \| signals: <...> \| domains: <...>` 한 줄 (Stage 0 포함, `staging.md` 규정) |

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

스테이징 + Step 5 pre-check 통과 후 `git commit` 직전에 호출한다.

**핵심 원칙: prompt에 `git diff --cached` 결과 텍스트를 직접 박는다.**
review 에이전트가 스스로 git 명령을 실행해서 diff를 가져오게 두면 잘못된
커밋(HEAD, HEAD~1 등)을 보고 엉뚱한 분석을 할 수 있다 (실측 사례:
v1.4.1 커밋에서 review가 직전 커밋 diff를 잘못 분석).

스킬이 Bash로 직접 실행해서 결과를 prompt에 삽입한다:

**그룹 성격 기반 diff 전달 (단계별 — 이 규칙을 따른다):**

split 후 각 sub-커밋은 단일 char 그룹으로 구성된다. `split_group_1_name`의
`char:` prefix로 그룹 성격을 판별해 전달 방식을 결정한다.

| 그룹 성격 | 전달 방식 | 근거 |
|----------|----------|------|
| `char:exec` / `char:agent-rule` / `char:skill` / `wip:*` | 전처리된 full diff | 실행 로직·판단 기준·흐름 — 줄 단위 패턴 감지 필요 |
| `char:doc` | 전처리된 full diff (3000줄+ 시 truncate) | diff 없이 stat만 주면 review가 Read N회 소진 → maxTurns 초과 (incident `hn_review_maxturns_verdict_miss` 2026-04-28) |

공통 전처리 (모든 그룹):
- `--unified=1`: context lines 3→1 (PR-Agent 방식 적용, 변경 줄 집중)
- `index` 줄 제거: `grep -v "^index "`
- `diff --git` 헤더 제거: `grep -v "^diff --git "`

**doc 그룹 3000줄+ truncate**: stat을 앞에 붙이고 diff를 3000줄에서 잘라 전달.
review가 나머지 파일을 Read로 확인하더라도 이미 stat으로 전체 윤곽을 알고 있어
불필요한 Read를 줄일 수 있다. stat-only였던 구 방식(37% 감소)은 Read 소진이라는
더 큰 비용을 발생시켜 폐기.

```bash
# 1. 그룹 성격 판별 (pre-check stdout에서 추출)
GROUP_NAME=$(echo "$PRE_CHECK_OUTPUT" | grep "^split_group_1_name:" | cut -d' ' -f2-)

# 2. 공통 전처리
DIFF_PROCESSED=$(git diff --cached --unified=1 \
  | grep -v "^index " \
  | grep -v "^diff --git ")

# 3. 그룹별 전달 방식 결정 (전 그룹 full diff — doc는 3000줄 truncate)
if echo "$GROUP_NAME" | grep -qE "^char:doc"; then
  # doc 그룹: full diff, 단 3000줄 초과 시 truncate + stat 보조
  DIFF_LINE_COUNT=$(echo "$DIFF_PROCESSED" | wc -l)
  if [ "$DIFF_LINE_COUNT" -gt 3000 ]; then
    DIFF_BLOCK="변경 성격: doc (자연어·문서). diff 3000줄 초과로 앞부분만 포함:
$(git diff --cached --stat)
---
$(echo "$DIFF_PROCESSED" | head -3000)
--- (이하 생략 — 필요 시 Read로 개별 파일 확인)"
  else
    DIFF_BLOCK="$DIFF_PROCESSED"
  fi
else
  # exec/agent-rule/skill/wip: 전처리된 full diff
  DIFF_BLOCK="$DIFF_PROCESSED"
fi
```

```
Agent tool 호출
  subagent_type: "review"
  prompt: 아래 블록 6개를 그대로 포함
    1. ## 이번 커밋의 목적 (1~2줄)
    2. ## 연관 WIP 문서 (경로 또는 "없음")
    3. ## 전제 컨텍스트 (review가 staged diff만 보고는 알 수 없는 사실)
    4. ## pre-check 결과 (review가 쓰는 10 keys만 — pre_check_passed·split_plan·split_action_recommended·prior_session_files 제외)
    5. ## staged diff (git diff --cached 결과 텍스트 — 위 DIFF_BLOCK 그대로)
    6. ## 지시
```

### 전제 컨텍스트 블록 (필수 — review 오판 방지)

review는 staged diff와 자기가 Read한 파일만 본다. 그래서 다음 정보가
필요하면 commit 스킬이 prompt에 직접 박아준다:

- `is_starter: true|false` — `.claude/HARNESS.json`에서 읽음. true면 review가
  오염 검토 카테고리 추가 수행.
- 변경이 의존하는 기존 파일·구조 (예: "docs 관리 로직은 v0.21.x에서
  스킬 → `docs_ops.py` 스크립트화됨")
- 최근 관련 커밋 SHA + 한 줄 요약 (Claude가 알지만 diff에 안 나타나는 맥락)
- WIP 문서에 없는 추가 의도 배경

이 블록이 빠지면 review가 자기가 본 파일만으로 단정해서 "에이전트 없음"
같은 오판을 한다 (실측 사례 — 2026-04-19 contamination 커밋).

is_starter는 **항상** 박아라 (스킬이 자동 추출):

```bash
IS_STARTER=$(grep -o '"is_starter":[[:space:]]*\(true\|false\)' .claude/HARNESS.json 2>/dev/null | grep -oE '(true|false)')
[ -z "$IS_STARTER" ] && IS_STARTER="false"
```

> **메타 파일 본문 박기 섹션 삭제 (audit #6, 2026-04-22)**: `HARNESS.json`·
> `promotion-log.md`·`MIGRATIONS.md`를 review prompt에 박던 블록 제거.
> 실측상 review가 이 블록을 활용한 증거 없고 prompt 부피만 증가. review가
> 필요 시 Read로 직접 조회하는 편이 더 정확.

### prompt 예시
```
## 이번 커밋의 목적
<1~2줄>

## 연관 WIP 문서
<경로 또는 "없음">

## 전제 컨텍스트
- is_starter: true
- <변경 의도 배경 또는 의존 파일 — Claude가 알지만 diff에 안 나타나는 사실>
- <필요 시 최근 관련 커밋 SHA + 한 줄>

## pre-check 결과
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: 핵심 설정 파일 변경
signals: S2,S9
domains: harness
domain_grades: critical
multi_domain: false
recommended_stage: deep
s1_level: 

## staged diff
diff --git a/.claude/scripts/pre_commit_check.py b/.claude/scripts/pre_commit_check.py
index abc..def 100644
--- a/.claude/scripts/pre_commit_check.py
+++ b/.claude/scripts/pre_commit_check.py
@@ -1,3 +1,5 @@
... (실제 diff 내용 그대로)

## 지시
위 staged diff만이 검증 대상이다. 추가로 git 명령(git diff, git log, git show)을
실행해서 다른 커밋의 변경을 보지 마라 — prompt 안의 staged diff가 진실이다.
파일 본문 맥락이 필요하면 Read만 사용해도 좋다.

위 risk_factors에 우선순위를 두고 3관점(회귀/계약/스코프) 검증하라.
already_verified 항목은 재검사 마라.
반환 형식은 review.md "## 출력 형식" SSOT를 따른다 (markdown + verdict 헤더).
```

review 에이전트는 prompt 안의 diff를 진실로 삼고, Read/Glob/Grep으로 파일
본문 맥락만 확인한 뒤 markdown으로 응답한다. **`git diff`/`git log`/`git show`
같은 staged-diff 우회 명령은 실행하지 않는다.**

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
> 전체 pre-check에서만 실행. Step 1~4(잔여물·WIP·버전·스테이징)는 1초
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

### 3. 하네스 버전 체크 (harness-starter 전용 — audit #4, 2026-04-22)

```bash
python3 .claude/scripts/harness_version_bump.py
```

- 다운스트림(`is_starter: false` 또는 파일 없음)은 스크립트가 즉시 exit,
  stdout·stderr 없음 → Step 4로 진행
- 업스트림은 stdout에 `version_bump: minor|patch|none` + 근거를 출력.
  commit 스킬이 이 값을 참고해 사용자에게 범프 여부 확인

**버전 범프 기준** (스크립트 내장):

| 변경 유형 | 버전 범프 | 예시 |
|-----------|-----------|------|
| 스킬/에이전트/규칙 **신설** 또는 폴더 구조 변경 | minor (0.X.0) | 에이전트 추가, docs/ 리팩토링 |
| 기존 스킬/스크립트/규칙 **로직 수정**, 버그 수정 | patch (0.0.X) | pre-commit 조건 추가, 경로 오류 수정 |
| 문서·주석·오타만 | 올리지 않음 | README 업데이트, 프론트매터 수정 |

**버전을 올릴 때** (사용자 확인 후):
1. `.claude/HARNESS.json`의 `version` 필드 갱신
2. **커밋 메시지 제목에 `(v0.X.Y)` 포함** — 이것이 버전 이력의 SSOT.
   회고는 `git log --oneline --grep "(v0\."`로 전체 범프 조회. 세부 변경은
   해당 WIP/decisions 문서 + 커밋 메시지 본문이 담는다.

> **과거 `docs/harness/promotion-log.md` 폐기 (v0.20.7)**: 수동 row append
> 비용이 매 커밋 누적되고 git log와 SSOT가 중복됐다. 이제 `git log`가 유일
> SSOT. promotion-log.md 갱신 단계는 없다.

**스크립트 제안이 애매하거나 사용자 의도와 다르면** 사용자에게 묻는다.
자의적으로 올리지 않는다.

### 4. 스테이징

`git status`로 변경 파일 확인 후, 특별한 제외 요청 없으면 `git add .`

**메타 파일 자동 병합 (분리 커밋 차단)**:

Step 3에서 버전 범프가 있었거나, 본 커밋의 변경으로 인해 다음 메타 파일
이 함께 갱신되어야 한다면 **본 커밋에 자동 포함**한다 (분리 커밋 만들지
마라):

- `.claude/HARNESS.json` (버전 범프 시)
- `docs/clusters/*.md` (문서 추가·이동 시)

이유: 이 메타 파일을 별도 커밋으로 분리하면 review가 두 번 돌고, 두
번째 커밋은 의미 있는 검증이 불가능 (버전 1자리 변경에 6카테고리 검증).
0d047a5 이후 면제 리스트가 도입되어 분리할 이유가 사라졌다.

### 5. pre-check (정적 검사, 빠름)

**목적**: 비싼 LLM 리뷰 전에 값싼 정적 검사를 먼저 돌려 실패 시 조기 차단.
린터 에러·TODO/FIXME·WIP 잔여물·`--no-verify` 같은 명백한 문제는 Agent 호출
없이 걸러낸다.

**stdout 캡처 필수**: pre-check은 stderr에 사용자용 메시지를, **stdout에
14 keys**를 출력한다. Bash tool로 실행 시 stdout 전체를 스킬 컨텍스트에
보관하되, **review prompt에는 allowlist grep으로 8 keys만 추출해 박는다**:
`already_verified`, `risk_factors`, `signals`, `domains`,
`domain_grades`, `multi_domain`, `recommended_stage`, `s1_level`.
`diff_stats`·`repeat_count`는 review가 실제로 참조하지 않아 제외.
나머지 4개(`pre_check_passed`, `split_plan`,
`split_action_recommended`, `prior_session_files`)는 commit 스킬 내부용 —
review prompt에 포함하지 마라 (입력 비대 방지).
`split_action_recommended: split`일 때 pre-check stdout에 `split_group_N_name`·
`split_group_N_files` 동적 키가 추가되므로 allowlist grep이 없으면 이 키들도
review에 들어간다.

**단일 실행 + 변수 중심** (audit #5, 2026-04-22 재설계). tree-hash 캐싱
폐기 — "캐싱 대기"의 I/O 오버헤드가 무의미하다는 사용자 지적 반영.
재commit 시 pre-check 재실행이 기본 경로. diff는 변수로 유지.

**sub-커밋 예외**: `HARNESS_SPLIT_SUB=1` 환경에서는 pre-check을 재실행하지
않는다. 부모 커밋에서 캡처한 `PRE_CHECK_OUTPUT`·`REVIEW_PRECHECK` 변수를
그대로 이어받아 사용한다. 신호·린터·분리 판정은 이미 완료됐다.

```bash
STAGED_DIFF=$(git diff --cached)
PRE_CHECK_OUTPUT=$(python3 .claude/scripts/pre_commit_check.py)
# review prompt용 — allowlist로 8 keys만 추출 (split_group_N_* 동적 키 차단)
REVIEW_PRECHECK=$(echo "$PRE_CHECK_OUTPUT" | grep -E \
  "^(already_verified|risk_factors|signals|domains|domain_grades|multi_domain|recommended_stage|s1_level):")
```

- Step 6·7은 **Bash 변수** 재사용 (`STAGED_DIFF`·`PRE_CHECK_OUTPUT`·`REVIEW_PRECHECK`) —
  파일 I/O 없음. review prompt에는 `REVIEW_PRECHECK` 사용 (`PRE_CHECK_OUTPUT` 직접 박기 금지)
- pre-check이 **exit 2**면 stdout에 `pre_check_passed: false`로 판정.
  exit 코드는 부차적
- hook 전달이 필요하면 **background write** 사용: `echo "$PRE_CHECK_OUTPUT" > .claude/memory/session-pre-check.txt &`.
  스킬은 기다리지 않고 다음 Step로. hook이 나중에 파일 읽음
- snapshot 파일은 `session-pre-check.txt` 1개만. `session-staged-diff.txt`·
  `session-tree-hash.txt`는 폐기. 용도·수명은 `.claude/rules/memory.md`
  "## 동적 snapshot" 섹션 SSOT

stdout 출력 형식 (key: value):
```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: <세미콜론 구분 위험 요인 목록 또는 빈 값>
diff_stats: files=N,+A,-D
signals: S1,S2,S5,...                              # staging 신호 (rules/staging.md)
domains: harness,docs                              # 변경된 도메인
domain_grades: critical,meta                       # 등급 매핑
multi_domain: true|false                           # 2개 이상 도메인 여부
repeat_count: max=N                                # 연속 수정 최대 카운트
recommended_stage: skip|micro|standard|deep        # Step 7 stage 분기 결정
s1_level: ""|file-only|line-confirmed              # S1 시크릿 신호 강도 (stage 분기에 사용)
```

`signals`·`recommended_stage`는 Step 7에서 review 호출 분기와 prompt
주입에 모두 사용된다. **전체 stdout을 그대로 보관**해야 한다 (4 keys만
잘라내면 안 됨).

- **exit 2 (차단)**: stderr 메시지를 사용자에게 전달. 문제 수정 후
  스테이징(Step 4)부터 재시도. 리뷰 단계로 진행하지 마라.
- **exit 0 (통과)**: stdout 전체를 보관하고 5.5단계로 진행.

> pre-check은 commit 스킬만 실행한다. `git commit` hook에서 재실행하지
> 않음 (2회 낭비 제거, v0.9.4). Step 5에서 전체(린터+staged 신호)로 1회만
> 돌림 (audit #1, 2026-04-22: Step 0 제거). `--no-verify` 차단은
> bash-guard.sh에서 유지.

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

**Stage 0 (skip)**:
- review 호출 안 함
- 커밋 메시지에 `🔍 review: skip | signals: <...> | domains: <...>` 한 줄 자동 포함

**Stage 1 (micro)** — 1~2 tool calls, 시크릿/스코프 위주:
- review 호출, prompt에 `recommended_stage: micro` 명시
- 신규 파일만(S3)인 경우 신규 패스 모드 (프론트매터·구조만)
- 한도 내 종료, 응답 처리는 아래

**Stage 2 (standard)** — 3~5 tool calls, 현재 기본 동작:
- review 호출, prompt에 `recommended_stage: standard` 명시

**Stage 3 (deep)** — 10+ tool calls, 전체 검증:
- review 호출, prompt에 `recommended_stage: deep` 명시
- S1·S2·S8·S9(critical)·S14 hit 또는 사용자 `--deep`

**거대 커밋 정책** — 파일 30+ 또는 diff 1500줄+이면 pre-check이 stderr에
"스코프 분리 권장" 경고 출력. 자동 분기·우회 플래그 없음. 사용자가
커밋을 논리 단위로 쪼개 여러 개로 분리한다. 배경: `staging.md` "거대
커밋 정책" 섹션 + incident `hn_review_maxturns_verdict_miss` 참조.

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
🔍 review: <stage> | signals: <S1,S5,...> | domains: <harness,docs>
```

Stage 0(skip)도 반드시 한 줄 남긴다. 사후 회고 가능해야 함
(`git log --grep "review: skip"`).

#### 사용자 노출

stage 결정 직후 한 줄로 알림:
> 🔍 review stage: standard (signals: S7, 5 files, 142 lines)

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

### downstream 한 줄 (S2 또는 scripts/** 변경 시)

pre-check signals에 `S2`가 있거나 staged 파일에 `.claude/scripts/**`가
포함된 경우, 커밋 본문 끝(🔍 review 라인 직전)에 한 줄 추가한다:

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
