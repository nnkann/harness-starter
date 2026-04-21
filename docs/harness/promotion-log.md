---
title: 승격/강등 이력
domain: harness
tags: [promotion, rule-change]
relates-to:
  - path: archived/promotion-log-2026q2-early.md
    rel: supersedes
status: completed
created: 2026-04-08
updated: 2026-04-20
---

# 승격/강등 이력

> **운영 규칙 (B+D 압축 + 분기 롤링)**:
> - 버전 범프 행 **한 줄** 기록 (날짜·이전→이후 버전·minor/patch 근거)
> - 세부 규칙 변경은 **해당 `decisions/`·`harness/` 문서 포인터만**
> - 분기 경계에서 `archived/promotion-log-YYYY-q{N}-{suffix}.md`로 이동
> - 본 파일은 항상 최신 분기만 담는다. 경량 유지 목표 50행 이내.
>
> 상세 규칙: commit 스킬 Step 3 "한 줄 기록 원칙".

## 아카이브

- 2026 Q2 초반 (2026-04-08 ~ 2026-04-20, 152행): [archived/promotion-log-2026q2-early.md](../archived/promotion-log-2026q2-early.md)

## 현재 이력 (2026-04-20 ~)

| 날짜 | 버전 | 근거 문서 | 비고 |
|------|------|----------|------|
| 2026-04-20 | 1.9.0 → 0.7.0 | (아카이브 참조) | 다운그레이드 — semver 0.x 실험 단계 정렬 |
| 2026-04-20 | 0.7.0 → 0.12.0 | (아카이브 참조) | 0.7.0 이후 누적 변경. 정보 흐름 규약·implementation 라우터·핸드오프 계약 SSOT·threat-analyst 신설·advisor 판단 엔진 재설계 |
| 2026-04-20 | 0.12.0 → 0.13.0 | [decisions/hn_skill_agent_role_audit.md](../decisions/hn_skill_agent_role_audit.md) | P0-3 harness-adopt 핸드오프 이식 · P1-1 advisor 슬림화 · SSOT 우선·분리 판단 원칙 규칙화 |
| 2026-04-20 | 0.13.0 → 0.13.1 | (본 파일 + commit/docs-manager/review/threat-analyst) | 코드 SSOT 서더링 3건(위험도 게이트·차단 키워드·시크릿 패턴) + promotion-log B+D 압축(152→33줄, archived 백업) + review verdict 폼 수정(응답 순서 엄수·재호출 규정). patch — 기존 로직 정리·중복 제거 |
| 2026-04-20 | 0.13.1 → 0.13.2 | (pre-commit-check·bash-guard·session-start·stop-guard·commit SKILL) | hook 스크립트 성능 최적화 — bash-guard pre-check 2회 실행 제거 + commit Step 0 린터 조기 체크 신설 + pre-check git 호출 22→4회·SIGNALS bash 내장·awk 1패스(1953→850ms, -56%) + bash-guard·session-start·stop-guard 동일 기법. patch — 동작 불변, 체감 지연만 감소 |
| 2026-04-20 | 0.13.2 → 0.13.3 | [harness/hn_review_whitelist_autodetect.md](hn_review_whitelist_autodetect.md) | harness-upgrade 화이트리스트 → 동적 탐색. rules 본문에서 `docs/(guides\|decisions)/*.md` 참조를 grep으로 자동 추출해 이식 범위에 포함. 수동 등록 의무·dead link 재발 위험 원천 제거. patch — SSOT 일원화 |
| 2026-04-20 | 0.13.3 → 0.14.0 | [harness/hn_index_md_removal.md](hn_index_md_removal.md) | docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거. clusters/{domain}.md가 진입점 SSOT. 참조 14곳(rules·skills·agents·scripts) 정리 + README 갱신(v0.7.0 → v0.14.0, 14 keys, 30 케이스). minor — 탐색 흐름·다운스트림 구조 변경 |
| 2026-04-21 | 0.14.0 → 0.14.1 | [decisions/hn_memory.md](../decisions/hn_memory.md) | memory 재설계 1차 — `.claude/tmp/` 폐기 + `.claude/memory/` 흡수 + rules/memory.md 재작성(실제 Claude vs 프로젝트 memory 경계·3트리거·session-* snapshot 용도) + stop-guard 환기 1줄 + bash-guard에 tmp 차단 hook + external-experts에 Charles Packer. patch — 규칙 재작성·잔재 폴더 제거(동적 캐싱 로직은 커밋 2로 분리) |
| 2026-04-21 | 0.14.1 → 0.15.0 | [decisions/hn_memory.md](../decisions/hn_memory.md) | memory 재설계 2차 — commit 스킬 Step 5에 tree-hash 캐시 로직 도입(같은 staged 재commit 시 pre-check·diff 재사용) + push 성공 후 `session-*` 정리 소섹션 + `test-pre-commit.sh` T20 회귀 테스트(동일성·민감성·snapshot 생성 3케이스) + rules/bash-guard dead-link 보정 + WIP → decisions/ 이동. minor — 신기능(캐시 로직) 도입 |
| 2026-04-21 | 0.15.0 → 0.16.0 | [decisions/hn_doc_naming.md](../decisions/hn_doc_naming.md) | 문서 네이밍 전면 개편 — 도메인 약어 SSOT(naming.md) + 파일명 `{abbr}_{slug}.md` 통일 + 날짜 suffix 전면 폐기(incidents 포함) + clusters 자동 매핑 직교 파싱 규칙 + docs.md 핵심 원칙·탐색 재구성 + write-doc/docs-manager abbr 검증·`--validate` 약어 검사. 업스트림 문서 40개 일괄 rename + 본문 참조 173건 치환 + clusters/harness.md 재생성 + 기존 경로 오류 보정(hn_frontmatter_graph_spec·hn_improvement). minor — 파일명 체계 전면 전환·다운스트림 수동 액션 필요 |
