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

## v0.35.2 — CLAUDE.md 절대 규칙 + 진입점 보강 (2026-05-05)

### 변경 내용
- CLAUDE.md 절대 규칙에 `docs/WIP/ 파일 Write 직접 생성 금지` 추가
- CLAUDE.md 진입점 표에 "문서 생성 (코드 작업 수반) → /implementation" 항목 추가
- CLAUDE.md `<important>` 태그 조건에 Write 도구 직접 사용 명시

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.

---

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

