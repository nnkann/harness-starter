# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. 공통 하네스 계약과 runtime adapter를 분리해 Claude, Codex, Hermes, Agy 같은 여러 agent 조합을 통합 관리한다.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

현재 버전: **v0.54.1** — 0.x = 공개 API·동작 불안정·실험 단계. 다운스트림 실측 누적·매처 동작 검증·README 격차 안정화 후 1.0.0 검토. 변경 이력은 `git log --oneline --grep "(v0\."`, 다운스트림 마이그레이션은 `docs/harness/MIGRATIONS.md`.

## 빠른 시작

요구사항: Python 3.10+ (하네스 스크립트는 `str | None` 타입 힌트 등 Python 3.10 문법을 사용한다).

```bash
# 신규 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/h-setup.sh .

# Hermes, Codex, Claude 등 사용 가능한 runtime에서 harness-init으로 스택 결정
```

h-setup.sh는 멱등성 보장. 이미 있는 파일은 건드리지 않는다.

```bash
# (필수) pre-commit 시크릿 스캔 훅 설치 — 다운스트림 안전망
bash scripts/install-secret-scan-hook.sh
```

이 hook은 **commit 스킬 우회·`HARNESS_DEV=1`·터미널 직접 `git commit` 모든 경로**에서 시크릿 line-confirmed를 차단하는 마지막 안전망. 미설치 시 pre-check이 매 commit마다 경고. 단 `git commit --no-verify`는 hook 자체를 우회 — 절대 사용 금지.

gitleaks가 있으면 `gitleaks protect --staged` 사용, 없으면 grep 폴백. grep 폴백은 best-effort — 리터럴 분할이나 Base64 우회는 탐지하지 못하므로 실제 방어가 중요하면 gitleaks 설치 권장.

```bash
# 기존 프로젝트에 하네스 이식
# → 사용 가능한 runtime(Hermes/Codex/Claude 등)에서 /harness-adopt → /harness-init 순서로 실행

# 하네스를 최신 버전으로 업그레이드
bash /path/to/harness-starter/h-setup.sh --upgrade /path/to/my-project
# → 사용 가능한 runtime에서 /harness-upgrade (git 3-way merge + MIGRATIONS.md 자동 안내)
```

## 구조

```
CLAUDE.md                        Claude Code runtime adapter 루트 인스트럭션
AGENTS.md                        Codex runtime adapter 루트 인스트럭션
.agents/
└── skills/                      Codex가 직접 읽는 generated/validated adapter 후보
.codex/
├── agents/                      Codex agent adapter (TOML)
└── hooks.json                   Codex hook adapter
.claude/
├── settings.json                Claude hook adapter (단일 bash-guard.sh로 통합)
├── HARNESS.json                 하네스 메타 (버전, 프로파일, runtime_stack, runtime_adapters)
├── rules/                       자동 로드 규칙 (10개)
│   ├── self-verify.md           [상시] 작업 중 자기 검증 (AC 트리거 매트릭스)
│   ├── code-ssot.md             [상시] 코드 심볼 SSOT drift 방지
│   ├── coding.md                [상시] 코딩 컨벤션 (Surgical Changes)
│   ├── naming.md                [paths] 네이밍 + 도메인 등급 + cluster 자동 매핑
│   ├── docs.md                  [상시] 문서 구조 + 프론트매터 + 탐색 규칙 + completed 차단 키워드
│   ├── memory.md                [상시] 메모리 활용 규칙 (에이전트 memory vs 프로젝트 memory 경계)
│   ├── security.md              [상시] 시크릿 금지 + 4계층 방어
│   ├── internal-first.md        [상시] 외부 자료 전 내부 자료 우선 (git/docs/rules)
│   ├── no-speculation.md        [상시] 추측 수정 금지 — 첫 행동은 관찰·재현·선행 사례
│   └── hooks.md                 [상시] PreToolUse argument-constraint 매처 금지
├── skills/                      legacy skill source/Claude adapter (13개, starter 전용 3개 포함)
│   ├── harness-init/            [starter] 프로젝트 초기화 (CPS + 스택 결정)
│   ├── harness-adopt/           [starter] 기존 프로젝트에 하네스 이식
│   ├── harness-dev/             [starter] 스크립트·스킬 추가 시 h-setup.sh·README·HARNESS.json 자동 갱신
│   ├── harness-sync/            클론 후 환경 동기화
│   ├── harness-upgrade/         하네스 업그레이드 (3-way merge + MIGRATIONS.md 안내)
│   ├── implementation/          작업 문서 라이프사이클
│   ├── cps-learn/               복수 P#/S# 해석 + AC 단계화·반복·분리 검증 설계
│   ├── commit/                  커밋 + Review (--review/--no-review 2단계, starter push 보호)
│   ├── eval/                    건강 검진 (--quick/--harness)
│   ├── advisor/                 멀티 에이전트 판단 엔진 (specialist 풀 + 의사결정 프레임)
│   ├── write-doc/               문서 단독 생성 (incidents symptom-keywords 강제)
│   ├── naming-convention/       네이밍 + 도메인 등급 설정
│   └── coding-convention/       코딩 컨벤션 설정
├── agents/                      서브에이전트 (8개)
│   ├── advisor.md               PM/orchestrator — specialist 종합 (opus)
│   ├── doc-finder.md            문서 검색·요약 (사서, haiku)
│   ├── codebase-analyst.md      내부 코드·문서 분석 (컨설턴트, sonnet)
│   ├── researcher.md            외부 자료 조사 (sonnet)
│   ├── risk-analyst.md          비판자·devil's advocate (sonnet)
│   ├── performance-analyst.md   성능·N+1·동시성 (sonnet)
│   ├── threat-analyst.md        외부 위협 분석 (public repo·번들·RLS bypass, sonnet)
│   └── review.md                커밋 전 diff 단위 검증 (2축 + 회귀 알파 + 조기 중단, sonnet)
├── memory/                      프로젝트 memory (자동 주입 아님, session-start가 제한 노출)
│   ├── MEMORY.md                memory index
│   ├── reminders/               active reminder routing signal
│   │   └── reminder_*.md        반복 패턴·후속 판단 회상 후보
│   ├── feedback_*.md            다운스트림/운영 피드백
│   ├── project_eval_last.md     최근 eval 관찰 기록
│   ├── stop_hook_audit.log      Stop hook 감사 로그
│   └── session-*.txt            세션 snapshot (gitignore)
└── scripts/                     hook 스크립트 + 회귀 테스트
    ├── session-start.py         SessionStart hook
    ├── stop-guard.py            Stop hook
    ├── post-compact-guard.py    PostCompact hook
    ├── auto-format.sh           PostToolUse 포매터
    ├── write-guard.sh           Write 가드
    ├── bash-guard.sh            Bash 단일 hook (jq 토큰 파싱 + git commit 직접 호출 차단)
    ├── agy-review.sh            다운스트림 공통 Agy advisory review runner
    ├── validate-settings.sh     settings.json schema 검증
    ├── pre_commit_check.py      커밋 전 정적 검사 + staging 신호 감지 (dead link 증분, frontmatter relates-to 검증, S6 ≤5줄 skip)
    ├── downstream-readiness.sh  다운스트림 자가 진단 (silent fail 6항목)
    ├── docs_ops.py              docs/ 관리 (validate/move/reopen/cluster-update/verify-relates)
    ├── harness_version_bump.py  업스트림 버전 범프 제안 (is_starter 가드 내장)
    ├── task_groups.py           staged 파일을 WIP task × abbr × kind로 그룹화 (분리 판정)
    ├── split-commit.sh          커밋 분리 실행 (task_groups.py 기반)
    ├── install-starter-hooks.sh starter 전용 pre-commit hook 설치 (버전 범프 체크 포함)
    ├── tests/                   pytest 회귀 테스트
    │   ├── test_pre_commit.py
    │   ├── test_eval_harness.py
    │   └── test_session_start.py
    └── test-bash-guard.sh       Bash hook 회귀 테스트
scripts/                         유틸 스크립트 (하네스 외부)
└── install-secret-scan-hook.sh  pre-commit 시크릿 스캔 훅 설치 (gitleaks 우선, grep 폴백)
docs/
├── clusters/                    도메인별 인덱스 (진입점 SSOT — 문서 목록 + 관계 맵)
├── WIP/                         진행 중 (파일 있으면 할 일 있다)
├── decisions/                   결정과 그 근거 ("왜 X를 선택했나?")
├── guides/                      방법과 패턴 ("X를 어떻게 하나?")
├── incidents/                   문제와 해결 ("X가 왜 깨졌고 어떻게 고쳤나?")
├── harness/                     하네스 자체 변경 이력 + MIGRATIONS.md
└── archived/                    중단, 참조 불필요, 대체된 문서
```

## 워크플로우

### 신규 프로젝트

```
0a. h-setup.sh         하네스 파일 복사. 프로파일 선택(minimal/standard/full).
                     완료 시 .claude/HARNESS.json(is_starter=false)과 첫 WIP 작업 문서 생성.

0b. /harness-sync    (클론한 머신에서만, 한 번만) 의존성 설치 + 권한 설정 + git hook 설치.

1. /harness-init     PRD/아이디어 입력 → CPS 정리, 스택/강도 결정, 하네스 빈 칸 채움.
                     PRD 파일이 이미 있으면 초안을 제안하고, 사용자가 확인한 뒤 반영.
                     완료 시 도메인 목록·약어·등급 분류와 docs/guides/project_kickoff.md 갱신.

2. docs/WIP/ 확인    파일이 있으면 할 일이 있다.

3. /implementation   작업 시작 전 계획 문서 생성. CPS와 대조.
                     status: pending → in-progress.

4. 구현              코드 작성. 결정 사항과 메모를 계획 문서에 기록.

5. /commit           작업 잔여물 정리, 완료 문서 이동, staging 자동 단계화 review, 커밋+푸시.

6. 반복              docs/WIP/에 다음 작업이 남아있으면 3번으로.
```

### 기존 프로젝트 이식

```
0. h-setup.sh         하네스 파일 복사 (기존 파일은 건드리지 않음).

1. /harness-adopt    기존 .claude/, docs/ 병합. 문서 재분류 + 프론트매터 추가.
                     harness-upstream remote 설정. HARNESS.json에 adopted_at 기록.

2. /harness-init     CPS 정리 + 환경 빈 칸 채우기 (기존 프로젝트라도 필요).
                     adopt 없이 init 실행 시 차단됨.

3. bash .claude/scripts/downstream-readiness.sh
                     자가 진단. HARNESS.json·도메인 등급·is_starter·매처 누락 확인.

4. 이후 신규 프로젝트와 동일 흐름.
```

### 업그레이드

```
방법 1: remote 방식 (권장)
  /harness-upgrade       harness-upstream remote에서 fetch → 변경 분석 → 3-way merge.
                         한 명령으로 완료. Step 10에서 MIGRATIONS.md 수동 액션 안내.

방법 2: 파일 복사 방식 (remote 없을 때)
  h-setup.sh --upgrade   스타터에서 실행. 변경 파일을 .upgrade/에 스테이징.
  /harness-upgrade       스테이징된 파일을 대화형 병합.

업그레이드 후 검증:
  pytest .claude/scripts/tests/test_pre_commit.py
  bash .claude/scripts/test-bash-guard.sh   # 18/18 기대
  bash .claude/scripts/downstream-readiness.sh  # 0 누락 기대
```

**docs/WIP/가 비어있으면 할 일이 없다는 뜻이다.**

상태값: `pending` → `in-progress` → `completed` (커밋 시 이동) / `abandoned` (archived로 이동)

## 건강 검진 — /eval

하네스가 의도대로 작동하는지 주기적으로 점검한다.

```
/eval --quick     30초 헬스체크 (린터·WIP 잔여·dead link)
/eval --harness   문서 헬스체크 + CPS 무결성 + 레거시 정비 안내
```

`/eval --harness`는 다운스트림에서 특히 유용하다. `harness-upgrade` 후 실행하면
solution-ref 박제·Problem 인플레이션·CPS 인용 분포를 한 번에 확인할 수 있다.
제품 CPS와 하네스 운영 CPS가 같은 `project_kickoff.md`에 섞이면 P#/S# 의미가
충돌하므로, `## Problems`/`## Solutions` 표 형식을 canonical shape로 유지한다.

---

## CPS (Context / Problem / Solution)

모든 프로젝트 결정의 출발점. `harness-init`이 대화를 통해 구조화한다.

- **Context**: 배경, 제약, 프로젝트 중요도
- **Problem**: 해결해야 할 핵심 문제 1~3개
- **Solution**: 각 Problem에 대한 대응 방안 + 강제력 설계

CPS 문서는 `docs/guides/project_kickoff.md`에 저장된다. `docs/guides/project_kickoff_sample.md`에 예제가 포함되어 있으며, `harness-init` 실행 시 실제 내용으로 대체된다.

권장 canonical shape:

```markdown
## Problems

| ID | 1줄 요약 |
|----|---------|
| P1 | ... |

## Solutions

| ID | 대상 P# | 1줄 메커니즘 | 해결 기준 |
|----|---------|------------|----------|
| S1 | P1 | ... | ... |
```

다운스트림 제품 CPS에는 제품 문제와 제품 해결책만 남긴다. `MCP`, `review maxTurns`,
`bash-guard`, `harness-upgrade`, `pre-check`, `commit skill` 같은 하네스 운영
항목이 제품 Solution으로 섞이면 `/eval --harness` warning 신호로 본다.

`/implementation` 스킬은 작업 시작 전 CPS와 대조하여 방향성을 검증한다. init 미완료 시 차단된다.

## 문서 체계

모든 docs/ 문서는 YAML 프론트매터 필수 (`title`, `domain`, `status`, `created`).
`incidents/`는 `symptom-keywords` 추가 필수 (재발 검색용 고유명사).
문서 간 관계는 `relates-to` 필드로 명시. rel 타입 정의는 `.claude/rules/docs.md` "프론트매터 — wiki 그래프 모델" SSOT.

```
탐색 흐름: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

도메인 목록 SSOT: `.claude/rules/naming.md`.

폴더는 문서의 **성격** (왜/어떻게/무엇이 깨졌나), `domain`은 문서의 **의미**를 담당. 이중 분류.

`completed` 전환 차단 키워드: `TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`, `별도로`. `docs-ops.sh move`가 본문에서 자동 검사 (회고 섹션은 면제).

## Review 분기

`/commit` 호출 시 플래그로 review agent 호출 여부 결정.

| 플래그 | 동작 |
|--------|------|
| `/commit` (default) | review 안 함 — pre-check + 시크릿 게이트만 |
| `/commit --review` | review agent 1회 호출, diff별 한 줄 의견 |
| `/commit --no-review` | review 명시 스킵 |

시크릿 line-confirmed는 플래그 무관하게 review 강제 (보안 게이트).

다운스트림은 `naming.md`의 "도메인 등급" 섹션에 critical/normal/meta 분류 필요. 자세한 안내는 `docs/harness/MIGRATIONS.md`.

## 핵심 원칙

- **루트 인스트럭션은 소원 목록이다. Hooks는 법이다. Linter는 물리 법칙이다.**
- 린터가 잡을 수 있는 건 루트 인스트럭션에 쓰지 않는다.
- 추측으로 수정 시작 금지. 첫 행동은 관찰·재현·선행 사례 (`rules/no-speculation.md`).
- 외부 자료 전 내부(git log·docs·rules) 우선 (`rules/internal-first.md`).
- 하네스는 뜯어내기 쉬워야 한다 (rippable harness).
- "더 추가"가 아니라 "더 빼기" — 단순화 정신 (`docs/harness/hn_simplification.md`).

## 다운스트림 마이그레이션

`docs/harness/MIGRATIONS.md`에 버전별 자동/수동/검증/회귀 위험을 명세. `harness-upgrade` Step 10이 새 버전 섹션을 자동 표시.

**다운스트림 자가 진단:**
```bash
bash .claude/scripts/downstream-readiness.sh
```

`eval --harness`와 pre-check는 라이브 안내·스크립트의 하네스 경로 문자열을
path contract lint로 확인한다. `ruff`, `pyright`, `mypy`, `shellcheck`는 설치
상태를 관측 보고하며, 누락된 도구를 실행된 검증으로 간주하지 않는다.
silent fail 6항목 점검 (HARNESS·도메인 등급·매처·스킬 카테고리). 누락 1+ 시 exit 1.

## 다른 도구

현재 기본 pilot 조합은 Hermes + Codex + Agy이며, Claude는 optional runtime adapter로 취급한다. rules/의 마크다운 내용은 Cursor(`.cursor/rules/*.mdc`), Windsurf(`.windsurf/rules/*.md`) 등으로 포맷 변환하면 재사용 가능하다. Claude용 adapter는 `.claude/`, Codex용 adapter는 `.agents/`·`.codex/`, Hermes/Agy orchestration은 Hermes skill·cron·profile 쪽에서 통합 관리한다.

Agy advisory review는 `bash .claude/scripts/agy-review.sh "검토 질문"`로 호출한다. 기본값은 `AGY_PERMISSION_MODE=full`이며 runner가 `agy --dangerously-skip-permissions --add-dir <root> --print ...` 형태로 실행해 Agy가 판단에 필요한 프로젝트 파일을 직접 확인할 수 있게 한다. 권한 프롬프트를 유지해야 하는 환경만 `AGY_PERMISSION_MODE=prompt`로 낮춘다. Agy는 `~/.gemini/antigravity-cli`에 대화·cache·brain 상태를 쓰므로, Codex tool sandbox처럼 해당 디렉터리에 쓸 수 없는 환경에서는 runner가 실행을 중단하고 같은 프로젝트 root에서 로컬 터미널로 직접 실행할 명령을 안내한다. 로컬 실행 결과는 fallback handoff인 `.claude/memory/session-agy-review.md`에 저장되며, Codex는 이 파일을 읽어 같은 작업 흐름에 Agy 의견을 반영한다.

## 최근 주요 변경

최신 5개만 표기. 더 자세한 마이그레이션 가이드는 `docs/harness/MIGRATIONS.md`
(최신 5개 본문) + `docs/harness/MIGRATIONS-archive.md` (이전 누적). 전체
이력은 `git log --oneline --grep "(v0\."`.

### v0.55.0 (2026-06-02) — CPS+AC 학습 스킬 (minor)

`cps-learn` 스킬을 추가해 복수 P#를 문제 차원 증가로, 복수 S#를 실행 구조 증가로 해석하고 AC 단계화·반복·분리 검증과 specialist 호출 폭 판단을 학습 신호로 남긴다.

### v0.54.2 (2026-06-02) — downstream feedback visibility + bootstrap gate (patch)

신규 설치 HARNESS 정의 파일에 `is_starter=false`를 명시하고, 초기 placeholder가 HARNESS 생성 후 `/harness-init` 도메인 분류로 이어지도록 안내한다. Hermes guardian는 반복 Feedback Report에 상태 라벨을 붙이고, HARNESS 없는 registry 항목을 bootstrap owner-action으로 보고한다.

### v0.54.1 (2026-06-02) — typed AC + CPS agent learning loop (patch)

AC를 대표 Goal + typed AC로 분리하고, pre-check가 개별 P#/S# 추적성을 검사한다. implementation은 reverse/resume/interrupt CPS flow와 specialist CPS packet을 기록하며, cron/guardian report는 `memory-signal`로 재확인하게 했다.

### v0.54.0 (2026-05-30) — downstream 공통 Agy review runner (patch)

다운스트림에서 공통 Agy review runner를 사용할 수 있도록 하네스 문서와 마이그레이션 안내를 보강했다.

### v0.53.0 (2026-05-26) — 다중 runtime adapter 통합 관리 (patch)

하네스 기본 운영 전제를 Claude 중심에서 Hermes + Codex + Agy pilot stack으로 전환했다. `HARNESS.json`과 `h-setup.sh`가 `runtime_stack`/`runtime_adapters`를 기록·백필하고, `downstream-readiness.sh`가 이를 관측 신호로 출력한다. Claude는 호환성을 위해 유지하되 optional adapter로 분류한다.

### v0.52.9 (2026-05-25) — init gate UTF-8 출력 복구 + Python 요구사항 명시 (patch)

`check_init_done.sh`의 `${KICKOFF}` 변수 경계를 명시해 macOS/bash 조합에서 stderr 한글 출력이 깨지며 Python `text=True` 테스트가 실패하던 문제를 고쳤다. 또한 하네스 스크립트가 Python 3.10+ 문법을 사용한다는 요구사항을 README·루트 지침에 명시하고, GitHub license metadata 인식을 위해 `LICENSE` 파일을 추가했다.

### v0.52.8 (2026-05-22) — implementation WIP 실행 계획 soft warning (patch)

implementation WIP에 실행 단계와 단계별 산출물이 없으면 Step 3·5에서 soft warning으로 보완하도록 했다. AC 포맷은 다음 단계 진입 조건을 드러내도록 연결하되, 순수 결정문·조사문·사고 기록·write-doc 산출물은 예외로 둔다.

### v0.52.7 (2026-05-21) — commit review 기본값 정렬과 agy 수동 handoff reminder (patch)

commit review 호출 정책을 실제 commit 스킬 기본값과 맞췄다. 기본 `/commit`은 pre-check + 시크릿 게이트만 실행하고, review는 `/commit --review` 옵트인으로 명시한다. agy CLI 응답 자동 회수 실패 실측을 reminder로 남겨, Codex 명령어 작성 → 사용자 VS Code 터미널 직접 실행 → 답변 수동 전달 흐름을 기억하도록 했다.

### v0.52.6 (2026-05-21) — CPS 헤더형 추출 보강 + canonical shape 문서화 (patch)

StageLink 다운스트림 보고를 반영해 `eval --harness`가 `**P1 — ...**`, `### P5. ...`, `### S7. ... (P8)` 같은 헤더형 CPS를 문제/해결책 ID로 읽도록 보강했다. 제품 CPS와 하네스 CPS 혼합을 피하기 위해 표 형식 canonical shape도 README와 MIGRATIONS에 명시했다.

### v0.52.5 (2026-05-21) — path contract lint + 검증 도구 가용성 관측 (patch)

pre-check이 staged Python/Shell 문법을 직접 검사하고, eval/pre-check/downstream-readiness가 검증 도구 가용성과 라이브 하네스 경로 drift를 보고한다. 누락된 `ruff`, `pyright`, `mypy`, `shellcheck`는 조용한 통과가 아니라 환경 관측 신호로 남긴다.

### v0.52.4 (2026-05-21) — 루트 지침·mirror 경로 정합 복구 (patch)

CLAUDE/AGENTS에 reminder 생성 계약을 추가하고, `.claude`/`.agents` 스킬 mirror와 downstream-readiness의 낡은 hook·memory 경로 검사를 현재 Python hook과 `reminders/` 구조에 맞췄다.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)
- [Claude Code — Permission rule syntax](https://code.claude.com/docs/en/permissions) (matcher 패턴 함정 회피)

MIT License
