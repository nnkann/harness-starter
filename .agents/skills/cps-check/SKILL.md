---
name: cps-check
description: >-
  현재 작업의 C·P·S 정합을 결정적 grep으로 검사하는 옵트인 스킬. TRIGGER when:
  사용자가 "이 작업의 C·P·S 어떻게 봐?", "정합 확인해줘", "cps-check" 등 명시
  호출 시. SKIP: 호출 안 했으면 자동 실행 금지. implementation Step 2의 자동
  정합 substep과 같은 로직, 사용자 의견 개진용으로 단독 실행.
---

# CPS Check (옵트인)

implementation Step 2의 정합 substep을 사용자 명시 호출 시 단독 실행.
**호출 강제 없음** — 흐름에 박지 않음.

## 동작

1. 현재 WIP 파일 또는 사용자가 제시한 텍스트에서 C·P·S 추출
   - C = WIP `## 목표` 또는 frontmatter `c:` 또는 사용자 직접 입력
   - P = frontmatter `problem: P#`
   - S = frontmatter `s: [S2, S6]` 또는 `solution-ref` 번호
2. `docs_ops.py cps show P#`로 P# 정의 가져옴
3. **3축 결정적 측정**:
   - C·P 키워드 교집합 비율
   - P·S 키워드 교집합 비율 (S 정의는 kickoff에서 grep)
   - C·S 키워드 교집합 비율
4. 임계값(기본 0.3, wave 누적되며 좁혀나감)
5. 결과 출력 — 1줄 알림 또는 OK

## 출력 형식

```
[CPS 정합 — cp_{slug}]
C: <짧은 인용>
P: P8 (자가 발화 의존 규칙의 일반 실패)
S: [S8]

정합도:
  C·P: 0.42 (임계 0.3 통과)
  P·S: 0.51 (통과)
  C·S: 0.18 (⚠ 임계 미달)

→ C·S 정합 약함. 사용자 판단:
   (a) C 재정의 — 맥락 확장
   (b) 새 P# 후보 — P10 등록 검토
   (c) 무시 — 진행
```

## 어긋남 후속 행동

본 스킬은 **감지·알림만**. 자동 발굴·후보 제안 없음.
사용자/메인 Claude가 판단:
- C 재정의 → WIP 본문 수정
- 새 P# → `docs_ops.py cps add "1줄"`
- 무시 → 진행

## 호출 예시

- "cps-check 돌려줘"
- "이 작업 C·P·S 정합 봐줘"
- "/cps-check"

## 흐름에 박지 않는 이유

자동 실행은 implementation Step 2가 담당. 본 스킬은 사용자가 의식적으로
의견 묻고 싶을 때 단독 실행용. 호출 강제 = 자가 발화 의존 복귀.

