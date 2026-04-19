---
title: 범용성 오염 방지 후속 — review 검증 항목 + 스킬 질의
domain: harness
tags: [contamination, review, write-doc]
relates-to:
  - path: ../harness/generic_contamination_protection_260418.md
    rel: extends
status: pending
created: 2026-04-19
---

# 범용성 오염 방지 후속

원본 WIP `harness--generic_contamination_protection_260418.md`의 잔여
P2/P3 항목.

## 완료된 것

- P1: pre-check + contamination.md 허용어 리스트 (커밋 f879396)
- 면제 파일 6종 (incidents/·promotion-log·HARNESS.json·scripts/·hooks/·자기 자신)
- ALLOWLIST 영문 90+ / 한글 80+

## 잔여 작업

### P2. review 에이전트 검증 항목 추가

review.md에 "범용성 오염" 카테고리 신설 (rules/staging.md의 신호↔카테고리
매핑에도 등록):

```
### 범용성 오염 (harness-starter 한정)
- diff에 다운스트림 프로젝트 특유의 고유명사가 들어있는가?
- 허용 리스트에 없는 대문자 시작 단어가 추가되었으면 근거 확인
- 예시가 필요한 맥락이면 placeholder 사용 권장
```

신호 신설 검토: S16(contamination hit) — 기존 신호와 70% 겹침 게이트 통과 여부 점검 필요.

### P3. write-doc/implementation 스킬 확장

새 문서 생성 시 harness-starter 리포에서:
> 이 문서가 참조하는 고유명사가 있는가?
> 있다면 범용 placeholder(`<제품명>`, `<업체명>`)로 대체.
> 실제 이름이 꼭 필요하다면 그 근거를 문서에 남겨라.

UX 영향 크므로 후순위. pre-check 검출만으로 일정 부분 잡히는지 관찰 후 결정.

### 정밀화 후속

- 소문자로 시작하는 고유명사 검출 (현재 미탐) — 위험·이득 평가 후
- docs/clusters/·docs/INDEX.md 면제 추가 검토
- ALLOWLIST 동기화 자동화 (contamination.md ↔ pre-check.sh 양쪽 관리 부담)

## 우선순위

P2~P3. P1만으로 핵심 사고는 막힘. staging의 risk_factors에 "오염 의심"
이 들어가면 review가 보긴 함 — review.md에 명시 카테고리만 추가하면 됨.

## 검증

- review가 contamination 신호 hit 시 적절히 검증하는지
- 다운스트림 프로젝트에서 이 규칙이 비활성화되는지 (is_starter false 케이스)
