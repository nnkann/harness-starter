---
title: 코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리
domain: harness
tags: [ssot, audit, code, refactor]
problem: P7
s: [S7, S9]
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# 코드 SSOT 서더링 감사

## 배경

rules/docs.md에 "SSOT 우선 + 분리 판단" 원칙을 **문서 레벨**로 박은 직후,
사용자 지적:

> 문서에 적용된 SSOT 규칙은 코드에도 마찬가지 적용되어야 한다.

코드 파일들(셸 스크립트·설정·JSON·에이전트·스킬 본문)에 "같은 사실이
여러 곳에 중복 정의되어 동기화 부담이 생긴 곳"이 있는지 codebase-analyst로
전수 감사.

## 감사 결과 (7건 식별)

| 중복 대상 | 존재 위치 | 중복 유형 | 영향도 | 처리 |
|-----------|-----------|-----------|--------|------|
| 위험도 게이트 조건 (파일 5개·삭제 50줄·핵심 설정·보안 패턴·인프라) | `pre-commit-check.sh` L103~134 (구현) / `commit/SKILL.md` L85~91 (텍스트) | 사양+구현 이중 정의. sh 수정 시 SKILL 드리프트 위험 | **높음** | ✅ 해소 — SKILL을 SSOT 포인터로 축소 |
| 시크릿 패턴 정규식 (`sb_secret_`·`service_role`·`AKIA[0-9A-Z]{16}`·`sk_live_`·`ghp_`) | `pre-commit-check.sh` L231 / `review.md` L71~73 / `threat-analyst.md` L48~50 / `security.md` | 탐지 로직 중복. 4곳 중 sh만 갱신하고 나머지 구버전 잔존 위험 | **중간** | ✅ 해소 — review·threat-analyst를 pre-commit-check.sh SSOT 참조로 |
| completed 차단 키워드 (`TODO`·`FIXME`·`후속`·`미결`·`미결정`·`추후`·`나중에`·`별도로`) | `rules/docs.md` / `commit/SKILL.md` L339 / `docs-manager/SKILL.md` L145 | 3곳 열거, 키워드 추가 시 3곳 동기화 | **중간** | ✅ 해소 — rules/docs.md SSOT, SKILL 2곳은 포인터 |
| WIP 파일명 접두사 규칙 (`decisions--`·`guides--`·`incidents--`·`harness--`) | `rules/docs.md` / `commit/SKILL.md` L323 / `staging.md` / `pre-commit-check.sh` L318 | 4곳 산재. 새 접두사 추가 시 일부만 갱신 위험 | **중간** | ⏸ 보류 — commit SKILL의 "이동 표"는 LLM 행동 규칙이라 텍스트 복사본 필요 |
| 이동 허용 폴더 (`decisions·guides·incidents·harness·archived`) | `rules/docs.md` / `commit/SKILL.md` L345 / `docs-manager/SKILL.md` | 목록 재열거 | **낮음** | ⏸ 보류 — 변경 빈도 낮아 실제 부담 미미 |
| staging 신호 정의 (S1~S15) | `pre-commit-check.sh` L206~390 (탐지 SSOT) / `rules/staging.md` (명세 SSOT) / `review.md` L258~275 (카테고리 표) | 탐지·명세·소비 3층 구조 | **낮음** | ⏸ 보류 — 의도적 "소비 계약" 패턴. 설계 의도 |
| 하네스 강도 판정 (CLAUDE.md에서 읽기) | `pre-commit-check.sh` L96 (grep) / `commit/SKILL.md` L63 (LLM이 읽는 방식) | sh 읽기 로직은 sh에만, SKILL은 "값 읽는다"만 서술 | **낮음** | ⏸ 현행 유지 — sh stdout 노출 방안은 후일 검토 |

## 즉시 해소 3건 (상세)

### 해소 #1: 위험도 게이트 이중 정의 제거

- **Before**: commit/SKILL.md L83~91에 5개 조건 텍스트 나열
- **After**: `"SSOT: pre-commit-check.sh의 CORE_FILES·SECURITY_PATTERNS·
  INFRA_FILES 정규식 + 임계. pre-check stdout risk_factors 참조"`
- **효과**: sh 수정 시 SKILL 드리프트 불가. 조건 추가는 sh 한 곳만

### 해소 #2: completed 차단 키워드 3중 → SSOT 포인터

- **Before**: commit/SKILL.md L339와 docs-manager/SKILL.md에 키워드 8개
  나열
- **After**:
  - commit/SKILL.md: `"SSOT: rules/docs.md '## completed 전환 차단' 섹션"`
  - docs-manager/SKILL.md: grep 패턴은 유지(실행 구현), 상단에 SSOT 포인터
- **효과**: 키워드 추가는 rules/docs.md 한 곳. grep 패턴은 그 SSOT를
  실행하는 구현으로 명시

### 해소 #3: 시크릿 패턴 분산 → pre-check SSOT 위임

- **Before**: review.md에 자체 정규식, threat-analyst.md에 자체 패턴 리스트
- **After**:
  - review.md: `"pre-check s1_level=line-confirmed 신뢰. 패턴은 SSOT 참조,
    재탐지 안 함"` + false positive 예외 (전제 컨텍스트 명시 시)
  - threat-analyst.md: 패턴 리스트는 요약 유지(독자 이해용), SSOT 명시 +
    실제 스캔 시 pre-commit-check.sh 정규식 참조
- **효과**: pre-check가 1차 탐지 완료 후 s1_level을 넘겨주는 기존 구조
  활용. 에이전트가 패턴을 재보유할 이유 제거

## 보류 대상 (의도적)

- **WIP 파일명 접두사 (commit 이동 표)**: LLM이 이동 결정을 직접 내리는
  행동 규칙. 텍스트 복사본 필요. rules/docs.md와 동기화만 주의.
- **staging 신호 3층 구조**: 탐지(sh) + 명세(staging.md) + 소비(review.md)
  는 설계 의도. "소비 계약" 패턴으로 허용.
- **허용 폴더 목록**: 짧고 변경 빈도 낮음. 실제 동기화 부담 미미.

## 사각지대 (감사 외)

- harness-init/adopt/upgrade SKILL.md에 WIP 접두사 언급 있음 → 실제 사용
  예시(파일명 템플릿)이지 목록 재정의 아님. 문제 없음.
- gitleaks 설정 파일(`.gitleaks.toml`)은 리포에 없음. 시크릿 패턴 4번째
  정의 위치 없음.

## 메모

- 해소 3건은 같은 커밋(0.13.0 → 0.13.1)에 포함. 본 문서가 근거 SSOT.
- 보류 3건은 향후 실측(해당 영역 수정 빈도·드리프트 발생 여부)에 따라
  재평가.
- 문서 SSOT 원칙(rules/docs.md)과 코드 SSOT 원칙은 동일한 기준 적용:
  "같은 사실이 여러 곳에 있으면 한 곳은 정의(SSOT), 나머지는 포인터".
