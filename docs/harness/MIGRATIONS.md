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

**현재 버전 섹션 1개만 유지.** harness-upgrade 완료 후 해당 섹션 삭제.
버전 히스토리는 upstream git log가 SSOT (`git log --oneline --grep "(v0\."` 로 조회).

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

## 포맷

```markdown
## vX.Y — 한 줄 요약

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

