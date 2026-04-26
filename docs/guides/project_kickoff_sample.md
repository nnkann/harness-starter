---
title: 프로젝트 출범 샘플
domain: meta
tags: [cps, stack, sample]
relates-to: []
status: sample
created: 2026-04-08
---

# 프로젝트 출범: [프로젝트명]

> ⚠️ 이 파일은 **예제 샘플**입니다.
> `harness-init` 스킬을 실행하면 실제 프로젝트의 CPS로 대체됩니다.
> 직접 편집하지 말고, `/harness-init`을 실행하세요.

## 한 줄 정의
소규모 팀을 위한 업무 추적 웹앱.

## 페르소나와 핵심 기능
- **팀 리더**: 작업 생성, 할당, 진행률 대시보드
- **팀원**: 자기 작업 확인, 상태 갱신, 코멘트

## CPS
### Context
- 3~5인 팀에서 스프레드시트로 업무를 추적하고 있으나 상태 동기화가 안 됨.
- 예산과 시간이 제한적이라 기존 도구(Jira 등) 도입 대신 경량 자체 구축.
- 프로젝트 중요도: 팀 내부 도구. → **하네스 강도: light**

### Problem
1. 작업 상태가 팀원 간에 실시간으로 공유되지 않는다.
2. 누가 어떤 작업을 맡고 있는지 한눈에 파악하기 어렵다.

### Solution
1. Problem #1 → 실시간 상태 갱신 (WebSocket 또는 polling).
   ssot: docs/WIP/guides--task_realtime.md
2. Problem #2 → 칸반 보드 UI에 담당자별 필터.
   ssot: docs/WIP/guides--ui_kanban.md
- **강제력**: 상태 변경은 반드시 API를 거치도록 (직접 DB 수정 금지 → 린터/타입으로 강제 불가, 코드 리뷰에서 잡기).

### current
current: Problem #1 실시간 상태 갱신 구현 중 → docs/WIP/guides--task_realtime.md

## 기술 결정
- **프로젝트 유형**: 웹앱 (풀스택)
- **규모**: 소 (도메인 2개: auth, task)
- **아키텍처 패턴**: flat
- **하네스 강도**: light
- **언어/런타임**: TypeScript / Node.js
- **프레임워크**: Next.js
- **패키지 매니저**: pnpm
- **테스트**: Vitest
- **린터/포매터**: ESLint + Prettier
- **배포 환경**: Vercel

## 도메인 목록
- auth (인증)
- task (작업 관리)

## 구현 순서 (Phase 1)
1. auth — 로그인/회원가입
2. task — CRUD + 칸반 보드

## 메모
(프로젝트 진행 중 주요 결정 변화를 간단히 기록)
