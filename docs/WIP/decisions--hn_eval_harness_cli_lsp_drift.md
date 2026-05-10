---
title: eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단
domain: harness
problem: P6
solution-ref:
  - S6 — "SKILL.md·rules 변경 커밋에 ... 실행 기록이 있음 (부분)"
  - S6 — "WIP AC 완료 후 CPS Solution 항목 갱신 여부가 명시적으로 확인됨"
tags: [eval, cli, lsp, drift, typecheck, downstream]
relates-to:
  - path: decisions/hn_eval_cps_integrity.md
    rel: extends
status: in-progress
created: 2026-05-10
updated: 2026-05-10
---

# eval --harness CLI 백엔드 + LSP/검증 도구 정렬 진단

## 사전 준비
- 읽을 문서:
  - `.claude/skills/eval/SKILL.md` (현 --harness 점검 항목 1~7)
  - `.claude/scripts/eval_cps_integrity.py` (기존 CLI 백엔드 패턴 — importlib 동적 import)
  - `.claude/scripts/pre_commit_check.py` (frontmatter·신호 검출 헬퍼 재사용)
  - `.claude/rules/staging.md`, `.claude/rules/self-verify.md` (검증 도구 정렬과 SKIP 정책 경계)
  - 다운스트림 보고서 본문 (StageLink LSP stale dist drift — 본 대화 컨텍스트)
- 이전 산출물: `hn_eval_cps_integrity.md` (CPS 무결성 점검 항목 5·6·7 도입 전례)
- MAP 참조: HARNESS_MAP.md `## CPS` P6 served-by 컬럼(eval), Skills 행 eval

## 목표

**일반 명제 (본 작업의 핵심)**:
> 검증 도구(LSP·lint·tsc·test runner)가 산출물(dist/build/생성된 .d.ts)이
> 아닌 **소스를 직접 보도록** 보장한다. 검증 도구가 산출물을 보면 silent
> drift가 발생해 LLM이 stale 타입을 추측 근거로 사용(P1) + 회귀가 검증망
> 통과(P6) + LSP 미반영을 운용 비용으로 흡수(P5).

**두 축 동시 진행**:

1. **eval --harness CLI 백엔드 신설** — 현재 SKILL.md 절차를 LLM이 매번
   해석하는 구조의 결정성·재현성 부족 해소. 결정적 측정 항목을 스크립트로
   이전. (사용자 메시지: "CLAUDE.md에 있는데도 무시하는 경우 많음" — 텍스트
   규칙 의존 한계 보강)

   **기존 점검 항목과의 관계 (사용자 인라인 질문 답변)**:
   - **유지 + 통합 + 추가**. 이전 작업을 대체하지 않음.
   - 기존 항목 1~7은 그대로 동작:
     - 항목 1 모호성 / 2 모순 / 3 부패 / 4 강제력 배치 → **LLM 해석 영역**
       으로 SKILL.md에 본문 절차 유지 (결정적 측정 불가 — Claude가 텍스트
       의미 판단 필요)
     - 항목 5 CPS 무결성 / 6 방어 활성 / 7 피드백 리포트 → 이미 부분적으로
       `eval_cps_integrity.py`가 처리 중. **본 wave가 이를 `eval_harness.py`
       단일 진입점으로 통합** (eval_cps_integrity.py는 호출 대상으로 유지,
       deprecated 표시 X)
   - 신설 항목:
     - 항목 8 검증 도구 정렬(LSP/lint/tsc 산출물 vs src) → **본 wave 신규**.
       결정적 영역이라 CLI 백엔드에서 직접 수행
   - 즉 사용자 호출 흐름:
     ```
     /eval --harness
       → SKILL.md 본문 (LLM 해석: 항목 1~4)
       → python3 eval_harness.py (CLI: 항목 5~8)
         → eval_cps_integrity.py 호출 (5·6·7)
         → 신규 LSP 정렬 검출 (8)
     ```

2. **LSP/검증 도구 정렬 진단 항목 추가** — 일반 명제 검증을 eval --harness
   주기 검진 채널에 통합. 진행된 프로젝트의 부분 적용·drift 누적·의도적
   비정렬 보존까지 측정.

**CPS 연결**:
- P6 (검증망 스킵): eval --harness가 LLM 해석 의존 → 결정성 부족 → 검증망
  스킵 위험. CLI 백엔드화로 결정적 검증 채널 강화.
- P1 (LLM 추측 수정): silent drift된 stale 타입을 LLM이 사실로 받아 추측
  근거 사용. 본 진단이 drift 자체를 박제.
- P5 (컨텍스트 팽창): 가장 많이 사용되는 모드의 LLM 해석 비용 = 매 호출
  컨텍스트 가산. CLI 백엔드화가 직접 완화.

본 wave는 P6 주축. P1·P5는 부수 효과로 본문 언급.

## 작업 목록

### Phase 1. eval_harness.py CLI 백엔드 신설

**사전 준비**:
- `eval_cps_integrity.py` 패턴 답습 (importlib spec_from_file_location로
  pre_commit_check 동적 import → 헬퍼 재사용)
- 출력 채널 분리: stdout=구조화 보고(SKILL.md가 파싱), stderr=사람용 경고

**영향 파일**:
- `.claude/scripts/eval_harness.py` (신규)
- `.claude/skills/eval/SKILL.md` (--harness 실행 섹션 — CLI 호출로 전환)

**Acceptance Criteria**:
- [ ] Goal: SKILL.md의 결정적 측정 가능 항목이 eval_harness.py CLI에서
      실행되고, SKILL.md는 CLI 호출 + LLM 해석 영역(서술형 진단)만 담당
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: python3 .claude/scripts/eval_harness.py 실행 후 종료 코드 0 + 구조화 출력 확인
- [ ] 출력 포맷: SKILL.md의 기존 보고 형식(모호성·모순·부패·강제력·CPS
      무결성·방어 활성·피드백 리포트 + 본 wave 신규 항목)과 정합
- [ ] 기존 `eval_cps_integrity.py`는 유지 (deprecated 표시 X — 점검 항목
      5·6은 그쪽 위임). eval_harness.py는 그것을 호출 + 본 wave 신규 항목만
      직접 수행
- [ ] importlib 동적 import로 pre_commit_check 헬퍼 재사용 (코드 중복 0)
- [ ] Windows + Git Bash 환경에서 utf-8 인코딩 안전 (cp949 디코딩 회피 —
      pre_commit_check.run() 패턴 답습)

### Phase 2. LSP/검증 도구 정렬 진단 — 신호 검출

**사전 준비**:
- 본질 명제: "검증 도구는 src를 봐야 한다"
- 신호 정의 (다운스트림 보고서 + 사용자 정리):
  - **A**: 워크스페이스 모노레포 (루트 `package.json`에 `workspaces` 필드)
  - **B**: 자동 생성 타입 의존 (`@supabase/supabase-js`·`@prisma/client`·
    `@graphql-codegen/*` 의존성 발견 또는 `prisma/schema.prisma` 등 스키마
    파일 존재)
  - **C**: 패키지 빌드 후 자체 소비 (워크스페이스 패키지 `package.json`의
    `exports`가 `./dist/*` 가리키고 동일 모노레포 내 다른 패키지에서 import)
  - **D**: 컴파일러 실행 디렉토리 분리 (`tsconfig.json`의 `outDir`가
    `rootDir` 밖)

**영향 파일**:
- `.claude/scripts/eval_harness.py` (신호 검출 함수 추가)

**Acceptance Criteria**:
- [ ] Goal: 4개 신호(A/B/C/D)를 패키지별로 검출하고, 결과를 `signals` 객체로
      구조화 출력
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_eval_harness.py::test_signal_detection -q
    실측: 본 starter(TypeScript 없음) 실행 시 모든 신호 0건 보고 + 위계
      획정용 픽스처 케이스에서 각 신호 hit 개별 검출
- [ ] TypeScript 미사용 프로젝트(본 starter 포함)에서 신호 0건 → 정렬 진단
      자체 SKIP. npm·node 호출 없음 (Python·Go·Rust 다운스트림 차단 회피)
- [ ] 검출 로직은 파일 시스템 + JSON 파싱만 사용. 외부 명령(npm·tsc) 호출
      금지 — eval은 보고 채널이지 빌드 도구가 아님
- [ ] 부분 적용 식별: 모노레포에서 패키지별로 신호 상태 다르면 그대로 보고
      (요약하지 않음). "5개 중 3개 src 정렬, 2개 dist 정렬" 형식

### Phase 3. LSP/검증 도구 정렬 진단 — 정렬 적용률 + drift 측정

**사전 준비**:
- 본 Phase는 신호 hit한 프로젝트에서만 동작 (Phase 2의 신호 검출 결과를
  입력으로 받음)
- 측정 대상: tsconfig paths가 src를 가리키는지, eslint resolver 설정,
  `package.json` `exports` 형식

**영향 파일**:
- `.claude/scripts/eval_harness.py` (정렬률 측정 함수)

**Acceptance Criteria**:
- [ ] Goal: 신호 hit한 프로젝트의 검증 도구 정렬 상태를 도구별·패키지별로
      측정해 보고
  검증:
    review: review-deep
    tests: pytest .claude/scripts/tests/test_eval_harness.py::test_alignment_metrics -q
    실측: 픽스처(정렬됨/미정렬/부분정렬 3종) 입력 시 정확히 3가지 분류로
      출력
- [ ] 측정 항목 (도구별):
      - tsconfig paths: src 직접 매핑 / dist 매핑 / 매핑 없음
      - package.json exports: src 노출 / dist 노출 / 양쪽 / 미노출
      - eslint resolver (있을 때): src / dist / 미설정
- [ ] codegen freshness (신호 B hit 시): 스키마 파일 mtime vs 산출물 mtime
      비교. 산출물이 더 오래되면 stale로 보고
- [ ] 의도적 비정렬 보존: `.claude/harness-overrides.md` 파일에 등록된
      패키지·도구는 "의도적 비정렬 ✅"로 보고 (경고 X). 미등록 비정렬만 경고
- [ ] 차단 아님: 모든 출력은 보고. exit code는 신호·정렬 상태와 무관하게 0
      (eval은 진단 채널)

### Phase 4. SKILL.md 통합 + 보고 형식

**사전 준비**:
- 기존 SKILL.md `--harness` 점검 항목 1~7과 본 wave 신규 항목의 위치 결정
- 사용자 메시지 반영: "CLAUDE.md에 있는데도 무시하는 경우 많음" → 진단
  항목 본문이 "스크립트 출력 기반"임을 명시. LLM 해석 의존 항목과 구별
  표시.

**영향 파일**:
- `.claude/skills/eval/SKILL.md`
- `.claude/HARNESS_MAP.md` (Skills 행 갱신, Scripts 섹션에 eval_harness.py 추가)

**Acceptance Criteria**:
- [ ] Goal: SKILL.md `--harness` 섹션이 CLI 호출 + 결과 해석으로 재구성됨.
      신규 항목 8(검증 도구 정렬) 추가
  검증:
    review: review
    tests: 없음 (문서 변경)
    실측: SKILL.md를 따라 `python3 .claude/scripts/eval_harness.py` 실행 →
      8개 항목 보고 출력 직접 확인
- [ ] 점검 항목 구조 재편: CLI 백엔드(결정적) vs LLM 해석(서술형) 명시 구분
      - 결정적: CPS 무결성·방어 활성·피드백 리포트·검증 도구 정렬
      - LLM 해석: 모호성·모순·부패·강제력 배치 (이건 SKILL.md 본문에 절차)
- [ ] HARNESS_MAP Scripts 섹션에 eval_harness.py 행 추가 (enforced-by-inverse:
      eval --harness, serves: S6)
- [ ] 다운스트림 신규 abbr·도메인 영향 없음 (본 wave는 starter 메커니즘만)

### Phase 5. MIGRATIONS.md + 회귀 가드

**사전 준비**:
- 본 wave는 신규 스크립트 + SKILL.md 절차 변경 → patch 범프 대상 (S6 4번
  방어 레이어)
- 다운스트림 영향: eval --harness 출력 항목 증가. 자동 적용 (스크립트 호출
  변경) — 다운스트림 수동 액션 없음

**영향 파일**:
- `docs/harness/MIGRATIONS.md`
- `.claude/scripts/tests/test_eval_harness.py` (신규)

**Acceptance Criteria**:
- [ ] Goal: MIGRATIONS.md에 본 버전 섹션 추가 + 회귀 가드 테스트 통과 ✅
  검증:
    review: review
    tests: pytest .claude/scripts/tests/test_eval_harness.py -q
    실측: harness-upgrade 시나리오에서 다운스트림 추가 액션 0건 확인
      (자동 적용 — 스크립트 호출 갱신만)
- [ ] MIGRATIONS.md 회귀 위험 섹션: 단정 표현 금지(no-speculation.md). 측정 ✅
      범위 + 미테스트 영역 명시
- [ ] 테스트 marker 등록 (test_pre_commit.py marker와 별도 — `eval` marker
      신설 또는 기존 활용). conftest.py 갱신 필요 시 동반
- [ ] starter에서 `python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q`
      통과 (모든 marker)

## 결정 사항

(작업하면서 채움)

## 메모

- **실행 순서**: 2번째 (후행). 선행 조건: `decisions--hn_self_invocation_failure.md`
  완료 후. 별 wave가 P8 등록을 처리하므로 본 wave의 `## 발견된 스코프 외 이슈`
  의 BIT NEW 플래그는 별 wave에서 흡수됨.

- **doc-finder fast scan**: hit 20개. 핵심은 `decisions/hn_eval_cps_integrity.md`
  (eval CLI 백엔드 패턴 전례 — `eval_cps_integrity.py`). 본 wave는 이 패턴을
  답습하면서 LSP 정렬 영역으로 확장.
- **CPS 매칭 근거**: P6 주축 (검증망 스킵 — eval --harness LLM 해석 의존이
  결정성 부족 신호). P1·P5는 부수 효과.
- **Solution 인용**: S6 4번·6번 충족 기준. 본 wave가 직접 충족. 새 충족
  기준 추가 X (Solution 변경은 owner 승인 필요).
- **본질 명제 박제**: "검증 도구는 src, 런타임은 dist 분리". 다운스트림
  보고서 폐기 시도 섹션의 자산 가치(`customConditions` Next.js 미지원 등)
  를 본 wave에서 활용하되, 보고서를 그대로 채택하지 않음. 일반 명제로
  격상 + 진행된 프로젝트 대응 5단계(진단·점진정렬·의사결정·지속검증·복구)
  구조 적용.
- **사용자 우려 보강**: "CLAUDE.md에 있는데도 무시하는 경우 많음" — 본 wave의
  핵심 가설(스크립트 결정성 > 텍스트 규칙)을 사용자가 직접 확인. AC 모든
  항목을 스크립트 출력 기반으로 작성. 텍스트 규칙 의존 항목 제거.

## 발견된 스코프 외 이슈

- 다운스트림에서 문서 작성 시 write-doc 스킬 우회 패턴 종종 발생 |
  발견: 본 wave Step 0 사용자 메시지 |
  P#: P6 (부분) — 검증망 스킵의 일종이지만, 스킬 발화 강제 메커니즘은 본
  wave 스코프 외. **별 wave 신설 후보**. BIT Q3=YES (조용한 실패 + 다운
  스트림 전파 — 자동 발견 어려움). 다음 implementation Step 0에서 신규
  P# 등록 vs P6 본문 확장 판단.

- BIT(bug-interrupt 규칙) 자가 발화 의존 메커니즘 실패 — 다운스트림에서
  발화 0건 |
  발견: 본 wave Step 2 사용자 메시지 + debug-specialist 진단 (2026-05-10) |
  P#: NEW — "자가 발화 의존 규칙의 일반 실패" — 새 P 후보. 기존 P1(추측
  수정)·P6(검증망 스킵)·P7(관계 불투명) 어느 것에도 정확 매칭 안 됨.
  메커니즘 자체의 결함(강제 트리거 부재 → 자가 발화 의존 → Claude가 안
  떠올리면 적용 0).
  
  **실측 증거**: LSP stale dist 결함이 다운스트림에서 Q3=YES 명백한 케이스
  (조용한 실패 + 다운스트림 전파 + 자동 발견 어려움)인데 BIT 한 번도 발화
  안 함. "에러가 무지하게 나고 있는" 상태에서도 트리거 0. 자가 발화 의존
  메커니즘 실패의 결정적 증거.
  
  **debug-specialist 진단 (원문 보존)**:
  - bug-interrupt.md 다운스트림 정상 배포됨 (h-setup.sh rules/ 전체 복사).
    전파 문제 아님.
  - enforced-by=review (커밋 사후 감지만). 작업 중 강제 hook 0건.
  - session-start.py는 이미 기록된 `## 발견된 스코프 외 이슈` 섹션 알림만,
    발견 유도 X.
  - P1 defends 다른 규칙(no-speculation·internal-first)은 debug-guard.sh
    UserPromptSubmit hook 강제력 있는데 BIT만 강제력 0.
  - 업스트림 가시성 착시: starter는 메타 작업이라 사용자·Claude가 BIT
    키워드 자주 입에 올림. 다운스트림은 앱 코드 작업이라 떠올릴 단서 부재.
  
  **수정 방향 후보 (사용자 결정 필요)**:
  1. PreToolUse hook 추가 — scope 정의 어려움
  2. debug-guard.sh 확장 — "버그·이상·왜 안 돼·이거 깨졌네·에러" 키워드 감지
     시 BIT Q1/Q2/Q3 블록 출력 강제. **가장 가벼운 개입.**
  3. session-start.py 사전 환기
  4. implementation SKILL Step 2/3 자가 점검 강제
  
  **별 wave 신설 후보** (본 wave 스코프 외). 다음 implementation Step 0에서
  신규 P# 등록 처리. write-doc 우회 + CLAUDE.md 무시 + BIT 미발화는 모두
  **자가 발화/자가 준수 의존 규칙의 일반 실패** 패턴 — 한 P로 묶을 가능성
  검토.

## 폐기 결정 (다운스트림 보고서 vs 본 wave)

다운스트림 보고서의 4개 업스트림 요청 중 채택 강도:

| 보고서 요청 | 본 wave 처리 |
|---|---|
| `rules/typecheck.md` 신설 | ❌ 거부. 일반 명제는 룰 신설 대신 eval 진단 항목으로 흡수. 룰은 원칙이어야 하는데 보고서 안은 npm 명령 디테일이라 stack-agnostic 원칙 충돌. |
| `pre_commit_check.py`에 npm type-check 호출 | ❌ 거부. pre-check은 차단 게이트 + Python·git만 의존. npm 호출 = 의존성 표면 확장 + Python/Go/Rust 다운스트림 ENOENT. eval(보고 채널)이 적합. |
| harness-init/adopt 자동 주입 | ⚠️ 약화. 본 wave 스코프 외 (별 wave 후보). 자동 주입은 silent override 위험(P3). 신호 검출 후 사용자 승인 패턴 필요. |
| MIGRATIONS.md 안내 | ✅ 채택. Phase 5에서 처리. |

채택 우선순위: **결함 진단 + 함정 공유(폐기 시도) + 참조 구현은 자산**.
강제 메커니즘 부분만 톤다운해서 eval 진단 채널로 흡수.
