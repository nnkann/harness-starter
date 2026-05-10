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

## v0.42.1 — harness-upgrade silent fail 차단 보강 (FR-001/002/003) (2026-05-10)

### 변경 내용

다운스트림 v0.42.0 upgrade 측정에서 보고된 silent fail 3건의 알고리즘 갭
보강 (FR-001~003).

- **FR-001 (Step 5)**: 3-way merge 직전 base↔ours sanity check 추가.
  frontmatter `name:` 필드 변경 시 즉시 ALERT, base↔ours 라인 차이율 70%
  이상 시 본체 swap 의심 confirm 강제. 3택 (Y 통과 / N theirs 강제 교체 /
  S 파일 skip) 처리. 다운스트림 `eval/SKILL.md` 본체가 `implementation/SKILL.md`
  로 swap된 채 3회 upgrade 통과한 사례 차단
- **FR-002 (Step 9.6 신설)**: upstream 정합성 자동 검증 단계. starter 영역
  한정 `git diff harness-upstream/main HEAD --name-only` 실행 후 USER_OWNED_FILES
  / STARTER_SKILL_FILES / UNAPPLIED_FILES 3 카테고리 분류. 미적용 1건+ 시
  사용자 알림 + 처리 옵션(재실행 / 무시 / 중단). 다운스트림 v0.42.0에서
  30+ 파일이 silent 미적용 통과한 사례 차단
- **FR-003 (Step 10)**: 완료 보고에 사용자 전용 / starter_skills / upstream
  정합성 미도달 카운트 추가. Step 9.6 배열 length 그대로 주입(재계산 금지).
  미도달 1건+ 강조 + 파일 목록 + migration-log.md `### 이상 소견`에 자동
  append. 5+ 사용자 전용 항목은 요약 + 전체 보기 옵션
- **MIGRATIONS.md 표준**: `## Feedback Reports` 절에 "버전 섹션 표준"
  추가 — 6번 서브섹션 "다운스트림 보고 요청"(선택) 정의. 자동 검증 불가
  영역 보강 시 사용

근거 문서: `docs/decisions/hn_upgrade_silent_fail_guards.md` (이 wave 후 이동).

### 자동 적용 항목

- `.claude/skills/harness-upgrade/SKILL.md` (Step 5 본체 swap sanity check
  + Step 9.6 신설 + Step 10 보고 포맷 갱신)
- `docs/harness/MIGRATIONS.md` (`## Feedback Reports` 절에 버전 섹션 표준 추가)

### 수동 적용 항목

없음. 다음 upgrade 시 자동으로 새 절차 적용.

### 검증

```bash
grep -nE "본체 swap|차이율|name:" .claude/skills/harness-upgrade/SKILL.md
grep -nE "정합성 미도달|UNAPPLIED_FILES" .claude/skills/harness-upgrade/SKILL.md
grep -nE "버전 섹션 표준|다운스트림 보고 요청" docs/harness/MIGRATIONS.md
```

### 회귀 위험

- upstream 격리 환경에서 SKILL.md 절차 변경만 검증. 실제 3-way merge
  sanity check 동작은 다음 다운스트림 upgrade에서 운용 측정 필요
- base↔ours 차이율 70% 임계는 이론값. false-positive·false-negative 분포는
  다운스트림 측정으로만 확인 가능 (의도된 대규모 리팩토링과 본체 swap
  구분이 임계 안에서 가능한지 미실증)
- Step 9.6 USER_OWNED_FILES 정의(naming/coding/docs.md 한정)가 다운스트림
  실제 사용자 전용 영역과 정합한지 미실증. 다운스트림이 다른 파일을 정당
  커스터마이징하면 미도달로 오분류 가능 — 보고 채널 1로 측정 예정

### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **Step 5 본체 swap sanity check 발화 빈도**:
   - 검사 1(`name:` 필드 변경 ALERT) 발화 횟수 / 검사 2(차이율 ≥70% 의심) 발화 횟수
   - 사용자 3택 결과 분포: Y(통과) / N(theirs 강제) / S(skip)
2. **Step 9.6 정합성 미도달 카운트**:
   - USER_OWNED_FILES / STARTER_SKILL_FILES / UNAPPLIED_FILES 각 카운트
   - 미도달 1건+ 시 사용자 선택: 재실행 / 무시 / 중단
3. **Step 10 보고 가독성 + 자가 발화 의존 잔존 여부**:
   - "정합성 미도달" 강조가 사용자 인지에 도달했는가
   - 사용자가 보고를 보고 추가 액션을 취했는가
   - silent 제외 카운트가 "이게 진짜 보존 맞나?" 검토를 유발했는가

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷(관점·약점·실천·심각도).

---

## v0.42.0 — eval --harness CLI 백엔드 + 검증 도구 정렬 진단 (2026-05-10)

### 변경 내용

eval --harness가 LLM 해석 의존이던 결정적 측정 항목을 CLI 백엔드(`eval_harness.py`)
로 이전. 단일 진입점에서 항목 5(CPS 무결성)·6(방어 활성)·7(피드백 리포트)·
8(검증 도구 정렬 신규)을 결정적으로 실행. SKILL.md 본문은 LLM 해석 영역
(항목 1~4: 모호성·모순·부패·강제력 배치)만 담당.

신규 항목 8(검증 도구 정렬 진단)은 TypeScript/JavaScript 프로젝트에서
검증 도구가 산출물(dist/build)이 아닌 소스를 직접 보도록 보장 — 4신호
(A 워크스페이스·B codegen 의존·C dist 자체 소비·D outDir 분리) 검출 후
신호 hit 패키지의 정렬 상태 측정. 외부 명령(npm·tsc) 호출 0건 (Python·Go·
Rust 다운스트림 차단 회피).

본 wave는 직전 wip_util_ssot(v0.41.0) 결정의 후속 의무 박제 — eval_harness.py가
wip_util import해서 4중 파편화 방지.

근거 문서: `docs/decisions/hn_eval_harness_cli_lsp_drift.md` (이 wave 후 이동).

### 자동 적용 항목

- `.claude/scripts/eval_harness.py` (신설 — CLI 백엔드 단일 진입점)
- `.claude/scripts/tests/test_eval_harness.py` (신설 — 7건 회귀 가드)
- `.claude/scripts/tests/conftest.py` (`eval` marker 등록)
- `.claude/skills/eval/SKILL.md` (--harness 섹션 재구성 + 항목 8 추가)
- `.claude/HARNESS_MAP.md` (Scripts 섹션 갱신: stop-guard.py·post-compact-guard.py·
  eval_harness.py·test-bash-guard.sh·test-debug-guard.sh 등재)

### 수동 적용 항목

없음. eval --harness 호출 흐름이 자동으로 새 CLI 백엔드를 사용. 구버전
호환을 위해 `eval_cps_integrity.py` 직접 호출도 그대로 작동.

### 검증

```
python3 .claude/scripts/eval_harness.py
# 항목 5·6·7·8 보고 출력 (TypeScript 미사용이면 항목 8 SKIP)
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q
# 7 passed
```

### 회귀 위험

- upstream 격리 환경(Windows + Git Bash + Python 3.12)에서 관찰된 범위 내 검증
- 항목 8(검증 도구 정렬)은 TypeScript 프로젝트가 없는 starter에서는 SKIP만
  실증됨. 실제 모노레포 + codegen 환경의 신호 검출은 미테스트 (픽스처 단위
  테스트만 통과)
- `.claude/harness-overrides.md` 의도적 비정렬 마커는 명세만 정의. 실제
  다운스트림 운용 검증은 미수행

---

## v0.41.0 — WIP 파싱 SSOT 통합 (wip_util.py + post-compact-guard.py 전환) (2026-05-10)

### 변경 내용

WIP frontmatter 파싱 로직이 3곳에 파편화돼 있던 상태(session-start.py·
post-compact-guard.sh·stop-guard.py)를 단일 SSOT(`utils/wip_util.py`)로
통합. 동시에 `post-compact-guard.sh`를 Python으로 전환해 sed/grep/awk
혼재 제거.

stop-guard 자기복제 케이스가 다른 sh에 적용되는지 14개 sh 점검 결과,
적합 1건(post-compact-guard.sh) + 부적합 12건. 1차 결론에서 사용자 통찰
("언어 전환이 아닌 로직 통합")로 SSOT 부재가 진짜 원인이라는 결론에
도달, 본 wave에서 점검·결정·실행을 단일 commit으로 처리.

근거 문서: `docs/decisions/hn_wip_util_ssot.md` (이 wave 후 이동).

### 자동 적용 항목 (다운스트림이 fetch 시 자동)

- `.claude/scripts/utils/__init__.py` (신설)
- `.claude/scripts/utils/wip_util.py` (신설 — `parse_wip_file()` + `is_in_progress()` SSOT)
- `.claude/scripts/session-start.py` (parse_wip_file 정의 제거 → import)
- `.claude/scripts/stop-guard.py` (is_in_progress 정의 제거 → import)
- `.claude/scripts/post-compact-guard.py` (신설 — sh 1:1 포팅)
- `.claude/scripts/post-compact-guard.sh` (삭제 — dead code 동시 제거)

### 수동 적용 항목

1. `.claude/settings.json` PostCompact hook command 갱신
   `bash .claude/scripts/post-compact-guard.sh` → `python3 .claude/scripts/post-compact-guard.py`
   (settings.json을 다운스트림이 자체 커스터마이즈한 경우 3-way merge 후 확인)
2. `bash .claude/scripts/post-compact-guard.sh`를 호출하는 외부 스크립트가
   있으면 동일하게 갱신 (downstream-readiness.sh가 hook 누락 자동 감지)

### 검증

```
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); from utils.wip_util import parse_wip_file"
echo '{}' | python3 .claude/scripts/post-compact-guard.py
python3 .claude/scripts/session-start.py
echo '{}' | python3 .claude/scripts/stop-guard.py
```

### 회귀 위험

- upstream 격리 환경(Windows + Git Bash + Python 3.12)에서 관찰된 범위 내 검증
- Linux/macOS·다른 Python 버전 미테스트
- WSL·Docker·CI 등 다른 실행 환경의 sys.path 동작 미검증
- 다운스트림이 `.claude/scripts/utils/` 경로에 자체 모듈을 두던 경우 충돌
  가능성 (현재 업스트림에서는 utils/ 폴더 부재였음)

---

## v0.40.2 — stop-guard.py / session-start.py cwd 보정 (2026-05-10)

### 변경 내용

v0.40.1 직후 Stop hook 실행 시 `python3 .claude/scripts/stop-guard.py`가
`.claude/scripts/.claude/scripts/stop-guard.py`로 이중 prepend되어 ENOENT
발생. Windows + Claude Code 환경에서 Stop hook의 cwd가 repo root가 아닌
`.claude/scripts/`로 들어오는 케이스 실측. 이전 `bash .sh` 시절에는 우연히
동작했을 가능성 있으나 .py 전환 후 즉시 노출.

- `.claude/scripts/stop-guard.py` — `os.chdir(Path(__file__).resolve().parents[2])`
  cwd 보정 1줄 추가 (import 직후)
- `.claude/scripts/session-start.py` — 동일 안전망 추가 (현재는 정상
  작동하나 동일 패턴 일관성)

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
cd .claude/scripts && python3 stop-guard.py    # ENOENT 없이 정상 출력
cd .claude/scripts && python3 session-start.py # 정상 출력
```

### 회귀 위험

upstream 격리 환경(Windows + Git Bash) 실측에서는 cwd 보정이 정상 작동
범위 내. Linux/macOS에서 hook cwd 거동은 미테스트 — 다른 OS의 Claude
Code hook이 cwd를 어떻게 설정하는지에 따라 redundant할 수 있으나 무해
(이미 repo root이면 chdir도 repo root). `__file__` 기반 절대경로라
cwd 무관하게 결과 동일.

downstream: harness-upgrade 적용 후 hook 재발화 시 ENOENT 사라짐 확인 권장

---

## v0.40.1 — stop-guard.sh → stop-guard.py 전환 (자기증식 차단) (2026-05-10)

### 변경 내용

v0.40.0 stop-guard.sh 도입 직후 검증에서 `grep -c || echo 0` Git Bash
호환 결함 발견·1회 fix. 이 1회 fix가 자기증식 신호 — bash 파싱 3종 혼재
(awk×2·grep×2)에 추측성 방어 코드 누적이 향후 조건 확장마다 증가할
구조. pre-emptive Python 전환:

- `.claude/scripts/stop-guard.py` 신설 — bash 4개 동작 절 1:1 포팅
  (미커밋 카운트·in-progress WIP·조건 A·B·C AND 발화·memory 환기/cleanup)
- `.claude/scripts/stop-guard.sh` 삭제 (signal_dead_code_after_refactor.md
  답습 — 호출 제거와 정의 제거 동시)
- `.claude/settings.json` Stop hook command 갱신: `bash` → `python3`
- session-start.py와 일관된 frontmatter 파싱 패턴 + Windows cp949 안전
  처리 동일 답습

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
python3 .claude/scripts/stop-guard.py
# 기존 sh와 동일 출력 4개 절 + 조건 A·B·C hit 시 stderr + audit log
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 sh·py 출력 1:1 일치 확인 (trailing
  space 제외). Linux/macOS 미테스트
- audit log 형식 호환 (`{ts} | A·B·C hit | {files}` 동일) — 기존 누적
  로그 무수정
- Python interpreter 시동 비용 ~50~100ms — session-start.py와 동일
  운용 검증된 비용
- settings.json hook command 1줄 변경 — Reversibility 5/5 (원복 비용 0)

