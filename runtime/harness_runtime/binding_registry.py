"""Canonical source-identity binding registry with isolated receipt readback."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path

BINDING_SCHEMA_NAME = "harness.runtime.canonical-binding.v1"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PROJECT_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class BindingResolutionError(ValueError):
    """A source identity cannot produce one authoritative canonical binding."""


def binding_schema_text() -> str:
    return resources.files("contracts").joinpath("canonical-binding.v1.schema.json").read_text(encoding="utf-8")


def _require_identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise BindingResolutionError(f"{name} identity is invalid")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class BindingRequest:
    platform: str
    guild_id: str
    parent_channel_id: str
    thread_id: str
    profile: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _require_identifier(value, name)

    def identity(self) -> dict[str, str]:
        return asdict(self)

    def key(self) -> str:
        return _canonical_json(self.identity())


@dataclass(frozen=True, slots=True)
class BindingResult:
    project_slug: str
    canonical_cwd: str
    write_scope: str
    binding_revision: str
    source_ref: str

    def normalized(self) -> BindingResult:
        if not isinstance(self.project_slug, str) or not _PROJECT_SLUG_RE.fullmatch(self.project_slug):
            raise BindingResolutionError("project_slug is invalid")
        if not isinstance(self.canonical_cwd, str):
            raise BindingResolutionError("canonical_cwd is invalid")
        candidate = Path(self.canonical_cwd).expanduser()
        if not candidate.is_absolute():
            raise BindingResolutionError("canonical_cwd must be absolute")
        normalized = candidate.resolve()
        if str(candidate) != str(normalized):
            raise BindingResolutionError("canonical_cwd is not canonical")
        if not isinstance(self.write_scope, str) or not self.write_scope or Path(self.write_scope).is_absolute():
            raise BindingResolutionError("write_scope is invalid")
        if any(part in {"", ".", ".."} for part in Path(self.write_scope).parts):
            raise BindingResolutionError("write_scope is invalid")
        _require_identifier(self.binding_revision, "binding_revision")
        if not isinstance(self.source_ref, str) or not self.source_ref:
            raise BindingResolutionError("source_ref is invalid")
        return BindingResult(
            project_slug=self.project_slug,
            canonical_cwd=str(normalized),
            write_scope=Path(self.write_scope).as_posix(),
            binding_revision=self.binding_revision,
            source_ref=self.source_ref,
        )

    def fields(self) -> dict[str, str]:
        return asdict(self.normalized())


@dataclass(frozen=True, slots=True)
class BindingRecord:
    request: BindingRequest
    result: BindingResult


@dataclass(frozen=True, slots=True)
class BindingReceipt:
    resolver_revision: str
    binding_digest: str
    session_key: str
    consumer_readback: dict[str, str]


@dataclass(frozen=True, slots=True)
class BindingResolution:
    result: BindingResult
    receipt: BindingReceipt


def _temporary_state_root() -> Path:
    root = os.environ.get("HARNESS_STATE_DIR")
    if not root:
        raise BindingResolutionError("HARNESS_STATE_DIR is required for binding receipt storage")
    return Path(root).expanduser().resolve()


class CanonicalBindingRegistry:
    """Registry authority is only the explicit source-identity record set."""

    def __init__(self, records: list[BindingRecord], *, resolver_revision: str) -> None:
        self._resolver_revision = _require_identifier(resolver_revision, "resolver_revision")
        self._records: dict[str, list[BindingResult]] = {}
        for record in records:
            if not isinstance(record, BindingRecord):
                raise BindingResolutionError("binding record is invalid")
            self._records.setdefault(record.request.key(), []).append(record.result.normalized())

    def resolve(self, request: BindingRequest) -> BindingResolution:
        if not isinstance(request, BindingRequest):
            raise BindingResolutionError("source identity is invalid")
        matches = self._records.get(request.key(), [])
        if not matches:
            raise BindingResolutionError("source identity is unknown")
        if len(matches) != 1:
            raise BindingResolutionError("source identity is ambiguous")
        result = matches[0]
        digest_material = {
            "schema": BINDING_SCHEMA_NAME,
            "resolver_revision": self._resolver_revision,
            "identity": request.identity(),
            "result": result.fields(),
        }
        binding_digest = hashlib.sha256(_canonical_json(digest_material).encode("utf-8")).hexdigest()
        session_key = "binding-" + hashlib.sha256(request.key().encode("utf-8")).hexdigest()
        return BindingResolution(
            result=result,
            receipt=BindingReceipt(
                resolver_revision=self._resolver_revision,
                binding_digest=binding_digest,
                session_key=session_key,
                consumer_readback=request.identity(),
            ),
        )

    def persist_receipt(self, resolution: BindingResolution) -> str:
        if not isinstance(resolution, BindingResolution):
            raise BindingResolutionError("binding resolution is invalid")
        root = _temporary_state_root() / "binding-receipts"
        path = root / f"{resolution.receipt.session_key}.json"
        payload = {
            "schema": BINDING_SCHEMA_NAME,
            "result": resolution.result.fields(),
            "receipt": asdict(resolution.receipt),
        }
        root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(_canonical_json(payload) + "\n", encoding="utf-8")
        temporary.replace(path)
        return str(path)

    def readback(self, request: BindingRequest, session_key: str, binding_digest: str) -> BindingResolution:
        if not isinstance(request, BindingRequest):
            raise BindingResolutionError("consumer identity is invalid")
        expected = self.resolve(request)
        if session_key != expected.receipt.session_key or binding_digest != expected.receipt.binding_digest:
            raise BindingResolutionError("receipt identity or digest does not match registry")
        path = _temporary_state_root() / "binding-receipts" / f"{session_key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BindingResolutionError("binding receipt readback is unavailable") from exc
        if payload.get("schema") != BINDING_SCHEMA_NAME:
            raise BindingResolutionError("binding receipt schema is invalid")
        if payload.get("result") != expected.result.fields() or payload.get("receipt") != asdict(expected.receipt):
            raise BindingResolutionError("binding receipt does not match registry")
        return expected
