---
title: 문서 헬스체크 레이어 재정의
domain: harness
c: "사용자: doc-health는 레거시 정비 외에도 하네스가 문서를 임의 생성할 때 품질 체크로 필요하지 않나?"
problem: [P6, P7, P11]
s: [S6, S7, S11]
tags: [doc-health, eval, docs]
status: completed
created: 2026-05-31
updated: 2026-06-01
---

# 문서 헬스체크 레이어 재정의

## CPS Rationale

- C -> P: doc-health를 레거시 정비로만 흡수하면 이후 문서 생성/수정 품질 게이트가 사라져 P6/P7/P11이 재발한다.
- P -> S: S6은 완료 증거 위치, S7은 문서 그래프 소유권, S11은 중복 SSOT drift 탐색을 고정한다.
- S -> AC: AC가 규칙·스킬·README에서 문서 헬스체크의 위치와 역할 분리를 확인한다.

## 구현 계획

1. `docs.md`에 문서 헬스체크 레이어의 owner SSOT를 추가한다.
2. 활성 `.claude`의 `eval`, `write-doc`, `implementation` 스킬이 해당 레이어를 호출하도록 문구를 정렬한다.
3. README의 `/eval --harness` 설명에서 레거시 정비만 강조하지 않게 조정한다.

## 작업 목록

### 1. 문서 헬스체크 역할 분리

**Acceptance Criteria**:
- [x] Goal: S6/S7/S11 기준으로 doc-health를 독립 레거시 정비 도구가 아니라 문서 생성/수정 품질 게이트 레이어로 재정의한다.
  검증:
    review: self
    tests: `python3 .claude/scripts/pre_commit_check.py`
    실측: `rg -n "문서 헬스체크|doc-health|레거시 정비" .claude/rules .claude/skills README.md`
- [x] `docs.md`가 문서 헬스체크 항목과 `write-doc`/`implementation`/`pre-check`/`eval --harness` 역할 분리를 정의한다.
- [x] `eval --harness` 설명이 레거시 정비보다 문서 헬스체크를 우선 역할로 설명한다.
- [x] 문서 생성 스킬들이 완료 전 문서 헬스체크를 수행하도록 지시한다.
- [x] README의 `/eval --harness` 한 줄 설명이 새 역할과 맞다.

## 결정 사항

- `.claude/rules/docs.md`를 owner SSOT로 지정했다. `doc-health`는 별도 레거시 정비 스킬이 아니라 문서 생성·수정 품질 게이트 레이어다.
- `eval --harness`는 repository 전체 문서 헬스와 CPS 무결성을 보는 보고 채널이고, 레거시 정비 안내는 부가 출력으로 둔다.
- `write-doc`과 `implementation`은 완료 전 문서 헬스체크 체크 항목을 자기 검증한다.
- CPS 갱신: 없음.

## 메모

- 과거 `docs/decisions/hn_adopt_legacy_doc_health.md`는 당시 레거시 정비 설계 근거로 유지한다. 현재 운영 SSOT는 `.claude/rules/docs.md`에 둔다.
- `.agents/skills/*` mirror 수정은 sandbox 밖 권한 요청이 거절되어 이번 커밋 범위에서 제외했다. 활성 owner SSOT는 `.claude/rules/docs.md`다.
