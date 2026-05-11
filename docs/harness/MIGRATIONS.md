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

---

## v0.43.0 — 오케스트레이터 MVI 도입 (PreToolUse hook + P9 강제 cascade) (2026-05-11)

### 변경 내용

P9 (정보 오염의 관성)·S9 (주관 격리 + 다층 검증) 결정 시리즈의 실측
구현. `scripts/orchestrator.py` + PreToolUse hook 등록으로 LLM 자가
발화 의존을 커널 강제로 전환.

- `.claude/scripts/orchestrator.py` 신설 (~290줄) — P1·P9 객관 신호
  detect 엔진. stdin JSON 파싱 + WIP frontmatter ↔ CPS Problems 매칭
  + 동일 파일 연속 수정 카운터. 이중 안전장치: stdout
  `additionalContext` + `.claude/session_signal.json` 파일 쓰기.
- `.claude/settings.json` — PreToolUse hook에 matcher 없는(모든 도구)
  orchestrator.py 등록 추가
- `.claude/rules/docs.md` — Layer 2 도구 frontmatter `trigger:` 필드
  스키마 + 명명 규칙·금지 패턴 정의
- `.gitignore` — `.claude/session_signal.json` 런타임 상태 격리
- `.claude/scripts/tests/conftest.py` — `orchestrator` marker 등록
- `.claude/scripts/tests/test_orchestrator.py` — 회귀 5케이스
- `docs/WIP/decisions--hn_orchestrator_mechanism.md` — 결정 박제
  (Gemini 2차 위임 결과 반영, Exit 2 강제 중단 합의)

P9 cascade 깨짐 (WIP frontmatter `problem` ↔ CPS Problems 매칭 실패)
detect 시 **Exit 2 강제 중단** — Praetorian 8계층 모델 + arXiv:2503.13657
"Ignored other agent's input" 실패 모드 차단.

### 적용 방법

다운스트림은 harness-upgrade 후 다음 자동 적용:
- `scripts/orchestrator.py` 배포
- `.claude/settings.json` PreToolUse hook 등록 (3-way merge)
- `.gitignore` `.claude/session_signal.json` 추가

수동 액션 — **있음**:
- 첫 실행 시 `.claude/session_signal.json` 자동 생성됨 (Claude가 도구
  호출 시점에). 별도 작업 불필요
- 다운스트림이 자체 P 신호 추가 원하면 후속 wave의 `P_DEFINITIONS.json`
  확장 인터페이스 사용 예정 (v0.43.0은 P1·P9만)
- P9 Critical detect로 Claude 도구 호출이 차단될 수 있음 — WIP
  frontmatter `problem` 필드가 CPS Problems 목록에 등록됐는지 확인 필수

### 검증

```
python3 -m py_compile .claude/scripts/orchestrator.py
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 .claude/scripts/orchestrator.py
pytest .claude/scripts/tests/test_orchestrator.py -v
```

### 회귀 위험

upstream 격리(Windows / Git Bash)에서 관찰된 범위 내에서는 5/5 통과.
다른 OS·셸 환경 미테스트. WIP frontmatter `problem` 필드가 CPS Problems
미등록인 다운스트림에서 Critical exit 2가 빈발할 가능성 — 다운스트림
첫 적용 시 마찰 측정 필요.

---

## v0.42.7 — starter 자가 모호성·박제 일괄 흡수 (다운스트림 노이즈 차단) (2026-05-11)

### 변경 내용

다운스트림 `/eval --harness` 보고가 다수 다운스트림에서 반복될 것이라는
구조 인식에 따라 starter 자체 결함을 선제 흡수. starter 자가 정의한
모호성 패턴을 자기 SKILL.md가 위반하는 자기증명 P7 잔재 + 박제 인용 3건
+ CPS Solution 정의 갭을 한 wave에 정리.

**1. eval/SKILL.md 모호성 정의 정밀화**:
- "필요하면"·"가능하면" 등 조건문은 모호성 아님 — false-positive 차단
- 새 분류: 판단 기준 부재(`적절한·상황에 따라·알아서`) vs 수치 부재(`짧게·간결하게`) vs 열거 불완전(`등·기타`)
- 조건문 제외 명시 절 추가

**2. SKILL.md 5건 수치·분기 명시**:
- `eval/SKILL.md:110` "간결하게 유지" → "거시·블로커·부채 3섹션, 각 5줄 이내"
- `eval/SKILL.md:445` (implementation) "간결하게" → "본문 50줄 이내 권장"
- `harness-upgrade/SKILL.md:23` "가능하면 3-way merge" → "기본은 3-way, 충돌 시 사용자 결정 요청"
- `write-doc/SKILL.md:120` "snake_case 의미명, 간결하게" → "단어 2~4개, 30자 이내"
- `implementation/SKILL.md:408` "자동으로 적절한 폴더" → "WIP 파일명의 `{대상폴더}--` 접두사 기준 라우팅"

**3. CPS P7 본문 보강 + S7 의도적 미정의 명시**:
- P7 본문에 "Solution 의도적 미정의 — HARNESS_MAP.md 메커니즘 자체가 P7 해소" 명시
- S6·S8은 정의 유지. S7 자리는 별도 Solution 정의 안 함 (중복 추상화 방지)

**4. 박제 인용 3건 흡수**:
- `hn_eval_harness_medium_fixes.md`: S6 인용 `(M, ≥3줄)` 보강어 누락 → CPS 본문 정확 substring으로 교체
- `hn_stop_guard_py_migration.md`: S7 미정의 → S6(self-verify SKIP 조건 명확화) 재매칭
- `hn_wip_util_ssot.md`: 동일

검증: pytest 92 passed / 4 skipped, eval_cps_integrity 박제 의심 0건.

### 자동 적용 항목

- `.claude/skills/eval/SKILL.md` (모호성 정의 + 보고 형식)
- `.claude/skills/harness-upgrade/SKILL.md`, `write-doc/SKILL.md`, `implementation/SKILL.md`
- `docs/guides/project_kickoff.md` (P7 본문 보강)
- `docs/decisions/hn_eval_harness_medium_fixes.md`, `hn_stop_guard_py_migration.md`, `hn_wip_util_ssot.md` (박제 인용 수정)

### 수동 적용 항목

없음.

### 검증

```bash
python -m pytest .claude/scripts/tests/ -q
# 92 passed / 4 skipped

python .claude/scripts/eval_cps_integrity.py
# 박제 의심: 0건
```

### 회귀 위험

upstream 격리 환경에서 회귀 없음. SKILL.md 수치 변경은 자가 보고 안내 수치
— Claude 행동 변화는 자동 검증 불가. 운용 검증 필요.

### 다운스트림 영향

starter 발 모호성·박제가 누적될수록 다운스트림 N개에서 같은 보고가 N회
반복됨. 본 wave는 그 노이즈를 starter 측에서 선제 흡수한 것 — 다운스트림이
본 patch 적용 후 `/eval --harness` 재실행 시 starter 발 false-positive
일부 해소 예상.

---

## v0.42.6 — eval_cps_integrity FR 필드 정규식 bold 내부 괄호 보강 (FR-010) (2026-05-11)

### 변경 내용

`_field_present` 정규식이 bold 마커 **내부 괄호 보강어** 양식을 인식하도록
확장. 다운스트림 실측 양식 `**약점 (부분 작동)**:`이 v0.42.4 정규식에서
미매칭으로 오경보 발생 — FR-010 응답.

**변경 전 (v0.42.4)**:
```
\*\*{name}\*\*\s*:
```
필드명 직후 닫는 `**`만 허용. `**약점 (부분 작동)**:` 미매칭.

**변경 후 (v0.42.6)**:
```
\*\*{name}(?:\s+\([^)]*\))?\*\*\s*:
```
필드명 뒤 선택적 1단 괄호 그룹 허용. 중첩 괄호 미지원 (`[^)]*`).

### 적용 방법

- 자동: `harness-upgrade`로 `.claude/scripts/eval_cps_integrity.py` 덮어쓰기 자동
- 수동: 없음

### 검증

```bash
python -m pytest .claude/scripts/tests/test_eval_harness.py -q
# 14 passed (기존 12 + 신규 2: bold_inner_paren positive + prose negative gate)
```

### 회귀 위험

upstream 격리 환경에서 관찰된 범위 내에서는 회귀 없음 (전체 92 passed / 4 skipped).
산문 false-positive 가드 테스트 추가로 정규식 과확장도 방어. 중첩 괄호 양식
(`**X ((sub))**:`)은 의도적으로 미지원 — 자연어 양식에서 1단으로 충분 판단.

### Feedback Reports

#### FR-010 (2026-05-11)

**관점 (정규식 양식 갭)**: v0.42.4가 3양식(bold·plain·헤더 인라인) 양면 매칭을 표방했으나 bold 양식 내부 괄호 보강어 변형을 닫지 못함.
**약점 (부분 작동)**: 다운스트림 실측 양식 `**약점 (부분 작동)**:`이 미매칭. FR-007 응답이 한 양식만 닫고 인접 변형 미고려.
**실천 (정규식 보강)**: 필드명 뒤 선택적 괄호 그룹 `(?:\s+\([^)]*\))?` 허용. false-positive 가드 회귀 테스트 동반.
**심각도 (low)**: 검출 갭이지만 보안·데이터 영향 없음. 다운스트림 운용 피드백 채널 자연 회복.

