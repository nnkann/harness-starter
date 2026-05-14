# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. Claude Code 전용.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

현재 버전: **v0.47.2** — 0.x = 공개 API·동작 불안정·실험 단계. 다운스트림 실측 누적·매처 동작 검증·README 격차 안정화 후 1.0.0 검토. 변경 이력은 `git log --oneline --grep "(v0\."`, 다운스트림 마이그레이션은 `docs/harness/MIGRATIONS.md`.

## 빠른 시작

```bash
# 신규 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/h-setup.sh .

# Claude Code 실행 → harness-init으로 스택 결정
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
├── skills/                      온디맨드 스킬 (14개, starter 전용 3개 포함)
│   ├── harness-init/            [starter] 프로젝트 초기화 (CPS + 스택 결정)
│   ├── harness-adopt/           [starter] 기존 프로젝트에 하네스 이식
│   ├── harness-dev/             [starter] 스크립트·스킬 추가 시 h-setup.sh·README·HARNESS.json 자동 갱신
│   ├── harness-sync/            클론 후 환경 동기화
│   ├── harness-upgrade/         하네스 업그레이드 (3-way merge + MIGRATIONS.md 안내)
│   ├── implementation/          작업 문서 라이프사이클
│   ├── commit/                  커밋 + Review (staging 자동 분기, starter push 보호)
│   ├── eval/                    건강 검진 (--quick/--harness/--surface/--deep)
│   ├── doc-health/              레거시 문서 정비 (abbr rename·CPS frontmatter·archived 이동 반자동화)
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

## 건강 검진 — /eval

하네스가 의도대로 작동하는지 주기적으로 점검한다.

```
/eval --quick     30초 헬스체크 (린터·WIP 잔여·dead link)
/eval --harness   CPS 무결성 전수 검사 (박제 인용·Problem 인플레이션·Solution 인용 분포)
/eval --surface   암묵지 발견 (규칙과 실제 코드 갭)
/eval --deep      전방위 감사 (시크릿·archive 강제 점검·4관점 병렬 에이전트)
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
문서 간 관계는 `relates-to` 필드로 명시 (6종: extends, caused-by, implements, supersedes, references, conflicts-with).

```
탐색 흐름: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

도메인 목록 SSOT: `.claude/rules/naming.md`.

폴더는 문서의 **성격** (왜/어떻게/무엇이 깨졌나), `domain`은 문서의 **의미**를 담당. 이중 분류.

`completed` 전환 차단 키워드: `TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`, `별도로`. `docs-ops.sh move`가 본문에서 자동 검사 (회고 섹션은 면제).

## Review 자동 단계화

`/commit` 호출 시 WIP AC `검증.review` 선언 값으로 review 강도가 자동 결정된다 (`rules/staging.md`).

| Stage | 시간 | `검증.review` 값 |
|-------|------|-----------------|
| 0 (skip) | 0초 | `skip` |
| 1 (micro) | 15~25초 | `self` |
| 2 (standard) | 30~60초 | `review` |
| 3 (deep) | 90~180초 | `review-deep` |

시크릿 line-confirmed는 AC 선언 무관하게 deep 강제. 수동 오버라이드: `--quick` / `--deep` / `--no-review`.

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

최신 5개만 표기. 더 자세한 마이그레이션 가이드는 `docs/harness/MIGRATIONS.md`
(최신 5개 본문) + `docs/harness/MIGRATIONS-archive.md` (이전 누적). 전체
이력은 `git log --oneline --grep "(v0\."`.

### v0.47.2 (2026-05-15) — harness-upgrade Step 7 격하 감지 + 클린 패치 안내 (patch)

73% 삭감 wave 후속 patch — v0.47.1 격하·폐기 잔재 자동 클린업 메커니즘 신설. harness-upgrade Step 7에 (B) starter_skills 격하 감지 추가 (기존 (A) DELETED 카테고리와 통합). upstream `HARNESS.json.starter_skills` 등록 폴더가 다운스트림 디스크에 있으면 격하 잔재로 감지 → 사용자 [Y/n/건너뛰기] 응답. starter 본인(`is_starter: true`)은 자기 파일이므로 (B) 검사 skip. 동기: v0.25.x 채택 다운스트림에 `harness-dev/` 잔재 실측 (2026-05-15), starter_skills 등록 시점(v0.35.1) 이전 채택 다운스트림 회수 메커니즘 부재. MIGRATIONS.md v0.47.1 클린 패치 안내 — 사용자 명령 복사 불필요, harness-upgrade 1회 실행 시 자동 처리.

### v0.47.1 (2026-05-15) — 73% 삭감 wave §S-3~§S-7 일괄 박제 (patch)

73% 삭감 wave의 후속 5영역 일괄 박제. (§S-3) bug-interrupt.md 폐기(Q1/Q2/Q3 자가 발화), debug-specialist 4→1~2단계 압축, no-speculation에 결정적 신호 트리거. (§S-4) implementation 465→153·commit 718→221·write-doc 248→111·eval 664→163 슬림화. doc-health·check-existing 스킬 폐기 (eval --harness 흡수·LSP+Grep 대체). harness-upgrade Step 9.3 (HARNESS_MAP 전파) 삭제. (§S-5) anti-defer·external-experts·pipeline-design rules 폐기, internal-first·memory·no-speculation·self-verify 축약, docs.md 부분 삭감 + §S-7 박제 흡수. (§S-6) orchestrator.py 696줄 전면 삭제, debug-guard.sh 폐기, pre_commit_check.py tag 정규식 차단 게이트 + split 발동 폐기, docs_ops.py cluster-update tag 백링크(2건+ 임계, DRY) + meta 폴백 버그 수정, eval_cps_integrity HARNESS_MAP·BIT NEW 점검 폐기. (§S-7) Wiki 그래프 모델 신설 — domain=zone, tag=edge(cross-domain). cluster 본문에 tag 분포·백링크 자동 생성. tag 정규식 `^[a-z0-9][a-z0-9-]*[a-z0-9]$` pre-check 차단(한글 금지). cps cluster 첫 case 박제(`docs/cps/cp_harness_73pct_cut.md`). 총 14,495→10,766줄 (26% 삭감, 핵심 자산 보유).

### v0.47.0 (2026-05-14) — 73% 삭감 wave §S-1 CPS 재설계 + §S-2 AC 단순화 (minor)

두 달 누적 통제 도구 정리의 첫 두 영역. (1) CPS 재설계: HARNESS_MAP.md 정적 표 폐기, CPS 도메인 신설(abbr `cp`·`docs/cps/`·`docs/clusters/cps.md`), 빠른 조회 명령 `docs_ops.py cps {list|add|cases|show|stats}` + 옵트인 스킬 `/cps-check`, kickoff 491→78줄 압축(C 판단 프롬프트, 자라지 않음). pre_commit_check.py CPS 인용 substring 박제 검사 함수 4개 삭제(~150줄). WIP frontmatter `s: [S2, S6]` 번호 list 도입. (2) AC 4필드 → 3필드: `검증.review` 5단계 자가 선언 폐기(분류 의미 못 가졌음), staging.md 폐기, stage 5단계 → default/deep 2단계, commit 플래그 `--quick`/`--deep` → `--review`/`--no-review`, review verdict 강제 추출 폐기(diff별 한 줄 의견). pre_commit_check.py 1060 → 959줄. 본 wave는 73% 삭감 ADR(`docs/decisions/hn_harness_73pct_cut.md`)의 첫 두 영역 실측 구현.

### v0.46.2 (2026-05-13) — 하네스 v0.41 baseline 회복 + audit 18 해소 단일 wave (patch)

v0.43.0 orchestrator MVI 이후 누적된 hook 강제·자동 트리거가 행동 붕괴 유발. 사용자 증언 "v0.41쯤이 정상 마지막"을 baseline으로 9b29f23(v0.44.1) 도돌이표 commit revert + audit 18 중 17건 해소. PreToolUse `orchestrator.py`·UserPromptSubmit `debug-guard.sh`·Gemini 자동 호출 hook 3종 무력화(파일 보존, 수동 호출 가능). harness_version_bump.py patch 트리거 좁힘(.claude/scripts/1줄 수정 = patch 룰 폐기). split-commit.sh 비파괴 default + `--apply` 옵트인. pre_commit_check.py `git diff --cached --name-only` 중복 호출 제거 + HARNESS.json 중복 read 제거. commit_finalize.sh wip-sync 조건부 실행. docs_ops.py wip-sync abbr 매칭 우선 후보 추출. audit #6 (Codex 인프라 유지) 사용자 명시 보류.

### v0.44.0 (2026-05-12) — Gemini 자동 호출 opt-in과 Codex hook 계약 보강 (minor)

Gemini 자동 검토를 기본 off로 바꾸고 `HARNESS_GEMINI_AUTO=1` 명시 opt-in일 때만 background worker를 실행하도록 정리. WIP의 `problem`·`solution-ref`가 있는 Solution 맥락 변경도 감지하되 hook은 조용히 통과한다. Codex agent TOML과 `.codex/hooks.json` matcher/type/command 계약을 pytest로 고정하고, Python 3.10 환경에서 TOML fallback 파서를 사용한다.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)
- [Claude Code — Permission rule syntax](https://code.claude.com/docs/en/permissions) (matcher 패턴 함정 회피)

MIT License
