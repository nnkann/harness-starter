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

---

## v0.34.8 — completed 봉인 — 본문 마크다운 링크 경로 교체 면제

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 면제에 "본문 마크다운 링크 경로 교체" 추가: hunk 내 삭제(-) 라인이 있는 상태에서 링크 패턴(`[...](...)`)을 포함한 추가(+) 라인은 면제. 순수 추가(삭제 없는 링크 줄 추가)는 기존과 동일하게 차단
- `.claude/scripts/tests/test_pre_commit.py` — T42.7(링크 경로 교체 면제), T42.8(순수 추가 차단) 회귀 테스트 추가

### 적용 방법

자동 적용. 수동 작업 없음.

### 회귀 위험

- 면제 조건은 `-U0` diff 기준 hunk 단위. 같은 hunk에 `-` 없이 `+`만 있는 링크 줄은 여전히 차단
- upstream 격리 환경(Windows)에서 pytest gate 20/20 통과 확인. Linux/macOS 미테스트

---

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

---

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

---

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

