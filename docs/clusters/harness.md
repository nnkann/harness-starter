# harness 클러스터

## 문서 목록

- [승격/강등 이력](../harness/promotion-log.md) — tags: promotion, rule-change
- [하네스 스타터 개선 계획](../decisions/harness_improvement_260408.md) — tags: improvement, profile, sync
- [업그레이드 계획](../decisions/harness_upgrade_260410.md) — tags: memory, hook, skill, upgrade
- [업그레이드 전파 전략](../guides/harness_upgrade_propagation_260410.md) — tags: upgrade, propagation, versioning
- [적합성 분석](../decisions/harness_gap_analysis_260414.md) — tags: gap-analysis, verification
- [프론트매터 그래프 스펙 설계](../decisions/frontmatter_graph_spec_260416.md) — tags: frontmatter, graph, docs-structure
- [Remote 기반 하네스 업그레이드 전략](../decisions/remote_upgrade_strategy_260416.md) — tags: upgrade, git-remote, merge

## 관계 맵

- harness_improvement_260408 --references--> promotion-log
- harness_upgrade_260410 --extends--> promotion-log
- harness_upgrade_propagation_260410 --implements--> harness_upgrade_260410
- harness_gap_analysis_260414 --references--> harness_upgrade_260410
- remote_upgrade_strategy_260416 --references--> promotion-log
