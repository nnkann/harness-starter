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

## v0.37.7 — HARNESS_MAP 연결 완성 — BIT·staging·implementation·review·harness-dev·eval·session-start (2026-05-06)

### 변경 내용
- `rules/bug-interrupt.md` — Q3 P# 매칭: HARNESS_MAP.md CPS 테이블 우선 진입 → 불가 시 project_kickoff.md 폴백. 관계 테이블에 HARNESS_MAP 추가
- `rules/staging.md` — 룰 4(CPS staged): cascade 범위 확인을 HARNESS_MAP defends-by 컬럼으로 안내
- `skills/implementation/SKILL.md` — Step 0 Problem 매칭: HARNESS_MAP CPS 테이블 우선 진입 명시
- `agents/review.md` — Solution 충족 기준 회귀: HARNESS_MAP serves 컬럼 확인 후 CPS 본문 Read
- `skills/harness-dev/SKILL.md` — 체크리스트에 HARNESS_MAP 정합 검증(eval_cps_integrity.py) 추가
- `skills/eval/SKILL.md` — --harness 결과 해석에 "관계 그래프 단절 N건" 항목 추가
- `HARNESS_MAP.md` — enforced-by-inverse 정정: session-start.py·post-compact-guard.sh·eval_cps_integrity.py. P5 표기 통일. 하향/상향 경로 분리. BIT 연계 역추적 절차
- `scripts/session-start.py` — section_harness_map() 추가: 세션 시작 시 MAP 미존재 경고
- `CLAUDE.md` — 하향/상향 경로 설명 갱신

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

---

## v0.37.6 — normalize_quote `**` 제거 + 박제 인용 수정 (2026-05-06)

### 변경 내용
- `pre_commit_check.py` `normalize_quote()`: CPS 본문의 `**bold**` 마크다운을 제거하지 않아 박제 감지 오작동 → `**` 제거 추가
- `docs/decisions/hn_verify_relates_precheck.md`: solution-ref `(부분)` 마커 제거 (50자 이내 원문)

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

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

