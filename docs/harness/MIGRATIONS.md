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

## v0.26.2 — 검증 파이프라인 강화 + MIGRATIONS.md 구조 재설계

### 변경 내용

- MIGRATIONS.md: 현재 버전 1개만 유지 구조로 재설계. 버전 히스토리는 upstream git log가 SSOT
- `docs/harness/migration-log.md` 경로 확정 (구 루트 경로 오류 수정)
- harness-upgrade Step 10: 업그레이드 완료 후 MIGRATIONS.md 해당 버전 섹션 삭제 추가
- commit Step 4: 버전 범프 확정 후 MIGRATIONS.md 섹션 자동 작성 절차 추가
- implementation Step 2.5: AC 검증 필수화 (자동화 가능/불가 구분 + 실행 기록 의무)
- implementation Step 4: CPS 갱신 없음도 WIP ## 결정 사항에 명시 의무

### 적용 방법

**자동 적용**:
- MIGRATIONS.md 구조 교체 (이 파일)
- harness-upgrade·commit·implementation SKILL.md 갱신

**수동 적용**:
- [ ] **migration-log.md 경로 이동** — 루트에 `migration-log.md`가 있으면 `docs/harness/`로 이동:
  ```bash
  git mv migration-log.md docs/harness/migration-log.md
  ```

### 검증

```bash
# migration-log 경로 확인
grep "migration-log" .claude/skills/harness-upgrade/SKILL.md | grep -v "docs/harness" | grep "migration-log\.md" && echo "❌ 루트 경로 잔존" || echo "✅ 정상"
```

---

## v0.26.1 — starter 전용 스킬 자기 삭제 + starter_skills 병합 버그 수정

### 변경 내용

- harness-init·adopt: 완료 시 자기 자신을 삭제 (`rm -rf .claude/skills/harness-*`)
- harness-upgrade Step 10: `starter_skills` 키 동기화 추가 — 구버전 다운스트림(키 없거나 null) 폴백 `"harness-init,harness-adopt"` 하드코딩
- MIGRATIONS.md: 현재 버전 1개만 유지 구조로 재설계. 기존 히스토리 섹션 제거
- `docs/harness/migration-log.md` 경로 확정 (구 루트 경로 오류 수정)

### 적용 방법

**자동 적용**:
- harness-upgrade Step 10이 `starter_skills` 키를 HARNESS.json에 동기화
- MIGRATIONS.md 구조 교체 (이 파일)

**수동 적용**:
- [ ] **starter 전용 스킬 폴더 삭제** — v0.26 이전에 복사된 경우 삭제 권장 (잔존해도 실행하지 않으면 무해):
  ```bash
  rm -rf .claude/skills/harness-init .claude/skills/harness-adopt .claude/skills/harness-dev
  ```
  v0.26.1+부터는 harness-init·adopt 완료 시 자동 삭제됨.
- [ ] **migration-log.md 경로 이동** — 루트에 `migration-log.md`가 있으면 `docs/harness/`로 이동:
  ```bash
  git mv migration-log.md docs/harness/migration-log.md
  ```

### 검증

```bash
# starter_skills 확인
python3 -c "import json; d=json.load(open('.claude/HARNESS.json')); print(d.get('starter_skills'))"
# 기대: harness-init,harness-adopt
```
