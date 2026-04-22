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
| 2026-04-21 | 0.16.0 → 0.16.1 | [incidents/hn_review_maxturns_verdict_miss.md](../incidents/hn_review_maxturns_verdict_miss.md) | `/commit --bulk` 플래그 신설 — 거대 일괄 변경 시 review(maxTurns 6) 대신 정량 가드 4종(test-pre-commit·test-bash-guard·downstream-readiness·파일명/참조 정합성)으로 대체. `bulk-commit-guards.sh` 신설 + staging.md Stage bulk 추가 + commit SKILL Stage 분기 + pre-check 대규모 감지 경고. 가드 실패 시 즉시 차단(우회 불가). patch — 신 플래그 도입, 기존 동작 불변 |
| 2026-04-21 | 0.16.1 → 0.17.0 | [decisions/hn_review_staging_rebalance.md](../decisions/hn_review_staging_rebalance.md) | review staging 5줄 룰 — 기존 16줄 Stage 결정 룰을 경로 기반 이진 판정 5줄로 전면 대체(업스트림 22 deep 중 41% 과잉 해소). 룰 1 `.claude/scripts|agents|hooks|settings.json`→deep · 룰 2 S1 line/S14/S8→deep · 룰 3 docs 대량 rename→bulk · 룰 4 S5/S4 단독→skip · 룰 5 나머지→standard. 다중 도메인 격상(룰 A) 폐기 — 5줄 룰이 커버. pre-commit-check.sh RECOMMENDED_STAGE 블록 교체 + test-pre-commit.sh T21~T32 12 케이스 추가(clone 시 로컬 스크립트 cp 보정). minor — staging 판정 로직 전환 |
| 2026-04-21 | 0.17.0 → 0.17.1 | [decisions/hn_review_tool_budget.md](../decisions/hn_review_tool_budget.md) | review 에이전트 tool call 예산 재설계 — 기존 "3관점(회귀·계약·스코프)"을 "계약·스코프 2축 + 회귀 알파(S7·S8 hit 시만)"로 재구성. 실측 warn 6건 축 분포 기반(계약 50%, 스코프 33%, 회귀 0%). 신호별 알파에 **발동 조건** 열 추가 — "신호 hit + 조건 충족" 둘 다일 때만 실행(고정 매핑 아님). **조기 중단 모든 stage 허용** — 필수 단계(micro=계약, standard=계약+스코프, deep=계약+스코프+알파) 완료 후 의심점 없으면 종료. maxTurns 6 유지 + 5회 이후 여유 1회 보존. 출력 템플릿에 조기 중단 응답 형식 신설. patch — 심도 로직 재구성, 신호 매핑·스킵 조건 재정의, 기본 동작 호환 |
| 2026-04-21 | 0.17.1 → 0.18.0 | [decisions/hn_pipeline_design_rule.md](../decisions/hn_pipeline_design_rule.md) | pipeline-design 규칙 업스트림 이식 — 다단 처리 파이프라인(ETL·ML·에이전트 체인·빌드 등) 설계·재편 시 **상류 신호 재사용**과 **하류 보존 책임**을 7항목 체크리스트로 강제. 다운스트림 한 달 재편에도 못 본 설계 실수("좋은 도구 한 번 쓰고 버림"·"상류 출력 암묵적 폐기") 방지 목적. `.claude/rules/pipeline-design.md` 신설(~120줄, 범용 버전 + 프로젝트 고유 사례 로컬 섹션) + CLAUDE.md `<important if>` 트리거 + self-verify 체크리스트 연계 항목 + hn_rules_metadata에 섹션 추가 + docs/incidents/hn_pipeline_design_rule_origin.md 사료 기록. **review 자동 감지 패턴은 미도입** — 의도 설계 문제는 diff 키워드 매칭 어려움·오탐 다수, rule + self-verify로 충분(v0.17.x 축소 방향과 정합). minor — 신규 rule 도입 |
| 2026-04-22 | 0.18.0 → 0.18.1 | [incidents/hn_test_isolation_git_log_leak.md](../incidents/hn_test_isolation_git_log_leak.md) | T13.1 다운스트림 격리 실패 fix — 고정 파일명 `docs/WIP/test--scenario_260419.md`가 다운스트림 repo 히스토리와 교차 오염 시 `git log -5` 기반 S10 카운트가 부풀려져 T13.1만 FAIL(44/45). 파일명을 PID + 에포크로 unique화(`test--scenario_$$_$(date +%s).md`). 운영 pre-check exempt regex 보강은 T13.2 max=2 체크를 깨뜨려 철회. A안 단독으로 45/45 통과 + S10 회귀 의미 보존. patch — 테스트 격리 fix, 운영 로직 무변경 |
| 2026-04-22 | 0.18.1 → 0.18.2 | [incidents/hn_test_isolation_git_log_leak.md](../incidents/hn_test_isolation_git_log_leak.md) | T13.1 재진단 — v0.18.1 fix(unique 파일명) 적용 후에도 다운스트림에서 exit 2 지속. unique 파일명이면 git history 교차 자체가 불가능한데도 실패 → **최초 가설(git log 교차)이 원인이 아니었음**. incident 문서 정정(status: in-progress, "원인 미확정" 자인) + 진단 훅 도입. `TEST_DEBUG=1 bash .claude/scripts/test-pre-commit.sh`로 T13 FAIL 시 캡처된 pre-check stdout+stderr를 dump해 exit 2 직접 원인 관찰 가능. A안(unique 파일명)은 "경로 교차 리스크 봉쇄" 근거로 유지. patch — 진단 인프라 추가, 운영 로직 무변경 |
| 2026-04-22 | 0.18.2 → 0.18.3 | [incidents/hn_test_isolation_git_log_leak.md](../incidents/hn_test_isolation_git_log_leak.md) | T13.1 원인 확정 — 다운스트림 TEST_DEBUG dump로 `npm run lint`가 `'eslint' is not recognized`·`'next' is not recognized` ENOENT로 exit 2 확인. node_modules 누락/PATH 문제가 진짜 원인. T13이 유일하게 exit_code를 직접 체크하는 구조라 린터 실패가 "T13 고유 버그"로 가시화됐을 뿐, 스위트 전체가 린터 실패 환경에서 돌던 중. pre-commit-check.sh 린터 단계에 **B-3 fix**: ENOENT 패턴(`is not recognized`·`command not found`·`No such file or directory`·`Cannot find module`·`ENOENT`) 감지 시 **warn + skip**(환경 문제), rule 위반은 기존대로 차단(ERRORS++). incident 전면 재작성(제목·결론·교훈), status: in-progress → completed. patch — 린터 호출 방어 로직, 기존 rule 위반 차단 동작 불변 |
| 2026-04-22 | 0.18.3 → 0.18.4 | [incidents/hn_lint_enoent_pattern_gaps.md](../incidents/hn_lint_enoent_pattern_gaps.md) | v0.18.3 린터 ENOENT 패턴 정교화 — 다운스트림 review가 upstream MIGRATIONS.md 단정(`ESLint 출력과 겹치지 않음`)을 역으로 검증해 오탐·OS 커버리지 갭 지적. **오탐 제거**: `No such file or directory`·`Cannot find module`·`ENOENT`는 ESLint 내부 crash와 구분 불가 → 패턴에서 삭제(rule 위반처럼 차단 유지). **OS 커버리지 확장**: zsh(`command not found: X$`)·Alpine(`exec: X: not found$`)·Dash(`sh: N: X: not found$`)·pnpm(`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`) 5개 추가. T33·T34 회귀 테스트(12 케이스) 신설 — 패턴 SSOT는 ENOENT_PATTERN 변수로 pre-commit-check.sh와 test 동기화. 실측 과정에서 다운스트림 제안 A안의 zsh 형식 갭도 T33.3이 잡음. no-speculation.md에 "MIGRATIONS 회귀 위험 섹션 작성 원칙" 추가(`겹치지 않음` 같은 단정 금지). patch — 린터 경계 로직 정교화, 기존 rule 위반 차단 동작 불변 |
| 2026-04-22 | 0.18.4 → 0.18.5 | [harness/hn_search_and_completion_gaps.md](../harness/hn_search_and_completion_gaps.md) | SSOT 선행 탐색 3층 방어 구조화 — v0.18.4 커밋 직후 Claude가 기존 SSOT 3건(`hn_review_staging_rebalance`·`hn_review_tool_budget`·`hn_staging_followup`) 존재 상태에서 중복 WIP 즉흥 생성. 사용자 지적으로 재발 패턴 자인. **3층 방어 정렬**: (1) `CLAUDE.md` `<important if>` 블록 추가 — 경로 불문 트리거(스킬 발동 여부 무관). (2) `.claude/rules/docs.md` "SSOT 우선 + 분리 판단" 섹션에 3단계 탐색(cluster 스캔 → 키워드 grep → 후보 본문 Read) + 실패 모드 체크리스트 5개 + "기본값은 기존 SSOT 갱신" 명문화. (3) `write-doc/SKILL.md` Step 2 docs.md 참조로 축약(중복 제거), `implementation/SKILL.md` Step 0.8에 3단계 탐색 명시 인용. 원칙: 절차는 docs.md 한 곳에만, 스킬·CLAUDE.md는 참조·트리거만. `hn_search_and_completion_gaps.md` Part E 신설(재개), `hn_staging_followup.md`에 경과시간 체감 축 추가. patch — 규정·스킬 정합성 강화, 새 동작 도입 없음 |
| 2026-04-22 | 0.18.5 → 0.18.6 | [WIP/harness--hn_search_and_completion_gaps.md](../WIP/harness--hn_search_and_completion_gaps.md) | dead link 검사 pre-check 이식 — v0.18.5 review deep이 30초 걸려 잡은 cluster dead link를 pre-check이 수 초에 잡는다. `pre-commit-check.sh` Step 3.5 신설: (A) 삭제·rename된 md를 가리키는 기존 링크 감지 (basename grep, 같은 커밋 소스는 skip), (B) 추가·수정된 md의 새 링크 대상 존재 검증 (staged diff의 + 라인만 awk로 추출, 경로 정규화 + test -f). 증분 검사 원칙 — 전수 검사는 `bulk-commit-guards.sh` 4b 유지 (거대 일괄 전용). T35 회귀 테스트 3케이스 신설 (삭제 cluster dead / 새 md broken link / 링크 대상 동반 staged). 60/60 통과. 원칙: 정적 정합성은 pre-check, 의미는 review (staging.md 설계 복구). patch — pre-check 새 검사 블록 추가, 기존 동작 불변 |
| 2026-04-22 | 0.18.6 → 0.18.7 | [WIP/harness--hn_search_and_completion_gaps.md](../WIP/harness--hn_search_and_completion_gaps.md) | 스킬 파일명 규약 드리프트 정리 (Part E 구멍 2 부분 처리) — naming.md "날짜 suffix 전면 금지" 규정이 6개 스킬 예시·템플릿에 반영 안 됨. implementation Step 1·naming-convention 계획 문서·commit Step 2.3·docs-manager Step 2.5·317 예시에서 `{대상폴더}--{작업내용}_{YYMMDD}.md` → `{대상폴더}--{abbr}_{slug}.md` + "날짜 suffix 전면 금지" 명시 + naming.md 참조 추가. 예시 날짜(260330·260416) → slug 이름(`hn_auth_stack` 등)으로 교체. harness-init/adopt/upgrade의 세션·마이그레이션 파일(session_{YYMMDD}·migration_v{X}_{YYMMDD})은 "같은 주제 반복" 원칙과 충돌 가능해 **실측 대기**(깊은 판단 필요). patch — 문서 규약 드리프트 정리, 기존 동작 불변 |
