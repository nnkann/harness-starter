---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-04-28
---

# 다운스트림 마이그레이션 가이드

`harness-upgrade` 스킬이 각 버전 업그레이드 시 이 문서를 읽어 다운스트림에
표시한다. **upstream 소유 — 다운스트림은 읽기만.**

**최신 5개 버전 본문만 유지** (v0.30.1 정책). 6번째 이전 버전은
`MIGRATIONS-archive.md`로 자동 이동 — `harness_version_bump.py --archive`가
이동 처리. 더 오래된 업그레이드 추적은 archive 또는 git log
(`git log --oneline --grep "(v0\."`).

다운스트림은 자기 환경 마지막 upgrade 이후 누적된 버전을 읽으면 된다.
5개 본문 기준 약 1~2개월 분량. 그보다 오래 누적된 다운스트림은 archive
참조.

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

## Feedback Reports — 다운스트림 → upstream 피드백 채널

업그레이드 후 운용 중 발견한 구조적 관찰·약점·개선 제안을 upstream에 전달하는
규격화된 채널. `migration-log.md`의 별도 섹션으로 작성한다.

**upstream이 이 채널을 통해 기대하는 것**: 다운스트림 환경에서만 보이는
사일런트 페일, 규칙 우회 패턴, 문서 부재 등 — upstream 격리 환경에서는
발견할 수 없는 피드백.

### 포맷 (항목당 1개)

```markdown
## Feedback Reports

### FR-001 (YYYY-MM-DD)

**관점**: <!-- 어떤 측면을 분석했는가 (1줄) -->

**약점**:
<!-- 발견된 문제·헛점·위험. 증상 + 영향 포함 -->

**동형 후보 위치** (선택, P11 인지 시):
<!-- 본 발견의 동형 패턴이 잠복할 가능성 있는 다른 위치 1~3개 -->
- 가능성 1: <위치> — <왜 잠복할 수 있는가>
- 가능성 2: <위치> — ...

**실천**:
<!-- 구체적 개선 방향. "~해야 한다" 형식 -->

**심각도**: low | medium | high
**관련 CPS**: P# (해당 시)
```

### 작성 규칙

- 항목 번호: `FR-NNN` 순차 증가 (프로젝트 내 전역)
- **관점**: 1줄 요약. "어느 레이어·어느 컴포넌트를 봤는가"
- **약점**: 추측 금지. 실측 또는 재현 가능한 시나리오만
- **동형 후보 위치** (선택): P11(동형 패턴 잠복) 인지 시 1차 발견 외 다른
  위치 후보 1~3개 동반 제안. starter가 본 항목을 본문 grep 대상에 자동 합류.
  "동형 가능성 없음"으로 판단하면 섹션 생략. 추측만으로 채우지 마라
- **실천**: "더 잘 해야 한다" 수준 금지. 구체 행동 또는 구체 파일명 제시
- **심각도**: `high` = upstream이 다음 버전에서 반드시 처리, `medium` = 권장, `low` = 참고
- 미작성(`없음`)도 명시 — 빈 섹션보다 "없음" 한 줄이 낫다

### 버전 섹션 표준 — "다운스트림 보고 요청" 서브섹션

각 버전 섹션은 다음 6개 서브섹션으로 구성된다 (선택적인 6번 추가):

1. **변경 내용** (필수)
2. **자동 적용 항목** (필수)
3. **수동 적용 항목** (필수 — `없음` 명시 가능)
4. **검증** (필수)
5. **회귀 위험** (필수 — `없음` 금지, "관찰 범위 내" 명시)
6. **다운스트림 보고 요청** (선택) — upstream이 본 변경에 대해 다운스트림에서
   특별히 관찰·수신을 기대하는 항목. 자가 발화 의존을 줄이는 능동 채널.

**6번 작성 기준**:

- 본 버전 변경이 "자동 검증 불가 — 운용 행동 변화"를 수반할 때만 작성
- 다음 upgrade 시 다운스트림이 `migration-log.md` `## Feedback Reports`에
  답할 수 있도록 **구체 관찰 질문** 형식
- 항목 1~3개. 많으면 다운스트림이 응답 안 함 (P8 자가 의존 한계)

**포맷 예시**:
```markdown
### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **<관찰 항목>**: <구체 질문 또는 측정 명령>
   - 응답 예: "N건 발생 / 0건 / 미관측"
2. **<관찰 항목>**: ...
```

응답 없이 다음 upgrade 통과해도 차단 아님 — 누적 패턴 자체가 데이터.
upstream은 응답 0건이 N개 버전 연속이면 본 보강의 다운스트림 적합도 재검토.

### eval --harness 검증 항목

`eval --harness` 실행 시 migration-log.md의 Feedback Reports 포맷을 검증한다:

- FR 항목이 있을 때: `관점`·`약점`·`실천`·`심각도` 4개 필드 모두 존재하는지 확인
- 필드 누락 시: `⚠️ FR-NNN: [누락 필드] 없음` 경고
- FR 항목이 없을 때: `피드백 리포트: 없음 ✅` 통과

---

## v0.48.0 — P11 본질 재정렬 (SSOT 인용 원칙 + CPS 채널 활성화) (2026-05-17)

### 변경 내용

v0.47.7~v0.47.12 P11 사이클이 `_DEAD_REF_PATTERNS` hardcoded list 누적
사이클로 빠지려던 순간, 사용자 통찰로 본 메커니즘의 진짜 본질로 복귀:

> "SSOT 호출과 더불어 그 내용이 희석되지 않고 내가 원하는 단계까지 전달이
> 안된다가 문제의 핵심" / "이 관계를 정의하고 있는게 cps잖아?"

**문제 진단**: 본문이 SSOT의 구체 list(`4종 (X·Y·Z·W)`·`--quick/--harness/
--surface/--deep 4모드`)를 **복제** → SSOT 갱신 시 본문 drift → P11 잠복.
`_DEAD_REF_PATTERNS` 누적은 cluster-update hardcoded 표 답습(v0.47.5에서
폐기 결정한 패턴 재발).

**해결 — 새 메커니즘 X, CPS 채널 활성화**:
- CPS `rel: references`가 이미 SSOT 인용 그래프 박제 메커니즘
- `verify-relates` 도구가 이미 cascade 추적 게이트
- 본문이 복제 대신 SSOT 링크로 박으면 drift 0

**A. `rules/docs.md` "SSOT 인용 원칙" 신설** (defends P11):
- 본문 복제 금지 + `rel: references` 권장 + 적용 범위 박제
- "본문 인용 금지: 구체 list" / "본문 인용 허용: 1줄 요약·맥락"
- 도구 안내: `verify-relates`·`section_dead_reference`·SSOT 원칙 3축

**B. 본문 복제 9곳 → SSOT 링크 전환**:
- `README.md`: eval 폐기 모드(`--surface`·`--deep`) 줄 제거,
  "relates-to 4종" → "rel 타입 정의는 rules/docs.md SSOT"
- `agents/advisor.md`·`threat-analyst.md` description: TRIGGER에서 폐기된
  `eval --deep` 참조 줄 삭제 (description은 매 LLM 호출 시스템 프롬프트
  적재라 영향 큼)
- `skills/advisor/SKILL.md` L43 "eval --deep 2차 검증" 행 삭제
- `skills/harness-init/SKILL.md` L83 "`--quick`/`--deep`/`--no-review`" →
  `/commit --review`/`--no-review` 2단계 박제로 교체
- `skills/harness-init/SKILL.md` L347 `rel: implements` → `rel: extends`
- `rules/security.md` L42·48 "eval --deep" → "eval --harness"

**C. `_DEAD_REF_PATTERNS` 본문 표현 등록 시도 폐기**:
- 직전 단계에서 추가했던 `/eval --surface`·`/eval --deep`·`rel: implements`
  등을 list에서 제거 — hardcoded 누적 사이클 차단
- 사상: 본문 표현은 SSOT 인용 원칙으로 차단, 파일/경로만 hardcoded 유지
  (git tree와 1:1 매핑이라 SSOT 자기 일치)

### 영향

- 매 LLM 호출 시스템 프롬프트에 적재되는 agents description의 dead
  reference 제거 — LLM이 폐기 모드 인지 0
- README·SKILL 본문이 SSOT 링크로 박혀 미래 SSOT 갱신 시 drift 0
- `_DEAD_REF_PATTERNS` list가 증식 사이클 중단 — 본문 표현 단속은 SSOT
  원칙으로 이양

### 다운스트림 영향

- agents description 변경 (advisor·threat-analyst) — 3-way merge로 흡수
- rules/docs.md "SSOT 인용 원칙" 박제 — 다운스트림 SKILL·본문 작성 가이드
- harness-init 템플릿 `rel: implements` → `rel: extends` 정합
- 다운스트림 본문에 `eval --deep`·`rel: implements` 잔재 있어도 본 wave
  game은 차단 안 함 (본문 표현 단속 폐기 — SSOT 원칙으로 자율 정비)

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 `migration-log.md` `## Feedback Reports`에 응답:

1. **SSOT 인용 원칙 인지**: 다음 wave에서 본문 작성 시 복제 대신 SSOT 링크
   박제가 자연스러웠는지 (자가 발화 없이 원칙 적용 가능했는지)
2. **rel: references 그래프 활용**: 새 문서 작성 시 `relates-to: rel: references`
   사용 빈도 (1차 발견 vs 동형 후보 탐색에 활용했는지)

---

## v0.47.12 — AC 헤더 차단 메시지에 auto-fix sed 안내 추가 (2026-05-16)

### 변경 내용

다운스트림 보고 동반 관찰 1건 (AC 헤더 `##` vs `**bold**` auto-fix 부재,
medium) 흡수. **auto-fix 자동 실행은 추가 안 함** — 빈도(wave당 1회) +
우연 변환 위험 대비 효익 작음.

**pre_commit_check.py L904 차단 메시지 보강**:
- 기존: "`### Acceptance Criteria` 헤더 형식은 인식하지 않습니다." 1줄
- 추가: `auto-fix: sed -i 's/^#\+\s*Acceptance Criteria.*$/**Acceptance Criteria**:/' {wip}`

사상: dead-ref 게이트의 `auto-fix: docs_ops.py tag-normalize` 패턴 정합 —
"결정적 차단 + 복붙 가능 fix 명령".

### 영향

- 다운스트림이 AC 헤더 형식 위반 차단 시 복붙 1회로 해결
- 자동화 아니지만 학습 곡선 + 수동 sed 작성 시간 제거
- starter·다운스트림 동일 효과 (메시지 출력 차이 없음)

### 다운스트림 보고 응답

FR 동반 관찰 1번 (AC 헤더 auto-fix 부재, medium):
- 본 wave로 medium → low 강등
- 자동 실행이 아니라 복붙 fix 안내라 false positive 위험 0

---

## v0.47.11 — P11 게이트 안전망 보강 (false positive 차단 + 다운스트림 격리) (2026-05-16)

### 변경 내용

v0.47.10 P11 결정적 게이트 승격 직후 사용자 우려로 재검증 → 위험 2건 식별
후 즉시 보강. 다운스트림 적용 전 안전망 보장.

**Patch A — `_DEAD_REF_PATTERNS` false positive 차단** (eval_harness.py):
- `staging.md` 단순 basename → `rules/staging.md` 경로 prefix화
- 이유: `staging.md`는 배포 staging 환경 등 일반 단어와 충돌 가능. 다운스트림
  `docs/staging.md` 같은 무관 파일이 false positive로 차단되는 위험 회피
- 검증: 일반 `staging.md` 0건 매칭, `rules/staging.md` 1건 정상 매칭

**Patch B — 다운스트림 격리** (pre_commit_check.py §3.6):
- `HARNESS.json` `is_starter` 분기 추가
- `is_starter: true` (starter): `❌` + ERRORS++ → commit 차단 (결정적 게이트)
- `is_starter: false` (다운스트림): `⚠` + commit 진행 → warn-only
- 이유: starter 폐기 파일명 list가 다운스트림 본문과 우연 충돌 시 작업
  마비 방지. 다운스트림은 alert 받고 자기 일정으로 정비
- 다운스트림 출력 끝에 `ℹ️ 다운스트림 모드 — commit 진행 가능. 정비 일정은
  자율 결정.` 안내

### 영향

- starter: 게이트 동작 동일 (차단 유지)
- 다운스트림: alert 받지만 commit 안 막힘 — 정비를 자기 wave로 처리
- false positive 패턴 1건 정밀화 (`rules/staging.md` 경로 한정)

### 다운스트림 영향

- 다운스트림이 폐기 파일 본문 잔재를 staged할 때 차단 대신 경고 표시
- 정비 일정은 다운스트림 자율 (긴급 작업 중에도 commit 가능)
- 안내 메시지로 정비 필요 인지 + harness-dev Step P1~P5 참조

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 `migration-log.md` `## Feedback Reports`에 응답:

1. **warn-only 안내 발생 빈도**: 본 게이트가 warn-only로 출력한 commit 수
   (다운스트림 잠재 잔재 누적 측정)
2. **false positive 제로 검증**: `rules/staging.md` prefix화 후 무관 파일이
   잘못 매칭된 사례 있는지

---

## v0.47.10 — P11 결정적 게이트 승격 + FR 양식 동형 후보 + eval_cps_integrity P11 카운트 버그 (2026-05-16)

### 변경 내용

다운스트림 StageLink가 v0.47.9 운용 후 3건 FR(X10·X11·X12) 보고. 핵심:

- **FR-X11 (성공 보고)**: v0.47.9 항목 9 첫 호출에서 7건 검출 — 도구 ROI 100%
- **FR-X12 (medium)**: 절차 자체의 P11 유발 — pre-check 게이트 승격 권장(옵션 B)
- **FR-X10 (medium)**: FR 양식에 "동형 후보 위치" 서브섹션 추가

starter eval 부수 발견: **eval_cps_integrity P11 카운트 0건** (실측 5건 인용) —
list 형식 frontmatter + 두자리수 정규식 누락 합산 버그.

**A. pre-check dead reference 게이트 승격** (FR-X12 옵션 B):
- `pre_commit_check.py` §3.6 신설 — staged diff에 폐기 파일 패턴 등장 시
  `eval_harness.scan_dead_reference_paths` 직접 호출
- 1건 이상이면 commit 차단 + 정비 안내
- 사상: v0.47.7 commit_finalize wrapper 흡수와 동일 — "LLM 책임 → 도구 책임"
- `eval_harness.py`: `section_dead_reference` 내부 로직을 `scan_dead_reference_paths`
  공개 함수로 분리 (pre-check 재사용)

**B. FR 양식 "동형 후보 위치" 서브섹션** (FR-X10):
- MIGRATIONS.md `## Feedback Reports` 포맷 SSOT 갱신
- 다운스트림이 1차 발견 시 starter가 동형 grep 대상에 자동 합류
- 선택적 — P11 인지 시만 작성, 추측만으로 채우지 마라

**C. eval_cps_integrity P11 카운트 버그 수정**:
- `CPS_REF_PATTERNS` 4개 정규식 `\b(P\d)\b` → `\b(P\d+)\b` (P10·P11 캡처)
- `scan_doc` frontmatter `problem` 파싱: str 형식만 처리 → str + list 모두
  처리 (`problem: [P7, P11]` 인식)
- 결과: P11 0건 → 5건, P7 17건 → 21건 정상화

### 영향

- 다운스트림이 폐기 파일 본문 잔재를 staged 시점에 결정적 차단 — 매 commit
  pre-check이 자동 실행 (도구 실행 누락 위험 0)
- FR 양식에 동형 후보 위치 박제 가능 — P11 메커니즘 채널 활성화
- eval_cps_integrity 카운트 정확도 회복 — 본 wave가 첫 검증 사례

### 다운스트림 영향

- pre-check이 폐기 파일 staged 시 차단 — 다운스트림 본문에 잔재 있으면
  다음 commit부터 차단 메시지 표시 + 정비 안내
- FR 양식 갱신은 다운스트림 `migration-log.md` 작성 시 참조용
- eval_cps_integrity 패치는 다운스트림 P11 인용 누락 카운트 정상화

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 `migration-log.md` `## Feedback Reports`에 응답:

1. **pre-check dead-ref 차단 발생 횟수**: 운용 중 staged 시점 차단된 commit
   수 (도구 ROI 측정)
2. **동형 후보 위치 서브섹션 활용**: 다음 FR 작성 시 P11 인지 후 동형 위치
   제안 가능했는지 (1차 발견 외 grep 대상 자동 합류 효과)
3. **eval_cps_integrity P# 카운트 정합**: 다운스트림 자체 P10·P11 인용 문서가
   카운트에 정상 잡히는지

---

## v0.47.9 — P11 첫 누적 case + dead reference 일괄 정비 + 구조적 재발 방지 (2026-05-16)

### 변경 내용

다운스트림 StageLink가 v0.47.8 upgrade 후 dead reference 정비 wave에서
`harness-upgrade SKILL.md L580` 1건 보고 → starter 본인 권장 grep 실행 시
README에 6건 추가 잠복 발견. **P11(동형 패턴 잠복) 직격 사례 + 첫 누적 case
박제**.

**A. dead reference 7건 일괄 정비**:
- `.claude/skills/harness-upgrade/SKILL.md` L580-581: 폐기 파일 예시
  `anti-defer.md`·`orchestrator.py` → placeholder `<deprecated-rule>.md`·
  `<deprecated-script>.py` (옵션 A: 미래 폐기 사이클에도 안정)
- `README.md` rules 트리: external-experts·pipeline-design·staging.md 폐기
  3건 줄 제거 (12개 → 9개)
- `README.md` skills 트리: doc-health/·check-existing/ 폐기 2건 줄 제거
  (14개 → 12개)
- `README.md` L47: self-verify "pipeline-design 체크리스트 연계" 안내 정정
- `README.md` "Review 자동 단계화" 섹션: staging.md 폐기 박제로 교체
  (5줄 룰·13신호 → `/commit --review`/`--no-review` 2단계)

**B. eval_harness.py 항목 9 dead reference 검사 신설**:
- 폐기 파일 패턴(`anti-defer.md`·`orchestrator.py` 등 10개) staged 본문 grep
- 박제 표현(`폐기`·`흡수`·`삭제`·`removed`·`deprecated`·MIGRATIONS·`회고`)
  정규식 면제로 false positive 차단
- 회귀 보호: `@pytest.mark.eval` 3건 신규 (총 17 passed)

**C. harness-dev SKILL.md 폐기 절차 Step P1~P5 신설**:
- 파일 삭제 시 본문 전수 grep 의무화 (Step P2)
- 정비 옵션 표(placeholder·줄 제거·실재 항목 대체) 박제 (Step P3)
- eval_harness 회귀 확인 + `_DEAD_REF_PATTERNS` 등록 (Step P4·P5)

### 영향

- LLM이 매 세션 시스템 프롬프트 로드 시 dead reference 안내 제거 → 폐기 스킬
  안내 노이즈 0
- 다운스트림 다음 upgrade 시 SKILL.md 본문 dead reference 자동 흡수
- 폐기 commit이 본문 정비 없이 closing되는 시나리오 결정적 차단

### 다운스트림 영향

- harness-upgrade L580 예시 변경 → 다운스트림 3-way merge 시 theirs 자동 적용
- 다운스트림 자체 작성한 SKIP 결정 박제(예: `hn_dead_ref_cleanup_v0_47.md`)는
  영향 없음 — 본 변경이 다운스트림 작성 문서를 건드리지 않음

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 `migration-log.md` `## Feedback Reports`에 응답:

1. **dead reference 검출 카운트**: 다운스트림 본문에 폐기 파일 잔재가 얼마나
   잠복하고 있었는지 (`eval --harness` 항목 9 출력)
2. **harness-dev Step P 운용 실효**: 다음 폐기 wave에서 Step P1~P5가 자가 의존
   없이 절차 수행 가능했는지

