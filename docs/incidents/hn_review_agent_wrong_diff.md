---

title: review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고
domain: harness
tags: [review-agent, agent-context, false-warning]
problem: P2
s: [S2]
symptom-keywords:
  - review 헛소리
  - review 잘못 분석
  - review 다른 커밋
  - 엉뚱한 경고
  - staged diff 무시
relates-to:
  - path: ../archived/hn_commit_perf_optimization.md
    rel: caused-by
status: completed
created: 2026-04-19
updated: 2026-04-19
---

# review 에이전트가 staged diff 대신 직전 커밋을 분석한 사고

## 증상

v1.4.1 커밋(11fe9f2) 시점에 commit 스킬이 review 에이전트를 호출했다.
review가 응답한 "diff 실제 변경 목록"이 실제 staged 5파일과 전혀 달랐다.

**review가 본 것** (실제로는 직전 커밋 26b72c6의 내용):
- `internal-first.md`, `no-speculation.md` (신설)
- `pre-commit-check.sh` 연속 수정 감지
- `hook_flow_efficiency_260418.md` 보강
- `HARNESS.json` 1.3.2 → 1.4.0

**진짜 staged diff** (`git diff --cached --stat` 검증):
- `.claude/HARNESS.json` (버전 1.4.0 → 1.4.1)
- `.claude/agents/review.md`
- `.claude/scripts/pre-commit-check.sh` (stdout 분리)
- `.claude/skills/commit/SKILL.md`

review는 엉뚱한 경고 3건을 출력 ("커밋 목적과 diff 불일치", "stdout 출력
누락" 등). 차단(`block: true`)은 아니어서 커밋은 진행됐다.

## 원인

1. SKILL.md의 prompt 예시는 git diff 텍스트 자체를 박지 않고 메타 정보
   (이번 커밋의 목적, pre-check 결과 4줄)만 전달했다.
2. review.md는 입력 섹션에 "`git diff --cached` (또는 `git diff` —
   스테이징 전이면)"이라고 적혀 있었지만 **그것을 어떻게 받는지(prompt에
   박혔는지, Bash로 실행하는지)** 명시하지 않았다.
3. review 에이전트가 자기 마음대로 git 명령을 실행했고, 그 결과가
   `git diff --cached`가 아닌 다른 명령(`git show HEAD`, `git log -p` 등
   추정)이었다. 직전 커밋 내용이 정확히 일치하므로 `git show HEAD` 추정.
4. 추가 증거: review가 "회귀" 검증 명목으로 `harness-adopt/SKILL.md`,
   `harness-upgrade/SKILL.md`까지 grep했다. review.md의 "diff 밖 이야기는
   하지 마라" 원칙도 어겼다. 자기 마음대로 git 명령을 쓸 수 있는 환경에서
   "어디까지 봐야 할지"의 경계가 무너진 결과.

## 해결

방안 C 채택: prompt에 diff 텍스트 직접 박기 + review에 자가 git 명령
금지 명시.

### SKILL.md 변경

호출 방법 섹션에 다음을 추가:
- 스킬이 Bash로 직접 `git diff --cached`를 실행해서 결과 텍스트를 캡처
- 크기 가드: 2000라인 초과 시 stat + head 2000라인으로 축약
- prompt에 `## staged diff` 블록으로 캡처한 텍스트를 그대로 박음
- "## 지시" 블록에 "추가 git 명령 실행 금지" 명시

### review.md 변경

`## 입력` 섹션 재작성:
- prompt에 받는 4개 블록(`## 이번 커밋의 목적`, `## 연관 WIP 문서`,
  `## pre-check 결과`, `## staged diff`) 명시
- **절대 규칙: staged diff는 prompt가 진실** 섹션 신설
  - `git diff`, `git diff --cached`, `git log -p`, `git show` 등 staged
    diff를 우회·중복 조회하는 명령 금지
  - 파일 본문 맥락은 Read/Glob/Grep으로만 보충
  - prompt에 `## staged diff` 블록이 없으면 빈 diff로 처리, 임의 보충 금지

## 후속 검증

다음 커밋부터 review가 prompt 안의 staged diff만 분석하는지 확인 필요.
한 번 더 같은 사고가 나면 review의 Bash tool 권한을 더 좁혀야 할 수도
있다 (현재 `tools: Read, Glob, Grep, Bash`).

## 교훈

- 에이전트에게 "전달받는다"고만 적어두면 안 된다. **어떻게 전달받는지**
  명시 필요.
- "스스로 필요한 맥락 확보"라는 모호한 자율성은 잘못된 출처를 선택할 여지
  를 준다. 진실 데이터는 prompt에 박는 게 안전.
- "diff 밖 이야기 금지" 같은 원칙도 자가 git 권한이 있으면 무력하다.
  수단 자체를 차단해야 원칙이 강제된다.
