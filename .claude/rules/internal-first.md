# Internal-First 규칙

defends: P1

새 구조·가설·해결책을 제안하기 전, **반드시 내부 자료부터** 확인한다.

## 우선순위 (위→아래)

1. **사용자 증언** — "예전엔 됐다"는 말이 있으면 그 시점을 찾기가 최우선
2. **git history** — `git log --all --oneline | grep <키워드>` → 해당 시점 파일
3. **docs/** — clusters/{domain}.md → decisions/incidents/guides
4. **rules/** — 관련 규칙·금지 사항이 이미 있는지
5. **외부** (WebFetch, 웹 검색, 공식 문서) — 위 4단계가 비었을 때만

**외부 검색이 1~4보다 먼저 나가면 위반.**

## 외부 검색 정당화 조건

- 외부 라이브러리·SDK 최신 API 시그니처 확인
- 새 프레임워크 도입 검토 (내부 사용 이력 없음 확인 후)
- 보안 권고·CVE 확인

이 경우에도 "내부에 유사 사례가 없는지 먼저 확인했다"는 근거를 남길 것.
도구 선택은 `docs/guides/hn_external_research_patterns.md` 참조.
