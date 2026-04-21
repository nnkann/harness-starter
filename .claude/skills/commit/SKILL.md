---
name: commit
description: 작업 잔여물 정리, 계획 문서 완료 처리, 변경 사항 분석 후 커밋+푸시. 모드는 CLAUDE.md의 하네스 강도에 따라 결정. 명시적으로 `--light` / `--strict`로 오버라이드 가능. `/commit` 또는 "커밋해줘" 요청 시 사용.
---

# /commit 스킬

커밋 과정에서 작업 잔여물을 정리하고, 계획 문서를 완료 처리하며,
작업 중 얻은 컨텍스트를 Git 히스토리에 보존한다.

## 고유 책임 (이 스킬만 하는 것)

1. 모드·플래그 결정 (light/strict/--quick/--deep/--no-review)
2. 작업 잔여물 정리 (WIP completed 이동·clusters 갱신 트리거)
3. pre-check 호출 + 결과 해석 (차단·재시도 판정)
4. review·test-strategist 호출 조립 (호출자 self-containment 유지)
5. 커밋 메시지 작성 + git log 추적성 라인 기록
6. push 실행

## 위임 대상 (여기서 하지 않는 것)

| 영역 | 위임 |
|------|------|
| diff 단위 회귀·계약·스코프 검증 | review |
| 테스트 누락·전략 | test-strategist |
| 문서 이동·clusters 정합성 실행 | docs-manager |
| 누적 드리프트·전체 코드베이스 분석 | eval |
| 시크릿 1차 차단 | `.claude/scripts/pre-commit-check.sh` + gitleaks |

## 핸드오프 계약 (상속)

핸드오프 계약 SSOT는 `.claude/skills/implementation/SKILL.md` "## 핸드오프
계약" 섹션 상속. commit 축 구체화:

| 축 | 내용 |
|----|------|
| Pass (implementation→나) | WIP 파일 경로 · status · CPS 갱신 여부 |
| Pass (pre-check→나) | `signals` · `recommended_stage` · `s1_level` · `needs_test_strategist` · `new_func_lines_b64` (스키마 SSOT는 `pre-commit-check.sh`) |
| Pass (나→review) | 아래 "review 호출" 섹션이 이 Pass 블록을 조립한다 (self-containment) |
| Pass (나→test-strategist) | 아래 "test-strategist 호출" 섹션이 조립. 입력 계약은 `.claude/agents/test-strategist.md` "## 입력 계약" 참조 |
| Preserve | pre-check signals·stage·domains 원본 (재계산·재가공 금지) · 사용자 플래그(--light/--strict/--no-review/--quick/--deep) |
| Signal risk | ⛔ pre-check 3회 연속 차단·시크릿 line-confirmed · ⚠️ stage 격상 사유·위험도 게이트 hit · 🔍 검증 흔적 |
| Record | commit log `🔍 review: <stage> \| signals: <...> \| domains: <...>` 한 줄 (Stage 0 포함, `staging.md` 규정) |

**self-containment 원칙**: commit은 호출자로서 스스로 prompt를 조립한다.
review.md·test-strategist.md는 입력 계약(무엇을 받는가)만 보유하며, commit이
그 계약을 내재화된 템플릿으로 충족한다. 호출자가 피호출자 파일을 Read해야
prompt를 조립할 수 있다면 설계 오류 (Anthropic Agent Skills 권장).

| 사용법 | 설명 |
|--------|------|
| `/commit` | CLAUDE.md `## 환경`의 `하네스 강도`에 따라 자동 선택. |
| `/commit --light` | light 모드 강제. |
| `/commit --strict` | strict 모드 강제. |
| `/commit --no-review` | 리뷰 에이전트 스킵 (커밋 메시지에 `[skip-review]` 태그 포함). |
| `/commit --quick` | review stage 1(micro) 강제. 자동 분류 무시. |
| `/commit --deep` | review stage 3(deep) 강제. 자동 분류 무시. |
| `/commit --bulk` | 거대 일괄 변경. review 건너뛰고 **정량 가드 4종** (`bulk-commit-guards.sh`)으로 대체. 가드 실패 시 즉시 차단. 사용처: 파일 30+ or diff 1500줄+ 일괄 rename·본문 일괄 치환 등. |

## 모드 결정 규칙

**기본값 없음.** 커밋 스킬은 절대 임의로 모드를 선택하지 않는다.

1. 명시적 플래그(`--light`/`--strict`)가 있으면 그걸 따른다.
2. 플래그가 없으면 `CLAUDE.md` `## 환경` 섹션의 `하네스 강도:` 값을 읽는다.
   - `strict` → strict 모드
   - `light` → light 모드
3. 강도가 **비어 있거나 기록되지 않았으면** → 커밋을 진행하지 말고 사용자에게 묻는다:
   > 하네스 강도가 설정되지 않았습니다. `harness-init`을 먼저 실행하거나,
   > 이번 커밋에 한해 `--light` / `--strict`를 지정하세요.

절대 "기본 light"로 떨어지지 말 것. 학습/프로토타입 성격이라도 **사용자가 선택한 결과**여야 한다.

## 리뷰는 스킬이 Agent tool로 직접 호출한다

코드 리뷰는 이 스킬이 `Agent` tool로 review 서브에이전트(`.claude/agents/review.md`)를
직접 호출한다. hook은 쓰지 않는다.

| 하네스 강도 | 리뷰 트리거 | `--no-review` 동작 |
|------------|------------|-------------------|
| strict | **항상** Agent로 review 호출 | 사용자 명시 시에만 스킵, 커밋 메시지에 `[skip-review]` 태그 |
| light | 위험도 감지 시 Agent로 review 호출 (기준은 아래 위험도 게이트) | 위험도 hit 시에도 스킵 |

### 위험도 게이트 (light 모드)

**SSOT**: `.claude/scripts/pre-commit-check.sh`의 위험도 판정 로직
(`CORE_FILES`·`SECURITY_PATTERNS`·`INFRA_FILES` 정규식 + 파일 수·삭제 줄수
임계). pre-check stdout의 `risk_factors` 필드에 hit한 신호가 나타나면
review 호출. SKILL에 조건 목록을 재서술하지 않는다.

### 호출 방법

스테이징 + Step 5 pre-check 통과 후 `git commit` 직전에 호출한다.

**핵심 원칙: prompt에 `git diff --cached` 결과 텍스트를 직접 박는다.**
review 에이전트가 스스로 git 명령을 실행해서 diff를 가져오게 두면 잘못된
커밋(HEAD, HEAD~1 등)을 보고 엉뚱한 분석을 할 수 있다 (실측 사례:
v1.4.1 커밋에서 review가 직전 커밋 diff를 잘못 분석).

스킬이 Bash로 직접 실행해서 결과를 prompt에 삽입한다:

**입력 크기 분기 기준 (단계별 — 이 규칙을 따른다):**

| diff 크기 | 전달 방식 | 근거 |
|-----------|-----------|------|
| 0~2000줄 | 전체 인라인 | review가 패턴 감지에 전체 컨텍스트 필요 |
| 2001~5000줄 | stat 요약 + 첫 2000줄 + `... (truncated)` | 패턴 검증은 앞부분 + stat으로 충분 |
| 5001줄+ | stat만 + "파일별 Read 지시" | 전체는 토큰 과소비. review가 필요 시 개별 Read |

```bash
# 1. diff 캡처 (스킬이 직접 실행)
DIFF=$(git diff --cached)

# 2. 크기 가드: 단계별 축약
DIFF_SIZE=$(echo "$DIFF" | wc -l)
if [ "$DIFF_SIZE" -gt 5000 ]; then
  # 과대 입력 — stat만, 개별 Read 지시
  DIFF_BLOCK="diff 매우 큼 ($DIFF_SIZE 라인). stat만 포함:
$(git diff --cached --stat)
---
(본문 생략. 파일별 Read로 맥락 확인 필요 — git diff --cached -- <파일>)"
elif [ "$DIFF_SIZE" -gt 2000 ]; then
  # 큰 입력 — stat + 앞부분
  DIFF_BLOCK="diff 너무 큼 ($DIFF_SIZE 라인). stat과 처음 2000라인만 포함:
$(git diff --cached --stat)
---
$(echo "$DIFF" | head -2000)
... (truncated)"
else
  DIFF_BLOCK="$DIFF"
fi
```

```
Agent tool 호출
  subagent_type: "review"
  prompt: 아래 블록 6개를 그대로 포함
    1. ## 이번 커밋의 목적 (1~2줄)
    2. ## 연관 WIP 문서 (경로 또는 "없음")
    3. ## 전제 컨텍스트 (review가 staged diff만 보고는 알 수 없는 사실)
    4. ## pre-check 결과 (Step 5에서 캡처한 stdout, 10 keys)
    5. ## staged diff (git diff --cached 결과 텍스트 — 위 DIFF_BLOCK 그대로)
    6. ## 지시
```

### 전제 컨텍스트 블록 (필수 — review 오판 방지)

review는 staged diff와 자기가 Read한 파일만 본다. 그래서 다음 정보가
필요하면 commit 스킬이 prompt에 직접 박아준다:

- `is_starter: true|false` — `.claude/HARNESS.json`에서 읽음. true면 review가
  오염 검토 카테고리 추가 수행.
- 변경이 의존하는 기존 파일·구조 (예: "docs-manager는 e52234f에서 에이전트
  → 스킬로 승격됨, skills/docs-manager/SKILL.md 존재")
- 최근 관련 커밋 SHA + 한 줄 요약 (Claude가 알지만 diff에 안 나타나는 맥락)
- WIP 문서에 없는 추가 의도 배경

이 블록이 빠지면 review가 자기가 본 파일만으로 단정해서 "에이전트 없음"
같은 오판을 한다 (실측 사례 — 2026-04-19 contamination 커밋).

is_starter는 **항상** 박아라 (스킬이 자동 추출):

```bash
IS_STARTER=$(grep -o '"is_starter":[[:space:]]*\(true\|false\)' .claude/HARNESS.json 2>/dev/null | grep -oE '(true|false)')
[ -z "$IS_STARTER" ] && IS_STARTER="false"
```

### 메타 파일 본문 박기 (정보 흐름 누수 #8·#1 해소)

**문제**: commit 스킬이 Step 3~5에서 다음 파일을 직접 Read·Edit·Write한
결과를 review에 텍스트 요약(예: "0.9.2 → 0.9.3")만 전달. review가 결국
같은 파일을 다시 Read해서 검증 → 같은 정보 2~3중 처리.

**해결**: commit 스킬이 자기가 직접 수정한 **작은 메타 파일의 본문**을
review prompt의 `## commit 처리 결과` 블록에 박는다.

대상 (자동 박기):
- `.claude/HARNESS.json` (변경 시 전체 — 보통 10줄 이하)
- `docs/harness/promotion-log.md` (**이번 커밋에 추가한 행만**, diff hunk)
- `docs/harness/MIGRATIONS.md` (**이번 커밋에 추가한 신규 섹션만**)

대상 외 (Read 그대로):
- 50줄 초과 + 이번 커밋이 직접 만지지 않은 파일
- 코드 파일 (.sh·.py 등) — 컨텍스트 의존성 크면 Read가 정확

박는 비용 (~500 tokens) << Read 절약 (3회 × ~1k tokens + 2~4초).

```
## commit 처리 결과 (Read 재확인 불필요)

### .claude/HARNESS.json (최종 본문)
```json
{"version": "0.9.3", "is_starter": true, ...}
```

### docs/harness/promotion-log.md (이번 커밋 추가 행)
```
| 2026-04-20 | pre-commit-check.sh 격상 면제 | ... |
| 2026-04-20 | staging.md 룰 A ※ 면제 명시 | ... |
| 2026-04-20 | 버전 | 0.9.2 → 0.9.3 | ... |
```

### docs/harness/MIGRATIONS.md (신규 v0.9.3 섹션)
```markdown
## v0.9.3 — stage 격상 면제 버그 수정
...
```
```

review prompt의 `## 지시` 블록에 다음 추가:
> 위 "commit 처리 결과" 블록에 있는 파일은 commit 스킬이 직접
> Read·Edit·Write한 결과다. Read 재확인 금지. 해당 파일 로직 일관성은
> diff와 commit 처리 결과 블록 대조로 검증하라.

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
pre_check_passed: true
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: 핵심 설정 파일 변경
diff_stats: files=4,+82,-15

## staged diff
diff --git a/.claude/scripts/pre-commit-check.sh b/.claude/scripts/pre-commit-check.sh
index abc..def 100644
--- a/.claude/scripts/pre-commit-check.sh
+++ b/.claude/scripts/pre-commit-check.sh
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

### 0. 린터 조기 체크

스테이징 전에 린터만 먼저 돌려 실패 시 조기 종료한다. Step 1~4(잔여물
정리·WIP 갱신·버전 범프·스테이징)를 다 수행한 뒤에 린터 에러를 발견하면
시간 낭비.

```bash
bash .claude/scripts/pre-commit-check.sh --lint-only
```

- exit 0: Step 1로 진행
- exit 2: stderr 메시지 전달 후 즉시 종료. 린터 에러 수정 후 `/commit`
  재호출.

`--lint-only` 모드는 signals·stage 계산을 건너뛰어 빠르다. 전체 pre-check
은 Step 5에서 staged diff 기반으로 수행한다.

### 1. 작업 잔여물 정리

커밋 전 임시 파일이 포함되지 않도록 정리한다.

- 현재 컨텍스트에서 알 수 있는 임시 파일을 찾아 확인한다.
  (예: 루트의 test-*.mjs, debug/ 내 일회성 스크립트 등)
- 용도가 끝난 파일은 삭제한다.
- 테스트/디버그 스크립트로 인한 좀비 프로세스가 남아있는지 확인한다.
- 사용자가 남겨두길 명시한 파일은 제외한다.

### 2. 계획 문서 진척도 자동 갱신 (보수 모드)

docs/WIP/에서 이번 작업과 연결된 문서의 **본문만 자동 갱신**한다.
status 변경·이동은 **사용자가 명시 요청한 경우에만** 수행.

이전 4지선다 인터랙션은 폐기됨. 사유: Claude가 안 묻고 자동 [s] 스킵
가정해 매번 무위로 끝남. 보수적 자동 [u]만 유지하면 인터랙션 없이도
최소 진척 추적은 작동함.

#### 2.1. 자동 매칭 + ✅ 표시

1. `git diff --cached --name-only`로 staged 파일 목록 추출.
2. docs/WIP/의 각 문서를 읽고 본문에서 staged 파일 경로가 언급된 줄을
   찾는다.
3. 매칭된 줄 옆에 `✅` 자동 추가 (이미 있으면 스킵).
4. 매칭된 WIP의 frontmatter `updated` 필드를 오늘 날짜로 갱신.
5. status·파일 위치는 변경 없음.

**매칭 안 되면 변경 없음.** 모호한 자동 판단으로 정보를 잃지 마라.

#### 2.2. 명시 요청 처리 (사용자가 직접 말한 경우만)

사용자가 "WIP 정리해줘", "이거 completed로 옮겨줘", "잔여를 분리해줘"
같이 **명시적으로** 요청한 경우에만 다음 동작 수행:

| 사용자 요청 | 동작 |
|------------|------|
| "completed로 이동" | (a) status → completed (b) 파일명 접두사 규칙으로 이동 (c) docs-manager에 위임해 clusters 갱신 |
| "부분 완료, 잔여 분리" | (a) 잔여를 `<원래이름>_followup_<YYMMDD>.md`로 신설, `relates-to: rel: extends` (b) 원본 completed로 이동 (c) clusters 갱신 |
| "abandoned로 보내" | (a) status → abandoned (b) archived/로 이동 |

사용자가 안 물으면 안 한다.

#### 2.3. 이동 시 파일명 규칙

파일명 형식: `{대상폴더}--{작업내용}_{YYMMDD}.md`

`--` 앞의 접두사로 이동 대상을 결정하고, **이동 시 접두사(`{대상폴더}--`)를 제거**한다.

| 접두사 | 이동 대상 | 이동 후 파일명 |
|--------|----------|---------------|
| `decisions--` | docs/decisions/ | 접두사 제거 |
| `guides--` | docs/guides/ | 접두사 제거 |
| `incidents--` | docs/incidents/ | 접두사 제거 |
| `harness--` | docs/harness/ | 접두사 제거 |
| 접두사 없음 또는 판단 불가 | 사용자에게 질문 | — |

예시: `docs/WIP/decisions--api_design_260416.md` → `docs/decisions/api_design_260416.md`

#### 2.4. 차단 조건 (docs.md 규칙)

**SSOT**: `.claude/rules/docs.md` "## completed 전환 차단" 섹션. status를
completed로 전환할 때 키워드 hit 시 [c] 차단. 키워드 목록·예외 규칙은
rules/docs.md 참조.

→ 차단 시 사용자에게 [p] 분리 권장 (잔여를 별도 WIP로 옮기면 해제).

#### 2.5. 제약

- 계획 문서가 없는 작업이면 이 단계 전체 스킵
- 이동 대상은 docs/ 규칙에 정의된 폴더만 허용 (decisions, guides, incidents, harness, archived). 새 폴더 금지
- 이동·갱신 처리는 docs-manager 스킬에 위임 — 호출 시 전달 규약 (누수 #3 해소):
  - `trigger`: "commit Step 2.2 — 사용자가 '<원문>' 요청"
  - `intent`: `move-document`
  - `scope: focused`, `files`: 이동한 WIP 파일 (action·domain·status·moved_from)
  - `context.prior_steps`: "Step 2.1에서 ✅ 표시 갱신 완료, 이번 호출은 이동 + clusters 갱신만"
- **자동 status 변경·이동 금지** — 사용자가 명시 요청한 경우에만 (잘못된 자동 판단으로 정보 손실 위험)

### 3. 하네스 버전 체크 (harness-starter 전용)

> 이 단계는 **harness-starter 리포에서만** 실행한다. 일반 프로젝트에서는 건너뛴다.
> 리포 이름이 `harness-starter`이고, `.claude/HARNESS.json`이 존재할 때만 해당.

이번 커밋이 하네스 스타터에 의미 있는 업그레이드인지 판단한다.

| 변경 유형 | 버전 범프 | 예시 |
|-----------|-----------|------|
| 스킬/에이전트/규칙 신설 또는 폴더 구조 변경 | minor (0.X.0) | 에이전트 디렉토리 추가, docs/ 리팩토링 |
| 기존 스킬/스크립트의 로직 수정, 버그 수정 | patch (0.0.X) | pre-commit 조건 추가, 경로 오류 수정 |
| 문서만 수정, 오타 수정, 주석 변경 | 올리지 않음 | README 업데이트, 프론트매터 수정 |

**버전을 올릴 때:**
1. `.claude/HARNESS.json`의 `version` 필드 갱신
2. `docs/harness/promotion-log.md`에 이력 추가 — **버전 범프 한 줄만**.
   세부 변경은 해당 `decisions/`·`harness/` 문서 포인터로 대체.

**promotion-log 한 줄 규칙** (B+D 압축 원칙):
- 날짜 · 이전→이후 버전 · 근거 문서 링크 · minor/patch 근거 한 줄
- 세부 변경 목록을 본 파일에 **복사하지 않는다**. 해당 WIP/decisions/
  문서가 SSOT
- 50행 넘기면 분기 경계에서 `docs/archived/promotion-log-YYYY-q{N}-{suffix}.md`
  로 이동 + 신규 빈 template 시작 (`archived/`에 분기별 누적)

**판단이 애매하면** 사용자에게 묻는다. 자의적으로 올리지 않는다.

### 4. 스테이징

`git status`로 변경 파일 확인 후, 특별한 제외 요청 없으면 `git add .`

**메타 파일 자동 병합 (분리 커밋 차단)**:

Step 3에서 버전 범프가 있었거나, 본 커밋의 변경으로 인해 다음 메타 파일
이 함께 갱신되어야 한다면 **본 커밋에 자동 포함**한다 (분리 커밋 만들지
마라):

- `.claude/HARNESS.json` (버전 범프 시)
- `docs/harness/promotion-log.md` (버전 범프 시)
- `docs/clusters/*.md` (문서 추가·이동 시)

이유: 이 메타 파일을 별도 커밋으로 분리하면 review가 두 번 돌고, 두
번째 커밋은 의미 있는 검증이 불가능 (버전 1자리 변경에 6카테고리 검증).
0d047a5 이후 면제 리스트가 도입되어 분리할 이유가 사라졌다.

### 5. pre-check (정적 검사, 빠름)

**목적**: 비싼 LLM 리뷰 전에 값싼 정적 검사를 먼저 돌려 실패 시 조기 차단.
린터 에러·TODO/FIXME·WIP 잔여물·`--no-verify` 같은 명백한 문제는 Agent 호출
없이 걸러낸다.

**stdout 캡처 필수**: pre-check은 stderr에 사용자용 메시지를, **stdout에
review 전달용 요약 (현재 14 keys)**를 출력한다. Bash tool로 실행 시 stdout
전체를 스킬 컨텍스트에 보관해 Step 7 review prompt에 그대로 주입한다.

**tree-hash 캐시 분기** (memory 재설계 2차, v0.15.0 도입). 재commit
사이클에서 staged가 동일하면 pre-check·diff를 재사용:

```bash
CURRENT_TREE=$(git write-tree)
HASH_FILE=".claude/memory/session-tree-hash.txt"
if [ -n "$CURRENT_TREE" ] && [ -f "$HASH_FILE" ] && [ "$CURRENT_TREE" = "$(cat "$HASH_FILE")" ]; then
  PRE_CHECK_OUTPUT=$(cat .claude/memory/session-pre-check.txt)
else
  rm -f .claude/memory/session-*.txt
  mkdir -p .claude/memory
  git diff --cached > .claude/memory/session-staged-diff.txt
  PRE_CHECK_OUTPUT=$(bash .claude/scripts/pre-commit-check.sh \
    | tee .claude/memory/session-pre-check.txt)
  echo "$CURRENT_TREE" > "$HASH_FILE"
fi
```

- Step 6·7의 `git diff --cached` 호출은 `Read .claude/memory/session-staged-diff.txt`로 교체
- **중요**: pre-check이 **exit 2**여도 tee로 stdout은 캡처되지만 재시도 시
  tree가 바뀌어야만 재실행됨. 차단 시 exit 코드는 `$?`가 아닌 stdout의
  `pre_check_passed: false`로 판정
- snapshot 파일 3개(`session-staged-diff.txt`·`session-pre-check.txt`·
  `session-tree-hash.txt`)는 `.gitignore` 대상. 용도·수명은
  `.claude/rules/memory.md` "## 동적 snapshot" 섹션 SSOT

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
needs_test_strategist: true|false                  # 새 함수·신규 코드 파일 감지 시 true
test_targets: <콤마 구분 파일>                     # test-strategist 분석 대상
s1_level: ""|file-only|line-confirmed              # S1 시크릿 신호 강도 (stage 분기에 사용)
new_func_lines_b64: <base64>                       # 새 함수 선언 줄 (test-strategist 인라인용)
```

`signals`·`recommended_stage`는 Step 7에서 review 호출 분기와 prompt
주입에 모두 사용된다. **전체 stdout을 그대로 보관**해야 한다 (4 keys만
잘라내면 안 됨).

- **exit 2 (차단)**: stderr 메시지를 사용자에게 전달. 문제 수정 후
  스테이징(Step 4)부터 재시도. 리뷰 단계로 진행하지 마라.
- **exit 0 (통과)**: stdout 전체를 보관하고 6단계로 진행.

> pre-check은 commit 스킬만 실행한다. `git commit` hook에서 재실행하지
> 않음 (2회 낭비 제거, v0.9.4). Step 0에서 린터만 먼저, Step 5에서
> 전체(staged 신호 포함)로 총 1.x회 돌림. `--no-verify` 차단만
> bash-guard.sh에서 유지.

### 6. 변경 내역 분석

`git diff --cached`로 스테이징된 변경 내역을 읽고,
어떤 파일에서 어떤 로직이 어떻게 수정되었는지 파악한다.

### 7. 리뷰 (Stage 분기 — `.claude/rules/staging.md` 참조)

pre-check stdout의 `recommended_stage` 값에 따라 분기. `--no-review`/
`--quick`/`--deep` 플래그가 있으면 자동 분류 오버라이드.

#### Stage 결정 우선순위

```
1. --bulk      → Stage bulk 강제 (review 대신 정량 가드)
2. --no-review → Stage 0 (skip), 메시지에 [skip-review] 태그
3. --quick     → Stage 1 (micro) 강제
4. --deep      → Stage 3 (deep) 강제
5. recommended_stage (pre-check 결과)
```

**충돌 처리**: 둘 이상 동시 입력 시 **번호가 낮은 쪽이 우선** (staging.md
룰 F "다른 플래그·신호 모두 무시" 규정과 일치). 예: `--bulk --no-review`
→ `--bulk` 이김 (1번). `--quick --deep` → `--quick` 이김 (3번 vs 4번).
사용자에게 충돌 사실 1줄 알림:
> 🔧 플래그 충돌: --bulk와 --no-review 동시 입력 → --bulk 우선 (우선순위 1 < 2)

#### Stage별 행동

**Stage 0 (skip)**:
- review 호출 안 함
- 커밋 메시지에 `🔍 review: skip | signals: <...> | domains: <...>` 한 줄 자동 포함
- light 모드의 위험도 게이트와 호환 (light + Stage 0 → 그냥 통과)

**Stage 1 (micro)** — 1~2 tool calls, 시크릿/스코프 위주:
- review 호출, prompt에 `recommended_stage: micro` 명시
- 신규 파일만(S3)인 경우 신규 패스 모드 (프론트매터·구조만)
- 한도 내 종료, 응답 처리는 아래

**Stage 2 (standard)** — 3~5 tool calls, 현재 기본 동작:
- review 호출, prompt에 `recommended_stage: standard` 명시

**Stage 3 (deep)** — 10+ tool calls, 전체 검증:
- review 호출, prompt에 `recommended_stage: deep` 명시
- S1·S2·S8·S9(critical)·S14 hit 또는 사용자 `--deep`

**Stage bulk** — 거대 일괄 변경 (파일 30+ or diff 1500줄+):
- 사용자 `--bulk` 명시로만 활성 (자동 분류 없음)
- review 호출 안 함. **정량 가드 4종**이 대체
- 실행: `bash .claude/scripts/bulk-commit-guards.sh`
- 가드 전부 통과해야 커밋 허용. 하나라도 실패 시 stderr 원인·대응책
  출력 + exit 2 → **커밋 차단 (우회 불가)**
- 커밋 메시지에 `[bulk]` 태그 + `🔍 review: skip-bulk | signals: <...> |
  domains: <...>` 한 줄 강제
- test-strategist 자동 호출 스킵 (가드에 포함 안 됨. 필요하면 사용자가
  별도 `/commit` without `--bulk`로 재검증)

배경: review maxTurns 6 상한이 거대 diff에서 verdict 미출력을 유발
(incident `hn_review_maxturns_verdict_miss`). 정량 가드가 review 영역을
일부 대체:
- 테스트 3종 = 회귀 검증
- dead link 0 + 날짜 suffix 0 = 파일명·참조 정합성
- downstream-readiness = 다운스트림 영향 확인

review가 잡는 "의도 일관성"(예: 결정문과 스킬 문구 불일치)은 가드가 못
잡음 → 거대 변경 전 사람이 설계 단계에서 확보해야 한다.

#### 호출 시점·선행 조건

- **호출 시점**: Step 6(변경 내역 분석) 후 커밋 메시지 작성 전.
- **선행 조건**: Step 5 pre-check이 통과해야 호출한다. pre-check이 실패하면
  리뷰는 건너뛴다 (어차피 커밋 못 함).

#### test-strategist 병렬 호출 (자동 트리거)

pre-check stdout의 `needs_test_strategist: true`면 review와 **병렬로**
test-strategist 에이전트를 호출한다 (self-verify.md 트리거 자동화).

- 트리거: 신규 코드 파일 또는 새 함수·메소드·클래스 추가 (pre-check이 감지)
- 분담: review = 이 diff가 안전한가, test-strategist = 이 diff에 어떤
  테스트가 필요한가

**병렬 실행 방법 (강제):**

두 에이전트를 **한 번의 응답 메시지에 두 개의 Agent tool use를 동시에**
포함해야 병렬 실행. 순차 대기하면 각 에이전트 시간이 합산됨.

```
(한 응답 안에 다음 두 tool use 동시 배치 — 분리 메시지 금지)

Agent tool call #1:
  subagent_type: "review"
  prompt: <기존 review prompt 6블록>

Agent tool call #2:
  subagent_type: "test-strategist"
  prompt:
    # test-strategist.md "## 입력 계약" 충족. pre-check 필드 매핑:
    #   분석 대상     ← test_targets (콤마 분리 파일)
    #   pre-check 신호 ← new_func_lines_b64 (base64 -d 디코드) + needs_test_strategist
    #   맥락          ← staged diff (review와 같은 텍스트)
    #   목적          ← "테스트 누락 식별 + 우선순위 권고"
    # new_func_lines가 비어 있으면 "신규 파일 기반 분석"으로 명시.
    # 시그니처 평가 가능하므로 파일 재Read 불필요.
```

**정보 흐름 누수 #2 해소** (docs/WIP/harness--hn_info_flow_leak_audit):
pre-check이 이미 함수 추가 라인을 추출했으므로 test-strategist가 파일을
다시 Read할 필요 없음. commit이 base64 디코드해서 prompt에 인라인 박음.

```bash
# base64 디코드 예 (commit 스킬이 실행)
NEW_FUNC_LINES=$(echo "$NEW_FUNC_LINES_B64" | base64 -d 2>/dev/null)
```

**금지 (순차 실행 유발 패턴):**
- review 먼저 호출 → 결과 받고 → test-strategist 호출 (두 메시지로 분리)
- 하나 끝난 뒤 다음 박기
- "review 결과 보고 test-strategist 필요한지 판단" (이미 pre-check에서 결정됨)

**응답 처리 (두 결과 종합):**
- review 차단 → 커밋 진행 X. test-strategist 권고는 수정 후 재검토.
- review 통과 + test-strategist 권고 있음 → 커밋 진행 + 사용자에게 권고 요약 보고.
- 둘 다 통과 → 그대로 진행.

플래그로 제어:
- `--no-test-strategy`: 자동 호출 스킵 (커밋 메시지에 `[skip-test-strategy]`)

#### 응답 처리

review의 첫 줄 `verdict:` 값으로 분기 (review.md "## 출력 형식" SSOT):

- **`verdict: block`**: 커밋 진행하지 말고 [차단] 섹션을 사용자에게 전달. 수정 후 재시도.
- **`verdict: warn`**: 진행하되 [주의] 섹션을 커밋 메시지에 요약 반영.
- **`verdict: pass`**: 그대로 다음 단계로.
- **verdict 누락**: review 규격 미준수. 재호출 또는 사용자 확인. 임의 해석 금지.

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

### light 모드

커밋 본문에 핵심 변경 요약을 간결하게 포함한다:
- 무엇이 바뀌었는가 (1~3줄)
- 연관 문서 경로 (있으면)

```bash
git commit -m "feat: [제목]" -m "[간결한 본문]"
```

### strict 모드

커밋 본문에 `[📝 주요 참고 사항]` 섹션을 포함한다:
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
rm -f .claude/memory/session-*.txt
```

라이프사이클: commit 실패 시 재시도에서 tree-hash 일치하면 재사용, 성공
후에는 다음 커밋 사이클을 위해 초기화. `rules/memory.md` "## 동적
snapshot" 섹션 SSOT.

### 요약에 다음을 포함:
- 커밋 SHA + 메시지 1줄
- 변경 stat (파일 수, +/- 라인)
- **리뷰 결과**: "✅ 리뷰 통과" / "⚠️ 리뷰 경고: ..." / "🚫 리뷰 차단: ..." / "리뷰 스킵 (`--no-review`)"
- (선택) push 결과 (origin/main 업데이트 SHA)

---

## 주의

- `--no-verify` 사용 금지 (`pre-commit-check.sh` hook에서 차단됨).
- docs/WIP/에 completed/abandoned 파일이 남아있으면 안 된다.
- 커밋 메시지는 한국어.
- 리뷰 차단 시 `--no-review`로 우회하지 마라. 지적 사항을 실제로 수정한 후 재시도.
