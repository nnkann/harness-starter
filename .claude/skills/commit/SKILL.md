---
name: commit
description: 작업 잔여물 정리, 계획 문서 완료 처리, 변경 사항 분석 후 커밋+푸시. 모드는 CLAUDE.md의 하네스 강도에 따라 결정. 명시적으로 `--light` / `--strict`로 오버라이드 가능. `/commit` 또는 "커밋해줘" 요청 시 사용.
---

# /commit 스킬

커밋 과정에서 작업 잔여물을 정리하고, 계획 문서를 완료 처리하며,
작업 중 얻은 컨텍스트를 Git 히스토리에 보존한다.

| 사용법 | 설명 |
|--------|------|
| `/commit` | CLAUDE.md `## 환경`의 `하네스 강도`에 따라 자동 선택. |
| `/commit --light` | light 모드 강제. |
| `/commit --strict` | strict 모드 강제. |
| `/commit --no-review` | 리뷰 에이전트 스킵 (커밋 메시지에 `[skip-review]` 태그 포함). |

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

아래 중 하나라도 해당하면 review 호출:
- 변경 파일 5개 이상
- 삭제 50줄 이상
- 핵심 설정 변경 (`CLAUDE.md`, `.claude/settings.json`, `.claude/rules/*`, `.claude/scripts/*`)
- 보안 패턴 (auth/token/secret/key/credential/password 관련 파일명 또는 +라인)
- 인프라 파일 (Dockerfile, docker-compose, `.github/workflows/`)

### 호출 방법

스테이징 + Step 5 pre-check 통과 후 `git commit` 직전에 호출한다.

**핵심 원칙: prompt에 `git diff --cached` 결과 텍스트를 직접 박는다.**
review 에이전트가 스스로 git 명령을 실행해서 diff를 가져오게 두면 잘못된
커밋(HEAD, HEAD~1 등)을 보고 엉뚱한 분석을 할 수 있다 (실측 사례:
v1.4.1 커밋에서 review가 직전 커밋 diff를 잘못 분석).

스킬이 Bash로 직접 실행해서 결과를 prompt에 삽입한다:

```bash
# 1. diff 캡처 (스킬이 직접 실행)
DIFF=$(git diff --cached)

# 2. 크기 가드: 너무 크면 stat + head로 축약
DIFF_SIZE=$(echo "$DIFF" | wc -l)
if [ "$DIFF_SIZE" -gt 2000 ]; then
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
  prompt: 아래 블록 5개를 그대로 포함
    1. ## 이번 커밋의 목적 (1~2줄)
    2. ## 연관 WIP 문서 (경로 또는 "없음")
    3. ## pre-check 결과 (Step 5에서 캡처한 stdout 4줄)
    4. ## staged diff (git diff --cached 결과 텍스트 — 위 DIFF_BLOCK 그대로)
    5. ## 지시
```

prompt 예시:
```
## 이번 커밋의 목적
<1~2줄>

## 연관 WIP 문서
<경로 또는 "없음">

## pre-check 결과
pre_check_passed: true
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: 핵심 설정 파일 변경;연속 수정: SKILL.md (3회)
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
JSON 반환: {"ok": bool, "block": bool, "warnings": []}
```

review 에이전트는 prompt 안의 diff를 진실로 삼고, Read/Glob/Grep으로 파일
본문 맥락만 확인한 뒤 JSON으로 응답한다. **`git diff`/`git log`/`git show`
같은 staged-diff 우회 명령은 실행하지 않는다.**

### 응답 처리

- `block: true` → 커밋 차단. 사용자에게 사유 전달, 수정 후 재시도.
- `block: false, warnings: [...]` → 경고 표시 후 진행. 커밋 메시지 본문에 경고 요약 포함 권장.
- `ok: true, warnings 없음` → 그대로 진행.

### 투명성

- 스킬 메시지로 "🔍 review 에이전트 호출 중..." 한 줄 선행 알림
- 응답 수신 후 "✅ 리뷰 통과" 또는 "⚠️ 리뷰 경고: ..." 또는 "🚫 리뷰 차단: ..." 요약

---

## 공통 단계 (light + strict)

### 1. 작업 잔여물 정리

커밋 전 임시 파일이 포함되지 않도록 정리한다.

- 현재 컨텍스트에서 알 수 있는 임시 파일을 찾아 확인한다.
  (예: 루트의 test-*.mjs, debug/ 내 일회성 스크립트 등)
- 용도가 끝난 파일은 삭제한다.
- 테스트/디버그 스크립트로 인한 좀비 프로세스가 남아있는지 확인한다.
- 사용자가 남겨두길 명시한 파일은 제외한다.

### 2. 계획 문서 완료 처리

docs/WIP/에서 이번 작업과 연결된 문서를 처리한다.

- git diff로 이번 세션의 작업 범위를 파악한다.
- 완료된 작업과 연결된 계획 문서를 찾는다.

| 문서 상태 | 처리 |
|----------|------|
| pending / in-progress | docs/WIP/에 유지 |
| completed | 파일명 접두사로 이동 대상 결정 |
| abandoned | docs/archived/로 이동 |

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

- 계획 문서가 없는 작업이면 넘어간다.
- 이동 대상은 docs/ 규칙에 정의된 폴더만 허용한다 (decisions, guides, incidents, harness, archived). 새 폴더를 만들지 않는다.
- 이동 처리는 docs-manager 에이전트에 위임할 수 있다.

**문서 이동 시 추가 작업:**
- 프론트매터의 `status` → completed (또는 abandoned)으로 갱신
- 프론트매터의 `updated` → 오늘 날짜로 갱신
- `docs/INDEX.md`에 이동된 문서 항목 추가 (해당 domain 섹션 하위에 배치, 관계 맵에 relates-to 반영)

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
2. `docs/harness/promotion-log.md`에 이력 추가 (날짜, 변경 내용, 이전→이후 버전)

**판단이 애매하면** 사용자에게 묻는다. 자의적으로 올리지 않는다.

### 4. 스테이징

`git status`로 변경 파일 확인 후, 특별한 제외 요청 없으면 `git add .`

### 5. pre-check (정적 검사, 빠름)

**목적**: 비싼 LLM 리뷰 전에 값싼 정적 검사를 먼저 돌려 실패 시 조기 차단.
린터 에러·TODO/FIXME·WIP 잔여물·`--no-verify` 같은 명백한 문제는 Agent 호출
없이 걸러낸다.

**stdout 캡처 필수**: pre-check은 stderr에 사용자용 메시지를, **stdout에
review 전달용 요약 4줄**을 출력한다. Bash tool로 실행 시 stdout을 스킬
컨텍스트에 보관해 Step 7 review prompt에 그대로 주입한다.

```bash
bash .claude/scripts/pre-commit-check.sh
```

stdout 출력 형식 (key: value):
```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: <세미콜론 구분 위험 요인 목록 또는 빈 값>
diff_stats: files=N,+A,-D
```

- **exit 2 (차단)**: stderr 메시지를 사용자에게 전달. 문제 수정 후
  스테이징(Step 4)부터 재시도. 리뷰 단계로 진행하지 마라.
- **exit 0 (통과)**: stdout 4줄을 보관하고 6단계로 진행.

> 이 검사는 7단계 `git commit` 시에도 PreToolUse hook으로 자동 재실행된다
> (최후 안전망). 5단계에서 미리 수동 실행하는 이유는 **리뷰 Agent 호출 비용을
> 아끼기 위함**이다 — pre-check이 fail할 diff를 LLM에 넘기는 건 낭비.

### 6. 변경 내역 분석

`git diff --cached`로 스테이징된 변경 내역을 읽고,
어떤 파일에서 어떤 로직이 어떻게 수정되었는지 파악한다.

### 7. 리뷰 (strict 또는 light 위험도 hit 시)

위 "리뷰는 스킬이 Agent tool로 직접 호출한다" 섹션의 호출 방법·응답 처리를
따른다. `--no-review`가 명시된 경우에만 스킵.

- **호출 시점**: Step 6(변경 내역 분석) 후 커밋 메시지 작성 전.
- **선행 조건**: Step 5 pre-check이 통과해야 호출한다. pre-check이 실패하면
  리뷰는 건너뛴다 (어차피 커밋 못 함).
- **차단(`block: true`)**: 커밋 진행하지 말고 사용자에게 사유 전달. 수정 후 재시도.
- **경고(`warnings`)**: 진행하되 커밋 메시지에 경고 요약 반영.
- **통과**: 그대로 다음 단계로.

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

기본 브랜치로 `git push`. 완료 후 요약 제공.

요약에 다음을 포함:
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
