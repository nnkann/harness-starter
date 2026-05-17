# AGENTS.md

## 언어
한국어 (답변·코드 주석·커밋 메시지).

## 환경
<!-- harness-init 실행 후 채워진다 -->
- 패키지 매니저: N/A (harness-starter — 배포 템플릿, 앱 빌드 없음)
- 빌드/실행 명령어: python3 .claude/scripts/pre_commit_check.py (pre-check), python3 -m pytest .claude/scripts/tests/ -q (테스트)
- 배포 방식: git push origin main → 다운스트림이 harness-upgrade로 fetch

## 행동 원칙

### AC (Acceptance Criteria)

모든 작업의 완료 기준. implementation Step 1이 WIP 문서에 작성.

- AC 없는 작업은 완료 선언 불가 — AC부터 작성
- AC 체크박스 전부 [x] → self-verify → /commit
- 필수 필드 4개: `Goal:` / `review: skip|self|review|review-deep` / `tests:` / `실측:`
- AC 형식 SSOT: `.claude/rules/docs.md` "## AC 포맷"

### CPS (Context·Problem·Solution)

모든 작업은 `docs/guides/project_kickoff.md`의 Problem에 매핑된다.

- implementation Step 0이 작업 발화 → P# 매칭 → WIP frontmatter에 기록
- WIP frontmatter 필수: `problem: P#` / `solution-ref: S# — "..."`
- CPS 없으면 pre-check이 차단 (harness-init 미완료)
- CPS 인용 형식 SSOT: `.claude/rules/docs.md` "## CPS 인용"

## 절대 규칙
- 커밋은 반드시 `/commit` 스킬 경유. WIP 없어도 `--no-review` 플래그 사용. 스킬 밖에서 `commit_finalize.sh`·`git commit` 직접 호출 금지 (스킬 Step 7이 지시한 wrapper 호출만 허용).
- worktree 생성 금지. Agent 호출 시 `isolation: "worktree"` 사용 금지.
- Bash는 복합 파이프라인·git·스크립트 실행만. 단일 조회는 Glob·Read·Grep. (LSP 가능하면 LSP 우선)
- 미루기 회피 사유 ("측정 후·다음 세션·데이터 누적 필요" 등) 단독 사용 금지 — 사용자 명시 승인 시만 허용
- completed 문서 본문 무단 변경 금지 — `docs_ops.py reopen`으로 in-progress 전환 후 수정. pre-check이 차단
- docs/WIP/ 파일 Write 직접 생성 금지 — `/write-doc` 또는 `/implementation` 스킬 발화 후에만. 스킬 없이 Write 도구로 WIP 파일 생성 시 즉각 삭제 후 스킬 재진입

## CPS

`docs/guides/project_kickoff.md` (CPS) 는 C 판단 프롬프트. 자라지 않음.
wave별 case는 `docs/cps/cp_{slug}.md`로 박제. git history가 박제 SSOT.
빠른 조회: `python .claude/scripts/docs_ops.py cps list/cases/show/stats`.

## 진입점

| 상황 | 진입 |
|------|------|
| 구현·버그수정·리팩토링·코드 수반 문서 생성 | `/implementation` 스킬 먼저 |
| 문서 단독 생성 | `/write-doc` 스킬 |
| 커밋 | `/commit` 스킬 |
| 기술 결정·스택 선택 | `/advisor` 스킬 |
| 에러·예상 밖 동작 (1회 시도로 원인 불명, 또는 동일 수정 2회 이상 반복) | `/debug-specialist` 에이전트 즉시 |
| 내부 자료 조사 | `doc-finder` 에이전트 |
| 외부 자료 조사 | `researcher` 에이전트 |
| 하네스 문서 품질 점검 (모호성·모순·CPS 무결성) + 레거시 정비 안내 | `/eval --harness` (doc-health 흡수) |


<important if="코드를 작성·수정·리팩토링하려 할 때">
/implementation 스킬을 먼저 발화했는가? 안 했다면 지금 즉시 발화하라.
예외: 1줄 타이포·문서만 수정·settings.json 키-값 토글.
</important>

<important if="docs/ 하위에 새 문서·WIP 파일을 만들려 할 때, 또는 Write 도구로 docs/ 경로에 파일을 생성하려 할 때">
1. 스킬을 먼저 발화했는가? — 문서 단독 생성은 `/write-doc`, 코드 작업 수반은 `/implementation`. Write 도구 직접 사용은 절대 규칙 위반 — 즉시 스킬로 재진입.
2. SSOT 탐색 — `.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" 적용. 기존 문서가 있으면 갱신이 기본. 새 파일은 분리 근거가 있을 때만.
</important>



