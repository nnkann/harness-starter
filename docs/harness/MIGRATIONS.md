---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-05-30
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

## v0.55.0 — CPS+AC 학습 스킬 (2026-06-02)

### 변경 내용

- `cps-learn` 스킬을 추가했다.
- 복수 P#는 문제 차원 증가로 해석해 무엇을 더 봐야 하는지 분석 축을 도출한다.
- 복수 S#는 실행 구조 증가로 해석해 AC 단계화·반복·분리 검증을 설계한다.
- `h-setup.sh` minimal/standard/full 프로파일과 `.claude/HARNESS.json` `skills`에
  `cps-learn`을 등록했다.
- Codex mirror `.agents/skills/cps-learn/SKILL.md`도 함께 배포한다.

### 자동 적용 항목

- `.claude/skills/cps-learn/SKILL.md`
- `.agents/skills/cps-learn/SKILL.md`
- `.claude/HARNESS.json`
- `h-setup.sh`
- `README.md`

### 수동 적용 항목

- 복수 P#/S#가 붙은 WIP에서 AC 구조가 애매하면 `/cps-learn`을 먼저 호출해
  P-axis, S-axis, AC 재구성, specialist 폭을 정한다.
- 기존 `/cps-check`는 번호 정합 검사이고, `/cps-learn`은 구조 해석·AC 재구성이다.

### 검증

- `bash -n h-setup.sh`
- `python3 -m pytest .claude/scripts/tests/test_skill_routing_contract.py .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
- `python3 .claude/scripts/docs_ops.py validate`
- `python3 .claude/scripts/docs_ops.py verify-relates`

## v0.54.2 — downstream feedback visibility + bootstrap gate (2026-06-02)

### 변경 내용

- `h-setup.sh` 신규 설치 HARNESS 정의 파일에 `is_starter=false`를 명시한다.
- 신규 설치 placeholder가 `.claude/HARNESS.json` 생성 후 `/harness-init`에서 CPS/스택/도메인 분류를 해야 한다고 안내한다.
- Hermes local guardian `harness_downstream_learning_check.py`는 반복 Feedback Report에 `new`/`existing`/`aging` 상태를 붙이고, `.claude/HARNESS.json` 없는 harness-downstream registry 항목을 bootstrap owner-action으로 분류한다.

### 자동 적용 항목

- `h-setup.sh`
- `README.md`

### 수동 적용 항목

- Hermes local guardian를 쓰는 환경은 `~/.hermes/scripts/harness_downstream_learning_check.py`가 최신인지 확인한다. 이 파일은 local binding이라 downstream repo에는 자동 전파되지 않는다.
- `.claude/HARNESS.json` 없는 프로젝트를 Hermes `type: harness-downstream`으로 등록했다면, 먼저 `bash /path/to/harness-starter/h-setup.sh /path/to/project`를 실행하고 이어서 `/harness-init`으로 도메인 목록·약어·등급을 분류한다.

### 검증

- `python3 -m py_compile ~/.hermes/scripts/harness_downstream_learning_check.py`
- `python3 -m pytest .claude/scripts/tests/test_h_setup_runtime_metadata.py -q`
- `bash -n h-setup.sh`
- `python3 ~/.hermes/scripts/harness_downstream_learning_check.py --force-report`

### 회귀 위험

- 관찰 범위 내: guardian 상태 라벨은 local Hermes state 기반이므로 state 파일을 삭제하면 기존 후보가 다시 `new`로 보일 수 있다.
- 관찰 범위 내: local guardian 변경은 repo upgrade만으로 전파되지 않는다. Hermes runtime binding 갱신 여부를 별도 확인해야 한다.

### 다운스트림 보고 요청

다음 upgrade 시 `migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **bootstrap 누락 안내**: `.claude/HARNESS.json` 없는 registry 항목이 owner-action으로 표시됐는가?
2. **후보 aging 가시성**: 반복 Feedback Report가 오래된 후보로 보이는가, 아니면 여전히 새 신호처럼 보이는가?

## v0.54.1 — typed AC + CPS agent learning loop (2026-06-02)

### 변경 내용

- AC 포맷이 대표 Goal + typed AC(`Problem AC`, `Solution AC`, `Step AC`, `Behavior AC`, `Guardrail AC`, `Verification AC`)로 확장됐다.
- `pre_commit_check.py`가 staged WIP의 typed AC 존재와 개별 P#/S# 인용을 검사한다.
- implementation 스킬이 `forward` 외 `reverse-solution`, `reverse-evidence`, `resume`, `interrupt` CPS flow를 기록한다.
- specialist handoff가 CPS packet(C/P/S/AC/flow/open question) 기반으로 좁혀지고, 일부 agent에 `trigger:` metadata가 추가됐다.
- downstream cron/guardian report는 사실 증거가 아니라 `memory-signal`로 취급하고, `/eval --harness`·harness-dev·harness-upgrade에서 확인한다.

### 자동 적용 항목

- `.claude/rules/docs.md`, `.claude/rules/memory.md`, `.claude/skills/*`, `.claude/agents/*`, `.claude/scripts/pre_commit_check.py`, 관련 테스트가 harness-upgrade로 갱신된다.
- `.agents/skills/*` mirror는 Codex runtime에서 사용되는 active mirror다. downstream runtime이 `.agents`를 쓰면 함께 반영된다.

### 수동 적용 항목

- 기존 in-progress WIP가 있으면 다음 작업 전 AC를 typed AC 형식으로 보강한다.
- downstream 자체 agent/skill에 `trigger:`를 추가할지는 각 프로젝트 routing 필요성에 따라 점진 적용한다.
- Hermes cron/guardian 보고를 받는 downstream은 report를 사실 증거로 쓰기 전 repo 명령·문서·git 상태 중 하나로 재확인한다.

### 검증

- `python3 .claude/scripts/pre_commit_check.py`
- `python3 -m pytest .claude/scripts/tests/test_pre_commit.py -q -k "ACTypedTraceability or ACSolutionRef or ACCheckbox"`
- `python3 -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q`

### 회귀 위험

- 관찰 범위 내: 기존 자유 형식 AC를 가진 open WIP는 commit 시 typed AC 누락으로 차단될 수 있다.
- 관찰 범위 내: `trigger:`는 routing hint이며 hard gate가 아니므로, agent 호출 판단을 trigger 목록만으로 제한하면 false negative가 생긴다.
- 관찰 범위 내: cron report는 `memory-signal`이므로 현재 repo evidence 없이 완료 증거로 포장하면 P9 오염이 재발한다.

### 다운스트림 보고 요청

upstream이 typed AC와 CPS agent learning loop의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다. 다음 upgrade 시 `migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **typed AC 마찰**: 기존 WIP가 typed AC 누락으로 차단된 건수가 있었는가?
   - 응답 예: "N건 발생 / 0건 / 미관측"
2. **reverse CPS 효과**: 테스트·cron·review에서 시작한 신호가 P#/S# 재분류로 이어진 사례가 있었는가?
   - 응답 예: "N건 발생 / 0건 / 미관측"
3. **cron report 재확인**: guardian/cron report를 현재 repo evidence로 재확인하지 못해 보류한 사례가 있었는가?
   - 응답 예: "N건 발생 / 0건 / 미관측"

## v0.54.0 — downstream 공통 Agy review runner (2026-05-30)

Hermes + Codex + Agy stack에서 Agy advisory review를 각 downstream 프로젝트가
같은 방식으로 호출할 수 있도록 공통 runner를 추가했다. Agy 인증·모델·로컬
실행 파일은 repo에 고정하지 않고 local execution binding으로 유지한다. Agy는
의사결정에 적극 개입하는 advisor이므로 runner 기본값은
`AGY_PERMISSION_MODE=full`이며 `--dangerously-skip-permissions`를 붙여 실행한다.

### 자동 적용
- `.claude/scripts/agy-review.sh`: 현재 프로젝트 root를 `--add-dir`로 붙여 Agy
  print mode를 실행하는 공통 runner를 추가한다. 실행 결과는
  fallback handoff인 `.claude/memory/session-agy-review.md`에 저장한다. 기본값은 full permission
  advisory이며, 권한 프롬프트를 유지해야 하는 환경만 `AGY_PERMISSION_MODE=prompt`로 낮춘다.
- `.claude/scripts/downstream-readiness.sh`: `runtime_adapters`에 `agy`가 있으면
  runner 존재, handoff 파일 경로, permission mode, local `agy` executable 또는
  `AGY_BIN` 설정을 관측한다.
- `README.md`: scripts 목록에 `agy-review.sh`를 추가한다.

### 수동 확인
- downstream에서 `bash .claude/scripts/downstream-readiness.sh`를 실행해
  `agy runner`, `agy handoff`, `agy permission_mode`, `agy callable` 관측값을 확인한다.
- Agy 실행 파일이 PATH에 없으면 `AGY_BIN=/path/to/agy`를 설정한다.
- Codex tool sandbox에서 runner가 exit 73으로 중단하면, 안내된 명령을 로컬
  터미널에서 실행한 뒤 Codex가 fallback handoff인 `.claude/memory/session-agy-review.md`를 읽게 한다.

### 검증
- `python -m pytest .claude/scripts/tests/test_downstream_readiness.py -q`
- `python -m pytest .claude/scripts/tests/test_agy_review.py -q`
- `bash .claude/scripts/downstream-readiness.sh`

### 회귀 위험
- 낮음. 새 runner는 opt-in 호출 표면이며, Agy executable 부재는 readiness 경고로만
  보고한다.

## v0.53.0 — 다중 runtime adapter 통합 관리 (2026-05-26)

하네스 기본 운영 전제를 Claude 중심에서 Hermes + Codex + Agy pilot stack으로 전환했다.
공통 하네스 계약과 runtime adapter를 분리하는 WIP 결정을 추가하고, 다운스트림 manifest에서
`runtime_stack`과 `runtime_adapters`를 관측할 수 있게 했다. Claude adapter는 기존 호환성을
위해 유지하되 optional adapter로 분류한다.

### 자동 적용
- `.claude/HARNESS.json`: 버전을 `0.53.0`으로 갱신하고 `runtime_stack: hermes-codex-agy`,
  `runtime_adapters` 기본값을 추가한다.
- `h-setup.sh`: 신규 설치와 기존 upgrade 경로 모두 runtime adapter metadata를 기록·백필한다.
- `.claude/scripts/downstream-readiness.sh`: `runtime_stack`과 `runtime_adapters`를 관측 출력한다.
- `README.md`: Claude 본체 중심 설명을 다중 runtime adapter 통합 관리 관점으로 바꾼다.
- `docs/decisions/hn_runtime_adapter_unification.md`: runtime adapter 통합 정책을 추가한다.
- `docs/archived/hn_hermes_integration.md`: Hermes orchestration adapter 초기 설계 기록을 보존한다.
- memory/reminder 관련 completed decision은 Hermes-managed downstream 정책 보강을 위해 WIP로 reopen한다.

### 수동 확인
- 다운스트림에서 `bash .claude/scripts/downstream-readiness.sh`를 실행해 `runtime_stack`이
  의도한 stack으로 출력되는지 확인한다.
- StageLink 같은 Hermes-managed downstream은 Hermes manifest/guardian 쪽에서도
  `runtime_stack: hermes-codex-agy`를 읽도록 후속 반영한다.
- Claude Code 구독/OAuth availability를 기본 전제로 둔 로컬 절차가 남아 있으면
  Codex/Hermes/Agy 경로로 대체할 수 있는지 점검한다.

### 검증
- `python -m pytest .claude/scripts/tests/test_downstream_readiness.py .claude/scripts/tests/test_h_setup_runtime_metadata.py .claude/scripts/tests/test_codex_agents.py -q`
- `python .claude/scripts/docs_ops.py validate`
- `python .claude/scripts/docs_ops.py verify-relates`
- `bash .claude/scripts/downstream-readiness.sh`
- `python .claude/scripts/pre_commit_check.py`

### 회귀 위험
- 중간. `.claude`는 현재 구현 본체로 계속 보존하지만 설계상 optional Claude adapter로
  강등했으므로, Claude-only 다운스트림은 manifest의 runtime metadata를 확인해야 한다.
  기존 HARNESS.json은 upgrade 시 기본값을 백필하지만, 프로젝트별 실제 runtime stack과 다르면
  수동으로 조정해야 한다.

