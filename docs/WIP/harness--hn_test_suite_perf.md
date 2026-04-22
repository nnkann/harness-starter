---
title: test-pre-commit 스위트 성능 — 잔여 구조 재설계
domain: harness
tags: [pre-check, test, perf, structure]
status: pending
created: 2026-04-22
updated: 2026-04-23
---

# test-pre-commit 스위트 성능 — 잔여 구조 재설계

2026-04-23 세션에서 단순 최적화(-40%)를 달성했으나, 남은 구간은 구조
재설계 없이는 의미 있는 개선이 어렵다. 본 WIP는 **다음 착수 조건과
방향만** 기록. 즉시 작업 대상 아님.

## 현재 실측 (2026-04-23 기준)

- **스위트 전체**: 91초 (date 명령 측정, Windows Git Bash 업스트림 repo)
- **pre-check 호출**: 42회 (run_case 50 - 캐시 히트 5 + 특수 2)
- **호출당 평균**: 2129ms (tmp clone 환경, 업스트림 리포 내 직접 실행의 ~2배)

**시간 분해**:
| 구간 | 비중 |
|------|------|
| pre-check 42회 실행 | ~90초 (99%) |
| reset / fixture 셋업 / 로그 출력 | ~1초 |

→ 스위트 시간의 99%가 pre-check 실행. 나머지 구간 최적화는 측정 noise
수준.

## 이번 세션 처리 완료 (2026-04-23)

| 버전 | 내용 | 실측 |
|------|------|------|
| v0.20.8 | task-groups 할당 루프 awk 통합 (파일당 fork 제거) | 151s → 124s |
| v0.20.9 | test-pre-commit fixture 캐시 (다중 key run_case 재실행 제거) | 124s → 98s |
| v0.20.10 | tmp → 리포 내 sandbox 디렉토리 | 98s → 91s |

**합계 -60초 (-40%)**. git history 조회: `git log --grep "(v0\.20\.(8\|9\|10))"`

## 롤백 (효과 없거나 diminishing)

- **pre-check NAME_STATUS 3 awk → 1 awk 통합**: 측정상 차이 없음
- **메타 흡수 2 awk → 1 awk NR==FNR 트릭**: 측정상 차이 없음
- **DOC_DOMAINS xargs 통합 + 등급 매핑 case 패턴**: 스위트 91초→91초
  (개별 pre-check은 noise 수준). 복잡도만 증가

공통 원인: pre-check 1회 2.1초 중 **고정 오버헤드**(bash 시작·git 3회 호출·
lint 감지)가 큼. 내부 awk·grep 호출 한두 개 줄여도 총합에서 묻힘.

## 남은 방향 (구조 재설계 필요)

### 1. 공유 fixture — 가장 효과 큰 방향

현재 reset × 45 = pre-check × 45. **T 케이스 여러 개가 같은 fixture를
공유하면 pre-check 1회만 실행**하고 여러 key 검증 가능.

- 예: T5~T10 모두 "S8 export 검출" 테스트 → 각자 fixture 만들지 말고 한
  fixture에서 여러 케이스 검증
- pre-check 호출 42 → ~15회까지 감소 가능
- **예상**: 91초 → 40~50초

**위험**: 테스트 간 의존성 생김, fixture 설계 난이도 상승. 실측 실패 시
격리 회복 어려움.

### 2. pre-check 자체 "테스트 모드" — diminishing 아님

pre-check 내부에 `TEST_MODE=1` 같은 환경변수 → lint 호출 skip, CLAUDE.md
파싱 skip, 외부 자료 조회 skip. 회귀 검증에 필요 없는 부분만 제거.

- **예상 절감**: pre-check 1회 2.1초 → 1.2초 수준
- **위험**: "테스트 때만 다른 경로" = 실제 환경 검증 못 함. pre-check
  자체 변경 시 테스트 모드와 실 모드 모두 확인 필요

### 3. 병렬화

이전에 사용자가 지적한 대로 증상 우회. 단, 공유 fixture와 결합하면
의미 있을 수 있음 (격리된 독립 그룹만 병렬).

## 착수 조건

- 스위트 시간이 **체감 장벽**이 될 때만. 현재 91초는 개발 중 1~2회 돌릴
  만한 수준
- 프로파일링 재실행으로 2.1초가 여전히 유효한지 확인 (환경·OS·fs 변경
  가능성)
- 공유 fixture 재설계는 **전체 T 케이스 맵 작성** 선행 — 어느 T끼리 묶일
  수 있나

## 영향 파일

- 주: `.claude/scripts/test-pre-commit.sh` (구조)
- 보조: `.claude/scripts/pre-commit-check.sh` (TEST_MODE 옵션)

## 검증 기준

- 스위트 < 60초 (목표)
- 회귀 64/64 유지
- test-bash-guard 18/18 유지
- 격리성: 단일 T 케이스 실패 시 다른 케이스로 전파 없음
