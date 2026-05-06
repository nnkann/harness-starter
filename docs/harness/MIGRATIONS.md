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

## Feedback Reports — 다운스트림 → upstream 피드백 채널

업그레이드 후 운용 중 발견한 구조적 관찰·약점·개선 제안을 upstream에 전달하는
규격화된 채널. `migration-log.md`의 별도 섹션으로 작성한다.

**upstream이 이 채널을 통해 기대하는 것**: 다운스트림 환경에서만 보이는
사일런트 페일, 규칙 우회 패턴, 문서 부재 등 — upstream 격리 환경에서는
발견할 수 없는 피드백.

### 포맷 (항목당 1개)

```markdown
## Feedback Reports

### FR-001 (YYYY-MM-DD)

**관점**: <!-- 어떤 측면을 분석했는가 (1줄) -->

**약점**:
<!-- 발견된 문제·헛점·위험. 증상 + 영향 포함 -->

**실천**:
<!-- 구체적 개선 방향. "~해야 한다" 형식 -->

**심각도**: low | medium | high
**관련 CPS**: P# (해당 시)
```

### 작성 규칙

- 항목 번호: `FR-NNN` 순차 증가 (프로젝트 내 전역)
- **관점**: 1줄 요약. "어느 레이어·어느 컴포넌트를 봤는가"
- **약점**: 추측 금지. 실측 또는 재현 가능한 시나리오만
- **실천**: "더 잘 해야 한다" 수준 금지. 구체 행동 또는 구체 파일명 제시
- **심각도**: `high` = upstream이 다음 버전에서 반드시 처리, `medium` = 권장, `low` = 참고
- 미작성(`없음`)도 명시 — 빈 섹션보다 "없음" 한 줄이 낫다

### eval --harness 검증 항목

`eval --harness` 실행 시 migration-log.md의 Feedback Reports 포맷을 검증한다:

- FR 항목이 있을 때: `관점`·`약점`·`실천`·`심각도` 4개 필드 모두 존재하는지 확인
- 필드 누락 시: `⚠️ FR-NNN: [누락 필드] 없음` 경고
- FR 항목이 없을 때: `피드백 리포트: 없음 ✅` 통과

---

## v0.38.3 — 침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계 (2026-05-06)

### 변경 내용
- `.claude/scripts/bash-guard.sh` — 차단 시 `.claude/memory/signal_defense_success.md`에 background append. P4 방어 활성 데이터 축적.
- `skills/eval/SKILL.md` — `--harness` 항목 6번 추가: signal_defense_success.md 존재·최근 기록 표시 (기존 6번은 7번으로 번호 이동)
- `skills/harness-upgrade/SKILL.md` — Step 10 완료 직후 방어 기전 설명 단계(6번) 추가: What이 아닌 Why 포함 강제
- `docs/guides/project_kickoff.md` — S4 추가 방어 레이어 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 다음 harness-upgrade 시 Step 10 완료 직후 방어 기전 설명을 받게 됨 — "왜 이런 제약이 있는가" 이해 기회
- `.claude/memory/signal_defense_success.md`가 자동 생성되어 eval --harness에서 방어 활성 상태 확인 가능

---

## v0.38.2 — HARNESS_MAP MVR 섹션 + 에이전트 빠른 진입 가이드 (2026-05-06)

### 변경 내용
- `.claude/HARNESS_MAP.md` — `## MVR (작업유형별 최소 필수 규칙셋)` 섹션 추가: 7개 작업유형별 Rules 2~3개 압축 매핑 (구현·커밋·디버그·문서·eval·harness-dev·설정변경)
- `.claude/HARNESS_MAP.md` — 최상단에 "⚡ 에이전트 빠른 진입" 가이드 추가: MAP 전체 Read 금지, MVR → 역추적 2단계 진입점 명시
- `docs/guides/project_kickoff.md` — S5 MVR 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 에이전트가 HARNESS_MAP 전체를 읽는 대신 `## MVR` 섹션만 참조하도록 유도하면 컨텍스트 절감 효과 기대
- 다운스트림은 자기 프로젝트 작업유형에 맞게 MVR 섹션 확장 가능 (harness-upgrade가 덮어쓰지 않는 영역에 추가)

---

## v0.38.1 — 피드백 채널 포맷 규격화 + bash-guard 우회 차단 강화 (2026-05-06)

### 변경 내용
- `docs/harness/MIGRATIONS.md` — `## Feedback Reports` 섹션 추가: 다운스트림 → upstream 역방향 피드백 포맷 규격화 (FR-NNN, 관점·약점·실천·심각도 4필드)
- `skills/eval/SKILL.md` — `--harness` 점검 항목 6번 추가: migration-log.md Feedback Reports 포맷 검증
- `.claude/scripts/eval_cps_integrity.py` — 피드백 리포트 포맷 자동 검증 로직 추가 (`check_feedback_reports`)
- `.claude/scripts/bash-guard.sh` — 간접 실행 차단 강화: `eval`/`sh -c`/`bash -c` 패턴 + 역슬래시 이스케이프(`git\ commit`) 정규화
- `docs/guides/project_kickoff.md` — P4·P5·P7 운용 약점 + S3·S4·S5 방향 갱신 (다운스트림 피드백 반영)
- `.claude/HARNESS_MAP.md` — P4·P5 row 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 권장 사항
- `docs/harness/migration-log.md`에 `## Feedback Reports` 섹션 추가 후 발견한 이상 소견·구조 관찰을 FR-NNN 형식으로 기록하면 eval --harness가 포맷 검증

---

## v0.38.0 — P4·P7 방어 실질화 + HARNESS_DEV 이스케이프 경계 명확화 (2026-05-06)

### 변경 내용
- `agents/review.md` — 카테고리 9 추가: settings.json `hooks` 블록 argument-constraint 패턴 감지 [차단] (P4 방어 실질화)
- `agents/review.md` — 카테고리 10 추가: commit_finalize.sh 스킬 외부 직접 호출 감지 [경고]
- `docs/guides/hn_harness_organism_design.md` — frontmatter `problem: P1` → `problem: P7` 수정 (P7 인용 0건 해소)
- `skills/implementation/SKILL.md` — WIP 사전 준비 섹션에 "MAP 참조" 필드 추가 (MAP 활용 흔적 기록)
- `memory/signal_commit_skill_bypass.md` — 합법/금지 경로 경계 명확화

### 배경
- P4: hooks.md가 review에 위임 선언했으나 review.md에 해당 검증 항목 없었음 — dangling reference 수정
- P7: hn_harness_organism_design.md가 P7 작업인데 P1으로 잘못 등재됨 → P7 인용 0건의 직접 원인
- HARNESS_DEV: 스킬 내부 사용(합법) vs 외부 직접 호출(금지) 경계가 텍스트로만 존재 → review 카테고리로 보강

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

---

## v0.37.9 — CLAUDE.md 커밋 스킬 우회 금지 절대 규칙 추가 + 신호 파일 등록 (2026-05-06)

### 변경 내용
- `CLAUDE.md` — 절대 규칙에 "커밋은 반드시 `/commit` 스킬 경유. WIP 없어도 `--no-review` 플래그. `commit_finalize.sh` 직접 호출 금지" 추가
- `.claude/memory/signal_commit_skill_bypass.md` — 커밋 스킬 우회 반복 패턴 strong 신호 등록

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.

