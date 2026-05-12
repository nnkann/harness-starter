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

## v0.46.1 — orchestrator P1 stdout mute (2026-05-12)

### 변경 내용

진단 wave 1 (D 옵션). orchestrator P1 신호 (동일 파일 연속 수정)의 stdout
INFO 출력 mute. detect 로직·signal_*.md 누적·session_signal 백그라운드
저장은 그대로 유지. P9 critical·Phase1 (Gemini 트리거)는 출력 유지.

본 세션 실측 — 본 변경 직전 P1 false positive 100% (모든 신호 stale,
의도된 wave 일관 변경 in-context). 본 변경 후 stdout INFO 0건.

- `.claude/scripts/orchestrator.py` main 함수 5줄 추가 — output_signals
  = [s for s in new_signals if s.get("p_id") != "P1"] 필터링. critical 판정
  은 전체 new_signals 기준 (P9 critical 보존).
- `.claude/scripts/tests/test_orchestrator.py` `test_p1_signal_muted_from_stdout`
  추가 — P1 임계 4회 강제 발화 후 stdout 빈 출력 + session_signal에 P1
  누적 검증.

### 자동 적용 항목

코드 수정은 harness-upgrade 3-way merge로 자동 적용.

### 수동 적용 항목

없음. 다운스트림이 P1 INFO 신호를 wrapper에서 의존하던 경우 호출부 수정
필요 (드문 케이스).

### 검증

```
python3 -m pytest .claude/scripts/tests/test_orchestrator.py -q
```

### 회귀 위험

upstream 격리 환경 관찰 범위 내: 기존 18 passed → 19 passed (+ P1 mute
회귀 가드 1건). P9 critical exit 2 시나리오 회귀 없음. detect_p1_same_file
로직 무변경 — signal_*.md 누적 그대로.

폐기 후보로 검토됐던 옵션 (orchestrator 전체 폐기·전면 재설계)는 진단
데이터(696줄 본체·Gemini 트리거·signal 7개 운용 가치 + 본 세션
false positive 100%가 본 세션 특수)로 부적합 판정. D 옵션 (stdout 필터링)
이 최소 비용·즉시 효용.

### 다운스트림 보고 요청

다음 upgrade 시 `migration-log.md` `## Feedback Reports`에 응답:

1. **P1 INFO 출력 빈도**: 본 변경 후 PreToolUse hook에서 P1 신호 stdout
   출력 횟수. 예: "10 wave 0건" / "1건 (예상 외)" / "미관측".
2. **P9 critical 차단 사례**: P1 mute 이후에도 P9 cascade 차단 정상
   동작하는지. 예: "P9 trigger 1건 정상 차단" / "0건".

---

## v0.46.0 — 퍼포먼스 baseline 측정 (5영역 1 commit, 2026-05-12)

### 변경 내용

§H 시리즈 마감 직후 5영역 baseline 박제 wave. 영역별 단축 wave는 본
baseline 데이터 보고 후 별 wave 결정.

- `.claude/scripts/measure_commit_latency.py` 신규 — git log에서 commit별
  추적성 라인(`🔍 review: <stage> | problem: P# | solution-ref: S#`)
  파싱, 시간 간격·stage 분포·problem 분포 종합. 인자: `N` (최근 N개) 또는
  `--since <rev>` (rev..HEAD).
- 본 세션 15 commit baseline 박제: stage 분포 (standard 5 / deep 3 / skip 3 /
  standard-self 3 / deep-unavailable 1), problem 분포 (P2 8 / P9 4 / none 3),
  commit 간격 평균 127분.
- hook overhead baseline: orchestrator 209ms / debug-guard 244ms /
  bash-guard 349ms / write-guard 101ms. Bash 매 호출에 orchestrator +
  bash-guard = 558ms 누적.
- eval_harness baseline: 278ms (45 lines 출력).
- review agent latency baseline: 4 review 평균 17.7s (standard stage, read
  budget 3회 이내 준수).

### 자동 적용 항목

`measure_commit_latency.py`는 신규 진단 도구. 다운스트림이 즉시 실행 가능 —
`python3 .claude/scripts/measure_commit_latency.py 20` 형태.

### 수동 적용 항목

없음. 본 wave는 측정 인프라 + baseline 박제만. 영역별 단축은 별 wave.

### 검증

```
python3 .claude/scripts/measure_commit_latency.py 15
```

### 회귀 위험

upstream 격리 환경 관찰 범위 내: `🔍 review:` 추적성 라인이 없는 옛 commit은
stage=?, problem=? 로 표시 (정규식 미매칭). 정상 동작.

본 wave 발견 결함 (별 wave 후보):
- commit log stage 값 정합 (`deep-unavailable`/`standard-self` 같은 자유
  표기 — 표준화 별 wave).
- review duration_ms가 git log에 박제 안 됨 (별 wave 후보).
- bash-guard 349ms × 매 Bash 누적이 가장 큰 단축 후보.

---

## v0.45.0 — §H-4~§H-11 묶음 wave (8 sub-task 1 commit, 2026-05-12)

### 변경 내용

사용자 명시 지시 "하나로 커밋, 쭈욱 진행" — followups 인덱스의 8 sub-task를
minimum viable change로 묶어 1 wave 1 commit 처리. 본 wave 종료로 followups
인덱스의 모든 sub-task 닫힘.

- **§H-4 Side Effect Ledger**: `docs_ops.py wip-sync` stdout에
  `cluster_updated`·`backrefs_updated` 추가 (yes|no 신호).
- **§H-5 Hook/Pre-check SSOT**: `pre_commit_check.py --print-secret-patterns`
  flag 추가. install 스크립트 hook block 통합은 별 wave 후속.
- **§H-6 Windows Commit Smoke**: `commit_smoke_windows.sh` 신규 — CRLF/
  shebang/git identity/PowerShell env 4축 검사.
- **§H-7 Cascade Integrity Check**: `pre_commit_check.py` stdout 끝에
  `cascade_check` 1줄 추가 (ERRORS 종합).
- **§H-8 wip-sync incident 역참조 갱신**: `_rewrite_relates_to`가 `../`
  prefix 매칭. §H-1·§H-2에서 발생하던 incident relates-to dead link 근본
  해소.
- **§H-9 .claude ↔ .agents SKILL 동기화 가드**: `TestAgentsBridgeSync` —
  두 SKILL 본문 동일(LF 차이 외) 회귀 가드.
- **§H-10 .sh 파일 LF 정규화**: `.gitattributes`에 `*.sh text eol=lf` 명시.
  `.claude/scripts/*.sh` 12개 워킹트리 LF 복원. autocrlf=true 환경에서
  pytest subprocess bash -n 실패 차단.
- **§H-11 README "최신 5개" 정책 자동 가드**: `harness_version_bump.py`
  stdout에 `readme_history_overflow` 검사 추가.

### 자동 적용 항목

파일 추가·수정은 harness-upgrade 3-way merge로 자동 적용된다. 신규 스킬
파일(`commit_smoke_windows.sh`)이 함께 배포되어 minor bump.

### 수동 적용 항목

다운스트림이 자체 wrapper로 wip-sync/pre_commit_check를 호출 중이라면 새
stdout 키 (`cluster_updated`/`backrefs_updated`/`cascade_check`/
`readme_history_overflow`)를 그쪽에서도 소비하도록 갱신 권장. install
스크립트의 hook block에 시크릿 패턴 통합은 본 버전에 포함 안 됨 — 별 wave
후속.

### 검증

```
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
bash .claude/scripts/commit_smoke_windows.sh
python3 .claude/scripts/pre_commit_check.py --print-secret-patterns
```

### 회귀 위험

upstream 격리 환경(Windows/Git Bash) 관찰 범위 내: pytest stage 7 passed
(+TestAgentsBridgeSync), smoke_pass 4/4. .sh 워킹트리 LF 복원은 사용자
환경 git config core.autocrlf 설정에 따라 다시 CRLF로 풀릴 수 있음 —
`git config core.autocrlf input` 권장. Linux/macOS 환경은 본 시점 미테스트.

본 wave는 거대 wave 금지 원칙의 사용자 명시 예외 — 8영역 review가 read
budget 한계로 전체 못 봄을 사용자가 수용한 trade-off. 영역별 회귀는 본 wave
회귀 가드 (`TestRouteOutput`/`TestSplitCommitNonDestructive`/`TestAgentsBridgeSync`)
와 smoke로 검증.

---

## v0.44.3 — split-commit.sh 비파괴 planner 전환 (2026-05-12)

### 변경 내용

§H-3 본 wave. split-commit.sh 기본 실행이 staged 상태를 변경하지 않는
non-destructive planner로 전환. `--apply` 시에만 기존 destructive 동작.
CRLF shebang 감지 안내 추가.

- `.claude/scripts/split-commit.sh`: 인자 파싱 (`--apply` 플래그) + 비파괴
  분기 + CRLF shebang 감지 함수 `check_crlf_sh`. 기본 실행은 분리 계획
  stdout 출력 후 즉시 종료 (staged 무변경). 재진입 흐름 (split-plan.txt
  존재)은 그대로 — 이미 --apply 흐름 진행 중.
- `.claude/skills/commit/SKILL.md` Step 5.5 호출부 갱신: 분리 계획 확인은
  무인자, 실제 분리는 `--apply` 명시.
- `.agents/skills/commit/SKILL.md` (Codex 브리지) 동본 동기화 (LF 유지).
- `.claude/scripts/tests/test_pre_commit.py`: `TestSplitCommitNonDestructive`
  추가 — 비파괴 로직 grep 정합 (APPLY=0·--apply 인자·CRLF 가드·destructive
  분기 위치).

### 자동 적용 항목

파일 수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. 다운스트림이 split-commit.sh를 자체 wrapper로 호출 중이라면
`--apply` 인자를 추가해야 기존 동작 유지. 무인자 호출은 plan만 출력하고
종료.

### 검증

```
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
bash .claude/scripts/split-commit.sh              # plan만, staged 무변경
bash .claude/scripts/split-commit.sh --apply      # destructive 진입
```

### 회귀 위험

upstream 격리 환경(Windows/Git Bash) 관찰 범위 내: split-commit.sh의 무인자
호출이 destructive에서 plan-only로 변경됨 — 기존 자동 split 흐름 의존하던
다운스트림 wrapper가 있다면 `--apply` 명시 갱신 필요. SKILL.md 호출부는
이미 갱신됨. Linux/macOS 환경은 본 시점 미테스트.

본 wave에서 발견된 부산물 결함 3건 (followups WIP §H-8/§H-9/§H-10 별 wave
후보 등록):
- §H-8: wip-sync 역참조 갱신이 incident 파일을 못 잡는 결함 (§H-1·§H-2
  연속 발생).
- §H-9: `.claude/skills/` ↔ `.agents/skills/` 동기화에 회귀 가드 없음.
- §H-10: `.sh` 파일이 CRLF로 저장되어 pytest subprocess `bash -n` 환경에서
  syntax 실패. `.gitattributes`에 `*.sh text eol=lf` + 일괄 변환 필요.

---

## v0.44.2 — commit SKILL이 route 출력 소비 (2026-05-12)

### 변경 내용

§H-2 본 wave. v0.44.1에서 freeze한 4축 6키 stdout(`commit_route`/
`review_route`/`promotion`/`side_effects.*`)을 commit SKILL이 실제로
소비하도록 본문 재작성. SKILL은 자연어 절차이므로 본 변경의 효과는
다음 commit부터 운용으로 검증.

- `.claude/skills/commit/SKILL.md` Step 4 (버전 체크): 진입 조건이
  `is_starter=true` 단독에서 `promotion=release`로 좁아짐.
  is_starter=true이지만 staged에 release 후보 파일(HARNESS.json /
  MIGRATIONS.md / README.md)이 없으면 본 Step skip → fast path.
- `.claude/skills/commit/SKILL.md` Step 5.5 (분리 판정): 1차 신호가
  `split_action_recommended` 에서 `commit_route` 로 전환. 분리 권고가
  있어도 사용자 명시(`HARNESS_SPLIT_OPT_IN=1`) 없으면 single 진행 +
  `AC-MIXED` 태그 (staging.md 정합).
- `.claude/skills/commit/SKILL.md` Step 7 (리뷰): 1차 신호가
  `recommended_stage` 에서 `review_route` 로 전환. recommended_stage는
  호환성 폴백 (review_route가 빈 경우만 사용).
- `.claude/skills/commit/SKILL.md` Step 8 push 요약: `side_effects.*` 3줄
  ledger 출력 절차 명시. 세 값 모두 none이면 요약 라인 생략 가능.
- `.agents/skills/commit/SKILL.md` (Codex 브리지) 동본 동기화. LF 유지.

### 자동 적용 항목

파일 수정은 harness-upgrade 3-way merge로 자동 적용된다. SKILL은 자연어
이므로 다운스트림 Claude/Codex가 본 SKILL을 다음 commit부터 따른다.

### 수동 적용 항목

없음. 다만 다운스트림이 SKILL 호출 흐름을 자체 wrapper로 감싸 자동화
중이라면 새 4축 stdout 키 (`commit_route`/`review_route`/`promotion`/
`side_effects.*`)를 그쪽에서도 소비하도록 갱신 권장.

### 검증

```
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
grep -n "review_route\|commit_route\|promotion\b\|side_effects" \
  .claude/skills/commit/SKILL.md
```

### 회귀 위험

upstream 격리 환경(Windows/Git Bash) 관찰 범위 내: pre-check stdout 키
스키마(§H-1)는 그대로, SKILL 본문만 1차 신호 변경. 옛 SKILL 운용 중인
다운스트림이 본 변경 적용 전까지 옛 신호(`recommended_stage`/
`split_action_recommended`/`is_starter` 단독)를 그대로 쓰며 호환성 폴백
경로가 유지됨. Linux/macOS 환경은 본 시점 미테스트. 다운스트림 운용
실측은 다음 wave 누적에서 별 wave 후보.

### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **fast path 진입 빈도**: 일반 코드/문서 커밋에서 promotion=none
   분기로 빠져 version bump·MIGRATIONS·README 갱신 절차를 건너뛴 횟수
   (`git log --grep "v0.44.[2-9]" | wc -l`로 누적 release 커밋 대비
   비교). 예: "10 commit 중 release 2, fast 8" / "미관측".
2. **commit_route 분기 행동**: split 권고를 single로 진행한 케이스에서
   `AC-MIXED` 태그가 commit 메시지에 들어갔는지. 예: "3건 모두 태그
   확인" / "태그 누락 1건" / "미관측".

