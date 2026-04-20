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
| 2026-04-20 | 0.12.0 → 0.13.0 | [decisions/skill_agent_role_audit_260420.md](../decisions/skill_agent_role_audit_260420.md) | P0-3 harness-adopt 핸드오프 이식 · P1-1 advisor 슬림화 · SSOT 우선·분리 판단 원칙 규칙화 |
| 2026-04-20 | 0.13.0 → 0.13.1 | (본 파일 + commit/docs-manager/review/threat-analyst) | 코드 SSOT 서더링 3건(위험도 게이트·차단 키워드·시크릿 패턴) + promotion-log B+D 압축(152→33줄, archived 백업) + review verdict 폼 수정(응답 순서 엄수·재호출 규정). patch — 기존 로직 정리·중복 제거 |
| 2026-04-20 | 0.13.1 → 0.13.2 | (pre-commit-check·bash-guard·session-start·stop-guard·commit SKILL) | hook 스크립트 성능 최적화 — bash-guard pre-check 2회 실행 제거 + commit Step 0 린터 조기 체크 신설 + pre-check git 호출 22→4회·SIGNALS bash 내장·awk 1패스(1953→850ms, -56%) + bash-guard·session-start·stop-guard 동일 기법. patch — 동작 불변, 체감 지연만 감소 |
| 2026-04-20 | 0.13.2 → 0.13.3 | [harness/review_whitelist_autodetect_260420.md](review_whitelist_autodetect_260420.md) | harness-upgrade 화이트리스트 → 동적 탐색. rules 본문에서 `docs/(guides\|decisions)/*.md` 참조를 grep으로 자동 추출해 이식 범위에 포함. 수동 등록 의무·dead link 재발 위험 원천 제거. patch — SSOT 일원화 |
| 2026-04-20 | 0.13.3 → 0.14.0 | [harness/index_md_removal_260420.md](index_md_removal_260420.md) | docs/INDEX.md 폐기 — 관리 드리프트 SSOT 제거. clusters/{domain}.md가 진입점 SSOT. 참조 14곳(rules·skills·agents·scripts) 정리 + README 갱신(v0.7.0 → v0.14.0, 14 keys, 30 케이스). minor — 탐색 흐름·다운스트림 구조 변경 |
| 2026-04-21 | 0.14.0 → 0.14.1 | [WIP/decisions--memory_redesign_260420.md](../WIP/decisions--memory_redesign_260420.md) | memory 재설계 1차 — `.claude/tmp/` 폐기 + `.claude/memory/` 흡수 + rules/memory.md 재작성(실제 Claude vs 프로젝트 memory 경계·3트리거·session-* snapshot 용도) + stop-guard 환기 1줄 + bash-guard에 tmp 차단 hook + external-experts에 Charles Packer. patch — 규칙 재작성·잔재 폴더 제거(동적 캐싱 로직은 커밋 2로 분리) |
