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

## v0.36.0 — BIT(Bug Interrupt Triage) 규칙 신설 + CPS 순환 루프 설계 (2026-05-05)

### 변경 내용
- `rules/bug-interrupt.md` 신설 — 스코프 외 버그 발견 시 Q1/Q2/Q3 결정 트리
  자율 판단. 판단 기준 SSOT를 AC+CPS+security.md로 외부화
- `implementation/SKILL.md` Step 3에 BIT 참조 추가
- `rules/docs.md` CPS 변경 권한 — Problem 추가를 BIT Q3 경로에서도 Claude 단독 가능으로 명시

### 적용 방법
자동 적용 (harness-upgrade가 rules/ 갱신).

### 수동 적용
없음.

---

## v0.35.3 — CLAUDE.md 행동 원칙 AC·CPS 실질 내용으로 교체 (2026-05-05)

### 변경 내용
- CLAUDE.md "행동 원칙" 섹션을 추상 원칙(Think Before Coding·Goal-Driven Execution)에서
  AC·CPS 실질 내용(형식·필수 필드·SSOT 링크)으로 교체

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.

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

