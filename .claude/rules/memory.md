# Memory 활용 규칙

defends: P8

세션 간 지속 정보 저장소. 세션 내 동적 snapshot은 별도.
memory는 판단의 원자료가 아니라 reminder·회상 보조 신호다. memory count,
라벨, 오래된 signal을 근거로 사실을 단정하지 않는다.

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

## signal_* 파일 스키마

`.claude/memory/signal_*.md` — 반복 패턴 회상 신호. SessionStart에서
glob 자동 로드 (session-start.py). frontmatter 필드:

```yaml
---
signal: <1줄 — 패턴 본질>
domain: harness
keywords: [회상-키워드]
strength: weak | medium | strong
candidate_p: P#  # 가까운 CPS Problem (없으면 P10)
last_validated: YYYY-MM-DD  # 선택. 마지막으로 현재 코드/문서와 대조한 날
valid_until: YYYY-MM-DD     # 선택. 이 날짜 이후 stale 후보
---
```

본문은 자유 형식. 운용 로그 누적(`signal_defense_success.md` 패턴)도
허용 — strength·candidate_p가 메타로 작동. `last_validated`·`valid_until`
없는 기존 signal은 허용하되, 오래된 신호는 사실이 아니라 재확인 후보로 읽는다.

### 회귀 signal 사용 계약

signal·incident·audit 로그는 회귀 증거가 아니라 **환기 신호**다. 현재 작업에
적용하려면 3단계를 거친다.

1. **환기**: domain·keywords·candidate_p가 현재 C와 가까운 후보를 보여준다.
2. **재확인**: 현재 코드·문서·git log와 대조해 stale 여부를 판정한다.
3. **검증 선택**: 여전히 맞는 경우에만 AC `tests` 또는 `실측` 범위에 반영한다.

금지:

- stale signal을 근거로 테스트 범위를 넓히기
- signal count를 근거로 위험도를 단정하기
- "과거에 회귀가 있었음"만으로 현재 변경의 실패를 단정하기
- memory에 없다는 이유로 회귀 위험이 없다고 단정하기

memory/reminder가 과거 회귀를 띄웠지만 현재 코드와 맞지 않으면 P9 정보 오염
후보로 기록하고, 필요한 경우 signal의 `last_validated`·`valid_until`을 갱신한다.
과거 회귀가 문서에 있는데 작업 시점에 전혀 떠오르지 않았으면 P8 누락 후보로
보고 signal·incident 키워드 또는 출력 조건을 보강한다.

## 출력 의미 계약

SessionStart·StopGuard가 memory를 노출할 때 count 단독 출력 금지.

- ✅ "signal 3건: validated 1 / stale 후보 2"
- ✅ "memory 없음 — 자동 주입된 사실 없음"
- ❌ "메모리 4개 항목 로드됨"만 출력

count는 본문·검증 상태·stale 여부 없이 단독 근거가 될 수 없다.

## 누적 감사 로그 (snapshot과 별개)

snapshot은 commit마다 정리되지만 감사 로그는 **세션 횡단 누적**. gitignore.

| 파일 | 내용 | write | read |
|------|------|-------|------|
| `stop_hook_audit.log` | Stop hook A·B·C 신호 hit (timestamp + reason + WIP 경로) | stop-guard.py | eval --quick (누적 빈도 보고) |

확장 금지 — 새 누적 감사 로그는 본 표 추가 후 도입.

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
memory가 현재 코드·git log·docs와 충돌하면 memory는 stale이다. stale 신호는
P9 정보 오염 후보로 보고, 현재 코드/문서 확인 없이 판단 baseline으로 쓰지 않는다.
