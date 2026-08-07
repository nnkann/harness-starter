from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

ENROLLMENT_VERSION = "1"
MANIFEST_SCHEMA = "harness.project-manifest.v2"
MAPPING_PREFIX = "platforms.discord.extra.channel_project_bindings"
_JSON_NULL = object()


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: MappingNode, deep: bool = False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError("while constructing a mapping", node.start_mark, "duplicate key", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class EnrollmentError(ValueError):
    pass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class FilesystemAdapter(Protocol):
    def lstat(self, path: Path) -> os.stat_result | None: ...

    def read_bytes(self, path: Path) -> bytes: ...

    def create_exclusive(self, path: Path, content: bytes) -> None: ...


class SubprocessAdapter(Protocol):
    def run(self, argv: list[str]) -> CommandResult: ...


class ConfigAdapter(Protocol):
    def get(self, executable: Path, key: str) -> object | None: ...

    def set(self, executable: Path, key: str, value: str) -> None: ...


@dataclass(frozen=True)
class EnrollmentAdapters:
    filesystem: FilesystemAdapter
    subprocess: SubprocessAdapter
    config: ConfigAdapter


@dataclass(frozen=True)
class EnrollmentRequest:
    version: str
    project_slug: str
    canonical_root: Path
    discord_parent_channel_id: str
    hermes_executable: Path
    hermes_config_target: Path
    idempotency_key: str

    def validated(self) -> "EnrollmentRequest":
        root = Path(self.canonical_root)
        if not root.is_absolute():
            raise EnrollmentError("canonical_root must be absolute")
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise EnrollmentError(f"canonical_root cannot be strictly resolved: {root}") from exc
        if resolved_root != root or not root.is_dir():
            raise EnrollmentError("canonical_root must be a canonical directory")
        executable = Path(self.hermes_executable)
        if not executable.is_absolute():
            raise EnrollmentError("Hermes executable must be absolute")
        try:
            resolved_executable = executable.resolve(strict=True)
        except OSError as exc:
            raise EnrollmentError(f"Hermes executable cannot be resolved: {executable}") from exc
        if resolved_executable != executable or not executable.is_file() or not os.access(executable, os.X_OK):
            raise EnrollmentError("Hermes executable must be a canonical executable file")
        config_target = Path(self.hermes_config_target)
        if not config_target.is_absolute() or config_target.resolve() != config_target:
            raise EnrollmentError("Hermes config target must be an absolute canonical path")
        if self.version != ENROLLMENT_VERSION:
            raise EnrollmentError(f"unsupported enrollment version: {self.version}")
        if (
            not isinstance(self.project_slug, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", self.project_slug)
            or not isinstance(yaml.safe_load(self.project_slug), str)
        ):
            raise EnrollmentError("project_slug must be an explicit lowercase slug")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.discord_parent_channel_id):
            raise EnrollmentError("Discord parent channel id must be explicit and contain no path separators")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise EnrollmentError("idempotency_key must be nonempty")
        return EnrollmentRequest(
            version=self.version,
            project_slug=self.project_slug,
            canonical_root=resolved_root,
            discord_parent_channel_id=self.discord_parent_channel_id,
            hermes_executable=resolved_executable,
            hermes_config_target=config_target,
            idempotency_key=self.idempotency_key,
        )


class LocalFilesystem:
    def lstat(self, path: Path) -> os.stat_result | None:
        try:
            return path.lstat()
        except FileNotFoundError:
            return None

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def create_exclusive(self, path: Path, content: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o644)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)


class LocalSubprocess:
    def run(self, argv: list[str]) -> CommandResult:
        completed = subprocess.run(
            argv,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"LANG": "C", "LC_ALL": "C", "PATH": os.defpath},
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class HermesConfig:
    def __init__(self, subprocess_adapter: SubprocessAdapter):
        self.subprocess = subprocess_adapter

    def get(self, executable: Path, key: str) -> object | None:
        result = self.subprocess.run([str(executable), "config", "get", "--json", key])
        if result.returncode == 0:
            try:
                value = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise EnrollmentError("Hermes config read failed: invalid JSON readback") from exc
            return _JSON_NULL if value is None else value
        if result.returncode == 1 and result.stderr.strip() == f"Config key not set: {key}":
            return None
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise EnrollmentError(f"Hermes config read failed: {detail}")

    def set(self, executable: Path, key: str, value: str) -> None:
        result = self.subprocess.run(
            [str(executable), "config", "set", "--force", key, value]
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            raise EnrollmentError(f"Hermes config write failed: {detail}")


def _manifest_bytes(request: EnrollmentRequest) -> bytes:
    return yaml.safe_dump(
        {
            "schema": MANIFEST_SCHEMA,
            "project_slug": request.project_slug,
            "workspace": {"canonical_cwd": str(request.canonical_root)},
        },
        sort_keys=False,
        width=2**31 - 1,
    ).encode("utf-8")


def _mapping_key(request: EnrollmentRequest) -> str:
    return f"{MAPPING_PREFIX}.{request.discord_parent_channel_id}"


def _run_checked(adapters: EnrollmentAdapters, argv: list[str], purpose: str) -> CommandResult:
    result = adapters.subprocess.run(argv)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise EnrollmentError(f"{purpose} failed: {detail}")
    return result


def _component(operation: str, **fields: str) -> dict[str, Any]:
    return {"operation": operation, **fields, "observations": [], "receipts": []}


def _record_error(component: dict[str, Any], error: Exception) -> None:
    component["receipts"].append({"status": "partial", "error": str(error)})


def _config_target_component(
    request: EnrollmentRequest, adapters: EnrollmentAdapters
) -> dict[str, Any]:
    component = _component("noop", requested_path=str(request.hermes_config_target))
    try:
        result = _run_checked(
            adapters,
            [str(request.hermes_executable), "config", "path"],
            "Hermes config path readback",
        )
        active_path = result.stdout.rstrip("\n")
        component["active_path"] = active_path
        if active_path != str(request.hermes_config_target):
            component["observations"].append("target_mismatch")
    except Exception as exc:
        _record_error(component, exc)
    return component


def _project_primary(
    request: EnrollmentRequest,
    adapters: EnrollmentAdapters,
    slug: str,
    *,
    missing_ok: bool = False,
) -> Path | None:
    result = adapters.subprocess.run(
        [str(request.hermes_executable), "project", "show", slug]
    )
    if result.returncode:
        expected = f"project: no such project: {slug}"
        if missing_ok and result.returncode == 1 and result.stderr.strip() == expected:
            return None
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise EnrollmentError(f"Hermes project read failed: {detail}")
    output_lines = result.stdout.splitlines()
    if not output_lines:
        return None
    primary = next(
        (
            line.removeprefix("  primary: ")
            for line in output_lines[1:]
            if line.startswith("  primary: ")
        ),
        None,
    )
    return Path(primary) if primary is not None else None


def _root_project_slug(
    request: EnrollmentRequest, adapters: EnrollmentAdapters
) -> str | None:
    result = _run_checked(
        adapters,
        [str(request.hermes_executable), "project", "list"],
        "Hermes project enumeration",
    )
    if result.stdout.strip().startswith("No projects yet."):
        return None
    slugs = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if len(line) < 3 or line[0] not in " *" or line[1] != " ":
            raise EnrollmentError("Hermes project enumeration returned an unsupported record")
        slugs.append(line[2:].split(None, 1)[0])
    for slug in slugs:
        if _project_primary(request, adapters, slug) == request.canonical_root:
            return slug
    return None


def _manifest_component(
    request: EnrollmentRequest, adapters: EnrollmentAdapters
) -> dict[str, Any]:
    path = request.canonical_root / "manifest.yml"
    component = _component("noop", path=str(path))
    try:
        metadata = adapters.filesystem.lstat(path)
    except Exception as exc:
        _record_error(component, exc)
        return component
    if metadata is None:
        component["operation"] = "create"
        return component
    if not stat.S_ISREG(metadata.st_mode):
        component["observations"].append("nonregular")
        return component
    try:
        content = adapters.filesystem.read_bytes(path)
    except Exception as exc:
        _record_error(component, exc)
        return component
    try:
        manifest = yaml.load(content, Loader=_UniqueKeyLoader)
    except yaml.YAMLError:
        component["observations"].append("malformed")
        return component
    if not isinstance(manifest, dict):
        component["observations"].append("invalid_form")
        return component
    workspace = manifest.get("workspace")
    if not isinstance(workspace, dict):
        component["observations"].append("workspace_form_mismatch")
    elif workspace.get("canonical_cwd") != str(request.canonical_root):
        component["observations"].append("root_mismatch")
    return component


def _mapping_component(
    request: EnrollmentRequest, adapters: EnrollmentAdapters
) -> tuple[dict[str, Any], object | None]:
    component = _component("noop", key=_mapping_key(request))
    try:
        value = adapters.config.get(request.hermes_executable, _mapping_key(request))
    except Exception as exc:
        component["operation"] = "reconcile"
        _record_error(component, exc)
        return component, None
    if value is None:
        component["operation"] = "create"
    elif not isinstance(value, str):
        component["operation"] = "reconcile"
        component["observations"].append("target_mismatch")
    else:
        try:
            mapped_primary = _project_primary(request, adapters, value, missing_ok=True)
            if mapped_primary != request.canonical_root:
                component["operation"] = "reconcile"
                component["observations"].append("target_mismatch")
        except Exception as exc:
            component["operation"] = "reconcile"
            _record_error(component, exc)
    return component, value


def _registry_component(
    request: EnrollmentRequest, adapters: EnrollmentAdapters
) -> tuple[dict[str, Any], str | None]:
    component = _component("create", project_slug=request.project_slug)
    try:
        slug = _root_project_slug(request, adapters)
        if slug is not None:
            component["operation"] = "noop"
        return component, slug
    except Exception as exc:
        component["operation"] = "reconcile"
        _record_error(component, exc)
        return component, None


def _has_partial_receipt(components: dict[str, dict[str, Any]]) -> bool:
    return any(component["receipts"] for component in components.values())


def plan_enrollment(request: EnrollmentRequest, adapters: EnrollmentAdapters) -> dict[str, object]:
    request = request.validated()
    mapping, _ = _mapping_component(request, adapters)
    registry, _ = _registry_component(request, adapters)
    components = {
        "config_target": _config_target_component(request, adapters),
        "manifest": _manifest_component(request, adapters),
        "registry": registry,
        "mapping": mapping,
    }
    return {
        "status": "partial" if _has_partial_receipt(components) else "planned",
        "components": components,
        "idempotency_key": request.idempotency_key,
    }


def apply_enrollment(request: EnrollmentRequest, adapters: EnrollmentAdapters) -> dict[str, object]:
    request = request.validated()
    config_target = _config_target_component(request, adapters)
    manifest = _manifest_component(request, adapters)
    mapping, _ = _mapping_component(request, adapters)
    registry, resolved_slug = _registry_component(request, adapters)
    components = {
        "config_target": config_target,
        "manifest": manifest,
        "registry": registry,
        "mapping": mapping,
    }
    changed = False

    if manifest["operation"] == "create":
        try:
            adapters.filesystem.create_exclusive(
                request.canonical_root / "manifest.yml", _manifest_bytes(request)
            )
            changed = True
        except FileExistsError:
            pass
        except Exception as exc:
            _record_error(manifest, exc)
        observed_manifest = _manifest_component(request, adapters)
        manifest["observations"].extend(observed_manifest["observations"])
        manifest["receipts"].extend(observed_manifest["receipts"])

    if registry["operation"] == "create":
        try:
            _run_checked(
                adapters,
                [
                    str(request.hermes_executable),
                    "project",
                    "create",
                    request.project_slug,
                    str(request.canonical_root),
                    "--slug",
                    request.project_slug,
                    "--primary",
                    str(request.canonical_root),
                ],
                "Hermes project create",
            )
            changed = True
        except Exception as exc:
            _record_error(registry, exc)

    try:
        resolved_slug = _root_project_slug(request, adapters)
        if resolved_slug is None:
            _record_error(
                registry,
                EnrollmentError("Hermes project enumeration did not resolve the canonical root"),
            )
    except Exception as exc:
        _record_error(registry, exc)

    if resolved_slug is None:
        mapping["observations"].append("registry_slug_unresolved")
    elif mapping["operation"] != "noop":
        try:
            adapters.config.set(request.hermes_executable, _mapping_key(request), resolved_slug)
            changed = True
            if adapters.config.get(request.hermes_executable, _mapping_key(request)) != resolved_slug:
                raise EnrollmentError("Hermes parent mapping direct readback did not match requested state")
        except Exception as exc:
            _record_error(mapping, exc)
    return {
        "status": "partial" if _has_partial_receipt(components) else "applied" if changed else "noop",
        "components": components,
        "idempotency_key": request.idempotency_key,
    }
