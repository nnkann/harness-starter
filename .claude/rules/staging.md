# Review Staging 규칙

`/commit` 실행 시 review 호출 강도를 자동 결정. **운영 룰 SSOT** —
`pre_commit_check.py`·`commit/SKILL.md`·`review.md`가 이 문서를 참조.

## 원칙

1. **Stage = 강도.** 같은 Stage라도 AC에 명시된 항목에 따라 검증 범위가 달라진다.
2. **검증 기준은 WIP AC에서 온다.** review는 diff 전에 WIP task의 `Goal:` 항목과
   AC를 먼저 읽는다. AC에 명시된 범위가 검증 스코프를 결정한다.
3. **분기 폭증 금지.** 규칙은 단순하게 유지한다.

## Stage (5단계)

| Stage | 시간·행동 |
|-------|---------|
| 0 skip | review 호출 안 함 |
| 1 micro | AC 항목만 직접 체크. 15~25초 |
| 2 standard | AC + 3관점(회귀·계약·스코프). 30~60초 |
| 3 deep | AC + 3관점 + AC `영향 범위:` 항목에 명시된 범위 전수 조사. 90~180초 |

## Stage 결정 (AC kind 기반)

`pre_commit_check.py`가 staged WIP 파일의 `kind:` 마커와 `영향 범위:` 항목을
읽어 `recommended_stage`를 결정한다. **`kind:` 마커가 검증 스코프를 선언한다.**

### 1단계 — 기본 룰 (첫 매칭)

```
0. HARNESS_UPGRADE=1 환경변수                                   → skip
1. .claude/scripts/** OR .claude/agents/** OR .claude/hooks/**
   OR .claude/settings.json 건드림                              → deep
2. 시크릿 line-confirmed                                        → deep
3. WIP 단독(docs/WIP/ 파일만) OR 메타 단독 OR rename 단독      → skip
4. docs 5줄 이하                                                → skip
5. (나머지 — AC kind 기반으로 판단)
```

### 2단계 — AC kind 기반 판단 (룰 5)

| kind | 기본 stage | 영향 범위 항목 있으면 |
|------|-----------|-------------------|
| `docs` / `chore` | micro | micro (변화 없음) |
| `bug` | micro | standard |
| `feature` | standard | deep |
| `refactor` | standard | deep |
| kind 미지정 | standard | — |

- `영향 범위:` 항목: `feature` / `refactor`에서만 필요할 때 작성
- `bug` / `docs` / `chore`는 kind가 이미 스코프를 선언하므로 생략

### 3단계 — 플래그 오버라이드

```
--quick     → micro 강제
--deep      → deep 강제
--no-review → skip 강제
```

**충돌 처리**: 번호가 낮은 쪽 우선 (no-review > quick > deep > auto).

## 거대 커밋 정책

거대 커밋(파일 30+ 또는 diff 1500줄+)은 **스코프를 나눠 작은 커밋 여러
개로 분리**한다. pre-check이 감지 시 stderr 경고만 출력. 강제 분기 없음.

## git log 추적성

커밋 메시지 본문에 자동 포함:

```
🔍 review: <stage> | wip_kind: <kind> | scope: <영향범위유무>
```

Stage 0(skip)도 반드시 한 줄. **검증 안 한 사실 자체가 추적 대상.**

## 참조

- `pre_commit_check.py`: AC kind 읽기 + stage 결정 SSOT
- `commit/SKILL.md`: stage 분기 + 플래그 처리
- `review.md`: AC 기반 검증 수행
- `docs/decisions/hn_staging_governance.md`: 거버넌스·한계
