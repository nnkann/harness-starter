---
title: harness-starter CPS
domain: harness
tags: [cps, meta, starter]
status: in-progress
created: 2026-04-20
updated: 2026-04-20
---

# harness-starter CPS

> starter는 다운스트림에 전파되는 메타 프로젝트. CPS 자체가 하네스 품질의
> 기준점. 이번 세션에 CPS 없이 작업이 진행되어 추측 수정·토큰 과소비·
> review 품질 저하가 누적됨. 본 문서로 회수.

## Context

**역할**: AI 코딩 에이전트(Claude Code) 행동을 예측 가능·안전하게 만드는
템플릿. 다운스트림 프로젝트가 이식·업그레이드해서 사용.

**제약:**
- 단일 관리자(nnkann) 운영 — 팀 협업 수단 불필요, 간결함 우선
- Claude Code 전용 — 다른 AI 도구 호환 고려 안 함
- Windows + Git Bash가 주 개발 환경 — POSIX 가정 금지
- 실험 단계 (v0.x) — 공개 API 불안정, 다운스트림 실측 누적 후 1.0.0

**공급:**
- 스킬 13 + 에이전트 8 + 규칙 10 + 스크립트 11 + docs 구조
- `~/.claude/` (사용자 전역) 아닌 프로젝트별 `.claude/`에 설치

## Problems

해결해야 할 핵심 문제. 우선순위 순.

### P1. LLM 추측 수정 반복

**증상**: LLM이 공식 문서·git log·기존 결정 확인 없이 같은 파일을 여러 번
"추측 기반"으로 수정. 본 세션만 settings.json 매처 3회, 각기 다른
패턴으로.

**영향**:
- schema validation 에러 → 40k 토큰 허비
- 잘못된 수정 → 추가 수정 → 누적
- 실제 원인은 못 잡고 증상 완화만

**승격 상태**: `rules/no-speculation.md` + `rules/internal-first.md`
활성. pre-check 핵심 설정 3회 차단 + HARNESS_EXPAND 우회.

### P2. review 과잉 비용

**증상**: review 에이전트가 단순 커밋(docs 이동·1줄 수정)에도 deep stage
선택하고 15 tool calls로 68k 토큰 소비. "궁금증 탐색"으로 불필요한 Read
반복.

**영향**:
- 매 커밋 수십 초 대기
- 토큰 낭비 누적

**승격 상태**: `rules/staging.md` 1번 룰 정밀화(S9+메타 단독은 deep X),
review.md 패턴→행동 매핑, `maxTurns: 6`.

### P3. 다운스트림 사일런트 페일

**증상**: 다운스트림 프로젝트에 starter 업그레이드 적용 시 사용자 수동 액션
(도메인 등급·경로 매핑) 누락 감지 못 함. README 덮어쓰기 위험. 구버전
매처 찌꺼기 잔존.

**영향**: 업그레이드했는데 하네스 일부 기능 무력화 (silent).

**승격 상태**: `MIGRATIONS.md` + `downstream-readiness.sh` + harness-upgrade
Step 8.2(구 hook 감지) + 9.5(수동 액션 표시).

### P4. 광역 hook 매처 fragility

**증상**: Claude Code `Bash(* ... *)` 매처가 공백 포함 모든 문자 매칭이라
정당 명령 오차단. 본 세션에 `IS=$(grep ...)`·compound 명령 등이 git commit
매처에 우연 매칭 차단됨.

**영향**: LLM이 작업 중 의도 외 차단 → 우회 시도 → 매처 추가 수정 루프.

**승격 상태**: `rules/hooks.md` 금지 규칙 + `bash-guard.sh` 단일 hook
통합 + `test-bash-guard.sh` 회귀.

### P5. MCP·플러그인 컨텍스트 팽창

**증상**: 서브에이전트 spawn 시 컨텍스트 3545k 토큰 보고. 정확한 원인은
아직 실측 중 (MCP 통합·플러그인·rules 자동 로드 후보).

**영향**: 모든 review 호출이 비싸짐.

**승격 상태**: 조사 진행 중. `MIGRATIONS.md` v0.7.1에 MCP 다운스트림
최소화 가이드. review.md `tools` allowlist 이미 적용.

## Solutions

각 Problem의 현 접근 + 대안·제약.

### S1 (for P1): 규칙 + 자동 차단 + 우회 장치

- **규칙**: no-speculation·internal-first·hooks — 원칙 명시
- **자동 차단**: pre-check의 핵심 설정 3회 연속 수정 차단
- **우회**: `HARNESS_EXPAND=1 git commit ...` (정당 점진 확장 시)
- **검증 수단**: review의 "허위 후속 감지" 카테고리

**제약**: LLM이 규칙을 읽고도 위반함 (이번 세션 실측). 자동 차단이 마지막
안전망이지만 그 전에 review가 잡아야 함. review.md에 추측 패턴 감지 추가
검토.

### S2 (for P2): 패턴 → 행동 매핑 + hard 상한

- **행동 가이드**: review.md "검증 루프" 섹션, diff에서 감지할 8가지 패턴
  각각에 tool 선택·호출 횟수 명시
- **hard 상한**: `maxTurns: 6` frontmatter
- **Stage 차등**: staging.md 룰 조정으로 doc-only critical을 micro로

**제약**: LLM이 가이드를 따르지 않으면 무의미. 실측이 유일한 검증 수단.
다운스트림에서 다음 review 호출 토큰 재측정 필요.

### S3 (for P3): 3중 방어

- **사용자 가이드**: MIGRATIONS.md 버전별 수동 액션 체크리스트
- **자동 안내**: harness-upgrade Step 9.5가 업그레이드 시 표시
- **자가 진단**: downstream-readiness.sh로 적용 후 누락 검출

**제약**: 사용자가 readiness를 돌리지 않으면 무력. 다음 업그레이드 때 Step
9.5가 readiness 자동 실행하도록 개선 검토.

### S4 (for P4): 단일 hook + 금지 규칙

- **통합**: bash-guard.sh 하나로 모든 argument-constraint 검증. settings.json
  매처는 `"Bash"` 한 줄.
- **금지 규칙**: rules/hooks.md + review가 settings.json diff 보면 감지

**제약**: claude-code matcher 동작이 공식 문서와 실측이 다를 때 있음.
incident `bash_n_flag_overblock`에 미해결 수수께끼 1건 기록.

### S5 (for P5): 조사 + 최소화

**현재 가설 (미확정)**:
- claude.ai 웹 통합(Gmail·Slack 등 7개) → 사용자가 웹에서 해제 가능
- enabledPlugins 5개 → 필요한 것만 on
- 서브에이전트 `tools` allowlist → 이미 적용 (효과 실측 중)

**제약**: 정확한 원인을 사용자 환경에서만 측정 가능 (transcript·/context).
starter 관리자가 단정 수정하지 않고 실측 기반으로 조치.

## 도메인 목록

현재 확정: harness, meta.

다운스트림은 `naming.md`에서 자기 도메인 추가. starter는 자체 도메인
확장 계획 없음.

## 하네스 강도

strict (본 CLAUDE.md `## 환경`에 기록됨).

이유: starter의 변경은 다운스트림 전파되는 메타 변경. 검증 약화 시
다운스트림 전체에 영향.

## 메모

- 본 문서는 **starter 자체 CPS** — 다운스트림에 전파 안 됨 (`is_starter:
  true` 전용).
- `project_kickoff_sample.md`는 다운스트림이 `harness-init` 실행 시
  템플릿으로 사용.
- P1~P5는 본 세션(2026-04-19~20) 실측 기반. 새 Problem 발견 시 본 문서
  갱신 + 세션 incident 기록.
- Solution은 현 시점 최선. 다운스트림 실측 누적 후 재평가.
