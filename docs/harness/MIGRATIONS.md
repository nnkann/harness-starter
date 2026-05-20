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

---

## v0.51.8 — 느슨한 결합 관측 + CPS 결합도 + 검증 다이어트 (2026-05-20)

관측 지표가 단일 신호로 오판하거나, 오류가 skip/warn/pass 뒤에 묻히는 문제를
줄였다. 다운스트림 피드백과 작업 중 발견된 drift를 바탕으로 `eval --harness`가
CPS P↔S 결합도, C 보강 루프, silent exception 후보, 토큰 다이어트 상태를 함께
보고한다.

### 자동 적용
- `.claude/scripts/eval_cps_integrity.py`: CPS Problems/Solutions 표에서 P↔S 결합도를 검사. orphan Problem, unmapped Solution, dangling P#를 분리해 출력
- `.claude/scripts/eval_harness.py`: 느슨한 결합 관측, 토큰 다이어트 관측, C 보강·회귀 루프 관측 섹션 추가
- `.claude/scripts/docs_ops.py`: `wip-sync`의 WIP glob을 1회로 줄이고, 자동 이동 후 `cluster-update`를 batch 1회 실행
- `.claude/skills/implementation`, `write-doc`, `commit`: WIP 파일명 계약을 `docs_ops.py move`의 `{대상폴더}--{abbr}_{slug}.md` 요구사항에 맞춤
- `.claude/skills/implementation`, `eval`: pytest 전체 스위트 반복 실행 금지. 기본은 단일 파일·test id·좁은 marker
- `project_kickoff.md`: S6/S7/S9 해결 기준에 silent exception, skip/warn/pass 의미, 타깃 테스트 기준 반영

### 수동 확인
- 다운스트림에서 `eval --harness` 실행 후 `CPS P↔S 결합도`, `C 보강·회귀 루프 관측`, `토큰 다이어트 관측` 섹션을 확인
- `silent exception 후보`가 표시되면 intentional skip과 진짜 swallow를 분류하고, 필요한 경우 warning/return reason으로 바꾼다
- pytest는 기본 검증으로 전체 실행하지 않는다. 변경 파일에 대응하는 단일 test id 또는 marker를 우선 사용

### 회귀 위험
- 중간. eval 출력 섹션이 늘어나고 일부 기준이 더 엄격하게 보인다. 다만 기본 동작은 관측 중심이며 차단 게이트가 아니다. WIP 이동 규칙 문서는 기존 `docs_ops.py move` 실제 동작에 맞춰진다

## v0.51.7 — CPS 0건 Problem 폐기 권고 보조 신호 보강 (2026-05-20)

다운스트림 FR-011 반영. `eval --harness`가 `problem:` primary 인용 0건만으로
장기 도메인 Problem을 폐기·병합 후보로 강하게 권고하면, 관련 Solution 인용과
진행 중 WIP의 하위 목표를 놓칠 수 있다.

### 자동 적용
- `.claude/scripts/eval_cps_integrity.py`: CPS Solutions 표에서 `S# → P#` 매핑을 추출하고, `solution-ref`와 `s:` frontmatter 인용을 모두 S# 보조 신호로 집계
- 진행 중 `docs/WIP` 문서에 P# 또는 관련 S# 언급이 있으면 primary 인용 0건 Problem의 보조 신호로 표시
- primary 인용 0건이더라도 관련 Solution/WIP 신호가 있으면 폐기·병합 강권 대신 "보조 신호 있음 — 보존 사유 확인" 문구로 낮춤
- `.claude/scripts/tests/test_eval_harness.py`: FR-011 재현 테스트 포함 4건 추가

### 수동 확인
- 다운스트림에서 `eval --harness` 출력의 "primary 인용 0건" 항목을 확인할 때 related S# 인용과 WIP mentions를 함께 본다
- 장기 Problem은 `project_kickoff.md` 본문에 보존 사유를 남겨 후속 eval 해석 기준으로 삼는다

### 회귀 위험
- 낮음. eval 출력의 해석 보강이며 차단 게이트가 아니다. 다만 기존 "6개월 이상 인용 0이면 폐기/병합" 문구가 더 보수적으로 바뀐다

## v0.51.6 — 다운스트림 pytest fixture 격리 보강 (2026-05-19)

다운스트림 `harness-upgrade` 직후 upstream/starter 테스트를 실행하면
다운스트림의 `is_starter: false` 정책과 프로젝트별 CPS 문서 형식 때문에
starter 전용 회귀 테스트가 false failure를 냈다.

### 자동 적용
- `.claude/scripts/tests/test_pre_commit.py`: 통합 sandbox를 starter 정책으로 명시 고정. `relates-to` 차단 기대 테스트는 `is_starter: true`, 다운스트림 warn-only 케이스는 `is_starter: false`를 테스트 내부에서 명시
- `TestCpsAddTableInsert`: 실제 다운스트림 `project_kickoff.md` 형식에 의존하지 않도록 starter형 synthetic kickoff fixture 사용
- `.claude/scripts/docs_ops.py`: `cmd_cps_add` docstring의 잘못된 미래 버전 표기 정정

### 수동 확인
- 다운스트림에서 `python -m pytest .claude/scripts/tests/ -q`를 직접 실행하는 경우, 이번 버전 이후 동일 성격 false failure가 사라지는지 확인
- `harness-upgrade` 자체 적용에는 추가 수동 조치 없음

### 회귀 위험
- 낮음. 제품 동작 변경이 아니라 테스트 fixture 격리 보강. starter 차단 정책과 다운스트림 warn-only 정책을 테스트 안에서 분리한다

