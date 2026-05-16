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

**실천**:
<!-- 구체적 개선 방향. "~해야 한다" 형식 -->

**심각도**: low | medium | high
**관련 CPS**: P# (해당 시)
```

### 작성 규칙

- 항목 번호: `FR-NNN` 순차 증가 (프로젝트 내 전역)
- **관점**: 1줄 요약. "어느 레이어·어느 컴포넌트를 봤는가"
- **약점**: 추측 금지. 실측 또는 재현 가능한 시나리오만
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

## v0.47.7 — docs/harness cascade 화이트리스트 좁힘 + 회고 잔재 자동 정리 + commit_finalize wrapper 흡수 (2026-05-16)

### 변경 내용

starter 내부 회고 문서가 다운스트림에 cascade되던 결함을 원천 차단 + commit 흐름의 자가 발화 의존 1건 wrapper 흡수.

**docs/harness cascade 화이트리스트 좁힘** (harness-upgrade Step 3):
- 옛 정의: "하네스 파일 범위"에 `docs/harness` 통째 포함 → starter 내부 회고(`hn_*.md`) 38건이 다운스트림 docs/harness/로 따라감
- 새 정의: `docs/harness/MIGRATIONS.md docs/harness/MIGRATIONS-archive.md` 명시 2건만
- **opt-in 화이트리스트** — 새 `hn_*.md` 추가돼도 자동 제외, 별도 등록·결정 불필요
- 다운스트림이 알아야 할 건 "이번 변경 내용"(MIGRATIONS) 한정. 히스토리는 starter에만 박제

**Step 7 (C) starter 회고 잔재 자동 정리** (신설):
- 옛 버전에서 이미 cascade된 hn_* 잔재 회수 메커니즘
- 판정: `git cat-file -e $UPSTREAM_REMOTE/main:<path>` hit → upstream 존재 = starter 회고 잔재 → 자동 삭제
- 다운스트림 자체 작성 hn_* 문서는 upstream 부재로 자동 보존 (false-positive 차단)
- (A) DELETED + (B) starter_skills 격하 + (C) starter 회고 — 3축 정리 통합

**commit_finalize.sh session snapshot 자동 정리** (wrapper 흡수):
- 옛 흐름: commit 스킬 Step 8이 LLM에게 `rm -f .claude/memory/session-*.txt` 자가 발화 의존 (P8 패턴)
- 권한 분류기 잔향·LLM 누락 시 흔적 잔존 결함 발생 (2026-05-16 실측)
- 새 흐름: `commit_finalize.sh`가 `git commit` 성공 시 직접 정리. LLM 책임 0
- commit 스킬 Step 8 본문은 "wrapper 자동 처리" 1줄로 단순화

### 영향 파일

- `.claude/skills/harness-upgrade/SKILL.md` (Step 3 화이트리스트 + Step 7 (C) 신설)
- `.claude/scripts/commit_finalize.sh` (commit 성공 시 session snapshot 정리)
- `.claude/skills/commit/SKILL.md` (Step 8 본문 단순화)

### 자동 적용

- HARNESS.json version → 0.47.7
- harness-upgrade 다음 실행 시:
  - Step 3 화이트리스트로 신규 hn_* cascade 자동 차단
  - Step 7 (C)가 기존 hn_* 잔재 자동 삭제 + 알림
- commit_finalize wrapper는 다음 commit부터 자동 정리

### 수동 확인 권장

- (C) 격하 정리 알림 출력 시 starter 회고 파일 목록 검토 — 다운스트림 자체 작성 파일이 우연히 같은 이름이면 false-positive 가능성 (upstream에 같은 이름 파일이 있다면 삭제됨). 본 starter의 38건은 전부 `hn_` prefix + starter 고유 슬러그라 충돌 가능성 낮음. 우려되면 첫 upgrade는 dry-run 검토 후 실행
- session snapshot 자동 정리는 `git commit` 성공 시만 동작 (실패 시 보존 — 디버깅용)

### 회귀 위험

- Step 3 화이트리스트 좁힘은 **명시 2개 라인 변경**만 — `docs/harness` 통째에서 2건 명시로. 다운스트림 첫 upgrade 시 (C)가 38건 삭제 알림 표출 (대량). 사용자 인지 부담 가능 — 알림 메시지에 "starter 내부 회고 — 다운스트림 미전파" 라벨로 명확화
- commit_finalize 변경은 `exit "$COMMIT_RC"` 추가 — 기존 묵시적 0 종료에서 명시 종료로. wrapper 호출자가 exit code 검사하면 동일 동작

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 다음을 측정해 `migration-log.md` `## Feedback Reports`에 응답:

1. **Step 7 (C) 격하 대상 카운트**: 다운스트림에 누적된 starter 회고 hn_* 파일 수 (보통 30~40건 예상)
2. **false-positive 발생**: (C)가 다운스트림 자체 작성 hn_* 문서를 잘못 삭제한 사례 있는지
3. **session snapshot 잔재**: commit 후 `.claude/memory/session-*.txt` 잔존 0건인지 확인

---

## v0.47.6 — Step 11 false positive 축소 (FR-X1) + tag-normalize 도구 (FR-X2) + Step 재번호 + P11 신규 (2026-05-16)

### 변경 내용

다운스트림 v0.42.7→v0.47.4 적용 보고에서 받은 FR-X1·X2 두 축 + 사용자 요청 Step 번호 정수화 + 본질 박제 P11 신규.

**FR-X1 — Step 11 (구 Step 9.6) false positive 축소**:
- 다운스트림 측정: UNAPPLIED 18건 중 14건 false positive (78%) — 진짜 미적용 신호가 noise에 묻힘
- 분류 코드에 (a) `git log UPSTREAM_REF -- <path>` hit 0건 = upstream 부재 → USER_OWNED 재분류 (b) `git ls-files --others`로 untracked 신규 파일 사전 수집 → `STAGED_PENDING_FILES` 별 카테고리
- 3 카테고리(USER_OWNED·STARTER_SKILL·UNAPPLIED) → 4 카테고리 (STAGED_PENDING 추가)
- 시뮬레이션: 18건 → USER_OWNED 11(다운스트림 전용) + STAGED_PENDING 3(untracked) + UNAPPLIED 4(진짜 미적용 의심). false positive 14건 차단

**Step 번호 정수화 (사용자 요청)**:
- `Step 9.5 → 10` (마이그레이션 액션 표시)
- `Step 9.6 → 11` (upstream 정합성 검증)
- `Step 9.7 → 12` (수동 액션 완료 확인)
- `Step 10 → 13` (완료 처리)
- SKILL.md 본문 + 내부 참조 + README.md 살아있는 진입점만 갱신. completed 결정 문서(7개)는 박제 본질 보존

**FR-X2 — tag 정규식 누적 부채 auto-fix 도구**:
- 다운스트림 측정: 7개 문서 tag 정규식 위반 (대문자·언더바·한글) — v0.47.1 정규식 도입 전 작성 문서들. 다음 수정 시 즉시 차단
- `docs_ops.py tag-normalize` 서브커맨드 신설:
  - `normalize_tag()` 결정적 변환 (camelCase·언더바·대문자·비허용·중복 dedup)
  - 한글 포함 tag는 자동 변환 거부 (`None` 반환) — 사용자 영문 매핑 필수
  - `--apply` 플래그(기본 dry-run), `--yes` 비대화형
- `pre_commit_check.py` tag 위반 차단 메시지에 `auto-fix: ... tag-normalize <wip> --apply` 한 줄 안내 추가
- `test_tag_normalize.py` 15케이스 통과

**P11 신규 등록**:
- "동형 패턴 잠복 — 1차 발견 시 다른 위치 후보 자동 탐색 부재"
- 사용자 본질 발화: "하나의 증상을 찾았는데 이게 다른 곳에서도 동일하게 있을 수 있다"
- P7(관계 불투명)과 직교 — P7은 *구조* 관계(wiki 그래프), P11은 *동형 패턴* 관계
- S11 정의는 별 wave에서 정련 (현재는 본질만 박제)
- 본 wave 결정 문서들이 P11 동형 잠복 후보를 메모로 박제 (`hn_upgrade_silent_fail_guards.md` Phase 6 + `hn_doc_naming.md` 변경 이력)

### 영향 파일

- `.claude/skills/harness-upgrade/SKILL.md` (Step 11 분류 로직 + 4 헤더 재번호 + 내부 참조)
- `.claude/scripts/docs_ops.py` (`normalize_tag` + `cmd_tag_normalize` + dispatch + USAGE)
- `.claude/scripts/pre_commit_check.py` (tag 차단 안내 1줄)
- `.claude/scripts/tests/test_tag_normalize.py` (신규 15케이스)
- `README.md` (Step 번호 2곳)
- `docs/guides/project_kickoff.md` (P11 1줄 추가)
- `docs/decisions/hn_upgrade_silent_fail_guards.md` (Phase 6 박제, problem `[P3, P11]`)
- `docs/decisions/hn_doc_naming.md` (변경 이력 + v0.47.6 wave AC + problem `[P7, P11]`)

### 자동 적용

- HARNESS.json version → 0.47.6
- SKILL.md Step 11 분류 코드는 다운스트림 다음 upgrade 시 자동 적용 (3-way merge)
- pre-check tag 위반 안내는 다음 commit부터 자동 표시

### 수동 확인 권장

- 다운스트림 누적 tag 위반 문서 점검: `python .claude/scripts/docs_ops.py tag-normalize docs/ --apply` (dry-run 먼저 권장)
- 한글 tag 포함 문서는 자동 skip — 사용자가 영문 매핑 결정 필요
- Step 번호 변경은 SKILL.md 내부 참조만 자동 갱신. 다운스트림 자체 문서에 옛 "Step 9.6" 등의 라벨이 있으면 stale (수동 갱신 또는 박제 보존)

### 회귀 위험

- Step 11 분류 로직 변경 — `git log UPSTREAM_REF -- <path>` 호출이 추가됨. 대규모 repo에서 약간의 latency 증가 가능 (drift 파일 수에 비례)
- tag-normalize `--apply`가 frontmatter `tags:` 라인을 정규식 1회 치환으로 갱신 — multi-line `tags:` 포맷(YAML block) 사용 시 미인식 가능. 본 starter는 inline `[a, b, c]` 표기만 사용하므로 영향 없음. 다운스트림이 block 표기 사용 시 주의

### 다운스트림 보고 요청

본 wave 적용 후 다음 upgrade에서 다음을 측정해 `migration-log.md` `## Feedback Reports`에 응답:

1. **Step 11 UNAPPLIED 카운트 변화**: 본 보강 전(v0.47.5) 대비 false positive 감소율
2. **tag-normalize 실측**: `--apply` 실행 시 변환 성공 건수 / 한글 skip 건수
3. **P11 동형 잠복 후보 관찰**: 본 wave에서 박제한 후보들(SEALED 면제 분류, cluster abbr 파싱 등)이 실제 결함을 만들었는지

---

## v0.47.5 — Wiki 그래프 자산 생성 wave (§A frontmatter 보강·§B tag normalize·§C rel 정리) (2026-05-15)

### 변경 내용

73% 삭감 wave §S-7 박제의 자산화 단계. 메커니즘 → 데이터 누적.

**§A. problem 인용률 보강 (39% → 95.8%)**:
- 72개 누락 문서에 frontmatter `problem`·`s` 일제 추가
- 자동 분류기 (tag·title 키워드 매칭) + 사용자 검토 7건 정정 + L 22건 본문 검토
- 최종: 113/118 인용 (면제 5건: sample 3 + MIGRATIONS 2)
- 분류기 false-positive 7건은 다음 wave 정련 후보로 박제

**§B. tag normalize (271 unique → 정리)**:
- 단복수 통합: rule→rules, skills→skill, agents→agent, incidents→incident
- p# tag 제거: p3·p4·p5·p7·p8·p9·p9-candidate (frontmatter problem cascade와
  이중 박제 회피)
- 13 파일 수정. 5+ tag: 20개 (review 18·commit 13·downstream 13 등)

**§C. relates-to rel 4종 수렴**:
- 사용 빈도 측정: 47% (57/121 문서, 75 rel 인스턴스)
- 유지 4종: extends 35·caused-by 22·references 15·supersedes 1
- 폐기 3종:
  - **implements** (2건) → extends 흡수 (의미 겹침)
  - **precedes** (2건) → 제거 (git history가 시간 SSOT)
  - **conflicts-with** (0건) → SSOT 정의만 있고 사용 0
- docs.md rel SSOT: 6종 → 4종 (`extends`·`caused-by`·`references`·`supersedes`)

### 적용 방법

**자동 적용**: harness-upgrade가 3-way merge로 처리.

**수동 확인 권장**:
1. 다운스트림 문서 frontmatter `relates-to: ... rel: implements|precedes|conflicts-with`
   사용 시 pre-check 차단 가능성. 4종 중 하나로 변경:
   - `implements` → `extends`
   - `precedes` → 제거 또는 본문 언급
   - `conflicts-with` → `references` 또는 제거
2. `python .claude/scripts/docs_ops.py cluster-update` 실행 — tag normalize 반영

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -m "gate or tag" -q --deselect .claude/scripts/tests/test_pre_commit.py::TestCommitFinalize
```

### 회귀 위험

- rel 폐기 3종 사용 다운스트림이 있으면 첫 commit 차단 가능 (실측 starter
  본인 사용 빈도 매우 낮음 — 다운스트림 영향 작을 것으로 추정).
- p# tag 제거는 cluster 자동 갱신 — 다운스트림 영향 없음.
- frontmatter problem 보강: 자동 분류기 정확도가 100% 아님 (false-positive 7건
  실측). 다음 wave에서 eval --harness 인용 빈도로 잘못된 매핑 자연 발견.

---

## v0.47.4 — §S-8 AC 체크박스 게이트 + §S-9 S# cascade 정합 게이트 (2026-05-15)

### 변경 내용

**§S-8 AC 체크박스 형식 강제**:
- pre_commit_check.py에 AC 섹션 체크박스(`- [ ]`/`- [x]`) 형식 검사 추가
- 자유 텍스트 AC 차단 — 완료 판정 게이트(`docs_ops.py move` 빈 체크박스)
  작동 보장
- test_pre_commit.py `@pytest.mark.gate` 4 케이스 신설

**§S-9 S# → AC cascade 정합 게이트**:
- kickoff `## Problems` 표에 **P10 (본질 미정, catch-all)** 추가
- kickoff `## Solutions` 표에 **"해결 기준" 컬럼** 신설 — S1~S9 각 1~2줄 박제
  (archived 본문에서 추출) + **S10 (본질 의심) 추가**
- pre_commit_check.py 게이트 신설:
  - `s:` 비어있음 차단 (학습 데이터 입력 의무)
  - AC 섹션에 각 S# 번호 1개 이상 등장 검사 (substring X — §S-1 함정 회피)
  - 자기 변경 면제: kickoff·cps_master·docs/cps/* staged 시 skip
  - P10 인용 시 ℹ️ 안내 (차단 X) — 엄격 기준 + 후보 동반 권장
- docs.md AC 포맷 박제 강화 — S# 인용 강제 + substring 인용 금지 + P10 엄격 기준
- test_pre_commit.py `@pytest.mark.gate` 5 케이스 신설

**P10·S10 본질**:
- 학습 시스템의 관찰 큐 — `docs_ops.py cps cases --p P10` 누적 패턴 조회
- 엄격 기준: P1~P9 각각 검토 후 어디에도 명확히 안 맞을 때만
- 부적합 패턴: "잘 모르겠음·귀찮음·빠르게 넘기고 싶음" — 도피처 아님
- 의심 근거 1줄 박제 의무 + 가장 가까운 후보 P#·S# 동반 권장

**동기**: 사용자 우려 "S#를 선택했으면 그에 합당한 AC가 나와야지. 임의로
툭 튀어나온 AC가 아니라." cascade 단절(S# 박제와 AC 작성 사이) 해소.

### 적용 방법

**자동 적용**: harness-upgrade가 3-way merge로 처리.

**수동 확인 권장**:
1. 기존 WIP의 frontmatter `s:`가 빈 list이면 commit 차단됨. wave 내용 검토 후
   S# 1개 이상 추가 (안 맞으면 P10·S10 사용 단 엄격 기준)
2. 기존 WIP의 AC 섹션이 자유 텍스트면 차단됨. `- [ ] Goal: ...` 형식으로 변환
3. `kickoff Solutions` 표 "해결 기준" 컬럼 참조해 AC `검증.실측` 보강 권장

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -m "gate" -q --deselect .claude/scripts/tests/test_pre_commit.py::TestCommitFinalize
```

### 회귀 위험

- 다운스트림 기존 WIP가 자유 텍스트 AC 또는 `s: []`이면 첫 commit 차단.
  WIP 수정 후 재커밋 필요. 차단 메시지에 보강 가이드 박혀있음.
- starter 운용 1~2회 후 사용자 판정 (S# 인용 강제가 작업 흐름 마찰 vs
  학습 신호 품질 향상 균형).

---

## v0.47.3 — 격하 잔재 강제 삭제 정정 (2026-05-15)

### 변경 내용

**harness-upgrade Step 7 (B) 격하 잔재 — 강제 삭제로 정정**:
- v0.47.2에서 (B)도 (A)와 동일하게 [Y/n/건너뛰기] 응답으로 처리했으나,
  격하 폴더는 starter 소유 자기 파일이라 사용자 커스텀 가능성 0 → 보존 가치 0
- 응답 없이 즉시 삭제 + 알림만 출력으로 정정
- (A) DELETED는 사용자가 fork/커스텀했을 잠재 가능성으로 [Y/n] 응답 유지

**근거**: 사용자 명시 정정 "삭제 제안이 아니고 삭제해야지. 남겨둘 이유 없잖아?"
(2026-05-15). 격하 메커니즘 의미상 다운스트림은 격하 폴더를 의도적으로
보유할 이유가 없음 — starter 전용 도구이므로 다운스트림에 무용.

### 적용 방법

자동. v0.47.2 적용 후 별도 액션 불필요. 다음 harness-upgrade 1회 실행 시
(B)는 자동 삭제 (응답 불필요), (A)는 [Y/n] 응답.

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -q --deselect .claude/scripts/tests/test_pre_commit.py::TestCommitFinalize
```

### 회귀 위험

- (B) 강제 삭제는 `is_starter: false` 분기 안에서만 실행 — starter 본인
  자기 파일 오삭제 방어 잔존. 다운스트림 격하 폴더 강제 삭제는 운용 1회
  후 사용자 판정 (사용자 의도 X → 0 보존 가치 전제 검증).

