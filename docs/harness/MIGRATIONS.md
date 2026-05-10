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

---

## v0.42.5 — wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단 (2026-05-11)

### 변경 내용

매 commit 직후 `docs/clusters/*.md` + 이동된 `docs/{decisions,...}/*.md`
2건이 unstaged 잔여로 남던 결함 차단. v0.42.1~42.4 모두 동일 잔여 발생
(starter 본인 5회 자기증명 = P6 검증망 스킵의 메커니즘 변종).

진단 결과 (코드 직접 Read):
- `cmd_cluster_update` (L499): `cluster.write_text(...)` 후 git add 0건 호출
- `cmd_move` (L350): `git mv`는 rename만 staging — 그 후 `write_frontmatter_field`
  (status·updated) 갱신은 working tree만 수정되어 unstaged
- `cmd_reopen` (L400): `cmd_move`와 동일 패턴

보강:
- 세 함수 모두 갱신 직후 `subprocess.run(["git", "add", str(...)], capture_output=True)` 추가
- `commit_finalize.sh` 주석 정정 — 기존 "`cmd_cluster_update`가 git add 호출"
  거짓 박제를 실제 코드와 정합한 설명으로 교체
- 회귀 가드 신설: `test_docs_ops_staging.py` 3건 (cluster_update / move / reopen).
  tmp_path + git init fixture로 격리. `git diff --cached`에 대상 파일 hit +
  unstaged 잔여 0건 검증

전체 90 passed (87 → 90, 회귀 0).

근거 문서: `docs/decisions/hn_wip_sync_staging_gaps.md`.

### 자동 적용 항목

- `.claude/scripts/docs_ops.py` (`cmd_cluster_update` + `cmd_move` + `cmd_reopen`)
- `.claude/scripts/commit_finalize.sh` (주석 정정)
- `.claude/scripts/tests/test_docs_ops_staging.py` (회귀 가드 3건 신설)

### 수동 적용 항목

없음. 다음 `/commit` 호출부터 자동으로 새 staging 흐름 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_docs_ops_staging.py -v
# 3 passed
python3 -m pytest .claude/scripts/tests/ -q
# 90 passed (회귀 0)

# 메타 검증 — 본 commit 직후 git status 깨끗하면 v0.42.5 보강이 자기 첫
# 적용 사례에서 즉시 작동 입증
git status --short
```

### 회귀 위험

- 회귀 가드 3건 + 전체 90 passed (회귀 0) 확인
- `capture_output=True`로 stderr·stdout 묻음 — git add 실패해도 commit 흐름은
  진행. 실패 시 잔여 발생으로 가시화 (자기검증)
- 한 cluster·dest 파일을 두 번 git add하는 케이스 가능 (cmd_move + 후속
  cmd_cluster_update 호출 시) — git add는 멱등이라 영향 없음
- tmp_path 회귀 테스트가 Windows 환경 한정 검증. Linux/macOS hook cwd 거동
  미테스트 — git subprocess 호출 표준이라 영향 미약

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **commit 직후 `git status --short` 결과**: v0.42.5 적용 후 첫 commit
   직후 잔여 파일 수. 0건이 정상. 1건+ 이면 starter 본인이 검증 못 한
   추가 결함 (보고 필수)

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.

---

## v0.42.4 — eval_cps_integrity 필드 매칭 정규식 다양성 확보 (FR-007) (2026-05-11)

### 변경 내용

다운스트림 v0.42.3 적용 측정 FR-007 후속 처리. 직전 wave에서 헤더 양면
매칭은 보강했으나 필드 substring 검사가 좁아 다운스트림 양식의 6건 모두
"⚠ 심각도 없음" 오경보 발생.

- **`check_feedback_reports` 필드 매칭 보강**: `required_fields` substring
  검사 → `_field_present` 헬퍼의 정규식 검사로 교체. 4 필수 필드(관점·약점·
  실천·심각도) 모두 3 양식 양면 매칭:
  - bold 마커: `**필드**:`
  - plain: `필드:` (한국어 단어 경계 lookbehind로 부분 단어 매칭 방지)
  - 헤더 인라인: `(필드:` 괄호 안
- **회귀 가드 신설**: `test_feedback_reports_inline_header_severity` 추가.
  `#### FR-NNN ... (심각도: medium — ...)` 헤더 인라인만 있고 본문에
  `**심각도**:` 별도 라인 없는 케이스도 정상 검출 (`FR-NNN ✅`)
- 12 passed (기존 11 + 신규 1) / 전체 87 passed / 회귀 0

근거 문서: `docs/decisions/hn_eval_harness_medium_fixes.md` Phase 3 + 변경 이력.

### 자동 적용 항목

- `.claude/scripts/eval_cps_integrity.py` (`_field_present` 헬퍼 + 정규식 매칭)
- `.claude/scripts/tests/test_eval_harness.py` (회귀 가드 1건 추가)

### 수동 적용 항목

없음. 다음 `eval --harness` 호출부터 자동 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -v
# 12 passed (기존 11 + 신규 1)
```

### 회귀 위험

- 정규식 한국어 단어 경계는 `(?<![\w가-힣])` lookbehind로 처리 — 부분 단어
  오탐 방지. 다른 한국어 위치(예: "관점 비교") 본문에서 우연히 hit할 가능성
  있으나 본 함수는 FR 블록 한정 검사라 영향 미약
- bold 마커 + plain + 헤더 인라인 외 다른 양식(예: 굵은 점만 `• 심각도: medium`,
  HTML `<b>심각도</b>:`)은 미인식. 본 보강은 v0.42.1 가이드 양식 + 다운
  스트림 실측 양식 두 케이스 커버

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **`eval --harness` 항목 7 출력**: v0.42.4 적용 후 다운스트림 6건 FR이
   `FR-NNN ✅`로 정상 검출되는가? (이전 6건 "⚠ 심각도 없음" 오경보 → 0건)
2. **다른 양식 발견 여부**: bold/plain/헤더 인라인 외 다른 필드 양식이
   본 다운스트림 migration-log.md에 존재하는가?

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.

---

## v0.42.3 — eval_cps_integrity Feedback Reports 인식 보강 + self-verify 모호성 정밀화 (2026-05-10)

### 변경 내용

다운스트림 v0.42.1 적용 후 측정된 eval --harness 결과 medium 우선순위 정비.

- **5-4 (eval_cps_integrity.py)**: `check_feedback_reports`의 정규식이
  `## Feedback Reports` (top-level 헤더)만 매칭하던 결함을 `### Feedback Reports`
  (버전 섹션 내 서브헤더) 양면 매칭으로 보강. FR 헤더 레벨도 `### FR-NNN` +
  `#### FR-NNN` 양면 지원. 같은 FR ID 중복 방지(set). 다운스트림이 어느
  양식을 써도 FR 항목 검출되도록 자율성 보존
- **5-4 회귀 가드**: `test_eval_harness.py`에 4건 추가 (top-level / 서브헤더 /
  필수 필드 누락 / 파일 부재). 11/11 통과
- **5-5 (self-verify.md)**: "**가능하면:** dev 서버 부팅" 모호 표현을
  "**UI/frontend 변경 시 필수**" + "**그 외(백엔드·CLI·문서·hooks·스크립트) 선택**"
  명확 트리거로 정밀화. CLAUDE.md "UI 또는 frontend 변경" 원칙과 정합

근거 문서: `docs/decisions/hn_eval_harness_medium_fixes.md`.

### 자동 적용 항목

- `.claude/scripts/eval_cps_integrity.py` (`check_feedback_reports` 정규식 + 파싱 로직)
- `.claude/scripts/tests/test_eval_harness.py` (회귀 가드 4건 추가)
- `.claude/rules/self-verify.md` (검증 항목 트리거 명확화)

### 수동 적용 항목

없음. 다음 `eval --harness` 호출부터 자동으로 새 인식 로직 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -v
# 11 passed (기존 7 + 신규 4)
grep -nE "UI|frontend" .claude/rules/self-verify.md | head -3
```

### 회귀 위험

- 회귀 테스트 4건 통과 + 전체 86 passed 확인 (Phase 1 + Phase 2 회귀 0)
- 다운스트림 양식이 `## Feedback Reports` (top-level) + `### Feedback Reports`
  (서브헤더) 외 다른 헤더 레벨(예: `# Feedback Reports`)을 쓰면 미인식. 본
  보강은 v0.42.1 가이드 양식과 다운스트림 실측 양식 두 케이스만 커버
- 한 migration-log.md에 같은 FR-NNN ID가 여러 섹션에 출현하면 첫 번째만
  인식 (set으로 중복 방지). 의도된 설계 — 다른 ID라면 둘 다 출력

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **eval --harness 항목 7 출력**: v0.42.3 적용 후 `eval --harness` 실행 시
   migration-log.md의 FR 항목이 정상 검출되는가? (FR-NNN ✅ 또는 ⚠️ 출력)
2. **양식 정합성**: 다운스트림 migration-log.md의 헤더 레벨 (top-level
   `## Feedback Reports` vs 서브헤더 `### Feedback Reports`) 어느 쪽이 사용되는지

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.

