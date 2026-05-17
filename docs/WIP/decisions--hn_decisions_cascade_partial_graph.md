---
title: starter decisions 부분 cascade로 인한 dead link 그래프 끊김
domain: harness
problem: [P11]
s: [S11]
tags: [cascade, decisions, dead-link, downstream, verify-relates]
status: pending
created: 2026-05-17
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

**Acceptance Criteria** (별 wave 진입 시):

- [ ] Goal: cascade된 decisions가 비-cascade 동료를 frontmatter로 가리킬
  때 다운스트림 dead link 발생 차단 (S11)
  검증:
    tests: pytest -m docs_ops
    실측: 다운스트림 verify-relates 출력에 본 패턴 경고 0건
- [ ] 실천 옵션 결정 (advisor·3엔진 비교 후) (S11)
- [ ] starter `decisions/hn_*` 전수 frontmatter 감사 — 비-cascade 참조
  잠복 사례 발견 (Step 0) (S11)
- [ ] 결정한 옵션 구현 (lint 또는 후처리) (S11)
- [ ] 회귀 테스트 추가 (S11)
- [ ] MIGRATIONS 갱신

본 박제는 별 wave 진입 트리거. 동일 패턴 1~2회 추가 발견 시 진입.
