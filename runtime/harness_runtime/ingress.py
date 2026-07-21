from __future__ import annotations

import errno
import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

READY = "READY"
HOLD = "HOLD"
INGRESS_PACKET_SCHEMA = "harness.gateway.ingress-packet.v1"
EXECUTION_RECEIPT_SCHEMA = "harness.cps.execution-receipt.v1"
_GIT_ENV = {"LANG": "C", "LC_ALL": "C", "PATH": os.defpath}
_BOOTSTRAP_MANIFEST = b"schema: harness.project.v1\n"
BASELINE_CACHE_SECONDS = 2.0
TERMINAL_RECEIPT_RETENTION_SECONDS = 7 * 24 * 60 * 60
RECEIPT_PRUNE_INTERVAL_SECONDS = 5 * 60
_receipt_prune_due: dict[Path, float] = {}


class IngressValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EventRef:
    event_id: str
    payload_hash: str
    channel_id: str
    bound: bool
    parent_event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not self.channel_id:
            raise IngressValidationError("event_id and channel_id are required")
        if len(self.payload_hash) != 64 or any(character not in "0123456789abcdef" for character in self.payload_hash):
            raise IngressValidationError("payload_hash must be a lowercase SHA-256 digest")
        if self.parent_event_id is not None and not self.parent_event_id:
            raise IngressValidationError("parent_event_id cannot be empty")


@dataclass(frozen=True)
class ProjectRef:
    root: Path
    manifest: Path
    allow_bootstrap_manifest: bool = False

    @classmethod
    def bind_cwd(
        cls,
        root: str | Path | None = None,
        *,
        allow_bootstrap_manifest: bool = False,
    ) -> ProjectRef:
        binding_root = Path.cwd() if root is None else Path(root)
        binding_root = Path(os.path.abspath(binding_root.expanduser()))
        return cls(binding_root, binding_root / "manifest.yml", allow_bootstrap_manifest)


@dataclass(frozen=True)
class IntakeResult:
    status: str
    manifest_ref: str
    manifest_hash: str | None
    binding_evidence: Mapping[str, Any]
    baseline_worktree_state: Mapping[str, Any]
    cps_receipt_id: str
    cache_key: tuple[str, int, str] | None
    hold_reason: str | None = None


@dataclass(frozen=True)
class IngressPacket:
    schema: str
    event_ref: EventRef
    project_ref: ProjectRef
    intake: IntakeResult
    cps_receipt_id: str
    intent: str


def cps_receipt_id(event_ref: EventRef) -> str:
    return f"cps-{event_ref.event_id}-{event_ref.payload_hash[:12]}"


def _immutable(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_GIT_ENV,
    )


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


class IngressIntake:
    """Shared in-process intake for bound Gateway events."""

    def __init__(self) -> None:
        self._binding_cache: dict[tuple[str, str], tuple[Mapping[str, Any] | None, str | None]] = {}
        self._baseline_cache: dict[Path, tuple[float, Mapping[str, Any]]] = {}

    def evaluate(self, event_ref: EventRef, project_ref: ProjectRef) -> IntakeResult:
        if not isinstance(event_ref, EventRef) or not isinstance(project_ref, ProjectRef):
            raise IngressValidationError("intake accepts only EventRef and ProjectRef")

        receipt_id = cps_receipt_id(event_ref)
        root = project_ref.root.expanduser().resolve()
        manifest = project_ref.manifest.expanduser().resolve()
        manifest_ref = str(manifest)
        baseline = self._baseline(root)
        manifest_created = False

        try:
            stat = project_ref.manifest.stat()
            content = project_ref.manifest.read_bytes()
        except OSError as exc:
            if exc.errno != errno.ENOENT or not project_ref.allow_bootstrap_manifest:
                return self._hold(receipt_id, manifest_ref, baseline, f"manifest unavailable: {exc.__class__.__name__}")
            try:
                manifest_created = self._bootstrap_manifest(project_ref)
                stat = project_ref.manifest.stat()
                content = project_ref.manifest.read_bytes()
            except (OSError, IngressValidationError) as bootstrap_exc:
                return self._hold(
                    receipt_id,
                    manifest_ref,
                    baseline,
                    f"manifest unavailable: {bootstrap_exc.__class__.__name__}",
                )

        manifest_hash = hashlib.sha256(content).hexdigest()
        cache_key = (str(root), stat.st_mtime_ns, manifest_hash)
        validation_key = (str(root), manifest_hash)
        if validation_key not in self._binding_cache:
            try:
                evidence = self._validate_binding(project_ref, content, manifest_hash)
                self._binding_cache[validation_key] = (evidence, None)
            except IngressValidationError as exc:
                self._binding_cache[validation_key] = (None, str(exc))

        cached_evidence, hold_reason = self._binding_cache[validation_key]
        evidence = (
            _immutable({**cached_evidence, "manifest_created": manifest_created})
            if cached_evidence is not None
            else None
        )
        if hold_reason is not None or evidence is None:
            return IntakeResult(
                HOLD,
                manifest_ref,
                manifest_hash,
                _immutable({}),
                baseline,
                receipt_id,
                cache_key,
                hold_reason,
            )
        return IntakeResult(READY, manifest_ref, manifest_hash, evidence, baseline, receipt_id, cache_key)

    def _bootstrap_manifest(self, project_ref: ProjectRef) -> bool:
        root = project_ref.root.expanduser()
        manifest = project_ref.manifest.expanduser()
        if not root.is_absolute() or manifest != root / "manifest.yml":
            raise IngressValidationError("manifest boundary must be <root>/manifest.yml")
        if _has_symlink_component(root) or _has_symlink_component(manifest):
            raise IngressValidationError("bootstrap boundary must not contain symlinks")

        top_level = _git(root, "rev-parse", "--show-toplevel")
        if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root.resolve():
            raise IngressValidationError("binding root must be the Git worktree root")

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        try:
            descriptor = os.open(manifest, flags, 0o600)
        except FileExistsError:
            return False

        try:
            view = memoryview(_BOOTSTRAP_MANIFEST)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("manifest write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        except BaseException:
            try:
                manifest.unlink()
            except OSError:
                pass
            raise
        finally:
            os.close(descriptor)
        return True

    def _validate_binding(
        self,
        project_ref: ProjectRef,
        content: bytes,
        manifest_hash: str,
    ) -> Mapping[str, Any]:
        root = project_ref.root.expanduser().resolve()
        manifest = project_ref.manifest.expanduser().resolve()
        expected_manifest = root / "manifest.yml"
        if not root.is_dir():
            raise IngressValidationError("binding root is not a directory")
        if manifest != expected_manifest or project_ref.manifest.is_symlink():
            raise IngressValidationError("manifest boundary must be <root>/manifest.yml")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IngressValidationError("manifest must be UTF-8") from exc
        if not text.strip():
            raise IngressValidationError("manifest must not be empty")

        top_level = _git(root, "rev-parse", "--show-toplevel")
        if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root:
            raise IngressValidationError("binding root must be the Git worktree root")
        return _immutable({
            "root": str(root),
            "manifest_entry": str(expected_manifest),
            "manifest_hash": manifest_hash,
            "environment_valid": True,
            "boundary_valid": True,
        })

    def _baseline(self, root: Path) -> Mapping[str, Any]:
        now = time.monotonic()
        cached = self._baseline_cache.get(root)
        if cached is not None and now - cached[0] < BASELINE_CACHE_SECONDS:
            return cached[1]
        head = _git(root, "rev-parse", "HEAD")
        status = _git(root, "status", "--porcelain", "--untracked-files=all")
        if head.returncode != 0 or status.returncode != 0:
            baseline = _immutable({"head": None, "dirty": False, "changes": (), "available": False})
            self._baseline_cache[root] = (now, baseline)
            return baseline
        changes = tuple(status.stdout.splitlines())
        baseline = _immutable({"head": head.stdout.strip(), "dirty": bool(changes), "changes": changes})
        self._baseline_cache[root] = (now, baseline)
        return baseline

    def _hold(
        self,
        receipt_id: str,
        manifest_ref: str,
        baseline: Mapping[str, Any],
        reason: str,
    ) -> IntakeResult:
        return IntakeResult(HOLD, manifest_ref, None, _immutable({}), baseline, receipt_id, None, reason)


def structured_packet(
    event_ref: EventRef,
    project_ref: ProjectRef,
    intake: IntakeResult,
    intent: str,
) -> IngressPacket:
    if intake.status != READY:
        raise IngressValidationError("structured Hermes-kann ingress requires READY")
    if not isinstance(intent, str) or not intent.strip():
        raise IngressValidationError("structured Hermes-kann ingress requires an intent")
    return IngressPacket(
        INGRESS_PACKET_SCHEMA,
        event_ref,
        project_ref,
        intake,
        intake.cps_receipt_id,
        intent,
    )


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def canonical_packet_json(packet: IngressPacket) -> str:
    value = {
        "schema": packet.schema,
        "event_ref": {
            "event_id": packet.event_ref.event_id,
            "payload_hash": packet.event_ref.payload_hash,
            "channel_id": packet.event_ref.channel_id,
            "bound": packet.event_ref.bound,
            "parent_event_id": packet.event_ref.parent_event_id,
        },
        "project_ref": {
            "root": str(packet.project_ref.root),
            "manifest": str(packet.project_ref.manifest),
        },
        "manifest_ref": packet.intake.manifest_ref,
        "manifest_hash": packet.intake.manifest_hash,
        "binding_evidence": packet.intake.binding_evidence,
        "baseline_worktree_state": packet.intake.baseline_worktree_state,
        "cps_receipt_id": packet.cps_receipt_id,
        "intent": packet.intent,
    }
    return _canonical(_jsonable(value)).decode("ascii")


class ExecutionReceipts:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory).expanduser().resolve()

    def start(self, receipt_id: str, event_ref: EventRef) -> None:
        self.prune_terminal_if_due()
        receipt = {"schema": EXECUTION_RECEIPT_SCHEMA, "cps_receipt_id": receipt_id, "entries": []}
        self._append(
            receipt,
            "received",
            {"event_id": event_ref.event_id, "payload_hash": event_ref.payload_hash},
            exclusive=True,
        )

    def prune_terminal(self, *, retention_seconds: float = TERMINAL_RECEIPT_RETENTION_SECONDS) -> int:
        if retention_seconds < 0:
            raise ValueError("retention_seconds must be non-negative")
        if not self.directory.is_dir():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - retention_seconds
        removed = 0
        for path in self.directory.glob("*.json"):
            try:
                receipt = json.loads(path.read_text(encoding="ascii"))
                entries = receipt["entries"]
                terminal_at = datetime.fromisoformat(entries[-1]["recorded_at"]).timestamp()
            except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if entries[-1].get("stage") != "terminal" or terminal_at > cutoff:
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed

    def prune_terminal_if_due(self) -> None:
        directory = self.directory
        now = time.monotonic()
        if now - _receipt_prune_due.get(directory, 0.0) < RECEIPT_PRUNE_INTERVAL_SECONDS:
            return
        self.prune_terminal()
        _receipt_prune_due[directory] = now

    def transition(self, receipt_id: str, stage: str, evidence: Mapping[str, Any]) -> None:
        receipt = self.read(receipt_id, require_terminal=False)
        self._append(receipt, stage, dict(evidence))

    def read(self, receipt_id: str, *, require_terminal: bool = True) -> dict[str, Any]:
        try:
            receipt = json.loads(self._path(receipt_id).read_text(encoding="ascii"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngressValidationError("CPS execution receipt readback unavailable") from exc
        if receipt.get("schema") != EXECUTION_RECEIPT_SCHEMA or receipt.get("cps_receipt_id") != receipt_id:
            raise IngressValidationError("CPS execution receipt identity mismatch")
        previous_hash = None
        for sequence, entry in enumerate(receipt.get("entries", ()), start=1):
            body = {key: value for key, value in entry.items() if key != "receipt_hash"}
            if entry.get("sequence") != sequence or entry.get("previous_hash") != previous_hash:
                raise IngressValidationError("CPS execution receipt lifecycle is discontinuous")
            expected_hash = hashlib.sha256(_canonical(body)).hexdigest()
            if entry.get("receipt_hash") != expected_hash:
                raise IngressValidationError("CPS execution receipt digest mismatch")
            previous_hash = expected_hash
        stages = [entry["stage"] for entry in receipt["entries"]]
        valid = stages in (
            ["received", "intake-ready", "route", "running", "terminal"],
            ["received", "intake-ready", "terminal"],
            ["received", "intake-hold", "terminal"],
        )
        if require_terminal and not valid:
            raise IngressValidationError("CPS execution receipt is not terminal")
        return receipt

    def _append(
        self,
        receipt: dict[str, Any],
        stage: str,
        evidence: Mapping[str, Any],
        *,
        exclusive: bool = False,
    ) -> None:
        entries = receipt["entries"]
        body = {
            "sequence": len(entries) + 1,
            "stage": stage,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "previous_hash": entries[-1]["receipt_hash"] if entries else None,
            "evidence": _jsonable(evidence),
        }
        entries.append({**body, "receipt_hash": hashlib.sha256(_canonical(body)).hexdigest()})
        path = self._path(receipt["cps_receipt_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if exclusive:
            try:
                with path.open("xb") as stream:
                    stream.write(_canonical(receipt) + b"\n")
            except FileExistsError as exc:
                raise IngressValidationError("CPS execution receipt already exists") from exc
            return
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(_canonical(receipt) + b"\n")
        temporary.replace(path)

    def _path(self, receipt_id: str) -> Path:
        digest = hashlib.sha256(receipt_id.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"


def process_bound_ingress(
    event_ref: EventRef,
    project_ref: ProjectRef,
    *,
    intent: str,
    receipt_dir: str | Path,
    intake: IngressIntake | None = None,
) -> dict[str, Any]:
    receipts = ExecutionReceipts(receipt_dir)
    receipt_id = cps_receipt_id(event_ref)
    receipts.start(receipt_id, event_ref)
    intake_result = (intake or IngressIntake()).evaluate(event_ref, project_ref)
    intake_evidence = {
        "status": intake_result.status,
        "manifest_ref": intake_result.manifest_ref,
        "manifest_hash": intake_result.manifest_hash,
        "binding_evidence": intake_result.binding_evidence,
        "baseline_worktree_state": intake_result.baseline_worktree_state,
        "cps_receipt_id": intake_result.cps_receipt_id,
    }
    if intake_result.status != READY:
        receipts.transition(receipt_id, "intake-hold", intake_evidence)
        result = {"status": HOLD, "reason": intake_result.hold_reason, "cps_receipt_id": receipt_id}
        receipts.transition(receipt_id, "terminal", result)
        receipts.read(receipt_id)
        return result

    receipts.transition(receipt_id, "intake-ready", intake_evidence)
    packet = structured_packet(event_ref, project_ref, intake_result, intent)
    return {
        "status": READY,
        "cps_receipt_id": receipt_id,
        "packet": packet,
        "canonical_packet": canonical_packet_json(packet),
    }
