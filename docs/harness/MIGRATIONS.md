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

## v0.44.1 — pre_commit_check route 출력 추가 (2026-05-12)

### 변경 내용

`harness--hn_commit_perf_optimization.md` §H-1을 본 wave로 좁혀 처리한
첫 닫힘. SKILL은 손대지 않고 stdout 신호만 추가 — 다음 wave (§H-2 commit
SKILL이 route 소비)의 입력 계약을 freeze한다.

- `pre_commit_check.py`: stdout 끝에 6개 키 추가 — `commit_route`
  (single|sub), `review_route` (skip|micro|standard|deep), `promotion`
  (none|release|repair), `side_effects.required`, `side_effects.release`,
  `side_effects.repair`.
- `promotion=release` 판정: `is_starter=true` + staged 파일에
  `.claude/HARNESS.json` / `docs/harness/MIGRATIONS.md` / `README.md`
  포함. 그 외 `none`. `repair`는 §H-5(hook SSOT 통합)에서 활성화.
- `side_effects.required`: staged WIP 있으면 `docs_ops.wip-sync` 후보로
  마킹. 없으면 `none`.
- `test_pre_commit.py`: `TestRouteOutput` 클래스 추가 (3 테스트) —
  기본 케이스에서 6키 출력 + 기존 키 회귀 없음, 시크릿 차단 시에도
  4축 공존, release 후보 staging에서 `promotion=release` 발화.
- WIP 분리: `harness--hn_commit_perf_followups.md` 신설 (§H-2~7 인덱스).

### 자동 적용 항목

파일 수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. 본 wave는 stdout 신호만 추가하며 commit SKILL이 아직 소비하지
않는다 — 운용 행동 변화 0.

### 검증

```
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
python3 .claude/scripts/pre_commit_check.py
```

### 회귀 위험

upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내: 기존 13개
stdout 키 보존 (TestStageBasic 2개 통과로 검증), 새 6키 추가만. stdout
parser가 미지의 키를 무시하는 구조면 다운스트림 영향 0. parser가 키 화이트
리스트를 강제하는 경우 신규 키를 인식하지 못하지만 그 자체는 차단 사유
아님. Linux/macOS 환경은 본 시점 미테스트.

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

---

## v0.43.2 — gemini_delegation_pipeline Phase 1 (CPS Solution 변경 자동 Gemini 의견) (2026-05-11)

### 변경 내용

gemini_delegation_pipeline 결정 Phase 1 박제. orchestrator.py에 CPS
Solution 변경 staged 시 gemini CLI 자동 호출 트리거 추가.

- `detect_solution_change()` 신설 — `git diff --cached
  docs/guides/project_kickoff.md` Solutions 섹션 변경 detect
- `gemini_cli_available()` — `shutil.which("gemini")` 확인. 미설치 시
  graceful skip (다운스트림 cascade 영향 0 보장)
- `call_gemini_background()` — detach subprocess. PreToolUse hook 지연
  없이 반환. 결과 `.claude/memory/gemini-solution-review.md`
- 세션당 1회만 호출 — `gemini_solution_review_called` 플래그
- INFO 신호로 사용자 알림. Critical 아님 — 권고 수준

회귀 가드 3건 신설 — CLI 미설치 skip·Solutions 미변경 skip·세션당 1회.
전체 10/10 통과 (기존 7 + 신규 3).

`docs/decisions/hn_gemini_delegation_pipeline.md` Phase 분리 결정 박제 +
completed 전환. Q1~Q6 본 wave 합의 (Phase 1 객관 신호 트리거만 구현,
Phase 3 의미 신호·PostToolUse review verdict 트리거는 별 wave 후보).

### 적용 방법

자동 적용. gemini CLI 설치 안 한 다운스트림은 무영향.

설치한 환경에서만 작동:
- gemini CLI 0.41+ + OAuth 인증 (`gemini` 첫 실행 시 자동)
- 또는 `GEMINI_API_KEY` 환경 변수

### 검증

```
pytest .claude/scripts/tests/test_orchestrator.py -v
# 10/10 통과
```

### 회귀 위험

upstream 격리 10/10 통과. Solution 변경 detect의 false-positive 가능 —
Solutions 섹션 외 P# 섹션 변경에 hit하지 않도록 heuristic 적용했으나
완벽하지 않음. 실측 누적 후 정밀화 필요.

OAuth quota 일 한도 도달 시 호출 실패 — Popen detach라 오류가
사용자에게 안 노출. 결과 파일이 비어 있으면 quota 또는 timeout 의심.

---

## v0.43.1 — orchestrator P1 신호 stale 누적 해소 (upsert) (2026-05-11)

### 변경 내용

v0.43.0 직후 실측 — orchestrator.py 자기 수정·README 수정마다 P1 INFO
신호가 count 변화별로 별도 누적되어 PreToolUse 컨텍스트에 stale 신호 3건
이상 동시 출력 (3회·4회·5회가 각각 별도 신호). session 길어질수록 노이즈
증폭.

원인: `deduplicate_signals`가 `(p_id, message)` 키 사용 — count 변화 시
message 문자열 달라져 새 식별자로 인식 → upsert 안 됨.

해소:
- 신호에 `key` 필드 (예: `"P1:{file_path}"`) 추가 — count 무관 안정 식별자
- `_signal_key()` 헬퍼: `key` 보유 시 upsert, 미보유 시 `(p_id, message)`
  fallback (P9 등 정적 신호 호환)
- `deduplicate_signals` 재작성 — `key` 일치 시 기존 신호 교체

### 적용 방법

자동 적용. 기존 다운스트림 session_signal.json은 새 형식과 호환
(fallback 동작) — 첫 P1 발화 시 자동 upsert 키 부여로 점진 정리.

### 검증

```
pytest .claude/scripts/tests/test_orchestrator.py -v
# 7/7 통과 (기존 5 + 신규 upsert·dedup fallback 2)
```

### 회귀 위험

upstream 격리 환경 7/7 통과. 기존 stale 신호가 session_signal.json에
누적된 다운스트림은 한 번 reset 권장 (`rm .claude/session_signal.json`)
또는 다음 새 신호 발생 시 자동 정리.

