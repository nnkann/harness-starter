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

## v0.37.5 — review tool call 과다 소모 근본 수정 (2026-05-06)

### 변경 내용
- `skills/commit/SKILL.md` — `## 지시` 블록: "영향 범위 파일 Read" 능동 권유 → "AC+컨텍스트로 판단 가능하면 Read 금지, Read+Grep 합계 3회 이내" 로 교체
- `agents/review.md` — `## 한도`: maxTurns 6→10 텍스트 동기화, "Read+Grep 3회 이내·8회 사용 후 추가 Read 금지" 명시

### 배경
commit/SKILL.md `## 지시`의 "영향 범위 항목이 있으면 해당 파일 Read" 문구가 AC 항목 N개당 Read N회를 유도. review.md의 "Read 최대 2회" 제한이 user prompt에 없어서 시스템 프롬프트 제한이 무시됨. (incident hn_review_maxturns_verdict_miss 5번째 재발 후 근본 수정)

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

---

## v0.37.4 — review maxTurns 6→10 + enforced-by/defends-by 정규식 오탐 수정 (2026-05-06)

### 변경 내용
- `agents/review.md` — `maxTurns: 6` → `maxTurns: 10` (verdict 출력 턴 확보)
- `eval_cps_integrity.py` — `enforced_empty_pat`: 마지막 컬럼이 아닌 중간 컬럼 구조 대응, 빈 문자열 always-match 제거
- `eval_cps_integrity.py` — `no_rule_pat`: 빈 문자열 대안 제거, "—"/"-" 명시 감지만

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

---

## v0.37.3 — 하네스 유기체화 Phase 1~6 완료 (2026-05-06)

### 변경 내용
- `eval_cps_integrity.py` — `check_harness_map()` 추가: HARNESS_MAP.md vs 실제 파일 단절 감지 (rules/skills/agents/scripts 4섹션 + enforced-by 공백 + defends-by 공백)
- `.claude/HARNESS_MAP.md` — 유기체 구조 섹션 추가 (CPS=뇌·MAP=대혈관·docs/=미세혈관), 규칙 간 참조 맵 갱신
- `agents/review.md` — 카테고리 8 "SSOT 문서 미완독 감지" 추가 + HARNESS_MAP.md 역추적 진입점 절차
- `rules/docs.md` — "하네스 구성요소 메타데이터" 섹션 추가: defends:/serves:/enforced-by: 필드 형식 + Layer 배치 기준 + 판단 트리
- `skills/harness-upgrade/SKILL.md` — Step 9.3 신설: HARNESS_MAP.md 전파 확인
- `scripts/downstream-readiness.sh` — 섹션 4-pre 추가: HARNESS_MAP.md 존재 체크
- `CLAUDE.md` — "하네스 신경망 허브" 섹션 추가: HARNESS_MAP.md 참조 + CPS 기억 귀환 구조

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.

---

## v0.37.2 — P7 신설 + HARNESS_MAP.md 임시 생성 + defends 매핑 정정 (2026-05-06)

### 변경 내용
- `docs/guides/project_kickoff.md` — P7 "시스템 구성 요소 간 관계 불투명" 신설 (P1·P6의 구조적 원인)
- `.claude/HARNESS_MAP.md` — 하네스 신경망 허브 임시 생성 (CPS·Rules·Skills·Agents·Scripts·Domains 양방향 관계 지도)
- `.claude/rules/anti-defer.md`, `docs.md`, `memory.md`, `naming.md` — `defends: P5` → `defends: P7` 정정
- `.claude/scripts/eval_cps_integrity.py` — `PROBLEM_INFLATION_THRESHOLD` 고정 6 → `max(8, problem_count + 2)` 동적 계산
- `.claude/scripts/session-start.sh` — session-start.py로 완전 대체됨, 파일 삭제

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
- `security.md`는 다운스트림 앱 전용. 필요 시 `.claude/rules/security.md` 직접 추가 (starter_skills에 포함 안 됨)

### 회귀 위험
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.

---

## v0.37.1 — write-doc CPS 필드 강제 + 재개 절차 단일화 + review 폐기 필드 제거 (2026-05-05)

### 변경 내용
- `skills/write-doc/SKILL.md` — Step 3 프론트매터에 `problem:·solution-ref:` 필드 추가, 필수 필드 목록 갱신
- `skills/write-doc/SKILL.md` — Step 2 "완료 문서 재개" 절차를 `git mv` → `docs_ops.py reopen`으로 단일화
- `rules/docs.md` — "완료 문서 재개" 절차 동일하게 `docs_ops.py reopen`으로 단일화
- `agents/review.md` — "핸드오프 계약" Pass 행에서 폐기된 `wip_kind·has_impact_scope` 제거

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- write-doc으로 생성한 기존 WIP에 `problem·solution-ref`가 없으면 commit 시 pre-check 차단. 직접 frontmatter 추가 후 커밋.
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.

