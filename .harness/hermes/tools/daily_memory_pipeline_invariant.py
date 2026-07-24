from __future__ import annotations

import re
from typing import Any, Mapping, Type

LAYER_IDS = frozenset({"harness_brain", "honcho", "gbrain"})
REF_KEYS = ("canonical_source_ref", "pointer_ref", "canonical_index_ref")
REVISION_KEYS = ("canonical_revision", "canonical_index_revision")
BOOLEAN_KEYS = ("canonical_index_aligned", "verified_outcome_eligible")
_SHA256_REVISION = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def validate_layers(layers: Any, error_type: Type[ValueError] = ValueError) -> None:
    if not isinstance(layers, list) or len(layers) != len(LAYER_IDS):
        raise error_type("layers must contain the exact pipeline layer set")
    if any(not isinstance(layer, Mapping) for layer in layers):
        raise error_type("layer must be an object")
    layer_ids = [layer.get("layer_id") for layer in layers]
    if len(set(layer_ids)) != len(layer_ids) or set(layer_ids) != LAYER_IDS:
        raise error_type("layers must contain the exact pipeline layer set")

    for layer in layers:
        availability = layer.get("availability")
        if availability not in {"available", "unavailable"}:
            raise error_type("invalid layer availability")
        available = availability == "available"
        for key in REF_KEYS:
            value = layer.get(key)
            if available:
                if not isinstance(value, str) or not value or len(value) > 256:
                    raise error_type(f"invalid available {key}")
            elif value is not None:
                raise error_type(f"invalid unavailable {key}")
        for key in REVISION_KEYS:
            value = layer.get(key)
            if available:
                if not isinstance(value, str) or _SHA256_REVISION.fullmatch(value) is None:
                    raise error_type(f"invalid available {key}")
            elif value is not None:
                raise error_type(f"invalid unavailable {key}")
        pointer_digest = layer.get("pointer_digest")
        if available:
            if not isinstance(pointer_digest, str) or _SHA256_DIGEST.fullmatch(pointer_digest) is None:
                raise error_type("invalid available pointer_digest")
            if layer.get("pointer_integrity") not in {"valid", "invalid"}:
                raise error_type("invalid available pointer_integrity")
        elif pointer_digest is not None or layer.get("pointer_integrity") != "unknown":
            raise error_type("invalid unavailable pointer state")
        for key in BOOLEAN_KEYS:
            value = layer.get(key)
            if (available and type(value) is not bool) or (not available and value is not None):
                raise error_type(f"invalid {availability} {key}")
