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

## 관계 맵

- harness_improvement_260408 --references--> promotion-log
- harness_upgrade_260410 --extends--> promotion-log
- harness_upgrade_propagation_260410 --implements--> harness_upgrade_260410
- harness_gap_analysis_260414 --references--> harness_upgrade_260410
- remote_upgrade_strategy_260416 --references--> promotion-log
- commit_perf_optimization_260418 --references--> commit_review_staging_260419
- llm_mistake_guardrails_260418 --references--> commit_review_staging_260419
