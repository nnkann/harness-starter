# 네이밍 규칙

<!-- naming-convention 스킬 실행 후 채워진다 -->

## 도메인 목록
확정: harness, meta
후보:

## 도메인 등급 (review staging)

`/commit` 시 review 강도 자동 결정용. `.claude/rules/staging.md` 참조.

- **critical** (변경 시 무조건 deep): harness
- **normal** (크기 기준 분기): (없음)
- **meta** (skip 검토): meta

다운스트림 프로젝트는 자기 도메인을 추가:
```
- critical: payment, auth, infra, migration, security
- normal:   api, data, ui
- meta:     docs, changelog
```

이 섹션이 비어 있으면 staging.md의 S9 신호 무시 (S7 일반 코드로 폴백).

## 경로 → 도메인 매핑 (선택, 코드 영역용)

`docs/` 외 코드 파일의 도메인을 추출하기 위한 경로 매핑. 정의 안 하면
프론트매터·WIP 접두사로만 추출.

예시 (다운스트림 프로젝트):
```
src/payment/**     → payment
src/auth/**        → auth
src/api/**         → api
infra/**           → infra
migrations/**      → migration
```

이 레포(harness-starter)는 코드 폴더가 거의 없어 정의 생략.

## 폴더명

## 파일명

## 클래스/함수/메소드
