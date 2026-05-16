---
name: harness-upgrade
description: 하네스 업그레이드. harness-upstream remote에서 fetch → 변경 분석 → 3-way merge 대화형 병합. 구 파일 자동 마이그레이션 포함. "harness-upgrade", "하네스 업그레이드", "하네스 업데이트" 요청 시 사용.
---

# harness-upgrade 스킬

`harness-upstream` remote에서 최신 하네스를 가져와 대화형으로 병합한다.
**한 명령으로 완료** — 별도 스크립트 실행 불필요.

## 전제

- 일반 프로젝트: `harness-upstream` remote가 설정되어 있어야 한다.
  - `h-setup.sh`로 설치했으면 자동 설정됨.
  - `/harness-adopt`로 이식했으면 Step 6에서 설정됨.
  - 없으면 안내 후 중단.
- harness-starter 자체(`is_starter: true`): `origin`을 upstream으로 사용. 별도 remote 불필요.
- `.claude/HARNESS.json`이 존재해야 한다.

## 핵심 원칙

- **사용자 커스터마이징 보존**: 사용자가 채운 내용은 절대 덮어쓰지 않는다.
- **3-way merge 우선**: 기본은 base + theirs + ours 3-way merge. base 부재·충돌 해소 실패 시 사용자에게 theirs/ours 결정 요청.
- **승인 필수**: 각 파일 병합 전 사용자에게 계획을 보여주고 승인받는다.
- **검증 필수**: 병합 후 구문 오류를 검증한다.

## 흐름

### Step 0. 사전 점검

1. `.claude/HARNESS.json` 존재 확인. 없으면 중단.

#### 0.1. worktree 잔여 자동 정리 (CLAUDE.md 절대 규칙 강제)

CLAUDE.md `## 절대 규칙`은 worktree 생성을 금지하지만, 과거 세션이나 다른
도구가 만든 잔여가 있을 수 있다. upgrade 시작 시 자동 정리:

```bash
STRAY=$(git worktree list --porcelain | awk '/^worktree / && NR>1 {print $2}')
if [ -n "$STRAY" ]; then
  echo "⚠ worktree 잔여 발견 — CLAUDE.md 절대 규칙 위반 상태:"
  echo "$STRAY"
  for wt in $STRAY; do
    DIRTY=$(git -C "$wt" status --porcelain 2>/dev/null)
    if [ -n "$DIRTY" ]; then
      echo "  ⚠ $wt: uncommitted 변경 있음 — 자동 정리 skip"
      echo "     변경 목록:"
      echo "$DIRTY" | sed 's/^/       /'
      echo "     정리하려면: 변경 commit/stash 후 git worktree remove $wt"
    else
      echo "  ✓ $wt: clean → 자동 정리"
      git worktree remove "$wt" 2>&1
      [ -d "$wt" ] && rm -rf "$wt"
    fi
  done
  git worktree prune
fi
```

**원칙**: clean은 자동 제거, dirty는 안내만 (작업 손실 방지). `git worktree
prune`으로 stale 메타데이터까지 청소.

#### 0.2. 스타터 자체 여부 판별

2. **스타터 자체 여부 판별** — `HARNESS.json`의 `is_starter` 확인:
   - **`is_starter: true`** → 이 리포가 harness-starter 자체. `harness-upstream` remote가 필요 없다. `origin`을 upstream으로 사용하고 Step 1로 진행.
   - **그 외** → 아래 3~4번으로 진행.
3. `harness-upstream` remote 존재 확인:
   ```bash
   git remote get-url harness-upstream
   ```
   없으면:
   ```
   ❌ harness-upstream remote가 없습니다.

   방법 1: remote 설정 후 다시 실행
     git remote add harness-upstream <스타터 리포 URL>
     /harness-upgrade

   방법 2: 스타터에서 파일 복사 방식으로 업그레이드
     cd /path/to/harness-starter && bash h-setup.sh --upgrade /path/to/project
     /harness-upgrade  (스테이징된 파일 병합)

   또는 /harness-adopt를 실행하면 remote가 자동 설정됩니다.
   ```
4. `HARNESS.json`에 `adopted_at` 필드 확인:
   - **있으면** → 정상. Step 1로 진행.
   - **없고 `is_starter`가 false/없음** → adopt 미완료 프로젝트.
     ```
     ⚠️ adopt가 완료되지 않은 프로젝트입니다.
     upgrade 전에 harness-adopt를 먼저 실행합니다.
     (문서 재분류, 프론트매터, clusters 생성이 필요합니다)
     ```
     harness-adopt 스킬을 실행한다. adopt 완료 후 upgrade를 이어서 진행.

### Step 1. Fetch + 버전 비교

Step 0에서 결정된 upstream remote를 사용한다:
- `is_starter: true` → `UPSTREAM_REMOTE=origin`
- 그 외 → `UPSTREAM_REMOTE=harness-upstream`

```bash
git fetch $UPSTREAM_REMOTE
```

#### Windows Git Bash path 변환 가드 (필수)

**모든 `git show <ref>:<path>` 형태 명령에 `MSYS_NO_PATHCONV=1` prefix
필수.** 빠뜨리면 Git Bash가 `:`를 path separator로 보고 `<ref>:<path>`를
Windows path로 변환하여 다음 에러:

```
fatal: ambiguous argument 'harness-upstream\main;.claude\HARNESS.json':
unknown revision or path not in the working tree.
```

incident: `docs/incidents/msys_path_conversion_*` 참조.

권장 형태:
```bash
MSYS_NO_PATHCONV=1 git show $UPSTREAM_REMOTE/main:.claude/HARNESS.json
```

또는 `--` 사용 + path 뒤에 명시:
```bash
git show $UPSTREAM_REMOTE/main -- .claude/HARNESS.json   # 다른 동작 — diff 아님 주의
```

가장 안전: `cat-file blob`:
```bash
git cat-file blob $UPSTREAM_REMOTE/main:.claude/HARNESS.json
```

본 SKILL의 모든 후속 `git show <ref>:<path>` 호출은 위 가드 적용을
가정한다. 호출자는 매 명령마다 `MSYS_NO_PATHCONV=1` prefix 또는
`cat-file blob` 형태로 변환할 것.

fetch 실패 시 네트워크 문제로 보고하고 중단.

#### installed_from_ref sanity check

`HARNESS.json`의 `installed_from_ref`가 stale이면 3-way merge가 ADDED 카테
고리를 부풀려 분류한다 (incident: hn_upstream_anomalies.md F 항목). fetch
직후 실재성 확인:

```bash
INSTALLED_REF=$(jq -r '.installed_from_ref // ""' .claude/HARNESS.json)
if [ -n "$INSTALLED_REF" ] && [ "$INSTALLED_REF" != "unknown" ]; then
  if ! git cat-file -e "$INSTALLED_REF" 2>/dev/null; then
    echo "⚠ installed_from_ref ($INSTALLED_REF)가 git history에 없습니다."
    echo "   원인 추정: 이전 업그레이드의 갱신 누락 또는 history 재작성."
    echo "   3-way merge가 ADDED를 부풀려 분류할 수 있습니다."
    echo "   재지정: HARNESS.json의 installed_from_ref를 마지막 정상 업그레이드 시점 ref로 수동 갱신."
    echo "   계속하시겠습니까? (two-way 모드로 진행됩니다) [y/N]"
    # 사용자 응답에 따라 BASE_REF=""로 비우고 two-way로 강제 또는 중단
  elif ! git merge-base "$UPSTREAM_REMOTE/main" "$INSTALLED_REF" >/dev/null 2>&1; then
    echo "⚠ installed_from_ref ($INSTALLED_REF)가 upstream history에 도달 불가."
    echo "   권장: 사용자에게 재지정 요청 후 진행."
  fi
fi
```

sanity check 통과 후 버전 비교로 진행.

버전 비교:
```bash
# 현재 버전
CUR_VERSION=$(현재 HARNESS.json의 version 필드)

# 업스트림 버전 (MSYS path 변환 가드 필수)
SRC_VERSION=$(MSYS_NO_PATHCONV=1 git show $UPSTREAM_REMOTE/main:.claude/HARNESS.json | jq -r '.version')
```

- 이미 최신이면: `✅ 이미 최신 버전 (X.Y.Z). 업그레이드 불필요.` → 종료.
- 업스트림 버전을 읽을 수 없으면 에러 보고 후 중단.

버전과 방식을 사용자에게 표시:
```
═══ 하네스 업그레이드 ═══
현재:    0.9.2
최신:    1.0.0
방식:    remote ($UPSTREAM_REMOTE)
base:    abc1234 (또는 "없음")
```

### Step 2. 구 파일 마이그레이션

v1.0.0 이전 프로젝트에 남아있을 수 있는 구 파일을 정리한다.

| 구 파일 | 처리 |
|---------|------|
| `.claude/HARNESS_VERSION` | 버전을 HARNESS.json에 반영 후 삭제 |
| `.claude/.harness_adopted` | adopted_at을 HARNESS.json에 추가 후 삭제 |
| `.claude/scheduled_tasks.lock` | 삭제 (런타임 찌꺼기) |
| `.claude/ts_errors.log` | 삭제 (런타임 찌꺼기) |

구 파일이 없으면 이 단계를 건너뛴다.
마이그레이션 결과를 사용자에게 보고한다.

### Step 3. 변경 파일 분석

HARNESS.json에서 `installed_from_ref`를 읽어 diff 모드를 결정한다:

| 조건 | diff 모드 |
|------|----------|
| `installed_from_ref`가 유효한 커밋 | three-way (base + ours + theirs) |
| 없거나 "unknown" | two-way (ours + theirs만) |

하네스 파일 범위 (업그레이드 대상):
```
.claude/skills .claude/scripts .claude/rules .claude/agents
.claude/settings.json .claude/HARNESS.json
CLAUDE.md h-setup.sh docs/harness
docs/guides/project_kickoff_sample.md
```
+ **rules 참조 docs (동적 탐색, 아래 참조)**

**rules 참조 docs 동적 확장**: `.claude/rules/*.md` 본문에서
`docs/(guides|decisions)/[a-z0-9_-]+\.md` 패턴을 grep으로 추출해
**하네스 파일 범위에 자동 포함**한다. rules가 참조하는 docs는 그 자체가
규칙의 일부이므로 이식 누락 시 dead link 발생 — 수동 화이트리스트 유지
없이 원천 방지.

```bash
# Step 3 실행 전 동적 탐색 (upstream 원본 기준으로 grep, 존재 파일만 필터)
REFERENCED_DOCS=$(
  git show harness-upstream/main -- .claude/rules/ 2>/dev/null \
    | grep -hoE 'docs/(guides|decisions)/[a-z0-9_-]+\.md' \
    | sort -u \
    | while read p; do
        # upstream에 실제 파일이 존재하는 것만 포함 (오탐 방어)
        git cat-file -e "harness-upstream/main:$p" 2>/dev/null && echo "$p"
      done
)
```

발견된 경로는 Step 3 분류 시 "하네스 파일 범위"에 합쳐진다. rules 수정
시 새 docs 참조 추가해도 **수동 등록 불필요** — grep이 자동 발견.

**오탐 방어 (2단)**:
1. 위 `git cat-file -e` 체크가 **upstream에 실제 존재하는 파일만** 통과
   시킴. rules 본문에 예시·반례로 등장한 가상 경로(`docs/guides/bad_example.md`
   등)는 upstream에 파일이 없어 자동 필터링됨.
2. 통과한 경로 중 다운스트림에 없으면 "신규" 카테고리로 추가 제안. 실제
   의도된 참조라 다운스트림에 추가되어야 정상.

변경된 파일을 분류한다.

**분류 전 필수: `--diff-filter`로 상태별 분리**

`git diff --name-only`는 수정(M)·추가(A)·삭제(D)를 구분 없이 나열하므로
**절대 사용 금지**. 삭제 파일을 덮어쓰기 대상에 포함하면 `git show
<ref>:<path>` 단계에서 `fatal: path exists on disk, but not in upstream`
에러가 발생한다 (incident: 2026-04-25 harness-upgrade 버그).

```bash
BASE_REF=<installed_from_ref>  # 없으면 two-way 모드로 전환

# 수정 파일 (M) — 자동 덮어쓰기 또는 3-way merge 대상
MODIFIED=$(git diff "$BASE_REF" "$UPSTREAM_REMOTE/main" \
  --diff-filter=M --name-only -- <하네스 파일 범위>)

# 추가 파일 (A) — upstream에만 있음 → 신규 제안 대상
ADDED=$(git diff "$BASE_REF" "$UPSTREAM_REMOTE/main" \
  --diff-filter=A --name-only -- <하네스 파일 범위>)

# 삭제 파일 (D) — upstream에서 제거됨 → Step 7 삭제 제안 대상
# ⚠️ 이 목록 파일에는 git show <ref>:<path>를 시도하지 마라 — upstream에 없음
DELETED=$(git diff "$BASE_REF" "$UPSTREAM_REMOTE/main" \
  --diff-filter=D --name-only -- <하네스 파일 범위>)
```

two-way 모드(base 없음)에서는 DELETED를 추출할 수 없으므로 삭제 카테고리
는 건너뛴다. upstream에 없는 로컬 파일은 "사용자 전용"으로 그대로 보존.

**MIGRATIONS.md `### 변경 파일` 섹션 우선 참조**:

upstream MIGRATIONS.md의 해당 버전 섹션에 `### 변경 파일` 표가 있으면,
git diff 결과보다 이 표를 **우선 신뢰**한다. 표의 `처리` 열 값이 분류 근거:

| 처리 값 | 분류 |
|---------|------|
| `자동 덮어쓰기` | 자동 덮어쓰기 |
| `3-way merge` | 3-way merge |
| `신규 추가` | 신규 |
| `삭제` | 삭제 |

표에 없는 파일은 git diff 결과로 분류한다 (기존 로직 유지).
표 자체가 없는 버전은 git diff만으로 분류 (하위 호환).

분류 표:

| 카테고리 | 감지 | 대상 | 처리 |
|----------|------|------|------|
| 자동 덮어쓰기 | `MODIFIED` 중 `.claude/scripts/*`, `h-setup.sh`, **`docs/harness/MIGRATIONS.md`** | — | upstream 그대로 적용. **MIGRATIONS.md는 upstream 소유 — 다운스트림이 수정했어도 반드시 덮어씀** |
| 3-way merge | `MODIFIED` 중 위 이외 | `CLAUDE.md`, `.claude/rules/*`, `.claude/skills/*`, 기타 | 대화형 병합 |
| **사용자 전용 (절대 건드리지 마라)** | `MODIFIED`·`ADDED` 중 사용자 전용 리스트 해당 | `HARNESS.json`, `coding.md`, `naming.md`, **`README.md`**, **`CHANGELOG.md`**, **`.gitignore`**, **`docs/decisions/*`**, **`docs/incidents/*`**, **`docs/WIP/*`**, **`docs/guides/*`**, **`docs/harness/*`** (`docs/harness/MIGRATIONS.md` 제외 — 위 자동 덮어쓰기 처리), **`docs/harness/migration-log.md`** (다운스트림 소유 기록 파일, 절대 덮어쓰기 금지) (단 "하네스 파일 범위"의 명시 목록 + `REFERENCED_DOCS` 동적 탐색 결과는 제외) | **무조건 건너뜀.** starter 버전이 다운스트림에 없어도 추가 안 함. diff가 있어도 표시만 하고 병합 시도 X. |
| 신규 | `ADDED` 중 사용자 전용 리스트 **미**해당 | 타겟에 없는 파일 | 추가 제안 (Step 6) |
| 삭제 | `DELETED` (three-way만) | upstream에서 제거된 파일 | 삭제 제안 (Step 7). **`git show`로 내용 조회 절대 금지** |

### 사용자 전용 파일 처리 규칙 (강행)

위 "사용자 전용" 카테고리의 파일은 **starter에 어떤 변경이 있든 무조건
건너뛴다**. 사유:

- README/CHANGELOG/.gitignore: 다운스트림 프로젝트 자체 문서. starter
  버전을 덮으면 사용자 콘텐츠 손실.
- decisions/incidents/WIP/guides: 다운스트림이 작성한 docs. starter는
  `docs/harness/` + `docs/guides/project_kickoff_sample.md`만 관리.

**금지 행동:**
- "다운스트림에 README 없으니 starter 버전 추가" — 절대 X
- "diff 있으니 3-way merge 제안" — 절대 X
- "사용자 confirm 받고 덮어쓰기" — 사용자 전용은 confirm 자체 안 띄움

starter의 README가 변경됐다는 사실은 사용자에게 **정보로만 보고**
("upstream README 변경됨, 본인 README 갱신 검토는 사용자 판단"), 어떤
수정도 시도하지 않는다.

분석 결과를 사용자에게 보여준다:
```
📋 변경 분석 완료

  자동 덮어쓰기: 4개
  3-way merge:   3개
  신규:          2개
  사용자 전용:   2개 (건너뜀)
```

### Step 4. 자동 덮어쓰기

스크립트/인프라 파일은 사용자 수정 없이 upstream 그대로 적용:

```bash
MSYS_NO_PATHCONV=1 git show <upstream_ref>:<파일경로> > <파일경로>
```

목록을 사용자에게 보여주고 승인 없이 바로 적용한다:
```
📦 자동 덮어쓰기 (스크립트/인프라)

  .claude/scripts/session-start.sh
  .claude/scripts/pre_commit_check.py
  h-setup.sh

→ 적용 완료
```

### Step 5. 3-way merge

#### three-way 모드

각 파일에 대해:

```bash
TMPDIR=$(mktemp -d)

# base: 설치 시점의 파일
MSYS_NO_PATHCONV=1 git show <base_ref>:<파일경로> > "$TMPDIR/base"

# theirs: upstream 최신
MSYS_NO_PATHCONV=1 git show <upstream_ref>:<파일경로> > "$TMPDIR/theirs"

# ours: 현재 작업 디렉토리 — CRLF→LF 정규화 (Windows + Git Bash 환경 통째 충돌 방지)
# incident: hn_upstream_anomalies.md D 항목 — autocrlf 환경에서 ours만 CRLF면
# merge-file이 1줄부터 끝까지 통째 충돌로 마킹.
tr -d '\r' < <파일경로> > "$TMPDIR/ours"

# 3-way merge
git merge-file "$TMPDIR/ours" "$TMPDIR/base" "$TMPDIR/theirs"
MERGE_RESULT=$?

rm -rf "$TMPDIR"
```

- `MERGE_RESULT = 0`: 충돌 없이 병합 성공
- `MERGE_RESULT > 0`: 충돌 존재 (마커 포함)
- `MERGE_RESULT < 0`: 에러

#### two-way 모드 (base 없음)

사용자에게 양쪽 버전을 보여주고 선택:

```
📄 .claude/rules/docs.md — base 없음, 수동 병합 필요

현재 (ours):
  [현재 파일 내용 요약]

업스트림 (theirs):
  [upstream 파일 내용 요약]

선택: [ours 유지 / theirs 적용 / 수동 편집]
```

#### 본체 swap sanity check (3-way 모드 전용 — FR-001 대응)

`git merge-file` 호출 **직전**, base와 ours를 비교해 본체 swap 사고를 감지한다.

배경: 다운스트림에서 어떤 파일의 본체가 다른 SKILL/스크립트로 통째 교체되는
사고가 발생할 수 있다. 이 경우 base(설치 시점) ≠ ours(현재 본체)이고 patch
알고리즘이 ours 그대로 유지한 채 충돌 0으로 통과 → 사고가 upgrade 흐름에서
영구 보존된다 (다운스트림 v0.42.0 측정 사례: `eval/SKILL.md` 본체가
`implementation/SKILL.md`로 swap된 채 3회 upgrade 통과).

**검사 1 — frontmatter `name:` 필드 변경**:

```bash
# `.md` 파일 한정. SKILL.md의 frontmatter `name:` 첫 매칭 비교
BASE_NAME=$(awk '/^name:/{print $2; exit}' "$TMPDIR/base")
OURS_NAME=$(awk '/^name:/{print $2; exit}' "$TMPDIR/ours")
if [ -n "$BASE_NAME" ] && [ -n "$OURS_NAME" ] && [ "$BASE_NAME" != "$OURS_NAME" ]; then
  echo "🚨 ALERT: 본체 swap 의심 — frontmatter name 필드 변경"
  echo "  base:  name: $BASE_NAME"
  echo "  ours:  name: $OURS_NAME"
  echo "  파일:  <파일경로>"
  echo "  스킬명 변경은 거의 항상 사고. 정말 다운스트림이 의도한 변경인가?"
fi
```

`name:` 필드가 다르면 즉시 ALERT (스킬명 변경은 거의 항상 사고). 사용자에게
`[Y 의도된 변경 / N theirs로 강제 교체 / S 이 파일 skip]` 3택을 묻는다.

**검사 2 — base ↔ ours 라인 차이율**:

```bash
BASE_LINES=$(wc -l < "$TMPDIR/base")
DIFF_LINES=$(diff --suppress-common-lines "$TMPDIR/base" "$TMPDIR/ours" 2>/dev/null | grep -cE '^[<>]')
if [ "$BASE_LINES" -gt 0 ]; then
  RATIO=$(awk -v d="$DIFF_LINES" -v b="$BASE_LINES" 'BEGIN{printf "%.0f", (d/b)*100}')
  if [ "$RATIO" -ge 70 ]; then
    echo "🚨 본체 swap 의심: base ↔ ours 차이율 ${RATIO}% (임계 70%)"
    echo "  파일: <파일경로>"
    echo "  base ${BASE_LINES}줄 / 차이 ${DIFF_LINES}줄"
    echo "  정말 다운스트림이 의도한 변경인가?"
  fi
fi
```

차이율 ≥70%이면 동일 3택 confirm.

**3택 처리**:
- `Y` (의도된 변경): 검사 통과 표시 후 정상 3-way merge로 진행
- `N` (theirs로 강제 교체): `cat "$TMPDIR/theirs" > <파일경로>` 적용. `merge-file` skip. 처리 결과는 "본체 swap 복구"로 별도 카운트
- `S` (이 파일 skip): 해당 파일 ours 그대로 유지. **`UNAPPLIED_FILES` 목록에 추가** (Step 11의 "그 외 미적용" 카테고리에 합류)

검사 적용 대상은 **3-way 모드(base 존재)**. 2-way 모드는 base 자체가 없어
적용 불가. 적용 파일 종류: `.md`·`.sh`·`.py`·`.json` 등 텍스트 전반.

#### 파일별 처리 절차

1. merge 실행 (3-way 또는 2-way) — **3-way 모드는 위 sanity check 먼저 수행**
2. 충돌 없으면 → diff를 사용자에게 보여주고 승인 없이 바로 적용:
   ```
   📄 .claude/rules/docs.md — 충돌 없이 병합됨

   변경 내용:
     + 프론트매터 필수화 규칙 추가 (3줄)
     + 문서 탐색 트리거 섹션 추가 (15줄)

   사용자 커스터마이징 보존:
     도메인 목록, 폴더 판단 기준 (변경 없음)

   → 적용 완료
   ```
3. 충돌 있으면 → 충돌 마커를 보여주고 해결 (사용자 개입 필요):
   ```
   📄 .claude/skills/commit/SKILL.md — 충돌 1개

   <<<<<<< ours
   [사용자 버전]
   =======
   [upstream 버전]
   >>>>>>> theirs

   해결 방법: [ours 유지 / theirs 적용 / 직접 편집]
   ```
   충돌 해소 후 해당 파일을 `CONFLICT_RESOLVED` 목록에 추가한다.
   (two-way 모드에서 사용자가 직접 편집한 파일도 동일하게 추가)
4. 승인 후 파일에 적용
5. 검증:
   - `.sh`: `bash -n <파일>`
   - `.json`: JSON 파싱 유효성
   - `.md`: 프론트매터 YAML 파싱

### Step 6. 신규 파일 추가

upstream에만 있는 파일을 처리한다. **단, `starter_skills` 목록의 스킬 폴더는 제외한다.**

#### 6.0. starter_skills 필터

HARNESS.json의 `starter_skills` 값을 읽어 다운스트림 전달 제외 목록을 구성한다:

```bash
STARTER_SKILLS=$(python3 -c "
import json
d = json.load(open('.claude/HARNESS.json'))
print(d.get('starter_skills', 'harness-init,harness-adopt,harness-dev'))
" 2>/dev/null || echo "harness-init,harness-adopt,harness-dev")

# ADDED 파일 중 starter_skills 경로 제외
# 예: starter_skills="harness-init,harness-adopt,harness-dev"
# → .claude/skills/harness-init/**, .claude/skills/harness-adopt/**, .claude/skills/harness-dev/** 제외
```

ADDED 파일 목록에서 `.claude/skills/{starter_skill}/` 경로에 해당하는 파일은 **조용히 제외** (사용자에게 별도 알림 없음).

#### 6.1. 적용

```bash
MSYS_NO_PATHCONV=1 git show <upstream_ref>:<파일경로> > <파일경로>
```

파일 목록을 보여주고 승인 없이 바로 적용한다:
```
📦 신규 파일 추가

  .claude/agents/doc-finder.md (신규 에이전트)
  .claude/skills/advisor/SKILL.md (신규 스킬)
  (starter 전용 스킬 harness-init, harness-adopt, harness-dev 제외됨)

→ 추가 완료
```

### Step 7. 삭제 + 격하 잔재 처리

두 종류의 잔재를 함께 처리한다:

**(A) upstream에서 제거된 파일** (three-way 모드만) — DELETED 카테고리.

**(B) starter_skills 격하 잔재** — upstream `HARNESS.json.starter_skills`에
포함됐는데 다운스트림 디스크에 폴더가 존재하는 경우. starter가 "이 스킬은
starter 전용으로 격하"한 신호인데 다운스트림은 옛 버전에서 받은 폴더를
보유 중 → 회수 필요.

```bash
# (A) upstream에서 제거된 파일
DELETED=$(git diff "$BASE_REF" "$UPSTREAM_REMOTE/main" --diff-filter=D --name-only \
  -- <하네스 파일 범위>)

# (B) starter_skills 격하 감지 — 다운스트림 전용
# starter 본인은 starter_skills 폴더가 자기 파일이므로 검사 skip
IS_STARTER=$(python3 -c "
import json
d = json.load(open('.claude/HARNESS.json', encoding='utf-8'))
print('true' if d.get('is_starter') else 'false')
" 2>/dev/null)

DEMOTED_DIRS=()
if [ "$IS_STARTER" = "false" ]; then
  STARTER_SKILLS=$(python3 -c "
import json
d = json.load(open('.claude/HARNESS.json', encoding='utf-8'))
print(d.get('starter_skills', ''))
" 2>/dev/null | tr ',' '\n')

  for skill in $STARTER_SKILLS; do
    [ -d ".claude/skills/$skill" ] && DEMOTED_DIRS+=(".claude/skills/$skill/")
  done
fi
```

사용자 알림 + 처리:

**(A) DELETED — 사용자 [Y/n] 응답** (사용자가 fork·커스텀했을 잠재 가능성):

```
📦 upstream에서 제거된 파일 (M개)
  .claude/rules/anti-defer.md
  .claude/scripts/orchestrator.py
  ...
삭제할까요? [Y/n/건너뛰기]
```

사용자가 건너뛰면 파일을 남긴다.

**(B) 격하 잔재 — 강제 삭제 + 알림만** (starter 소유 자기 파일이므로 보존 가치 0):

```
🗑️ starter 전용으로 격하된 스킬 자동 삭제 (N개):
  .claude/skills/harness-dev/  (starter_skills 등록 — 다운스트림 미전파 의도)
```

```bash
for d in "${DEMOTED_DIRS[@]}"; do
  rm -rf "$d"
  echo "  삭제: $d"
done
```

응답 없이 즉시 삭제. 다운스트림이 격하 폴더를 커스텀했을 가능성은 메커니즘
상 0 — 사용자가 starter_skills 폴더를 의도적으로 보유할 이유 없음 (starter
전용 도구 격하 = 다운스트림에 무용).

**주의**: (B) 검사는 다운스트림(`is_starter: false`)에서만 실행. starter
본인(`is_starter: true`)은 자기 파일이므로 검사 skip (코드 분기 박힘).

### Step 8. settings.json 동기화

settings.json은 통째로 교체하지 않는다. **starter 소유 항목만 동기화**
하고 **사용자 커스텀은 건드리지 않는다**.

#### 8.1. permissions.allow 동기화 (v0.26 신규)

`permissions.allow`에도 starter가 관리하는 기본 항목과 사용자 추가 항목이
공존한다. hooks와 동일한 방식으로 분리해 동기화한다.

**starter 신규 항목 감지:**
- upstream `permissions.allow` 목록과 현재 목록을 diff
- **upstream에만 있는 항목** = starter가 새로 추가한 항목 → 추가 제안
- **현재에만 있는 항목** = 사용자가 추가한 항목 → 건드리지 않음

**위험 패턴 명시 승인 강제** (incident: hn_upstream_anomalies.md B):

upstream 신규 항목 중 다음 위험 패턴이 포함되면 일괄 자동 추가 금지.
사용자에게 별도 항목으로 표시하고 **각각 명시 승인** 받는다:

- `Bash(rm *)`, `Bash(rm -rf *)` 등 와일드카드 삭제
- `Bash(* --force *)`, `Bash(* -f *)` (force 동작)
- `Bash(* reset --hard*)`, `Bash(* push --force*)`
- `Bash(export *)` (임의 환경변수 설정 — 보안 영향)
- `Bash(curl * | *sh*)`, `Bash(* | sudo *)` (실행 파이프)

표시 + 승인:
```
📦 permissions.allow 동기화

  추가 제안 (upstream 신규 starter 항목):
    "Bash(HARNESS_DEV=1 git *)"
    "Bash(python3 .claude/scripts/pre_commit_check.py *)"
    "Bash(python3 -m pytest *)"

  보존됨 (사용자 추가 항목):
    "Bash(cmake *)"
    "Bash(ctest *)"

추가할까요? [Y/n/각각 확인]
```

주의: `permissions.allow`의 `Bash(...)` 패턴은 **허용 목록**이므로
`rules/hooks.md`의 argument-constraint 금지 규칙 적용 대상이 아님 (혼동 금지).

#### 8.2. 누락 hook 추가

1. upstream에 있지만 현재에 없는 matcher를 찾아 승인 후 추가.

#### 8.3. 구 hook 제거 (v0.7.0 신규)

starter 소유 hook이 upstream에서 사라졌으면 다운스트림에서도 제거한다.
예: v0.6.x의 광역 매처(`Bash(* --no-verify*)`·`Bash(git commit -n)` 등)가
v0.7.0에서 단일 `bash-guard.sh`로 통합됨 → 구 매처는 찌꺼기.

**starter 소유 hook 판정:**
- `matcher` 필드가 starter 기본값 (예: `"Bash"`, `"Write|Edit|MultiEdit"`,
  빈 문자열 `""`)
- `hooks[].command`가 `bash .claude/scripts/<starter-script>.sh` 형태
  (session-start·stop-guard·post-compact-guard·auto-format·bash-guard·
  write-guard·pre-commit-check 등 starter 제공 스크립트)
- 또는 `if` 필드에 argument-constraint 패턴 (`Bash(... -X ...)` 같은
  rules/hooks.md 금지 패턴)

**사용자 커스텀 판정:**
- 위 어디에도 해당 안 하는 matcher·command
- 또는 `command`가 starter에 없는 외부 스크립트·도구 호출

표시 + 승인:
```
📦 구 starter hook 감지 (upstream에서 제거됨)

  [PreToolUse] "Bash(git commit -n)" → bash-guard.sh로 통합
  [PreToolUse] "Bash(* --no-verify*)" → bash-guard.sh로 통합

제거할까요? [Y/n/각각 확인]

(사용자 커스텀 hook은 변경 없음: <사용자 영역 요약>)
```

사용자 커스텀은 **보여주기만** 하고 수정 제안 안 함. 사용자가 직접
판단하도록 남긴다.

### Step 9. docs/ 정합성 검증

업그레이드로 docs/ 관련 규칙(docs.md, 폴더 구조, 프론트매터 스펙)이 변경되었을 수 있다.
`.claude/scripts/docs_ops.py`로 검증:

```bash
bash .claude/scripts/docs_ops.py validate           # 프론트매터·약어 검증
bash .claude/scripts/docs_ops.py verify-relates     # relates-to 경로 유효성
bash .claude/scripts/docs_ops.py cluster-update     # clusters/ 자동 재생성
```

(audit #10, 2026-04-22: docs-manager 스킬 폐기 후 `docs_ops.py`로 이관)
- 업그레이드가 docs/ 규칙 자체를 바꿔 전수 검증이 필요하다고 판단되면
  `scope: full` + `intent: full-refresh`로 명시 (드문 경우)

문제가 발견되면 사용자에게 보고하고 수정을 제안한다.
문제가 없으면 "docs/ 정합성 확인 완료"로 넘어간다.

### Step 10. 마이그레이션 액션 표시

업스트림의 `docs/harness/MIGRATIONS.md`를 읽어 **수동 적용** 항목을
사용자에게 보여준다.

MIGRATIONS.md는 항상 현재 적용 대상 버전 1개 섹션만 유지한다 (v0.26.2
구조 재설계). 버전 범위 추출 불필요 — 섹션이 있으면 그대로 표시.

```bash
# upstream의 MIGRATIONS.md를 읽음
MSYS_NO_PATHCONV=1 git show $UPSTREAM_REMOTE/main:docs/harness/MIGRATIONS.md
```

**수동 적용 항목이 있는 경우:**

```
═══ 수동 액션 필요 (MIGRATIONS.md) ═══

v0.26.2 → 업그레이드 적용됩니다.

[ ] migration-log.md 경로 이동 — 루트에 migration-log.md가 있으면
    docs/harness/migration-log.md 로 이동:
    git mv migration-log.md docs/harness/migration-log.md

이 항목들은 자동으로 채워지지 않습니다. 지금 처리하시겠어요?
[1] 지금 한 항목씩 안내받기 (대화형)
[2] 나중에 직접 처리 (목록만 출력하고 넘어감)
[3] MIGRATIONS.md를 열어서 보기
```

**수동 적용 항목이 없는 경우** (`없음` 명시된 경우):

```
✅ 이번 업그레이드는 수동 액션 없음.
```

선택 1이면 항목별로 사용자와 대화하며 채운다. 검증 명령까지 같이 실행.
선택 2면 docs/WIP/에 `harness--migration_followup.md` 자동 생성·갱신하여
TODO로 추적 (다음 세션 SessionStart에서 노출됨). 이미 있으면 새 버전 섹션을
`## v{X}` 형태로 본문에 누적. 날짜 suffix 금지 (naming.md SSOT).

MIGRATIONS.md를 읽지 못하면 `docs/harness/MIGRATIONS.md` 위치만 안내하고
넘어간다.

### Step 11. upstream 정합성 자동 검증 (FR-002 대응)

Step 5(3-way merge)·Step 6(신규 추가)·Step 7(삭제)·Step 8(settings)이
"처리한 횟수"만 보고하고 **실제 정합성 도달 여부**는 검증하지 않았다.
다운스트림 v0.42.0 측정에서 30+ 파일이 silent 미적용 상태로 통과한
사례(FR-002)가 본 단계의 부재를 증명. 본 단계는 그 갭을 메운다.

```bash
UPSTREAM_REF=$(git rev-parse "$UPSTREAM_REMOTE/main")

# starter 영역 한정. apps/web 등 다운스트림 코드는 검증 대상 아님
DRIFT_FILES=$(git diff --name-only "$UPSTREAM_REF" HEAD -- \
  .claude/skills .claude/scripts .claude/rules .claude/agents \
  .claude/HARNESS.json \
  docs/harness/MIGRATIONS.md)

# Step 6에서 추가된 신규 파일은 untracked 상태일 수 있음 (HEAD 미포함).
# 비교에 포함시켜야 "deleted from HEAD" 오표시 차단 (v0.47.6 — FR-X1 대응).
UNTRACKED_FILES=$(git ls-files --others --exclude-standard -- \
  .claude/skills .claude/scripts .claude/rules .claude/agents \
  .claude/HARNESS.json \
  docs/harness/MIGRATIONS.md)
```

#### 분류 (4 카테고리)

각 drift 파일을 다음 순서로 분류한다:

1. **사용자 전용 (제외)** — 다운스트림이 정당하게 커스터마이징하는 영역.
   변경되어 있어도 정상. **디렉토리 단위로 광범위 인정** (v0.42.2 — FR-006
   대응):
   - `.claude/rules/*.md` — 모든 rules 파일. starter는 기본 패턴만 제공하고
     다운스트림이 자기 도메인·금지 사항·메타데이터 규칙을 자유롭게 확장
   - `.claude/agents/*.md` — 에이전트 정의는 starter 기본을 다운스트림이
     `tools` allowlist·프롬프트·도메인 적합성으로 자체 customize 대상
   - 기타 SEALED_FOLDERS 영역 (Step 3 정의)

   **starter 소유 영역의 다운스트림 전용 파일 — USER_OWNED 재분류** (v0.47.6 —
   FR-X1 대응, false-positive 차단):
   - `.claude/skills/*`·`.claude/scripts/*` 중 **upstream에 한 번도 존재한
     적 없는** 파일은 다운스트림 전용 자산 → USER_OWNED 분류
   - 판정: `git log "$UPSTREAM_REF" -- "$f"` hit 0건이면 다운스트림 전용
   - hit 있으면 (과거 존재 → 현재 부재) "upstream에서 삭제됨" 라벨 + UNAPPLIED
     유지 (다운스트림이 upstream 삭제를 적용 안 한 경우)

   **starter 소유 명백 영역 — USER_OWNED 분류 금지** (false-negative 방어):
   - `.claude/skills/*`·`.claude/scripts/*` 중 upstream에 존재하는 파일은
     starter 소유 → 차이 = 진짜 미적용 (UNAPPLIED 분류)
   - `.claude/HARNESS.json` — starter 메타
2. **starter_skills (제외)** — `.claude/skills/<starter_skill>/` 경로
   (`STARTER_SKILLS` 변수 — Step 6.0 정의 재사용). 다운스트림 미전파 의도
3. **신규 추가 — stage 대기** (v0.47.6 — FR-X1 대응) — Step 6에서 추가된
   untracked 신규 파일. working tree에는 있지만 HEAD에 없어 `git diff
   UPSTREAM HEAD`가 "deleted" 또는 차이로 표시. 실제로는 정합 진행 중 →
   UNAPPLIED 아님
4. **그 외 (미적용 의심)** — 위 셋 어디에도 해당 안 하는 파일. starter가
   소유하고 변경한 영역인데 upstream과 다르다 → 3-way merge가 묻힌 의심

```bash
USER_OWNED_FILES=()
STARTER_SKILL_FILES=()
STAGED_PENDING_FILES=()
UNAPPLIED_FILES=()

# untracked 파일은 별 카테고리 (신규 추가 stage 대기). v0.47.6.
for f in $UNTRACKED_FILES; do
  STAGED_PENDING_FILES+=("$f")
done

# upstream 부재 판정 함수 (v0.47.6 — FR-X1)
is_downstream_only() {
  local path="$1"
  # log hit 0건 == upstream에 한 번도 존재한 적 없음
  [ -z "$(git log "$UPSTREAM_REF" --oneline -- "$path" 2>/dev/null | head -1)" ]
}

for f in $DRIFT_FILES; do
  # untracked로 이미 STAGED_PENDING에 들어갔으면 skip
  case " ${STAGED_PENDING_FILES[*]:-} " in *" $f "*) continue ;; esac

  case "$f" in
    .claude/rules/*.md|.claude/agents/*.md)
      # 다운스트림 정당 커스터마이징 영역 (디렉토리 단위)
      USER_OWNED_FILES+=("$f") ;;
    .claude/skills/*)
      # starter_skills 매칭 우선
      matched=0
      IFS=',' read -ra SKILLS <<< "$STARTER_SKILLS"
      for s in "${SKILLS[@]}"; do
        case "$f" in .claude/skills/${s}/*) matched=1; break ;; esac
      done
      if [ "$matched" -eq 1 ]; then
        STARTER_SKILL_FILES+=("$f")
      elif is_downstream_only "$f"; then
        # upstream 부재 → 다운스트림 전용 스킬 (v0.47.6 — FR-X1)
        USER_OWNED_FILES+=("$f")
      else
        # upstream 존재 → starter 소유 → 진짜 미적용
        UNAPPLIED_FILES+=("$f")
      fi ;;
    .claude/scripts/*)
      if is_downstream_only "$f"; then
        # upstream 부재 → 다운스트림 전용 스크립트 (v0.47.6 — FR-X1)
        USER_OWNED_FILES+=("$f")
      else
        UNAPPLIED_FILES+=("$f")
      fi ;;
    *)
      # .claude/HARNESS*·docs/harness/MIGRATIONS.md 등
      # starter 소유 영역 — 차이는 진짜 미적용
      UNAPPLIED_FILES+=("$f") ;;
  esac
done
```

#### 출력 + 처리

```
═══ upstream 정합성 검증 ═══

사용자 전용 (제외):    N개  (보존 확인 — 변경 정당)
starter_skills (제외): N개  (다운스트림 미전파 의도)
upstream 정합성 미도달: M개  ⚠
```

**미도달 0건이면**: "✅ upstream 정합성 도달" 한 줄 출력 후 Step 12 진행.

**미도달 1건 이상이면**: 파일 목록 표시 + 사용자 후속 액션 선택:

```
⚠ upstream 정합성 미도달 (M개):
  .claude/skills/eval/SKILL.md
  .claude/HARNESS.json
  .claude/rules/memory.md
  ...

이 파일들은 starter 소유 영역인데 upstream과 다릅니다. Step 5 3-way
merge가 묻혔거나 본체 swap 사고일 가능성이 있습니다.

선택:
  [1] 각 파일별 base↔ours sanity check 재실행 (Step 5 본체 swap 검사)
  [2] 무시하고 계속 (silent fail 위험 — migration-log.md에 기록 필수)
  [3] 업그레이드 중단 (이번 변경 롤백)
```

선택 1이면 `UNAPPLIED_FILES` 각각에 대해 Step 5 본체 swap sanity check를
재실행한다 (3택 확인 후 적용). 선택 2이면 `UNAPPLIED_FILES` 목록을 Step
10 보고 + migration-log.md에 그대로 기록. 선택 3이면 `git restore` 권고
후 중단.

`USER_OWNED_FILES`·`STARTER_SKILL_FILES`·`UNAPPLIED_FILES` 카운트는
**Step 13 완료 보고에 그대로 전달**한다.

### Step 12. 수동 액션 완료 확인 (게이트)

Step 13 진행 전, 수동 액션이 모두 처리됐는지 확인한다:

```bash
grep "- \[ \]" docs/harness/MIGRATIONS.md | grep -v '`- \[ \]`'
```

미완료 항목이 있으면:
```
⚠️ MIGRATIONS.md에 미완료 수동 액션이 남아있습니다:
  - [ ] ...
Step 10으로 돌아가 처리하거나, 나중에 처리하려면 docs/WIP/harness--migration_followup.md에 기록합니다.
계속하시겠습니까? [y/n]
```

미완료 상태로 완료 처리하면 다운스트림이 silent fail 상태가 됨. 사용자가 명시적으로 승인한 경우에만 넘어간다.

### Step 13. 완료 처리

1. `HARNESS.json` 갱신:
   - `version` → 새 버전
   - `installed_from_ref` → upstream ref
   - `upgraded_at` → 현재 시각
   - `starter_skills` → upstream 값으로 동기화. 다운스트림 HARNESS.json에 `starter_skills` 키가 없거나 null이면 upstream 값을 그대로 주입. upstream 값도 없으면 폴백: `"harness-init,harness-adopt"`
   - **갱신 후 sanity check** (incident: hn_upstream_anomalies.md F):
     ```bash
     NEW_REF=$(jq -r '.installed_from_ref' .claude/HARNESS.json)
     if ! git cat-file -e "$NEW_REF" 2>/dev/null; then
       echo "❌ installed_from_ref 갱신 직후 ref가 git history에 없음: $NEW_REF"
       echo "   다음 업그레이드에서 ADDED 분류가 부풀려질 위험. 즉시 확인 필요."
       exit 1
     fi
     ```
     실패 시 즉시 사용자에게 보고. 다음 업그레이드 시점까지 묻혀 있으면
     ADDED 60+개로 부풀려져 발견됨.
2. `.claude/.upgrade/` 디렉토리가 있으면 삭제 (구버전 잔여물)
3. **`docs/harness/migration-log.md` 섹션 자동 생성** (append only, 덮어쓰기 금지):
   - 파일이 없으면 생성, 있으면 기존 내용 보존하고 새 섹션 append
   - 헤더만 생성. 내용은 다운스트림이 직접 채움:
   ```markdown
   ## v{CUR_VERSION} → v{SRC_VERSION} ({YYYY-MM-DD})

   ### 충돌·수동 결정
   <!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 등 -->

   ### 이상 소견
   <!-- 예상 밖 동작, 확인 필요 항목 등 -->
   <!-- Step 11 UNAPPLIED_FILES 목록은 본 섹션에 자동 append (1건 이상일 때만) -->

   ### 수동 적용 결과
   <!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
   ```
   - **`docs/harness/migration-log.md`는 upstream이 절대 덮어쓰지 않는다.** 다운스트림 소유.
   - 문제 발생 시 이 파일을 upstream에 전달하면 맥락 파악 가능.
4. **커밋** — `CONFLICT_RESOLVED` 목록 유무로 분기:

   **충돌 해소 파일이 없는 경우** (자동 덮어쓰기·신규 추가만):
   upstream 검증 코드이므로 review 불필요. commit 스킬에 `--no-review`
   전달해 단일 커밋:
   ```bash
   git add .
   /commit --no-review
   ```
   > `--no-review`는 commit 스킬 Stage 결정 우선순위 1번 — review 호출 자체를 skip.

   **충돌 해소 파일이 있는 경우** (`CONFLICT_RESOLVED` 비어있지 않음):
   충돌 해소 결과만 검증이 필요. `--quick`으로 해당 파일만 review:
   ```bash
   git add .
   # commit 스킬 호출 전 충돌 해소 파일 목록을 컨텍스트로 전달
   /commit --quick
   ```
   commit 스킬 호출 시 전제 컨텍스트에 다음을 명시:
   - "하네스 업그레이드 커밋. 충돌 해소 파일: `<CONFLICT_RESOLVED 목록>`"
   - "나머지 파일은 upstream 그대로 — 충돌 해소 파일만 검증 대상"

5. 완료 보고 (FR-003 대응 — "처리한 횟수"가 아닌 **"upstream 정합성 도달 여부"** 보고):
   ```
   ✅ 하네스 업그레이드 완료 (0.9.2 → 1.0.0)

   자동 덮어쓰기:           4개  ✅
   3-way merge:             3개 (충돌 0, 본체 swap 검사 통과)
   본체 swap 복구(Step 5):  N개  ← FR-001 검사로 theirs 강제 교체된 건수 (있으면)
   신규 추가:               2개  ✅
   permissions.allow 동기화: 3개 추가
   hook 동기화:             1개

   ── upstream 정합성 (Step 11) ──
   사용자 전용 (제외):      N개   (보존 확인 — 변경 정당)
   starter_skills (제외):   N개   (다운스트림 미전파 의도)
   upstream 정합성 미도달:  M개   ← 0이면 "✅ 정합성 도달", 1+ 이면 "⚠ 정합성 미도달" 강조 + 파일 목록

   보존됨 (사용자 커스터마이징):
     - CLAUDE.md ## 환경 섹션
     - coding.md 패턴/금지 목록
     - naming.md 도메인/파일명 규칙

   📝 docs/harness/migration-log.md에 이번 업그레이드 섹션을 추가했습니다.
      충돌·이상 소견·수동 적용 결과 + 정합성 미도달 항목을 기록해두세요.
   ```

   **카운트 데이터 흐름**: Step 11에서 채운 `USER_OWNED_FILES`·
   `STARTER_SKILL_FILES`·`UNAPPLIED_FILES` 배열의 length를 그대로 본 보고에
   주입한다. 별도 재계산 금지 — 분류 기준이 분기되면 silent fail 재발.

   **정합성 미도달이 1건 이상이면 강조**:
   ```
   ⚠ upstream 정합성 미도달 — M개 파일이 starter 소유 영역인데 upstream과 다름:
     .claude/skills/eval/SKILL.md
     .claude/HARNESS.json
     ...
   다음 upgrade 전에 Step 11 sanity check 재실행 권장.
   migration-log.md `### 이상 소견` 섹션에 위 목록 자동 append됨.
   ```

   **사용자 전용 제외 목록 표시 정책**: 4개 이하면 전체 표시. 5개 이상이면
   요약 4개 + "... 외 N개 (전체 보기? [Y/n])" 옵션 제공. 사용자가 "이게
   진짜 보존 맞나?" 검토 기회 확보.

6. **이번 업그레이드로 강화된 방어 기전 설명 (지식 내면화 단계)**

   완료 보고 직후, 이번 업그레이드에서 변경된 방어 기전을 1~3줄로 설명한다.
   에이전트가 직접 설명하는 과정에서 "왜 이런 제약이 있는가"가 내면화됨.

   대상: 이번 diff에서 변경된 `.claude/rules/*.md`, `.claude/scripts/bash-guard.sh`,
   `.claude/agents/review.md` 중 **방어 기전** 관련 항목만.
   MIGRATIONS.md 해당 버전 섹션의 변경 내용에서 추출한다.

   형식:
   ```
   🛡 이번 업그레이드 방어 기전 변경:

   1. [규칙/스크립트명]: [무엇이 강화됐는가 — 1줄]
      Why: [왜 필요한가 — 1줄. "우회 시 어떤 문제가 생기는가"]

   2. (없으면 "방어 기전 변경 없음 ✅")
   ```

   **작성 원칙**:
   - What이 아니라 **Why**를 반드시 포함한다. "무엇이 바뀌었다"만으로는 지식 전달 실패.
   - 1항목 2줄 이내. 장문 금지.
   - MIGRATIONS.md에 변경 내용이 없으면 "방어 기전 변경 없음 ✅" 한 줄만.
   - 자동화 불가 — 에이전트가 diff를 보고 직접 판단해 작성.

---

## Fallback: .upgrade/ 스테이징 파일 병합

`harness-upstream` remote가 없어서 `h-setup.sh --upgrade`로 파일 복사 방식을 사용한 경우,
`.claude/.upgrade/`에 스테이징된 파일과 `UPGRADE_REPORT.md`가 존재한다.

이 경우 Step 0에서 remote 대신 `.claude/.upgrade/UPGRADE_REPORT.md` 존재 여부를 확인하고,
스테이징 파일 기반으로 병합한다:

1. UPGRADE_REPORT를 읽어 변경 파일 목록과 hook 누락 정보를 파악한다.
2. 스테이징된 각 파일에 대해 현재 파일과 diff를 보여주고 병합한다.

| 파일 유형 | 병합 전략 |
|----------|----------|
| `.sh` 스크립트 | diff 분석 후 병합 제안. `bash -n`으로 구문 검증. |
| `settings.json` | 새 hook만 추가, 기존 hook 보존. |
| `SKILL.md` | diff 보여주고 교체 승인. |
| `CLAUDE.md` | `## 환경` 섹션 보존. 하네스 공통 섹션만 병합. |
| `rules/*.md` | 사용자가 채운 내용 보존. 새 섹션만 병합. |

3. 완료 후 `.claude/.upgrade/` 삭제, HARNESS.json 갱신.

---

## 주의

- 병합 중 3회 시도해도 검증 실패하면 건너뛰고 수동 병합 요청.
- 이 스킬은 코드를 수정한다. 각 수정마다 사용자 승인을 받는다.
- `--no-verify` 사용 금지.

### Windows 호환성

- **파일 추출은 반드시 `MSYS_NO_PATHCONV=1 git show <ref>:<path>`를 사용한다.** `git archive | tar -x`는 Windows에서 조용히 실패하므로 절대 사용 금지. `MSYS_NO_PATHCONV=1` 없으면 `<ref>:<path>` 인자가 Windows path(`<ref>\main;<path>`)로 자동 변환되어 fatal 에러.
- `mktemp -d`는 Git Bash에서 동작하지만, 경로에 백슬래시가 섞이지 않도록 주의한다.
- 경로 구분자는 항상 `/`(포워드 슬래시)를 사용한다.

## 다른 스킬과의 관계

| 스킬 | 관계 |
|------|------|
| harness-sync | sync = 환경(의존성, 권한), upgrade = 하네스 파일 업데이트. 별개. |
| harness-init | init은 최초 프로젝트 결정. upgrade는 스타터 버전 업. |
| harness-adopt | adopt은 기존 프로젝트에 하네스 이식. upgrade는 이미 설치된 하네스 갱신. |
| commit | 업그레이드 완료 후 커밋은 commit 스킬로. 충돌 해소 없으면 `--no-review` 전달 (review skip). 충돌 있으면 `--quick`. 예: `/commit --no-review` 또는 `/commit --quick`. |
