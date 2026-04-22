---
title: 커밋 프로세스 감사 잔여 — 실측 대기 4건
domain: harness
tags: [commit, review, pre-check, audit, staging]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: decisions/hn_review_staging_rebalance.md
    rel: references
  - path: decisions/hn_review_tool_budget.md
    rel: references
  - path: harness/hn_commit_review_staging.md
    rel: extends
status: in-progress
created: 2026-04-22
updated: 2026-04-23
---

# 커밋 프로세스 감사 — 실측 대기 잔여 4건

2026-04-22 세션에서 `bulk` 폐기를 시작으로 커밋 프로세스 15+항목을
감사했다. 대부분(#1~#12·#14·#15 외)은 v0.19.0~v0.20.7에서 구현 완료.
본 문서에는 **실측이 더 필요한 4건**만 남는다.

완료된 항목의 근거는 git history로 조회:
```bash
git log --oneline --grep "(v0\.(19|20)\."
```

## 남은 4건

| # | 제목 | 차단 이유 | 트리거 |
|---|------|----------|--------|
| #13 | review 2번 호출 구조 선택 (D/E/F) | 5커밋 실측 필요 (4건 확보, 1건 더) | 다음 warn 발생 커밋 |
| #16 | harness-init/adopt/upgrade 세션 파일명 규칙 | 실행 사례 없음 | 다음 harness-adopt 실행 |
| #17 | staging S8 정밀화 + 폭증 게이트 | #13 측정 결과 연동 | #13 완료 |
| #18 | 커밋 분리 자동화 판단 | #13 측정 5건 + perf 시간 로그 | #13 완료 + 성능 로깅 |

---

### #13. review 2번 호출 구조 — 실측 후 D/E/F 중 선택

**현 상태**: 1차 warn → 수정 → pre-check 재실행 → **2차 review 자동
호출**. 이번 세션 실측: 2차 review 30초 + 실질 이슈 0건 발견 빈번.

**사용자 원칙**: CPS 정합성 위험으로 2차 review 자동 호출 자체 생략 금지.
답은 "2번 돌아야 하는 상황 자체를 없애는" 것.

#### 설계 공간 (측정 후 선택)

- **D (warn 기준 재정의) — 가장 유력**:
  review가 "참고 1건"을 warn으로 분류 안 하고 pass 내 메모로 처리하면
  2차 review 자체 발생 안 함. 구현 위치: `.claude/agents/review.md`
  "## 출력 형식" + 판정 기준. pre-check 복잡도 증가 없음.

- **E (pre-check 재실행 건너뛰기) — 이미 있는 경로 실측 확인 필요**:
  `commit/SKILL.md` 응답 처리에 `verdict: warn → 경고 표시 후 진행`
  이미 존재. 실측 운영에서 이 경로 사용 빈도 기록 필요.

- **F (review 자체 분류) — B의 대안**:
  review가 warn에 "정적/의미론" 플래그 붙임. LLM 분류 일관성은 T35류
  회귀 테스트로 고정. D·E로 안 되면 검토.

#### 실측 누적 (4/5건)

| 커밋 | signals | stage | 실측 | 판정 |
|------|---------|-------|------|------|
| v0.18.4 | S2,S9,S10,S7 | deep | 4 calls, ~30s, pass | 과잉 |
| v0.18.5 | S2,S9,S10,S7 | deep | 7 calls, ~60s, block→pass | 값어치 (cluster dead link) |
| v0.18.6 | S2,S9,S10,S7 | deep | 재호출 포함 80s+, warn | 과잉 (참고 1건) |
| v0.18.7 | S9,S10,S7 | deep | 1 call, ~27s, pass | 과잉 |

**4건 중 3건 deep 과잉 (75%)**. 유일한 값어치 건(v0.18.5)의 cluster dead
link는 v0.18.6에서 pre-check Step 3.5로 이식 → 남은 deep 값어치 감소 예상.

**공통 패턴**: `.claude/scripts/**` 수정 → 5줄 룰 1 무조건 deep.

**1건 더 누적 후 결정**.

#### 해결책 후보 (측정 완료 후)

- **A**: `.claude/scripts/**` deep 강제 완화 — 회귀 테스트 동반 + 녹색이면 standard
- **B**: deep 내부 조기 중단 공격적 — tool_budget 원칙 강화
- **C**: review 병렬화
- **D**: 현상 유지 — "허용 범위"로 판정되면 개선 불필요

**영향 파일**:
- `commit/SKILL.md` 응답 처리 섹션 — 실측 기록 섹션 추가
- `.claude/agents/review.md` (D 채택 시)

#### 사각지대 (test-strategist 지적)

1. **v0.18.6 warn 원인 docs 미기록** → "반복 패턴" 확정 불가, 5건 필수
2. **CPS와 정적 검사의 교환 관계**: pre-check 확장은 정적 오류만. CPS
   맥락 이해는 review 담당. 의미론적 warn은 여전히 재호출 필요
3. **"사용자가 warn 받았을 때 정적/의미론 즉각 판단 가능" 전제 실측 없음**

---

### #16. harness-init/adopt/upgrade 세션 파일명 규칙

v0.18.7 일반 스킬은 `{abbr}_{slug}` 형식으로 정리 완료. 세션·마이그레이션
파일만 "같은 주제 반복" 원칙과 충돌해 판단 대기:

| 파일 | 쟁점 |
|------|------|
| `project_kickoff_{YYMMDD}.md` | 개시 시점 1회만. 단일 파일 가능? |
| `adopt-session_{YYMMDD}.md` | 이식 세션마다 독립 결정. 누적 vs 세션별? |
| `migration_v{X}_{YYMMDD}.md` | `{X}` 버전이 이미 분리 키. 날짜 중복? |

**판단 옵션**:
- A. 같은 주제 1파일 + `## 변경 이력` (naming.md 원칙 유지)
- B. naming.md에 "세션 리포트" 예외 조항 추가
- C. `session_{N}` 순차 번호

**트리거**: 다음 harness-adopt 실행 사례 관찰 후 결정. 선제 변경은
추측 수정 위험.

**영향 파일 (결정 후)**:
- `.claude/skills/harness-init/SKILL.md`
- `.claude/skills/harness-adopt/SKILL.md`
- `.claude/skills/harness-upgrade/SKILL.md`
- `.claude/rules/naming.md` (옵션 B 채택 시)

---

### #17. staging 신호 정밀화 잔여 — S8 + 폭증 게이트

v0.20.0에서 S6 ≤5줄 → skip 자동화 완료(T37). 잔여:

**S8 export 검출 정밀화**:
- 현재 휴리스틱 `grep -E '^[+-].*export'` — 문자열·주석에도 매칭
- 언어별 시그니처(TS export / Python def / Go func) 분리 검토

**폭증 차단 게이트 코드 강제 (장기)**:
- 현재 staging.md "신호 추가 4질문"·"연결 규칙 5케이스"는 텍스트 규범
- pre-check이 신호 수 13 초과 시 경고 로직 추가 검토
- 1인 운영이면 후순위

**트리거**: #13 5커밋 측정 결과에 따라 결정. "deep 과잉" 확정되면
S8 정밀화가 해결책(A·B) 중 하나로 선택됨.

**영향 파일**:
- `.claude/scripts/pre-commit-check.sh`
- `.claude/rules/staging.md` (신호 정의 갱신 시)

---

### #18. 커밋 분리 자동화 판단 — 측정 대기

#### 현 상태 (v0.20.4)

`task-groups.sh` + `split-commit.sh` 구현 완료(task × abbr × kind 3축).
rename 그룹 병합 버그(`--name-only` D+A 분리)도 v0.20.4에서 fix.

**남은 것**: 자동화 수준 결정 — 판정만 제안 vs 자동 분리 실행 vs
현상 유지(사용자 판단).

#### 관점

분리는 **거대 커밋 전용이 아니라 모든 커밋에 적용되는 글로벌 원칙**.
bulk 폐기(2026-04-22)로 정량 처리 방향이 전체로 확장됨.

- 목적: **원자적 커밋 강제** (1 커밋 = 1 논리 단위)
- 판정은 **커밋 시도 시작 시점 1회만**. sub-커밋은 재판정 SKIP
  (`HARNESS_SPLIT_SUB=1` 환경변수로 pre-check이 분리 블록 통째 스킵)

#### 설계 공간 (결정 대기)

- **A. 분리 축**: `naming.md` "경로 → 도메인 매핑" 재활용 (SSOT 존재)
  - 폴백: 매핑 없는 파일은 폴더 1단계 prefix로 그룹화
- **B. 임계·재분리**: 그룹 내 파일 N개 초과 시 재분리 (N 초안: 10)
- **C. 내용별 묶음**: subject 키워드 + diff hunk 패턴 유사성
- **D. hunk 분리**: 같은 파일 내 독립 주제 hunk `git add -p` 식 분리
  (파일 단위 정립 후 확장)
- **E. 속도 최적화**: sub-커밋은 사이즈 작아져 stage 자동 재판정
  (standard → skip까지). bulk의 실질 목적(빠른 커밋) 계승
- **F. 구현 위치**: pre-check = 판정, `split-commit.sh` = 실행
  (commit 스킬 아님 — staging/pre-check 영역)

#### 예외

- **rename-only 대량 커밋**: 원자적, 분리 불가 → 예외
- **의존성 있는 변경**: sub-staging 각각에 pre-check·빌드 통과 확인
- **사용자 수동 오버라이드**: `--no-split` 같은 플래그

#### 선행 조건 + 상위 SSOT

- #13 5커밋 측정 누적 (staging rebalance 재평가)
- commit 스킬 stage별 경과시간 로그 (`hn_commit_perf_optimization.md` §4)
- 거대 커밋 발생 케이스 관찰
- 상위 SSOT: `hn_review_staging_rebalance` / `hn_review_tool_budget` /
  `hn_review_maxturns_verdict_miss` (bulk 폐기 근거) / `hn_commit_perf_optimization`

**결정 문서 승격 대상**: 실측 누적 후 `decisions/`로.

---

## 완료된 항목 (v0.19.0~v0.20.7에서 구현)

감사 시작 시점(2026-04-22) 기준 15+ 항목 중 아래는 모두 완료. 세부는
commit 메시지 참조:

```bash
git log --oneline --grep "(v0\.(19|20)\."
```

- **#1** 린터 2회 → Step 5 통합 (v0.19.0)
- **#2·9** light/strict 모드 폐기, `--quick`/`--deep`/`--no-review` 단일화 (v0.19.0)
- **#3** 진척도 갱신 Step 2 → Step 7.5 재배치 (v0.19.0)
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
  위임하고 WIP에는 미결만 유지**하는 규율 필요
