---
title: 다운스트림 마이그레이션 가이드 — 아카이브
domain: harness
tags: [migration, upgrade, downstream, archive]
status: completed
created: 2026-05-02
---

# 다운스트림 마이그레이션 가이드 — 아카이브

`MIGRATIONS.md`는 최근 5개 버전 본문만 유지한다. 6번째 이전 버전은 본
파일로 이동된다 (v0.30.1 정책). 다운스트림이 오래된 업그레이드를 추적해야
할 때만 참조.
## v0.28.9 — Phase 3 split 옵트인 강등 + AC [x] 자동 이동 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | split 결정 로직 옵트인 강등. char 다양성 ≥ 2 + (HARNESS_SPLIT_OPT_IN=1 OR 거대 커밋) + non-skip stage 모두 만족 시에만 split. 5/5 skip 케이스 자동 single |
| `.claude/scripts/docs_ops.py` | 3-way merge | wip-sync 자동 이동 트리거 확장. body_referenced 신호 추가 — 이미 [x] 상태 WIP에서도 staged 파일 본문 언급 시 자동 이동. 미완료 검사를 체크박스 패턴(`- [ ]`)으로 정밀화 |
| `.claude/rules/staging.md` | 3-way merge | "split 옵트인 정책" 섹션 신설. 기본 single, 분할은 명시 트리거 시에만 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **이전 동작 변경**: char 다양성 ≥ 2면 무조건 split → 이제는 거대 커밋 OR `HARNESS_SPLIT_OPT_IN=1` 명시 시에만. 다운스트림이 split 동작에 의존하지 않으면 자연 흡수
- **AC [x] 자동 이동**: 사용자가 미리 [x] 마킹한 WIP가 commit 시 자동 completed 이동. 차단 키워드(`TODO:`·빈 체크박스 등) 검사 통과 시에만
- **회고 영향**: "단일 결정 = 단일 커밋" atomic 원칙 적용. 다운스트림이 char별 selective fetch하지 않는 경우만 안전 (확인됨)
- 한계: `HARNESS_SPLIT_OPT_IN=1` 미지원 다운스트림 환경에선 자동 분할 의존이 불가능 — 거대 커밋 시 자동 분할은 동작

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash):
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: 본 commit 자체 — char 다양성 2 + non-huge → split_action: single (이전엔 split)
  - T40.1 wip-sync abbr 테스트는 본 환경 fixture 격리 갭으로 fail (본 fix 무관, MIGRATIONS v0.28.4 주의 참조)

### 검증
```bash
pytest -m "secret or stage"
HARNESS_SPLIT_OPT_IN=1 /commit  # 명시 분할 옵트인
```

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



## v0.47.8 — 73% 삭감 wave 후 부패 잔재 정리 (check-existing·doc-health·hn_review_staging) (2026-05-16)

### 변경 내용

`/eval --harness`에서 발견된 부패 4건 + HARNESS.json `skills` 목록 잔재 정리.
73% 삭감 wave §S-4에서 폐기한 스킬(`check-existing`·`doc-health`)이 일부
hook 안내·설정 목록에 그대로 남아 매 세션·매 compact·매 Write 호출마다
존재하지 않는 스킬을 안내하던 부패 잔재.

### 영향

- `.claude/scripts/session-start.py:350`·`post-compact-guard.py:155`:
  "check-existing으로 중복 확인" → "LSP + Grep으로 중복 확인"
- `.claude/scripts/write-guard.sh`: 헤더 주석·src 안내 메시지 동일 교체
- `.claude/rules/docs.md` cluster 예시: 폐기된 `hn_review_staging.md` 참조
  → 실재 문서(`hn_review_tool_budget.md`·`hn_review_staging_rebalance.md`)로 교체
- `.claude/HARNESS.json` `skills`: `check-existing`·`doc-health` 제거

### 다운스트림 영향

`harness-upgrade` 자동 적용 시 hook 출력 1줄 + skills 목록 정합화. 다운스트림
사용자 행동 변화 없음 (안내 메시지만 정확해짐).



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



## v0.47.2 — harness-upgrade Step 7 격하 감지 + 클린 패치 안내 (2026-05-15)

### 변경 내용

**harness-upgrade Step 7 확장 — 격하 감지 (B) 신설**:
- 기존 (A) DELETED 카테고리에 더해 **(B) starter_skills 격하 잔재 감지** 추가
- (A) DELETED — 사용자 [Y/n/건너뛰기] 응답 (사용자가 fork/커스텀했을 잠재 가능성)
- (B) 격하 잔재 — **강제 삭제 + 알림만** (starter 소유 자기 파일이므로 보존 가치 0)
- starter 본인(`is_starter: true`)은 (B) 검사 skip — 자기 파일 오삭제 방어

**MIGRATIONS.md v0.47.1 클린 패치 안내**:
- 본 wave에서 격하·폐기된 파일이 v0.25.x 시기 채택 다운스트림에 잔재할
  수 있음을 명시. harness-upgrade Step 7이 자동 처리 — 사용자 명령 복사 불필요

**본 patch의 직접 동기**:
- 2026-05-15 실측 — v0.42.7 다운스트림에 `harness-dev/` 폴더 잔재 (v0.25.x
  채택 시점에 받음, v0.35.1 starter_skills 등록 후 회수 메커니즘 부재)
- harness-upgrade가 새 파일 추가는 처리하지만 "starter_skills 격하" 신호는
  못 잡음. 본 patch로 갭 해소

### 적용 방법

**자동 적용**: harness-upgrade가 Step 7에서 (A) + (B) 자동 안내.

**수동 확인 불필요**: 본 patch 적용 후 다음 harness-upgrade 1회 실행 시
모든 격하·폐기 잔재 자동 감지 + [Y/n/건너뛰기] 응답.

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -q --deselect .claude/scripts/tests/test_pre_commit.py::TestCommitFinalize
```

### 회귀 위험

- harness-upgrade Step 7 (B)는 신설 메커니즘. starter 본인 분기 처리로
  자기 파일 오삭제 방어. 다운스트림 격하 감지는 운용 1~2회 후 사용자 판정 필요.



## v0.47.1 — 73% 삭감 wave §S-3·§S-4·§S-5·§S-6·§S-7 일괄 박제 (2026-05-15)

### 변경 내용

**§S-3 (버그 대처 영역)**:
- `rules/bug-interrupt.md` **삭제** (170줄) — Q1/Q2/Q3 자가 발화 의존 블록 폐기
- `agents/debug-specialist.md` 4→1~2단계 압축 (214→80줄)
- `rules/no-speculation.md`에 결정적 신호 트리거(test 실패·exit code) 박제

**§S-4 (스킬 슬림화)**:
- `skills/implementation/SKILL.md` 465→153 (Phase 6원칙·라우팅 매트릭스 폐기)
- `skills/commit/SKILL.md` 718→221 (AC 자동 실행·verdict 추출·5단계 stage 폐기)
- `skills/write-doc/SKILL.md` 248→111 (6종 템플릿·라우팅 태그 폐기)
- `skills/eval/SKILL.md` 664→163 (--surface·--deep·4관점 병렬 폐기, --quick·--harness만)
- `skills/doc-health/SKILL.md` **삭제** → eval --harness 흡수
- `skills/check-existing/SKILL.md` **삭제** → LSP + Grep 1회로 대체
- `skills/harness-upgrade/SKILL.md` Step 9.3 (HARNESS_MAP 전파 확인) 삭제

**§S-5 (rules 본문 처리)**:
- `rules/anti-defer.md` **삭제** (70줄) — 자가 점검 의존
- `rules/external-experts.md` **삭제** (81줄) — 외부 전문가 캐시 폐기
- `rules/pipeline-design.md` **삭제** (116줄) — 7항목 자가 점검 의존
- `rules/internal-first.md` 38→24 축약
- `rules/memory.md` 133→59 축약 (session-* 3파일 정의만)
- `rules/no-speculation.md` 93→40 축약 (첫 행동 3원칙)
- `rules/self-verify.md` 141→69 축약
- `rules/docs.md` 440→311 (구성요소 메타데이터 trigger·Layer·enforced-by 폐기 + wiki 그래프 모델 박제)
- `rules/naming.md` "tag 정책" 신설 (정규식 + 한글 금지)

**§S-6 (스크립트 슬림화)**:
- `scripts/orchestrator.py` **전면 삭제** (696줄, hook 무력화 후 사용 0)
- `scripts/debug-guard.sh` **삭제** (BIT hook 폐기)
- `scripts/pre_commit_check.py` tag 정규식 차단 게이트 추가 + 자동 split 발동 폐기 (`HARNESS_SPLIT_OPT_IN` 명시 옵트인만 잔존)
- `scripts/docs_ops.py` cluster-update 갱신: tag 분포·백링크 자동 생성 (2건+ 임계, DRY) + meta cluster 폴백 버그 수정 (sample 자동 등록)
- `scripts/eval_cps_integrity.py` HARNESS_MAP 점검 + BIT NEW 플래그 폐기 (478→285줄) + 사전 회귀(`get_cps_text`·`verify_solution_ref` import 깨짐) 해소
- `scripts/session-start.py` BIT 출력 + HARNESS_MAP 출력 폐기
- `scripts/stop-guard.py` BIT 블록 검사 폐기
- `tests/test_pre_commit.py` tag 정규식 marker 18 케이스 신설 (`@pytest.mark.tag`)

**§S-7 (Wiki 그래프 모델 신설)**:
- 발견 본질: "wiki처럼 이어지는 거 — 원래 이걸 원했던 거"
- domain = 노드 zone (변경 전파 범위), tag = 간선 (cross-domain edge)
- cluster 파일에 tag 분포·백링크 섹션 자동 생성 (`docs_ops.py cluster-update`)
- 백링크 임계: tag별 2건 이상만 (1건은 분포 표와 동일 정보 — DRY)
- tag 정규식: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` — pre-check 결정적 차단
- 한글 tag 금지 (grep·anchor 호환성, 다운스트림 cascade)
- meta cluster: sample·template zone, 빈 상태 정상
- cps cluster 첫 case 박제: `docs/cps/cp_harness_73pct_cut.md` (본 wave 자체)

**잔존 참조 일괄 정리**:
- `CLAUDE.md`·`agents/review.md`·`agents/researcher.md`·`agents/advisor.md`·`agents/codebase-analyst.md`
- `skills/harness-upgrade`·`harness-dev`·`harness-adopt`에서 HARNESS_MAP·doc-health·anti-defer·external-experts·BIT 참조 폐기 또는 폐기 의도 명시

> harness-upgrade Step 7 격하 메커니즘 신설은 후속 v0.47.2 patch에 박제 (위 섹션 참조).

### 적용 방법

**자동 적용**: harness-upgrade가 3-way merge로 처리.

**수동 확인 권장**:
1. 본인 프로젝트 frontmatter `tags`에 영문 소문자+숫자+하이픈 외 문자(대문자·언더바·한글) 있으면 pre-check 차단됨. 사전 grep 권장:
   ```bash
   grep -rE "^tags:.*[A-Z_가-힣]" docs/
   ```
2. `python .claude/scripts/docs_ops.py cluster-update` 실행 — 신규 tag 분포·백링크 섹션 자동 생성
3. CPS case 누적은 점진적 — wave 완료 시마다 `docs/cps/cp_{slug}.md` 박제 (선택)

**자동 클린업**: harness-upgrade Step 7이 본 wave에서 폐기·격하된 모든
파일을 자동 감지하고 삭제를 제안합니다 — 사용자 명령 복사 불필요:

- **DELETED 카테고리** (upstream git rm): rules 4·scripts 4·skills 2 폐기 자동 감지
- **starter_skills 격하 카테고리** (Step 7 (B) 신설): `harness-dev` 같은 격하 잔재 자동 감지

각 항목 [Y/n/건너뛰기] 1회 응답. 자동 처리 신뢰 우려 시 응답 전 사용자가
파일 목록 확인 가능.

### 검증

```bash
python -m pytest .claude/scripts/tests/test_pre_commit.py -m "tag or gate or secret" -q
python .claude/scripts/eval_cps_integrity.py
python .claude/scripts/docs_ops.py cluster-update
```

### 회귀 위험

- upstream 격리 환경에서 관찰된 범위 내에서는 회귀 0. commit_finalize.sh의 Windows 경로 git alternates fail은 본 wave 무관 (사전 환경 결함).
- 다운스트림이 frontmatter tags에 한글·대문자·언더바를 사용 중이면 첫 commit에서 차단됨 — 위 "수동 확인 권장" grep으로 사전 검증 권장.
- pytest 84 passed, 4 skipped (commit_finalize 환경 fail 3건 제외)



## v0.47.0 — 73% 삭감 wave §S-1 CPS 재설계 + §S-2 AC 단순화 (2026-05-14)

### 변경 내용

**§S-1 CPS 재설계 (자라는 시스템 + CPS 도메인 신설)**:
- `.claude/HARNESS_MAP.md` **삭제** — defends/serves/enforced-by/trigger 정적 표 폐기.
  CPS cascade 표가 정적이라 죽었음을 박제. wave별 case는 `docs/cps/cp_{slug}.md` + git history.
- CPS 도메인 신설 — abbr `cp`, `docs/cps/` 폴더, `docs/clusters/cps.md` 자동 매핑.
- 신규 스킬: `.claude/skills/cps-check/SKILL.md` (옵트인 정합 검사).
- 신규 명령: `python .claude/scripts/docs_ops.py cps {list|add|cases|show|stats}`.
- `docs/guides/project_kickoff.md` 491 → 78줄 압축 (C 판단 프롬프트, 자라지 않음).
  압축 전 본문은 `docs/archived/hn_kickoff_pre_73pct_cut.md`에 보존.
- `pre_commit_check.py` CPS 인용 박제 substring 검사 폐기 (~150줄):
  `normalize_quote`·`parse_solution_ref`·`get_cps_text`·`verify_solution_ref` 함수 삭제.
- `docs.md` "CPS 인용" 섹션 폐기 — 50자·(부분)·normalize 룰 삭제, 번호 list만.
- WIP frontmatter `s: [S2, S6]` 번호 list 형식 도입. 레거시 `solution-ref` 호환 유지.

**§S-2 AC 4필드 → 3필드 (검증.review 5단계 자가 선언 폐기)**:
- `.claude/rules/staging.md` **삭제** — Stage 5단계 룰 폐기.
- AC 형식: `Goal:` + `검증.tests:` + `검증.실측:` 3필드. `검증.review:` 폐기.
- `pre_commit_check.py` stage 결정 단순화 — 5단계(skip/micro/standard/deep) → 2단계(default/deep).
  default = 사용자 플래그 결정, deep = 시크릿 line-confirmed 강제.
- commit 스킬 플래그 단순화 — `--quick`/`--deep` 폐기, `--review`/`--no-review` 2단계.
- review agent verdict 강제 추출 폐기 — diff별 한 줄 의견 자유 형식.

**기타**:
- `pre_commit_check.py` 1060 → 959줄 (101줄 감소).
- CLAUDE.md "하네스 신경망 허브" → "## CPS" 짧은 안내 (HARNESS_MAP 참조 제거).

### 적용 방법

**자동**: harness-upgrade 시 위 파일 변경이 머지된다.

**수동**:
- 기존 WIP frontmatter `solution-ref: - S2 — "..."` 형식은 그대로 두면 호환 (S# 번호만 추출).
  신규 WIP는 `s: [S2, S6]` 인라인 list 권장.
- AC 형식: 기존 WIP의 `검증.review: skip|self|review|review-deep` 라인은 무시됨 (파싱 안 함).
  신규 WIP는 `검증.tests` + `검증.실측` 2개만.
- HARNESS_MAP.md 참조하는 다운스트림 룰·스킬이 있으면 본문 직접 갱신 권장 (자동 머지 불가).

### 검증

```bash
# CPS 시스템 작동 확인
python .claude/scripts/docs_ops.py cps list      # P1~P# 1줄 요약
python .claude/scripts/docs_ops.py cps stats     # case 수·P# 분포

# pre-check 작동 확인 (WIP 작성 후)
python .claude/scripts/pre_commit_check.py       # ac_tests·ac_actual 출력, ac_review 사라짐
```

### 회귀 위험

- upstream 격리(Windows/Git Bash)에서 `pre_check_passed: true` 실측.
- 기존 WIP의 `solution-ref` 50자 인용 형식 파일은 다음 커밋 시 그대로 통과 (S# 번호만 추출). 박제 substring 검사 폐기로 인용 의미 검증이 사라짐 — wave 간 역영향 추적은 commit body·git log로 수동 처리.
- Linux/macOS 미테스트.



## v0.46.2 — 하네스 v0.41 baseline 회복 + audit 18 해소 단일 wave (2026-05-13)

### 변경 내용

**의도**: v0.43.0 orchestrator MVI 도입 이후 누적된 hook 강제 패턴·자동
트리거가 행동 붕괴 유발. 사용자 증언 "v0.41쯤이 정상 마지막"을 baseline
으로 단일 wave 회복. 9b29f23(v0.44.1) 도돌이표 commit revert + audit 18
중 17건 해소.

**revert 범위 (9b29f23 일괄 환원)**:
- pre_commit_check.py route 출력 8키(commit_route·review_route·promotion·
  blocking_reasons·warning_reasons·side_effects.*) 폐기
- commit/SKILL.md route 소비 코드 베이스라인 환원
- split-commit.sh 9b29f23 변경 환원 (본 wave가 새 비파괴 default 재구현)
- Windows smoke 테스트(TestWindowsCommitSmoke) + windows·cascade marker 폐기
- side effect ledger·cascade integrity check 폐기

**hook 무력화 (Phase 1)**:
- `.claude/settings.json` PreToolUse `orchestrator.py` hook 제거
- `.claude/settings.json` UserPromptSubmit `debug-guard.sh` hook 제거
- Gemini 자동 호출은 orchestrator 내부 호출이라 자동 무력화
- worker 파일(orchestrator.py·debug-guard.sh·gemini_background_worker.py)
  보존 — 수동 호출 또는 후속 재설계에 사용
- bug-interrupt.md "## 강제 트리거" 절을 "## 수동 가이드"로 변경

**정합 패치 (Phase 2~4)**:
- harness_version_bump.py: patch 트리거 좁힘. `.claude/scripts/*.{sh,py}`
  1줄 수정 = patch 룰 폐기. skills SKILL.md·rules·agents·CLAUDE.md만 patch
  자동 (그 외는 promotion=none, 작성자 명시 옵트인만)
- split-commit.sh: 비파괴 default + `--apply` 옵트인 + `SPLIT_PRE_OUT`
  env로 pre-check 중복 호출 우회
- pre_commit_check.py: `git diff --cached --name-only` 중복 호출 제거 +
  HARNESS.json 중복 read 제거(main 함수 내 1회 캐시)
- commit_finalize.sh: wip-sync 조건부 실행 (staged에 `docs/(WIP|clusters)/`
  변경 있을 때만)
- docs_ops.py wip-sync: abbr 매칭 우선 후보 추출 → 매칭 시 그 WIP만 iter,
  매칭 0이면 전체 iter fallback

**.gitignore 보강**: `.claude/worktrees/` 차단 (절대 규칙: worktree 금지).

### 적용 방법

**자동**: 다운스트림이 `/harness-upgrade` 실행 시 코드 변경 자동 병합.

**수동 (다운스트림 영향)**:
- 다운스트림 `.claude/settings.json`의 hook 블록이 v0.43.0~v0.44.0 hook
  3종(orchestrator·debug-guard·gemini)을 포함하면 3-way merge로 제거 처리.
  hook 커스터마이즈된 다운스트림은 ours/theirs 결정 필요
- 다운스트림이 SKILL.md route 출력(`commit_route`·`review_route` 등) 키를
  소비하는 커스텀 스크립트를 만들었다면 해당 키 사용 코드 제거 또는
  버전 분기 필요

### 검증

```bash
python3 -c "import json; s=json.load(open('.claude/settings.json')); print('UserPromptSubmit:', s['hooks'].get('UserPromptSubmit', 'REMOVED'))"
# 예상 출력: UserPromptSubmit: REMOVED
python3 .claude/scripts/pre_commit_check.py 2>&1 | grep -E "^(commit_route|review_route|promotion):" | wc -l
# 예상 출력: 0 (revert 확인)
```

### 회귀 위험

- upstream 격리 환경(Windows·Git Bash)에서 관찰된 범위 내에서는 v0.41
  baseline 동작 회복 정합. Linux/macOS 미테스트
- hook 무력화로 BIT 키워드 grep·orchestrator 신호 안 나옴 — 자가 인지
  의존 영역으로 환원. 자가 발화 의존 한계는 P8/P9가 박제하는 본질이라
  hook 강제력으로 우회 불가 (Anthropic Issue #13912 명시)
- audit #6(Codex 인프라 사본 부담)는 명시적 보류. 사용자 결정 "Codex 유지"



## v0.44.0 — Gemini 자동 호출 opt-in과 Codex hook 계약 보강 (2026-05-12)

### 변경 내용

Codex 전환 후 드러난 hook/agent 경계와 Gemini 자동 위임 노이즈를 정리했다.

- `orchestrator.py`: Gemini 자동 호출을 기본 off로 전환하고 `HARNESS_GEMINI_AUTO=1`일 때만 background worker를 실행한다.
- `orchestrator.py`: CPS 본문뿐 아니라 `problem`·`solution-ref`가 있는 WIP의 Solution 맥락 변경도 검토 후보로 감지한다.
- `gemini_background_worker.py` 추가: 긴 prompt를 파일/stdin 경유로 전달하고 stdout/stderr를 세션 scratch 파일에 기록한다.
- `.codex/hooks.json`·`.claude/settings.json`: 빈 matcher를 명시해 Codex/Claude hook schema 경고를 줄인다.
- `test_codex_agents.py` 추가: Codex agent TOML, hook matcher/type/command 계약, Gemini 미지원 tool 이름 박제를 회귀 가드로 고정한다.
- `test_orchestrator.py`: Gemini auto off, worker 출력 기록, WIP Solution 맥락 감지, Python 3.10 호환 경로를 보강한다.

### 자동 적용 항목

파일 추가·수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. Gemini 자동 검토가 필요한 upstream 운용자는 명시적으로 `HARNESS_GEMINI_AUTO=1`을 설정해야 한다.

### 검증

```
python3 .claude/scripts/pre_commit_check.py
python3 -m pytest .claude/scripts/tests/ -q
```

### 회귀 위험

관찰 범위 내 위험: Gemini 자동 호출이 기본 off가 되므로, 이전처럼 PreToolUse에서 자동 외부 의견 파일이 생성된다고 기대하던 운용은 명시 opt-in으로 전환해야 한다. Codex hook matcher 계약이 더 엄격해져 다운스트림의 기존 `.codex/hooks.json` 커스터마이즈와 충돌할 수 있다.



## v0.43.3 — Codex 하네스 브리지와 Gemini 위임 WIP 정렬 (2026-05-11)

### 변경 내용

Codex 환경에서 기존 하네스 규칙·스킬·에이전트 지시가 함께 로드되도록
브리지 파일을 추가했다.

- 루트 `AGENTS.md` 추가 — Codex 진입점에서 하네스 핵심 규칙 노출
- `.agents/skills/**` 추가 — 하네스 스킬 본문을 Codex skill discovery 경로로 제공
- `.codex/agents/*.toml` 추가 — 기존 specialist 에이전트를 Codex subagent 정의로 연결
- `.codex/hooks.json` 추가 — Codex hook 설정 진입점 추가
- `pre_commit_check.py`와 `orchestrator.py` 보강 — starter 자가 검증 및 반복 신호 흐름 정렬
- `hn_gemini_delegation_pipeline` 결정 문서를 WIP로 되돌려 Phase 후속 작업 진행 상태 반영
- 세션 거짓 완료·자기 위반 패턴 incident WIP 추가

### 자동 적용 항목

파일 추가·수정은 harness-upgrade 3-way merge로 자동 적용된다.

### 수동 적용 항목

없음. 다만 다운스트림에서 자체 Codex 설정을 이미 운용 중이면 `.codex/` 충돌 해소 시
로컬 설정 유지 여부를 확인한다.

### 검증

```
python3 .claude/scripts/pre_commit_check.py
python3 -m pytest .claude/scripts/tests/ -q
```

### 회귀 위험

관찰 범위 내 위험: Codex 전용 브리지 파일이 다운스트림의 기존 `.codex/`
커스터마이즈와 충돌할 수 있다. 충돌 시 harness-upgrade 3-way merge에서
로컬 설정과 upstream 기본값을 비교해야 한다.



## v0.43.2 — gemini_delegation_pipeline Phase 1 (CPS Solution 변경 자동 Gemini 의견) (2026-05-11)

### 변경 내용

gemini_delegation_pipeline 결정 Phase 1 박제. orchestrator.py에 CPS
Solution 변경 staged 시 gemini CLI 자동 호출 트리거 추가.

- `detect_solution_change()` 신설 — `git diff --cached
  docs/guides/project_kickoff.md` Solutions 섹션 변경 detect
- `gemini_cli_available()` — `shutil.which("gemini")` 확인. 미설치 시
  graceful skip (다운스트림 cascade 영향 0 보장)
- `call_gemini_background()` — detach subprocess. PreToolUse hook 지연
  없이 반환. 결과 `.claude/memory/gemini-solution-review.md`
- 세션당 1회만 호출 — `gemini_solution_review_called` 플래그
- INFO 신호로 사용자 알림. Critical 아님 — 권고 수준

회귀 가드 3건 신설 — CLI 미설치 skip·Solutions 미변경 skip·세션당 1회.
전체 10/10 통과 (기존 7 + 신규 3).

`docs/decisions/hn_gemini_delegation_pipeline.md` Phase 분리 결정 박제 +
completed 전환. Q1~Q6 본 wave 합의 (Phase 1 객관 신호 트리거만 구현,
Phase 3 의미 신호·PostToolUse review verdict 트리거는 별 wave 후보).

### 적용 방법

자동 적용. gemini CLI 설치 안 한 다운스트림은 무영향.

설치한 환경에서만 작동:
- gemini CLI 0.41+ + OAuth 인증 (`gemini` 첫 실행 시 자동)
- 또는 `GEMINI_API_KEY` 환경 변수

### 검증

```
pytest .claude/scripts/tests/test_orchestrator.py -v
# 10/10 통과
```

### 회귀 위험

upstream 격리 10/10 통과. Solution 변경 detect의 false-positive 가능 —
Solutions 섹션 외 P# 섹션 변경에 hit하지 않도록 heuristic 적용했으나
완벽하지 않음. 실측 누적 후 정밀화 필요.

OAuth quota 일 한도 도달 시 호출 실패 — Popen detach라 오류가
사용자에게 안 노출. 결과 파일이 비어 있으면 quota 또는 timeout 의심.



## v0.43.1 — orchestrator P1 신호 stale 누적 해소 (upsert) (2026-05-11)

### 변경 내용

v0.43.0 직후 실측 — orchestrator.py 자기 수정·README 수정마다 P1 INFO
신호가 count 변화별로 별도 누적되어 PreToolUse 컨텍스트에 stale 신호 3건
이상 동시 출력 (3회·4회·5회가 각각 별도 신호). session 길어질수록 노이즈
증폭.

원인: `deduplicate_signals`가 `(p_id, message)` 키 사용 — count 변화 시
message 문자열 달라져 새 식별자로 인식 → upsert 안 됨.

해소:
- 신호에 `key` 필드 (예: `"P1:{file_path}"`) 추가 — count 무관 안정 식별자
- `_signal_key()` 헬퍼: `key` 보유 시 upsert, 미보유 시 `(p_id, message)`
  fallback (P9 등 정적 신호 호환)
- `deduplicate_signals` 재작성 — `key` 일치 시 기존 신호 교체

### 적용 방법

자동 적용. 기존 다운스트림 session_signal.json은 새 형식과 호환
(fallback 동작) — 첫 P1 발화 시 자동 upsert 키 부여로 점진 정리.

### 검증

```
pytest .claude/scripts/tests/test_orchestrator.py -v
# 7/7 통과 (기존 5 + 신규 upsert·dedup fallback 2)
```

### 회귀 위험

upstream 격리 환경 7/7 통과. 기존 stale 신호가 session_signal.json에
누적된 다운스트림은 한 번 reset 권장 (`rm .claude/session_signal.json`)
또는 다음 새 신호 발생 시 자동 정리.



## v0.43.0 — 오케스트레이터 MVI 도입 (PreToolUse hook + P9 강제 cascade) (2026-05-11)

### 변경 내용

P9 (정보 오염의 관성)·S9 (주관 격리 + 다층 검증) 결정 시리즈의 실측
구현. `scripts/orchestrator.py` + PreToolUse hook 등록으로 LLM 자가
발화 의존을 커널 강제로 전환.

- `.claude/scripts/orchestrator.py` 신설 (~290줄) — P1·P9 객관 신호
  detect 엔진. stdin JSON 파싱 + WIP frontmatter ↔ CPS Problems 매칭
  + 동일 파일 연속 수정 카운터. 이중 안전장치: stdout
  `additionalContext` + `.claude/session_signal.json` 파일 쓰기.
- `.claude/settings.json` — PreToolUse hook에 matcher 없는(모든 도구)
  orchestrator.py 등록 추가
- `.claude/rules/docs.md` — Layer 2 도구 frontmatter `trigger:` 필드
  스키마 + 명명 규칙·금지 패턴 정의
- `.gitignore` — `.claude/session_signal.json` 런타임 상태 격리
- `.claude/scripts/tests/conftest.py` — `orchestrator` marker 등록
- `.claude/scripts/tests/test_orchestrator.py` — 회귀 5케이스
- `docs/WIP/decisions--hn_orchestrator_mechanism.md` — 결정 박제
  (Gemini 2차 위임 결과 반영, Exit 2 강제 중단 합의)

P9 cascade 깨짐 (WIP frontmatter `problem` ↔ CPS Problems 매칭 실패)
detect 시 **Exit 2 강제 중단** — Praetorian 8계층 모델 + arXiv:2503.13657
"Ignored other agent's input" 실패 모드 차단.

### 적용 방법

다운스트림은 harness-upgrade 후 다음 자동 적용:
- `scripts/orchestrator.py` 배포
- `.claude/settings.json` PreToolUse hook 등록 (3-way merge)
- `.gitignore` `.claude/session_signal.json` 추가

수동 액션 — **있음**:
- 첫 실행 시 `.claude/session_signal.json` 자동 생성됨 (Claude가 도구
  호출 시점에). 별도 작업 불필요
- 다운스트림이 자체 P 신호 추가 원하면 후속 wave의 `P_DEFINITIONS.json`
  확장 인터페이스 사용 예정 (v0.43.0은 P1·P9만)
- P9 Critical detect로 Claude 도구 호출이 차단될 수 있음 — WIP
  frontmatter `problem` 필드가 CPS Problems 목록에 등록됐는지 확인 필수

### 검증

```
python3 -m py_compile .claude/scripts/orchestrator.py
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 .claude/scripts/orchestrator.py
pytest .claude/scripts/tests/test_orchestrator.py -v
```

### 회귀 위험

upstream 격리(Windows / Git Bash)에서 관찰된 범위 내에서는 5/5 통과.
다른 OS·셸 환경 미테스트. WIP frontmatter `problem` 필드가 CPS Problems
미등록인 다운스트림에서 Critical exit 2가 빈발할 가능성 — 다운스트림
첫 적용 시 마찰 측정 필요.



## v0.42.7 — starter 자가 모호성·박제 일괄 흡수 (다운스트림 노이즈 차단) (2026-05-11)

### 변경 내용

다운스트림 `/eval --harness` 보고가 다수 다운스트림에서 반복될 것이라는
구조 인식에 따라 starter 자체 결함을 선제 흡수. starter 자가 정의한
모호성 패턴을 자기 SKILL.md가 위반하는 자기증명 P7 잔재 + 박제 인용 3건
+ CPS Solution 정의 갭을 한 wave에 정리.

**1. eval/SKILL.md 모호성 정의 정밀화**:
- "필요하면"·"가능하면" 등 조건문은 모호성 아님 — false-positive 차단
- 새 분류: 판단 기준 부재(`적절한·상황에 따라·알아서`) vs 수치 부재(`짧게·간결하게`) vs 열거 불완전(`등·기타`)
- 조건문 제외 명시 절 추가

**2. SKILL.md 5건 수치·분기 명시**:
- `eval/SKILL.md:110` "간결하게 유지" → "거시·블로커·부채 3섹션, 각 5줄 이내"
- `eval/SKILL.md:445` (implementation) "간결하게" → "본문 50줄 이내 권장"
- `harness-upgrade/SKILL.md:23` "가능하면 3-way merge" → "기본은 3-way, 충돌 시 사용자 결정 요청"
- `write-doc/SKILL.md:120` "snake_case 의미명, 간결하게" → "단어 2~4개, 30자 이내"
- `implementation/SKILL.md:408` "자동으로 적절한 폴더" → "WIP 파일명의 `{대상폴더}--` 접두사 기준 라우팅"

**3. CPS P7 본문 보강 + S7 의도적 미정의 명시**:
- P7 본문에 "Solution 의도적 미정의 — HARNESS_MAP.md 메커니즘 자체가 P7 해소" 명시
- S6·S8은 정의 유지. S7 자리는 별도 Solution 정의 안 함 (중복 추상화 방지)

**4. 박제 인용 3건 흡수**:
- `hn_eval_harness_medium_fixes.md`: S6 인용 `(M, ≥3줄)` 보강어 누락 → CPS 본문 정확 substring으로 교체
- `hn_stop_guard_py_migration.md`: S7 미정의 → S6(self-verify SKIP 조건 명확화) 재매칭
- `hn_wip_util_ssot.md`: 동일

검증: pytest 92 passed / 4 skipped, eval_cps_integrity 박제 의심 0건.

### 자동 적용 항목

- `.claude/skills/eval/SKILL.md` (모호성 정의 + 보고 형식)
- `.claude/skills/harness-upgrade/SKILL.md`, `write-doc/SKILL.md`, `implementation/SKILL.md`
- `docs/guides/project_kickoff.md` (P7 본문 보강)
- `docs/decisions/hn_eval_harness_medium_fixes.md`, `hn_stop_guard_py_migration.md`, `hn_wip_util_ssot.md` (박제 인용 수정)

### 수동 적용 항목

없음.

### 검증

```bash
python -m pytest .claude/scripts/tests/ -q
# 92 passed / 4 skipped

python .claude/scripts/eval_cps_integrity.py
# 박제 의심: 0건
```

### 회귀 위험

upstream 격리 환경에서 회귀 없음. SKILL.md 수치 변경은 자가 보고 안내 수치
— Claude 행동 변화는 자동 검증 불가. 운용 검증 필요.

### 다운스트림 영향

starter 발 모호성·박제가 누적될수록 다운스트림 N개에서 같은 보고가 N회
반복됨. 본 wave는 그 노이즈를 starter 측에서 선제 흡수한 것 — 다운스트림이
본 patch 적용 후 `/eval --harness` 재실행 시 starter 발 false-positive
일부 해소 예상.



## v0.42.6 — eval_cps_integrity FR 필드 정규식 bold 내부 괄호 보강 (FR-010) (2026-05-11)

### 변경 내용

`_field_present` 정규식이 bold 마커 **내부 괄호 보강어** 양식을 인식하도록
확장. 다운스트림 실측 양식 `**약점 (부분 작동)**:`이 v0.42.4 정규식에서
미매칭으로 오경보 발생 — FR-010 응답.

**변경 전 (v0.42.4)**:
```
\*\*{name}\*\*\s*:
```
필드명 직후 닫는 `**`만 허용. `**약점 (부분 작동)**:` 미매칭.

**변경 후 (v0.42.6)**:
```
\*\*{name}(?:\s+\([^)]*\))?\*\*\s*:
```
필드명 뒤 선택적 1단 괄호 그룹 허용. 중첩 괄호 미지원 (`[^)]*`).

### 적용 방법

- 자동: `harness-upgrade`로 `.claude/scripts/eval_cps_integrity.py` 덮어쓰기 자동
- 수동: 없음

### 검증

```bash
python -m pytest .claude/scripts/tests/test_eval_harness.py -q
# 14 passed (기존 12 + 신규 2: bold_inner_paren positive + prose negative gate)
```

### 회귀 위험

upstream 격리 환경에서 관찰된 범위 내에서는 회귀 없음 (전체 92 passed / 4 skipped).
산문 false-positive 가드 테스트 추가로 정규식 과확장도 방어. 중첩 괄호 양식
(`**X ((sub))**:`)은 의도적으로 미지원 — 자연어 양식에서 1단으로 충분 판단.

### Feedback Reports

#### FR-010 (2026-05-11)

**관점 (정규식 양식 갭)**: v0.42.4가 3양식(bold·plain·헤더 인라인) 양면 매칭을 표방했으나 bold 양식 내부 괄호 보강어 변형을 닫지 못함.
**약점 (부분 작동)**: 다운스트림 실측 양식 `**약점 (부분 작동)**:`이 미매칭. FR-007 응답이 한 양식만 닫고 인접 변형 미고려.
**실천 (정규식 보강)**: 필드명 뒤 선택적 괄호 그룹 `(?:\s+\([^)]*\))?` 허용. false-positive 가드 회귀 테스트 동반.
**심각도 (low)**: 검출 갭이지만 보안·데이터 영향 없음. 다운스트림 운용 피드백 채널 자연 회복.



## v0.42.5 — wip-sync 후 cluster·frontmatter 갱신 staging 누락 차단 (2026-05-11)

### 변경 내용

매 commit 직후 `docs/clusters/*.md` + 이동된 `docs/{decisions,...}/*.md`
2건이 unstaged 잔여로 남던 결함 차단. v0.42.1~42.4 모두 동일 잔여 발생
(starter 본인 5회 자기증명 = P6 검증망 스킵의 메커니즘 변종).

진단 결과 (코드 직접 Read):
- `cmd_cluster_update` (L499): `cluster.write_text(...)` 후 git add 0건 호출
- `cmd_move` (L350): `git mv`는 rename만 staging — 그 후 `write_frontmatter_field`
  (status·updated) 갱신은 working tree만 수정되어 unstaged
- `cmd_reopen` (L400): `cmd_move`와 동일 패턴

보강:
- 세 함수 모두 갱신 직후 `subprocess.run(["git", "add", str(...)], capture_output=True)` 추가
- `commit_finalize.sh` 주석 정정 — 기존 "`cmd_cluster_update`가 git add 호출"
  거짓 박제를 실제 코드와 정합한 설명으로 교체
- 회귀 가드 신설: `test_docs_ops_staging.py` 3건 (cluster_update / move / reopen).
  tmp_path + git init fixture로 격리. `git diff --cached`에 대상 파일 hit +
  unstaged 잔여 0건 검증

전체 90 passed (87 → 90, 회귀 0).

근거 문서: `docs/decisions/hn_wip_sync_staging_gaps.md`.

### 자동 적용 항목

- `.claude/scripts/docs_ops.py` (`cmd_cluster_update` + `cmd_move` + `cmd_reopen`)
- `.claude/scripts/commit_finalize.sh` (주석 정정)
- `.claude/scripts/tests/test_docs_ops_staging.py` (회귀 가드 3건 신설)

### 수동 적용 항목

없음. 다음 `/commit` 호출부터 자동으로 새 staging 흐름 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_docs_ops_staging.py -v
# 3 passed
python3 -m pytest .claude/scripts/tests/ -q
# 90 passed (회귀 0)

# 메타 검증 — 본 commit 직후 git status 깨끗하면 v0.42.5 보강이 자기 첫
# 적용 사례에서 즉시 작동 입증
git status --short
```

### 회귀 위험

- 회귀 가드 3건 + 전체 90 passed (회귀 0) 확인
- `capture_output=True`로 stderr·stdout 묻음 — git add 실패해도 commit 흐름은
  진행. 실패 시 잔여 발생으로 가시화 (자기검증)
- 한 cluster·dest 파일을 두 번 git add하는 케이스 가능 (cmd_move + 후속
  cmd_cluster_update 호출 시) — git add는 멱등이라 영향 없음
- tmp_path 회귀 테스트가 Windows 환경 한정 검증. Linux/macOS hook cwd 거동
  미테스트 — git subprocess 호출 표준이라 영향 미약

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **commit 직후 `git status --short` 결과**: v0.42.5 적용 후 첫 commit
   직후 잔여 파일 수. 0건이 정상. 1건+ 이면 starter 본인이 검증 못 한
   추가 결함 (보고 필수)

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.



## v0.42.4 — eval_cps_integrity 필드 매칭 정규식 다양성 확보 (FR-007) (2026-05-11)

### 변경 내용

다운스트림 v0.42.3 적용 측정 FR-007 후속 처리. 직전 wave에서 헤더 양면
매칭은 보강했으나 필드 substring 검사가 좁아 다운스트림 양식의 6건 모두
"⚠ 심각도 없음" 오경보 발생.

- **`check_feedback_reports` 필드 매칭 보강**: `required_fields` substring
  검사 → `_field_present` 헬퍼의 정규식 검사로 교체. 4 필수 필드(관점·약점·
  실천·심각도) 모두 3 양식 양면 매칭:
  - bold 마커: `**필드**:`
  - plain: `필드:` (한국어 단어 경계 lookbehind로 부분 단어 매칭 방지)
  - 헤더 인라인: `(필드:` 괄호 안
- **회귀 가드 신설**: `test_feedback_reports_inline_header_severity` 추가.
  `#### FR-NNN ... (심각도: medium — ...)` 헤더 인라인만 있고 본문에
  `**심각도**:` 별도 라인 없는 케이스도 정상 검출 (`FR-NNN ✅`)
- 12 passed (기존 11 + 신규 1) / 전체 87 passed / 회귀 0

근거 문서: `docs/decisions/hn_eval_harness_medium_fixes.md` Phase 3 + 변경 이력.

### 자동 적용 항목

- `.claude/scripts/eval_cps_integrity.py` (`_field_present` 헬퍼 + 정규식 매칭)
- `.claude/scripts/tests/test_eval_harness.py` (회귀 가드 1건 추가)

### 수동 적용 항목

없음. 다음 `eval --harness` 호출부터 자동 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -v
# 12 passed (기존 11 + 신규 1)
```

### 회귀 위험

- 정규식 한국어 단어 경계는 `(?<![\w가-힣])` lookbehind로 처리 — 부분 단어
  오탐 방지. 다른 한국어 위치(예: "관점 비교") 본문에서 우연히 hit할 가능성
  있으나 본 함수는 FR 블록 한정 검사라 영향 미약
- bold 마커 + plain + 헤더 인라인 외 다른 양식(예: 굵은 점만 `• 심각도: medium`,
  HTML `<b>심각도</b>:`)은 미인식. 본 보강은 v0.42.1 가이드 양식 + 다운
  스트림 실측 양식 두 케이스 커버

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **`eval --harness` 항목 7 출력**: v0.42.4 적용 후 다운스트림 6건 FR이
   `FR-NNN ✅`로 정상 검출되는가? (이전 6건 "⚠ 심각도 없음" 오경보 → 0건)
2. **다른 양식 발견 여부**: bold/plain/헤더 인라인 외 다른 필드 양식이
   본 다운스트림 migration-log.md에 존재하는가?

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.



## v0.42.3 — eval_cps_integrity Feedback Reports 인식 보강 + self-verify 모호성 정밀화 (2026-05-10)

### 변경 내용

다운스트림 v0.42.1 적용 후 측정된 eval --harness 결과 medium 우선순위 정비.

- **5-4 (eval_cps_integrity.py)**: `check_feedback_reports`의 정규식이
  `## Feedback Reports` (top-level 헤더)만 매칭하던 결함을 `### Feedback Reports`
  (버전 섹션 내 서브헤더) 양면 매칭으로 보강. FR 헤더 레벨도 `### FR-NNN` +
  `#### FR-NNN` 양면 지원. 같은 FR ID 중복 방지(set). 다운스트림이 어느
  양식을 써도 FR 항목 검출되도록 자율성 보존
- **5-4 회귀 가드**: `test_eval_harness.py`에 4건 추가 (top-level / 서브헤더 /
  필수 필드 누락 / 파일 부재). 11/11 통과
- **5-5 (self-verify.md)**: "**가능하면:** dev 서버 부팅" 모호 표현을
  "**UI/frontend 변경 시 필수**" + "**그 외(백엔드·CLI·문서·hooks·스크립트) 선택**"
  명확 트리거로 정밀화. CLAUDE.md "UI 또는 frontend 변경" 원칙과 정합

근거 문서: `docs/decisions/hn_eval_harness_medium_fixes.md`.

### 자동 적용 항목

- `.claude/scripts/eval_cps_integrity.py` (`check_feedback_reports` 정규식 + 파싱 로직)
- `.claude/scripts/tests/test_eval_harness.py` (회귀 가드 4건 추가)
- `.claude/rules/self-verify.md` (검증 항목 트리거 명확화)

### 수동 적용 항목

없음. 다음 `eval --harness` 호출부터 자동으로 새 인식 로직 적용.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -v
# 11 passed (기존 7 + 신규 4)
grep -nE "UI|frontend" .claude/rules/self-verify.md | head -3
```

### 회귀 위험

- 회귀 테스트 4건 통과 + 전체 86 passed 확인 (Phase 1 + Phase 2 회귀 0)
- 다운스트림 양식이 `## Feedback Reports` (top-level) + `### Feedback Reports`
  (서브헤더) 외 다른 헤더 레벨(예: `# Feedback Reports`)을 쓰면 미인식. 본
  보강은 v0.42.1 가이드 양식과 다운스트림 실측 양식 두 케이스만 커버
- 한 migration-log.md에 같은 FR-NNN ID가 여러 섹션에 출현하면 첫 번째만
  인식 (set으로 중복 방지). 의도된 설계 — 다른 ID라면 둘 다 출력

### 다운스트림 보고 요청

upstream이 본 보강의 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **eval --harness 항목 7 출력**: v0.42.3 적용 후 `eval --harness` 실행 시
   migration-log.md의 FR 항목이 정상 검출되는가? (FR-NNN ✅ 또는 ⚠️ 출력)
2. **양식 정합성**: 다운스트림 migration-log.md의 헤더 레벨 (top-level
   `## Feedback Reports` vs 서브헤더 `### Feedback Reports`) 어느 쪽이 사용되는지

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.



## v0.42.2 — Step 9.6 USER_OWNED_FILES 화이트리스트 디렉토리 단위 확장 (FR-006) (2026-05-10)

### 변경 내용

다운스트림 v0.42.1 적용 측정에서 보고된 FR-006(11건 USER_OWNED 오분류) 후속 처리.
직전 wave에서 Step 9.6 분류 코드가 산문 정의보다 좁게 하드코딩됐던 결함 수정.

- **Step 9.6 분류 코드**: `.claude/rules/{naming,coding,docs}.md` 3 파일
  매칭 → `.claude/rules/*.md|.claude/agents/*.md` 디렉토리 단위로 확장
- **산문 정의 갱신**: 사용자 전용 영역을 디렉토리 단위 광범위로 명시.
  starter 소유 명백 영역(`.claude/skills/*` 비-starter_skills · `.claude/scripts/*` ·
  `.claude/HARNESS_MAP.md` · `.claude/HARNESS.json`)은 USER_OWNED 분류
  금지로 false-negative 방어 명시
- **시뮬레이션 검증**: FR-006 보고된 11건이 USER_OWNED 8 + STARTER_SKILL 3 +
  UNAPPLIED 0으로 100% 정상 분류 (rules 5건 + agents 3건이 USER_OWNED로 정상 합류)

본 보강은 v0.42.1이 silent fail의 새 변종(USER_OWNED 오분류 → 사용자 피로)을
만든 형태를 수정. P3 영역 그대로 (Solution 정의 변경 아님 — 메커니즘 강화).

근거 문서: `docs/decisions/hn_upgrade_silent_fail_guards.md` Phase 5 + 변경 이력.

### 자동 적용 항목

- `.claude/skills/harness-upgrade/SKILL.md` (Step 9.6 산문 정의 + 분류 코드)

### 수동 적용 항목

없음. 다음 upgrade 시 자동으로 새 분류 적용.

### 검증

```bash
grep -nE "rules/\*\.md|agents/\*\.md" .claude/skills/harness-upgrade/SKILL.md
# Step 9.6 영역에서 hit (3건 이상)
```

### 회귀 위험

- 시뮬레이션 검증만 수행 (실제 다운스트림 환경 다중 사례는 미실증)
- starter 소유 영역에서 starter가 정당 변경 의도한 파일이 USER_OWNED에
  해당하지 않아도 안전 — 명시 화이트리스트만 USER_OWNED 분류
- 다운스트림이 `.claude/scripts/` 같은 starter 소유 영역을 자체 customize
  하는 케이스는 false-positive(UNAPPLIED 오분류)로 잡힘. 권장 패턴은 자체
  스크립트를 별 디렉토리에 두는 것 — 본 화이트리스트 정책과 정합

### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **Step 9.6 분류 정확도**:
   - USER_OWNED_FILES / STARTER_SKILL_FILES / UNAPPLIED_FILES 각 카운트
   - false-positive 발생 여부 (starter 소유 영역에서 정당 변경한 파일이 UNAPPLIED 오분류)
   - 사용자가 수동 분류 보정한 항목 수 (FR-006 같은 사례)

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷.



## v0.42.1 — harness-upgrade silent fail 차단 보강 (FR-001/002/003) (2026-05-10)

### 변경 내용

다운스트림 v0.42.0 upgrade 측정에서 보고된 silent fail 3건의 알고리즘 갭
보강 (FR-001~003).

- **FR-001 (Step 5)**: 3-way merge 직전 base↔ours sanity check 추가.
  frontmatter `name:` 필드 변경 시 즉시 ALERT, base↔ours 라인 차이율 70%
  이상 시 본체 swap 의심 confirm 강제. 3택 (Y 통과 / N theirs 강제 교체 /
  S 파일 skip) 처리. 다운스트림 `eval/SKILL.md` 본체가 `implementation/SKILL.md`
  로 swap된 채 3회 upgrade 통과한 사례 차단
- **FR-002 (Step 9.6 신설)**: upstream 정합성 자동 검증 단계. starter 영역
  한정 `git diff harness-upstream/main HEAD --name-only` 실행 후 USER_OWNED_FILES
  / STARTER_SKILL_FILES / UNAPPLIED_FILES 3 카테고리 분류. 미적용 1건+ 시
  사용자 알림 + 처리 옵션(재실행 / 무시 / 중단). 다운스트림 v0.42.0에서
  30+ 파일이 silent 미적용 통과한 사례 차단
- **FR-003 (Step 10)**: 완료 보고에 사용자 전용 / starter_skills / upstream
  정합성 미도달 카운트 추가. Step 9.6 배열 length 그대로 주입(재계산 금지).
  미도달 1건+ 강조 + 파일 목록 + migration-log.md `### 이상 소견`에 자동
  append. 5+ 사용자 전용 항목은 요약 + 전체 보기 옵션
- **MIGRATIONS.md 표준**: `## Feedback Reports` 절에 "버전 섹션 표준"
  추가 — 6번 서브섹션 "다운스트림 보고 요청"(선택) 정의. 자동 검증 불가
  영역 보강 시 사용

근거 문서: `docs/decisions/hn_upgrade_silent_fail_guards.md` (이 wave 후 이동).

### 자동 적용 항목

- `.claude/skills/harness-upgrade/SKILL.md` (Step 5 본체 swap sanity check
  + Step 9.6 신설 + Step 10 보고 포맷 갱신)
- `docs/harness/MIGRATIONS.md` (`## Feedback Reports` 절에 버전 섹션 표준 추가)

### 수동 적용 항목

없음. 다음 upgrade 시 자동으로 새 절차 적용.

### 검증

```bash
grep -nE "본체 swap|차이율|name:" .claude/skills/harness-upgrade/SKILL.md
grep -nE "정합성 미도달|UNAPPLIED_FILES" .claude/skills/harness-upgrade/SKILL.md
grep -nE "버전 섹션 표준|다운스트림 보고 요청" docs/harness/MIGRATIONS.md
```

### 회귀 위험

- upstream 격리 환경에서 SKILL.md 절차 변경만 검증. 실제 3-way merge
  sanity check 동작은 다음 다운스트림 upgrade에서 운용 측정 필요
- base↔ours 차이율 70% 임계는 이론값. false-positive·false-negative 분포는
  다운스트림 측정으로만 확인 가능 (의도된 대규모 리팩토링과 본체 swap
  구분이 임계 안에서 가능한지 미실증)
- Step 9.6 USER_OWNED_FILES 정의(naming/coding/docs.md 한정)가 다운스트림
  실제 사용자 전용 영역과 정합한지 미실증. 다운스트림이 다른 파일을 정당
  커스터마이징하면 미도달로 오분류 가능 — 보고 채널 1로 측정 예정

### 다운스트림 보고 요청

upstream이 본 변경의 운용 효과를 측정하기 위해 다음 관찰을 요청합니다.
다음 upgrade 시 `docs/harness/migration-log.md` `## Feedback Reports` 섹션에 응답:

1. **Step 5 본체 swap sanity check 발화 빈도**:
   - 검사 1(`name:` 필드 변경 ALERT) 발화 횟수 / 검사 2(차이율 ≥70% 의심) 발화 횟수
   - 사용자 3택 결과 분포: Y(통과) / N(theirs 강제) / S(skip)
2. **Step 9.6 정합성 미도달 카운트**:
   - USER_OWNED_FILES / STARTER_SKILL_FILES / UNAPPLIED_FILES 각 카운트
   - 미도달 1건+ 시 사용자 선택: 재실행 / 무시 / 중단
3. **Step 10 보고 가독성 + 자가 발화 의존 잔존 여부**:
   - "정합성 미도달" 강조가 사용자 인지에 도달했는가
   - 사용자가 보고를 보고 추가 액션을 취했는가
   - silent 제외 카운트가 "이게 진짜 보존 맞나?" 검토를 유발했는가

응답 형식: `migration-log.md` 본 버전 섹션 안에 FR 표준 포맷(관점·약점·실천·심각도).



## v0.42.0 — eval --harness CLI 백엔드 + 검증 도구 정렬 진단 (2026-05-10)

### 변경 내용

eval --harness가 LLM 해석 의존이던 결정적 측정 항목을 CLI 백엔드(`eval_harness.py`)
로 이전. 단일 진입점에서 항목 5(CPS 무결성)·6(방어 활성)·7(피드백 리포트)·
8(검증 도구 정렬 신규)을 결정적으로 실행. SKILL.md 본문은 LLM 해석 영역
(항목 1~4: 모호성·모순·부패·강제력 배치)만 담당.

신규 항목 8(검증 도구 정렬 진단)은 TypeScript/JavaScript 프로젝트에서
검증 도구가 산출물(dist/build)이 아닌 소스를 직접 보도록 보장 — 4신호
(A 워크스페이스·B codegen 의존·C dist 자체 소비·D outDir 분리) 검출 후
신호 hit 패키지의 정렬 상태 측정. 외부 명령(npm·tsc) 호출 0건 (Python·Go·
Rust 다운스트림 차단 회피).

본 wave는 직전 wip_util_ssot(v0.41.0) 결정의 후속 의무 박제 — eval_harness.py가
wip_util import해서 4중 파편화 방지.

근거 문서: `docs/decisions/hn_eval_harness_cli_lsp_drift.md` (이 wave 후 이동).

### 자동 적용 항목

- `.claude/scripts/eval_harness.py` (신설 — CLI 백엔드 단일 진입점)
- `.claude/scripts/tests/test_eval_harness.py` (신설 — 7건 회귀 가드)
- `.claude/scripts/tests/conftest.py` (`eval` marker 등록)
- `.claude/skills/eval/SKILL.md` (--harness 섹션 재구성 + 항목 8 추가)
- `.claude/HARNESS_MAP.md` (Scripts 섹션 갱신: stop-guard.py·post-compact-guard.py·
  eval_harness.py·test-bash-guard.sh·test-debug-guard.sh 등재)

### 수동 적용 항목

없음. eval --harness 호출 흐름이 자동으로 새 CLI 백엔드를 사용. 구버전
호환을 위해 `eval_cps_integrity.py` 직접 호출도 그대로 작동.

### 검증

```
python3 .claude/scripts/eval_harness.py
# 항목 5·6·7·8 보고 출력 (TypeScript 미사용이면 항목 8 SKIP)
python3 -m pytest .claude/scripts/tests/test_eval_harness.py -q
# 7 passed
```

### 회귀 위험

- upstream 격리 환경(Windows + Git Bash + Python 3.12)에서 관찰된 범위 내 검증
- 항목 8(검증 도구 정렬)은 TypeScript 프로젝트가 없는 starter에서는 SKIP만
  실증됨. 실제 모노레포 + codegen 환경의 신호 검출은 미테스트 (픽스처 단위
  테스트만 통과)
- `.claude/harness-overrides.md` 의도적 비정렬 마커는 명세만 정의. 실제
  다운스트림 운용 검증은 미수행



## v0.41.0 — WIP 파싱 SSOT 통합 (wip_util.py + post-compact-guard.py 전환) (2026-05-10)

### 변경 내용

WIP frontmatter 파싱 로직이 3곳에 파편화돼 있던 상태(session-start.py·
post-compact-guard.sh·stop-guard.py)를 단일 SSOT(`utils/wip_util.py`)로
통합. 동시에 `post-compact-guard.sh`를 Python으로 전환해 sed/grep/awk
혼재 제거.

stop-guard 자기복제 케이스가 다른 sh에 적용되는지 14개 sh 점검 결과,
적합 1건(post-compact-guard.sh) + 부적합 12건. 1차 결론에서 사용자 통찰
("언어 전환이 아닌 로직 통합")로 SSOT 부재가 진짜 원인이라는 결론에
도달, 본 wave에서 점검·결정·실행을 단일 commit으로 처리.

근거 문서: `docs/decisions/hn_wip_util_ssot.md` (이 wave 후 이동).

### 자동 적용 항목 (다운스트림이 fetch 시 자동)

- `.claude/scripts/utils/__init__.py` (신설)
- `.claude/scripts/utils/wip_util.py` (신설 — `parse_wip_file()` + `is_in_progress()` SSOT)
- `.claude/scripts/session-start.py` (parse_wip_file 정의 제거 → import)
- `.claude/scripts/stop-guard.py` (is_in_progress 정의 제거 → import)
- `.claude/scripts/post-compact-guard.py` (신설 — sh 1:1 포팅)
- `.claude/scripts/post-compact-guard.sh` (삭제 — dead code 동시 제거)

### 수동 적용 항목

1. `.claude/settings.json` PostCompact hook command 갱신
   `bash .claude/scripts/post-compact-guard.sh` → `python3 .claude/scripts/post-compact-guard.py`
   (settings.json을 다운스트림이 자체 커스터마이즈한 경우 3-way merge 후 확인)
2. `bash .claude/scripts/post-compact-guard.sh`를 호출하는 외부 스크립트가
   있으면 동일하게 갱신 (downstream-readiness.sh가 hook 누락 자동 감지)

### 검증

```
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); from utils.wip_util import parse_wip_file"
echo '{}' | python3 .claude/scripts/post-compact-guard.py
python3 .claude/scripts/session-start.py
echo '{}' | python3 .claude/scripts/stop-guard.py
```

### 회귀 위험

- upstream 격리 환경(Windows + Git Bash + Python 3.12)에서 관찰된 범위 내 검증
- Linux/macOS·다른 Python 버전 미테스트
- WSL·Docker·CI 등 다른 실행 환경의 sys.path 동작 미검증
- 다운스트림이 `.claude/scripts/utils/` 경로에 자체 모듈을 두던 경우 충돌
  가능성 (현재 업스트림에서는 utils/ 폴더 부재였음)



## v0.40.2 — stop-guard.py / session-start.py cwd 보정 (2026-05-10)

### 변경 내용

v0.40.1 직후 Stop hook 실행 시 `python3 .claude/scripts/stop-guard.py`가
`.claude/scripts/.claude/scripts/stop-guard.py`로 이중 prepend되어 ENOENT
발생. Windows + Claude Code 환경에서 Stop hook의 cwd가 repo root가 아닌
`.claude/scripts/`로 들어오는 케이스 실측. 이전 `bash .sh` 시절에는 우연히
동작했을 가능성 있으나 .py 전환 후 즉시 노출.

- `.claude/scripts/stop-guard.py` — `os.chdir(Path(__file__).resolve().parents[2])`
  cwd 보정 1줄 추가 (import 직후)
- `.claude/scripts/session-start.py` — 동일 안전망 추가 (현재는 정상
  작동하나 동일 패턴 일관성)

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
cd .claude/scripts && python3 stop-guard.py    # ENOENT 없이 정상 출력
cd .claude/scripts && python3 session-start.py # 정상 출력
```

### 회귀 위험

upstream 격리 환경(Windows + Git Bash) 실측에서는 cwd 보정이 정상 작동
범위 내. Linux/macOS에서 hook cwd 거동은 미테스트 — 다른 OS의 Claude
Code hook이 cwd를 어떻게 설정하는지에 따라 redundant할 수 있으나 무해
(이미 repo root이면 chdir도 repo root). `__file__` 기반 절대경로라
cwd 무관하게 결과 동일.

downstream: harness-upgrade 적용 후 hook 재발화 시 ENOENT 사라짐 확인 권장



## v0.40.1 — stop-guard.sh → stop-guard.py 전환 (자기증식 차단) (2026-05-10)

### 변경 내용

v0.40.0 stop-guard.sh 도입 직후 검증에서 `grep -c || echo 0` Git Bash
호환 결함 발견·1회 fix. 이 1회 fix가 자기증식 신호 — bash 파싱 3종 혼재
(awk×2·grep×2)에 추측성 방어 코드 누적이 향후 조건 확장마다 증가할
구조. pre-emptive Python 전환:

- `.claude/scripts/stop-guard.py` 신설 — bash 4개 동작 절 1:1 포팅
  (미커밋 카운트·in-progress WIP·조건 A·B·C AND 발화·memory 환기/cleanup)
- `.claude/scripts/stop-guard.sh` 삭제 (signal_dead_code_after_refactor.md
  답습 — 호출 제거와 정의 제거 동시)
- `.claude/settings.json` Stop hook command 갱신: `bash` → `python3`
- session-start.py와 일관된 frontmatter 파싱 패턴 + Windows cp949 안전
  처리 동일 답습

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
python3 .claude/scripts/stop-guard.py
# 기존 sh와 동일 출력 4개 절 + 조건 A·B·C hit 시 stderr + audit log
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 sh·py 출력 1:1 일치 확인 (trailing
  space 제외). Linux/macOS 미테스트
- audit log 형식 호환 (`{ts} | A·B·C hit | {files}` 동일) — 기존 누적
  로그 무수정
- Python interpreter 시동 비용 ~50~100ms — session-start.py와 동일
  운용 검증된 비용
- settings.json hook command 1줄 변경 — Reversibility 5/5 (원복 비용 0)



## v0.40.0 — P8 Phase 3: incident 회상 + signal lifecycle + stop-guard 조건 C (2026-05-10)

### 변경 내용

P8 자가 의존 보강 3축 1차 도입 (advisor + 사용자 라운드 합의):

- **D-Lite — `session-start.py` `section_incidents()` 신설**: 현재 WIP
  frontmatter `domain` ∩ `docs/incidents/*.md` `domain`, 최근 30일
  `created` 필터, 최대 3건 자동 출력. tags ∩ symptom-keywords 매칭은
  복잡도·소급 적용 부담으로 Phase 4 유보 (advisor 권고)
- **E — signal lifecycle 변경**: incidents 승급 시 signal 파일 **삭제
  → `archived: true` 마커 잔존**으로 변경. session-start.py가 archived
  신호를 약한 톤(`· (archived) ...`)으로 출력. 회상 다리 유지
  - `rules/memory.md` "## 신호 파일" 절 갱신
  - `session-start.py` `section_signals()` archived 분기 추가
- **B — `stop-guard.sh` 조건 C 확장 (Soft + Dry-run)**: 기존 미커밋·
  in-progress 알림에 더해 조건 A·B·C AND 발화 추가:
  - A: git status 수정 파일 있음
  - B: 변경된 WIP 중 status: in-progress 있음
  - C: 그 WIP에 빈 체크박스 `- [ ]` 또는 BIT 판단 블록 부재
  - hit 시 stderr 1줄 + `.claude/memory/stop_hook_audit.log` append
    (gitignore). 차단 아님 — 측정용. Phase 4 Hard Stop 결정 근거
- 신규 signal 4건 추가 (Phase 2.5, 별도): dead code 잔존·WIP move
  dead link·AC 미체크·자동화 불가 검증 단락. 모두 `hn_commit_process_gaps`
  (2026-04-27) 인용

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

다운스트림 권장 (선택):

- `docs/incidents/*.md` frontmatter에 `domain:` 명시 (D-Lite 매칭 입력).
  미명시 incident는 출력 대상 제외 — 회귀 아님, 보강 기회 누락만
- 향후 incidents 등록 시 `symptom-keywords` 명시 (Phase 4 매칭 강화 대비)

### 검증

```bash
python3 .claude/scripts/session-start.py 2>&1 | grep -E "(반복 신호|incident)"
# 현재 WIP domain 매칭 incident 1~3건 출력 확인

python3 .claude/scripts/stop-guard.py   # v0.40.1에서 sh → py 전환
# A·B·C AND 조건 hit 시 "🛑 [stop-guard A·B·C]" stderr 출력 확인

cat .claude/memory/stop_hook_audit.log
# hit 기록 누적 확인 (gitignore — 다운스트림 본인 환경에서만 잔존)
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 75 passed (회귀 0) 확인. Linux/macOS 미테스트
- `section_incidents()`는 incident frontmatter `domain`·`title`·`created`
  3 필드 모두 있어야 출력. 누락 시 침묵 (회귀 아님)
- `archived: true` 마커는 backward compatible — 기존 signal 파일 무수정.
  마커 없는 signal은 기존 톤 유지
- stop-guard 조건 C는 Soft 모드 — stderr 1줄만, 차단 0. 노이즈 위험
  낮음. 단 다운스트림이 BIT 판단 블록 양식 다르게 쓰면 has_bit 매칭이
  `^\[BIT 판단\]` 정확 일치 요구로 false-positive (BIT 누락 알림 과다)
  가능. 운용 audit 로그로 검토 후 패턴 완화 검토
- audit 로그는 gitignore — 다운스트림 본인 환경에서만 잔존. upstream
  공유 안 됨

### 운용 측정 계획

starter 본인 다음 5~10 commit 동안:

1. `.claude/memory/stop_hook_audit.log` hit 빈도 + 유효 경고/노이즈 비율
2. P8 자기증명 카운트 (commit별 자가 의존 변종 발생)
3. `section_incidents()` 출력 hit rate

데이터 누적 후 Phase 4 진입 결정 (Hard Stop 도입 또는 조건 정밀화).



## v0.39.0 — BIT 강제 트리거 보강 (debug-guard.sh 키워드 사전 확장) (2026-05-10)

### 변경 내용

- CPS P8 신설: "자가 발화 의존 규칙의 일반 실패". 다운스트림에서 BIT
  (bug-interrupt) 발화 0건 실측 기반 (LSP stale dist 결함 케이스에서 메커니즘
  0 작동). S8 1차 초안 — "강제 트리거 우선 + 자가 의존 보조". 충족 기준
  확정은 owner 승인 후
- `.claude/scripts/debug-guard.sh`: 키워드 사전 17개로 확장 — 한국어 `에러|
  버그|실패|오류|크래시|충돌`, 영어 `error|bug|fail|exception|panic|crash|
  traceback|stacktrace|regression|broken|conflict`. hit 시 기존
  debug-specialist 안내 + 신규 BIT Q1/Q2/Q3 적용 안내 둘 다 출력
- `.claude/scripts/test-debug-guard.sh`: 신규 회귀 가드. 22/22 통과 (hit 17 +
  miss 5, false-positive 가드 포함)
- `.claude/rules/bug-interrupt.md`: "## 강제 트리거 (debug-guard.sh)" 절 추가.
  키워드 SSOT는 hook 스크립트로 위임 (룰에 박지 않음)
- `.claude/HARNESS_MAP.md`: CPS 테이블 P8 행 추가 (defends-by=bug-interrupt,
  enforced-by=debug-guard.sh)

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영. 수동 액션 없음.

### 검증

```bash
bash .claude/scripts/test-debug-guard.sh
# 22/22 통과 기대
```

다운스트림 운용에서 사용자가 증상 키워드 발화 시 두 안내 출력 확인.

### 회귀 위험

- Windows + Git Bash 격리 환경에서 22/22 통과 확인. Linux/macOS 미테스트
- 키워드 사전 확장은 누적 — 기존 v0.38.5까지의 6개 키워드 모두 포함, 신규
  11개 추가만. 기존 hit 케이스 회귀 없음
- BIT 안내 추가 출력은 stdout 경로 — 기존 debug-specialist 안내와 충돌
  없음 (둘 다 누적 출력)
- false-positive 가드: "원인" 키워드 제외 ("원인 분석해줘"류 회피).
  실측 누적 후 사전 재조정 가능



## v0.38.5 — Python 콘솔 인코딩 안전 처리 (Windows cp949 환경) (2026-05-08)

### 변경 내용

- `.claude/scripts/eval_cps_integrity.py`: 진입점에 `sys.stdout/stderr.reconfigure(encoding="utf-8")` 안전 처리 추가
  - Windows cp949 콘솔에서 emoji `✅` 출력 시 `UnicodeEncodeError` 발생하던 결함 차단
  - `PYTHONIOENCODING=utf-8` prefix 없이도 정상 동작
- `.claude/scripts/session-start.py`: 동일 안전 처리 추가
- `.claude/scripts/docs_ops.py`: 동일 안전 처리 추가 — 한글 mojibake 출력(`## ���� �̵�`) 정상화
- 결함 자체는 v0.0~v0.38.4 전 기간 잠재. eval --harness 박제 의심 점검 중 노출

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영.

### 검증

```bash
# Windows cp949 환경에서 PYTHONIOENCODING 없이 실행
python .claude/scripts/eval_cps_integrity.py
# emoji ✅ 정상 출력 확인

python .claude/scripts/docs_ops.py validate
# 한글 정상 출력 확인 (mojibake 없음)
```

### 회귀 위험

- Windows + Git Bash 격리 환경에서 3개 스크립트 실행 통과 확인
- 콘솔 인코딩이 이미 utf-8(Linux/macOS·`PYTHONIOENCODING=utf-8` 설정 환경)이면 reconfigure 분기 미실행 — 기존 동작 유지
- `sys.stdout.reconfigure`는 Python 3.7+ 필수. 미만 버전은 `except (AttributeError, OSError)` 분기로 silent fall-through (정상 환경에서는 도달 불가)
- `errors="replace"` 모드 — 표현 불가 문자는 `?`로 치환 (raise보다 safer)



## v0.38.4 — completed 봉인 오탐 수정 — reopen→move 정상 절차 면제 (2026-05-08)

### 변경 내용

- `pre_commit_check.py`: completed 봉인 보호 로직 오탐 수정
  - reopen→move 절차 경유 파일이 rename 두 번 상쇄로 M(modify)으로 분류되어 차단되던 버그 수정
  - `docs_ops.py move`가 완료 시 `session-moved-docs.txt`에 경로 기록, pre-check이 대조해 면제
- `docs_ops.py`: `move` 완료 시 `.claude/memory/session-moved-docs.txt` 기록 추가
- `rules/memory.md`: session 파일 목록 2→3개 갱신 (`session-moved-docs.txt` 추가)
- 회귀 테스트 T42.9(면제), T42.10(무단 변경 차단) 추가

### 적용 방법

자동. `harness-upgrade` 실행 시 자동 반영.

### 검증

```bash
python3 -m pytest .claude/scripts/tests/test_pre_commit.py -m gate -q
# 22 passed 확인
```

### 회귀 위험

- upstream 격리 환경(Windows)에서 gate 22 passed 확인
- `session-moved-docs.txt` 미생성 환경(세션 첫 커밋)에서는 면제 미적용 → 기존 동작 유지
- Linux/macOS 미테스트



## v0.38.3 — 침묵하는 방어 가시화 + harness-upgrade 지식 내면화 단계 (2026-05-06)

### 변경 내용
- `.claude/scripts/bash-guard.sh` — 차단 시 `.claude/memory/signal_defense_success.md`에 background append. P4 방어 활성 데이터 축적.
- `skills/eval/SKILL.md` — `--harness` 항목 6번 추가: signal_defense_success.md 존재·최근 기록 표시 (기존 6번은 7번으로 번호 이동)
- `skills/harness-upgrade/SKILL.md` — Step 10 완료 직후 방어 기전 설명 단계(6번) 추가: What이 아닌 Why 포함 강제
- `docs/guides/project_kickoff.md` — S4 추가 방어 레이어 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 다음 harness-upgrade 시 Step 10 완료 직후 방어 기전 설명을 받게 됨 — "왜 이런 제약이 있는가" 이해 기회
- `.claude/memory/signal_defense_success.md`가 자동 생성되어 eval --harness에서 방어 활성 상태 확인 가능



## v0.38.2 — HARNESS_MAP MVR 섹션 + 에이전트 빠른 진입 가이드 (2026-05-06)

### 변경 내용
- `.claude/HARNESS_MAP.md` — `## MVR (작업유형별 최소 필수 규칙셋)` 섹션 추가: 7개 작업유형별 Rules 2~3개 압축 매핑 (구현·커밋·디버그·문서·eval·harness-dev·설정변경)
- `.claude/HARNESS_MAP.md` — 최상단에 "⚡ 에이전트 빠른 진입" 가이드 추가: MAP 전체 Read 금지, MVR → 역추적 2단계 진입점 명시
- `docs/guides/project_kickoff.md` — S5 MVR 구현 완료 승격 상태 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 참고
- 에이전트가 HARNESS_MAP 전체를 읽는 대신 `## MVR` 섹션만 참조하도록 유도하면 컨텍스트 절감 효과 기대
- 다운스트림은 자기 프로젝트 작업유형에 맞게 MVR 섹션 확장 가능 (harness-upgrade가 덮어쓰지 않는 영역에 추가)



## v0.38.1 — 피드백 채널 포맷 규격화 + bash-guard 우회 차단 강화 (2026-05-06)

### 변경 내용
- `docs/harness/MIGRATIONS.md` — `## Feedback Reports` 섹션 추가: 다운스트림 → upstream 역방향 피드백 포맷 규격화 (FR-NNN, 관점·약점·실천·심각도 4필드)
- `skills/eval/SKILL.md` — `--harness` 점검 항목 6번 추가: migration-log.md Feedback Reports 포맷 검증
- `.claude/scripts/eval_cps_integrity.py` — 피드백 리포트 포맷 자동 검증 로직 추가 (`check_feedback_reports`)
- `.claude/scripts/bash-guard.sh` — 간접 실행 차단 강화: `eval`/`sh -c`/`bash -c` 패턴 + 역슬래시 이스케이프(`git\ commit`) 정규화
- `docs/guides/project_kickoff.md` — P4·P5·P7 운용 약점 + S3·S4·S5 방향 갱신 (다운스트림 피드백 반영)
- `.claude/HARNESS_MAP.md` — P4·P5 row 갱신

### 적용 방법
- **자동**: 파일 덮어쓰기로 적용됨
- **수동**: 없음

### 다운스트림 권장 사항
- `docs/harness/migration-log.md`에 `## Feedback Reports` 섹션 추가 후 발견한 이상 소견·구조 관찰을 FR-NNN 형식으로 기록하면 eval --harness가 포맷 검증



## v0.38.0 — P4·P7 방어 실질화 + HARNESS_DEV 이스케이프 경계 명확화 (2026-05-06)

### 변경 내용
- `agents/review.md` — 카테고리 9 추가: settings.json `hooks` 블록 argument-constraint 패턴 감지 [차단] (P4 방어 실질화)
- `agents/review.md` — 카테고리 10 추가: commit_finalize.sh 스킬 외부 직접 호출 감지 [경고]
- `docs/guides/hn_harness_organism_design.md` — frontmatter `problem: P1` → `problem: P7` 수정 (P7 인용 0건 해소)
- `skills/implementation/SKILL.md` — WIP 사전 준비 섹션에 "MAP 참조" 필드 추가 (MAP 활용 흔적 기록)
- `memory/signal_commit_skill_bypass.md` — 합법/금지 경로 경계 명확화

### 배경
- P4: hooks.md가 review에 위임 선언했으나 review.md에 해당 검증 항목 없었음 — dangling reference 수정
- P7: hn_harness_organism_design.md가 P7 작업인데 P1으로 잘못 등재됨 → P7 인용 0건의 직접 원인
- HARNESS_DEV: 스킬 내부 사용(합법) vs 외부 직접 호출(금지) 경계가 텍스트로만 존재 → review 카테고리로 보강

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.9 — CLAUDE.md 커밋 스킬 우회 금지 절대 규칙 추가 + 신호 파일 등록 (2026-05-06)

### 변경 내용
- `CLAUDE.md` — 절대 규칙에 "커밋은 반드시 `/commit` 스킬 경유. WIP 없어도 `--no-review` 플래그. `commit_finalize.sh` 직접 호출 금지" 추가
- `.claude/memory/signal_commit_skill_bypass.md` — 커밋 스킬 우회 반복 패턴 strong 신호 등록

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.8 — memory 신호 파일 + session-start 컨텍스트 매칭 주입 (2026-05-06)

### 변경 내용
- `rules/memory.md` — 신호 파일(`signal_*.md`) 형식 정의: domain·strength·candidate_p 3필드. lifecycle(weak→medium→strong→incidents 등록→삭제) 명시
- `scripts/session-start.py` — `section_signals()` 추가: 현재 WIP frontmatter domain과 매칭되는 신호만 출력. WIP 없으면 전체 출력.

### 배경
memory = 지속 신호 수집기 + CPS 보조 수단. incidents 등록 전 weak 신호를 보관하고, 같은 도메인 작업 시작 시 관련 신호만 선별 주입.

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.7 — HARNESS_MAP 연결 완성 — BIT·staging·implementation·review·harness-dev·eval·session-start (2026-05-06)

### 변경 내용
- `rules/bug-interrupt.md` — Q3 P# 매칭: HARNESS_MAP.md CPS 테이블 우선 진입 → 불가 시 project_kickoff.md 폴백. 관계 테이블에 HARNESS_MAP 추가
- `rules/staging.md` — 룰 4(CPS staged): cascade 범위 확인을 HARNESS_MAP defends-by 컬럼으로 안내
- `skills/implementation/SKILL.md` — Step 0 Problem 매칭: HARNESS_MAP CPS 테이블 우선 진입 명시
- `agents/review.md` — Solution 충족 기준 회귀: HARNESS_MAP serves 컬럼 확인 후 CPS 본문 Read
- `skills/harness-dev/SKILL.md` — 체크리스트에 HARNESS_MAP 정합 검증(eval_cps_integrity.py) 추가
- `skills/eval/SKILL.md` — --harness 결과 해석에 "관계 그래프 단절 N건" 항목 추가
- `HARNESS_MAP.md` — enforced-by-inverse 정정: session-start.py·post-compact-guard.sh·eval_cps_integrity.py. P5 표기 통일. 하향/상향 경로 분리. BIT 연계 역추적 절차
- `scripts/session-start.py` — section_harness_map() 추가: 세션 시작 시 MAP 미존재 경고
- `CLAUDE.md` — 하향/상향 경로 설명 갱신

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.6 — normalize_quote `**` 제거 + 박제 인용 수정 (2026-05-06)

### 변경 내용
- `pre_commit_check.py` `normalize_quote()`: CPS 본문의 `**bold**` 마크다운을 제거하지 않아 박제 감지 오작동 → `**` 제거 추가
- `docs/decisions/hn_verify_relates_precheck.md`: solution-ref `(부분)` 마커 제거 (50자 이내 원문)

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.5 — review tool call 과다 소모 근본 수정 (2026-05-06)

### 변경 내용
- `skills/commit/SKILL.md` — `## 지시` 블록: "영향 범위 파일 Read" 능동 권유 → "AC+컨텍스트로 판단 가능하면 Read 금지, Read+Grep 합계 3회 이내" 로 교체
- `agents/review.md` — `## 한도`: maxTurns 6→10 텍스트 동기화, "Read+Grep 3회 이내·8회 사용 후 추가 Read 금지" 명시

### 배경
commit/SKILL.md `## 지시`의 "영향 범위 항목이 있으면 해당 파일 Read" 문구가 AC 항목 N개당 Read N회를 유도. review.md의 "Read 최대 2회" 제한이 user prompt에 없어서 시스템 프롬프트 제한이 무시됨. (incident hn_review_maxturns_verdict_miss 5번째 재발 후 근본 수정)

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.4 — review maxTurns 6→10 + enforced-by/defends-by 정규식 오탐 수정 (2026-05-06)

### 변경 내용
- `agents/review.md` — `maxTurns: 6` → `maxTurns: 10` (verdict 출력 턴 확보)
- `eval_cps_integrity.py` — `enforced_empty_pat`: 마지막 컬럼이 아닌 중간 컬럼 구조 대응, 빈 문자열 always-match 제거
- `eval_cps_integrity.py` — `no_rule_pat`: 빈 문자열 대안 제거, "—"/"-" 명시 감지만

### 적용 방법
자동 적용.

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨.



## v0.37.3 — 하네스 유기체화 Phase 1~6 완료 (2026-05-06)

### 변경 내용
- `eval_cps_integrity.py` — `check_harness_map()` 추가: HARNESS_MAP.md vs 실제 파일 단절 감지 (rules/skills/agents/scripts 4섹션 + enforced-by 공백 + defends-by 공백)
- `.claude/HARNESS_MAP.md` — 유기체 구조 섹션 추가 (CPS=뇌·MAP=대혈관·docs/=미세혈관), 규칙 간 참조 맵 갱신
- `agents/review.md` — 카테고리 8 "SSOT 문서 미완독 감지" 추가 + HARNESS_MAP.md 역추적 진입점 절차
- `rules/docs.md` — "하네스 구성요소 메타데이터" 섹션 추가: defends:/serves:/enforced-by: 필드 형식 + Layer 배치 기준 + 판단 트리
- `skills/harness-upgrade/SKILL.md` — Step 9.3 신설: HARNESS_MAP.md 전파 확인
- `scripts/downstream-readiness.sh` — 섹션 4-pre 추가: HARNESS_MAP.md 존재 체크
- `CLAUDE.md` — "하네스 신경망 허브" 섹션 추가: HARNESS_MAP.md 참조 + CPS 기억 귀환 구조

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.



## v0.37.2 — P7 신설 + HARNESS_MAP.md 임시 생성 + defends 매핑 정정 (2026-05-06)

### 변경 내용
- `docs/guides/project_kickoff.md` — P7 "시스템 구성 요소 간 관계 불투명" 신설 (P1·P6의 구조적 원인)
- `.claude/HARNESS_MAP.md` — 하네스 신경망 허브 임시 생성 (CPS·Rules·Skills·Agents·Scripts·Domains 양방향 관계 지도)
- `.claude/rules/anti-defer.md`, `docs.md`, `memory.md`, `naming.md` — `defends: P5` → `defends: P7` 정정
- `.claude/scripts/eval_cps_integrity.py` — `PROBLEM_INFLATION_THRESHOLD` 고정 6 → `max(8, problem_count + 2)` 동적 계산
- `.claude/scripts/session-start.sh` — session-start.py로 완전 대체됨, 파일 삭제

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
- `security.md`는 다운스트림 앱 전용. 필요 시 `.claude/rules/security.md` 직접 추가 (starter_skills에 포함 안 됨)

### 회귀 위험
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.



## v0.37.1 — write-doc CPS 필드 강제 + 재개 절차 단일화 + review 폐기 필드 제거 (2026-05-05)

### 변경 내용
- `skills/write-doc/SKILL.md` — Step 3 프론트매터에 `problem:·solution-ref:` 필드 추가, 필수 필드 목록 갱신
- `skills/write-doc/SKILL.md` — Step 2 "완료 문서 재개" 절차를 `git mv` → `docs_ops.py reopen`으로 단일화
- `rules/docs.md` — "완료 문서 재개" 절차 동일하게 `docs_ops.py reopen`으로 단일화
- `agents/review.md` — "핸드오프 계약" Pass 행에서 폐기된 `wip_kind·has_impact_scope` 제거

### 적용 방법
자동 적용 (harness-upgrade가 파일 갱신).

### 수동 적용
없음.

### 회귀 위험
- write-doc으로 생성한 기존 WIP에 `problem·solution-ref`가 없으면 commit 시 pre-check 차단. 직접 frontmatter 추가 후 커밋.
- upstream 격리 환경에서만 확인됨. 다운스트림 환경 미테스트.



## v0.37.0 — session-start.py 신설 — bash spawn 제거로 세션 시작 66% 단축 (2026-05-05)

### 변경 내용
- `scripts/session-start.py` 신설 — session-start.sh의 완전 Python 재작성
  bash spawn 23~25회 → git subprocess 최소화. 실행 시간 0.9초 → 0.28초 (66% 단축)
- `settings.json` SessionStart hook: `bash session-start.sh` → `python3 session-start.py`

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·settings.json 갱신).

### 수동 적용
없음. python3는 이미 필수 의존성.

### 회귀 위험
- session-start.sh는 삭제되지 않음 (이 버전). 롤백 필요 시 settings.json 복원.
- src/ TODO 감지는 Python glob으로 대체 — bash grep과 동일 결과 확인됨.
- upstream 격리 환경(Windows/Git Bash)에서 0.28초 실측. Linux/macOS 미테스트.



## v0.36.4 — BIT 루프 단절 수정 — eval_cps_integrity NEW 집계 + bug-interrupt 문서 부패 제거 (2026-05-05)

### 변경 내용
- `eval_cps_integrity.py`: `P#:.*NEW` 패턴 grep 추가 — docs/WIP/·decisions/ 스캔 후 미처리 NEW 플래그 집계 출력. eval --harness 고리 4 단절 수정
- `rules/bug-interrupt.md` 순환 루프 다이어그램: "Phase 2 구현 예정" → "Phase 2 완료" (문서 부패 제거)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·rules/ 갱신).

### 수동 적용
없음.



## v0.36.3 — BIT Phase 4 — CPS staged 경고 + implementation Step 0 NEW 플래그 인식 (2026-05-05)

### 변경 내용
- `pre_commit_check.py` 룰 2: project_kickoff.md staged 시 다른 staged 파일 중 solution-ref 있으면 "인용 박제 재확인 필요" 경고 출력
- `implementation/SKILL.md` Step 0 Problem 매칭 표: BIT NEW 플래그 항목 추가 — WIP `## 발견된 스코프 외 이슈`의 `P#: NEW` 항목을 P# 등록 후보로 자동 인식

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.



## v0.36.2 — BIT Phase 3 — eval --harness NEW 플래그 집계 + pre-check CPS empty 경고 (2026-05-05)

### 변경 내용
- `eval/SKILL.md` --harness 보고 섹션: CPS 무결성에 `NEW 플래그 미처리` 집계 항목 추가
- `pre_commit_check.py`: `get_cps_text()` 빈 문자열 반환 시 "CPS 본문 없음 — 박제 감지 불가" 경고 추가 (harness-init 미완료 환경 사각지대 차단)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.



## v0.36.1 — BIT Phase 2 — session-start.sh 이슈 감지 + Step 0.8 기록 의무 (2026-05-05)

### 변경 내용
- `session-start.sh` 블록 2: WIP 파일에 `## 발견된 스코프 외 이슈` 섹션 감지 시
  세션 시작 알림. `problem: NEW` 플래그 있으면 "CPS 신규 P# 검토 필요" 강조
- `implementation/SKILL.md` Step 0.8: "분리 불필요" 판정 시 탐색 결과 기록 의무 명시 (갭 1 차단)

### 적용 방법
자동 적용 (harness-upgrade가 scripts/·skills/ 갱신).

### 수동 적용
없음.



## v0.36.0 — BIT(Bug Interrupt Triage) 규칙 신설 + CPS 순환 루프 설계 (2026-05-05)

### 변경 내용
- `rules/bug-interrupt.md` 신설 — 스코프 외 버그 발견 시 Q1/Q2/Q3 결정 트리
  자율 판단. 판단 기준 SSOT를 AC+CPS+security.md로 외부화
- `implementation/SKILL.md` Step 3에 BIT 참조 추가
- `rules/docs.md` CPS 변경 권한 — Problem 추가를 BIT Q3 경로에서도 Claude 단독 가능으로 명시

### 적용 방법
자동 적용 (harness-upgrade가 rules/ 갱신).

### 수동 적용
없음.



## v0.35.3 — CLAUDE.md 행동 원칙 AC·CPS 실질 내용으로 교체 (2026-05-05)

### 변경 내용
- CLAUDE.md "행동 원칙" 섹션을 추상 원칙(Think Before Coding·Goal-Driven Execution)에서
  AC·CPS 실질 내용(형식·필수 필드·SSOT 링크)으로 교체

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.



## v0.35.2 — CLAUDE.md 절대 규칙 + 진입점 보강 (2026-05-05)

### 변경 내용
- CLAUDE.md 절대 규칙에 `docs/WIP/ 파일 Write 직접 생성 금지` 추가
- CLAUDE.md 진입점 표에 "문서 생성 (코드 작업 수반) → /implementation" 항목 추가
- CLAUDE.md `<important>` 태그 조건에 Write 도구 직접 사용 명시

### 적용 방법
자동 적용 (harness-upgrade가 CLAUDE.md 갱신).

### 수동 적용
없음.



## v0.35.1 — starter_skills 필터링 구현 + harness-dev 등록

### 변경 파일

- `.claude/HARNESS.json` — `starter_skills`에 `harness-dev` 추가 (`"harness-init,harness-adopt,harness-dev"`)
- `.claude/skills/harness-upgrade/SKILL.md` — Step 6에 `starter_skills` 필터 로직 추가: ADDED 파일 중 `.claude/skills/{starter_skill}/` 경로는 다운스트림 전달 제외

### 적용 방법

자동 적용. 수동 작업 없음.

### 선택적 정리 (기존 다운스트림)

이전 버전에서 harness-upgrade를 통해 starter 전용 스킬 폴더를 받은 다운스트림은
삭제해도 무방 (기능상 문제 없음 — 실행하지 않으면 무해):

```bash
rm -rf .claude/skills/harness-init/
rm -rf .claude/skills/harness-adopt/
rm -rf .claude/skills/harness-dev/
```

harness-sync는 다운스트림도 사용하므로 삭제하지 않는다.

### 회귀 위험

- `starter_skills` 필터는 SKILL.md 절차 문서 변경 — Claude가 Step 6 실행 시 이 절차를 따름
- upstream 격리 환경에서 별도 테스트 없음. 운용 검증 필요



## v0.35.0 — doc-health 스킬 신설 + CLAUDE.md 진입점 추가

### 변경 파일

- `.claude/skills/doc-health/SKILL.md` — 신규 스킬. 하네스 도입 이전 레거시 문서를 반자동 정비 (abbr rename·CPS frontmatter 추가·archived 이동). eval --harness 진단 결과를 이어받아 4단계로 진행
- `.claude/skills/eval/SKILL.md` — `--harness` 결과에 doc-health 호출 권장 안내 추가 (abbr 없는 파일 5개+·CPS 누락 10개+·박제 의심 3건+ 시 트리거)
- `.claude/skills/harness-adopt/SKILL.md` — 완료 리포트 "다음 할 일"에 `/doc-health` 실행 권장 안내 추가
- `CLAUDE.md` — 진입점 테이블에 `/eval --harness`, `/doc-health` 행 추가
- `.claude/HARNESS.json` — `skills`에 `doc-health` 추가

### 적용 방법

자동 적용. 수동 작업 없음.

### 다운스트림 권장

레거시 문서(하네스 도입 이전 작성)가 많은 경우 `/eval --harness` → `/doc-health` 순으로 실행해 탐색 체인 정합성을 확보할 것.

### 회귀 위험

- 신규 스킬 추가만. 기존 스킬 로직 변경 없음
- CLAUDE.md 진입점 행 추가는 기존 행에 영향 없음



## v0.34.8 — completed 봉인 — 본문 마크다운 링크 경로 교체 면제

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 면제에 "본문 마크다운 링크 경로 교체" 추가: hunk 내 삭제(-) 라인이 있는 상태에서 링크 패턴(`[...](...)`)을 포함한 추가(+) 라인은 면제. 순수 추가(삭제 없는 링크 줄 추가)는 기존과 동일하게 차단
- `.claude/scripts/tests/test_pre_commit.py` — T42.7(링크 경로 교체 면제), T42.8(순수 추가 차단) 회귀 테스트 추가

### 적용 방법

자동 적용. 수동 작업 없음.

### 회귀 위험

- 면제 조건은 `-U0` diff 기준 hunk 단위. 같은 hunk에 `-` 없이 `+`만 있는 링크 줄은 여전히 차단
- upstream 격리 환경(Windows)에서 pytest gate 20/20 통과 확인. Linux/macOS 미테스트



## v0.34.7 — eval_cps_integrity 다운스트림 호환성 강화 + completed 봉인 frontmatter 면제

### 변경 파일

- `.claude/scripts/eval_cps_integrity.py` — `extract_cps_solution_ids()` 정규식 확장: `**S1**` 굵은 글씨 형식 인식 추가. `docs/harness/` 폴더를 스캔 제외 (upstream CPS 참조 문서 오탐 방지)
- `.claude/scripts/pre_commit_check.py` — completed 봉인 면제에 frontmatter 블록 내 변경 추가: `reopen → solution-ref 수정 → move` 정상 절차 후 차단되는 문제 해소

### 적용 방법

자동 적용. 수동 작업 없음.

### 회귀 위험

- `eval_cps_integrity.py` 정규식 변경은 `### S1` 패턴을 그대로 유지하면서 `**S1**` 추가. upstream CPS(`### S1` 형식)에 영향 없음
- `docs/harness/` 스캔 제외는 다운스트림 harness 자체 문서가 없는 프로젝트에서는 동작 무관
- `pre_commit_check.py` frontmatter 면제는 `---` 블록 내 라인에만 적용. 본문 변경은 기존과 동일하게 차단
- upstream 격리 환경(Windows)에서 71/71 통과 확인. Linux/macOS 미테스트



## v0.34.6 — eval Solution 충족 인용 분포 집계 + PRD 레이어 보강 (User Needs·milestones 샘플·harness-init 권고)

### 변경 파일

- `.claude/scripts/eval_cps_integrity.py` — `count_solution_refs()` 함수 추가. Solution별 frontmatter 인용 카운트 집계
- `.claude/skills/eval/SKILL.md` — CPS 무결성 결과 해석에 "Solution 충족 인용 분포" 가이드 추가
- `.claude/skills/harness-init/SKILL.md` — CPS 템플릿에 `### User Needs` 선택 섹션 추가, 규모별 선택적 레이어 권고 단락 추가
- `docs/guides/project_kickoff_sample.md` — `### User Needs` 섹션(Personas·Success Metrics) 샘플 추가
- `docs/guides/milestones_sample.md` — 신규 생성. 에픽 = 사용자 가치 묶음 원칙 + backlog/in-progress/done 추적 샘플
- `.claude/scripts/tests/test_pre_commit.py` — wipsync_repo fixture: 빈 커밋 방지 (`git status --porcelain` 체크 추가)

### 적용 방법

자동 적용. 수동 작업 없음.

### 선택적 활성화 (다운스트림 권장)

도메인 5개+ 또는 decisions 30+ 누적된 프로젝트:
1. `docs/guides/milestones_sample.md`를 `docs/guides/milestones.md`로 복사 후 에픽 정의
2. `docs/guides/project_kickoff.md`의 `### Context` 아래 `### User Needs` 섹션 작성

### 회귀 위험

- eval_cps_integrity.py 추가 함수는 기존 출력(박제 의심·Problem 인용 빈도)에 영향 없음. upstream 격리 환경(Windows)에서 71/71 통과 확인
- test_pre_commit.py fixture 수정은 WipSync 관련 10개 테스트에만 영향. 기존 로직 변경 없음
- Linux/macOS 미테스트



## v0.34.5 — supabase/migrations/*.sql PostgreSQL role 이름 오탐 면제

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — `S1_LINE_EXEMPT`에 `^supabase/migrations/.*\.sql$` 추가
- `scripts/install-secret-scan-hook.sh` — `EXEMPT_RE`에 `|^supabase/migrations/.*\.sql$` 추가 (동기화)
- `.claude/scripts/tests/test_pre_commit.py` — `test_supabase_migration_sql_exempt` 회귀 테스트 신규

### 다운스트림 영향

**`supabase/migrations/*.sql`의 PostgreSQL role DCL이 시크릿으로 오탐되어 커밋 차단되는 문제 해소**:

`GRANT ... TO service_role`, `REVOKE ... FROM service_role`, `CREATE POLICY ... = 'service_role'` 등
PostgreSQL DCL에서 role 이름 `service_role`이 시크릿 패턴 `service_role(?![A-Z_])`에 걸려
`line-confirmed` 차단됐음 (뒤 문자가 `;`·`,`·공백이라 negative lookahead 통과).

v0.34.5부터 `supabase/migrations/*.sql` 파일은 `S1_LINE_EXEMPT` 면제.
`scripts/install-secret-scan-hook.sh` grep 폴백도 동기화됨.

**잔여 위험**: `supabase/migrations/` 면제로 인해 해당 경로 파일에서 진짜 시크릿(`sb_secret_*` 등)
라인이 있어도 line-confirmed 미적용. 정상 워크플로우에서 migration SQL에 시크릿 리터럴을
하드코딩하는 경우는 없으므로 잔여 위험 낮음.

### 적용 방법

자동. `harness-upgrade` 후 별도 수동 적용 없음.
`scripts/install-secret-scan-hook.sh`를 재설치하면 grep 폴백에도 면제 반영됨:
```bash
bash scripts/install-secret-scan-hook.sh
```

### 검증

- `pytest -m secret` 5/5 통과 (`test_supabase_migration_sql_exempt` 신규 포함)
- 회귀 위험: 기존 4건 모두 통과 확인



## v0.34.4 — pre-check false-block 2건 수정 (AC 에러 메시지·service_role 환경변수 이름)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — AC 섹션 미탐지 에러 메시지 개선, `service_role` 패턴 negative lookahead 추가

### 다운스트림 영향

**이슈 1 — AC `**Acceptance Criteria**:` 형식 누락 시 에러 메시지 개선**:

`### Acceptance Criteria` 헤더 형식으로 AC 섹션을 작성하면 pre-check이
`AC Goal: 항목 누락`으로 차단했으나 원인 파악이 어려웠음. v0.34.4부터
"AC 섹션 없음. `**Acceptance Criteria**:` (bold 형식) 헤더가 필요합니다."
메시지로 즉시 원인 파악 가능. docs.md SSOT(bold 형식) 변경 없음.

**이슈 2 — `service_role` 환경변수 이름 참조 false-block 해소**:

`process.env.SUPABASE_SERVICE_ROLE_KEY` 등 대문자+언더스코어가 뒤에 오는
환경변수 이름이 `service_role` 시크릿 패턴에 걸려 line-confirmed 차단됐음.
v0.34.4부터 `service_role(?![A-Z_])` negative lookahead로 변수 이름은 면제.
`"service_role"` 값 리터럴·`role: service_role` 직접 노출은 계속 차단.

### 적용 방법

자동. `harness-upgrade` 후 별도 수동 적용 없음.

### 검증

- `pytest -m secret` 4/4 통과
- 회귀 위험: `service_role(?![A-Z_])` 패턴이 실제 시크릿 값을 false-negative할 가능성 — 실제 JWT 등 키 값에는 `_`가 뒤에 오지 않으므로 위험 없음



## v0.34.3 — completed 봉인 relates-to path 수정 면제 (dead-link 복구 루프 해소)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — 봉인 게이트 면제 목록에 `- path: <경로>` 라인 추가
- `.claude/scripts/tests/test_pre_commit.py` — T42.6 회귀 테스트 신규

### 다운스트림 영향

**v0.34.2 업그레이드 후 발생하는 루프 해소**:

v0.34.2의 verify-relates 전수 검사와 기존 completed 봉인이 충돌해 영구
차단 루프가 발생했음 — completed 문서의 dead relates-to를 수정하면 봉인이
차단, 차단 상태로는 수정 불가.

v0.34.3부터 completed 문서의 `- path: <경로>` 라인 변경은 봉인 면제.
**dead-link 복구(경로 수정·항목 제거)가 즉시 가능**.

### 적용 방법

자동. `harness-upgrade` 후 relates-to 경로 직접 수정 후 커밋 가능.

`verify-relates`로 확인 후 수정:
```bash
python3 .claude/scripts/docs_ops.py verify-relates
# 경로 수정 또는 항목 제거
git add <수정한 파일>
git commit ...
```

### 검증

- `pytest -m gate` 18/18 통과 (T42.6 신규 포함)
- 실측: completed 문서 `path:` 라인 수정 시 봉인 통과 + verify-relates 차단만 남음
- 회귀 위험: `path:` 면제가 봉인 우회로 악용될 가능성 낮음 — frontmatter 내 구조화된 경로 값이므로 본문 의미 변경과 구분 가능

### 결정 근거

다운스트림 보고: v0.34.2 upgrade 후 모든 커밋 차단. debug-specialist 진단
후 completed 봉인 면제 화이트리스트에 `path:` 추가로 해소.



## v0.34.2 — verify-relates pre-check 통합 (커밋 시 relates-to 전수 검사)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — 3.5단계 섹션 C 재설계: 기존 staged 파일 단독 검사 → `cmd_verify_relates` 전수 호출로 교체
- `.claude/scripts/tests/test_pre_commit.py` — `TestVerifyRelatesPrecheck` T45.1·T45.2 신규

### 다운스트림 영향

pre-check 3.5단계 C 동작 변경:

**이전**: staged 파일 자신의 frontmatter `relates-to`만 검사 (inbound 역검색 없음)

**v0.34.2**: `docs/` 전체 모든 파일의 `relates-to` 전수 검사. **기존 커밋된 파일의 깨진 ref도 차단**.

**영향**:
- 다운스트림에 사전 dead relates-to 부채가 있으면 첫 커밋 시 차단됨
- `python3 .claude/scripts/docs_ops.py verify-relates`로 상세 확인 후 경로 수정 또는 항목 제거
- 비용: docs/ 전체 검사 0.13s (다운스트림 N=18 환경 기준 — v0.34.1 다운스트림 검증 실측치)

### 적용 방법

`harness-upgrade` 후 즉시 `python3 .claude/scripts/docs_ops.py verify-relates` 실행. 미연결 건이 있으면 수정 후 커밋.

**수동 적용 필요**: 사전 부채 있는 다운스트림은 upgrade 후 첫 커밋 전 `verify-relates` 실행·수정 필수.

### 검증

- `pytest -m docs_ops` 27/27 통과 (기존 25 + 신규 2 — T45.1·T45.2)
- 실측: 깨진 ref 인위 생성 후 pre-check 차단 확인
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다른 파일시스템·인코딩 환경 재발 시 본 섹션 갱신

### 결정 근거

`docs/decisions/hn_verify_relates_precheck.md` — 다운스트림 v0.34.1 검증에서 relates-to dead link 7건 발견 후 debug-specialist 진단. H3 박제 ref 확정, 전수화가 근본 해결로 판단.



## v0.34.1 — amplification 후속 4 wave 처리 (cluster 게이팅·WIP 가시성·glob 가이드·adopt 안내)

### 변경 파일

- `.claude/scripts/docs_ops.py` — `cmd_cluster_update` 결정적 출력 + WIP 수집
- `.claude/scripts/tests/test_pre_commit.py` — `TestClusterUpdateGating` 3 케이스 신규
- `.claude/rules/docs.md` — "## 문서 탐색 > 기본 경로" 양쪽 wildcard + cluster 진입점 격상
- `.claude/rules/naming.md` — "왜 — 파일명이 곧 인덱스" bullet 갱신
- `.claude/skills/harness-adopt/SKILL.md` — Step 8 "다음 할 일" `/harness-init` 강조

### 다운스트림 영향

#### (c) cluster 재생성 게이팅 — 결정적 출력 + diff 비교
- `cluster-update`가 동일 본문이면 write skip → mtime noise 0
- cluster 양식·인터페이스 무변경. 자동 이행

#### (b) WIP cluster 가시성 — 진행 중 섹션 자동 등록
- cluster 본문에 `## 진행 중 (WIP)` 섹션 신규 (기존 `## 문서` 무변경)
- 사용자·에이전트가 cluster scan 한 번에 completed + 진행 중 발견
- 첫 호출 시 WIP 있는 도메인 cluster만 1회 갱신 후 안정. 추가 작업 불필요

#### (d) Glob 라우팅 태그 가이드 — 양쪽 wildcard 명시
- `docs.md`·`naming.md` 가이드 문구만 변경 (라우팅 태그 폐기 안 함)
- 사용자·에이전트가 `docs/**/*<abbr>_*` 양쪽 wildcard로 WIP 포함 발견 가능
- 다운스트림 WIP 양식 마이그레이션 불필요

#### (e) adopt-without-init 사전 안내 강화
- `harness-adopt` Step 8 "다음 할 일"에 `/harness-init` 미실행 시 implementation 차단됨을 명시
- (a) v0.34.0 차단 메시지와 이중 안전망 (사전 + 사후)
- 기존 adopt 완료 + init 미완료 다운스트림은 (a) 차단 메시지로 사후 안내. 추가 작업 불필요

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

다운스트림은 v0.34.1 적용 후 첫 commit 1회에 cluster 본문에 `## 진행 중 (WIP)`
섹션이 추가되며 (WIP 있는 도메인만), 이후 호출은 영향 도메인만 갱신.

### 검증

- `pytest -m docs_ops` 25/25 통과 (기존 22 + 신규 3)
- starter 실측: 멱등 호출 시 skip 2/2, 단일 cluster stale 시 영향 cluster만 갱신
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. POSIX bash 또는 다른
  파일시스템(mtime 정밀도)에서 멱등성 재발 시 본 섹션 갱신 필요

### 결정 근거

- `docs/decisions/hn_cluster_update_gating.md`
- `docs/decisions/hn_wip_cluster_visibility.md`
- `docs/decisions/hn_glob_routing_tag.md`
- `docs/decisions/hn_adopt_without_init_guard.md`



## v0.34.0 — implementation init 게이트 의미 재정의 (A4)

### 변경 파일

- `.claude/skills/implementation/SKILL.md` 라인 69~85 — Step 0 게이트 로직 재서술
- `.claude/scripts/check_init_done.sh` (신설) — 판정 로직 추출 (회귀 테스트 가능 + 다운스트림 자가 점검 용도)
- `.claude/scripts/tests/test_pre_commit.py` — TestInitGate 5 케이스 신규 추가

### 다운스트림 영향

implementation Step 0의 init 미완료 감지 로직이 변경됨.

**이전 (v0.33.x까지)**:
- CLAUDE.md `## 환경`의 `패키지 매니저:` 키 1개만 검사
- 비어있으면 차단
- 다운스트림 baseline 측정에서 false-block 입증 (15~19s 헛돔)

**v0.34.0 (A4 의미 재정의)**:
- `docs/guides/project_kickoff.md` 부재 OR `status: sample` 단독 → 차단
- CLAUDE.md `## 환경` drift는 차단 사유 아님 (다운스트림 자율)

**다운스트림 자유도 회복**:
- C++/CMake처럼 `패키지 매니저:` 키가 N/A인 환경도 정상 통과
- 다운스트림이 자기 양식·언어로 CLAUDE.md `## 환경` 채울 자유 확보

**여전히 차단되는 케이스 (의도)**:
- `harness-adopt` 끝났지만 `harness-init` 안 돈 다운스트림 (sample만 존재)
- `project_kickoff.md` 자체가 없는 신규 프로젝트

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

`harness-init` 정상 완료한 다운스트림은 영향 없음. `harness-adopt`만 돌고
`harness-init` 미실행한 다운스트림은 본 v0.34.0부터 implementation Step 0
가 차단됨 — `/harness-init` 실행 후 작업 진행.

### 검증

- `pytest -m gate` (TestInitGate 6/6 신규 통과 — 인라인 주석 케이스 포함)
- pytest 전체 64 passed (기존 58 + 신규 6, 회귀 0)
- starter `check_init_done.sh` 비용 측정: 5회 평균 ~0.07s (max 0.15s) —
  ≤2s 게이트 27x 여유
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다른 다운스트림
  환경(POSIX bash·다른 CPS 위치) 재발 시 본 incident 갱신 필요

### 결정 근거

`docs/decisions/hn_init_gate_redesign.md` (이동 후) — advisor 4 대안
weighted matrix 평가 결과 A4 채택 (96점 / A1 82 / A3 62 / A2 40).



## v0.33.1 — SEALED 면제 (MIGRATIONS류 자기 운영 파일)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — `SEALED_PATH_EXEMPT` 추가 (MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md 3개 path 화이트리스트)
- `.claude/scripts/tests/test_pre_commit.py` — T42.5 회귀 테스트 추가

### 다운스트림 영향

v0.32.0 (약속 박제 보호)에서 도입한 SEALED(completed 봉인) 룰이 starter
자기 운영 누적 파일을 면제하지 않아, 다운스트림이 `harness-upgrade`로
v0.33.0을 fetch한 직후 `/commit` 시 MIGRATIONS.md가 차단되는 결함이
발견됨 (incident 2026-05-02 다운스트림 보고).

본 fix로 MIGRATIONS.md / MIGRATIONS-archive.md / migration-log.md는
SEALED 검사에서 면제. 다운스트림 정상 흐름 복귀.

### 적용 방법

자동. `harness-upgrade` 후 추가 작업 불필요.

### 검증

- pytest -m gate (T42.5 신규 포함, 11/11 통과)
- pytest 전체 58 passed (기존 57 + 신규 1, 회귀 0)
- 회귀 위험: upstream Windows/Git Bash 환경 검증 범위. 다운스트림 환경
  재발 시 본 incident 갱신 필요



## v0.33.0 — commit_finalize wrapper (wip-sync + git commit 단일 흐름)

### 변경 파일

- `.claude/scripts/commit_finalize.sh` (신설) — wip-sync → git commit 단일 흐름 wrapper
- `.claude/skills/commit/SKILL.md` Step 7.5·8·커밋 메시지 작성 — wrapper 호출 1줄로 단순화
- `.claude/scripts/tests/test_pre_commit.py` — TestCommitFinalize 3 케이스 신설

### 변경 내용

자기증명 사고 (2026-05-02): SKILL.md SSOT는 "git commit **직전** wip-sync"
명시했으나 Claude가 git commit 먼저 호출 → wip-sync → 별 이동 commit
패턴 반복. 8 commit 중 3건 위반 (37.5%).

자율 신뢰만으로는 부족 → 메커니즘 차단으로 전환:

- `git commit` 직접 호출 금지. wrapper 경유 의무
- wrapper 내부: VERDICT != block 이면 wip-sync 호출 → wip 이동·cluster·
  역참조 갱신 모두 staging → `git commit "$@"` 단일 호출
- 결과: 1 wave = 1 commit. 별 이동 commit 사라짐

### 적용 방법

자동. harness-upgrade 후 commit 흐름 자동 변경.

호출 형식:
```bash
VERDICT="$VERDICT" HARNESS_DEV=1 \
  bash .claude/scripts/commit_finalize.sh \
    -m "feat: [제목]" -m "[본문]"
```

### 검증

```bash
pytest -m gate  # TestCommitFinalize 3 케이스
```

회귀 위험: TestCommitFinalize 3/3 통과 (HARNESS_DEV 차단·simple commit·
block skip wip-sync). 본 commit 자체가 자기증명 — wrapper 사용해 commit.



## v0.32.0 — 약속 박제 보호 (completed 봉인 + anti-defer 룰)

### 변경 파일

- `.claude/scripts/pre_commit_check.py` — completed 봉인 게이트 신설 (3.5번 섹션). status: completed 문서 본문 무단 변경 시 exit 2 차단
- `.claude/rules/anti-defer.md` (신설) — 미루기 회피 사유 블랙리스트 + 사용자 명시 처리 지시 우선 규칙
- `.claude/agents/review.md` — 검증 루프 7번 "wave scope 무단 확장 감지" 추가
- `CLAUDE.md` — 절대 규칙에 anti-defer + completed 봉인 명시
- `.claude/scripts/tests/test_pre_commit.py` — TestCompletedSeal 5 케이스 신설
- `docs/decisions/hn_session_test_results.md` (reopen) — 우선순위 5 측정 결과 누적 후 재 completed 처리
- `docs/WIP/decisions--hn_promise_protection.md` (신설) — 본 wave WIP

### 변경 내용

**자기증명 사고 (2026-05-02)**: v0.31.2 commit 후 완료된 wave WIP를 같은 세션에서 무단 확장 시도 → "최악 패턴" 사고. 다음 시스템 보호 메커니즘 신설:

1. **completed 봉인 게이트 (메커니즘)**: status: completed 문서 본문 변경을 pre-check이 차단. 변경하려면 `docs_ops.py reopen`으로 in-progress 전환 의무. `## 변경 이력` 섹션·updated/status 필드·rename은 면제.

2. **anti-defer 룰 (자율 신뢰 보강)**: "측정 후·다음 세션·데이터 누적 필요" 같은 미루기 회피 사유의 사용자 승인 없는 단독 사용 금지. 별 wave 분리는 정상 흐름이지만 처리 시점이 "후속"이면 미루기로 간주.

3. **review 자동 감지**: review.md 검증 루프에 wave scope 무단 확장 감지 추가.

**자기증명 검증**: 본 commit 작성 중 우선순위 5 측정을 `decisions/hn_session_test_results.md` (completed)에 직접 수정 → 본 게이트가 즉시 차단 → reopen 절차 거쳐 정상 처리. 메커니즘 정확 작동.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음. 다운스트림이 completed 문서 수정 시 `docs_ops.py reopen` 절차 의무.

### 검증

```bash
pytest -m gate
```

회귀 위험: TestCompletedSeal 5/5 통과. 본 commit이 자기증명 — 봉인 게이트가 본 작업 자체를 차단해 reopen 절차 거치게 함.



## v0.31.2 — commit/SKILL.md Step 7 staging.md SSOT link로 단순화

### 변경 파일

- `.claude/skills/commit/SKILL.md` — Step 7 Stage 결정 우선순위·Stage별 행동·거대 커밋 정책 본문 재진술 제거 → staging.md SSOT 참조 한 단락
- `docs/WIP/decisions--hn_rule_skill_ssot_apply.md` (신설) — Task 2 wave WIP

### 변경 내용

`hn_rule_skill_ssot.md` Task 1 측정 결과 핫스팟 1순위(commit × staging)
처리. SKILL.md 본문에 staging.md의 Stage 정의·플래그 우선순위·충돌 처리·
거대 커밋 정책이 일부 인라인되어 있던 것을 SSOT 참조로 단순화.

스킬 ~30줄 → ~5줄. staging.md 갱신 시 SKILL.md 동기화 누락 위험 제거.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음.

### 검증

```bash
pytest -m stage
```

회귀 위험: 본 변경은 SKILL.md 본문만 — Claude가 staging.md를 follow하는지 운용에서 확인 필요. 본 commit 자체가 자기증명 (Step 7 흐름이 정상 작동했음).



## v0.31.1 — scripts/tests 폴더 분리 (운영/테스트 혼재 해소)

### 변경 파일

- `.claude/scripts/tests/` (신설 폴더) — `test_pre_commit.py`·`test_extract_review_verdict.py`·`conftest.py` 이동
- `.claude/scripts/downstream-readiness.sh` — 회귀 스크립트 존재 검사 경로 갱신
- `.claude/settings.json` — pytest 권한 패턴 갱신
- `CLAUDE.md` — 빌드 명령어 경로 갱신

### 변경 내용

운영 코드(`pre_commit_check.py`·`docs_ops.py` 등)와 테스트 코드가 같은 `.claude/scripts/`에 섞여 있어 IDE 노이즈·분리 원칙 위반. `tests/` 하위로 분리. 다운스트림 영향 0 — `pytest .claude/scripts/`도 재귀로 작동.

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음. 다운스트림이 자체 테스트를 추가했다면 `tests/` 하위로 옮길지 자율 결정.

### 검증

```bash
pytest .claude/scripts/tests/ -q
```

회귀 위험: import 경로(`Path(__file__).parent`)가 한 단계 깊어진 만큼 `parent.parent`로 수정. 49/49 통과 확인.



## v0.31.0 — review verdict 추출 단순화 + wip-sync 의미 게이트

### 변경 파일

- `.claude/scripts/extract_review_verdict.py` (신설) — review 응답에서 verdict 단어만 추출하는 10줄 스크립트
- `.claude/scripts/test_extract_review_verdict.py` (신설) — markdown leak 5종 + 미존재 케이스 회귀 가드 (`pytest -m review`)
- `.claude/scripts/conftest.py` — `review` marker 등록
- `.claude/agents/review.md` — JSON 스키마·AC 매핑 의무·duplicate key 강제 폐기. "verdict 단어 포함" 한 줄로 단순화
- `.claude/skills/commit/SKILL.md` — Step 7 inline python heredoc(~80줄) → 1줄 호출 교체
- `.claude/scripts/docs_ops.py` wip-sync — frontmatter `problem` 의미 게이트 추가. 직접·body_referenced·abbr 매칭 모두 staged WIP의 problem 일치 의무
- `.claude/scripts/test_pre_commit.py` — TestWipSyncProblemGate 3 케이스 신설. wipsync_repo fixture WIP 비우기 보강 (T40 회귀). `_run_wip_sync` 반환값에 stdout 포함

### 변경 내용

**review verdict 추출 단순화 (Agent tool sub-agent prefill 미작동 대응)**:
- v0.30.5 JSON 스키마 강제는 5/5 markdown 머릿말 leak 실측 — debug-specialist 진단으로 sub-agent prefill 메커니즘 자체가 작동 안 함을 확인
- 형식 강제 폐기 + verdict 단어(`pass|warn|block`) 추출만으로 분기. 부가 정보(blockers·warnings·ac_check)는 응답 본문 그대로 사용자에게 노출

**wip-sync 의미 게이트 (어휘 일치 ≠ 의미 일치 false positive 차단)**:
- v0.30.6 자기증명 사례: `hn_rule_skill_ssot.md` AC 본문 "commit/SKILL.md" 어휘 hit으로 우연 ✅ 추가됨
- staged WIP의 frontmatter `problem` 집합 수집 → 후보 WIP의 `problem`이 그 집합에 있을 때만 매칭 인정
- 자기 자신 staged·staged WIP 부재 시 게이트 skip (작성자 직접 의도·코드 단독 commit 면제)

### 적용 방법

자동. harness-upgrade 후 별도 작업 없음.

### 검증

```bash
pytest -m "review or docs_ops"
```

회귀 위험: upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내에서는 기존 review·wip-sync 호출 흐름과 호환. Linux/macOS subprocess stderr 동작 차이는 미테스트.



## v0.30.6 — Step 7.5 Stage 0 skip 우회 결함 수정 (자기증명 사고 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 7.5 wip-sync 실행 조건 변경 — "Stage 0 skip도 스킵"에서 "block만 차단, skip·pass·warn 모두 실행"으로. wip-sync는 staged 확정 상태 기반이지 review LLM 호출 여부와 무관 |
| `docs/decisions/hn_review_verdict_compliance.md` | 수동 이동 (v0.30.5에서 누락) + 변경 이력 추가 | v0.30.5 commit에서 AC 모두 [x]였음에도 Stage 0 skip이 wip-sync를 가로챘던 사고 기록. 본 commit이 자기증명 — 결함 수정 + 누락 수습 함께 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 변경 작음 — Step 7.5 분기 조건 1줄 + 본문 명시. 다음 commit부터 Stage 0 skip이어도 AC 완료 WIP가 자동 이동
- 운용 추적: `git log --oneline`에서 WIP 파일 자동 이동 누락 사례 0건 기대
- v0.30.5의 review 영역 변경이 우연히 Stage 0 skip을 트리거 → 본 결함 노출 → 즉시 수정. 자기증명 + 즉시 대응 패턴

### 검증
```bash
# 다음 commit에서 wip-sync 실행 여부 stdout 확인
# `wip_sync_matched`·`wip_sync_moved` 출력 누락 없어야
```



## v0.30.5 — review 응답 JSON 규격화 + AC 매핑 의무 (verdict 100% 누락 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/agents/review.md` | 3-way merge | 출력 형식 SSOT를 markdown 템플릿 → raw JSON 1개 객체. 스키마: `{verdict, ac_check[{goal,result,evidence}], blockers[{ac_index}], warnings, axis_check, solution_regression, early_stop, conclusion}`. AC 매핑 의무(prompt N개 ↔ ac_check N개 1:1). duplicate key 금지 명시 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | review prompt prefill을 `{"verdict":"`로 변경. 응답 처리부 markdown grep → JSON 파싱(`json.loads` + `object_pairs_hook` duplicate key 감지). 종료 코드별 재호출 메시지 분기 (exit 1 파싱 실패 / exit 2 verdict 위반 / exit 3 ac_check 정합성 위반) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 본 세션 직전 5 commit (v0.29.2~v0.30.4) 모두 markdown 형식으로는 verdict
  100% 누락 → 1차 재호출 회복 패턴. v0.30.3 prefill만으로 부족 확인.
  JSON 스키마 강제로 형식 위반 자체를 invalid로 만들고, AC 매핑 의무로
  review의 구조화된 사고 강제
- dry test 통과: 정상 + 4가지 위반 시나리오 (필드 누락·dup key·정합성 위반·완전 invalid) 모두 정확 분기
- 다음 commit부터 효과 측정 — 자동 검증 불가, 운용 5 commit 1패스 성공률 추적
- review 영역 변경이라 본 commit은 자기증명 불가 (review.md를 review가 검증해도 의미 약함)

### 검증
```bash
# JSON 파싱·duplicate key·ac_check 정합성 dry test (별 스크립트 없음 — review 응답 받을 때 인라인 실행)
# 다음 commit review 응답이 JSON 형식인지 관찰
git log --grep "review-json-fail" --oneline  # 0건 기대
```



## v0.30.4 — eval_cps_integrity 본문 인용 grep 보강 (proxy 정밀화)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/eval_cps_integrity.py` | 3-way merge | `CPS_REF_PATTERNS` 4종 정규식 + `detect_cps_problem_refs` 함수 신설. frontmatter `problem` 필드만 카운트하던 한계를 본문 CPS 의미 인용("CPS 연결: P#"·"P#(...)"·"P# → S#"·"P# 충족")까지 확장. 자체 우선순위 라벨(`**P#**:`·`### P#.`)은 포지티브 매칭만 사용해 자연스럽게 제외 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- 본 starter 실측: P1 0→4, P2 2→8, P5 4→9, P6 0→2 (false positive 해소).
  P3·P4만 진짜 정체로 남음 — 수동 검토 결론과 100% 일치
- 자체 라벨 false positive 0건 (검증 통과)
- 정규식 휴리스틱이라 future 표기 패턴이 새로 생기면 누락 가능. 운용에서 추적

### 검증
```bash
# 보강 효과 확인
python3 .claude/scripts/eval_cps_integrity.py
# 기대: P1·P2·P5·P6 0건 아님, P3·P4만 정체
```



## v0.30.3 — review verdict prefill 패턴 (효율 개선)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | review prompt 끝을 `## 리뷰 결과 / verdict: `로 끝내 prefill 효과. "출력 형식 — 절대 규칙" 섹션 추가 — 분석 머릿말 금지·결론부터 출력 명시 |
| `.claude/agents/review.md` | 3-way merge | 상단 헤더 인용 박스 강화 — 자주 나오는 실수 명시·"분석은 reasoning에서, 출력은 결론부터" 행동 가이드. line 201 SSOT는 형식 정의, 상단은 행동 가이드로 역할 분리 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용. 다음 commit부터 review
1패스 통과율 추적.

### 회귀 위험
- prefill 패턴 효과 자동 검증 불가 — 운용에서 5 commit 1패스 성공률로 측정
- 본 세션 직전 4 commit (v0.29.2~v0.30.2) 모두 verdict 누락 → 1차 재호출 회복 패턴 100%
- 다운스트림 환경(Linux/macOS) 미테스트 (prompt 텍스트 변경이라 OS 무관)

### 검증
```bash
# 다음 commit 시 review 1차 응답 첫 2줄 형식 준수 여부 관찰
# git log 메시지에 [review-form-warn] 태그 빈도 추적
git log --grep "review-form-warn" --oneline
```



## v0.30.2 — MIGRATIONS·README 슬림화 + archive 자동화 (효율 개선)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `docs/harness/MIGRATIONS.md` | 자동 (slim) | 759줄(24개) → 240줄(5개). 6번째 이전 18개 섹션은 신규 archive로 이동. 정책 갱신 — "최신 5개 본문만 유지" |
| `docs/harness/MIGRATIONS-archive.md` | 신규 | 18개 섹션 누적 (v0.28.8 이전). 보존용·갱신 없음 |
| `README.md` | 자동 (slim) | 420줄 → 297줄. "최근 주요 변경" 섹션 31개 → 5개. 자세한 이력은 MIGRATIONS·archive·git log로 안내 |
| `.claude/scripts/harness_version_bump.py` | 3-way merge | `--archive [keep=5]` 서브커맨드 신설. MIGRATIONS.md 6번째 이전 섹션 자동 이동. 멱등성 보장 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 4에 `harness_version_bump.py --archive` 호출 추가 (5개 → 4개). 매번 자동 archive로 본문 비대화 방지 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용. 다운스트림이 자기 환경
MIGRATIONS.md를 슬림화하려면 `python3 .claude/scripts/harness_version_bump.py --archive`
1회 실행.

### 회귀 위험
- upstream 격리 환경에서 archive 멱등성·keep=4 시뮬 동작 확인
- 다운스트림이 마지막 upgrade 이후 6개 이상 누적된 경우 본 정책 적용 시
  archive로 일부 이동 — 본문은 최신 5개만 보임. 더 오래된 항목은 archive 참조
- README 변경 이력은 archive로 옮기지 않음 (git log + MIGRATIONS-archive로 충분)

### 검증
```bash
# archive 멱등성
python3 .claude/scripts/harness_version_bump.py --archive

# 본문 5개 + archive 18개 (본 시점 기준)
grep -c "^## v0\." docs/harness/MIGRATIONS.md docs/harness/MIGRATIONS-archive.md
```



## v0.30.1 — wip-sync 매칭 정밀화 + 위임 트리거 강화 (자기증명 사고 대응)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | wip-sync 매칭 정규식 정밀화 — `^\s*([-*]\|\d+\.)\s` → `^\s*[-*]\s+\[[ xX]\]\s` (체크박스 라인 한정). frontmatter 영역 마킹 제외(`_fm_end` 인덱스). `body_referenced`도 `[x]` 마크 + staged 파일 언급으로 좁힘 |
| `.claude/scripts/session-start.sh` | 3-way merge | 연속 fix 감지를 prefix 무관 "공통 파일 2 커밋 연속 수정"으로 확장. 메타 파일(HARNESS.json·README·MIGRATIONS·clusters) 노이즈 제외 |
| `.claude/rules/no-speculation.md` | 3-way merge | 호출 조건표에 "동일 시스템 동작 이슈 2회 이상" 행 추가 + 본문 보강 (사용자 키워드 보고 없어도 Claude 자가 트리거 의무) |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | TestWipSyncMatchPrecision 3 케이스 신설 (사전 준비·frontmatter relates-to false positive 차단 + 정상 매칭 회귀 가드) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경에서 `pytest -m docs_ops` 신규 3 케이스 통과 확인
- `bash -n session-start.sh` 구문 검증 통과
- 기존 2 failure (`TestWipSyncAbbrMatch::test_abbr_*`)는 본 변경과 무관 — 별건 abbr 보조 매칭 경로 이슈 (debug-specialist 진단 결과)
- 다운스트림 환경(Linux/macOS) 미테스트
- session-start hook은 매 세션 시작에 동작 — 변경 후 다음 세션부터 효과

### 검증
```bash
# wip-sync 매칭 정밀화 회귀 가드
python -m pytest .claude/scripts/test_pre_commit.py::TestWipSyncMatchPrecision -v

# session-start.sh 구문
bash -n .claude/scripts/session-start.sh
```



## v0.30.0 — eval --harness CPS 무결성 감시 + commit 잔여 정정 (efficiency overhaul follow-up)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/eval_cps_integrity.py` | 신규 (3-way merge) | docs/ 전수 frontmatter solution-ref 박제 grep + Problem 인플레이션·인용 빈도 측정. `pre_commit_check.py` (verify_solution_ref·get_cps_text·parse_frontmatter) 동적 import 재사용 (코드 중복 0) |
| `.claude/skills/eval/SKILL.md` | 3-way merge | `--harness` 점검 항목 5(CPS 무결성) 신설 + 보고 형식·`--deep` 활용 가이드 추가 |
| `docs/decisions/hn_commit_auto_verify.md` | 자동 (status 정정) | v0.29.2 wip-sync 흐름 잔여 — in-progress → completed |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경에서 `eval_cps_integrity.py` 박제 감지·인플레이션 경고·인용 0건 검출 시뮬레이션 통과
- 본 starter 실측: P1·P3·P4·P6 frontmatter 인용 0건 발견 (정체 의심 — Problem 정의 자체 검토 신호, 자동 조치 X)
- 다운스트림 환경(Linux/macOS) 미테스트
- `eval --harness` 사용자가 본 SKILL.md 절차에 따라 수동 실행해야 작동 (자동 hook 아님)

### 검증
```bash
# CPS 무결성 1회 실행
python3 .claude/scripts/eval_cps_integrity.py
```



## v0.29.2 — commit 5.3 자동 실행 코드 구체화 (efficiency overhaul follow-up)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 5.3 코드 블록 구체화 — `PRE_CHECK_OUTPUT`에서 `AC_TESTS`/`AC_ACTUAL` 변수 추출, 화이트리스트 정규식 SSOT (`^(pytest\|bash -n\|python -m\|grep)\b`), `run_ac_check` 공유 함수 (tests·실측 동일 분기), `HARNESS_SPLIT_SUB=1` sub-커밋 재실행 가드 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 회귀 위험
- upstream 격리 환경(Windows/PowerShell + bash)에서 6 케이스(pytest·grep·bash -n·python -m·rm -rf·none) 분기 시뮬레이션 통과
- pytest -m stage 2 passed
- 다운스트림 환경(Linux/macOS) 미테스트
- 화이트리스트 외 명령은 자동 실행 skip — 보안

### 검증
```bash
# stage 회귀 가드
python -m pytest .claude/scripts/test_pre_commit.py -m stage -q
```



## v0.29.1 — Phase 2-A 2단계: AC + CPS 시스템 강제 (efficiency overhaul)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | frontmatter `problem`·`solution-ref` 검증 + AC `Goal:` + 검증 묶음 추출 + CPS 박제 감지 (normalize_quote·verify_solution_ref·parse_ac_block 신설). 외형 룰 (UPSTREAM_PAT·META_M_PAT·rename/meta/WIP/docs-5줄 단독 skip) 폐기. `wip_kind`·`has_impact_scope` 폐기, `wip_problem`·`wip_solution_ref`·`ac_review`·`ac_tests`·`ac_actual` 출력 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 외형 metric 테스트 (TestStageBasic 4개·TestIntegMoveCommit 전체) deprecate. 시크릿 게이트·standard 폴백 테스트만 유지 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | 자기증명 적용 — solution-ref list + 검증 묶음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 필수 작업**:
- 신규 WIP·decisions·incidents·guides 작성 시 frontmatter `problem: P#`·`solution-ref:` (list) + AC `Goal:` + `검증:` 묶음 (review·tests·실측 3 키) 작성. 누락 시 commit 차단.
- 기존 50개 문서는 본 wave 밖 — 별 wave에서 backfill (점진).

### 자기증명 통과
본 commit 자체가 새 검증 시스템 통과:
```
pre_check_passed: true
wip_problem: P2
wip_solution_ref: S2 — "review tool call 평균 ≤4회 (부분)"; S2 — "docs-only 커밋이 skip 또는 micro로 분류됨"
ac_review: review-deep
ac_tests: pytest -m secret
ac_actual: AKIA 더미 staged + HARNESS_DEV=1 git commit → exit 1, 차단 확인
recommended_stage: deep
```

### 주의 — 외형 metric 폐기 영향
- `.claude/scripts/**` → deep 자동 격상 → 폐기. AC `검증.review` 작성자 선언이 결정
- `docs 5줄 이하` skip → 폐기. 줄 수 무관, AC 기반
- `WIP 단독`·`meta 단독`·`rename 단독` skip → 폐기. AC 기반
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목 → 코드에서 더 이상 읽지 않음. 다운스트림 그대로 둬도 동작 무관

### 한계 (별 wave)
- eval/SKILL.md CPS 무결성 감시 (`--harness` 박제 발견) — 본 wave 밖
- commit 스킬 5.3 자동 실행 코드 (tests·실측 화이트리스트 실행) — 본 wave 밖, 1단계에 SSOT 정의는 됨
- legacy 50개 문서 frontmatter backfill — 별 wave (다운스트림 영향)
- AC 미작성 진입점 결함 audit (write-doc·implementation 진입점) — 별 WIP

### 회귀 위험
- upstream 격리 환경 검증:
  - `pytest -m "secret or stage"` 6/6 통과 + 4 skip (TestIntegMoveCommit deprecate)
  - 본 commit 자체 자기증명 통과 (위 출력 참조)
- staged WIP 없는 hot-fix 케이스: standard 폴백 (이전 외형 metric 추정 대신 보수)

### 검증
```bash
python3 .claude/scripts/pre_commit_check.py
pytest -m "secret or stage"
```



## v0.29.0 — Phase 2-A 1단계: AC + CPS 시스템 정의 (efficiency overhaul)

### 변경 파일 (24개 — 시스템 정의 문서만, 코드 변경 0)

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/rules/docs.md` | 3-way merge | frontmatter `problem`·`solution-ref` SSOT 신설. AC 포맷 통합 (`Goal` + `검증` 묶음). CPS 면제 룰. 박제 감지 룰 |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | 단일 룰 재작성 — AC `검증.review` 그대로 stage 결정. 외형 metric 룰 폐기 (kind 라벨·줄 수·경로) |
| `.claude/rules/naming.md` | 3-way merge | 메타데이터 SSOT 참조 추가 (docs.md로 위임) |
| `.claude/rules/coding.md`·`external-experts.md`·`hooks.md`·`internal-first.md`·`memory.md`·`no-speculation.md`·`pipeline-design.md`·`security.md`·`self-verify.md` | 3-way merge | 각 룰 상단에 `defends: P#` 추가 (어느 Problem 막는지 추적) |
| `.claude/skills/implementation/SKILL.md` | 3-way merge | Step 0 강화 — CPS 매칭 + AC 묶음 1차 제안. WIP 템플릿 갱신 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 5 책임 재정의. Step 5.3 신설 — tests·실측 자동 실행 (화이트리스트만). 핸드오프 계약 갱신 |
| `.claude/agents/review.md` | 3-way merge | `serves: S2` + Solution 회귀 검증 루프 + 입력 블록 `wip_problem`·`wip_solution_ref` |
| `.claude/agents/{advisor,codebase-analyst,debug-specialist,doc-finder,performance-analyst,researcher,risk-analyst,threat-analyst}.md` | 3-way merge | 각 에이전트 frontmatter에 `serves: S#` 추가 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | starter 자체 WIP — AC 1단계 ✅ |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의 — 동작 변경 없음 (정의만)
- 본 버전은 **시스템 정의 SSOT만 갱신**. pre_commit_check.py 등 강제 코드는 변경 없음.
- 강제는 v0.29.1 (Phase 2-A 2단계)에서 — pre_commit_check이 새 SSOT 따라 frontmatter 검증·외형 metric 폐기.
- 다운스트림은 본 버전 적용 후 신규 문서 작성 시 새 형식 권장. **차단은 v0.29.1부터**.

### 폐기 마커 호환성
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목은 무시 (코드에서 더 이상 읽지 않음 — v0.29.1부터)
- 다운스트림이 그대로 둬도 동작 무관. 점진 마이그레이션

### 회귀 위험
- 코드 변경 0 — 동작 회귀 위험 없음
- 문서 SSOT 변경 — 다운스트림이 신규 문서 작성 시 새 형식 학습 부담

### 검증
```bash
# 룰 12개에 defends: 적용 확인
grep -L "^defends:" .claude/rules/*.md  # 0건 expect

# 에이전트 9개에 serves: 적용 확인
grep -L "^serves:" .claude/agents/*.md  # 0건 expect

# CPS 면제 (project_kickoff.md에 problem·solution-ref 없음)
grep -E "^(problem|solution-ref):" docs/guides/project_kickoff.md  # 0건 expect
```

---





**SSOT는 `MIGRATIONS.md`** — 본 파일은 보존용. 이동 시점 기준 그대로
박제되며 본문 갱신 안 함. 변경 이력은 git log가 담당.

---

## v0.28.8 — Phase 1 시크릿 hook 이중화 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/install-starter-hooks.sh` | 3-way merge | hook 본문에 시크릿 패턴 풀 grep 추가 (sb_secret·service_role·AKIA·sk_live·ghp·glpat·xox·AIza·sk-ant·PRIVATE KEY 등). `HARNESS_DEV=1` 분기 이전에 시크릿 검사 실행 — 우회 불가. HARNESS.json hook_installed 자동 갱신 |
| `scripts/install-secret-scan-hook.sh` | 자동 덮어쓰기 | HARNESS.json hook_installed 자동 갱신 추가 (다운스트림용). 패턴 풀 변경 없음 |
| `.claude/scripts/pre_commit_check.py` | 3-way merge | json import + hook 미설치 경고 stderr 출력 (`HARNESS.json hook_installed` 체크). starter/다운스트림별 설치 명령 안내 |
| `.claude/scripts/bash-guard.sh` | 3-way merge | `git commit` 차단 메시지에 "시크릿 line-confirmed 가드는 git pre-commit hook이 항상 실행 — 우회 불가" 추가. 안내 톤 갱신 |
| `.claude/HARNESS.json` | 사용자 전용 (skip) | starter 자체에서 `hook_installed: true` 추가. 다운스트림은 install 스크립트가 자동 추가 |
| `README.md` | 사용자 전용 (skip) | secret-scan hook "선택" → "필수" 격상 + 우회 경로 안내 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 추가 작업 (필수)**:
1. `bash scripts/install-secret-scan-hook.sh` 실행 — 시크릿 hook 설치 (`HARNESS.json` `hook_installed` 자동 갱신)
2. 미설치 상태에서 commit 시 `pre_commit_check.py`가 stderr 경고 출력

### 주의
- **threat-analyst 발견**: 이전까지 `HARNESS_DEV=1 git commit` 경로가 시크릿 가드 완전 우회. bash-guard 통과(L101-103) + pre_commit_check 미호출 + hook도 통과. 본 버전이 hook 본문에 시크릿 검사 박아 우회 차단 (안전망 5/10 → 7.5/10).
- **`git commit --no-verify` 한계**: hook 자체 우회 — Phase 1으로 막을 수 없음. README 경고 + bash-guard 차단(Claude Code 내)으로 대응.
- **면제 위치**: `^\.claude/(scripts|agents|rules|skills|memory)/` 경로는 시크릿 패턴 SSOT 문서화 위치이므로 면제 (S1_LINE_EXEMPT와 동일).

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash) 검증:
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: `HARNESS_DEV=1 git commit` + AKIA 더미 시크릿 → exit 1 차단 확인
  - 실측: `hook_installed=false` 시 stderr 경고 출력 확인
- PowerShell·WSL 환경 미테스트 (운용 검증 필요)
- 다운스트림이 secret-scan hook 미설치 시 안전망 부재 — pre-check 경고가 유일 알림

### 검증
```bash
bash .claude/scripts/install-starter-hooks.sh   # starter용
bash scripts/install-secret-scan-hook.sh        # 다운스트림용
pytest -m "secret or stage"
```

---

## v0.28.7 — HARNESS_UPGRADE 환경변수 폐기 (C 항목 — 옵션 B)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | L108 `HARNESS_UPGRADE` 정의 제거, L549 룰 0 분기 제거. 환경변수 의존 0 |
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(HARNESS_UPGRADE=1 bash *)` 제거 |
| `.claude/rules/staging.md` | 3-way merge | 1단계 룰 0번 제거 + 폐기 안내 블록. review skip은 commit 스킬 `--no-review`로 흡수 |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 — `HARNESS_UPGRADE=1 git commit` → `/commit --no-review`. "다른 스킬과의 관계" 표 commit 항목 갱신 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **다운스트림 영향**: 기존에 `HARNESS_UPGRADE=1` 환경변수를 쓰던 스크립트·alias가 있다면 **자연 무시**(분기 제거됨). 명시적 정리 권장 — `git grep HARNESS_UPGRADE`로 확인 후 제거.
- **review skip 대체**: harness-upgrade 자체는 본 버전부터 `/commit --no-review` 호출. 사용자가 직접 review skip 필요하면 동일하게 `--no-review` 플래그 사용.
- 회고적 기록(README v0.26.9 변경 이력, MIGRATIONS L398, hn_upstream_anomalies.md 본문)은 당시 상태 보존 — 변경 안 함.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `from pre_commit_check import ENOENT_PATTERNS` import OK
  - `pytest -m "secret or stage"` 12/12 통과
- 활성 코드 잔여 참조 0 (회고적 기록 5건만).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
python3 -m pytest .claude/scripts/test_pre_commit.py -m "secret or stage"
grep -l HARNESS_UPGRADE .claude/scripts/ .claude/rules/ .claude/skills/  # 활성 코드 0건
```

---

## v0.28.6 — upstream anomalies B·D·E·F 일괄 wave (보안·LF·worktree·sanity)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(rm *)`·`Bash(export *)` 제거. 와일드카드 삭제·임의 export는 starter 기본 권한에서 빠짐 (B) |
| `.gitattributes` | 신규 | `* text=auto eol=lf` + 바이너리 제외. Windows + Git Bash 환경에서 3-way merge 통째 충돌 방지 (D) |
| `.claude/scripts/bash-guard.sh` | 3-way merge | 검증 2.5 추가 — `git worktree add` 차단. CLAUDE.md 절대 규칙 코드 강제. list/remove/prune은 통과 (E) |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 0.1 worktree 잔여 자동 정리(clean 자동/dirty 안내) + Step 1 fetch 후 installed_from_ref sanity check + Step 5 ours `tr -d '\r'` LF 정규화 + Step 8.1 위험 패턴 명시 승인 강제 + Step 10 갱신 후 sanity check (B·D·E·F) |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 사용자 전용 (skip) | starter 자체 WIP 갱신 — 다운스트림은 건드리지 않음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **B 위험 권한 제거**: 다운스트림이 `Bash(rm *)`·`Bash(export *)`를 이전 업그레이드에서 받았다면 Step 8.1이 자동 제거하지 않는다 (사용자 추가로 분류). 직접 `.claude/settings.json`에서 제거 검토.
- **D LF 정규화**: 신규 클론은 `.gitattributes`로 보호. 기존 워킹트리(autocrlf 환경)는 `git add --renormalize .` 1회 실행 권장. harness-upgrade 자체는 Step 5에서 `tr -d '\r'`로 런타임 보호.
- **E worktree 차단**: `git worktree add` 시도 시 exit 2. 잔여가 있으면 harness-upgrade Step 0.1이 clean한 것만 자동 제거. dirty는 안내만 — 사용자 직접 정리.
- **F sanity check**: Step 1 fetch 직후 + Step 10 갱신 후 양쪽. 한 지점만으로는 다음 업그레이드 시점까지 stale ref가 묻혀 ADDED 부풀림 발생.
- C(HARNESS_UPGRADE 환경변수 의미 일관화)는 미해결 — 별 wave.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증 범위:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `bash -n .claude/scripts/bash-guard.sh` 구문 OK
  - `echo '{"tool_input":{"command":"git worktree add foo"}}' | bash bash-guard.sh` → exit 2 차단 실측
  - `echo '{"tool_input":{"command":"git worktree list"}}' | bash bash-guard.sh` → exit 0 통과 실측
- harness-upgrade SKILL.md 변경분은 자동 검증 불가 — 다운스트림 업그레이드 사이클에서 운용 검증 필요.
- `.gitattributes` 첫 도입 — 기존 워킹트리에서 `git add` 시 CRLF→LF 정규화 경고 발생 (의도된 동작).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
bash -n .claude/scripts/bash-guard.sh
echo '{"tool_input":{"command":"git worktree add foo"}}' | bash .claude/scripts/bash-guard.sh  # exit 2
echo '{"tool_input":{"command":"git worktree list"}}' | bash .claude/scripts/bash-guard.sh    # exit 0
```

---

## v0.28.5 — docs_ops·harness_version_bump·task_groups encoding="utf-8" 일괄 (G Phase 3)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `git()` helper에 `encoding="utf-8"` 추가. 한글 git 출력에서 cp949 디코딩 실패 방지 |
| `.claude/scripts/harness_version_bump.py` | 3-way merge | `run()` helper에 `encoding="utf-8"` + `or ""` 방어 |
| `.claude/scripts/task_groups.py` | 3-way merge | 동일 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- G 항목(Windows + 한글 환경 무한 막힘) 마지막 wave. Phase 1·2가 `pre_commit_check.py`의 갈래 1·2를 해소했고, 본 Phase 3은 같은 패턴이 다른 스크립트에 반복돼 있던 것을 일괄 정리.
- 세 파일 모두 `def main()` + `if __name__ == "__main__":` 구조는 이미 적용돼 있어 추가 리팩토링 불필요.
- WIP `harness--hn_upstream_anomalies.md` G 항목 ✅ 해결로 마킹. B·C·D·E·F는 미해결 — 별 wave로 진행.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과.
- 세 파일의 subprocess 호출 변경 — 한글 미포함 출력은 기존과 동일 동작. UTF-8 디코딩 가능한 모든 입력 처리.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"
```

---

## v0.28.4 — pre_commit_check.py main 함수화 (G Phase 2 — script-as-module 결함 해소)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | 580줄 module-level main 로직 → `def main() -> int:` 함수화 + `if __name__ == "__main__": sys.exit(main())` 보호. ENOENT_PATTERNS만 module-level 유지 (test가 import). 입력 수집·검사·출력 전부 main() 안으로 이동 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | `TestModuleImportSafe::test_import_does_not_exit` 신규 — staged 변경 유무 무관 import 후 sys.exit 발생 안 함 검증 (`enoent` marker) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **import 시 main 로직 미실행**: `from pre_commit_check import X`가 모듈 import만 수행. 기존 module-level mutable 변수(staged_files·name_status_raw 등)에 outer scope에서 직접 접근하던 코드가 있다면 → 본 변경으로 영향. test_pre_commit.py 외 import 사용처 없음 확인.
- ENOENT_PATTERNS 정규식만 module-level 유지. 다른 정규식(S1_LINE_PAT·SKIP_TODO 등)은 main() 안에 있음 — main 호출당 1회 컴파일. 미미.
- Phase 1(v0.28.3)의 `encoding="utf-8"` fix와 함께 동작. 둘 다 갈래 1·2 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과 확인.
- Linux/macOS·다운스트림 환경 미테스트. 580줄 들여쓰기 변경이라 실측 회귀 모니터링 권장.
- T40.1 wip-sync abbr 매칭 테스트는 본 작업 sandbox 환경에서 fixture 격리 갭으로 fail (본 fix 무관) — fixture가 starter repo clone 시 작업 중 WIP가 따라가서 같은 abbr 충돌. 별 issue.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"  # 27/27 통과
python -c "import sys; sys.path.insert(0, '.claude/scripts'); from pre_commit_check import ENOENT_PATTERNS; print(ENOENT_PATTERNS)"  # import 후 sys.exit 없음
```

---

## v0.28.3 — pre_commit_check.py run() encoding="utf-8" (G Phase 1)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `run()`에 `encoding="utf-8"` + `or ""` 방어 추가. Windows + 한글 staged diff에서 system locale(cp949) 디코딩 실패로 `stdout=None` 되던 결함 해소 |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 신규 | 다운스트림 발견 이상 징후 묶음 SSOT (B·C·D·E·F·G) — G Phase 1만 해결, 나머지 미해결 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- Phase 1만으론 `from pre_commit_check import X` 회귀 가드 미적용 — Phase 2(main 함수화) 후 박을 예정.
- staged 변경이 없을 때 직접 호출(`python pre_commit_check.py`)은 PYTHONUTF8 없이도 정상 동작 확인.
- 다운스트림 영향: Windows 사용자가 한글 commit 메시지·diff에서 겪던 무한 차단 부분 해소 (직접 호출 경로). Linux/macOS 미영향.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash, 한글 staged diff)에서 직접 호출 통과 실측 확인.
- import 경로(staged 시 sys.exit)는 Phase 2까지 미해소 — 회귀 가드 테스트 추가도 Phase 2 의존.

### 검증
```bash
unset PYTHONUTF8; python .claude/scripts/pre_commit_check.py  # cp949 실패 안 함
pytest -m secret  # 기존 회귀 가드 통과
```

---

## v0.28.2 — pre-check 시크릿 line 면제 갭 + docs_ops untracked move 갭

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `S1_LINE_EXEMPT` 정규식을 `^\.claude/(scripts\|agents\|rules\|skills\|memory)/`로 확장. 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치(agents·rules·skills·memory)가 line-confirmed로 잘못 차단되던 문제 해소 |
| `.claude/scripts/docs_ops.py` | 3-way merge | `cmd_move` fallback에서 `git ls-files --error-unmatch`로 src 인덱스 존재 여부 확인 후 `git rm --cached` 시도. untracked WIP 이동이 매번 returncode 1로 실패하던 갭 해소 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 회귀 테스트 2건 추가 — `TestSecretScan::test_harness_doc_line_exempt`, `TestMoveUntrackedWip::test_untracked_move_succeeds` |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- 다운스트림에서 `.claude/agents/threat-analyst.md` 같은 패턴 SSOT 문서를 수정하면
  `🚫 pre-check 차단 — 시크릿 line-confirmed (s1_level)` 메시지가 발생하던 false-positive 해소.
- 면제 범위는 `.claude/(scripts|agents|rules|skills|memory)/`로 한정. `docs/`·사용자 코드(`src/` 등)는 여전히 line 스캔 적용.
- untracked WIP fallback fix로 implementation→commit 흐름의 잠재 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내에서는 영향 없음.
  `pytest -m secret` 4/4 통과, untracked move 직접 sandbox 검증 통과.
- 별개 환경 결함(Windows cp949 디코딩 + module-level main 로직 import)으로
  `pytest -m docs_ops`는 본 환경에서 실행 불가 → 관련 테스트는 `PYTHONIOENCODING=utf-8`
  + 임시 repo subprocess로 우회 검증. 별도 추적 필요.

### 검증
```bash
pytest -m secret
PYTHONIOENCODING=utf-8 pytest .claude/scripts/test_pre_commit.py::TestMoveUntrackedWip
```

---

## v0.28.1 — completed 전환 차단 — 코드블록 안 면제

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `_extract_body`에 코드블록(``` ```·`~~~`) 추적 추가. 코드블록 안 라인은 차단 검사 대상 아님 |
| `.claude/rules/docs.md` | 3-way merge | "completed 전환 차단" 섹션에 "코드블록 안 면제" 룰 명시 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- AC 포맷 예시·문법 설명을 코드블록에 박은 WIP들이 completed 이동 시 거짓 차단되던 문제 해소.
- 회고형 차단(v0.27.6) + 코드블록 면제(이번)로 차단 룰 정밀도가 두 단계 향상.

### 검증
```bash
python3 .claude/scripts/docs_ops.py move <테스트용 WIP>
```

---

## v0.27.3 — Karpathy 원칙 적용 (Phase 1): 코딩 컨벤션·행동 원칙·AC 기반 검증 구조

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `CLAUDE.md` | 3-way merge | `## 행동 원칙` 섹션 추가 (Think Before Coding + Goal-Driven) |
| `.claude/rules/coding.md` | 3-way merge | Surgical Changes 원칙·금지 패턴 추가 |
| `.claude/rules/self-verify.md` | 3-way merge | Goal-Driven 원칙, AC 완료 기준, TDD/fail-first |
| `.claude/rules/docs.md` | 3-way merge | WIP AC 포맷 확장 (`Goal:` + `영향 범위:`) |
| `.claude/rules/staging.md` | 3-way merge | AC 기반 검증 원칙 추가, 연결 규칙 B·C에 AC 조건 추가 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Stage별 행동 직접 서술 → staging.md 포인터로 교체 |

### 변경 내용
- CLAUDE.md에 구현 전 사고 원칙(Think Before Coding, Goal-Driven) 추가
- coding.md에 Surgical Changes 원칙 5개 + 금지 패턴 5개 명문화
- self-verify.md: AC 체크박스가 완료 기준임을 명시, TDD/fail-first 원칙 추가
- docs.md: WIP AC에 `Goal:` + `영향 범위:` 항목 포맷 추가
- staging.md: AC 기반 검증 원칙 추가, `영향 범위:` → deep 트리거, AC 전부 [x] → micro 완화
- commit/SKILL.md: staging SSOT 충돌 해소 (Stage별 행동 재서술 제거)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

### 회귀 위험
- staging.md 연결 규칙 B·C에 AC 기반 조건 추가됨 — 기존 신호 체계는 유지
- 다운스트림 CLAUDE.md에 `## 행동 원칙` 섹션이 추가됨 (기존 절대 규칙 위치 변경 없음)

---

## 포맷

```markdown
## vX.Y — 한 줄 요약

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/foo/SKILL.md` | 3-way merge | 변경 이유 한 줄 |
| `.claude/scripts/bar.py` | 자동 덮어쓰기 | |
| `.claude/agents/baz.md` | 신규 추가 | |

처리 값: `자동 덮어쓰기` · `3-way merge` · `신규 추가` · `삭제`

### 변경 내용
이번 버전에서 달라진 것. 다운스트림이 맥락 파악용.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.
- ...

**수동 적용**: upgrade 후 직접 실행. 안 하면 미동작.
- 없음  ← 없을 때도 명시

### 검증
적용 후 확인 방법.
```

---

## v0.27.2 — 도메인 시스템 갭 수정 및 문서 참조 정합성 복구

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | docs_ops 함수 import + S9 WIP 도메인 추출 수정 + 경로→도메인 3단계 구현 |
| `.claude/scripts/docs_ops.py` | 3-way merge | extract_path_domain_map 예시 블록 오파싱 수정 |
| `.claude/scripts/task_groups.py` | 자동 덮어쓰기 | NAMING_MD dead code 제거 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | _add_path_domain_map 헬퍼 실제 매핑 블록 참조로 수정 |
| `.claude/rules/naming.md` | 3-way merge | docs-ops.sh → docs_ops.py 참조 수정 + 실제 매핑 코드블록 추가 |
| `.claude/rules/docs.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py 참조 수정 (4곳) |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | pre-commit-check.sh → pre_commit_check.py 참조 수정 (3곳) |
| `.claude/rules/security.md` | 자동 덮어쓰기 | install-secret-scan-hook.sh → install-starter-hooks.sh |
| `.claude/agents/review.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py, docs-ops.sh → docs_ops.py |
| `.claude/agents/doc-finder.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py |
| `.claude/agents/threat-analyst.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py + bash 스니펫 S1_LINE_PAT 기반으로 교체 |

### 변경 내용

**갭 1 — WIP 도메인 추출 오류 수정**: `pre_commit_check.py` S9 블록에서 WIP 파일
도메인을 라우팅 태그(`decisions`, `guides`)로 잘못 추출하던 문제 수정.
`docs_ops.detect_abbr()` + abbr→domain 역매핑으로 실제 도메인(`harness`, `meta`) 추출.
WIP-only 커밋에서 critical 도메인이 deep으로 격상되지 않던 문제 해소.

**갭 2 — naming.md 파싱 중복 제거**: `pre_commit_check.py`가 `docs_ops.py`의
`extract_abbrs`, `detect_abbr`, `extract_path_domain_map`, `path_to_domain`을
동적 import해 재사용. naming.md를 두 스크립트가 별도 파싱하던 중복 제거.

**갭 3 — 경로→도메인 매핑 3단계 구현**: staging.md 명세 4단계 중 3단계
(naming.md 경로→도메인 매핑)가 구현되지 않던 문제 수정. naming.md에
`실제 매핑` 코드블록 영역 추가 — 다운스트림이 여기에 경로 매핑 등록 시 S9에 반영.

**문서 참조 정합성**: 존재하지 않는 `docs-ops.sh`, `pre-commit-check.sh`,
`install-secret-scan-hook.sh` 참조를 실제 파일명으로 일괄 수정 (총 14곳).

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: naming.md `## 경로 → 도메인 매핑` 섹션 하단 `실제 매핑` 코드블록에
프로젝트 코드 폴더 경로 매핑 추가 권장 (S9 도메인 등급 신호 정확도 향상).
예: `src/payment/**     → payment`

### 검증
`python3 -m pytest .claude/scripts/test_pre_commit.py -q` → 56 passed.

---

## v0.27.1 — eval 기본 모드 보고 구조 개선 (거시/미시 계층 + memory 저장)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/eval/SKILL.md` | 3-way merge | 기본 모드 절차 4→6단계 확장 |

### 변경 내용

`/eval` 기본 모드 절차에 분류(4)·보고(5)·저장(6) 단계 추가.

- 발견된 간극을 **거시**(CPS 방향 이탈) / **단기 블로커**(다음 작업 차단) / **장기 부채**(방치 시 위험) 세 층으로 분류
- 대화 출력은 거시 요약 + 단기 블로커만 간결하게, 장기 부채 상세는 memory 참조로 압축
- eval 완료 시 항상 `.claude/memory/project_eval_last.md`에 전체 상세를 덮어쓰기 저장 + `MEMORY.md` 인덱스 갱신 (0건이어도 실행)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`/eval` 실행 후 `.claude/memory/project_eval_last.md` 생성 여부 확인.

---

## v0.27.0 — UserPromptSubmit debug-guard 훅 신설

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/debug-guard.sh` | 신규 추가 | UserPromptSubmit 키워드 감지 스크립트 |

### 변경 내용
사용자 메시지에 "에러", "버그", "오류", "원인" 등 키워드가 감지되면
`debug-specialist` 에이전트를 먼저 호출하도록 Claude 컨텍스트에 주입.
Claude가 직접 추측 수정으로 진행하는 패턴을 시스템 레벨에서 차단.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`echo '{"prompt":"에러났어 원인을 찾아"}' | bash .claude/scripts/debug-guard.sh`
→ `⚠️ [debug-guard]` 메시지 출력되면 정상.

---

## v0.26.9 — harness-upgrade 커밋 분기 + MIGRATIONS 변경 파일 섹션

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 + Step 3 변경 파일 표 참조 추가 |
| `docs/harness/MIGRATIONS.md` | 자동 덮어쓰기 | `### 변경 파일` 섹션 포맷 추가 |

### 변경 내용

- `harness-upgrade/SKILL.md` Step 10: 커밋 시 `CONFLICT_RESOLVED` 유무로 분기. 충돌 해소 파일 없으면 `HARNESS_UPGRADE=1`로 review skip, 있으면 해당 파일만 `--quick` review
- `harness-upgrade/SKILL.md` Step 3: MIGRATIONS.md `### 변경 파일` 표를 git diff보다 우선 참조해 처리 방식 결정
- `MIGRATIONS.md` 포맷에 `### 변경 파일` 섹션 추가 — 파일별 처리 방식(`자동 덮어쓰기`·`3-way merge`·`신규 추가`·`삭제`) 명시

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.8 — commit Step 4 다운스트림 skip 명시

### 변경 내용

- `commit/SKILL.md` Step 4: `is_starter` 값을 먼저 확인해 `false`(다운스트림)이면 Step 4 전체를 건너뛰도록 명시. 기존에는 스크립트가 내부적으로 exit했지만 Step 자체는 실행됐음

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.7 — harness_version_bump.py HEAD 버전 기준 수정

### 변경 내용

- `harness_version_bump.py`: `current` 버전을 디스크(HARNESS.json)가 아닌 HEAD에서 읽도록 수정. commit Step 4에서 HARNESS.json을 디스크에 먼저 쓰고 staged하면 `current`가 이미 범프된 버전을 가리켜 "범프 필요" 오탐 발생하던 버그 수정

### 적용 방법

**자동 적용**: 스크립트 갱신

**수동 적용**: 없음

---

## v0.26.6 — harness-upgrade Step 9.7 오탐 수정 + Step 10.4 제거

### 변경 내용

- harness-upgrade Step 9.7: `grep "- \[ \]"` 패턴이 백틱 인라인 코드(`` `- [ ]` ``)까지 오탐하던 문제 수정 — `grep -v` 추가
- harness-upgrade Step 10.4 제거: MIGRATIONS.md는 Step 3 자동 덮어쓰기로 이미 단일 섹션 유지됨. Claude가 섹션을 수동 삭제하는 불안정한 단계 제거

### 적용 방법

**자동 적용**: harness-upgrade SKILL.md 갱신

**수동 적용**: 없음

---

## v0.26.5 — hook 버전 체크 제거 + pre-check 경고로 이전

### 변경 내용

- `install-starter-hooks.sh`: hook의 버전 범프 체크 로직 제거. 버전 판단은 commit Step 4(Claude)가 담당
- `pre_commit_check.py`: is_starter 전용 버전 미범프 경고 추가 (차단 아님 — `risk_factors`에 기록)

### 적용 방법

**자동 적용**: 스크립트 갱신. hook은 `harness-sync` 또는 `bash .claude/scripts/install-starter-hooks.sh` 재실행으로 갱신.

**수동 적용**: 없음

---

