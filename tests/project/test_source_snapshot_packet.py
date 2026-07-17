from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[2]
    / ".harness/project/scripts/runtime/source_snapshot_packet.py"
)
SPEC = importlib.util.spec_from_file_location("source_snapshot_packet", MODULE_PATH)
assert SPEC and SPEC.loader
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Snapshot Test")
    git(tmp_path, "config", "user.email", "snapshot@example.test")
    write(tmp_path / "scope/staged.txt", "staged old\n")
    write(tmp_path / "scope/unstaged.txt", "unstaged old\n")
    write(tmp_path / "scope/deleted.txt", "deleted old\n")
    write(tmp_path / "other/dirty.txt", "other old\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def dirty_scope(repo: Path) -> None:
    write(repo / "scope/staged.txt", "staged new\n")
    git(repo, "add", "scope/staged.txt")
    write(repo / "scope/unstaged.txt", "unstaged new\n")
    write(repo / "scope/untracked.txt", "untracked new\n")
    (repo / "scope/deleted.txt").unlink()


def entry_map(packet: dict) -> dict[str, dict]:
    return {entry["path"]: entry for entry in packet["entries"]}


def decoded(entry: dict, capture: str) -> bytes:
    return base64.b64decode(entry["captures"][capture]["base64"])


def test_captures_all_scoped_dirty_kinds_and_canonical_hashes(repo: Path) -> None:
    dirty_scope(repo)

    packet = snapshot.produce_snapshot_packet(repo, ["scope"])
    entries = entry_map(packet)

    assert set(entries) == {
        "scope/deleted.txt",
        "scope/staged.txt",
        "scope/unstaged.txt",
        "scope/untracked.txt",
    }
    assert entries["scope/staged.txt"]["states"] == ["staged"]
    assert entries["scope/unstaged.txt"]["states"] == ["unstaged"]
    assert entries["scope/untracked.txt"]["states"] == ["untracked"]
    assert entries["scope/deleted.txt"]["states"] == ["deleted"]
    assert decoded(entries["scope/staged.txt"], "staged") == b"staged new\n"
    assert decoded(entries["scope/unstaged.txt"], "unstaged") == b"unstaged new\n"
    assert decoded(entries["scope/untracked.txt"], "untracked") == b"untracked new\n"
    assert decoded(entries["scope/deleted.txt"], "deleted_from_index") == b"deleted old\n"
    for path, entry in entries.items():
        assert entry["path_sha256"] == hashlib.sha256(path.encode()).hexdigest()
    body = {key: value for key, value in packet.items() if key != "packet_sha256"}
    assert packet["packet_sha256"] == hashlib.sha256(
        snapshot.canonical_json(body).encode()
    ).hexdigest()


def test_excludes_unrelated_dirty_paths_and_preserves_repo(repo: Path) -> None:
    dirty_scope(repo)
    write(repo / "other/dirty.txt", "other new\n")
    write(repo / "other/untracked.txt", "outside\n")
    before_status = git(repo, "status", "--porcelain=v1", "-uall")
    before_index = (repo / ".git/index").read_bytes()

    packet = snapshot.produce_snapshot_packet(repo, ["scope"])

    serialized = snapshot.canonical_json(packet)
    assert "other/" not in serialized
    assert git(repo, "status", "--porcelain=v1", "-uall") == before_status
    assert (repo / ".git/index").read_bytes() == before_index


def test_rejects_invalid_repo_and_scope(repo: Path, tmp_path: Path) -> None:
    nested = repo / "scope"
    with pytest.raises(snapshot.SnapshotError, match="repository root"):
        snapshot.produce_snapshot_packet(nested, ["staged.txt"])
    with pytest.raises(snapshot.SnapshotError, match="normalized"):
        snapshot.produce_snapshot_packet(repo, ["../outside"])
    with pytest.raises(snapshot.SnapshotError, match="does not match"):
        snapshot.produce_snapshot_packet(repo, ["missing"])
    with pytest.raises(snapshot.SnapshotError, match="scope"):
        snapshot.produce_snapshot_packet(repo, [])


def test_rejects_clean_scoped_state(repo: Path) -> None:
    with pytest.raises(snapshot.SnapshotError, match="clean"):
        snapshot.produce_snapshot_packet(repo, ["scope"])


def test_rejects_scoped_mutation_during_capture(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirty_scope(repo)
    original = snapshot._capture_scoped_state
    calls = 0

    def capture(repo_path: Path, scopes: tuple[str, ...]) -> dict:
        nonlocal calls
        result = original(repo_path, scopes)
        calls += 1
        if calls == 1:
            write(repo / "scope/unstaged.txt", "mutated during capture\n")
        return result

    monkeypatch.setattr(snapshot, "_capture_scoped_state", capture)
    with pytest.raises(snapshot.SnapshotError, match="changed during capture"):
        snapshot.produce_snapshot_packet(repo, ["scope"])


def test_tolerates_unrelated_mutation_during_capture(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirty_scope(repo)
    original = snapshot._capture_scoped_state
    calls = 0

    def capture(repo_path: Path, scopes: tuple[str, ...]) -> dict:
        nonlocal calls
        result = original(repo_path, scopes)
        calls += 1
        if calls == 1:
            write(repo / "other/dirty.txt", "mutated outside scope\n")
        return result

    monkeypatch.setattr(snapshot, "_capture_scoped_state", capture)
    packet = snapshot.produce_snapshot_packet(repo, ["scope"])
    assert "other/" not in snapshot.canonical_json(packet)


def test_output_is_stable_and_cli_emits_canonical_json(repo: Path) -> None:
    dirty_scope(repo)
    first = snapshot.produce_snapshot_packet(repo, ["scope"])
    second = snapshot.produce_snapshot_packet(repo, ["scope"])
    assert first == second

    completed = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--repo",
            str(repo),
            "--scope",
            "scope",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stdout == snapshot.canonical_json(first) + "\n"
    assert json.loads(completed.stdout) == first
