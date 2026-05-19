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

## v0.51.5 — CPS P# 정련 + memory/reminder 회귀 계약 보강 (2026-05-19)

P12~P15 대량 신설안을 폐기하고, 신규 P# 0개 원칙으로 기존 P6/P7/P8/P9/P11의
경계를 보강했다. 특히 memory count·stale signal·PASS 라벨이 판단 baseline을
오염시키는 P9 사례와, reminder/incident가 작업 시점에 환기되지 않는 P8 사례를
C-P-S-AC 연결 계약으로 정리했다.

### 자동 적용
- `project_kickoff.md`: P6/P7/P8/P9/P11 Problems 표와 S6/S7/S8/S9/S11 해결 기준 보강. S9는 P9 primary 작업의 회귀 가드 기본값을 명시
- `.claude/rules/docs.md`: WIP frontmatter `c:` 권장, CPS Rationale 형식, AC `review/tests/실측` 4필드 명시
- `.claude/rules/memory.md`: memory를 판단 원자료가 아닌 reminder 신호로 재정의. 회귀 signal 사용 계약(환기→재확인→검증 선택) 추가
- `.claude/rules/self-verify.md`: 닫히지 않는 AC, `tests: 없음`, PASS/WARN/SKIP 단독 증거 금지와 P9 회귀 가드 기본값 보강
- `.claude/rules/hooks.md`: hook stdout/stderr 출력 의미 계약 추가
- `.claude/rules/code-ssot.md`: 새 PR/WIP 분리 원칙과 C-P-S-AC 기준 분리 정당 조건 보강
- `session-start.py`·`stop-guard.py`: memory count 단독 출력과 상시 reminder 노이즈 축소
- `docs_ops.py`: `cps--` WIP를 `docs/cps/`로 completed 이동할 수 있게 보강. 회귀 테스트 1건 추가

### 수동 확인
- 다운스트림은 기존 P12~P15 신설안이 있다면 폐기하고 P6/P7/P8/P9/P11 조합으로 재분류
- P9 primary 작업은 회귀 테스트 또는 재오염 방지 실측을 AC에 남기는지 확인
- pytest 효율과 회귀 라우팅 재정렬은 별도 WIP로 분리됨

### 회귀 위험
- 중간. 문서 계약과 hook 출력 의미가 함께 바뀐다. memory/reminder 출력은 판단 근거가 아니라 환기 신호로 읽어야 한다

## v0.51.4 — P12·S12 폐기 + P11에 흡수 (2026-05-18)

P12 박제 직후 LLM이 정확히 P12 패턴 위반 실측 (별 WIP 4개 자기 분리).
codex·gemini 재검토 합의로 P12·S12 폐기, P11에 "sub-task 분리 우회 금지" 흡수.

### 자동 적용
- `project_kickoff.md`: P12·S12 Problems/Solutions 표·본문 섹션 모두 폐기. P11/S11 본문에 "sub-task 분리 우회 금지" 흡수
- `.claude/rules/code-ssot.md`: "sub-task 분리 우회 금지" 1단락 보강
- `docs/decisions/hn_split_completion_bypass.md` → `docs/archived/`로 이동
- `docs/cps/cp_split_completion_p12.md` 사례 잔류 (P11 첫 회피 사례 박제)
- `pre_commit_check.py` §3.7 게이트 정밀화 — 기존 P# 행 갱신 vs 신규 신설 구분
- 회귀 테스트 1건 추가 (`test_existing_p_row_update_no_block`)

### 수동 확인
- 다운스트림 cascade: P# 표 변경 + rule 본문 갱신. harness-upgrade 시 frontmatter 동기화
- P12 박제 참조하던 다운스트림은 P11로 매핑 갱신 필요 (다운스트림 자율)

### 회귀 위험
- 낮음. 게이트 정밀화는 false positive만 차단 (false negative 영역 변경 없음)

## v0.51.3 — .claude/ 잔재 정리 + skills/agents serves: 다중 매핑 (2026-05-18)

P11/P12 자기 적용. codebase-analyst + codex + gemini 3개 의견 종합.

### 자동 적용
- skills 13개 + agents 9개 frontmatter `serves: S#` 다중 매핑 정착 (advisor S5→S1,S8 등)
- `.claude/memory/MEMORY.md` 인덱스 6개 누락 등록 + signal_* 섹션 분리
- `.claude/rules/memory.md` "누적 감사 로그" 섹션 신설 + stop_hook_audit.log 박제
- 별 wave 후보 4건 WIP 분리 (P12 위반 회피 — guard 점검·보안 P# 신설·signal 스키마·Solutions dead link)

### 수동 확인
- 다운스트림 영향: skills/agents serves: 메타데이터만 갱신. 행동 동작 변경 없음. 다운스트림 cascade 시 frontmatter 동기화

### 회귀 위험
- 낮음. 메타데이터 정합성 영역. signal_defense_success.md는 본 wave에서 의미 직교 확인 후 유지

## v0.51.2 — CPS P# 신설 cp_{slug}.md 박제 누락 차단 + cps_add 표 갱신 (2026-05-18)

P12 박제 wave에서 노출된 동형 박제 위치 분산 결함 (P11 직격) 차단.

### 자동 적용
- `pre_commit_check.py` §3.7 신설 — staged diff에 `project_kickoff.md` `| P\d+ |` 신규 행 + `docs/cps/cp_*.md` 신규 파일 동반 staging 없으면 차단
- `docs_ops.py cmd_cps_add` — Problems 표 마지막 P# 행 뒤에 새 P# 행 자동 삽입 (기존엔 `### P# — ...` 헤더만 append, 표 누락 잠복)
- 회귀 테스트 4건 (TestCpsNewProblemCaseGate 3건 + TestCpsAddTableInsert 1건)

### 수동 확인
- 다운스트림 영향 없음 — starter 본문 차단 게이트라 다운스트림 commit 흐름 변경 없음
- `cps add` 호출자: 표 행 자동 삽입 추가됐으나 헤더 append는 동일 → 기존 사용 패턴 호환

### 회귀 위험
- 낮음. 표 인식 정규식이 기존 행을 못 잡으면 표 갱신 누락 → 본문 헤더만 append (기존 동작 유지)

