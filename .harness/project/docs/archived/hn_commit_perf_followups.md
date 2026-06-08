---
title: hn_commit_perf_optimization wave 후속 별 wave 모음
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, followup, backlog, abandoned-asset]
relates-to:
  - path: archived/hn_commit_perf_optimization.md
    rel: extends
  - path: archived/hn_commit_perf_audit.md
    rel: references
  - path: archived/hn_harness_recovery_v0_41_baseline.md
    rel: caused-by
status: abandoned
created: 2026-05-13
updated: 2026-05-13
---

# 후속 별 wave 모음 (abandoned — 자산 보존)

> **abandoned 사유 (2026-05-13)**: 본 followups는 9b29f23 도돌이표 commit
> 직후 "별 wave 신설" 패턴으로 작성됨 — 그 자체가 anti-defer.md 블랙리스트
> ("별 wave로 분리·후속 처리"). 본 wave `hn_harness_recovery_v0_41_baseline`
> Phase 0에서 abandoned 처리. 본문 backlog 항목은 후속 마이그레이션 wave
> 입력 자료로 박제.
>
> 본 wave SSOT: `docs/WIP/hn_harness_recovery_v0_41_baseline.md`.

본 wave 9b29f23 완료 직후 anti-defer 규칙에 따라 "별 wave 신설 + 즉시
처리 가능"으로 분리한 항목들. audit WIP에서 거짓 수정 hit이 추가 발견되면
여기에 누적한다.

## 후속 1 — install 스크립트 시크릿 SSOT 마이그레이션

### 사유
- `pre_commit_check.py:get_secret_patterns()` SSOT 함수를 도입했지만
  `install-starter-hooks.sh`와 `scripts/install-secret-scan-hook.sh`가
  여전히 자체 정규식을 들고 있다 (3중 정의).
- 본 wave가 "다운스트림 영향 평가 필요"로 별 wave 분리한 항목.
- 실측 마찰("hook과 pre-check 예외 불일치 — 2026-05-11 Codex 전환 커밋")의
  근본 원인은 SSOT 함수 도입만으로 해소되지 않는다. 실제 hook 생성물이
  SSOT를 소비해야 함.

### 미루기 근거 (anti-defer 객관 사유)
- 다운스트림 환경 의존: install 스크립트는 다운스트림에서도 실행되며,
  Python 의존 추가가 다운스트림 환경에 영향. starter 단독 측정 불가.
- 사용자 입력 필요: Python 미설치 다운스트림에 대한 graceful degradation
  정책 결정이 owner 영역.

### 범위
- install-starter-hooks.sh: PATTERN 합성을 `python3 pre_commit_check.py
  --emit-secret-patterns | jq` 경유로 전환
- scripts/install-secret-scan-hook.sh: 동일
- 회귀 가드: pre-check 통과 후 hook에서 같은 사유로 차단되는 사례 0건
  확인 테스트

### Acceptance Criteria
- [ ] Goal: install 두 스크립트가 SSOT 함수를 호출해 PATTERN 생성. 정규식
      중복 정의 0.
  검증:
    review: review-deep
    tests: pytest -m secret
    실측: bash install-starter-hooks.sh 실행 후 hook 본문에 SSOT의 패턴이
          정확히 포함됐는지 grep
- [ ] install-starter-hooks.sh PATTERN 합성을 SSOT 호출로 대체
- [ ] scripts/install-secret-scan-hook.sh 동일
- [ ] Python 미설치 다운스트림 graceful degradation 정책 명시
- [ ] hook 생성물 ↔ pre-check 예외 hash 동일성 회귀 테스트 추가

---

## 후속 2 — SKILL.md frontmatter serves/trigger 필드 추가

### 사유
- 본 wave 9b29f23 pre-check이 잡은 cascade 경고:
  `cascade-serves-trigger-missing:SKILL.md`
- `.claude/skills/commit/SKILL.md` (+ `.agents/skills/commit/SKILL.md`)
  frontmatter에 `serves:` 또는 `trigger:` 필드 없음.
- sub-task 7 cascade check가 본 wave의 staged 파일에 대해 경고를 띄웠는데,
  그 경고 대상이 본 wave가 수정한 파일이라는 자기증명 — 신규 도입한
  cascade 룰이 즉시 작동하지만 본 wave가 그 룰을 만족시키지 않음.

### 범위
- `.claude/skills/commit/SKILL.md` frontmatter에 `serves: S2` 추가
- `trigger:` 필드 적정 값 결정 (commit 스킬 발화 신호 — 사용자가 "/commit"
  발화 또는 LLM이 commit 의도 인식)
- `.agents/` 사본 동기화
- 회귀 가드: pre-check에서 cascade-serves-trigger-missing 경고가 사라지는지

### Acceptance Criteria
- [ ] Goal: cascade-serves-trigger-missing 경고 0건.
  검증:
    review: review
    tests: pytest -m cascade
    실측: python3 .claude/scripts/pre_commit_check.py 결과 warning_reasons에
          해당 라벨 없음
- [ ] .claude/skills/commit/SKILL.md frontmatter `serves:` 추가
- [ ] trigger 값 결정 + 추가
- [ ] .agents/ 사본 동기화
- [ ] 다른 SKILL.md들(implementation/write-doc/eval 등)도 같은 검사 대상이
      되는지 확인 (현재 cascade check는 첫 hit break — false negative 가능성)

---

## 후속 3 — SKILL.md 두 사본 동기화 자동화

### 사유
- `.claude/skills/commit/SKILL.md`와 `.agents/skills/commit/SKILL.md`가
  Claude/Codex 어휘 5곳만 차이.
- 본 wave에서 수동 cp + sed로 동기화. 다음 SKILL.md 갱신 시 누락 가능.
- 회귀 가드 0건.

### 범위
- 자동 동기화 스크립트 또는 한 사본만 SSOT로 두고 다른 사본은 빌드 시점
  생성 (다운스트림 영향 평가 필요)
- 또는 pytest 회귀 가드로 5곳 차이 외 차이가 생기면 실패

### Acceptance Criteria
- [ ] Goal: 두 사본이 의도된 5곳 외 drift 시 차단.
  검증:
    review: review
    tests: pytest -m docs_ops (새 marker 또는 stage 통합)
    실측: 수동으로 한 사본만 수정 후 테스트 실행 → 실패
- [ ] 자동 동기화 또는 회귀 가드 방식 결정 (advisor 호출)
- [ ] 구현
- [ ] 두 SKILL.md 외 다른 스킬도 같은 구조인지 audit (전역 적용 여부)

---

## 후속 4 — TestCommitFinalize Windows path 이슈

### 사유
- 본 wave + 이전 baseline 둘 다에서 동일 실패:
  `TestCommitFinalize::test_simple_commit_passes`
  `TestCommitFinalize::test_block_skips_wip_sync`
- 에러: `fatal: could not parse HEAD` — Windows path 혼합 (`D:\...\.git\
  objects\D:\Work\...`)
- 본 wave에서 BIT IGNORE 처리. 별 wave에서 root cause 분석 필요.

### 범위
- _git() 헬퍼의 cwd 처리 검토
- subprocess.run env 또는 GIT_DIR 변수 누락 여부
- module 스코프 sandbox(`integ_repo`) 초기화 시 git env 격리

### Acceptance Criteria
- [ ] Goal: 두 테스트가 Windows + Git Bash 환경에서 통과.
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_pre_commit.py::TestCommitFinalize
    실측: Windows 환경에서 직접 실행 — green
- [ ] root cause 식별
- [ ] 수정 후 회귀 가드

---

## 후속 5 — Windows commit smoke 검사 범위 확장

### 사유
- audit TC6.1·TC6.4 — 현재 `TestWindowsCommitSmoke.SHELL_SCRIPTS`는 4개
  파일만 (`commit_finalize.sh`·`split-commit.sh`·`bash-guard.sh`·
  `install-starter-hooks.sh`).
- 실제 .sh는 12개. 8개 누락.
- 사전 차단(pre-check이 CRLF staging 차단) 미구현 — WIP "E. 실행 환경 원칙"
  1번 항목.

### 범위
- SHELL_SCRIPTS 리스트를 `git ls-files '*.sh'` 결과로 확장 (자동 수집)
- pre_commit_check.py에 staged .sh CRLF 차단 룰 추가 (또는 자동 정규화)

### Acceptance Criteria
- [ ] Goal: 본 repo 모든 .sh가 CRLF 0 + 사전 차단 메커니즘.
  검증:
    review: review-deep
    tests: pytest -m windows
    실측: 의도적으로 CRLF .sh staging → pre-check이 차단
- [ ] SHELL_SCRIPTS 자동 수집
- [ ] pre-check CRLF 차단 룰
- [ ] 회귀 가드

---

## 후속 6 — Cascade Integrity Check 9→9 완성

### 사유
- audit TC7.1 — WIP "G" 표가 정의한 9 항목 중 본 wave 구현은 3종만.
  Trigger·Side effect·Upward feedback 등 6 항목 미구현.
- audit TC7.2 — `for ... break` 구조로 첫 hit만 잡음. false negative.
- audit TC7.5 — 차단 룰과 경고 룰이 분리됐는데 통합 안 됨.

### 범위
- 9 항목 모두 검사 코드 추가
- break 제거 (다중 hit 누적)
- 차단 정책 통합 (staging.md "## Stage 결정 룰"과 정합)

### Acceptance Criteria
- [ ] Goal: WIP G 표 9항목 모두 자동 검출. false negative 없음.
  검증:
    review: review-deep
    tests: pytest -m cascade (현재 2종 → 9종+ 확장)
    실측: 의도된 9 종 결함을 의도적으로 만들고 모두 감지하는지
- [ ] 9 항목 검사 코드
- [ ] 다중 hit 누적
- [ ] 차단 vs 경고 정책 통합 (staging.md 참조)

---

## 후속 7 — release path 자동 진입 정합성 audit

### 사유 (사용자 체감 "더 느려졌다" 1차 가설)
- 본 wave 9b29f23 커밋이 patch 범프 자동 감지 → MIGRATIONS·README·archive
  5종 메타 갱신 자동 진입.
- WIP "B. release 승격 조건 명시"는 "release 커밋만 무거운 절차"를
  목표했지만, 실측은 "코드 변경 = patch 범프 = release path 자동 진입".
- 결과: 본 wave 같은 일반 변경마다 release 절차 비용 지불.

### 범위
- harness_version_bump.py의 patch 판정 기준 재검토 — 핵심 파일 수정 1건이면
  patch라는 룰이 너무 광범위함
- 또는 release path 진입 게이트에 사용자 명시 동의 추가
- 또는 MIGRATIONS·README 갱신을 N개 commit 누적 후 일괄 처리로 전환

### Acceptance Criteria
- [ ] Goal: release path가 정말 다운스트림 영향이 있는 변경에만 진입.
      일반 패치는 fast path.
  검증:
    review: review-deep
    tests: pytest -m stage (release 트리거 정확성)
    실측: 본 wave 같은 변경에서 release path 자동 진입 안 함
- [ ] harness_version_bump.py 판정 기준 재검토 (advisor 호출)
- [ ] 게이트 정책 결정
- [ ] 회귀 가드

---

## Acceptance Criteria (본 followups WIP 전체)

- [ ] Goal: 본 wave 후속 항목 7건이 모두 별 WIP로 분리 또는 본 문서에서
      직접 처리됨.
  검증:
    review: skip
    tests: 없음
    실측: 본 문서 각 후속 항목의 AC 또는 별 WIP 링크 존재
- [ ] 후속 1 (install 스크립트 SSOT 마이그레이션) 별 WIP 분리 또는 본문 처리
- [ ] 후속 2 (SKILL.md serves/trigger) 별 WIP 분리 또는 본문 처리
- [ ] 후속 3 (SKILL.md 사본 동기화 자동화) 별 WIP 분리 또는 본문 처리
- [ ] 후속 4 (TestCommitFinalize Windows path) 별 WIP 분리 또는 본문 처리
- [ ] 후속 5 (Windows smoke 범위 확장) 별 WIP 분리 또는 본문 처리
- [ ] 후속 6 (Cascade 9→9 완성) 별 WIP 분리 또는 본문 처리
- [ ] 후속 7 (release path 자동 진입 audit) 별 WIP 분리 또는 본문 처리

## 메모

- 본 문서는 모음 (index). 각 후속이 자체 wave가 될 만큼 커지면 별 WIP로
  승격 + `relates-to: rel: extends` 링크.
- 우선순위 제안: **후속 7 (release path) > 후속 6 (cascade) > 후속 2
  (SKILL.md serves/trigger) > 나머지**.
  - 후속 7: 사용자 체감 마찰 1차 가설. 검증 후 hit이면 본 wave 의도 미달
  - 후속 6: sub-task 7이 67% 미구현 — 본 wave가 거짓 수정인지 audit의 핵심
  - 후속 2: 즉시 처리 가능. cascade 경고 자기증명 해소
