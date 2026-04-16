---
name: harness-upgrade
description: 하네스 업그레이드 병합. remote(harness-upstream) 방식은 git merge-file로 3-way merge, fallback은 .upgrade/ 스테이징 파일 비교. "harness-upgrade", "하네스 업그레이드" 요청 시 사용.
---

# harness-upgrade 스킬

`h-setup.sh --upgrade` 실행 후, 변경 파일들을 대화형으로 병합한다.
두 가지 방식을 지원한다:

| 방식 | 조건 | 병합 도구 |
|------|------|----------|
| **remote** | `harness-upstream` remote 존재 + UPGRADE_REPORT에 "방식: remote" | `git show` + `git merge-file` |
| **fallback** | remote 없음, `.claude/.upgrade/`에 파일이 스테이징됨 | 파일 diff + 수동 병합 |

## 전제

- `h-setup.sh --upgrade`가 이미 실행되어 `.claude/.upgrade/UPGRADE_REPORT.md`가 존재해야 한다.
- UPGRADE_REPORT를 읽어 방식(remote/fallback)과 변경 파일 목록을 파악한다.

## 핵심 원칙

- **사용자 커스터마이징 보존**: 사용자가 채운 내용은 절대 덮어쓰지 않는다.
- **3-way merge 우선**: 가능하면 base + theirs + ours 3-way merge.
- **승인 필수**: 각 파일 병합 전 사용자에게 계획을 보여주고 승인받는다.
- **검증 필수**: 병합 후 구문 오류를 검증한다.

## 흐름

### Step 0. 사전 점검

1. `.claude/.upgrade/UPGRADE_REPORT.md` 존재 확인. 없으면:
   ```
   ❌ UPGRADE_REPORT.md가 없음.
   먼저 `bash h-setup.sh --upgrade <프로젝트 경로>`를 실행하세요.
   ```
2. UPGRADE_REPORT를 읽어 방식, 버전, 파일 목록을 파악한다.
3. 방식에 따라 Step 1R(remote) 또는 Step 1F(fallback)로 분기한다.

---

## Remote 방식 (Step 1R ~ 5R)

UPGRADE_REPORT에 `방식: remote`가 기록되어 있을 때.

### Step 1R. 정보 추출

UPGRADE_REPORT에서 다음을 읽는다:
- `base ref`: 설치 시점 커밋 (3-way merge의 base)
- `upstream ref`: 업스트림 최신 커밋
- `diff 모드`: three-way 또는 two-way
- 파일 분류: 자동 덮어쓰기 / 3-way merge / 신규 / 삭제

### Step 2R. 자동 덮어쓰기 실행

UPGRADE_REPORT의 "자동 덮어쓰기 대상" 파일을 처리한다.
스크립트/인프라 파일은 사용자 수정 없이 upstream 그대로 적용:

```bash
git show <upstream_ref>:<파일경로> > <파일경로>
```

적용 전 목록을 사용자에게 보여주고 한번에 승인받는다:
```
📦 자동 덮어쓰기 (스크립트/인프라)

  .claude/scripts/session-start.sh
  .claude/scripts/pre-commit-check.sh
  .claude/HARNESS.json
  h-setup.sh

적용할까요? [Y/n]
```

### Step 3R. 3-way merge 실행

UPGRADE_REPORT의 "3-way merge 대상" 파일을 하나씩 처리한다.

#### 3-way merge 절차 (diff 모드 = three-way)

각 파일에 대해:

```bash
# 임시 디렉토리 준비
TMPDIR=$(mktemp -d)

# base: 설치 시점의 파일 (사용자도 upstream도 수정하기 전)
git show <base_ref>:<파일경로> > "$TMPDIR/base"

# theirs: upstream 최신 (하네스 측 변경)
git show <upstream_ref>:<파일경로> > "$TMPDIR/theirs"

# ours: 현재 작업 디렉토리 (사용자 측 변경)
cp <파일경로> "$TMPDIR/ours"

# 3-way merge
git merge-file "$TMPDIR/ours" "$TMPDIR/base" "$TMPDIR/theirs"
MERGE_RESULT=$?

# 정리
rm -rf "$TMPDIR"
```

- `MERGE_RESULT = 0`: 충돌 없이 병합 성공
- `MERGE_RESULT > 0`: 충돌 존재 (마커 포함)
- `MERGE_RESULT < 0`: 에러

#### 2-way diff 절차 (diff 모드 = two-way, base 없음)

base가 없으면 3-way merge 불가. 사용자에게 양쪽 버전을 보여주고 선택:

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

### Step 4R. 신규 파일 추가

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

### Step 4R-2. 삭제된 파일 처리

upstream에서 제거된 파일이 있으면:
```
📦 upstream에서 제거된 파일

  .claude/scripts/old-guard.sh

삭제할까요? [Y/n/건너뛰기]
```

사용자가 건너뛰면 파일을 남긴다 (강제 삭제하지 않음).

### Step 5R. 완료 처리

1. `HARNESS.json` 갱신:
   - `version` → 새 버전
   - `installed_from_ref` → upstream ref
   - `upgraded_at` → 현재 시각
   ```bash
   # jq가 있으면
   jq --arg v "$NEW_VERSION" --arg r "$UPSTREAM_REF" --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '.version = $v | .installed_from_ref = $r | .upgraded_at = $t' \
     .claude/HARNESS.json > .claude/HARNESS.json.tmp && mv .claude/HARNESS.json.tmp .claude/HARNESS.json
   ```
2. `.claude/.upgrade/` 디렉토리 삭제
3. 완료 보고:
   ```
   ✅ 하네스 업그레이드 완료 (0.8.0 → 0.9.0)

   자동 덮어쓰기: 4개
   3-way merge:   3개 (충돌 0)
   신규 추가:     2개

   보존됨 (사용자 커스터마이징):
     - CLAUDE.md ## 환경 섹션
     - coding.md 패턴/금지 목록
     - naming.md 도메인/파일명 규칙
   ```

---

## Fallback 방식 (Step 1F ~ 5F)

remote가 없고, `.claude/.upgrade/`에 스테이징된 파일이 있을 때.
기존 파일 복사 방식과 동일.

### Step 1F. 파일별 순회 및 병합

스테이징된 각 파일에 대해:

#### 파일 분류

| 파일 유형 | 병합 전략 |
|----------|----------|
| `.sh` 스크립트 | diff 분석 후 병합 제안. `bash -n`으로 구문 검증. |
| `settings.json` | 새 훅만 추가, 기존 훅 보존. |
| `SKILL.md` | diff 보여주고 교체 승인. |
| `CLAUDE.md` | `## 환경` 섹션 보존. 하네스 공통 섹션만 병합. |
| `rules/*.md` | 사용자가 채운 내용 보존. 새 섹션만 병합. |

#### 각 파일 처리 절차

1. 현재 파일과 새 파일의 diff를 분석한다.
2. 변경 내용을 분류한다:
   - **하네스 추가분**: 새로 추가된 내용
   - **사용자 커스터마이징**: 사용자가 수정한 내용
3. 병합 계획을 보여주고 승인받는다.
4. 승인 후 적용.
5. 검증: `.sh` → `bash -n`, `.json` → JSON 파싱

### Step 2F. settings.json hook 추가

**통째로 교체하지 않는다. 누락된 hook만 추가한다.**

1. UPGRADE_REPORT에서 누락된 hook 목록 확인.
2. 추가할 hook을 보여주고 승인.
3. 기존 permissions와 사용자 커스텀 hook 보존.

### Step 3F. docs/ 폴더 마이그레이션

업그레이드 시 docs/ 구조가 최신 규칙과 다를 수 있다.

#### 이전 폴더 감지

| 이전 폴더 | 매핑 대상 |
|-----------|----------|
| `plans/`, `planning/` | `decisions/` |
| `development/` | `decisions/` 또는 `guides/` |
| `setup/` | `guides/` |
| `history/` | 문서별 분배 |
| `bugs/`, `issues/`, `postmortem/` | `incidents/` |
| `archive/` | `archived/` |

감지된 이전 폴더가 없으면 건너뛴다.

#### 마이그레이션 절차

1. 문서별 분류 초안 생성 → 사용자 검수.
2. `git mv`로 이동 (히스토리 보존).
3. 프론트매터 없는 문서에 프론트매터 추가.
4. INDEX.md + clusters/ 갱신.

### Step 4F. HARNESS.json 업데이트

1. `version` 갱신
2. `upgraded_at` 기록
3. 새 스킬이 있으면 skills 목록 업데이트

### Step 5F. 정리 및 보고

1. `.claude/.upgrade/` 삭제
2. 완료 보고 출력

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
