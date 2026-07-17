#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "harness.operational-driver.packet.v1"
RECEIPT_SCHEMA = "harness.operational-driver.scope-receipt.v1"
TEST_ENVIRONMENT_SCHEMA = "harness.operational-test-environment.v1"
TEST_ENVIRONMENT_PATH = PurePosixPath(".harness/project/config/operational-test-environment.v1.json")
FOCUSED_TEST_TIMEOUT_SECONDS = 300


class DriverError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _read_once(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise DriverError(f"cannot read immutable input: {exc.__class__.__name__}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise DriverError("immutable input is not a regular file")
        with os.fdopen(fd, "rb") as stream:
            return stream.read()
    except OSError as exc:
        raise DriverError(f"cannot read immutable input: {exc.__class__.__name__}") from exc


def consume_receipt(path: Path) -> tuple[dict[str, Any], str]:
    raw = _read_once(path)
    try:
        receipt = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("scope receipt is not valid UTF-8 JSON") from exc
    required = {
        "schema", "task_ref", "revision", "source_root", "files", "focused_test_command",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise DriverError("full scope receipt has unknown or missing fields")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise DriverError("unsupported scope receipt schema")
    if not isinstance(receipt["task_ref"], str) or not receipt["task_ref"]:
        raise DriverError("task_ref must be a non-empty string")
    if not isinstance(receipt["revision"], str) or not receipt["revision"]:
        raise DriverError("revision must be a non-empty string")
    if not isinstance(receipt["source_root"], str) or not Path(receipt["source_root"]).is_absolute():
        raise DriverError("source_root must be absolute")

    command = receipt["focused_test_command"]
    if not isinstance(command, dict) or set(command) != {"args"}:
        raise DriverError("focused_test_command accepts test args only")
    args = command["args"]
    if not isinstance(args, list) or not args or any(not isinstance(item, str) or not item for item in args):
        raise DriverError("focused_test_command args must be a non-empty string list")
    forbidden = {"-m", "python", "python3", "pytest", "py.test", "sh", "bash", "uv"}
    if args[0] in forbidden or Path(args[0]).name in forbidden or "--pyargs" in args:
        raise DriverError("receipt executables and wrappers are forbidden")
    files = receipt["files"]
    if not isinstance(files, list) or not files:
        raise DriverError("files must be a non-empty list")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise DriverError("each file requires only path and sha256")
        relative = item["path"]
        digest = item["sha256"]
        pure = PurePosixPath(relative) if isinstance(relative, str) else PurePosixPath("/")
        if (not relative or pure.is_absolute() or "." in pure.parts or ".." in pure.parts
                or str(pure) != relative or relative in seen):
            raise DriverError("file paths must be unique normalized relative POSIX paths")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise DriverError(f"invalid sha256 for {relative}")
        seen.add(relative)
    return receipt, _sha256(raw)


def load_test_environment(root: Path) -> tuple[dict[str, str], bytes]:
    raw = _read_once(_source_file(root, str(TEST_ENVIRONMENT_PATH)))
    try:
        config = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("test environment config is not valid UTF-8 JSON") from exc
    required = {"schema", "runner_path", "expected_identity", "expected_version"}
    if not isinstance(config, dict) or set(config) != required:
        raise DriverError("test environment config has unknown or missing fields")
    if config["schema"] != TEST_ENVIRONMENT_SCHEMA:
        raise DriverError("unsupported test environment config schema")
    if raw != _canonical_json(config) + b"\n":
        raise DriverError("test environment config is not canonical JSON")
    if config["expected_identity"] != "pytest" or config["expected_version"] != "8.4.2":
        raise DriverError("test environment identity or version is not canonical")
    relative = config["runner_path"]
    pure = PurePosixPath(relative) if isinstance(relative, str) else PurePosixPath("/")
    if not relative or pure.is_absolute() or "." in pure.parts or ".." in pure.parts or str(pure) != relative:
        raise DriverError("runner_path must be a normalized relative POSIX path")
    return config, raw


def verify_runner(root: Path, config: dict[str, str]) -> dict[str, str]:
    runner = _source_file(root, config["runner_path"])
    if not runner.stat().st_mode & 0o111:
        raise DriverError("configured runner is not executable")
    runner_bytes = _read_once(runner)
    identity = config["expected_identity"]
    version = config["expected_version"]
    if runner.name != identity or b"from pytest import console_main" not in runner_bytes:
        raise DriverError("configured runner identity mismatch")
    environment = runner.parent.parent
    metadata_path = environment / "lib" / "python3.11" / "site-packages" / f"{identity}-{version}.dist-info" / "METADATA"
    entry_points_path = metadata_path.with_name("entry_points.txt")
    metadata = BytesParser().parsebytes(_read_once(_source_file(root, str(metadata_path.relative_to(root)))))
    entry_points = _read_once(_source_file(root, str(entry_points_path.relative_to(root))))
    if metadata.get("Name") != identity or metadata.get("Version") != version:
        raise DriverError("configured runner identity or version mismatch")
    if b"pytest = pytest:console_main" not in entry_points:
        raise DriverError("configured runner entry point mismatch")
    return {
        "relative_path": config["runner_path"],
        "absolute_path": str(runner.resolve(strict=True)),
        "sha256": _sha256(runner_bytes),
        "verified_identity": metadata["Name"],
        "verified_version": metadata["Version"],
    }


def _source_file(root: Path, relative: str) -> Path:
    current = root
    root_real = root.resolve(strict=True)
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise DriverError(f"scoped source is unavailable: {relative}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise DriverError(f"symlink is forbidden: {relative}")
    try:
        if not stat.S_ISREG(current.stat().st_mode) or not current.resolve(strict=True).is_relative_to(root_real):
            raise DriverError(f"scoped source is not a contained regular file: {relative}")
    except OSError as exc:
        raise DriverError(f"scoped source is unavailable: {relative}") from exc
    return current


def capture_snapshot(receipt: dict[str, Any], destination: Path) -> dict[str, Any]:
    root = Path(receipt["source_root"])
    try:
        root_info = root.lstat()
        root_real = root.resolve(strict=True)
    except OSError as exc:
        raise DriverError("source_root is unavailable") from exc
    if stat.S_ISLNK(root_info.st_mode) or not root.is_dir() or Path(os.path.abspath(root)) != root_real:
        raise DriverError("source_root must be a real directory")
    destination.mkdir(mode=0o700)
    captured = []
    for item in sorted(receipt["files"], key=lambda entry: entry["path"]):
        data = _read_once(_source_file(root, item["path"]))
        digest = _sha256(data)
        if digest != item["sha256"]:
            raise DriverError(f"source digest mismatch: {item['path']}")
        target = destination.joinpath(*PurePosixPath(item["path"]).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o644)
        captured.append({"path": item["path"], "sha256": digest, "size": len(data)})
    return {"files": captured, "sha256": _sha256(_canonical_json(captured))}


def execute_focused_test(argv: list[str], snapshot: Path) -> dict[str, Any]:
    started_ns = time.monotonic_ns()
    try:
        result = subprocess.run(
            argv,
            cwd=snapshot,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            timeout=FOCUSED_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ns = time.monotonic_ns() - started_ns
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "outcome": "timeout", "argv": argv, "duration_ns": duration_ns,
            "timeout_seconds": FOCUSED_TEST_TIMEOUT_SECONDS, "stdout": stdout, "stderr": stderr,
        }
    return {
        "outcome": "success" if result.returncode == 0 else "failure",
        "argv": argv,
        "duration_ns": time.monotonic_ns() - started_ns,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run(receipt_path: Path) -> dict[str, Any]:
    receipt = None
    receipt_sha256 = None
    task_ref = None
    revision = None
    work = None
    phase = "receipt"
    packet: dict[str, Any]
    cleanup_status = "not_started"
    cleanup_error = None
    try:
        receipt, receipt_sha256 = consume_receipt(receipt_path)
        task_ref = receipt["task_ref"]
        revision = receipt["revision"]
        source_root = Path(receipt["source_root"])
        phase = "test_environment"
        config, config_raw = load_test_environment(source_root)
        runner = verify_runner(source_root, config)
        final_argv = [runner["absolute_path"], *receipt["focused_test_command"]["args"]]
        work = Path(tempfile.mkdtemp(prefix="harness-operational-driver-"))
        cleanup_status = "pending"
        phase = "snapshot"
        manifest = capture_snapshot(receipt, work / "snapshot")
        phase = "focused_test"
        execution = execute_focused_test(final_argv, work / "snapshot")
        packet = {
            "schema": SCHEMA,
            "recipients": ["anubis", "maat"],
            "status": execution["outcome"],
            "phase": phase,
            "task_ref": task_ref,
            "revision": revision,
            "evidence": {
                "scope_receipt_sha256": receipt_sha256,
                "snapshot_manifest": manifest,
                "test_environment": {
                    "config": config,
                    "bytes_utf8": config_raw.decode("utf-8"),
                    "sha256": _sha256(config_raw),
                },
                "runner": runner,
                "final_argv": final_argv,
                "execution": execution,
            },
        }
    except Exception as exc:
        error = exc if isinstance(exc, DriverError) else DriverError(f"unexpected driver failure: {exc.__class__.__name__}")
        packet = {
            "schema": SCHEMA,
            "recipients": ["anubis", "maat"],
            "status": "failure",
            "phase": phase,
            "task_ref": task_ref,
            "revision": revision,
            "evidence": {
                "scope_receipt_sha256": receipt_sha256,
            },
            "error": {"type": error.__class__.__name__, "message": str(error)},
        }
    finally:
        if work is None:
            cleanup_status = "not_applicable"
        else:
            try:
                shutil.rmtree(work)
                cleanup_status = "removed"
            except Exception as exc:
                cleanup_status = "failed"
                cleanup_error = {"type": exc.__class__.__name__, "message": "ephemeral work cleanup failed"}
    packet["cleanup_status"] = cleanup_status
    packet["evidence_retention"] = {"location": "packet.evidence", "until": "maat_close"}
    if cleanup_error is not None:
        packet["status"] = "failure"
        packet["phase"] = "cleanup"
        packet["cleanup_error"] = cleanup_error
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope-receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    packet = run(args.scope_receipt)
    print(json.dumps(packet, sort_keys=True, separators=(",", ":")))
    return 0 if packet["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
