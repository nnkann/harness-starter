# Self-Verify 규칙

defends: P6

## 검증 워크플로우

```
WIP task AC 전부 [x]
  └─ work-verify (이 규칙): 내가 만든 것이 동작하는가? (린터 + AC가 요구한 테스트)
      └─ /commit 스킬 호출
           └─ commit-check (pre_commit_check.py): 커밋 가능한 상태인가?
               └─ review: 변경이 안전한가? (옵트인)
```

**AC 전부 [x] = self-verify 통과 기준.** 체크박스가 남아 있으면 미완료다.

## 원칙

성공 기준(AC)을 먼저 정의하고 구현하라. AC 없는 작업은 완료 선언 불가.

- WIP task AC 체크박스가 완료 기준
- 구현 후 AC 항목을 직접 실행·체크. "아마 됐겠지" 금지
- UI/frontend 변경 시: dev 서버 부팅 + 실제 동작 확인

## 검증 시점

- 파일 새로 만들거나 수정한 직후
- 함수/모듈 단위 작업 끝날 때
- 사용자에게 "완료" 보고 전

## 테스트 판단 — AC가 트리거 SSOT

| 상황 | 행동 |
|------|------|
| AC `검증.tests: pytest -m <marker>` | 그 marker만 실행 |
| AC `검증.tests: pytest <경로>` | 그 경로 실행 |
| AC `검증.tests: 없음` | 실행 안 함 |
| 사용자 명시 요청 | 요청 범위 실행 |
| 신규 함수·기능 | TDD/fail-first — 테스트 먼저 |
| 버그 수정 | 회귀 테스트 먼저, 수정 그 다음 |

### marker (test_pre_commit.py)

- `secret` — 시크릿 스캔
- `gate` — completed 봉인
- `stage` — pre_commit_check.py
- `enoent` — 린터 ENOENT 회귀
- `docs_ops` — dead link / wip-sync

전체 실행은 CI · 사용자 명시 요청 한정.

## 자동화 불가 검증 처리

Claude 행동·UI 동작·운용 시 효과는 자동화 불가:

1. "자동 검증 불가 — 운용에서 확인 필요" 명시
2. 테스트 커버 범위·미커버 범위 구분 전달
3. **자동화 불가 검증을 자동화한 것처럼 포장 금지**

예시:
- ❌ "테스트 54/54 통과 → 검증됐습니다"
- ✅ "테스트 54/54 통과 — pre-commit 로직 검증 완료. Claude 행동 변화는 운용에서 확인 필요"

## 행동 규칙

- 검증 없이 "완료" 금지
- 실패하면 스스로 고치고 재검증
- 3회 시도해도 안 되면 사용자 보고. 추측 금지
- 검증 결과를 숨기지 마라
