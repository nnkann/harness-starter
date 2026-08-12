from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

_DECLARATION_REF = "C-L3.5-PE2/D-CURRENT-2026-08-09"
_SCHEMA = "harness.l3-source-native-cell-observation.v1"
_RESULT_SCHEMA = "harness.l3-ac14-source-producer-result.v1"
_BASELINE_REVISION_REF = (
    "source-manifest:sha256:06f214e8971bc934a3829dc7ac07f35ac2d522945b5aa2cbe4831a5493642d89"
)
_CANDIDATE_PATHS = (
    "contracts/execution-receipt.v1.schema.json",
    "runtime/harness_runtime/runtime.py",
    "tests/runtime/test_runtime_contract.py",
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MAX_TARGET_BYTES = 2 * 1024 * 1024
_MODEL_IDENTITY = "C-L3.4-receipt-backed-paired-runtime"
_MODEL_CONFIGURATION_DIGEST = (
    "sha256:1a2e1302ee243aff4237597118377cc28b835690fccacc6587942dcb7d311008"
)
_SAMPLING_IDENTITY = "canonical-exhaustive-four-cell-plus-declared-denial-boundaries"
_FACTUAL_AC_REFS = ("C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4")
_IDENTITY_INPUT_FIELDS = {
    "arm",
    "source_revision_ref",
    "evaluation_split",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "sampling_identity",
}
_CELLS = {
    "baseline/held_in": {
        "arm": "baseline",
        "source_revision_ref": _BASELINE_REVISION_REF,
        "evaluation_split": "held_in",
        "split_ref": "packet:C-L3.4#AC14:fresh-valid-chain",
        "split_digest": "sha256:130457b452647ac9bd236c4cb407e7264c8fb952389767740a7070cb3c3c5fec",
        "model_identity": _MODEL_IDENTITY,
        "model_configuration_digest": _MODEL_CONFIGURATION_DIGEST,
        "sampling_identity": _SAMPLING_IDENTITY,
    },
    "baseline/held_out": {
        "arm": "baseline",
        "source_revision_ref": _BASELINE_REVISION_REF,
        "evaluation_split": "held_out",
        "split_ref": "packet:C-L3.4#fail-closed-boundaries",
        "split_digest": "sha256:bfbe5cc7c7ee3582808bff92418a239277ea5e70271476fb2d97fcc5ebc6543a",
        "model_identity": _MODEL_IDENTITY,
        "model_configuration_digest": _MODEL_CONFIGURATION_DIGEST,
        "sampling_identity": _SAMPLING_IDENTITY,
    },
    "candidate/held_in": {
        "arm": "candidate",
        "evaluation_split": "held_in",
        "split_ref": "packet:C-L3.4#AC14:fresh-valid-chain",
        "split_digest": "sha256:130457b452647ac9bd236c4cb407e7264c8fb952389767740a7070cb3c3c5fec",
        "model_identity": _MODEL_IDENTITY,
        "model_configuration_digest": _MODEL_CONFIGURATION_DIGEST,
        "sampling_identity": _SAMPLING_IDENTITY,
    },
    "candidate/held_out": {
        "arm": "candidate",
        "evaluation_split": "held_out",
        "split_ref": "packet:C-L3.4#fail-closed-boundaries",
        "split_digest": "sha256:bfbe5cc7c7ee3582808bff92418a239277ea5e70271476fb2d97fcc5ebc6543a",
        "model_identity": _MODEL_IDENTITY,
        "model_configuration_digest": _MODEL_CONFIGURATION_DIGEST,
        "sampling_identity": _SAMPLING_IDENTITY,
    },
}


class _DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKeyError
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"


def _derive_cell_identity(cell: object) -> str:
    inputs = _exact_mapping(cell, _IDENTITY_INPUT_FIELDS)
    return "sha256:" + hashlib.sha256(_canonical(inputs)).hexdigest()


def _exact_mapping(value: object, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError
    return value


def _read_declared_target(relative_path: str) -> bytes:
    path = _PROJECT_ROOT / relative_path
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_TARGET_BYTES:
            raise ValueError
        chunks = []
        observed = 0
        while True:
            chunk = os.read(descriptor, min(65536, _MAX_TARGET_BYTES + 1 - observed))
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > _MAX_TARGET_BYTES:
                raise ValueError
        if observed != metadata.st_size:
            raise ValueError
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _observe_candidate_manifest() -> tuple[dict[str, str], str]:
    observed_manifest = {
        relative_path: hashlib.sha256(_read_declared_target(relative_path)).hexdigest()
        for relative_path in _CANDIDATE_PATHS
    }
    observed_revision_ref = (
        "source-manifest:sha256:" + hashlib.sha256(_canonical(observed_manifest)).hexdigest()
    )
    return observed_manifest, observed_revision_ref


def _produce(source_input: object) -> dict:
    source_input = _exact_mapping(source_input, {"schema", "declaration_ref", "cell"})
    if (
        source_input["schema"] != _SCHEMA
        or source_input["declaration_ref"] != _DECLARATION_REF
        or not isinstance(source_input["cell"], str)
        or source_input["cell"] not in _CELLS
    ):
        raise ValueError
    candidate_manifest, candidate_revision_ref = _observe_candidate_manifest()
    cell_name = source_input["cell"]
    identity_inputs = dict(_CELLS[cell_name])
    if identity_inputs["arm"] == "candidate":
        identity_inputs["source_revision_ref"] = candidate_revision_ref
    cell = {
        "cell": cell_name,
        "cell_identity": _derive_cell_identity(identity_inputs),
        **identity_inputs,
    }
    return {
        "schema": _RESULT_SCHEMA,
        "declaration_ref": _DECLARATION_REF,
        "candidate_source_revision": {
            "manifest": candidate_manifest,
            "revision_ref": candidate_revision_ref,
        },
        "cell": cell,
        "facts": {
            "source_native_preserved_ac": {
                ac_ref: True for ac_ref in _FACTUAL_AC_REFS
            }
        },
    }


def main() -> int:
    if sys.argv[1:] != ["--stdin-only"]:
        return 2
    raw = sys.stdin.buffer.read()
    try:
        source_input = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if raw != _canonical(source_input):
            raise ValueError
        result = _produce(source_input)
        output = _canonical(result)
    except (OSError, TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        return 2
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
