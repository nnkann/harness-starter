# AGENTS.md migrated from top-level during Phase B-2D

Source: top-level AGENTS.md
Reason: Hermes-native cleanup removed legacy top-level agent surface; content preserved for owner review.

---

# AGENTS.md

## 언어
한국어 (답변·코드 주석·커밋 메시지).

## 환경
<!-- harness-init 실행 후 채워진다 -->
- 패키지 매니저: N/A (harness-starter — 배포 템플릿, 앱 빌드 없음)
- Python 요구사항: 3.10+ (`str | None` 타입 힌트 등 3.10 문법 사용)
- 빌드/실행 명령어: python3 .claude/scripts/pre_commit_check.py (pre-check), python3 -m pytest .claude/scripts/tests/ -q (테스트)
- 배포 방식: git push origin main → 다운스트림이 harness-upgrade로 fetch

## Runtime Adapter 표면

이 루트의 하네스 파일은 제품 아키텍처가 아니라 agent runtime adapter와
manifest다. 제품 코드는 별도 `src/`, `app/`, `packages/` 등 프로젝트가
정한 위치에 둔다.

| 경로 | 역할 |
|------|------|
| `CLAUDE.md` | Claude Code adapter 루트 인스트럭션 |
| `AGENTS.md` | Codex adapter 루트 인스트럭션 |
| `.claude/` | 현재 하네스 core 구현 + Claude adapter + manifest |
| `.agents/` | Codex가 읽는 skill adapter mirror |
| `.codex/` | Codex agent/hook adapter |
| `.harness/` | Hermes/project orchestration metadata |

`minimal` 프로파일은 기능 minimal이다. runtime surface minimal이 아니므로
사용하지 않는 adapter를 삭제하기 전에 `.claude/HARNESS.json`의
`runtime_stack`과 `runtime_adapters`를 확인하고, hooks/scripts/skills 참조를
먼저 추적한다.

## Codex 안전 조회/검증

Codex에서 단순 조회·검증 명령이 반복 승인으로 흐름을 끊으면, 우선
`.claude/scripts/safe_command.py` dispatcher를 사용한다.

```bash
python .claude/scripts/safe_command.py status
python .claude/scripts/safe_command.py cps-list
python .claude/scripts/safe_command.py verify-relates
python .claude/scripts/safe_command.py eval-harness
python .claude/scripts/safe_command.py precheck
```

dispatcher 변경 후에는 `python -m py_compile .claude/scripts/safe_command.py`와
`python -m pytest .claude/scripts/tests/test_pre_commit.py -q`를 실행한다.

지속 승인 후보 prefix는 위 스크립트 파일까지 포함한 좁은 prefix다. 삭제·이동·커밋·푸시·설정 변경·네트워크·의존성 설치는 dispatcher에 넣지 않는다.

## 검증 레이어

- pre-check은 staged Python을 `python -m py_compile`, staged Shell을 `bash -n`으로 검사한다.
- `eval --harness`와 pre-check은 루트 안내·하네스 스크립트의 path contract drift를 관측/차단한다.
- sandbox는 permission-ready 조건에서만 완료 증거로 쓴다. 필요한 파일·도구·네트워크·자격 증명 권한이 해결되지 않아 검증이 실행되지 않았으면, sandbox 실행 자체를 통과 근거로 삼지 않는다.
- `ruff`, `pyright`, `mypy`, `shellcheck`는 가용성을 보고하며, 미설치 도구는 실행된 검증으로 간주하지 않는다.

## 행동 원칙

### AC (Acceptance Criteria)

모든 작업의 완료 기준. implementation Step 1이 WIP 문서에 작성.

- AC 없는 작업은 완료 선언 불가 — AC부터 작성
- AC 체크박스 전부 [x] → self-verify → /commit
- 필수 필드 4개: `Goal:` / `review: skip|self|review|review-deep` / `tests:` / `실측:`
- AC 형식 SSOT: `.claude/rules/docs.md` "## AC 포맷"

### CPS (Context·Problem·Solution)

모든 작업은 `docs/guides/project_kickoff.md`의 Problem에 매핑된다.

- 사실상의 C는 task와 일대일로 매칭한다. 하나의 완료 판단으로 닫히는 작업은 하나의 C 안에 복수 P/S/AC를 담고, 완료 기준·산출물이 갈라질 때만 task/C를 분리한다.
- implementation Step 0이 작업 발화(C) → P# 매칭 → WIP frontmatter에 기록
- WIP frontmatter 필수: `c:` / `problem: P#` / `s: [S#]`
- CPS 없으면 pre-check이 차단 (harness-init 미완료)
- CPS 인용 형식 SSOT: `.claude/rules/docs.md` "## CPS 인용"

## 절대 규칙
- 커밋은 반드시 `/commit` 스킬 경유. WIP 없어도 `--no-review` 플래그 사용. 스킬 밖에서 `commit_finalize.sh`·`git commit` 직접 호출 금지 (스킬 Step 7이 지시한 wrapper 호출만 허용).
- worktree는 blanket ban이 아니다. 생성 시 소유권·정리 책임·변경 보존 계약을 명시하고, 권한·경로 binding이 불명확하면 진행하지 않는다.
- Bash는 복합 파이프라인·git·스크립트 실행만. 단일 조회는 Glob·Read·Grep. (LSP 가능하면 LSP 우선)
- 미루기 회피 사유 ("측정 후·다음 세션·데이터 누적 필요" 등) 단독 사용 금지 — 사용자 명시 승인 시만 허용
- completed 문서 본문 무단 변경 금지 — `docs_ops.py reopen`으로 in-progress 전환 후 수정. pre-check이 차단
- docs/WIP/ 파일 Write 직접 생성 금지 — `/write-doc` 또는 `/implementation` 스킬 발화 후에만. 스킬 없이 Write 도구로 WIP 파일 생성 시 즉각 삭제 후 스킬 재진입

## CPS

`docs/guides/project_kickoff.md` (CPS) 는 C 판단 프롬프트. 자라지 않음.
wave별 case는 `docs/cps/cp_{slug}.md`로 박제. git history가 박제 SSOT.
빠른 조회: `python .claude/scripts/docs_ops.py cps list/cases/show/stats`.

## Reminder

작업 중 사용자가 "리마인더로 남기자"라고 하면 관련 WIP 흡수 가능성을 먼저 본다.
반복 회상 신호가 필요할 때만 `.claude/memory/reminders/reminder_*.md`에 규격대로
얇게 남긴다. `docs/`는 SSOT 자리이므로 active reminder를 새 폴더로 만들지 않는다.

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
