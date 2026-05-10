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

### eval --harness 검증 항목

`eval --harness` 실행 시 migration-log.md의 Feedback Reports 포맷을 검증한다:

- FR 항목이 있을 때: `관점`·`약점`·`실천`·`심각도` 4개 필드 모두 존재하는지 확인
- 필드 누락 시: `⚠️ FR-NNN: [누락 필드] 없음` 경고
- FR 항목이 없을 때: `피드백 리포트: 없음 ✅` 통과

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

---

## v0.40.0 — P8 Phase 3: incident 회상 + signal lifecycle + stop-guard 조건 C (2026-05-10)

### 변경 내용

P8 자가 의존 보강 3축 1차 도입 (advisor + 사용자 라운드 합의):

- **D-Lite — `session-start.py` `section_incidents()` 신설**: 현재 WIP
  frontmatter `domain` ∩ `docs/incidents/*.md` `domain`, 최근 30일
  `created` 필터, 최대 3건 자동 출력. tags ∩ symptom-keywords 매칭은
  복잡도·소급 적용 부담으로 Phase 4 유보 (advisor 권고)
- **E — signal lifecycle 변경**: incidents 승급 시 signal 파일 **삭제
  → `archived: true` 마커 잔존**으로 변경. session-start.py가 archived
  신호를 약한 톤(`· (archived) ...`)으로 출력. 회상 다리 유지
  - `rules/memory.md` "## 신호 파일" 절 갱신
  - `session-start.py` `section_signals()` archived 분기 추가
- **B — `stop-guard.sh` 조건 C 확장 (Soft + Dry-run)**: 기존 미커밋·
  in-progress 알림에 더해 조건 A·B·C AND 발화 추가:
  - A: git status 수정 파일 있음
  - B: 변경된 WIP 중 status: in-progress 있음
  - C: 그 WIP에 빈 체크박스 `- [ ]` 또는 BIT 판단 블록 부재
  - hit 시 stderr 1줄 + `.claude/memory/stop_hook_audit.log` append
    (gitignore). 차단 아님 — 측정용. Phase 4 Hard Stop 결정 근거
- 신규 signal 4건 추가 (Phase 2.5, 별도): dead code 잔존·WIP move
  dead link·AC 미체크·자동화 불가 검증 단락. 모두 `hn_commit_process_gaps`
  (2026-04-27) 인용

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

다운스트림 권장 (선택):

- `docs/incidents/*.md` frontmatter에 `domain:` 명시 (D-Lite 매칭 입력).
  미명시 incident는 출력 대상 제외 — 회귀 아님, 보강 기회 누락만
- 향후 incidents 등록 시 `symptom-keywords` 명시 (Phase 4 매칭 강화 대비)

### 검증

```bash
python3 .claude/scripts/session-start.py 2>&1 | grep -E "(반복 신호|incident)"
# 현재 WIP domain 매칭 incident 1~3건 출력 확인

python3 .claude/scripts/stop-guard.py   # v0.40.1에서 sh → py 전환
# A·B·C AND 조건 hit 시 "🛑 [stop-guard A·B·C]" stderr 출력 확인

cat .claude/memory/stop_hook_audit.log
# hit 기록 누적 확인 (gitignore — 다운스트림 본인 환경에서만 잔존)
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 75 passed (회귀 0) 확인. Linux/macOS 미테스트
- `section_incidents()`는 incident frontmatter `domain`·`title`·`created`
  3 필드 모두 있어야 출력. 누락 시 침묵 (회귀 아님)
- `archived: true` 마커는 backward compatible — 기존 signal 파일 무수정.
  마커 없는 signal은 기존 톤 유지
- stop-guard 조건 C는 Soft 모드 — stderr 1줄만, 차단 0. 노이즈 위험
  낮음. 단 다운스트림이 BIT 판단 블록 양식 다르게 쓰면 has_bit 매칭이
  `^\[BIT 판단\]` 정확 일치 요구로 false-positive (BIT 누락 알림 과다)
  가능. 운용 audit 로그로 검토 후 패턴 완화 검토
- audit 로그는 gitignore — 다운스트림 본인 환경에서만 잔존. upstream
  공유 안 됨

### 운용 측정 계획

starter 본인 다음 5~10 commit 동안:

1. `.claude/memory/stop_hook_audit.log` hit 빈도 + 유효 경고/노이즈 비율
2. P8 자기증명 카운트 (commit별 자가 의존 변종 발생)
3. `section_incidents()` 출력 hit rate

데이터 누적 후 Phase 4 진입 결정 (Hard Stop 도입 또는 조건 정밀화).

---

## v0.39.0 — BIT 강제 트리거 보강 (debug-guard.sh 키워드 사전 확장) (2026-05-10)

### 변경 내용

- CPS P8 신설: "자가 발화 의존 규칙의 일반 실패". 다운스트림에서 BIT
  (bug-interrupt) 발화 0건 실측 기반 (LSP stale dist 결함 케이스에서 메커니즘
  0 작동). S8 1차 초안 — "강제 트리거 우선 + 자가 의존 보조". 충족 기준
  확정은 owner 승인 후
- `.claude/scripts/debug-guard.sh`: 키워드 사전 17개로 확장 — 한국어 `에러|
  버그|실패|오류|크래시|충돌`, 영어 `error|bug|fail|exception|panic|crash|
  traceback|stacktrace|regression|broken|conflict`. hit 시 기존
  debug-specialist 안내 + 신규 BIT Q1/Q2/Q3 적용 안내 둘 다 출력
- `.claude/scripts/test-debug-guard.sh`: 신규 회귀 가드. 22/22 통과 (hit 17 +
  miss 5, false-positive 가드 포함)
- `.claude/rules/bug-interrupt.md`: "## 강제 트리거 (debug-guard.sh)" 절 추가.
  키워드 SSOT는 hook 스크립트로 위임 (룰에 박지 않음)
- `.claude/HARNESS_MAP.md`: CPS 테이블 P8 행 추가 (defends-by=bug-interrupt,
  enforced-by=debug-guard.sh)

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
bash .claude/scripts/test-debug-guard.sh
# 22/22 통과 기대
```

다운스트림 운용에서 사용자가 증상 키워드 발화 시 두 안내 출력 확인.

### 회귀 위험

- Windows + Git Bash 격리 환경에서 22/22 통과 확인. Linux/macOS 미테스트
- 키워드 사전 확장은 누적 — 기존 v0.38.5까지의 6개 키워드 모두 포함, 신규
  11개 추가만. 기존 hit 케이스 회귀 없음
- BIT 안내 추가 출력은 stdout 경로 — 기존 debug-specialist 안내와 충돌
  없음 (둘 다 누적 출력)
- false-positive 가드: "원인" 키워드 제외 ("원인 분석해줘"류 회피).
  실측 누적 후 사전 재조정 가능

---

## v0.38.5 — Python 콘솔 인코딩 안전 처리 (Windows cp949 환경) (2026-05-08)

### 변경 내용

- `.claude/scripts/eval_cps_integrity.py`: 진입점에 `sys.stdout/stderr.reconfigure(encoding="utf-8")` 안전 처리 추가
  - Windows cp949 콘솔에서 emoji `✅` 출력 시 `UnicodeEncodeError` 발생하던 결함 차단
  - `PYTHONIOENCODING=utf-8` prefix 없이도 정상 동작
- `.claude/scripts/session-start.py`: 동일 안전 처리 추가
- `.claude/scripts/docs_ops.py`: 동일 안전 처리 추가 — 한글 mojibake 출력(`## ���� �̵�`) 정상화
- 결함 자체는 v0.0~v0.38.4 전 기간 잠재. eval --harness 박제 의심 점검 중 노출

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영.

### 검증

```bash
# Windows cp949 환경에서 PYTHONIOENCODING 없이 실행
python .claude/scripts/eval_cps_integrity.py
# emoji ✅ 정상 출력 확인

python .claude/scripts/docs_ops.py validate
# 한글 정상 출력 확인 (mojibake 없음)
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 3개 스크립트 실행 통과 확인
- 콘솔 인코딩이 이미 utf-8(Linux/macOS·`PYTHONIOENCODING=utf-8` 설정 환경)이면 reconfigure 분기 미실행 — 기존 동작 유지
- `sys.stdout.reconfigure`는 Python 3.7+ 필수. 미만 버전은 `except (AttributeError, OSError)` 분기로 silent fall-through (정상 환경에서는 도달 불가)
- `errors="replace"` 모드 — 표현 불가 문자는 `?`로 치환 (raise보다 safer)

