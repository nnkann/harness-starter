---
title: code-ssot 규칙 신설 — 동형 SSOT 패턴 starter 흡수
domain: harness
problem: [P11]
s: [S11]
tags: [code-ssot, ssot, rule, downstream-cascade]
status: pending
created: 2026-05-17
relates-to:
  - path: decisions/hn_runtime_ssot_generation.md
    rel: caused-by
  - path: decisions/hn_code_ssot_audit.md
    rel: references
---

# code-ssot 규칙 신설 — 동형 SSOT 패턴 starter 흡수

> **상태**: 본 wave(`runtime_ssot_generation`) 종료 후 즉시 진입 예정.
> 박제 시점에는 결정·근거·AC만 기록. 본문 작성 + rule 신설은 다음 wave.

## Context

다운스트림 StageLink가 4건 incident(`ticketOpenDates`·`price`·`poster`·
`artist`) 누적 후 자체 작성한 `ssot-field-audit.md` 규칙이 도메인 무관
일반 패턴:

1. **3+ reference rule** — 같은 로직 3곳 이상 → core 모듈 추출
2. **Derived pointer pattern** — Record/배열 "현재 대표값" 파생 시 단일
   함수로 강제
3. **New field pre-checklist** — 단일 모듈 결정 → 함수 셋업 → 모든 진입점
   통과 → 추출/매칭/처리 통합

starter `.claude/rules/`에 해당 카테고리 부재. 다른 다운스트림이 같은
학습 곡선(4건 누적 → 규칙화)을 독립 재발견할 가능성 高. starter `defends`
체계의 사각지대.

발화 위치: `docs/WIP/decisions--hn_runtime_ssot_generation.md` 본문 끝
FR-011 단락.

## 결정 — 3엔진 만장일치

advisor(Claude) · Gemini · Codex 3엔진 비교 결과 합의 도달:

- **흡수 형태**: 신규 `.claude/rules/code-ssot.md` 신설
  - `coding.md`에 흡수 거부 — Surgical Changes는 변경 *범위* 통제, code-ssot는
    *구조* 판정으로 판단 타이밍이 다름
- **defends 매핑**: P11 (동형 패턴 잠복) 단독
  - P1(no-speculation)은 절차 원칙으로 너무 일반, P7(메타 SSOT)은 문서/인덱스
    영역으로 과확장
  - 신규 P# 불필요 — P11이 본질 포착
- **분리 구조**: starter=일반 원칙 / 다운스트림=사례부 + `rel: references`
  - docs.md "SSOT 인용 원칙 — 본문 복제 금지" 정합

## Codex 추가 정밀 (다음 wave 본문 작성 시 반영)

- **P11 본문 예시 보강**: "field normalization / representative derivation
  / persistence entry points" 추가
- **P12 신설 분기 조건**: "P11이 코드 위치 탐색만 의미하고 lifecycle
  ownership 실패를 담을 수 없다"는 합의가 생길 때만. 미리 만들지 말 것
- **되돌릴 조건 5개**:
  1. 2개 이상 다운스트림에서 2-use 로직까지 과추상화하는 PR 반복
  2. P11 매핑이 review에서 무관한 중복 제거 지적으로 확장
  3. 3+ rule 적용 후 결합도 증가로 필드별 독립 변경 어려운 사례 2건 이상
  4. 다운스트림 사례가 특정 도메인 파서에만 머물고 일반 필드 lifecycle
     문제로 재현되지 않음
  5. 기존 `coding.md`만으로 동일 문제를 안정적으로 차단했다는 반례 축적

## Gemini 추가 사각지대

- Surgical Changes vs SSOT 통합 원칙 충돌 가능성 — `code-ssot.md` 본문에
  "충돌 해소 룰" 1줄 명시 필요 (예: "SSOT 통합 리팩토링은 별도 wave에서,
  본 작업 범위와 분리")

## advisor 사각지대 (해소됨)

- 다운스트림 `ssot-field-audit.md` 원문 미확인 — starter는 일반 원칙만
  담고 사례는 references라서 원문 무관

## 기존 `hn_code_ssot_audit.md`와의 관계

- 기존 audit 문서는 **하네스 내부 SSOT** (스크립트·rule·skill 본문 중복
  정리, P7 매핑) 감사. 주제·관점·defends 모두 다름.
- 본 결정은 **다운스트림 코드 영역 SSOT** (데이터 필드 lifecycle drift,
  P11 매핑). 분리 근거 충족 — references로만 연결.

## 부수 정비 (다음 wave 진입 시 함께)

- `project_kickoff.md` Solutions 표가 S10에서 끝남. P11 정의는 §S-11 박제로
  추가됐으나 S11 행 누락. **매칭 강제 없음(`rules/docs.md` 운영 원칙)**이라
  박제 차단 요인은 아니지만, P11 정의된 wave에 S11 행도 함께 추가하는 게
  표 정합. AC에 포함.

**Acceptance Criteria**:

- [ ] Goal: starter에 `.claude/rules/code-ssot.md` 신설로 동형 SSOT 패턴
  cascade 학습 비용 압축 (S11)
  검증:
    tests: 없음
    실측: 운용 검증 — 다운스트림 1개 이상이 references로 가리키는지
          6개월 관찰
- [ ] `code-ssot.md` 본문: 3+ reference rule · derived pointer pattern ·
  new field pre-checklist 3개 원칙만 (S11)
- [ ] frontmatter `defends: P11` 매핑 (S11)
- [ ] Surgical Changes 충돌 해소 룰 1줄 명시 (S11)
- [ ] `project_kickoff.md` P11 본문에 field lifecycle 예시 보강 + S11 행
  Solutions 표 추가 (S11)
- [ ] MIGRATIONS.md 갱신 (S11)
