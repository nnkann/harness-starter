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
