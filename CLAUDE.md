# CLAUDE.md

## 언어
- 답변, 코드 주석, 커밋 메시지 모두 한국어.

## 절대 규칙
- 린터 에러 0인 상태에서만 커밋하라.
- 새 파일 생성 전 .claude/rules/naming.md를 읽어라.
- **worktree를 생성하지 마라.** main에서 직접 작업한다. Agent 호출 시 `isolation: "worktree"` 사용 금지.
- **Bash tool은 최후 수단이다.** 전용 도구 매핑 — `ls`·`find`→Glob,
  `cat`·`head`→Read, `grep`→Grep tool. (LSP 가능하면 LSP 우선). Bash는
  `git`·실제 스크립트 실행·시간 측정·여러 명령 연결(`|`·`&&`·서브쉘)
  같은 **복합 파이프라인**이 필요할 때만. 단일 명령은 전용 도구. 성능
  측정·회귀 실행은 1회로 판단 가능하면 1회만 — 3회 루프는 결론이 흔들리는
  경계 케이스에서만.

## 환경
<!-- harness-init 스킬 실행 후 채워진다 -->
- 패키지 매니저:
- 빌드/실행 명령어:
- 배포 방식:
- 기존 환경이 있으면 새로 만들지 마라.

## 구조
- 테스트: tests/ 또는 __tests__/ 폴더에만.
- 문서: docs/ 하위에만. 루트에 만들지 마.

<important if="새 파일을 생성할 때">
.claude/rules/naming.md를 먼저 읽고 규칙에 맞는 이름으로 생성하라.
</important>

<important if="코드 작업 없이 문서만 단독으로 생성할 때">
write-doc 스킬을 사용하라. docs/에 직접 파일을 만들지 마라.
</important>

<important if="docs/ 하위에 새 문서·WIP 파일을 만들려 할 때 (스킬 발동 여부 무관)">
먼저 `.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" 섹션을 읽어라.
3단계 탐색 의무: cluster 스캔 → 키워드 grep → 후보 본문 Read. hit이
있으면 **기본은 기존 문서 갱신** (완료 문서는 WIP로 재개). 새 파일은
분리 근거가 있을 때만. 동격 선택지로 사용자에게 떠넘기지 마라.
</important>

<important if="기존 코드 수정 중 새 함수를 만들려 할 때">
check-existing 스킬로 같은 도메인에 유사 함수가 있는지 먼저 확인하라.
</important>

<important if="에러가 발생했을 때">
추측하지 마. 먼저 조사하라. 재시작 제안 전에 코드를 확인하라.
</important>

<important if="다단 처리 파이프라인(여러 단계가 입력→중간신호→출력으로 연결되는 구조)을 설계·재편할 때">
.claude/rules/pipeline-design.md를 먼저 읽어라. 상류 신호 재사용·
하류 보존 책임·전제 검증을 7항목 체크리스트로 강제한다.
</important>
