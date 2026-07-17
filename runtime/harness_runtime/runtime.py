from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Sequence

SCHEMA_NAME = "harness.runtime.execution-receipt.v1"
_CASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": os.defpath, "TZ": "UTC"}


class ReceiptValidationError(ValueError):
    """The isolated runtime input or persisted receipt is invalid."""


def schema_text() -> str:
    return resources.files("contracts").joinpath("execution-receipt.v1.schema.json").read_text(encoding="utf-8")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _state_root() -> Path:
    override = os.environ.get("HARNESS_STATE_DIR")
    if not override:
        raise ReceiptValidationError("HARNESS_STATE_DIR is required; implicit or live state is forbidden")
    return Path(override).expanduser().resolve()


def _case_dir(case_id: str) -> Path:
    if not isinstance(case_id, str) or not _CASE_RE.fullmatch(case_id):
        raise ReceiptValidationError("case_id must be 1-128 safe filename characters")
    return _state_root() / "receipts" / _sha256(case_id.encode("utf-8"))


def _artifact(path: Path, case_dir: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {"ref": path.relative_to(case_dir).as_posix(), "sha256": _sha256(content), "bytes": len(content)}


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _append(case_dir: Path, receipt: dict[str, Any]) -> None:
    receipt_path = case_dir / "receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("a", encoding="utf-8") as output:
        output.write(_canonical_bytes(receipt).decode("ascii") + "\n")
        output.flush()
        os.fsync(output.fileno())
    projection = case_dir / "current.json"
    temporary = projection.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(projection)


def _receipt(
    sequence: int,
    event: str,
    status: str,
    case_id: str,
    consumer: str,
    artifacts: dict[str, Any],
    exit_code: int | None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "sequence": sequence,
        "event": event,
        "status": status,
        "case_id": case_id,
        "consumer": consumer,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "artifacts": artifacts,
    }
    if execution is not None:
        receipt["execution"] = execution
    return receipt


def _git(worktree: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_EXECUTION_ENVIRONMENT,
    )
    if completed.returncode != 0:
        raise ReceiptValidationError("worktree_cwd must be a Git worktree with a committed HEAD")
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _worktree(path: str | Path) -> tuple[Path, str, str]:
    worktree = Path(path).expanduser().resolve()
    if not worktree.is_dir():
        raise ReceiptValidationError("worktree_cwd must be an existing directory")
    root = Path(_git(worktree, "rev-parse", "--show-toplevel")).resolve()
    if root != worktree:
        raise ReceiptValidationError("worktree_cwd must be the Git worktree root")
    commit = _git(worktree, "rev-parse", "HEAD")
    tree = _git(worktree, "rev-parse", "HEAD^{tree}")
    if _git(worktree, "status", "--porcelain", "--untracked-files=all"):
        raise ReceiptValidationError("worktree_cwd must be clean")
    return worktree, commit, tree


def _execution(argv: list[str], worktree: Path, commit: str, tree: str, environment: dict[str, str]) -> dict[str, Any]:
    return {
        "argv": argv,
        "argv_sha256": _sha256(_canonical_bytes(argv)),
        "environment": environment,
        "environment_sha256": _sha256(_canonical_bytes(environment)),
        "git_commit": commit,
        "git_tree": tree,
        "worktree_cwd": str(worktree),
        "worktree_cwd_sha256": _sha256(str(worktree).encode("utf-8")),
    }


def execute(
    case_id: str,
    consumer: str,
    body: bytes,
    command: Sequence[str],
    *,
    worktree_cwd: str | Path | None = None,
) -> dict[str, Any]:
    """Run one command in an explicit clean worktree and persist a verifiable receipt."""
    if not isinstance(consumer, str) or not consumer:
        raise ReceiptValidationError("consumer is required")
    if not isinstance(body, bytes):
        raise ReceiptValidationError("body must be bytes")
    argv = list(command)
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ReceiptValidationError("command must contain non-empty strings")
    if worktree_cwd is None:
        raise ReceiptValidationError("worktree_cwd is required; implicit caller cwd is forbidden")
    worktree, commit, tree = _worktree(worktree_cwd)
    state_root = _state_root()
    if state_root == worktree or worktree in state_root.parents:
        raise ReceiptValidationError("HARNESS_STATE_DIR must be outside worktree_cwd")
    case_dir = _case_dir(case_id)
    if (case_dir / "current.json").exists():
        raise ReceiptValidationError("case_id already has a receipt; choose a new isolated case")

    artifacts_dir = case_dir / "artifacts"
    artifact_paths = {name: artifacts_dir / f"{name}.bin" for name in ("body", "stdout", "stderr")}
    _write(artifact_paths["body"], body)
    _write(artifact_paths["stdout"], b"")
    _write(artifact_paths["stderr"], b"")
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    _append(case_dir, _receipt(1, "dispatch", "observed", case_id, consumer, artifacts, None))

    environment = {**_EXECUTION_ENVIRONMENT, "HARNESS_STATE_DIR": str(state_root)}
    execution = _execution(argv, worktree, commit, tree, environment)
    try:
        completed = subprocess.run(
            argv,
            input=body,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd=worktree,
            env=environment,
        )
        exit_code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except OSError as exc:
        exit_code, stdout, stderr = 127, b"", f"runner error: {exc.__class__.__name__}\n".encode("ascii")
    _write(artifact_paths["stdout"], stdout)
    _write(artifact_paths["stderr"], stderr)
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    terminal = _receipt(2, "terminal", "pass" if exit_code == 0 else "fail", case_id, consumer, artifacts, exit_code, execution)
    _append(case_dir, terminal)
    verified, _ = _readback(case_id, consumer)
    return verified["receipt"]


def _validate_execution(execution: object) -> None:
    if not isinstance(execution, dict):
        raise ReceiptValidationError("execution metadata is required for consumer readback")
    argv = execution.get("argv")
    environment = execution.get("environment")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ReceiptValidationError("receipt argv is invalid")
    if execution.get("argv_sha256") != _sha256(_canonical_bytes(argv)):
        raise ReceiptValidationError("receipt argv digest does not match")
    if not isinstance(environment, dict) or environment != {**_EXECUTION_ENVIRONMENT, "HARNESS_STATE_DIR": environment.get("HARNESS_STATE_DIR")}:
        raise ReceiptValidationError("receipt environment is not constrained")
    if not isinstance(environment.get("HARNESS_STATE_DIR"), str):
        raise ReceiptValidationError("receipt environment is not constrained")
    if execution.get("environment_sha256") != _sha256(_canonical_bytes(environment)):
        raise ReceiptValidationError("receipt environment digest does not match")
    worktree_cwd = execution.get("worktree_cwd")
    if not isinstance(worktree_cwd, str) or execution.get("worktree_cwd_sha256") != _sha256(worktree_cwd.encode("utf-8")):
        raise ReceiptValidationError("receipt worktree cwd digest does not match")
    if not all(isinstance(execution.get(name), str) and re.fullmatch(r"[0-9a-f]{40,64}", execution[name]) for name in ("git_commit", "git_tree")):
        raise ReceiptValidationError("receipt Git identity is invalid")


def _verified_artifacts(case_dir: Path, artifacts: object) -> dict[str, bytes]:
    if not isinstance(artifacts, dict) or set(artifacts) != {"body", "stdout", "stderr"}:
        raise ReceiptValidationError("receipt artifacts are invalid")
    contents: dict[str, bytes] = {}
    for name in ("body", "stdout", "stderr"):
        item = artifacts[name]
        if not isinstance(item, dict) or set(item) != {"ref", "sha256", "bytes"} or not isinstance(item.get("ref"), str):
            raise ReceiptValidationError("receipt artifacts are invalid")
        artifact_path = (case_dir / item["ref"]).resolve()
        if case_dir not in artifact_path.parents:
            raise ReceiptValidationError("artifact escapes isolated state")
        try:
            content = artifact_path.read_bytes()
        except OSError as exc:
            raise ReceiptValidationError("artifact readback is unavailable") from exc
        if item.get("sha256") != _sha256(content) or item.get("bytes") != len(content):
            raise ReceiptValidationError("artifact readback does not match receipt")
        contents[name] = content
    return contents


def _readback(case_id: str, expected_consumer: str | None) -> tuple[dict[str, Any], dict[str, bytes]]:
    case_dir = _case_dir(case_id)
    path = case_dir / "current.json"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        journal = [json.loads(line) for line in (case_dir / "receipts.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError("receipt readback is unavailable") from exc
    if len(journal) != 2 or journal[-1] != receipt:
        raise ReceiptValidationError("receipt journal does not match terminal projection")
    dispatch = journal[0]
    if (
        dispatch.get("schema") != SCHEMA_NAME
        or dispatch.get("sequence") != 1
        or dispatch.get("event") != "dispatch"
        or dispatch.get("status") != "observed"
        or dispatch.get("case_id") != case_id
        or dispatch.get("consumer") != receipt.get("consumer")
        or dispatch.get("exit_code") is not None
        or "execution" in dispatch
    ):
        raise ReceiptValidationError("dispatch receipt is invalid")
    required = {"schema", "sequence", "event", "status", "case_id", "consumer", "recorded_at", "exit_code", "artifacts", "execution"}
    if set(receipt) != required or receipt.get("schema") != SCHEMA_NAME or receipt.get("sequence") != 2 or receipt.get("event") != "terminal":
        raise ReceiptValidationError("terminal receipt is invalid")
    if (
        receipt.get("case_id") != case_id
        or receipt.get("status") not in {"pass", "fail"}
        or not isinstance(receipt.get("exit_code"), int)
        or (receipt["status"] == "pass") != (receipt["exit_code"] == 0)
    ):
        raise ReceiptValidationError("terminal receipt is invalid")
    if expected_consumer is not None and receipt.get("consumer") != expected_consumer:
        raise ReceiptValidationError("consumer does not match receipt")
    _validate_execution(receipt["execution"])
    contents = _verified_artifacts(case_dir, receipt["artifacts"])
    result = {
        "analysis_basis": SCHEMA_NAME,
        "consumer": receipt["consumer"],
        "receipt": receipt,
        "artifacts": receipt["artifacts"],
        "receipt_path": str(path),
    }
    return result, contents


def readback(case_id: str, expected_consumer: str | None = None) -> dict[str, Any]:
    result, _ = _readback(case_id, expected_consumer)
    return result


def analysis_input(case_id: str, expected_consumer: str | None = "anubis", output_limit: int = 16384) -> dict[str, Any]:
    """Return a verified receipt and bounded output for Anubis analysis."""
    if not isinstance(output_limit, int) or isinstance(output_limit, bool) or output_limit < 0:
        raise ReceiptValidationError("output_limit must be a non-negative integer")
    result, contents = _readback(case_id, expected_consumer)
    outputs = {
        name: {
            "text": contents[name][:output_limit].decode("utf-8", errors="replace"),
            "truncated": len(contents[name]) > output_limit,
        }
        for name in ("stdout", "stderr")
    }
    return {**result, "outputs": outputs}
