from pathlib import Path


MAAT_DOC = Path(__file__).resolve().parents[2] / "docs/harness/agents/maat.md"


def test_maat_allows_adjudication_before_working_graph_materialization() -> None:
    text = MAAT_DOC.read_text(encoding="utf-8")
    policy = text.split("## Working-graph bootstrap policy", maxsplit=1)[1].split(
        "\n## ", maxsplit=1
    )[0]

    assert "pre-existing `graph_ref@revision` is not a prerequisite" in policy
    assert "C1, retain/split decision, or bounded capability observation" in policy
    assert "valid project binding and bounded user scope" in policy
    assert "first decides C/P/S/AC/owner/order" in policy
    assert "`base_graph_ref: null`" in policy
    assert "after the semantic route decision" in policy
    assert "creates the current working-graph revision" in policy
    assert "before executor-local projection and semantic-checkpoint closure" in policy
    assert "not as an ingress input" in policy
    assert "concrete source/evidence absence actually needed for adjudication" in policy
    assert "an uncreated graph alone is not a HOLD reason" in policy
