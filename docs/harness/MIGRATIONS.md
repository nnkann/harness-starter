---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-04-28
---

# 다운스트림 마이그레이션 가이드

`harness-upgrade` 스킬이 각 버전 업그레이드 시 이 문서를 읽어 다운스트림에
표시한다. **upstream 소유 — 다운스트림은 읽기만.**

**최신 5개 버전 본문만 유지** (v0.30.1 정책). 6번째 이전 버전은
`MIGRATIONS-archive.md`로 자동 이동 — `harness_version_bump.py --archive`가
이동 처리. 더 오래된 업그레이드 추적은 archive 또는 git log
(`git log --oneline --grep "(v0\."`).

다운스트림은 자기 환경 마지막 upgrade 이후 누적된 버전을 읽으면 된다.
5개 본문 기준 약 1~2개월 분량. 그보다 오래 누적된 다운스트림은 archive
참조.

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

---

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

---

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

---

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

---

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

---

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

