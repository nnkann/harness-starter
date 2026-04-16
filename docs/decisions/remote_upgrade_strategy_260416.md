---
title: Remote 기반 하네스 업그레이드 전략
domain: harness
tags: [upgrade, git-remote, merge]
relates-to:
  - path: harness/promotion-log.md
    rel: references
status: completed
created: 2026-04-16
updated: 2026-04-16
---

# Remote 기반 하네스 업그레이드 전략

## 목표
- h-setup.sh --upgrade를 파일 복사 방식에서 git remote 방식으로 전환
- 3-way merge로 사용자 커스터마이징을 보존하면서 업스트림 변경을 적용
- harness-upgrade 스킬을 remote 기반으로 재설계

## 배경

### 현재 문제
- h-setup.sh --upgrade는 `.claude/.upgrade/`에 파일을 복사 후 diff 기반 비교
- 파일 복사 방식은 git 히스토리 활용 불가, 3-way merge 불가
- 사용자가 커스터마이징한 파일을 덮어쓸 위험

### 기존 인프라
h-setup.sh가 이미 설정하는 것:
- `origin` → `harness-upstream`으로 rename (push DISABLED)
- 사용자가 자신의 origin을 별도로 설정
- 하지만 --upgrade 모드에서 이 remote를 **활용하지 않고** 있음

### 해결 방향
`git fetch harness-upstream` + `git merge-file` (3-way merge)로 전환.
`harness.json`에 `installed_from_ref`를 추가해 base commit 추적.

---

## 설계

### 1. harness.json 스키마 변경

```json
{
  "is_starter": false,
  "installed_from": "harness-starter",
  "installed_from_ref": "abc1234",
  "version": "0.8.0"
}
```

- `installed_from_ref`: 설치 시점의 harness-upstream 커밋 해시
- h-setup.sh가 clone 시 `git rev-parse HEAD`로 기록
- 3-way merge의 base revision으로 사용

### 2. h-setup.sh --upgrade 재설계

```
현재 흐름 (파일 복사):
  clone → .upgrade/에 복사 → diff → 수동 비교

새 흐름 (remote):
  1. harness-upstream remote 확인 (없으면 fallback)
  2. git fetch harness-upstream
  3. 버전 비교 (현재 vs upstream)
  4. UPGRADE_REPORT 생성 (변경된 파일 목록 + diff)
  5. harness-upgrade 스킬에 위임 (파일 복사 없음)
```

#### 2-1. Remote 확인
```bash
if git remote get-url harness-upstream &>/dev/null; then
    # remote 방식
    git fetch harness-upstream
else
    # fallback: 파일 복사 방식 (레거시 호환)
    # remote가 없는 프로젝트를 위해 유지
fi
```

#### 2-2. 변경 파일 감지
```bash
BASE_REF=$(jq -r '.installed_from_ref' .claude/harness.json)
UPSTREAM_REF="harness-upstream/main"

# 변경된 하네스 파일 목록
git diff --name-only "$BASE_REF" "$UPSTREAM_REF" -- \
    .claude/ CLAUDE.md docs/harness/ docs/guides/project_kickoff_sample.md
```

#### 2-3. UPGRADE_REPORT 생성
`.claude/.upgrade/UPGRADE_REPORT.md`에 기록:
- 현재 버전 → 업스트림 버전
- 변경된 파일 목록 (카테고리별)
- 각 파일의 변경 요약 (추가/수정/삭제)
- 파일 자체는 복사하지 않음 (git show로 접근)

### 3. harness-upgrade 스킬 재설계

현재 스킬은 `.claude/.upgrade/` 디렉토리의 복사된 파일을 비교.
새 스킬은 git 명령어로 직접 비교 + merge.

#### 3-1. 파일 분류

| 카테고리 | 파일 | 전략 |
|----------|------|------|
| 자동 덮어쓰기 | scripts/*, h-setup.sh | upstream 그대로 적용 |
| 3-way merge | CLAUDE.md, rules/*.md, skills/*/SKILL.md | merge-file 사용 |
| 사용자 전용 | harness.json, naming.md (일부) | 건드리지 않음 |
| 신규 파일 | upstream에만 있는 파일 | 추가 (사용자 확인) |
| 삭제된 파일 | upstream에서 제거된 파일 | 사용자에게 알림 |

#### 3-2. 3-way merge 절차

```bash
# base: 설치 시점의 파일
git show $BASE_REF:.claude/rules/docs.md > /tmp/base.md

# theirs: upstream 최신
git show $UPSTREAM_REF:.claude/rules/docs.md > /tmp/theirs.md

# ours: 현재 작업 디렉토리
cp .claude/rules/docs.md /tmp/ours.md

# 3-way merge
git merge-file /tmp/ours.md /tmp/base.md /tmp/theirs.md

# 충돌 없으면 적용
cp /tmp/ours.md .claude/rules/docs.md
```

#### 3-3. 충돌 처리

- `git merge-file` 반환값 > 0 → 충돌 존재
- 충돌 마커(`<<<<<<<`, `=======`, `>>>>>>>`)가 포함된 파일을 사용자에게 표시
- 사용자가 수동으로 해결하거나, Claude가 제안

#### 3-4. 완료 후

```bash
# harness.json의 installed_from_ref 갱신
jq '.installed_from_ref = "NEW_REF"' .claude/harness.json > tmp && mv tmp .claude/harness.json

# HARNESS_VERSION 갱신 (있으면)
# UPGRADE_REPORT 정리
```

### 4. harness-adopt에서 remote 설정

adopt 스킬이 기존 프로젝트에 하네스를 이식할 때:

```bash
# 하네스 소스 URL을 사용자에게 질문
git remote add harness-upstream <URL>
git remote set-url --push harness-upstream DISABLED

# 현재 upstream HEAD를 installed_from_ref로 기록
git fetch harness-upstream
REF=$(git rev-parse harness-upstream/main)
# harness.json에 기록
```

### 5. Edge Cases

| 상황 | 처리 |
|------|------|
| harness-upstream remote 없음 | 파일 복사 fallback (레거시 호환) |
| installed_from_ref 없음 | 태그/버전으로 base 추정, 불가하면 2-way diff |
| 네트워크 없음 | fetch 실패 시 오프라인 안내 |
| 사용자가 .claude/ 파일을 대량 수정 | merge 충돌 많음 → 파일별 순차 처리 |
| upstream에 breaking change | UPGRADE_REPORT에 경고 표시 + 수동 검토 권고 |

---

## 변경 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `h-setup.sh` | --upgrade 모드를 remote 기반으로 전환, 초기 설치 시 installed_from_ref 기록 |
| `.claude/skills/harness-upgrade/SKILL.md` | 전체 재설계: git show + merge-file 기반 |
| `.claude/skills/harness-adopt/SKILL.md` | remote 설정 단계 추가 |
| `harness.json` (템플릿) | installed_from_ref 필드 추가 |

## 구현 순서

1. **h-setup.sh 수정**: 초기 설치 시 `installed_from_ref` 기록 로직 추가
2. **h-setup.sh --upgrade**: remote 기반으로 전환 (fallback 유지)
3. **harness-upgrade SKILL.md**: 3-way merge 기반으로 재설계
4. **harness-adopt SKILL.md**: remote 설정 단계 추가
5. **테스트**: 실제 프로젝트에서 upgrade 시나리오 검증

## 결정 사항

- git remote 방식 채택 (subtree/submodule 불가 — 사용자 git 히스토리 오염)
- 3-way merge의 base는 `installed_from_ref`로 추적
- 파일 복사 방식은 fallback으로 유지 (remote가 없는 레거시 프로젝트)
- 자동 덮어쓰기 vs 3-way merge vs 사용자 전용 3단계 분류

## 메모

- h-setup.sh 라인 556-575에 이미 `origin → harness-upstream` rename + push DISABLED 로직 존재
- h-setup.sh 라인 91-403의 --upgrade 모드가 주요 수정 대상
- h-setup.sh 라인 506-520의 harness.json 생성 로직에 installed_from_ref 추가 필요
- `git merge-file`은 Git 기본 내장 명령어, 별도 설치 불필요
