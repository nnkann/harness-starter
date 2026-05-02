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

---

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

---

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

---

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

---

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

---

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

