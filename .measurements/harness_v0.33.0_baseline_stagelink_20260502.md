# Harness v0.33.0 Baseline Trace — StageLink (2026-05-02)

업스트림 `docs/WIP/decisions--hn_downstream_amplification.md` Phase 4-A 측정 결과.

## 환경
- 프로젝트: StageLink (K-POP 공연 정보 플랫폼, Next.js 15 + Express + Supabase + n8n 모노레포)
- 도메인 수 (확정): 18 (harness, meta, crawler, pipeline, blog, web, api, database, design, infra, admin, concert, pricing, poster, artist, venue, ticketing, link)
- 등록된 abbr 수: 18 (도메인당 1개, 1:1)
- docs/ 총 문서 수: 359
  - WIP: 4
  - decisions: 85
  - guides: 56
  - incidents: 95
  - harness: 37
  - clusters: 18
  - archived: 64
- 측정 작업: lk(link) 도메인 DB 스키마 마이그레이션 — tag_axes/tags/concert_tags 등 7개 테이블 신설

## 측정값

### (a) implementation Step 0 진입 ~ Step 0.8 완료
- wall time = 83.4초
  - init check: 19.7초
  - doc-finder fast scan: 12.3초
  - SSOT 3단계: 34.4초
- tool calls = 8회
  - init check: Bash(ls) + Grep = 2
  - doc-finder: Glob×2 + Grep×1 = 3
  - SSOT: Read(cluster) + Grep×2 + Read(후보) = 4 (1개 중복 보정 후 8회)

특이사항: CLAUDE.md `## 환경`에 `패키지 매니저:` 키가 없음 (다운스트림이 자체 양식). project_kickoff.md도 sample만 존재. 정상 시나리오라면 implementation이 ⛔ "init 미완료" 차단해야 하지만 다운스트림에서는 이 게이트가 false-block. 측정에서는 차단 무시하고 0.3 진행.

### (b) doc-finder fast scan
- tool calls = 3회 (Glob 2 + Grep 1)
- wall = 12.3초
- hit = 1 (`docs/WIP/decisions--lk_domain_architecture.md`)
- 키워드: `lk`, `tag_axes`, `ontology`, `마이그레이션` → 파일명 `lk_*` glob은 hit 0 (WIP `--` prefix 때문에 매칭 실패), `*tag*` glob은 hit 9이지만 무관 파일 다수, tags frontmatter grep으로 1건 확정

### (c) SSOT 3단계 탐색
- cluster scan (`docs/clusters/link.md`): 5.6초, hit 0
  - link cluster는 비어있음 (WIP는 cluster 미포함이 정상)
- keyword grep (본문 2회): 12.6초, unique hit 6
- 후보 Read: 6.2초, 1개 파일 (50줄)

### (d) commit 시 clusters 갱신 — 최근 5 commit
- 142ae2f (하네스 v0.33.0 업그레이드): 18/18 cluster 전부 갱신
- 656208d (gitignore 추가): 0
- ad2ed23 (v0.27.2 업그레이드): 0
- 525d6c9 (v0.27.0 업그레이드): 0
- 9cf7615 (revert admin): 0

신규 문서 추가/이동이 없는데도 cluster-update를 호출하면 18개 파일 전부 mtime 갱신 후 staging됨. v0.33.0 업그레이드는 docs_ops.py 본체 변경으로 출력 포맷 바뀐 것으로 추정. **상시 N 비례 갱신 아님**.

## 관찰

### 가장 비싼 단계
SSOT 3단계 탐색 (34.4초, 41%) > init check (19.7초, 24%) > doc-finder (12.3초, 15%)

### 도메인 수 비례 비용 — 부분 Y
- Y: cluster 재생성, cluster scan hit rate 저하
- N: keyword grep, doc-finder fast scan

### 다른 병목 후보
1. CLAUDE.md/CPS 양식 drift — 19.7s 헛 시간
2. cluster-update의 "전체 재생성" 비용 — incremental update 후보
3. cluster scan의 hit rate — WIP 미포함 설계 부작용
4. Glob 패턴 미스매치 — 라우팅 태그 `--` 통과 못 함

### 비교 baseline
- starter 단독 환경 추정 SSOT 약 10~15초 (실측 후 정확화)
- StageLink 실측 34.4초 / 추정 starter 12초 = 약 2.8x amplification

## 측정 한계
- N=1
- wall time에 Bash 타임스탬프 호출 오버헤드 포함
- 인간 사고 시간 미포함
- starter baseline 부재 — 본 보고 수령 후 starter 단독 측정으로 보강
