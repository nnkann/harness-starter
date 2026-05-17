# 코드 SSOT 규칙

defends: P11

같은 의미의 코드 로직이 여러 진입점에 분산되면 drift가 잠복한다. 1차
발견 시 다른 후보 위치를 자동 탐색하지 못하면 같은 패턴이 N곳에서
독립 진화 → 의미 갈라짐.

## 원칙 — 단일 진입점 강제

같은 데이터·필드·파생값을 다루는 로직은 단일 모듈을 거친다.

### 1. 3+ reference rule

동일 로직이 **3곳 이상**에서 발견되면 core 모듈로 추출한다.

- 2곳은 허용 — 분기 의도일 수 있다
- 3곳째 발견 시 추출 의무. 더 늘기 전에 차단
- "비슷해 보이는" 로직 무리 통합 금지 — 의미가 같아야 추출

### 2. Derived pointer pattern

Record/배열에서 "현재 대표값"을 파생할 때 단일 함수로 강제한다.

- 호출부마다 `array[0]`·`Object.values(record)[0]` 같은 임시 파생 금지
- "최신·기본·대표" 선택 로직은 함수 하나에 박는다
- 함수 이름이 의미를 박제(`getCurrent*`·`pickRepresentative*` 등)

### 3. New field pre-checklist

새 도메인 필드 추가 전 다음을 결정한다:

- [ ] 소유 모듈 (extraction·normalization·matching·persistence)
- [ ] 단일 함수 셋업 (모든 진입점이 통과)
- [ ] 모든 entry point 경유 확인 (parser·API·UI·migration)
- [ ] 추출/매칭/처리 흐름이 동일 모듈 안에 있음

이 4개 결정 없이 필드 추가 금지.

## Surgical Changes 충돌 해소

[coding.md](./coding.md) "Surgical Changes" 원칙(요청 범위 밖 건드리지
마라)과 본 규칙(3곳 발견 시 추출)은 판단 타이밍이 다르다.

- **현재 작업 범위 안**: Surgical Changes 우선. 3+ rule 위반 발견해도
  본 작업으로 추출 강행 금지
- **별 wave**: 추출 리팩토링을 작업 단위로 박는다. 위반 발견은 별 WIP
  생성 또는 `## 메모` 기록

"발견 = 즉시 추출"이 아니다. 발견 = 박제 + 다음 wave 의무.

## 다운스트림 사례 누적

본 규칙은 도메인 무관 일반 원칙만 둔다. 구체 사례·필드명·사고 경위는
다운스트림 `docs/incidents/` 또는 다운스트림 자체 audit 문서에 누적한다.

다운스트림에서 starter 규칙을 가리키는 형식:

```yaml
relates-to:
  - path: .claude/rules/code-ssot.md
    rel: references
```

## 금지

- **사전 추상화**: 2곳에서만 쓰이는 로직을 "나중을 위해" 미리 추출
- **사례명 starter 본문 인용**: 다운스트림 고유 필드명(특정 도메인 데이터)을
  본 규칙 본문에 박는 것 — 사례는 다운스트림 잔류
- **3+ rule 우회**: "복잡해 보여서" 그냥 두는 패턴 — 추출 비용보다 drift
  비용이 늘 크다
- **God Module 강제 통합**: 의미가 다른 로직을 SSOT 명목으로 한 모듈에
  강제 통합 — 결합도 증가, 필드별 독립 변경 어려워짐

## 참고

- 결정 근거: [hn_code_ssot_rule.md](../../docs/decisions/hn_code_ssot_rule.md)
- 하네스 내부 SSOT (스크립트·rule·skill 본문 중복): [hn_code_ssot_audit.md](../../docs/decisions/hn_code_ssot_audit.md) (P7 매핑, 별 트랙)
