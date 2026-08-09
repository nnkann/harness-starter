from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

_SCHEMA = "harness.l3-manual-candidate-classification.v1"
_DISPOSITIONS = frozenset({"confirm", "revert", "owner-hold"})
_OBSERVATION_FIELDS = {
    "schema",
    "candidate_ref",
    "classification_mode",
    "classifier",
    "disposition",
    "disposition_ref",
    "producer",
    "consumer",
    "authority_effect",
}
_ENVELOPE_FIELDS = {"observation", "observation_sha256"}


def _bounded_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError(f"{field} is invalid")
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _path(state_dir: str | Path, disposition_ref: str) -> Path:
    if isinstance(state_dir, str) and not state_dir:
        raise ValueError("state_dir is required")
    if not isinstance(state_dir, (str, Path)):
        raise TypeError("state_dir must be a path")
    filename = hashlib.sha256(disposition_ref.encode("utf-8")).hexdigest() + ".json"
    return Path(state_dir) / "l3-manual-classifications" / filename


def _validate_observation(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _OBSERVATION_FIELDS:
        raise ValueError("observation fields are not exact")
    candidate_ref = _bounded_text(value["candidate_ref"], "candidate_ref")
    disposition_ref = _bounded_text(value["disposition_ref"], "disposition_ref")
    disposition = value["disposition"]
    if disposition not in _DISPOSITIONS:
        raise ValueError("disposition is unsupported")
    expected = {
        "schema": _SCHEMA,
        "candidate_ref": candidate_ref,
        "classification_mode": "manual",
        "classifier": "Maat",
        "disposition": disposition,
        "disposition_ref": disposition_ref,
        "producer": "ptah",
        "consumer": "maat",
        "authority_effect": "evidence-only",
    }
    if value != expected:
        raise ValueError("observation semantics are invalid")
    return value


def record_manual_classification(
    state_dir: str | Path,
    *,
    candidate_ref: str,
    disposition: str,
    disposition_ref: str,
) -> dict[str, str]:
    candidate_ref = _bounded_text(candidate_ref, "candidate_ref")
    disposition_ref = _bounded_text(disposition_ref, "disposition_ref")
    if disposition not in _DISPOSITIONS:
        raise ValueError("disposition is unsupported")
    observation = {
        "schema": _SCHEMA,
        "candidate_ref": candidate_ref,
        "classification_mode": "manual",
        "classifier": "Maat",
        "disposition": disposition,
        "disposition_ref": disposition_ref,
        "producer": "ptah",
        "consumer": "maat",
        "authority_effect": "evidence-only",
    }
    canonical_observation = _canonical(observation)
    envelope = {
        "observation": observation,
        "observation_sha256": hashlib.sha256(canonical_observation).hexdigest(),
    }
    path = _path(state_dir, disposition_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(_canonical(envelope) + b"\n")
    return observation


def read_manual_classification(
    state_dir: str | Path,
    *,
    expected_candidate_ref: str,
    expected_disposition: str,
    expected_disposition_ref: str,
    expected_consumer: str,
) -> dict[str, Any]:
    expected_candidate_ref = _bounded_text(expected_candidate_ref, "expected_candidate_ref")
    expected_disposition_ref = _bounded_text(
        expected_disposition_ref, "expected_disposition_ref"
    )
    expected_consumer = _bounded_text(expected_consumer, "expected_consumer")
    if expected_disposition not in _DISPOSITIONS:
        raise ValueError("expected_disposition is unsupported")
    path = _path(state_dir, expected_disposition_ref)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError("persisted observation is unavailable") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("persisted observation is not a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            persisted = stream.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not persisted.endswith(b"\n") or persisted.endswith(b"\n\n"):
        raise ValueError("persisted observation is not newline-terminated canonical JSON")
    try:
        envelope = json.loads(persisted.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("persisted observation is malformed") from exc
    if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_FIELDS:
        raise ValueError("envelope fields are not exact")
    observation = _validate_observation(envelope["observation"])
    digest = envelope["observation_sha256"]
    if not isinstance(digest, str) or digest != hashlib.sha256(
        _canonical(observation)
    ).hexdigest():
        raise ValueError("observation digest mismatch")
    if persisted != _canonical(envelope) + b"\n":
        raise ValueError("persisted observation is not canonical")
    if (
        observation["candidate_ref"] != expected_candidate_ref
        or observation["disposition"] != expected_disposition
        or observation["disposition_ref"] != expected_disposition_ref
        or observation["consumer"] != expected_consumer
    ):
        raise ValueError("persisted observation binding mismatch")
    return observation
