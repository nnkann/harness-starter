# Internal-First 규칙

새 구조·가설·해결책을 제안하기 전, **반드시 내부 자료부터** 확인한다.
배경·자동 감지 트리거 상세는 `docs/decisions/rules_metadata_260420.md` 참조.

## 우선순위 (위→아래)

1. **사용자 증언** — "예전엔 됐다"는 말이 있으면 그 시점을 찾기가 **최우선**
2. **git history** — `git log --all --oneline | grep <키워드>` → 해당 시점
   파일 내용 확인. 작동했던 시점이 있으면 거기서 출발
3. **docs/** — INDEX.md → clusters/{domain}.md → decisions/incidents/guides
4. **rules/** — 관련 규칙·금지 사항이 이미 있는지
5. **외부** (Context7, 웹 검색, 공식 문서) — 위 4단계가 비었을 때만

**외부 검색이 1·2·3·4보다 먼저 나가면 이 규칙 위반.**

implementation Step 0와 commit Step 6에서 review가 외부 자료 언급 + 내부
자료 참조 누락 패턴을 감지해 경고한다.

## 외부 검색이 정당한 경우

- 외부 라이브러리·SDK의 최신 API 시그니처 확인
- 새 프레임워크 도입 검토 (내부 사용 이력 없음 확인 후)
- 보안 권고·CVE 확인

이 경우에도 "내부에 유사 사례가 없는지 먼저 확인했다"는 근거를 남길 것.

**도구 선택** → `docs/guides/external-research-patterns_260420.md`
- Context7 MCP 금지, HTTP API(curl) 사용
- WebFetch는 URL 알 때만
- WebSearch는 최후 수단

## 위반 시

- review 에이전트가 "내부 자료 확인 누락" 경고
- 사용자가 추측 기반 수정을 발견하면 즉시 되돌리고 internal-first 재실행
