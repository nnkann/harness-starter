---
title: 자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)
domain: harness
problem: P7
solution-ref:
  - S7 — "정의 보류 — owner 합의 영역 (별 사안)"
tags: [sh, wip-parsing, ssot, python, migration, hook, refactor, audit]
relates-to:
  - path: decisions/hn_stop_guard_py_migration.md
    rel: extends
status: completed
created: 2026-05-10
updated: 2026-05-10
---

# 자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합

## 배경

stop-guard.sh가 자기증식 케이스(Git Bash 호환 hack 누적·bash 파싱 도구
혼재·확장 로드맵 명시·Python 자매 hook 존재 — 4신호 동시 hit)로 v0.40.1에서
Python으로 전환됐다. 이 케이스가 다른 14개 sh에도 적용되는지 점검을
stop-guard 전환 직후 합의했으나 WIP·메모리 어디에도 기록 없이 다음 세션으로
넘어가 유실됐다 (anti-defer.md "다음 세션" 블랙리스트 정확히 hit).

본 wave는 (1) 그 누락된 점검을 14개 sh 전체에 수행하고 (2) 점검 결과
도출된 진짜 원인(SSOT 부재)을 실행으로 옮긴다.

## 선택지

### A. 14개 모두 py 전환

장점: 단일 언어 정합성. 단점: bash 내장 패턴이 더 효율적인 hook까지 spawn
비용 추가. 자기 검증 메타 루프 위험(bash-guard).

### B. stop-guard 4신호 동시 hit 후보만 전환

장점: 외형 metric(언어) 아닌 실증 신호 기반. 단점: 1차 점검에서 후보가
1건만 나와 "케이스 일반화 안 됨" 결론으로 단락될 위험. 시스템 차원의
파편화는 보지 못함.

### C. 본질은 SSOT 부재 — 공통 모듈 + 후속 hook 마이그레이션

장점: WIP 파싱 로직이 3곳(session-start.py·post-compact-guard.sh·stop-guard.py)에
파편화된 진짜 원인 해결.

## 결정 — C 선택

### 14개 sh 점검 결과

#### 적합 (1건)

**`post-compact-guard.sh`** — 단순 wrapper 아닌 WIP 데이터 가공·리포팅
도구. sed/grep/awk 3종 혼재로 파싱(#2 hit). session-start.py와 동일 작업
중복(#4 hit). P8 보강 로직(D=section_incidents·E=signal lifecycle)을
post-compact 시점에 보여주려면 bash 복잡도 기하급수적 증가(#3 hit).
컴팩션 빈도 낮아 spawn 비용 무시 가능.

#### 부적합 (12건)

| sh 파일 | 부적합 사유 |
|---------|-------------|
| `bash-guard.sh` | PreToolUse Bash hook — 매 Bash 호출마다 python3 spawn 비용 큼. bash 내장 `[[ =~ ]]`로 호환 hack 0. 자기 검증 메타 루프 위험 |
| `write-guard.sh` | PreToolUse Write hook — case 패턴 매칭 + jq 1회. 호환 hack 0, 확장 로드맵 0 |
| `debug-guard.sh` | UserPromptSubmit — `grep -qiE` 단일 키워드. 이미 python3로 JSON 파싱(혼재 해소). 호환 hack 0 |
| `auto-format.sh` | PostToolUse — prettier·ruff·black wrapper. 외부 도구 호출이 본체라 py 전환 이득 0 |
| `commit_finalize.sh` | wrapper 30줄 — `git diff` + `python3 docs_ops.py` + `git commit`. 이득 0 |
| `split-commit.sh` | 일회성 분할 wrapper — 사용자/Claude가 호출. hook 아님 |
| `validate-settings.sh` | 본체 이미 python3 heredoc. bash는 wrapper 30줄 |
| `check_init_done.sh` | init 게이트 — `[ -f ]` + `grep -qE` 단일. 호환 hack 0 |
| `downstream-readiness.sh` | 일회성 자가 진단 — 다운스트림 수동 실행. 발화 빈도 0 |
| `install-starter-hooks.sh` | 일회성 hook 설치 — harness-sync에서만 실행. hook 자체 아님 |
| `test-bash-guard.sh` | bash-guard.sh 테스트 — 대상이 sh로 남으므로 같은 환경 검증 |
| `test-debug-guard.sh` | debug-guard.sh 테스트 — 동일 |

### 시스템적 문제 — 파싱 로직 3중 파편화

| 위치 | 언어 | 파싱 방식 | 추출 항목 |
|------|------|----------|----------|
| `session-start.py` `parse_wip_file()` | Python | 정교 파서 | status·title·bit_count·has_new |
| `post-compact-guard.sh` line 22~40 | Bash | `sed`+`grep`+`awk` 혼재 | status·title·결정 사항 |
| `stop-guard.py` `is_in_progress()` | Python | 단일 책임 함수 | status |

**위험**:
- 유지보수: frontmatter 규격(status 필드 이름·옵션 등) 변경 시 3곳 동시 수정
- 불일치: post-compact-guard.sh의 sed 약식 파서와 Python 정교 파서가 다른
  결과 산출 가능 (주석 처리된 status·인라인 코멘트·다중 라인 case)

이 파편화는 stop-guard 자기증식 4신호 중 #2(파싱 도구 혼재)·#4(자매 hook
일관성)가 **시스템 전체 차원으로 확장된 형태**다. stop-guard 한 파일을
py로 옮긴 것은 증상 fix였지, 근본 원인(SSOT 부재)은 그대로다.

### 대안 — `wip_util.py` 공통 모듈

1. `.claude/scripts/utils/wip_util.py` 신설 — `parse_wip_file()` 이관
2. session-start.py·stop-guard.py·(전환 후) post-compact-guard.py 모두
   동일 함수 호출
3. sed 약식 파싱을 Python 안정 파서로 대체

## 사전 준비

- 읽을 문서:
  - `docs/decisions/hn_stop_guard_py_migration.md` (4원칙 답습 SSOT)
  - `.claude/scripts/session-start.py` (`parse_wip_file()` 정교 파서 SSOT)
  - `.claude/scripts/stop-guard.py` (`is_in_progress()` 단일 책임 함수)
  - `.claude/scripts/post-compact-guard.sh` (sed/grep/awk 혼재 — 마이그레이션 대상)
- MAP 참조: `.claude/HARNESS_MAP.md` Scripts 섹션 (session-start.py·stop-guard.py 행)

## 목표

CPS 연결: P7(하네스 자체의 탐색 가능성·유지보수성). Solution 충족 기준
변경 아닌 메커니즘 정합 정비 — 작성자가 동일 frontmatter 규격을 3곳 다른
파서로 처리해 발생하는 불일치 위험 차단.

## 작업 목록

### Phase 1. wip_util.py 신설

**사전 준비**:
- session-start.py `parse_wip_file()` Read해 반환 4필드(status·title·
  bit_count·has_new) 시그니처·동작 확보
- cp949 안전 처리 패턴(Windows Git Bash 대응) 답습 위치 확인

**영향 파일**:
- `.claude/scripts/utils/wip_util.py` (신설)
- `.claude/scripts/utils/__init__.py` (필요 시 — 빈 파일 또는 생략)

**Acceptance Criteria**:
- [x] Goal: `wip_util.parse_wip_file(path) -> dict` 함수가 session-start.py ✅
      현행 동작과 1:1 일치 (status·title·bit_count·has_new 4필드 반환)
  검증:
    review: review
    tests: 없음
    실측: `python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); from utils.wip_util import parse_wip_file; print(parse_wip_file('docs/WIP/decisions--hn_wip_util_ssot.md'))"` 실행 결과가 status='in-progress'·title 일치·bit_count·has_new 정상 반환

### Phase 2. session-start.py 마이그레이션

**사전 준비**: Phase 1 완료 (wip_util.py 존재)

**영향 파일**:
- `.claude/scripts/session-start.py`

**Acceptance Criteria**:
- [x] Goal: session-start.py 안의 `parse_wip_file()` 정의 제거 + wip_util ✅
      import로 교체. 출력 변화 0 (마이그레이션 전후 stdout diff = 0)
  검증:
    review: review
    tests: 없음
    실측: `python3 .claude/scripts/session-start.py > /tmp/after.txt` 실행 후
          마이그레이션 전 캡처본과 diff 0 (trailing space 제외)

### Phase 3. stop-guard.py 마이그레이션

**사전 준비**: Phase 1 완료

**영향 파일**:
- `.claude/scripts/stop-guard.py`

**Acceptance Criteria**:
- [x] Goal: stop-guard.py의 `is_in_progress()` 단일 책임 함수를 wip_util. ✅
      parse_wip_file() 사용으로 교체 (또는 wip_util에 `is_in_progress` alias
      제공). 출력 변화 0
  검증:
    review: review
    tests: 없음
    실측: `echo '{}' | python3 .claude/scripts/stop-guard.py > /tmp/after.txt`
          실행 후 마이그레이션 전 캡처본과 diff 0

### Phase 4. post-compact-guard.sh → .py 전환 + sh 삭제 + settings.json 갱신

**사전 준비**: Phase 1·2·3 완료 (wip_util 안정성 확인 후 진행)

**영향 파일**:
- `.claude/scripts/post-compact-guard.py` (신설)
- `.claude/scripts/post-compact-guard.sh` (삭제 — dead code 동시 제거)
- `.claude/settings.json` (PostCompact hook command: bash → python3)

**Acceptance Criteria**:
- [x] Goal: post-compact-guard.py가 sh 4개 동작 절(WIP 목록·staged 변경· ✅
      TODO 진행률·규칙 재주입)을 1:1 포팅. wip_util.parse_wip_file() 사용
      으로 sed/grep/awk 혼재 제거. settings.json PostCompact hook command
      를 python3로 갱신. sh 삭제
  검증:
    review: review-deep
    tests: 없음
    실측: `echo '{}' | python3 .claude/scripts/post-compact-guard.py > /tmp/py.txt`
          실행 결과가 sh 삭제 전 동일 입력 sh 출력과 1:1 일치 (trailing
          space 제외). settings.json command가 `python3 .claude/scripts/post-compact-guard.py`로 변경됨. sh 파일 부재

### Phase 5. 다운스트림 마이그레이션 박제 (MIGRATIONS.md + 회귀 위험)

**사전 준비**: Phase 1·2·3·4 완료

**영향 파일**:
- `docs/harness/MIGRATIONS.md` (새 버전 섹션 추가 — commit Step 4 자동
  처리 영역이지만 본 wave가 박제할 내용을 정리)

**다운스트림 도달 경로**: `harness-upgrade`가 업스트림 fetch → 3-way merge

**자동 적용 항목** (다운스트림이 fetch하면 자동):
- `.claude/scripts/utils/__init__.py` (신설)
- `.claude/scripts/utils/wip_util.py` (신설)
- `.claude/scripts/session-start.py` (parse_wip_file 정의 제거 + import 추가)
- `.claude/scripts/stop-guard.py` (is_in_progress 정의 제거 + wip_util 사용)
- `.claude/scripts/post-compact-guard.py` (신설)
- `.claude/scripts/post-compact-guard.sh` (삭제)

**수동 액션** (다운스트림 의무):
1. `.claude/settings.json` PostCompact hook command 갱신
   `bash .claude/scripts/post-compact-guard.sh` → `python3 .claude/scripts/post-compact-guard.py`
   (settings.json을 다운스트림이 자체 커스터마이즈한 경우 3-way merge 후 확인)
2. `bash .claude/scripts/post-compact-guard.sh` 호출하는 외부 스크립트가
   있으면 동일 갱신 (downstream-readiness.sh가 hook 누락 자동 감지)

**회귀 위험** (no-speculation.md "MIGRATIONS.md 회귀 위험" 정합):
- upstream 격리 환경(Windows + Git Bash + Python 3.12)에서 관찰된 범위 내
  검증
- Linux/macOS·다른 Python 버전 미테스트
- WSL·Docker·CI 등 다른 실행 환경의 sys.path 동작 미검증
- 다운스트림이 utils/ 경로에 자체 모듈을 두던 경우 충돌 가능성 (현재
  업스트림에서는 utils/ 폴더 부재였음)

**검증 명령** (다운스트림이 upgrade 후 실행):
```
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); from utils.wip_util import parse_wip_file"
echo '{}' | python3 .claude/scripts/post-compact-guard.py
python3 .claude/scripts/session-start.py
echo '{}' | python3 .claude/scripts/stop-guard.py
```

**Acceptance Criteria**:
- [x] Goal: 본 섹션 내용이 commit Step 4에서 `docs/harness/MIGRATIONS.md` ✅
      새 버전 섹션의 "변경 내용·적용 방법·검증·회귀 위험" 4영역에 박제
      되도록 정리 완료
  검증:
    review: review
    tests: 없음
    실측: 본 WIP 본문에 자동 적용 항목·수동 액션·회귀 위험·검증 명령 4
          영역이 모두 작성됨. commit Step 4가 이를 MIGRATIONS.md로 옮김

## 답습 의무 (stop-guard 4원칙)

1. 1:1 동작 (기능 변경 0) — 마이그레이션 전후 출력 diff 0
2. session-start.py·stop-guard.py 패턴 답습 (cp949 안전·frontmatter 파싱)
3. dead code 동시 제거 (post-compact-guard.sh 삭제 = settings.json 전환
   같은 commit)
4. Reversibility 5/5 (settings.json 1줄 원복으로 sh 복구 가능 — 단 sh
   삭제 후엔 git revert 필요)

## 결정 사항

### Phase 1·2·3·4 완료 (2026-05-10)

- **wip_util.py SSOT 신설**: `.claude/scripts/utils/wip_util.py` + `__init__.py`
  추가. `parse_wip_file(path) -> (status, title, bit_count, has_new)` +
  `is_in_progress(path) -> bool` alias 제공
- **session-start.py 마이그레이션**: parse_wip_file 정의 제거 → import로
  교체. 출력 1:1 동등 (diff는 본 wave가 만든 unstaged 파일이 출력에 잡힌
  것 외 차이 없음)
- **stop-guard.py 마이그레이션**: is_in_progress 정의 제거 → wip_util
  import로 교체. 출력 1:1 동등 (diff는 미커밋 파일 카운트 차이만)
- **post-compact-guard.sh → .py 전환**: bash 4개 동작 절(카운터·WIP 목록·
  staged·진행률·경고·규칙) 1:1 포팅. wip_util 사용으로 sed/grep/awk 혼재
  제거. sh·py 출력 비교 결과 CRLF/LF line ending 차이만 (내용 1:1 일치)
- **settings.json PostCompact command 갱신**: `bash .sh` → `python3 .py`
- **post-compact-guard.sh 삭제**: dead code 동시 제거 (stop-guard 답습)

### CPS 갱신: 없음

본 wave는 메커니즘 정합 정비 — Solution 충족 기준 변경 없음.

## 메모

- **anti-defer 자기증명 사례**: 합의 → 다음 세션 미루기 → 기록 유실 →
  사용자 환기 → 복원
- **결론 재구성 자기증명**: 1차 점검에서 "재검토 후보 1건" 결론으로
  단락하려다 사용자 통찰("언어 전환이 아닌 로직 통합")로 결론 재구성.
  점검 표 칸 채우기에 집중해 시스템 차원 위험을 시야 밖에 둔 점은 박제
- **이전 문서 frontmatter 일괄 수정 불필요**: 본 wave는 신규 frontmatter
  필드 도입이 아니라 파싱 코드 SSOT 통합. 정교 파서에 깨지는 변종 표기
  발견 시점에 일괄 수정 (회귀 발견 시점 처리)
- **eval --harness wave 후속 의무**: 현재 in-progress인
  `decisions--hn_eval_harness_cli_lsp_drift.md`가 만들 `eval_harness.py`가
  frontmatter 정합성을 검사한다면 동일 SSOT(`wip_util.py`)를 import해야
  한다. 자체 파싱을 박으면 현재 3중 파편화가 4중으로 확장됨. 본 wave 종료
  후 해당 WIP에 의무 박제 필요
- **문서 분리 → 병합 자기증명**: 원래 audit과 ssot 두 WIP로 분리해 진행
  했으나 같은 세션·같은 흐름이라 분리 근거 약함 → 사용자 환기로 병합.
  "조사·결정과 실행은 별 wave"라는 stop-guard 답습 원칙을 기계적으로
  적용한 결과 — 답습은 맥락 봐서 적용
