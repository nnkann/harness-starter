from __future__ import annotations

import json
import re
import sys

_SCHEMA = "harness.l3-ac14-source-observation.v1"
_EVALUATOR_IDENTITY = "maat:C-L3.4:AC14-direct-runtime-evaluator"
_EVALUATOR_CONFIGURATION_DIGEST = (
    "sha256:5da3457d462cdfe75b792ed4b48dea7d872eae9ce66aba894b38442bfcb83994"
)
_RESULT_CONTRACT_REF = "harness.runtime.execution-receipt.v1"
_RESULT_CONTRACT_DIGEST = (
    "sha256:928954a0f4ac84768e14b752386a6a6de2ae03fe43ac8e34d56384b941f305cb"
)
_SHA256_IDENTITY = re.compile(r"sha256:[0-9a-f]{64}")
_SOURCE_REVISION_IDENTITY = re.compile(r"source-manifest:sha256:[0-9a-f]{64}")
_TOP_LEVEL_FIELDS = {"schema", "binding", "facts", "owner_holds", "evidence_refs"}
_BINDING_FIELDS = {
    "candidate_ref",
    "candidate_admission_digest",
    "pair_plan_digest",
    "arm",
    "evaluation_split",
    "source_revision_ref",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "evaluator_identity",
    "evaluator_configuration_digest",
    "result_contract_ref",
    "result_contract_digest",
    "target_ac_ref",
}
_OBSERVED_AC_REFS = {"C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4"}
_OWNER_HOLDS = {
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "runtime/harness_runtime/runtime.py#_construct_l35_source_observation",
            "status": "no_value_and_owner_hold",
        }
        for number in (2, 6, 9)
    },
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "runtime/harness_runtime/runtime.py#paired_readback",
            "status": "no_value_and_owner_hold",
        }
        for number in (5, 7, 8, 10, 11)
    },
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "independent-verifier:anubis:C-L3.4",
            "status": "no_value_and_owner_hold",
        }
        for number in (12, 13)
    },
    "C-L3.4:AC14": {
        "owner_ref": _EVALUATOR_IDENTITY,
        "status": "no_value_and_owner_hold",
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


def _exact_mapping(value: object, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError
    return value


def _bounded_text(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or _SHA256_IDENTITY.fullmatch(value) is None:
        raise ValueError
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError
    return value


def _validate(observation: object) -> dict:
    observation = _exact_mapping(observation, _TOP_LEVEL_FIELDS)
    if observation["schema"] != _SCHEMA:
        raise ValueError

    binding = _exact_mapping(observation["binding"], _BINDING_FIELDS)
    for field in ("candidate_ref", "split_ref", "model_identity"):
        _bounded_text(binding[field])
    for field in (
        "candidate_admission_digest",
        "pair_plan_digest",
        "split_digest",
        "model_configuration_digest",
    ):
        _digest(binding[field])
    source_revision_ref = binding["source_revision_ref"]
    if (
        not isinstance(source_revision_ref, str)
        or _SOURCE_REVISION_IDENTITY.fullmatch(source_revision_ref) is None
    ):
        raise ValueError
    if binding["arm"] not in {"baseline", "candidate"}:
        raise ValueError
    if binding["evaluation_split"] not in {"held_in", "held_out"}:
        raise ValueError
    if binding["evaluator_identity"] != _EVALUATOR_IDENTITY:
        raise ValueError
    if binding["evaluator_configuration_digest"] != _EVALUATOR_CONFIGURATION_DIGEST:
        raise ValueError
    if binding["result_contract_ref"] != _RESULT_CONTRACT_REF:
        raise ValueError
    if binding["result_contract_digest"] != _RESULT_CONTRACT_DIGEST:
        raise ValueError
    if binding["target_ac_ref"] != "AC14":
        raise ValueError

    facts = _exact_mapping(observation["facts"], {"preserved_ac"})
    observed = _exact_mapping(facts["preserved_ac"], _OBSERVED_AC_REFS)
    for value in observed.values():
        _boolean(value)

    owner_holds = _exact_mapping(observation["owner_holds"], set(_OWNER_HOLDS))
    for ac_ref, expected in _OWNER_HOLDS.items():
        hold = _exact_mapping(owner_holds[ac_ref], {"owner_ref", "status"})
        if hold != expected:
            raise ValueError
    if set(observed) & set(owner_holds):
        raise ValueError

    evidence_refs = observation["evidence_refs"]
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError
    for evidence_ref in evidence_refs:
        _bounded_text(evidence_ref)
    if evidence_refs != sorted(evidence_refs) or len(set(evidence_refs)) != len(
        evidence_refs
    ):
        raise ValueError
    return observation


def _evaluate(observation: dict) -> dict:
    return {
        "evaluator_identity": _EVALUATOR_IDENTITY,
        "evaluator_configuration_digest": _EVALUATOR_CONFIGURATION_DIGEST,
        "result_contract_ref": _RESULT_CONTRACT_REF,
        "result_contract_digest": _RESULT_CONTRACT_DIGEST,
        "evaluation_state": "partial_unresolved",
        "evaluated_phase": "phase_1_source_observation",
        "observed_ac_values": dict(observation["facts"]["preserved_ac"]),
        "unresolved_inputs": {
            ac_ref: dict(hold) for ac_ref, hold in observation["owner_holds"].items()
        },
    }


def main() -> int:
    if len(sys.argv) != 1:
        return 2
    raw = sys.stdin.buffer.read()
    try:
        text = raw.decode("utf-8", errors="strict")
        observation = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if raw != _canonical(observation):
            raise ValueError
        result = _evaluate(_validate(observation))
        output = _canonical(result)
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        return 2
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
