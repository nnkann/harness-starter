---
title: 승격/강등 이력
domain: harness
tags: [promotion, rule-change]
relates-to: []
status: completed
created: 2026-04-08
---

# 승격/강등 이력

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
