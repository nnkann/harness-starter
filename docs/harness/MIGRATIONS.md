---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-04-28
---

# 다운스트림 마이그레이션 가이드

`harness-upgrade` 스킬이 각 버전 업그레이드 시 이 문서를 읽어 다운스트림에
표시한다. **upstream 소유 — 다운스트림은 읽기만.**

**최신 5개 버전 본문만 유지** (v0.30.1 정책). 6번째 이전 버전은
`MIGRATIONS-archive.md`로 자동 이동 — `harness_version_bump.py --archive`가
이동 처리. 더 오래된 업그레이드 추적은 archive 또는 git log
(`git log --oneline --grep "(v0\."`).

다운스트림은 자기 환경 마지막 upgrade 이후 누적된 버전을 읽으면 된다.
5개 본문 기준 약 1~2개월 분량. 그보다 오래 누적된 다운스트림은 archive
참조.

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

## Feedback Reports — 다운스트림 → upstream 피드백 채널

업그레이드 후 운용 중 발견한 구조적 관찰·약점·개선 제안을 upstream에 전달하는
규격화된 채널. `migration-log.md`의 별도 섹션으로 작성한다.

**upstream이 이 채널을 통해 기대하는 것**: 다운스트림 환경에서만 보이는
사일런트 페일, 규칙 우회 패턴, 문서 부재 등 — upstream 격리 환경에서는
발견할 수 없는 피드백.

### 포맷 (항목당 1개)

```markdown
## Feedback Reports

### FR-001 (YYYY-MM-DD)

**관점**: <!-- 어떤 측면을 분석했는가 (1줄) -->

**약점**:
<!-- 발견된 문제·헛점·위험. 증상 + 영향 포함 -->

**실천**:
<!-- 구체적 개선 방향. "~해야 한다" 형식 -->

**심각도**: low | medium | high
**관련 CPS**: P# (해당 시)
```

### 작성 규칙

- 항목 번호: `FR-NNN` 순차 증가 (프로젝트 내 전역)
- **관점**: 1줄 요약. "어느 레이어·어느 컴포넌트를 봤는가"
- **약점**: 추측 금지. 실측 또는 재현 가능한 시나리오만
- **실천**: "더 잘 해야 한다" 수준 금지. 구체 행동 또는 구체 파일명 제시
- **심각도**: `high` = upstream이 다음 버전에서 반드시 처리, `medium` = 권장, `low` = 참고
- 미작성(`없음`)도 명시 — 빈 섹션보다 "없음" 한 줄이 낫다

### 버전 섹션 표준 — "다운스트림 보고 요청" 서브섹션

각 버전 섹션은 다음 6개 서브섹션으로 구성된다 (선택적인 6번 추가):

1. **변경 내용** (필수)
2. **자동 적용 항목** (필수)
3. **수동 적용 항목** (필수 — `없음` 명시 가능)
4. **검증** (필수)
5. **회귀 위험** (필수 — `없음` 금지, "관찰 범위 내" 명시)
6. **다운스트림 보고 요청** (선택) — upstream이 본 변경에 대해 다운스트림에서
   특별히 관찰·수신을 기대하는 항목. 자가 발화 의존을 줄이는 능동 채널.

**6번 작성 기준**:

- 본 버전 변경이 "자동 검증 불가 — 운용 행동 변화"를 수반할 때만 작성
- 다음 upgrade 시 다운스트림이 `migration-log.md` `## Feedback Reports`에
  답할 수 있도록 **구체 관찰 질문** 형식
- 항목 1~3개. 많으면 다운스트림이 응답 안 함 (P8 자가 의존 한계)

**포맷 예시**:
```markdown
### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **<관찰 항목>**: <구체 질문 또는 측정 명령>
   - 응답 예: "N건 발생 / 0건 / 미관측"
2. **<관찰 항목>**: ...
```

응답 없이 다음 upgrade 통과해도 차단 아님 — 누적 패턴 자체가 데이터.
upstream은 응답 0건이 N개 버전 연속이면 본 보강의 다운스트림 적합도 재검토.

### eval --harness 검증 항목

`eval --harness` 실행 시 migration-log.md의 Feedback Reports 포맷을 검증한다:

- FR 항목이 있을 때: `관점`·`약점`·`실천`·`심각도` 4개 필드 모두 존재하는지 확인
- 필드 누락 시: `⚠️ FR-NNN: [누락 필드] 없음` 경고
- FR 항목이 없을 때: `피드백 리포트: 없음 ✅` 통과

---

## v0.47.1 — 73% 삭감 wave §S-3·§S-4·§S-5·§S-6·§S-7 일괄 박제 (2026-05-15)

### 변경 내용

**§S-3 (버그 대처 영역)**:
- `rules/bug-interrupt.md` **삭제** (170줄) — Q1/Q2/Q3 자가 발화 의존 블록 폐기
- `agents/debug-specialist.md` 4→1~2단계 압축 (214→80줄)
- `rules/no-speculation.md`에 결정적 신호 트리거(test 실패·exit code) 박제

**§S-4 (스킬 슬림화)**:
- `skills/implementation/SKILL.md` 465→153 (Phase 6원칙·라우팅 매트릭스 폐기)
- `skills/commit/SKILL.md` 718→221 (AC 자동 실행·verdict 추출·5단계 stage 폐기)
- `skills/write-doc/SKILL.md` 248→111 (6종 템플릿·라우팅 태그 폐기)
- `skills/eval/SKILL.md` 664→163 (--surface·--deep·4관점 병렬 폐기, --quick·--harness만)
- `skills/doc-health/SKILL.md` **삭제** → eval --harness 흡수
- `skills/check-existing/SKILL.md` **삭제** → LSP + Grep 1회로 대체
- `skills/harness-upgrade/SKILL.md` Step 9.3 (HARNESS_MAP 전파 확인) 삭제

**§S-5 (rules 본문 처리)**:
- `rules/anti-defer.md` **삭제** (70줄) — 자가 점검 의존
- `rules/external-experts.md` **삭제** (81줄) — 외부 전문가 캐시 폐기
- `rules/pipeline-design.md` **삭제** (116줄) — 7항목 자가 점검 의존
- `rules/internal-first.md` 38→24 축약
- `rules/memory.md` 133→59 축약 (session-* 3파일 정의만)
- `rules/no-speculation.md` 93→40 축약 (첫 행동 3원칙)
- `rules/self-verify.md` 141→69 축약
- `rules/docs.md` 440→311 (구성요소 메타데이터 trigger·Layer·enforced-by 폐기 + wiki 그래프 모델 박제)
- `rules/naming.md` "tag 정책" 신설 (정규식 + 한글 금지)

**§S-6 (스크립트 슬림화)**:
- `scripts/orchestrator.py` **전면 삭제** (696줄, hook 무력화 후 사용 0)
- `scripts/debug-guard.sh` **삭제** (BIT hook 폐기)
- `scripts/pre_commit_check.py` tag 정규식 차단 게이트 추가 + 자동 split 발동 폐기 (`HARNESS_SPLIT_OPT_IN` 명시 옵트인만 잔존)
- `scripts/docs_ops.py` cluster-update 갱신: tag 분포·백링크 자동 생성 (2건+ 임계, DRY) + meta cluster 폴백 버그 수정 (sample 자동 등록)
- `scripts/eval_cps_integrity.py` HARNESS_MAP 점검 + BIT NEW 플래그 폐기 (478→285줄) + 사전 회귀(`get_cps_text`·`verify_solution_ref` import 깨짐) 해소
- `scripts/session-start.py` BIT 출력 + HARNESS_MAP 출력 폐기
- `scripts/stop-guard.py` BIT 블록 검사 폐기
- `tests/test_pre_commit.py` tag 정규식 marker 18 케이스 신설 (`@pytest.mark.tag`)

**§S-7 (Wiki 그래프 모델 신설)**:
- 발견 본질: "wiki처럼 이어지는 거 — 원래 이걸 원했던 거"
- domain = 노드 zone (변경 전파 범위), tag = 간선 (cross-domain edge)
- cluster 파일에 tag 분포·백링크 섹션 자동 생성 (`docs_ops.py cluster-update`)
- 백링크 임계: tag별 2건 이상만 (1건은 분포 표와 동일 정보 — DRY)
- tag 정규식: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` — pre-check 결정적 차단
- 한글 tag 금지 (grep·anchor 호환성, 다운스트림 cascade)
- meta cluster: sample·template zone, 빈 상태 정상
- cps cluster 첫 case 박제: `docs/cps/cp_harness_73pct_cut.md` (본 wave 자체)

**잔존 참조 일괄 정리**:
- `CLAUDE.md`·`agents/review.md`·`agents/researcher.md`·`agents/advisor.md`·`agents/codebase-analyst.md`
- `skills/harness-upgrade`·`harness-dev`·`harness-adopt`에서 HARNESS_MAP·doc-health·anti-defer·external-experts·BIT 참조 폐기 또는 폐기 의도 명시

### 적용 방법

**자동 적용**: harness-upgrade가 3-way merge로 처리.

**수동 확인 권장**:
1. 본인 프로젝트 frontmatter `tags`에 영문 소문자+숫자+하이픈 외 문자(대문자·언더바·한글) 있으면 pre-check 차단됨. 사전 grep 권장:
   ```bash
   grep -rE "^tags:.*[A-Z_가-힣]" docs/
   ```
2. `python .claude/scripts/docs_ops.py cluster-update` 실행 — 신규 tag 분포·백링크 섹션 자동 생성
3. CPS case 누적은 점진적 — wave 완료 시마다 `docs/cps/cp_{slug}.md` 박제 (선택)

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -m "tag or gate or secret" -q
python .claude/scripts/eval_cps_integrity.py
python .claude/scripts/docs_ops.py cluster-update
```

### 회귀 위험

- upstream 격리 환경에서 관찰된 범위 내에서는 회귀 0. commit_finalize.sh의 Windows 경로 git alternates fail은 본 wave 무관 (사전 환경 결함).
- 다운스트림이 frontmatter tags에 한글·대문자·언더바를 사용 중이면 첫 commit에서 차단됨 — 위 "수동 확인 권장" grep으로 사전 검증 권장.
- pytest 84 passed, 4 skipped (commit_finalize 환경 fail 3건 제외)

---

## v0.47.0 — 73% 삭감 wave §S-1 CPS 재설계 + §S-2 AC 단순화 (2026-05-14)

### 변경 내용

**§S-1 CPS 재설계 (자라는 시스템 + CPS 도메인 신설)**:
- `.claude/HARNESS_MAP.md` **삭제** — defends/serves/enforced-by/trigger 정적 표 폐기.
  CPS cascade 표가 정적이라 죽었음을 박제. wave별 case는 `docs/cps/cp_{slug}.md` + git history.
- CPS 도메인 신설 — abbr `cp`, `docs/cps/` 폴더, `docs/clusters/cps.md` 자동 매핑.
- 신규 스킬: `.claude/skills/cps-check/SKILL.md` (옵트인 정합 검사).
- 신규 명령: `python .claude/scripts/docs_ops.py cps {list|add|cases|show|stats}`.
- `docs/guides/project_kickoff.md` 491 → 78줄 압축 (C 판단 프롬프트, 자라지 않음).
  압축 전 본문은 `docs/archived/hn_kickoff_pre_73pct_cut.md`에 보존.
- `pre_commit_check.py` CPS 인용 박제 substring 검사 폐기 (~150줄):
  `normalize_quote`·`parse_solution_ref`·`get_cps_text`·`verify_solution_ref` 함수 삭제.
- `docs.md` "CPS 인용" 섹션 폐기 — 50자·(부분)·normalize 룰 삭제, 번호 list만.
- WIP frontmatter `s: [S2, S6]` 번호 list 형식 도입. 레거시 `solution-ref` 호환 유지.

**§S-2 AC 4필드 → 3필드 (검증.review 5단계 자가 선언 폐기)**:
- `.claude/rules/staging.md` **삭제** — Stage 5단계 룰 폐기.
- AC 형식: `Goal:` + `검증.tests:` + `검증.실측:` 3필드. `검증.review:` 폐기.
- `pre_commit_check.py` stage 결정 단순화 — 5단계(skip/micro/standard/deep) → 2단계(default/deep).
  default = 사용자 플래그 결정, deep = 시크릿 line-confirmed 강제.
- commit 스킬 플래그 단순화 — `--quick`/`--deep` 폐기, `--review`/`--no-review` 2단계.
- review agent verdict 강제 추출 폐기 — diff별 한 줄 의견 자유 형식.

**기타**:
- `pre_commit_check.py` 1060 → 959줄 (101줄 감소).
- CLAUDE.md "하네스 신경망 허브" → "## CPS" 짧은 안내 (HARNESS_MAP 참조 제거).

### 적용 방법

**자동**: harness-upgrade 시 위 파일 변경이 머지된다.

**수동**:
- 기존 WIP frontmatter `solution-ref: - S2 — "..."` 형식은 그대로 두면 호환 (S# 번호만 추출).
  신규 WIP는 `s: [S2, S6]` 인라인 list 권장.
- AC 형식: 기존 WIP의 `검증.review: skip|self|review|review-deep` 라인은 무시됨 (파싱 안 함).
  신규 WIP는 `검증.tests` + `검증.실측` 2개만.
- HARNESS_MAP.md 참조하는 다운스트림 룰·스킬이 있으면 본문 직접 갱신 권장 (자동 머지 불가).

### 검증

```bash
# CPS 시스템 작동 확인
python .claude/scripts/docs_ops.py cps list      # P1~P# 1줄 요약
python .claude/scripts/docs_ops.py cps stats     # case 수·P# 분포

# pre-check 작동 확인 (WIP 작성 후)
python .claude/scripts/pre_commit_check.py       # ac_tests·ac_actual 출력, ac_review 사라짐
```

### 회귀 위험

- upstream 격리(Windows/Git Bash)에서 `pre_check_passed: true` 실측.
- 기존 WIP의 `solution-ref` 50자 인용 형식 파일은 다음 커밋 시 그대로 통과 (S# 번호만 추출). 박제 substring 검사 폐기로 인용 의미 검증이 사라짐 — wave 간 역영향 추적은 commit body·git log로 수동 처리.
- Linux/macOS 미테스트.

---

## v0.46.2 — 하네스 v0.41 baseline 회복 + audit 18 해소 단일 wave (2026-05-13)

### 변경 내용

**의도**: v0.43.0 orchestrator MVI 도입 이후 누적된 hook 강제 패턴·자동
트리거가 행동 붕괴 유발. 사용자 증언 "v0.41쯤이 정상 마지막"을 baseline
으로 단일 wave 회복. 9b29f23(v0.44.1) 도돌이표 commit revert + audit 18
중 17건 해소.

**revert 범위 (9b29f23 일괄 환원)**:
- pre_commit_check.py route 출력 8키(commit_route·review_route·promotion·
  blocking_reasons·warning_reasons·side_effects.*) 폐기
- commit/SKILL.md route 소비 코드 베이스라인 환원
- split-commit.sh 9b29f23 변경 환원 (본 wave가 새 비파괴 default 재구현)
- Windows smoke 테스트(TestWindowsCommitSmoke) + windows·cascade marker 폐기
- side effect ledger·cascade integrity check 폐기

**hook 무력화 (Phase 1)**:
- `.claude/settings.json` PreToolUse `orchestrator.py` hook 제거
- `.claude/settings.json` UserPromptSubmit `debug-guard.sh` hook 제거
- Gemini 자동 호출은 orchestrator 내부 호출이라 자동 무력화
- worker 파일(orchestrator.py·debug-guard.sh·gemini_background_worker.py)
  보존 — 수동 호출 또는 후속 재설계에 사용
- bug-interrupt.md "## 강제 트리거" 절을 "## 수동 가이드"로 변경

**정합 패치 (Phase 2~4)**:
- harness_version_bump.py: patch 트리거 좁힘. `.claude/scripts/*.{sh,py}`
  1줄 수정 = patch 룰 폐기. skills SKILL.md·rules·agents·CLAUDE.md만 patch
  자동 (그 외는 promotion=none, 작성자 명시 옵트인만)
- split-commit.sh: 비파괴 default + `--apply` 옵트인 + `SPLIT_PRE_OUT`
  env로 pre-check 중복 호출 우회
- pre_commit_check.py: `git diff --cached --name-only` 중복 호출 제거 +
  HARNESS.json 중복 read 제거(main 함수 내 1회 캐시)
- commit_finalize.sh: wip-sync 조건부 실행 (staged에 `docs/(WIP|clusters)/`
  변경 있을 때만)
- docs_ops.py wip-sync: abbr 매칭 우선 후보 추출 → 매칭 시 그 WIP만 iter,
  매칭 0이면 전체 iter fallback

**.gitignore 보강**: `.claude/worktrees/` 차단 (절대 규칙: worktree 금지).

### 적용 방법

**자동**: 다운스트림이 `/harness-upgrade` 실행 시 코드 변경 자동 병합.

**수동 (다운스트림 영향)**:
- 다운스트림 `.claude/settings.json`의 hook 블록이 v0.43.0~v0.44.0 hook
  3종(orchestrator·debug-guard·gemini)을 포함하면 3-way merge로 제거 처리.
  hook 커스터마이즈된 다운스트림은 ours/theirs 결정 필요
- 다운스트림이 SKILL.md route 출력(`commit_route`·`review_route` 등) 키를
  소비하는 커스텀 스크립트를 만들었다면 해당 키 사용 코드 제거 또는
  버전 분기 필요

### 검증

```bash
python3 -c "import json; s=json.load(open('.claude/settings.json')); print('UserPromptSubmit:', s['hooks'].get('UserPromptSubmit', 'REMOVED'))"
# 예상 출력: UserPromptSubmit: REMOVED
python3 .claude/scripts/pre_commit_check.py 2>&1 | grep -E "^(commit_route|review_route|promotion):" | wc -l
# 예상 출력: 0 (revert 확인)
```

### 회귀 위험

- upstream 격리 환경(Windows·Git Bash)에서 관찰된 범위 내에서는 v0.41
  baseline 동작 회복 정합. Linux/macOS 미테스트
- hook 무력화로 BIT 키워드 grep·orchestrator 신호 안 나옴 — 자가 인지
  의존 영역으로 환원. 자가 발화 의존 한계는 P8/P9가 박제하는 본질이라
  hook 강제력으로 우회 불가 (Anthropic Issue #13912 명시)
- audit #6(Codex 인프라 사본 부담)는 명시적 보류. 사용자 결정 "Codex 유지"

---

## v0.44.0 — Gemini 자동 호출 opt-in과 Codex hook 계약 보강 (2026-05-12)

### 변경 내용

Codex 전환 후 드러난 hook/agent 경계와 Gemini 자동 위임 노이즈를 정리했다.

- `orchestrator.py`: Gemini 자동 호출을 기본 off로 전환하고 `HARNESS_GEMINI_AUTO=1`일 때만 background worker를 실행한다.
- `orchestrator.py`: CPS 본문뿐 아니라 `problem`·`solution-ref`가 있는 WIP의 Solution 맥락 변경도 검토 후보로 감지한다.
- `gemini_background_worker.py` 추가: 긴 prompt를 파일/stdin 경유로 전달하고 stdout/stderr를 세션 scratch 파일에 기록한다.
- `.codex/hooks.json`·`.claude/settings.json`: 빈 matcher를 명시해 Codex/Claude hook schema 경고를 줄인다.
- `test_codex_agents.py` 추가: Codex agent TOML, hook matcher/type/command 계약, Gemini 미지원 tool 이름 박제를 회귀 가드로 고정한다.
- `test_orchestrator.py`: Gemini auto off, worker 출력 기록, WIP Solution 맥락 감지, Python 3.10 호환 경로를 보강한다.

### 자동 적용 항목

파일 추가·수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. Gemini 자동 검토가 필요한 upstream 운용자는 명시적으로 `HARNESS_GEMINI_AUTO=1`을 설정해야 한다.

### 검증

```
python3 .claude/scripts/pre_commit_check.py
python3 -m pytest .claude/scripts/tests/ -q
```

### 회귀 위험

관찰 범위 내 위험: Gemini 자동 호출이 기본 off가 되므로, 이전처럼 PreToolUse에서 자동 외부 의견 파일이 생성된다고 기대하던 운용은 명시 opt-in으로 전환해야 한다. Codex hook matcher 계약이 더 엄격해져 다운스트림의 기존 `.codex/hooks.json` 커스터마이즈와 충돌할 수 있다.

---

## v0.43.3 — Codex 하네스 브리지와 Gemini 위임 WIP 정렬 (2026-05-11)

### 변경 내용

Codex 환경에서 기존 하네스 규칙·스킬·에이전트 지시가 함께 로드되도록
브리지 파일을 추가했다.

- 루트 `AGENTS.md` 추가 — Codex 진입점에서 하네스 핵심 규칙 노출
- `.agents/skills/**` 추가 — 하네스 스킬 본문을 Codex skill discovery 경로로 제공
- `.codex/agents/*.toml` 추가 — 기존 specialist 에이전트를 Codex subagent 정의로 연결
- `.codex/hooks.json` 추가 — Codex hook 설정 진입점 추가
- `pre_commit_check.py`와 `orchestrator.py` 보강 — starter 자가 검증 및 반복 신호 흐름 정렬
- `hn_gemini_delegation_pipeline` 결정 문서를 WIP로 되돌려 Phase 후속 작업 진행 상태 반영
- 세션 거짓 완료·자기 위반 패턴 incident WIP 추가

### 자동 적용 항목

파일 추가·수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. 다만 다운스트림에서 자체 Codex 설정을 이미 운용 중이면 `.codex/` 충돌 해소 시
로컬 설정 유지 여부를 확인한다.

### 검증

```
python3 .claude/scripts/pre_commit_check.py
python3 -m pytest .claude/scripts/tests/ -q
```

### 회귀 위험

관찰 범위 내 위험: Codex 전용 브리지 파일이 다운스트림의 기존 `.codex/`
커스터마이즈와 충돌할 수 있다. 충돌 시 harness-upgrade 3-way merge에서
로컬 설정과 upstream 기본값을 비교해야 한다.

