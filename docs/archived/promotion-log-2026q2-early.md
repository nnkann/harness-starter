---
title: 승격/강등 이력 (2026 Q2 초반 — 2026-04-08 ~ 2026-04-20 아카이브)
domain: harness
tags: [promotion, rule-change, archive]
relates-to:
  - path: harness/promotion-log.md
    rel: supersedes
status: completed
created: 2026-04-08
updated: 2026-04-20
---

# 승격/강등 이력 — 2026 Q2 초반 아카이브

> 원본 `docs/harness/promotion-log.md`의 2026-04-08 ~ 2026-04-20 구간 전체.
> 아카이브 이유: 152행 누적으로 파일 비대화. B+D 전략(버전 범프 중심 압축
> + 분기 롤링) 적용. 상세 내역은 해당 시점 `decisions/`·`harness/` 문서가
> 실제 SSOT이며, 본 아카이브는 시간순 통합 뷰 보존용.

## 이력

| 날짜 | 규칙 | 변경 | 이유 |
|------|------|------|------|
| 2026-04-16 | docs/ 폴더 구조 | 리팩토링 | development/setup/history/ → decisions/guides/incidents/ 의미 기반 분류 |
| 2026-04-16 | .claude/agents/ | 신설 | docs-lookup, docs-manager, review 에이전트 추가 |
| 2026-04-16 | INDEX.md + clusters/ | 신설 | 3홉 탐색 구조 (INDEX → cluster → 본문) |
| 2026-04-16 | 버전 | 0.6.0 → 0.7.0 | 폴더 구조 변경 + 에이전트 인프라는 breaking change |
| 2026-04-16 | harness-adopt 스킬 | 신설 | 기존 프로젝트에 하네스 이식하는 대화형 흐름 |
| 2026-04-16 | harness-init | 차단 게이트 추가 | 기존 프로젝트 감지 시 adopt 먼저 강제 |
| 2026-04-16 | implementation | 차단 게이트 강화 | init 미완료 시 선택지 제거, 차단으로 변경 |
| 2026-04-16 | 버전 | 0.7.0 → 0.8.0 | 신규 스킬 + 기존 스킬 게이트 로직 변경 |
| 2026-04-16 | h-setup.sh --upgrade | 재설계 | 파일 복사 → git remote 기반 (harness-upstream fetch + diff) |
| 2026-04-16 | harness-upgrade 스킬 | 재설계 | .upgrade/ 스테이징 → git show + merge-file 3-way merge |
| 2026-04-16 | harness-adopt 스킬 | remote 단계 추가 | Step 6에 harness-upstream remote 설정 + installed_from_ref 기록 |
| 2026-04-16 | harness.json | installed_from_ref 추가 | 3-way merge의 base revision 추적용 |
| 2026-04-16 | 버전 | 0.8.0 → 0.9.0 | 업그레이드 인프라 전면 재설계 |
| 2026-04-16 | advisor/check-existing/implementation | description TRIGGER/SKIP 추가, advisor 에이전트 관점 분리 | 스킬 자동 트리거 강화 |
| 2026-04-16 | 버전 | 0.9.0 → 0.9.1 | 기존 스킬 로직 수정 (patch) |
| 2026-04-16 | commit 스킬 Review | hook으로 분리 | Review를 스킬 내부에서 PreToolUse agent hook으로 이동, 위험도 기반 조건부 실행 |
| 2026-04-16 | pre-commit-check.sh | 위험도 차단→경고 | light 모드 위험도 감지 시 차단 대신 경고만 출력, 리뷰 판단은 hook agent가 담당 |
| 2026-04-16 | 버전 | 0.9.1 → 0.9.2 | commit 스킬 리뷰 분리 (patch) |
| 2026-04-16 | 메타데이터 통합 | HARNESS_VERSION + harness.json + .harness_adopted → HARNESS.json | 3개 파일을 단일 HARNESS.json으로 통합 |
| 2026-04-16 | 버전 | 0.9.2 → 1.0.0 | 메타데이터 구조 전면 변경 — 안정 버전 전환 |
| 2026-04-16 | harness-upgrade 스킬 | remote 로직 흡수 | h-setup.sh의 remote 업그레이드를 스킬이 직접 처리. h-setup.sh는 fallback만 |
| 2026-04-16 | harness-upgrade Step 0 | adopt 사전 점검 추가 | adopt 미완료 프로젝트에서 upgrade 시 adopt를 먼저 자동 실행 |
| 2026-04-16 | 버전 | 1.0.0 → 1.0.1 | 기존 스킬 로직 수정 (patch) |
| 2026-04-16 | advisor/review/docs-lookup/docs-manager | docs/ 클러스터 탐색 통합 | 에이전트들이 decisions/incidents/guides/를 직접 참조하도록 개선 |
| 2026-04-16 | harness-init/upgrade/adopt | docs-manager 위임·정합성 검증 추가 | INDEX.md/clusters 생성·검증을 docs-manager에 위임, 분류 기준 명시 |
| 2026-04-16 | 버전 | 1.0.1 → 1.0.2 | 전체 에이전트·스킬의 docs/ 클러스터 활용 누락 수정 (patch) |
| 2026-04-16 | settings.json | 훅 중복 제거 + permissions 분리 | [skip-review] 중복 matcher 제거, permissions를 settings.local.json으로 이동, .gitignore 추가 |
| 2026-04-16 | 버전 | 1.0.2 → 1.0.3 | 설정 파일 구조 정리 (patch) |
| 2026-04-16 | write-doc 스킬 | 신설 | 코드 작업 없이 문서만 단독 생성할 때 폴더 판단·프론트매터·파일명 규칙 강제 |
| 2026-04-16 | 버전 | 1.0.3 → 1.1.0 | 신규 스킬 추가 (minor) |
| 2026-04-18 | rules/security.md | 신설 | 시크릿 하드코딩 금지 + 4계층 방어(pre-commit / CI / eval --deep / rotation 플레이북) |
| 2026-04-18 | eval --deep | Step 0 + Step 1 + 4관점 | 시크릿 스캔(working tree + history) + archive 폴더 강제 점검 + 외부 공격자 페르소나 추가 |
| 2026-04-18 | agents/review.md | 스코프 경계 + 3관점 | diff 전용으로 재분배, 회귀/계약/스코프 관점 추가, 전체 코드 기반 판단 항목은 eval로 이관 |
| 2026-04-18 | scripts/install-secret-scan-hook.sh | 신설 | pre-commit 시크릿 스캔 훅 설치기, gitleaks 우선 grep 폴백 |
| 2026-04-18 | .claude/memory/ | 신설 | feedback 메모리 경로 활성화, 2026-04-18 dev-tools 사고 교훈 저장 |
| 2026-04-18 | h-setup.sh | BSD sed 호환 | sed_inplace 헬퍼 추가 + awk 기반 JSON 치환, macOS 호환성 확보 |
| 2026-04-18 | settings.json | matcher 확장 | --no-verify 차단을 모든 명령으로 확대, git commit 공백 2개 케이스 포함 |
| 2026-04-18 | 버전 | 1.1.0 → 1.2.0 | 보안 인프라 신설 (minor) |
| 2026-04-18 | settings.json matcher | 문법 오류 수정 | PreToolUse matcher를 tool name("Bash")으로 단일화, 명령어 인자 매칭은 if 필드로 이관. 2일간 hook 전체 무력 상태였음. |
| 2026-04-18 | 버전 | 1.2.0 → 1.2.1 | hook 발화 복구 (patch) |
| 2026-04-18 | settings.json + commit 스킬 | agent hook 가시성 | agent hook 3개에 statusMessage 추가 (spinner UI로 실행 노출), commit 스킬에 리뷰 결과 보고 규정 추가 |
| 2026-04-18 | 버전 | 1.2.1 → 1.2.2 | agent hook 가시성 개선 (patch) |
| 2026-04-18 | settings.json | agent → prompt hook 교체 + if 파이프 문법 수정 | VSCode 확장에서 agent hook 미동작 확인. prompt 타입으로 교체, if 필드 파이프(\|) 미지원으로 핸들러 분리 |
| 2026-04-18 | 버전 | 1.2.2 → 1.2.3 | hook 타입 교체 및 if 문법 수정 (patch) |
| 2026-04-18 | rules/docs.md | 검색·완료 규칙 강화 | IDE 컨텍스트 신뢰도 규칙, 3단계 검색 강제, 검색 실패 escalation, incidents/ 전용 symptom-keywords 필드, completed 전환 시 본문 미결 패턴 차단 |
| 2026-04-18 | settings.json | prompt hook matcher 보완 | git commit prompt hook 2개에 `Bash(* git commit*)` 체이닝 변형 추가 (command hook은 이미 있었으나 prompt 쪽 누락) |
| 2026-04-18 | pre-commit-check.sh | 문서 제외 | TODO/FIXME/HACK 검사에서 docs/, *.md, README/CHANGELOG 제외. 규칙 문서가 차단 키워드를 예시로 언급하는 메타 케이스에서 오탐 발생 |
| 2026-04-18 | 버전 | 1.2.3 → 1.3.0 | 문서 규칙 신설 (minor) |
| 2026-04-18 | settings.json | 리뷰 hook 제거 | prompt/agent type hook이 이 환경(PreToolUse)에서 리뷰 목적으로 작동 불가 확인. 이전 모든 버전에서 hook 리뷰는 사실상 무력. 공식 문서상 agent type은 PostToolUse 용 |
| 2026-04-18 | commit 스킬 | hook 리뷰 → Agent tool 직접 호출 | 스킬이 strict/위험도 hit 시 Agent tool로 review 서브에이전트를 직접 호출하도록 전환. v0.9.2 이전 구조 복원. Agent tool 호출 검증 완료 |
| 2026-04-18 | 버전 | 1.3.0 → 1.3.1 | 리뷰 구조 복원 (patch — 스킬 로직 수정) |
| 2026-04-18 | commit 스킬 | pre-check 조기 실행 단계 추가 | 스테이징 직후 pre-commit-check.sh를 명시 단계로 수동 실행. 정적 검사 실패 시 LLM 리뷰 호출 비용 절감. hook은 최후 안전망으로 유지 |
| 2026-04-18 | 버전 | 1.3.1 → 1.3.2 | pre-check 조기 실행으로 비용 최적화 (patch) |
| 2026-04-19 | rules/internal-first.md | 신설 | 외부 검색 전 내부 자료(사용자 증언·git log·docs·rules) 우선 강제. 가장 파괴적인 실수 패턴(외부는 뒤지면서 내부 무시) 차단 |
| 2026-04-19 | rules/no-speculation.md | 신설 | 추측으로 수정 시작 금지. 첫 행동 3원칙(관찰·재현·선행 사례) + review 에이전트가 감지할 패턴 정의. CLAUDE.md 텍스트 규칙으로는 sonnet 추측 방지 불충분 |
| 2026-04-19 | pre-commit-check.sh | 연속 수정 감지 추가 | 같은 파일 최근 5커밋 중 2회 경고/3회 차단. 증상 완화 반복 차단. [expand] 태그 또는 FORCE_REPEAT=1로 면제 |
| 2026-04-19 | 버전 | 1.3.2 → 1.4.0 | 새 규칙 2개 신설 (minor) |
| 2026-04-19 | pre-commit-check.sh | stdout 요약 4줄 출력 | stderr는 사용자용, stdout은 commit 스킬이 캡처해 review prompt에 주입. pre_check_passed/already_verified/risk_factors/diff_stats 4 key |
| 2026-04-19 | commit 스킬 SKILL.md | Step 5 stdout 캡처 + 호출 방법 prompt 예시 갱신 | review가 already_verified 재검사 안 하도록 데이터 경로 명시 |
| 2026-04-19 | review 에이전트 | "pre-check 결과 블록 처리" 섹션 신설 | already_verified 재검사 금지, risk_factors 우선순위 검증 명시 |
| 2026-04-19 | 버전 | 1.4.0 → 1.4.1 | commit 성능 최적화 데이터 경로 (patch — 기존 로직 수정) |
| 2026-04-19 | commit 스킬 + review 에이전트 | staged diff prompt 직접 주입 | review가 직전 커밋을 보던 사고(11fe9f2) 재발 방지. 스킬이 git diff --cached를 직접 캡처해 prompt에 박고, review는 git diff/log/show 자가 호출 금지 |
| 2026-04-19 | 버전 | 1.4.1 → 1.4.2 | review 신뢰성 회복 (patch) |
| 2026-04-19 | agents/ 재편 | 신규 6개 + 삭제 2개 + 1개 승격 | doc-finder(haiku), codebase-analyst, researcher, risk-analyst, performance-analyst, test-strategist, advisor 신설. docs-lookup 폐지(→doc-finder), docs-manager 에이전트→스킬 승격 |
| 2026-04-19 | advisor 스킬 | PM orchestrator 패턴으로 재설계 | 본문 3관점 상세는 에이전트로 흡수, 스킬은 얇은 래퍼. specialist 풀 (5종) 병렬 호출 + 종합. Anthropic Opus(lead)+Sonnet(sub) 패턴 (+90.2% 성능 사례) |
| 2026-04-19 | rules/self-verify.md | test-strategist 자동 트리거 연계 | 새 함수·버그 수정·리팩토링 전·flaky 테스트 시 자동 호출. self-verify가 위반 감지하면 호출자가 실제 호출 |
| 2026-04-19 | 버전 | 1.4.2 → 1.5.0 | 멀티 에이전트 풀 + advisor PM 패턴 (minor) |
| 2026-04-19 | pre-commit-check.sh | 연속 수정 면제 리스트 추가 | HARNESS.json·promotion-log·INDEX·clusters는 매 커밋마다 같이 갱신되는 정상 패턴이라 카운트에서 제외. 매번 [expand]로 우회하던 진짜 문제 해결 |
| 2026-04-19 | 버전 | 1.5.0 → 1.5.1 | 면제 리스트 추가 (patch — 기존 로직 수정) |
| 2026-04-19 | rules/staging.md 신설 | review staging 단일 진실 | 13개 신호 + 4단계 stage + 2단계 결정 + 3종 연결규칙 + 신호↔검증 매핑 + 폭증 차단 게이트 + git log 추적성. 외부 리서치(Anthropic·MAST 함정) 기반 |
| 2026-04-19 | naming.md 도메인 등급 섹션 | S9 신호 인프라 | "도메인 등급 (review staging)" + "경로 → 도메인 매핑" 섹션 추가. critical/normal/meta 3등급 |
| 2026-04-19 | pre-commit-check.sh | 신호 감지 + stdout 확장 | 13개 신호(S1~S15) 감지 로직 + 6개 신규 stdout key (signals/domains/domain_grades/multi_domain/repeat_count/recommended_stage). 1단계+2단계 결합 평가로 stage 자동 결정 |
| 2026-04-19 | commit 스킬 SKILL.md | Step 4 자동 병합 + Step 7 stage 분기 | 메타 파일 분리 커밋 차단(자동 병합), --quick/--deep 플래그, stage별 행동 명세, git log 추적성 한 줄 자동 포함 |
| 2026-04-19 | review.md | 신호별 검증 매핑 + Stage 모드 | recommended_stage·signals 처리, 신호↔카테고리 매핑 표 (13개), Stage 1 신규 패스 모드 |
| 2026-04-19 | 버전 | 1.5.1 → 1.6.0 | review staging 시스템 (minor — 신규 규칙 + 신규 스킬 인터페이스) |
| 2026-04-19 | rules/contamination.md 신설 | 범용성 오염 방지 P1 | harness-starter 전용 — 다운스트림 고유명사 검출 + 허용어 리스트(영문 90+ / 한글 80+). is_starter 리포에서만 활성. incidents/·scripts/·hooks/·자기 자신 면제. 사용자 판단용 경고 수준 (차단 안 함) |
| 2026-04-19 | pre-commit-check.sh | contamination 검출 블록 추가 | git diff에서 대문자 시작 3자+/한글 2자+ 추출 후 허용어 필터. risk_factors에 "오염 의심" 합쳐 review가 보도록 |
| 2026-04-19 | 버전 | 1.6.0 → 1.6.1 | contamination 검출 (patch — 기존 스크립트 확장) |
| 2026-04-19 | commit 스킬 Step 2 재설계 | WIP 부분 완료 자동 인식 흐름 | 사용자 명시 질문 4지선다(c/p/u/s) + 잔여 작업 별도 WIP 분리 + 차단 조건. 6개 WIP 정체 사고 재발 방지 |
| 2026-04-19 | WIP 6개 정리 | 5 completed 이동 + 4 후속 신설 + 1 pending 유지 | search_and_completion_gaps·commit_perf·llm_mistake_guardrails·generic_contamination·commit_review_staging → docs/harness/ 이동. 잔여는 commit_step2_partial·guardrails_followup·contamination_followup·staging_followup 4개 후속으로 분리 |
| 2026-04-19 | 버전 | 1.6.1 → 1.6.2 | Step 2 재설계 + WIP 정리 (patch) |
| 2026-04-19 | 하네스 단순화 P0 | 마찰 회수 6단계 일괄 적용 | (1) pre-check 연속수정 차단·경고 제거 — 카운트만 stdout으로 유지 (2) contamination 셸 검출 제거 + rules/contamination.md 삭제, review.md "오염 검토" 카테고리로 이전 (3) commit Step 2 4지선다 폐기 → 자동 본문 갱신 보수 모드 (4) review prompt에 "전제 컨텍스트" 블록 + is_starter 자동 주입 (5) test-strategist 자동 호출 신호(needs_test_strategist/test_targets) 추가. 사용자 발언 "이러면 하네스 만드는 이유가 없잖아" 트리거 |
| 2026-04-19 | 버전 | 1.6.2 → 1.7.0 | 하네스 단순화 (minor — 차단 시스템 회수 + 신호 인터페이스 변경) |
| 2026-04-19 | MIGRATIONS.md 신설 | 다운스트림 마이그레이션 가이드 도입 — 버전별 자동/수동 액션·검증·회귀 위험 명세 |
| 2026-04-19 | harness-upgrade Step 9.5 추가 | upstream MIGRATIONS.md 읽고 수동 액션 표시. 대화형 처리 또는 WIP 자동 생성 |
| 2026-04-19 | downstream-readiness.sh 신설 | 다운스트림 자가 진단 — HARNESS·도메인 등급·매처·스킬 카테고리 silent fail 6개 항목 점검 |
| 2026-04-19 | settings.json 매처 추가 정밀화 | git commit -n* substring 매칭이 path에 commit 포함 시 오탐 → 'git commit -n ' 정확 매칭으로 한정 |
| 2026-04-19 | 버전 | 1.7.0 → 1.8.0 | 다운스트림 마이그레이션 자동화 인프라 (minor — 신규 스킬 단계·문서 포맷·진단 도구) |
| 2026-04-19 | pre-check.sh lint stdout 오염 수정 | $LINT_CMD 2>/dev/null → 2>&1 변수 캡처. 다운스트림 lint stdout이 신호 줄과 섞이는 silent 버그 해결. 사용자 발견 (test-pre-commit 12/21 보고) |
| 2026-04-19 | commit 스킬 푸시 섹션 강화 | is_starter: true 분기 + HARNESS_DEV=1 git push 명시. silent push 누락 차단 (incident starter_push_skipped) |
| 2026-04-19 | test-hooks.sh S1 추가 | starter pre-push 보호 회귀 케이스 |
| 2026-04-19 | 버전 | 1.8.0 → 1.8.1 | lint 오염 + push 보강 (patch — 회귀 수정) |
| 2026-04-19 | settings.json Bash matcher 광역 패턴 폐기 | 공식 문서 https://code.claude.com/docs/en/permissions 확인 결과 단일 *가 공백 포함 모든 문자 매칭 + "argument constraint fragile" 경고. 매처 7개 → 1개 (bash-guard.sh 단일 hook으로 통합) |
| 2026-04-19 | bash-guard.sh 신설 | jq 파싱 + 토큰 단위 검증 (공식 권장 패턴). git commit -n 정확 차단, 메시지 안 -n 통과. test-bash-guard.sh 13/13 |
| 2026-04-19 | test-hooks.sh 폐기 | bash glob 모사가 공식 matcher와 다름 → 거짓 안전감. test-bash-guard.sh가 실제 hook 입력 형식으로 검증 |
| 2026-04-19 | pre-check 핵심 설정 연속 3회 차단 복원 | 단순화 작업으로 사라진 차단을 settings.json·rules/·scripts/·CLAUDE.md에 한정 복원. [expand] 태그로 정당 확장 우회 |
| 2026-04-19 | 버전 | 1.8.1 → 1.9.0 | matcher 광역 패턴 폐기 (minor — 검증 모델 자체 교체) |
| 2026-04-19 | harness-upgrade README 보호 강화 | 사용자 전용 리스트에 README·CHANGELOG·.gitignore·docs/{decisions,incidents,WIP,guides}(sample 제외) 추가. "사용자 전용 파일 처리 규칙 (강행)" 섹션 신설 — confirm 없이 무조건 건너뜀. 다운스트림 README 덮어쓰기 방지 |
| 2026-04-19 | harness-upgrade MSYS path 변환 가드 | Git Bash가 `<ref>:<path>` 인자를 Windows path로 자동 변환 (`<ref>\main;<path>`) → fatal 에러. 모든 `git show <ref>:<path>` 호출에 `MSYS_NO_PATHCONV=1` prefix 추가 |
| 2026-04-19 | incident matcher_false_block_and_readme_overwrite 기록 | 다운스트림 프로젝트 v0.7.0 업그레이드 중 3-way merge 명령이 구버전 매처에 오탐 차단. 증상 2건(매처 오탐 + README 덮어쓰기 위험) 근본 원인 공통(광역 매처 fragility) 분석 |
| 2026-04-19 | rules/hooks.md 신설 | argument-constraint 광역 매처 금지 규칙 (36줄). 공식 문서 인용 + bash-guard.sh 대안. 재발 방지 |
| 2026-04-19 | harness-upgrade Step 8.2 추가 | 구버전 starter 소유 hook(광역 매처) 다운스트림에서 감지·제거 제안. 사용자 커스텀은 보여주기만·수정 제안 X |
| 2026-04-19 | readiness argument-constraint 감지 | `Bash(... -X ...)` / `Bash(* --X...)` 패턴을 settings.json에서 전수 감지. 구버전 찌꺼기 자가 진단 |
| 2026-04-19 | staging 룰 1번 정밀화 | S9(critical) + 메타·문서 단독은 deep 강제 제외. docs-only 48k 토큰 과소비 사용자 실측 보고 기반 수정 |
| 2026-04-19 | review.md Read 상한 축소 | Stage 2: 3~5 → 0~3, Stage 3: 10+ → 상한 5. "과도한 Read 경계" 원칙 추가 |
| 2026-04-19 | MIGRATIONS MCP 다운스트림 최소화 가이드 | 전역 `~/.claude/settings.json`의 MCP 상속이 spawn 토큰 증가 요인. 프로젝트별 `.mcp.json`으로 분산 권장 |
| 2026-04-19 | 버전 | 0.7.0 → 0.7.1 | review 토큰 과소비 수정 + MCP 가이드 (patch) |
| 2026-04-20 | validate-settings.sh 신설 | Claude Code가 settings.json schema 에러 시 전체 schema를 응답으로 덤프(~20k tokens). 사용자 실측: 한 세션 2회 발생해 40k 허비. 사전 검증으로 재발 차단 |
| 2026-04-20 | auto-format.sh + readiness에 통합 | settings.json Write/Edit 후 자동 검증, readiness 자가 진단에도 추가 |
| 2026-04-20 | 버전 | 0.7.1 → 0.7.2 | settings.json schema 검증 자동화 (patch) |
| 2026-04-20 | review.md 전면 재작성 | "카테고리 설명"을 "diff 패턴 → 검증 행동" 매핑 9개로 전환. 각 패턴별 tool 선택·호출 횟수 명시. maxTurns: 6 frontmatter 상한 |
| 2026-04-20 | starter 자체 CPS 작성 | `docs/guides/project_kickoff_harness_starter_260420.md`. 이번 세션 내내 CPS 없이 작업 진행(하네스 자체 무너짐)이라 사용자 지적. P1~P5 정리, 기존 Solution 상태 기록. 다음 세션부터 implementation Step 0이 본 CPS와 대조 가능 |
| 2026-04-20 | review.md 9번 CPS 감지 패턴 | 새 도메인·규칙·스킬·에이전트 신설 시 CPS 갱신 누락 감지 [주의]. sample 외 실제 CPS 있을 때만 작동 |
| 2026-04-20 | 버전 | 0.7.2 → 0.8.0 | review·CPS 구조 변경 (minor — 검증 모델 자체 업그레이드) |
| 2026-04-20 | commit Step 7 병렬 호출 명시 강화 | review + test-strategist를 한 응답 메시지에 Agent tool use 2개 동시 배치하도록 강제. 순차 실행 유발 금지 패턴 명시 (분리 메시지·결과 대기·조건부 호출) |
| 2026-04-20 | Context7 MCP 폐기 권고 | 공식 HTTP API(https://context7.com/api/v2/libs/search, /context) 직접 curl 호출이 MCP보다 가벼움. 사용자 claude.ai 통합에서 Context7 해제 권장. MCP 없이도 public 라이브러리 조회 가능 (API key optional) |
| 2026-04-20 | docs/guides/external-research-patterns 신설 | Context7 HTTP·WebFetch·WebSearch 도구 선택 가이드. Context7 MCP 사용 금지 명시. internal-first.md에 포인터 추가 |
| 2026-04-20 | 버전 | 0.8.0 → 0.9.0 | 외부 조사 패턴 재정립 (minor — MCP 폐기 권고·가이드 추가는 새 인터페이스) |
| 2026-04-20 | rules/ 파일 다이어트 | 7개 파일 대폭 압축 (staging.md 49%↓, docs.md 55%↓, security.md 43%↓, self-verify.md 40%↓, no-speculation.md 42%↓, internal-first.md 25%↓, memory.md 소폭). 매 세션 시스템 프롬프트 용량 약 15KB 절감. 배경·자동 감지 상세·rotation 플레이북·탐색 절차는 docs/decisions·docs/guides로 분리 (LLM이 매 세션 읽을 필요 없는 메타·거버넌스) |
| 2026-04-20 | docs/decisions/staging_governance_260420 신설 | 폭증 차단 게이트·신호 추가 4질문·알려진 한계·pre-check stdout 스키마 분리 보관 |
| 2026-04-20 | docs/decisions/rules_metadata_260420 신설 | no-speculation·internal-first·security의 배경·자동 감지 패턴·2026-04-18 사고 참고 통합 보관 |
| 2026-04-20 | docs/guides/doc-search-protocol_260420 신설 | IDE 컨텍스트 힌트·"없다" 3단계·escalation 절차. doc-finder 에이전트와 메인 Claude가 탐색 시 참조 |
| 2026-04-20 | 버전 | 0.9.0 → 0.9.1 | rules 재구조화 + docs/ 3개 문서 신설 (patch — 행동 변경 없음, SSOT 이동과 압축) |
| 2026-04-20 | harness-upgrade 화이트리스트 | rules가 참조하는 `docs/guides/*`·`docs/decisions/*` 파일을 "하네스 파일 범위"에 명시 추가. v0.9.1 다운스트림에서 dead link 발생(rules/docs.md → doc-search-protocol_260420.md)한 실측 증상에 대응. 원칙(guides/decisions는 사용자 전용) 유지 + 화이트리스트 예외 도입 |
| 2026-04-20 | MIGRATIONS v0.9.1 섹션 추가 | 다운스트림이 rules 참조 문서 4개를 수동 복사하는 절차. 이전 버전 upgrade가 `docs/guides/*`를 이식 안 했기 때문에 v0.9.1에서 dead link가 필연적 발생 |
| 2026-04-20 | 버전 | 0.9.1 → 0.9.2 | harness-upgrade SKILL 수정 + MIGRATIONS 보강 (patch — dead link 회귀 수정) |
| 2026-04-20 | pre-commit-check.sh 격상 면제 | 룰 0a("메타·문서 단독은 도메인 등급 무시")가 1단계 stage 결정에서만 적용되고 2단계 격상(MULTI_DOMAIN + critical → deep)이 짓밟던 버그. IS_DOC_ONLY 변수 도입 — S5/S6 단독(코드/핵심설정/마이그레이션/빌드 미동반)이면 격상 면제. 다운스트림 c976255 측정에서 발견 (S6+S9 critical, 자동분류 deep → --quick 오버라이드 필요했음) |
| 2026-04-20 | staging.md 룰 A에 면제 명시 | "다중 도메인 hit + critical → deep 격상" 룰에 ※ S5/S6 단독은 면제 추가. 룰 0a 의도가 격상 단계까지 일관 |
| 2026-04-20 | 버전 | 0.9.2 → 0.9.3 | stage 격상 면제 버그 수정 (patch) |
| 2026-04-20 | 정보 흐름 누수 전수 조사 | 13 스킬·8 에이전트·11 스크립트 감사. 10건 누수 식별 (강 1·중 5·약 4). codebase-analyst 위임 결과를 docs/WIP/harness--info_flow_leak_audit_260420.md에 정리 |
| 2026-04-20 | Phase 1 — pre-check + commit + eval 누수 해소 | (1) pre-check stdout에 new_func_lines_b64 key 추가 (test-strategist 파일 재Read 방지) (2) commit Step 7에 메타 파일 본문 박기 규정 신설 (HARNESS.json·promotion-log·MIGRATIONS·INDEX 본문 인라인) (3) eval 4관점 에이전트 prompt에 Step 0/1 결과 인라인 주입 명시 |
| 2026-04-20 | Phase 2 — docs-manager 호출자 전달 규약 | docs-manager SKILL 상단에 trigger·intent·scope·files·context 5종 필드 규약 신설. commit·harness-upgrade·harness-init·harness-adopt 4개 호출자가 규약 따르도록 수정. 누수 #3·#5·#11 일괄 해소 |
| 2026-04-20 | WIP 후속 과제 2건 | (a) review 화이트리스트 자동 감지 (rules → docs 참조 시 harness-upgrade SKILL 화이트리스트 등록 여부) (b) implementation 스킬 재정의 (라우터·추적자로 역할 좁히기) |
| 2026-04-20 | 버전 | 0.9.3 → 0.10.0 | 정보 흐름 규약 도입 (minor — 다운스트림 호출자가 새 규약 따라야 함) |
| 2026-04-20 | implementation 스킬 라우터 재정의 | TRIGGER/SKIP 재작성(승인 표현 6종 + 연속 작업 재발화), "고유 책임 / 위임 대상" 표 신설, 규모·위험도 분기(Step 0.7), Step 2.5 실행 흐름(라우팅만), 실패·escalate 흐름. 159→245줄 |
| 2026-04-20 | 핸드오프 계약 SSOT 도입 | implementation/SKILL.md "## 핸드오프 계약 (SSOT)" 섹션이 4축(Pass/Preserve/Signal risk/Record) + 3기호(⛔/⚠️/🔍) 정의. 하류 스킬·에이전트는 상속 |
| 2026-04-20 | commit·review·test-strategist 계약 상속 | commit/SKILL.md 서두에 "고유 책임/위임 대상" 표 + 핸드오프 계약(상속) 표. review.md "## 경계" 표 신설(eval 위임 SSOT) + 핸드오프 계약 표. test-strategist.md "호출 전제"→"입력 계약" 승격. review 반복 "→ /eval" 위임 화살표 10건 제거 |
| 2026-04-20 | commit L419-476 부분 압축 | test-strategist prompt 본문 17줄→9줄, test-strategist.md "## 입력 계약" 참조로 대체. self-containment 원칙 유지(L56-162 호출 규약은 commit 고유 실행 로직이라 포인터화 취소 — advisor 판정) |
| 2026-04-20 | 버전 | 0.10.0 → 0.11.0 | 스킬·에이전트 구조 변경(minor — 다운스트림이 자기 커스텀 스킬에 핸드오프 계약 표를 박아야 함) |
| 2026-04-20 | review 출력 포맷 SSOT 통일 | commit→review 형식 충돌 해소. review.md "## 출력 형식"은 markdown + `verdict: pass\|warn\|block` 첫 줄 필수. commit/SKILL.md는 verdict 값으로 분기(기존 `block: true/false` JSON 파싱 코드 제거). 실측 배경: review 에이전트가 JSON vs markdown 이중 지시로 중간 보고 후 종료(tool_uses 7·11). 10쌍 중 이 1쌍만 충돌 — codebase-analyst 전수 조사 |
| 2026-04-20 | review 입력 크기 3단계 분기 | 0~2000줄 전체 / 2001~5000줄 stat+head 2000 / 5001줄+ stat만+파일별 Read 지시. 기존 2000줄 단일 가드만 있던 구간을 명문화 |
| 2026-04-20 | threat-analyst 에이전트 신설 | 외부 공격면 전담 specialist (GitHub public·클라이언트 번들·전직자 클론 가정). 6시나리오: git history 시크릿·공개 docs 노출·클라이언트 env inline·CORS/CSP·service_role 브라우저 경로·admin/debug 가드. codebase-analyst(내부) ↔ threat-analyst(외부) 대칭 관계. 189줄 |
| 2026-04-20 | specialist 공통 산출물 자가 평가 블록 이식 | 6 specialist(researcher·codebase·risk·threat·performance·test-strategist)에 1~5점 평가(근거강도·커버리지·실행가능성·사각지대·종합) 일괄 이식. 점수 기준 specialist별 명시(근거 유형별 5/4/3/2/1 대응). LLM-as-Judge 5축(Anthropic) 대응 |
| 2026-04-20 | researcher 업계 탑 인물 반영 + 캐시 운용 | `.claude/rules/external-experts.md` 빈 템플릿 신설. researcher가 조사 시 캐시 조회 → 없으면 1회 메타 검색으로 1~2명 식별·자료 수집(최대 2 소스)·캐시 자동 추가. 신뢰 3단계(최초 식별→다회 사용됨→사용자 확정). 첫 실전 호출로 5명 등록(Larson·Fournier·Majors·Nygard·Fowler) |
| 2026-04-20 | eval 4관점 advisor 이관 | eval/SKILL.md L317-432(115줄) → advisor 호출 섹션(70줄)으로 대체. 4관점 → 4 specialist 1:1 매핑(risk/researcher/codebase/threat). Step 0/1 결과를 advisor prompt에 인라인 전달(누수 #6 해소 유지). 508 → 458줄 |
| 2026-04-20 | advisor 판단 엔진 전면 재설계 | 단순 "종합 기계"에서 판단 엔진으로 승격. 6단계 Orchestration + 의사결정 프레임 6개 라이브러리(Weighted Matrix·Pre-mortem·Trade-off·Expected Value·ADR·Reversibility) + 주제별 매핑표 + Specialist 응답 구조 사전 인지표 + 6단계 충돌 해소 tie-breaker + 판단 경로·뒤집힐 조건 필수. 171 → 334줄. researcher 외부 조사 기반(Nygard·Fowler·Larson·Majors·Fournier + Anthropic Lead-Subagent·LLM-as-Judge·Implicit Consensus) |
| 2026-04-20 | 버전 | 0.11.0 → 0.12.0 | 스킬·에이전트 구조 변경(minor — 다운스트림이 자기 커스텀 스킬에 자가평가 블록 이식·advisor 판단 엔진 호출 패턴 대응 필요) |
| 2026-04-20 | P0-3 harness-adopt 핸드오프 이식 | harness-adopt/SKILL.md 서두에 "고유 책임 / 위임 대상 / 핸드오프 계약(상속)" 3 섹션 이식. 본문 Step 1~9 변경 없음. 498→542줄. 줄수 감축은 실측 후 재평가로 보류 |
| 2026-04-20 | P1-1 advisor 스킬 슬림화 | advisor/SKILL.md 79→43줄. "흐름 Step 1~3 나열"·"핵심 원칙 5줄" 제거(에이전트 SSOT 중복). description TRIGGER/SKIP이 SSOT. 감사 목표 ~40줄 달성 |
| 2026-04-20 | SSOT 우선·분리 판단 원칙 규칙화 | 본 세션에서 "harness-adopt 이식용 WIP를 감사 문서와 중복 생성"한 실수를 규칙으로 코드화. rules/docs.md "## SSOT 우선 + 분리 판단" + "## 완료 문서 재개" 신설(106→143). implementation Step 0.8 신설(WIP 생성 여부 판단을 규모 분기 Step 0.7과 분리. 245→267). docs-manager `--reopen` 모드 + Step 2.5 신설(263→271). 단순 지표(규모 hit) 판단 금지, 분리 필요성은 판단 기준으로 결정 |
| 2026-04-20 | 버전 | 0.12.0 → 0.13.0 | 워크플로 규칙 추가(minor — 다운스트림이 Step 0.8 분기·rules/docs.md 신규 섹션·docs-manager --reopen 플로우 적용 필요) |
| 2026-04-19 | 버전 | 1.9.0 → 0.7.0 | **다운그레이드.** 사용자 지적: "수정한거와 실제 내용 꼬라지에 비해 버전이 너무 높다, 오류 투성이가 무슨 1.8.0이 넘냐". 정당함 — 이번 세션만 추측 수정 3회·매처 갈아엎기·12커밋 push 누락. semver 0.x = "공개 API 불안정·실험 단계"가 현재 상태와 정확히 일치. 다운스트림 실측 누적·매처 동작 충분 검증·README 격차 안정화 등이 누적된 후에 1.0.0 검토. |
