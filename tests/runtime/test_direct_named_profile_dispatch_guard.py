from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
DISPATCHER = REPO / ".harness" / "hermes" / "tools" / "external_runtime_dispatcher.py"


@pytest.fixture(scope="module")
def dispatcher():
    spec = importlib.util.spec_from_file_location("direct_named_profile_dispatch_guard", DISPATCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identity(body: bytes) -> dict[str, object]:
    return {
        "work_id": "guard-work",
        "graph_ref": "graph:guard",
        "graph_revision": 1,
        "graph_digest": "a" * 64,
        "stage_ref": "S:guard",
        "owner_ref": "ptah",
        "parent_edge_ref": "C/P",
        "return_to_node_ref": "C",
        "run_handle": "guard-run",
        "attempt": 1,
        "immutable_body_digest": hashlib.sha256(body).hexdigest(),
    }


def test_legacy_dispatch_cannot_create_a_named_profile_process_or_receipt(dispatcher, tmp_path):
    body = b"legacy direct dispatch must be blocked"
    launched = False

    def launch(_argv):
        nonlocal launched
        launched = True
        return 1

    with pytest.raises(dispatcher.DirectNamedProfileDispatchDisabled, match="canonical bound Harness ingress"):
        dispatcher.dispatch_external_runtime(
            "ptah", body, tmp_path, identity=_identity(body), process_runner=launch,
        )

    assert launched is False
    assert list(tmp_path.iterdir()) == []


def test_legacy_runner_is_blocked_before_it_reads_or_launches_a_job(dispatcher, tmp_path):
    with pytest.raises(dispatcher.DirectNamedProfileDispatchDisabled, match="canonical bound Harness ingress"):
        dispatcher.run_job(tmp_path / "missing" / "current.json")
