---
title: harness-upgrade silent fail 차단 보강 (FR-001/002/003 + FR-006)
domain: harness
problem: [P3, P11]
solution-ref:
  - S3 — "harness-upgrade Step 9.5 — 업그레이드 시 수동 액션 섹션 자동 표시 (부분)"
  - S3 — "다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨 (부분)"
  - S11 — "동형 패턴 잠복 — 본 wave는 1차 결함만 처리, 동형 후보 메모만 박제"
tags: [upgrade, silent-fail, three-way-merge, downstream]
relates-to:
  - path: decisions/hn_upgrade.md
    rel: extends
  - path: incidents/hn_sealed_migrations_exempt_gap.md
    rel: references
status: completed
created: 2026-05-10
updated: 2026-05-16
---

# harness-upgrade silent fail 차단 보강 (FR-001/002/003)

## 사전 준비
- 읽을 문서: `.claude/skills/harness-upgrade/SKILL.md` (Step 5/9/10), `docs/decisions/hn_upgrade.md`, `docs/incidents/hn_sealed_migrations_exempt_gap.md` — doc-finder fast+deep scan으로 확인 완료
- 이전 산출물: 다운스트림 v0.42.0 upgrade 후 측정된 FR-001/002/003 피드백 리포트 (MIGRATIONS.md `## Feedback Reports`)
- MAP 참조: HARNESS_MAP.md CPS 테이블 P3 행 (defends-by: harness-upgrade, downstream-readiness.sh)

## 목표
- 다운스트림 v0.42.0 upgrade 직후 측정된 silent fail 3건의 **알고리즘 갭** 보강
- harness-upgrade가 "처리한 횟수"가 아니라 **"upstream 정합성 도달 여부"** 를 보고하도록 흐름 강화
- CPS 연결: P3(다운스트림 사일런트 페일) Solution S3의 미달 영역(upgrade Step 자체에서 발견 안 됨) 보완

### 갭 정의 (사료 기반)
- doc-finder 결과 (deep scan): SKILL.md Step 5(라인 349~378)에 `base↔ours` 비교 로직 **없음**. 충돌 = 0 ↔ 정합성 도달이 등치되어 있음
- Step 9 정합성 검증은 docs/ 한정(`docs_ops.py validate`). `.claude/` 영역 정합성은 없음
- Step 10 완료 보고는 처리 카운트만, silent 제외 항목 + 정합성 미도달 항목 표기 없음

## 작업 목록

### 1. FR-001 — Step 5 3-way merge에 base↔ours sanity check 추가

**사전 준비**: SKILL.md Step 5 라인 349~430. `git merge-file` 호출 직전·후
**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`
**Acceptance Criteria**:
- [x] Goal: 본체 swap (frontmatter `name:` 변경 또는 base와 ours 70% 이상 차이) 감지 시 사용자 명시 confirm 강제
  검증:
    review: review-deep
    tests: 없음
    실측: SKILL.md Step 5 본문에 (a) `name:` 비교 절차 (b) base↔ours 라인 차이율 임계 절차가 명시됨. grep으로 두 절차 키워드 hit 확인 (`grep -E "name:|유사도|swap" .claude/skills/harness-upgrade/SKILL.md`)
- [x] Step 5에 frontmatter `name:` 필드 변경 ALERT 절차 명시 (스킬명 변경은 거의 항상 사고)
- [x] base↔ours 라인 차이율 70% 초과 시 "본체 swap 의심" confirm 강제. confirm 거부 시 theirs로 강제 교체 옵션 명시
- [x] sanity check 실패 케이스 처리: 사용자가 confirm Y → 기존 흐름 / N → theirs로 교체 / 보류 → 해당 파일 skip + log

### 2. FR-002 — Step 9 직후 upstream 정합성 자동 검증 단계

**사전 준비**: SKILL.md Step 9 라인 567~599 직후 신규 Step 추가 (Step 9.6 신설)
**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`
**Acceptance Criteria**:
- [x] Goal: upgrade Step 9 직후 `git diff harness-upstream/main HEAD --name-only` 자동 실행, 결과를 (a) 사용자 전용 (b) starter_skills 제외 (c) **그 외 미적용 의심** 3개 카테고리로 분류해 표시
  검증:
    review: review-deep
    tests: 없음
    실측: SKILL.md Step 9.6 신설 섹션에 위 3 카테고리 분류 코드 + 출력 포맷 명시. `grep -E "정합성|미적용|사용자 전용" .claude/skills/harness-upgrade/SKILL.md` hit 3+ 라인
- [x] 사용자 전용 영역 정의 위치 명시 (CLAUDE.md `## 환경`·naming.md 도메인 목록·coding.md 패턴 등 — 기존 SEALED_FOLDERS + 사용자 커스터마이징 보존 원칙과 정합)
- [x] starter_skills 제외 (Step 6.0 STARTER_SKILLS 동일 변수 재사용)
- [x] "그 외 미적용 의심" 항목이 1개 이상이면 사용자 알림 + 파일 목록 표시 + 처리 옵션 제공 (재시도 / 무시하고 계속 / 중단)

### 3. FR-003 — Step 10 완료 보고 silent 제외 카운트 + 정합성 미도달 강조

**사전 준비**: SKILL.md Step 10 라인 721~738 완료 보고 포맷
**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`
**Acceptance Criteria**:
- [x] Goal: 완료 보고 출력에 (a) 사용자 전용 제외 카운트 (b) starter_skills 제외 카운트 (c) upstream 정합성 미도달 카운트가 명시됨. 정합성 미도달이 0 아니면 강조 + 파일 목록 동봉
  검증:
    review: review-deep
    tests: 없음
    실측: SKILL.md Step 10 완료 보고 템플릿에 위 3개 카운트 라인 + "정합성 미도달" 라벨 명시. `grep -E "사용자 전용|미적용|미도달" .claude/skills/harness-upgrade/SKILL.md` hit
- [x] Step 9.6과 데이터 흐름 연결: Step 9.6 카테고리별 카운트가 Step 10 보고에 그대로 전달되는 절차 명시
- [x] 정합성 미도달 0건이면 "✅ upstream 정합성 도달" 한 줄. 1건 이상이면 "⚠ 정합성 미도달: N건" + 파일 목록 + 후속 액션 안내

### 4. 다운스트림 보고 사이클 — MIGRATIONS.md 표준 + 본 wave 보고 요청 박제

**사전 준비**: MIGRATIONS.md `## Feedback Reports` 가이드 절 + 본 WIP `## 다운스트림 보고 요청` 섹션
**영향 파일**: `docs/harness/MIGRATIONS.md` (가이드 갱신), 본 WIP (다음 범프 시 commit 스킬이 사용)
**Acceptance Criteria**:
- [x] Goal: SKILL.md 절차 보강 = 자동 검증 불가 영역. 다운스트림 운용 측정으로만 효과 확인 가능. MIGRATIONS.md 버전 섹션에 "다운스트림 보고 요청" 6번 서브섹션 표준 정의 + 본 wave 보고 요청 항목 3건 사전 박제 ✅
  검증:
    review: review-deep
    tests: 없음
    실측: `grep -nE "다운스트림 보고 요청|버전 섹션 표준" docs/harness/MIGRATIONS.md` hit. 본 WIP `## 다운스트림 보고 요청` 섹션 존재
- [x] MIGRATIONS.md `## Feedback Reports` 절 안에 "버전 섹션 표준" 추가 — 6번 서브섹션 (선택) 정의 + 작성 기준 + 포맷 예시 ✅
- [x] 본 WIP에 `## 다운스트림 보고 요청` 섹션 신설 — 보고 요청 1(Step 5 발화) / 2(Step 9.6 카운트) / 3(Step 10 가독성) 항목 박제. commit 스킬 Step 4가 다음 버전 범프 시 MIGRATIONS.md 새 섹션의 6번에 그대로 복사 ✅
- [x] migration-log.md (다운스트림 소유)가 응답 채널임을 명시 — upstream 읽기만 정책 준수, MIGRATIONS.md 직접 기록 금지 ✅

### 5. FR-006 — Step 9.6 USER_OWNED_FILES 화이트리스트 디렉토리 단위 확장

**사전 준비**: 다운스트림 v0.42.1 적용 측정 보고 FR-006 (총 11건 오분류). SKILL.md Step 9.6 분류 코드 (L738) 확인 — 현재 `naming.md|coding.md|docs.md` 3 파일만 매칭. Step 3 분류 표(L297)는 이미 `coding.md`·`naming.md` + `docs/decisions/*` 등 디렉토리 단위 광범위 정의. **두 정의 불일치가 직접 원인**.
**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md` (Step 9.6 분류 코드 1곳, ~30줄)
**Acceptance Criteria**:
- [x] Goal: Step 9.6 분류가 다운스트림 정당 커스터마이징 영역(rules/* + agents/*)을 USER_OWNED로 정상 분류. v0.42.1 측정의 11건 오분류가 0건으로 차단됨 ✅
  검증:
    review: review-deep
    tests: 없음
    실측: SKILL.md Step 9.6 분류 코드에 `.claude/rules/*` 디렉토리 단위 매칭 + `.claude/agents/*` 디렉토리 단위 매칭이 존재. `grep -nE "rules/\*|agents/\*" .claude/skills/harness-upgrade/SKILL.md` Step 9.6 영역에서 hit. 시뮬레이션: rules 5건 + agents 3건 → USER_OWNED 8건, UNAPPLIED 0건 (FR-006 11건 오분류 → 0건 차단 검증)
- [x] `.claude/rules/*.md` 디렉토리 단위 매칭으로 확장. 단, starter 소유 명백한 rules 파일은 예외 명시 — 본 starter의 `external-experts.md`(런타임 갱신되는 캐시)는 Step 3 SEALED 정의에 부재 + 다운스트림이 자체 관리하므로 USER_OWNED 정합. 별도 예외 불필요 ✅
- [x] `.claude/agents/*.md` 디렉토리 단위 매칭 추가. starter 기본 에이전트(review·debug-specialist 등)도 다운스트림이 customize 대상 — Step 3가 이미 SEALED 영역 외 자유로움을 인정함과 정합 ✅
- [x] false-negative 방어: starter 영역에서 진짜 미적용을 USER_OWNED로 오분류하지 않도록 화이트리스트는 **다운스트림이 정당 변경할 영역**에만 한정. `.claude/skills/*`·`.claude/scripts/*`·`.claude/HARNESS_MAP.md`·`.claude/HARNESS.json`은 제외 (이들은 starter 소유 → 차이 = 진짜 미적용) ✅
- [x] 변경 이력: 본 WIP `## 변경 이력`에 "v0.42.1 → v0.42.2 화이트리스트 확장" 항목 추가 ✅

## 결정 사항

### Phase 1 (FR-001) — base↔ours sanity check
- **반영 위치**: `.claude/skills/harness-upgrade/SKILL.md` Step 5 "본체 swap sanity check (3-way 모드 전용)" 섹션 신설 (라인 396~)
- **검사 1**: frontmatter `name:` 필드 비교 — 다르면 즉시 ALERT (스킬명 변경 = 거의 항상 사고)
- **검사 2**: base ↔ ours 라인 차이율 — `diff --suppress-common-lines | grep -cE '^[<>]'` / `wc -l < base` — 70% 임계
- **3택 처리**: Y(의도된 변경 통과) / N(theirs 강제 교체 + "본체 swap 복구" 카운트) / S(파일 skip + UNAPPLIED_FILES 합류)
- **이유**: 다운스트림 v0.42.0 `eval/SKILL.md`가 `implementation/SKILL.md`로 swap된 채 3회 upgrade 통과한 사례. base와 ours가 거의 완전히 다르면 patch 알고리즘이 ours 그대로 유지 → 충돌 0 통과 → 사고 보존

### Phase 2 (FR-002) — Step 9.6 신설
- **반영 위치**: SKILL.md Step 9.5와 9.7 사이에 Step 9.6 "upstream 정합성 자동 검증" 신설 (라인 699~)
- **검사 범위**: starter 영역 한정 — `.claude/skills`, `.claude/scripts`, `.claude/rules`, `.claude/agents`, `.claude/HARNESS_MAP.md`, `.claude/HARNESS.json`, `docs/harness/MIGRATIONS.md`. apps/web 등 다운스트림 코드 제외
- **3 카테고리**: USER_OWNED_FILES (naming/coding/docs.md 등) / STARTER_SKILL_FILES (Step 6.0 STARTER_SKILLS 변수 재사용) / UNAPPLIED_FILES (그 외)
- **출력**: 미도달 0건 → "✅ 정합성 도달" 한 줄. 1건+ → 파일 목록 + 3택 (sanity check 재실행 / 무시 / 중단)
- **이유**: 다운스트림 v0.42.0에서 30+ 파일이 silent 미적용 통과. Step 5/6/7/8이 "처리한 횟수"만 보고하고 정합성은 검증 안 함

### Phase 3 (FR-003) — Step 10 완료 보고 silent 제외 카운트
- **반영 위치**: SKILL.md Step 10.5 완료 보고 템플릿 + 10.3 migration-log.md 헤더
- **3 카운트 라인 추가**: 사용자 전용 / starter_skills / upstream 정합성 미도달
- **데이터 흐름 명시**: Step 9.6 배열 length를 그대로 주입. 별도 재계산 금지(silent fail 재발 방지)
- **migration-log.md `### 이상 소견`에 UNAPPLIED_FILES 자동 append** (1건+ 일 때만)
- **사용자 전용 표시 정책**: 4개 이하 전체 / 5개+ 요약 + 전체 보기 옵션
- **이유**: 카운트만 보고 "모두 OK"로 보이는 silent fail 패턴 차단

### Phase 5 (FR-006) — Step 9.6 USER_OWNED_FILES 화이트리스트 디렉토리 단위 확장
- **반영 위치**: `.claude/skills/harness-upgrade/SKILL.md` Step 9.6 산문 정의(L720~) + 분류 코드(L747)
- **변경 핵심**: `.claude/rules/naming.md|coding.md|docs.md` 3 파일 매칭 → `.claude/rules/*.md|.claude/agents/*.md` 디렉토리 단위로 확장
- **false-negative 방어 명시**: starter 소유 영역(`.claude/skills/*` 비-starter_skills, `.claude/scripts/*`, `.claude/HARNESS_MAP.md`, `.claude/HARNESS.json`)은 USER_OWNED 분류 금지 — 진짜 미적용으로 간주
- **다운스트림 측정 검증**: FR-006 보고된 11건(rules 5 + agents 3 + starter_skills 3) 시뮬레이션 — 새 분류로 USER_OWNED 8 + STARTER_SKILL 3 + UNAPPLIED 0. 100% 정상 분류 ✅
- **이유**: 직전 wave에서 Step 9.6 분류 코드가 산문 정의보다 좁게 하드코딩됨 (Step 3 분류 표는 이미 디렉토리 단위 광범위). 본 보강이 silent fail의 새 변종(USER_OWNED 오분류로 인한 사용자 피로)을 만든 형태 → P3 영역 그대로

### Phase 4 — 다운스트림 보고 사이클 닫기
- **반영 위치 1**: `docs/harness/MIGRATIONS.md` `## Feedback Reports` 절 안 "버전 섹션 표준 — 다운스트림 보고 요청 서브섹션" 추가 (라인 90~)
- **반영 위치 2**: 본 WIP `## 다운스트림 보고 요청` 섹션 신설 — 본 wave가 다음 버전 범프에 들어갈 때 MIGRATIONS.md 새 섹션의 6번 서브섹션에 그대로 복사
- **소유 정책 정합 확인**: MIGRATIONS.md = upstream 소유 / migration-log.md = 다운스트림 소유. 사용자 지적("다운스트림이 자의적으로 MIGRATIONS.md에 기록")은 실제로 migration-log.md를 가리킨 것 — 정책 정합 확인됨
- **응답 채널**: 다운스트림은 `migration-log.md` `## Feedback Reports` 섹션에 응답. upstream 정책상 MIGRATIONS.md 직접 기록 금지 (라인 13 "upstream 소유 — 다운스트림은 읽기만")
- **본 wave 보고 요청 3건**: (1) Step 5 sanity check 발화 빈도·3택 분포 (2) Step 9.6 정합성 미도달 카운트·사용자 처리 (3) Step 10 보고 강조의 인지 도달 여부
- **이유**: 본 보강은 SKILL.md 절차 변경 = self-verify.md "자동화 불가 검증" 영역. 운용 측정 사이클을 닫지 않으면 P8(자가 발화 의존) 변종으로 박제 위험. 응답 N개 버전 연속 0건이면 보강 실효성 재검토 트리거

## 다운스트림 보고 요청 (다음 MIGRATIONS.md 버전 섹션에 박을 항목)

본 wave는 SKILL.md 절차 보강이라 starter 측 자동 검증 불가. 다운스트림이
다음 upgrade 후 운용에서 다음을 관찰해 `migration-log.md` `## Feedback
Reports`에 응답해주세요. 응답 0건이 N개 버전 연속이면 starter는 본 보강의
실효성 재검토.

### 보고 요청 1 — Step 5 본체 swap sanity check 발화 빈도

본 보강 적용 후 첫 upgrade에서:
- 검사 1(`name:` 필드 변경 ALERT) 발화 횟수: ___건
- 검사 2(차이율 ≥70% 의심) 발화 횟수: ___건
- 사용자 3택 결과 분포: Y(통과)=__ / N(theirs 강제)=__ / S(skip)=__

**왜 묻는가**: 본 검사는 다운스트림 v0.42.0 `eval/SKILL.md` swap 사례에서
출발. 임계 70% + `name:` 필드가 실제 swap 사고를 잡는지 / false-positive
가 빈발하는지 측정 필요.

### 보고 요청 2 — Step 9.6 정합성 미도달 카운트

본 보강 적용 후 첫 upgrade에서:
- USER_OWNED_FILES (제외): ___개
- STARTER_SKILL_FILES (제외): ___개
- UNAPPLIED_FILES (정합성 미도달): ___개
- 미도달 1건+ 시 사용자 선택: 재실행=__ / 무시=__ / 중단=__

**왜 묻는가**: starter는 다운스트림 환경의 정확한 차이를 모름. 30+ 미도달이
관찰 (v0.42.0)되었으나 본 보강 적용 후 실제 카운트와 사용자 처리 패턴은
다운스트림 측정으로만 확인 가능.

### 보고 요청 3 — Step 10 보고 가독성 + 자가 발화 의존 잔존 여부

본 보강 적용 후 첫 upgrade 보고 출력에서:
- "정합성 미도달" 강조가 사용자 인지에 도달했는가: 예/아니오/무관 (0건)
- 사용자가 보고를 보고 추가 액션을 취했는가: 예/아니오
- silent 제외 카운트(사용자 전용 N개)가 "이게 진짜 보존 맞나?" 검토를
  유발했는가: 예/아니오

**왜 묻는가**: P8 자가 발화 의존 패턴이 본 보강에도 남아 있을 수 있음.
강조 출력이 실제 인지로 이어지는지 측정 필요.

응답 형식: `migration-log.md` 본 버전 섹션의 `## Feedback Reports` 안에
`### FR-NNN — silent fail 보강 측정 결과` 형태로 답변. 항목별 측정값 +
관점·약점·실천 (FR 표준 포맷).

## Phase 6 (FR-X1) — Step 11 false positive 축소 (v0.47.6)

- **반영 위치**: `.claude/skills/harness-upgrade/SKILL.md` Step 11 본문 + 분류 코드 (재번호 9.6→11 동반 적용)
- **다운스트림 v0.42.7→v0.47.4 측정**: UNAPPLIED 18건 중 14건 false positive (78%). 진짜 미적용 신호가 noise에 묻힘
- **변경 1 — upstream 부재 → USER_OWNED 재분류**: `.claude/skills/*`·`.claude/scripts/*` 중 `git log UPSTREAM_REF -- <path>` hit 0건이면 다운스트림 전용 자산 → USER_OWNED로 분류. hit 있으면 (upstream에서 삭제됨) UNAPPLIED 유지
- **변경 2 — untracked 파일 별 카테고리**: `git ls-files --others --exclude-standard`로 Step 6 신규 추가 파일 사전 수집 → `STAGED_PENDING_FILES` 별 배열로 처리. "deleted from HEAD" 오표시 차단
- **분류 결과**: 3 카테고리(USER_OWNED·STARTER_SKILL·UNAPPLIED) → 4 카테고리 (STAGED_PENDING 추가)
- **시뮬레이션**: 다운스트림 측정 18건 → USER_OWNED 11건(다운스트림 전용 재분류) + STAGED_PENDING 3건(untracked) + UNAPPLIED 4건(진짜 미적용 의심). false positive 14건 차단
- **이유**: 본 보강이 Phase 5와 동일 패턴 — 분류 코드가 산문 정의보다 좁아 false positive 발생. 정합성 노이즈가 silent fail 변종 (진짜 신호 묻힘)을 만들어 P3 본질 유지
- **P11 동형 잠복 후보 (별 wave)**: 본 wave 결함 패턴 "분류 코드가 산문 정의와 어긋남"의 동형 후보 — pre_commit_check.py SEALED 면제 분류, docs_ops.py cluster abbr 파싱, SKILL.md Step 3 SEALED_FOLDERS. 본 wave 스코프 외, P11 정련 wave로 분리

## 변경 이력

### v0.47.6 (2026-05-15) — Phase 6 추가 (FR-X1 후속) + Step 재번호
- 다운스트림 v0.42.7→v0.47.4 적용 측정 보고 FR-X1 수신 — Step 9.6 false positive 78%
- Step 11(구 9.6) 분류 코드에 upstream 부재 판정 + untracked 처리 추가
- Step 번호 체계 정수화: 9.5→10, 9.6→11, 9.7→12, 10→13 (사용자 요청)
- problem frontmatter `P3` → `[P3, P11]` 확장 (P11 동형 잠복 본질 박제)

### v0.42.2 (2026-05-10) — Phase 5 추가 (FR-006 후속)
- 다운스트림 v0.42.1 적용 측정 보고 FR-006 수신 — Step 9.6 USER_OWNED_FILES 화이트리스트가 너무 좁아 11건 오분류
- Step 9.6 분류 코드를 `.claude/rules/*.md|.claude/agents/*.md` 디렉토리 단위로 확장
- false-negative 방어 명시 — starter 소유 영역(skills 비-starter_skills, scripts, HARNESS_MAP, HARNESS.json)은 USER_OWNED 분류 금지

### v0.42.1 (2026-05-10) — 초기 버전 (FR-001/002/003 + Phase 4)
- Step 5 base↔ours sanity check (frontmatter `name:` + 차이율 70%)
- Step 9.6 정합성 자동 검증 신설 (3 카테고리 분류)
- Step 10 완료 보고 silent 제외 카운트
- MIGRATIONS.md 6번 서브섹션 표준 + 본 wave 보고 요청 박제

## CPS 갱신
- P3 본문 변경 없음 (Solution 충족 기준에 부합하는 알고리즘 보강)
- S3 5중 방어 본체 변경 없음. 본 wave는 S3 메커니즘 자체 강화 (각 단계 실효성 보강)이며 Solution 정의 변경 아님 → owner 추가 승인 불필요
- Phase 5도 동일 — Solution 정의 변경 아님. 본 보강의 분류 정확도 결함 수정

## 메모
- doc-finder fast+deep scan 완료 (2026-05-10). 핵심 사료: SKILL.md Step 5/9/10, hn_upgrade.md, hn_sealed_migrations_exempt_gap.md
- CPS 매칭: 사용자가 P7 제시했으나 P3가 정확. defends-by가 harness-upgrade 본인이라 정합. P7은 부수적 (upstream-downstream 관계 투명성)
- 다운스트림 eval/SKILL.md 본체 swap 복구 자체는 본 wave 스코프 외 — 다운스트림 측 수동 작업 (`git checkout harness-upstream/main -- .claude/skills/eval/SKILL.md`)
- Solution 메커니즘 자체 변경이라 owner 승인 필요 영역 — 본 wave는 SKILL.md 절차 보강(메커니즘 강화)이며 S3 충족 기준 변경은 아님. owner 추가 승인 없이 진행 가능
- Phase 4는 사용자 지적("다운스트림에서 받아서 실행하고 보고할 내용 언급")으로 추가. 본 보강이 자동 검증 불가 영역이라 운용 측정 사이클 닫기가 필수. 사용자 후속 지적("MIGRATION-log.md 파일이네")으로 소유 정책 정합 확인 — 다운스트림은 migration-log.md(다운스트림 소유)에 응답, MIGRATIONS.md(upstream 소유)는 가이드만 박제
- Phase 5는 다운스트림 v0.42.1 적용 측정에서 FR-005/006으로 받음. FR-005(sanity check 발화 0건)는 사용자 선제 복구로 입력 부재 — 측정 공백, 별 wave (negative-test 픽스처)로 분리. FR-006(11건 오분류)는 정합성 검증 분류 정확도 결함 — 본 wave에서 즉시 처리. 사용자 결정: "FR-006 화이트리스트 확장만 먼저"
- doc-finder fast scan (Phase 5): USER_OWNED_FILES SSOT 단일 (Step 9.6 한 곳) — 분산 없음 안전한 단일 변경. `.harness-overrides.md` 마커는 코드 메커니즘 미존재, v0.42.0 MIGRATIONS.md에 한 차례 언급만 — 본 wave 스코프 외
