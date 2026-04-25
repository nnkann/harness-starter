# Review Staging 규칙

`/commit` 실행 시 review 호출 강도를 자동 결정. **운영 룰 SSOT** —
`pre-commit-check.sh`·`commit/SKILL.md`·`review.md`가 이 문서를 참조.

거버넌스(신호 추가 게이트)·알려진 한계·pre-check stdout 스키마는
`docs/decisions/hn_staging_governance.md`로 분리.

## 원칙

1. **Stage = 강도, 신호 = 검증 영역.** 같은 Stage라도 hit 신호에 따라
   검증 항목이 달라진다.
2. **분기 폭증 금지.** 신호 13개·연결 규칙 각 5케이스 이내. 신규 추가
   는 거버넌스 문서의 4질문 게이트 통과 필요.

## 신호 (13개)

상세 패턴은 `pre-commit-check.sh`가 SSOT.

| 신호 | 영역 |
|------|------|
| S1 | 보안·시크릿. `s1_level=line-confirmed`→deep, `file-only`→standard. 테스트·docs·example·`-helper.`/`-utils.` 면제 |
| S2 | 핵심설정 — `CLAUDE.md`, `.claude/{settings.json,rules,scripts,hooks}`, `Dockerfile*`, `.github/workflows/*` |
| S3 | 신규 파일만 (전부 `A`) |
| S4 | lock 파일만 |
| S5 | 면제 메타만 — `HARNESS.json`, `clusters/*`, `memory/*`, `CHANGELOG.md` |
| S6 | 문서만 — `docs/**`, 루트 `*.md` (README/CHANGELOG 제외) |
| S7 | 일반 코드 (위 어디에도 안 속함) |
| S8 | 공유 모듈 — export 추가/제거, 공개 시그니처 변경 |
| S9 | 도메인 등급 — `naming.md` (critical/normal/meta) |
| S10 | 연속 수정 — 같은 파일 최근 5커밋 중 N회 |
| S11 | 빌드/CI — 프로젝트 `scripts/**.sh`, `.husky/*`, `Makefile` |
| S14 | DB 마이그레이션 — `migrations/**`, `alembic/versions/**`, `prisma/migrations/**` |
| S15 | 패키지 manifest — `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` 등 |

> S12·S13 결번. 권한·환경 파일은 S1·S2에 흡수.

## Stage (5단계)

| Stage | 시간·tool | 행동 |
|-------|----------|------|
| 0 skip | 0초 | review 호출 안 함 |
| 1 micro | 15~25초, 1~2 calls | hit 신호 매핑 카테고리만 |
| 2 standard | 30~60초, 3~5 calls | hit 카테고리 + 3관점 |
| 3 deep | 90~180초, 10+ calls | hit 카테고리 전체 + 3관점 + 호출자 grep |

**거대 커밋 정책** (2026-04-22 재설계):

거대 커밋(파일 30+ 또는 diff 1500줄+)은 **스코프를 나눠 작은 커밋 여러
개로 분리**한다. 이전에 존재하던 `--bulk` 플래그(정량 가드 4종으로 review
대체)는 폐기:

- 정량 가드 4종 중 거대 커밋 특유 위험을 잡는 건 dead link 하나뿐이었고,
  그건 pre-check Step 3.5(v0.18.6)에 이미 이식됨
- 나머지 3종(test 스위트·downstream-readiness·날짜 suffix)은 거대 여부
  와 무관한 일상 정합성. bulk 전용일 이유 없음
- "review maxTurns 터지니까 우회"는 거대 커밋을 정당화하는 역방향 설계
  — 답은 커밋을 쪼개는 것. review 예산 문제는 `hn_review_tool_budget`에서 해결
- 관련 incident: `hn_review_maxturns_verdict_miss.md` (원인 진단 유효,
  해법만 재해석)

pre-check이 거대 변경 감지 시 **stderr로 "스코프 분리 권장" 경고만** 출력.
강제 분기 없음. 사용자가 판단.

## Stage 결정

### 1단계 — 기본 (5줄 룰, 첫 매칭)

**v0.17.0부터 전면 대체**. 기존 16줄 룰은 업스트림 편향 실측(22 deep
중 41%가 과잉)에서 폐기. `hn_review_staging_rebalance.md` 참조.

```
0. HARNESS_UPGRADE=1 환경변수                                   → skip (upstream 검증 코드)
1. .claude/scripts/** OR .claude/agents/** OR .claude/hooks/**
   OR .claude/settings.json 건드림                              → deep
2. S1 line-confirmed OR S14 OR S8(export 시그니처 변경)         → deep
3. S5(메타 단독) OR S4(lock 단독) OR WIP 단독(docs/WIP/ 파일만) → skip
4. (나머지 — 업스트림 외 경로·일반 코드·문서·rules·skills)      → standard
```

v0.17.0 룰 3(docs rename ≥30% → bulk)은 폐기됨 (2026-04-22). bulk 스테이지
자체가 사라졌다.

**설계 철학**:
- **경로 기반 이진 판정**. 줄 수·파일 수 임계 없음 (ec85c790: 13줄 수정이
  warn 1건). scripts 한 줄도 위험
- **standard도 신호 hit 카테고리는 잡음**. 놓침 아님, 심도 차이
- **단순성 = 신뢰성**. 사용자가 "왜 deep인지" 즉시 추론 가능

**룰 1 "업스트림 위험 경로" 근거**:
- `.claude/scripts/` — 실행 로직. 한 줄 bug가 다운스트림 전체 파괴
- `.claude/agents/` — 에이전트 판정 기준. 회귀 시 매 커밋에 영향
- `.claude/hooks/` — PreToolUse·SessionStart. 잘못되면 하네스 자체 불안정
- `.claude/settings.json` — matcher·permission. 오버블록 incident 이력

`.claude/rules/`·`.claude/skills/`는 **룰 1에 미포함** — 문서형 수정이
대부분이라 standard로 충분. review.md 신호 매핑이 S2 hit 시 카테고리
추가로 커버.

### 2단계 — 격상·완화 (유지)

```
B. S10 2회               → +1 격상 (skip→standard 포함)
C. S10 3회               → deep 강제
D. --quick               → micro 강제 (격상 무시)
E. --deep                → deep 강제
F. --no-review           → skip 강제
```

**룰 A 폐기** (다중 도메인 격상): 5줄 룰이 경로 기반이라 이미 "업스트림
하면 deep"로 격상 의미 무효. 다운스트림 `src/payment/*` + `src/auth/*`
같은 혼합은 S9 critical로 룰 1 miss 시 standard 유지 (review.md가 다중
도메인 경고 출력).

격상 후 skip이면 micro로. 누적 가능.

## 연결 규칙

신호=명사, 연결=동사. 폭증 차단 위해 3종만 허용.

### A. 동반 → 무거운 쪽으로
1단계 룰 1~16이 이미 동반 패턴.

### B. 강화 (검증 카테고리 추가)
- S10 + S2 → "변경 이력 패턴 분석"
- S9(critical) + S15 → "의존성 보안 이력"
- 다중 도메인 + S8 → "도메인 간 결합도"
- S14 + S15 → "데이터·의존성 동시 변경 위험"
- S2 + 권한 섹션 → "권한 변경 영향" 경고

### C. 완화 (격상 면제·다운그레이드)
- S10 + 매번 다른 영역 → 격상 면제
- 다중 도메인 중 1개가 docs/메타 → 경고만
- S15 + patch 버전만 → 1 가능
- S6 + ≤5줄 → 0 검토
- S6 + docs/WIP/ 단독 → 0 (계획 문서는 review 대상 아님)

## 신호 ↔ review 카테고리

| 신호 | 카테고리 |
|------|---------|
| S1 | 시크릿 패턴 |
| S2 | 핵심설정 정합성 + 호출자 영향 |
| S3 | 프론트매터·구조·description (신규 패스) |
| S4 | (단독 검증 X, S7 동반 시 의존성 보안) |
| S5 | 검증 안 함 |
| S6 | clusters 정합성 + 프론트매터 |
| S7 | 회귀 + 계약 + 스코프 (3관점) |
| S8 | 호출자 grep + 시그니처 호환성 |
| S9 | 해당 도메인의 incidents/decisions 인용 |
| S10 | 변경 이력 패턴 (`git log -5 <file>`) |
| S11 | 스크립트 안전성 + 권한 |
| S14 | 롤백 시나리오 + 데이터 영향 |
| S15 | 의존성 보안 + 버전 호환성 |

## 도메인 추출 (S9용)

순서대로, 첫 성공:

1. `docs/**.md` 프론트매터 `domain:`
2. WIP 파일명 접두사
3. `naming.md`의 "경로 → 도메인 매핑"
4. 실패 → S9 무시 (S7로 처리)

등급은 `naming.md`의 "도메인 등급" 섹션. 섹션 없으면 S9 전체 무시.

## git log 추적성

커밋 메시지 본문에 자동 포함:

```
🔍 review: <stage> | signals: <S1,S5,...> | domains: <harness,docs>
```

Stage 0(skip)도 반드시 한 줄. **검증 안 한 사실 자체가 추적 대상.**
`git log --grep "review: skip"` / `--grep "signals: S2"`로 회고.

## 참조

- `naming.md`: 도메인 등급 + 경로 매핑
- `pre-commit-check.sh`: 신호 감지 SSOT + stdout 스키마
- `commit/SKILL.md`: stage 분기 + 플래그 처리
- `review.md`: 카테고리 매핑 수행
- `docs/decisions/hn_staging_governance.md`: 거버넌스·한계·stdout 스키마
- `docs/WIP/harness--hn_commit_review_staging.md`: 설계 배경
