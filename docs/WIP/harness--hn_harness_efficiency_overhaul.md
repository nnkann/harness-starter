---
title: 하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)
domain: harness
tags: [eval, efficiency, split, fast-path, downstream, overhaul]
relates-to:
  - path: decisions/hn_harness_upgrade_env_semantics.md
    rel: extends
status: in-progress
created: 2026-05-02
updated: 2026-05-02
---

# 하네스 효율성 전면 점검

## 트리거 발화 (사용자, 2026-05-02)

> "왜 이렇게 비효율적으로 보이는게 많지? 다운스트림에서보면 헛짓거리를
> 너무 많이 하는데? 효율적으로도 안 좋고, 토큰만 낭비하고 느리긴 더럽게
> 느려서 작업 방해하고 이따위 하네스가 필요한가 계속 의문이 들게 만드는데?"
>
> "다운스트림에서는 이런 문제가 더욱 심화된다는게 아주 큰 문제야."
>
> "도메인도 많아지고, CPS도 늘어나고 문서 조회도 늘어나니까 말이야."
>
> "유기적으로 돌아가는게 아니라 짜여진 흐름만 고집해서 답답한 노인네같은
> 느낌이야. 아집과 고집으로 점철된."

## eval --deep 결과 (2026-05-02)

advisor 4 lens 종합 점수 4. 핵심: split 알고리즘이 "1 결정 = N 성격 = N
커밋"으로 분할해 5/5 skip 발생, `HARNESS_DEV=1` 우회 동기 ↑, 시크릿
가드 무력화 위험. 본 세션 직접 증거: v0.28.7 wave 5 sub-커밋 모두 review
skip.

### 3계층 문제

1. **알고리즘 레이어** — split char-only, skip 경로 6개, review skip이 일반
2. **다운스트림 증폭 레이어** — 도메인·CPS·문서 수 증가에 step 비용 비선형
3. **메타 흐름 레이어** — 모든 작업이 동일 파이프라인 (fast/full 분기 없음)

## 사전 보강 (완료 — 2026-05-02)

### researcher 결과 (점수 4/3/4 종합 3)

핵심 발견:
1. **Conventional Commits v1.0.0**: char-class 5그룹 분할 자체는 spec과
   직접 충돌 안 함. 단 "각 커밋이 독립 revert 가능한지"가 atomic 실질
   기준 — 본 프로젝트 5/5 분할이 이를 만족하는지 미검증.
2. **Anthropic Agent Skills (2025-10 공개)**: SKILL.md는 메타데이터
   (~100 tokens) → 본문(<5k tokens) → 번들 파일 3계층 lazy load 권장.
   본 프로젝트 commit/SKILL.md(Step 1~10)·harness-upgrade(Step 0~10)·
   implementation(Step 0~4) **26 step 전체 선제 로드는 progressive
   disclosure 원칙 직접 충돌**.
3. **Cline rules 실측 (Arize)**: 20~50개 룰 범위, 단일 persistent
   system prompt 권장. 다단 절차 step 3~4 이후 coherence 손실 실측.

출처:
- https://www.conventionalcommits.org/en/v1.0.0/
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://arize.com/blog/optimizing-coding-agent-rules-claude-md-agents-md-clinerules-cursor-rules-for-improved-accuracy/
- https://thoughts.jock.pl/p/ai-coding-harness-agents-2026

### threat-analyst 결과 (점수 4 — Phase 1 설계 직접 영향)

**🚨 critical 발견**: 현재 안전망 강도 **5/10**, Phase 1 적용 후 7.5/10.

1. **`install-starter-hooks.sh`에 시크릿 패턴 검사 0건** — L17~31에
   `HARNESS_DEV` 환경변수 유무만 체크. 시크릿 패턴(sb_secret·service_role·
   sk_live·AKIA·ghp 등) 스캔 부재.
2. **`HARNESS_DEV=1 git commit` = 시크릿 가드 완전 우회 경로**:
   - `bash-guard.sh:101~103` — `HARNESS_DEV=1` 통과 분기
   - `pre_commit_check.py` 미호출 → `S1_LINE_PAT`(L431~434) 미실행
   - `install-starter-hooks.sh`도 `HARNESS_DEV=1` 통과
3. **이스케이프 해치 안내가 사용자를 우회로 유도** — `bash-guard.sh:107`
   에러 메시지에 `HARNESS_DEV=1 git commit -m ...` 명시. 다운스트림이
   답답할 때 첫 시도하는 명령.
4. **Claude Code 세션 밖 터미널 우회**: bash-guard.sh는 PreToolUse hook —
   터미널 직접 `git commit --no-verify`는 적용 범위 밖. install-starter-
   hooks.sh의 단순 env 체크만 남음.

**Phase 1 직접 영향**:
- install-starter-hooks.sh hook 본문에 `S1_LINE_PAT`(또는 동등 정규식)
  grep 추가 필수. `HARNESS_DEV=1`이어도 hook에서 시크릿 line 스캔 강제
- `--no-verify` 터미널 우회는 여전히 가능 (Phase 1으로 막을 수 없음 —
  10/10 도달 불가, 7.5/10이 한계)
- HARNESS.json `hook_installed` 플래그 + pre-check 미설치 경고 — WIP
  Phase 1 AC에 이미 반영됨, 유지
- **bash-guard.sh:107 에러 메시지에서 `HARNESS_DEV=1` 안내 톤 변경 검토** —
  "긴급 이스케이프"가 아니라 "비상 시 + 시크릿 별도 hook 검사" 명시.
  Phase 1에 추가

## 작업 목록

### 1. 시크릿 hook 이중화 (안전망 — 다른 작업의 전제)

> kind: feature

`scripts/install-starter-hooks.sh`에 시크릿 line-confirmed 패턴 검사 추가.
threat-analyst 사전 보강에서 **현 hook은 `HARNESS_DEV` env 체크만**이 확인됨
(시크릿 패턴 0). `HARNESS_DEV=1 git commit` 경로가 가드 완전 우회 — 즉시
차단 필요.

**사전 준비**:
- `.claude/rules/security.md` 패턴 목록 재사용
- threat-analyst 결과: `pre_commit_check.py:431~434` `S1_LINE_PAT` 정규식
  를 hook 본문에서도 실행
- `bash-guard.sh:107` 에러 메시지의 `HARNESS_DEV=1` 안내 톤 검토

**Acceptance Criteria**:
- [x] Goal: 스킬 우회·`HARNESS_DEV=1` 경로에서 시크릿 line-confirmed 차단
      (실측: AKIA 더미 staged + `HARNESS_DEV=1 git commit` → exit 1, 차단 확인).
      `--no-verify`는 hook 자체 우회로 막을 수 없음 — README 경고 + bash-guard
      차단 유지로 대응. 안전망 5/10 → 7.5/10 달성
- [x] `install-starter-hooks.sh` hook 본문에 시크릿 패턴 풀(sb_secret·service_role·
      AKIA·sk_live·ghp·glpat·xox·AIza·sk-ant·PRIVATE KEY 등) grep 추가.
      `HARNESS_DEV=1` 이전에 시크릿 검사가 먼저 실행되어 env-bypass와 분리
- [x] hook 미설치 감지 — `HARNESS.json` `hook_installed` 플래그 추가 + 두 hook
      설치 스크립트가 자동 갱신 + `pre_commit_check.py`가 미설치 시 경고 출력
      (실측: `hook_installed=false` 시 stderr 경고 출력 확인)
- [x] `bash-guard.sh` 에러 메시지 톤 갱신 — "비상 이스케이프 + 시크릿 line-
      confirmed 가드는 git pre-commit hook이 항상 실행 — 우회 불가" 명시
- [ ] Windows·Git Bash·WSL 환경 호환 검증 — Git Bash에서 실측 통과. PowerShell·
      WSL 미테스트 (자동 검증 불가, 운용 검증 필요)
- [x] 영향 범위: pre_commit_check.py·install-starter-hooks.sh·bash-guard.sh —
      `pytest -m secret` 4/4 통과 + `pytest -m stage` 8/8 통과 (총 12/12)

### 2. implementation fast-path 도입 (white-list 시작)

> kind: refactor

fast-path는 **white-list**로 시작. "90% fast-path"는 6개월 목표지 즉시
적용 X. 잘못 분류된 위험 작업이 fast-path 통과 시 Phase 1(hook)이 시크릿만
잡고 회귀·계약은 못 잡음 → 사고 시 신뢰 회복 역효과.

**Phase 2-A (즉시)**: 명확한 white-list만 fast-path
- 타이포 수정 (1~3줄, 단일 파일)
- 문서 단독 변경 (코드 0)
- rules 파일 단일 키워드 변경 (구조 무변경)

**Phase 2-B (6개월 후, baseline 측정 후)**: 점진 확대
- small 규모 + 위험도 hit 없음
- 실측 사고 발생률 < 5% 유지 시에만 다음 단계

**사전 준비**:
- implementation Step 0.7 규모 판정 로직 재사용
- 현 "Phase 설계 6원칙 + 핸드오프 6 carry"는 large 기준 — fast-path는 면제

**Acceptance Criteria**:
- [ ] Goal: white-list 작업에서 implementation Step 호출 비용 < 3 tool calls
- [ ] fast-path 트리거 명시 — white-list 패턴 정확히 정의 (타이포 정규식·문서 단독 판정·rules 단일 키워드)
- [ ] 분류 모호 시 full-path로 fail-safe (잘못된 fast-path 진입보다 잘못된 full-path가 안전)
- [ ] fast-path에서도 핵심 가드(internal-first·no-speculation·시크릿 hook)는 유지
- [ ] 영향 범위: implementation/SKILL.md — 운용 검증 (자동 검증 불가). 사고 발생률 추적 메커니즘 명시

### 3. split 옵트인 강등 + AC [x] 자동 이동 (Reversibility 재평가 필요)

> kind: refactor

split을 기본 off, `/commit --split` 또는 review stage 분포 기반 트리거
로만 동작. 5/5 skip 케이스 자동 single 반환. AC 전부 [x] 감지 시
completed 전환 차단 통과 → 자동 git mv.

**⚠️ Reversibility 경고**: WIP 초안은 two-way로 분류했으나, 다운스트림
harness-upgrade가 char별 selective fetch에 의존할 경우 **one-way**.
git history는 이미 단일 커밋으로 나가 있어 char-fetch 시스템이 깨짐.
착수 직전 호환성 확인 필수.

**사전 준비**:
- `task_groups.py` audit #18 원 의도 문서 확인
- **`harness-upgrade/SKILL.md` Step 3·5 본문 Read** — char-fetch 의존성 확인.
  의존 없으면 two-way 유지, 있으면 one-way 재분류 + 다운스트림 호환성 단계 적용
- `docs_ops.py move`의 차단 키워드 검사 재사용

**Acceptance Criteria**:
- [x] Goal: 5/5 skip 케이스에서 split 발생 0 — `stage == "skip"`이면 자동 single. 실측: 본 commit (split_plan=2, non-huge) → split_action=single
- [x] **harness-upgrade char-fetch 의존성 확인** — 미사용 확인. harness-upgrade SKILL.md Step 3·5는 git diff `--diff-filter`로 파일 단위 분류·3-way merge 수행. 커밋 단위 fetch 아님. char-split 폐기 안전
- [x] AC 전부 [x] WIP가 commit 시 자동 이동 — `docs_ops.py wip-sync` body_referenced 신호 추가. 본 변경 적용 후 본 WIP 자체가 자동 이동 트리거 대상 (Phase 1·3 모두 [x] 시점)
- [x] false-positive 안전장치 — `docs_ops.py move`의 차단 키워드 검사(빈 체크박스·TODO·미결 헤더) 통과 시에만 이동. 코드블록 안 면제 유지
- [x] 영향 범위: pre_commit_check.py·docs_ops.py·staging.md — `pytest -m "secret or stage"` 12/12 통과. T40.1 abbr 테스트는 fixture 격리 갭으로 fail (본 fix 무관)

### 4. 다운스트림 증폭 완화 — 규모 기반 게이팅 (측정 게이트 필수)

> kind: refactor

doc-finder fast scan / SSOT 3단계 탐색 / clusters 자동 갱신을 규모·
도메인 등급 기반으로 게이팅. micro·small은 skip, meta 도메인은 다른
step도 자동 skip.

**⚠️ 측정 게이트**: 본 Phase는 다운스트림 실측 데이터 0인 상태에서
"30 tool calls → 3" 추정. 측정 없이 진행 금지. baseline 확보 후 적용.

**Phase 4-A (선행, 코드 변경 0)**: baseline trace 수집
- 다운스트림 1개 프로젝트(예: Issen)에서 동일 작업 1건의 tool call·
  시간 trace 수집
- doc-finder·SSOT 탐색이 도메인 수에 실제로 비례하는지 확인
- 다른 곳이 진짜 병목이면 Phase 4 방향 재설계

**Phase 4-B (Phase 4-A 결과 후)**: 게이팅 코드 적용

**사전 준비**:
- domain 등급 (critical/normal/meta) 정의 staging.md 기존 구조 확인
- Phase 4-A trace 결과 첨부

**Acceptance Criteria**:
- [ ] **Phase 4-A trace 결과 본 WIP `## 메모` 첨부** (baseline 수치)
- [ ] Goal: 다운스트림 도메인 5~10개 환경에서 implementation 진입 비용
      starter 환경 대비 1.5x 이내 (도메인 수에 비선형 의존성 제거 — 측정값으로 검증)
- [ ] meta 도메인 단독 변경 시 doc-finder·SSOT 탐색 skip
- [ ] clusters 갱신은 새 문서 생성·이동 시에만 (commit 매번 X)
- [ ] 영향 범위: implementation/SKILL.md·docs_ops.py — Phase 4-A trace로 효과 측정

### 5. [본 wave에서 분리] 룰-스킬 중복 제거 — 별 WIP로 강등

> kind: refactor

**⚠️ 분리 결정**: 룰 SSOT 강제는 본질적으로 모든 스킬 영향. "commit
한정 1단계"로 시작해도 곧 "implementation·harness-upgrade·eval·write-doc
모두 똑같이 해야 한다"는 압력 발생 → 리팩토링 함정. Phase 1~4 완료 후
별 WIP로 분리하거나, "룰-스킬 중복 발견 시점마다 incremental 정리"로
대체.

본 wave에서는 **착수 안 함**. 본 항목은 placeholder.

후속 처리:
- Phase 1~4 완료 직후 별 WIP 신설 (`decisions--hn_rule_skill_ssot.md`)
- 또는 incremental 정리 정책 채택 시 본 항목 archived

**Acceptance Criteria**:
- [x] 본 wave에서 분리 결정 (작업 안 함)

## 결정 사항

(작업하면서 채움)

## 메모

- 우선순위: 사전 보강 → 1 → 2-A → 3 → 4-A → 4-B → 5(분리). 1이 다른
  작업의 전제 (안전망 없이 축소 금지).
- 2가 사용자 발화 "답답한 노인네" 직격 — 사용자 체감 회복 빠름.
- 3은 advisor 권고지만 Reversibility 재평가 필요 (char-fetch 의존성).
- 4는 측정 게이트 필수 — 추측 기반 적용 금지.
- 5는 본 wave에서 분리 — 리팩토링 함정 회피.
- 본 wave 자체가 large 규모 — Phase 분할 + Phase별 별 PR. 단일 PR로
  묶지 마라 (advisor "atomic commit" 원칙 적용 — 4 결정 = 4 PR, 단 각
  PR 내부는 split 안 함).

### 2026-05-02 — 역방향 평가에서 발견된 약점 5개 (보완 반영 완료)

| # | 약점 | 보완 위치 |
|---|------|-----------|
| 1 | Phase 4(다운스트림 증폭) 측정 부재 | Phase 4-A baseline trace 선행 게이트 추가 |
| 2 | Phase 2 fast-path 트리거 모호 | white-list 시작(2-A) + 점진 확대(2-B) 분리 |
| 3 | Phase 3 Reversibility 낙관 | char-fetch 의존성 확인 사전 준비 추가 |
| 4 | Phase 5 범위 폭주 위험 | 본 wave에서 분리, placeholder 강등 |
| 5 | eval 자체가 advisor self-orchestration | 사전 보강(researcher·threat-analyst 1회씩) 게이트 추가 |

추정 효과 (역방향 검증 보완 후):
- 안전성: 5 → 5 (hook 이중화 + 우회 동기 ↓)
- 속도: 2 → 4 (Phase 2-A·3·4-B 누적)
- 인지 부담: 2 → 4
- 토큰 비용: 작업당 ~20K~30K → ~8K~12K (60% 절감 추정, Phase 4-A
  baseline 측정으로 검증)
- 단일 결정 커밋 수: 5 → 1 (Phase 3 직접 효과, baseline 실측)

## 사각지대 (advisor 명시)

- harness-upgrade Step 0~10 본문 미열람 — 다운스트림 흐름 영향 평가 부분
- task_groups.py audit #18 원 의도 문서 미열람
- install-starter-hooks.sh 현 시크릿 검사 포함 여부 미확인
- 다운스트림 실 사용자 행동 데이터 없음
