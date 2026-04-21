---
title: 린터 도구 실종 — T13이 우연히 가시화한 환경 이슈
domain: harness
tags: [testing, lint, env, diagnosis-discipline]
symptom-keywords:
  - T13.1 repeat_count 다운스트림 격리 실패
  - 44/45 T13.1만 실패
  - eslint is not recognized
  - next is not recognized
  - npm run lint exit 2
  - pre-check 린터 스킵
  - TEST_DEBUG=1
relates-to:
  - path: decisions/hn_review_staging_rebalance.md
    rel: references
status: completed
created: 2026-04-22
updated: 2026-04-22
---

# 린터 도구 실종 — T13이 우연히 가시화한 환경 이슈

> **파일명 주석**: `git_log_leak` 파일명은 v0.18.1의 **초기 가설**(철회됨)
> 에서 유래. 실제 원인은 린터 도구 실종. symptom-keywords에 옛·새 키워드
> 모두 포함되어 grep 탐색 유지. 파일명 변경은 git history·링크 깨짐
> 부작용이 커 보존 결정.

## 결론 — 진짜 원인

다운스트림 repo(`<프로젝트 사례>`)의 `npm run lint` 실행이 **`eslint`·
`next` 바이너리를 PATH에서 찾지 못해 exit 2**:

```
'eslint' is not recognized as an internal or external command
'next' is not recognized as an internal or external command
```

`node_modules` 누락 또는 PATH 문제. pre-commit-check.sh의 린터 단계가
매 커밋·매 테스트 실행마다 exit 2를 반환하던 상태.

**T13이 유일하게 FAIL로 보인 건 우연** — run_case 헬퍼는 stdout의
key-value만 grep하고 pre-check stderr를 버리기 때문에 린터 실패가
PASS/FAIL 판정에 영향 주지 않음. T13만 `exit_code`를 직접 체크하는
구조라서 린터 실패의 exit 2가 여기서만 노출.

실제로는 **스위트 전체가 린터 실패 환경에서 돌고 있었음**. T13.1은
증상이었지, 원인 지점이 아니었음.

## 증상 이력

- v0.18.0 병합 후 다운스트림에서 `test-pre-commit.sh` **44/45 보고
  (T13.1만 FAIL)**
- upstream 격리 clone은 45/45 통과 — upstream은 CLAUDE.md의 패키지
  매니저 비어 있어 린터 스킵, 다운스트림은 npm 프로젝트라 린터 실행
- 수동 T13 재현(동일 steps, pre-check 직접 호출)은 **exit 0** — 이 경로는
  린터 아닌 다른 단계만 밟음? **아님. 수동 실행이 package.json이 있는
  디렉토리가 아니었거나**, 또는 사용자가 manual 재현 시 CLAUDE.md의
  패키지 매니저 설정을 다르게 읽었을 가능성

## 관찰·확정 과정

### v0.18.1 (2026-04-22): 잘못된 가설 확정
- 최초 진단: "고정 파일명 `docs/WIP/test--scenario_260419.md`가 다운스트림
  repo 히스토리와 교차 오염 → `git log -5 <file>` 기반 S10 카운트 부풀림"
- 파일명 unique화로 fix 시도 (A안)
- **실수**: upstream 45/45 통과를 근거로 "병합 무결 = 원인 진단 완료"로
  착각. 다운스트림 재검증 없이 merge·push

### v0.18.2 (2026-04-22): 가설 철회·TEST_DEBUG 훅 추가
- 다운스트림 재검증 결과 unique 파일명 적용 후에도 T13.1 exit 2 지속
- **unique 파일명이면 git history 교차 자체 불가능** → 최초 가설 오답
  자인
- 스위트 내부 FAIL 분기가 `output` 캡처만 하고 출력 안 해 stderr
  사유 불명 → `TEST_DEBUG=1` 옵트인 훅 추가

### v0.18.3 (2026-04-22): 원인 확정
- 다운스트림에서 `TEST_DEBUG=1` 실행 → stderr dump에 **린터 도구 실종**
  확인
- `eslint`·`next`가 PATH에 없음 → lint exit 2 → pre-check exit 2 →
  T13.1 FAIL
- 원인은 pre-check·테스트 스크립트와 **무관**. 다운스트림 환경 이슈

## 해결 (v0.18.3)

### B-3. 린터 도구 실종 구분 (upstream fix)

`pre-commit-check.sh` 린터 단계에서 ENOENT 패턴을 실제 rule 위반과
구분:

```bash
if echo "$LINT_OUTPUT" | grep -qE "is not recognized as an internal or external command|command not found|No such file or directory|Cannot find module|ENOENT"; then
  echo "⚠ 린터 도구 미설치 또는 PATH 누락. 린트 스킵 (커밋 계속)." >&2
  # ERRORS 증가 없음 — 환경 문제는 다운스트림이 해결
else
  echo "❌ 린터 에러. 에러 0에서만 커밋 가능." >&2
  ERRORS=$((ERRORS + 1))
fi
```

**정책**:
- 도구 실종 → warn + skip (커밋 계속). 환경 문제는 차단 대상 아님
- 실제 rule 위반 → 기존대로 차단
- 패턴은 **보수적 문자열 매칭** — ESLint 자체 출력과 겹치지 않음

### A. 테스트 파일명 unique화 (유지)

v0.18.1에서 추가한 `test--scenario_$$_$(date +%s).md` unique화는 실제
다운스트림 원인과 **무관**했지만, **고정 경로 교차 리스크**는 이론적으로
존재 → 별도 리스크 봉쇄 가치로 유지.

### TEST_DEBUG=1 훅 (유지)

v0.18.2에서 추가한 옵트인 디버그 출력은 본 사안 해결에 결정적 도구였음.
범용 진단 가치가 있어 유지.

## 교훈 (과정 자체에 대한)

### 관찰 없이 가설 확정 금지
- 초기 가설("git log 교차")이 그럴듯해서 `unique 파일명이면 교차 불가능`
  이라는 단순 반증을 놓침. `rules/no-speculation.md` "첫 행동 3원칙"
  위반
- **upstream 격리 통과 ≠ 원인 진단 완료**. 격리 환경은 재현 환경을 전부
  커버하지 못함. 격리 통과는 "병합 로직 무결"만 증명

### 테스트 인프라가 정보를 버리면 진단 불가
- run_case가 stderr 버리는 건 의도 (stdout 파싱 보호)지만, **exit_code를
  체크하지 않으면 환경 실패가 PASS로 위장**
- T13만 exit_code 체크했던 탓에 문제가 "T13 고유 버그"로 오인됨. 실제로는
  **스위트 전체의 린터 실패**가 T13에서만 가시화

### 환경 문제와 코드 문제 구분
- "린터 실패"에 도구 실종(ENOENT)과 rule 위반 두 가지가 섞여 있었음
- 둘 다 exit ≠ 0이라 현재 pre-check은 동일 처리 → 환경 마찰이 커밋 차단
  으로 이어짐. B-3 fix로 구분

## 다운스트림 수동 액션

- [ ] **`npm install`** — node_modules 복구. 근본 해결
- [ ] v0.18.3 upgrade 후 pre-check이 린터 스킵 warn으로만 경고하는지 확인
- [ ] 정상 린터 환경에서 rule 위반 테스트 — 기존처럼 차단되는지 확인

## 변경 이력

- 2026-04-22 (v0.18.1): 최초 진단 `git log 교차`를 원인으로 확정, 파일명
  unique화로 fix 시도. **관찰 없이 확정한 실수**, 다운스트림에서 여전히
  exit 2
- 2026-04-22 (v0.18.2): 가설 철회, `TEST_DEBUG=1` 훅 추가. status:
  in-progress (원인 미확정 자인)
- 2026-04-22 (v0.18.3): 다운스트림 TEST_DEBUG dump로 **린터 도구 실종**
  원인 확정. B-3 fix 반영. status: completed
