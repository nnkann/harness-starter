---
signal: review 에이전트 응답에 verdict 단어(pass|warn|block) 첫 호출에서 누락 반복
domain: harness
keywords: [review, verdict, agent, prompt-compliance, extract-fail]
strength: medium
candidate_p: P8
---

# review verdict 누락 패턴

## 관찰

본 wave(2026-05-10, wip_util.py SSOT 통합 commit) review 호출에서 verdict
단어 미포함 응답 수신 → `extract_review_verdict.py` exit 1 → SendMessage
재호출 1회로 `verdict: warn` 추출 성공.

## 패턴

review.md "## 출력 형식 (SSOT)"이 첫 줄에 `verdict: <값>` **권장만 하고
강제 안 함**. 자유 서술로 분석을 풀어 쓰는 경우 verdict 단어 자체를 누락.

기존 박제: `docs/decisions/hn_review_verdict_compliance.md` — Agent tool
sub-agent prefill 미작동을 인지하고 형식 강제 폐기 + 추출 방식 채택.
즉 **시스템 결함은 이미 알려져 있고**, commit SKILL.md도 "추출 실패 →
재호출 1회 → 사용자 보고 + `[review-extract-fail]` 태그" 절차를 둠.

본 신호는 그 결함이 운영 중 실제 발화한 사례를 weak → medium 레벨로 박제.

## 영향

- 첫 호출 토큰 낭비 (재호출 발생)
- review 응답 시간 2배
- 재호출에서도 누락하면 사용자 보고로 escalate (운영 흐름 단절)

## 후속 판단 후보 (별 wave)

- review.md prompt에 "verdict 누락 시 응답 즉시 재시도" 메커니즘 추가
- 또는 commit SKILL.md prompt 조립 시 verdict 강제 첫 줄 prefill 시도
  (이전에 폐기된 방식이지만 재검토 가치)
- strong 승급 시 incident 등록 후보 (반복 카운트 누적 후)
