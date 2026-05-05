---
title: session-start.sh → session-start.py 전환 — spawn 비용 절감
domain: harness
problem: P6
solution-ref:
  - S6 — "행동 정의 문서 변경 효과가 검증 없이 커밋됨 (부분)"
tags: [performance, session-start, python]
relates-to: []
status: in-progress
created: 2026-05-05
updated: 2026-05-05
---

# session-start.sh → session-start.py 전환

## 사전 준비
- 읽을 문서: `.claude/scripts/session-start.sh` (현재 bash 구현 전체)
- 이전 산출물: 없음

## 목표
- session-start.sh의 모든 기능을 session-start.py로 완전 포팅
- bash 서브프로세스 spawn 23~25회 → python subprocess 최소화
- 실행 시간 0.8~0.9초 → 0.3~0.4초 목표
- settings.json SessionStart hook 명령 교체

## 작업 목록

### Phase 1 — session-start.py 작성 + settings.json 교체

**영향 파일**:
- `.claude/scripts/session-start.py` (신규)
- `.claude/settings.json` (hook 명령 교체)

**주의사항**:
- session-start.sh는 즉시 삭제하지 않는다. 검증 후 별도 커밋에서 제거.
- git 명령은 subprocess로 묶어서 호출 횟수를 최소화한다.
- stderr 출력이 필요한 섹션(연속 수정 감지)은 sys.stderr에 쓴다.
- Windows Git Bash 경로 호환: Path 사용, 슬래시 방향 주의.

**Acceptance Criteria**:
- [x] Goal: session-start.py가 session-start.sh와 동일한 출력을 내고 ✅
       실행 시간이 0.5초 이하
  검증:
    review: self
    tests: 없음
    실측: time python3 .claude/scripts/session-start.py 로 실행시간 측정.
          출력 내용을 session-start.sh 출력과 육안 비교.

- [x] 9개 섹션 전부 포팅 (git 상태, WIP, memory, TODO, 좀비, upgrade, 연속수정, rules) ✅
- [x] BIT 스코프 외 이슈 감지 + NEW P# 알림 포함 ✅
- [x] settings.json SessionStart hook → python3 .claude/scripts/session-start.py ✅
- [x] 실행시간 0.5초 이하 실측 확인 ✅ (0.28~0.35초 — bash 0.8~0.9초 대비 66% 단축)

## 결정 사항

## 메모
- bash 현재 총 spawn: 23~25회 (performance-analyst 분석)
- 가장 큰 병목: 섹션 7 연속수정감지 (10 spawn) + 섹션 1 git 상태 (10 spawn)
- python subprocess.run()으로 git 명령 결과를 파이썬 내부에서 처리 → spawn 횟수 대폭 감소
- CPS 갱신: 없음
