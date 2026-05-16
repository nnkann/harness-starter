---
title: harness 클러스터
domain: harness
tags: [cluster, index]
status: completed
created: 2026-04-16
updated: 2026-05-16
---

# harness 클러스터

도메인 harness(hn) 소속 문서 + tag 간선. docs-ops.py cluster-update 자동 생성.

## 문서

- [harness-adopt 레거시 문서 정비 지원 — doc-health 진단 플로우](../decisions/hn_adopt_legacy_doc_health.md)
- [adopt-without-init 다운스트림 능동 유도 — harness-init 자동 트리거](../decisions/hn_adopt_without_init_guard.md)
- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계](../decisions/hn_bug_interrupt_triage.md)
- [cluster 재생성 게이팅 — 본체 변경 시 전수 갱신 패턴 분리](../decisions/hn_cluster_update_gating.md)
- [코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리](../decisions/hn_code_ssot_audit.md)
- [commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)](../decisions/hn_commit_auto_verify.md)
- [commit 흐름 자동화 — wip-sync + git commit wrapper](../decisions/hn_commit_finalize_wrapper.md)
- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [CPS Problem 인용 빈도 검토 — P1·P3·P4·P6 정체 의심 판정](../decisions/hn_cps_problem_inflation_review.md)
- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [다운스트림 증폭 측정 — Phase 4-A baseline 수집·가설 검증](../decisions/hn_downstream_amplification.md)
- [eval CPS 무결성 감시 — 박제 감지·Problem 인플레이션](../decisions/hn_eval_cps_integrity.md)
- [eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단](../decisions/hn_eval_harness_cli_lsp_drift.md)
- [eval --harness medium 결과 정비 (5-4 Feedback Reports 인식 + 5-5 self-verify 모호성)](../decisions/hn_eval_harness_medium_fixes.md)
- [프론트매터 그래프 스펙 설계](../decisions/hn_frontmatter_graph_spec.md)
- [하네스 엔지니어링 적합성 분석](../decisions/hn_gap_analysis.md)
- [Gemini CLI subagent 위임 파이프라인 설계](../decisions/hn_gemini_delegation_pipeline.md)
- [Glob 라우팅 태그 통과 — 사용자·에이전트 검색 비대칭 해소](../decisions/hn_glob_routing_tag.md)
- [하네스 73% 삭감 설계 — 통제에서 가속으로](../decisions/hn_harness_73pct_cut.md)
- [HARNESS_UPGRADE 환경변수 의미 일관화](../decisions/hn_harness_upgrade_env_semantics.md)
- [하네스 스타터 개선 계획](../decisions/hn_improvement.md)
- [implementation init check 게이트 정밀화 — 환경 양식 drift 비용 제거](../decisions/hn_init_gate_redesign.md)
- [Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT](../decisions/hn_karpathy_principles.md)
- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI](../decisions/hn_orchestrator_mechanism.md)
- [P8 starter 자기 적용 + commit 흐름 강제 트리거 보강](../decisions/hn_p8_starter_self_application.md)
- [pipeline-design 규칙 업스트림 이식 계획](../decisions/hn_pipeline_design_rule.md)
- [약속 박제 보호 — completed 봉인 + 미루기 차단 룰](../decisions/hn_promise_protection.md)
- [Remote 기반 하네스 업그레이드 전략](../decisions/hn_remote_upgrade_strategy.md)
- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분](../decisions/hn_review_tool_budget.md)
- [review 에이전트 verdict 헤더 형식 준수율 — 100% 누락 패턴](../decisions/hn_review_verdict_compliance.md)
- [룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)](../decisions/hn_rule_skill_ssot.md)
- [룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md](../decisions/hn_rule_skill_ssot_apply.md)
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md)
- [completed 봉인 — 본문 마크다운 링크 경로 교체 면제](../decisions/hn_sealed_link_exempt.md)
- [자가 발화 의존 규칙의 일반 실패 — P8 등록 + debug-guard.sh 확장](../decisions/hn_self_invocation_failure.md)
- [본 세션 시험 결과 종합 — review verdict + wip-sync false positive 누적 데이터](../decisions/hn_session_test_results.md)
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md)
- [starter 모호성 흡수 + CPS Problem 임계 상향 + S7 미정의 명시](../decisions/hn_starter_ambiguity_absorption.md)
- [starter 전용 스킬 격리 — harness-dev 스킬 신설](../decisions/hn_starter_skill_isolation.md)
- [starter_skills 필터링 미구현 — harness-upgrade 폴더 복사 제외 + harness-dev 등록](../decisions/hn_starter_skills_filter.md)
- [stop-guard.sh → stop-guard.py 전환 (자기증식 차단)](../decisions/hn_stop_guard_py_migration.md)
- [테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거](../decisions/hn_test_diet.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [harness-upgrade silent fail 차단 보강 (FR-001/002/003 + FR-006)](../decisions/hn_upgrade_silent_fail_guards.md)
- [verify-relates pre-check 통합 — 커밋 시 relates-to 전수 검사](../decisions/hn_verify_relates_precheck.md)
- [Wiki 그래프 자산 생성 wave — frontmatter·tag·relates-to 일제 정비](../decisions/hn_wiki_graph_assets.md)
- [WIP cluster scan 가시성 — in-progress 도달 경로 추가](../decisions/hn_wip_cluster_visibility.md)
- [docs_ops.py wip-sync 부분 매칭 버그 — 매칭 정밀화](../decisions/hn_wip_sync_match_precision.md)
- [wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단](../decisions/hn_wip_sync_staging_gaps.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md)
- [eval --deep 보안 강화 패치 타 프로젝트 이식 가이드](../guides/hn_eval_security_patch_port.md)
- [외부 자료 조사 패턴 — Context7·공식 문서](../guides/hn_external_research_patterns.md)
- [하네스 유기체화 설계 — HARNESS_MAP.md 신경망 허브 구현 방안](../guides/hn_harness_organism_design.md)
- [하네스 스타터 업그레이드 전파 전략](../guides/hn_upgrade_propagation.md)
- [harness-starter CPS — C 판단 프롬프트](../guides/project_kickoff.md)
- [advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시](../harness/hn_advisor_decision_framework.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [commit Step 2 후속 — write-doc symptom-keywords 재질의 + completed 미결 차단 자동화](../harness/hn_commit_step2_partial_completion.md)
- [범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의](../harness/hn_contamination_followup.md)
- [debug-specialist 에이전트 신설 — 막힐 때 자동 위임처 확보](../harness/hn_debug_specialist.md)
- [침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계](../harness/hn_defense_visibility.md)
- [docs_ops.py move 시 relates-to 역참조 자동 갱신](../harness/hn_docs_ops_relates_to_rewrite.md)
- [eval 4관점 advisor 이관 + specialist 품질 보강 (threat-analyst 신설·산출물 점수·업계 탑 인물)](../harness/hn_eval_advisor_migration.md)
- [eval 기본 모드 보고 구조 개선](../harness/hn_eval_basic_mode_report.md)
- [다운스트림 피드백 채널 포맷 규격화 + eval --harness 테스트](../harness/hn_feedback_channel_format.md)
- [하네스 범용성 오염 방지 — 다운스트림 고유명사 유입 차단](../harness/hn_generic_contamination_protection.md)
- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)
- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)
- [HARNESS.json skills 목록 정리 — 1회성 스킬 삭제 + 활성 목록 정비](../harness/hn_harness_json_cleanup.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md)
- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md)
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md)
- [LLM 실수 방지 가드레일 — 내부 자료 우선 + 추측 차단 + advisor 연동](../harness/hn_llm_mistake_guardrails.md)
- [하네스 자잘한 버그 묶음 — MIGRATIONS 누락·starter_skills 오염·permissions.allow 미전파·h-setup.sh 오분류·신규설치 필터 누락·harness-sync 경계 불명확·docs/harness 전달 오염](../harness/hn_migrations_version_gap.md)
- [MVR 매핑 + HARNESS_MAP 에이전트 관점 개선](../harness/hn_mvr_map_agent_view.md)
- [Phase 구조 보강 — WIP AC 섹션 + Phase 6원칙 + escalate 에이전트 트리거 + WIP 실행 순서](../harness/hn_phase_agent_improvements.md)
- [PRD 레이어 보강 — User Needs 섹션·milestones 샘플·harness-init 권고](../harness/hn_prd_layers.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)
- [session-start.sh → session-start.py 전환 — spawn 비용 절감](../harness/hn_session_start_py.md)
- [하네스 단순화 — 추가 누적으로 인한 마찰 회수](../harness/hn_simplification.md)
- [eval에 Solution 충족 인용 분포 집계 추가](../harness/hn_solution_ref_aggregation.md)
- [split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정](../harness/hn_split_commit_review_stage.md)
- [split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화](../harness/hn_split_diff_delivery.md)
- [review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트](../harness/hn_staging_remaining.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)
- [test-pre-commit 스위트 성능 — 잔여 구조 재설계](../harness/hn_test_suite_perf.md)
- [harness-starter 이상 징후 묶음 (다운스트림 발견)](../harness/hn_upstream_anomalies.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)
- [WIP 완료 자동화 구조적 결함 — Step 7.5 미동작 + SSOT 드리프트 + 이동 미연결](../harness/hn_wip_completion_gap.md)
- [다운스트림 마이그레이션 가이드 — 아카이브](../harness/MIGRATIONS-archive.md)
- [다운스트림 마이그레이션 가이드](../harness/MIGRATIONS.md)
- [PreToolUse Bash -n 오탐으로 정당한 명령 차단](../incidents/hn_bash_n_flag_overblock.md)
- [커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)](../incidents/hn_commit_process_gaps.md)
- [docs-ops.sh cluster-update 성능 저하 — extract_abbrs() 반복 호출](../incidents/hn_docs_ops_cluster_update_perf.md)
- [archived/promotion-log에 다운스트림 제품명 유출 — review 발견](../incidents/hn_downstream_name_leak.md)
- [FR 필드 정규식 — bold 마커 내부 괄호 보강어 미인식 회귀](../incidents/hn_fr_field_regex_bold_inner_paren.md)
- [v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭](../incidents/hn_lint_enoent_pattern_gaps.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)
- [pipeline-design 규칙 업스트림 이식 원천 사례](../incidents/hn_pipeline_design_rule_origin.md)
- [review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고](../incidents/hn_review_agent_wrong_diff.md)
- [review 에이전트 maxTurns 소진 시 verdict 누락](../incidents/hn_review_maxturns_verdict_miss.md)
- [review v0.8.0 패턴 매핑 재설계 — starter 격리 벤치마크](../incidents/hn_review_v080_benchmark.md)
- [pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단](../incidents/hn_sealed_migrations_exempt_gap.md)
- [pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단](../incidents/hn_sealed_reopen_false_block.md)
- [pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단](../incidents/hn_secret_line_exempt_gap.md)
- [세션 거짓 완료·자기 위반 패턴 누적 (다음 세션 인계)](../incidents/hn_session_false_completion.md)
- [starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄](../incidents/hn_starter_push_skipped.md)
- [린터 도구 실종 — T13이 우연히 가시화한 환경 이슈](../incidents/hn_test_isolation_git_log_leak.md)
- [wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락](../incidents/hn_wip_sync_incidents_gap.md)

## tag 분포 (간선)

review (18건) | commit (13건) | downstream (13건) | cps (11건) | skill (11건) | eval (10건) | ssot (9건) | staging (9건) | hook (8건) | rules (8건) | upgrade (8건) | audit (7건) | pre-check (7건) | ac (6건) | harness-upgrade (6건) | migration (6건) | docs-ops (5건) | false-positive (5건) | split (5건) | wip-sync (5건) | agent (4건) | contamination (4건) | dead-link (4건) | frontmatter (4건) | harness-dev (4건) | implementation (4건) | incident (4건) | refactor (4건) | starter (4건) | advisor (3건) | cascade (3건) | docs (3건) | governance (3건) | harness-adopt (3건) | harness-init (3건) | harness-map (3건) | measurement (3건) | memory (3건) | orchestration (3건) | performance (3건) | pipeline (3건) | python (3건) | relates-to (3건) | sealed (3건) | secret-scan (3건) | self-verify (3건) | simplification (3건) | trigger (3건) | upstream-rule (3건) | archive (2건) | automation (2건) | bit (2건) | clusters (2건) | doc-finder (2건) | drift (2건) | duplication (2건) | efficiency (2건) | escalation (2건) | false-block (2건) | fast-path (2건) | guardrails (2건) | harness-starter (2건) | information-flow (2건) | isolation (2건) | lint (2건) | move (2건) | naming (2건) | pre-tool-use (2건) | propagation (2건) | regex-gap (2건) | routing (2건) | search (2건) | self-dependency (2건) | self-violation (2건) | test (2건) | tokens (2건) | verdict (2건) | whitelist (2건) | wip (2건) | write-doc (2건) | abbr (1건) | adr (1건) | advisor-flow (1건) | agent-context (1건) | agent-orchestration (1건) | agent-spec (1건) | aggregation (1건) | ambiguity (1건) | amplification (1건) | anomaly (1건) | anti-defer (1건) | apply (1건) | architecture (1건) | atomic (1건) | baseline (1건) | bash (1건) | benchmark (1건) | bidirectional (1건) | brainstorm (1건) | bug (1건) | bug-triage (1건) | cleanup (1건) | cli (1건) | cluster (1건) | cluster-update (1건) | code (1건) | coding-convention (1건) | commit-flow (1건) | commit-skill (1건) | completed (1건) | completion (1건) | completion-gate (1건) | compliance (1건) | context (1건) | context7 (1건) | cost (1건) | cps-integrity (1건) | dead-code (1건) | debug (1건) | debug-guard (1건) | decision-framework (1건) | defense (1건) | delegation (1건) | diagnosis-discipline (1건) | diet (1건) | diff (1건) | doc-health (1건) | docs-structure (1건) | docs_ops (1건) | downstream-name (1건) | dynamic-resolution (1건) | enoent (1건) | env (1건) | env-var (1건) | eval-integrity (1건) | execution (1건) | exempt (1건) | external-docs (1건) | false-completion (1건) | false-warning (1건) | fast-help (1건) | feedback (1건) | feedback-report (1건) | feedback-reports (1건) | force-trigger (1건) | format (1건) | friction (1건) | gap-analysis (1건) | gate-redesign (1건) | gating (1건) | gemini (1건) | generic (1건) | git-remote (1건) | glob (1건) | graph (1건) | guard (1건) | handoff (1건) | harness-json (1건) | historical (1건) | hook-strength (1건) | improvement (1건) | incremental-update (1건) | index-removal (1건) | inflation (1건) | init-check (1건) | integrity (1건) | internalization (1건) | interrupt (1건) | json-schema (1건) | judgment (1건) | karpathy (1건) | kickoff (1건) | layering (1건) | legacy (1건) | living-harness (1건) | lsp (1건) | matcher (1건) | matching (1건) | maxturns (1건) | mcp (1건) | merge (1건) | meta-decision (1건) | metadata (1건) | migration-log (1건) | migrations (1건) | milestones (1건) | mvi (1건) | mvr (1건) | no-speculation (1건) | objectification (1건) | orchestrator (1건) | organism (1건) | overhaul (1건) | perf (1건) | permissions (1건) | phase (1건) | phase3 (1건) | philosophy-shift (1건) | port (1건) | prd (1건) | pre-commit-check (1건) | problem (1건) | profile (1건) | promise (1건) | protection (1건) | push (1건) | quality (1건) | read-enforce (1건) | readme (1건) | redesign (1건) | regex (1건) | reliability (1건) | reopen (1건) | reporting (1건) | research (1건) | review-agent (1건) | review-pattern (1건) | rollback (1건) | routing-tag (1건) | rule-origin (1건) | scoring (1건) | security (1건) | self-correction (1건) | self-invocation (1건) | self-multiplication (1건) | session-handoff (1건) | session-start (1건) | session-summary (1건) | sh (1건) | signal (1건) | silent-fail (1건) | simplify (1건) | skill-md (1건) | snapshot (1건) | solution-ref (1건) | specialist (1건) | starter_skills (1건) | step7.5 (1건) | stop-guard (1건) | structure (1건) | subagent (1건) | sync (1건) | task_groups (1건) | test-results (1건) | testing (1건) | threat-analyst (1건) | three-way-merge (1건) | tool-budget (1건) | tool-usage (1건) | typecheck (1건) | upstream (1건) | upstream-feedback (1건) | upstream-only (1건) | v0.42.4-regression (1건) | verification (1건) | verify-relates (1건) | versioning (1건) | wiki-graph (1건) | wip-parsing (1건) | wip-template (1건)

## tag별 문서 (백링크, 2건+)

### review

- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분](../decisions/hn_review_tool_budget.md)
- [review 에이전트 verdict 헤더 형식 준수율 — 100% 누락 패턴](../decisions/hn_review_verdict_compliance.md)
- [본 세션 시험 결과 종합 — review verdict + wip-sync false positive 누적 데이터](../decisions/hn_session_test_results.md)
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의](../harness/hn_contamination_followup.md)
- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)
- [split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정](../harness/hn_split_commit_review_stage.md)
- [split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화](../harness/hn_split_diff_delivery.md)
- [review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트](../harness/hn_staging_remaining.md)
- [커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)](../incidents/hn_commit_process_gaps.md)
- [archived/promotion-log에 다운스트림 제품명 유출 — review 발견](../incidents/hn_downstream_name_leak.md)
- [review 에이전트 maxTurns 소진 시 verdict 누락](../incidents/hn_review_maxturns_verdict_miss.md)
- [review v0.8.0 패턴 매핑 재설계 — starter 격리 벤치마크](../incidents/hn_review_v080_benchmark.md)

### commit

- [commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)](../decisions/hn_commit_auto_verify.md)
- [commit 흐름 자동화 — wip-sync + git commit wrapper](../decisions/hn_commit_finalize_wrapper.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [commit Step 2 후속 — write-doc symptom-keywords 재질의 + completed 미결 차단 자동화](../harness/hn_commit_step2_partial_completion.md)
- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)
- [split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정](../harness/hn_split_commit_review_stage.md)
- [split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화](../harness/hn_split_diff_delivery.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)
- [WIP 완료 자동화 구조적 결함 — Step 7.5 미동작 + SSOT 드리프트 + 이동 미연결](../harness/hn_wip_completion_gap.md)
- [커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)](../incidents/hn_commit_process_gaps.md)
- [wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락](../incidents/hn_wip_sync_incidents_gap.md)

### downstream

- [다운스트림 증폭 측정 — Phase 4-A baseline 수집·가설 검증](../decisions/hn_downstream_amplification.md)
- [eval CPS 무결성 감시 — 박제 감지·Problem 인플레이션](../decisions/hn_eval_cps_integrity.md)
- [eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단](../decisions/hn_eval_harness_cli_lsp_drift.md)
- [자가 발화 의존 규칙의 일반 실패 — P8 등록 + debug-guard.sh 확장](../decisions/hn_self_invocation_failure.md)
- [테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거](../decisions/hn_test_diet.md)
- [harness-upgrade silent fail 차단 보강 (FR-001/002/003 + FR-006)](../decisions/hn_upgrade_silent_fail_guards.md)
- [다운스트림 피드백 채널 포맷 규격화 + eval --harness 테스트](../harness/hn_feedback_channel_format.md)
- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)
- [다운스트림 마이그레이션 가이드 — 아카이브](../harness/MIGRATIONS-archive.md)
- [다운스트림 마이그레이션 가이드](../harness/MIGRATIONS.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)
- [starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄](../incidents/hn_starter_push_skipped.md)

### cps

- [adopt-without-init 다운스트림 능동 유도 — harness-init 자동 트리거](../decisions/hn_adopt_without_init_guard.md)
- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계](../decisions/hn_bug_interrupt_triage.md)
- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [CPS Problem 인용 빈도 검토 — P1·P3·P4·P6 정체 의심 판정](../decisions/hn_cps_problem_inflation_review.md)
- [eval CPS 무결성 감시 — 박제 감지·Problem 인플레이션](../decisions/hn_eval_cps_integrity.md)
- [starter 모호성 흡수 + CPS Problem 임계 상향 + S7 미정의 명시](../decisions/hn_starter_ambiguity_absorption.md)
- [harness-starter CPS — C 판단 프롬프트](../guides/project_kickoff.md)
- [PRD 레이어 보강 — User Needs 섹션·milestones 샘플·harness-init 권고](../harness/hn_prd_layers.md)
- [eval에 Solution 충족 인용 분포 집계 추가](../harness/hn_solution_ref_aggregation.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)

### skill

- [룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)](../decisions/hn_rule_skill_ssot.md)
- [룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md](../decisions/hn_rule_skill_ssot_apply.md)
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [starter 전용 스킬 격리 — harness-dev 스킬 신설](../decisions/hn_starter_skill_isolation.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [eval 기본 모드 보고 구조 개선](../harness/hn_eval_basic_mode_report.md)
- [HARNESS.json skills 목록 정리 — 1회성 스킬 삭제 + 활성 목록 정비](../harness/hn_harness_json_cleanup.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)

### eval

- [eval CPS 무결성 감시 — 박제 감지·Problem 인플레이션](../decisions/hn_eval_cps_integrity.md)
- [eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단](../decisions/hn_eval_harness_cli_lsp_drift.md)
- [eval --harness medium 결과 정비 (5-4 Feedback Reports 인식 + 5-5 self-verify 모호성)](../decisions/hn_eval_harness_medium_fixes.md)
- [eval --deep 보안 강화 패치 타 프로젝트 이식 가이드](../guides/hn_eval_security_patch_port.md)
- [eval 4관점 advisor 이관 + specialist 품질 보강 (threat-analyst 신설·산출물 점수·업계 탑 인물)](../harness/hn_eval_advisor_migration.md)
- [eval 기본 모드 보고 구조 개선](../harness/hn_eval_basic_mode_report.md)
- [다운스트림 피드백 채널 포맷 규격화 + eval --harness 테스트](../harness/hn_feedback_channel_format.md)
- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)
- [eval에 Solution 충족 인용 분포 집계 추가](../harness/hn_solution_ref_aggregation.md)
- [FR 필드 정규식 — bold 마커 내부 괄호 보강어 미인식 회귀](../incidents/hn_fr_field_regex_bold_inner_paren.md)

### ssot

- [코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리](../decisions/hn_code_ssot_audit.md)
- [HARNESS_UPGRADE 환경변수 의미 일관화](../decisions/hn_harness_upgrade_env_semantics.md)
- [Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT](../decisions/hn_karpathy_principles.md)
- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)](../decisions/hn_rule_skill_ssot.md)
- [룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md](../decisions/hn_rule_skill_ssot_apply.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md)
- [WIP 완료 자동화 구조적 결함 — Step 7.5 미동작 + SSOT 드리프트 + 이동 미연결](../harness/hn_wip_completion_gap.md)

### staging

- [Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT](../decisions/hn_karpathy_principles.md)
- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md)
- [wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단](../decisions/hn_wip_sync_staging_gaps.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정](../harness/hn_split_commit_review_stage.md)
- [review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트](../harness/hn_staging_remaining.md)
- [review v0.8.0 패턴 매핑 재설계 — starter 격리 벤치마크](../incidents/hn_review_v080_benchmark.md)

### hook

- [오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI](../decisions/hn_orchestrator_mechanism.md)
- [P8 starter 자기 적용 + commit 흐름 강제 트리거 보강](../decisions/hn_p8_starter_self_application.md)
- [자가 발화 의존 규칙의 일반 실패 — P8 등록 + debug-guard.sh 확장](../decisions/hn_self_invocation_failure.md)
- [stop-guard.sh → stop-guard.py 전환 (자기증식 차단)](../decisions/hn_stop_guard_py_migration.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [PreToolUse Bash -n 오탐으로 정당한 명령 차단](../incidents/hn_bash_n_flag_overblock.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)

### rules

- [BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계](../decisions/hn_bug_interrupt_triage.md)
- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [pipeline-design 규칙 업스트림 이식 계획](../decisions/hn_pipeline_design_rule.md)
- [약속 박제 보호 — completed 봉인 + 미루기 차단 룰](../decisions/hn_promise_protection.md)
- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)](../decisions/hn_rule_skill_ssot.md)
- [룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md](../decisions/hn_rule_skill_ssot_apply.md)
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md)

### upgrade

- [HARNESS_UPGRADE 환경변수 의미 일관화](../decisions/hn_harness_upgrade_env_semantics.md)
- [Remote 기반 하네스 업그레이드 전략](../decisions/hn_remote_upgrade_strategy.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [harness-upgrade silent fail 차단 보강 (FR-001/002/003 + FR-006)](../decisions/hn_upgrade_silent_fail_guards.md)
- [하네스 스타터 업그레이드 전파 전략](../guides/hn_upgrade_propagation.md)
- [harness-starter 이상 징후 묶음 (다운스트림 발견)](../harness/hn_upstream_anomalies.md)
- [다운스트림 마이그레이션 가이드 — 아카이브](../harness/MIGRATIONS-archive.md)
- [다운스트림 마이그레이션 가이드](../harness/MIGRATIONS.md)

### audit

- [코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리](../decisions/hn_code_ssot_audit.md)
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md)
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)

### pre-check

- [completed 봉인 — 본문 마크다운 링크 경로 교체 면제](../decisions/hn_sealed_link_exempt.md)
- [verify-relates pre-check 통합 — 커밋 시 relates-to 전수 검사](../decisions/hn_verify_relates_precheck.md)
- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [test-pre-commit 스위트 성능 — 잔여 구조 재설계](../harness/hn_test_suite_perf.md)
- [pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단](../incidents/hn_sealed_migrations_exempt_gap.md)
- [pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단](../incidents/hn_sealed_reopen_false_block.md)
- [pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단](../incidents/hn_secret_line_exempt_gap.md)

### ac

- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [BIT(Bug Interrupt Triage) — 스코프 외 버그 자율 판단 시스템 설계](../decisions/hn_bug_interrupt_triage.md)
- [commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)](../decisions/hn_commit_auto_verify.md)
- [Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT](../decisions/hn_karpathy_principles.md)
- [테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거](../decisions/hn_test_diet.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)

### harness-upgrade

- [starter_skills 필터링 미구현 — harness-upgrade 폴더 복사 제외 + harness-dev 등록](../decisions/hn_starter_skills_filter.md)
- [침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계](../harness/hn_defense_visibility.md)
- [하네스 자잘한 버그 묶음 — MIGRATIONS 누락·starter_skills 오염·permissions.allow 미전파·h-setup.sh 오분류·신규설치 필터 누락·harness-sync 경계 불명확·docs/harness 전달 오염](../harness/hn_migrations_version_gap.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)

### migration

- [stop-guard.sh → stop-guard.py 전환 (자기증식 차단)](../decisions/hn_stop_guard_py_migration.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [하네스 자잘한 버그 묶음 — MIGRATIONS 누락·starter_skills 오염·permissions.allow 미전파·h-setup.sh 오분류·신규설치 필터 누락·harness-sync 경계 불명확·docs/harness 전달 오염](../harness/hn_migrations_version_gap.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)
- [다운스트림 마이그레이션 가이드 — 아카이브](../harness/MIGRATIONS-archive.md)
- [다운스트림 마이그레이션 가이드](../harness/MIGRATIONS.md)

### docs-ops

- [cluster 재생성 게이팅 — 본체 변경 시 전수 갱신 패턴 분리](../decisions/hn_cluster_update_gating.md)
- [wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단](../decisions/hn_wip_sync_staging_gaps.md)
- [docs_ops.py move 시 relates-to 역참조 자동 갱신](../harness/hn_docs_ops_relates_to_rewrite.md)
- [docs-ops.sh cluster-update 성능 저하 — extract_abbrs() 반복 호출](../incidents/hn_docs_ops_cluster_update_perf.md)
- [wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락](../incidents/hn_wip_sync_incidents_gap.md)

### false-positive

- [docs_ops.py wip-sync 부분 매칭 버그 — 매칭 정밀화](../decisions/hn_wip_sync_match_precision.md)
- [PreToolUse Bash -n 오탐으로 정당한 명령 차단](../incidents/hn_bash_n_flag_overblock.md)
- [v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭](../incidents/hn_lint_enoent_pattern_gaps.md)
- [광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험](../incidents/hn_matcher_false_block.md)
- [pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단](../incidents/hn_secret_line_exempt_gap.md)

### split

- [커밋 프로세스 감사 — #18 false-negative 축 보강](../harness/hn_commit_process_audit.md)
- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)
- [split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정](../harness/hn_split_commit_review_stage.md)
- [split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화](../harness/hn_split_diff_delivery.md)
- [커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)](../incidents/hn_commit_process_gaps.md)

### wip-sync

- [commit 흐름 자동화 — wip-sync + git commit wrapper](../decisions/hn_commit_finalize_wrapper.md)
- [본 세션 시험 결과 종합 — review verdict + wip-sync false positive 누적 데이터](../decisions/hn_session_test_results.md)
- [docs_ops.py wip-sync 부분 매칭 버그 — 매칭 정밀화](../decisions/hn_wip_sync_match_precision.md)
- [wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단](../decisions/hn_wip_sync_staging_gaps.md)
- [wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락](../incidents/hn_wip_sync_incidents_gap.md)

### agent

- [review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분](../decisions/hn_review_tool_budget.md)
- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)
- [debug-specialist 에이전트 신설 — 막힐 때 자동 위임처 확보](../harness/hn_debug_specialist.md)

### contamination

- [범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의](../harness/hn_contamination_followup.md)
- [하네스 범용성 오염 방지 — 다운스트림 고유명사 유입 차단](../harness/hn_generic_contamination_protection.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)
- [archived/promotion-log에 다운스트림 제품명 유출 — review 발견](../incidents/hn_downstream_name_leak.md)

### dead-link

- [completed 봉인 — 본문 마크다운 링크 경로 교체 면제](../decisions/hn_sealed_link_exempt.md)
- [verify-relates pre-check 통합 — 커밋 시 relates-to 전수 검사](../decisions/hn_verify_relates_precheck.md)
- [docs_ops.py move 시 relates-to 역참조 자동 갱신](../harness/hn_docs_ops_relates_to_rewrite.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)

### frontmatter

- [harness-adopt 레거시 문서 정비 지원 — doc-health 진단 플로우](../decisions/hn_adopt_legacy_doc_health.md)
- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [프론트매터 그래프 스펙 설계](../decisions/hn_frontmatter_graph_spec.md)
- [Wiki 그래프 자산 생성 wave — frontmatter·tag·relates-to 일제 정비](../decisions/hn_wiki_graph_assets.md)

### harness-dev

- [starter 전용 스킬 격리 — harness-dev 스킬 신설](../decisions/hn_starter_skill_isolation.md)
- [starter_skills 필터링 미구현 — harness-upgrade 폴더 복사 제외 + harness-dev 등록](../decisions/hn_starter_skills_filter.md)
- [하네스 자잘한 버그 묶음 — MIGRATIONS 누락·starter_skills 오염·permissions.allow 미전파·h-setup.sh 오분류·신규설치 필터 누락·harness-sync 경계 불명확·docs/harness 전달 오염](../harness/hn_migrations_version_gap.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)

### implementation

- [implementation init check 게이트 정밀화 — 환경 양식 drift 비용 제거](../decisions/hn_init_gate_redesign.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)
- [Phase 구조 보강 — WIP AC 섹션 + Phase 6원칙 + escalate 에이전트 트리거 + WIP 실행 순서](../harness/hn_phase_agent_improvements.md)
- [검증 파이프라인 강화 — MIGRATIONS 자동생성·AC 강제·CPS 갱신 강제](../harness/hn_verification_pipeline.md)

### incident

- [pipeline-design 규칙 업스트림 이식 원천 사례](../incidents/hn_pipeline_design_rule_origin.md)
- [review 에이전트 maxTurns 소진 시 verdict 누락](../incidents/hn_review_maxturns_verdict_miss.md)
- [세션 거짓 완료·자기 위반 패턴 누적 (다음 세션 인계)](../incidents/hn_session_false_completion.md)
- [wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락](../incidents/hn_wip_sync_incidents_gap.md)

### refactor

- [코드 SSOT 서더링 감사 — 중복 정의·동기화 부담 정리](../decisions/hn_code_ssot_audit.md)
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [commit + review 핸드오프 계약 이식 + 중복 제거](../harness/hn_commit_review_handoff.md)

### starter

- [P8 starter 자기 적용 + commit 흐름 강제 트리거 보강](../decisions/hn_p8_starter_self_application.md)
- [starter 전용 스킬 격리 — harness-dev 스킬 신설](../decisions/hn_starter_skill_isolation.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)
- [starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄](../incidents/hn_starter_push_skipped.md)

### advisor

- [advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시](../harness/hn_advisor_decision_framework.md)
- [eval 4관점 advisor 이관 + specialist 품질 보강 (threat-analyst 신설·산출물 점수·업계 탑 인물)](../harness/hn_eval_advisor_migration.md)
- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)

### cascade

- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI](../decisions/hn_orchestrator_mechanism.md)

### docs

- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md)
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md)

### governance

- [HARNESS_UPGRADE 환경변수 의미 일관화](../decisions/hn_harness_upgrade_env_semantics.md)
- [Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세](../decisions/hn_rules_metadata.md)
- [Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계](../decisions/hn_staging_governance.md)

### harness-adopt

- [harness-adopt 레거시 문서 정비 지원 — doc-health 진단 플로우](../decisions/hn_adopt_legacy_doc_health.md)
- [adopt-without-init 다운스트림 능동 유도 — harness-init 자동 트리거](../decisions/hn_adopt_without_init_guard.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)

### harness-init

- [adopt-without-init 다운스트림 능동 유도 — harness-init 자동 트리거](../decisions/hn_adopt_without_init_guard.md)
- [PRD 레이어 보강 — User Needs 섹션·milestones 샘플·harness-init 권고](../harness/hn_prd_layers.md)
- [starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정](../harness/hn_starter_skill_self_delete.md)

### harness-map

- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [하네스 유기체화 설계 — HARNESS_MAP.md 신경망 허브 구현 방안](../guides/hn_harness_organism_design.md)
- [MVR 매핑 + HARNESS_MAP 에이전트 관점 개선](../harness/hn_mvr_map_agent_view.md)

### measurement

- [다운스트림 증폭 측정 — Phase 4-A baseline 수집·가설 검증](../decisions/hn_downstream_amplification.md)
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md)
- [review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트](../harness/hn_staging_remaining.md)

### memory

- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [Harness-Starter 업그레이드 계획](../decisions/hn_upgrade.md)
- [eval 기본 모드 보고 구조 개선](../harness/hn_eval_basic_mode_report.md)

### orchestration

- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시](../harness/hn_advisor_decision_framework.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)

### performance

- [commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합](../harness/hn_commit_review_staging.md)
- [session-start.sh → session-start.py 전환 — spawn 비용 절감](../harness/hn_session_start_py.md)
- [docs-ops.sh cluster-update 성능 저하 — extract_abbrs() 반복 호출](../incidents/hn_docs_ops_cluster_update_perf.md)

### pipeline

- [Gemini CLI subagent 위임 파이프라인 설계](../decisions/hn_gemini_delegation_pipeline.md)
- [pipeline-design 규칙 업스트림 이식 계획](../decisions/hn_pipeline_design_rule.md)
- [pipeline-design 규칙 업스트림 이식 원천 사례](../incidents/hn_pipeline_design_rule_origin.md)

### python

- [stop-guard.sh → stop-guard.py 전환 (자기증식 차단)](../decisions/hn_stop_guard_py_migration.md)
- [자기복제 케이스 sh 적용 점검 + WIP 파싱 SSOT 통합 (wip_util.py + 3 hook 마이그레이션)](../decisions/hn_wip_util_ssot.md)
- [session-start.sh → session-start.py 전환 — spawn 비용 절감](../harness/hn_session_start_py.md)

### relates-to

- [verify-relates pre-check 통합 — 커밋 시 relates-to 전수 검사](../decisions/hn_verify_relates_precheck.md)
- [Wiki 그래프 자산 생성 wave — frontmatter·tag·relates-to 일제 정비](../decisions/hn_wiki_graph_assets.md)
- [docs_ops.py move 시 relates-to 역참조 자동 갱신](../harness/hn_docs_ops_relates_to_rewrite.md)

### sealed

- [completed 봉인 — 본문 마크다운 링크 경로 교체 면제](../decisions/hn_sealed_link_exempt.md)
- [pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단](../incidents/hn_sealed_migrations_exempt_gap.md)
- [pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단](../incidents/hn_sealed_reopen_false_block.md)

### secret-scan

- [eval --deep 보안 강화 패치 타 프로젝트 이식 가이드](../guides/hn_eval_security_patch_port.md)
- [harness-starter 이상 징후 묶음 (다운스트림 발견)](../harness/hn_upstream_anomalies.md)
- [pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단](../incidents/hn_secret_line_exempt_gap.md)

### self-verify

- [eval --harness medium 결과 정비 (5-4 Feedback Reports 인식 + 5-5 self-verify 모호성)](../decisions/hn_eval_harness_medium_fixes.md)
- [Karpathy 원칙 적용 — 코딩 컨벤션·행동 원칙·self-verify·staging·commit SSOT](../decisions/hn_karpathy_principles.md)
- [커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)](../incidents/hn_commit_process_gaps.md)

### simplification

- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거](../harness/hn_index_md_removal.md)
- [하네스 단순화 — 추가 누적으로 인한 마찰 회수](../harness/hn_simplification.md)

### trigger

- [CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성](../decisions/hn_cps_entry_signal_layering.md)
- [memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의](../decisions/hn_memory.md)
- [테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거](../decisions/hn_test_diet.md)

### upstream-rule

- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [pipeline-design 규칙 업스트림 이식 계획](../decisions/hn_pipeline_design_rule.md)
- [pipeline-design 규칙 업스트림 이식 원천 사례](../incidents/hn_pipeline_design_rule_origin.md)

### archive

- [다운스트림 마이그레이션 가이드 — 아카이브](../harness/MIGRATIONS-archive.md)
- [archived/promotion-log에 다운스트림 제품명 유출 — review 발견](../incidents/hn_downstream_name_leak.md)

### automation

- [commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)](../decisions/hn_commit_auto_verify.md)
- [commit 흐름 자동화 — wip-sync + git commit wrapper](../decisions/hn_commit_finalize_wrapper.md)

### bit

- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [자가 발화 의존 규칙의 일반 실패 — P8 등록 + debug-guard.sh 확장](../decisions/hn_self_invocation_failure.md)

### clusters

- [cluster 재생성 게이팅 — 본체 변경 시 전수 갱신 패턴 분리](../decisions/hn_cluster_update_gating.md)
- [WIP cluster scan 가시성 — in-progress 도달 경로 추가](../decisions/hn_wip_cluster_visibility.md)

### doc-finder

- [WIP cluster scan 가시성 — in-progress 도달 경로 추가](../decisions/hn_wip_cluster_visibility.md)
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md)

### drift

- [eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단](../decisions/hn_eval_harness_cli_lsp_drift.md)
- [implementation init check 게이트 정밀화 — 환경 양식 drift 비용 제거](../decisions/hn_init_gate_redesign.md)

### duplication

- [룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)](../decisions/hn_rule_skill_ssot.md)
- [룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md](../decisions/hn_rule_skill_ssot_apply.md)

### efficiency

- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)
- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md)

### escalation

- [debug-specialist 에이전트 신설 — 막힐 때 자동 위임처 확보](../harness/hn_debug_specialist.md)
- [Phase 구조 보강 — WIP AC 섹션 + Phase 6원칙 + escalate 에이전트 트리거 + WIP 실행 순서](../harness/hn_phase_agent_improvements.md)

### false-block

- [pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단](../incidents/hn_sealed_migrations_exempt_gap.md)
- [pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단](../incidents/hn_sealed_reopen_false_block.md)

### fast-path

- [WIP cluster scan 가시성 — in-progress 도달 경로 추가](../decisions/hn_wip_cluster_visibility.md)
- [하네스 효율성 전면 점검 — 3계층 통합 (split·다운스트림 증폭·흐름 유기성)](../harness/hn_harness_efficiency_overhaul.md)

### guardrails

- [LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합](../harness/hn_guardrails_followup.md)
- [LLM 실수 방지 가드레일 — 내부 자료 우선 + 추측 차단 + advisor 연동](../harness/hn_llm_mistake_guardrails.md)

### harness-starter

- [하네스 범용성 오염 방지 — 다운스트림 고유명사 유입 차단](../harness/hn_generic_contamination_protection.md)
- [업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소](../harness/hn_upstream_only_audit.md)

### information-flow

- [하네스 단계간 정보 흐름 누수 전수 조사](../harness/hn_info_flow_leak_audit.md)
- [정보 흐름 누수 해소 Phase 3 — 정성 평가 종결](../harness/hn_info_flow_leak_phase3.md)

### isolation

- [starter 전용 스킬 격리 — harness-dev 스킬 신설](../decisions/hn_starter_skill_isolation.md)
- [starter_skills 필터링 미구현 — harness-upgrade 폴더 복사 제외 + harness-dev 등록](../decisions/hn_starter_skills_filter.md)

### lint

- [v0.18.3 린터 ENOENT 패턴 — 오탐 가능성·OS 커버리지 갭](../incidents/hn_lint_enoent_pattern_gaps.md)
- [린터 도구 실종 — T13이 우연히 가시화한 환경 이슈](../incidents/hn_test_isolation_git_log_leak.md)

### move

- [docs_ops.py move 시 relates-to 역참조 자동 갱신](../harness/hn_docs_ops_relates_to_rewrite.md)
- [pre-check SEALED 오탐 — reopen→수정→move 정상 절차 경유 파일 차단](../incidents/hn_sealed_reopen_false_block.md)

### naming

- [문서 네이밍 전면 개편 — 도메인 약어 + 통합 원칙](../decisions/hn_doc_naming.md)
- [Glob 라우팅 태그 통과 — 사용자·에이전트 검색 비대칭 해소](../decisions/hn_glob_routing_tag.md)

### pre-tool-use

- [오케스트레이터 메커니즘 설계 — PreToolUse hook + orchestrator.py MVI](../decisions/hn_orchestrator_mechanism.md)
- [PreToolUse Bash -n 오탐으로 정당한 명령 차단](../incidents/hn_bash_n_flag_overblock.md)

### propagation

- [하네스 스타터 업그레이드 전파 전략](../guides/hn_upgrade_propagation.md)
- [starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄](../incidents/hn_starter_push_skipped.md)

### regex-gap

- [pre-check SEALED 면제 갭 — MIGRATIONS류 자기 운영 파일 잘못 차단](../incidents/hn_sealed_migrations_exempt_gap.md)
- [pre-check 시크릿 line 면제 갭 — agents/threat-analyst.md 잘못 차단](../incidents/hn_secret_line_exempt_gap.md)

### routing

- [스킬·에이전트 역할 분담 감사 — 라우터 패턴 전방위 적용](../decisions/hn_skill_agent_role_audit.md)
- [implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기](../harness/hn_implementation_router.md)

### search

- [Glob 라우팅 태그 통과 — 사용자·에이전트 검색 비대칭 해소](../decisions/hn_glob_routing_tag.md)
- [문서 탐색 프로토콜](../guides/hn_doc_search_protocol.md)

### self-dependency

- [BIT cascade 객관화 — Q3·NEW 플래그·CPS P# 매칭 자가 발화 의존 해소](../decisions/hn_bit_cascade_objectification.md)
- [P8 starter 자기 적용 + commit 흐름 강제 트리거 보강](../decisions/hn_p8_starter_self_application.md)

### self-violation

- [starter 모호성 흡수 + CPS Problem 임계 상향 + S7 미정의 명시](../decisions/hn_starter_ambiguity_absorption.md)
- [세션 거짓 완료·자기 위반 패턴 누적 (다음 세션 인계)](../incidents/hn_session_false_completion.md)

### test

- [테스트 다이어트 + 트리거 좁힘 — AC 기반 시스템과 중복 제거](../decisions/hn_test_diet.md)
- [test-pre-commit 스위트 성능 — 잔여 구조 재설계](../harness/hn_test_suite_perf.md)

### tokens

- [review staging 재조정 — scripts/agents 이진 판정](../decisions/hn_review_staging_rebalance.md)
- [review 에이전트 tool call 예산 재설계 — 조기 중단 + 유동 배분](../decisions/hn_review_tool_budget.md)

### verdict

- [review 에이전트 verdict 헤더 형식 준수율 — 100% 누락 패턴](../decisions/hn_review_verdict_compliance.md)
- [본 세션 시험 결과 종합 — review verdict + wip-sync false positive 누적 데이터](../decisions/hn_session_test_results.md)

### whitelist

- [commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)](../decisions/hn_commit_auto_verify.md)
- [rules → docs 참조 화이트리스트 — 동적 탐색으로 대체](../harness/hn_review_whitelist_autodetect.md)

### wip

- [WIP cluster scan 가시성 — in-progress 도달 경로 추가](../decisions/hn_wip_cluster_visibility.md)
- [WIP 완료 자동화 구조적 결함 — Step 7.5 미동작 + SSOT 드리프트 + 이동 미연결](../harness/hn_wip_completion_gap.md)

### write-doc

- [commit Step 2 후속 — write-doc symptom-keywords 재질의 + completed 미결 차단 자동화](../harness/hn_commit_step2_partial_completion.md)
- [범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의](../harness/hn_contamination_followup.md)
