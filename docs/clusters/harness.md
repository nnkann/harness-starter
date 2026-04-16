# harness 클러스터

## 문서 목록

- [승격/강등 이력](../harness/promotion-log.md) — tags: promotion, rule-change
- [하네스 스타터 개선 계획](../decisions/harness_improvement_260408.md) — tags: improvement, profile, sync
- [업그레이드 계획](../decisions/harness_upgrade_260410.md) — tags: memory, hook, skill, upgrade
- [업그레이드 전파 전략](../guides/harness_upgrade_propagation_260410.md) — tags: upgrade, propagation, versioning
- [적합성 분석](../decisions/harness_gap_analysis_260414.md) — tags: gap-analysis, verification

## 관계 맵

- harness_improvement_260408 --references--> promotion-log
- harness_upgrade_260410 --extends--> promotion-log
- harness_upgrade_propagation_260410 --implements--> harness_upgrade_260410
- harness_gap_analysis_260414 --references--> harness_upgrade_260410
