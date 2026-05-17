---
title: Neutral SSOT Runtime Output Generation
domain: harness
problem: [P5, P7, P11]
s: [S5, S7]
tags: [codex, ssot, runtime, bridge, generation]
status: in-progress
created: 2026-05-17
relates-to:
  - path: harness/hn_codex_port.md
    rel: extends
  - path: decisions/hn_rule_skill_ssot.md
    rel: references
  - path: decisions/hn_ssot_citation_mechanism.md
    rel: references
  - path: decisions/hn_code_ssot_audit.md
    rel: references
---

# Neutral SSOT Runtime Output Generation

## Context

현재 하네스는 Claude Code를 원점으로 자라서 `.claude/`가 사실상 SSOT 역할을 한다. Codex 포팅은 `AGENTS.md`, `.agents/`, `.codex/`로 분리되었지만, 원천 지식과 런타임 산출물이 아직 같은 층위에 섞여 있다.

이 구조는 두 런타임을 함께 유지할 때 세 가지 비용을 만든다.

- Codex용 문서에 Claude 도구명, hook 전제, 스킬 경로가 남을 수 있다.
- `.claude/skills/**`와 `.agents/skills/**`가 복제되면서 수정 누락과 의미 drift가 생긴다.
- 런타임별 지원 범위가 다른데도 생성 규칙이 없어 수동 포팅마다 판단이 반복된다.

## Review Response

Claude 검토 주석의 핵심 우려는 타당하다. 이 문서는 처음부터 generator + adapter + manifest를 전제로 두면 `.claude/rules/docs.md`의 SSOT 인용 원칙과 충돌할 수 있다. 생성물 헤더와 hash 검사는 drift를 탐지할 뿐, 복제 자체를 줄인다는 보장은 아니다.

따라서 이 WIP의 결론은 "즉시 생성기 도입"이 아니라 "Phase 0 audit으로 실제 drift를 먼저 측정한 뒤, generator와 더 가벼운 대안을 비교한다"로 조정한다.

## Decision Candidate

후보 A는 중립 SSOT를 별도 계층으로 두고, Claude와 Codex 파일을 런타임 adapter가 생성하거나 갱신하는 방식이다.

```text
.harness/
  ssot/
    instructions.md
    skills/*.md
    agents/*.md
    hooks.yml
    runtime-policy.yml
  runtimes/
    claude.yml
    codex.yml
  generators/
    render.py
  generated-manifest.json
```

중립 SSOT는 "무엇을 해야 하는가"만 보관한다. Claude와 Codex adapter는 "어떤 파일 형식과 도구 이름으로 표현할 것인가"를 담당한다.

후보 B는 generator 없이 단일 SSOT + runtime marker 또는 runtime overlay만 두는 방식이다. 예를 들어 공통 본문은 하나만 두고, 런타임별 차이는 `runtime: codex|claude` marker나 overlay 파일에서만 표현한다. 이 방식은 구조가 작고 SSOT 인용 원칙과 더 잘 맞을 가능성이 있다.

## Runtime Outputs

Claude adapter 출력 후보:

- `CLAUDE.md`
- `.claude/skills/**`
- `.claude/agents/**`
- `.claude/settings.json`

Codex adapter 출력 후보:

- `AGENTS.md`
- `.agents/skills/**`
- `.codex/agents/*.toml`
- `.codex/hooks.json`

생성 파일에는 공통 헤더를 둔다.

```text
Generated from: .harness/ssot/<source>
Runtime: codex|claude
Manual edits: runtime overlay only
```

## Flow

1. 중립 SSOT 또는 런타임 overlay를 수정한다.
2. generator를 dry-run으로 실행한다.
3. Claude 출력 diff와 Codex 출력 diff를 분리해서 보여준다.
4. 사용자가 선택한 런타임 산출물만 적용한다.
5. manifest hash와 런타임별 금지어 검사를 통과해야 완료한다.

## Validation Ideas

- 중립 SSOT schema 검사.
- `generated-manifest.json`의 source hash와 산출물 hash 검사.
- Codex 산출물에 Claude 전용 도구명과 hook 전제가 남지 않는지 검사.
- Claude 산출물에 Codex plugin, Codex app directive, `.codex/` 전제가 섞이지 않는지 검사.
- `.agents/skills/**`와 `.claude/skills/**`의 수동 drift를 manifest로 탐지.

## Migration Sketch

Phase 0은 읽기 전용 audit이다. 기존 `.claude/`, `.agents/`, `.codex/`, `AGENTS.md`, `CLAUDE.md`를 스캔해서 실제 drift와 중립 SSOT 후보만 측정한다. 이 단계에서는 generator를 만들지 않고, manifest 초안과 drift 목록만 만든다.

Phase 1은 Phase 0 결과가 충분할 때만 진행한다. 후보 A를 고르면 Codex 산출물만 생성한다. 후보 B를 고르면 runtime marker 또는 overlay만 실험한다. Claude 전용 파일은 계속 보존한다.

Phase 2는 사용자 승인 후 Claude 산출물도 생성 대상으로 전환한다. 이때 기존 Claude 동작 보존이 최우선이다.

Phase 3은 pre-check 또는 eval에 manifest drift 검사를 연결한다.

## Open Questions

- 중립 SSOT 위치를 `.harness/`로 둘지, 기존 `docs/`와 `.claude/rules/`를 원천으로 유지할지 결정해야 한다.
- 어떤 파일을 생성물로 보고 어떤 파일을 수동 overlay로 둘지 경계가 필요하다.
- `.claude/rules/*.md`를 즉시 중립화할지, Claude 원천으로 임시 유지할지 선택해야 한다.
- Codex hooks는 현재 비활성 상태가 더 안전한데, adapter가 hook 파일을 생성할 조건을 별도로 둘지 정해야 한다.
- 실제 drift가 몇 건인지, 그리고 그 drift가 generator 도입 비용을 정당화하는지 먼저 측정해야 한다.

**Acceptance Criteria**:

- [ ] Goal: 중립 SSOT에서 Claude와 Codex 런타임 산출물을 관리하는 방식을 검토 가능하게 만든다.
  검증:
    tests: 문서 검토.
    실측: 사용자가 Phase 0 audit, generator, lightweight overlay 중 다음 단계를 판단할 수 있다.
- [ ] S5: 런타임별 instruction과 skill 복제를 줄여 Codex 컨텍스트 팽창을 줄이는 방향을 제시한다.
  검증:
    tests: 문서 검토.
    실측: Codex 산출물이 중립 SSOT, runtime marker, overlay 중 어떤 최소 입력만 읽으면 되는지 비교한다.
- [ ] S7: 구성 요소 관계를 `source -> adapter -> runtime output -> validation` 흐름으로 드러낸다.
  검증:
    tests: 문서 검토.
    실측: Claude 전용 파일과 Codex 전용 파일의 책임 경계가 표로 재구성 가능하다.
- [ ] P11: 한 런타임에서 발견한 문제를 다른 런타임 후보 위치까지 탐색하는 검증 아이디어를 포함한다.
  검증:
    tests: 문서 검토.
    실측: 금지어 검사와 manifest drift 검사가 Claude, Codex 양쪽을 모두 대상으로 한다.
