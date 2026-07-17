#!/usr/bin/env python3
"""Reference-only CPS runtime source navigator."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "harness.cps_runtime_navigation_receipt.v1"
TARGETS = {"source", "contract", "working_graph", "runtime", "test", "receipt"}
SEMANTIC_PROVENANCE_FIELDS = {
    "canonical_source_locator", "canonical_source_readback", "current_source_revision",
    "current_content_hash", "canonical_section", "semantic_field_definition_coverage",
}
ANCHOR_SEMANTIC_FIELDS = {
    "schema", "cluster_key", "source_id", "source_revision", "content_hash",
    "C.shape", "C.boundary_hint", "C.domain", "P_order[].id", "P_order[].statement",
    "S_mapping[].id", "S_mapping[].targets", "S_mapping[].operator", "AC_anchor",
    "goal_state", "source_refs", "gbrain_pointers", "lifecycle", "freshness",
    "expires_at", "supersedes",
}
SEMANTIC_HOLD = {"status": "hold", "failure_codes": ["HOLD_UNMAPPED_SEMANTIC_FIELD"]}


def _semantic_leaves(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        leaves: set[str] = set()
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            leaves.update(_semantic_leaves(item, path))
        return leaves
    if isinstance(value, list):
        if not value or all(not isinstance(item, (dict, list)) for item in value):
            return {prefix}
        leaves: set[str] = set()
        for item in value:
            leaves.update(_semantic_leaves(item, f"{prefix}[]"))
        return leaves
    return {prefix}


def _anchor_definition_refs(locator: Path, text: str) -> tuple[str, dict[str, str]] | None:
    lines = text.splitlines()
    heading = next((index for index, line in enumerate(lines) if re.fullmatch(r"##\s+(?:\d+\.\s+)?CPS Anchor Contract", line)), None)
    if heading is None:
        return None
    fence = next((index for index in range(heading + 1, len(lines)) if lines[index].strip() == "```yaml"), None)
    if fence is None:
        return None
    closing = next((index for index in range(fence + 1, len(lines)) if lines[index].strip() == "```"), None)
    if closing is None:
        return None
    refs: dict[str, str] = {}
    parent = ""
    scalar_lists = {"AC_anchor"}
    for index in range(fence + 1, closing):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or ":" not in stripped:
            continue
        indent = len(raw) - len(raw.lstrip())
        item = stripped[2:] if stripped.startswith("- ") else stripped
        key, value = item.split(":", 1)
        key = key.strip()
        if indent == 0:
            parent = key
            if value.strip() or key in scalar_lists:
                refs[key] = f"{locator}:{index + 1}"
        elif parent in {"P_order", "S_mapping"}:
            refs[f"{parent}[].{key}"] = f"{locator}:{index + 1}"
        else:
            refs[f"{parent}.{key}"] = f"{locator}:{index + 1}"
    return f"{locator}:{heading + 1}-{closing + 1}", refs


def _current_git_revision(locator: Path) -> str | None:
    try:
        root = Path(subprocess.check_output(
            ["git", "-C", str(locator.parent), "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip())
        locator.relative_to(root)
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def validate_semantic_binding(binding: Any) -> dict[str, Any]:
    if not isinstance(binding, dict) or set(binding) != SEMANTIC_PROVENANCE_FIELDS:
        return dict(SEMANTIC_HOLD)
    locator = binding["canonical_source_locator"]
    coverage = binding["semantic_field_definition_coverage"]
    if (
        not isinstance(locator, str) or not locator
        or not isinstance(binding["canonical_source_readback"], str)
        or not isinstance(binding["current_source_revision"], str)
        or not isinstance(binding["current_content_hash"], str)
        or not isinstance(binding["canonical_section"], str)
        or not isinstance(coverage, dict) or not coverage
    ):
        return dict(SEMANTIC_HOLD)
    source = Path(locator).resolve()
    try:
        content = source.read_bytes()
        text = content.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return dict(SEMANTIC_HOLD)
    revision = _current_git_revision(source)
    definitions = _anchor_definition_refs(source, text)
    if revision is None or definitions is None:
        return dict(SEMANTIC_HOLD)
    section_ref, definition_refs = definitions
    if (
        binding["canonical_source_locator"] != str(source)
        or binding["canonical_source_readback"] != f"{source}:1-{len(text.splitlines())}"
        or binding["current_source_revision"] != revision
        or binding["current_content_hash"] != hashlib.sha256(content).hexdigest()
        or binding["canonical_section"] != section_ref
        or not set(coverage).issubset(ANCHOR_SEMANTIC_FIELDS)
        or any(not isinstance(ref, str) or definition_refs.get(field) != ref for field, ref in coverage.items())
    ):
        return dict(SEMANTIC_HOLD)
    return {"status": "pass", "failure_codes": []}


def validate_semantic_provenance(binding: Any, semantic_body: Any) -> dict[str, Any]:
    if not isinstance(semantic_body, dict) or validate_semantic_binding(binding)["status"] != "pass":
        return dict(SEMANTIC_HOLD)
    leaves = _semantic_leaves(semantic_body)
    if leaves != set(binding["semantic_field_definition_coverage"]):
        return dict(SEMANTIC_HOLD)
    return {"status": "pass", "failure_codes": []}


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _entry_section(readme: Path) -> str | None:
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(
        r"^##\s+Project[ -]entry[ -]point\s*$([\s\S]*?)(?=^##\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1) if match else None


def _receipt(
    *,
    entry_ref: str,
    authority_ref: str | None,
    requested_target: Any,
    resolved_refs: list[str],
    revisions: dict[str, str],
    digests: dict[str, str],
    diagnostics: list[str],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "entry_source_ref": entry_ref,
        "canonical_authority_ref": authority_ref,
        "requested_target": requested_target if isinstance(requested_target, str) else None,
        "resolved_refs": resolved_refs,
        "source_revisions": revisions,
        "source_digests": digests,
        "status": "hold" if diagnostics else "resolved",
        "diagnostic_codes": list(dict.fromkeys(diagnostics)),
        "c1_runtime_closure": False,
    }


def navigate_cps_runtime(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    """Resolve one bounded target class without returning source bodies."""
    repo = repo.absolute()
    readme = repo / "README.md"
    entry_ref = f"{readme}#Project-entry-point"
    target = request.get("requested_target") if isinstance(request, dict) else None
    authority = repo.parent / "harness-brain" / "projects" / repo.name
    diagnostics: list[str] = []

    entry = _entry_section(readme)
    if entry is None:
        diagnostics.append("HOLD_RUNTIME_NAVIGATION_ENTRY_MISSING")
    authority_valid = bool(
        entry is not None
        and re.search(r"\bharness-brain\b", entry, re.IGNORECASE)
        and re.search(r"\bcanonical\s+authority\b", entry, re.IGNORECASE)
        and authority.is_dir()
    )
    if entry is not None and not authority_valid:
        diagnostics.append("HOLD_RUNTIME_NAVIGATION_AUTHORITY_MISSING")
    if not isinstance(target, str) or target not in TARGETS:
        diagnostics.append("HOLD_RUNTIME_NAVIGATION_TARGET_AMBIGUOUS")

    authority_ref = str(authority) if authority_valid else None
    if diagnostics:
        return _receipt(
            entry_ref=entry_ref,
            authority_ref=authority_ref,
            requested_target=target,
            resolved_refs=[],
            revisions={},
            digests={},
            diagnostics=diagnostics,
        )

    assert isinstance(target, str)
    target_roots = {
        "source": (authority,),
        "contract": (authority / "contracts",),
        "working_graph": (authority / "working-graphs",),
        "runtime": (repo / ".harness",),
        "test": (repo / "tests", repo / ".harness" / "hermes" / "tests"),
        "receipt": (repo / ".harness" / "project" / "runs",),
    }[target]
    target_roots = tuple(root.resolve() for root in target_roots)
    raw_refs = request.get("requested_refs")
    refs = raw_refs if isinstance(raw_refs, list) else []
    if not refs:
        diagnostics.append("HOLD_RUNTIME_NAVIGATION_TARGET_AMBIGUOUS")

    resolved_refs: list[str] = []
    revisions: dict[str, str] = {}
    digests: dict[str, str] = {}
    expected_map = request.get("expected_source_revisions")
    expected_revisions = expected_map if isinstance(expected_map, dict) else {}
    base = authority if target in {"source", "contract", "working_graph"} else repo

    for raw in refs:
        item = raw if isinstance(raw, dict) else {"ref": raw}
        raw_ref = item.get("ref")
        if not isinstance(raw_ref, str) or not raw_ref.strip():
            diagnostics.append("HOLD_RUNTIME_NAVIGATION_TARGET_AMBIGUOUS")
            continue
        supplied = Path(raw_ref)
        if ".." in supplied.parts:
            diagnostics.append("HOLD_RUNTIME_NAVIGATION_PATH_ESCAPE")
            continue
        path = (supplied if supplied.is_absolute() else base / supplied).absolute()
        canonical_path = path.resolve()
        if not _inside(canonical_path, target_roots):
            diagnostics.append("HOLD_RUNTIME_NAVIGATION_UNAPPROVED_ROOT")
            continue
        try:
            content = path.read_bytes()
        except OSError:
            diagnostics.append("HOLD_RUNTIME_NAVIGATION_REF_MISSING")
            continue
        path_ref = str(path)
        digest = hashlib.sha256(content).hexdigest()
        revision = str(item.get("source_revision") or digest)
        expected = item.get("expected_revision", expected_revisions.get(raw_ref, expected_revisions.get(path_ref)))
        if expected is not None and str(expected) != revision:
            diagnostics.append("HOLD_RUNTIME_NAVIGATION_REVISION_MISMATCH")
            continue
        resolved_refs.append(path_ref)
        revisions[path_ref] = revision
        digests[path_ref] = digest

    if diagnostics:
        resolved_refs, revisions, digests = [], {}, {}
    return _receipt(
        entry_ref=entry_ref,
        authority_ref=authority_ref,
        requested_target=target,
        resolved_refs=resolved_refs,
        revisions=revisions,
        digests=digests,
        diagnostics=diagnostics,
    )
