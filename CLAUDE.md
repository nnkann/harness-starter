# CLAUDE.md

## 언어
- 답변, 코드 주석, 커밋 메시지 모두 한국어.

## 절대 규칙
- 린터 에러 0인 상태에서만 커밋하라.
- 새 파일 생성 전 .claude/rules/naming.md를 읽어라.
- grep 대신 LSP를 우선 사용하라.

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

<important if="기존 코드 수정 중 새 함수를 만들려 할 때">
check-existing 스킬로 같은 도메인에 유사 함수가 있는지 먼저 확인하라.
</important>

<important if="에러가 발생했을 때">
추측하지 마. 먼저 조사하라. 재시작 제안 전에 코드를 확인하라.
</important>
