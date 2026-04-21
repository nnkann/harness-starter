# harness 클러스터

## 문서 목록

### 전역 마스터 (프로젝트 전역)
- [승격/강등 이력](../harness/promotion-log.md) — tags: promotion, rule-change
- [다운스트림 마이그레이션 가이드](../harness/MIGRATIONS.md) — tags: migration, upgrade, downstream
- [harness-starter CPS](../guides/project_kickoff.md) — tags: cps, meta, starter

### decisions/
- [하네스 스타터 개선 계획](../decisions/hn_improvement.md) — tags: improvement, profile, sync
- [업그레이드 계획](../decisions/hn_upgrade.md) — tags: memory, hook, skill, upgrade
- [적합성 분석](../decisions/hn_gap_analysis.md) — tags: gap-analysis, verification
- [Remote 기반 하네스 업그레이드 전략](../decisions/hn_remote_upgrade_strategy.md) — tags: upgrade, git-remote, merge
- [프론트매터 그래프 스펙 설계](../decisions/hn_frontmatter_graph_spec.md) — tags: frontmatter, graph, docs-structure
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md) — tags: staging, review, governance
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md) — tags: rules, governance, refactor
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md) — tags: skill, agent, routing, orchestration, audit
- [코드 SSOT 서더링 감사](../decisions/hn_code_ssot_audit.md) — tags: ssot, audit, code, refactor
- [memory 재설계 — tmp 폐기 + 동적 snapshot + 트리거 3개](../decisions/hn_memory.md) — tags: memory, snapshot, ssot, simplification, trigger
- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md) — tags: naming, docs, upstream-rule
- [review staging 재조정 — 5줄 룰 이진 판정](../decisions/hn_review_staging_rebalance.md) — tags: staging, review, rule, tokens
- [review 에이전트 tool call 예산 재설계](../decisions/hn_review_tool_budget.md) — tags: review, agent, tool-budget, tokens

### guides/
- [업그레이드 전파 전략](../guides/hn_upgrade_propagation.md) — tags: upgrade, propagation, versioning
- [eval 보안 강화 패치 이식 가이드](../guides/hn_eval_security_patch_port.md) — tags: eval, security, secret-scan, port
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md) — tags: docs, search, doc-finder
- [외부 자료 조사 패턴 — Context7·공식 문서](../guides/hn_external_research_patterns.md) — tags: research, context7, external-docs, mcp

### harness/
- [하네스 구멍 정리 + 리뷰 구조 재확정](../harness/hn_search_and_completion_gaps.md) — tags: search, ide-context, incident-doc, completion-gate, review-agent
- [커밋 속도 최적화](../harness/hn_commit_perf_optimization.md) — tags: commit, performance, review-agent
- [LLM 실수 방지 가드레일](../harness/hn_llm_mistake_guardrails.md) — tags: guardrails, self-correction, reliability, advisor-flow
- [하네스 범용성 오염 방지](../harness/hn_generic_contamination_protection.md) — tags: harness-starter, contamination, generic
- [commit·review 단계화](../harness/hn_commit_review_staging.md) — tags: commit, review, performance, staging, cost
- [범용성 오염 방지 후속 (단순화로 흡수)](../harness/hn_contamination_followup.md) — tags: contamination, review, write-doc
- [commit Step 2 후속 — symptom-keywords + completed 차단](../harness/hn_commit_step2_partial_completion.md) — tags: commit, write-doc, completion-gate
- [review staging 후속 — S1 오탐 보정 + S6 완화](../harness/hn_staging_followup.md) — tags: staging, review, performance, measurement
- [LLM 가드레일 후속 — 허위 후속 감지](../harness/hn_guardrails_followup.md) — tags: guardrails, advisor, review, commit
- [staging 잔여 — S8·5커밋 측정·폭증 게이트](../harness/hn_staging_remaining.md) — tags: staging, review, measurement
- [하네스 단순화 P0 — 마찰 회수 6단계](../harness/hn_simplification.md) — tags: simplification, friction, rollback, hook-strength
- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md) — tags: audit, information-flow, efficiency, agent-orchestration
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md) — tags: implementation, skill, routing, orchestration
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md) — tags: skill, agent, commit, review, handoff, refactor
- [eval 4관점 advisor 이관 + specialist 품질 보강](../harness/hn_eval_advisor_migration.md) — tags: eval, advisor, specialist, threat-analyst, quality, scoring
- [advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시](../harness/hn_advisor_decision_framework.md) — tags: advisor, decision-framework, orchestration, judgment
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md) — tags: audit, information-flow, measurement, phase3
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md) — tags: review, harness-upgrade, whitelist, dead-link, dynamic-resolution
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md) — tags: docs, ssot, simplification, index-removal

### incidents/
- [review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고](../incidents/hn_review_agent_wrong_diff.md) — tags: review-agent, agent-context, false-warning
- [starter push 누락 + lint stdout 오염](../incidents/hn_starter_push_skipped.md) — tags: push, starter, downstream, propagation
- [PreToolUse Bash -n 오탐 차단](../incidents/hn_bash_n_flag_overblock.md) — tags: hook, pre-tool-use, false-positive, bash
- [광역 매처 오탐 + README 덮어쓰기 위험](../incidents/hn_matcher_false_block.md) — tags: hook, matcher, false-positive, harness-upgrade, readme, downstream
- [review v0.8.0 starter 격리 벤치마크](../incidents/hn_review_v080_benchmark.md) — tags: review, benchmark, staging, tool-usage
- [archived/promotion-log에 다운스트림 제품명 유출](../incidents/hn_downstream_name_leak.md) — tags: contamination, review, archive, downstream-name
- [review 에이전트 maxTurns 소진 시 verdict 누락](../incidents/hn_review_maxturns_verdict_miss.md) — tags: review, maxturns, bulk-commit, agent-spec

### archived/
- [(abandoned) advisor 통합](../archived/advisor_integration_260419.md) — staging 신호와 70% 겹쳐 자체 규칙 위반
- [(abandoned) hook 흐름 감사](../archived/hook_flow_efficiency_260418.md) — 이번 세션 중 의도 80% 자연 달성, 남은 자동화는 단순화와 충돌
- [(archived) 승격/강등 이력 2026 Q2 초반](../archived/promotion-log-2026q2-early.md) — promotion-log B+D 압축 전 원본, 2026-04-08~20 구간 152행 보존

## 관계 맵

- hn_improvement --references--> promotion-log
- hn_upgrade --extends--> promotion-log
- hn_upgrade_propagation --implements--> hn_upgrade
- hn_gap_analysis --references--> hn_upgrade
- hn_remote_upgrade_strategy --references--> promotion-log
- hn_commit_perf_optimization --references--> hn_commit_review_staging
- hn_llm_mistake_guardrails --references--> hn_commit_review_staging
- hn_staging_governance --references--> promotion-log
- hn_rules_metadata --references--> promotion-log
- hn_doc_search_protocol --extends--> (rules/docs.md)
- hn_info_flow_leak_audit --references--> promotion-log
- hn_implementation_router --references--> hn_info_flow_leak_audit
- hn_skill_agent_role_audit --extends--> hn_implementation_router
- hn_commit_review_handoff --implements--> hn_skill_agent_role_audit
- hn_commit_review_handoff --extends--> hn_implementation_router
- hn_eval_advisor_migration --implements--> hn_skill_agent_role_audit
- hn_eval_advisor_migration --extends--> hn_implementation_router
- hn_advisor_decision_framework --extends--> hn_eval_advisor_migration
- hn_advisor_decision_framework --extends--> hn_implementation_router
- hn_code_ssot_audit --extends--> hn_skill_agent_role_audit
- hn_code_ssot_audit --references--> hn_commit_review_handoff
- hn_downstream_name_leak --references--> hn_matcher_false_block
- hn_downstream_name_leak --extends--> hn_generic_contamination_protection
- hn_info_flow_leak_phase3 --caused-by--> hn_info_flow_leak_audit
- hn_review_whitelist_autodetect --references--> promotion-log
- hn_index_md_removal --extends--> hn_simplification
- hn_doc_naming --references--> hn_memory
- hn_doc_naming --extends--> hn_index_md_removal
