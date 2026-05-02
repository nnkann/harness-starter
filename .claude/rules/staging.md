# Review Staging 규칙

defends: P2

`/commit` 실행 시 review 호출 강도를 자동 결정. **운영 룰 SSOT** —
`pre_commit_check.py`·`commit/SKILL.md`·`review.md`·`implementation/SKILL.md`
가 이 문서를 참조.

## 원칙 — AC + CPS 의미 기반 분류

1. **분류는 AC + CPS 메타데이터의 부산물**. 외형 metric(파일·줄 수·경로 패턴·
   kind 라벨) 사용 금지.
2. **유일한 분류 입력**: 작성자가 AC `검증.review`로 직접 선언한 강도.
3. **분류 근거가 부족하면 분류하지 않고 차단**. deep 격상으로 회피하지 마라 —
   진짜 답은 AC 작성을 정밀화하는 것.

## Stage (5단계)

| Stage | 시간·행동 |
|-------|---------|
| 0 skip | review 호출 안 함 |
| 1 micro (= self) | AC Goal·충족 기준만 직접 체크. 15~25초, tool call 0~2 |
| 2 standard (= review) | AC + 2축(계약·스코프). 30~60초, tool call 1~4 |
| 3 deep (= review-deep) | AC + 2축 + Solution 충족 기준 회귀 전수. 90~180초, tool call 3~5 |

`검증.review` 값과 stage 매핑:
- `skip` → Stage 0
- `self` → Stage 1
- `review` → Stage 2
- `review-deep` → Stage 3

## Stage 결정 (AC + CPS 기반 단일 룰)

### 1단계 — 단일 룰 (첫 매칭)

```
1. 시크릿 line-confirmed                              → deep (보안 게이트)
2. AC frontmatter 누락 (problem/solution-ref)         → 차단 (분류 불가)
3. AC Goal·검증 묶음 누락                             → 차단 (분류 불가)
4. CPS Problem 정의 자체 staged                       → deep (cascade 영향)
   (docs/guides/project_kickoff.md Problems 섹션 변경)
5. AC `검증.review` 값 그대로 stage 결정              → skip|micro|standard|deep
```

**룰 1만 AC와 무관**. 시크릿은 보안 게이트 — 작성자 선언 무시.
**룰 4는 CPS 정의 변경 보호** — Solution 충족 기준 cascade 영향 검증.

### 2단계 — 플래그 오버라이드

```
--no-review → skip (사용자 명시)
--quick     → micro 강제
--deep      → deep 강제
```

**충돌 처리**: 번호가 낮은 쪽 우선 (no-review > quick > deep > auto).

## AC 작성 가이드 (implementation Step 0가 1차 제안)

implementation Step 0가 작업 발화 받으면 frontmatter·검증 묶음 1차 제안:

| 작업 성격 | review 추천 | tests 추천 | 실측 추천 |
|----------|-----------|----------|---------|
| Solution 메커니즘 코드 변경 | `review` 또는 `review-deep` | `pytest -m <영역>` | 구체 명령 |
| Solution 적용 데이터·문서 변경 | `self` | `없음` | 운용 검증 |
| 보안·인증·시크릿 영역 | `review-deep` | `pytest -m secret` | 우회 시도 실측 |
| Problem 본문 확장 | `review` | `없음` | CPS 본문 정합 |

작성자가 수정 가능. 최종 선언은 작성자 책임.

## 다운스트림 자연 회복 (CPS 매칭)

implementation Step 0가 작업 발화를 P1~P6에 매칭. 매칭 hit 없으면 단독 판단:
- **병합**: 의미 거리 가까움 → 기존 Problem 본문 확장 (write-doc 위임)
- **추가**: 의미 거리 멀고 새 영역 → 신규 Problem 등록 (write-doc 위임)
- **Solution 변경**: 프로젝트 owner 승인 필수 (cascade 영향 큼)

다운스트림이 새 Problem을 발견하면 implementation이 자연 인식 → write-doc이
project_kickoff.md 갱신.

## 폐기된 룰 (2026-05-02, v0.28.x — 외형 metric)

| 룰 | 폐기 사유 |
|----|----------|
| `.claude/scripts/**` → deep | 경로 외형. Solution 메커니즘 코드인지 데이터인지가 본질 |
| `docs 5줄 이하` → skip | 줄 수 외형. 1줄이 회귀 유발 가능 |
| `WIP 단독` → skip | 외형. WIP 본문이 Problem 정의 변경하면 deep이어야 |
| `meta 단독` → skip | 외형. HARNESS.json 변경이 Solution 메커니즘 영향 가능 |
| `rename 단독` → skip | 외형. rename이 import 경로·참조 깨면 회귀 |
| AC `kind:` 마커 (docs/chore/feature/refactor/bug) | 외형 라벨. 작성자가 `검증.review` 직접 선언 |
| AC `영향 범위:` 항목 | kind 변동 트리거였음. `검증.tests`에 흡수 |

호환성: 기존 WIP의 `kind:`·`영향 범위:`는 무시 (코드에서 더 이상 읽지 않음).
다운스트림이 그대로 둬도 동작 무관.

## 거대 커밋 정책

거대 커밋(파일 30+ 또는 diff 1500줄+)은 **스코프를 나눠 작은 커밋 여러
개로 분리**한다. pre-check이 감지 시 stderr 경고만 출력. 강제 분기 없음.
거대 커밋 자체는 stage 결정과 무관 — `검증.review` 값이 결정.

## split 옵트인 정책 (Phase 3 — v0.28.9)

**기본은 단일 커밋** (atomic commit 표준). 분할은 다음 모두 만족 시에만:

1. char 다양성 ≥ 2 (성격 다른 그룹 2개 이상)
2. `HARNESS_SPLIT_OPT_IN=1` 명시 OR 거대 커밋 임계 hit
3. `recommended_stage`가 `skip` 아님 (skip이면 review 분산 효과 0)

옵트인 트리거:
- 사용자: `HARNESS_SPLIT_OPT_IN=1 /commit`
- 자동: 거대 커밋(files>30·+>1500·->1500) + char 다양성 + non-skip stage

## 자가 보고 신뢰 시스템

작성자가 거짓 `검증.review: skip` 선언:
- commit log에 `🔍 review: skip | declared-by: author` 기록
- eval --deep이 사후 audit ("skip 선언 작업 중 회귀 추적")
- 반복 시 incident → rules에 "이 영역 review 필수" 패턴 추가

신뢰 점진 학습. 보안 게이트(시크릿 line-confirmed)만 작성자 선언 무시.

## git log 추적성

커밋 메시지 본문에 자동 포함:

```
🔍 review: <stage> | problem: P# | solution-ref: S#
```

Stage 0(skip)도 반드시 한 줄. 검증 안 한 사실 자체가 추적 대상.

## 참조

- `pre_commit_check.py`: AC + CPS 추출 + stage 결정 SSOT
- `commit/SKILL.md`: stage 분기 + 플래그 처리 + tests·실측 자동 실행
- `review.md`: Solution 충족 기준 회귀 검증
- `implementation/SKILL.md`: CPS Problem 매칭 + AC 1차 제안
- `docs.md`: frontmatter `problem`·`solution-ref` SSOT + AC 포맷 SSOT
- `docs/decisions/hn_staging_governance.md`: 거버넌스·한계
