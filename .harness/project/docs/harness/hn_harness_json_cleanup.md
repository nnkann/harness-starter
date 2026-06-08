---
title: HARNESS.json skills 목록 정리 — 1회성 스킬 삭제 + 활성 목록 정비
domain: harness
tags: [harness-json, skill, cleanup, metadata]
problem: P7
s: [S7, S9]
status: completed
created: 2026-04-25
updated: 2026-04-25
---

# HARNESS.json skills 목록 정리

## 배경

현재 `.claude/HARNESS.json`의 `skills` 값:
```
harness-init, harness-adopt, harness-sync, harness-upgrade,
implementation, commit, advisor, check-existing, write-doc,
naming-convention, coding-convention, eval
```

1회성·준1회성 스킬이 활성 스킬과 혼재. 이미 실행 완료된 스킬이 목록에
계속 남아 있을 이유가 없음. 업스트림에서 필요 시 다시 가져올 수 있음.

## 스킬 분류

| 스킬 | 분류 | 현재 상태 |
|------|------|---------|
| `harness-sync` | 1회성 | 클론 직후 1회. 이미 완료. 삭제 대상. |
| `harness-adopt` | 1회성 | adopt 완료. 재실행 시나리오 없음. 삭제 대상. |
| `naming-convention` | 준1회성 | 세팅 완료. `rules/naming.md`가 SSOT. 삭제 대상. |
| `coding-convention` | 준1회성 | 세팅 완료. `rules/coding.md`가 SSOT. 삭제 대상. |
| `harness-init` | 준1회성 | 다운스트림 셋업 시 트리거. starter 본체 비활성. 삭제 대상. |
| `harness-upgrade` | 간헐적 | 업스트림 변경 시 트리거. 유지. |
| `implementation` | 활성 | 매 구현 작업. 유지. |
| `commit` | 활성 | 매 커밋. 유지. |
| `advisor` | 활성 | 아키텍처·기술 결정. 유지. |
| `check-existing` | 활성 | 새 함수·모듈 전. 유지. |
| `write-doc` | 활성 | 단독 문서 생성. 유지. |
| `eval` | 활성 | 주기적 건강 검진. 유지. |

## 변경 방향 — 안 C (확정)

1회성 스킬을 **삭제**. 필드 구조 변경 없이 `skills` 목록만 정리.
업스트림에서 필요 시 `harness-upgrade`로 재취득 가능.

```json
{
  "skills": "harness-upgrade,implementation,commit,advisor,check-existing,write-doc,naming-convention,coding-convention,eval"
}
```

> 안 A(필드 분리)·안 B(별도 필드 추가)는 기각.
> 1회성 스킬 삭제 후 분류 문제 자체가 해소되므로 구조 변경 불필요.

**삭제 스킬**: `harness-sync`, `harness-adopt`, `harness-init`

**유지 이유 있는 것**:
- `naming-convention`, `coding-convention`: 다운스트림 프로젝트가 아직 세팅
  전이라면 필요할 수 있음. starter 기준으로는 완료지만, 다운스트림 배포
  용도를 고려해 일단 유지. → 이 WIP에서 결정 후 반영.
- `harness-upgrade`: 주기적으로 쓰임. 유지.

## skills 정리 효용

1. **Claude Code 스킬 로딩 범위 축소**: Claude Code는 HARNESS.json `skills` 목록을
   기준으로 사용자에게 스킬을 제안. 불필요한 스킬이 있으면 제안 노이즈 발생.
2. **실제 활성 스킬 파악 즉시 가능**: `HARNESS.json`만 봐도 "지금 쓸 수 있는 것"
   확인 가능. 다운스트림 프로젝트가 상속·참고 시 기준이 명확.
3. **하네스 무결성 검사 정확도 향상**: `harness-sync` Step 6이 `skills` 목록과
   실제 `skills/` 디렉토리를 비교. 목록에 없는 스킬 디렉토리는 "추가 스킬"로
   감지됨 — 삭제 후 이 감지가 더 정확해짐.

## 미래 스코프 (현재 제외)

- 업스트림 보고 시스템: 현재 스코프 밖. 논의 필요 시 별도 WIP 생성.

## 작업 목록

### 1. HARNESS.json 수정
> kind: chore

**사전 준비**:
- 읽을 문서: `.claude/HARNESS.json` (현재 상태 확인)
- 이전 산출물: 없음

**영향 파일**:
- `.claude/HARNESS.json`

**Acceptance Criteria**:
- [ ] `skills` 목록에서 `harness-sync`, `harness-adopt`, `harness-init` 제거됨
- [ ] `naming-convention`, `coding-convention` 유지 여부 확정 후 반영됨
- [ ] 실제 `.claude/skills/` 디렉토리 파일은 그대로 유지 (삭제 금지 — 업스트림 배포용)

---

### 2. harness-sync Step 6 점검
> kind: chore

`harness-sync/SKILL.md` Step 6이 `HARNESS.json`의 `skills` 목록으로
`skills/` 디렉토리를 비교. 삭제된 스킬이 "누락 스킬"로 오탐될 수 있음.

**사전 준비**:
- 읽을 문서: `.claude/skills/harness-sync/SKILL.md` (Step 6 로직 확인)
- 이전 산출물: 작업 1 완료 후 진행

**영향 파일**:
- `.claude/skills/harness-sync/SKILL.md` (Step 6 비교 로직 수정 필요 시)

**Acceptance Criteria**:
- [ ] Step 6 로직이 "skills 목록에 없는 디렉토리 = 추가 스킬"로 올바르게 동작
- [ ] 오탐(삭제된 스킬을 "누락"으로 잡는 것) 없음

---

### 3. 하네스 버전 범프
> kind: chore

메타데이터 변경. patch 범프.

**Acceptance Criteria**:
- [ ] `HARNESS.json` `version` patch 범프됨

---

## 결정 사항

- 방향: 안 C — 1회성 스킬 삭제. 필드 구조 변경 없음.
- 삭제: `harness-sync`, `harness-adopt`, `harness-init`. 디렉토리 파일은 유지.
- `naming-convention`, `coding-convention` 유지 (다운스트림 배포 용도).
- version 0.22.0 → 0.22.1 patch 범프.
- harness-sync Step 6 오탐 없음 — 삭제된 스킬은 "추가 스킬 (정보 출력)" 처리, 경고 아님.

## 메모

- `.claude/skills/` 디렉토리에 harness-sync·adopt·init은 그대로 존재. 업스트림 배포용.
- harness-sync Step 6: skills 목록 ↔ 디렉토리 비교에서 "목록에 없는데 디렉토리에 있으면 정보 출력"이므로 경고 없음. 수정 불필요.
