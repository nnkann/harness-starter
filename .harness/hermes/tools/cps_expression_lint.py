#!/usr/bin/env python3
"""Validate ordered CPS expression and adaptive actor-binding packets.

The linter is intentionally small and dependency-light. It accepts JSON by
default, and YAML only when PyYAML is available. It enforces the contract in
`.harness/hermes/reference/ops/cps-flow-audit.yaml` closely enough to catch the
failure classes from the CPS dogfood sessions: unordered many-to-many P/S,
review/audit conflation, fixed role checklist actor calls, and missing actor
binding rationale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_JUDGMENT_PREFIXES = ("review.", "audit.")
REQUIRED_STEP_FIELDS = [
    "order",
    "p",
    "s",
    "role_in_expression",
    "judgment_function",
    "review_or_audit",
    "actor_binding",
    "consumes",
    "emits",
]
REQUIRED_BINDING_FIELDS = [
    "mode",
    "candidate_pool",
    "selected",
    "selection_basis",
    "alternatives_considered",
    "rebind_triggers",
]
BINDING_BASIS_ALLOWED = {
    "cps_expression_step",
    "judgment_function",
    "evidence_obligation",
    "current_risk",
    "available_context",
    "source_ref_authority",
    "prior_outcome_trace",
    "owner_boundary",
    "tool_or_profile_availability",
}
REBIND_ALLOWED = {
    "missing_evidence",
    "new_security_signal",
    "owner_boundary_detected",
    "failed_review",
    "failed_audit",
    "external_fact_required",
    "context_stale",
    "source_ref_conflict",
    "actor_unavailable",
    "blocked_owner_action",
}


def _load_packet(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"YAML input requires PyYAML; use JSON or install PyYAML. ({exc})")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit("Top-level packet must be an object")
    return data


def _as_nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _selected_actor(binding: dict[str, Any]) -> str | None:
    selected = binding.get("selected")
    if isinstance(selected, dict):
        actor = selected.get("actor")
        return str(actor) if actor else None
    if isinstance(selected, str):
        return selected
    return None


def validate(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not packet.get("root_goal_id"):
        errors.append("root_goal_id is required")
    if not packet.get("flow_graph_id"):
        errors.append("flow_graph_id is required")
    if not packet.get("root_goal"):
        errors.append("root_goal is required")
    if not _as_nonempty_list(packet.get("source_refs")):
        errors.append("source_refs must be a non-empty list")

    c = packet.get("c")
    if not isinstance(c, dict) or not c.get("id") or not c.get("concern"):
        errors.append("c.id and c.concern are required")

    raw_steps = packet.get("flow_expression")
    if not isinstance(raw_steps, list) or not raw_steps:
        errors.append("flow_expression must be a non-empty ordered list")
        return sorted(errors)
    steps: list[Any] = raw_steps

    orders: list[int] = []
    seen_pairs: dict[tuple[str, str], int] = {}
    saw_review = False
    saw_audit = False

    for idx, step in enumerate(steps):
        loc = f"flow_expression[{idx}]"
        if not isinstance(step, dict):
            errors.append(f"{loc} must be an object")
            continue
        for field in REQUIRED_STEP_FIELDS:
            if field not in step:
                errors.append(f"{loc}.{field} is required")
        order = step.get("order")
        if not isinstance(order, int):
            errors.append(f"{loc}.order must be an integer")
        else:
            orders.append(order)
        if not _as_nonempty_list(step.get("p")):
            errors.append(f"{loc}.p must be a non-empty list")
        if not _as_nonempty_list(step.get("s")):
            errors.append(f"{loc}.s must be a non-empty list")
        if not isinstance(step.get("consumes"), list):
            errors.append(f"{loc}.consumes must be a list")
        if not _as_nonempty_list(step.get("emits")):
            errors.append(f"{loc}.emits must be a non-empty list")

        judgment = str(step.get("judgment_function") or "")
        if not judgment.startswith(ALLOWED_JUDGMENT_PREFIXES):
            errors.append(f"{loc}.judgment_function must start with review. or audit.")
        saw_review = saw_review or judgment.startswith("review.")
        saw_audit = saw_audit or judgment.startswith("audit.")

        review_or_audit = step.get("review_or_audit")
        if not isinstance(review_or_audit, dict) or not review_or_audit.get("type"):
            errors.append(f"{loc}.review_or_audit.type is required")
        elif str(review_or_audit.get("type")) != judgment:
            errors.append(f"{loc}.review_or_audit.type must match judgment_function")

        for p in step.get("p") or []:
            for s in step.get("s") or []:
                key = (str(p), str(s))
                seen_pairs[key] = seen_pairs.get(key, 0) + 1

        binding = step.get("actor_binding")
        if not isinstance(binding, dict):
            errors.append(f"{loc}.actor_binding must be an object")
            continue
        for field in REQUIRED_BINDING_FIELDS:
            if field not in binding:
                errors.append(f"{loc}.actor_binding.{field} is required")
        pool = binding.get("candidate_pool")
        if not _as_nonempty_list(pool) or len(pool) < 2:
            errors.append(f"{loc}.actor_binding.candidate_pool must include at least two candidates")
        selected = _selected_actor(binding)
        if not selected:
            errors.append(f"{loc}.actor_binding.selected.actor is required")
        elif isinstance(pool, list) and selected not in [str(x) for x in pool]:
            errors.append(f"{loc}.actor_binding.selected actor must be present in candidate_pool")
        basis = binding.get("selection_basis")
        if not _as_nonempty_list(basis):
            errors.append(f"{loc}.actor_binding.selection_basis must be non-empty")
        else:
            unknown = sorted(set(map(str, basis)) - BINDING_BASIS_ALLOWED)
            if unknown:
                errors.append(f"{loc}.actor_binding.selection_basis has unknown values: {unknown}")
        alternatives = binding.get("alternatives_considered")
        if not _as_nonempty_list(alternatives):
            errors.append(f"{loc}.actor_binding.alternatives_considered must be non-empty")
        triggers = binding.get("rebind_triggers")
        if not _as_nonempty_list(triggers):
            errors.append(f"{loc}.actor_binding.rebind_triggers must be non-empty")
        else:
            unknown = sorted(set(map(str, triggers)) - REBIND_ALLOWED)
            if unknown:
                errors.append(f"{loc}.actor_binding.rebind_triggers has unknown values: {unknown}")

    if orders != sorted(orders) or len(set(orders)) != len(orders):
        errors.append("flow_expression.order values must be unique and strictly ascending")
    if not saw_review:
        errors.append("at least one review.* step is required")
    if not saw_audit:
        errors.append("at least one audit.* step is required")
    if all(count == 1 for count in seen_pairs.values()):
        # This is only a warning-level modelling smell, but this linter is used
        # for CPS design packets where order/repetition should be explicit.
        errors.append("no repeated P/S pair found; confirm this is not a 1:1/static mapping packet")
    return sorted(errors)


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a Harness CPS expression packet.")
    ap.add_argument("packet", type=Path)
    ap.add_argument("--json", action="store_true", help="Emit JSON result")
    args = ap.parse_args()

    packet = _load_packet(args.packet)
    errors = validate(packet)
    result = {"ok": not errors, "error_count": len(errors), "errors": errors, "packet": str(args.packet)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("ok" if not errors else "fail")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
