---
title: commit·review 단계화 — Stage 0~3 + 신규 파일 패스 + 메타 자동 병합
domain: harness
tags: [commit, review, performance, staging, cost]
status: pending
created: 2026-04-19
---

# commit·review 단계화

## 배경

사용자 지적: "review 매번 7~8분, 매 커밋마다 지옥". 실측:

| 커밋 | review 시간 | 입력 토큰 | tool_uses | 변경 규모 |
|------|-----------|----------|-----------|----------|
| 11fe9f2 | 73.9s | 33k | 11 | 5 files (자가 git 호출 사고) |
| fd66269 | 45.5s | 32k | 5 | 5 files (270라인 prompt 박힘) |
| e52234f | **113.5s** | 57k | 24 | **20 files** (stat + Read 24회) |
| 0d047a5 | 33.6s | 21k | 3 | 3 files (작은 diff) |

근본 문제: review.md가 **모든 호출에서 6카테고리 × 3관점**을 다 검증.
- 타이포 1줄도 6카테고리 검증 → 과잉
- 버전 범프 1줄도 마찬가지 → 분리 커밋이 만들어 두 번 검증
- 신규 파일 20개도 같은 6카테고리 → 토큰 폭증, Read 24회

## 설계

### Stage 분기 (4단계)

`pre-commit-check.sh`가 stdout에 `review_stage` 필드 추가 출력.
commit 스킬이 그 값에 따라 분기.

```
pre_check_passed: true
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: ...
diff_stats: files=N,+A,-D
review_stage: skip|micro|standard|deep
```

### 분기 원칙 — 성격이 1차, 크기는 2차

크기(줄·파일 수)만으로 분기하면 오류:
- 3줄·1파일이지만 `.claude/settings.json` hook 변경 → deep 필요
- 500줄·1파일 신규 LLM agent 정의 → 신규 패스로 끝
- 20파일이지만 18파일이 lock 자동 갱신 → micro로 충분

**1차 분류는 변경 성격 (signal), 2차 필터가 크기.**

### 변경 성격 신호 (signal)

| 신호 | 정의 | 분기 영향 |
|------|------|----------|
| S1. 보안·시크릿 | 시크릿 패턴 hit, auth/token 파일 | → Stage 3 강제 |
| S2. 핵심 설정 | `.claude/settings.json`, hook, `rules/*`, `scripts/*` | → Stage 3 강제 |
| S3. 신규 파일만 | 호출자 영향 없는 신규 .md/.ts/.py | → 신규 패스 (Stage 1) |
| S4. lock 파일만 | `package-lock.json`, `pnpm-lock.yaml`, `bun.lockb`, `uv.lock` 등 | → Stage 0 (skip), 단 manifest 동반 시 Stage 2 |
| S5. 면제 메타만 | HARNESS, promotion-log, INDEX, clusters, memory | → Stage 0 (skip) |
| S6. 문서만 | `docs/**`, `*.md` | light: skip / strict: Stage 1 |
| S7. 일반 코드 | 위 어디에도 안 속함 | → 크기로 micro/standard 결정 |
| S8. 공유 모듈 변경 | export 추가/제거, 공개 시그니처 변경 | → Stage 3 강제 |
| S9. 도메인 등급 | 변경 도메인의 등급 (critical/normal/meta) | 등급별 분기 (아래) |
| S10. 연속 수정 hit | 같은 파일 최근 5커밋 중 N회 등장 (pre-check 감지) | N회별 stage 격상 (아래) |

### S9. 도메인 등급 신호

같은 커밋의 변경이 어떤 도메인인지가 가장 강한 신호. 같은 도메인 변경은
같은 위험 패턴을 공유한다.

#### 도메인 추출 경로 (우선순위 순)

1. **변경된 docs/ 파일의 프론트매터 `domain:`** — 가장 정확
2. **WIP 파일명 접두사** (`harness--`, `decisions--`) → 도메인 간접 추론
3. **경로 패턴 매핑** — 프로젝트별 `naming.md`에 정의 가능
   ```
   src/payment/** → payment
   src/auth/**    → auth
   infra/**       → infra
   ```
4. 추출 실패 → S9 신호 무시 (S7로 처리)

#### 도메인 등급 — 프로젝트가 정의

하네스가 등급을 강제하지 않는다 (일반화 안 됨). `naming.md`에 등급
섹션을 두고 프로젝트별로 정의:

```markdown
## 도메인 등급 (review staging)
- critical: harness, payment, auth, infra, migration, security
- normal:   api, data, ui
- meta:     docs, harness-meta
```

`naming.md`에 등급 섹션이 없으면 S9는 무시 (S7로 폴백).

#### 등급별 분기

| 등급 | 분기 |
|------|------|
| critical | 크기 무관 **Stage 3 강제** |
| normal | S7과 동일 (크기로 결정) |
| meta | 크기 무관 **Stage 0 skip 검토** (S5와 결합) |

#### 다중 도메인 변경 — 스코프 이탈 신호

같은 커밋에 **여러 도메인이 섞이면**:
- 자동 분류는 **가장 높은 등급으로 격상** (critical 1개 + ui 다수 → Stage 3)
- 추가로 "다중 도메인 변경 감지: payment + ui" 경고 출력
- review의 "스코프 이탈" 검증과 자연스럽게 연결
- 사용자에게 "두 커밋으로 분리 검토" 권유 (강제 아님)

### S10. 연속 수정 신호 — 자동 격상

pre-check.sh가 이미 감지 중 (최근 5커밋 중 같은 파일 등장 횟수).
그 정보를 stage 결정에 반영해서 자동 격상:

| pre-check 감지 | 의미 | stage 영향 |
|---------------|------|-----------|
| 0~1회 | 정상 | 영향 없음 |
| 2회 (경고) | 근본 원인 미해결 의심 | **+1 stage 격상** |
| 3회 (차단) | 거의 확실히 증상 완화 반복 | **Stage 3 강제** (차단 해제 시) |

격상 의미:
- 자동 분류가 Stage 1이었다면 → Stage 2
- Stage 2였다면 → Stage 3
- Stage 0(skip)이었다면 → Stage 1 (skip 차단)

이유: 같은 파일을 또 만지는 건 "이전에 안 잡힌 무엇이 있다"는 신호.
검증 강도 ↑가 합리적.

#### review prompt에 연속 수정 정보 주입

risk_factors에 연속 수정 정보가 들어가면 review가 더 집중:
```
risk_factors: 연속 수정: SKILL.md (3회) — 근본 원인 미해결 의심
```

review.md에 추가 명시:
> 연속 수정 hit이 risk_factors에 있으면 해당 파일의 변경 이력
> (`git log --oneline -5 <file>`)을 확인하고 다음 패턴 검증:
> - 매번 같은 영역만 만지면 → 진짜 근본 원인은 다른 곳일 가능성
> - 매번 다른 영역을 만지면 → 정상적 점진 개선 (경고 면제)
> - 점점 복잡해지면 → 잘못된 추상화 가능성

### 면제 메타 리스트 (확장)

기존 4종 + 추가:
- `.claude/HARNESS.json`
- `docs/harness/promotion-log.md`
- `docs/INDEX.md`
- `docs/clusters/*.md`
- **`.claude/memory/*.md`** (메모리 항목 — 사람 검증 의미 없음)
- **`.claude/memory/MEMORY.md`** (메모리 인덱스)
- **`CHANGELOG.md`** (있는 프로젝트만)
- (옵션) `.gitignore` 단순 추가

### 신호 결합 규칙 (우선순위 순 평가)

**1단계 — 기본 stage 결정** (1번부터 순서대로, 첫 매칭에서 결정):

```
1. S9(critical) hit → Stage 3
2. S1·S2·S8 hit → Stage 3
3. S5 + S9(meta)만 → Stage 0
4. S5만 → Stage 0
5. S4만 → Stage 0
6. S6만 + S9(meta) → Stage 0
7. S4 + S7 → Stage 2
8. S3만 → 신규 패스 (Stage 1)
9. S6만 + light → Stage 0
10. S6만 + strict → Stage 1
11. S7·S9(normal) + 크기 ≤ 50줄·≤ 3파일 → Stage 1
12. S7·S9(normal) + 크기 ≤ 300줄·≤ 10파일 → Stage 2
13. S7·S9(normal) + 크기 > 300줄·> 10파일 → Stage 3
```

**2단계 — 격상 규칙** (1단계 결과에 위에서 아래로 적용):

```
A. 다중 도메인 hit → 가장 높은 등급으로 격상 + 스코프 이탈 경고
B. S10(연속 수정) 2회 → +1 stage 격상
C. S10(연속 수정) 3회 → Stage 3 강제
D. --quick 플래그 → Stage 1 강제 (격상 무시)
E. --deep 플래그 → Stage 3 강제
```

격상 후 stage가 0이면 1로 (skip 차단). 격상은 누적 가능 (다중 도메인 +
연속 수정 동시 hit이면 둘 다 적용).

### 사용자 의도 플래그 (오버라이드)

자동 분류가 항상 정확할 수 없음. 사용자가 의도 명시:
- `/commit --quick` → Stage 1 강제 (작은 변경 자가 판단 시)
- `/commit --deep` → Stage 3 강제 (중요한 변경 자가 판단 시)
- `/commit --no-review` → Stage 0 강제 (이미 정의됨)

자동 분류 결과를 사용자에게 짧게 노출:
> 🔍 review stage: standard (S7 + 5 files, 142 lines)

사용자가 본 결과가 부적절하면 다음 커밋에 플래그로 조정.

### Stage 정의 (검증 항목)

#### Stage 0: skip (0초)

review 호출 안 함. 위 면제·메타 후속 케이스.

**메타 후속 커밋**: 면제 리스트만 변경 + 직전 커밋 5분 이내 +
직전 review 통과 (현재는 분리 자체를 자동 병합으로 차단하지만,
혹시 발생 시 안전망).

#### Stage 1: micro (15~25초, sonnet, 1~2 tool calls)

**검증 항목 (축소)**: 시크릿 + 스코프 이탈만. diff 통째 prompt 박음.

**신규 파일 패스 모드** (S3): 프론트매터·tools·model·description 형식만
확인. 6카테고리 적용 안 함. //git log에는 남도록

#### Stage 2: standard (30~60초, sonnet, 3~5 tool calls)

**현재 기본값**. risk_factors가 가리키는 카테고리 + 3관점.

#### Stage 3: deep (90~180초, sonnet, 10+ tool calls)

전체 6카테고리 + 3관점 + 호출자 영향 grep. S1·S2·S8 hit 시.

### 신규 파일 패스 (Stage 3 내부 또는 독립)

20파일 신규 에이전트 같은 케이스:
- 신규 파일은 **회귀 영향 없음** (호출자 없음)
- **계약**도 호출자 없으니 깨질 수 없음
- 검증 의미 있는 항목: **프론트매터·구조 정합성·description 일관성**

별도 모드 `--new-files-mode`:
- 각 신규 파일 1회 Read (병렬)
- 프론트매터·tools·model·description 형식만 확인
- 6카테고리 적용 안 함

20파일 수정 = 6×3×20 = 360회 검증 vs 신규 패스 = 20회 검증. **18배 절감.**

### 버전·이력 자동 병합 (분리 차단)

commit 스킬 Step 3 (하네스 버전 체크)에서 버전 범프 결정 시:

**현재**: HARNESS.json + promotion-log를 사용자가 분리 커밋
**개선**: **본 커밋에 자동 포함** — Step 4 스테이징에 같이 들어감

`git add` 단계에서 다음 자동:
- 본 커밋의 변경 파일 + HARNESS.json + promotion-log를 한 번에 staged
- 분리 커밋 발생 자체를 막음

직전 e52234f + db686b8 분리는 0d047a5(면제 리스트) 이전 우회 흔적.
이미 면제 리스트 있으니 분리할 이유 없음.

## 폭증 차단 원칙 (필수)

신호·연결 규칙은 시간 지나면서 늘어나기 쉽다. 다음 게이트로 차단:

### 신호 추가 게이트

새 신호 후보가 나오면 다음 4질문에 모두 통과해야 추가:

1. **기존 신호와 70% 이상 겹치는가?** Y → 추가 금지 (sub-rule로 흡수)
2. **연 1회 미만 hit 예상되는가?** Y → 추가 금지 (유지 부담 > 가치)
3. **셸로 정확히 감지 가능한가?** N → 추가 보류 (오탐 위험)
4. **검증 카테고리가 기존과 다른가?** N → 추가 금지 (stage만 격상으로 충분)

### 중복 신호 식별·통합

신호 정의 시 다음 중복 패턴 명시 회피:

| 중복 사례 | 해결 |
|----------|------|
| `.claude/scripts/*.sh` 변경 | S2(핵심설정)에 흡수, S11에 포함 안 함 |
| `Dockerfile`, `docker-compose` | S2(인프라)에 흡수, 별도 신호 안 만듦 |
| `.env*` 시크릿 | S1(시크릿) 패턴에 흡수 |
| `.github/workflows/*` | S2(인프라)에 흡수 |
| settings.json permissions 변경 | S2 sub-rule 경고만, 별도 신호 안 만듦 |

S11은 **프로젝트 `scripts/**.sh`, `.husky/`만** 잡음 (S2와 안 겹치는 영역).

### 연결 규칙 한도

연결 규칙(강화·완화)은 **각 종류 5케이스 이내**. 초과 시 신호 자체를
재설계해야 한다는 신호 (분기 트리가 잘못 그려져 있다는 뜻).

## 연결 규칙 (3종, 얕은 레벨)

신호는 명사(독립), 연결은 동사(상호작용). 분기 트리가 결정적이지만
유기성을 더하기 위해 다음 3종 연결만 허용:

### A. 동반 (1단계 결합 규칙에 이미 있음)

여러 신호 동시 hit 시 가장 무거운 쪽으로. 위 1단계 규칙 1~13번이
이미 이 패턴.

### B. 강화 (격상)

| 케이스 | 동작 |
|--------|------|
| S10(연속수정) + S2(핵심설정) | review에 "변경 이력 패턴 분석" 카테고리 추가 |
| S9(critical) + S15(manifest) | review에 "의존성 보안 이력" 카테고리 추가 |
| 다중 도메인 + S8(공유 모듈) | review에 "도메인 간 결합도 검증" 추가 |
| S14(마이그레이션) + S15(manifest) | review에 "데이터·의존성 동시 변경 위험" 추가 |
| S2 + 권한 섹션 변경 | review에 "권한 변경 영향" 경고 (별도 신호 X) |

### C. 완화

| 케이스 | 동작 |
|--------|------|
| S10(연속수정) + 매번 다른 영역 | 정상 점진 개선 → 격상 면제 |
| 다중 도메인이지만 1개가 docs/메타 | 진짜 다중 아님 → 경고만 |
| S15(manifest) + patch 버전만 변경 | 보안 위험 낮음 → Stage 1 가능 |
| S6(문서) + 줄 수 ≤ 5 | 타이포 가능성 → Stage 0 검토 |

## Stage·신호 분리 + 신호↔검증 매핑 (유기성)

핵심: **Stage = 강도(시간·tool 한도), 신호 = 검증 영역**. 두 축 분리.

같은 Stage 2라도 hit한 신호에 따라 검증 항목이 달라짐.

### 신호 ↔ 검증 카테고리 매핑

| 신호 | review가 수행할 카테고리 |
|------|-----------------------|
| S1(시크릿) | 시크릿 패턴만 |
| S2(핵심설정) | 핵심설정 정합성 + 호출자 영향 |
| S3(신규파일) | 프론트매터·구조·description 일관성 (신규 패스) |
| S4(lock) | (단독이면 검증 안 함, S7 동반 시 의존성 보안) |
| S5(메타면제) | 검증 안 함 (Stage 0) |
| S6(문서) | INDEX/clusters 정합성 + 프론트매터 |
| S7(일반코드) | 회귀 + 계약 + 스코프 |
| S8(공유모듈) | 호출자 grep + 시그니처 호환성 |
| S9(도메인) | 해당 도메인의 incidents/decisions 인용 |
| S10(연속수정) | 변경 이력 패턴 분석 (`git log -5 <file>`) |
| S11(빌드/CI) | 스크립트 안전성 + 권한 |
| S14(마이그레이션) | 롤백 시나리오 + 데이터 영향 |
| S15(manifest) | 의존성 보안 + 버전 호환성 |

review.md에 **prompt에서 hit 신호 읽고 매핑된 카테고리만 수행** 명시.

### 효과

- Stage 1 + S2만 hit → 짧지만 핵심설정에 정확히 집중
- Stage 3 + S6만 hit → 깊지만 문서 정합성에 집중 (불필요한 보안 검증 안 함)
- 같은 토큰으로 더 정확한 검증

## 구현 영향 영역 (전수 점검)

### 1. `.claude/rules/staging.md` — 신규

신호 정의 + 연결 규칙 + 신호↔검증 매핑 + 폭증 차단 게이트의 단일 진실.
다른 파일이 이걸 참조.

### 2. `naming.md` — 도메인 등급 섹션 추가

```markdown
## 도메인 등급 (review staging)
- critical: ...
- normal: ...
- meta: ...

## 경로 → 도메인 매핑 (선택, 코드 영역용)
- src/payment/** → payment
```

없으면 S9 신호 무시.

### 3. `pre-commit-check.sh` — stdout 확장 + 신호 감지

추가 stdout key:
```
signals: S1,S2,S5,...
domains: harness,docs
domain_grades: critical,meta
multi_domain: true|false
repeat_count: max=3
recommended_stage: skip|micro|standard|deep
```

신규 검사 로직:
- S3 신규 파일 (`git diff --cached --name-status | grep ^A`)
- S4 lock + manifest 동반
- S6 문서만
- S8 export·시그니처 변경 (셸 한계 — `grep -E '^[+-].*export'` 수준)
- S9 도메인 추출 (프론트매터·WIP 접두사·경로 매핑)
- S11/S14/S15

### 4. `commit/SKILL.md` — Step 4·7 재설계

- Step 4: 본 커밋 + HARNESS.json + promotion-log 자동 병합 스테이징
- Step 7: stage별 분기 (skip 즉시 통과 / micro·standard·deep는 다른 prompt)
- 사용자 플래그 `--quick`/`--deep` 처리
- stage 결과 1줄 노출

### 5. `review.md` — 신호별 검증 + Stage 모드

- prompt에서 `signals:` 읽어 매핑 카테고리만 수행
- prompt에서 `recommended_stage:` 읽어 한도 인식
- Stage 1 신규 패스 모드 (프론트매터만)

### 6. hook (`.claude/settings.json`) — 변경 없음

기존 PreToolUse `git commit` hook 그대로 유지. exit 코드 변화 없음.

(옵션) PostToolUse `Edit|Write`로 `naming.md` 도메인 등급 섹션 검증
hook 추가 검토 — 등급 누락 시 경고. 후속.

### 알려진 한계

- **S8 공유 모듈 감지** — 셸로 100% 정확하지 않음. export 라인 변경 감지
  수준. 프로젝트별 신뢰도 다름.
- **Stage 시간·tool 한도** — review.md에 명시해도 LLM이 100% 지키는 건
  아님. 강한 가드는 어려움.

## 구현 순서 (각 별도 커밋)

| # | 작업 | 파일 | 위험 |
|---|------|------|------|
| 1 | `.claude/rules/staging.md` 신설 (단일 진실) | 신규 1 | 낮음 (스펙만) |
| 2 | `naming.md` 도메인 등급 섹션 추가 | 1 | 낮음 (스펙만) |
| 3 | `commit/SKILL.md` Step 4 자동 병합 (즉시 효과) | 1 | 낮음 |
| 4 | `pre-commit-check.sh` 신호 S1~S6 + stdout 확장 | 1 | 중간 |
| 5 | `commit/SKILL.md` Step 7 stage 분기 + `review.md` 신호별 매핑 | 2 | 중간 |
| 6 | `pre-commit-check.sh` 신호 S8/S9/S10/S11/S14/S15 추가 | 1 | 중간 |
| 7 | 5번 커밋 측정 후 효과 평가 | — | — |

각 단계 검증 후 다음 단계. 한 번에 다 밀어넣지 말 것.

## 측정 기준

다음 5번 커밋의:
- review 시간 평균
- tool_uses 평균
- 입력 토큰 평균
- Stage별 분포 (몇 번이 skip/micro/standard/deep)

목표: 평균 시간 60% 절감 (60s → 24s 수준).

## 우려

- Stage 0 스킵이 진짜 위험을 놓치면? → 면제 조건은 보안·핵심 설정 hit 시
  무조건 Stage 2~3으로 격상. 면제는 "정말 메타 변경"에만.
- Stage 1 검증 축소가 부작용을 놓치면? → 작은 변경의 부작용 범위는 좁음
  (≤50줄). 시크릿 + 스코프만 봐도 차단 사유는 거의 다 잡음.
- 신규 파일 패스가 description 오류를 놓치면? → 프론트매터 형식만 봐도
  주요 오류(model 미지정, tools 누락)는 잡힘. 깊은 검증은 첫 사용 시점에.

## 우선순위

P0 — 매 커밋마다 발생하는 비용. 다른 어떤 작업보다 일상 영향 큼.
