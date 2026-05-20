"""스킬 라우팅/문서-도구 계약 회귀 가드.

느슨하게 결합된 스킬 문서와 docs_ops.py 요구사항이 서로 다른 SSOT를 말하면
다운스트림에서 계획 문서·WIP 이동이 뒤늦게 실패한다.
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.routing
def test_plan_doc_before_code_routes_to_implementation_not_write_doc():
    """코드·테스트 개선을 앞둔 계획 문서는 implementation 계약으로 고정한다."""
    implementation = _read(".claude/skills/implementation/SKILL.md")
    write_doc = _read(".claude/skills/write-doc/SKILL.md")

    assert "코드·테스트·스크립트·룰 감사/개선을 위한 계획 문서" in implementation
    assert "먼저 계획 문서부터" in implementation
    assert "write-doc은 문서 자체가 최종 산출물" in implementation

    assert "코드 구현·감사·리팩토링·테스트 보강을 앞둔 계획 문서" in write_doc
    assert "write-doc이 아니라 implementation" in write_doc
    assert "문서 자체가 완료" in write_doc


@pytest.mark.routing
def test_wip_filename_contract_matches_docs_ops_move_prefix_requirement():
    """docs_ops.py move가 요구하는 WIP routing prefix를 스킬 문서가 반대로 안내하지 않는다."""
    docs_ops = _read(".claude/scripts/docs_ops.py")
    naming = _read(".claude/rules/naming.md")
    implementation = _read(".claude/skills/implementation/SKILL.md")
    write_doc = _read(".claude/skills/write-doc/SKILL.md")
    commit = _read(".claude/skills/commit/SKILL.md")

    assert "접두사 없음 (decisions--/guides--/cps--/... 필요)" in docs_ops
    assert "{대상폴더}--{abbr}_{slug}.md" in naming

    for text in (implementation, write_doc, commit):
        assert "{대상폴더}--{abbr}_{slug}.md" in text
        assert "라우팅 태그 폐기" not in text
