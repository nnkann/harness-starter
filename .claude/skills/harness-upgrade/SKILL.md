---
name: harness-upgrade
description: 하네스 업그레이드. harness-upstream remote에서 fetch → 변경 분석 → 3-way merge 대화형 병합. 구 파일 자동 마이그레이션 포함. "harness-upgrade", "하네스 업그레이드", "하네스 업데이트" 요청 시 사용.
---

# harness-upgrade 스킬

`harness-upstream` remote에서 최신 하네스를 가져와 대화형으로 병합한다.
**한 명령으로 완료** — 별도 스크립트 실행 불필요.

## 전제

- `harness-upstream` remote가 프로젝트에 설정되어 있어야 한다.
  - `h-setup.sh`로 설치했으면 자동 설정됨.
  - `/harness-adopt`로 이식했으면 Step 6에서 설정됨.
  - 없으면 안내 후 중단.
- `.claude/HARNESS.json`이 존재해야 한다.

## 핵심 원칙

- **사용자 커스터마이징 보존**: 사용자가 채운 내용은 절대 덮어쓰지 않는다.
- **3-way merge 우선**: 가능하면 base + theirs + ours 3-way merge.
- **승인 필수**: 각 파일 병합 전 사용자에게 계획을 보여주고 승인받는다.
- **검증 필수**: 병합 후 구문 오류를 검증한다.

## 흐름

### Step 0. 사전 점검

1. `harness-upstream` remote 존재 확인:
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
2. `.claude/HARNESS.json` 존재 확인. 없으면 중단.
3. `HARNESS.json`에 `adopted_at` 필드 확인:
   - **있으면** → 정상. Step 1로 진행.
   - **없고 `is_starter: true`** → 스타터 자체이므로 adopt 불필요. Step 1로 진행.
   - **없고 `is_starter`가 false/없음** → adopt 미완료 프로젝트.
     ```
     ⚠️ adopt가 완료되지 않은 프로젝트입니다.
     upgrade 전에 harness-adopt를 먼저 실행합니다.
     (문서 재분류, 프론트매터, INDEX/clusters 생성이 필요합니다)
     ```
     harness-adopt 스킬을 실행한다. adopt 완료 후 upgrade를 이어서 진행.

### Step 1. Fetch + 버전 비교

```bash
git fetch harness-upstream
```

fetch 실패 시 네트워크 문제로 보고하고 중단.

버전 비교:
```bash
# 현재 버전
CUR_VERSION=$(현재 HARNESS.json의 version 필드)

# 업스트림 버전
SRC_VERSION=$(git show harness-upstream/main:.claude/HARNESS.json에서 version 필드)
```

- 이미 최신이면: `✅ 이미 최신 버전 (X.Y.Z). 업그레이드 불필요.` → 종료.
- 업스트림 버전을 읽을 수 없으면 에러 보고 후 중단.

버전과 방식을 사용자에게 표시:
```
═══ 하네스 업그레이드 ═══
현재:    0.9.2
최신:    1.0.0
방식:    remote (harness-upstream)
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
CLAUDE.md h-setup.sh docs/harness docs/guides/project_kickoff_sample.md
```

변경된 파일을 분류한다:

| 카테고리 | 대상 | 처리 |
|----------|------|------|
| 자동 덮어쓰기 | `.claude/scripts/*`, `h-setup.sh` | upstream 그대로 적용 |
| 3-way merge | `CLAUDE.md`, `.claude/rules/*`, `.claude/skills/*`, 기타 | 대화형 병합 |
| 사용자 전용 | `HARNESS.json`, `coding.md`, `naming.md` | 건너뜀 |
| 신규 | 타겟에 없는 파일 | 추가 제안 |
| 삭제 | upstream에서 제거된 파일 (three-way만) | 삭제 제안 |

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
git show <upstream_ref>:<파일경로> > <파일경로>
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
git show <base_ref>:<파일경로> > "$TMPDIR/base"

# theirs: upstream 최신
git show <upstream_ref>:<파일경로> > "$TMPDIR/theirs"

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
git show <upstream_ref>:<파일경로> > <파일경로>
```

파일 목록을 보여주고 한번에 승인:
```
📦 신규 파일 추가

  .claude/agents/docs-lookup.md (신규 에이전트)
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

settings.json은 통째로 교체하지 않는다. **누락된 hook만 추가한다.**

1. upstream의 settings.json과 현재 settings.json을 비교한다.
2. upstream에 있지만 현재에 없는 matcher를 찾는다.
3. 누락된 hook을 보여주고 승인:
   ```
   📦 누락된 hook 2개 감지

     [PreToolUse] matcher: "Bash(git commit*[skip-review]*)"
     [SessionStart] 카테고리 전체 누락

   추가할까요? [Y/n]
   ```
4. 기존 permissions와 사용자 커스텀 hook 보존.

### Step 9. 완료 처리

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

## 다른 스킬과의 관계

| 스킬 | 관계 |
|------|------|
| harness-sync | sync = 환경(의존성, 권한), upgrade = 하네스 파일 업데이트. 별개. |
| harness-init | init은 최초 프로젝트 결정. upgrade는 스타터 버전 업. |
| harness-adopt | adopt은 기존 프로젝트에 하네스 이식. upgrade는 이미 설치된 하네스 갱신. |
| commit | 업그레이드 완료 후 커밋은 commit 스킬로. |
