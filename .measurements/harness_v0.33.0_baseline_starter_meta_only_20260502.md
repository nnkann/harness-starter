# Harness v0.33.0 Baseline Trace — starter (meta 단독 시나리오, 2026-05-02)

업스트림 `docs/WIP/decisions--hn_downstream_amplification.md` Phase 4-A
보강 측정 (StageLink 보고 후 starter 단독 baseline 부재 한계 해소).

## 환경
- 프로젝트: harness-starter (배포 템플릿)
- 도메인 수 (확정): 2 (harness, meta)
- abbr 수: 2
- docs 총: ~140
- 측정 작업: `.measurements/` 디렉토리 신설 + README 작성 (meta 도메인 단독 변경)

## 측정값
| 단계 | wall (s) | tool calls |
|------|----------|------------|
| init check | 4.85 | 2 (Bash + Grep) |
| doc-finder fast scan | 9.96 | 2 (Glob + Grep) |
| SSOT 3단계 | 13.74 | 3 (Read + Grep×2) |
| **Step 0 합계** | **28.55** | **5** |

세부:
- doc-finder: hit 2 (둘 다 본 wave 관련 문서 — 신규 디렉토리 진행 OK 신호)
- SSOT cluster scan: meta cluster Read, hit 0 (정상 — meta 비어 있음)
- SSOT keyword grep: 본문 검색 hit 0

## StageLink 셋 재현 확인
- (f) **init check drift = N**. starter CLAUDE.md `## 환경`에 `패키지 매니저:` 키 존재 → 게이트 통과. 4.85s만 소비
- (g) **WIP cluster hit = N/A**. meta 단독 작업이라 WIP 검색 자체가 비핵심
- (h) **glob 라우팅 태그 통과 = 미측정** (meta 작업이라 라우팅 태그 abbr glob 시나리오 없음)

## 비교 — StageLink 대비

| 항목 | starter | StageLink | 비율 |
|------|---------|-----------|------|
| Step 0 wall | 28.55s | 83.4s | 2.9x |
| init check | 4.85s | 19.7s | 4.1x |
| doc-finder | 9.96s | 12.3s | 1.2x |
| SSOT 3단계 | 13.74s | 34.4s | 2.5x |
| tool calls | 5 | 8 | 1.6x |
| 도메인 수 | 2 | 18 | 9x |

## 관찰

### init drift는 게이트 결함이 맞다
StageLink 19.7s vs starter 4.85s = **4.1x 차이**. 도메인 수(9x)와
무관한 환경 양식 drift 비용. Phase 4-B (a) drift 게이트 정밀화는
다운스트림 보고 무관하게 선행 가능 — 효과 입증됨.

### doc-finder는 도메인 수 거의 무관
1.2x. 가설("고정 호출 수")과 일치. Phase 4-B에서 doc-finder 게이팅
우선순위 낮음.

### SSOT는 도메인 수보다 문서 수에 비례
도메인 9x인데 SSOT는 2.5x만 증가. 본문 grep이 ripgrep 효율로 빠르고,
cluster scan은 빈 cluster 만나도 즉시 종료(meta처럼). 도메인 수 비례
가설 약함, **문서 수 비례가 더 정확**.

### meta 단독 작업에서도 SSOT 13.74s 소비
Phase 4-B (a) `meta skip` 게이팅 효과 = SSOT 13.74s + doc-finder 9.96s
= **23.7s 절감 가능** (meta 단독 변경 시). 본 측정의 28.55s가 4.85s로
줄어듦. 큰 효과.

## 측정 한계
- starter는 도메인 2개 환경 — 중간 규모(5~10) baseline 부재
- 본 측정도 N=1 (단일 작업·단일 시나리오)
- wall에 측정 오버헤드(타임스탬프 Bash) 포함
- starter 자체가 평가 도구이자 평가 대상 — 자기참조 편향 가능

## 결론

1. **init drift 게이트 결함 확정** — 4.1x 차이 입증. Phase 4-B (a)
   선행 착수 정당화
2. **meta skip 게이팅 효과 큼** — meta 단독 변경에서 23.7s 절감
   (현 28.55s → 4.85s, ~83% 감소)
3. **도메인 수 비례 가설 약화** — 문서 수 + 환경 drift가 실제 변수
4. **추가 측정 필요**:
   - 중간 규모(5~10) 다운스트림 baseline (자연 발생 대기)
   - 4-B (a) 적용 후 starter·StageLink 재측정
