---
title: docs-ops.sh cluster-update 성능 저하 — extract_abbrs() 반복 호출
domain: harness
tags: [docs-ops, cluster-update, performance]
status: completed
created: 2026-04-23
updated: 2026-04-23
symptom-keywords:
  - docs-ops.sh
  - cluster-update
  - extract_abbrs
---

## 증상

`bash .claude/scripts/docs-ops.sh cluster-update` 실행 시 완료까지 수 분 이상 소요.
commit 스킬에서 문서 이동 후 cluster-update를 호출하는 경로에서 체감 지연 발생.

## 환경

- 다운스트림 docs 파일 수: **337개**
- 약어(abbr) 수: **17개** (naming.md 확정 도메인 기준)

## 원인

`cmd_cluster_update()` 내 이중 루프 구조에서 `extract_abbrs()`가 **파일마다 반복 호출**됨.

```
약어 17개 루프
  └─ find docs -name '*.md' (337개)
      └─ while 루프 — 파일마다 detect_abbr() 호출
          └─ detect_abbr() 내부에서 매번 extract_abbrs() 호출
              └─ extract_abbrs() = naming.md awk 파싱 (I/O + 프로세스 생성)
```

호출 횟수: 17 × 337 = **최소 5,729회** (실제로는 서브셸 오버헤드 포함).

`extract_abbrs()`는 매번 `naming.md`를 awk로 파싱하는 I/O 작업이며, bash 서브셸
`$()` 로 호출돼 프로세스 생성 비용도 수반.

## 재현 조건

docs 파일이 수십 개 이상인 다운스트림에서 cluster-update 실행 시 항상 발생.
업스트림 자체 테스트 환경(소수 파일)에서는 체감 안 됨.

## 수정 (v0.20.12)

**`ABBR_PATTERN` 환경변수 주입 인터페이스** 추가.

`detect_abbr()`이 `ABBR_PATTERN` 환경변수가 설정돼 있으면 `extract_abbrs()`를
재호출하지 않고 재사용. `cmd_cluster_update()`에서 루프 진입 전 1회 계산 후 export.

```bash
# detect_abbr() — ABBR_PATTERN 캐시 활용
local abbrs="${ABBR_PATTERN:-$(extract_abbrs | tr '\n' '|' | sed 's/|$//')}"

# cmd_cluster_update() — 루프 전 1회 계산
export ABBR_PATTERN=$(echo "$abbrs" | tr '\n' '|' | sed 's/|$//')
```

호출 횟수: 5,729회 → **1회**. 기존 `detect_abbr()` 단독 호출 경로는 폴백으로 유지.

## 영향 범위

- `commit` 스킬의 cluster-update 호출 경로 (문서 이동 후 자동 갱신)
- 직접 `docs-ops.sh cluster-update` 호출
- docs 파일이 많을수록 선형 이상으로 악화

## 도입 버전 / 수정 버전

- **도입**: v0.20.0 (audit #10 — docs-manager 스킬 → 스크립트 이관)
- **수정**: v0.20.12
