---
name: eval
description: 놓치고 있는 것을 찾는다. 기본은 코드 간극 분석. --quick은 30초 헬스체크. --harness는 하네스 문서 품질 평가. --surface는 암묵지 발견. --deep을 붙이면 시크릿 스캔 + archive 폴더 강제 점검 + 4관점 병렬 에이전트(파괴자/트렌드/비용/외부공격자) 검증. 주기적으로 돌리는 건강 검진.
---

# /eval 스킬

"놓치고 있는 것이 무엇인가?"를 찾는다.

## 스코프 경계 (중요)

- **eval** = 프로젝트 전체 / 누적 / 과거 git history까지. 변경 없이도 돈다.
- **review** = 이번 diff만. 커밋 직전에 commit 스킬이 자동 호출.

"이 커밋 괜찮아?"는 review, "프로젝트 전체에서 놓치고 있는 건?"은 eval.
같은 질문을 중복해서 다루지 않는다. 아래 표로 경계를 구분한다.

| 질문 | review | eval |
|------|--------|------|
| 계획 vs 구현 일치 | 이번 커밋 | 누적 드리프트 |
| 하네스 규칙 준수 | diff가 규칙 위반인지 | 규칙 자체가 모호/모순/부패인지 (`--harness`) |
| 중복 코드 탐지 | 판단 불가 (diff만으로 안 됨) | `--deep` 비용/과잉 관점 |
| 시크릿 스캔 | staged diff (pre-commit hook) | working tree + git history (`--deep` Step 0) |

---

4가지 모드 + 1개 플래그가 있다.

| 사용법 | 설명 |
|--------|------|
| `/eval --quick` | 30초 헬스체크 (가장 빠름) |
| `/eval` | 코드 간극 분석 (기본) |
| `/eval --harness` | 하네스 문서 품질 평가 |
| `/eval --surface` | 암묵지 발견 |
| `/eval --deep` | 기본 + 시크릿 스캔 + 4관점 병렬 에이전트 검증 |
| `/eval --harness --deep` | 하네스 품질 + 4관점 병렬 에이전트 검증 |

`--deep`은 기본과 `--harness`에만 붙일 수 있다. `--surface`는 대화형이라 해당 없음.
`--quick`은 독립 모드. 다른 플래그와 조합하지 않는다.

---

## /eval --quick (30초 헬스체크)

깊은 분석 없이, 프로젝트의 현재 건강 상태를 빠르게 확인한다.

### 왜 필요한가

기본 eval은 CPS 대조까지 하므로 무겁다. 작업 중간에 "지금 괜찮은가?"를 빠르게 확인하고 싶을 때 사용한다.

### 점검 항목 (순서대로, 30초 이내)

1. **린터 에러 수** — 빌드/린트 명령 실행, 에러 카운트
2. **미완료 WIP 문서 수** — docs/WIP/에서 pending/in-progress 파일 수
3. **TODO/FIXME/HACK 수** — src/ 하위 코드에서 카운트
4. **마지막 커밋 경과 시간** — `git log -1 --format="%ar"`
5. **미커밋 변경 파일 수** — `git status --porcelain | wc -l`

### 보고 형식

```
## /eval --quick

✅ 린터: 에러 0
📋 WIP: 2개 (1 in-progress, 1 pending)
⚠️ TODO/FIXME: 3개
🕐 마지막 커밋: 2시간 전
📦 미커밋 변경: 5개 파일
```

문제없으면 한 줄: "헬스체크 통과. ✅"

---

## /eval (기본: 코드 간극 분석)

"지금 잘 되고 있는가?"가 아니라, **"최종 형태에서 놓치고 있는 것이 무엇인가?"**를 찾는다.

### 왜 필요한가

개별 커밋은 전부 합리적이다. 리뷰도 통과했다.
하지만 50개 쌓이면, 원래 가려던 곳에서 벗어나 있다.
다른 Agent는 현재 시점만 본다. eval만 앞을 본다.

### 절차

**1. 최종 형태 확인** — docs/guides/의 CPS 문서를 연다. 원래 Problem, Solution, 아키텍처 결정. 이것이 "목적지".

**2. 현재 상태 파악** — 실제 코드와 docs/를 본다. 구현된 기능, 폴더 구조, 진행 중 작업(docs/WIP/). 이것이 "현재 위치".

**3. 간극 분석** — 목적지와 현재 위치를 대조해서 네 가지를 찾는다.

| 간극 | 의미 | 질문 |
|------|------|------|
| 빠진 것 | CPS에 있지만 구현에 없음 | 의식적 보류인가, 무의식적 누락인가? |
| 줄어든 것 | 구현했지만 원래 범위보다 좁음 | 어떤 결정 때문에 줄었는가? |
| 틀어진 것 | 원래 방향과 다르게 구현됨 | 의식적 변경인가, 점진적 드리프트인가? |
| 늘어난 것 | CPS에 없는데 구현에 있음 | 정말 필요한가, 스코프 크리프인가? |

**4. 분류** — 발견된 간극을 세 층으로 분류한다.

| 층 | 정의 | 판단 기준 |
|----|------|----------|
| 거시 | CPS 방향 이탈 또는 WIP 집중도에 영향 | 이탈 없으면 "방향 유지 ✅" 한 줄 |
| 단기 블로커 | 해결 안 하면 다음 작업이 불가한 것 | 선행 조건이 막혀 있으면 블로커 |
| 장기 부채 | 지금 당장은 아니지만 방치 시 위험한 것 | 누적되면 비용 증가 |

분류 후 **단기 블로커별 다음 행동을 1줄로 작성**한다 (어떤 스킬/에이전트로 시작하는가).

**5. 보고** — 대화 출력은 간결하게 유지한다.

```
## /eval

**거시**: {방향 유지 ✅ 또는 이탈 내용}

**단기 블로커 {N}개**:
1. {항목} → {스킬/에이전트} ({예상 소요})
2. ...

**장기 부채 {N}건** — 상세는 memory `project_eval_last.md` 참조.
```

간극 없으면: "간극 없음. ✅" 한 줄. 장기 부채만 있으면 단기 블로커 섹션 생략.

**6. 저장** — eval 완료 시 항상 실행한다 (결과 0건이어도).

`.claude/memory/project_eval_last.md`에 **전체 상세를 덮어쓰기**로 저장한다. 누적하지 않는다.

```yaml
---
name: eval-last-result
description: 마지막 /eval 실행 결과 (덮어쓰기, 누적 아님)
type: project
---
실행: {YYYY-MM-DD}

## 거시
{내용}

## 단기 블로커
{목록 또는 "없음"}

## 장기 부채
{목록 또는 "없음"}

## 다음 행동
{블로커별 1줄}
```

저장 후 `MEMORY.md` 인덱스를 갱신한다:
- 기존 eval-last 항목이 있으면 날짜만 교체
- 없으면 한 줄 추가: `- [마지막 eval 결과](project_eval_last.md) — {YYYY-MM-DD} 실행`

### 핵심 질문

> "지금 이 상태로 완성하면, 원래 풀려던 Problem이 전부 해결되는가?"

---

## /eval --harness (하네스 문서 품질 평가)

하네스 문서 자체가 **모호하거나 모순되거나 부패한** 부분을 찾는다.

### 왜 필요한가

규칙이 있어도 AI가 이상하게 행동하면, 규칙 자체가 문제일 수 있다.
"적절하게 처리하라" 같은 모호한 표현은 규칙이 아니라 소원이다.
문서 간 모순이 있으면 AI는 둘 중 하나를 무시한다.

### 점검 대상

CLAUDE.md, .claude/rules/ 전체, .claude/skills/ 전체를 읽는다.

### 점검 항목

**1. 모호성** — AI가 해석을 달리할 수 있는 표현을 찾는다.

위험 신호:
- "적절한", "필요하면", "가능하면", "상황에 따라"
- 수치 없는 기준 ("짧게", "간결하게", "너무 길지 않게")
- "등", "기타", "필요 시" 로 끝나는 목록

발견 시: 구체적 대안을 제시한다. "짧게" → "500줄 이하" 또는 "한 함수 30줄 이하".

**2. 모순** — 문서 간 충돌하는 지시를 찾는다.

점검 방법:
- CLAUDE.md와 rules/ 사이에 같은 주제를 다른 기준으로 다루는 곳
- rules/ 간에 상충하는 규칙
- skills/ 내 절차가 rules/의 규칙과 맞지 않는 곳

발견 시: 어느 쪽이 맞는지 사용자에게 질문한다. 임의로 해결하지 마라.

**3. 부패** — 현재 프로젝트 상태와 맞지 않는 규칙을 찾는다.

점검 방법:
- 존재하지 않는 파일/폴더를 참조하는 규칙
- 이미 린터가 잡고 있는데 rules/에도 남아있는 중복
- 강등 대상인데 아직 강등 안 된 규칙 (최근 3개월간 실제로 문제를 막은 적 없는 것)

**4. 강제력 배치 오류** — 방어 레이어에 잘못 놓인 규칙을 찾는다.

원칙: 린터가 잡을 수 있는 건 린터에 있어야 한다.
- rules/에 있지만 린터로 강제할 수 있는 것 → 승격 제안
- CLAUDE.md에 있지만 rules/에 있어야 하는 것 → 이동 제안

**5. CPS 무결성** — CPS = 마스터, 다른 모든 문서는 단방향 인용. 인용 박제·
Problem 인플레이션을 전수 감시한다. pre-check은 commit 시점 staged만 검증
하므로 누적 박제는 eval만 잡는다.

#### 실행

```bash
python3 .claude/scripts/eval_cps_integrity.py
```

스크립트가 `pre_commit_check.py`의 `verify_solution_ref`·`get_cps_text`·
`parse_frontmatter`를 import 재사용한다 (코드 중복 X). docs/ 하위 모든
.md 파일의 frontmatter `solution-ref` 인용을 CPS 본문과 grep:

- 50자 이내 인용 → 원문 그대로 매칭 필요
- 50자 초과 인용 → `(부분)` 마커 + substring 매칭
- 미매칭 시 박제 의심 보고 (path:warning)

CPS Problem 6개 초과 시 인플레이션 경고 — 근접 Problem 병합 검토.

#### 결과 해석

- **관계 그래프 점검 단절 N건**: HARNESS_MAP.md에 등재됐으나 실제 파일 없거나, 실제 파일이 MAP에 미등재. 신규 구성요소 추가 시 MAP 갱신 누락 신호. MAP을 직접 수정하거나 파일 삭제 확인.
- **박제 의심 0건**: CPS 본문이 진화한 만큼 인용도 정합. 통과
- **박제 의심 N건**: 작성자가 인용 후 CPS 본문이 의도적으로 진화했거나,
  반대로 인용이 박제(본문이 바뀐 줄 모르고 옛 표현 유지). path:line 제시
  → 작성자 판단 (본문 갱신 vs 인용 수정)
- **Problem 인플레이션**: 6개 초과면 의미 거리 가까운 Problem 병합 후보
  검토. write-doc으로 CPS 갱신
- **Solution 충족 인용 분포**: 인용 카운트가 높을수록 그 Solution이 활발히
  문서화된 것. **0건 = 즉 실패가 아니다** — 최근 등록됐거나 아직 구현 전이거나
  문서화가 지연된 것일 수 있다. 다음 기준으로 사람이 판단:
  - 0건 + 등록 3개월 이상 → Solution 정의 재검토 또는 대응 WIP 신설 검토
  - 0건 + 최근 등록 → 정상. 넘어간다
  - 특정 Solution에 집중(80% 이상) → 나머지 Solution 방치 신호. 균형 검토

### 보고

```
## /eval --harness 결과

### 모호성
- coding.md: "함수는 짧게 작성하라" → 기준 없음. "30줄 이하" 같은 수치 제안.

### 모순
- 없음 ✅

### 부패
- naming.md: docs/plans/ 참조하지만 실제 폴더는 docs/WIP/

### 강제력 배치
- rules/coding.md: "console.log 금지" → 린터(no-console)로 승격 가능

### CPS 무결성
- 스캔 문서: 80개
- Problem 수: 6개 ✅ (임계 6 이하)
- 박제 의심: 0건 ✅
- Problem 인용 빈도: P2=2건, P5=4건
- 인용 0건 Problem: P1, P3, P4, P6 ⚠ (정체 의심 — 6개월 이상이면 폐기·병합 검토)
- Solution 충족 인용 분포: S1=0건 ⚠, S2=5건, S3=1건, S4=0건 ⚠, S5=14건, S6=1건
  (0건 Solution: S1, S4 — 맥락 확인 필요. 사람 판단)
- NEW 플래그 미처리: 0건 ✅
```

NEW 플래그 집계: docs/WIP/·docs/decisions/ 파일에서 `P#:.*NEW` 패턴을
grep해 미처리 스코프 외 이슈 수를 집계한다. 1건 이상이면:

```
- NEW 플래그 미처리: N건 ⚠
  - [파일명]: "[버그 설명]" (발견: Step/파일)
  → implementation Step 0에서 CPS P# 매칭 필요
```

0건이면 `NEW 플래그 미처리: 0건 ✅` 한 줄만.

#### doc-health 안내

CPS 무결성 스캔 결과에서 다음 중 하나라도 해당하면 doc-health 실행을 권장한다:

- abbr 없는 파일이 5개 이상
- CPS frontmatter(`problem`/`solution-ref`) 없는 파일이 10개 이상
- 박제 의심 3건 이상

해당 시 보고 마지막에 추가:

```
⚠️ 레거시 문서 정비 권장: `/doc-health` 실행으로 abbr rename·CPS frontmatter
   추가를 반자동화할 수 있습니다. (진단 결과를 그대로 이어받아 시작)
```

문제없으면 "하네스 정상. ✅"

#### --deep 활용 (Problem 진전 측정)

`eval --deep`은 위 출력의 "Problem 인용 빈도"를 시계열로 비교한다 (이전
실행과의 delta). 본 starter는 단일 시점만 보여주지만, 운용에서는 다음
지표 추적:

- 인용 빈도 증가 = Problem이 활발히 다뤄지는 중 (정상)
- 빈도 변화 없음 + 6개월 경과 = 정체 신호 → Problem 정의 재검토
- 인용 0건 Problem = 정의 자체 사용 안 됨 → write-doc으로 CPS 갱신 검토

---

## /eval --surface (암묵지 발견)

**내가 당연하다고 생각하지만 하네스에 기록되지 않은 가정**을 찾는다.

### 왜 필요한가

"교육용이니까 당연히 코드가 짧아야지" — 나는 알지만 AI는 모른다.
문서에 없으면 AI는 자기 판단으로 행동하고, 그 판단이 내 기대와 다를 수 있다.
CPS Agent가 init에서 "왜 만드는가"를 잡지만, "어떻게 만들어야 하는가"에 대한
암묵적 기대는 개발이 진행되면서 계속 드러난다.

### 절차

**1. 현재 하네스 읽기** — CLAUDE.md, rules/, skills/를 읽고 명시된 규칙을 파악한다.

**2. 카테고리별 질문** — 아래 카테고리에서 하네스에 **없는** 가정을 찾는다.

사용자에게 직접 질문하는 방식으로 진행한다. 추측하지 않는다.

| 카테고리 | 질문 예시 |
|----------|----------|
| 품질 기준 | 파일 길이 상한? 함수 복잡도? 테스트 커버리지 목표? |
| UX 기대 | 로딩 시간? 에러 메시지 톤? 접근성 수준? |
| 엣지 케이스 | 빈 입력? 대량 데이터? 오프라인? 동시 접속? |
| 성능 | 응답 시간? 메모리 제한? 번들 크기? |
| 코드 스타일 | 주석 언어? 로그 레벨? 에러 메시지 형식? |
| 사용자 경험 | 첫 사용자 흐름? 이탈 시나리오? 데이터 보존 정책? |

모든 카테고리를 매번 다 묻지 않는다.
현재 프로젝트 상태와 최근 작업에서 관련 있는 카테고리만 선별한다.

**3. 발견된 가정 분류** — 사용자 답변에서 나온 암묵지를 하네스 어디에 넣을지 분류한다.

| 가정 성격 | 배치 |
|----------|------|
| 수치/기준 (500줄 이하, 3초 이내) | 린터 또는 rules/ |
| 패턴/방식 (에러는 이렇게 처리) | rules/coding.md 또는 rules/ 신규 |
| 방향/톤 (친절하게, 전문적으로) | CLAUDE.md |

**4. 반영** — 분류된 항목을 해당 하네스 파일에 추가한다. 사용자 확인 후.

### 핵심 질문

> "AI가 내 기대와 다르게 행동할 수 있는 '당연한 것'이 아직 문서에 없는가?"

### 주의

- 이 스킬은 사용자의 머릿속을 끌어내는 것이다. AI가 추측해서 채우는 게 아니다.
- 질문을 던지고 사용자가 답하는 형식. 답이 "모르겠다"이면 넘어간다.
- 한 세션에 모든 걸 다 찾으려 하지 마라. 2~3개 발견하면 충분하다.
- 발견된 암묵지가 반드시 규칙이 될 필요는 없다. "지금은 안 정해도 된다"도 유효.

---

## --deep (4관점 2차 검증 + 시크릿 스캔)

기본 또는 `--harness` 결과가 나온 후, **다른 관점에서 한 번 더** 돌린다.
1차 분석에서 "문제없음 ✅"가 나와도 2차에서 발견되는 것이 있다.

### Step 0: 시크릿 스캔 (무조건 선행, skip 금지)

`--deep` 시작 시 3관점 병렬 호출 **이전에** 자동 스캔을 반드시 실행한다.
사람의 정성 평가는 패턴 매칭에 약하므로 도구로 보강한다.

#### 실행 명령 (working tree + git history)

```bash
# 1) working tree 스캔
gitleaks detect --source . --no-git --verbose --redact || true

# 2) git history 스캔 (과거 커밋에 노출된 적 있는지)
gitleaks detect --source . --log-opts=--all --verbose --redact || true

# gitleaks 미설치 시 대체:
#   trufflehog filesystem . --no-verification
#   또는 git-secrets --scan-history
```

gitleaks가 없으면 수동 grep 폴백을 실행한다:

```bash
# Supabase service_role / secret
git grep -nE "sb_secret_|service_role|sb_publishable_" -- . || true
# AWS
git grep -nE "AKIA[0-9A-Z]{16}|aws_secret_access_key" -- . || true
# Stripe
git grep -nE "sk_(live|test)_[0-9a-zA-Z]{20,}|rk_live_" -- . || true
# GitHub / GitLab
git grep -nE "ghp_[0-9a-zA-Z]{36}|gho_|glpat-[0-9a-zA-Z_-]{20,}" -- . || true
# Slack
git grep -nE "xox[baprs]-[0-9a-zA-Z-]+" -- . || true
# 일반 토큰/비밀번호 (20자 이상 리터럴)
git grep -nE "(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{20,}['\"]" -- . || true
# 짧은 평문 비밀번호
git grep -nE "password\s*=\s*['\"][^'\"]{6,}['\"]" -- . || true
```

#### 출력 요구

- 발견 위치는 `파일:라인` 포맷으로, 키 종류와 함께 보고.
- **working tree 노출 vs git history 노출을 분리**해서 표시.
- 노출 키는 "즉시 rotation 필요" (service_role, sk_live_, aws_secret 등)와
  "공개 무방" (publishable anon key 등)으로 구분.
- 0건이어도 "시크릿 스캔 실행 완료, 0건"으로 **명시한다. skip 금지.**

#### 보고 예

```
### 시크릿 스캔
- working tree: 0건 ✅
- git history: 4건 발견 🚨
  - tools/dev-tools/seed.ts:12 — sb_secret_xxx (service_role) — 즉시 rotation
  - tools/setup/admin.ts:8 — password = "..." (admin 비밀번호) — 즉시 rotation
  → Supabase 대시보드에서 service_role 키 재발급 + git history 재작성(BFG) 필요
```

### Step 1: archive 후보 폴더 강제 1회 점검

eval은 "곧 삭제할 archive/legacy/cleanup 후보"로 분류한 폴더의
**내부 파일을 한 번도 보지 않는 편향**이 있다. 이 편향이 이번 사고의 직접 원인.

#### 규칙

archive/cleanup/legacy/deprecated 분류 후보로 지목된 모든 폴더에 대해:

1. 폴더 내 **모든 파일의 첫 20줄을 1회 Read**한다 (Glob + Read 반복).
2. 시크릿 스캔 결과와 교차 대조.
3. 아래 **삭제 안전성 체크리스트 4개 모두 만족**해야 "삭제 안전" 판정.

```
폴더: tools/dev-tools/
- [ ] 시크릿 0건 (Step 0 결과와 교차)
- [ ] 외부 코드 참조 0건 (grep으로 import/require 확인)
- [ ] 활성 cron/CI에서 호출 0건 (.github/workflows, package.json scripts 확인)
- [ ] 현재 사용 중 문서에서 언급되지 않음 (docs/ grep)
```

하나라도 실패 시 **"삭제 위험"으로 판정**하고, 본문에 위험 사유를 명시한다.
"archive 이동 후보"라는 분류만으로 내부 점검을 건너뛰지 마라.

### 2차 검증 4관점 (advisor 경유)

`--deep` 2차 검증은 **advisor 스킬로 4 specialist 병렬 호출**한다. 각
관점은 independent specialist에 1:1 매핑돼 있어 eval이 4관점을 직접
내재화하지 않는다 (self-containment 원칙 + 재사용성).

| eval 4관점 | 담당 specialist | 중점 질문 |
|-----------|----------------|----------|
| 파괴자 | risk-analyst | "이게 어디서 깨지는가? 빈약한 가정·악의 입력·에러 핸들링 누락·외부 의존성 죽음" |
| 트렌드 | researcher | "지금도 유효한 선택인가? deprecated·업계 표준 변경·더 나은 대안" |
| 비용/과잉 | codebase-analyst | "더 단순하게 할 수 있는가? 한 곳에서만 쓰는 추상화·불필요 패턴·미사용 심볼" |
| 외부공격자 | threat-analyst | "외부에서 뚫을 구멍? 6 시나리오 — git history·public docs·클라이언트 번들·CORS/CSP·RLS bypass·admin 가드" |

`--harness` 분기: risk-analyst는 "규칙 허점 악용", researcher는 "시대 뒤떨어진
패턴 강제", codebase-analyst는 "규칙 자체 과잉·관성" 관점으로 호출.

### 실행 방식

1. 기본 또는 `--harness` 분석을 정상 실행 → 1차 결과 보고.
2. **Step 0(시크릿 스캔) + Step 1(archive 폴더 점검)** 실행 → 결과 보고.
3. **advisor 스킬 호출** — advisor가 4 specialist 병렬 실행.
   - eval의 `--deep` 호출은 advisor "2~3개 기본" rule의 **예외**로
     **4 specialist 필수 병렬**. advisor.md가 이 패턴을 지원.
4. advisor 종합 결과(산출물 점수 포함)를 받아 사용자에게 보고.

**병렬 이유**: 독립 관점 보장. 앞 분석이 뒤 분석에 영향을 주면 안 됨.

### advisor 호출 시 박는 입력 (정보 흐름 누수 #6 해소 — 핸드오프 계약 Pass 축)

eval이 advisor 호출 prompt에 다음을 **인라인**으로 박는다. advisor가 각
specialist에 재전달. 누수 차단.

```
## eval 맥락
- 모드: --deep | --deep --harness
- 1차 분석 요약: <간극 분석 또는 --harness 결과>

## Step 0 (시크릿 스캔) 결과
- working tree hit: <파일:라인 목록 또는 "0건">
- git history hit: <파일:commit 목록 또는 "0건">
- archive 후보 폴더 스캔: <폴더별 결과>

## Step 1 (archive 폴더 점검) 결과
- 점검 폴더: <목록>
- 삭제 안전: <예/체크리스트 결과>
- 위험 발견: <있으면 명시>

## 지시
위 결과는 eval 스킬이 이미 확인했다. **재스캔 금지.** 각 specialist는
자기 관점에서 "이 결과가 놓친 것·추가 탐색할 것"만 집중.

- risk-analyst: 취약 경로 특정 의심 영역만 추가 탐색
- codebase-analyst: Step 1 archive 결과 외 미사용 심볼 grep만
- threat-analyst: Step 0 시크릿 hit를 rotation·history 정리 관점으로 재해석 (재스캔 금지)
- researcher: Step 0/1과 무관. 업계 동향·deprecated·탑 인물 의견만
```

이 주입으로 specialist당 2~3 tool calls 기대 (재스캔 없음).

### 산출물 점수 활용 (품질 게이트)

각 specialist 자가 평가 종합점수가 **≤ 2점**인 관점이 있으면:
- 사용자에게 "이 관점 신뢰도 낮음" 경고 표시
- 필요 시 사용자 요청으로 재호출·보완 specialist 호출

점수는 절대 지표가 아닌 **상대 비교·재호출 판단**용.

### 보고 형식

```
## 2차 검증 (--deep)

### 시크릿 스캔 (Step 0)
- working tree: 0건 ✅
- git history: 0건 ✅

### archive 후보 폴더 점검 (Step 1)
- tools/dev-tools/: 삭제 안전 ✅ (체크리스트 4/4 통과)

### 파괴자
- payments_api: 결제 실패 시 재시도 로직 없음. 네트워크 끊기면 무한 대기.

### 트렌드
- 없음 ✅

### 비용/과잉
- shared/utils/: 유틸 함수 12개 중 3개만 사용됨. 나머지 9개 삭제 가능.

### 외부 공격자
- 없음 ✅
```

### Step 마무리: 세션 종료 시 메모리/룰 저장

시크릿 또는 외부 공격자 시나리오에서 **사고급 발견**이 있으면 다음을 수행한다.
발견이 0건이면 skip.

#### 1) feedback 메모리 저장 (`.claude/memory/`)

파일: `.claude/memory/feedback_eval_secret_scan.md` (없으면 새로, 있으면 최신 사고로 갱신)

```yaml
---
name: eval-deep-secret-scan-enforcement
description: eval --deep 시 archive 후보 폴더도 반드시 시크릿 스캔 + 헤더 1회 검토
type: feedback
---

eval --deep 시 archive/legacy/cleanup 분류 후보 폴더에 대해서도
Step 0(시크릿 스캔) + Step 1(파일 헤더 20줄 훑기)을 반드시 실행한다.

**Why:** 2026-04-18 tools/dev-tools/ + tools/setup/ 6개 파일에서
Supabase service_role 키와 admin 비밀번호가 git history에 영구 노출된 채
eval --deep가 "archive 이동 후보"로만 분류하고 내부를 들여다보지 않아 검출 실패.

**How to apply:** --deep 시작 시 Step 0/1을 자동 실행. 폴더를 "곧 삭제할"이라고
분류했다는 이유로 내부 파일 1회 훑기를 건너뛰지 마라. 삭제 안전성 체크리스트
4개 모두 통과해야 archive 이동 허가.
```

그리고 `.claude/memory/MEMORY.md`에 한 줄 인덱스 추가:

```markdown
- [eval-deep-secret-scan-enforcement](feedback_eval_secret_scan.md) — archive 후보도 시크릿 스캔 필수 (2026-04-18 사고 기반)
```

#### 2) `.claude/rules/security.md` 룰 신설/갱신

security.md가 없으면 신설한다 (템플릿은 본 레포 `.claude/rules/security.md` 참조).
이미 있으면 이번 사고에서 새로 드러난 패턴만 추가한다.

#### 3) 인시던트 문서

사고급 발견이면 `docs/incidents/` 밑에 write-doc 스킬로 인시던트 문서 생성을 제안.
파일명: `incidents--<슬러그>_YYMMDD.md`.

### 주의

- 4관점 + Step 0/1 전부 문제없으면 "2차 검증 통과. ✅"로 끝. 장문 금지.
- 파괴자 관점에서 찾은 것이 반드시 즉시 수정해야 하는 건 아니다. 위험 인지가 목적.
- 트렌드 관점에서 "더 새로운 게 있다"는 교체 권고가 아니다. 사용자가 판단.
- **외부 공격자 관점에서 "즉시 조치" 분류된 항목은 즉시 사용자에게 보고. 미루지 마라.**
