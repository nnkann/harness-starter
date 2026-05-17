---
name: commit
description: 작업 잔여물 정리, 계획 문서 완료 처리, 변경 사항 분석 후 커밋+푸시. review 호출은 `--review`/`--no-review` 플래그 + 시크릿 게이트로 제어. `/commit` 또는 "커밋해줘" 요청 시 사용.
---

# /commit 스킬

커밋 잔여물 정리 + pre-check + review 분기 + 커밋 + push.

## 사용법

| 사용법 | 설명 |
|--------|------|
| `/commit` | review 안 함 (default). pre-check + 시크릿 게이트만 |
| `/commit --review` | review agent 호출. diff별 한 줄 의견 |
| `/commit --no-review` | review 명시 스킵 (보안 게이트 hit 시 무시) |

## 핸드오프 계약 (implementation 상속)

| 축 | 내용 |
|----|------|
| Pass | implementation→나: WIP 경로 · status · CPS 갱신 여부 |
| Pass | pre-check→나: `wip_problem` · `wip_solution_ref` · `s1_level` · `recommended_stage` |
| Pass | 나→review: AC 전문 + 전제 컨텍스트 + pre-check 결과 (self-containment) |
| Preserve | pre-check stage 원본 (재계산 금지) · 사용자 플래그 |
| Signal | ⛔ pre-check 차단·시크릿 line-confirmed |
| Record | commit log `🔍 review: <on\|off\|forced> \| problem: P# \| s: S#` |

## Step 1. 작업 잔여물 정리

- 컨텍스트에서 알 수 있는 임시 파일(`test-*.mjs`·`debug/` 등) 확인 후 삭제
- 좀비 프로세스 확인
- 사용자 명시 보존 파일은 제외

**prior_session_files 경고** (Step 4 pre-check 후 확인): pre-check stdout의
`prior_session_files` 값이 `none`이 아니면 1줄 환기. 사용자 결정.

## Step 2. 계획 문서 이동 (사용자 명시 요청만)

사용자가 "completed로 이동"·"잔여 분리"·"abandoned로 보내" 같이 **명시**한
경우만:

| 요청 | 동작 |
|------|------|
| "completed로 이동" | `python3 .claude/scripts/docs_ops.py move <WIP>` + cluster-update |
| "잔여 분리" | (a) `<원본>_followup.md` 신설 + `relates-to: rel: extends` (b) 원본은 `docs_ops.py move` |
| "abandoned로 보내" | status → abandoned + archived/로 이동 |

**`git mv` 직접 금지** — 역참조 dead link 누락.

**파일명 이동 규칙** (naming.md SSOT): `{abbr}_{slug}.md`. 라우팅 태그 폐기.
폴더는 frontmatter `domain` + abbr로 자동 결정.

**차단 조건**: `.claude/rules/docs.md` "## completed 전환 차단" SSOT. 키워드
hit 시 [c] 차단 → [p] 분리 권장.

## Step 3. 스테이징

`git status` 확인 후 `git add .` (특별 제외 요청 없으면).

**메타 파일 자동 병합** (분리 커밋 차단):
- `.claude/HARNESS.json` (버전 범프 시)
- `docs/clusters/*.md` (문서 추가·이동 시)

## Step 4. 하네스 버전 체크 (is_starter 전용)

```bash
python3 .claude/scripts/harness_version_bump.py
```

- `version_bump: none` → Step 5로
- `version_bump: patch|minor` → 사용자 확인 후 5개 일괄 처리:
  1. **HARNESS.json** `version` 갱신
  2. **MIGRATIONS.md** 새 섹션 삽입 (포맷 SSOT는 본 파일 상단)
  3. **archive 자동**: `harness_version_bump.py --archive` (6개째부터 이동)
  4. **README.md** 버전 + 변경 이력 최신 5개 유지
  5. **git add** 일괄 스테이징

다운스트림(`is_starter: false`)은 Step 5로 즉시 진행.

## Step 5. pre-check

```bash
PRE_CHECK_OUTPUT=$(python3 .claude/scripts/pre_commit_check.py)
```

**책임**:
1. 정적 게이트: 린터·TODO·dead link·시크릿·WIP 잔여
2. frontmatter 검증: staged WIP의 `problem`·`s` 누락 시 차단
3. **tag 정규식**: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` 위반 시 차단 (naming.md SSOT)
4. AC 추출: Goal·검증 묶음 누락 시 차단
5. stage 결정: 시크릿 line-confirmed → `deep`, 그 외 → `default`

**stdout 형식**:
```
pre_check_passed: true|false
wip_problem: P#
wip_solution_ref: S2; S6
recommended_stage: default|deep
s1_level: ""|file-only|line-confirmed
```

- **exit 2 (차단)**: stderr 메시지 사용자 전달. 수정 후 Step 3부터 재시도
- **exit 0 (통과)**: Step 6으로

**sub-커밋 예외**: `HARNESS_SPLIT_SUB=1`이면 pre-check 재실행 안 함.
부모 `PRE_CHECK_OUTPUT` 재사용.

## Step 6. review 분기

| 조건 | 호출 |
|------|------|
| `--no-review` | skip (보안 게이트 무시) |
| `--review` | 호출 |
| 플래그 없음 (default) | skip |
| `recommended_stage: deep` | **강제 호출** (--no-review 무시) |

**호출 방법** (`Agent` tool):

```
subagent_type: "review"
prompt:
  ## 이번 커밋의 목적
  <1~2줄>

  ## 연관 WIP 문서
  경로: docs/WIP/...
  Acceptance Criteria:
  <AC 전문>

  ## 전제 컨텍스트
  - is_starter: true|false
  - <배경 사실>

  ## pre-check 결과
  wip_problem: P#
  wip_solution_ref: S#
  s1_level: ...

  ## 지시
  WIP AC를 검증 기준으로. AC + 전제 컨텍스트만으로 판단 가능하면 즉시 의견 출력 — 파일 Read 금지.
  의심점 명확할 때만 Read/Grep, **합계 3회 이내**. 스코프 이탈 의심 시에만 `git diff --cached` 1회.

  ## 출력 형식
  diff별 한 줄 의견. verdict 단어 강제 없음. 명확 차단 사유 있으면 첫 줄 명시.
```

**응답 처리**: verdict 강제 추출 폐기. 응답 본문 사용자에게 그대로 전달.
사용자가 응답 보고 판단 (차단 → 수정 후 재시도, 경고 → 메시지 반영 후 진행).

**투명성**: 호출 직전 1줄 알림: `🔍 review: --review 플래그 (또는 시크릿 게이트 강제)`.

## Step 7. 커밋 + 푸시 (commit_finalize wrapper)

**`git commit` 직접 호출 금지** — `bash-guard.sh`가 차단. `HARNESS_DEV=1`
prefix + `commit_finalize.sh` wrapper 의무.

```bash
VERDICT="$VERDICT" HARNESS_DEV=1 \
  bash .claude/scripts/commit_finalize.sh \
    -m "feat: [제목]" \
    -m "[본문 — 🔍 review 라인 포함]"
```

**wrapper 내부**:
1. VERDICT != block 이면 staged 파일 추출 → `docs_ops.py wip-sync` 호출
2. wip-sync가 ✅ 마킹·move·cluster·역참조 일괄 staging
3. `git commit "$@"` 단일 호출

**git log 추적성** (본문 끝):
```
🔍 review: on|off|forced | problem: P# | s: S#
```

**커밋 메시지**: Conventional Commits (feat:·fix:·refactor:). 한국어. 본문에
변경 요약 1~3줄 + 연관 문서 경로.

**downstream 한 줄** (`.claude/scripts/**`·`agents/**`·`rules/**`·`settings.json` 변경 시):
```
downstream: <harness-upgrade 시 주의 1줄>
```

**확장 포맷** (`[📝 주요 참고 사항]` 섹션 — 아래 조건 중 하나 이상):
- 시크릿 line-confirmed (보안 게이트)
- review가 명확한 차단·주의 보고
- 아키텍처·설계 결정
- 까다로운 버그 원인·해결

## Step 8. push

`.claude/HARNESS.json`의 `is_starter`로 분기:

```bash
if [ "$IS_STARTER" = "true" ]; then
  HARNESS_DEV=1 git push origin main
else
  git push origin main
fi
```

**session snapshot 정리**: `commit_finalize.sh`가 `git commit` 성공 시 자동
처리 (v0.47.7 — wrapper 흡수). LLM 책임 없음.

**요약 출력**:
- 커밋 SHA + 메시지 1줄
- 변경 stat (파일 수, +/-)
- 리뷰 결과: ✅ 통과 / ⚠️ 경고 / 🚫 차단 / 리뷰 스킵
- push 결과 (origin/main SHA)

## 주의

- `--no-verify` 사용 금지 (bash-guard 차단)
- docs/WIP/에 completed/abandoned 잔재 금지
- 커밋 메시지 한국어
- review 차단 시 `--no-review`로 우회 금지. 지적 사항 수정 후 재시도
- AC 자동 실행은 **implementation 종료 단계로 이동** (§S-2 73% 삭감). commit은
  사실 게이트 + review 분기만
- split 발동 폐기 (§S-6 73% 삭감). 자동 거대 커밋 분리 없음. `HARNESS_SPLIT_OPT_IN=1`
  명시 옵트인만 잔존

