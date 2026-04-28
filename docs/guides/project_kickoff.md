---
title: harness-starter CPS
domain: harness
tags: [cps, meta, starter]
status: in-progress
created: 2026-04-20
updated: 2026-04-28
---

# harness-starter CPS

> starter는 다운스트림에 전파되는 메타 프로젝트. CPS 자체가 하네스 품질의
> 기준점.

## Context

**역할**: AI 코딩 에이전트(Claude Code) 행동을 예측 가능·안전하게 만드는
템플릿. 다운스트림 프로젝트가 이식·업그레이드해서 사용.

**제약:**
- 단일 관리자(nnkann) 운영 — 팀 협업 수단 불필요, 간결함 우선
- Claude Code 전용 — 다른 AI 도구 호환 고려 안 함
- Windows + Git Bash가 주 개발 환경 — POSIX 가정 금지
- 실험 단계 (v0.x) — 공개 API 불안정, 다운스트림 실측 누적 후 1.0.0

**공급:**
- 스킬 14 + 에이전트 8 + 규칙 10 + 스크립트 11 + docs 구조
- `~/.claude/` (사용자 전역) 아닌 프로젝트별 `.claude/`에 설치

## Problems

해결해야 할 핵심 문제. 우선순위 순.

### P1. LLM 추측 수정 반복

**증상**: LLM이 공식 문서·git log·기존 결정 확인 없이 같은 파일을 여러 번
"추측 기반"으로 수정.

**영향**:
- 잘못된 수정 → 추가 수정 → 누적
- 실제 원인은 못 잡고 증상 완화만

**승격 상태**: `rules/no-speculation.md` + `rules/internal-first.md` 활성.
pre-check 핵심 설정 연속 수정 차단. HARNESS_EXPAND 우회.

### P2. review 과잉 비용

**증상**: review 에이전트가 단순 커밋(docs 이동·1줄 수정)에도 deep stage
선택하고 불필요한 Read 반복.

**영향**: 매 커밋 수십 초 대기, 토큰 낭비 누적.

**승격 상태**: `rules/staging.md` 경로 기반 5줄 룰, review.md 2축 + 회귀
알파 구조, `maxTurns: 6`.

### P3. 다운스트림 사일런트 페일

**증상**: 다운스트림 업그레이드 시 사용자 수동 액션 누락 감지 못 함.
permissions.allow 미전파, MIGRATIONS.md 공백, starter_skills 오염 등
경계 관리 구멍이 여러 곳에서 발생.

**영향**: 업그레이드했는데 하네스 일부 기능 무력화 (silent). 매 명령마다
승인 프롬프트가 뜨는 등 하네스 효과를 못 받음.

**승격 상태**: 5중 방어 (아래 S3 참조).

### P4. 광역 hook 매처 fragility

**증상**: Claude Code `Bash(* ... *)` 매처가 공백 포함 모든 문자 매칭이라
정당 명령 오차단.

**영향**: LLM이 작업 중 의도 외 차단 → 우회 시도 → 매처 추가 수정 루프.

**승격 상태**: `rules/hooks.md` 금지 규칙 + `bash-guard.sh` 단일 hook
통합 + `test-bash-guard.sh` 회귀.

### P5. MCP·플러그인 컨텍스트 팽창

**증상**: 서브에이전트 spawn 시 컨텍스트 3545k 토큰 보고.

**영향**: 모든 review 호출이 비싸짐.

**승격 상태**: 조사 진행 중. review.md `tools` allowlist 이미 적용.

### P6. 검증망 스킵 패턴

**증상**: SKILL.md·rules 변경이 "단순 문서 변경"으로 분류되어 테스트·CPS
갱신이 암묵적으로 건너뛰어짐. harness-dev 절차에 테스트·CPS 강제 없음.

**영향**: 행동 정의 문서 변경 효과가 검증 없이 커밋됨. MIGRATIONS.md 3개
버전 누락 같은 버그가 오래 방치됨 (2026-04-28 실측).

**승격 상태**: 4중 방어 (아래 S6 참조).

## Solutions

각 Problem의 현 접근. **해결 기준**: 이 조건이 충족돼야 Solution이 작동하는 것으로 판단.
기준 미달이 관찰되면 Problem이 재발한 것 — 새 WIP로 대응.

### S1 (for P1): 규칙 + 자동 차단 + 우회 장치

- **규칙**: no-speculation·internal-first·hooks — 원칙 명시
- **자동 차단**: pre-check의 핵심 설정 연속 수정 차단
- **우회**: `HARNESS_DEV=1 git commit` (정당 점진 확장 시)
- **검증 수단**: review 카테고리 8 CPS 갱신 누락 감지

**해결 기준**:
- 같은 파일을 근거 없이 3회 이상 수정하는 패턴이 세션당 0건
- pre-check이 추측 수정을 차단한 경우 에이전트가 즉시 관찰→재현 흐름으로 전환

**제약**: LLM이 규칙을 읽고도 위반함. 자동 차단이 마지막 안전망.

### S2 (for P2): 패턴 → 행동 매핑 + hard 상한

- **행동 가이드**: review.md 2축(계약·스코프) + 회귀 알파(S7·S8 hit 시만)
- **hard 상한**: `maxTurns: 6` frontmatter
- **Stage 차등**: staging.md 경로 기반 5줄 룰

**해결 기준**:
- review tool call 평균 ≤4회 (micro: 0~2, standard: 1~4, deep: 3~6)
- maxTurns 소진으로 verdict 누락 0건
- docs-only 커밋이 skip 또는 micro로 분류됨

**검증됨 (2026-04-20)**: starter 격리 벤치마크 3시나리오 실측.
상세: `docs/incidents/hn_review_v080_benchmark.md`.

**제약**: 다운스트림은 환경 요인(플러그인·MCP) 추가로 기준선이 다름.

### S3 (for P3): 5중 방어

1. **MIGRATIONS.md** — upstream 소유 지시 문서. 버전별 "이번에 뭘 해야 하는가" 명시
2. **harness-upgrade Step 8** — permissions.allow 동기화 (starter 신규 항목 추가 제안)
3. **harness-upgrade Step 9.5** — 업그레이드 시 수동 액션 섹션 자동 표시
4. **migration-log.md** — 다운스트림 소유 기록 문서. 업그레이드 충돌·이상 소견 기록 → upstream 전달 가능
5. **downstream-readiness.sh** — 적용 후 누락 자가 진단

**해결 기준**:
- 새 버전 릴리즈 시 MIGRATIONS.md에 해당 버전 섹션 존재 (수동 적용 없음도 `없음` 명시)
- 다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨
- 업그레이드 후 `downstream-readiness.sh` 실행 시 누락 항목 0건

**구조 변경 (2026-04-28)**:
- MIGRATIONS.md: 기록물 → 지시 문서로 재설계. 자동/수동 적용 명확히 분리
- migration-log.md 신설: 다운스트림이 작성, upstream은 읽기만
- h-setup.sh 신규 설치 경로 starter_skills 필터 추가
- HARNESS.json starter_skills 경계 정비: harness-dev 제거, harness-sync skills 등록

**제약**: 사용자가 수동 액션을 건너뛰면 무력. migration-log.md를 채우지
않으면 이상 소견 추적 불가.

### S4 (for P4): 단일 hook + 금지 규칙

- **통합**: bash-guard.sh 하나로 모든 argument-constraint 검증
- **금지 규칙**: rules/hooks.md + review가 settings.json diff 보면 감지

**해결 기준**:
- `bash -n` 같은 정당 명령이 hook에 의해 차단되는 사례 0건
- settings.json diff에 argument-constraint 패턴 추가 시 review가 [차단] 발행
- `test-bash-guard.sh` 전 케이스 통과

**제약**: claude-code matcher 동작이 공식 문서와 실측이 다를 때 있음.
incident `hn_bash_n_flag_overblock` 참조.

### S5 (for P5): 조사 + 최소화

**현재 가설 (미확정)**:
- claude.ai 웹 통합 7개 → 사용자가 웹에서 해제 가능
- enabledPlugins 5개 → 필요한 것만 on
- 서브에이전트 `tools` allowlist → 이미 적용 (효과 실측 중)

**해결 기준**:
- 서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (현재 3545k)
- 원인이 특정되면 해당 항목 제거 + 실측 재측정

**제약**: 정확한 원인을 사용자 환경에서만 측정 가능.

### S6 (for P6): 4중 방어

1. **self-verify.md SKIP 조건 명확화** — SKILL.md·rules/*.md는 "단순 문서"가 아님. 테스트 + "자동화 불가 검증" 명시 의무
2. **harness-dev Step 5 semver 표** — SKILL.md·rules 절차 변경 = patch 범프 대상으로 명시
3. **harness-dev Step 6 체크리스트** — 테스트 통과 + CPS 갱신 항목 추가
4. **review 카테고리 8** — 기존 SKILL.md·rules 실질 변경(M, ≥3줄)도 CPS 갱신 감지 대상 추가
5. **commit Step 4 MIGRATIONS.md 자동 작성** — 버전 범프 확정 후 MIGRATIONS.md 섹션 작성 절차 추가 (v0.26.2)
6. **implementation Step 2.5 AC 강제화** — 자동화 가능 AC 실행 기록 의무, 불가 항목 명시 의무 (v0.26.2)
7. **implementation Step 4 CPS 갱신 명시 의무** — "없음"도 WIP ## 결정 사항에 명기 (v0.26.2)

**해결 기준**:
- SKILL.md·rules 변경 커밋에 `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 실행 기록이 있음
- SKILL.md 절차 변경 시 MIGRATIONS.md 해당 버전 섹션 동반
- WIP AC 완료 후 CPS Solution 항목 갱신 여부가 명시적으로 확인됨

**구현 완료 (2026-04-28, v0.26.2)**: 5·6·7번 방어 레이어 추가. 해결 기준 3개 모두 스킬 절차에 강제화됨.
실제 Claude 행동 변화는 운용에서 확인 필요 — "테스트 통과 = 검증됨"으로 포장 금지.

**제약**: SKILL.md 변경의 실제 Claude 행동 변화는 자동 검증 불가 — 운용에서
확인 필요. "테스트 통과 = 검증됨"으로 포장 금지.

## 도메인 목록

현재 확정: harness, meta.

다운스트림은 `naming.md`에서 자기 도메인 추가. starter는 자체 도메인
확장 계획 없음.

## 하네스 강도

strict (본 CLAUDE.md `## 환경`에 기록됨).

이유: starter의 변경은 다운스트림 전파되는 메타 변경. 검증 약화 시
다운스트림 전체에 영향.

## 메모

- 본 문서는 **starter 자체 CPS** — 다운스트림에 전파 안 됨 (`is_starter: true` 전용)
- `project_kickoff_sample.md`는 다운스트림이 `harness-init` 실행 시 템플릿으로 사용
- P1~P5는 2026-04-19~20 실측 기반. P6는 2026-04-28 실측 추가
- Solution은 현 시점 최선. 다운스트림 실측 누적 후 재평가
