# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. Claude Code 본체를 보존하고 Codex bridge를 함께 제공.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

현재 버전: **v0.50.0** — 0.x = 공개 API·동작 불안정·실험 단계. 다운스트림 실측 누적·매처 동작 검증·README 격차 안정화 후 1.0.0 검토. 변경 이력은 `git log --oneline --grep "(v0\."`, 다운스트림 마이그레이션은 `docs/harness/MIGRATIONS.md`.

## 빠른 시작

```bash
# 신규 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/h-setup.sh .

# Claude Code 또는 Codex 실행 → harness-init으로 스택 결정
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
# → Claude Code 또는 Codex에서 /harness-adopt → /harness-init 순서로 실행

# 하네스를 최신 버전으로 업그레이드
bash /path/to/harness-starter/h-setup.sh --upgrade /path/to/my-project
# → Claude Code 또는 Codex에서 /harness-upgrade (git 3-way merge + MIGRATIONS.md 자동 안내)
```

## 구조

```
CLAUDE.md                        Claude Code 루트 인스트럭션
AGENTS.md                        Codex 루트 인스트럭션
.agents/
└── skills/                      Codex가 직접 읽는 스킬 mirror
.codex/
├── agents/                      Codex agent bridge (TOML)
└── hooks.json                   Codex hook bridge
.claude/
├── settings.json                hook source mirror (단일 bash-guard.sh로 통합)
├── HARNESS.json                 하네스 메타 (버전, 프로파일, is_starter, installed_from_ref)
├── rules/                       자동 로드 규칙 (9개)
│   ├── self-verify.md           [상시] 작업 중 자기 검증 (AC 트리거 매트릭스)
│   ├── coding.md                [상시] 코딩 컨벤션 (Surgical Changes)
│   ├── naming.md                [paths] 네이밍 + 도메인 등급 + cluster 자동 매핑
│   ├── docs.md                  [상시] 문서 구조 + 프론트매터 + 탐색 규칙 + completed 차단 키워드
│   ├── memory.md                [상시] 메모리 활용 규칙 (에이전트 memory vs 프로젝트 memory 경계)
│   ├── security.md              [상시] 시크릿 금지 + 4계층 방어
│   ├── internal-first.md        [상시] 외부 자료 전 내부 자료 우선 (git/docs/rules)
│   ├── no-speculation.md        [상시] 추측 수정 금지 — 첫 행동은 관찰·재현·선행 사례
│   └── hooks.md                 [상시] PreToolUse argument-constraint 매처 금지
├── skills/                      스킬 source mirror (12개, starter 전용 3개 포함)
│   ├── harness-init/            [starter] 프로젝트 초기화 (CPS + 스택 결정)
│   ├── harness-adopt/           [starter] 기존 프로젝트에 하네스 이식
│   ├── harness-dev/             [starter] 스크립트·스킬 추가 시 h-setup.sh·README·HARNESS.json 자동 갱신
│   ├── harness-sync/            클론 후 환경 동기화
│   ├── harness-upgrade/         하네스 업그레이드 (3-way merge + MIGRATIONS.md 안내)
│   ├── implementation/          작업 문서 라이프사이클
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
└── scripts/                     hook 스크립트 + 회귀 테스트 (15개)
    ├── session-start.sh         SessionStart hook
    ├── stop-guard.sh            Stop hook
    ├── post-compact-guard.sh    PostCompact hook
    ├── auto-format.sh           PostToolUse 포매터
    ├── write-guard.sh           Write 가드
    ├── bash-guard.sh            Bash 단일 hook (jq 토큰 파싱 + git commit 직접 호출 차단)
    ├── validate-settings.sh     settings.json schema 검증
    ├── pre_commit_check.py      커밋 전 정적 검사 + staging 신호 감지 (dead link 증분, frontmatter relates-to 검증, S6 ≤5줄 skip)
    ├── downstream-readiness.sh  다운스트림 자가 진단 (silent fail 6항목)
    ├── docs_ops.py              docs/ 관리 (validate/move/reopen/cluster-update/verify-relates)
    ├── harness_version_bump.py  업스트림 버전 범프 제안 (is_starter 가드 내장)
    ├── task_groups.py           staged 파일을 WIP task × abbr × kind로 그룹화 (분리 판정)
    ├── split-commit.sh          커밋 분리 실행 (task_groups.py 기반)
    ├── install-starter-hooks.sh starter 전용 pre-commit hook 설치 (버전 범프 체크 포함)
    ├── test_pre_commit.py       회귀 테스트 (51 케이스, pytest — 단위+통합)
    └── test-bash-guard.sh       회귀 테스트 (18 케이스, 강제 경유 G1~G5 포함)
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
                     완료 시 docs/WIP/harness_init_pending.md 생성.

0b. /harness-sync    (클론한 머신에서만, 한 번만) 의존성 설치 + 권한 설정 + git hook 설치.

1. /harness-init     PRD/아이디어 입력 → CPS 정리, 스택/강도 결정, 하네스 빈 칸 채움.
                     완료 시 docs/WIP/project_kickoff.md + 첫 작업 문서 생성.

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
                     자가 진단. 도메인 등급·is_starter·매처 누락 6항목 확인.

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
  pytest .claude/scripts/test_pre_commit.py  # 51/51 기대
  bash .claude/scripts/test-bash-guard.sh   # 18/18 기대
  bash .claude/scripts/downstream-readiness.sh  # 0 누락 기대
```

**docs/WIP/가 비어있으면 할 일이 없다는 뜻이다.**

상태값: `pending` → `in-progress` → `completed` (커밋 시 이동) / `abandoned` (archived로 이동)

## 건강 검진 — /eval

하네스가 의도대로 작동하는지 주기적으로 점검한다.

```
/eval --quick     30초 헬스체크 (린터·WIP 잔여·dead link)
/eval --harness   하네스 문서 품질 + CPS 무결성 + 레거시 정비 안내 (doc-health 흡수)
```

`/eval --harness`는 다운스트림에서 특히 유용하다. `harness-upgrade` 후 실행하면
solution-ref 박제·Problem 인플레이션·CPS 인용 분포를 한 번에 확인할 수 있다.

---

## CPS (Context / Problem / Solution)

모든 프로젝트 결정의 출발점. `harness-init`이 대화를 통해 구조화한다.

- **Context**: 배경, 제약, 프로젝트 중요도
- **Problem**: 해결해야 할 핵심 문제 1~3개
- **Solution**: 각 Problem에 대한 대응 방안 + 강제력 설계

CPS 문서는 `docs/guides/project_kickoff.md`에 저장된다. `docs/guides/project_kickoff_sample.md`에 예제가 포함되어 있으며, `harness-init` 실행 시 실제 내용으로 대체된다.

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
- "더 추가"가 아니라 "더 빼기" — 단순화 정신 (`docs/harness/harness_simplification_260419.md`).

## 다운스트림 마이그레이션

`docs/harness/MIGRATIONS.md`에 버전별 자동/수동/검증/회귀 위험을 명세. `harness-upgrade` Step 10이 새 버전 섹션을 자동 표시.

**다운스트림 자가 진단:**
```bash
bash .claude/scripts/downstream-readiness.sh
```
silent fail 6항목 점검 (HARNESS·도메인 등급·매처·스킬 카테고리). 누락 1+ 시 exit 1.

## 다른 도구

현재 Claude Code 본체 + Codex bridge 제공. rules/의 마크다운 내용은 Cursor(`.cursor/rules/*.mdc`), Windsurf(`.windsurf/rules/*.md`) 등으로 포맷 변환하면 재사용 가능. Claude용 skills/hooks는 `.claude/`, Codex용 bridge는 `.agents/`·`.codex/`에 둔다.

## 최근 주요 변경

최신 5개만 표기. 더 자세한 마이그레이션 가이드는 `docs/harness/MIGRATIONS.md`
(최신 5개 본문) + `docs/harness/MIGRATIONS-archive.md` (이전 누적). 전체
이력은 `git log --oneline --grep "(v0\."`.

### v0.50.0 (2026-05-17) — code-ssot 규칙 신설 (동형 SSOT 패턴 starter 흡수) (minor)

다운스트림이 필드 lifecycle drift incident 4건 누적 후 자체 작성하던 "코드 SSOT 단일화 규칙"을 starter가 일반 원칙으로 흡수. 다른 다운스트림이 같은 학습 곡선을 독립 재발견하는 비용 차단. **`.claude/rules/code-ssot.md` 신설** (defends: P11) — 3개 원칙: 3+ reference rule(같은 로직 3곳 이상 → core 모듈 추출), Derived pointer pattern(Record/배열 "현재 대표값" 파생은 단일 함수), New field pre-checklist(소유 모듈·단일 함수·모든 진입점 통과·추출/매칭/처리 통합 4개 결정 없이 새 필드 추가 금지). **Surgical Changes 충돌 해소 룰** 본문 명시(발견 = 즉시 추출 아님, 발견 = 박제 + 다음 wave 의무). **`project_kickoff.md`** Problems 표 P11 행 추가, Solutions 표 S11 행 추가, P11 본문에 field lifecycle 예시(normalization·derivation·persistence entry points) 보강. 3엔진(advisor·Gemini·Codex) 만장일치 — coding.md 흡수 거부(판단 타이밍 다름), 신규 P# 신설 안 함, 다운스트림 사례명은 starter 본문 비포함(`rel: references`로 연결). 결정: `docs/decisions/hn_code_ssot_rule.md`.

### v0.49.0 (2026-05-17) — Codex 안전 조회/검증 dispatcher 신설 (minor)

Codex CLI의 untrusted 기본 정책이 `rg`·`git status`·`docs_ops.py` 조회마다 명시 승인을 요구해 문서 작성·검토 흐름이 끊기는 문제 해소. **`.claude/scripts/safe_command.py` 신설** — read-only/검증 dispatcher. 좁은 prefix 하나(`python .claude/scripts/safe_command.py <cmd>`)만 지속 승인하면 14개 안전 명령(`status`·`diff`·`log`·`show`·`rg`·`read`·`docs-list`·`docs-show`·`docs-validate`·`cps-list`·`cps-show`·`cps-stats`·`verify-relates`·`precheck`) 모두 커버. 화이트리스트 + workspace 경로 격리 + `--ext-diff`·`--pre` blocklist 3중 방어. **`AGENTS.md`**에 "Codex 안전 조회/검증" 섹션 추가. 쓰기·삭제·커밋·푸시·hook 변경·네트워크·의존성 설치는 의도적 제외 — 계속 명시 승인. `.codex/hooks.json`은 빈 상태 유지(신규 hook 0건). dispatcher 위치는 호출 대상(`docs_ops.py`·`pre_commit_check.py`)과 같은 `.claude/scripts/` — 런타임 중립이라 Claude 워크플로에서도 사용 가능. 결정 문서: `docs/WIP/hn_codex_approval_policy.md` (위험도 3분류 + Codex CLI 명령별 allowlist 스키마 미확인으로 `.codex/config.toml` 보류).

### v0.48.1 (2026-05-17) — SSOT 인용 원칙 메커니즘 활성화 (patch)

v0.48.0이 박은 "SSOT 인용 원칙"의 실제 작동 메커니즘 활성화. **verify-relates 스코프 확장**: `docs/` 폴더만 검사 → `docs/` + `.claude/rules`·`.claude/skills`·`.claude/agents` + `README.md` + `CLAUDE.md`. 경로 해석 보강 — `rules/X.md`·`skills/X.md` 단축 경로 자동 변환. **pre-check 통합 + is_starter 분기**: starter는 깨진 references `❌` 차단, 다운스트림은 `⚠` warn-only. `docs_ops` 마커 31 passed. CPS `rel: references` 그래프가 실제로 cascade 추적 가능 — wiki 그래프 일원화된 `.claude/` 노드까지 검사. SSOT 이동·이름 변경 시 자동 검출 — drift 방지.

### v0.48.0 (2026-05-17) — P11 본질 재정렬 (SSOT 인용 원칙 + CPS 채널 활성화) (minor)

v0.47.7~v0.47.12 P11 사이클이 `_DEAD_REF_PATTERNS` hardcoded list 누적으로 빠지려던 순간 본 메커니즘 본질로 복귀. 사용자 통찰: "SSOT 호출과 더불어 그 내용이 희석되지 않고 내가 원하는 단계까지 전달이 안된다가 문제의 핵심". **문제 진단**: 본문이 SSOT 구체 list(`4종 (X·Y·Z·W)`·`4모드`)를 복제 → SSOT 갱신 시 본문 drift → P11 잠복. **해결**: 새 메커니즘 X, CPS 채널 활성화 — `rules/docs.md` "SSOT 인용 원칙" 박제(본문 복제 금지, `rel: references` frontmatter 박제). 본문 표현 단속 폐기(`_DEAD_REF_PATTERNS` hardcoded 답습 회피) — 원칙 박제로 자율 정비. 본 wave의 cascade 추적 메커니즘 활성화는 v0.48.1에서 보강.

### v0.47.12 (2026-05-16) — AC 헤더 차단 메시지에 auto-fix sed 안내 추가 (patch)

다운스트림 보고: §S-9 AC 헤더 정규식 차단 시 사용자가 매번 수동 헤더 정정. **개선**: pre-check이 AC 헤더 정규식 위반 감지 시 차단 메시지에 결정적 `sed` 1줄 auto-fix 안내 출력. 사용자 명령 복사 → 즉시 정정. tag-normalize(v0.47.6) 패턴 답습 — 결정적 변환 안내로 마찰 감소.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)
- [Claude Code — Permission rule syntax](https://code.claude.com/docs/en/permissions) (matcher 패턴 함정 회피)

MIT License


