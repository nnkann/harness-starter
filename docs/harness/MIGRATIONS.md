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

## v0.37.0 — session-start.py 신설 — bash spawn 제거로 세션 시작 66% 단축 (2026-05-05)

### 변경 내용
- `scripts/session-start.py` 신설 — session-start.sh의 완전 Python 재작성
  bash spawn 23~25회 → git subprocess 최소화. 실행 시간 0.9초 → 0.28초 (66% 단축)
- `settings.json` SessionStart hook: `bash session-start.sh` → `python3 session-start.py`

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·settings.json 갱신).

### 수동 적용
없음. python3는 이미 필수 의존성.

### 회귀 위험
- session-start.sh는 삭제되지 않음 (이 버전). 롤백 필요 시 settings.json 복원.
- src/ TODO 감지는 Python glob으로 대체 — bash grep과 동일 결과 확인됨.
- upstream 격리 환경(Windows/Git Bash)에서 0.28초 실측. Linux/macOS 미테스트.

---

## v0.36.4 — BIT 루프 단절 수정 — eval_cps_integrity NEW 집계 + bug-interrupt 문서 부패 제거 (2026-05-05)

### 변경 내용
- `eval_cps_integrity.py`: `P#:.*NEW` 패턴 grep 추가 — docs/WIP/·decisions/ 스캔 후 미처리 NEW 플래그 집계 출력. eval --harness 고리 4 단절 수정
- `rules/bug-interrupt.md` 순환 루프 다이어그램: "Phase 2 구현 예정" → "Phase 2 완료" (문서 부패 제거)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·rules/ 갱신).

### 수동 적용
없음.

---

## v0.36.3 — BIT Phase 4 — CPS staged 경고 + implementation Step 0 NEW 플래그 인식 (2026-05-05)

### 변경 내용
- `pre_commit_check.py` 룰 2: project_kickoff.md staged 시 다른 staged 파일 중 solution-ref 있으면 "인용 박제 재확인 필요" 경고 출력
- `implementation/SKILL.md` Step 0 Problem 매칭 표: BIT NEW 플래그 항목 추가 — WIP `## 발견된 스코프 외 이슈`의 `P#: NEW` 항목을 P# 등록 후보로 자동 인식

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.

---

## v0.36.2 — BIT Phase 3 — eval --harness NEW 플래그 집계 + pre-check CPS empty 경고 (2026-05-05)

### 변경 내용
- `eval/SKILL.md` --harness 보고 섹션: CPS 무결성에 `NEW 플래그 미처리` 집계 항목 추가
- `pre_commit_check.py`: `get_cps_text()` 빈 문자열 반환 시 "CPS 본문 없음 — 박제 감지 불가" 경고 추가 (harness-init 미완료 환경 사각지대 차단)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.

---

## v0.36.1 — BIT Phase 2 — session-start.sh 이슈 감지 + Step 0.8 기록 의무 (2026-05-05)

### 변경 내용
- `session-start.sh` 블록 2: WIP 파일에 `## 발견된 스코프 외 이슈` 섹션 감지 시
  세션 시작 알림. `problem: NEW` 플래그 있으면 "CPS 신규 P# 검토 필요" 강조
- `implementation/SKILL.md` Step 0.8: "분리 불필요" 판정 시 탐색 결과 기록 의무 명시 (갭 1 차단)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.

