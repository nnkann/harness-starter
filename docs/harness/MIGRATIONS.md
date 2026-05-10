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

---

## v0.38.4 — completed 봉인 오탐 수정 — reopen→move 정상 절차 면제 (2026-05-08)

### 변경 내용

- `pre_commit_check.py`: completed 봉인 보호 로직 오탐 수정
  - reopen→move 절차 경유 파일이 rename 두 번 상쇄로 M(modify)으로 분류되어 차단되던 버그 수정
  - `docs_ops.py move`가 완료 시 `session-moved-docs.txt`에 경로 기록, pre-check이 대조해 면제
- `docs_ops.py`: `move` 완료 시 `.claude/memory/session-moved-docs.txt` 기록 추가
- `rules/memory.md`: session 파일 목록 2→3개 갱신 (`session-moved-docs.txt` 추가)
- 회귀 테스트 T42.9(면제), T42.10(무단 변경 차단) 추가

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m gate -q
# 22 passed 확인
```

### 회귀 위험

- upstream 격리 환경(Windows)에서 gate 22 passed 확인
- `session-moved-docs.txt` 미생성 환경(세션 첫 커밋)에서는 면제 미적용 → 기존 동작 유지
- Linux/macOS 미테스트

---

## v0.38.3 — 침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계 (2026-05-06)

### 변경 내용
- `.claude/scripts/bash-guard.sh` — 차단 시 `.claude/memory/signal_defense_success.md`에 background append. P4 방어 활성 데이터 축적.
- `skills/eval/SKILL.md` — `--harness` 항목 6번 추가: signal_defense_success.md 존재·최근 기록 표시 (기존 6번은 7번으로 번호 이동)
- `skills/harness-upgrade/SKILL.md` — Step 10 완료 직후 방어 기전 설명 단계(6번) 추가: What이 아닌 Why 포함 강제
- `docs/guides/project_kickoff.md` — S4 추가 방어 레이어 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 다음 harness-upgrade 시 Step 10 완료 직후 방어 기전 설명을 받게 됨 — "왜 이런 제약이 있는가" 이해 기회
- `.claude/memory/signal_defense_success.md`가 자동 생성되어 eval --harness에서 방어 활성 상태 확인 가능

---

## v0.38.2 — HARNESS_MAP MVR 섹션 + 에이전트 빠른 진입 가이드 (2026-05-06)

### 변경 내용
- `.claude/HARNESS_MAP.md` — `## MVR (작업유형별 최소 필수 규칙셋)` 섹션 추가: 7개 작업유형별 Rules 2~3개 압축 매핑 (구현·커밋·디버그·문서·eval·harness-dev·설정변경)
- `.claude/HARNESS_MAP.md` — 최상단에 "⚡ 에이전트 빠른 진입" 가이드 추가: MAP 전체 Read 금지, MVR → 역추적 2단계 진입점 명시
- `docs/guides/project_kickoff.md` — S5 MVR 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 에이전트가 HARNESS_MAP 전체를 읽는 대신 `## MVR` 섹션만 참조하도록 유도하면 컨텍스트 절감 효과 기대
- 다운스트림은 자기 프로젝트 작업유형에 맞게 MVR 섹션 확장 가능 (harness-upgrade가 덮어쓰지 않는 영역에 추가)

