---
title: Rules 파일 다이어트 — 분리한 메타·배경·자동 감지 상세
domain: harness
tags: [rules, governance, refactor]
problem: P5
s: [S5]
status: completed
created: 2026-04-20
---

# Rules 메타·배경 모음

`.claude/rules/*.md`에서 분리한 **배경·자동 감지 상세·사고 참고**를 모은
문서. LLM이 매 세션마다 시스템 프롬프트로 읽지 않아도 되는 메타 정보.

분리 사유: rules 합계 30KB → 매 세션 컨텍스트 압박. 배경·메타·1회성
사고 참고는 회고·재설계 시점에만 필요.

## no-speculation.md

### 배경

CLAUDE.md "추측 금지"가 있어도 매번 "이것일 거"라고 예측하고 수정 진행.
sonnet 사용 시 이 확률이 크게 증가한다고 사용자가 명시적으로 지적.

텍스트 규칙만으로는 LLM 행동이 바뀌지 않는다. 자동 감지·차단 장치가
없으면 위반에 비용이 없어서 패턴이 반복된다. 이 규칙은 **review 에이전트가
감지**한다.

### 자동 감지 (review 에이전트)

review가 다음 패턴 검증:

1. **추측 단어 + 근거 없음** — 커밋·WIP·주석에 "아마", "일 것 같은",
   "예상", "추정", "probably", "might be" 옆에 근거(파일·라인·로그) 없음 → 경고
2. **문제 설명 없는 수정** — diff가 "무엇이 깨졌는지" 설명 없이 바로 수정,
   커밋 메시지에 해결 문제 기술 없음 → 경고
3. **검증 없는 "완료" 선언** — 변경 후 빌드·테스트·실행 흔적 없이 "fix"
   커밋 → 경고

### 모델 영향

추측이 반복되는 영역은 **모델 격상** 고려 (sonnet → opus).
commit_perf_optimization의 모델 스위치에서 "추측 hit이 있던 영역은 격상"
로직 검토.

## internal-first.md

### 배경

가장 파괴적인 실수 패턴: **외부 자료(Context7·웹 검색)는 잘 뒤지면서,
내부에 이미 있는 작동 사례·결정·실패 기록은 무시하고 새로 설계.**

git history에 작동했던 코드가 있는데 새로 만들고, 같은 incident가 있는데
같은 가설을 다시 시험한다. 내부에 답이 있는데 외부에서 찾는다.

### 자동 감지 트리거

implementation Step 0, commit Step 6(리뷰 직전):

- WIP·작업 로그·리뷰 prompt에 "공식 문서", "Context7", "SDK 문서",
  "웹 검색" 언급이 있는데 같은 맥락에서 "git log", "docs/decisions",
  "docs/incidents" 참조가 **없으면** 경고
- 경고 수준. 차단 아님 — 사용자가 "외부만 봐도 충분"이라 판단 가능

## security.md

### 방어 레이어 4단

#### 레이어 1: pre-commit hook (로컬)

gitleaks 또는 grep 기반 스캔을 pre-commit에 등록.
설치: `bash scripts/install-secret-scan-hook.sh`.
staged 파일에서 시크릿 패턴 발견 시 커밋 차단.

#### 레이어 2: CI 스캔

PR 단계에서 `gitleaks detect --log-opts="-log <base>..<head>"` 실행.
노출 의심 건은 머지 차단.

#### 레이어 3: eval --deep

주기적 `/eval --deep`. Step 0 시크릿 스캔으로 working tree + git
history 전체 스캔. 이미 들어간 시크릿 확인.

#### 레이어 4: 즉시 rotation 플레이북

시크릿이 git history에 한 번이라도 커밋되었다면:

1. **해당 키를 즉시 발급 기관에서 rotation** (Supabase 대시보드, AWS IAM,
   Stripe 대시보드). "history만 지우면 된다" 착각 금지.
2. git history 재작성: BFG Repo-Cleaner 또는 `git filter-repo`로 해당
   파일/패턴 제거 후 force push.
3. 팀 전체 re-clone 지시 (로컬 reflog에 남아있을 수 있음).
4. `docs/incidents/`에 인시던트 문서 작성.

### 2026-04-18 사고 참고

`tools/dev-tools/` 4개 파일 + `tools/setup/` 2개 파일에 service_role 키와
admin 비밀번호 평문 하드코딩, git history 영구 노출. eval --deep가 폴더를
"archive 후보"로만 분류하고 내부를 검사하지 않아 검출 실패. security.md는
이 사고 후 신설됨.

## pipeline-design.md

### 배경

다운스트림 프로젝트에서 detection pipeline 재편 중 상류 단계가 계산한
풍부한 중간 신호를 한 번의 결정에만 쓰고 **출력 구조에서 폐기** → 하류
단계들이 같은 축의 판단을 **열등한 정보로 재계산**하는 구조가 한 달간
draft1→2→3 재편에도 발견되지 않음.

이 실수는 ML 파이프라인뿐 아니라 ETL·빌드·에이전트 체인 등 다단 처리
전반에 적용되므로 업스트림 규칙으로 승격.

상세 사료: `docs/incidents/hn_pipeline_design_rule_origin.md`.

### 자동 감지 — 채택 안 함 (review 비도입)

review 에이전트의 자동 감지 패턴 추가를 **채택하지 않음** (2026-04-21).

이유:
- 의도 설계 문제는 diff 키워드 매칭으로 잡기 어려워 오탐 다수
- rule 체크리스트(7항목)가 이미 "강제 도구" 역할 수행
- v0.17.0·0.17.1 review 재조정 방향(과잉 호출 축소)과 정합

대신:
- **rule 체크리스트 강제** — pipeline-design.md "설계 리뷰 체크리스트
  7항목" 누락 시 self-verify가 "완료 보고 금지" 적용
- **사용자 질문 트리거** — 같은 판단이 여러 단계에서 반복되는 패턴
  발견 시 즉시 rule 참조
- **self-verify 연계** — 파이프라인 단계 설계·재편 작업에서 체크리스트
  검토를 자가 검증 단계에 포함

### 7항목 체크리스트

1. 입력 — 상류에서 받는 신호 목록
2. 중간 계산 — 이 단계에서 새로 계산하는 것
3. 출력 — 하류로 넘기는 신호 목록
4. 폐기 — 의도적으로 버리는 것 + 근거
5. 보존 책임 — 하류가 재계산할 축을 유지하는지
6. 전제 — "X 없이 작동한다"의 X 목록과 검증
7. 검증 케이스 — 여러 입력 케이스에서 성립 확인

### 모델 영향

파이프라인 단계 설계·재편 시:
1. CLAUDE.md `<important if>` 블록 트리거로 rule 참조
2. 7항목 체크리스트 명시 (설계 문서 또는 계획 WIP에)
3. 완료 전 self-verify가 누락 검사
4. 누락 시 "완료" 보고 금지
