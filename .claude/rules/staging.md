# Review Staging 규칙

`/commit` 실행 시 review 에이전트 호출 강도를 자동 결정한다. **단일 진실** —
다른 파일(pre-commit-check.sh, commit/SKILL.md, review.md)은 이 문서를
참조한다.

## 배경

review가 매번 모든 변경에 대해 6카테고리×3관점 전수 검증 → 매 커밋
30~120초 소비. 변경 성격에 맞는 강도로 분기하면 60% 절감 가능.

## 원칙 2개

1. **Stage = 강도, 신호 = 검증 영역.** 두 축이 분리된다.
   같은 Stage 2라도 hit한 신호에 따라 검증 항목이 달라진다.
2. **분기 폭증 금지.** 신호 13개·연결 규칙 각 5케이스 이내. 새 신호 추가
   는 아래 게이트 통과해야 가능.

## 신호 정의 (13개)

| 신호 | 정의 |
|------|------|
| S1 | 보안·시크릿 — 시크릿 패턴 hit, `auth/token/secret/key/credential/password` 파일명 또는 라인 |
| S2 | 핵심 설정 — `CLAUDE.md`, `.claude/settings.json`, `.claude/rules/*`, `.claude/scripts/*`, `.claude/hooks/*`, `Dockerfile`, `docker-compose*`, `.github/workflows/*` |
| S3 | 신규 파일만 — staged 변경이 전부 새 파일 (`git diff --cached --name-status` 모두 `A`) |
| S4 | lock 파일만 — `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`, `uv.lock`, `Cargo.lock`, `go.sum` 만 변경 |
| S5 | 면제 메타만 — `.claude/HARNESS.json`, `docs/harness/promotion-log.md`, `docs/INDEX.md`, `docs/clusters/*.md`, `.claude/memory/*.md`, `CHANGELOG.md` 만 변경 |
| S6 | 문서만 — `docs/**`, 루트 `*.md` (단 README/CHANGELOG 제외) 만 변경 |
| S7 | 일반 코드 — 위 어디에도 안 속함 |
| S8 | 공유 모듈 — export 추가/제거, 공개 시그니처 변경 (`grep -E '^[+-].*\b(export|public|def )\b'`) |
| S9 | 도메인 등급 — 변경 도메인의 `naming.md` 등급 (critical/normal/meta) |
| S10 | 연속 수정 — 같은 파일 최근 5커밋 중 N회 등장 (pre-check이 이미 감지) |
| S11 | 빌드/CI 스크립트 — 프로젝트 `scripts/**.sh`, `.husky/*`, `Makefile` (`.claude/scripts/*`는 S2에 흡수) |
| S14 | DB 마이그레이션 — `migrations/**`, `*/migrations/*.{sql,py,ts}`, `alembic/versions/**`, `prisma/migrations/**` |
| S15 | 패키지 manifest — `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `requirements*.txt`, `Gemfile`, `composer.json` |

> S12·S13 결번: 권한 변경·환경 파일은 S1·S2에 흡수 (중복 회피).

## Stage 정의 (4단계)

| Stage | 시간·tool | 검증 행동 |
|-------|----------|----------|
| 0 (skip) | 0초 | review 호출 안 함 |
| 1 (micro) | 15~25초, 1~2 tool calls | hit 신호의 매핑 카테고리만, diff 통째 prompt 박음 |
| 2 (standard) | 30~60초, 3~5 tool calls | hit 신호의 매핑 카테고리 + 3관점 (현재 기본) |
| 3 (deep) | 90~180초, 10+ tool calls | hit 신호의 매핑 카테고리 전체 + 3관점 + 호출자 grep |

**Stage는 강도(시간·tool 한도), 검증 영역은 신호가 결정.**

## Stage 결정 (2단계 평가)

### 1단계 — 기본 stage (1번부터 순서대로, 첫 매칭)

```
1. S9(critical) hit → Stage 3
2. S1·S2·S8 hit → Stage 3
3. S14 hit → Stage 3 (마이그레이션은 무조건 deep)
4. S5 + S9(meta)만 → Stage 0
5. S5만 → Stage 0
6. S4만 → Stage 0
7. S6만 + S9(meta) → Stage 0
8. S4 + S7 → Stage 2 (lock 단독 신뢰 X)
9. S15 + S7 → Stage 2 (manifest는 의존성 검증)
10. S11 hit → Stage 2 (빌드/CI 스크립트)
11. S3만 → 신규 패스 (Stage 1)
12. S6만 + light → Stage 0
13. S6만 + strict → Stage 1
14. S7·S9(normal) + 크기 ≤ 50줄·≤ 3파일 → Stage 1
15. S7·S9(normal) + 크기 ≤ 300줄·≤ 10파일 → Stage 2
16. S7·S9(normal) + 크기 > 300줄·> 10파일 → Stage 3
```

### 2단계 — 격상·완화 (위에서 아래 적용)

```
A. 다중 도메인 hit → 가장 높은 등급으로 격상 + "스코프 이탈 의심" 경고
B. S10(연속수정) 2회 → +1 stage 격상
C. S10(연속수정) 3회 → Stage 3 강제
D. --quick 플래그 → Stage 1 강제 (격상 무시)
E. --deep 플래그 → Stage 3 강제
```

격상 후 stage가 0이면 1로 (skip 차단). 격상 누적 가능.

## 연결 규칙 (3종, 각 5케이스 이내)

신호는 명사(독립), 연결은 동사(상호작용). 분기 트리 폭증 차단을 위해
다음 3종만 허용.

### A. 동반 → 무거운 쪽으로

1단계 결합 규칙(위 1~16번)이 이미 동반 패턴.

### B. 강화 (검증 카테고리 추가)

| 케이스 | 동작 |
|--------|------|
| S10(연속수정) + S2(핵심설정) | "변경 이력 패턴 분석" 카테고리 추가 |
| S9(critical) + S15(manifest) | "의존성 보안 이력" 카테고리 추가 |
| 다중 도메인 + S8(공유 모듈) | "도메인 간 결합도 검증" 추가 |
| S14(마이그레이션) + S15(manifest) | "데이터·의존성 동시 변경 위험" 추가 |
| S2 + 권한 섹션 변경 | "권한 변경 영향" 경고 (별도 신호 X) |

### C. 완화 (격상 면제 또는 stage 다운그레이드)

| 케이스 | 동작 |
|--------|------|
| S10(연속수정) + 매번 다른 영역 | 정상 점진 개선 → 격상 면제 |
| 다중 도메인이지만 1개가 docs/메타 | 진짜 다중 아님 → 경고만 |
| S15(manifest) + patch 버전만 변경 | 보안 위험 낮음 → Stage 1 가능 |
| S6(문서) + 줄 수 ≤ 5 | 타이포 가능성 → Stage 0 검토 |

## 신호 ↔ 검증 카테고리 매핑

review가 prompt에서 hit 신호 읽고 **매핑된 카테고리만** 수행.

| 신호 | review 카테고리 |
|------|---------------|
| S1 | 시크릿 패턴 |
| S2 | 핵심설정 정합성 + 호출자 영향 |
| S3 | 프론트매터·구조·description 일관성 (신규 패스) |
| S4 | (단독은 검증 안 함, S7 동반 시 의존성 보안) |
| S5 | 검증 안 함 (Stage 0) |
| S6 | INDEX/clusters 정합성 + 프론트매터 |
| S7 | 회귀 + 계약 + 스코프 (3관점) |
| S8 | 호출자 grep + 시그니처 호환성 |
| S9 | 해당 도메인의 incidents/decisions 인용 |
| S10 | 변경 이력 패턴 분석 (`git log -5 <file>`) |
| S11 | 스크립트 안전성 + 권한 |
| S14 | 롤백 시나리오 + 데이터 영향 |
| S15 | 의존성 보안 + 버전 호환성 |

## 도메인 추출 (S9용)

우선순위 순으로 시도, 첫 성공에서 결정:

1. 변경된 `docs/**.md` 프론트매터 `domain:` 필드
2. WIP 파일명 접두사 (`harness--`, `decisions--`, ...) → 도메인 간접 추론
3. `naming.md`의 "경로 → 도메인 매핑" 섹션 (정의된 경우)
4. 추출 실패 → S9 신호 무시 (S7 일반 코드로 처리)

도메인 등급은 `naming.md`의 "도메인 등급 (review staging)" 섹션을 참조.
섹션이 없으면 S9 신호 전체 무시.

## 폭증 차단 게이트

### 신호 추가 4질문 (모두 통과해야 신규 신호 추가 가능)

1. 기존 신호와 70% 이상 겹치는가? Y → 추가 금지 (sub-rule로 흡수)
2. 연 1회 미만 hit 예상되는가? Y → 추가 금지 (유지 부담 > 가치)
3. 셸로 정확히 감지 가능한가? N → 추가 보류 (오탐 위험)
4. 검증 카테고리가 기존과 다른가? N → 추가 금지 (stage 격상으로 충분)

### 중복 신호 식별·통합

다음은 **별도 신호로 만들지 마라** — 기존 신호에 흡수:

| 변경 영역 | 흡수 위치 |
|----------|----------|
| `.claude/scripts/*.sh` | S2 |
| `Dockerfile`, `docker-compose*` | S2 |
| `.env*` 시크릿 | S1 |
| `.github/workflows/*` | S2 |
| settings.json permissions 변경 | S2 sub-rule (경고만) |

### 연결 규칙 한도

연결 규칙은 **각 종류 5케이스 이내**. 초과 시 신호 자체를 재설계해야
한다는 신호 (분기 트리가 잘못 그려져 있다는 뜻).

## pre-commit-check.sh stdout 스키마

pre-check이 다음 stdout 키를 출력한다 (review·commit이 소비):

```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: <세미콜론 구분 위험 요인>
diff_stats: files=N,+A,-D
signals: S1,S2,S5,...           # NEW — hit한 신호 목록 (콤마 구분)
domains: harness,docs           # NEW — 변경된 도메인 (콤마 구분)
domain_grades: critical,meta    # NEW — domains와 같은 순서의 등급
multi_domain: true|false        # NEW — 2개 이상 도메인 변경 여부
repeat_count: max=N             # NEW — 연속 수정 최대 카운트
recommended_stage: skip|micro|standard|deep   # NEW — 1+2단계 결합 결과
```

## git log 추적성 (모든 stage 공통)

review를 가볍게(또는 skip) 한 결정 자체가 git log에서 추적 가능해야 한다.
나중에 "이 커밋이 왜 깊은 검증 없이 통과됐지?" 의문이 생기면 추적할 수
있어야 한다.

commit 스킬은 커밋 메시지 본문에 다음 한 줄을 자동 포함한다:

```
🔍 review: <stage> | signals: <S1,S5,...> | domains: <harness,docs>
```

예시:
- `🔍 review: skip | signals: S5 | domains: meta` (메타 후속)
- `🔍 review: micro | signals: S3 | new-files-pass: 7 files` (신규 패스)
- `🔍 review: deep | signals: S2,S10 | repeat=3 | warnings: 2` (격상 사례)
- `🔍 review: standard | signals: S7,S9(harness) | warnings: 0`

Stage 0(skip)도 반드시 한 줄 남긴다. **검증 안 한 사실 자체가 추적 대상.**

이렇게 하면:
- `git log --grep "review: skip"` → 검증 스킵된 커밋 회고 가능
- `git log --grep "signals: S2"` → 핵심설정 변경 이력 추출
- 사고 발생 시 "어떤 stage였나" 즉시 확인

## 한계 (알려진 것)

- **S1 파일명 오탐** — 파일명에 `auth`·`token`·`secret`·`key`·`credential`·
  `password`·`.env` 단어가 포함되면 시크릿 값이 없어도 hit. 예:
  `src/auth-helper.ts`만 만져도 S1 → Stage 3 deep 강제. 안전 방향 오탐
  이지만 사용자가 의외의 deep 사유를 추적하기 어려울 수 있음. 정밀화는
  후속 — 라인 패턴 신뢰도가 충분히 높아지면 파일명 패턴을 좁힌다.
- **S8 공유 모듈 감지** — 셸로 100% 정확하지 않음. export 라인 변경 감지
  수준. 프로젝트별 신뢰도 다름. 의심 시 사용자가 `--deep` 강제.
- **Stage 시간·tool 한도** — review.md에 명시해도 LLM이 100% 지키는 건
  아님. 강한 가드는 어려움.
- **자동 분류 오판** — 사용자가 매번 결과 보고 `--quick`/`--deep`로 보정.
  반복 오판은 incidents/에 기록.
- **폭증 차단 게이트가 코드 강제 X** — 위 "신호 추가 4질문"과 "연결 규칙
  5케이스"는 텍스트 규범. pre-check이 신호 수를 검사하지 않음. 1인 운영
  이면 자기 적용이라 위험 낮음, 팀 확장 시 신호 수 초과 자동 경고 추가
  검토.

## 참조

- `naming.md`: 도메인 등급 + 경로→도메인 매핑
- `pre-commit-check.sh`: 신호 감지 + stdout 출력
- `commit/SKILL.md`: stage 분기 + 사용자 플래그 처리
- `review.md`: 신호별 카테고리 매핑 수행
- `docs/WIP/harness--commit_review_staging_260419.md`: 설계 배경·실측 데이터
