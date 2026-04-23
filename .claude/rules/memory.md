# Memory 활용 규칙

"실수를 코드화"의 세션 간 확장 + 세션 내 동적 snapshot 저장소.
배경: `docs/decisions/hn_memory.md`.

## 두 종류의 memory — 경계 엄수

### 실제 Claude memory (Anthropic 관리, 로컬)

- Claude Code의 auto memory가 자율 관리하는 개인 메모리
- 저장 대상: **이 사용자·이 Claude 세션 페어에만 의미 있는 것**
  - 사용자 개인 성향·선호 (예: 근본 해결 선호, 비유 선호)
  - Claude 자체의 실수 패턴
- **프로젝트 repo에 저장 X**. 사용자별 `~/.claude/` 경로

### 프로젝트 memory (`.claude/memory/`, git 추적)

- 조건: **다른 사람·다른 Claude 세션이 읽어야 의미 있음**
- 저장 대상:
  - 프로젝트 관행·hard-won lessons (예: "eval --deep은 archive도 검사")
  - 다운스트림이 상속받아야 할 운영 교훈
- **사용자 개인 성향은 여기에 저장 X** — 실제 Claude memory로

## 경로

- 프로젝트 memory 디렉토리: `.claude/memory/`
- 인덱스: `.claude/memory/MEMORY.md` (세션 시작 자동 로드)
- 동적 snapshot: `.claude/memory/session-*.txt` (gitignore, 세션 한정)

## 저장 대상 (정적 memory)

| 우선순위 | 타입 | 대상 | 예시 |
|----------|------|------|------|
| 1 | feedback | 사용자가 수정한 접근법 | "이 프로젝트는 단일 PR로 묶어라" |
| 2 | project | 프로젝트 맥락·마감 | "4/15까지 인증 완료 필요" |
| 3 | user | 사용자 역할·전문 분야 | "백엔드 풍부, 프론트 초심자" |
| 4 | reference | 외부 시스템 포인터 | "버그 트래킹 Linear INGEST" |

## 저장하지 않는 것 (중복 금지)

- 코드에서 읽을 수 있는 것 (구조·패턴·아키텍처)
- `git log`로 알 수 있는 것 (변경 이력)
- `CLAUDE.md`·`rules/`에 이미 있는 것
- 사용자 개인 성향 (→ 실제 Claude memory 경로)

> 이전 규칙 "현재 세션에서만 유효한 임시 정보 → 저장 금지"는 **삭제**.
> session-* snapshot 여지를 확보하기 위해 (2026-04-20 재설계).

## 동적 snapshot (`session-*.txt`)

commit 스킬이 hook·외부 도구에 전달할 필요가 있을 때만 쓰는 1개 파일.
commit 내부 경로는 Bash 변수 재사용 (파일 I/O 대기 없음).

| 파일 | 내용 | write | read |
|------|------|-------|------|
| `session-pre-check.txt` | pre-check stdout (recommended_stage 등) | Step 5 직후 background (`&`) | git hook이 커밋 메시지에 주입할 때 |
| `session-start-unstaged.txt` | SessionStart 시점 `git diff --name-only` 목록 | SessionStart hook | pre-commit-check이 `prior_session_files` 신호 계산 시 |

**폐기 (audit #5, 2026-04-22)**:
- `session-staged-diff.txt`: Bash 변수 `STAGED_DIFF`로 대체
- `session-tree-hash.txt`: tree-hash 캐싱 자체 폐기 (I/O 대기 무의미)

**확장 금지**: 2개 외 추가 원할 시 `hn_memory.md` 수정 후 재합의.

**라이프사이클**:
- commit 성공 → 스킬 끝에서 `rm -f .claude/memory/session-*.txt`
- commit 실패·재시도 → pre-check 재실행이 기본. 파일은 hook용 참조만

## 트리거 3개 (확정)

| 시점 | 동작 | 구현 위치 |
|------|------|----------|
| 세션 시작 | `MEMORY.md` 자동 로드 | Claude Code 기본 동작 |
| 사용자 "기억해" 명시 | 즉시 저장 | Claude 행동 |
| 세션 종료 직전 | "저장할 것 있나?" 환기 1줄 | `stop-guard.sh` |

**자동 저장 강제 안 함**. 환기만. `/clear` 전에 사용자가 눈으로 판단.

## 행동 규칙

- 사용자가 접근법을 수정 → feedback memory 저장 검토
- "기억해" 요청 → 즉시 저장
- 참조 시 → 현재 상태와 대조 후 사용 (오래된 memory 주의)
- memory와 현재 코드 충돌 → 현재 코드 신뢰, memory 업데이트

## 지속성 매트릭스

| 지속성 | 도구 | 용도 |
|--------|------|------|
| 세션 내 (짧음) | `.claude/memory/session-*` | staged diff·pre-check 캐시 |
| 세션 내 (작업) | `docs/WIP/` + TODO | 현재 작업 |
| 세션 간 (코드화 가능) | `rules/`, `CLAUDE.md` | 규칙 강제 |
| 세션 간 (코드화 불가) | `.claude/memory/*.md` | 관행·피드백·맥락 |
| 영구 | `git history` | 변경 이력 |
