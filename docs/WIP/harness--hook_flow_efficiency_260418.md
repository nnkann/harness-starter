---
title: hook 전체 흐름 효율성 검토 — PreToolUse/PostToolUse/Stop/SessionStart 통합 감사
domain: harness
tags: [hook, architecture, performance, ux]
status: pending
created: 2026-04-18
---

# hook 전체 흐름 효율성 검토

## 배경

사용자 원칙: **"하네스가 걸리적거리면 실패 프로젝트. 항상 도움을 준다는 느낌이
들도록 확실하게."**

현재 hook 구성이 각 기능 단위로 쌓여 있고 전체 관점에서 **비용-효용 감사**가
된 적이 없다. 최근 hook 관련 실패 경험:
- prompt/agent type hook이 리뷰 목적으로 동작 안 함 (v1.2.0~v1.3.0 2일간 삽질)
- hook matcher 문법 오류로 2일간 전체 hook 무력 (v1.0.3~v1.2.0)
- pre-commit-check이 문서 내 TODO 키워드에 오탐 (메타 케이스)

이런 실패가 쌓이면 하네스 자체에 대한 신뢰 저하.

## 검토 범위

### 1. 현재 등록된 모든 hook 목록화

`.claude/settings.json`의 이벤트별 hook 전수 조사. 각 항목에 대해:
- **이벤트**: PreToolUse / PostToolUse / Stop / SessionStart / PostCompact / UserPromptSubmit 등
- **matcher**: 어떤 도구에 걸리나
- **type**: command / prompt / agent / http
- **목적**: 왜 있는가
- **비용**: 매 발화마다 드는 시간 (측정 필요)
- **효용**: 실제로 잡은 실수 수 (로그 분석 필요)
- **오탐 이력**: 잘못 차단한 사례

### 2. "걸리적거림" 패턴 식별

아래 경험이 있는 hook은 개선 대상:
- 정당한 작업을 차단해 우회/재시도를 유발
- 발화 빈도는 높은데 실제로 문제를 잡은 적은 드묾
- hook 출력이 산만해서 진짜 중요한 경고가 묻힘
- hook 자체가 느려서 체감 저하

### 3. 이벤트별 용도 재검토

공식 문서 기준 각 이벤트의 적합한 용도:
- **PreToolUse**: 도구 실행 전 차단/검증 (gate)
- **PostToolUse**: 실행 후 자동 검증 (agent type 권장)
- **Stop**: Claude가 응답 끝내려 할 때 — 미완료 검증
- **SessionStart**: 세션 컨텍스트 주입
- **PostCompact**: 컨텍스트 압축 후 핵심 정보 복원
- **UserPromptSubmit**: 프롬프트 사전 필터링

현재 하네스가 각 이벤트를 **용도에 맞게** 쓰고 있는가?

## 개선 원칙 (초안)

1. **차단은 명확한 근거가 있을 때만** — 애매하면 경고로 시작
2. **hook 출력은 정보 밀도 높게** — 긴 메시지 금지, 핵심 한 줄
3. **비용-효용 주기적 재평가** — 적어도 분기별 1회 전수 감사
4. **오탐 발생 시 스크립트 개선, 우회 금지**
5. **사용자가 hook 이름만 보고 역할을 알 수 있어야 함**
6. **Claude에게 주는 피드백이 실행 가능한 수준이어야 함** (단순히 "에러"
   가 아니라 "X를 Y로 고쳐라")

## 산출물

1. **현재 hook 감사 리포트** — 전체 목록 + 비용/효용 표
2. **개선 제안 문서** — 제거·병합·재배치 제안
3. **hook 표준 가이드** — 신규 hook 추가 시 따라야 할 원칙
4. (선택) `/eval --hooks` 스킬 또는 옵션 — 주기적 감사 자동화

## 연관

- `harness--commit_perf_optimization_260418.md`: commit 관련 hook은 이 검토와
  같이 진행하는 게 효율적
- `harness--llm_mistake_guardrails_260418.md`: 연속 수정 감지·고유명사 감지
  같은 신규 hook 아이디어는 이 검토 결과 나온 표준 가이드에 맞춰야 함

## 우선순위

P2. 당장 동작 중인 hook이 심각한 문제를 일으키고 있지는 않다. 다만 **하네스
신뢰성의 장기 건전성**에 중요하므로 분기별 검토 권장.

## 검토 방법 제안

1. **감사 스크립트 작성**: `.claude/scripts/hook-audit.sh` — settings.json
   파싱 + 최근 세션 hook 발화 로그 집계
2. **리포트 자동 생성**: 감사 결과를 `docs/harness/hook-audit-YYMMDD.md`로
3. **세션 종료 시 힌트**: SessionStop에 "이번 세션에서 hook이 N회 발화하고
   M건 차단" 요약을 주면 hook 과밀도 자각 도움

## 우려

hook 검토가 또 다른 미로가 될 위험. 최근 2일간 hook 삽질 경험을 반복 않으려면:
- **관찰부터**, 수정은 나중
- 감사 스크립트부터 만들고 데이터 보고 개선안 설계
- 한 번에 여러 hook 건드리지 말 것 (단위 분리)
