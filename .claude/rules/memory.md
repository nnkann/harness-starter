# Memory 활용 규칙

defends: P7

세션 간 지속 정보 저장소. 세션 내 동적 snapshot은 별도.

## 두 종류

### 실제 Claude memory (`~/.claude/`, Anthropic 관리)

사용자 개인 성향·선호 + Claude 자체 실수 패턴. **프로젝트 repo에 저장 X**.

### 프로젝트 memory (`.claude/memory/`, git 추적)

조건: **다른 사람·다른 Claude 세션이 읽어야 의미 있음**.
- 프로젝트 관행·hard-won lessons
- 다운스트림이 상속받아야 할 운영 교훈

**사용자 개인 성향은 여기에 저장 X**.

## 경로

- 디렉토리: `.claude/memory/`
- 인덱스: `.claude/memory/MEMORY.md` (세션 시작 자동 로드)
- 동적 snapshot: `.claude/memory/session-*.txt` (gitignore)

## 동적 snapshot — 3개 파일 (확장 금지)

| 파일 | 내용 | write | read |
|------|------|-------|------|
| `session-pre-check.txt` | pre-check stdout | Step 5 직후 background | git hook 커밋 메시지 주입 |
| `session-start-unstaged.txt` | SessionStart `git diff --name-only` | SessionStart hook | pre_commit_check.py prior_session_files |
| `session-moved-docs.txt` | `docs_ops.py move` 완료 경로 | move 완료 직후 | pre_commit_check.py 봉인 면제 판정 |

**라이프사이클**: commit 성공 → 스킬 끝에서 `rm -f .claude/memory/session-*.txt`.

## 저장 대상

| 우선순위 | 타입 | 예시 |
|---|---|---|
| 1 | feedback | 사용자가 수정한 접근법 |
| 2 | project | 프로젝트 맥락·마감 |
| 3 | user | 사용자 역할·전문 분야 |
| 4 | reference | 외부 시스템 포인터 |

## 저장하지 않는 것

- 코드에서 읽을 수 있는 것 (구조·패턴·아키텍처)
- `git log`로 알 수 있는 것
- `CLAUDE.md`·`rules/`에 이미 있는 것
- 사용자 개인 성향 (→ 실제 Claude memory)

## 트리거

- 세션 시작: `MEMORY.md` 자동 로드
- 사용자 "기억해" 명시: 즉시 저장
- 세션 종료 직전: `stop-guard.sh`가 1줄 환기

memory와 현재 코드 충돌 시 현재 코드 신뢰, memory 업데이트.
