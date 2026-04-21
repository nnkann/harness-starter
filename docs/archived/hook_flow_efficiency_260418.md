---
title: hook 전체 흐름 효율성 검토 — PreToolUse/PostToolUse/Stop/SessionStart 통합 감사
domain: harness
tags: [hook, architecture, performance, ux]
status: abandoned
created: 2026-04-18
updated: 2026-04-19
---

# hook 전체 흐름 효율성 검토

## abandoned 사유 (2026-04-19, 단순화 후속)

본 WIP의 4개 산출물(감사 리포트·개선 제안·표준 가이드·`/eval --hooks`
스킬) 중 큰 작업은 진행하지 않기로 결정. 사유:

1. **단순화 정신과 충돌** — 새 감사 스크립트 추가 = "더 빼기"가 아니라
   "더 추가". 1인 운영 환경에서 분기별 자동 감사는 과함.

2. **이번 세션이 본 WIP 의도 80% 달성** — 단순화 작업과 시나리오 검증
   중 자연스럽게 처리됨:
   - PreToolUse `Bash(* -n *)` 광역 매처 오탐 발견·수정
     (커밋 1a50efd, incident hn_bash_n_flag_overblock)
   - 매처 substring 매칭 동작 문서화
   - 신규 hook 추가 시 격리 시나리오 검증 절차 확립
   - 매처 추가 4질문 도출 (광역 와일드카드 금지)

3. **남은 위험은 운영적 — `git commit -m "hello -n"` 같은 quote 안 -n
   매칭은 claude-code matcher가 잡지 못함. 발생 빈도 낮고 우회 쉬워
   (메시지 표현 변경) 코드 강제 가치 < 추가 복잡도.

## 회수된 부분

- 광역 매처 1건 수정 ✅
- 매처 동작 incident 기록 ✅
- 신규 hook 추가 시 검증 절차 (incident "재발 방지" 섹션) ✅

## 재검토 트리거

다음 발생 시 재평가:
- 분기 1회 이상 hook 오탐·우회·삽질 incident 누적
- 새 hook 이벤트(공식 문서 추가) 등장으로 통합 재설계 필요
- hook 수가 10개 초과 (현재 PreToolUse 6 + PostToolUse 1 + Stop·SessionStart·
  PostCompact 각 1 = 10)

---

## 원본 (참고용)

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

### 1. 현재 등록된 모든 hook 목록화 + 흐름 도식

단순 목록화로는 부족. **흐름이 보여야** 한다. 산출물에 다음을 포함:

- **이벤트 타임라인 도식**: 한 발화에서 어떤 hook이 어떤 순서로 트리거되고
  어디서 차단/통과하는지 (mermaid sequence 또는 ASCII)
- **유효성 평가**: 각 hook이 실제로 의도한 일을 하는지 (오탐/누락 사례)
- **개선점 요약**: hook별 한 줄 액션 (유지/병합/제거/재배치)
- **리포트 채널 설계**: hook 결과가 Claude에게 어떻게 전달되고, 사용자에게는
  어떻게 노출되는지 (현재는 stderr 텍스트만 → 산만함의 원인)

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

### 4. 외부 사례 조사 (차용 후보 발굴)

현재 쓰는 hook 평가에만 머무르지 말 것. **다른 곳에서 유효하게 쓰는 hook
패턴을 찾아 차용**해야 사각지대를 메울 수 있다.

조사 대상:
- **claude-code 공식 문서·예제**: 권장 hook 패턴, 새로 추가된 이벤트
- **plugin-dev 등 설치된 플러그인**: hook을 어떻게 구성하는지
- **커뮤니티 사례**: GitHub에서 `.claude/settings.json` 검색, 블로그 글
- **다른 IDE 자동화 (git hooks, husky, lefthook)**: 이벤트 모델 비교

산출물: "차용 후보 hook 리스트" — 패턴 / 출처 / 우리 하네스에 적용 시 가치

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

- `harness--hn_commit_perf_optimization.md`: commit 관련 hook은 이 검토와
  같이 진행하는 게 효율적
- `harness--hn_llm_mistake_guardrails.md`: 연속 수정 감지·고유명사 감지
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
