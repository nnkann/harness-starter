---
title: 외부 자료 조사 패턴 — Context7·공식 문서
domain: harness
tags: [research, context7, external-docs, mcp]
status: completed
created: 2026-04-20
---

# 외부 자료 조사 패턴

`rules/internal-first.md` 통과 후 외부 자료가 정당한 경우의 도구 선택
가이드. **MCP 무거움 우회 + 토큰 절약**이 목적.

## 우선순위

| 우선 | 도구 | 언제 |
|:---:|------|------|
| 1 | **Context7 HTTP (curl)** | 라이브러리·프레임워크 문서 (React·Next.js·Prisma 등) |
| 2 | **WebFetch** | 특정 URL 알고 있을 때 (공식 문서 페이지 직접) |
| 3 | **WebSearch** | 키워드로 찾아야 할 때 |
| — | ~~Context7 MCP~~ | **폐기.** 토큰 무겁고 deferred라도 목록 부하 |

## Context7 HTTP API (MCP 대체)

### 라이브러리 검색 (resolve-library-id 대체)

```bash
curl -s "https://context7.com/api/v2/libs/search?libraryName=react" | jq
# 또는 특정 쿼리 포함:
curl -s "https://context7.com/api/v2/libs/search?libraryName=next.js&query=middleware" | jq
```

결과: `{ libraries: [{ id: "/vercel/next.js", ... }] }` 형식.

### 문서 조회 (query-docs 대체)

```bash
curl -s "https://context7.com/api/v2/context?libraryId=/vercel/next.js&query=middleware+auth&type=json"
```

라이브러리 ID 형식:
- `/owner/repo` — 최신 버전
- `/owner/repo/v14.3.0` — 특정 버전 (슬래시)
- `/owner/repo@v14.3.0` — 특정 버전 (`@`)

### 인증 (선택)

- **없어도 public 라이브러리 조회 가능** — 대부분 케이스 충분
- 필요 시 [context7.com/dashboard](https://context7.com/dashboard)에서 API key 발급
- `-H "Authorization: Bearer ctx7sk_..."` 헤더 추가

## WebFetch 직접

Claude Code 내장 도구. URL + 자연어 프롬프트.

```
WebFetch
  url: https://docs.anthropic.com/claude/docs/...
  prompt: "X에 대한 설정 방법 추출"
```

Context7보다 LLM 재랭킹 없지만 특정 페이지 알 때 최단 경로.

## WebSearch

URL 모를 때. 결과 요약 + 상위 링크 — 이후 WebFetch로 상세.

## 금지 패턴

- **Context7 MCP 서버 사용 금지** — 세션 context에 schema 부하. HTTP API로
  같은 기능 더 가볍게 가능.
- `mcp__claude_ai_Context7__*` 도구 호출 전에 curl 대안 고려할 것.

## 배경

MCP 서버는 deferred라도 도구 이름·설명이 세션 시작 시 context에 등록됨.
Context7 MCP 2개 tool × 평균 200 tokens = 400 tokens. HTTP API는 0.
작지만 상시 부하라 매 세션 누적.

사용자 claude.ai 통합에서 Context7 해제 권장 (2026-04-20 세션 결정).
