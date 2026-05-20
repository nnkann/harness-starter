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

## v0.52.3 — reminder memory 계약 정리 (2026-05-21)

reminder를 `docs/`의 SSOT 문서가 아니라 `.claude/memory/reminders/` 아래의
routing signal로 정리했다. 관련 WIP가 있으면 reminder를 새 backlog처럼 쌓지
않고 AC·메모·결정 사항에 흡수하며, 독립 판단 단위가 될 때만 WIP를 거쳐
decision/incident/guide로 승격한다.

### 자동 적용
- `.claude/memory/reminders/`: starter 본체의 기존 `signal_*.md` memory를 `reminder_*.md`로 승격·이동
- `.claude/scripts/session-start.py`: 새 reminder 폴더 우선 로드, 루트 `reminder_*.md`/`signal_*.md` fallback 유지, `kv_group` hit 우선 정렬 추가
- `.claude/scripts/eval_harness.py`: reminder frontmatter/stale/group lint와 관련 WIP 흡수·승격 후보 보고 추가
- `.claude/scripts/bash-guard.sh`: 방어 성공 기록을 `reminders/reminder_defense_success.md`에 append
- `.claude/rules/memory.md`, `.claude/memory/MEMORY.md`, `.claude/skills/eval/SKILL.md`: reminder 위치·lifecycle·eval 계약 갱신

### 수동 확인
- 다운스트림에 루트 `.claude/memory/reminder_*.md` 또는 `signal_*.md`가 남아 있으면 그대로 동작하지만, 신규 reminder는 `.claude/memory/reminders/`에 생성한다
- 작업 중 “리마인더로 남기자” 요청이 나오면 관련 WIP 흡수 가능성을 먼저 확인하고, 필요한 경우 얇은 `reminders/reminder_*.md`만 남긴다
- `/eval --harness`를 실행해 memory/reminder lint가 stale·과밀·strong+source 약함 후보를 보고하는지 확인한다

### 회귀 위험
- 중간. memory 파일 위치와 session-start/eval 로딩 경로가 바뀐다. 루트 fallback을 유지해 즉시 단절 위험은 낮췄지만, downstream custom script가 루트 `reminder_*.md`만 직접 glob하면 새 표준 경로를 반영해야 한다

---

## v0.52.2 — SSOT drift 통합 의무 보강 (2026-05-20)

작업 중 SSOT가 여러 곳에 나뉜 것을 발견하면 그 자체를 본 작업의 문제로
처리하도록 규칙을 보강했다. 문서·절차뿐 아니라 함수, 메서드, 변수, 상수,
정규식, schema key, 환경변수 이름 같은 코드 심볼도 owner 지정·참조화·mirror
역할 분리 대상임을 명시했다.

### 자동 적용
- `.claude/rules/docs.md`: SSOT drift 발견 시 owner SSOT 지정, 참조화, 역할 분리, WIP AC 포함을 의무화
- `.claude/rules/code-ssot.md`: 코드 심볼 SSOT drift 규칙 추가
- `.claude/skills/implementation`, `.agents/skills/implementation`: Step 2에 SSOT drift와 코드 심볼 SSOT 실행 절차 추가

### 수동 확인
- 작업 중 같은 의미의 절차·판정·심볼이 2곳 이상 보이면 한 곳만 고치지 말고 owner SSOT와 mirror/참조 역할을 먼저 정한다
- 같은 로직이 3곳 이상이면 기존 `code-ssot.md` 3+ reference rule에 따라 별도 core 추출 wave를 검토한다

### 회귀 위험
- 낮음. 절차·규칙 보강이며 런타임 동작 변경은 없다. 다만 implementation 단계에서 SSOT 탐색·정리 범위가 더 엄격해질 수 있다

---

## v0.52.1 — eval false positive + 버전 범프 opt-in 복구 (2026-05-20)

`eval --harness` false positive 수정이 버전 범프 없이 push되며 다운스트림
upgrade 경로에서 사라질 수 있던 문제를 복구했다. scripts 수정은 기본적으로
자동 patch를 강제하지 않되, 다운스트림에 전파되어야 하는 버그 수정이면
`HARNESS_BUMP=patch`로 명시 patch를 제안하도록 계약을 코드와 commit Step 4에
반영했다.

### 자동 적용
- `.claude/scripts/eval_cps_integrity.py`: 헤더형 `### S# (for P#)` Solution 매핑 파싱 지원
- `.claude/scripts/eval_harness.py`: 자기 진단 스크립트를 silent exception 사용자 조치 후보에서 제외
- `.claude/scripts/harness_version_bump.py`: `HARNESS_BUMP=patch|minor` 명시 범프 제안 지원
- `.claude/skills/commit`, `.agents/skills/commit`: scripts 수정이 다운스트림 동작에 영향 있으면 `HARNESS_BUMP=patch`로 Step 4를 재실행하도록 명시

### 수동 확인
- 다운스트림에서 `/eval --harness`를 실행해 CPS P↔S 결합도 false positive와 eval 자기 진단 스크립트 경고가 줄었는지 확인
- starter 개발자는 `.claude/scripts/*.py|*.sh` 기존 파일 수정 시 `version_bump: none`이 나오면 다운스트림 영향 여부를 판단하고, 영향이 있으면 `HARNESS_BUMP=patch python .claude/scripts/harness_version_bump.py`로 재확인

### 회귀 위험
- 낮음. eval 출력과 버전 제안 계약 보강이다. 다만 scripts 수정은 여전히 자동 patch가 아니므로 작성자가 다운스트림 영향 여부를 판단해야 한다

---

## v0.52.0 — commit push 타임아웃 재발 방지 (2026-05-20)

Codex Windows 환경에서 `bash -lc 'HARNESS_DEV=1 git push ...'` 형태가 Git for
Windows/GCM 하위 프로세스 대기로 타임아웃될 수 있어 commit Step 8 push 계약을
비대화형·shell별 명령으로 고정했다.

### 자동 적용
- `.claude/skills/commit`: Codex Windows 기본 push를 PowerShell env 방식과 `--porcelain` 출력으로 명시
- `.claude/skills/commit`: Bash push도 `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`를 포함하도록 명시
- `.claude/scripts/tests/test_skill_routing_contract.py`: `.claude`와 `.agents` commit 스킬의 push 계약 회귀 테스트 추가

### 수동 확인
- Codex Windows에서는 push를 `bash -lc`로 감싸지 않고 PowerShell env 방식으로 실행한다
- 인증 프롬프트가 필요하면 Codex 밖에서 credential을 갱신한 뒤 다시 push한다

### 회귀 위험
- 낮음. commit 스킬의 push 실행 절차만 바꾸며, pre-push guard와 origin/main 대상은 유지된다

---

## v0.51.9 — 버전 범프 스테이징 계약 보강 (2026-05-20)

`harness_version_bump.py`가 staged 변경이 없을 때 `none`만 출력해 실제 patch/minor
필요성을 숨기던 흐름을 보강했다. 지원하지 않는 CLI 인자도 기본 체크로 조용히
폴백하지 않고 usage와 함께 실패한다.

### 자동 적용
- `.claude/scripts/harness_version_bump.py`: staged 변경이 없더라도 unstaged/untracked 핵심 변경이 있으면 `stage_required: true`와 `pending_bump`를 출력
- `.claude/scripts/harness_version_bump.py`: `--archive`, `--help` 외 unsupported arg는 exit 2로 실패
- `.claude/skills/commit`, `.claude/skills/harness-dev`: 버전 범프 스크립트가 제안/검사 도구이며 HARNESS.json은 직접 갱신해야 한다는 계약 명시
- `.claude/scripts/tests/test_harness_version_bump.py`: stage-required, staged patch, untracked minor, unsupported arg 회귀 테스트 추가

### 수동 확인
- 다운스트림에서 harness-starter 변경을 만들고 `harness_version_bump.py`를 stage 전 실행하면 `stage_required: true`가 보이는지 확인
- unsupported arg를 쓰던 로컬 alias가 있다면 `--archive` 또는 기본 실행으로 정리

### 회귀 위험
- 낮음. 버전 제안 출력과 CLI 실패 계약만 바뀐다. 기존 `version_bump: patch|minor|none` staged 계약은 유지된다

