---
title: 다운스트림 마이그레이션 가이드 — 아카이브
domain: harness
tags: [migration, upgrade, downstream, archive]
status: completed
created: 2026-05-02
---

# 다운스트림 마이그레이션 가이드 — 아카이브

`MIGRATIONS.md`는 최근 5개 버전 본문만 유지한다. 6번째 이전 버전은 본
파일로 이동된다 (v0.30.1 정책). 다운스트림이 오래된 업그레이드를 추적해야
할 때만 참조.
## v0.28.9 — Phase 3 split 옵트인 강등 + AC [x] 자동 이동 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | split 결정 로직 옵트인 강등. char 다양성 ≥ 2 + (HARNESS_SPLIT_OPT_IN=1 OR 거대 커밋) + non-skip stage 모두 만족 시에만 split. 5/5 skip 케이스 자동 single |
| `.claude/scripts/docs_ops.py` | 3-way merge | wip-sync 자동 이동 트리거 확장. body_referenced 신호 추가 — 이미 [x] 상태 WIP에서도 staged 파일 본문 언급 시 자동 이동. 미완료 검사를 체크박스 패턴(`- [ ]`)으로 정밀화 |
| `.claude/rules/staging.md` | 3-way merge | "split 옵트인 정책" 섹션 신설. 기본 single, 분할은 명시 트리거 시에만 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **이전 동작 변경**: char 다양성 ≥ 2면 무조건 split → 이제는 거대 커밋 OR `HARNESS_SPLIT_OPT_IN=1` 명시 시에만. 다운스트림이 split 동작에 의존하지 않으면 자연 흡수
- **AC [x] 자동 이동**: 사용자가 미리 [x] 마킹한 WIP가 commit 시 자동 completed 이동. 차단 키워드(`TODO:`·빈 체크박스 등) 검사 통과 시에만
- **회고 영향**: "단일 결정 = 단일 커밋" atomic 원칙 적용. 다운스트림이 char별 selective fetch하지 않는 경우만 안전 (확인됨)
- 한계: `HARNESS_SPLIT_OPT_IN=1` 미지원 다운스트림 환경에선 자동 분할 의존이 불가능 — 거대 커밋 시 자동 분할은 동작

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash):
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: 본 commit 자체 — char 다양성 2 + non-huge → split_action: single (이전엔 split)
  - T40.1 wip-sync abbr 테스트는 본 환경 fixture 격리 갭으로 fail (본 fix 무관, MIGRATIONS v0.28.4 주의 참조)

### 검증
```bash
pytest -m "secret or stage"
HARNESS_SPLIT_OPT_IN=1 /commit  # 명시 분할 옵트인
```

---

## v0.35.3 — CLAUDE.md 행동 원칙 AC·CPS 실질 내용으로 교체 (2026-05-05)

### 변경 내용
- CLAUDE.md "행동 원칙" 섹션을 추상 원칙(Think Before Coding·Goal-Driven Execution)에서
  AC·CPS 실질 내용(형식·필수 필드·SSOT 링크)으로 교체

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.



## v0.35.2 — CLAUDE.md 절대 규칙 + 진입점 보강 (2026-05-05)

### 변경 내용
- CLAUDE.md 절대 규칙에 `docs/WIP/ 파일 Write 직접 생성 금지` 추가
- CLAUDE.md 진입점 표에 "문서 생성 (코드 작업 수반) → /implementation" 항목 추가
- CLAUDE.md `<important>` 태그 조건에 Write 도구 직접 사용 명시

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.



## v0.35.1 — starter_skills 필터링 구현 + harness-dev 등록

### 변경 파일

- `.claude/HARNESS.json` — `starter_skills`에 `harness-dev` 추가 (`"harness-init,harness-adopt,harness-dev"`)
- `.claude/skills/harness-upgrade/SKILL.md` — Step 6에 `starter_skills` 필터 로직 추가: ADDED 파일 중 `.claude/skills/{starter_skill}/` 경로는 다운스트림 전달 제외

### 적용 방법

자동 적용. 수동 작업 없음.

### 선택적 정리 (기존 다운스트림)

이전 버전에서 harness-upgrade를 통해 starter 전용 스킬 폴더를 받은 다운스트림은
삭제해도 무방 (기능상 문제 없음 — 실행하지 않으면 무해):

```bash
rm -rf .claude/skills/harness-init/
rm -rf .claude/skills/harness-adopt/
rm -rf .claude/skills/harness-dev/
```

harness-sync는 다운스트림도 사용하므로 삭제하지 않는다.

### 회귀 위험

- `starter_skills` 필터는 SKILL.md 절차 문서 변경 — Claude가 Step 6 실행 시 이 절차를 따름
- upstream 격리 환경에서 별도 테스트 없음. 운용 검증 필요



## v0.35.0 — doc-health 스킬 신설 + CLAUDE.md 진입점 추가

### 변경 파일

- `.claude/skills/doc-health/SKILL.md` — 신규 스킬. 하네스 도입 이전 레거시 문서를 반자동 정비 (abbr rename·CPS frontmatter 추가·archived 이동). eval --harness 진단 결과를 이어받아 4단계로 진행
- `.claude/skills/eval/SKILL.md` — `--harness` 결과에 doc-health 호출 권장 안내 추가 (abbr 없는 파일 5개+·CPS 누락 10개+·박제 의심 3건+ 시 트리거)
- `.claude/skills/harness-adopt/SKILL.md` — 완료 리포트 "다음 할 일"에 `/doc-health` 실행 권장 안내 추가
- `CLAUDE.md` — 진입점 테이블에 `/eval --harness`, `/doc-health` 행 추가
- `.claude/HARNESS.json` — `skills`에 `doc-health` 추가

### 적용 방법

자동 적용. 수동 작업 없음.

### 다운스트림 권장

레거시 문서(하네스 도입 이전 작성)가 많은 경우 `/eval --harness` → `/doc-health` 순으로 실행해 탐색 체인 정합성을 확보할 것.

### 회귀 위험

- 신규 스킬 추가만. 기존 스킬 로직 변경 없음
- CLAUDE.md 진입점 행 추가는 기존 행에 영향 없음



## v0.34.8 — completed 봉인 — 본문 마크다운 링크 경로 교체 면제

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 면제에 "본문 마크다운 링크 경로 교체" 추가: hunk 내 삭제(-) 라인이 있는 상태에서 링크 패턴(`[...](...)`)을 포함한 추가(+) 라인은 면제. 순수 추가(삭제 없는 링크 줄 추가)는 기존과 동일하게 차단
- `.claude/scripts/tests/test_pre_commit.py` — T42.7(링크 경로 교체 면제), T42.8(순수 추가 차단) 회귀 테스트 추가

### 적용 방법

자동 적용. 수동 작업 없음.

### 회귀 위험

- 면제 조건은 `-U0` diff 기준 hunk 단위. 같은 hunk에 `-` 없이 `+`만 있는 링크 줄은 여전히 차단
- upstream 격리 환경(Windows)에서 pytest gate 20/20 통과 확인. Linux/macOS 미테스트



## v0.34.7 — eval_cps_integrity 다운스트림 호환성 강화 + completed 봉인 frontmatter 면제

### 변경 파일

- `.claude/scripts/eval_cps_integrity.py` — `extract_cps_solution_ids()` 정규식 확장: `**S1**` 굵은 글씨 형식 인식 추가. `docs/harness/` 폴더를 스캔 제외 (upstream CPS 참조 문서 오탐 방지)
- `.claude/scripts/pre_commit_check.py` — completed 봉인 면제에 frontmatter 블록 내 변경 추가: `reopen → solution-ref 수정 → move` 정상 절차 후 차단되는 문제 해소

### 적용 방법

자동 적용. 수동 작업 없음.

### 회귀 위험

- `eval_cps_integrity.py` 정규식 변경은 `### S1` 패턴을 그대로 유지하면서 `**S1**` 추가. upstream CPS(`### S1` 형식)에 영향 없음
- `docs/harness/` 스캔 제외는 다운스트림 harness 자체 문서가 없는 프로젝트에서는 동작 무관
- `pre_commit_check.py` frontmatter 면제는 `---` 블록 내 라인에만 적용. 본문 변경은 기존과 동일하게 차단
- upstream 격리 환경(Windows)에서 71/71 통과 확인. Linux/macOS 미테스트



## v0.34.6 — eval Solution 충족 인용 분포 집계 + PRD 레이어 보강 (User Needs·milestones 샘플·harness-init 권고)

### 변경 파일

- `.claude/scripts/eval_cps_integrity.py` — `count_solution_refs()` 함수 추가. Solution별 frontmatter 인용 카운트 집계
- `.claude/skills/eval/SKILL.md` — CPS 무결성 결과 해석에 "Solution 충족 인용 분포" 가이드 추가
- `.claude/skills/harness-init/SKILL.md` — CPS 템플릿에 `### User Needs` 선택 섹션 추가, 규모별 선택적 레이어 권고 단락 추가
- `docs/guides/project_kickoff_sample.md` — `### User Needs` 섹션(Personas·Success Metrics) 샘플 추가
- `docs/guides/milestones_sample.md` — 신규 생성. 에픽 = 사용자 가치 묶음 원칙 + backlog/in-progress/done 추적 샘플
- `.claude/scripts/tests/test_pre_commit.py` — wipsync_repo fixture: 빈 커밋 방지 (`git status --porcelain` 체크 추가)

### 적용 방법

자동 적용. 수동 작업 없음.

### 선택적 활성화 (다운스트림 권장)

도메인 5개+ 또는 decisions 30+ 누적된 프로젝트:
1. `docs/guides/milestones_sample.md`를 `docs/guides/milestones.md`로 복사 후 에픽 정의
2. `docs/guides/project_kickoff.md`의 `### Context` 아래 `### User Needs` 섹션 작성

### 회귀 위험

- eval_cps_integrity.py 추가 함수는 기존 출력(박제 의심·Problem 인용 빈도)에 영향 없음. upstream 격리 환경(Windows)에서 71/71 통과 확인
- test_pre_commit.py fixture 수정은 WipSync 관련 10개 테스트에만 영향. 기존 로직 변경 없음
- Linux/macOS 미테스트



## v0.34.5 — supabase/migrations/*.sql PostgreSQL role 이름 오탐 면제

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — `S1_LINE_EXEMPT`에 `^supabase/migrations/.*\.sql$` 추가
- `scripts/install-secret-scan-hook.sh` — `EXEMPT_RE`에 `|^supabase/migrations/.*\.sql$` 추가 (동기화)
- `.claude/scripts/tests/test_pre_commit.py` — `test_supabase_migration_sql_exempt` 회귀 테스트 신규

### 다운스트림 영향

**`supabase/migrations/*.sql`의 PostgreSQL role DCL이 시크릿으로 오탐되어 커밋 차단되는 문제 해소**:

`GRANT ... TO service_role`, `REVOKE ... FROM service_role`, `CREATE POLICY ... = 'service_role'` 등
PostgreSQL DCL에서 role 이름 `service_role`이 시크릿 패턴 `service_role(?![A-Z_])`에 걸려
`line-confirmed` 차단됐음 (뒤 문자가 `;`·`,`·공백이라 negative lookahead 통과).

v0.34.5부터 `supabase/migrations/*.sql` 파일은 `S1_LINE_EXEMPT` 면제.
`scripts/install-secret-scan-hook.sh` grep 폴백도 동기화됨.

**잔여 위험**: `supabase/migrations/` 면제로 인해 해당 경로 파일에서 진짜 시크릿(`sb_secret_*` 등)
라인이 있어도 line-confirmed 미적용. 정상 워크플로우에서 migration SQL에 시크릿 리터럴을
하드코딩하는 경우는 없으므로 잔여 위험 낮음.

### 적용 방법

자동. `harness-upgrade` 후 별도 수동 적용 없음.
`scripts/install-secret-scan-hook.sh`를 재설치하면 grep 폴백에도 면제 반영됨:
```bash
bash scripts/install-secret-scan-hook.sh
```

### 검증

- `pytest -m secret` 5/5 통과 (`test_supabase_migration_sql_exempt` 신규 포함)
- 회귀 위험: 기존 4건 모두 통과 확인



## v0.34.4 — pre-check false-block 2건 수정 (AC 에러 메시지·service_role 환경변수 이름)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — AC 섹션 미탐지 에러 메시지 개선, `service_role` 패턴 negative lookahead 추가

### 다운스트림 영향

**이슈 1 — AC `**Acceptance Criteria**:` 형식 누락 시 에러 메시지 개선**:

`### Acceptance Criteria` 헤더 형식으로 AC 섹션을 작성하면 pre-check이
`AC Goal: 항목 누락`으로 차단했으나 원인 파악이 어려웠음. v0.34.4부터
"AC 섹션 없음. `**Acceptance Criteria**:` (bold 형식) 헤더가 필요합니다."
메시지로 즉시 원인 파악 가능. docs.md SSOT(bold 형식) 변경 없음.

**이슈 2 — `service_role` 환경변수 이름 참조 false-block 해소**:

`process.env.SUPABASE_SERVICE_ROLE_KEY` 등 대문자+언더스코어가 뒤에 오는
환경변수 이름이 `service_role` 시크릿 패턴에 걸려 line-confirmed 차단됐음.
v0.34.4부터 `service_role(?![A-Z_])` negative lookahead로 변수 이름은 면제.
`"service_role"` 값 리터럴·`role: service_role` 직접 노출은 계속 차단.

### 적용 방법

자동. `harness-upgrade` 후 별도 수동 적용 없음.

### 검증

- `pytest -m secret` 4/4 통과
- 회귀 위험: `service_role(?![A-Z_])` 패턴이 실제 시크릿 값을 false-negative할 가능성 — 실제 JWT 등 키 값에는 `_`가 뒤에 오지 않으므로 위험 없음



## v0.34.3 — completed 봉인 relates-to path 수정 면제 (dead-link 복구 루프 해소)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — 봉인 게이트 면제 목록에 `- path: <경로>` 라인 추가
- `.claude/scripts/tests/test_pre_commit.py` — T42.6 회귀 테스트 신규

### 다운스트림 영향

**v0.34.2 업그레이드 후 발생하는 루프 해소**:

v0.34.2의 verify-relates 전수 검사와 기존 completed 봉인이 충돌해 영구
차단 루프가 발생했음 — completed 문서의 dead relates-to를 수정하면 봉인이
차단, 차단 상태로는 수정 불가.

v0.34.3부터 completed 문서의 `- path: <경로>` 라인 변경은 봉인 면제.
**dead-link 복구(경로 수정·항목 제거)가 즉시 가능**.

### 적용 방법

자동. `harness-upgrade` 후 relates-to 경로 직접 수정 후 커밋 가능.

`verify-relates`로 확인 후 수정:
```bash
python3 .claude/scripts/docs_ops.py verify-relates
# 경로 수정 또는 항목 제거
git add <수정한 파일>
git commit ...
```

### 검증

- `pytest -m gate` 18/18 통과 (T42.6 신규 포함)
- 실측: completed 문서 `path:` 라인 수정 시 봉인 통과 + verify-relates 차단만 남음
- 회귀 위험: `path:` 면제가 봉인 우회로 악용될 가능성 낮음 — frontmatter 내 구조화된 경로 값이므로 본문 의미 변경과 구분 가능

### 결정 근거

다운스트림 보고: v0.34.2 upgrade 후 모든 커밋 차단. debug-specialist 진단
후 completed 봉인 면제 화이트리스트에 `path:` 추가로 해소.



## v0.34.2 — verify-relates pre-check 통합 (커밋 시 relates-to 전수 검사)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — 3.5단계 섹션 C 재설계: 기존 staged 파일 단독 검사 → `cmd_verify_relates` 전수 호출로 교체
- `.claude/scripts/tests/test_pre_commit.py` — `TestVerifyRelatesPrecheck` T45.1·T45.2 신규

### 다운스트림 영향

pre-check 3.5단계 C 동작 변경:

**이전**: staged 파일 자신의 frontmatter `relates-to`만 검사 (inbound 역검색 없음)

**v0.34.2**: `docs/` 전체 모든 파일의 `relates-to` 전수 검사. **기존 커밋된 파일의 깨진 ref도 차단**.

**영향**:
- 다운스트림에 사전 dead relates-to 부채가 있으면 첫 커밋 시 차단됨
- `python3 .claude/scripts/docs_ops.py verify-relates`로 상세 확인 후 경로 수정 또는 항목 제거
- 비용: docs/ 전체 검사 0.13s (다운스트림 N=18 환경 기준 — v0.34.1 다운스트림 검증 실측치)

### 적용 방법

`harness-upgrade` 후 즉시 `python3 .claude/scripts/docs_ops.py verify-relates` 실행. 미연결 건이 있으면 수정 후 커밋.

**수동 적용 필요**: 사전 부채 있는 다운스트림은 upgrade 후 첫 커밋 전 `verify-relates` 실행·수정 필수.

### 검증

- `pytest -m docs_ops` 27/27 통과 (기존 25 + 신규 2 — T45.1·T45.2)
- 실측: 깨진 ref 인위 생성 후 pre-check 차단 확인
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다른 파일시스템·인코딩 환경 재발 시 본 섹션 갱신

### 결정 근거

`docs/decisions/hn_verify_relates_precheck.md` — 다운스트림 v0.34.1 검증에서 relates-to dead link 7건 발견 후 debug-specialist 진단. H3 박제 ref 확정, 전수화가 근본 해결로 판단.



## v0.34.1 — amplification 후속 4 wave 처리 (cluster 게이팅·WIP 가시성·glob 가이드·adopt 안내)

### 변경 파일

- `.claude/scripts/docs_ops.py` — `cmd_cluster_update` 결정적 출력 + WIP 수집
- `.claude/scripts/tests/test_pre_commit.py` — `TestClusterUpdateGating` 3 케이스 신규
- `.claude/rules/docs.md` — "## 문서 탐색 > 기본 경로" 양쪽 wildcard + cluster 진입점 격상
- `.claude/rules/naming.md` — "왜 — 파일명이 곧 인덱스" bullet 갱신
- `.claude/skills/harness-adopt/SKILL.md` — Step 8 "다음 할 일" `/harness-init` 강조

### 다운스트림 영향

#### (c) cluster 재생성 게이팅 — 결정적 출력 + diff 비교
- `cluster-update`가 동일 본문이면 write skip → mtime noise 0
- cluster 양식·인터페이스 무변경. 자동 이행

#### (b) WIP cluster 가시성 — 진행 중 섹션 자동 등록
- cluster 본문에 `## 진행 중 (WIP)` 섹션 신규 (기존 `## 문서` 무변경)
- 사용자·에이전트가 cluster scan 한 번에 completed + 진행 중 발견
- 첫 호출 시 WIP 있는 도메인 cluster만 1회 갱신 후 안정. 추가 작업 불필요

#### (d) Glob 라우팅 태그 가이드 — 양쪽 wildcard 명시
- `docs.md`·`naming.md` 가이드 문구만 변경 (라우팅 태그 폐기 안 함)
- 사용자·에이전트가 `docs/**/*<abbr>_*` 양쪽 wildcard로 WIP 포함 발견 가능
- 다운스트림 WIP 양식 마이그레이션 불필요

#### (e) adopt-without-init 사전 안내 강화
- `harness-adopt` Step 8 "다음 할 일"에 `/harness-init` 미실행 시 implementation 차단됨을 명시
- (a) v0.34.0 차단 메시지와 이중 안전망 (사전 + 사후)
- 기존 adopt 완료 + init 미완료 다운스트림은 (a) 차단 메시지로 사후 안내. 추가 작업 불필요

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

다운스트림은 v0.34.1 적용 후 첫 commit 1회에 cluster 본문에 `## 진행 중 (WIP)`
섹션이 추가되며 (WIP 있는 도메인만), 이후 호출은 영향 도메인만 갱신.

### 검증

- `pytest -m docs_ops` 25/25 통과 (기존 22 + 신규 3)
- starter 실측: 멱등 호출 시 skip 2/2, 단일 cluster stale 시 영향 cluster만 갱신
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. POSIX bash 또는 다른
  파일시스템(mtime 정밀도)에서 멱등성 재발 시 본 섹션 갱신 필요

### 결정 근거

- `docs/decisions/hn_cluster_update_gating.md`
- `docs/decisions/hn_wip_cluster_visibility.md`
- `docs/decisions/hn_glob_routing_tag.md`
- `docs/decisions/hn_adopt_without_init_guard.md`



## v0.34.0 — implementation init 게이트 의미 재정의 (A4)

### 변경 파일

- `.claude/skills/implementation/SKILL.md` 라인 69~85 — Step 0 게이트 로직 재서술
- `.claude/scripts/check_init_done.sh` (신설) — 판정 로직 추출 (회귀 테스트 가능 + 다운스트림 자가 점검 용도)
- `.claude/scripts/tests/test_pre_commit.py` — TestInitGate 5 케이스 신규 추가

### 다운스트림 영향

implementation Step 0의 init 미완료 감지 로직이 변경됨.

**이전 (v0.33.x까지)**:
- CLAUDE.md `## 환경`의 `패키지 매니저:` 키 1개만 검사
- 비어있으면 차단
- 다운스트림 baseline 측정에서 false-block 입증 (15~19s 헛돔)

**v0.34.0 (A4 의미 재정의)**:
- `docs/guides/project_kickoff.md` 부재 OR `status: sample` 단독 → 차단
- CLAUDE.md `## 환경` drift는 차단 사유 아님 (다운스트림 자율)

**다운스트림 자유도 회복**:
- C++/CMake처럼 `패키지 매니저:` 키가 N/A인 환경도 정상 통과
- 다운스트림이 자기 양식·언어로 CLAUDE.md `## 환경` 채울 자유 확보

**여전히 차단되는 케이스 (의도)**:
- `harness-adopt` 끝났지만 `harness-init` 안 돈 다운스트림 (sample만 존재)
- `project_kickoff.md` 자체가 없는 신규 프로젝트

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

`harness-init` 정상 완료한 다운스트림은 영향 없음. `harness-adopt`만 돌고
`harness-init` 미실행한 다운스트림은 본 v0.34.0부터 implementation Step 0
가 차단됨 — `/harness-init` 실행 후 작업 진행.

### 검증

- `pytest -m gate` (TestInitGate 6/6 신규 통과 — 인라인 주석 케이스 포함)
- pytest 전체 64 passed (기존 58 + 신규 6, 회귀 0)
- starter `check_init_done.sh` 비용 측정: 5회 평균 ~0.07s (max 0.15s) —
  ≤2s 게이트 27x 여유
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다른 다운스트림
  환경(POSIX bash·다른 CPS 위치) 재발 시 본 incident 갱신 필요

### 결정 근거

`docs/decisions/hn_init_gate_redesign.md` (이동 후) — advisor 4 대안
weighted matrix 평가 결과 A4 채택 (96점 / A1 82 / A3 62 / A2 40).



## v0.33.1 — SEALED 면제 (MIGRATIONS류 자기 운영 파일)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — `SEALED_PATH_EXEMPT` 추가 (MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md 3개 path 화이트리스트)
- `.claude/scripts/tests/test_pre_commit.py` — T42.5 회귀 테스트 추가

### 다운스트림 영향

v0.32.0 (약속 박제 보호)에서 도입한 SEALED(completed 봉인) 룰이 starter
자기 운영 누적 파일을 면제하지 않아, 다운스트림이 `harness-upgrade`로
v0.33.0을 fetch한 직후 `/commit` 시 MIGRATIONS.md가 차단되는 결함이
발견됨 (incident 2026-05-02 다운스트림 보고).

본 fix로 MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md는
SEALED 검사에서 면제. 다운스트림 정상 흐름 복귀.

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

### 검증

- pytest -m gate (T42.5 신규 포함, 11/11 통과)
- pytest 전체 58 passed (기존 57 + 신규 1, 회귀 0)
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다운스트림 환경
  재발 시 본 incident 갱신 필요



## v0.33.0 — commit_finalize wrapper (wip-sync + git commit 단일 흐름)

### 변경 파일

- `.claude/scripts/commit_finalize.sh` (신설) — wip-sync → git commit 단일 흐름 wrapper
- `.claude/skills/commit/SKILL.md` Step 7.5·8·커밋 메시지 작성 — wrapper 호출 1줄로 단순화
- `.claude/scripts/tests/test_pre_commit.py` — TestCommitFinalize 3 케이스 신설

### 변경 내용

자기증명 사고 (2026-05-02): SKILL.md SSOT는 "git commit **직전** wip-sync"
명시했으나 Claude가 git commit 먼저 호출 → wip-sync → 별 이동 commit
패턴 반복. 8 commit 중 3건 위반 (37.5%).

자율 신뢰만으로는 부족 → 메커니즘 차단으로 전환:

- `git commit` 직접 호출 금지. wrapper 경유 의무
- wrapper 내부: VERDICT != block 이면 wip-sync 호출 → wip 이동·cluster·
  역참조 갱신 모두 staging → `git commit "$@"` 단일 호출
- 결과: 1 wave = 1 commit. 별 이동 commit 사라짐

### 적용 방법

자동. harness-upgrade 후 commit 흐름 자동 변경.

호출 형식:
```bash
VERDICT="$VERDICT" HARNESS_DEV=1 \
  bash .claude/scripts/commit_finalize.sh \
    -m "feat: [제목]" -m "[본문]"
```

### 검증

```bash
pytest -m gate  # TestCommitFinalize 3 케이스
```

회귀 위험: TestCommitFinalize 3/3 통과 (HARNESS_DEV 차단·simple commit·
block skip wip-sync). 본 commit 자체가 자기증명 — wrapper 사용해 commit.



## v0.32.0 — 약속 박제 보호 (completed 봉인 + anti-defer 룰)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 게이트 신설 (3.5번 섹션). status: completed 문서 본문 무단 변경 시 exit 2 차단
- `.claude/rules/anti-defer.md` (신설) — 미루기 회피 사유 블랙리스트 + 사용자 명시 처리 지시 우선 규칙
- `.claude/agents/review.md` — 검증 루프 7번 "wave scope 무단 확장 감지" 추가
- `CLAUDE.md` — 절대 규칙에 anti-defer + completed 봉인 명시
- `.claude/scripts/tests/test_pre_commit.py` — TestCompletedSeal 5 케이스 신설
- `docs/decisions/hn_session_test_results.md` (reopen) — 우선순위 5 측정 결과 누적 후 재 completed 처리
- `docs/WIP/decisions--hn_promise_protection.md` (신설) — 본 wave WIP

### 변경 내용

**자기증명 사고 (2026-05-02)**: v0.31.2 commit 후 완료된 wave WIP를 같은 세션에서 무단 확장 시도 → "최악 패턴" 사고. 다음 시스템 보호 메커니즘 신설:

1. **completed 봉인 게이트 (메커니즘)**: status: completed 문서 본문 변경을 pre-check이 차단. 변경하려면 `docs_ops.py reopen`으로 in-progress 전환 의무. `## 변경 이력` 섹션·updated/status 필드·rename은 면제.

2. **anti-defer 룰 (자율 신뢰 보강)**: "측정 후·다음 세션·데이터 누적 필요" 같은 미루기 회피 사유의 사용자 승인 없는 단독 사용 금지. 별 wave 분리는 정상 흐름이지만 처리 시점이 "후속"이면 미루기로 간주.

3. **review 자동 감지**: review.md 검증 루프에 wave scope 무단 확장 감지 추가.

**자기증명 검증**: 본 commit 작성 중 우선순위 5 측정을 `decisions/hn_session_test_results.md` (completed)에 직접 수정 → 본 게이트가 즉시 차단 → reopen 절차 거쳐 정상 처리. 메커니즘 정확 작동.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음. 다운스트림이 completed 문서 수정 시 `docs_ops.py reopen` 절차 의무.

### 검증

```bash
pytest -m gate
```

회귀 위험: TestCompletedSeal 5/5 통과. 본 commit이 자기증명 — 봉인 게이트가 본 작업 자체를 차단해 reopen 절차 거치게 함.



## v0.31.2 — commit/SKILL.md Step 7 staging.md SSOT link로 단순화

### 변경 파일

- `.claude/skills/commit/SKILL.md` — Step 7 Stage 결정 우선순위·Stage별 행동·거대 커밋 정책 본문 재진술 제거 → staging.md SSOT 참조 한 단락
- `docs/WIP/decisions--hn_rule_skill_ssot_apply.md` (신설) — Task 2 wave WIP

### 변경 내용

`hn_rule_skill_ssot.md` Task 1 측정 결과 핫스팟 1순위(commit × staging)
처리. SKILL.md 본문에 staging.md의 Stage 정의·플래그 우선순위·충돌 처리·
거대 커밋 정책이 일부 인라인되어 있던 것을 SSOT 참조로 단순화.

스킬 ~30줄 → ~5줄. staging.md 갱신 시 SKILL.md 동기화 누락 위험 제거.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음.

### 검증

```bash
pytest -m stage
```

회귀 위험: 본 변경은 SKILL.md 본문만 — Claude가 staging.md를 follow하는지 운용에서 확인 필요. 본 commit 자체가 자기증명 (Step 7 흐름이 정상 작동했음).



## v0.31.1 — scripts/tests 폴더 분리 (운영/테스트 혼재 해소)

### 변경 파일

- `.claude/scripts/tests/` (신설 폴더) — `test_pre_commit.py`·`test_extract_review_verdict.py`·`conftest.py` 이동
- `.claude/scripts/downstream-readiness.sh` — 회귀 스크립트 존재 검사 경로 갱신
- `.claude/settings.json` — pytest 권한 패턴 갱신
- `CLAUDE.md` — 빌드 명령어 경로 갱신

### 변경 내용

운영 코드(`pre_commit_check.py`·`docs_ops.py` 등)와 테스트 코드가 같은 `.claude/scripts/`에 섞여 있어 IDE 노이즈·분리 원칙 위반. `tests/` 하위로 분리. 다운스트림 영향 0 — `pytest .claude/scripts/`도 재귀로 작동.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음. 다운스트림이 자체 테스트를 추가했다면 `tests/` 하위로 옮길지 자율 결정.

### 검증

```bash
pytest .claude/scripts/tests/ -q
```

회귀 위험: import 경로(`Path(__file__).parent`)가 한 단계 깊어진 만큼 `parent.parent`로 수정. 49/49 통과 확인.



## v0.31.0 — review verdict 추출 단순화 + wip-sync 의미 게이트

### 변경 파일

- `.claude/scripts/extract_review_verdict.py` (신설) — review 응답에서 verdict 단어만 추출하는 10줄 스크립트
- `.claude/scripts/test_extract_review_verdict.py` (신설) — markdown leak 5종 + 미존재 케이스 회귀 가드 (`pytest -m review`)
- `.claude/scripts/conftest.py` — `review` marker 등록
- `.claude/agents/review.md` — JSON 스키마·AC 매핑 의무·duplicate key 강제 폐기. "verdict 단어 포함" 한 줄로 단순화
- `.claude/skills/commit/SKILL.md` — Step 7 inline python heredoc(~80줄) → 1줄 호출 교체
- `.claude/scripts/docs_ops.py` wip-sync — frontmatter `problem` 의미 게이트 추가. 직접·body_referenced·abbr 매칭 모두 staged WIP의 problem 일치 의무
- `.claude/scripts/test_pre_commit.py` — TestWipSyncProblemGate 3 케이스 신설. wipsync_repo fixture WIP 비우기 보강 (T40 회귀). `_run_wip_sync` 반환값에 stdout 포함

### 변경 내용

**review verdict 추출 단순화 (Agent tool sub-agent prefill 미작동 대응)**:
- v0.30.5 JSON 스키마 강제는 5/5 markdown 머릿말 leak 실측 — debug-specialist 진단으로 sub-agent prefill 메커니즘 자체가 작동 안 함을 확인
- 형식 강제 폐기 + verdict 단어(`pass|warn|block`) 추출만으로 분기. 부가 정보(blockers·warnings·ac_check)는 응답 본문 그대로 사용자에게 노출

**wip-sync 의미 게이트 (어휘 일치 ≠ 의미 일치 false positive 차단)**:
- v0.30.6 자기증명 사례: `hn_rule_skill_ssot.md` AC 본문 "commit/SKILL.md" 어휘 hit으로 우연 ✅ 추가됨
- staged WIP의 frontmatter `problem` 집합 수집 → 후보 WIP의 `problem`이 그 집합에 있을 때만 매칭 인정
- 자기 자신 staged·staged WIP 부재 시 게이트 skip (작성자 직접 의도·코드 단독 commit 면제)

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음.

### 검증

```bash
pytest -m "review or docs_ops"
```

회귀 위험: upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내에서는 기존 review·wip-sync 호출 흐름과 호환. Linux/macOS subprocess stderr 동작 차이는 미테스트.



## v0.30.6 — Step 7.5 Stage 0 skip 우회 결함 수정 (자기증명 사고 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 7.5 wip-sync 실행 조건 변경 — "Stage 0 skip도 스킵"에서 "block만 차단, skip·pass·warn 모두 실행"으로. wip-sync는 staged 확정 상태 기반이지 review LLM 호출 여부와 무관 |
| `docs/decisions/hn_review_verdict_compliance.md` | 수동 이동 (v0.30.5에서 누락) + 변경 이력 추가 | v0.30.5 commit에서 AC 모두 [x]였음에도 Stage 0 skip이 wip-sync를 가로챘던 사고 기록. 본 commit이 자기증명 — 결함 수정 + 누락 수습 함께 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 변경 작음 — Step 7.5 분기 조건 1줄 + 본문 명시. 다음 commit부터 Stage 0 skip이어도 AC 완료 WIP가 자동 이동
- 운용 추적: `git log --oneline`에서 WIP 파일 자동 이동 누락 사례 0건 기대
- v0.30.5의 review 영역 변경이 우연히 Stage 0 skip을 트리거 → 본 결함 노출 → 즉시 수정. 자기증명 + 즉시 대응 패턴

### 검증
```bash
# 다음 commit에서 wip-sync 실행 여부 stdout 확인
# `wip_sync_matched`·`wip_sync_moved` 출력 누락 없어야
```



## v0.30.5 — review 응답 JSON 규격화 + AC 매핑 의무 (verdict 100% 누락 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/agents/review.md` | 3-way merge | 출력 형식 SSOT를 markdown 템플릿 → raw JSON 1개 객체. 스키마: `{verdict, ac_check[{goal,result,evidence}], blockers[{ac_index}], warnings, axis_check, solution_regression, early_stop, conclusion}`. AC 매핑 의무(prompt N개 ↔ ac_check N개 1:1). duplicate key 금지 명시 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | review prompt prefill을 `{"verdict":"`로 변경. 응답 처리부 markdown grep → JSON 파싱(`json.loads` + `object_pairs_hook` duplicate key 감지). 종료 코드별 재호출 메시지 분기 (exit 1 파싱 실패 / exit 2 verdict 위반 / exit 3 ac_check 정합성 위반) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 본 세션 직전 5 commit (v0.29.2~v0.30.4) 모두 markdown 형식으로는 verdict
  100% 누락 → 1차 재호출 회복 패턴. v0.30.3 prefill만으로 부족 확인.
  JSON 스키마 강제로 형식 위반 자체를 invalid로 만들고, AC 매핑 의무로
  review의 구조화된 사고 강제
- dry test 통과: 정상 + 4가지 위반 시나리오 (필드 누락·dup key·정합성 위반·완전 invalid) 모두 정확 분기
- 다음 commit부터 효과 측정 — 자동 검증 불가, 운용 5 commit 1패스 성공률 추적
- review 영역 변경이라 본 commit은 자기증명 불가 (review.md를 review가 검증해도 의미 약함)

### 검증
```bash
# JSON 파싱·duplicate key·ac_check 정합성 dry test (별 스크립트 없음 — review 응답 받을 때 인라인 실행)
# 다음 commit review 응답이 JSON 형식인지 관찰
git log --grep "review-json-fail" --oneline  # 0건 기대
```



## v0.30.4 — eval_cps_integrity 본문 인용 grep 보강 (proxy 정밀화)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/eval_cps_integrity.py` | 3-way merge | `CPS_REF_PATTERNS` 4종 정규식 + `detect_cps_problem_refs` 함수 신설. frontmatter `problem` 필드만 카운트하던 한계를 본문 CPS 의미 인용("CPS 연결: P#"·"P#(...)"·"P# → S#"·"P# 충족")까지 확장. 자체 우선순위 라벨(`**P#**:`·`### P#.`)은 포지티브 매칭만 사용해 자연스럽게 제외 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 본 starter 실측: P1 0→4, P2 2→8, P5 4→9, P6 0→2 (false positive 해소).
  P3·P4만 진짜 정체로 남음 — 수동 검토 결론과 100% 일치
- 자체 라벨 false positive 0건 (검증 통과)
- 정규식 휴리스틱이라 future 표기 패턴이 새로 생기면 누락 가능. 운용에서 추적

### 검증
```bash
# 보강 효과 확인
python3 .claude/scripts/eval_cps_integrity.py
# 기대: P1·P2·P5·P6 0건 아님, P3·P4만 정체
```



## v0.30.3 — review verdict prefill 패턴 (효율 개선)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | review prompt 끝을 `## 리뷰 결과 / verdict: `로 끝내 prefill 효과. "출력 형식 — 절대 규칙" 섹션 추가 — 분석 머릿말 금지·결론부터 출력 명시 |
| `.claude/agents/review.md` | 3-way merge | 상단 헤더 인용 박스 강화 — 자주 나오는 실수 명시·"분석은 reasoning에서, 출력은 결론부터" 행동 가이드. line 201 SSOT는 형식 정의, 상단은 행동 가이드로 역할 분리 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용. 다음 commit부터 review
1패스 통과율 추적.

### 회귀 위험
- prefill 패턴 효과 자동 검증 불가 — 운용에서 5 commit 1패스 성공률로 측정
- 본 세션 직전 4 commit (v0.29.2~v0.30.2) 모두 verdict 누락 → 1차 재호출 회복 패턴 100%
- 다운스트림 환경(Linux/macOS) 미테스트 (prompt 텍스트 변경이라 OS 무관)

### 검증
```bash
# 다음 commit 시 review 1차 응답 첫 2줄 형식 준수 여부 관찰
# git log 메시지에 [review-form-warn] 태그 빈도 추적
git log --grep "review-form-warn" --oneline
```



## v0.30.2 — MIGRATIONS·README 슬림화 + archive 자동화 (효율 개선)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `docs/harness/MIGRATIONS.md` | 자동 (slim) | 759줄(24개) → 240줄(5개). 6번째 이전 18개 섹션은 신규 archive로 이동. 정책 갱신 — "최신 5개 본문만 유지" |
| `docs/harness/MIGRATIONS-archive.md` | 신규 | 18개 섹션 누적 (v0.28.8 이전). 보존용·갱신 없음 |
| `README.md` | 자동 (slim) | 420줄 → 297줄. "최근 주요 변경" 섹션 31개 → 5개. 자세한 이력은 MIGRATIONS·archive·git log로 안내 |
| `.claude/scripts/harness_version_bump.py` | 3-way merge | `--archive [keep=5]` 서브커맨드 신설. MIGRATIONS.md 6번째 이전 섹션 자동 이동. 멱등성 보장 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 4에 `harness_version_bump.py --archive` 호출 추가 (5개 → 4개). 매번 자동 archive로 본문 비대화 방지 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용. 다운스트림이 자기 환경
MIGRATIONS.md를 슬림화하려면 `python3 .claude/scripts/harness_version_bump.py --archive`
1회 실행.

### 회귀 위험
- upstream 격리 환경에서 archive 멱등성·keep=4 시뮬 동작 확인
- 다운스트림이 마지막 upgrade 이후 6개 이상 누적된 경우 본 정책 적용 시
  archive로 일부 이동 — 본문은 최신 5개만 보임. 더 오래된 항목은 archive 참조
- README 변경 이력은 archive로 옮기지 않음 (git log + MIGRATIONS-archive로 충분)

### 검증
```bash
# archive 멱등성
python3 .claude/scripts/harness_version_bump.py --archive

# 본문 5개 + archive 18개 (본 시점 기준)
grep -c "^## v0\." docs/harness/MIGRATIONS.md docs/harness/MIGRATIONS-archive.md
```



## v0.30.1 — wip-sync 매칭 정밀화 + 위임 트리거 강화 (자기증명 사고 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | wip-sync 매칭 정규식 정밀화 — `^\s*([-*]\|\d+\.)\s` → `^\s*[-*]\s+\[[ xX]\]\s` (체크박스 라인 한정). frontmatter 영역 마킹 제외(`_fm_end` 인덱스). `body_referenced`도 `[x]` 마크 + staged 파일 언급으로 좁힘 |
| `.claude/scripts/session-start.sh` | 3-way merge | 연속 fix 감지를 prefix 무관 "공통 파일 2 커밋 연속 수정"으로 확장. 메타 파일(HARNESS.json·README·MIGRATIONS·clusters) 노이즈 제외 |
| `.claude/rules/no-speculation.md` | 3-way merge | 호출 조건표에 "동일 시스템 동작 이슈 2회 이상" 행 추가 + 본문 보강 (사용자 키워드 보고 없어도 Claude 자가 트리거 의무) |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | TestWipSyncMatchPrecision 3 케이스 신설 (사전 준비·frontmatter relates-to false positive 차단 + 정상 매칭 회귀 가드) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경에서 `pytest -m docs_ops` 신규 3 케이스 통과 확인
- `bash -n session-start.sh` 구문 검증 통과
- 기존 2 failure (`TestWipSyncAbbrMatch::test_abbr_*`)는 본 변경과 무관 — 별건 abbr 보조 매칭 경로 이슈 (debug-specialist 진단 결과)
- 다운스트림 환경(Linux/macOS) 미테스트
- session-start hook은 매 세션 시작에 동작 — 변경 후 다음 세션부터 효과

### 검증
```bash
# wip-sync 매칭 정밀화 회귀 가드
python -m pytest .claude/scripts/test_pre_commit.py::TestWipSyncMatchPrecision -v

# session-start.sh 구문
bash -n .claude/scripts/session-start.sh
```



## v0.30.0 — eval --harness CPS 무결성 감시 + commit 잔여 정정 (efficiency overhaul follow-up)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/eval_cps_integrity.py` | 신규 (3-way merge) | docs/ 전수 frontmatter solution-ref 박제 grep + Problem 인플레이션·인용 빈도 측정. `pre_commit_check.py` (verify_solution_ref·get_cps_text·parse_frontmatter) 동적 import 재사용 (코드 중복 0) |
| `.claude/skills/eval/SKILL.md` | 3-way merge | `--harness` 점검 항목 5(CPS 무결성) 신설 + 보고 형식·`--deep` 활용 가이드 추가 |
| `docs/decisions/hn_commit_auto_verify.md` | 자동 (status 정정) | v0.29.2 wip-sync 흐름 잔여 — in-progress → completed |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경에서 `eval_cps_integrity.py` 박제 감지·인플레이션 경고·인용 0건 검출 시뮬레이션 통과
- 본 starter 실측: P1·P3·P4·P6 frontmatter 인용 0건 발견 (정체 의심 — Problem 정의 자체 검토 신호, 자동 조치 X)
- 다운스트림 환경(Linux/macOS) 미테스트
- `eval --harness` 사용자가 본 SKILL.md 절차에 따라 수동 실행해야 작동 (자동 hook 아님)

### 검증
```bash
# CPS 무결성 1회 실행
python3 .claude/scripts/eval_cps_integrity.py
```



## v0.29.2 — commit 5.3 자동 실행 코드 구체화 (efficiency overhaul follow-up)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 5.3 코드 블록 구체화 — `PRE_CHECK_OUTPUT`에서 `AC_TESTS`/`AC_ACTUAL` 변수 추출, 화이트리스트 정규식 SSOT (`^(pytest\|bash -n\|python -m\|grep)\b`), `run_ac_check` 공유 함수 (tests·실측 동일 분기), `HARNESS_SPLIT_SUB=1` sub-커밋 재실행 가드 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경(Windows/PowerShell + bash)에서 6 케이스(pytest·grep·bash -n·python -m·rm -rf·none) 분기 시뮬레이션 통과
- pytest -m stage 2 passed
- 다운스트림 환경(Linux/macOS) 미테스트
- 화이트리스트 외 명령은 자동 실행 skip — 보안

### 검증
```bash
# stage 회귀 가드
python -m pytest .claude/scripts/test_pre_commit.py -m stage -q
```



## v0.29.1 — Phase 2-A 2단계: AC + CPS 시스템 강제 (efficiency overhaul)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | frontmatter `problem`·`solution-ref` 검증 + AC `Goal:` + 검증 묶음 추출 + CPS 박제 감지 (normalize_quote·verify_solution_ref·parse_ac_block 신설). 외형 룰 (UPSTREAM_PAT·META_M_PAT·rename/meta/WIP/docs-5줄 단독 skip) 폐기. `wip_kind`·`has_impact_scope` 폐기, `wip_problem`·`wip_solution_ref`·`ac_review`·`ac_tests`·`ac_actual` 출력 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 외형 metric 테스트 (TestStageBasic 4개·TestIntegMoveCommit 전체) deprecate. 시크릿 게이트·standard 폴백 테스트만 유지 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | 자기증명 적용 — solution-ref list + 검증 묶음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 필수 작업**:
- 신규 WIP·decisions·incidents·guides 작성 시 frontmatter `problem: P#`·`solution-ref:` (list) + AC `Goal:` + `검증:` 묶음 (review·tests·실측 3 키) 작성. 누락 시 commit 차단.
- 기존 50개 문서는 본 wave 밖 — 별 wave에서 backfill (점진).

### 자기증명 통과
본 commit 자체가 새 검증 시스템 통과:
```
pre_check_passed: true
wip_problem: P2
wip_solution_ref: S2 — "review tool call 평균 ≤4회 (부분)"; S2 — "docs-only 커밋이 skip 또는 micro로 분류됨"
ac_review: review-deep
ac_tests: pytest -m secret
ac_actual: AKIA 더미 staged + HARNESS_DEV=1 git commit → exit 1, 차단 확인
recommended_stage: deep
```

### 주의 — 외형 metric 폐기 영향
- `.claude/scripts/**` → deep 자동 격상 → 폐기. AC `검증.review` 작성자 선언이 결정
- `docs 5줄 이하` skip → 폐기. 줄 수 무관, AC 기반
- `WIP 단독`·`meta 단독`·`rename 단독` skip → 폐기. AC 기반
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목 → 코드에서 더 이상 읽지 않음. 다운스트림 그대로 둬도 동작 무관

### 한계 (별 wave)
- eval/SKILL.md CPS 무결성 감시 (`--harness` 박제 발견) — 본 wave 밖
- commit 스킬 5.3 자동 실행 코드 (tests·실측 화이트리스트 실행) — 본 wave 밖, 1단계에 SSOT 정의는 됨
- legacy 50개 문서 frontmatter backfill — 별 wave (다운스트림 영향)
- AC 미작성 진입점 결함 audit (write-doc·implementation 진입점) — 별 WIP

### 회귀 위험
- upstream 격리 환경 검증:
  - `pytest -m "secret or stage"` 6/6 통과 + 4 skip (TestIntegMoveCommit deprecate)
  - 본 commit 자체 자기증명 통과 (위 출력 참조)
- staged WIP 없는 hot-fix 케이스: standard 폴백 (이전 외형 metric 추정 대신 보수)

### 검증
```bash
python3 .claude/scripts/pre_commit_check.py
pytest -m "secret or stage"
```



## v0.29.0 — Phase 2-A 1단계: AC + CPS 시스템 정의 (efficiency overhaul)

### 변경 파일 (24개 — 시스템 정의 문서만, 코드 변경 0)

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/rules/docs.md` | 3-way merge | frontmatter `problem`·`solution-ref` SSOT 신설. AC 포맷 통합 (`Goal` + `검증` 묶음). CPS 면제 룰. 박제 감지 룰 |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | 단일 룰 재작성 — AC `검증.review` 그대로 stage 결정. 외형 metric 룰 폐기 (kind 라벨·줄 수·경로) |
| `.claude/rules/naming.md` | 3-way merge | 메타데이터 SSOT 참조 추가 (docs.md로 위임) |
| `.claude/rules/coding.md`·`external-experts.md`·`hooks.md`·`internal-first.md`·`memory.md`·`no-speculation.md`·`pipeline-design.md`·`security.md`·`self-verify.md` | 3-way merge | 각 룰 상단에 `defends: P#` 추가 (어느 Problem 막는지 추적) |
| `.claude/skills/implementation/SKILL.md` | 3-way merge | Step 0 강화 — CPS 매칭 + AC 묶음 1차 제안. WIP 템플릿 갱신 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 5 책임 재정의. Step 5.3 신설 — tests·실측 자동 실행 (화이트리스트만). 핸드오프 계약 갱신 |
| `.claude/agents/review.md` | 3-way merge | `serves: S2` + Solution 회귀 검증 루프 + 입력 블록 `wip_problem`·`wip_solution_ref` |
| `.claude/agents/{advisor,codebase-analyst,debug-specialist,doc-finder,performance-analyst,researcher,risk-analyst,threat-analyst}.md` | 3-way merge | 각 에이전트 frontmatter에 `serves: S#` 추가 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | starter 자체 WIP — AC 1단계 ✅ |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의 — 동작 변경 없음 (정의만)
- 본 버전은 **시스템 정의 SSOT만 갱신**. pre_commit_check.py 등 강제 코드는 변경 없음.
- 강제는 v0.29.1 (Phase 2-A 2단계)에서 — pre_commit_check이 새 SSOT 따라 frontmatter 검증·외형 metric 폐기.
- 다운스트림은 본 버전 적용 후 신규 문서 작성 시 새 형식 권장. **차단은 v0.29.1부터**.

### 폐기 마커 호환성
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목은 무시 (코드에서 더 이상 읽지 않음 — v0.29.1부터)
- 다운스트림이 그대로 둬도 동작 무관. 점진 마이그레이션

### 회귀 위험
- 코드 변경 0 — 동작 회귀 위험 없음
- 문서 SSOT 변경 — 다운스트림이 신규 문서 작성 시 새 형식 학습 부담

### 검증
```bash
# 룰 12개에 defends: 적용 확인
grep -L "^defends:" .claude/rules/*.md  # 0건 expect

# 에이전트 9개에 serves: 적용 확인
grep -L "^serves:" .claude/agents/*.md  # 0건 expect

# CPS 면제 (project_kickoff.md에 problem·solution-ref 없음)
grep -E "^(problem|solution-ref):" docs/guides/project_kickoff.md  # 0건 expect
```

---





**SSOT는 `MIGRATIONS.md`** — 본 파일은 보존용. 이동 시점 기준 그대로
박제되며 본문 갱신 안 함. 변경 이력은 git log가 담당.

---

## v0.28.8 — Phase 1 시크릿 hook 이중화 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/install-starter-hooks.sh` | 3-way merge | hook 본문에 시크릿 패턴 풀 grep 추가 (sb_secret·service_role·AKIA·sk_live·ghp·glpat·xox·AIza·sk-ant·PRIVATE KEY 등). `HARNESS_DEV=1` 분기 이전에 시크릿 검사 실행 — 우회 불가. HARNESS.json hook_installed 자동 갱신 |
| `scripts/install-secret-scan-hook.sh` | 자동 덮어쓰기 | HARNESS.json hook_installed 자동 갱신 추가 (다운스트림용). 패턴 풀 변경 없음 |
| `.claude/scripts/pre_commit_check.py` | 3-way merge | json import + hook 미설치 경고 stderr 출력 (`HARNESS.json hook_installed` 체크). starter/다운스트림별 설치 명령 안내 |
| `.claude/scripts/bash-guard.sh` | 3-way merge | `git commit` 차단 메시지에 "시크릿 line-confirmed 가드는 git pre-commit hook이 항상 실행 — 우회 불가" 추가. 안내 톤 갱신 |
| `.claude/HARNESS.json` | 사용자 전용 (skip) | starter 자체에서 `hook_installed: true` 추가. 다운스트림은 install 스크립트가 자동 추가 |
| `README.md` | 사용자 전용 (skip) | secret-scan hook "선택" → "필수" 격상 + 우회 경로 안내 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 추가 작업 (필수)**:
1. `bash scripts/install-secret-scan-hook.sh` 실행 — 시크릿 hook 설치 (`HARNESS.json` `hook_installed` 자동 갱신)
2. 미설치 상태에서 commit 시 `pre_commit_check.py`가 stderr 경고 출력

### 주의
- **threat-analyst 발견**: 이전까지 `HARNESS_DEV=1 git commit` 경로가 시크릿 가드 완전 우회. bash-guard 통과(L101-103) + pre_commit_check 미호출 + hook도 통과. 본 버전이 hook 본문에 시크릿 검사 박아 우회 차단 (안전망 5/10 → 7.5/10).
- **`git commit --no-verify` 한계**: hook 자체 우회 — Phase 1으로 막을 수 없음. README 경고 + bash-guard 차단(Claude Code 내)으로 대응.
- **면제 위치**: `^\.claude/(scripts|agents|rules|skills|memory)/` 경로는 시크릿 패턴 SSOT 문서화 위치이므로 면제 (S1_LINE_EXEMPT와 동일).

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash) 검증:
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: `HARNESS_DEV=1 git commit` + AKIA 더미 시크릿 → exit 1 차단 확인
  - 실측: `hook_installed=false` 시 stderr 경고 출력 확인
- PowerShell·WSL 환경 미테스트 (운용 검증 필요)
- 다운스트림이 secret-scan hook 미설치 시 안전망 부재 — pre-check 경고가 유일 알림

### 검증
```bash
bash .claude/scripts/install-starter-hooks.sh   # starter용
bash scripts/install-secret-scan-hook.sh        # 다운스트림용
pytest -m "secret or stage"
```

---

## v0.28.7 — HARNESS_UPGRADE 환경변수 폐기 (C 항목 — 옵션 B)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | L108 `HARNESS_UPGRADE` 정의 제거, L549 룰 0 분기 제거. 환경변수 의존 0 |
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(HARNESS_UPGRADE=1 bash *)` 제거 |
| `.claude/rules/staging.md` | 3-way merge | 1단계 룰 0번 제거 + 폐기 안내 블록. review skip은 commit 스킬 `--no-review`로 흡수 |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 — `HARNESS_UPGRADE=1 git commit` → `/commit --no-review`. "다른 스킬과의 관계" 표 commit 항목 갱신 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **다운스트림 영향**: 기존에 `HARNESS_UPGRADE=1` 환경변수를 쓰던 스크립트·alias가 있다면 **자연 무시**(분기 제거됨). 명시적 정리 권장 — `git grep HARNESS_UPGRADE`로 확인 후 제거.
- **review skip 대체**: harness-upgrade 자체는 본 버전부터 `/commit --no-review` 호출. 사용자가 직접 review skip 필요하면 동일하게 `--no-review` 플래그 사용.
- 회고적 기록(README v0.26.9 변경 이력, MIGRATIONS L398, hn_upstream_anomalies.md 본문)은 당시 상태 보존 — 변경 안 함.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `from pre_commit_check import ENOENT_PATTERNS` import OK
  - `pytest -m "secret or stage"` 12/12 통과
- 활성 코드 잔여 참조 0 (회고적 기록 5건만).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
python3 -m pytest .claude/scripts/test_pre_commit.py -m "secret or stage"
grep -l HARNESS_UPGRADE .claude/scripts/ .claude/rules/ .claude/skills/  # 활성 코드 0건
```

---

## v0.28.6 — upstream anomalies B·D·E·F 일괄 wave (보안·LF·worktree·sanity)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(rm *)`·`Bash(export *)` 제거. 와일드카드 삭제·임의 export는 starter 기본 권한에서 빠짐 (B) |
| `.gitattributes` | 신규 | `* text=auto eol=lf` + 바이너리 제외. Windows + Git Bash 환경에서 3-way merge 통째 충돌 방지 (D) |
| `.claude/scripts/bash-guard.sh` | 3-way merge | 검증 2.5 추가 — `git worktree add` 차단. CLAUDE.md 절대 규칙 코드 강제. list/remove/prune은 통과 (E) |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 0.1 worktree 잔여 자동 정리(clean 자동/dirty 안내) + Step 1 fetch 후 installed_from_ref sanity check + Step 5 ours `tr -d '\r'` LF 정규화 + Step 8.1 위험 패턴 명시 승인 강제 + Step 10 갱신 후 sanity check (B·D·E·F) |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 사용자 전용 (skip) | starter 자체 WIP 갱신 — 다운스트림은 건드리지 않음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **B 위험 권한 제거**: 다운스트림이 `Bash(rm *)`·`Bash(export *)`를 이전 업그레이드에서 받았다면 Step 8.1이 자동 제거하지 않는다 (사용자 추가로 분류). 직접 `.claude/settings.json`에서 제거 검토.
- **D LF 정규화**: 신규 클론은 `.gitattributes`로 보호. 기존 워킹트리(autocrlf 환경)는 `git add --renormalize .` 1회 실행 권장. harness-upgrade 자체는 Step 5에서 `tr -d '\r'`로 런타임 보호.
- **E worktree 차단**: `git worktree add` 시도 시 exit 2. 잔여가 있으면 harness-upgrade Step 0.1이 clean한 것만 자동 제거. dirty는 안내만 — 사용자 직접 정리.
- **F sanity check**: Step 1 fetch 직후 + Step 10 갱신 후 양쪽. 한 지점만으로는 다음 업그레이드 시점까지 stale ref가 묻혀 ADDED 부풀림 발생.
- C(HARNESS_UPGRADE 환경변수 의미 일관화)는 미해결 — 별 wave.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증 범위:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `bash -n .claude/scripts/bash-guard.sh` 구문 OK
  - `echo '{"tool_input":{"command":"git worktree add foo"}}' | bash bash-guard.sh` → exit 2 차단 실측
  - `echo '{"tool_input":{"command":"git worktree list"}}' | bash bash-guard.sh` → exit 0 통과 실측
- harness-upgrade SKILL.md 변경분은 자동 검증 불가 — 다운스트림 업그레이드 사이클에서 운용 검증 필요.
- `.gitattributes` 첫 도입 — 기존 워킹트리에서 `git add` 시 CRLF→LF 정규화 경고 발생 (의도된 동작).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
bash -n .claude/scripts/bash-guard.sh
echo '{"tool_input":{"command":"git worktree add foo"}}' | bash .claude/scripts/bash-guard.sh  # exit 2
echo '{"tool_input":{"command":"git worktree list"}}' | bash .claude/scripts/bash-guard.sh    # exit 0
```

---

## v0.28.5 — docs_ops·harness_version_bump·task_groups encoding="utf-8" 일괄 (G Phase 3)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `git()` helper에 `encoding="utf-8"` 추가. 한글 git 출력에서 cp949 디코딩 실패 방지 |
| `.claude/scripts/harness_version_bump.py` | 3-way merge | `run()` helper에 `encoding="utf-8"` + `or ""` 방어 |
| `.claude/scripts/task_groups.py` | 3-way merge | 동일 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- G 항목(Windows + 한글 환경 무한 막힘) 마지막 wave. Phase 1·2가 `pre_commit_check.py`의 갈래 1·2를 해소했고, 본 Phase 3은 같은 패턴이 다른 스크립트에 반복돼 있던 것을 일괄 정리.
- 세 파일 모두 `def main()` + `if __name__ == "__main__":` 구조는 이미 적용돼 있어 추가 리팩토링 불필요.
- WIP `harness--hn_upstream_anomalies.md` G 항목 ✅ 해결로 마킹. B·C·D·E·F는 미해결 — 별 wave로 진행.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과.
- 세 파일의 subprocess 호출 변경 — 한글 미포함 출력은 기존과 동일 동작. UTF-8 디코딩 가능한 모든 입력 처리.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"
```

---

## v0.28.4 — pre_commit_check.py main 함수화 (G Phase 2 — script-as-module 결함 해소)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | 580줄 module-level main 로직 → `def main() -> int:` 함수화 + `if __name__ == "__main__": sys.exit(main())` 보호. ENOENT_PATTERNS만 module-level 유지 (test가 import). 입력 수집·검사·출력 전부 main() 안으로 이동 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | `TestModuleImportSafe::test_import_does_not_exit` 신규 — staged 변경 유무 무관 import 후 sys.exit 발생 안 함 검증 (`enoent` marker) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **import 시 main 로직 미실행**: `from pre_commit_check import X`가 모듈 import만 수행. 기존 module-level mutable 변수(staged_files·name_status_raw 등)에 outer scope에서 직접 접근하던 코드가 있다면 → 본 변경으로 영향. test_pre_commit.py 외 import 사용처 없음 확인.
- ENOENT_PATTERNS 정규식만 module-level 유지. 다른 정규식(S1_LINE_PAT·SKIP_TODO 등)은 main() 안에 있음 — main 호출당 1회 컴파일. 미미.
- Phase 1(v0.28.3)의 `encoding="utf-8"` fix와 함께 동작. 둘 다 갈래 1·2 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과 확인.
- Linux/macOS·다운스트림 환경 미테스트. 580줄 들여쓰기 변경이라 실측 회귀 모니터링 권장.
- T40.1 wip-sync abbr 매칭 테스트는 본 작업 sandbox 환경에서 fixture 격리 갭으로 fail (본 fix 무관) — fixture가 starter repo clone 시 작업 중 WIP가 따라가서 같은 abbr 충돌. 별 issue.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"  # 27/27 통과
python -c "import sys; sys.path.insert(0, '.claude/scripts'); from pre_commit_check import ENOENT_PATTERNS; print(ENOENT_PATTERNS)"  # import 후 sys.exit 없음
```

---

## v0.28.3 — pre_commit_check.py run() encoding="utf-8" (G Phase 1)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `run()`에 `encoding="utf-8"` + `or ""` 방어 추가. Windows + 한글 staged diff에서 system locale(cp949) 디코딩 실패로 `stdout=None` 되던 결함 해소 |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 신규 | 다운스트림 발견 이상 징후 묶음 SSOT (B·C·D·E·F·G) — G Phase 1만 해결, 나머지 미해결 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- Phase 1만으론 `from pre_commit_check import X` 회귀 가드 미적용 — Phase 2(main 함수화) 후 박을 예정.
- staged 변경이 없을 때 직접 호출(`python pre_commit_check.py`)은 PYTHONUTF8 없이도 정상 동작 확인.
- 다운스트림 영향: Windows 사용자가 한글 commit 메시지·diff에서 겪던 무한 차단 부분 해소 (직접 호출 경로). Linux/macOS 미영향.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash, 한글 staged diff)에서 직접 호출 통과 실측 확인.
- import 경로(staged 시 sys.exit)는 Phase 2까지 미해소 — 회귀 가드 테스트 추가도 Phase 2 의존.

### 검증
```bash
unset PYTHONUTF8; python .claude/scripts/pre_commit_check.py  # cp949 실패 안 함
pytest -m secret  # 기존 회귀 가드 통과
```

---

## v0.28.2 — pre-check 시크릿 line 면제 갭 + docs_ops untracked move 갭

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `S1_LINE_EXEMPT` 정규식을 `^\.claude/(scripts\|agents\|rules\|skills\|memory)/`로 확장. 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치(agents·rules·skills·memory)가 line-confirmed로 잘못 차단되던 문제 해소 |
| `.claude/scripts/docs_ops.py` | 3-way merge | `cmd_move` fallback에서 `git ls-files --error-unmatch`로 src 인덱스 존재 여부 확인 후 `git rm --cached` 시도. untracked WIP 이동이 매번 returncode 1로 실패하던 갭 해소 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 회귀 테스트 2건 추가 — `TestSecretScan::test_harness_doc_line_exempt`, `TestMoveUntrackedWip::test_untracked_move_succeeds` |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- 다운스트림에서 `.claude/agents/threat-analyst.md` 같은 패턴 SSOT 문서를 수정하면
  `🚫 pre-check 차단 — 시크릿 line-confirmed (s1_level)` 메시지가 발생하던 false-positive 해소.
- 면제 범위는 `.claude/(scripts|agents|rules|skills|memory)/`로 한정. `docs/`·사용자 코드(`src/` 등)는 여전히 line 스캔 적용.
- untracked WIP fallback fix로 implementation→commit 흐름의 잠재 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내에서는 영향 없음.
  `pytest -m secret` 4/4 통과, untracked move 직접 sandbox 검증 통과.
- 별개 환경 결함(Windows cp949 디코딩 + module-level main 로직 import)으로
  `pytest -m docs_ops`는 본 환경에서 실행 불가 → 관련 테스트는 `PYTHONIOENCODING=utf-8`
  + 임시 repo subprocess로 우회 검증. 별도 추적 필요.

### 검증
```bash
pytest -m secret
PYTHONIOENCODING=utf-8 pytest .claude/scripts/test_pre_commit.py::TestMoveUntrackedWip
```

---

## v0.28.1 — completed 전환 차단 — 코드블록 안 면제

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `_extract_body`에 코드블록(``` ```·`~~~`) 추적 추가. 코드블록 안 라인은 차단 검사 대상 아님 |
| `.claude/rules/docs.md` | 3-way merge | "completed 전환 차단" 섹션에 "코드블록 안 면제" 룰 명시 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- AC 포맷 예시·문법 설명을 코드블록에 박은 WIP들이 completed 이동 시 거짓 차단되던 문제 해소.
- 회고형 차단(v0.27.6) + 코드블록 면제(이번)로 차단 룰 정밀도가 두 단계 향상.

### 검증
```bash
python3 .claude/scripts/docs_ops.py move <테스트용 WIP>
```

---

## v0.27.3 — Karpathy 원칙 적용 (Phase 1): 코딩 컨벤션·행동 원칙·AC 기반 검증 구조

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `CLAUDE.md` | 3-way merge | `## 행동 원칙` 섹션 추가 (Think Before Coding + Goal-Driven) |
| `.claude/rules/coding.md` | 3-way merge | Surgical Changes 원칙·금지 패턴 추가 |
| `.claude/rules/self-verify.md` | 3-way merge | Goal-Driven 원칙, AC 완료 기준, TDD/fail-first |
| `.claude/rules/docs.md` | 3-way merge | WIP AC 포맷 확장 (`Goal:` + `영향 범위:`) |
| `.claude/rules/staging.md` | 3-way merge | AC 기반 검증 원칙 추가, 연결 규칙 B·C에 AC 조건 추가 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Stage별 행동 직접 서술 → staging.md 포인터로 교체 |

### 변경 내용
- CLAUDE.md에 구현 전 사고 원칙(Think Before Coding, Goal-Driven) 추가
- coding.md에 Surgical Changes 원칙 5개 + 금지 패턴 5개 명문화
- self-verify.md: AC 체크박스가 완료 기준임을 명시, TDD/fail-first 원칙 추가
- docs.md: WIP AC에 `Goal:` + `영향 범위:` 항목 포맷 추가
- staging.md: AC 기반 검증 원칙 추가, `영향 범위:` → deep 트리거, AC 전부 [x] → micro 완화
- commit/SKILL.md: staging SSOT 충돌 해소 (Stage별 행동 재서술 제거)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

### 회귀 위험
- staging.md 연결 규칙 B·C에 AC 기반 조건 추가됨 — 기존 신호 체계는 유지
- 다운스트림 CLAUDE.md에 `## 행동 원칙` 섹션이 추가됨 (기존 절대 규칙 위치 변경 없음)

---

## 포맷

```markdown
## vX.Y — 한 줄 요약

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/foo/SKILL.md` | 3-way merge | 변경 이유 한 줄 |
| `.claude/scripts/bar.py` | 자동 덮어쓰기 | |
| `.claude/agents/baz.md` | 신규 추가 | |

처리 값: `자동 덮어쓰기` · `3-way merge` · `신규 추가` · `삭제`

### 변경 내용
이번 버전에서 달라진 것. 다운스트림이 맥락 파악용.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.
- ...

**수동 적용**: upgrade 후 직접 실행. 안 하면 미동작.
- 없음  ← 없을 때도 명시

### 검증
적용 후 확인 방법.
```

---

## v0.27.2 — 도메인 시스템 갭 수정 및 문서 참조 정합성 복구

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | docs_ops 함수 import + S9 WIP 도메인 추출 수정 + 경로→도메인 3단계 구현 |
| `.claude/scripts/docs_ops.py` | 3-way merge | extract_path_domain_map 예시 블록 오파싱 수정 |
| `.claude/scripts/task_groups.py` | 자동 덮어쓰기 | NAMING_MD dead code 제거 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | _add_path_domain_map 헬퍼 실제 매핑 블록 참조로 수정 |
| `.claude/rules/naming.md` | 3-way merge | docs-ops.sh → docs_ops.py 참조 수정 + 실제 매핑 코드블록 추가 |
| `.claude/rules/docs.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py 참조 수정 (4곳) |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | pre-commit-check.sh → pre_commit_check.py 참조 수정 (3곳) |
| `.claude/rules/security.md` | 자동 덮어쓰기 | install-secret-scan-hook.sh → install-starter-hooks.sh |
| `.claude/agents/review.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py, docs-ops.sh → docs_ops.py |
| `.claude/agents/doc-finder.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py |
| `.claude/agents/threat-analyst.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py + bash 스니펫 S1_LINE_PAT 기반으로 교체 |

### 변경 내용

**갭 1 — WIP 도메인 추출 오류 수정**: `pre_commit_check.py` S9 블록에서 WIP 파일
도메인을 라우팅 태그(`decisions`, `guides`)로 잘못 추출하던 문제 수정.
`docs_ops.detect_abbr()` + abbr→domain 역매핑으로 실제 도메인(`harness`, `meta`) 추출.
WIP-only 커밋에서 critical 도메인이 deep으로 격상되지 않던 문제 해소.

**갭 2 — naming.md 파싱 중복 제거**: `pre_commit_check.py`가 `docs_ops.py`의
`extract_abbrs`, `detect_abbr`, `extract_path_domain_map`, `path_to_domain`을
동적 import해 재사용. naming.md를 두 스크립트가 별도 파싱하던 중복 제거.

**갭 3 — 경로→도메인 매핑 3단계 구현**: staging.md 명세 4단계 중 3단계
(naming.md 경로→도메인 매핑)가 구현되지 않던 문제 수정. naming.md에
`실제 매핑` 코드블록 영역 추가 — 다운스트림이 여기에 경로 매핑 등록 시 S9에 반영.

**문서 참조 정합성**: 존재하지 않는 `docs-ops.sh`, `pre-commit-check.sh`,
`install-secret-scan-hook.sh` 참조를 실제 파일명으로 일괄 수정 (총 14곳).

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: naming.md `## 경로 → 도메인 매핑` 섹션 하단 `실제 매핑` 코드블록에
프로젝트 코드 폴더 경로 매핑 추가 권장 (S9 도메인 등급 신호 정확도 향상).
예: `src/payment/**     → payment`

### 검증
`python3 -m pytest .claude/scripts/test_pre_commit.py -q` → 56 passed.

---

## v0.27.1 — eval 기본 모드 보고 구조 개선 (거시/미시 계층 + memory 저장)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/eval/SKILL.md` | 3-way merge | 기본 모드 절차 4→6단계 확장 |

### 변경 내용

`/eval` 기본 모드 절차에 분류(4)·보고(5)·저장(6) 단계 추가.

- 발견된 간극을 **거시**(CPS 방향 이탈) / **단기 블로커**(다음 작업 차단) / **장기 부채**(방치 시 위험) 세 층으로 분류
- 대화 출력은 거시 요약 + 단기 블로커만 간결하게, 장기 부채 상세는 memory 참조로 압축
- eval 완료 시 항상 `.claude/memory/project_eval_last.md`에 전체 상세를 덮어쓰기 저장 + `MEMORY.md` 인덱스 갱신 (0건이어도 실행)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`/eval` 실행 후 `.claude/memory/project_eval_last.md` 생성 여부 확인.

---

## v0.27.0 — UserPromptSubmit debug-guard 훅 신설

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/debug-guard.sh` | 신규 추가 | UserPromptSubmit 키워드 감지 스크립트 |

### 변경 내용
사용자 메시지에 "에러", "버그", "오류", "원인" 등 키워드가 감지되면
`debug-specialist` 에이전트를 먼저 호출하도록 Claude 컨텍스트에 주입.
Claude가 직접 추측 수정으로 진행하는 패턴을 시스템 레벨에서 차단.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`echo '{"prompt":"에러났어 원인을 찾아"}' | bash .claude/scripts/debug-guard.sh`
→ `⚠️ [debug-guard]` 메시지 출력되면 정상.

---

## v0.26.9 — harness-upgrade 커밋 분기 + MIGRATIONS 변경 파일 섹션

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 + Step 3 변경 파일 표 참조 추가 |
| `docs/harness/MIGRATIONS.md` | 자동 덮어쓰기 | `### 변경 파일` 섹션 포맷 추가 |

### 변경 내용

- `harness-upgrade/SKILL.md` Step 10: 커밋 시 `CONFLICT_RESOLVED` 유무로 분기. 충돌 해소 파일 없으면 `HARNESS_UPGRADE=1`로 review skip, 있으면 해당 파일만 `--quick` review
- `harness-upgrade/SKILL.md` Step 3: MIGRATIONS.md `### 변경 파일` 표를 git diff보다 우선 참조해 처리 방식 결정
- `MIGRATIONS.md` 포맷에 `### 변경 파일` 섹션 추가 — 파일별 처리 방식(`자동 덮어쓰기`·`3-way merge`·`신규 추가`·`삭제`) 명시

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.8 — commit Step 4 다운스트림 skip 명시

### 변경 내용

- `commit/SKILL.md` Step 4: `is_starter` 값을 먼저 확인해 `false`(다운스트림)이면 Step 4 전체를 건너뛰도록 명시. 기존에는 스크립트가 내부적으로 exit했지만 Step 자체는 실행됐음

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.7 — harness_version_bump.py HEAD 버전 기준 수정

### 변경 내용

- `harness_version_bump.py`: `current` 버전을 디스크(HARNESS.json)가 아닌 HEAD에서 읽도록 수정. commit Step 4에서 HARNESS.json을 디스크에 먼저 쓰고 staged하면 `current`가 이미 범프된 버전을 가리켜 "범프 필요" 오탐 발생하던 버그 수정

### 적용 방법

**자동 적용**: 스크립트 갱신

**수동 적용**: 없음

---

## v0.26.6 — harness-upgrade Step 9.7 오탐 수정 + Step 10.4 제거

### 변경 내용

- harness-upgrade Step 9.7: `grep "- \[ \]"` 패턴이 백틱 인라인 코드(`` `- [ ]` ``)까지 오탐하던 문제 수정 — `grep -v` 추가
- harness-upgrade Step 10.4 제거: MIGRATIONS.md는 Step 3 자동 덮어쓰기로 이미 단일 섹션 유지됨. Claude가 섹션을 수동 삭제하는 불안정한 단계 제거

### 적용 방법

**자동 적용**: harness-upgrade SKILL.md 갱신

**수동 적용**: 없음

---

## v0.26.5 — hook 버전 체크 제거 + pre-check 경고로 이전

### 변경 내용

- `install-starter-hooks.sh`: hook의 버전 범프 체크 로직 제거. 버전 판단은 commit Step 4(Claude)가 담당
- `pre_commit_check.py`: is_starter 전용 버전 미범프 경고 추가 (차단 아님 — `risk_factors`에 기록)

### 적용 방법

**자동 적용**: 스크립트 갱신. hook은 `harness-sync` 또는 `bash .claude/scripts/install-starter-hooks.sh` 재실행으로 갱신.

**수동 적용**: 없음

---

