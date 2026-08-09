---
id: lazycodex-integration-cps
project_id: harness-starter
type: project
kind: decision
status: active
created: 2026-06-25
title: LazyCodex Integration into Harness CPS
description: "Harness CPS와 LazyCodex의 병렬 리서치, doc_ops/LLM Wiki 지식 연동, Clean & Slim 감사를 유지하는 아키텍처 결정"
domain: "harness-starter"
relates_to:
  - gbrain-doc-ops-cps-policy
owner_boundary: "owner-approved integration lanes"
tags:
  - lazycodex
  - harness
  - cps
  - ultrasearch
  - ultrawork-retired
---

# LazyCodex Integration into Harness CPS

## Root Goal
LazyCodex의 병렬 리서치(Ultra Search), 도메인별 약어(abbr) doc_ops 기반 LLM Wiki 지식 연동, Clean & Slim 감사를 Harness CPS 라이프사이클에서 유지한다. 종전 Ultra Work Boulder/S2 자가교정 및 컨텍스트 체이닝은 현재 아키텍처에서 제외한다.

## Task AC
- **AC-1 (GitHub API 및 비동기 Swarm 리서치 설계)**: 무료 범위 내에서 개인 액세스 토큰(Read-only)을 활용해 Rate Limit을 5,000회로 확장하고, 필요한 채널만 비동기 Swarm 형태로 기동하는 리서치 메커니즘을 정의한다.
- **AC-2 (retired/superseded)**: Boulder/S2의 2회 자동 자가교정, 상태 영속화, 컨텍스트 체이닝은 더 이상 현재 권한 또는 런타임 아키텍처가 아니다.
- **AC-3 (doc_ops / LLM Wiki 및 약어 사전 통합)**: 도메인별 약어(abbr) 및 개념 정의를 포괄하는 LLM Wiki 형태의 지식 체계를 doc_ops 매니페스트로 관리하여 라이프사이클의 지식 탐색 리소스를 가속화한다.
- **AC-4 (Clean & Slim 감사 기준 정의)**: 과도한 방어 코드, 쓸모없는 주석, 문서 내 중복 강조를 제거하는 Clean & Slim 원칙을 T8(Maat) 감사 조건으로 강제한다.

---

## C — Context
- Harness 프레임워크는 모든 작업을 Context(C), Problem(P), Solution(S)으로 계층화하여 처리한다.
- 종전 결정은 구현 실패 시 Boulder/S2가 자동 자가교정과 컨텍스트 체이닝을 수행하도록 설계했으나, 이 경로는 현재 Maat 경계와 맞지 않는다.
- 또한, 도메인별로 흩어진 약어(abbr)와 개념 명세가 체계적으로 연동되지 않아 리서치 단계에서 토큰 소모와 시간 지연이 발생했다.
- 현재 결정은 LazyCodex의 병렬 탐색, LLM Wiki 형태의 doc_ops, Clean & Slim 감사로 구성된 생존 라이프사이클만 유지한다.

---

## P — Problems

| ID | 1줄 요약 | 상세 내용 |
|---|---|---|
| **P1** | 비효율적 단선 리서치 및 Rate Limit 병목 | 단순 웹서치와 로컬 탐색만으로는 외부 라이브러리/리포지토리의 최신 소스 트리 및 AST 맥락 조회가 불가능하며, 인증 없는 API 사용 시 시간당 60회 제한으로 인해 비동기 Swarm 탐색이 자주 중단됨. |
| **P2 (historical)** | 종전 루프의 CPS 추적성 결여 및 무한 루프 위험 | 이 문제에 대응하던 Boulder/S2 자동 루프는 retired/superseded 상태다. |
| **P3** | 도메인 지식 파편화 및 지연 | 프로젝트 전반의 핵심 도메인 약어(abbr)와 아키텍처 맥락이 파편화되어, 울트라워크 리서치 시 매번 방대한 문서를 재검색해야 하므로 컨텍스트 비용과 탐색 시간이 급증함. |
| **P4** | 무분별한 주석 및 과도한 방어 코드로 인한 품질 저하 | 자가교정을 거치면서 쓸모없는 예외 처리 블록, 불필요한 디버깅 주석, 문서 내 과도한 동일 내용 중복 강조 등이 누적되어 산출물의 무결성이 훼손됨. |

---

## S — Solutions

| ID | 대상 P# | 1줄 메커니즘 | 해결 및 강제력 기준 (Validation) |
|---|---|---|---|
| **S1** | **P1** | GitHub Token 기반 비동기 Swarm 리서치 및 필요 기반 채널링 | Read-only 개인 토큰을 환경 변수로 연동해 Rate Limit을 5,000회로 확장하고, GitHub API와 로컬 AST, Web 검색을 비동기 Swarm으로 구동하여 최신 소스 및 AST 구조를 정밀 수집. |
| **S2 (retired/superseded)** | **P2** | 종전 2회 자가교정 Boulder 루프 및 컨텍스트 체이닝 | 현재 런타임 아키텍처와 권한에서 제외한다. 자동 `New C` 또는 `new_context_id` 생성은 현재 권한이 아니다. |
| **S3** | **P3** | doc_ops 연계형 LLM Wiki 및 도메인 약어(abbr) 고속 인덱싱 | 도메인 약어 정보와 핵심 설계 문서를 LLM Wiki 형태로 구조화하고, doc_ops 매니페스트를 통해 탐색 시 최우선 순위로 고속 주입하여 탐색 지연과 토큰 소모를 차단. |
| **S4** | **P4** | Clean & Slim 코드 및 문서 정제 규칙의 T8(Maat) 검증 강제 | 예방용 try-catch 남발 및 임시 주석 배제, 문서 내 불필요한 미사여구와 중복 강조의 엄격한 제거를 Maat 감사 매트릭스로 검증하여 통과 시에만 머지 승인. |

---

## 운영 사양 및 설계 기준

### 1. GitHub API 연동 및 비동기 Swarm 리서치 (S1)
*   **Rate Limit 확장**: `GITHUB_TOKEN`(기본 Read-only 권한)을 활용하여 API 한도를 시간당 5,000회로 확장함으로써 비동기 다중 호출 시의 403 Forbidden 오류를 완벽히 예방한다.
*   **필요 기반 비동기 Swarm**: 무분별한 10개 이상의 채널 구동 대신, 탐색 대상의 복잡도와 위험도에 맞춰 **필수 채널(GitHub API, 로컬 AST, Web Search 등)**만 동적으로 기동한다.
*   **산출물 규격**: 수집된 맥락은 인용구(Citation)와 파일 라인 링크가 정확히 명시된 단일 정제 문서인 `research_notes.md`로 비동기 합성된다.

### 2. Retired/superseded Boulder 자가교정 및 컨텍스트 체이닝 (S2)
*   Boulder/S2 구현과 callable CLI entrypoint는 퇴역했다. 2회 자동 자가교정, Boulder 상태/ledger 기록, 후속 루프 전이는 현재 라이프사이클의 일부가 아니다.
*   자동 `New C` 또는 `new_context_id` 생성은 현재 권한이 아니다.
*   canonical replacement boundary는 **현재 Maat-selected C-boundary**와 그 경계를 변경하지 않는 **immutable packet-bound actor path**다. 선택된 actor는 고정된 packet 범위 안에서만 실행하고 새 C를 자동 생성하거나 packet을 재해석하지 않는다.

### 3. doc_ops 기반 LLM Wiki 및 도메인 약어(abbr) 통합 (S3)
*   **LLM Wiki 구조화**: 프로젝트의 도메인 약어(abbr), 핵심 설계 원칙, 인터페이스 스펙을 `.harness/project/docs/guides/` 및 `gbrain` 내에 LLM Wiki 형태로 유지한다.
*   **고속 탐색 인덱스**: 라이프사이클 기동 시, doc_ops 매니페스트(`doc-ops-manifest.schema.yaml` 기반)에 명시된 약어 사전과 아키텍처 가이드를 에이전트 컨텍스트에 즉각 매핑하여 불필요한 전체 검색 비용을 차단하고 탐색 정확도를 높인다.

### 4. Clean & Slim 품질 감사 (S4)
*   **코드 품질 규격**: 작동을 증명하지 못하는 임시 방어 코드(Unused Try-Catch), 디버깅용 주석 및 하드코딩 요소를 원천 배제한다.
*   **문서 품질 규격**: 팩트 중심의 담백한 한국어/영어 기술을 준수하고, 동일한 성공 조건이나 제약 사항을 수식어로 중복 강조하는 것을 전면 금지한다.
*   **T8(Maat) Gate 연동**: `audit_ponytail_compliance.py` 및 추가적인 정밀 정제 검사 스크립트를 T8 단계에서 실행하여, 정제 기준을 충족하지 못한 코드는 즉시 FAIL 반려한다.
