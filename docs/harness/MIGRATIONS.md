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

## v1.8.1 — pre-check lint stdout 오염 수정 + commit push 보강

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 패치 — lint 명령의 stdout/stderr
  모두 캡처 후 종료 코드만 평가. 이전엔 stdout만 흘려 신호 줄과 섞임.
- `.claude/skills/commit/SKILL.md` 푸시 섹션 강화 — `is_starter: true`
  분기 + `HARNESS_DEV=1 git push` 명시.
- `.claude/scripts/test-hooks.sh` push 회귀 케이스 추가 (S1).

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

## v1.7.0 — 하네스 단순화 (마찰 회수)

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
bash .claude/scripts/test-hooks.sh         # 11/11 통과 기대

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

## v1.6.x 이전

기록 없음. v1.7.0이 본 마이그레이션 가이드 도입 시점. 이전 버전은
`docs/harness/promotion-log.md`의 변경 항목을 참조.
