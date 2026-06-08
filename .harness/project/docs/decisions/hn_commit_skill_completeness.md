---
title: commit 스킬 cp_{slug}.md 박제 누락 + 메타 파일 갱신 병렬화
domain: harness
problem: P11
s: [S11]
tags: [commit-skill, cps-cascade, parallel-meta-update, wip-sync]
status: completed
created: 2026-05-18
updated: 2026-05-18
---

# commit 스킬 cp_{slug}.md 박제 누락 + 메타 파일 갱신 병렬화

## Goal

commit 흐름의 동형 패턴 잠복 결함 정비. P11 직격 — wave 박제 6개 위치
(P# 표·S# 표·P# 본문·decision·case·cluster) 중 **case (cp_{slug}.md)
자동 박제 부재**로 매 wave 박제 누락 위험. 추가로 cps_add 명령이 표 형식
갱신 안 함.

**Acceptance Criteria**:
- [x] Goal: S11 (동형 후보 위치 자동 탐색 + 단일 진입점 강제) 충족 — commit 흐름이 P# 신설 wave 박제 시 cp_{slug}.md 동반 staging 누락을 결정적으로 차단하고, cps_add 명령이 표 형식까지 갱신한다
  검증:
    tests: python -m pytest .claude/scripts/tests/test_pre_commit.py::TestCpsNewProblemCaseGate .claude/scripts/tests/test_pre_commit.py::TestCpsAddTableInsert -q
    실측: P# 신설 staged인데 cp_*.md 동반 staged 없으면 pre-check 차단 메시지 1줄 출력
- [x] **cp_{slug}.md 누락 차단** — `pre_commit_check.py`에 게이트 추가: staged diff에 `project_kickoff.md`의 `| P\d+ |` 신규 행 추가가 있고 `docs/cps/cp_*.md` 신규 파일이 staged에 없으면 차단. 회귀 테스트 3건 (TestCpsNewProblemCaseGate)
- [x] **cps_add P# 표 갱신** — `cmd_cps_add`가 `## Problems` 표 마지막 `| P\d+ |` 행 뒤에 새 P# 행 삽입. S# 표는 본 wave 범위 밖. 회귀 테스트 1건 (TestCpsAddTableInsert)
- [x] **wip-sync에 cp 박제 흡수는 별 WIP** — 본 wave 범위 밖. P# 신설 wave에서 case 본문은 사용자/LLM 박제 필요 (자동 생성 시 본문 환각 위험). 누락 차단만으로 충분
- [x] **메타 파일 병렬화는 별 WIP** — 본 wave 범위 밖. 시간 절감은 부차적, 누락 차단이 본 wave 본질

## 결정 사항

- **본 wave = 누락 차단만**. 자동 생성·병렬화는 분리 (사용자 지적: "병렬화는 시간 절감, 누락 차단은 정확성. 후자가 본 wave 노출 결함의 본질")
- 별 wave 후보 (본 WIP 메모): wip-sync cp 박제 흡수, 메타 파일 갱신 병렬화

## 메모

- 노출 흐름: 754b73c (P12 박제) → cp_{slug}.md 누락 → 2ef5406 (cp 후속 박제). 2회 commit
- cps_add 결함 발견: 헤더만 append, 표 형식 미갱신. 본 wave 박제 시 수동 Edit 3회 발생
- P11 본질 적용: "wave 박제 N곳 분산 → 1곳 갱신 시 나머지 후보 자동 탐색 부재". 본 결함이 P11 정의에 정확히 부합
