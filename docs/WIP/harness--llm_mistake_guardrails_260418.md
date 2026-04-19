---
title: LLM 실수 방지 가드레일 — 내부 자료 우선 + 추측 차단 + advisor 연동
domain: harness
tags: [guardrails, self-correction, reliability, advisor-flow]
status: pending
created: 2026-04-18
updated: 2026-04-18
---

# LLM 실수 방지 가드레일

## 배경

하네스 개발 중 반복 관찰된 실패 패턴 6개:

1. **허위 진단 → 즉시 행동**: 확신 없는 가설을 "확정"으로 쓰고 바로 우회/수정
2. **성급한 단정**: 1~2회 테스트로 "X는 불가능"이라 결론, 변형 조건 미검증
3. **선행 성공 사례 무시** ⭐⭐⭐: **외부 자료는 검색해도 내부 자료 검토는 무시**.
   git history에 작동 사례가 있는데 새로 설계. **가장 파괴적인 패턴.**
4. **같은 영역 연속 수정**: 증상 완화 반복, 근본 원인 미도달. 테스트가 단위로
   분리되지 않아 어느 단계에서 실패했는지 추적 불가.
5. **허위 후속 작업 생성**: "재검토 필요" 같은 모호한 후속을 문서에 박음
6. **추측 기반 수정** ⭐⭐⭐: CLAUDE.md에 "추측 금지"를 명기해도 매번 "이것일
   거"라고 예측하고 수정 진행. **sonnet 사용 시 이 확률 크게 증가**.

설계 원칙: **CLAUDE.md 비대화 원치 않음.** 단순 텍스트 규칙은 무시된다.
`.claude/rules/` 명기 + 스킬/에이전트 흐름에 **자동 감지 코드**로 박는다.

---

## P0: 내부 자료 우선 (C3 대응)

### 규칙 명기

`.claude/rules/internal-first.md` (신설):

> **새 구조/가설을 제안하기 전 반드시 내부 자료부터 확인.**
>
> 순서:
> 1. **git history** — 관련 키워드로 `git log --all --oneline | grep` 그리고
>    관련 시점 파일 내용 확인
> 2. **docs/** — INDEX.md → clusters → decisions/incidents/guides 탐색
> 3. **rules/** — 관련 규칙이 이미 있는지
> 4. **사용자 증언** — "예전엔 됐다"는 말이 있으면 그 시점 찾기가 **최우선**
> 5. 그래도 부족하면 **외부 검색/문서**
>
> 외부(Context7 등) 검색이 먼저 나가면 이 규칙 위반.

### 자동 감지 흐름

**implementation 스킬 Step 0 + commit 스킬 Step 6(리뷰 직전)**:
- WIP 문서나 리뷰 프롬프트에 "공식 문서", "Context7", "SDK 문서" 언급이 있는데
  같은 맥락에서 "git log", "decisions/", "incidents/" 참조가 없으면 경고
- **경고만**: 사용자 판단이지만 자동으로 힌트 제공

### 규모 큰 판단: advisor로 확대

간단한 규칙·컨벤션은 self-check로 충분. 단 다음 상황은 **advisor 스킬**로 확대:
- 구조적 결정 (hook 구조 변경, 파일 레이아웃 변경 등)
- 여러 선택지가 있고 각각 트레이드오프 큰 경우
- 선행 실패 이력이 있는 영역

이 "규모 크다" 판단은 review 에이전트가 수행 (아래 advisor 연동 참조).

---

## P0: 추측 차단 (C4/C6 대응)

### 문제

사용자 지적: *"CLAUDE.md에 추측 금지 써도 매번 '이것일 거'라 예측하고 수정
진행. sonnet으로 모델 바꾸면 1,000% 증가."*

### 원인 가설

- 텍스트 규칙만으로는 LLM 행동 변화 유도 약함
- 자동 감지/차단 장치가 없어 위반 시 비용 없음
- "빠르게 답하려는" 기본 성향이 규칙을 override

### 규칙 명기

`.claude/rules/no-speculation.md` (신설):

> **추측으로 수정을 시작하지 마라.**
>
> 문제에 대한 첫 행동은 다음 중 하나여야 한다:
> 1. **관찰**: 실제 상태를 읽기 (파일, 로그, git status 등)
> 2. **재현**: 문제가 발생하는 최소 케이스 만들기
> 3. **선행 사례 확인**: 내부 자료(git/docs)에서 유사 사례
>
> 아래 행동은 금지:
> - "아마 X가 원인일 것"으로 시작해서 X를 바로 고치는 것
> - 원문을 보기 전에 해결책을 설계하는 것
> - 테스트 없이 "이제 될 것"이라고 결론내리는 것
>
> 확신이 없으면 말로 표현: "가설이다", "확인 필요". 사용자에게 검증 책임
> 넘기지 마라 — Claude가 관찰로 줄여야 한다.

### 자동 감지 흐름

**review 에이전트의 검증 항목**:
- 커밋 메시지·WIP에 "아마", "일 것 같은", "예상", "추정" 단어가 근거 없이
  있으면 경고
- diff가 "문제 설명 없이 바로 수정"으로만 구성되어 있으면 경고
  (해결하려는 문제 기술이 명확한가?)

**모델 선택의 영향**:
- commit_perf_optimization WIP의 모델 스위치에서 **추측이 나온 영역은 sonnet
  대신 opus 격상** 고려 (장기 개선)

---

## P1: 단위 분리 + 단계적 테스트 + 실패 보고 (C3 후반)

### 문제

사용자 지적: *"테스트가 단위 형태로 분리되지 않아 어느 과정에서 실패했는지
판단 불가. 결과적으로 증상 완화만 반복."*

### 규칙 (신설 or self-verify.md 확장)

**테스트 3원칙**:

1. **단위 분리** — 하나의 수정에 하나의 검증 가능 단위. 가설 → 변경 1개 →
   검증 1개. 여러 변경을 한 번에 시험하지 마라.

2. **단계적 테스트** — 실패가 나면 다음 중 판단:
   - **오류 단계만 수정**: 다른 단계는 유효, 해당 단계만 문제
   - **단위 플로우 자체 변경**: 가설 자체가 틀림, 되돌리고 재설계
   섣불리 "주변 환경도 같이 바꾸자"로 범위 확대 금지.

3. **실패 보고 형식** (중요):
   - **실패 시**: 무엇을 시도했고 → 무엇을 기대했고 → 실제 무슨 일이 일어났고
     → 거기서 **무엇을 배웠는지** 명시
   - **성공 시**: 한 줄로 간략히. 성공은 다 성공이니까.
   - 배움이 없는 실패는 반복된다.

### 자동 감지

**commit 스킬 Step 6(리뷰) 전 pre-check 단계에서**:
- 최근 N커밋 중 같은 파일을 반복 수정 중이면 "테스트 단위가 너무 넓지
  않은지" 경고 (아래 "연속 수정 감지"와 결합)

---

## P1: 같은 영역 연속 수정 감지 (C5 반영, 임계값 하향)

### 변경 요지

임계값 5회 → **2회 경고, 3회 차단**. (사용자 지적: "5회는 너무 관대")

### pre-commit-check.sh 확장

```bash
# 최근 커밋에서 같은 staged 파일이 반복 등장하는지
REPEAT_WARN=2   # 2회 반복: 경고
REPEAT_BLOCK=3  # 3회 반복: 차단 (근본 원인 재점검 요구)

# 최근 5커밋 (범위는 유지, 임계값만 조정)
RECENT_FILES=$(git log -5 --name-only --format= 2>/dev/null | sort)

git diff --cached --name-only | while read f; do
  COUNT=$(echo "$RECENT_FILES" | grep -cFx "$f")
  if [ "$COUNT" -ge "$REPEAT_BLOCK" ]; then
    echo "❌ $f: 최근 5커밋 중 ${COUNT}회 수정. 근본 원인 재점검 필요." >&2
    echo "   우회하려면 '--force-repeat' 플래그 또는 리뷰어 승인." >&2
    exit 2
  elif [ "$COUNT" -ge "$REPEAT_WARN" ]; then
    echo "⚠️  $f: 최근 5커밋 중 ${COUNT}회 수정. 근본 원인 미해결 의심." >&2
  fi
done
```

**정당한 반복 수정 이스케이프**:
- 기능을 단계별로 확장하는 정상 패턴은 `--force-repeat` 플래그로 허용
- 또는 커밋 메시지 첫 줄에 `[expand]` 태그 포함 시 면제

### 범용성 오염 결합

`harness--generic_contamination_protection_260418.md` §5에서 참조:
같은 파일에 고유명사 의심 단어가 반복 추가되면 **차단 수준 격상** — 이
기능의 구현 소유는 guardrails 쪽 (§위 로직에 contamination 감지 결과 주입).

---

## P1: 허위 후속 감지 (기존 유지)

### 규칙 명기

review 에이전트 검증 항목에 추가:

> WIP/커밋 메시지에 다음 패턴 있으면 경고:
> - "재검토 필요", "추후 확인", "검증 예정"
> - 왜 재검토가 필요한지 **구체 근거가 없으면** 차단
> - 근거 있으면 "X 때문에 Y 단계 후속 필요"처럼 명시 요구

---

## P0: advisor · review 동급 병렬 배치

### 설계 원칙

**review와 advisor는 역할이 다르며, 같은 선상의 독립 검증자다.**

| 검증자 | 질문 | 입력 | 모델 |
|--------|------|------|------|
| **review** | "이 diff가 괜찮은가?" (회귀·계약·스코프) | diff + pre-check 결과 | sonnet (frontmatter) |
| **advisor** | "이 결정이 맞는가?" (대안·트레이드오프·리스크) | 계획/결정 맥락 | Opus (상위 세션 상속) |

하나가 다른 하나를 호출하지 않는다. commit 스킬(메인, Opus)이 **diff 성격을
보고 둘을 독립 호출**한다.

### 모델 격상 자연화

- review는 sonnet으로 빠르게 diff 검증 (현재 frontmatter `model: sonnet`)
- advisor는 **에이전트로 승격**해 frontmatter `model: opus` 지정 필요.
  승격하면 commit 스킬이 sonnet으로 돌더라도 advisor 호출 시 자동으로 Opus
- 판단 성격에 맞는 모델이 자동 배정됨 (사용자 설정 없이)

### advisor 에이전트 승격 (선행 작업)

현재 advisor는 **스킬**이고 스킬 frontmatter는 model 필드 지원이 불명확하다.
따라서 다음 중 하나로 승격:

**방식 A — advisor 자체를 단일 에이전트로**
- `.claude/agents/advisor.md` 신설, `model: opus`
- 내부에서 3개 관점(research/codebase/risk)을 Agent tool로 병렬 호출
- **기술적 가능성 확인됨**: Claude Code는 복잡한 작업을 서브에이전트 여러 개에
  병렬 할당 지원. 3개 고정이 규칙은 아니며 2·4개도 가능.
- **주의 사항** (자동 위임이 기대대로 안 될 때):
  - 각 관점 에이전트의 `description`에 MUST use 같은 강한 문구
  - 또는 `@agent-name`으로 명시 호출
  - 이름 겹침 주의. `claude agents`로 활성 에이전트 목록 확인 가능

**방식 B — 부분 에이전트화**
- advisor 스킬 오케스트레이터는 유지 (상위 세션 모델 상속)
- 3개 관점(research/codebase/risk)을 개별 에이전트로 등록, 각 `model: opus`
- advisor 스킬이 Agent tool로 3개 에이전트 호출 → 병렬 검증
- 현재 구조 최소 변경. 단 사용자가 "Opus 메인"으로 돌지 않을 때 advisor
  오케스트레이션 부분은 sonnet 이하

**권장**: 방식 A. 자동 위임 신뢰성이 관건이므로 description 설계와
`@agent-name` 명시 호출 전략을 병행.

이 작업은 **이 WIP와 독립된 선행 작업**이므로 별도 WIP로 분리 후속 고려.

### commit 스킬 Step 6·7 흐름 재설계

현재 Step 7은 review 단독 호출. 다음과 같이 변경:

```
Step 6. 변경 내역 분석
  └─ 여기서 commit 스킬이 diff 성격 판단 (advisor 호출 필요 여부)

Step 7. 병렬 검증
  ├─ review 호출 (항상) — sonnet, diff 검증
  └─ advisor 호출 (조건부) — Opus, 결정 검증
      ↑ 아래 트리거 중 하나라도 hit 시

Step 8. 검증자 응답 종합 → 커밋 진행/차단
```

### advisor 호출 트리거 (commit 스킬이 Step 6에서 판단)

다음 중 **하나라도** 해당하면 review와 **병렬로** advisor 호출:

- **구조적 결정 포함**: 새 스킬/에이전트 추가, hook 구조 변경, 파일 레이아웃 변경
- **선행 실패 이력**: diff가 만지는 영역에 과거 incidents/ 기록 있음
- **여러 선택지가 있는 판단**: WIP 문서에 "A안/B안" 표기 또는
  커밋 메시지에 "...로 갔다"는 판단 이유 표현
- **규칙 신설 또는 변경**: `.claude/rules/` 변경 포함
- **공개 API 또는 공유 설정 변경**: `.claude/settings.json`, 공유 모듈

판단이 애매하면 review만 호출 (advisor는 명확한 트리거 hit 시에만).

### 응답 종합 규칙

- **review.block: true** → 즉시 차단 (advisor 결과 무관하게)
- **review.block: false + advisor.recommendation: block** → 사용자에게 근거
  제시 후 확인 요구
- **둘 다 통과** → 진행
- **advisor만 호출된 경우 없음** — review는 항상 실행

### 독립 호출도 가능

advisor는 커밋과 무관하게 **결정 단계**에서 독립 호출 가능 (현재도 그렇게
동작). guardrails는 커밋 흐름에서의 연동만 다룬다.

---

## 우선순위 정리

| 우선순위 | 항목 | 반영 위치 |
|---------|------|----------|
| P0 | 내부 자료 우선 (C3) | `.claude/rules/internal-first.md` (신설) + 자동 감지 |
| P0 | 추측 차단 (C4/C6) | `.claude/rules/no-speculation.md` (신설) + review 감지 |
| P0 | advisor 연동 흐름 A | `SKILL.md`(commit), `review.md`, `advisor` 스킬 |
| P1 | 단위 분리 + 단계적 테스트 + 실패 보고 (C3) | `self-verify.md` 확장 |
| P1 | 연속 수정 감지 임계값 하향 (C5) | `pre-commit-check.sh` |
| P1 | 허위 후속 감지 | `review.md` 검증 항목 |

## 구현 순서 제안

1. rules 신설 2개 (internal-first, no-speculation) — 가장 싸고 명시적
2. pre-commit-check.sh 임계값 수정 (2/3회)
3. review.md에 needs_advisor 기준 + 허위 후속 감지 항목 추가
4. commit 스킬 Step 7을 advisor 연동 흐름으로 확장
5. self-verify.md에 테스트 3원칙 추가

각 단계 **별도 커밋**으로. 한 번에 밀어넣지 말 것.
