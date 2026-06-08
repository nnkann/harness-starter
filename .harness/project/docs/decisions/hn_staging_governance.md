---

title: Review Staging 거버넌스 — 신호 추가 게이트와 알려진 한계
domain: harness
tags: [staging, review, governance]
problem: P2
s: [S2]
status: completed
created: 2026-04-20
---

# Review Staging 거버넌스

`.claude/rules/staging.md`의 **운영 룰**(신호 정의·Stage 결정·매핑)에서
분리한 **거버넌스 문서**. LLM이 매 커밋마다 읽지 않아도 되는 메타 규범과
알려진 한계를 모은다.

분리 사유: rules/staging.md가 5.9k 토큰 → 매 세션 시스템 프롬프트에 박혀
들어감. 거버넌스/한계 섹션은 신호 추가·재설계 시점에만 필요.

## 폭증 차단 게이트

### 신호 추가 4질문

신규 신호 추가 전 모두 통과 필요:

1. 기존 신호와 70% 이상 겹치는가? Y → 추가 금지 (sub-rule로 흡수)
2. 연 1회 미만 hit 예상되는가? Y → 추가 금지 (유지 부담 > 가치)
3. 셸로 정확히 감지 가능한가? N → 추가 보류 (오탐 위험)
4. 검증 카테고리가 기존과 다른가? N → 추가 금지 (stage 격상으로 충분)

### 중복 신호 식별·통합 (별도 신호 금지 → 기존 흡수)

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

## 알려진 한계

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

## pre-commit-check.sh stdout 스키마

SSOT는 `.claude/scripts/pre-commit-check.sh` 자체. 이 문서는 사람이
읽기용 요약일 뿐 **참조 시 항상 스크립트로 검증할 것**.

```
pre_check_passed: true|false
already_verified: lint todo_fixme test_location wip_cleanup
risk_factors: <세미콜론 구분>
diff_stats: files=N,+A,-D
signals: S1,S2,S5,...
domains: harness,docs
domain_grades: critical,meta
multi_domain: true|false
repeat_count: max=N
recommended_stage: skip|micro|standard|deep
needs_test_strategist: true|false
test_targets: <콤마 구분>
s1_level: ""|file-only|line-confirmed
```
