from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
import harness_runtime.ingress as ingress
from harness_runtime.ingress import (
    EventRef,
    ExecutionReceipts,
    IngressIntake,
    ProjectRef,
    canonical_packet_json,
    process_bound_ingress,
)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def project(path: Path, manifest: str | None = "schema: harness.project.v1\n") -> Path:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    if manifest is not None:
        (path / "manifest.yml").write_text(manifest, encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "--allow-empty", "-m", "fixture")
    return path.resolve()


def event(event_id: str, *, bound: bool = True, parent_event_id: str | None = None) -> EventRef:
    return EventRef(
        event_id=event_id,
        payload_hash=hashlib.sha256(event_id.encode()).hexdigest(),
        channel_id="discord-project" if bound else "general",
        bound=bound,
        parent_event_id=parent_event_id,
    )


def test_pure_intake_returns_ready_with_required_evidence(tmp_path):
    root = project(tmp_path / "project")
    result = IngressIntake().evaluate(event("parent"), ProjectRef.bind_cwd(root))

    assert result.status == "READY"
    assert result.manifest_ref == str(root / "manifest.yml")
    assert result.manifest_hash == hashlib.sha256((root / "manifest.yml").read_bytes()).hexdigest()
    assert result.binding_evidence["root"] == str(root)
    assert result.binding_evidence["manifest_entry"] == str(root / "manifest.yml")
    assert result.binding_evidence["environment_valid"] is True
    assert result.binding_evidence["boundary_valid"] is True
    assert result.baseline_worktree_state == {"head": _git(root, "rev-parse", "HEAD"), "dirty": False, "changes": ()}
    assert result.cps_receipt_id.startswith("cps-parent-")


def test_absent_manifest_without_bootstrap_flag_holds(tmp_path):
    root = project(tmp_path / "project", manifest=None)

    result = IngressIntake().evaluate(event("absent-closed"), ProjectRef.bind_cwd(root))

    assert result.status == "HOLD"
    assert not (root / "manifest.yml").exists()


def test_absent_manifest_with_bootstrap_flag_creates_exact_valid_manifest(tmp_path):
    root = project(tmp_path / "project", manifest=None)

    result = IngressIntake().evaluate(
        event("absent-open"),
        ProjectRef.bind_cwd(root, allow_bootstrap_manifest=True),
    )

    manifest = root / "manifest.yml"
    assert result.status == "READY"
    assert manifest.read_bytes() == b"schema: harness.project.v1\n"
    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
    assert result.binding_evidence["manifest_created"] is True


def test_bootstrap_flag_never_overwrites_preexisting_manifest(tmp_path):
    root = project(tmp_path / "project", manifest="existing: immutable\n")

    result = IngressIntake().evaluate(
        event("existing"),
        ProjectRef.bind_cwd(root, allow_bootstrap_manifest=True),
    )

    assert result.status == "READY"
    assert (root / "manifest.yml").read_bytes() == b"existing: immutable\n"
    assert result.binding_evidence["manifest_created"] is False


def test_non_enoent_manifest_read_error_holds_without_overwrite(tmp_path, monkeypatch):
    root = project(tmp_path / "project", manifest="existing: immutable\n")
    manifest = root / "manifest.yml"
    original_read_bytes = Path.read_bytes

    def denied(path):
        if path == manifest:
            raise PermissionError("denied")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    result = IngressIntake().evaluate(
        event("denied"),
        ProjectRef.bind_cwd(root, allow_bootstrap_manifest=True),
    )

    assert result.status == "HOLD"
    with manifest.open("rb") as stream:
        assert stream.read() == b"existing: immutable\n"


def test_symlink_manifest_holds_without_creating_target(tmp_path):
    root = project(tmp_path / "project", manifest=None)
    target = tmp_path / "outside-manifest.yml"
    (root / "manifest.yml").symlink_to(target)

    result = IngressIntake().evaluate(
        event("symlink"),
        ProjectRef.bind_cwd(root, allow_bootstrap_manifest=True),
    )

    assert result.status == "HOLD"
    assert not target.exists()


def test_bootstrap_race_revalidates_winner_without_overwrite(tmp_path, monkeypatch):
    root = project(tmp_path / "project", manifest=None)
    manifest = root / "manifest.yml"
    race_body = b"race: winner\n"
    original_open = ingress.os.open

    def race_open(path, flags, mode=0o777):
        if Path(path) == manifest and flags & os.O_EXCL:
            manifest.write_bytes(race_body)
            raise FileExistsError(path)
        return original_open(path, flags, mode)

    monkeypatch.setattr(ingress.os, "open", race_open)
    result = IngressIntake().evaluate(
        event("race"),
        ProjectRef.bind_cwd(root, allow_bootstrap_manifest=True),
    )

    assert result.status == "READY"
    assert manifest.read_bytes() == race_body
    assert result.binding_evidence["manifest_created"] is False


def test_manifest_cache_key_and_hash_invalidation(tmp_path, monkeypatch):
    root = project(tmp_path / "project")
    intake = IngressIntake()
    calls = 0
    original = intake._validate_binding

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(intake, "_validate_binding", counted)
    ref = ProjectRef.bind_cwd(root)
    first = intake.evaluate(event("one"), ref)
    manifest = root / "manifest.yml"
    manifest.touch()
    second = intake.evaluate(event("two"), ref)

    assert calls == 1
    assert first.cache_key[0] == str(root)
    assert first.cache_key[2] == first.manifest_hash
    assert second.cache_key[1] == manifest.stat().st_mtime_ns

    manifest.write_text("schema: harness.project.v2\n", encoding="utf-8")
    third = intake.evaluate(event("three"), ref)
    assert calls == 2
    assert third.manifest_hash != first.manifest_hash


def test_dirty_worktree_is_baseline_evidence_not_hold(tmp_path):
    root = project(tmp_path / "project")
    (root / "dirty.txt").write_text("baseline\n", encoding="utf-8")

    result = IngressIntake().evaluate(event("dirty"), ProjectRef.bind_cwd(root))

    assert result.status == "READY"
    assert result.baseline_worktree_state["dirty"] is True
    assert result.baseline_worktree_state["changes"] == ("?? dirty.txt",)


def test_bound_event_absent_ready_terminalizes_hold_receipt(tmp_path):
    root = project(tmp_path / "project", manifest="")
    receipt_dir = tmp_path / "receipts"

    result = process_bound_ingress(
        event("held"),
        ProjectRef.bind_cwd(root),
        intent="held intent",
        receipt_dir=receipt_dir,
    )

    assert result["status"] == "HOLD"
    receipt = ExecutionReceipts(receipt_dir).read(result["cps_receipt_id"])
    assert [entry["stage"] for entry in receipt["entries"]] == [
        "received", "intake-hold", "terminal"
    ]


def test_ready_creates_one_canonical_packet_without_terminalizing(tmp_path):
    root = project(tmp_path / "project")
    receipt_dir = tmp_path / "receipts"

    result = process_bound_ingress(
        event("integrated"),
        ProjectRef.bind_cwd(root),
        intent="structured intent",
        receipt_dir=receipt_dir,
    )
    receipt = ExecutionReceipts(receipt_dir).read(result["cps_receipt_id"], require_terminal=False)

    assert result["status"] == "READY"
    assert "compact_C" not in result
    packet_json = result["canonical_packet"]
    assert packet_json == canonical_packet_json(result["packet"])
    assert packet_json.encode("ascii") == json.dumps(
        json.loads(packet_json), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    packet = json.loads(packet_json)
    assert packet["schema"] == "harness.gateway.ingress-packet.v1"
    assert packet["event_ref"]["event_id"] == "integrated"
    assert packet["project_ref"] == {
        "manifest": str(root / "manifest.yml"),
        "root": str(root),
    }
    assert packet["manifest_ref"] == str(root / "manifest.yml")
    assert packet["manifest_hash"] == hashlib.sha256((root / "manifest.yml").read_bytes()).hexdigest()
    assert packet["binding_evidence"]["root"] == str(root)
    assert packet["baseline_worktree_state"]["dirty"] is False
    assert packet["cps_receipt_id"] == result["cps_receipt_id"]
    assert [entry["stage"] for entry in receipt["entries"]] == [
        "received", "intake-ready"
    ]


def test_ready_does_not_invoke_an_agent_or_create_compact_c(tmp_path):
    root = project(tmp_path / "project")
    receipt_dir = tmp_path / "receipts"
    result = process_bound_ingress(
        event("dispatched"),
        ProjectRef.bind_cwd(root),
        intent="structured intent",
        receipt_dir=receipt_dir,
    )

    assert result["packet"].intent == "structured intent"
    assert "compact_C" not in result


def test_duplicate_receipt_is_rejected_without_overwriting_lifecycle(tmp_path):
    root = project(tmp_path / "project")
    receipt_dir = tmp_path / "receipts"

    first = process_bound_ingress(
        event("replay"), ProjectRef.bind_cwd(root), intent="intent", receipt_dir=receipt_dir
    )

    with pytest.raises(ValueError, match="already exists"):
        process_bound_ingress(
            event("replay"), ProjectRef.bind_cwd(root), intent="intent", receipt_dir=receipt_dir
        )

    receipt = ExecutionReceipts(receipt_dir).read(first["cps_receipt_id"], require_terminal=False)
    assert [entry["stage"] for entry in receipt["entries"]] == ["received", "intake-ready"]
