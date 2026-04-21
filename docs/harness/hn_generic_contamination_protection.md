---
title: 하네스 범용성 오염 방지 — 다운스트림 고유명사 유입 차단
domain: harness
tags: [harness-starter, contamination, generic]
status: completed
created: 2026-04-18
updated: 2026-04-19
---

## ✅ 완료 (2026-04-19)

- P1 pre-check + 허용 리스트 (커밋 f879396, v1.6.1)
- rules/contamination.md 신설 (영문 90+ / 한글 80+ 허용어, 면제 6종)

## 잔여 → 후속 WIP로 분리

- P2 review 검증 항목 + P3 스킬 질의 + 정밀화
  → `harness--hn_contamination_followup.md`

# 하네스 범용성 오염 방지

## 배경

harness-starter는 **범용 하네스 템플릿**이다. 다운스트림 프로젝트에 전파되는
기반 코드/문서이므로 다운스트림 프로젝트의 고유명사(제품명, 업체명, 엔티티 ID,
도메인 특화 용어)가 여기 박히면 다른 프로젝트에 전파 시 오염된다.

최근 세션에서 두 번 실수:
- 사용자가 제시한 다운스트림 사고 사례의 고유명사를 rules의 예시로 박음
- WIP 문서에 다운스트림 프로젝트 이름을 "현재 상태"로 명시

## 제안 방지 장치

### 1. harness-starter 전용 경고 (pre-check 확장)

`.claude/scripts/pre-commit-check.sh`에 추가:

```bash
# harness-starter 리포에서만 활성
if grep -q '"is_starter": true' .claude/HARNESS.json 2>/dev/null; then
  # staged diff에서 의심 고유명사 추출 (한글/영문 대문자 시작 단어)
  SUSPECT=$(git diff --cached -U0 | grep -E '^\+' | \
    grep -oE '[A-Z][a-zA-Z0-9]+|[가-힣]{2,}' | \
    sort -u | \
    grep -vE '^(CLAUDE|HARNESS|README|TODO|FIXME|...|일반|사용자|하네스)$')

  # 알려진 허용어(하네스 도메인 용어) 제외 후 남는 것이 있으면 경고
  # 초기에는 경고만, 패턴 정교화 후 차단
  if [ -n "$SUSPECT" ]; then
    echo "⚠️  harness-starter에 고유명사 가능 단어 감지:" >&2
    echo "$SUSPECT" | head -10 >&2
    echo "   다운스트림 프로젝트 특유의 이름이면 <제품명> 같은 placeholder로 교체하라." >&2
  fi
fi
```

### 2. 허용어 리스트 (.claude/rules/)

하네스 도메인 고유어(허용):
```
harness, starter, skill, agent, hook, matcher, rules, docs, WIP,
Claude, Anthropic, CLAUDE, Bash, Read, Glob, Grep, PreToolUse, PostToolUse,
...
```

이 리스트는 `.claude/rules/generic-allow-list.txt` 또는
`.claude/rules/contamination.md`에 관리.

### 3. write-doc/implementation 스킬 확장

새 문서 생성 시 harness-starter 리포에서는 다음 질문:

> 이 문서가 참조하는 고유명사가 있는가?
> 있다면 범용 placeholder(`<제품명>`, `<업체명>`)로 대체하라.
> 실제 이름이 꼭 필요하다면 그 근거를 문서에 남겨라.

### 4. review agent 검증 항목 추가

review.md에:

```
### 범용성 오염 (harness-starter 한정)
- diff에 다운스트림 프로젝트 특유의 고유명사가 들어있는가?
- 허용 리스트에 없는 대문자 시작 단어가 추가되었으면 근거 확인.
- 예시가 필요한 맥락이면 placeholder 사용 권장.
```

### 5. 연속 수정 + 범용성 오염 결합 감지 (참조만)

> **기능 소유**: `harness--hn_llm_mistake_guardrails.md` §4 "같은 영역 연속
> 수정 감지"가 구현한다. 이 문서는 **재구현하지 않고**, 해당 기능이 추가되면
> 고유명사 감지 결과와 결합해 차단 수준으로 격상하는 **통합 로직만** 추가한다.

같은 파일에 다운스트림 고유명사 의심 단어가 여러 커밋에 걸쳐 추가되면 경고가
아닌 **차단**으로 격상. 구현은 guardrails의 연속 수정 감지 후속 단계에서.

## 우선순위

- **P1**: 1 + 2 (pre-check + 허용 리스트) — 가장 싼 자동 방지
- **P2**: 4 (review agent)
- **P3**: 3 (스킬 질의) — UX 영향 크므로 후순위

## 구현 주의

- 정규식이 너무 느슨하면 오탐 대량 발생 (`CLAUDE`, `Bash` 같은 허용어까지 잡음)
- 허용 리스트 관리 비용이 큼 — 초기엔 경고 수준으로만, 오탐/미탐 보면서 조정
- 다운스트림 전파 시 이 pre-check이 다운스트림에서는 비활성화되어야 함
  (`is_starter` 체크로 처리)

## 관련 실패 사례

- 2026-04-18 범용 하네스 WIP에 다운스트림 사고 사례 고유명사 두 번 삽입
  (사용자 지적 후 세션 중 두 번 교정). 코드화된 방지 장치 없어서 재발 가능.
