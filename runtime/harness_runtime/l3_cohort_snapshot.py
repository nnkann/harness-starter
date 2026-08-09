from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml


class _DuplicateKeyError(yaml.YAMLError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise _DuplicateKeyError
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def serialize_snapshot(snapshot: dict) -> bytes:
    return _canonical(snapshot) + b"\n"


class CohortCompilerError(ValueError):
    pass


_POLICY_FIELDS = {
    ("schema",): "harness.l3-enrollment-policy.v1",
    ("policy_id",): "C-L3.0b-R2-dynamic-enrollment-policy-authority",
    ("membership", "universe"): "all_active_native_records_at_cutoff",
    ("membership", "source_commands"): [
        "env -u HERMES_HOME hermes project list",
        "env -u HERMES_HOME hermes project show <native_slug>",
    ],
    ("membership", "fixed_roster_or_allowlist"): "prohibited",
    ("membership", "per_project_exceptions"): "prohibited",
    ("cutoff", "format"): "RFC3339_UTC",
    ("cutoff", "rule"): "immutable_caller_supplied_observation_time",
    ("identity", "stable"): ["project_id", "canonical_native_primary_root"],
    ("identity", "canonical_native_primary_root"): "native_show_primary",
    ("identity", "manifest_identity"): "manifest.project_slug",
    ("identity", "deterministic_order"): [
        "project_id",
        "canonical_native_primary_root",
        "native_slug",
        "evaluation_slug",
    ],
    ("alias", "evaluation_slug"): "manifest.project_slug",
    ("alias", "locator_alias"): "native_slug",
    ("alias", "root_agrees_name_differs_gap"): "registry_alias_mismatch",
    ("alias", "behavior"): "preserve_both_without_rename_reregister_or_exclusion",
    ("manifest", "source"): "<canonical_native_primary_root>/manifest.yml",
    ("manifest", "required"): ["schema", "project_slug", "workspace.canonical_cwd"],
    ("manifest", "schema"): "harness.project-manifest.v2",
    ("manifest", "root_rule"): "workspace.canonical_cwd_equals_canonical_native_primary_root",
    ("manifest", "invalid_record_behavior"): "retain_as_member_local_HOLD_GAP",
    ("conflicts", "keys"): [
        "project_id",
        "canonical_native_primary_root",
        "manifest.project_slug",
    ],
    ("conflicts", "classification"): "HOLD_GAP",
    ("conflicts", "behavior"): "retain_every_conflicting_native_record",
    ("classifications", "baseline_ready", "value"): "baseline_ready",
    ("classifications", "baseline_ready", "reason"): "source_native_active_record",
    ("classifications", "baseline_ready", "evidence_source"): "native_project_registry",
    ("classifications", "non_applicable_approved", "value"): "non_applicable-approved",
    ("classifications", "non_applicable_approved", "approval_reference"): "required_explicit",
    ("classifications", "non_applicable_approved", "candidate_non_regression_condition"): "required",
    ("classifications", "non_applicable_approved", "auto_generation"): "prohibited",
    ("classifications", "held", "value"): "HOLD_GAP",
    ("serialization", "policy_revision"): "sha256_exact_policy_bytes",
    ("serialization", "canonical_json", "sort_keys"): True,
    ("serialization", "canonical_json", "separators"): [",", ":"],
    ("serialization", "canonical_json", "ensure_ascii"): False,
    ("serialization", "canonical_json", "newline_terminated"): True,
    ("serialization", "membership_digest", "algorithm"): "sha256",
    ("serialization", "membership_digest", "input"): [
        "policy_revision",
        "cutoff",
        "deterministically_ordered_member_identity_projections",
    ],
    ("compiler", "access"): "read_only",
    ("compiler", "allowed_sources"): [
        "native_registry",
        "native_config",
        "manifests",
        "repositories",
    ],
    ("compiler", "mutation_prohibited"): [
        "native_registry",
        "native_config",
        "manifests",
        "repositories",
        "channel_bindings",
        "receipts",
        "scheduled_consumers",
        "task_pointers",
        "worktrees",
    ],
}
_UTC_CUTOFF = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
_NON_REGRESSION_CONDITION = "candidate_does_not_reduce_required_membership"


def _validate_policy(policy: object) -> None:
    for path, expected in _POLICY_FIELDS.items():
        value = policy
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value != expected:
            raise CohortCompilerError(
                "enrollment policy semantics are incompatible: policy field "
                + ".".join(path)
            )


def _run_native_hermes(args: list[str]) -> str:
    environment = os.environ.copy()
    environment.pop("HERMES_HOME", None)
    result = subprocess.run(
        ["hermes", *args],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result.stdout


def collect_native_records(
    *,
    run: Callable[[list[str]], str] = _run_native_hermes,
    read_manifest: Callable[[Path], bytes] | None = None,
) -> list[dict]:
    read_manifest = read_manifest or Path.read_bytes
    listed = []
    for line in run(["project", "list"]).splitlines():
        if not line.strip():
            continue
        match = re.match(r"^[* ]\s+([a-z0-9][a-z0-9_-]*)\s+.*\[\d+ folder\(s\)\]$", line)
        fallback = re.match(r"^[* ]\s+([a-z0-9][a-z0-9_-]*)\b", line)
        if fallback is None:
            raise CohortCompilerError("native project list record identity is incomplete")
        listed.append((fallback.group(1), [] if match else ["registry_list_malformed"]))
    slug_counts = Counter(slug for slug, _ in listed)
    records = []
    for slug, registry_gaps in listed:
        shown = run(["project", "show", slug])
        identities = re.findall(rf"^{re.escape(slug)}\s+\[([^]]+)\]", shown, re.MULTILINE)
        primaries = re.findall(r"^\s+primary:\s+(.+)$", shown, re.MULTILINE)
        if not identities or not primaries:
            raise CohortCompilerError(
                f"native project show identity is incomplete for {slug}"
            )
        if len(identities) > 1 or len(primaries) > 1:
            registry_gaps.append("registry_show_duplicate_field")
        if slug_counts[slug] > 1:
            registry_gaps.append("duplicate_registry_record")
        root = primaries[0].strip()
        manifest_path = Path(root) / "manifest.yml"
        try:
            manifest_bytes = read_manifest(manifest_path)
        except FileNotFoundError:
            manifest_bytes = None
        records.append(
            {
                "project_id": identities[0],
                "native_slug": slug,
                "primary_root": root,
                "manifest_bytes": manifest_bytes,
                "registry_gaps": registry_gaps,
            }
        )
    return records


def compile_snapshot(
    *,
    policy_path: str | Path,
    cutoff: str,
    native_records: list[dict],
    non_applicable_approvals: dict[str, dict] | None = None,
) -> dict:
    source = Path(policy_path).resolve()
    policy_bytes = source.read_bytes()
    try:
        policy = yaml.load(policy_bytes, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise CohortCompilerError("enrollment policy is malformed") from exc
    _validate_policy(policy)
    if not isinstance(cutoff, str) or _UTC_CUTOFF.fullmatch(cutoff) is None:
        raise CohortCompilerError("cutoff must be RFC3339 UTC")
    try:
        datetime.fromisoformat(cutoff.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise CohortCompilerError("cutoff must be RFC3339 UTC") from exc
    approvals = non_applicable_approvals or {}
    for project_id, approval in approvals.items():
        if not isinstance(approval, dict) or not isinstance(
            approval.get("approval_reference"), str
        ) or not approval["approval_reference"].strip() or approval.get(
            "candidate_non_regression_condition"
        ) != _NON_REGRESSION_CONDITION:
            raise CohortCompilerError(
                f"non-applicable approval is incomplete for {project_id}"
            )
    policy_revision = "sha256:" + hashlib.sha256(policy_bytes).hexdigest()
    members = []
    for record in native_records:
        identity = tuple(record.get(key) for key in ("project_id", "native_slug", "primary_root"))
        if not all(isinstance(value, str) and value.strip() for value in identity):
            raise CohortCompilerError("native record identity is incomplete")
        manifest_bytes = record.get("manifest_bytes")
        gaps = list(record.get("registry_gaps", []))
        if manifest_bytes is None:
            manifest = None
            gaps.append("manifest_missing")
        else:
            try:
                manifest = yaml.load(manifest_bytes, Loader=_UniqueKeyLoader)
            except _DuplicateKeyError:
                manifest = None
                gaps.append("manifest_duplicate_key")
            except yaml.YAMLError:
                manifest = None
                gaps.append("manifest_malformed")
            else:
                workspace = manifest.get("workspace") if isinstance(manifest, dict) else None
                evaluation_slug = manifest.get("project_slug") if isinstance(manifest, dict) else None
                canonical_cwd = workspace.get("canonical_cwd") if isinstance(workspace, dict) else None
                if not isinstance(manifest, dict) or manifest.get("schema") != "harness.project-manifest.v2":
                    gaps.append("manifest_schema_invalid")
                elif not all(
                    isinstance(value, str) and value.strip()
                    for value in (evaluation_slug, canonical_cwd)
                ):
                    gaps.append("manifest_missing_required_fields")
                elif canonical_cwd != record["primary_root"]:
                    gaps.append("canonical_root_mismatch")
                elif record["native_slug"] != evaluation_slug:
                    gaps.append("registry_alias_mismatch")
        evaluation_slug = manifest.get("project_slug") if isinstance(manifest, dict) else None
        held = any(gap != "registry_alias_mismatch" for gap in gaps)
        member = {
                "project_id": record["project_id"],
                "native_slug": record["native_slug"],
                "evaluation_slug": evaluation_slug,
                "primary_root": record["primary_root"],
                "classification": "HOLD_GAP" if held else "baseline_ready",
                "reason": (
                    gaps[0]
                    if held
                    else "source_native_active_record"
                ),
                "gaps": gaps,
                "evidence": [
                    {
                        "source": "native_project_registry",
                        "project_id": record["project_id"],
                        "native_slug": record["native_slug"],
                        "primary_root": record["primary_root"],
                        "digest": "sha256:" + hashlib.sha256(_canonical({
                            "project_id": record["project_id"],
                            "native_slug": record["native_slug"],
                            "primary_root": record["primary_root"],
                        })).hexdigest(),
                    },
                    {
                        "source": "canonical_manifest",
                        "path": str(Path(record["primary_root"]) / "manifest.yml"),
                        "digest": (
                            "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
                            if manifest_bytes is not None
                            else None
                        ),
                    },
                ],
            }
        members.append(member)
    unknown_approvals = set(approvals) - {member["project_id"] for member in members}
    if unknown_approvals:
        raise CohortCompilerError("non-applicable approval does not match a native member")
    conflict_fields = (
        ("project_id", "duplicate_project_id"),
        ("primary_root", "duplicate_primary_root"),
        ("evaluation_slug", "duplicate_manifest_identity"),
    )
    for field, gap in conflict_fields:
        counts = Counter(member[field] for member in members if member[field] is not None)
        for member in members:
            if member[field] is not None and counts[member[field]] > 1:
                member["gaps"].append(gap)
    for member in members:
        hold_gaps = [gap for gap in member["gaps"] if gap != "registry_alias_mismatch"]
        if hold_gaps:
            member["classification"] = "HOLD_GAP"
            member["reason"] = hold_gaps[0]
    for member in members:
        approval = approvals.get(member["project_id"])
        if approval is None:
            continue
        if member["classification"] == "HOLD_GAP":
            raise CohortCompilerError(
                "non-applicable approval cannot target final HOLD_GAP for "
                + member["project_id"]
            )
        member.update(
            classification="non_applicable-approved",
            reason="explicit_non_applicable_approval",
            approval_reference=approval["approval_reference"],
            candidate_non_regression_condition=_NON_REGRESSION_CONDITION,
        )
    members.sort(
        key=lambda member: (
            member["project_id"],
            member["primary_root"],
            member["native_slug"],
            member["evaluation_slug"] or "",
        )
    )
    identity_fields = ("project_id", "primary_root", "native_slug", "evaluation_slug")
    digest_input = {
        "policy_revision": policy_revision,
        "cutoff": cutoff,
        "members": [
            {field: member[field] for field in identity_fields} for member in members
        ],
    }
    return {
        "schema": "harness.l3-cohort-snapshot.v1",
        "enrollment_policy": {
            "source": str(source),
            "revision": policy_revision,
        },
        "cutoff": cutoff,
        "cohort_members": members,
        "membership_digest": "sha256:"
        + hashlib.sha256(_canonical(digest_input)).hexdigest(),
    }


def compile_live_snapshot(
    *,
    policy_path: str | Path,
    cutoff: str,
    run: Callable[[list[str]], str] = _run_native_hermes,
    read_manifest: Callable[[Path], bytes] | None = None,
) -> dict:
    return compile_snapshot(
        policy_path=policy_path,
        cutoff=cutoff,
        native_records=collect_native_records(run=run, read_manifest=read_manifest),
    )
