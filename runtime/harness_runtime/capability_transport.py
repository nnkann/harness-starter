from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .project_binding import BINDING_SCHEMA, CAPABILITY_GRAPH_SCHEMA

STATE_NAMESPACE = "capability-readiness-transport-foundation-v1"
RECEIPT_SCHEMA = "harness.capability-transport.immutable-receipt.v1"
RESULT_SCHEMA = "harness.capability-transport.result.v1"
CLAIM_SCHEMA = "harness.capability-transport.claim.v1"
CLAIM_TTL = timedelta(minutes=5)
_HOST_FIELDS = frozenset({"profile", "session_id", "task_id"})
_REPAIR_REASONS = frozenset({
    "binding_invalid",
    "capability_ref_invalid",
    "claim_malformed",
    "host_context_invalid",
    "sealed_claim_corrupt",
    "sealed_claim_expired",
    "sealed_delivery_unresolved",
    "state_dir_unavailable",
    "terminal_claim_corrupt",
    "tool_arguments_invalid",
})
_SEALED_FIELDS = (
    "capability_ref",
    "producer",
    "recipient",
    "action",
    "expires_at",
    "correlation",
    "seal_digest",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bounded_ref(value: object) -> str:
    if isinstance(value, str) and value:
        return value[:256]
    return "invalid"


def _correlation(
    capability_ref: object,
    host_context: object,
    project_id: object = None,
    action: object = None,
) -> dict[str, str | None]:
    host = host_context if isinstance(host_context, Mapping) else {}
    def bounded(value: object) -> str | None:
        return value if isinstance(value, str) and 0 < len(value) <= 256 else None

    correlation: dict[str, str | None] = {
        "project_id": bounded(project_id),
        "profile": bounded(host.get("profile")),
        "session_id": bounded(host.get("session_id")),
        "task_id": bounded(host.get("task_id")),
        "action": bounded(action),
        "digest": None,
    }
    correlation["digest"] = _digest({
        "capability_ref": _bounded_ref(capability_ref),
        **{
            key: correlation[key]
            for key in ("project_id", "profile", "session_id", "task_id", "action")
        },
    })
    return correlation


def repair_envelope(
    capability_ref: object,
    reason: str,
    *,
    host_context: object = None,
    project_id: object = None,
    action: object = None,
) -> dict[str, Any]:
    correlation = _correlation(capability_ref, host_context, project_id, action)
    return {
        "schema": RESULT_SCHEMA,
        "capability_ref": _bounded_ref(capability_ref),
        "correlation": correlation,
        "status": "foundation_repair_required",
        "digest": _digest({"correlation": correlation["digest"], "reason": reason}),
        "size": 0,
        "assessment": "foundation_repair_required",
        "repair": {"ref": _bounded_ref(capability_ref), "reason": reason},
    }


def _open_child_directory(parent_fd: int, name: str, mode: int = 0o700) -> int:
    try:
        os.mkdir(name, mode=mode, dir_fd=parent_fd)
    except FileExistsError:
        pass
    fd = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("state component is not a directory")
        os.fchmod(fd, mode)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _state_layout() -> tuple[Path, int]:
    configured = os.environ.get("HARNESS_STATE_DIR")
    if not configured:
        raise ValueError("HARNESS_STATE_DIR is required")
    base = Path(os.path.abspath(Path(configured).expanduser()))
    base.parent.mkdir(parents=True, exist_ok=True)
    parent = base.parent.resolve(strict=True)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        base_fd = _open_child_directory(parent_fd, base.name)
    finally:
        os.close(parent_fd)
    root = base / STATE_NAMESPACE
    try:
        root_fd = _open_child_directory(base_fd, STATE_NAMESPACE)
    finally:
        os.close(base_fd)
    try:
        claims_fd = _open_child_directory(root_fd, "claims")
    finally:
        os.close(root_fd)
    return root, claims_fd


def _state_root() -> Path:
    root, claims_fd = _state_layout()
    os.close(claims_fd)
    return root


def _load_binding(capability_ref: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path.cwd().resolve()
    path = root / ".harness" / "project-binding.json"
    binding = json.loads(path.read_text(encoding="utf-8"))
    if binding.get("schema") != BINDING_SCHEMA:
        raise ValueError("binding schema")
    project = binding.get("project")
    if (
        not isinstance(project, dict)
        or project.get("root") != str(root)
        or not isinstance(project.get("id"), str)
        or not project["id"]
        or len(project["id"]) > 256
    ):
        raise ValueError("binding project")
    graph = binding.get("capability_graph")
    if not isinstance(graph, dict) or graph.get("schema") != CAPABILITY_GRAPH_SCHEMA:
        raise ValueError("binding graph")
    claimed_digest = graph.get("digest")
    unsigned = {key: value for key, value in graph.items() if key != "digest"}
    if not isinstance(claimed_digest, str) or claimed_digest != _digest(unsigned):
        raise ValueError("binding graph digest")
    capabilities = graph.get("capabilities")
    matches = [
        item for item in capabilities if isinstance(item, dict) and item.get("capability_id") == capability_ref
    ] if isinstance(capabilities, list) else []
    if len(matches) != 1:
        raise LookupError("capability ref")
    capability = matches[0]
    profiles = capability.get("profiles")
    required = (
        capability.get("operation"),
        profiles.get("preflight") if isinstance(profiles, dict) else None,
        profiles.get("consumer") if isinstance(profiles, dict) else None,
    )
    if any(not isinstance(value, str) or not value or len(value) > 256 for value in required):
        raise ValueError("binding transport")
    return binding, capability


def _validate_host_context(host_context: object) -> dict[str, str]:
    if not isinstance(host_context, Mapping) or frozenset(host_context) != _HOST_FIELDS:
        raise ValueError("host context fields")
    if any(
        not isinstance(host_context[key], str)
        or not host_context[key]
        or len(host_context[key]) > 256
        for key in _HOST_FIELDS
    ):
        raise ValueError("host context values")
    return {key: host_context[key] for key in sorted(_HOST_FIELDS)}


def _claim_key(capability_ref: str, host: Mapping[str, str], project_id: str) -> str:
    return _digest({
        "capability_ref": capability_ref,
        "project_id": project_id,
        "profile": host["profile"],
        "session_id": host["session_id"],
        "task_id": host["task_id"],
    })


def _claim_path(capability_ref: str, host_context: Mapping[str, str]) -> Path:
    host = _validate_host_context(host_context)
    binding, _ = _load_binding(capability_ref)
    return _state_root() / "claims" / f"{_claim_key(capability_ref, host, binding['project']['id'])}.json"


def _claims_directory(path: Path) -> int:
    root, claims_fd = _state_layout()
    if path.parent != root / "claims" or path.name in {"", ".", ".."}:
        os.close(claims_fd)
        raise OSError("claim path outside state namespace")
    return claims_fd


def _regular_entry(fd: int, name: str) -> bool:
    try:
        metadata = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(metadata.st_mode):
        raise OSError("state artifact is not a regular file")
    return True


def _atomic_write(path: Path, value: object) -> None:
    payload = _canonical(value) + b"\n"
    claims_fd = _claims_directory(path)
    temporary = ""
    try:
        _regular_entry(claims_fd, path.name)
        for _ in range(8):
            candidate = f".{path.name}.{secrets.token_hex(8)}"
            try:
                fd = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=claims_fd,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
        else:
            raise OSError("atomic state name unavailable")
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path.name, src_dir_fd=claims_fd, dst_dir_fd=claims_fd)
        temporary = ""
        written_fd = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=claims_fd,
        )
        try:
            if not stat.S_ISREG(os.fstat(written_fd).st_mode):
                raise OSError("written claim is not regular")
            os.fchmod(written_fd, 0o600)
        finally:
            os.close(written_fd)
        os.fsync(claims_fd)
    finally:
        if temporary:
            try:
                os.unlink(temporary, dir_fd=claims_fd)
            except FileNotFoundError:
                pass
        os.close(claims_fd)


def _read_claim(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    claims_fd = None
    try:
        claims_fd = _claims_directory(path)
        if not _regular_entry(claims_fd, path.name):
            return None, None
        fd = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=claims_fd,
        )
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, "state_dir_unavailable"
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "claim_malformed"
    finally:
        if claims_fd is not None:
            os.close(claims_fd)
    if not isinstance(value, dict):
        return None, "claim_malformed"
    return value, None


def _open_lock(path: Path) -> int:
    claims_fd = _claims_directory(path)
    try:
        try:
            fd = os.open(
                path.name,
                os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=claims_fd,
            )
        except FileExistsError:
            fd = os.open(
                path.name,
                os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=claims_fd,
            )
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("lock is not a regular file")
            os.fchmod(fd, 0o600)
            return fd
        except BaseException:
            os.close(fd)
            raise
    finally:
        os.close(claims_fd)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _sealed_claim(
    capability_ref: str,
    host: Mapping[str, str],
    binding: Mapping[str, Any],
    capability: Mapping[str, Any],
) -> dict[str, Any]:
    correlation = _correlation(
        capability_ref,
        host,
        binding["project"]["id"],
        capability["operation"],
    )
    expires_at = _timestamp(_now() + CLAIM_TTL)
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "capability_ref": capability_ref,
        "producer": capability["profiles"]["preflight"],
        "recipient": capability["profiles"]["consumer"],
        "action": capability["operation"],
        "expires_at": expires_at,
        "correlation": correlation,
    }
    receipt["seal_digest"] = _digest(receipt)
    claim: dict[str, Any] = {
        "schema": CLAIM_SCHEMA,
        "status": "sealed",
        **{key: receipt[key] for key in _SEALED_FIELDS if key in receipt},
        "receipt": receipt,
    }
    claim["seal_digest"] = receipt["seal_digest"]
    return claim


def _expected_seal(
    capability_ref: str,
    host: Mapping[str, str],
    binding: Mapping[str, Any],
    capability: Mapping[str, Any],
    claim: Mapping[str, Any],
) -> dict[str, Any] | None:
    receipt = claim.get("receipt")
    expires_at = claim.get("expires_at")
    if not isinstance(receipt, dict) or not isinstance(expires_at, str):
        return None
    expected = {
        "schema": RECEIPT_SCHEMA,
        "capability_ref": capability_ref,
        "producer": capability["profiles"]["preflight"],
        "recipient": capability["profiles"]["consumer"],
        "action": capability["operation"],
        "expires_at": expires_at,
        "correlation": _correlation(
            capability_ref,
            host,
            binding["project"]["id"],
            capability["operation"],
        ),
    }
    expected["seal_digest"] = _digest(expected)
    if receipt != expected:
        return None
    if any(claim.get(key) != expected.get(key) for key in _SEALED_FIELDS):
        return None
    return expected


def _terminal_result(
    capability_ref: str,
    correlation: Mapping[str, Any],
    *,
    status: str,
    assessment: str,
    output: object,
) -> dict[str, Any]:
    raw = output if isinstance(output, bytes) else str(output or "").encode("utf-8", errors="replace")
    return {
        "schema": RESULT_SCHEMA,
        "capability_ref": capability_ref,
        "correlation": dict(correlation),
        "status": status,
        "digest": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
        "assessment": assessment,
        "repair": None,
    }


def _repair_terminal(
    capability_ref: str,
    reason: str,
    host: Mapping[str, str],
    project_id: str,
    action: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = repair_envelope(
        capability_ref,
        reason,
        host_context=host,
        project_id=project_id,
        action=action,
    )
    persisted = {"schema": CLAIM_SCHEMA, "status": "terminal", "terminal": result}
    return persisted, result


def _valid_terminal(
    value: object,
    capability_ref: str,
    host: Mapping[str, str],
    project_id: str,
    action: str,
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "capability_ref",
        "correlation",
        "status",
        "digest",
        "size",
        "assessment",
        "repair",
    }:
        return False
    if (
        value.get("schema") != RESULT_SCHEMA
        or value.get("capability_ref") != capability_ref
        or value.get("correlation") != _correlation(capability_ref, host, project_id, action)
        or value.get("status") not in {"delivered", "failed", "foundation_repair_required"}
        or not isinstance(value.get("digest"), str)
        or len(value["digest"]) != 64
        or any(character not in "0123456789abcdef" for character in value["digest"])
        or not isinstance(value.get("size"), int)
        or value["size"] < 0
    ):
        return False
    if value["status"] == "foundation_repair_required":
        repair = value.get("repair")
        return (
            value.get("assessment") == "foundation_repair_required"
            and isinstance(repair, dict)
            and set(repair) == {"ref", "reason"}
            and repair.get("ref") == capability_ref
            and repair.get("reason") in _REPAIR_REASONS
        )
    return (
        value.get("repair") is None
        and value.get("assessment")
        in {"consumer_delivered", "delivery_failure", "delivery_timeout", "delivery_signal"}
    )


def _run_delivery(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )


def consume_capability(capability_ref: object, *, host_context: object) -> dict[str, Any]:
    try:
        host = _validate_host_context(host_context)
    except ValueError:
        return repair_envelope(capability_ref, "host_context_invalid", host_context=host_context)
    if not isinstance(capability_ref, str) or not capability_ref or len(capability_ref) > 256:
        return repair_envelope(capability_ref, "capability_ref_invalid", host_context=host)
    try:
        binding, capability = _load_binding(capability_ref)
    except LookupError:
        return repair_envelope(capability_ref, "capability_ref_invalid", host_context=host)
    except (OSError, ValueError, json.JSONDecodeError):
        return repair_envelope(capability_ref, "binding_invalid", host_context=host)
    project_id = binding["project"]["id"]
    try:
        state_root = _state_root()
    except (OSError, ValueError):
        return repair_envelope(
            capability_ref,
            "state_dir_unavailable",
            host_context=host,
            project_id=project_id,
            action=capability["operation"],
        )
    key = _claim_key(capability_ref, host, project_id)
    claim_path = state_root / "claims" / f"{key}.json"
    lock_path = state_root / "claims" / f"{key}.lock"
    try:
        lock_fd = _open_lock(lock_path)
    except OSError:
        return repair_envelope(
            capability_ref,
            "state_dir_unavailable",
            host_context=host,
            project_id=project_id,
            action=capability["operation"],
        )
    try:
        lock = os.fdopen(lock_fd, "r+")
    except OSError:
        os.close(lock_fd)
        return repair_envelope(
            capability_ref,
            "state_dir_unavailable",
            host_context=host,
            project_id=project_id,
            action=capability["operation"],
        )
    try:
        with lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            claim, read_error = _read_claim(claim_path)
            if read_error == "state_dir_unavailable":
                return repair_envelope(
                    capability_ref,
                    read_error,
                    host_context=host,
                    project_id=project_id,
                    action=capability["operation"],
                )
            if read_error:
                persisted, result = _repair_terminal(
                    capability_ref,
                    read_error,
                    host,
                    project_id,
                    capability["operation"],
                )
                _atomic_write(claim_path, persisted)
                return result
            if claim and claim.get("status") == "terminal":
                terminal = claim.get("terminal")
                if isinstance(terminal, dict) and _valid_terminal(
                    terminal,
                    capability_ref,
                    host,
                    project_id,
                    capability["operation"],
                ):
                    return terminal
                persisted, result = _repair_terminal(
                    capability_ref,
                    "terminal_claim_corrupt",
                    host,
                    project_id,
                    capability["operation"],
                )
                _atomic_write(claim_path, persisted)
                return result
            if claim and claim.get("status") == "sealed":
                receipt = _expected_seal(capability_ref, host, binding, capability, claim)
                if receipt is None:
                    reason = "sealed_claim_corrupt"
                else:
                    expiry = _parse_timestamp(receipt["expires_at"])
                    reason = "sealed_claim_expired" if expiry is None or expiry <= _now() else "sealed_delivery_unresolved"
                persisted, result = _repair_terminal(
                    capability_ref,
                    reason,
                    host,
                    project_id,
                    capability["operation"],
                )
                _atomic_write(claim_path, persisted)
                return result
            if claim is not None and claim != {"schema": CLAIM_SCHEMA, "status": "prepared"}:
                persisted, result = _repair_terminal(
                    capability_ref,
                    "claim_malformed",
                    host,
                    project_id,
                    capability["operation"],
                )
                _atomic_write(claim_path, persisted)
                return result
            claim = _sealed_claim(capability_ref, host, binding, capability)
            _atomic_write(claim_path, claim)
            receipt_text = _canonical(claim["receipt"]).decode("utf-8")
            argv = [
                "hermes",
                "-p",
                claim["recipient"],
                "chat",
                "--resume",
                host["session_id"],
                "-Q",
                "-q",
                receipt_text,
            ]
            try:
                completed = _run_delivery(argv)
            except subprocess.TimeoutExpired as exc:
                stdout = exc.output.decode("utf-8", errors="replace") if isinstance(exc.output, bytes) else str(exc.output or "")
                stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
                output = stdout + stderr
                assessment = "delivery_timeout"
                status = "failed"
            except BaseException as exc:
                output = type(exc).__name__
                assessment = "delivery_signal" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "delivery_failure"
                status = "failed"
            else:
                output = f"{completed.stdout or ''}{completed.stderr or ''}"
                if completed.returncode == 0:
                    assessment = "consumer_delivered"
                    status = "delivered"
                elif completed.returncode < 0:
                    assessment = "delivery_signal"
                    status = "failed"
                else:
                    assessment = "delivery_failure"
                    status = "failed"
            result = _terminal_result(
                capability_ref,
                claim["correlation"],
                status=status,
                assessment=assessment,
                output=output,
            )
            claim["status"] = "terminal"
            claim["terminal"] = result
            _atomic_write(claim_path, claim)
            return result
    except OSError:
        return repair_envelope(
            capability_ref,
            "state_dir_unavailable",
            host_context=host,
            project_id=project_id,
            action=capability["operation"],
        )
    finally:
        try:
            lock.close()
        except OSError:
            pass
