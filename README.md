# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. Claude Code 전용.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

현재 버전: **v0.28.7** — 0.x = 공개 API·동작 불안정·실험 단계. 다운스트림 실측 누적·매처 동작 검증·README 격차 안정화 후 1.0.0 검토. 변경 이력은 `git log --oneline --grep "(v0\."`, 다운스트림 마이그레이션은 `docs/harness/MIGRATIONS.md`.

## 빠른 시작

```bash
# 신규 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/h-setup.sh .

# Claude Code 실행 → harness-init으로 스택 결정
```

h-setup.sh는 멱등성 보장. 이미 있는 파일은 건드리지 않는다.

```bash
# (선택) pre-commit 시크릿 스캔 훅 설치
bash scripts/install-secret-scan-hook.sh
```

gitleaks가 있으면 `gitleaks protect --staged` 사용, 없으면 grep 폴백. grep 폴백은 best-effort — 리터럴 분할이나 Base64 우회는 탐지하지 못하므로 실제 방어가 중요하면 gitleaks 설치 필수.

```bash
# 기존 프로젝트에 하네스 이식
# → Claude Code에서 /harness-adopt → /harness-init 순서로 실행

# 하네스를 최신 버전으로 업그레이드
bash /path/to/harness-starter/h-setup.sh --upgrade /path/to/my-project
# → Claude Code에서 /harness-upgrade (git 3-way merge + MIGRATIONS.md 자동 안내)
```

## 구조

```
CLAUDE.md                        에이전트 루트 인스트럭션 (≤30줄)
.claude/
├── settings.json                hooks 정의 (단일 bash-guard.sh로 통합)
├── HARNESS.json                 하네스 메타 (버전, 프로파일, is_starter, installed_from_ref)
├── rules/                       자동 로드 규칙 (12개)
│   ├── self-verify.md           [상시] 작업 중 자기 검증 + pipeline-design 체크리스트 연계
│   ├── coding.md                [상시] 코딩 컨벤션 (플레이스홀더)
│   ├── naming.md                [paths] 네이밍 + 도메인 등급 + cluster 자동 매핑
│   ├── docs.md                  [상시] 문서 구조 + 프론트매터 + 탐색 규칙 + completed 차단 키워드
│   ├── memory.md                [상시] 메모리 활용 규칙 (실제 Claude vs 프로젝트 memory 경계)
│   ├── security.md              [상시] 시크릿 금지 + 4계층 방어
│   ├── internal-first.md        [상시] 외부 자료 전 내부 자료 우선 (git/docs/rules)
│   ├── no-speculation.md        [상시] 추측 수정 금지 — 첫 행동은 관찰·재현·선행 사례
│   ├── hooks.md                 [상시] PreToolUse argument-constraint 매처 금지
│   ├── external-experts.md      [온디맨드] 분야별 레퍼런스 인물 캐시 (researcher)
│   ├── pipeline-design.md       [if] 다단 처리 파이프라인 설계 7항목 체크리스트
│   └── staging.md               [상시] /commit review 자동 단계화 (5줄 룰 + 13신호)
├── skills/                      온디맨드 스킬 (13개, starter 전용 3개 포함)
│   ├── harness-init/            [starter] 프로젝트 초기화 (CPS + 스택 결정)
│   ├── harness-adopt/           [starter] 기존 프로젝트에 하네스 이식
│   ├── harness-dev/             [starter] 스크립트·스킬 추가 시 h-setup.sh·README·HARNESS.json 자동 갱신
│   ├── harness-sync/            클론 후 환경 동기화
│   ├── harness-upgrade/         하네스 업그레이드 (3-way merge + MIGRATIONS.md 안내)
│   ├── implementation/          작업 문서 라이프사이클
│   ├── commit/                  커밋 + Review (staging 자동 분기, starter push 보호)
│   ├── eval/                    건강 검진 (--quick/--harness/--surface/--deep)
│   ├── advisor/                 멀티 에이전트 판단 엔진 (specialist 풀 + 의사결정 프레임)
│   ├── check-existing/          기존 코드 중복 확인
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
                         한 명령으로 완료. Step 9.5에서 MIGRATIONS.md 수동 액션 안내.

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
문서 간 관계는 `relates-to` 필드로 명시 (6종: extends, caused-by, implements, supersedes, references, conflicts-with).

```
탐색 흐름: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

도메인 목록 SSOT: `.claude/rules/naming.md`.

폴더는 문서의 **성격** (왜/어떻게/무엇이 깨졌나), `domain`은 문서의 **의미**를 담당. 이중 분류.

`completed` 전환 차단 키워드: `TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`, `별도로`. `docs-ops.sh move`가 본문에서 자동 검사 (회고 섹션은 면제).

## Review 자동 단계화

`/commit` 호출 시 변경 성격에 따라 review 강도가 자동 결정된다 (`rules/staging.md` — v0.17.0부터 **5줄 룰** 경로 기반 이진 판정).

```
1. .claude/scripts|agents|hooks|settings.json  → deep
2. S1 line-confirmed OR S14 OR S8              → deep
3. S5 OR S4 단독                               → skip
4. 나머지                                      → standard
```

| Stage | 시간 | 적용 |
|-------|------|------|
| 0 (skip) | 0초 | 메타·lock 단독 |
| 1 (micro) | 15~25초 | `--quick` 명시 시만 (자동 판정에서는 사용 안 함) |
| 2 (standard) | 30~60초 | 일반 코드·문서·rules·skills (기본) |
| 3 (deep) | 90~180초 | 업스트림 위험 경로·시크릿 라인·DB 마이그레이션·export 변경 |

review 에이전트는 **계약·스코프 2축** 기본 검사 + **회귀 알파(S7·S8 hit 시만)**. 13개 신호별 알파는 발동 조건 충족 시에만 실행. 조기 중단 모든 stage 허용 (필수 단계 완료 후 의심점 없으면 종료). 수동 오버라이드: `--quick` / `--deep` / `--no-review`.

거대 커밋은 스코프를 나눠 작은 커밋 여러 개로 분리한다 (pre-check이 파일 30+ 또는 diff 1500줄+ 시 stderr 경고). 과거 `--bulk` 플래그·bulk 스테이지는 2026-04-22 폐기 (staging.md 참조).

다운스트림은 `naming.md`의 "도메인 등급" 섹션에 critical/normal/meta 분류 필요. 자세한 안내는 `docs/harness/MIGRATIONS.md`.

## 핵심 원칙

- **CLAUDE.md는 소원 목록이다. Hooks는 법이다. Linter는 물리 법칙이다.**
- 린터가 잡을 수 있는 건 CLAUDE.md에 쓰지 않는다.
- 추측으로 수정 시작 금지. 첫 행동은 관찰·재현·선행 사례 (`rules/no-speculation.md`).
- 외부 자료 전 내부(git log·docs·rules) 우선 (`rules/internal-first.md`).
- 하네스는 뜯어내기 쉬워야 한다 (rippable harness).
- "더 추가"가 아니라 "더 빼기" — 단순화 정신 (`docs/harness/harness_simplification_260419.md`).

## 다운스트림 마이그레이션

`docs/harness/MIGRATIONS.md`에 버전별 자동/수동/검증/회귀 위험을 명세. `harness-upgrade` Step 9.5가 새 버전 섹션을 자동 표시.

**다운스트림 자가 진단:**
```bash
bash .claude/scripts/downstream-readiness.sh
```
silent fail 6항목 점검 (HARNESS·도메인 등급·매처·스킬 카테고리). 누락 1+ 시 exit 1.

## 다른 도구

현재 Claude Code 전용. rules/의 마크다운 내용은 Cursor(`.cursor/rules/*.mdc`), Windsurf(`.windsurf/rules/*.md`) 등으로 포맷 변환하면 재사용 가능. skills/와 hooks는 Claude Code 고유 기능.

## 최근 주요 변경

자세한 마이그레이션 가이드는 `docs/harness/MIGRATIONS.md`. 전체 이력은 `git log --oneline --grep "(v0\."`.

### v0.28.5 (2026-05-01) — docs_ops·harness_version_bump·task_groups encoding="utf-8" 일괄 (G Phase 3) (patch)

`docs_ops.py git()`·`harness_version_bump.py run()`·`task_groups.py run()` 세 helper에 `encoding="utf-8"` 일괄 추가. Phase 1·2가 `pre_commit_check.py`의 갈래 1·2를 해소한 뒤, 같은 cp949 디코딩 결함이 다른 스크립트에 반복돼 있던 것을 정리. G 항목(Windows + 한글 환경 무한 막힘) 마지막 wave — Phase 1·2·3 모두 완료.

### v0.28.4 (2026-05-01) — pre_commit_check.py main 함수화 (G Phase 2 — script-as-module 결함) (patch)

580줄 module-level main 로직 → `def main() -> int:` + `if __name__ == "__main__": sys.exit(main())` 보호. ENOENT_PATTERNS만 module-level 유지 (test가 import). `from pre_commit_check import X` 시 staged 변경 유무 무관 sys.exit 없이 통과 — 다운스트림 발견 G 항목의 갈래 2(script-as-module 결함) 해소. `TestModuleImportSafe` 회귀 가드 1건 신규.

### v0.28.3 (2026-05-01) — pre_commit_check.py run() encoding="utf-8" (G Phase 1) (patch)

`run()`에 `encoding="utf-8"` + `or ""` 방어 추가. Windows + 한글 staged diff에서 system locale(cp949) 디코딩 실패로 `stdout=None` 되던 결함 해소. 다운스트림 발견 G 항목의 Phase 1 fix — Phase 2(main 함수화)는 별 commit. WIP `harness--hn_upstream_anomalies.md`에 B·C·D·E·F·G 미해결 누적 SSOT.

### v0.28.2 (2026-05-01) — pre-check 시크릿 line 면제 갭 + docs_ops untracked move 갭 (patch)

`pre_commit_check.py` `S1_LINE_EXEMPT`가 `^\.claude/scripts/`만 면제 → `.claude/agents/threat-analyst.md` 같은 패턴 SSOT 문서가 line-confirmed로 잘못 차단되던 false-positive 해소. `^\.claude/(scripts|agents|rules|skills|memory)/`로 확장. `docs_ops.py cmd_move` fallback이 untracked WIP에서 `git rm --cached` 실패로 매번 returncode 1 → `git ls-files --error-unmatch`로 src 인덱스 존재 여부 체크 후 시도. 회귀 테스트 2건 추가.

### v0.28.1 (2026-04-30) — completed 전환 차단 — 코드블록 안 빈 체크박스/TODO 면제 (patch)

`docs_ops.py _extract_body`가 ``` ``` ``·`~~~` 코드블록 안 라인을 차단 검사 대상에서 제외. AC 포맷 예시처럼 코드블록에 박힌 빈 체크박스가 진짜 미완료로 잡히던 문제. docs.md SSOT 동기화.

### v0.28.0 (2026-04-30) — 테스트 다이어트: AC 트리거 + marker + 다운스트림 격리 (minor)

자동 회귀 테스트의 매 커밋 무조건 실행 폐기. `test_pre_commit.py`에 5개 영역 marker(secret/gate/stage/enoent/docs_ops) 부여. AC `영향 범위:`에 `pytest -m <marker>` 표현이 있을 때만 실행. self-verify.md/harness-dev/implementation SKILL.md의 "테스트 무조건" 룰 제거. h-setup.sh에 `STARTER_ONLY_SCRIPTS`(`test_pre_commit.py`·`conftest.py`) 격리 — 신규 설치·upgrade 모두에서 다운스트림 미복사 + 기존 cleanup. 매 커밋 16초 → 0초(일상)/0.6초(AC 명시).

### v0.27.6 (2026-04-30) — completed 전환 차단 로직 정밀화 (단어 단독 매칭 → 명령형 패턴) (patch)

`docs_ops.py`의 BLOCK_ITEMS 정규식이 `후속`·`미결` 등 키워드 단독으로도 본문 불릿을 차단해 회고적 서술까지 잡던 문제 수정. TODO/FIXME 콜론 표기·빈 체크박스(`- [ ]`)·미결 섹션 헤더(`## 후속`)만 차단. `docs.md` SSOT 동기화.

### v0.27.5 (2026-04-30) — pre_commit_check task 단위 AC scope + review diff 조건 명시 (patch)

`pre_commit_check.py`가 staged WIP 파일 전체를 스캔해 다른 task의 `영향 범위:` 항목까지 잡던 버그 수정. `task_groups.py`에 `parse_wip_tasks()` 신설 — task 단위 `{kind, impact_files, has_impact_scope}` 반환. staged 파일을 task의 `impact_files`에 매칭한 뒤 그 task 정보만 사용. `review.md` 라인 72에 diff 실행 조건 3개 명시 + 도구 선택 표 재배치(AC 충족 첫 행, diff 마지막 조건부).

### v0.26.9 (2026-04-28) — harness-upgrade 커밋 분기 + MIGRATIONS 변경 파일 섹션 (patch)

harness-upgrade Step 10에 커밋 분기 추가: 충돌 해소 파일 없으면 `HARNESS_UPGRADE=1`로 review skip, 있으면 해당 파일만 `--quick` review. Step 3에서 MIGRATIONS.md `### 변경 파일` 표를 git diff보다 우선 참조. MIGRATIONS 포맷에 변경 파일 섹션 추가.

### v0.26.8 (2026-04-28) — commit Step 4 다운스트림 skip 명시 (patch)

commit Step 4에서 `HARNESS.json`의 `is_starter` 값을 먼저 확인해 `false`(다운스트림)이면 Step 전체를 건너뛰도록 명시. 기존에는 스크립트 내부적으로 exit했지만 Step 자체는 실행됐음.

### v0.20.13 (2026-04-23) — docs-ops cluster-update 성능 수정

`docs-ops.sh cluster-update`에서 `extract_abbrs()`가 파일마다 반복 호출(337파일 × 17약어 = 5,729회)되던 문제 수정. `detect_abbr()`에 `ABBR_PATTERN` 환경변수 캐시 인터페이스 추가, `cmd_cluster_update()`에서 루프 전 1회 계산 후 주입. 다운스트림 대용량 환경에서 수 분 지연 → 수 초로. incident: `docs/incidents/hn_docs_ops_cluster_update_perf.md`.

### v0.26.5 (2026-04-28) — hook 버전 체크 제거 + pre-check 경고로 이전 (patch)

hook의 버전 범프 차단 로직 제거. 버전 판단은 commit Step 4(Claude)가 담당. pre_commit_check.py에 미범프 경고 추가(차단 아님).

### v0.26.4 (2026-04-28) — commit Step 4 버전 범프 연동 갱신 통합 (patch)

commit Step 4에서 버전 범프 확정 후 HARNESS.json·MIGRATIONS.md·README.md를 한 번에 처리하도록 통합. 기존 4단계 분산 → 1단계.

### v0.26.3 (2026-04-28) — harness-upgrade MIGRATIONS.md 분류 버그 수정 (patch)

harness-upgrade Step 3에서 `docs/harness/MIGRATIONS.md`가 `docs/harness/*` 사용자 전용 패턴에 묻혀 업그레이드 시 건너뛰는 버그 수정 — 자동 덮어쓰기 카테고리에 명시적 등록. Step 9.5 단순화(단일 섹션 구조 대응). Step 9.7 신설 — 미완료 수동 액션 잔존 시 완료 처리 차단.

### v0.26.2 (2026-04-28) — 검증 파이프라인 강화 + MIGRATIONS.md 구조 재설계 (patch)

MIGRATIONS.md 현재 버전 1개만 유지 구조로 재설계 — 히스토리는 upstream git log가 SSOT. `docs/harness/migration-log.md` 경로 확정(구 루트 오류 수정). harness-upgrade Step 10에 업그레이드 완료 후 해당 버전 섹션 삭제 추가. commit Step 4에 버전 범프 후 MIGRATIONS.md 섹션 자동 작성 절차 추가. implementation Step 2.5 AC 검증 필수화(자동화 가능/불가 구분·실행 기록 의무). implementation Step 4 CPS 갱신 없음도 명시 의무화. docs_ops.py cmd_move 미추적 파일 FileNotFoundError 버그 수정.

### v0.26.1 (2026-04-28) — starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정 (patch)

harness-init·adopt 완료 시 자기 자신 삭제(`rm -rf .claude/skills/harness-*`). harness-upgrade Step 10에 `starter_skills` 키 동기화 추가 — 구버전 다운스트림 폴백 `"harness-init,harness-adopt"` 하드코딩. MIGRATIONS.md v0.26 문서 오류 수정(잘못된 자동 적용 항목 제거, 수동 삭제 안내 강도 조정).

### v0.26.0 (2026-04-28) — MIGRATIONS 시스템 재설계 + starter_skills 경계 정비 (minor)

MIGRATIONS.md 기록물 → 지시 문서 재설계. migration-log.md 신설(다운스트림 기록용). `starter_skills` 경계 정비: harness-dev 제거, harness-sync skills 등록. harness-upgrade Step 8 `permissions.allow` 동기화 로직 추가. h-setup.sh 신규 설치 경로 starter_skills 필터 추가.

### v0.25.0 (2026-04-28) — harness-dev 스킬 신설 + starter_skills 필드 (minor)

starter 개발 전용 스킬 `harness-dev` 신설. `HARNESS.json`에 `starter_skills` 필드 추가 — 다운스트림에 전달하지 않을 스킬 목록.

### v0.24.0 (2026-04-28) — install-starter-hooks.sh 신설 + hooks.md 적용 범위 명확화 (minor)

pre-commit 버전 범프 hook 설치 스크립트 신설. `hooks.md` "적용 범위" 섹션 추가 — `permissions.allow`의 `Bash(...)` 패턴은 허용 목록이라 hooks.md 금지 규칙 적용 대상 아님을 명확화.

### v0.23.0 (2026-04-28) — debug-specialist 강화 + split 자동 stage + 버전 체크 이동 (minor)

debug-specialist 에이전트 연속 fix 자동 감지 추가. split 커밋 split-plan.txt 기반 자동 stage(그룹 2·3 수동 stage 버그 수정). 버전 체크 스테이징 이후로 이동(`--no-review` 시 누락 수정 포함). task_groups.py abbr→char 성격 분류 + pre-check split 조건 교체.

### v0.20.12 (2026-04-23) — prior_session_files 신호 추가

다운스트림 실측 보고 대응: 이전 세션 잔여 파일이 staged에 섞이는 false-negative 갭 보강. `session-start.sh`가 SessionStart 시점 unstaged 목록을 `session-start-unstaged.txt`에 저장, `pre-commit-check.sh`가 staged 교집합을 `prior_session_files` 신호로 출력. 자동 분리 아님 — commit Step 1에서 사용자 1줄 환기만. split 자동화 #18 판정(false-positive 방지) 유지.

### v0.20.11 (2026-04-23) — 커밋 프로세스 감사 판정 완료 (patch)

#13·#16·#17·#18 판정 완료. harness-init/adopt/upgrade 세션 파일명 단일 파일 + 변경 이력 방식 확정(#16) — 날짜 suffix 생성 경로 전부 제거. split 알고리즘 현 구조 유지 판정(#18) — 자동 완전 분리 마찰 > 편익.

### v0.20.0 (2026-04-22) — 커밋 프로세스 감사 P2 (minor)

docs-manager 스킬(332줄) 폐기 → `docs-ops.sh` 5 서브커맨드(validate/move/reopen/cluster-update/verify-relates)로 대체. `harness-version-bump.sh` 신설 — commit Step 3가 한 줄 호출로. bash-guard에 검증 4 신설 — `git commit` 직접 호출 차단(`HARNESS_DEV=1` prefix 필수 — v0.20.5부터 단일화, G1~G5 5케이스). pre-check S6 단독 + ≤5줄 → skip 자동화(T37 3케이스). 다운스트림 호환성 변화 — MIGRATIONS v0.20.0 수동 액션 필수.

### v0.19.0 (2026-04-22) — 커밋 프로세스 감사 P0+P1 (minor)

10개 항목 일괄 반영. **light/strict 모드 폐기** — 하네스 강도 필드 제거, `--light`·`--strict` 플래그 제거. staging 자동 판정 + `--quick`/`--deep`/`--no-review`로 단일화. pre-check 검사 C(`relates-to.path` dead link) + T36 6케이스. Step 0 린트 + `--lint-only` 제거. 메타 본문 박기 섹션 삭제. test-strategist 에이전트 폐기. session 캐시 3→1, tree-hash 캐싱 폐기. 다운스트림 호환성 변화 — MIGRATIONS v0.19.0 수동 액션 필수.

### v0.18.8 (2026-04-22) — 업스트림 전용 로직 감사 Top 3 정리

codebase-analyst 실측(12파일) 결과 오염 1건·조건부 3건·정당 8건. `pre-commit-check.sh`에 `IS_STARTER` 변수 도입, S10 반복 면제 regex·S5 메타 awk 매칭 조건부화 — `docs/harness/promotion-log.md`가 다운스트림에서는 doc으로 분류됨. commit Step 3 자연어 조건을 실행 가능한 `grep` 판정으로 교체. `naming.md` 경로 매핑 섹션을 "업스트림 기본값: 생략. 다운스트림 권장"으로 교체.

### v0.18.7 (2026-04-22) — 스킬 파일명 규약 드리프트 정리

naming.md "날짜 suffix 전면 금지"가 6개 스킬 예시·템플릿에 반영 안 됨. `{대상폴더}--{작업내용}_{YYMMDD}.md` → `{대상폴더}--{abbr}_{slug}.md` + 날짜 suffix 금지 명시 + naming.md 참조. 예시 날짜(260330·260416) → slug 이름(`hn_auth_stack` 등)으로 교체.

### v0.18.6 (2026-04-22) — dead link 검사 pre-check 이식

v0.18.5 review deep이 30초 걸려 잡은 cluster dead link를 pre-check이 수 초에 잡는다. `pre-commit-check.sh` Step 3.5 신설: 삭제·rename된 md를 가리키는 기존 링크 감지(basename grep) + 추가·수정된 md의 새 링크 대상 존재 검증(staged diff + 라인 awk). T35 3케이스. 원칙: 정적 정합성은 pre-check, 의미는 review.

### v0.18.5 (2026-04-22) — SSOT 선행 탐색 3층 방어 구조화

v0.18.4 직후 중복 WIP 즉흥 생성 재발 → 3층 방어 정렬. (1) `CLAUDE.md` `<important if>` 블록 — 경로 불문 트리거. (2) `.claude/rules/docs.md` "SSOT 우선 + 분리 판단" 섹션 — 3단계 탐색(cluster 스캔 → 키워드 grep → 후보 Read) + 실패 모드 체크리스트 + "기본값은 기존 SSOT 갱신" 명문화. (3) `write-doc`/`implementation` 스킬은 docs.md 참조·트리거만 담당.

### v0.18.4 (2026-04-22) — 린터 ENOENT 패턴 정교화 (오탐·OS 커버리지 fix)

다운스트림 review가 v0.18.3의 MIGRATIONS 단정을 역으로 검증해 오탐·갭 지적. ESLint crash와 겹치는 3패턴 제거(`No such file or directory`·`Cannot find module`·`ENOENT`), OS 커버리지 5개 추가(zsh·Alpine·Dash·pnpm). T33·T34 회귀 테스트(12 케이스) 신설 — 패턴 SSOT는 ENOENT_PATTERN 변수로 동기화. no-speculation.md에 "MIGRATIONS 작성 원칙" 추가.

### v0.18.3 (2026-04-22) — 린터 도구 실종 구분 (T13.1 원인 확정)

다운스트림 `TEST_DEBUG=1` dump로 진짜 원인 확정: `npm run lint`가 ENOENT로 exit 2 (node_modules 누락). pre-commit-check.sh 린터 단계에 **B-3 fix** — 도구 실종은 warn + skip, rule 위반은 차단. incident 전면 재작성(진짜 원인·교훈 본문화, status: completed).

### v0.18.2 (2026-04-22) — T13 재진단 훅 (철회된 중간 단계)

v0.18.1 fix로 T13.1 미해결 → 가설 철회·TEST_DEBUG=1 옵트인 훅 추가. v0.18.3에서 원인 확정으로 결론. TEST_DEBUG 훅은 범용 진단 도구로 유지.

### v0.18.1 (2026-04-22) — T13 테스트 격리 fix (잘못된 가설, 부분 유지)

파일명을 PID + 에포크로 unique화. 최초 "git log 교차 = 원인" 가설은 철회됐지만 경로 교차 리스크 봉쇄라는 별건 가치로 유지.

### v0.18.0 (2026-04-21) — pipeline-design 규칙 업스트림 이식

다단 처리 파이프라인(ETL·ML·에이전트 체인·빌드) 설계·재편 시 **상류 신호 재사용**과 **하류 보존 책임**을 7항목 체크리스트로 강제. 다운스트림에서 한 달간 draft1→2→3 재편에도 발견되지 못한 "상류 출력 암묵적 폐기" 패턴을 방지.

- `.claude/rules/pipeline-design.md` 신규 — 7항목 체크리스트 + 4 금지 패턴
- CLAUDE.md `<important if>` 트리거, `rules/self-verify.md` 연계
- review 자동 감지는 **미도입** (의도 설계 문제는 diff 키워드 매칭 어려움)

### v0.17.1 (2026-04-21) — review tool call 예산 재설계

"3관점(회귀·계약·스코프)" → **"계약·스코프 2축 + 회귀 알파(S7·S8 hit 시만)"** 재구성. 실측 warn 6건 축 분포 기반 (계약 50%, 스코프 33%, 회귀 0%).

- 신호 매핑에 **알파 발동 조건** 열 추가 — 고정 tool 매핑 폐기
- **조기 중단 모든 stage 허용** — 필수 단계 완료 후 의심점 없으면 종료
- maxTurns 6 유지 + 5회 이후 여유 1회 보존, verdict 출력 의무 재강조

### v0.17.0 (2026-04-21) — staging 5줄 룰 (경로 기반 이진 판정)

기존 16줄 Stage 결정 룰을 **경로 기반 5줄**로 전면 대체. 업스트림 실측 52커밋 중 deep 42% / standard 0% 편향 해소 (deep 22건 중 41%가 과잉).

- 핵심: `.claude/scripts|agents|hooks|settings.json` 건드림 → deep
- 다중 도메인 격상(룰 A) 폐기 — 5줄 룰이 커버
- 회귀 테스트 T21~T32 (12 케이스) + clone 시 로컬 스크립트 cp 보정

### v0.16.1 (2026-04-20) — `/commit --bulk` 플래그 (2026-04-22 폐기)

거대 일괄 변경 시 review 대신 정량 가드 4종으로 대체하는 플래그였으나, 2026-04-22 설계 오류로 판단하고 폐기. 가드 4종 중 거대 커밋 특유 위험을 잡는 건 dead link 하나뿐이었고 그건 pre-check Step 3.5(v0.18.6)에 이식됨. 거대 커밋은 스코프 분리가 답.

### v0.16.0 (2026-04-20) — 문서 네이밍 전면 개편

파일명 `{abbr}_{slug}.md` 통일 + 도메인 약어 SSOT(naming.md) + **날짜 suffix 전면 폐기**(incidents 포함) + cluster 자동 매핑 직교 파싱 규칙. 탐색 체인: 파일명 → 도메인 → cluster가 grep/ls만으로 완료.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)
- [Claude Code — Permission rule syntax](https://code.claude.com/docs/en/permissions) (matcher 패턴 함정 회피)

MIT License
