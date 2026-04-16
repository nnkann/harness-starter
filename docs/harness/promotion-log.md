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
| 2026-04-16 | 버전 | 0.9.2 → 0.10.0 | 메타데이터 구조 변경 (minor) |
