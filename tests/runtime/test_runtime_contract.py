import json
import os
import sys
from pathlib import Path

import pytest

from harness_runtime import ReceiptValidationError, execute, readback, schema_text
from harness_runtime.binding_registry import (
    BindingRecord,
    BindingRequest,
    BindingResolutionError,
    BindingResult,
    CanonicalBindingRegistry,
    binding_schema_text,
)


def test_schema_is_versioned_and_artifact_only():
    schema = json.loads(schema_text())
    assert schema["$id"].endswith("execution-receipt.v1.schema.json")
    assert schema["properties"]["schema"]["const"] == "harness.runtime.execution-receipt.v1"


def test_invalid_case_is_a_validation_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    with pytest.raises(ReceiptValidationError, match="case_id"):
        execute("../unit-case", "unit-consumer", b"body", [sys.executable, "-c", "pass"])


def test_lifecycle_producer_receipt_to_consumer_readback(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    result = execute(
        "lifecycle-case",
        "test-consumer",
        b"producer-body",
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
    )
    assert result["status"] == "pass"
    receipt = readback("lifecycle-case", expected_consumer="test-consumer")
    assert receipt["receipt"]["status"] == "pass"
    assert receipt["artifacts"]["stdout"]["sha256"] == receipt["artifacts"]["body"]["sha256"]
    assert Path(receipt["receipt_path"]).is_relative_to(tmp_path / "isolated-state")
    assert not Path(".harness/project/runs").joinpath("runtime-test-marker").exists()


def _binding_registry(tmp_path: Path) -> tuple[CanonicalBindingRegistry, BindingRequest, BindingResult]:
    request = BindingRequest(
        platform="discord",
        guild_id="guild-1",
        parent_channel_id="channel-1",
        thread_id="thread-1",
        profile="ptah",
    )
    result = BindingResult(
        project_slug="harness-starter",
        canonical_cwd=str(tmp_path / "canonical-project"),
        write_scope="runtime",
        binding_revision="binding-r1",
        source_ref="fixture:canonical-binding-r1",
    )
    return CanonicalBindingRegistry([BindingRecord(request, result)], resolver_revision="resolver-r1"), request, result


def test_canonical_binding_contract_resolves_and_round_trips_temporary_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    registry, request, expected = _binding_registry(tmp_path)
    schema = json.loads(binding_schema_text())
    assert schema["$id"].endswith("canonical-binding.v1.schema.json")

    resolved = registry.resolve(request)
    assert resolved.result == expected.normalized()
    assert resolved.receipt.binding_digest == registry.resolve(request).receipt.binding_digest
    receipt_path = registry.persist_receipt(resolved)
    readback = registry.readback(request, resolved.receipt.session_key, resolved.receipt.binding_digest)

    assert Path(receipt_path).is_relative_to(tmp_path / "isolated-state")
    assert readback.result == expected.normalized()
    assert readback.receipt.consumer_readback == request.identity()
    assert readback.receipt.binding_digest == resolved.receipt.binding_digest


def test_canonical_binding_rejects_unknown_ambiguous_and_invalid_without_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    registry, request, expected = _binding_registry(tmp_path)
    unknown = BindingRequest("discord", "guild-1", "channel-1", "unknown-thread", "ptah")
    duplicate = CanonicalBindingRegistry(
        [BindingRecord(request, expected), BindingRecord(request, expected)], resolver_revision="resolver-r1"
    )

    with pytest.raises(BindingResolutionError, match="unknown"):
        registry.resolve(unknown)
    with pytest.raises(BindingResolutionError, match="ambiguous"):
        duplicate.resolve(request)
    with pytest.raises(BindingResolutionError, match="identity"):
        registry.resolve(BindingRequest("discord", "guild-1", "channel-1", "../thread", "ptah"))
    with pytest.raises(BindingResolutionError, match="project_slug"):
        CanonicalBindingRegistry(
            [BindingRecord(request, BindingResult("../unsafe", str(tmp_path / "canonical-project"), "runtime", "binding-r1", "fixture:unsafe"))],
            resolver_revision="resolver-r1",
        )
    with pytest.raises(BindingResolutionError, match="canonical_cwd"):
        CanonicalBindingRegistry(
            [BindingRecord(request, BindingResult("safe-project", "relative/path", "runtime", "binding-r1", "fixture:relative"))],
            resolver_revision="resolver-r1",
        )
