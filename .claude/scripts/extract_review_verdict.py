#!/usr/bin/env python3
"""review 응답에서 verdict 단어만 추출.

배경: Agent tool sub-agent 호출에서 prefill 미작동 → markdown 머릿말·
서론·코드 블록 leak 빈발. JSON 스키마·AC 매핑 의무로 강제하려 했으나
sub-agent에 안 먹힘 (5/5 leak 실측). commit 분기 결정엔 verdict 한 단어
(pass|warn|block)만 필요하므로 형식 강제 폐기 + 추출만 한다.

배경 결정: docs/decisions/hn_review_verdict_compliance.md (v0.30.7 단순화).

입력: stdin 텍스트 (review 응답 원문, 형식 자유)
출력: stdout에 pass|warn|block 한 줄
exit:
  0 — verdict 추출 성공
  1 — pass|warn|block 단어를 못 찾음 (재호출 트리거)
"""
import re
import sys


def extract(text: str) -> str | None:
    m = re.search(r'\b(pass|warn|block)\b', text)
    return m.group(1) if m else None


def main() -> int:
    v = extract(sys.stdin.read())
    if v is None:
        return 1
    print(v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
