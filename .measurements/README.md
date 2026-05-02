# .measurements/

다운스트림·starter baseline trace 산출물 보존 디렉토리.

`docs/WIP/decisions--hn_downstream_amplification.md` Phase 4-A·4-B의
실측 데이터 원본을 여기에 둔다. WIP `## 메모`에는 요약만, 본 디렉토리에는
원본 보고서.

## 파일명 규칙

```
harness_v<버전>_baseline_<프로젝트명>_<YYYYMMDD>.md
harness_v<버전>_baseline_<프로젝트명>_<scenario>_<YYYYMMDD>.md
```

예:
- `harness_v0.33.0_baseline_stagelink_20260502.md`
- `harness_v0.33.0_baseline_starter_meta_only_20260502.md`

## 보존 정책

- Phase 4-B 절감 측정의 비교 baseline 역할
- 4-B 종료 후에도 회귀 가드용으로 보존
- gitignore 대상 아님 (재현 근거)
