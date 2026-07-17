---
title: starter decisions 부분 cascade로 인한 dead link 그래프 끊김
domain: harness
problem: [P11]
s: [S11]
tags: [cascade, decisions, dead-link, downstream, verify-relates]
status: completed
created: 2026-05-17
updated: 2026-05-17
relates-to:
  - path: decisions/hn_code_ssot_rule.md
    rel: caused-by
  - path: .claude/skills/harness-upgrade/SKILL.md
    rel: references
---

# starter decisions 부분 cascade로 인한 dead link 그래프 끊김

> **상태**: 박제. 동일 패턴 1~2회 추가 발견 시 별 wave 진입 트리거.

## Context

v0.50.0 다운스트림 적용 후 FR-002로 보고된 첫 발생 사례. starter
`docs/decisions/hn_*` cascade 정책이 rules 본문 grep 기반 동적 탐색
(`harness-upgrade` Step 3 REFERENCED_DOCS)인데, cascade된 decisions가
**비-cascade 동료 decisions를 frontmatter로 참조**하면 다운스트림
verify-relates에 영구 dead link 경고가 누적된다.

## 다운스트림 실측 (FR-002 본문 그대로)

- upstream에 target 파일 존재 확인:
  `git cat-file -e harness-upstream/main:docs/decisions/hn_runtime_ssot_generation.md` → EXISTS
- upstream `decisions/hn_*` 60개 중 **48개가 다운스트림 부재**
- cascade된 12개는 모두 rules 본문에서 직접 grep된 docs만
  (`harness-upgrade` Step 3 REFERENCED_DOCS 동적 탐색 결과)
- dead link 발생 메커니즘: cascade된 12개 중 `caused-by`·`references`로
  비-cascade 48개를 가리키는 frontmatter가 있으면 dead link 영구화.
  `hn_code_ssot_rule.md`가 **첫 사례**

## verify-relates 실제 출력 (다운스트림)

```
⚠️  docs/decisions/hn_code_ssot_rule.md: relates-to 'decisions/hn_runtime_ssot_generation.md' (resolved: docs/decisions/hn_runtime_ssot_generation.md) 존재하지 않음
결과: 미연결 relates-to 1 건
```

`hn_code_ssot_rule.md` frontmatter:
```yaml
relates-to:
  - path: decisions/hn_runtime_ssot_generation.md
    rel: caused-by              # ← 비-cascade 회고
  - path: decisions/hn_code_ssot_audit.md
    rel: references              # ← cascade됨 (rules가 가리킴)
```

## starter 측 사실 확인

- starter 자체 `verify-relates`: 경고 없음 (`hn_runtime_ssot_generation.md`
  존재)
- 다운스트림에서만 발생 — cascade 정책 산물
- FR-002 진단 정확

## 실천 후보 (다운스트림 제안)

1. cascade된 decisions의 `relates-to`에서 비-cascade 동료 참조를 빌드
   타임에 감지·차단 (starter CI에 lint 추가)
2. `rel: references-starter-only` 신규 rel type 도입 (다운스트림
   verify-relates에서 자동 skip)
3. cascade된 decisions의 `relates-to`에서 비-cascade 동료 참조를 자동
   제거 (cascade 시 frontmatter 후처리)

## starter 측 평가 (별 wave 진입 시 advisor·3엔진 비교 필요)

- **옵션 1 (lint)**: 가장 보수적. 단 작성 시점에 cascade 여부를 LLM이
  알기 어려움 — rules 본문 grep으로 결정되는 동적 cascade라 작성 직후
  판정 불가
- **옵션 2 (신규 rel type)**: P11 함정 (taxonomy 비대) 우려. 단 의미가
  명확하면 회피 가능. 기존 4종(`extends`·`caused-by`·`references`·
  `supersedes`)과 직교성 확보 필요
- **옵션 3 (cascade 시 후처리)**: 자동·투명. 단 다운스트림이 받는 결정
  문서의 frontmatter가 starter 원본과 다름 — drift 위험

**잠정 권고** (별 wave에서 3엔진 비교 후 확정): 옵션 1+3 조합이 자연스러움.
starter 작성 시점 lint(작성자 인지 도움) + cascade 시 후처리(다운스트림
노이즈 0). 단 추측이므로 본 wave에서 확정 금지.

## 사각지대

- **재발 빈도 미측정**: 본 wave가 첫 사례. 1~2 wave 추가 발생 시점에
  별 wave 본격 진입. 단발 사례로 메커니즘 변경하면 over-engineering 위험
- **starter `decisions/hn_*` 전수 frontmatter 감사 누락**: 본 사례 외
  다른 비-cascade 참조가 잠복할 가능성 — 별 wave Step 0으로 감사 필요
- **REFERENCED_DOCS 동적 탐색 자체의 한계**: rules 본문이 가리키지
  않는 decisions는 cascade에서 누락. 결정의 link 그래프가 rules 본문
  의존도와 무관하게 끊김

## 결정 사항

- **옵션 1+3 결합** (advisor·Gemini·Codex 3엔진 비교 후 Gemini·Codex 일치).
  advisor는 옵션 1 단독 권고했으나, 본 wave Step 0 감사에서 **이미 발생한
  2건의 잠복 사례** 발견 → 옵션 3 (cascade-time rewrite) 필수성 증명.
- **신규 helper script** `.claude/scripts/cascade_docs.py` 신설 (Codex 권고
  구조). `docs_ops.py` 과부하 회피.
- **함수 분해**: `compute_cascade_set()`·`find_rule_referenced_decisions()`·
  `strip_non_cascading_relates()`·`rewrite_frontmatter_for_downstream()`·
  `check_cascade_boundary_violations()`.
- **docs_ops.py `cmd_verify_relates` 확장**: starter 환경(`is_starter: true`)
  에서만 cascade boundary 위반 차단. 다운스트림은 일반 dead-link warn-only
  로 흡수.
- **`harness-upgrade` Step 3에 rewrite 호출 추가**: cascade되는 결정문서를
  복사하기 전 frontmatter projection-safe 정제. upstream 원본 불변.
- **starter 기존 2건 cleanup**: `hn_code_ssot_rule` (caused-by 제거,
  본문에 발화 위치 인용 유지), `hn_harness_73pct_cut` (supersedes 제거,
  본문 §0에 supersede 정보 1줄 인용).
- **CPS 갱신**: 없음. P11/S11 매핑 그대로.

## 메모

- 3엔진 결과 비교 (요약):
  - advisor: 옵션 1 단독 (drift 우려). 70 vs 97 vs 120(옵션 1 단독)
  - Gemini: 옵션 1+3 결합. "Starter는 엄격, Downstream은 쾌적"
  - Codex: 옵션 1+3 결합 + helper script 분리. "의미 drift 아닌 projection
    drift — 허용 가능"
- Codex 추가 정밀: rewrite된 파일 본문에 주석 X (upgrade 로그에만), helper
  script 분리 (`docs_ops.py` 과부하 회피), 함수 명시 분해
- Gemini 추가 사각지대 정합: starter 엄격·downstream 쾌적 원칙은 본 wave
  구현과 자연 정합
- Step 0 감사 실측: cascade decisions 5개 / 잠복 사례 2건 (decisions
  target만; archived target 1건은 본 wave 범위 외)
- 본 wave 옵션 2(신규 rel type) 만장일치 탈락 — rel taxonomy 오염·one-way

**Acceptance Criteria**:

- [x] Goal: cascade된 decisions가 비-cascade 동료를 frontmatter로 가리킬
  때 다운스트림 dead link 발생 차단 (S11)
  검증:
    tests: pytest -m docs_ops
    실측: starter `cascade_docs.py check` 위반 0건, verify-relates 통과
- [x] 실천 옵션 결정 (advisor·3엔진 비교 후) — 1+3 결합 (S11)
- [x] starter `decisions/hn_*` 전수 frontmatter 감사 — 2건 잠복 사례
  발견 후 cleanup (S11)
- [x] 결정한 옵션 구현 — `cascade_docs.py` 신설 + `docs_ops.py
  verify-relates` 확장 + `harness-upgrade` Step 3 호출 (S11)
- [x] 회귀 테스트 추가 — `test_cascade_boundary.py` 6 케이스 (S11)
- [x] MIGRATIONS 갱신 (commit 흐름에서 처리)

본 wave에서 옵션 1+3 결합 구현 완료. 본 박제 문서는 결정 박제로 마감.
