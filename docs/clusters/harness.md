# harness 클러스터

## 문서 목록

- [승격/강등 이력](../harness/promotion-log.md) — tags: promotion, rule-change
- [하네스 스타터 개선 계획](../decisions/harness_improvement_260408.md) — tags: improvement, profile, sync
- [업그레이드 계획](../decisions/harness_upgrade_260410.md) — tags: memory, hook, skill, upgrade
- [업그레이드 전파 전략](../guides/harness_upgrade_propagation_260410.md) — tags: upgrade, propagation, versioning
- [적합성 분석](../decisions/harness_gap_analysis_260414.md) — tags: gap-analysis, verification
- [프론트매터 그래프 스펙 설계](../decisions/frontmatter_graph_spec_260416.md) — tags: frontmatter, graph, docs-structure
- [Remote 기반 하네스 업그레이드 전략](../decisions/remote_upgrade_strategy_260416.md) — tags: upgrade, git-remote, merge
- [eval 보안 강화 패치 이식 가이드](../guides/eval-security-patch-port_260418.md) — tags: eval, security, secret-scan, port
- [review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고](../incidents/review-agent-wrong-diff_260419.md) — tags: review-agent, agent-context, false-warning
- [하네스 구멍 정리 + 리뷰 구조 재확정](../harness/search_and_completion_gaps_260418.md) — tags: search, ide-context, incident-doc, completion-gate, review-agent
- [커밋 속도 최적화](../harness/commit_perf_optimization_260418.md) — tags: commit, performance, review-agent
- [LLM 실수 방지 가드레일](../harness/llm_mistake_guardrails_260418.md) — tags: guardrails, self-correction, reliability, advisor-flow
- [하네스 범용성 오염 방지](../harness/generic_contamination_protection_260418.md) — tags: harness-starter, contamination, generic
- [commit·review 단계화](../harness/commit_review_staging_260419.md) — tags: commit, review, performance, staging, cost
- [범용성 오염 방지 후속 (단순화로 흡수)](../harness/contamination_followup_260419.md) — tags: contamination, review, write-doc
- [commit Step 2 후속 — symptom-keywords + completed 차단](../harness/commit_step2_partial_completion_260419.md) — tags: commit, write-doc, completion-gate
- [review staging 후속 — S1 오탐 보정 + S6 완화](../harness/staging_followup_260419.md) — tags: staging, review, performance, measurement
- [LLM 가드레일 후속 — 허위 후속 감지](../harness/guardrails_followup_260419.md) — tags: guardrails, advisor, review, commit
- [PreToolUse Bash -n 오탐 차단](../incidents/bash_n_flag_overblock_260419.md) — tags: hook, pre-tool-use, false-positive, bash
- [하네스 단순화 P0 — 마찰 회수 6단계](../harness/harness_simplification_260419.md) — tags: simplification, friction, rollback, hook-strength
- [(abandoned) advisor 통합](../archived/advisor_integration_260419.md) — staging 신호와 70% 겹쳐 자체 규칙 위반
- [(abandoned) hook 흐름 감사](../archived/hook_flow_efficiency_260418.md) — 이번 세션 중 의도 80% 자연 달성, 남은 자동화는 단순화와 충돌
- [staging 잔여 — S8·5커밋 측정·폭증 게이트](../harness/staging_remaining_260419.md) — tags: staging, review, measurement

## 관계 맵

- harness_improvement_260408 --references--> promotion-log
- harness_upgrade_260410 --extends--> promotion-log
- harness_upgrade_propagation_260410 --implements--> harness_upgrade_260410
- harness_gap_analysis_260414 --references--> harness_upgrade_260410
- remote_upgrade_strategy_260416 --references--> promotion-log
- commit_perf_optimization_260418 --references--> commit_review_staging_260419
- llm_mistake_guardrails_260418 --references--> commit_review_staging_260419
