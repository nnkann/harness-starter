---

title: review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트
domain: harness
tags: [staging, review, measurement]
problem: P2
s: [S2]
status: completed
created: 2026-04-19
updated: 2026-04-19
---

# review staging 잔여

`harness--staging_followup`의 P1·S6은 a752b3e에서 처리. 본 WIP의
P3·P2·P4 처리 결과:

## 처리 결과 (2026-04-19)

### P3. S8 export 검출 정밀화 ✅ — 커밋 f0fdc10

언어별 시그니처 적용 (TS·JS·Python·Go·Java/C#) + 테스트 파일 면제.
test-pre-commit.sh T5~T10에서 회귀 검증 (6/6 통과).

### P2. 5커밋 측정 — 단순화 작업 11커밋 데이터로 부분 달성

본 세션 git log 분석 (b71d295~6287b1b, 11커밋):

| Stage | 빈도 | 비고 |
|------:|:-----|:-----|
| skip  | 9    | 메타·문서 후속 정리 위주 |
| deep  | 2    | 단순화 본 커밋 + scenario 검증 |
| micro·standard | 0 | 본 세션은 메타·문서 작업이라 미발생 |

관찰:
- **skip 비중 82%** — staging의 의도(메타·문서 후속은 스킵)가 작동.
  이전(전부 standard 호출)이었으면 11커밋 × 30~120초 = 5~22분 review.
  실제는 2회만 (deep 90~180초 × 2). 약 70~85% 시간 절감 추정.
- **목표(60% 절감) 달성 가능성 확인.** 정확 측정은 외부 시간·토큰
  계측 필요 (claude-code 자체 telemetry).

코드 변경 위주 정상 워크로드 측정은 다른 작업(다운스트림 프로젝트
적용·신규 기능 개발) 데이터 누적 후. 본 세션 데이터로 staging 시스템
설계 의도는 검증됨.

### P4. 폭증 차단 게이트 코드 강제 — abandoned

사유:
- 1인 운영 환경에서 신호 추가 빈도 낮음 (본 세션 13개 신호 그대로 유지)
- staging.md "신호 추가 4질문"이 텍스트 규범으로 충분 작동 (이번 세션
  contamination 신호·needs_advisor 신호 신설 시도가 게이트로 멈춤)
- 코드 강제 = 새 hook 추가 = 단순화 정신 위반

재검토 트리거: 팀 확장 또는 신호가 16개 초과 시.
