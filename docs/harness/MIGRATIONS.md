---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-05-21
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

**누적 관리 권장**: starter `MIGRATIONS.md`와 동일하게 **최신 5개 버전
본문만 본 파일에 유지**, 이전은 `migration-log-archive.md`로 분리 권장
(다운스트림 자율). 5개 본문 기준 약 1~2개월 분량으로 가독성 유지.
분리 시점·정책은 다운스트림 결정 — 자동화 도구 없음.

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

**동형 후보 위치** (선택, P11 인지 시):
<!-- 본 발견의 동형 패턴이 잠복할 가능성 있는 다른 위치 1~3개 -->
- 가능성 1: <위치> — <왜 잠복할 수 있는가>
- 가능성 2: <위치> — ...

**실천**:
<!-- 구체적 개선 방향. "~해야 한다" 형식 -->

**심각도**: low | medium | high
**관련 CPS**: P# (해당 시)
```

### 작성 규칙

- 항목 번호: `FR-NNN` 순차 증가 (프로젝트 내 전역)
- **관점**: 1줄 요약. "어느 레이어·어느 컴포넌트를 봤는가"
- **약점**: 추측 금지. 실측 또는 재현 가능한 시나리오만
- **동형 후보 위치** (선택): P11(동형 패턴 잠복) 인지 시 1차 발견 외 다른
  위치 후보 1~3개 동반 제안. starter가 본 항목을 본문 grep 대상에 자동 합류.
  "동형 가능성 없음"으로 판단하면 섹션 생략. 추측만으로 채우지 마라
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

## v0.52.8 — implementation WIP 실행 계획 soft warning (2026-05-22)

implementation WIP가 AC 형식만 갖추고 실제 작업 단계와 단계별 산출물을 빠뜨리는
문제를 줄이기 위해, implementation 스킬 Step 3·5에 실행 계획 soft warning을
추가했다. 처음부터 hard fail로 막지 않고, 완료 선언 전 보완하도록 유도한다.

### 자동 적용
- `.claude/skills/implementation/SKILL.md`, `.agents/skills/implementation/SKILL.md`:
  implementation WIP에 `## 구현 계획` 또는 동등한 실행 단계 섹션, 단계별 산출물,
  다음 단계 진입 기준이 없으면 soft warning을 남긴다.
- `.claude/rules/docs.md`: AC 포맷에 implementation WIP 실행성 원칙과
  implementation 스킬의 soft warning 책임을 연결한다.

### 수동 적용
- 없음.

### 검증
- `rg -n "implementation WIP 실행 계획 경고|실행 계획 점검|implementation WIP 실행성" .claude/skills/implementation/SKILL.md .agents/skills/implementation/SKILL.md .claude/rules/docs.md`
- `python .claude/scripts/pre_commit_check.py`

### 회귀 위험
- 낮음. 차단 규칙이 아니라 soft warning이므로 기존 WIP 작성 흐름을 즉시 막지 않는다.
  다만 implementation WIP 작성 시 짧은 실행 계획 섹션이 권장된다.

## v0.52.7 — commit review 기본값 정렬과 agy 수동 handoff reminder (2026-05-21)

commit review 호출 정책이 실제 commit 스킬 기본값과 어긋나 있던 문구를 정리했다.
기본 `/commit`은 review를 호출하지 않고 pre-check + 시크릿 게이트만 실행하며,
review가 필요하면 `/commit --review`로 명시한다. 또한 agy CLI 응답 자동 회수
실패 실측을 reminder로 남겨, Codex가 명령어를 작성하고 사용자가 VS Code
터미널에서 직접 실행한 뒤 답변을 전달하는 수동 handoff 운영을 기억한다.

### 자동 적용
- `.claude/rules/docs.md`: commit review 호출 정책을 실제 commit 스킬 기본값과 정렬한다.
- `.claude/memory/reminders/reminder_agy_cli_manual_handoff.md`: agy CLI 수동 handoff 운영 원칙을 reminder로 추가한다.

### 수동 확인
- review가 필요한 커밋에서는 `/commit --review`를 명시한다.
- agy 검증이 필요하면 Codex가 제시한 `agy --print ...` 명령을 VS Code 터미널에서 직접 실행하고, 응답을 Codex 대화에 붙여준다.

### 검증
- `python .claude/scripts/harness_version_bump.py`
- `python .claude/scripts/pre_commit_check.py`

### 회귀 위험
- 낮음. 런타임 로직 변경은 없다. 다만 다운스트림이 기본 `/commit`에서 review 호출을 기대했다면 `/commit --review`로 명시해야 한다.

## v0.52.6 — CPS 헤더형 추출 보강 + canonical shape 문서화 (2026-05-21)

StageLink 다운스트림 `/eval --harness` 보고에서 `project_kickoff.md` 안의
제품 CPS와 하네스 운영 CPS가 섞이면 같은 P#/S#가 다른 의미로 재사용될 수
있다는 실제 사례가 확인됐다. 동시에 evaluator가 `**P1 — ...**`,
`### P5. ...`, `### S7. ... (P8)` 같은 헤더형 CPS를 표 형식만큼 안정적으로
읽지 못해 false warning을 만들 수 있었다.

### 자동 적용
- `.claude/scripts/eval_cps_integrity.py`: 표 형식 외에 헤더형/굵은 글씨형 P#/S# 추출을 지원한다.
- `.claude/scripts/eval_cps_integrity.py`: `### S7. ... (P8)`처럼 점/괄호를 쓰는 헤더형 Solution→Problem 매핑을 지원한다.
- `.claude/scripts/tests/test_eval_harness.py`: 다운스트림 보고 포맷 회귀 테스트를 추가한다.
- `README.md`: CPS canonical shape와 제품 CPS/하네스 CPS 혼합 금지 원칙을 문서화한다.

### 수동 확인
- 다운스트림에서 `/eval --harness`를 다시 실행해 정상 매핑인 `S# -> P#`가 “존재하지 않는 P#”로 보고되지 않는지 확인한다.
- `docs/guides/project_kickoff.md`는 가능하면 아래 표 형식을 유지한다:

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

- 제품 CPS에는 제품 문제와 제품 해결책만 남긴다. `MCP`, `review maxTurns`,
  `bash-guard`, `harness-upgrade`, `pre-check`, `commit skill` 같은 하네스 운영
  항목이 제품 Solution으로 섞이면 CPS drift 후보로 정리한다.

### 검증
- `python -m py_compile .claude/scripts/eval_cps_integrity.py`
- `python -m pytest .claude/scripts/tests/test_eval_harness.py -q`
- `python .claude/scripts/eval_harness.py`

### 회귀 위험
- 낮음. eval 출력의 false warning을 줄이는 파서 보강이다. 다만 헤더형 CPS는
  프로젝트별 표현 차이가 커서, 다운스트림 CPS는 표 형식을 canonical으로 유지하는
  편이 가장 안정적이다.

## v0.52.5 — path contract lint + 검증 도구 가용성 관측 (2026-05-21)

### 자동 적용
- `pre_commit_check.py`: staged Python 파일은 `python -m py_compile`, staged Shell 파일은 `bash -n`으로 문법 검사를 수행한다.
- `pre_commit_check.py`: starter에서는 루트 안내·하네스 스크립트의 path contract drift를 staged 시점에 차단한다. 다운스트림은 warn-only다.
- `eval_harness.py`: `ruff`, `pyright`, `mypy`, `shellcheck` 가용성을 보고하고, 라이브 하네스 경로 문자열 drift를 별도 섹션으로 보고한다.
- `downstream-readiness.sh`: 검증 도구 설치 여부를 `[관측]`으로 출력한다. 누락은 silent skip이 아니라 환경 신호로 남긴다.

### 수동 적용
- 없음.

### 검증
- `python -m py_compile .claude/scripts/pre_commit_check.py .claude/scripts/eval_harness.py`
- `bash -n .claude/scripts/downstream-readiness.sh`
- `python -m pytest .claude/scripts/tests/test_eval_harness.py .claude/scripts/tests/test_pre_commit.py -q`
- `python .claude/scripts/eval_harness.py`

### 회귀 위험
- path contract lint가 의도적 예시 경로를 drift로 오탐할 수 있다. 예시·샘플·다운스트림·archive/history/legacy/fallback 문맥은 면제한다.

## v0.52.4 — 루트 지침·mirror 경로 정합 복구 (2026-05-21)

v0.52.3 이후 루트 지침과 skill mirror 일부에 예전 hook·memory 경로가 남아 있던
문제를 정리했다. downstream-readiness도 현재 pre-check stdout과 review 카테고리를
기준으로 검사하도록 갱신했다.

### 자동 적용
- `CLAUDE.md`, `AGENTS.md`: 사용자가 "리마인더로 남기자"라고 할 때의 active reminder 저장 계약 추가
- `.claude/skills/harness-adopt`, `.agents/skills/harness-adopt`: SessionStart/Stop/PostCompact hook 예시를 `.py` 경로로 갱신
- `.claude/skills/harness-upgrade`, `.agents/skills/harness-upgrade`: 자동 덮어쓰기 예시의 `session-start.sh`를 `session-start.py`로 갱신
- `.claude/skills/eval`, `.agents/skills/eval`: 방어 활성 기록 경로를 `reminders/reminder_defense_success.md`로 통일
- `.claude/scripts/downstream-readiness.sh`: settings hook 검사와 pre-check/review 신호 검사를 현재 계약에 맞게 갱신

### 수동 확인
- 다운스트림에서 `bash .claude/scripts/downstream-readiness.sh` 실행 시 hook 경로·review 카테고리 관련 stale 경고가 사라지는지 확인한다
- custom 문서나 로컬 스크립트가 `session-start.sh`, `stop-guard.sh`, `post-compact-guard.sh`, `signal_defense_success.md`를 직접 참조하면 현재 `.py`/`reminders/` 경로로 갱신한다

### 회귀 위험
- 낮음. 런타임 로직 변경은 readiness 검사와 문서/스킬 경로 정합 복구에 한정된다. 다만 stale 경로를 기대하던 다운스트림 custom check는 새 경로로 맞춰야 한다

