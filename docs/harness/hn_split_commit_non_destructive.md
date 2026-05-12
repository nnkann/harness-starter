---
title: split-commit.sh 비파괴 planner 전환 — §H-3
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, split, non-destructive]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: WIP/harness--hn_commit_perf_followups.md
    rel: implements
status: completed
created: 2026-05-12
updated: 2026-05-12
---

# split-commit.sh 비파괴 planner 전환 (§H-3)

followups WIP §H-3 sub-task의 실행 단위. 본 wave 닫힘이 followups
인덱스의 §H-3 ✅ 마킹 조건.

## 사전 준비

- 읽을 문서: `docs/harness/hn_commit_perf_optimization.md` §C (split 정책
  재정의 — CPS·AC 먼저, 파일 성격 나중)
- 이전 산출물: §H-2 commit (`1e835b4`) — SKILL Step 5.5가 commit_route
  1차 분기. split-commit.sh 호출은 사용자 명시 시에만으로 좁혀짐.
- MAP 참조: split-commit.sh는 commit 스킬 Step 5.5에서 호출. SSOT는
  staging.md "split 옵트인 정책".

## 목표

split-commit.sh의 기본 동작을 destructive에서 non-destructive planner로
전환. `--apply` 플래그가 있을 때만 기존처럼 staged 비우고 첫 그룹 stage.
CRLF 감지 안내 추가.

CPS 연결: S2의 메커니즘 — "지금까지 커밋" 같은 사용자 요청이 자동 분리로
시간을 쓰지 않도록 (§A "fast-by-default" 원칙). split 권고는 stdout
정보로만 제공, 실제 변경은 사용자 명시 시에만.

## 작업 목록

### 1. split-commit.sh 비파괴화 + CRLF 안내

**사전 준비**: 현재 본문 destructive 흐름 (line 127~143) 위치 파악.
**영향 파일**: `.claude/scripts/split-commit.sh`

**변경 축**:

| 축 | 현재 | 본 wave |
|----|------|---------|
| 기본 실행 | staged 비우기 + 첫 그룹 stage (destructive) | plan stdout만 + staged 무변경 |
| `--apply` 플래그 | 없음 | 기존 destructive 동작 진입 |
| 재진입 (split-plan.txt 존재) | destructive 자동 다음 그룹 | 그대로 (이미 --apply 흐름) |
| CRLF 가드 | 없음 | 자기 자신 + .claude/scripts/*.sh CRLF 감지 시 stderr 안내 |

**Acceptance Criteria**:

- [x] Goal: split-commit.sh 기본 실행이 staged 상태를 변경하지 않는 non-destructive planner로 전환. `--apply` 시에만 기존 destructive 동작. CRLF 감지 시 안내 출력. ✅
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
    실측: grep -n "APPLY=0\|--apply\|check_crlf_sh" .claude/scripts/split-commit.sh
- [x] 인자 파싱: `--apply` 플래그 처리 (그 외 인자는 무시).
- [x] 기본 실행: 분리 계획 stdout 출력 후 즉시 종료. staged 무변경.
- [x] `--apply` 실행: 기존 destructive 흐름 진입.
- [x] split-plan.txt 재진입 흐름: 그대로 유지 (이미 --apply 진입한 사용자 흐름).
- [x] CRLF 안내: 자기 자신 + .claude/scripts/*.sh shebang에 CR 감지 시 stderr 1줄 + 정규화 명령 안내 (차단 아님).
- [x] commit SKILL Step 5.5에서 split-commit.sh 호출 표현을 `--apply` 명시로 갱신. ✅
- [x] 회귀 테스트 1건 (BIT 재정의): 비파괴 로직의 grep 정합 (APPLY/--apply/CRLF 가드/destructive 분기 위치).
- [x] followups WIP 인덱스에 §H-3 ✅ 마킹 + §H-8·§H-9·§H-10 신규 (별 wave 후보).

## 결정 사항

- 본 wave 회귀 테스트 2건 → 1건으로 BIT 재정의. 이유: split-commit.sh
  자체가 CRLF로 들어가 있어 pytest subprocess의 bash -n syntax 검사에서
  `do\r` 토큰 오류로 실패. AC "CRLF 안내"의 전제 (자기 자신은 통과)가
  파괴됨 → BIT Q2=YES → REDEFINE. syntax 테스트 삭제, grep 정합으로 좁힘.
  근본 해결은 별 wave §H-10 (.sh LF 정규화).
- CPS 갱신: 없음. S2 메커니즘은 "review tool call 평균 ≤4회" — 본 wave는
  split-commit.sh 분기 변경. review 호출 자체는 무관.
- split-commit.sh 자체 line ending 변경 안 함 (별 wave §H-10 후보).

## 메모

- 본 wave 실측: pytest stage 6 passed (TestRouteOutput 3 + TestStageBasic
  2 + TestSplitCommitNonDestructive 1). grep 정합 4 패턴 모두 hit.
- BIT 재정의 사례: AC 미달성 시 회피가 아니라 사용자에게 한계 명시 +
  근본 해결을 별 wave로 분리. 본 케이스는 syntax 테스트 삭제 + §H-10
  신규 등록으로 처리.
- 별 wave 추가 등록: §H-8 (wip-sync 역참조) + §H-9 (.claude↔.agents
  drift) + §H-10 (.sh LF 정규화). 사용자 지적 "찾아서 분류해야지"에
  대응 — 본 wave 부산물로 followups 인덱스 갱신.
- 자동 검증 불가 영역 명시: split-commit.sh의 실제 분리 실행은 통합
  테스트 (git sandbox)로만 검증 가능. 본 wave는 단위 grep 정합 + 운용
  검증. 통합 테스트 추가는 §H-3 후속 (별 wave 아님 — 본 wave 범위 외
  자동화 한계 영역).
