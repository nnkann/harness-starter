---
title: 마일스톤 추적 샘플
domain: meta
tags: [milestones, epic, sample]
status: sample
created: 2026-05-03
---

# 마일스톤 추적

> ⚠️ 이 파일은 **예제 샘플**입니다.
> 프로젝트에서 사용하려면 이 파일을 `docs/guides/milestones.md`로 복사해 내용을 채우세요.
> 도메인 5개 이상 또는 decisions 30+ 누적 시 활성화를 권장합니다.

## 에픽 설계 원칙

에픽은 **사용자가 얻는 가치** 중심으로 이름을 짓는다.

- ✅ "사용자가 공연 정보를 검색하고 저장할 수 있다"
- ✅ "팀원이 작업 상태를 실시간으로 공유할 수 있다"
- ❌ "Database Setup" — 기술 레이어명은 에픽이 아니다
- ❌ "API Development" — 사용자 가치가 없다

각 에픽은 다른 에픽 없이도 독립 동작해야 한다.
같은 파일을 반복 수정하는 에픽은 하나로 통합한다.

---

## 에픽 목록

### Epic 1: [사용자 가치 한 줄]

**상태**: backlog | in-progress | done

**왜**: 이 에픽이 해결하는 사용자 문제.

| 상태 | WIP / 문서 |
|------|-----------|
| done | `docs/decisions/hn_xxx.md` (완료 후 경로 기입) |
| in-progress | `docs/WIP/decisions--hn_xxx.md` (진행 중 경로 기입) |
| backlog | — |

---

### Epic 2: [사용자 가치 한 줄]

**상태**: backlog

**왜**: 이 에픽이 해결하는 사용자 문제.

| 상태 | WIP / 문서 |
|------|-----------|
| backlog | — |

---

## 현재 집중 에픽

```
현재: Epic 1 — [진행 중 작업 1줄] → [WIP 경로]
다음: Epic 2 — [착수 조건]
```

## 메모

에픽 완료 기준: 해당 에픽의 모든 WIP가 decisions/guides/로 이동되고,
`eval`에서 Solution 충족 인용이 증가한 것이 확인됐을 때.
