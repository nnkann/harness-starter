"""extract_review_verdict.py 회귀 가드.

review sub-agent 응답 형식 leak 케이스에서도 verdict 단어가 추출되는지
검증. 형식 강제 폐기 + 추출만으로 분기하는 단순화 정책의 안전망.
"""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "extract_review_verdict.py"


def _run(stdin_text: str) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_text, capture_output=True, text=True,
    )
    return r.returncode, r.stdout.strip()


@pytest.mark.review
class TestExtractReviewVerdict:
    def test_raw_json_pass(self):
        code, out = _run('{"verdict":"pass","ac_check":[]}')
        assert (code, out) == (0, "pass")

    def test_markdown_leak_pass(self):
        # 본 세션 5/5 leak 패턴
        text = '## 리뷰 결과\nverdict: pass\n\n{"verdict":"pass",...}'
        code, out = _run(text)
        assert (code, out) == (0, "pass")

    def test_codeblock_warn(self):
        text = '```json\n{"verdict": "warn", "warnings": ["..."]}\n```'
        code, out = _run(text)
        assert (code, out) == (0, "warn")

    def test_prose_block(self):
        text = "분석 결과: 이 변경은 block 처리해야 합니다."
        code, out = _run(text)
        assert (code, out) == (0, "block")

    def test_no_verdict_word(self):
        code, out = _run("Looks good to me!")
        assert code == 1

    def test_first_match_wins(self):
        # 본문에 단어가 먼저 나오면 그것 — review가 결론을 앞에 적도록 유도
        text = "verdict: warn\n\n{...}"
        code, out = _run(text)
        assert (code, out) == (0, "warn")
