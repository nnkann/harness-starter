---
name: harness-upgrade
description: 하네스 스타터 업그레이드 후 충돌 파일을 대화형으로 병합. h-setup.sh --upgrade 실행 후 .claude/.upgrade/ 에 스테이징된 파일들을 분석하고 사용자 승인 하에 병합. "harness-upgrade", "하네스 업그레이드", "업그레이드 병합" 요청 시 사용.
---

# harness-upgrade 스킬

`h-setup.sh --upgrade` 실행 후, 스테이징된 변경 파일들을 대화형으로 병합한다.

## 전제

- `h-setup.sh --upgrade`가 이미 실행되어 `.claude/.upgrade/` 디렉토리가 존재해야 한다.
- `.claude/.upgrade/UPGRADE_REPORT.md`에 변경 파일 목록과 diff가 있다.

## 핵심 원칙

- **사용자 커스터마이징 보존**: 사용자가 채운 내용(CLAUDE.md 환경, rules 도메인/패턴 등)은 절대 덮어쓰지 않는다.
- **병합 우선**: 덮어쓰기가 아니라 병합. 새 섹션/훅만 추가.
- **승인 필수**: 각 파일 병합 전 사용자에게 diff와 병합 계획을 보여주고 승인받는다.
- **검증 필수**: 병합 후 구문 오류(bash syntax, JSON validity)를 검증한다.

## 흐름

### Step 0. 사전 점검

- [ ] `.claude/.upgrade/` 디렉토리 존재 확인. 없으면:
  ```
  ❌ .claude/.upgrade/ 디렉토리가 없음.
  먼저 harness-starter에서 `bash h-setup.sh --upgrade <이 프로젝트 경로>`를 실행하세요.
  ```
- [ ] `UPGRADE_REPORT.md` 읽어서 변경 파일 목록 파악.

### Step 1. 파일별 순회 및 병합

스테이징된 각 파일에 대해 아래 순서로 처리:

#### 1-1. 파일 분류

| 파일 유형 | 병합 전략 |
|----------|----------|
| `.sh` 스크립트 | 현재 파일과 새 파일의 diff 분석. 사용자 수정 부분 식별 후 병합 제안. bash -n으로 구문 검증. |
| `settings.json` | JSON 파싱. 새 훅(Stop, Write 등)만 추가, 기존 훅 보존. 사용자 커스텀 훅 보존. jq 또는 수동 병합. |
| `SKILL.md` | 스킬 파일은 사용자 수정 가능성 낮음. diff 보여주고 교체 승인. |
| `CLAUDE.md` | `## 환경` 섹션 보존. `## 절대 규칙` 등 하네스 공통 섹션은 새 내용으로 병합. |
| `rules/*.md` | 사용자가 채운 내용(도메인, 패턴, 금지 목록 등) 보존. 하네스가 추가한 새 섹션만 병합. |

#### 1-2. 각 파일 처리 절차

1. 현재 파일과 새 파일의 diff를 분석한다.
2. 변경 내용을 분류한다:
   - **하네스 추가분**: 스타터에서 새로 추가된 내용 (새 훅, 새 규칙, 새 기능)
   - **사용자 커스터마이징**: 사용자가 프로젝트에 맞게 수정한 내용
3. 병합 계획을 사용자에게 보여준다:
   ```
   📄 .claude/scripts/session-start.sh
   
   하네스 추가분:
     + git log --oneline -3 출력
     + 마지막 커밋 경과 시간 표시
   
   사용자 커스터마이징 (보존):
     (없음 / 있으면 구체적 내용)
   
   병합 결과 미리보기:
     [병합된 코드 표시]
   
   적용할까요? [Y/n]
   ```
4. 사용자가 승인하면 병합 적용.
5. 병합 후 검증:
   - `.sh` 파일: `bash -n <파일>` 로 구문 검증
   - `.json` 파일: `jq . <파일>` 또는 JSON 파싱으로 유효성 검증
   - 검증 실패 시 롤백하고 사용자에게 보고

### Step 2. settings.json — hook 추가 (덮어쓰기 아님)

settings.json에는 프로젝트 고유의 permissions와 커스텀 hook이 있다.
**통째로 교체하지 않는다. 누락된 hook만 추가한다.**

#### 2-1. UPGRADE_REPORT 확인

`UPGRADE_REPORT.md`에 "누락된 hook" 섹션이 있는지 확인한다.
없으면 settings.json은 건너뛴다.

#### 2-2. 추가 절차

1. 타겟 `.claude/settings.json`을 읽는다 (현재 프로젝트의 설정).
2. 스테이징된 `.claude/.upgrade/.claude/settings.json`을 읽는다 (스타터 최신).
3. **보존 대상** (절대 건드리지 않음):
   - `permissions` 객체 전체
   - 타겟에만 있는 hook (사용자가 직접 추가한 것)
   - 타겟에 이미 있는 matcher의 hooks 내용
4. **추가 대상** (없으면 추가):
   - 스타터에 있지만 타겟에 없는 hook 카테고리 (예: `PostCompact` 전체)
   - 스타터에 있지만 타겟에 없는 matcher (예: `PreToolUse`의 `Bash(git commit*)`)
5. **식별 기준**:
   - hook 카테고리: `SessionStart`, `Stop`, `PostCompact`, `PostToolUse`, `PreToolUse`
   - 개별 hook: `(카테고리, matcher)` 조합으로 식별
   - 하네스 관리 hook 판별: command가 `bash .claude/scripts/`로 시작하는 것
6. 추가할 hook 목록을 사용자에게 보여주고 승인받는다:
   ```
   📄 settings.json — hook 추가

   추가할 hook:
     + [PreToolUse] "Bash(git commit*)" → pre-commit-check.sh + 테스트 커버리지 에이전트
     + [PostCompact] "" → post-compact-guard.sh

   기존 설정 보존:
     - permissions (변경 없음)
     - [PreToolUse] "Write" (사용자 커스텀, 보존)

   적용할까요? [Y/n]
   ```
7. 승인 후 settings.json에 hook을 추가하고 JSON 유효성을 검증한다.

#### 2-3. 기존 hook의 내용이 변경된 경우

같은 matcher가 양쪽에 있지만 command/prompt가 다른 경우:
- 양쪽 버전을 보여주고 사용자가 선택한다.
- 강제 교체하지 않는다.

### Step 3. harness.json 업데이트

모든 병합 완료 후:
1. `harness.json`의 version을 새 버전으로 업데이트
2. `upgraded_at` 필드에 현재 시각 기록
3. 새로 추가된 스킬이 있으면 skills 목록 업데이트

### Step 4. 정리 및 보고

1. `.claude/.upgrade/` 디렉토리 삭제
2. 완료 보고:
   ```
   ✅ 하네스 업그레이드 완료 (0.5.0 → 0.6.0)
   
   병합됨:
     - session-start.sh (git 상태 출력 개선)
     - settings.json (Stop 훅, Write 훅 추가)
     - eval/SKILL.md (--quick, --deep 모드 추가)
   
   새로 추가됨:
     - memory.md
     - stop-guard.sh
     - advisor/SKILL.md
   
   보존됨 (사용자 커스터마이징):
     - CLAUDE.md ## 환경 섹션
     - coding.md 패턴/금지 목록
   ```

## 주의

- 병합 중 3회 시도해도 검증 실패하는 파일은 건너뛰고 사용자에게 수동 병합 요청.
- `.upgrade/` 디렉토리의 파일은 "참조용 최신 버전"이지, 직접 사용하는 파일이 아님.
- 이 스킬은 코드를 수정하는 스킬이다. 각 수정마다 사용자 승인을 받는다.

## 다른 스킬과의 관계

| 스킬 | 관계 |
|------|------|
| harness-sync | sync = 환경(의존성, 권한), upgrade = 하네스 파일 업데이트. 완전 별개. |
| harness-init | init은 최초 프로젝트 결정. upgrade는 스타터 버전 업. |
| commit | 업그레이드 완료 후 커밋은 commit 스킬로. |
