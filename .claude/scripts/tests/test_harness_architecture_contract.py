"""Harness-first architecture contract tests.

These tests keep the Hermes/Harness split executable instead of only documented.
"""

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent.parent
DOCS_OPS = REPO_ROOT / ".claude" / "scripts" / "docs_ops.py"


def load_docs_ops():
    spec = importlib.util.spec_from_file_location("docs_ops", DOCS_OPS)
    assert spec is not None
    docs_ops = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(docs_ops)
    return docs_ops


@pytest.mark.harness_architecture
def test_harness_architecture_files_exist():
    """Harness core tracking and worker/feedback contracts are actual files."""
    required = [
        ".harness/upstream.lock",
        ".harness/schemas/workers.schema.yaml",
        ".harness/schemas/feedback.schema.yaml",
        ".harness/hermes/workers.yaml",
        ".harness/project/overlay.yaml",
        "docs/harness/hn_harness_core_overlay_binding.md",
    ]
    missing = [path for path in required if not (REPO_ROOT / path).exists()]
    assert missing == []


@pytest.mark.harness_architecture
def test_harness_architecture_manifest_validation_passes():
    """docs_ops validate-harness-architecture accepts the checked-in contracts."""
    assert load_docs_ops().cmd_validate_harness_architecture() == 0


@pytest.mark.harness_architecture
def test_harness_architecture_rejects_provider_specific_role_contract(tmp_path, monkeypatch):
    """Role contracts must stay engine-class based; provider/model names belong in local binding."""
    root = tmp_path
    (root / ".harness/schemas").mkdir(parents=True)
    (root / ".harness/hermes").mkdir(parents=True)
    (root / ".harness/project").mkdir(parents=True)
    (root / ".harness/upstream.lock").write_text(
        "version: 1\nschema: harness-upstream-lock\nupstream:\n  repo: example\n  ref: abc\nlayout:\n  core_path: .claude\n  overlay_path: .harness/project\n  hermes_binding_path: .harness/hermes\npolicy:\n  core_direct_edit: report-upstream-candidate\n  apply_mode: owner-approved\n",
        encoding="utf-8",
    )
    (root / ".harness/project/overlay.yaml").write_text(
        "version: 1\nschema: harness-project-overlay\nproject:\n  slug: sample\nconstraints: {}\n",
        encoding="utf-8",
    )
    (root / ".harness/schemas/workers.schema.yaml").write_text("schema: workers\n", encoding="utf-8")
    (root / ".harness/schemas/feedback.schema.yaml").write_text("schema: feedback\n", encoding="utf-8")
    (root / ".harness/hermes/workers.yaml").write_text(
        "version: 1\nschema: harness-hermes-workers\nroles:\n  - name: coder\n    preferred_engine_class: Codex gpt-5.5\n    write_permission: scoped-write\n    timeout: 30m\n    concurrency: 1\n    accepts: [implementation]\n    refuses: [secrets]\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(root)
    assert load_docs_ops().cmd_validate_harness_architecture() == 1
