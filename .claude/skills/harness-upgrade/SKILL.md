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
- **3-way merge 우선**: 가능하면 base + theirs + ours 3-way merge.
- **승인 필수**: 각 파일 병합 전 사용자에게 계획을 보여주고 승인받는다.
- **검증 필수**: 병합 후 구문 오류를 검증한다.

## 흐름

### Step 0. 사전 점검

1. `.claude/HARNESS.json` 존재 확인. 없으면 중단.
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
     (문서 재분류, 프론트매터, INDEX/clusters 생성이 필요합니다)
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

변경된 파일을 분류한다:

| 카테고리 | 대상 | 처리 |
|----------|------|------|
| 자동 덮어쓰기 | `.claude/scripts/*`, `h-setup.sh` | upstream 그대로 적용 |
| 3-way merge | `CLAUDE.md`, `.claude/rules/*`, `.claude/skills/*`, 기타 | 대화형 병합 |
| **사용자 전용 (절대 건드리지 마라)** | `HARNESS.json`, `coding.md`, `naming.md`, **`README.md`**, **`CHANGELOG.md`**, **`.gitignore`**, **`docs/decisions/*`**, **`docs/incidents/*`**, **`docs/WIP/*`**, **`docs/guides/*`** (단 "하네스 파일 범위"의 명시 목록 + `REFERENCED_DOCS` 동적 탐색 결과는 제외) | **무조건 건너뜀.** starter 버전이 다운스트림에 없어도 추가 안 함. diff가 있어도 표시만 하고 병합 시도 X. |
| 신규 | 타겟에 없는 파일 | 추가 제안 (위 사용자 전용 리스트는 제외) |
| 삭제 | upstream에서 제거된 파일 (three-way만) | 삭제 제안 (위 사용자 전용 리스트는 제외) |

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

적용 전 목록을 사용자에게 보여주고 한번에 승인받는다:
```
📦 자동 덮어쓰기 (스크립트/인프라)

  .claude/scripts/session-start.sh
  .claude/scripts/pre-commit-check.sh
  h-setup.sh

적용할까요? [Y/n]
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

# ours: 현재 작업 디렉토리
cp <파일경로> "$TMPDIR/ours"

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

#### 파일별 처리 절차

1. merge 실행 (3-way 또는 2-way)
2. 충돌 없으면 → diff를 사용자에게 보여주고 승인:
   ```
   📄 .claude/rules/docs.md — 충돌 없이 병합됨

   변경 내용:
     + 프론트매터 필수화 규칙 추가 (3줄)
     + 문서 탐색 트리거 섹션 추가 (15줄)

   사용자 커스터마이징 보존:
     도메인 목록, 폴더 판단 기준 (변경 없음)

   적용할까요? [Y/n]
   ```
3. 충돌 있으면 → 충돌 마커를 보여주고 해결:
   ```
   📄 .claude/skills/commit/SKILL.md — 충돌 1개

   <<<<<<< ours
   [사용자 버전]
   =======
   [upstream 버전]
   >>>>>>> theirs

   해결 방법: [ours 유지 / theirs 적용 / 직접 편집]
   ```
4. 승인 후 파일에 적용
5. 검증:
   - `.sh`: `bash -n <파일>`
   - `.json`: JSON 파싱 유효성
   - `.md`: 프론트매터 YAML 파싱

### Step 6. 신규 파일 추가

upstream에만 있는 파일을 처리한다:

```bash
MSYS_NO_PATHCONV=1 git show <upstream_ref>:<파일경로> > <파일경로>
```

파일 목록을 보여주고 한번에 승인:
```
📦 신규 파일 추가

  .claude/agents/doc-finder.md (신규 에이전트)
  .claude/skills/advisor/SKILL.md (신규 스킬)

추가할까요? [Y/n]
```

### Step 7. 삭제된 파일 처리

upstream에서 제거된 파일이 있으면 (three-way 모드만):
```
📦 upstream에서 제거된 파일

  .claude/scripts/old-guard.sh

삭제할까요? [Y/n/건너뛰기]
```

사용자가 건너뛰면 파일을 남긴다 (강제 삭제하지 않음).

### Step 8. settings.json hook 동기화

settings.json은 통째로 교체하지 않는다. **starter 소유 hook만 동기화**
하고 **사용자 커스텀은 건드리지 않는다**.

#### 8.1. 누락 hook 추가 (기존 동작)

1. upstream에 있지만 현재에 없는 matcher를 찾아 승인 후 추가.

#### 8.2. 구 hook 제거 (v0.7.0 신규)

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
**docs-manager 스킬을 호출**하여:
- 프론트매터 검증 (새 필수 필드 추가 등)
- INDEX.md + clusters/ 정합성 확인
- relates-to 경로 유효성 확인

호출 시 전달 규약 (누수 #3 해소):
- `trigger`: "harness-upgrade Step 9 — Step 4·5·6에서 docs/ 파일 변경됨"
- `intent`: `validate` (기본) 또는 `update-index` (Step 5/6에서 신규 파일 이식 시)
- `scope: focused`, `files`: Step 4·5·6에서 변경/신규/이동된 docs 파일 목록
  (각 파일에 action·domain·status 명시)
- `context.prior_steps`: "Step 4 자동 덮어쓰기 N개, Step 5 3-way merge M개,
  Step 6 신규 이식 K개 완료. 본 Step 9는 정합성 검증·INDEX 갱신만"
- 업그레이드가 docs/ 규칙 자체를 바꿔 전수 검증이 필요하다고 판단되면
  `scope: full` + `intent: full-refresh`로 명시 (드문 경우)

문제가 발견되면 사용자에게 보고하고 수정을 제안한다.
문제가 없으면 "docs/ 정합성 확인 완료"로 넘어간다.

### Step 9.5. 마이그레이션 액션 표시

업스트림의 `docs/harness/MIGRATIONS.md`에서 `CUR_VERSION`보다 **새로
적용되는 모든 버전 섹션**의 "수동 액션" 항목을 사용자에게 보여준다.

자동 병합으로 채워지지 않는 사용자 직접 입력 항목 (도메인 등급·경로
매핑·is_starter 같은 silent fail 위험 항목)이 여기에 모인다.

```bash
# upstream의 MIGRATIONS.md를 읽음 (현재 워킹트리는 이미 새 버전이지만
# 명확성 위해 upstream에서 fetch)
MSYS_NO_PATHCONV=1 git show $UPSTREAM_REMOTE/main:docs/harness/MIGRATIONS.md > /tmp/MIGRATIONS.md

# CUR_VERSION 다음 버전부터 SRC_VERSION까지의 섹션 추출
# (## vX.Y.Z 헤더로 분리)
```

표시 형식:
```
═══ 수동 액션 필요 (MIGRATIONS.md) ═══

다음 버전 업그레이드가 적용됩니다: 1.6.2 → 1.7.0

──── v1.7.0 ────
[ ] .claude/rules/naming.md "도메인 등급" 채우기
    이유: 도메인 등급 미분류면 staging S9 무시 → 전부 normal 폴백
    위치: ## 도메인 등급 (review staging) 섹션
    검증: grep -A2 "도메인 등급" .claude/rules/naming.md

[ ] .claude/rules/naming.md "경로 → 도메인 매핑" 채우기
    ...

이 항목들은 자동으로 채워지지 않습니다. 지금 처리하시겠어요?
[1] 지금 한 항목씩 안내받기 (대화형)
[2] 나중에 직접 처리 (목록만 출력하고 넘어감)
[3] MIGRATIONS.md를 열어서 보기
```

선택 1이면 항목별로 사용자와 대화하며 채운다. 검증 명령까지 같이 실행.
선택 2면 docs/WIP/에 `harness--migration_v{X}_{YYMMDD}.md` 자동 생성하여
TODO로 추적 (다음 세션 SessionStart에서 노출됨).

`installed_from_ref`가 없거나 (CUR_VERSION이 unknown) MIGRATIONS.md를
못 읽으면 전체 마이그레이션 가이드 위치만 안내하고 넘어간다.

### Step 10. 완료 처리

1. `HARNESS.json` 갱신:
   - `version` → 새 버전
   - `installed_from_ref` → upstream ref
   - `upgraded_at` → 현재 시각
2. `.claude/.upgrade/` 디렉토리가 있으면 삭제 (구버전 잔여물)
3. 완료 보고:
   ```
   ✅ 하네스 업그레이드 완료 (0.9.2 → 1.0.0)

   자동 덮어쓰기: 4개
   3-way merge:   3개 (충돌 0)
   신규 추가:     2개
   hook 동기화:   1개

   보존됨 (사용자 커스터마이징):
     - CLAUDE.md ## 환경 섹션
     - coding.md 패턴/금지 목록
     - naming.md 도메인/파일명 규칙
   ```

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
| commit | 업그레이드 완료 후 커밋은 commit 스킬로. |
