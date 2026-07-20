from __future__ import annotations

import hashlib
import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOOL_ID = "harness-project-binding"
BINDING_SCHEMA = "harness.project-binding.v1"
LOCK_SCHEMA = "harness.runtime-lock.v1"
RUNTIME_ROOT = Path(__file__).resolve().parents[1]
MANAGED_PATHS = (
    ".harness/bin/harness-binding",
    ".harness/bin/harness-sandbox-run",
    ".harness/project-binding.json",
    ".harness/runtime.lock.json",
)


class BindingError(ValueError):
    pass


@dataclass(frozen=True)
class BindingInputs:
    project_id: str
    project_root: Path
    protected_branch: str
    railway_service: str
    runtime_version: str = "1"

    def normalized(self) -> "BindingInputs":
        root = self.project_root.expanduser().resolve()
        values = (self.project_id, self.protected_branch, self.railway_service, self.runtime_version)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise BindingError("project id, protected branch, Railway service, and runtime version are required")
        if not root.is_dir():
            raise BindingError(f"project root does not exist: {root}")
        return BindingInputs(
            self.project_id.strip(),
            root,
            self.protected_branch.strip(),
            self.railway_service.strip(),
            self.runtime_version.strip(),
        )


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _desired(inputs: BindingInputs) -> dict[str, tuple[bytes, int]]:
    normalized = inputs.normalized()
    project = {
        "id": normalized.project_id,
        "root": str(normalized.project_root),
        "protected_branch": normalized.protected_branch,
        "railway_service": normalized.railway_service,
    }
    runtime_root = str(RUNTIME_ROOT)
    digest = hashlib.sha256(
        _canonical({"project": project, "runtime_root": runtime_root, "runtime_version": normalized.runtime_version})
    ).hexdigest()
    lock = {
        "schema": LOCK_SCHEMA,
        "managed_by": TOOL_ID,
        "version": normalized.runtime_version,
        "root": runtime_root,
        "digest": digest,
    }
    binding = {
        "schema": BINDING_SCHEMA,
        "managed_by": TOOL_ID,
        "project": project,
        "runtime_lock": {
            "path": ".harness/runtime.lock.json",
            "version": normalized.runtime_version,
            "digest": digest,
        },
        "verification": {
            "clean_worktree_required": True,
            "external_state_dir_required": True,
            "sandbox_backend": "macos-sandbox-exec",
            "network_default": "deny",
        },
        "managed_files": list(MANAGED_PATHS),
    }
    launcher_prefix = (
        "#!/bin/sh\n"
        "# managed-by: harness-project-binding\n"
        f"RUNTIME_ROOT={shlex.quote(runtime_root)}\n"
        'PYTHONPATH="$RUNTIME_ROOT${PYTHONPATH:+:$PYTHONPATH}"\n'
        "export PYTHONPATH\n"
    )
    binding_launcher = (launcher_prefix + 'exec "${PYTHON:-python3.11}" -m harness_runtime.binding_cli "$@"\n').encode()
    sandbox_launcher = (
        launcher_prefix + 'exec "${PYTHON:-python3.11}" -m harness_runtime.binding_cli sandbox "$@"\n'
    ).encode()
    return {
        MANAGED_PATHS[0]: (binding_launcher, 0o755),
        MANAGED_PATHS[1]: (sandbox_launcher, 0o755),
        MANAGED_PATHS[2]: (_json_bytes(binding), 0o644),
        MANAGED_PATHS[3]: (_json_bytes(lock), 0o644),
    }


def _owned(path: Path) -> bool:
    if path.name not in {"project-binding.json", "runtime.lock.json"}:
        try:
            return b"\n# managed-by: harness-project-binding\n" in path.read_bytes()[:128]
        except OSError:
            return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return value.get("managed_by") == TOOL_ID


def inspect_binding(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    binding_path = root / ".harness/project-binding.json"
    if not binding_path.exists():
        return {"status": "unbound", "project_root": str(root)}
    if not _owned(binding_path):
        return {"status": "conflict", "project_root": str(root), "path": ".harness/project-binding.json"}
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot inspect binding: {exc}") from exc
    missing = [path for path in binding.get("managed_files", []) if not (root / path).is_file()]
    return {"status": "drifted" if missing else "bound", "project_root": str(root), "binding": binding, "missing": missing}


def plan_binding(inputs: BindingInputs) -> dict[str, Any]:
    normalized = inputs.normalized()
    actions: list[dict[str, str]] = []
    for relative, (content, _) in _desired(normalized).items():
        path = normalized.project_root / relative
        if not path.exists():
            operation = "create"
        elif path.is_file() and path.read_bytes() == content:
            operation = "noop"
        elif _owned(path):
            operation = "update"
        else:
            operation = "conflict"
        actions.append({"operation": operation, "path": relative})
    return {"project_root": str(normalized.project_root), "actions": actions, "changed": any(a["operation"] in {"create", "update"} for a in actions)}


def _write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.chmod(temporary, mode)
    temporary.replace(path)


def apply_binding(inputs: BindingInputs) -> dict[str, Any]:
    normalized = inputs.normalized()
    plan = plan_binding(normalized)
    conflicts = [action["path"] for action in plan["actions"] if action["operation"] == "conflict"]
    if conflicts:
        raise BindingError("refusing to overwrite unmanaged files: " + ", ".join(conflicts))
    desired = _desired(normalized)
    for action in plan["actions"]:
        if action["operation"] in {"create", "update"}:
            content, mode = desired[action["path"]]
            _write(normalized.project_root / action["path"], content, mode)
    return plan


def reconcile_legacy(project_root: str | Path, *, apply: bool = False) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    manifest_path = root / ".harness/legacy-files.json"
    if not manifest_path.exists():
        return {"project_root": str(root), "actions": [], "changed": False}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot read legacy ownership manifest: {exc}") from exc
    files = manifest.get("files")
    if manifest.get("managed_by") != TOOL_ID or not isinstance(files, dict):
        raise BindingError("legacy ownership manifest is not tool-managed")

    actions: list[dict[str, str]] = []
    retained: dict[str, str] = {}
    removable: list[Path] = []
    for relative, expected_digest in files.items():
        if not isinstance(relative, str) or not isinstance(expected_digest, str):
            raise BindingError("legacy ownership manifest contains invalid entries")
        path = (root / relative).resolve()
        if path == root or root not in path.parents:
            actions.append({"operation": "retain-invalid", "path": relative})
            retained[relative] = expected_digest
        elif not path.is_file():
            actions.append({"operation": "retire-missing", "path": relative})
        elif hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest:
            actions.append({"operation": "remove", "path": relative})
            removable.append(path)
        else:
            actions.append({"operation": "retain-modified", "path": relative})
            retained[relative] = expected_digest

    if apply:
        for path in removable:
            path.unlink()
        if retained:
            _write(manifest_path, _json_bytes({"managed_by": TOOL_ID, "files": retained}), 0o644)
        else:
            manifest_path.unlink()
    return {
        "project_root": str(root),
        "actions": actions,
        "changed": bool(removable or any(action["operation"] == "retire-missing" for action in actions)),
    }