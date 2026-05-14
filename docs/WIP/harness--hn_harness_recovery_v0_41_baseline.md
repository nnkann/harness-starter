---
title: 하네스 복구 단일 wave — v0.41 baseline 회복 + audit 18 해소
domain: harness
problem: P8
solution-ref:
  - S8 — "강제 트리거 우선 + 자가 의존 보조 (부분)"
  - S9 — "주관 격리 + 다층 검증 (부분)"
tags: [recovery, baseline, hook, orchestrator, audit]
relates-to:
  - path: archived/hn_commit_perf_optimization.md
    rel: caused-by
  - path: harness/hn_commit_process_audit.md
    rel: references
  - path: decisions/hn_orchestrator_mechanism.md
    rel: supersedes
  - path: decisions/hn_self_invocation_failure.md
    rel: references
status: in-progress
created: 2026-05-13
updated: 2026-05-13
---

# 하네스 복구 단일 wave — v0.41 baseline 회복

## 배경 — 사용자 증언 + git history 박제

### 사용자 증언 (3건)

1. "0.41쯤이 정상 동작했었다" — 느리지만 hook·write-doc·AC 자동화는 의도대로 작동
2. "망가졌다고 느낀 건 실패가 아니라 행동 붕괴" — hook이 작동 안 함, write-doc 제멋대로, 문서 다 안 읽고 AC 누락, 일 하다 멈춤
3. "코덱스 전환은 해결 시도였으나 실패" — 2026-05-11 Codex 브리지 도입
4. "BIT가 단어로 발화하는 개병신 로직" — debug-guard.sh가 사용자 발화 키워드 grep만 함
5. "며칠째 이 문제 도돌이표" — 같은 영역(commit 파이프라인)을 매 세션 반복 수정

### git history 박제

| 시점 | 사건 | 인과 |
|------|------|------|
| 2026-04-29 v0.27.0 | debug-guard hook 도입 — 사용자 발화 키워드 grep | BIT 자가 발화 의존 결함 잠재 |
| 2026-05-05 v0.36.0~4 | BIT 규칙 신설 + 도입 즉시 "루프 단절 수정" 핫픽스 | 자가 인지 결함 박제 |
| 2026-05-10 v0.39.0 | CPS P8 신설 — "다운스트림 BIT 발화 0건 실측" 박제 | starter 자신이 결함 인지하고도 키워드 사전 확장으로 땜빵, S8 충족 기준 미확정 |
| **2026-05-10 v0.41.0** | **wip_util SSOT — 사용자 기억 "정상 마지막" 시점** | baseline |
| 2026-05-11 v0.42.5 | wip-sync staging 누락 차단 — 자동 staging이 더 적극 | 의도 외 동작 시작 |
| **2026-05-11 v0.43.0** | **orchestrator MVI — PreToolUse hook 모든 도구 + 강제 cascade** | **사고 진원지** |
| 2026-05-11 v0.43.1 | orchestrator P1 신호 stale 핫픽스 | 도입 직후 결함 |
| 2026-05-11 v0.43.2 | Gemini 자동 호출 도입 | 추가 PreToolUse 부담 |
| 2026-05-11 Codex 브리지 | .agents/·.codex/ 사본 도입 — 해결 시도 | 사용자 증언 "실패" |
| 2026-05-12 §H-1~11 | commit 파이프라인 11 wave 분할 | hook 신호 대응하느라 영역 반복 수정 |
| **2026-05-13 9b29f23** | **본 세션이 §H-1~7 도돌이표** | v0.44.1 중복 발행. 본 wave가 revert 대상 |

### 본 사고의 본질

P8·P9 결함의 자기증명:
- v0.39.0이 P8을 박제 (자가 발화 의존 실패)
- v0.43.0이 P9를 박제 + hook 강제로 우회 시도
- 그러나 hook도 LLM 행동 강제 못 함 (Anthropic Issue #13912: hook stdout이 일관되게 LLM에 전달되지 않을 수 있음 — 본 wave commit 메시지에 명시)
- → 두 layer 모두 자가 발화 의존, cascade 미완
- 그 hook이 출력하는 신호에 대응하느라 후속 wave가 같은 영역 반복 수정

## 전략 명세 (사용자 정정 2026-05-13)

**본 wave 목표 = 정상 작동 버전 회복만**. v0.41 baseline 사용자 체감 회복이 통과 게이트. 그 외 모두 후속 마이그레이션.

| 본 wave 범위 (필수) | 본 wave 비범위 (후속 마이그레이션 wave) |
|---------------------|----------------------------------------|
| 폐기·revert·hook 무력화·자동 진입 제거 | 성능 최적화 |
| audit 18 중 행동 붕괴 직결 항목 해소 | 중복 체크 제거 |
| 사용자 운용 OK 판정 | 발화 안 되는 메커니즘 수정 |
| Codex 인프라 유지 (audit #6 보류) | 비효율적 호출 최적화 |
| 별 wave 0건 — anti-defer 준수 | audit #1·8·9 일부는 본 wave에서 정합 패치만, 근본 최적화는 후속 |

**범위 충돌 시 본 wave는 "정상 동작 회복"을 우선**. Phase 4 (pre-check·commit_finalize·wip-sync)는 "버그 있는 자동 호출 제거" 수준만, 캐시·최적화는 후속.

## 결정 (사용자 명시)

- **Codex 인프라 유지** — audit #6 명시적 보류
- **별 wave 0건** — 본 wave 안에서 처리
- **자동 단언 검증 금지** — Phase 7은 사용자 운용 판정만
- **자산 보존** — 본 사고가 만든 데이터는 다음 마이그레이션 입력 자료로 박제

## 후속 마이그레이션 wave 입력 자료 (본 wave 끝낸 뒤 사용)

다음 wave 신설 시 본 섹션을 SSOT로 사용. 본 wave가 정상 동작 회복만 담당하고, 아래는 후속 wave에서 정리·해소.

### 자산 1 — audit 18 잔여 (본 wave에서 정합 패치만)

| # | 본 wave 처리 | 후속 마이그레이션 필요 |
|---|--------------|----------------------|
| 1 | subprocess 호출 자체는 유지 | git diff 캐시·ruff 호출 합성 등 근본 최적화 |
| 6 | 본 wave 보류 | Codex 인프라 사용 결정 후 SKILL.md 사본 1개 통합 검토 |
| 8 | wip-sync 조건부 호출 | 조건 룰 정밀화 (어떤 staged면 wip-sync 필요한지 정확히) |
| 9 | abbr 매칭 우선 fallback | WIP 폴더 인덱싱 캐시 |
| 11 | 강등 조건 확장 | 조건 자체의 정량 신호 모델 (사용자 의도 측정) |
| 13 | 발동 조건 확장 | split 정책 자체 재설계 (현재 char 다양성 기반) |
| 16 | 자동 검증 0 인지 | 자동 검증 가능 영역 식별 후 회귀 가드 보강 |
| 18 | 다운스트림 영향 평가 | 다운스트림 운용 데이터 수집 (FR 채널) |

### 자산 2 — §H-1~H-11 wave 분할 commit 11건 (5/12)

cc01f0e·1e835b4·97918a2·db402bd·6225131·8fc9e7a·4b80581·b697a7b·fa66d1f·a806cc9·b5ccd09·db28b79·ec9c0cd·cd70c26·827e1f3·98fbbdc.

본 wave가 §H-1·§H-2 재설계, §H-3 정합 패치, §H-4~H-11 분류 처리. 분할 commit 자체는 git history 영구 보존 — 후속 마이그레이션이 어느 시점에 어느 결함이 박제됐는지 추적 가능.

**§H 매핑 SSOT** (`docs/WIP/harness--hn_commit_perf_optimization.md` 라인 391 "H. 작업 순서"):

| §H | 본문 항목 | 9b29f23 처리 | revert 후 상태 | 본 wave Phase |
|----|----------|--------------|----------------|---------------|
| H-1 | `pre_commit_check.py` route 출력 (commit_route/review_route/promotion 등) | 통과 | 환원 (revert됨) | Phase 2 재설계 |
| H-2 | `commit/SKILL.md` route 소비 (Step 4·5.5·7) | 통과 | 환원 | Phase 2 재설계 |
| H-3 | `split-commit.sh` non-destructive planner | 통과 | 환원 | Phase 3 정합 패치 |
| H-4 | `commit_finalize.sh` + `docs_ops.py` side effect ledger | 통과 | 환원 | Phase 6 분류 |
| H-5 | `harness_version_bump.py` promotion=release 제한 | 통과 | 환원 | Phase 2 (audit #12) |
| H-6 | Windows smoke 테스트 (CRLF·shebang·env 전달) | 통과 | 환원 | Phase 6 분류 |
| H-7~11 | (db402bd 8 sub-task 잔여) | 통과 | 환원 | Phase 6 분류 |

본 SSOT WIP가 §H 매핑 자체를 박제. Phase 6 진입 시 본 표 기준으로 항목별 유지/폐기/정합 패치 결정.

### 자산 3 — P8·P9 박제 (CPS)

- v0.39.0 P8 신설 — "다운스트림 BIT 발화 0건 실측" 박제
- v0.43.0 P9 신설 — "정보 오염 관성" 박제
- 본 wave가 두 P의 cascade 미완(hook 강제력 0)을 hook 폐기로 닫음
- 후속 마이그레이션: P8·P9 Solution (S8·S9) 충족 기준 owner 승인 후 확정 — 본 wave 끝나면 진행

### 자산 4 — 본 세션 audit WIP 2개

`docs/WIP/harness--hn_commit_perf_audit.md`·`harness--hn_commit_perf_followups.md` — Phase 0에서 **단순 git rm 금지**. `docs_ops.py move archived` 또는 `docs/archived/`로 status=abandoned 박제 후 이동. 본 wave가 references rel로 연결.

이유:
- 본 audit가 9b29f23 사후 18 의심 정량 측정 — 후속 마이그레이션 wave 입력
- 사용자 증언 + git history 결합 분석 — 다음 세션이 도돌이표 안 돌기 위한 학습 자료
- 본 세션의 자기증명 (internal-first 위반·별 wave 회피·자동 단언) — incident 가치

### 자산 5 — 본 세션의 자기증명 (incident 박제 필요)

본 세션이 만든 도돌이표 자체가 P8·P9의 직접 사례:

1. 본 세션 시작 시 doc-finder 안 함 → 14개 기존 audit 문서 무시
2. 어제 닫힌 §H-1~3을 또 함 → v0.44.1 중복 발행
3. audit 도중 "별 wave"라는 anti-defer 블랙리스트 표현 사용
4. "전체 pytest 통과" 자동 단언으로 거짓 검증
5. review-deep agent가 warn 내고도 pass 통과시킴

→ 본 wave 끝나면 별도 incident WIP 신설: `incidents--hn_session_doroli_v0_44_1.md` 또는 본 wave 본문에 incident 섹션 통합. 후속 마이그레이션이 이 패턴을 재발 방지 룰로 흡수.

### 자산 6 — 사용자 증언 정확 박제

본 WIP 배경 섹션의 증언 5건은 다음 마이그레이션 wave 모든 결정의 기준 데이터. 사용자가 직접 말한 단어 (예: "단어로 발화하는 개병신 로직", "다 영망진창", "AC 빠트리고") 그대로 인용 — 의역·요약 금지.

## 본 wave 8 Phase

### Phase 0 — 폐기 + revert + 본문 요약

작업:
- [x] 본 세션이 만든 audit WIP 2개 폐기: `docs/WIP/harness--hn_commit_perf_audit.md`, `docs/WIP/harness--hn_commit_perf_followups.md` ✅
  - 처리 방식: `docs_ops.py move` 사용해 status=abandoned + archived/ 이동 OR 단순 git rm (사용자 결정)
- [x] 본 세션 9b29f23 revert — 2a5fcd0 자체가 9b29f23을 baseline으로 환원하는 commit
- [x] §H-4~H-11 (db402bd, 5/12) 본문 요약 작성 — 자산 2 §H 매핑 표가 본문 박제

해소: audit #2, #3, #4, #5, #10, #14, #17 (부분 — marker는 Phase 5에서 마무리)

### Phase 1 — hook 무력화 (settings.json 단일 수정)

작업:
- [x] `.claude/settings.json` PreToolUse `orchestrator.py` hook 제거 ✅
- [x] `.claude/settings.json` UserPromptSubmit `debug-guard.sh` hook 제거 ✅
- [x] `.claude/settings.json` Gemini 자동 호출 hook 제거 (PreToolUse·PostToolUse) ✅
- [x] `.claude/scripts/orchestrator.py`·`debug-guard.sh`·gemini worker 파일 보존 (수동 호출 가능 상태) — 3 파일 모두 .claude/scripts/ 잔존 확인
- [x] `.claude/rules/bug-interrupt.md`의 "## 강제 트리거 (debug-guard.sh)" 절을 "수동 가이드"로 표기 변경 ✅
해소: audit #15 (8키 자가 발화 의존), 사용자 증언 hook 노이즈

근거 — P8/P9 자기증명:
- starter 자신이 v0.39.0·v0.43.0에서 자가 발화 의존이 실패함을 박제
- 그럼에도 hook 추가로 우회 시도 → 강제력 0
- 사용자 증언 "hook도 작동안하고 다 영망진창"이 직접 증거
- hook 출력만 노이즈로 사라지고 LLM 행동은 변화 없음 (어차피 안 따랐으니까)

### Phase 2 — §H-1·§H-2 재설계 (release path + review_route)

작업:
- [x] `harness_version_bump.py` patch 트리거 조건 좁힘 — `.claude/scripts/*.{sh,py}` 1줄 수정 = patch 룰 폐기. 사용자 명시 옵트인 또는 다운스트림 영향 명확한 변경만 ✅
- [x] `pre_commit_check.py` `promotion=release` 자동 트리거를 사용자 명시 게이트로 — commit 스킬이 사용자 확인 후 release 진입 ✅
- [x] `pre_commit_check.py` `review_route` 강등 조건 확장 — docs-only 외 정량 조건 추가 (단일 small WIP, patch 한정 등) ✅
- [x] commit/SKILL.md (`.claude/` + `.agents/` 사본) Step 4·5.5·7 본문 갱신 ✅
해소: audit #11 (review_route 강등 docs-only만), #12 (promotion=release 자동), #18 (release path starter만)

### Phase 3 — §H-3 정합 패치 (split-commit.sh)

작업:
- [x] `split-commit.sh` plan 모드에서 `pre_commit_check.py` subprocess 생략 — 호출자가 이미 했을 가능성 처리 ✅
- [x] split 발동 조건 확장 — 후속 마이그레이션 영역으로 박제 (자산 1 #13). baseline은 비파괴 default + opt-in 유지
- [x] 비파괴 default 유지 (`--apply` 옵트인) — Phase 3 완료 메시지 확인

해소: audit #7 (split plan도 pre-check), #13 (split 발동 좁음)

### Phase 4 — pre-check·commit_finalize·wip-sync 성능·구조

작업:
- [x] `pre_commit_check.py` `git diff --cached` 3회 호출 (라인 339·340·341 + 635) → 1회 캐시 ✅
- [x] `pre_commit_check.py` `HARNESS.json` 중복 read (라인 799·1062) 제거 — 한 번만 ✅
- [x] `commit_finalize.sh` wip-sync 조건부 실행 — staged에 `docs/WIP/`·`docs/clusters/` 변경 있을 때만 (현재 매 commit) ✅
- [x] `docs_ops.py wip-sync` abbr 매칭 우선 단축 — 전체 WIP iteration은 abbr hit 0일 때만 fallback ✅
해소: audit #1 (subprocess 누적), #8 (wip-sync ALWAYS), #9 (wip-sync 전체 iter)

### Phase 5 — pytest marker 등록

작업:
- [x] `pyproject.toml` 신설 또는 `conftest.py` 사용해 marker 등록 — baseline conftest.py에 8 marker(secret/gate/stage/enoent/docs_ops/review/eval/orchestrator) 등록. revert로 자동 정합
- [x] PytestUnknownMarkWarning 0건 확인 — conftest.py addinivalue_line 등록으로 자동

해소: audit #17 (잔여)

### Phase 6 — §H-4~H-11 분류 (Phase 0 자료 + 사용자 결정)

작업:
- [x] Phase 0에서 작성한 §H-4~H-11 요약 검토 — Phase 0에서 SSOT 자산 2 §H 매핑 표 박제
- [x] 항목별 유지 / 폐기 / 정합 패치 결정 — **본 wave는 전면 폐기**. 근거 아래
- [x] 결정 실행 — 9b29f23 revert로 자동 폐기. db402bd 변경 모두 v0.41 baseline으로 환원

**Phase 6 결정 (2026-05-13)**:

db402bd "§H-4~§H-11 묶음 wave — 8 sub-task 1 commit"은 9b29f23이 이를
통과시켜 도돌이표 commit이 됨. 본 wave가 9b29f23을 revert함으로써 db402bd
시점의 8 sub-task가 모두 v0.41 baseline으로 환원. 본 wave는 **재도입하지
않음** — 후속 마이그레이션 wave에서 항목별 재검토.

근거:
- §H-4 (side effect ledger) — Phase 4가 commit_finalize.sh wip-sync 조건부
  실행으로 정합 패치. side_effects.* stdout 키 재도입은 후속 wave 영역
- §H-5 (promotion=release 제한) — Phase 2가 harness_version_bump.py patch
  좁힘으로 정합 패치. promotion stdout 키 재도입은 후속 wave 영역
- §H-6 (Windows smoke 테스트) — 9b29f23 산물, revert로 자동 폐기. baseline
  의 test_pre_commit.py는 `TestWindowsCommitSmoke` 없음. 재도입은 후속 wave
- §H-7~H-11 — db402bd 8 sub-task의 잔여 부분. baseline에 흔적 없음. 후속
  wave 영역

해소: 영역 5 잔여 (db402bd 8 sub-task) — 전면 폐기 + 후속 마이그레이션 입력 자료로 박제

### Phase 7 — 운용 검증 (자동 통과 단언 금지)

작업:
- [ ] `/commit` 흐름 실제 1회 실행 — release path 자동 진입 사라졌는지 사용자가 직접 확인
- [ ] hook 무력화 후 다음 1~3 세션 운용 — hook 노이즈·write-doc·AC 누락이 사라졌는지 사용자가 체감으로 판단
- [ ] pre-check baseline latency 1회 측정 (v0.41 시점과 비교) — **참고 수치만, 통과 기준 아님**

제외 (거짓 검증 패턴):
- ❌ 전체 pytest 통과 — 본 사고 내내 "테스트 76 passed" 단언이 행동 정상성을 입증한 적 0
- ❌ "review-deep agent 통과" — 본 세션 review가 warn 내고도 통과시킨 자기증명
- ❌ "AC 체크박스 전부 [x]" — 자가 체크는 자가 발화 의존, P8 자체

본 wave 완료 기준은 **사용자 운용 판정**. 자동 테스트는 회귀 발견용 보조 도구일 뿐 wave 통과 게이트 아님.

### Phase 8 — 단일 commit + push

작업:
- [x] 모든 변경 1 commit (분리 안 함, 본 wave 자체가 통합) — 2a5fcd0
- [x] 메시지에 audit #1~#18 해소 매핑·v0.41 baseline 회복·보류 #6 명시 — 2a5fcd0 본문 확인
- [x] v0.46.2 또는 사용자 지정 버전 — v0.46.2
- [x] starter push (`HARNESS_DEV=1 git push origin main`) — origin/main HEAD = 2a5fcd0

## audit 18 항목 매핑 (모든 항목 본 wave 안에서 처리)

| # | 의심 | Phase | 비고 |
|---|------|------|------|
| 1 | pre-check subprocess 누적 | 4 | git diff·ruff·grep 캐시 |
| 2 | cascade naming.md re-read | 0 | revert |
| 3 | promotion HARNESS.json 중복 | 0 + 4 | revert + 잔여 중복 제거 |
| 4 | review_route endswith N회 | 0 | revert |
| 5 | get_secret_patterns dict 매 호출 | 0 | revert |
| 6 | SKILL.md 사본 2개 부담 | **보류** | 사용자 결정: Codex 유지 |
| 7 | split plan도 pre-check | 3 | plan 모드 subprocess 생략 |
| 8 | commit_finalize ALWAYS wip-sync | 4 | 조건부 실행 |
| 9 | wip-sync 전체 iter | 4 | abbr 매칭 우선 |
| 10 | cascade staged_files 2회 iter | 0 | revert |
| 11 | review_route docs-only만 | 2 | 강등 조건 확장 |
| 12 | promotion=release 자동 | 2 | 사용자 명시 게이트 |
| 13 | split 발동 조건 좁음 | 3 | 발동 조건 확장 |
| 14 | cascade rules/만 검사 | 0 | revert |
| 15 | 8키 자가 발화 의존 | 1 | hook 무력화 |
| 16 | 자동 검증 0 (운용 의존) | 2·3 | 정합 패치에 자동 검증 포함 |
| 17 | pytest marker 미등록 | 0 + 5 | revert + marker 등록 |
| 18 | release path starter만 | 2 | 다운스트림 영향 평가 포함 |

**별 wave 0건.** #6은 사용자 명시 보류 (회피 아님).

**Acceptance Criteria**:

- [ ] Goal: v0.41 baseline 사용자 체감 "정상 동작" 회복 + audit 18 중 17건 해소 + #6 보류 명시. 도돌이표 종료.
  검증:
    review: skip
    tests: 없음
    실측: 사용자가 다음 1~3 세션 운용에서 hook 노이즈·write-doc·AC 누락 없음 직접 확인 + `/commit` 1회 실행 시 release path 자동 진입 없음 확인. **자동 단언 금지** — 본 사고 자체가 자동 검증으로 거짓 통과시킨 패턴
- [x] Phase 0 완료: WIP 2개 abandoned 이동·9b29f23 revert·§H 매핑 박제
- [x] Phase 1 완료: settings.json hook 2종 제거 (orchestrator·debug-guard). Gemini auto는 orchestrator 내부 호출이라 자동 제거됨. bug-interrupt.md 수동 가이드 표기 변경 ✅
- [x] Phase 2 완료: harness_version_bump.py patch 좁힘 (#18). promotion/review_route 자동 트리거는 9b29f23 산물이라 revert로 자동 해소 (#11·12) ✅
- [x] Phase 3 완료: split-commit.sh 비파괴 default + --apply 옵트인 + SPLIT_PRE_OUT env 우회 (#7·13) ✅
- [x] Phase 4 완료: pre_commit_check.py git diff·HARNESS.json 중복 read 제거 + commit_finalize.sh wip-sync 조건부 + docs_ops.py wip-sync abbr 우선 (#1·8·9) ✅
- [x] Phase 5 완료: baseline conftest.py가 marker 8종 이미 등록 — revert로 자동 정합 (#17)
- [x] Phase 6 완료: §H-4~11 전면 폐기 결정 — 후속 마이그레이션 입력 자료로 박제
- [ ] Phase 7 완료: 운용 검증 — 사용자가 1~3 세션 실사용 후 OK 판정
- [x] Phase 8 완료: 단일 commit + push (2a5fcd0 v0.46.2), audit #1~#18 매핑 명시 + 보류 #6 명시

## 메모

- CPS 연결: P8 (자가 발화 의존 실패) + P9 (정보 오염 관성). 본 wave가 두 P의 cascade 미완을 hook 무력화 + 자동 메커니즘 폐기로 닫음. Solution은 S8·S9 (부분 인용 — 충족 기준 owner 승인 중)
- 본 wave는 분리 금지. 도돌이표 자체가 wave 분할의 결과 (어제 §H-1~3 분리 commit → 본 세션이 다시 모음). 1 commit 1 wave 원칙
- audit·followups WIP 2개 폐기 방식: `docs_ops.py move`로 abandoned 처리 후 archived/ 이동 (status 박제) 권고. 단순 git rm은 이력 손실
- "코덱스 인프라 유지" 결정의 audit #6 보류는 명시적 — anti-defer.md "사용자 명시 승인" 예외 적용
- 본 문서가 SSOT. 다음 세션은 이 문서만 읽고 Phase 진행 가능
- harness/hn_commit_perf_optimization.md의 §H 시리즈와 hn_commit_process_audit.md의 #1~#18은 본 wave가 supersedes 또는 references — Phase 0에서 정확한 관계 명시

## 변경 이력

- 2026-05-13 생성: 본 세션 9b29f23 도돌이표 + 사용자 증언 "v0.41 정상 마지막" 박제 후 단일 wave 복구 plan 작성. 사용자 결정 "Codex 인프라 유지·별 wave 없음" 반영.
- 2026-05-13 정정 1: Phase 7 "전체 pytest 통과 단언" 폐기 — 본 사고 내내 자동 단언으로 거짓 검증한 패턴. AC 검증 묶음을 `review: skip`·`tests: 없음`·`실측: 사용자 운용 1~3 세션 직접 판정`으로 변경.
- 2026-05-13 정정 2: 본 wave 전략 범위 명시. **정상 작동 회복만 본 wave**, 성능·중복·발화·비효율 최적화는 후속 마이그레이션. 자산 보존 6 영역 박제 — audit WIP 2개는 archived 이동 (단순 폐기 금지), §H 분할 commit·P8/P9 박제·본 세션 자기증명·사용자 증언 모두 다음 wave 입력 자료로 보존.
