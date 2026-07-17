---
id: lazycodex-integration-cps
project_id: harness-starter
type: project
kind: decision
status: active
created: 2026-06-25
title: LazyCodex Integration into Harness CPS
description: "Harness CPS와 LazyCodex의 병렬 리서치, 2회 자가교정 CPS Trace 루프, doc_ops/LLM Wiki 지식 연동을 통합하는 아키텍처 설계"
domain: "harness-starter"
relates_to:
  - gbrain-doc-ops-cps-policy
owner_boundary: "owner-approved integration lanes"
tags:
  - lazycodex
  - harness
  - cps
  - ultrasearch
  - ultrawork
---

# LazyCodex Integration into Harness CPS

## Root Goal
LazyCodex의 강점인 병렬 리서치(Ultra Search) 및 오라클 검증 자가참조 루프(Ultra Work)를 Harness CPS 프레임워크와 결합한다. 이를 통해 2회의 정밀 자가교정 루프 내에서 CPS Trace 공식에 따라 오류를 해결하고, 도메인별 약어(abbr) doc_ops 기반 LLM Wiki 지식을 연동하여 군더더기 없는(Clean & Slim) 고속 개발 라이프사이클을 완성한다.

## Task AC
- **AC-1 (GitHub API 및 비동기 Swarm 리서치 설계)**: 무료 범위 내에서 개인 액세스 토큰(Read-only)을 활용해 Rate Limit을 5,000회로 확장하고, 필요한 채널만 비동기 Swarm 형태로 기동하는 리서치 메커니즘을 정의한다.
- **AC-2 (2회 자가교정 및 CPS Trace 루프 설계)**: 오류 발생 시 최대 2회까지 자가교정을 허용하되, 매 시도와 오류 복구 흐름을 `C > P# > S#` 형태의 CPS Trace 공식으로 구조화하고 `.harness/project/runs/boulder_state.json`에 영속 기록한다. 2회 초과 실패 시 즉시 `HOLD_BLOCKED`로 전이한다.
- **AC-3 (doc_ops / LLM Wiki 및 약어 사전 통합)**: 도메인별 약어(abbr) 및 개념 정의를 포괄하는 LLM Wiki 형태의 지식 체계를 doc_ops 매니페스트로 관리하여 울트라워크의 지식 탐색 리소스를 가속화한다.
- **AC-4 (Clean & Slim 감사 기준 정의)**: 과도한 방어 코드, 쓸모없는 주석, 문서 내 중복 강조를 제거하는 Clean & Slim 원칙을 T8(Maat) 감사 조건으로 강제한다.

---

## C — Context
- Harness 프레임워크는 모든 작업을 Context(C), Problem(P), Solution(S)으로 계층화하여 처리한다.
- 기존의 리서치는 단선적이고 정적이었으며, 구현 실패 시에 전체 맥락을 복구하고 정밀하게 자가교정하는 영속적인 상태 관리 기능이 부재했다.
- 또한, 도메인별로 흩어진 약어(abbr)와 개념 명세가 체계적으로 연동되지 않아 리서치 단계에서 토큰 소모와 시간 지연이 발생했다.
- 이에 LazyCodex의 병렬 탐색 및 오라클 영속 루프를 이식하고, CPS에 기반한 추적(Trace) 공식과 LLM Wiki 형태의 doc_ops를 통합함으로써 고속·고효율의 고품질 검증 라이프사이클을 수립한다.

---

## P — Problems

| ID | 1줄 요약 | 상세 내용 |
|---|---|---|
| **P1** | 비효율적 단선 리서치 및 Rate Limit 병목 | 단순 웹서치와 로컬 탐색만으로는 외부 라이브러리/리포지토리의 최신 소스 트리 및 AST 맥락 조회가 불가능하며, 인증 없는 API 사용 시 시간당 60회 제한으로 인해 비동기 Swarm 탐색이 자주 중단됨. |
| **P2** | 루프의 CPS 추적성 결여 및 무한 루프 위험 | 오류 발생 시 자가교정 과정에서 구체적인 '원인(P) - 해결책(S)' 매핑에 대한 학습 및 역추적(Traceability)이 불가능하여, 맹목적인 코드 수정을 반복하다 토큰을 소모하거나 루프에 갇힘. |
| **P3** | 도메인 지식 파편화 및 지연 | 프로젝트 전반의 핵심 도메인 약어(abbr)와 아키텍처 맥락이 파편화되어, 울트라워크 리서치 시 매번 방대한 문서를 재검색해야 하므로 컨텍스트 비용과 탐색 시간이 급증함. |
| **P4** | 무분별한 주석 및 과도한 방어 코드로 인한 품질 저하 | 자가교정을 거치면서 쓸모없는 예외 처리 블록, 불필요한 디버깅 주석, 문서 내 과도한 동일 내용 중복 강조 등이 누적되어 산출물의 무결성이 훼손됨. |

---

## S — Solutions

| ID | 대상 P# | 1줄 메커니즘 | 해결 및 강제력 기준 (Validation) |
|---|---|---|---|
| **S1** | **P1** | GitHub Token 기반 비동기 Swarm 리서치 및 필요 기반 채널링 | Read-only 개인 토큰을 환경 변수로 연동해 Rate Limit을 5,000회로 확장하고, GitHub API와 로컬 AST, Web 검색을 비동기 Swarm으로 구동하여 최신 소스 및 AST 구조를 정밀 수집. |
| **S2** | **P2** | CPS Trace 공식 (`C > P# > S#`) 및 HOLD_BLOCKED 시 컨텍스트 체이닝이 적용된 2회 자가교정 Boulder 루프 | 오류 발생 시 원인을 `P#`로 식별하고 수정안을 `S#`로 정의한 뒤, `C > P3, P5 > S6, S8 > P2 > S3` 형태의 단선 공식으로 역추적 로그를 남김. 최대 2회 초과 실패 시 즉시 `HOLD_BLOCKED` 전이 후 이전 실패 맥락을 상속하는 Chained Context (New C)를 자동 수립하고 새로운 루프 분기를 준비함. |
| **S3** | **P3** | doc_ops 연계형 LLM Wiki 및 도메인 약어(abbr) 고속 인덱싱 | 도메인 약어 정보와 핵심 설계 문서를 LLM Wiki 형태로 구조화하고, doc_ops 매니페스트를 통해 탐색 시 최우선 순위로 고속 주입하여 탐색 지연과 토큰 소모를 차단. |
| **S4** | **P4** | Clean & Slim 코드 및 문서 정제 규칙의 T8(Maat) 검증 강제 | 예방용 try-catch 남발 및 임시 주석 배제, 문서 내 불필요한 미사여구와 중복 강조의 엄격한 제거를 Maat 감사 매트릭스로 검증하여 통과 시에만 머지 승인. |

---

## 운영 사양 및 설계 기준

### 1. GitHub API 연동 및 비동기 Swarm 리서치 (S1)
*   **Rate Limit 확장**: `GITHUB_TOKEN`(기본 Read-only 권한)을 활용하여 API 한도를 시간당 5,000회로 확장함으로써 비동기 다중 호출 시의 403 Forbidden 오류를 완벽히 예방한다.
*   **필요 기반 비동기 Swarm**: 무분별한 10개 이상의 채널 구동 대신, 탐색 대상의 복잡도와 위험도에 맞춰 **필수 채널(GitHub API, 로컬 AST, Web Search 등)**만 동적으로 기동한다.
*   **산출물 규격**: 수집된 맥락은 인용구(Citation)와 파일 라인 링크가 정확히 명시된 단일 정제 문서인 `research_notes.md`로 비동기 합성된다.

### 2. CPS Trace 공식 및 2회 자가교정 Boulder 루프와 컨텍스트 체이닝 (S2)
*   **영속 상태 관리**: `.harness/project/runs/boulder_state.json`에 자가교정 단계와 상태 스냅샷을 저장하여 세션 유실을 방지한다.
*   **CPS Trace 표현식**: 자가교정 진행 과정에서 단서와 증거의 인과관계를 즉각 파악할 수 있도록 공식 흐름(Trace Expression)을 필수 기록한다.
    *   *형식*: `C > P[이슈번호] > S[적용솔루션] (> P[파생이슈] > S[추가솔루션])`
    *   *예시*: `C > P1, P3 > S2, S4 > P2 > S3` (컨텍스트 유입 후 문제 1, 3을 포착하여 솔루션 2, 4로 대응했으나, 파생 문제 2가 발생하여 최종 솔루션 3으로 완결됨을 직관적으로 표현)
*   **임계치 및 격리**: 
    *   자가교정 시도는 **최대 2회**로 제한한다. 2회차 수정 코드마저 오라클 검증(테스트/린트/빌드)을 통과하지 못하면 루프를 즉시 멈추고 `HOLD_BLOCKED` 상태로 전이한다.
    *   단, 이 2회 제한은 **동일 태스크/동일 오류 지점**에 대해서만 적용되며, 다른 독립적인 단계에서 발생하는 새로운 오류의 카운트는 격리되어 별도 적용된다.
*   **HOLD_BLOCKED 상태 시 Context Chaining (New C) 메커니즘**:
    *   2회 자가교정 실패로 `HOLD_BLOCKED` 상태에 도달하면, 이는 기존 오류가 해결 불가능한 구조적 난관에 봉착했음을 뜻하며 **새로운 맥락의 문제(New C)**가 발생한 것으로 정의한다.
    *   제어 엔진은 단순 중단에 그치지 않고, 이전 루프의 유산(실패 정보, 최종 오류 메시지, `cps_trace` 기록)을 고스란히 상속하는 `chained_context` 메타데이터를 자동 생성하여 상태 파일에 바인딩한다.
    *   이를 통해 이전의 맥락을 논리적으로 이어받는 **새로운 루프(Chained Session)**로의 전이(Transition)를 준비하며, 전이 시 새로운 `P#` 및 `S#`가 재할당되어 체이닝된 문제 해결 프로세스가 매끄럽게 지속되도록 보장한다.

### 3. doc_ops 기반 LLM Wiki 및 도메인 약어(abbr) 통합 (S3)
*   **LLM Wiki 구조화**: 프로젝트의 도메인 약어(abbr), 핵심 설계 원칙, 인터페이스 스펙을 `.harness/project/docs/guides/` 및 `gbrain` 내에 LLM Wiki 형태로 유지한다.
*   **고속 탐색 인덱스**: 울트라워크 기동 시, doc_ops 매니페스트(`doc-ops-manifest.schema.yaml` 기반)에 명시된 약어 사전과 아키텍처 가이드를 에이전트 컨텍스트에 즉각 매핑하여 불필요한 전체 검색 비용을 차단하고 탐색 정확도를 높인다.

### 4. Clean & Slim 품질 감사 (S4)
*   **코드 품질 규격**: 작동을 증명하지 못하는 임시 방어 코드(Unused Try-Catch), 디버깅용 주석 및 하드코딩 요소를 원천 배제한다.
*   **문서 품질 규격**: 팩트 중심의 담백한 한국어/영어 기술을 준수하고, 동일한 성공 조건이나 제약 사항을 수식어로 중복 강조하는 것을 전면 금지한다.
*   **T8(Maat) Gate 연동**: `audit_ponytail_compliance.py` 및 추가적인 정밀 정제 검사 스크립트를 T8 단계에서 실행하여, 정제 기준을 충족하지 못한 코드는 즉시 FAIL 반려한다.
