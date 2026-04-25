---
title: harness 클러스터
domain: harness
tags: [cluster, index]
status: completed
created: 2026-04-16
updated: 2026-04-25
---

# harness 클러스터

도메인 harness(hn) 소속 문서 목록. docs-ops.sh cluster-update 자동 생성.

## 문서

- [코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리](../decisions/hn_code_ssot_audit.md)
- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [프론트매터 그래프 스펙 설계](../decisions/hn_frontmatter_graph_spec.md)
- [하네스 엔지니어링 적합성 분석](../decisions/hn_gap_analysis.md)
- [하네스 스타터 개선 계획](../decisions/hn_improvement.md)
- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [pipeline-design 규칙 업스트림 이식 계획](../decisions/hn_pipeline_design_rule.md)
- [Remote 기반 하네스 업그레이드 전략](../decisions/hn_remote_upgrade_strategy.md)
- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분](../decisions/hn_review_tool_budget.md)
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md)
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md)
- [eval --deep 보안 강화 패치 타 프로젝트 이식 가이드](../guides/hn_eval_security_patch_port.md)
- [외부 자료 조사 패턴 — Context7·공식 문서](../guides/hn_external_research_patterns.md)
- [하네스 스타터 업그레이드 전파 전략](../guides/hn_upgrade_propagation.md)
- [advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시](../harness/hn_advisor_decision_framework.md)
- [커밋 속도 최적화 — 단계 조건부 실행 + pre-check→리뷰 데이터 전달 + 모델 스위치](../harness/hn_commit_perf_optimization.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [commit Step 2 후속 — write-doc symptom-keywords 재질의 + completed 미결 차단 자동화](../harness/hn_commit_step2_partial_completion.md)
- [범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의](../harness/hn_contamination_followup.md)
- [eval 4관점 advisor 이관 + specialist 품질 보강 (threat-analyst 신설·산출물 점수·업계 탑 인물)](../harness/hn_eval_advisor_migration.md)
- [하네스 범용성 오염 방지 — 다운스트림 고유명사 유입 차단](../harness/hn_generic_contamination_protection.md)
- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md)
- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md)
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md)
- [LLM 실수 방지 가드레일 — 내부 자료 우선 + 추측 차단 + advisor 연동](../harness/hn_llm_mistake_guardrails.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)
- [하네스 단순화 — 추가 누적으로 인한 마찰 회수](../harness/hn_simplification.md)
- [review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트](../harness/hn_staging_remaining.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)
- [PreToolUse Bash -n 오탐으로 정당한 명령 차단](../incidents/hn_bash_n_flag_overblock.md)
- [docs-ops.sh cluster-update 성능 저하 — extract_abbrs() 반복 호출](../incidents/hn_docs_ops_cluster_update_perf.md)
- [archived/promotion-log에 다운스트림 제품명 유출 — review 발견](../incidents/hn_downstream_name_leak.md)
- [v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭](../incidents/hn_lint_enoent_pattern_gaps.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)
- [pipeline-design 규칙 업스트림 이식 원천 사례](../incidents/hn_pipeline_design_rule_origin.md)
- [review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고](../incidents/hn_review_agent_wrong_diff.md)
- [review 에이전트 maxTurns 소진 시 verdict 누락](../incidents/hn_review_maxturns_verdict_miss.md)
- [review v0.8.0 패턴 매핑 재설계 — starter 격리 벤치마크](../incidents/hn_review_v080_benchmark.md)
- [starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄](../incidents/hn_starter_push_skipped.md)
- [린터 도구 실종 — T13이 우연히 가시화한 환경 이슈](../incidents/hn_test_isolation_git_log_leak.md)
