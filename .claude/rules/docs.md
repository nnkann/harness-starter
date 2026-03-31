# Docs 규칙

## 폴더 구조

```
docs/
├── wip/            ← 작업 중. 여기 파일 있으면 할 일 있다.
├── setup/          ← 초기 결정 (아키텍처, 스택, CPS)
├── history/        ← 수정 이력, 버그 원인, 왜 바꿨는지
├── development/    ← 구현 가이드, 패턴, 참고용
├── harness/        ← 하네스 변경 이력 (승격 로그 등)
└── archived/       ← 일회성, 참조 불필요, 중단된 작업
```

## 규칙

### 문서 생성
- 작업 시작 전 docs/wip/에 문서를 먼저 만든다 (implementation 스킬 참조).
- 파일명: snake_case. 간결하게. 예: `auth_stack_decision.md`
- 상태 헤더 필수: `> status: pending | in-progress | completed | abandoned`

### 문서 이동
- 완료/중단된 문서는 docs/wip/에 남기지 않는다.
- 이동은 commit 스킬이 처리한다. 수동으로 이동하지 마라.
- 이동 대상 폴더가 없으면 만든다.

### 금지
- docs/ 외의 위치에 문서를 만들지 마라 (README.md, CHANGELOG.md 등 루트 표준 파일 제외).
- docs/ 하위에 임의 폴더를 만들지 마라. 위 구조에 맞는 폴더만 사용.
- 새 폴더가 필요하면 사용자에게 먼저 확인.
