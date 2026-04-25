---
title: 커밋 프로세스 감사 — #18 false-negative 축 보강
domain: harness
tags: [commit, review, pre-check, audit, staging, split]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: decisions/hn_review_staging_rebalance.md
    rel: references
  - path: decisions/hn_review_tool_budget.md
    rel: references
  - path: harness/hn_commit_review_staging.md
    rel: extends
  - path: harness/hn_info_flow_leak_audit.md
    rel: extends
status: completed
created: 2026-04-22
updated: 2026-04-23
---

# 커밋 프로세스 감사 — 전체 판정 완료

2026-04-22 세션에서 `bulk` 폐기를 시작으로 커밋 프로세스 15+항목을
감사했다. 대부분(#1~#12·#14·#15 외)은 v0.19.0~v0.20.7에서 구현 완료.

**2026-04-23 세션에서 4건 판정 + 구현**: #13·#17·#18 논리 판정, #16
더미 시뮬레이션으로 구현까지 (v0.20.11).

완료된 항목의 근거는 git history로 조회:
```bash
git log --oneline --grep "(v0\.(19|20)\."
```

## 판정 요약

| # | 제목 | 상태 |
|---|------|------|
| #13 | review deep 과잉 판정 | ✅ **판정 D (현상 유지, 2026-04-23)** — 5건 실측 완료 |
| #16 | harness-init/adopt/upgrade 세션 파일명 규칙 | ✅ **판정 A (단일 파일 + 변경 이력, 2026-04-23)** — 더미 시뮬레이션·v0.20.11 구현 |
| #17 | staging S8 정밀화 + 폭증 게이트 | ✅ **S8 이미 완료** — 언어별 awk 1패스 구현 확인. 폭증 게이트는 트리거 대기 |
| #18 | 커밋 분리 자동화 판단 | ✅ **현 구조 유지** — 판정 제안 + 사용자 판단. 완전 자동화 마찰 증가 위험 |

---

### #13. review deep 과잉 판정 — **결론: D 현상 유지 (2026-04-23)**

#### 최종 실측 (5건)

| 커밋 | stage | tool calls | duration | verdict | 판정 |
|------|-------|-----------|----------|---------|------|
| v0.18.4 | deep | 4 | ~30s | pass | 과잉 |
| v0.18.5 | deep | 7 | ~60s | block→pass | **값어치** (cluster dead link) |
| v0.18.6 | deep | 재호출 80s+ | warn | — | 과잉 (참고 1건) |
| v0.18.7 | deep | 1 | ~27s | pass | 과잉 |
| fixture 실측 2026-04-23 | deep | **0** | **11s** | pass | 과잉 |

**5건 중 4건 deep 과잉 (80%)**. 값어치 1건(v0.18.5)의 cluster dead link는
v0.18.6에서 pre-check Step 3.5로 이식 → 이후 deep 실질 가치 감소.

5번째 실측은 scripts 수정 fixture에서 review 직접 호출 (조기 중단 설계가
실제 작동하는지 확인). tool calls **0회**, **11초**로 종료. v0.17.1의
"조기 중단 허용 + 필수 단계 완료 후 의심점 없으면 종료" 설계가 실제 작동.

#### 판정 D — 현상 유지

**근거**:
1. v0.17.1 조기 중단 설계 **실제 작동 확인**: fixture 실측 tool 0회·11초
2. `.claude/scripts/**` → deep 강제는 유지하되 실제 오버헤드 ~10~30초 수준
3. 값어치 있는 정적 검증(cluster dead link)은 pre-check로 이식됨. review는
   CPS 맥락 검증 가치 유지
4. 설계 공간 A/B/D 모두 명확한 우위 없음:
   - **A (scripts deep 완화)**: 조기 중단으로 이미 허용 가능한 오버헤드.
     값어치 놓칠 위험
   - **B (조기 중단 강화)**: 이미 v0.17.1에서 구현, 5번째 실측으로 작동 확인
   - **D (현상 유지)**: 최소 위험

#### 재검토 트리거

deep 평균 duration이 60초 이상 지속될 때 재평가. 현재는 ~10~30초 수준.

---

### #16. harness-init/adopt/upgrade 세션 파일명 — **판정 A (단일 파일 + 변경 이력, 2026-04-23)**

#### 더미 시뮬레이션 결과

3 시나리오(A 단일 파일 / B 날짜 suffix / C 순차 번호)로 탐색·파일 수·
SSOT 원칙 실측. **A 압도적 우위**:

| 축 | A (단일) | B (날짜) | C (순차) |
|----|----------|----------|----------|
| "현재 상태?" | 파일 1개 즉시 | sort -r | head | v_N 최대 |
| "2026-03 결정?" | grep 섹션 헤더 | 파일명 매칭 | 본문 grep |
| 파일 수 (N회 실행) | **1개** | N개 | N개 |
| naming.md 정합 | **예외 없음** | 예외 필요 | 예외 필요 |
| superseded 처리 | 자동 | 명시 관리 | 어려움 |

#### 구현 (v0.20.11)

- `harness-init/SKILL.md`: `project_kickoff.md` 단일. 재실행 시 `## 변경 이력` 누적
- `harness-adopt/SKILL.md`: `hn_adopt_session.md` 단일. 기존 파일명 정규화 섹션의
  "날짜 접미사 추가 제안"을 **제거 제안**으로 역전
- `harness-upgrade/SKILL.md`: `harness--migration_followup.md` 단일.
  버전 섹션(`## v{X}`)으로 본문 누적
- `implementation/SKILL.md`: glob `project_kickoff_*.md` → `project_kickoff.md`
- `MIGRATIONS.md`: v0.20.11 섹션 신설 + 기존 안내 호환 수정

**결론**: 외부 트리거(실 harness-adopt 실행) 대기 없이 더미 시뮬레이션으로
충분히 판정 가능. 과거 "실행 사례 대기" 차단 사유는 **잘못된 차단**이었음.

---

### #17. staging 신호 정밀화 — **S8 정밀화 이미 완료 확인 (2026-04-23)**

실측 결과:
- **S8 export 검출**: 이미 **언어별 시그니처 awk 1패스**로 구현됨
  (pre-commit-check.sh L519~535). TS/JS·Python·Go·Java 4개 언어 지원.
  문자열·주석 오탐 방지. T5·T6·T7·T8·T9·T10 6개 회귀 테스트 존재
- WIP 원문이 "휴리스틱 `grep -E '^[+-].*export'`"라 적었으나 실제 구현은
  오래 전에 정밀화됨. 기록 드리프트

**폭증 차단 게이트** (독립 항목):
- staging.md "신호 추가 4질문"·"연결 규칙 5케이스"는 텍스트 규범으로 유지
- pre-check 신호 수 13 초과 시 경고 로직은 **1인 운영 기준 후순위**. 실제
  신호 수 폭증 이슈 발생 시에만 착수

**결론**: #17 S8 정밀화 완료. 폭증 게이트는 트리거(신호 수 증가) 발생 시 재평가.

---

### #18. 커밋 분리 자동화 — **현 구조 유지 + 시간 축 경고 추가 (2026-04-23)**

#### 현 구현 (v0.20.4 → v0.21.0 보강)

- `task-groups.sh` — staged 파일을 task × abbr × kind 3축으로 그룹화
- `split-commit.sh` — 첫 그룹만 staged, 나머지는 `split-plan.txt`에 저장
- pre-check이 `split_action_recommended: split|single|sub` stdout 출력
- commit 스킬 Step 5.5가 `split` 값 받으면 `split-commit.sh` 호출 제안
- **사용자가 최종 판단** (single 강행 가능)
- **신규 (v0.21.0)**: `prior_session_files` 신호 — 이전 세션 잔여물이
  staged에 섞였을 가능성 경고. 자동 분리 아님 (아래 false-negative 축 참조)

#### 왜 완전 자동 분리 아님

이번 세션 실측에서 여러 번 `split` 권장을 **single로 우회**한 사례 존재:
- v0.20.4 rename fix (논리 단위 1개인데 그룹 2개로 쪼개짐)
- v0.20.5·0.20.6 분할 (bash-guard 수정은 논리 1개)

그룹화 알고리즘이 파일 경로 기반이라 **"논리 단위"와 어긋나는 경우**가
있음. 완전 자동 분리는 무의미한 쪼개기 유발 위험.

**판정: 현 구조(판정 제안 + 사용자 최종 판단)가 맞음**. 완전 자동화는
오히려 마찰 증가.

#### false-negative 축: 시간 축 누락 (2026-04-23 다운스트림 실측 보고)

3축(task × abbr × kind) 그룹화가 **시간 축(이전 세션 잔여 vs 현재 작업)**을
잡지 못한다. abbr/kind가 동일하면 이전 세션 잔여물과 현재 작업이 같은 그룹으로
묶여 `split=single` 출력.

**실측 근거**: 다운스트림에서 사용자 명시 개입 2회로 교정. SessionStart hook이
이미 unstaged를 보고하는데 그 신호가 split 입력에 활용되지 않음 (information flow
leak, `hn_info_flow_leak_audit.md` 누수 #10).

**대응 (경고 수준 채택, 자동 분리 아님)**:
- `session-start.sh`: SessionStart 시점 unstaged 목록을
  `.claude/memory/session-start-unstaged.txt`에 저장
- `pre-commit-check.sh`: staged와 교집합을 계산해 `prior_session_files` 신호 출력
- `commit/SKILL.md` Step 1: 신호 있으면 사용자에게 1줄 환기, 판단은 사용자

**task-groups.sh 미수정**: #18 false-positive(과쪼개기) 판정 유지. 시간 축을
그룹화 알고리즘에 넣으면 세션을 이어서 작업한 케이스에서 과쪼개기 재발.

**뒤집힐 조건**:
1. prior 경고가 2주에 1회 미만으로 무용지물이면 A·B·C 전부 기각
2. 경고 무시 학습 발생 시 자동 분리(B 강화) 재검토

#### 남은 실험 여지 (트리거 대기)

- **D (hunk 분리)**: `git add -p` 식 같은 파일 내 독립 주제 분리. 지금
  구현 규모 크고 효용 불확실. 사용자 명시 요청 시에만
- **E (속도 최적화)**: sub-커밋 stage 자동 재판정 — 이미 작동 중

#### 상위 SSOT

- `decisions/hn_review_staging_rebalance.md` (5줄 룰)
- `decisions/hn_review_tool_budget.md` (조기 중단)
- `incidents/hn_review_maxturns_verdict_miss.md` (bulk 폐기 근거)
- `harness/hn_commit_perf_optimization.md` (stage별 시간)
- `harness/hn_info_flow_leak_audit.md` 누수 #10 (prior_session 신호 배경)

---

## 완료된 항목 (v0.19.0~v0.20.7에서 구현)

감사 시작 시점(2026-04-22) 기준 15+ 항목 중 아래는 모두 완료. 세부는
commit 메시지 참조:

```bash
git log --oneline --grep "(v0\.(19|20)\."
```

- **#1** 린터 2회 → Step 5 통합 (v0.19.0)
- **#2·9** light/strict 모드 폐기, `--quick`/`--deep`/`--no-review` 단일화 (v0.19.0)
- **#3** 진척도 갱신 Step 2 → Step 7.5 **재배치(문서 위치)만** (v0.19.0) — ⚠️ bash 구현 없음 확정 (2026-04-25 실측). `hn_wip_completion_gap.md` 결함 B 참조
- **#4** `harness-version-bump.sh` 신설 (v0.20.0)
- **#5** session 캐시 3→1, tree-hash 캐싱 폐기 (v0.19.0)
- **#6** 메타 파일 본문 박기 섹션 삭제 (v0.19.0)
- **#7·#15** test-strategist 폐기 + 책임 이관 (v0.19.0)
- **#8** bash-guard `git commit` 강제 경유 (v0.20.0). 이후 v0.20.5~0.20.6에서
  이스케이프 단일화 + env prefix 매칭 버그 fix
- **#10** docs-manager 스킬 폐기 → `docs-ops.sh` 스크립트화 (v0.20.0)
- **#12** pre-check `relates-to.path` dead link 검사 (v0.19.0), basename
  과탐·경로 기준 불일치 근본 수정 (v0.20.0)
- **#14** pre-check stderr 기본 침묵, VERBOSE=1 가드 (v0.19.0)
- **#17 부분** S6 ≤5줄 skip 자동화 (v0.20.0)

## 세션 교훈 (감사 방법론)

- 감사·결정 문서는 **실측 없이 쓰면 추측의 집합**이 된다. no-speculation.md
  "단정형 추측 금지" 원칙이 감사 문서에도 적용
- specialist 호출(test-strategist, codebase-analyst)이 감사의 검증 장치로
  편입될 때 품질 향상 확인 (v0.20.7 promotion-log 폐기도 codebase-analyst
  전수 조사가 T30 공백·IS_STARTER orphan 발견)
- 완료 항목이 15건 쌓이면 본 문서 구조가 무거워짐. **완료 즉시 git log로
  위임하고 WIP에는 진행 중 항목만 유지**하는 규율 필요
