---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
---

# 다운스트림 마이그레이션 가이드

각 하네스 버전이 다운스트림 프로젝트에 요구하는 **수동 액션**을 정리한다.
`harness-upgrade` 스킬이 자동 병합하지만, **다음 항목은 사람이 직접
판단·입력**해야 한다.

스킬이 업그레이드 마지막 단계에서 본 문서를 읽고 새 버전 섹션을 사용자
에게 보여준다. 자동 채워지는 항목과 수동 액션이 명확히 분리되어야 silent
fail을 막는다.

> **버전 다운그레이드 노트 (2026-04-19):** 1.6.x~1.9.0으로 표기됐던
> 버전을 0.x로 리셋. semver 0.x가 "공개 API 불안정·실험 단계"이며
> 현재 상태와 정확히 일치. 섹션 헤더를 실제 적용 버전으로 갱신:
>
> | 구 표기 | 현 표기 | 내용 |
> |---|---|---|
> | v1.7.0 | v0.6.0 | 하네스 단순화 P0 |
> | v1.8.0 | v0.6.1 | 다운스트림 마이그레이션 인프라 |
> | v1.8.1 | v0.6.2 | pre-check lint stdout 오염 수정 |
> | v1.9.0 | v0.7.0 | Bash matcher 광역 패턴 폐기 |

## 포맷

각 버전 섹션은 다음 구조를 따른다:

```
## vX.Y.Z (요약)

### 자동 적용 (스킬이 처리)
- 어떤 파일이 자동 덮어씌워지는지

### 수동 액션 (사용자 필수)
- [ ] 체크박스 항목. 각 항목에 명령·예시·위치 포함

### 검증
- 적용 후 무엇으로 확인하는지 (test 스크립트·grep 등)

### 회귀 위험
- 기존 동작이 바뀌는 부분
```

---

## v0.16.0 — 문서 네이밍 전면 개편 (도메인 약어 + 통합 원칙)

### 자동 적용 (스킬이 처리)

**규칙 갱신**:
- `.claude/rules/naming.md` — "왜 — 파일명이 곧 인덱스다" 섹션 신설,
  "도메인 약어" 표 신설, "파일명 — 문서/WIP" 섹션 채움, "Cluster 자동
  매핑" 직교 파싱 규칙 추가. **날짜 suffix 전면 금지 (incidents 포함)**
- `.claude/rules/docs.md` — "핵심 원칙" 섹션 최상단 추가(탐색 체인),
  "문서 탐색" 섹션을 `ls`/`grep` 우선 경로로 재구성, 파일명 규칙 +
  주제 분할 기준, 금지 목록에 날짜 suffix·미등록 abbr 추가

**스킬 갱신**:
- `.claude/skills/write-doc/SKILL.md` — Step 1에 abbr 조회·검증 + 누락
  시 사용자 입력 요청, Step 3 파일명 생성이 신 형식, 날짜 suffix 요청
  거부 로직
- `.claude/skills/docs-manager/SKILL.md` — Step 3 cluster 매핑이 파일명
  abbr 직교 파싱(불투명 prefix·라우팅 태그·레거시 `_p2_` 통과), `--validate`
  에 약어 중복·도메인 1:1 대응·파일명 날짜 suffix 검사 추가

**업스트림 파일 rename (40개 + cluster + 결정문)**:
- `docs/decisions/*` 10개: 날짜 suffix 제거 + `hn_` abbr 부착
- `docs/guides/*` 6개: 동일 (전역 마스터 2개는 abbr 없음)
- `docs/harness/*` 19개: 동일 (`MIGRATIONS.md`·`promotion-log.md`는 전역 마스터)
- `docs/incidents/*` 6개: 날짜 suffix 제거 + `hn_` abbr 부착
- `docs/clusters/harness.md` 재생성 (신 파일명 기준 + 폴더별 분류)
- 본문 참조 173건 전수 치환 (마크다운 링크·relates-to·rules 본문)

### 왜

- 파일명이 곧 인덱스 → `ls docs/**/{abbr}_*`로 도메인 문서 즉시 목록화
- 같은 주제 = 같은 파일 → 날짜 suffix로 인한 SSOT 분열 차단
- docs-manager가 파일명만으로 cluster 자동 매핑 → 수동 인덱스 관리 제거
- 다운스트림이 앞에 `m3-`·`s12-` 같은 불투명 prefix를 붙여도 직교 파싱
  이 abbr만 추출해 cluster 매핑 유지
- tags 프론트매터로 세분화 (`skill`·`rule`·`agent` 등) → 도메인을 여러
  개로 쪼개지 않고도 축 분리 가능

자세한 결정 근거: `docs/decisions/hn_doc_naming.md`

### 수동 액션 (다운스트림 필수)

- [ ] **`.claude/rules/naming.md` "도메인 약어" 표 채우기**

  업그레이드 후 naming.md에 "도메인 약어" 섹션이 추가됐지만 표에는
  하네스 시드(`hn`·`mt`)만 있음. **"도메인 목록 > 확정"의 모든 도메인
  에 대해 abbr을 등록**해야 함.

  규칙:
  - 2~3자 소문자 영문
  - 도메인당 1개
  - 기존 약어와 충돌 금지
  - 원 이름의 첫 자·자음 조합 선호 (`payment → pm`, `migration → mg`)

  예:
  ```
  | 도메인 | abbr | cluster 파일 |
  |--------|------|--------------|
  | harness | hn | clusters/harness.md |
  | meta    | mt | clusters/meta.md    |
  | payment | pm | clusters/payment.md |
  | auth    | au | clusters/auth.md    |
  | api     | ap | clusters/api.md     |
  ```

  등록 안 하면 `docs-manager --validate`가 "도메인-약어 1:1 대응 누락"
  경고. 파일명 prefix 매칭도 실패해 cluster 자동 매핑 안 됨.

- [ ] **(선택) 기존 문서 이름 마이그레이션 정책 결정**

  현재 문서가 날짜 suffix(`hn_memory_260420.md` 같은)를 가지고 있을
  수 있음. 기존 파일 처리는 다운스트림 자율:

  **옵션 A — 점진 이동 (권장)**
  갱신 시점마다 같은 커밋에서 파일명도 신 규칙으로 변경 (`git mv`).
  본문 내 마크다운 링크·relates-to path 함께 갱신. 소규모·저위험.

  **옵션 B — 일괄 이동**
  자체 스크립트로 한 번에 이동. 업스트림이 v0.16.0에서 자기 40개 파일을
  이렇게 이동했음. 참조 대량 치환 필수. 프로젝트마다 참조 구조가 달라
  업스트림은 범용 스크립트 제공 안 함.

  업스트림 일괄 이동 절차 참고 (템플릿):
  ```bash
  # 1. rename 매핑 파일 작성 (src dst 쌍)
  # 2. 일괄 git mv
  # 3. 본문 참조 sed 치환 (옛 파일명 basename → 신 basename)
  # 4. dead link 검사
  # 5. clusters/* 재생성
  # 6. 회귀 테스트 (test-pre-commit.sh 등)
  ```

  **옵션 C — 현상 유지**
  옛 이름 그대로. 직교 파싱 규칙이 구 파일명도 abbr 추출 성공하므로
  cluster 매핑은 동작. 신규만 신 규칙 준수.

- [ ] **(선택) 마일스톤·Phase prefix 등 프로젝트 고유 확장 정의**

  Phase/Milestone/Sprint 기반 개발 구조를 가진 프로젝트는 `naming.md`
  하단에 `### 파일명 — 확장 (프로젝트 고유)` 섹션을 추가하고 자기
  문법 정의:
  ```
  ### 파일명 — 확장 (프로젝트 고유)

  m{N}-{abbr}_t{NN}_{slug}.md       마일스톤-task
  m{N}_{slug}.md                    마일스톤 횡단
  ```

  업스트림 직교 파싱은 앞쪽 `m{N}-`을 **불투명 prefix로 통과**시키고
  abbr만 추출하므로 cluster 매핑은 그대로 동작. `harness-upgrade`는
  업스트림 소유 섹션만 덮어쓰므로 이 확장 섹션은 보존됨.

### 검증

```bash
# 도메인-약어 1:1 대응 확인
grep -A20 "도메인 약어" .claude/rules/naming.md

# 파일명 규칙 위반 스캔
find docs -name "*.md" | grep -vE "(incidents/|^docs/WIP/)" \
  | grep -E "_[0-9]{6}\.md$"
# 출력 있으면: incidents 외 날짜 suffix 남은 파일

# docs-manager 정합성 검사
# (Claude에게 /docs-manager --validate 실행 요청)
```

### 회귀 위험

- **기존 파일 이름 혼재 기간** — 구 이름(`hn_memory_260420.md`)과 신
  이름(`hn_memory.md`) 공존. 직교 파싱으로 매핑은 둘 다 성공하나, 사용자
  ·LLM 모두 당분간 두 패턴 동시 노출
- **abbr 표 누락 시 조용한 실패** — 도메인 추가하고 약어 등록 안 하면
  그 도메인 문서는 cluster에 등록 안 됨. `--validate` 정기 실행 필요
- **마일스톤 확장 섹션 관리 책임** — 업스트림이 의미 해석 안 하므로
  다운스트림 자체 규율 필요. `m{N}-`이 무엇인지 그 프로젝트에서 정의

---

## v0.9.3 — stage 격상 면제 버그 수정

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` — 2단계 격상(MULTI_DOMAIN + critical → deep)에
  IS_DOC_ONLY 면제 추가. S5/S6 단독(코드/핵심설정/마이그레이션/빌드 미동반)은
  multi-domain critical이어도 deep 격상 안 함.
- `.claude/rules/staging.md` — 룰 A에 면제 ※ 명시.

### 수동 액션

없음.

### 검증

다운스트림에서 doc-only commit이 multi-domain critical 환경에서도 적절히 분류되는지:

```bash
# 더미: docs/만 변경된 staged 상태에서
bash .claude/scripts/pre-commit-check.sh | grep recommended_stage
# 기대: skip 또는 micro (이전엔 deep으로 격상되곤 함)
```

### 회귀 위험

- 정상 deep 격상(S7+S9 critical, S6+S7+S9 critical 혼합 등)은 그대로 작동.
  코드/핵심설정 동반 시 IS_DOC_ONLY="" 이라 면제 미발동.
- 시뮬레이션 검증: starter 측에서 두 케이스 통과 확인.

---

## v0.9.1 — rules 다이어트 + harness-upgrade 화이트리스트

### 자동 적용 (스킬이 처리)

- `.claude/rules/*.md` 7개 파일 재구조화 (본문 압축, 포인터 추가). 매 세션
  시스템 프롬프트 용량 약 15KB 절감.
- `.claude/skills/harness-upgrade/SKILL.md` — "하네스 파일 범위"에
  rules가 참조하는 docs/ 화이트리스트 추가. 이후 업그레이드는 이 목록을
  자동 이식.

### 수동 액션 (다운스트림 필수)

v0.9.1로 처음 업그레이드하는 다운스트림은 **rules가 docs/를 참조하는데 그
docs/가 존재하지 않는 dead link**가 발생한다. 이전 버전의 harness-upgrade
가 `docs/guides/*`·`docs/decisions/*`를 "사용자 전용"으로 분류해 전혀
이식하지 않았기 때문이다.

- [ ] **rules 참조 문서 4개를 다운스트림에 수동 복사**

  ```bash
  cd <다운스트림 프로젝트>

  # starter 리포에서 직접 복사 (harness-upstream remote 활용)
  for f in \
    docs/guides/hn_doc_search_protocol.md \
    docs/guides/hn_external_research_patterns.md \
    docs/decisions/hn_staging_governance.md \
    docs/decisions/hn_rules_metadata.md; do
    mkdir -p "$(dirname "$f")"
    MSYS_NO_PATHCONV=1 git show harness-upstream/main:"$f" > "$f"
  done

  # INDEX.md·clusters/harness.md 수동 갱신 (docs-manager 위임 권장)
  ```

  복사 후 해당 도메인이 `harness`인지 확인. 다운스트림이 starter 관리
  문서로 인식하면 업그레이드 때 건드리지 않도록 화이트리스트 자동 보호.

### 검증

```bash
# rules의 dead link 재확인
grep -nE "docs/(guides|decisions)/[a-z_-]+_260420\.md" .claude/rules/*.md

# 위 출력의 각 경로가 실제 존재하는지
ls docs/guides/hn_doc_search_protocol.md \
   docs/guides/hn_external_research_patterns.md \
   docs/decisions/hn_staging_governance.md \
   docs/decisions/hn_rules_metadata.md
```

### 회귀 위험

- 없음. 본문 축약·포인터 추가만. 행동 로직 변경 없음.
- 단, 후속 업그레이드에서 rules가 새 docs/ 파일을 참조하면 SKILL.md 화이트
  리스트에도 등록해야 dead link 재발 안 함. (review 자동 감지는 후속 과제)

---

## v0.8.0 — review 패턴 매핑 + CPS 복원

### 자동 적용 (스킬이 처리)

- `.claude/agents/review.md` 전면 재작성 — "카테고리 설명" → "diff 패턴 →
  검증 행동" 9개 매핑. 각 패턴별 tool 선택·호출 횟수 명시.
  frontmatter `maxTurns: 6` 추가 (agentic turn hard 상한).
- `.claude/agents/review.md`에 CPS 감지 패턴 9번 추가 — 새 도메인·규칙·
  스킬·에이전트 신설 시 CPS 문서 갱신 누락 감지.

### 수동 액션 (권장)

- [ ] **프로젝트 CPS 문서 확인·작성**

  `harness-init` 실행한 프로젝트면 `docs/guides/project_kickoff_*.md`가
  이미 있음. **없으면** (또는 `status: sample`만 있으면) CPS 무너진 상태 —
  review의 9번 패턴·implementation Step 0 모두 제대로 작동 안 함.

  조치:
  ```bash
  # CPS 확인
  ls docs/guides/project_kickoff_*.md
  # 없거나 sample만 있으면 /harness-init 다시 실행
  ```

  CPS는 Context(배경·제약)·Problems(해결할 핵심 문제)·Solutions(접근법)
  3섹션. 한 번 만들면 새 Problem 발견 시마다 갱신 (review 9번이 검증).

### 회귀 위험

- review가 이전엔 카테고리 전체 돌았는데 이제 패턴 hit한 것만 돔 → 특정
  회귀 누락 가능성. 발견 시 review.md에 패턴 추가.

---

## v0.7.2 — settings.json schema 검증 자동화

### 자동 적용 (스킬이 처리)

- `.claude/scripts/validate-settings.sh` 신설 — Claude Code 재로드 전
  schema 사전 검증. 실패 시 구체 에러 stderr.
- `.claude/scripts/auto-format.sh`에 settings.json 변경 시 자동 호출 추가.
- `.claude/scripts/downstream-readiness.sh`에 검증 항목 추가.

### 배경

사용자 실측: 한 세션에 settings.json validation 에러 2회 발생 → 40k 토큰
허비 (에러 응답에 전체 schema 덤프). 다음 실수 방지 위해 **Claude Code
재로드 전** 사전 검증.

### 수동 액션

없음. 자동 패치만.

### 회귀 위험

- validate-settings.sh가 모르는 새 공식 필드는 "알 수 없는 이벤트" 경고
  낼 수 있음 (에러 아닌 경고). 공식 스키마 변경 시 스크립트 갱신.

---

## v0.7.1 — review 토큰 과소비 수정 + MCP 다운스트림 최소화 권장

### 자동 적용 (스킬이 처리)

- `.claude/rules/staging.md` 룰 1번 정밀화 — S9(critical) + 메타·문서
  단독(S5/S6만)일 때 deep 강제 안 함
- `.claude/scripts/pre-commit-check.sh` 동일 수정 (HAS_CODE_OR_CORE 가드)
- `.claude/agents/review.md` Stage 2/3 Read 상한 축소 — "10+" 폐기,
  Stage 3 최대 5회. 과도한 Read 경계 규정 추가

### 수동 액션 (사용자 필수·권장)

- [ ] **MCP 서버 설정 점검** (spawn 시 토큰 과소비 방지)

  `~/.claude/settings.json`에 MCP 서버가 전역 등록돼 있으면 **모든 프로젝트**
  에 상속. 프로젝트별로 필요한 것만 `.mcp.json`(프로젝트 루트)에 정의 권장.

  현재 상태 확인:
  ```bash
  # 전역 (영향 큼)
  grep -A10 mcpServers ~/.claude/settings.json 2>/dev/null

  # 프로젝트별 (권장)
  cat .mcp.json 2>/dev/null
  ```

  조치:
  - **전역에 있는 MCP 중 프로젝트 무관한 것은 제거** (예: 일부 프로젝트만
    Supabase 사용하면 전역에서 빼고 해당 프로젝트 `.mcp.json`에만)
  - 서브에이전트는 `tools` allowlist로 이미 MCP 차단하지만, 메인 세션에는
    MCP 스키마가 계속 로드됨 → review 호출 시 상속되는지는 claude-code
    내부 구현 따라 다름. 실측으로 확인 필요.

  **주의:** `.mcp.json`은 프로젝트별 MCP 정의. 팀 공유 대상이라 민감한
  서버(개인 Gmail·Slack 등)는 팀 리포에 체크인 금지. 팀용은 `.mcp.json`,
  개인용은 `~/.claude/settings.json`.

### 회귀 위험

- **review 품질 저하 가능성** — Read 횟수 줄였으므로 복잡한 케이스에서
  검증 놓칠 수 있음. incident 발생 시 Stage 3 Read 상한 재검토.

---

## v0.7.0 — Bash matcher 광역 패턴 폐기 + 단일 hook 통합

### 자동 적용 (스킬이 처리)

- `.claude/rules/hooks.md` 신설 — argument-constraint 매처 금지 규칙.
- `.claude/settings.json` 단순화 — 모든 `Bash(... -X ...)` 광역 매처 제거.
  Bash matcher 1개 (단일 `bash-guard.sh` 호출).
- `harness-upgrade` Step 8.2 신규 — 구버전 starter 소유 hook(광역 매처)을
  다운스트림에서 감지·제거 제안. 사용자 커스텀 hook은 보존.
- `downstream-readiness.sh` argument-constraint 매처 전수 감지 추가.
- `.claude/scripts/bash-guard.sh` 신규 — jq로 명령 파싱 후 토큰 단위 검증.
  공식 권장 패턴 (https://code.claude.com/docs/en/permissions 인용).
- `.claude/scripts/test-bash-guard.sh` 신규 — 13건 회귀 테스트.
- `.claude/scripts/test-hooks.sh` **삭제** — bash glob로 매처 모사가 공식
  matcher와 달라 거짓 안전감 제공. test-bash-guard.sh가 실제 hook
  입력 형식(JSON via stdin)으로 검증.
- `.claude/scripts/pre-commit-check.sh` 핵심 설정 연속 수정 차단 복원 —
  `settings.json`·`rules/*`·`scripts/*`·`CLAUDE.md`가 5커밋 중 3회 이상
  변경되면 차단. `[expand]` 태그로 우회. 일반 코드는 차단 없이 카운트만.
- `.claude/scripts/downstream-readiness.sh` v1.9.0 신호 갱신.

### 수동 액션 (사용자 필수)

없음. 자동 패치만.

### 검증

```bash
bash .claude/scripts/test-pre-commit.sh   # 21/21
bash .claude/scripts/test-bash-guard.sh   # 13/13
bash .claude/scripts/downstream-readiness.sh  # 0/0
```

이전(v1.7~v1.8) 광역 매처가 잘못 차단했던 정당 명령 7가지(`bash -n`,
`head -n`, `git push origin main` 등) 모두 통과 검증됨.

### 회귀 위험

- **차단 메시지 변경** — 이전 "❌ git commit -n 금지" → "❌ git commit -n
  금지 (verify 우회). bash -n 같은 다른 -n은 영향 없음." (대안 명시 추가)
- **메시지 안 -n 통과** — `git commit -m "fix -n bug"` 같이 quote 안의
  -n은 토큰 분리 후 인자가 아니라고 판단해 통과. 이전엔 잘못 차단.
- **핵심 설정 3회 차단 복원** — settings.json·rules/·scripts/를 같은 영역
  3회 연속 수정하면 차단. 정당한 점진 확장이면 커밋 메시지에 `[expand]`
  태그 포함.

### 배경

이번 세션 중 사용자 지적: "이전에 수정한 내역이 있는데 어느 것도 참조
하지 않고 또 추측해서 수정". 1·2차 수정(1a50efd, 88f1ff2, 3468fb5)이
모두 공식 문서 미확인 + 추측 기반. 공식 문서 확인 결과 매처 `*`가
공백 포함 모든 문자에 매칭되며 "argument constraint는 fragile" 명시
경고 + jq 기반 hook 권장 발견. 이에 따라 매처 자체를 폐기.

incident: `docs/incidents/hn_bash_n_flag_overblock.md` 3차 섹션.

---

## v0.6.2 — pre-check lint stdout 오염 수정 + commit push 보강

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 패치 — lint 명령의 stdout/stderr
  모두 캡처 후 종료 코드만 평가. 이전엔 stdout만 흘려 신호 줄과 섞임.
- `.claude/skills/commit/SKILL.md` 푸시 섹션 강화 — `is_starter: true`
  분기 + `HARNESS_DEV=1 git push` 명시.
- `.claude/scripts/test-hooks.sh` push 회귀 케이스 추가 (S1).
  **※ v0.7.0에서 test-hooks.sh 자체 폐기. 본 케이스는 test-bash-guard.sh로 이전됨.**

### 수동 액션 (사용자 필수)

없음. 자동 패치만으로 완료.

### 검증

```bash
# 다운스트림(lint 있는 프로젝트)에서 21/21 통과 확인
bash .claude/scripts/test-pre-commit.sh
```

이전(v1.7.0~v1.8.0)에서 다운스트림이 12/21 같은 부분 통과로 떨어졌다면
본 패치 후 21/21로 복원됨.

### 회귀 위험

- lint 실패 시 출력 형식 변경 — 이전엔 명령만 stderr, 이제는 명령 + 마지막
  20줄 stderr. 더 자세해짐 (개선).

---

## v0.6.1 — 다운스트림 마이그레이션 인프라 (본 문서 도입)

MIGRATIONS.md 자체 도입 + `harness-upgrade` Step 9.5(사용자 액션 표시)
+ `downstream-readiness.sh`(자가 진단). 수동 액션 없음 (자동 패치만).

---

## v0.6.0 — 하네스 단순화 (마찰 회수)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 교체 — 연속수정 차단·contamination
  검출 블록 제거, S1 file-only/line-confirmed 분리, S8 언어별 시그니처,
  needs_test_strategist 신호, S6 ≤5줄 → skip
- `.claude/agents/review.md` 교체 — "전제 컨텍스트" 신뢰 규칙, "오염 검토",
  "허위 후속 감지" 카테고리
- `.claude/skills/commit/SKILL.md` 교체 — Step 2 자동 본문 갱신 보수화,
  review prompt 전제 컨텍스트 주입, test-strategist 병렬 호출 절차
- `.claude/skills/write-doc/SKILL.md` 교체 — incidents/ symptom-keywords
  필수 재질의
- `.claude/skills/docs-manager/SKILL.md` 교체 — Step 2 차단 검사 실행
  절차 (awk + grep)
- `.claude/rules/staging.md` 교체 — S1 강도 분리, stdout 13 keys, Stage
  결정 우선순위 정렬
- `.claude/rules/contamination.md` **삭제** — review.md "오염 검토"
  카테고리로 이전
- `.claude/settings.json` Bash 매처 갱신 — `Bash(* -n *)` 광역 제거,
  `Bash(git commit -n*)` + `Bash(git commit* -n*)`로 한정
- `.claude/scripts/test-pre-commit.sh` 신규 — 21건 회귀 테스트
- `.claude/scripts/test-hooks.sh` 신규 — 11건 매처 회귀 테스트
  **※ v0.7.0에서 폐기(bash glob 모사가 공식 matcher와 달라 거짓 안전감).
     test-bash-guard.sh가 실제 hook JSON 입력으로 검증.**

### 수동 액션 (사용자 필수)

- [ ] **`.claude/rules/naming.md` "도메인 등급" 채우기**
  - 현재 다운스트림 도메인이 critical/normal/meta 어디에도 분류 안 됐으면
    staging 시스템이 무력화됨 (S9 신호 무시 → 전부 normal로 폴백).
  - 위치: `## 도메인 등급 (review staging)` 섹션
  - 분류 기준:
    - **critical**: 사고 시 데이터·돈·접근 제어 영향 (예: payment, auth,
      database, infra, admin, ticketing)
    - **normal**: 기능 영역, 격리됨 (예: api, ui, crawler, blog)
    - **meta**: docs·changelog 같은 회고용
  - 검증: `grep -A2 "도메인 등급" .claude/rules/naming.md`로 확정 도메인
    전체가 셋 중 하나에 들어갔는지 확인

- [ ] **`.claude/rules/naming.md` "경로 → 도메인 매핑" 채우기**
  - 코드 파일(`src/`·`apps/` 등) 변경 시 도메인 추출 위해 필요.
  - 비어 있으면 staging이 코드 변경에 도메인 등급 적용 안 함.
  - 예시:
    ```
    src/payment/**     → payment
    src/auth/**        → auth
    apps/admin/**      → admin
    migrations/**      → migration
    ```

- [ ] **`.claude/HARNESS.json` `is_starter` 확인**
  - 다운스트림이면 `false`여야 함. `true`면 review "오염 검토" 카테고리가
    잘못 활성화됨.
  - `grep is_starter .claude/HARNESS.json`

- [ ] **이전 contamination 면제 설정 정리** (해당 시)
  - 이전 버전에서 `.claude/rules/contamination.md` 면제 리스트를 커스터마이징
    했으면, 그 내용을 review.md "오염 검토" 카테고리 본문(다운스트림은
    `is_starter: false`라 비활성)에 옮길 필요 없음. 그냥 삭제로 충분.

### 검증

```bash
# 회귀 테스트 (다운스트림에서도 실행 가능)
bash .claude/scripts/test-pre-commit.sh    # 21/21 통과 기대
# v0.7.0+ 에서는 test-hooks.sh 대신 test-bash-guard.sh 사용:
bash .claude/scripts/test-bash-guard.sh    # 13/13 통과 기대

# 도메인 등급 확정 도메인 전체 분류 검증
DOMAINS=$(grep -E '^확정:' .claude/rules/naming.md | sed 's/확정://' | tr ',' '\n' | sed 's/^ *//;s/ *$//')
for d in $DOMAINS; do
  if ! grep -qE "(critical|normal|meta).*\*?\*?:?.*$d" .claude/rules/naming.md; then
    echo "[누락] $d 등급 미분류"
  fi
done
```

### 회귀 위험

- **연속 수정 차단 사라짐** — 같은 파일 3회 수정해도 차단 안 됨. 의도적
  완화. 정보는 `repeat_count` stdout으로만 흐름.
- **contamination 셸 검출 사라짐** — `is_starter: true` 리포에서만 review가
  대신 검토. 다운스트림은 영향 없음.
- **commit Step 2 4지선다 사라짐** — 자동 본문 갱신만. status 변경·이동은
  사용자 명시 요청 필요.
- **`bash -n script.sh` 등 `-n` 옵션 정당 사용 통과** — 이전엔 차단됐음
  (incident bash_n_flag_overblock).

---

## v0.6.0 이전

기록 없음. v0.6.0이 본 마이그레이션 가이드 도입 시점. 이전 버전은
`docs/harness/promotion-log.md`의 변경 항목을 참조.
