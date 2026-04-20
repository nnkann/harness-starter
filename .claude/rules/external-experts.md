# External Experts — 분야별 레퍼런스 인물 캐시

researcher 에이전트가 외부 조사 시 참조할 업계 탑 인물 목록. **빈 상태로
시작하고 점진 축적**한다.

## 동작 규약

- researcher는 호출 시 먼저 이 파일에서 해당 분야를 조회한다.
- 없으면 1회 메타 검색("who is leading expert in <분야>") → 1~2명 식별 →
  자료 수집(최대 2 소스) → 이 파일에 자동 추가.
- 신뢰 단계: `최초 식별 (미검증)` → `다회 사용됨 (신뢰)` → `사용자 확정`
- 만료 없음. 정보 낡음 의심 시 사용자가 수동 무효화.
- 분야 없으면 스킵 — 일반 researcher 흐름으로 폴백.

## 저장 형식

```markdown
## <분야>

- <이름> (<핸들/소속>)
  - 최근 포지션: <2~3문장 요약>
  - source: <URL>
  - 신뢰: 최초 식별 (미검증) | 다회 사용됨 | 사용자 확정
  - 마지막 참조: YYYY-MM-DD
```

## 분야 캐시

### 엔지니어링 의사결정

- Will Larson (@lethain, Carta CTO)
  - 최근 포지션: "An Elegant Puzzle", "Staff Engineer" 저자. Staff
    Engineer 역할의 기술 결정 트레이드오프 체계화. 핵심 주장: "기술
    결정은 트레이드오프 열거가 핵심이며, 확신보다 투명성이 중요."
  - source: https://www.goodreads.com/book/show/56481725-staff-engineer
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-20

- Camille Fournier (전 Rent the Runway CTO, "The Manager's Path" 저자)
  - 최근 포지션: 엔지니어링 조직 설계·프로세스 전문가. 핵심 주장: "좋은
    프로세스는 지루해야 한다 — 예측 가능성이 신뢰를 만든다."
  - source: https://www.range.co/blog/camille-fournier-boring-plans
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-20

- Charity Majors (Honeycomb.io 공동창업자·CTO)
  - 최근 포지션: 프로덕션 관찰가능성 옹호자. 핵심 주장: "의사결정은
    추측이 아니라 실제 운영 데이터로 해야 한다."
  - source: https://www.honeycomb.io/author/charity
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-20

### 소프트웨어 아키텍처 결정 기록

- Michael Nygard (Cognitect/Nubank, ADR 창안)
  - 최근 포지션: "Release It!" 저자. 2011년 ADR 포맷 창안. 핵심 주장:
    "결정 자체보다 결정 당시의 맥락이 더 빠르게 소실된다 — 그것을
    기록해야 한다."
  - source: https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-20

- Martin Fowler (Thoughtworks 수석 과학자)
  - 최근 포지션: 소프트웨어 아키텍처·리팩토링 권위자. ADR을 공식 인정.
    핵심 주장: "superseded 결정은 수정 말고 새 ADR로 연결해야 한다."
  - source: https://martinfowler.com/bliki/ArchitectureDecisionRecord.html
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-20

### LLM 에이전트 메모리 아키텍처

- Charles Packer (Letta 공동창업자, MemGPT 창안자)
  - 최근 포지션: MemGPT 논문(2023) 제1저자. UC Berkeley → Letta 창업.
    Core/Recall/Archival 3계층 메모리·sleep-time compute 정제 패턴 제안.
    핵심 주장: "LLM의 컨텍스트는 OS의 RAM과 같다 — 외부 메모리와의
    페이징 전략이 에이전트의 장기 일관성을 결정한다."
  - source: https://arxiv.org/abs/2310.08560
  - 신뢰: 최초 식별 (미검증)
  - 마지막 참조: 2026-04-21
