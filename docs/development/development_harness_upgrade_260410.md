> status: completed

# Harness-Starter 업그레이드 계획 (claude-code 소스 기반)

## 배경

claude-code 소스(Anthropic 공식 CLI 역공학 분석 레포: github.com/l3tchupkt/claude-code)를 분석하여
harness-starter에 적용할 수 있는 패턴을 추출했다.
목표: **큰 관점에서 가볍게, 세부 관점에서 효율적으로**. 과도한 복잡성 없이 실질적 가치가 있는 것만 적용.

---

## 거시적 분석 (큰 그림에서 빠진 것)

| 영역 | claude-code | harness-starter 현재 | 갭 |
|------|-------------|---------------------|-----|
| **Memory** | 4타입 메모리 (user/feedback/project/reference) + findRelevantMemories | WIP 문서 + 훅으로 분산 | 세션 간 학습 없음 |
| **PostCompact** | 토큰 압축 시 멀티 전략 (reactive-compact, snip, context-collapse) | 단순 규칙 재출력 | 작업 컨텍스트 유실 |
| **Skill 트리거** | path-conditional (gitignore 패턴), 자동 활성화 | 수동 `/skill` 호출만 | 자동 개입 불가 |
| **에러 복구** | stuck 스킬, debug 스킬, 자동 fallback | self-verify 규칙만 (행동 가이드) | 막혔을 때 탈출구 없음 |
| **비용 추적** | 세션별 cost-tracker (USD, 토큰, 코드 변경량) | 없음 | 비용 인식 없음 |
| **Hook 다양성** | PreToolUse/PostToolUse/Stop 등 세밀한 매처 | 4개 스크립트 (기본적) | 개입 지점 부족 |

---

## 미시적 분석 (세부에서 효율화할 것)

| 항목 | 현재 문제 | claude-code에서 배울 점 |
|------|----------|----------------------|
| session-start.sh | 매번 같은 출력, 실제 git 상태 무시 | git diff --stat, 마지막 커밋 시간 표시 |
| post-compact-guard.sh | 규칙만 재출력, 작업 맥락 소실 | 현재 진행 중인 작업의 핵심 결정사항 재주입 |
| pre-commit-check.sh | staged 파일만 검사, pnpm/yarn 미지원 | CLAUDE.md의 패키지 매니저 설정 읽어서 동적 분기 |
| auto-format.sh | jq 의존, Windows 호환 이슈 가능 | 포매터 없을 때 silent fail은 좋으나, 포맷 결과 리포트 없음 |
| 스킬 간 연결 | 각 스킬 독립적, 흐름 끊김 | implementation -> commit 자동 전환 패턴 |

---

## 업그레이드 계획 (우선순위순)

### Phase 1: 진입점 강화 (가볍고 즉각적)

#### 1-1. session-start.sh 개선
- **파일**: `.claude/scripts/session-start.sh`
- **추가**:
  - `git log --oneline -3` 으로 최근 작업 맥락 표시
  - `git diff --stat` 으로 uncommitted 변경 요약
  - 마지막 커밋 경과 시간 표시 ("2시간 전")
- **이유**: 세션 시작 시 "어디까지 했더라?"를 즉시 파악

#### 1-2. post-compact-guard.sh 개선
- **파일**: `.claude/scripts/post-compact-guard.sh`
- **추가**:
  - WIP 문서의 `## 결정 사항` 섹션 내용 재주입 (있으면)
  - `git diff --cached --stat` (staged 상태 복원)
  - 현재 TODO 진행률 표시
- **이유**: 컴팩션 후 "뭘 하고 있었지?" 문제 해결

#### 1-3. pre-commit-check.sh 동적 패키지 매니저
- **파일**: `.claude/scripts/pre-commit-check.sh`
- **변경**: CLAUDE.md에서 `패키지 매니저:` 읽어서 lint 명령 동적 결정
  - npm -> npm run lint
  - pnpm -> pnpm lint
  - yarn -> yarn lint
  - pip/ruff -> ruff check .
- **이유**: 프로젝트마다 setup 없이 자동 적응

### Phase 2: Memory 시스템 도입 (가장 큰 갭)

#### 2-1. Memory 인프라 구축
- **새 파일**: `.claude/rules/memory.md`
- **내용**: harness-starter에 맞춘 메모리 가이드라인
  - `feedback` 타입 우선 (사용자가 수정한 접근법 기억)
  - `project` 타입 (현재 프로젝트 맥락, 마감일 등)
  - 메모리 경로: 프로젝트별 `.claude/memory/` 디렉토리
- **이유**: 세션 간 학습이 없으면 같은 실수 반복. 하네스의 핵심 철학("실수를 코드화")과 일치

#### 2-2. session-start에 메모리 참조 추가
- **파일**: `.claude/scripts/session-start.sh`
- **추가**: MEMORY.md 존재 시 메모리 수 표시
- **이유**: 메모리가 있다는 인식 -> 활용률 상승

### Phase 3: Hook 진입점 확장 (claude-code 패턴 차용)

#### 3-1. Stop 훅 추가 (세션 종료 시)
- **파일**: `.claude/settings.json`에 Stop 훅 추가 고려
- **목적**: 세션 종료 시 자동으로:
  - WIP 상태 업데이트 (in-progress인데 작업 안 했으면 경고)
  - 미커밋 변경 경고
- **주의**: Stop 훅이 현재 지원되는지 확인 필요 -> 지원되면 스크립트 추가

#### 3-2. Notification 훅 패턴
- **파일**: `.claude/scripts/post-compact-guard.sh`
- **개선**: 컴팩션 횟수 카운팅 (파일에 기록), 3회 이상이면 "작업이 너무 큼, 분할 고려" 안내
- **이유**: claude-code의 "토큰 압력에 따른 전략 분기" 아이디어를 단순화

### Phase 4: 스킬 자동 트리거 (path-conditional)

#### 4-1. check-existing 자동 트리거
- **파일**: `.claude/settings.json` PreToolUse 훅 추가
- **매처**: `Write` (새 파일 생성 시)
- **동작**: 파일이 `src/` 하위 + 새 파일이면, check-existing 관련 안내 출력
- **이유**: 수동으로 /check-existing 호출 잊는 문제 해결. claude-code의 path-conditional 패턴을 훅으로 구현

#### 4-2. naming 규칙 자동 체크
- **파일**: `.claude/settings.json` PreToolUse 훅 추가
- **매처**: `Write` (새 파일 생성 시)
- **동작**: naming.md의 규칙에 맞는지 파일명 패턴 검사 (snake_case 등)
- **이유**: CLAUDE.md의 `<important>` 블록은 "부탁"이지만, 훅은 "강제"

### Phase 5: eval 스킬 경량화 (--quick 모드)

#### 5-1. eval에 --quick 플래그 추가
- **파일**: `.claude/skills/eval/SKILL.md`
- **추가**: `--quick` 모드 - 30초 이내 빠른 체크
  - 린터 에러 수
  - 미완료 WIP 문서 수
  - TODO/FIXME 수
  - 마지막 커밋 경과 시간
- **이유**: 현재 eval은 무겁다 (gap analysis, harness quality 등). 빠른 헬스체크가 없음

### Phase 6: 멀티 에이전트 오케스트레이션

하네스의 전체 워크플로우에서 멀티 에이전트가 개입할 수 있는 **교차 지점 맵**:

```
harness-init ──→ implementation ──→ (작업) ──→ commit ──→ eval
     │                │                │           │          │
  [6-3]            [6-2a]          [6-1]       [6-2b]     [6-2c]
  스택 검증        접근법 검증     /advisor     리뷰 분리   병렬 분석
```

#### 6-1. advisor 스킬 신설 (독립 호출 — 언제든 사용 가능)
- **새 파일**: `.claude/skills/advisor/SKILL.md`
- **호출**: `/advisor <질문 또는 계획>`
- **트리거 시점**: 사용자가 판단이 어려울 때 수동 호출
- **동작**:
  1. 사용자의 질문/계획을 받아 3개 관점의 Agent를 **병렬** 호출
     - **리서치 에이전트**: 웹서칭으로 관련 기술 동향, 논문, 베스트 프랙티스 조사 (WebSearch + WebFetch 활용)
     - **코드 분석 에이전트**: 현재 코드베이스 탐색, 기존 패턴과의 정합성 검증 (Explore 서브에이전트)
     - **리스크 에이전트**: 보안, 성능, 유지보수 관점에서 리스크 식별 (Explore + 경험 기반)
  2. 3개 결과를 종합하여 **추천 + 주의사항 + 대안** 형태로 보고
  3. 사용자가 판단할 수 있는 근거 제공 (링크, 코드 위치 등)
- **이유**: 판단이 어려울 때 다각도 검증. "협업하는 느낌"을 실현
- **핵심 원칙**: advisor는 조언만 한다. 결정은 사용자가 내린다.

#### 6-2. 기존 스킬에 에이전트 검증 단계 삽입 (경량 통합)

**6-2a. implementation 스킬 — 접근법 검증**
- **트리거 시점**: Step 0 (CPS 체크) 이후, Step 1 (문서 생성) 이전
- **추가**: Step 0.5 `접근법 검증 (선택)`
  - 사용자에게 "이 계획을 검증할까요? [Y/n]" 질문
  - Y 선택 시: advisor의 리서치+코드분석 에이전트 2개 병렬 호출
    - 리서치: "이 접근법에 대한 업계 사례, 알려진 문제점, 대안"
    - 코드분석: "현재 코드베이스에서 이 접근법이 기존 패턴과 충돌하는지"
  - 결과를 WIP 문서의 `## 메모`에 자동 기록
- **이유**: 구현 전에 방향성 검증. 나중에 되돌리는 비용 절약.

**6-2b. commit 스킬 (strict 모드) — 리뷰 에이전트 분리**
- **트리거 시점**: Step 5S (Review 검증) 실행 시
- **현재**: 메인 에이전트가 직접 CPS 정합성, side effect, naming 검증
- **변경**: 별도 Agent 호출로 독립적 리뷰 (메인 컨텍스트 오염 방지)
  - 리뷰 에이전트에게 전달: `git diff --cached` + CPS 문서 + naming.md
  - 리뷰 에이전트가 차단/주의/참고 판정
  - 결과를 커밋 메시지 `[📝 Key Notes]`에 반영
- **이유**: 자기가 쓴 코드를 자기가 리뷰하는 편향 제거. 독립 관점 확보.

**6-2c. eval --deep — 3관점 병렬화**
- **트리거 시점**: `/eval --deep` 또는 `/eval --harness --deep` 실행 시
- **현재**: 파괴자/트렌드/비용 3관점을 순차 분석
- **변경**: 3개 Agent를 **병렬 호출**, 각각 독립적으로 분석 후 결과 합산
  - 파괴자 에이전트: 취약점, 깨지는 경로 탐색
  - 트렌드 에이전트: 웹서칭으로 현재 시점의 기술 트렌드 대비 검토
  - 비용 에이전트: 코드베이스에서 과잉/미사용 탐색
- **이유**: 독립 관점 보장 (순차 실행 시 앞 분석이 뒤 분석에 영향). 속도 향상.

#### 6-3. harness-init — 스택 결정 검증 (신규)
- **트리거 시점**: Step 6 (스택 결정) 에서 선택지 제시 전
- **동작**: 리서치 에이전트가 후보 기술들의 최신 상태를 웹서칭으로 확인
  - deprecated 여부, 최근 릴리스 날짜, 커뮤니티 활성도
  - "이 조합을 실제로 쓰고 있는 프로젝트" 사례 검색
- **결과**: Standards 원칙의 "오래된 정보를 최신처럼 말하지 마라"를 **실제로 검증**
- **이유**: 모델의 학습 데이터 컷오프 한계를 웹서칭으로 보완

#### 멀티 에이전트 설계 원칙

| 원칙 | 설명 |
|------|------|
| **사용자 주도** | 자동 실행 아님. advisor는 항상 사용자 호출 또는 Y/n 확인 후 실행 |
| **병렬 우선** | 독립적 관점은 반드시 병렬. 순차 실행하면 앞 결과가 뒤를 오염 |
| **결과만 반환** | 에이전트는 조사+분석만. 코드 수정 권한 없음 (읽기 전용) |
| **실패 허용** | 에이전트 1개 실패해도 나머지 결과로 진행. 전체 차단 안 함 |
| **비용 인식** | 에이전트 호출 = 추가 토큰 비용. 사소한 작업에는 사용하지 않음 |

---

## 적용하지 않는 것 (과도한 복잡성)

| claude-code 기능 | 미적용 이유 |
|------------------|-----------|
| Coordinator 모드 (전체 오케스트레이터) | claude-code의 전체 Coordinator 모드(모든 작업을 에이전트에 위임)는 과도. 대신 Phase 6에서 **필요 시점에 멀티 에이전트를 호출하는 경량 방식**으로 도입 |
| Bridge/Remote 세션 | 로컬 개발 하네스에 불필요 |
| Plugin 시스템 | 스킬 시스템으로 충분. 플러그인은 오버엔지니어링 |
| 비용 추적 시스템 | 유용하나 구현 복잡도 높음. 나중에 별도로 |
| Voice/IDE 통합 | 이미 VSCode 확장으로 동작 중. 별도 구현 불필요 |
| Fast-path 라우팅 | CLI 레벨 최적화. 하네스 영역 밖 |

---

## 수정 대상 파일 요약

| 파일 | 변경 유형 |
|------|----------|
| `.claude/scripts/session-start.sh` | 수정 (git 상태 + 메모리 참조 추가) |
| `.claude/scripts/post-compact-guard.sh` | 수정 (결정사항 재주입 + staged 상태) |
| `.claude/scripts/pre-commit-check.sh` | 수정 (동적 패키지 매니저) |
| `.claude/settings.json` | 수정 (Write PreToolUse 훅 추가) |
| `.claude/rules/memory.md` | **새 파일** (메모리 활용 가이드) |
| `.claude/skills/eval/SKILL.md` | 수정 (--quick 모드 + --deep 병렬화) |
| `.claude/skills/advisor/SKILL.md` | **새 파일** (멀티 에이전트 검증 스킬) |
| `.claude/skills/implementation/SKILL.md` | 수정 (접근법 검증 단계 추가) |
| `.claude/skills/commit/SKILL.md` | 수정 (strict 리뷰를 Agent로 분리) |
| `setup.sh` | 수정 (memory 디렉토리 + advisor 스킬 포함) |

## 결정 사항

- advisor 스킬의 리서치 에이전트는 Context7 MCP(공식 문서)를 1순위 출처로 사용 (사용자 피드백 반영)
- Coordinator 모드는 전체 도입 대신 경량 멀티 에이전트 패턴으로 Phase 6에 승격 (사용자 피드백 반영)
- Stop 훅 지원 확인됨 — stop-guard.sh 추가
- .compact_count는 gitignore 대상 (세션 임시 파일)
- full 프로파일에 advisor 스킬 포함

## 메모

- 출처: github.com/l3tchupkt/claude-code (Anthropic CLI 역공학 분석)
- claude-code는 803KB main.tsx, 120+ hooks, 180+ commands를 가진 대규모 프로덕션 시스템
- harness-starter는 이 중 "하네스 엔지니어링"에 해당하는 진입점만 차용
