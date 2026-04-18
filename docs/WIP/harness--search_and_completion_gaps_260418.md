---
title: 하네스 구멍 정리 — 검색 실패·IDE 컨텍스트 오신뢰·완료 선언 허점 + hook matcher 버그
domain: harness
tags: [search, ide-context, incident-doc, completion-gate, hook-matcher]
status: in-progress
created: 2026-04-18
updated: 2026-04-18
---

# 하네스 구멍 정리 (세션 핸드오프)

## 이 문서는

2026-04-18 세션에서 진단한 하네스 구멍 4개 + 실행 중 발견한 **settings.json
hook matcher 버그**까지 정리. 다음 세션에서 이어서 진행할 수 있도록
**현재 상태**와 **남은 일**을 명시.

## 진단한 구멍 4개 (rules/docs.md 반영 완료)

### 1. IDE 컨텍스트 파일명을 "진실"로 오인 (P0) — 반영 완료

`<ide_opened_file>`, `<ide_selection>`이 주는 경로는 존재 여부 무보장.
Claude가 이 파일명 단어만 키워드로 쓰면 사용자 원문과 어긋난 검색이 된다.

→ `rules/docs.md`에 "IDE 경로는 Read/Glob 존재 확인 후 사용. 없으면 버리고
사용자 원문 키워드로 재검색" 추가.

### 2. incident 문서에 증상 키워드 누락 허용 (P1) — 규칙만 반영, 스킬은 남음

incidents/ tags가 기술 분류 중심이면 증상 유발 고유명사·식별자가 누락됨.

→ `rules/docs.md` 프론트매터 스펙에 incidents/ 전용 필드 `symptom-keywords`
추가. **write-doc 스킬이 비면 재질의하도록 수정 필요 (후속)**.

### 3. completed로 닫을 때 미해결 후속을 본문에만 묻음 (P1) — 규칙만 반영, 스킬은 남음

"증상 해결, 정책 미결"이 completed로 닫히면 본문 TODO/메모가 묻힌다.

→ `rules/docs.md` "문서 이동"에 차단 조건 명시: `TODO|FIXME|후속|미결|
미결정|추후|나중에|별도로` 패턴 있으면 별도 WIP로 분리 강제. **commit
스킬이 실제로 검사하도록 수정 필요 (후속)**.

### 4. 검색 실패 자동 escalation 부재 (P0) — 반영 완료

1차 검색 공백이 바로 "없다" 결론으로 이어짐.

→ `rules/docs.md`에 3단계 검색(파일명 Glob → 제목/태그 grep → 본문 grep)
강제 + docs-lookup 에이전트 위임 escalation 명시.

## 추가로 발견한 버그 — settings.json hook matcher

세션 중 사용자가 "stagelink에서 커밋 스킬 hook이 발화 안 된다"고 지적.
git log로 추적한 결과:

- v1.2.3에서 파이프 문법(`Bash(x)|Bash(y)`)이 공식 문서상 미지원이라
  핸들러 분리했음.
- 분리 과정에서 `prompt` type hook은 `Bash(git commit*)` 하나만 등록,
  `Bash(* git commit*)` (체이닝 커밋) 변형 누락.
- **stagelink는 더 큰 문제**: `matcher` 필드에 `Bash(git commit*)` 같은
  세부 패턴을 넣어놨음. 공식 문서상 `matcher`는 **툴 이름만 허용**
  (`Bash`, `Write|Edit`). 세부 패턴은 `if` 필드에서만 동작.
- 즉 stagelink는 **모든 커밋 관련 hook이 조용히 발화 실패** 상태였음.
  HARNESS.json 버전이 1.2.3이어도 내용은 잘못된 독자 수정본.

### 반영 완료 (이번 세션)

1. `harness-starter/.claude/settings.json` — prompt hook 2개에 `Bash(*
   git commit*)` 변형 추가.
2. `stagelink/.claude/settings.json` — matcher 구조를 `matcher: "Bash"` +
   `if: "Bash(...)"`로 전면 정정. stagelink 고유 항목(permissions,
   pre-edit-validator.mjs, write-guard.sh) 보존.

## 현재 상태 (2026-04-18 세션 종료 시점)

### harness-starter 변경사항 (미커밋)

```
M .claude/rules/docs.md          ← 4개 구멍 반영 (IDE 규칙 + 3단계 검색 + symptom-keywords + completed 차단)
M .claude/settings.json          ← prompt hook에 * git commit* 변형 추가
?? docs/WIP/harness--search_and_completion_gaps_260418.md  ← 이 문서
```

### stagelink 변경사항 (미커밋, 이 레포와 무관)

```
M d:/Work/StageLink/dev/.claude/settings.json  ← hook matcher 전면 정정
```

## 다음 세션에서 이어할 일

### 즉시 (이어서 바로)

1. **harness-starter 커밋** — 위 3개 변경사항.
   - 이번 세션에서 "이 후 바로 이어할 수 있도록" 해달라 해서 커밋은 다음
     세션으로 넘김. 사용자가 한 번 더 리뷰 후 커밋 의사 확인.
   - 커밋 메시지 초안: "feat: 검색/완료 규칙 강화 + prompt hook matcher 보완"
   - strict 모드라 commit 스킬 내부 리뷰 + hook 리뷰가 돌 예정.

2. **stagelink 커밋 여부 확인** — stagelink의 settings.json 수정은 별도
   레포의 변경이라 사용자가 직접 확인 후 커밋해야 함.

### 후속 작업 (별도 WIP 필요)

3. **write-doc 스킬 수정** — incidents/ 생성 시 `symptom-keywords` 재질의
   로직 추가. 구멍 2 완결.

4. **commit 스킬 수정** — completed 전환 시 본문 미결 패턴 차단 로직 추가.
   구멍 3 완결.

5. **다운스트림 하네스 버전 검증 메커니즘** — stagelink 사례에서 HARNESS.json
   버전이 1.2.3이어도 settings.json 내용이 유효하지 않을 수 있음이 드러남.
   harness-upgrade 또는 harness-sync가 **settings.json 유효성**(matcher
   필드에 세부 패턴 들어있으면 경고)을 검사하도록 개선 필요.

## 이 세션에서 배운 것 (메모리 후보)

- **IDE 컨텍스트는 힌트일 뿐** — 이미 rules에 반영했으니 메모리는 불필요.
- **"없다"는 3단계 후에만** — 이미 rules에 반영.
- **프로젝트 성격(범용 vs 다운스트림) 구분 강화 필요** — harness-starter
  레포에서 다운스트림 고유명사를 예시로 박는 실수를 했음. 세션 중 즉시
  교정했으나, 재발 방지용 메모리 검토 여지 있음.
- **hook matcher 공식 스펙** — matcher는 툴 이름만, 세부 패턴은 if 필드.
  이건 rules에 명시해두면 후속 편집 시 도움. 별도 WIP/수정 고려.

## 참고 커밋

- `8f9d95a` — fix: agent hook → prompt 교체 + if 파이프 문법 수정 (v1.2.3)
- `ed21cca` — fix: PreToolUse matcher 문법 오류 수정 — hook이 한 번도 발화 안 됨 (v1.2.1)
- `4ec2a98` — refactor: commit 스킬의 Review를 PreToolUse hook으로 분리 (v0.9.2)
