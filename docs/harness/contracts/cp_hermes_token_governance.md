---
title: Hermes 토큰 거버넌스 계약 (Hermes-first, Harness 형식)
description: Hermes 토큰 과다 소모, 429 반복, stale route 누적을 줄이기 위한 실행 규약과 단계별 토큰 거버넌스 패턴
domain: harness/contracts
status: draft
c: hermes_token_governance
problem:
  - 24h 토큰 과다 소모(현재 28.3M > 20M)
  - 2h/24h 429 반복
  - 종료된 세션 라우트 미정리(stale route 46)
  - tool-output 과다로 인한 compression 반복 비용 증가
s:
  - 고빈도 증상의 원인 구간을 Hermes-first로 분해해 근거 기반으로 줄인다
  - 하네스 문서로 정책/운영 가이드를 고정한다
  - 동일 질의 재측정으로 개선 효과를 검증한다
  - route/session lifecycle debt를 지속적으로 축소한다
tags:
  - hermes
  - token-governance
  - cost-control
  - 429
  - route-lifecycle
  - tool-output
relates-to:
  - /Users/kann/.hermes/reports/hermes_token_governance_runtime_report.md
  - /Users/kann/.hermes/reports/token_watchdog/latest.json
  - /Users/kann/.hermes/reports/gbrain_token_analysis_report.md
owner_approval_boundary:
  - no repository or runtime config mutation without explicit owner approval
  - no commit/push until owner accepts post-write review
prohibited_actions:
  - policy changes as raw log snippets or raw stdout dumps
  - route cleanup by best-effort without evidence of stale_db_ended shrinkage
  - bypassing Maat/owner hold by direct implementation in unrelated profile
---

# Hermes Token Governance Contract

## Task AC
- AC1: 토큰 과다 소모/429 재현 지표를 Hermes 리포트(`.hermes/reports`)에서 고정하고 매 수정 전후 비교 가능한 baseline을 남긴다.
- AC2: 운영 작업은 Hermes-first로 시작하고, 정책은 Harness contract로 고정한다.
- AC3: 최소 툴/메모리 모드 적용 기준과 tool-output 상한 정책을 문서화한다.
- AC4: stale route 정리 및 오픈 라우트 상태를 검증할 수 있는 근거를 남긴다.
- AC5: 작업 종료 후 다음 지표 창(2h/24h)을 재측정해 개선 여부를 기록한다.

## C/P/S (evidence framing)

C (Context)
- 최근 `/Users/kann/.hermes/reports/token_watchdog/latest.json`에서
  - 24h 토큰 28.3M 경보
  - 2h 429 26건
  - stale route 46건
  - 라우트 total 64(open_db_open 18, stale_db_ended 46, missing_db 0)
  가 확인됨.
- 세션별 세부 분석에서 terminal/read_file/skill_view/search_files 바이트 비중이 높았고
  compression 종료 세션 비중이 큰 편임.

P (Problem)
- 최소비용 조사 모드가 아닌 기본 모드에서 툴 스키마/출력 누적이 유입되어
  초기부터 부담되는 패턴이 반복됨.
- 라우트 정리가 지연되어 동일 세션/스레드의 종료 상태가 라우팅 상태에 잔존.

S (Solution)
- Hermes-first 증적 경로를 유지: `.hermes/reports` 기준으로 근거만 우선 적재.
- 정책은 본 문서(CP contract)에서 통제:
  1) 최소 툴 모드 우선(예: `hermes --toolsets memory`)
  2) `tool_output.max_bytes` 하향
  3) 정기 stale route 정리
  4) 동일 질의의 사후 재측정.

## Evidence acquisition (digest-first)
- 입력: `token_watchdog/latest.json`, `hermes status`, `hermes sessions` 집계, 상태/세션 DB 조회
- 필수 증거:
  - 시간창(2h, 24h) 토큰합, 429 합계, preflight_compression
  - routes total/live_db_open/stale_db_ended
  - top tool bytes(top 6)
  - 변경 전/후 비교 지표(기준)
- 허용 출력: 행 단위 요약, 수치/경로/타임스탬프
- 금지 출력: 전체 로그, 광범위 grep 전량 결과

## 하네스 실행 단계(문서 기준)
1) 초기 상태 고정
- 기존 근거 파일 경로를 바인딩: `/Users/kann/.hermes/reports/token_watchdog/latest.json`
- baseline 값 캡처(24h,2h,routes,open sessions)

2) 단계별 적용(권장)
- 최소툴 규칙 선언: 메모리/요약 중심 작업 시 `hermes --toolsets memory`
- 출력 상한: `tool_output.max_bytes` 우선 20,000(조건부 10,000)
- 반복 조사: 한 번에 전체 덤프를 하지 말고 `read_file`/`terminal`/`search_files`는 잘린 범위 기반으로 실행
- stale route가 높은 구간은 라우트 정리 절차 후 1~2시간 재측정

3) 종료 조건
- 24h 총 토큰이 알림 임계치(예: 20M) 하향
- 2h 429가 안정 구간으로 하향(10 미만 목표)
- stale route 감소 추세 확인
- 다음 조치: 임시치료 완료 후 `.hermes/reports/hermes_token_governance_runtime_report.md`에 적용 시각 및 수치 반영

## 최소 툴 정책(기본값)
- `hermes --toolsets memory`는 고비용 근원 분석, 라우팅 점검, 요약 질의용으로 최우선 권고.
- 기본 모드 진입 전 다음 항목 점검:
  - 필요하면 `--toolsets` 최소화
  - read/search는 필요한 구간만 수행
  - terminal 출력은 `tail/head` 또는 샘플 라인 중심
- 목적은 정확도 포기 없이 비용/429 리스크를 동시에 낮추는 것.

## Validation matrix
- V1: 리포트 생성: baseline 증거 파일/시간 창 수치가 본 문서에 기록됨.
- V2: 적용 전후 비교: 2h 토큰/429, 24h 토큰, routes stale 지표의 변화가 파일로 남음.
- V3: 규칙 위반 없음: 본 문서의 증거 정책(불필요 대용량 stdout 금지) 준수 여부를 리뷰.

## Related artifacts
- Runtime report: `/Users/kann/.hermes/reports/hermes_token_governance_runtime_report.md`
- Prior analysis: `/Users/kann/.hermes/reports/gbrain_token_analysis_report.md`
- Watchdog snapshot: `/Users/kann/.hermes/reports/token_watchdog/latest.json`
