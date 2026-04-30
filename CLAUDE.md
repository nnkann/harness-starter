# CLAUDE.md

## 언어
한국어 (답변·코드 주석·커밋 메시지).

## 환경
<!-- harness-init 실행 후 채워진다 -->
- 패키지 매니저: N/A (harness-starter — 배포 템플릿, 앱 빌드 없음)
- 빌드/실행 명령어: python3 .claude/scripts/pre_commit_check.py (pre-check), python3 -m pytest .claude/scripts/test_pre_commit.py -q (테스트)
- 배포 방식: git push origin main → 다운스트림이 harness-upgrade로 fetch

## 행동 원칙

### Think Before Coding

구현 전에 가정을 명시한다.

- 요청에 해석이 여러 개라면 선택지를 먼저 제시하고 확인한다
- 가장 단순한 접근을 먼저 말한다. 복잡한 설계는 단순 방법이 실패한 뒤에
- 모호하면 멈추고 질문한다. 가정으로 달려가지 마라
- "아마 X일 것"으로 수정을 시작하지 마라 → `no-speculation.md`

### Goal-Driven Execution

성공 기준을 먼저 정의하고 구현한다.

- "버그 고쳐" → AC 먼저 정의, AC 통과하게 구현
- 다단계 작업은 `[단계] → verify: [AC 항목]` 형식으로 계획 수립
- WIP task AC 체크박스가 완료 기준. 전부 [x] → self-verify → /commit

## 절대 규칙
- worktree 생성 금지. Agent 호출 시 `isolation: "worktree"` 사용 금지.
- Bash는 복합 파이프라인·git·스크립트 실행만. 단일 조회는 Glob·Read·Grep. (LSP 가능하면 LSP 우선)

## 진입점

| 상황 | 진입 |
|------|------|
| 구현·버그수정·리팩토링 | `/implementation` 스킬 먼저 |
| 문서 단독 생성 | `/write-doc` 스킬 |
| 커밋 | `/commit` 스킬 |
| 기술 결정·스택 선택 | `/advisor` 스킬 |
| 에러·예상 밖 동작 (1회 시도로 원인 불명, 또는 동일 수정 2회 이상 반복) | `/debug-specialist` 에이전트 즉시 |
| 내부 자료 조사 | `doc-finder` 에이전트 |
| 외부 자료 조사 | `researcher` 에이전트 |


<important if="코드를 작성·수정·리팩토링하려 할 때">
/implementation 스킬을 먼저 발화했는가? 안 했다면 지금 즉시 발화하라.
예외: 1줄 타이포·문서만 수정·settings.json 키-값 토글.
</important>

<important if="docs/ 하위에 새 문서·WIP 파일을 만들려 할 때">
`.claude/rules/docs.md` "## SSOT 우선 + 분리 판단"을 먼저 읽어라.
기존 문서가 있으면 갱신이 기본. 새 파일은 분리 근거가 있을 때만.
</important>
