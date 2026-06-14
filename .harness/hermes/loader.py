#!/usr/bin/env python3
"""Hermes reference loader for the harness-starter export worktree."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()
CATALOG = ROOT / ".harness" / "hermes" / "reference" / "catalog.yaml"
PIPELINE = ROOT / ".harness" / "hermes" / "reference" / "pipeline.yaml"
HOOKS = ROOT / ".harness" / "hermes" / "reference" / "hook-contracts.yaml"
OFFICIAL_ALIGNMENT = ROOT / ".harness" / "hermes" / "reference" / "official-alignment.yaml"
RULES = ROOT / ".harness" / "hermes" / "reference" / "rules.yaml"
DOCS_OPS = ROOT / ".harness" / "hermes" / "reference" / "ops" / "docs-ops.yaml"
WIP_LIFECYCLE = ROOT / ".harness" / "hermes" / "reference" / "ops" / "wip-lifecycle.yaml"
DOCUMENT_STANDARDS = ROOT / ".harness" / "hermes" / "reference" / "ops" / "document-standards.yaml"
COMMIT_FLOW = ROOT / ".harness" / "hermes" / "reference" / "ops" / "commit-flow.yaml"
CPS_AC = ROOT / ".harness" / "hermes" / "reference" / "ops" / "cps-ac.yaml"
PROJECT_BOOTSTRAP = ROOT / ".harness" / "hermes" / "project-bootstrap.yaml"
PROJECT_SETUP_CRITERIA = ROOT / ".harness" / "hermes" / "reference" / "ops" / "project-setup-criteria.yaml"
SEMANTIC_TOOLING_CRITERIA = ROOT / ".harness" / "hermes" / "reference" / "ops" / "semantic-tooling-criteria.yaml"
SANDBOX = ROOT / ".harness" / "hermes" / "sandbox.yaml"
GATEWAY = ROOT / ".harness" / "hermes" / "gateway.yaml"
ROUTES = ROOT / ".harness" / "hermes" / "routes.yaml"
BOARD_ASSIGNEES = ROOT / ".harness" / "hermes" / "board-assignees.yaml"
PROFILE_DOCS = ROOT / ".harness" / "hermes" / "profile-docs"
PROFILE_DOC_SOUL = PROFILE_DOCS / "SOUL.md"
PROFILE_DOC_AGENTS = PROFILE_DOCS / "AGENTS.md"
PROFILE_DOC_USER = PROFILE_DOCS / "USER.md"
TASK_TEMPLATE = ROOT / ".harness" / "hermes" / "agent-task.template.yaml"
PROFILES = ROOT / ".harness" / "hermes" / "profiles.yaml"
PROFILE_SKILLS = ROOT / ".harness" / "hermes" / "profile-skills.yaml"
COORDINATION = ROOT / ".harness" / "hermes" / "coordination.yaml"
CPS_PROFILE_ROUTING = ROOT / ".harness" / "hermes" / "cps-profile-routing.yaml"
DOC_GENERATION = ROOT / ".harness" / "hermes" / "doc-generation.yaml"
AGENT_TASK_SCHEMA = ROOT / ".harness" / "schemas" / "agent-task.schema.yaml"
BOARD_ASSIGNEES_SCHEMA = ROOT / ".harness" / "schemas" / "board-assignees.schema.yaml"
FORBIDDEN_TOP_LEVEL = [f".{name}" for name in ("cla" + "ude", "co" + "dex", "agents")]
FORBIDDEN_TOP_LEVEL.extend(["docs", "scripts"])
FORBIDDEN_REFERENCE_FILES = [
    ROOT / ".harness" / "hermes" / "reference" / f"{stem}.yaml"
    for stem in ("agents", "skills", "source" + "-map")
]
REQUIRED_FILES = [
    CATALOG,
    PIPELINE,
    HOOKS,
    OFFICIAL_ALIGNMENT,
    RULES,
    DOCS_OPS,
    WIP_LIFECYCLE,
    DOCUMENT_STANDARDS,
    COMMIT_FLOW,
    CPS_AC,
    PROJECT_BOOTSTRAP,
    PROJECT_SETUP_CRITERIA,
    SEMANTIC_TOOLING_CRITERIA,
    SANDBOX,
    GATEWAY,
    ROUTES,
    BOARD_ASSIGNEES,
    PROFILE_DOC_SOUL,
    PROFILE_DOC_AGENTS,
    PROFILE_DOC_USER,
    TASK_TEMPLATE,
    PROFILES,
    PROFILE_SKILLS,
    COORDINATION,
    CPS_PROFILE_ROUTING,
    DOC_GENERATION,
    AGENT_TASK_SCHEMA,
    BOARD_ASSIGNEES_SCHEMA,
]
REQUIRED_DOCS_OPS_TERMS = [
    "validate",
    "verify-relates",
    "cps list",
    "cps add",
    "move",
    "reopen",
    "cluster-update",
    "wip-sync",
    "validate-harness-architecture",
]
REQUIRED_PIPELINE_GATES = ["intake-context", "classify-cps", "plan-docs", "executor-scope", "review-and-handoff"]
REQUIRED_BOUNDARY_TERMS = ["harness_owns", "hermes_owns", "gateway_owns"]
REQUIRED_CPS_AC_TERMS = [
    "goal_ac_semantics",
    "cps_flow_graph",
    "flow_inheritance_contract",
    "triage_split_policy",
    "runtime_flow_trace",
    "langsmith_eval_basis",
    "node_ownership",
    "legacy_task_policy",
    "root_goal",
    "task_AC",
    "split_on_C",
]
REQUIRED_TASK_PACKET_TERMS = [
    "cps_flow",
    "goal_ac_semantics",
    "langsmith_eval_basis",
    "root_goal_id",
    "task_AC",
    "c_split_rule",
]
OFFICIAL_REQUIRED_WORKSPACE_ENV = [
    "HERMES_KANBAN_TASK",
    "HERMES_KANBAN_DB",
    "HERMES_KANBAN_BOARD",
    "HERMES_KANBAN_WORKSPACES_ROOT",
    "HERMES_KANBAN_WORKSPACE",
    "HERMES_KANBAN_RUN_ID",
    "HERMES_KANBAN_CLAIM_LOCK",
    "HERMES_PROFILE",
]
OFFICIAL_CONDITIONAL_WORKSPACE_ENV = ["HERMES_TENANT"]
CONTEXT_SENSITIVE_OPERATIONS = {"branch", "commit", "push", "auth", "write"}
OWNER_APPROVAL_OPERATIONS = {"commit", "push", "auth"}
CONTROL_PLANE_ROOTS = [Path("/Users/kann/.hermes/hermes-agent")]
OWNER_APPROVAL_ENV = "HARNESS_OWNER_APPROVED_OPERATION"

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def _scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value.strip("'\"")


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is not None:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    # Tiny YAML subset parser for the reference contract files. It supports the
    # mapping/list/scalar shapes used here so validation does not depend on
    # PyYAML being installed in the executor runtime.
    rows: list[tuple[int, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        rows.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(rows):
            return {}, index
        if rows[index][1].startswith("- "):
            items: list[Any] = []
            while index < len(rows):
                row_indent, text = rows[index]
                if row_indent != indent or not text.startswith("- "):
                    break
                item_text = text[2:].strip()
                index += 1
                if not item_text:
                    child, index = parse_block(index, indent + 2)
                    items.append(child)
                elif ":" in item_text:
                    key, _, value = item_text.partition(":")
                    item: dict[str, Any] = {key.strip(): _scalar(value) if value.strip() else {}}
                    if index < len(rows) and rows[index][0] > indent:
                        child, index = parse_block(index, rows[index][0])
                        if isinstance(child, dict):
                            if value.strip():
                                item.update(child)
                            else:
                                item[key.strip()] = child
                    items.append(item)
                else:
                    items.append(_scalar(item_text))
            return items, index

        data: dict[str, Any] = {}
        while index < len(rows):
            row_indent, text = rows[index]
            if row_indent != indent or text.startswith("- "):
                break
            key, _, value = text.partition(":")
            key = key.strip()
            value = value.strip()
            index += 1
            if value:
                data[key] = _scalar(value)
            elif index < len(rows) and rows[index][0] > indent:
                data[key], index = parse_block(index, rows[index][0])
            else:
                data[key] = {}
        return data, index

    parsed, _ = parse_block(0, rows[0][0] if rows else 0)
    return parsed if isinstance(parsed, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _glob_to_regex_path(pattern: str) -> str:
    return pattern[:-3] if pattern.endswith("/**") else pattern


def _target_allowed(target: Path, allowed_scope: list[Any]) -> bool:
    try:
        rel = target.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return False
    for raw_pattern in allowed_scope:
        pattern = str(raw_pattern)
        prefix = _glob_to_regex_path(pattern)
        if pattern.endswith("/**") and (rel == prefix or rel.startswith(prefix + "/")):
            return True
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def guard_runtime_context(
    *,
    cwd: str | Path,
    env: dict[str, str] | None = None,
    operation: str = "write",
    target_paths: list[str | Path] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    cwd_path = _as_path(cwd)
    operation = operation.strip()
    task_packet = _load_yaml(TASK_TEMPLATE) if TASK_TEMPLATE.exists() else {}
    expected_workspace = env.get("HERMES_KANBAN_WORKSPACE") or str(task_packet.get("worktree_path") or "")
    expected_board = task_packet.get("kanban_board")
    allowed_scope = _list(task_packet.get("allowed_scope"))
    errors: list[str] = []

    if operation in CONTEXT_SENSITIVE_OPERATIONS:
        missing = [name for name in OFFICIAL_REQUIRED_WORKSPACE_ENV if not env.get(name)]
        if missing:
            errors.append(f"missing required env for {operation}: {', '.join(missing)}")

    if expected_workspace:
        workspace_path = _as_path(expected_workspace)
        if cwd_path != workspace_path:
            errors.append(f"cwd mismatch: expected HERMES_KANBAN_WORKSPACE {workspace_path}, got {cwd_path}")
    else:
        workspace_path = None
        errors.append("missing HERMES_KANBAN_WORKSPACE/worktree_path for runtime context guard")

    if expected_board and env.get("HERMES_KANBAN_BOARD") and env.get("HERMES_KANBAN_BOARD") != expected_board:
        errors.append(f"board mismatch: expected {expected_board}, got {env.get('HERMES_KANBAN_BOARD')}")

    effective_project_root = _as_path(project_root) if project_root else ROOT
    if any(effective_project_root == root or root in effective_project_root.parents for root in CONTROL_PLANE_ROOTS):
        errors.append("control-plane project_root cannot perform project branch/commit/push/auth without internal authorization")

    if operation in OWNER_APPROVAL_OPERATIONS and env.get(OWNER_APPROVAL_ENV) != "true":
        errors.append(f"owner approval env {OWNER_APPROVAL_ENV}=true required for {operation}")

    checked_targets: list[str] = []
    for target in target_paths or []:
        target_path = _as_path(target)
        checked_targets.append(target_path.as_posix())
        if allowed_scope and not _target_allowed(target_path, allowed_scope):
            errors.append(f"target outside allowed_scope: {target_path}")

    return {
        "schema": "harness-hermes-runtime-context-guard",
        "ok": not errors,
        "errors": errors,
        "expected": {
            "workspace": workspace_path.as_posix() if workspace_path else None,
            "board": expected_board,
            "allowed_scope": allowed_scope,
        },
        "actual": {
            "cwd": cwd_path.as_posix(),
            "operation": operation,
            "board": env.get("HERMES_KANBAN_BOARD"),
            "project_root": effective_project_root.as_posix(),
            "target_paths": checked_targets,
        },
    }


def _summary() -> dict[str, Any]:
    catalog = _load_yaml(CATALOG)
    exports = catalog.get("exports", {})
    pipeline = _load_yaml(PIPELINE)
    return {
        "schema": "harness-hermes-reference-summary",
        "project_root": ROOT.as_posix(),
        "purpose": catalog.get("purpose"),
        "not_a_merge_target": catalog.get("not_a_merge_target"),
        "pipeline": {
            "entrypoint": ".harness/hermes/reference/pipeline.yaml",
            "default_wrapper": pipeline.get("entrypoint", {}).get("default_wrapper"),
            "task_template": pipeline.get("entrypoint", {}).get("task_template"),
        },
        "gateway": ".harness/hermes/gateway.yaml",
        "board_assignees": ".harness/hermes/board-assignees.yaml",
        "sandbox": ".harness/hermes/sandbox.yaml",
        "profiles": ".harness/hermes/profiles.yaml",
        "profile_skills": ".harness/hermes/profile-skills.yaml",
        "coordination": ".harness/hermes/coordination.yaml",
        "cps_profile_routing": ".harness/hermes/cps-profile-routing.yaml",
        "doc_generation": ".harness/hermes/doc-generation.yaml",
        "project_bootstrap": ".harness/hermes/project-bootstrap.yaml",
        "semantic_tooling": ".harness/hermes/reference/ops/semantic-tooling-criteria.yaml",
        "native_agent_policy": catalog.get("native_agent_policy"),
        "rules": exports.get("rules", []),
        "hooks": exports.get("hooks", []),
        "operations": exports.get("operations", []),
    }


def _validate() -> dict[str, Any]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT).as_posix()}")
    for rel_path in FORBIDDEN_TOP_LEVEL:
        if (ROOT / rel_path).exists():
            errors.append(f"forbidden top-level path exists: {rel_path}")
    for path in FORBIDDEN_REFERENCE_FILES:
        if path.exists():
            errors.append(f"forbidden import-style reference file exists: {path.relative_to(ROOT).as_posix()}")
    if CATALOG.exists():
        catalog = _load_yaml(CATALOG)
        if catalog.get("not_a_merge_target") is not True:
            errors.append("catalog must declare not_a_merge_target: true")
        alignment = catalog.get("official_alignment", {})
        if "Hermes profile lane" not in str(alignment.get("worker_lane", "")):
            errors.append("catalog must align worker lane with Hermes profile lane")
        if "not a paved Hermes lane" not in str(alignment.get("external_cli_lane", "")):
            errors.append("catalog must mark external CLI lane as not paved")
    if DOCS_OPS.exists():
        text = DOCS_OPS.read_text(encoding="utf-8")
        for term in REQUIRED_DOCS_OPS_TERMS:
            if term not in text:
                errors.append(f"docs-ops contract missing term: {term}")
    if PIPELINE.exists():
        text = PIPELINE.read_text(encoding="utf-8")
        if "kanban_flow" in text:
            errors.append("pipeline must expose harness_gates, not own kanban_flow")
        for gate in REQUIRED_PIPELINE_GATES:
            if f"gate: {gate}" not in text:
                errors.append(f"pipeline missing gate: {gate}")
        if "kanban_complete" not in text or "kanban_block" not in text:
            errors.append("pipeline must describe kanban lifecycle terminators")
        for term in REQUIRED_BOUNDARY_TERMS:
            if term not in text:
                errors.append(f"pipeline missing ownership boundary term: {term}")
    if SANDBOX.exists():
        text = SANDBOX.read_text(encoding="utf-8")
        if "HERMES_KANBAN_WORKSPACE" not in text:
            errors.append("sandbox contract must require HERMES_KANBAN_WORKSPACE")
        if "mismatch_policy" not in text or "block before any write" not in text:
            errors.append("sandbox contract must block cwd/worktree mismatch before writes")
        if "direct git commit" not in text or "direct git push" not in text:
            errors.append("sandbox contract must forbid direct commit and push")
        for term in [
            "Env values are runtime context, not permission grants.",
            "HERMES_KANBAN_WORKSPACES_ROOT does not authorize sibling workspace access.",
            "HERMES_KANBAN_DB must not be directly written",
            "ambient_current_board_policy",
            "block_on_cwd_project_mismatch: true",
            "blocked_operations",
            "pinned_worktree_context_accepted: true",
        ]:
            if term not in text:
                errors.append(f"sandbox contract missing env/board guardrail: {term}")
    if GATEWAY.exists():
        text = GATEWAY.read_text(encoding="utf-8")
        if "Bot tokens stay" not in text:
            errors.append("gateway contract must keep tokens out of repo")
        if "require_mention true" not in text:
            errors.append("gateway contract must recommend require_mention true")
    if RULES.exists():
        text = RULES.read_text(encoding="utf-8")
        if "do_not_import" not in text:
            errors.append("rules contract must explicitly forbid importing harness agents or skills")
        for term in REQUIRED_BOUNDARY_TERMS:
            if term not in text:
                errors.append(f"rules contract missing ownership boundary term: {term}")
    if CPS_AC.exists():
        text = CPS_AC.read_text(encoding="utf-8")
        for term in REQUIRED_CPS_AC_TERMS:
            if term not in text:
                errors.append(f"cps-ac contract missing Goal/AC flow term: {term}")
    if DOCUMENT_STANDARDS.exists():
        text = DOCUMENT_STANDARDS.read_text(encoding="utf-8")
        for term in ["domain_selection", "abbr_selection", "document_shape", "review_gate"]:
            if term not in text:
                errors.append(f"document standards missing section: {term}")
        for term in REQUIRED_BOUNDARY_TERMS:
            if term not in text:
                errors.append(f"document standards missing ownership boundary term: {term}")
    if PROFILES.exists():
        text = PROFILES.read_text(encoding="utf-8")
        for axis in ["external-truth", "internal-truth", "adversarial", "execution", "standard-gate"]:
            if axis not in text:
                errors.append(f"profiles contract missing persona axis: {axis}")
        for profile in ["moderator", "orchestrator", "coder", "reviewer", "threat-guard", "researcher", "advisor", "designer", "marketer"]:
            if f"name: {profile}" not in text:
                errors.append(f"profiles contract missing required profile: {profile}")
    for path, terms in [
        (PROFILE_DOC_SOUL, ["`HERMES_KANBAN_WORKSPACE` is the filesystem anchor", "Profile output is evidence", "<project>-maat", "shared-seshat"]),
        (PROFILE_DOC_AGENTS, ["task.assignee", "threat-guard", "no fallback profile", "<project>-sekhmet"]),
        (PROFILE_DOC_USER, ["User preferences belong in `USER.md`", "Forbidden Memory", "Project Isolation"]),
    ]:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for term in terms:
                if term not in text:
                    errors.append(f"profile doc {path.name} missing term: {term}")
    if PROFILE_SKILLS.exists():
        text = PROFILE_SKILLS.read_text(encoding="utf-8")
        for skill in ["cps-profile-route", "advisor-decision-frame", "document-generation-route", "semantic-tooling-route", "one-round-consensus", "moderator-final-gate"]:
            if f"name: {skill}" not in text:
                errors.append(f"profile skills missing required skill: {skill}")
    if COORDINATION.exists():
        text = COORDINATION.read_text(encoding="utf-8")
        if "cps_routing_contract: .harness/hermes/cps-profile-routing.yaml" not in text:
            errors.append("coordination must point to cps-profile-routing contract")
        if "doc_generation_contract: .harness/hermes/doc-generation.yaml" not in text:
            errors.append("coordination must point to doc-generation contract")
        if "max_coordination_rounds: 1" not in text:
            errors.append("coordination must cap profile mixing at one round")
    if CPS_PROFILE_ROUTING.exists():
        text = CPS_PROFILE_ROUTING.read_text(encoding="utf-8")
        for term in [
            "profile_call_requires_cps_reason: true",
            "no_profile_mixing_without_cps_reason: true",
            "gateway_context_is_evidence_not_permission: true",
            "sandbox_scope_comes_from_task_packet: true",
            "semantic_evidence_prefers_cps_reason: true",
            "document_generation_problem",
            "semantic_evidence_used",
            "semantic_fallback_reason",
        ]:
            if term not in text:
                errors.append(f"cps profile routing missing term: {term}")
    if PROJECT_BOOTSTRAP.exists():
        text = PROJECT_BOOTSTRAP.read_text(encoding="utf-8")
        for term in ["structure_surface", "handoff_trigger", "advisory-only", "bounded-executor"]:
            if term not in text:
                errors.append(f"project bootstrap contract missing term: {term}")
    if SEMANTIC_TOOLING_CRITERIA.exists():
        text = SEMANTIC_TOOLING_CRITERIA.read_text(encoding="utf-8")
        for term in ["non_blocking: true", "fallback_rule", "owner_action_required_for_writes"]:
            if term not in text:
                errors.append(f"semantic tooling criteria missing term: {term}")
    if DOC_GENERATION.exists():
        text = DOC_GENERATION.read_text(encoding="utf-8")
        for section in ["cps_decision", "document_classification", "profile_routing", "docs_ops_binding", "moderator_gate"]:
            if section not in text:
                errors.append(f"doc generation contract missing section: {section}")
        if "contract: .harness/hermes/cps-profile-routing.yaml" not in text:
            errors.append("doc generation must point to cps-profile-routing contract")
    if TASK_TEMPLATE.exists() and AGENT_TASK_SCHEMA.exists() and SANDBOX.exists():
        task_text = TASK_TEMPLATE.read_text(encoding="utf-8")
        for term in REQUIRED_TASK_PACKET_TERMS:
            if term not in task_text:
                errors.append(f"task packet missing Goal/AC flow term: {term}")
        task_packet = _load_yaml(TASK_TEMPLATE)
        task_schema = _load_yaml(AGENT_TASK_SCHEMA)
        sandbox = _load_yaml(SANDBOX)
        task_env = set((task_packet.get("workspace_env") or {}).keys())
        schema_env = set(_list((task_schema.get("workspace_env") or {}).get("required_fields")))
        schema_conditional_env = set(_list((task_schema.get("workspace_env") or {}).get("conditional_fields")))
        workspace_binding = sandbox.get("workspace_binding") or {}
        sandbox_env = set(_list(workspace_binding.get("required_env")))
        sandbox_conditional_env = set(_list(workspace_binding.get("conditional_env")))
        required_env = set(OFFICIAL_REQUIRED_WORKSPACE_ENV)
        conditional_env = set(OFFICIAL_CONDITIONAL_WORKSPACE_ENV)
        for source_name, values in [
            ("task packet workspace_env", task_env),
            ("agent-task schema workspace_env.required_fields", schema_env),
            ("sandbox workspace_binding.required_env", sandbox_env),
        ]:
            missing = sorted(required_env - values)
            if missing:
                errors.append(f"{source_name} missing official required env: {', '.join(missing)}")
        for source_name, values in [
            ("task packet workspace_env", task_env),
            ("agent-task schema workspace_env.conditional_fields", schema_conditional_env),
            ("sandbox workspace_binding.conditional_env", sandbox_conditional_env),
        ]:
            missing = sorted(conditional_env - values)
            if missing:
                errors.append(f"{source_name} missing official conditional env: {', '.join(missing)}")
        classification = task_packet.get("workspace_env_classification") or {}
        if classification.get("filesystem_anchor") != "HERMES_KANBAN_WORKSPACE":
            errors.append("task packet workspace_env_classification must anchor filesystem on HERMES_KANBAN_WORKSPACE")
        if "permission grants" not in str(classification.get("permission_rule", "")):
            errors.append("task packet workspace_env_classification must say env values are not permission grants")
    if ROUTES.exists() and GATEWAY.exists() and TASK_TEMPLATE.exists():
        routes = _load_yaml(ROUTES)
        gateway = _load_yaml(GATEWAY)
        task_packet = _load_yaml(TASK_TEMPLATE)
        packet_board = task_packet.get("kanban_board")
        gateway_board = (gateway.get("route_to_kanban") or {}).get("kanban_board")
        route_boards = {
            route.get("kanban_board")
            for route in _list(routes.get("routes"))
            if isinstance(route, dict) and route.get("kanban_board")
        }
        if not packet_board:
            errors.append("task packet must declare kanban_board")
        if gateway_board != packet_board:
            errors.append("gateway route_to_kanban.kanban_board must match task packet kanban_board")
        if route_boards and route_boards != {packet_board}:
            errors.append("all route kanban_board values must match task packet kanban_board")
    if BOARD_ASSIGNEES.exists() and PROFILES.exists() and ROUTES.exists():
        board_assignees = _load_yaml(BOARD_ASSIGNEES)
        profiles = _load_yaml(PROFILES)
        routes = _load_yaml(ROUTES)
        text = BOARD_ASSIGNEES.read_text(encoding="utf-8")
        for term in [
            "concrete-hermes-profile-name",
            "role_archetype is classification",
            "local Hermes profile config owns profile creation",
            "no arbitrary fallback profile may execute",
        ]:
            if term not in text:
                errors.append(f"board assignee contract missing rule: {term}")
        policy = board_assignees.get("policy") or {}
        naming = board_assignees.get("naming_guidance") or {}
        for field in ["project_profile_pattern", "shared_profile_pattern", "role_archetype_required", "reserved_profiles_require_local_creation"]:
            if field not in naming:
                errors.append(f"board assignee naming guidance missing field: {field}")
        if policy.get("assignee_identity") != "concrete-hermes-profile-name":
            errors.append("board assignee policy must use concrete Hermes profile names as assignee identity")
        if policy.get("role_archetype_is_not_assignee") is not True:
            errors.append("board assignee policy must mark role archetype as classification only")
        if policy.get("no_arbitrary_fallback") is not True:
            errors.append("board assignee policy must forbid arbitrary fallback profiles")
        role_names: set[str] = set()
        profile_sets = profiles.get("profile_sets") or {}
        for profile_set in profile_sets.values():
            for profile in _list(profile_set):
                if isinstance(profile, dict) and profile.get("name"):
                    role_names.add(profile["name"])
        route_names = {
            route.get("name")
            for route in _list(routes.get("routes"))
            if isinstance(route, dict) and route.get("name")
        }
        route_boards = {
            route.get("kanban_board")
            for route in _list(routes.get("routes"))
            if isinstance(route, dict) and route.get("kanban_board")
        }
        assignee_boards: set[str] = set()
        for board in _list(board_assignees.get("boards")):
            if not isinstance(board, dict):
                continue
            board_name = board.get("board")
            if board_name:
                assignee_boards.add(board_name)
            if board_name not in route_boards:
                errors.append(f"board assignee contract references board not present in routes: {board_name}")
            unknown_routes = sorted(set(_list(board.get("routes"))) - route_names)
            if unknown_routes:
                errors.append(f"board assignee contract references unknown routes: {', '.join(unknown_routes)}")
            assignee_profiles: set[str] = set()
            assignee_roles: set[str] = set()
            for assignee in _list(board.get("selectable_assignees")):
                if not isinstance(assignee, dict):
                    continue
                profile_name = assignee.get("profile")
                role = assignee.get("role_archetype")
                deity = assignee.get("deity")
                lane_shape = assignee.get("lane_shape")
                if not profile_name:
                    errors.append(f"board {board_name} selectable assignee missing profile")
                elif profile_name in assignee_profiles:
                    errors.append(f"board {board_name} has duplicate selectable profile: {profile_name}")
                else:
                    assignee_profiles.add(profile_name)
                if role not in role_names:
                    errors.append(f"board {board_name} assignee {profile_name} references unknown role_archetype: {role}")
                else:
                    assignee_roles.add(role)
                if not deity:
                    errors.append(f"board {board_name} assignee {profile_name} missing deity")
                if lane_shape != "hermes-profile":
                    errors.append(f"board {board_name} assignee {profile_name} must use hermes-profile lane_shape")
            for required_role in ["moderator", "orchestrator", "coder", "reviewer", "threat-guard", "researcher", "advisor", "designer", "marketer"]:
                if required_role not in assignee_roles:
                    errors.append(f"board {board_name} missing selectable assignee for role_archetype: {required_role}")
        missing_board_contracts = sorted(route_boards - assignee_boards)
        if missing_board_contracts:
            errors.append(f"routes reference boards without assignee contracts: {', '.join(missing_board_contracts)}")
    return {"schema": "harness-hermes-reference-validation", "ok": not errors, "errors": errors}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Hermes loader for harness reference export.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    sub.add_parser("validate-reference")
    guard_parser = sub.add_parser("guard-runtime-context")
    guard_parser.add_argument("--operation", default="write")
    guard_parser.add_argument("--cwd", default=str(Path.cwd()))
    guard_parser.add_argument("--project-root", default=None)
    guard_parser.add_argument("--target-path", action="append", default=[])
    args = parser.parse_args(argv)

    if args.command == "summary":
        data = _summary()
    elif args.command == "validate-reference":
        data = _validate()
    else:
        data = guard_runtime_context(
            cwd=args.cwd,
            operation=args.operation,
            project_root=args.project_root,
            target_paths=args.target_path,
        )
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if data.get("ok") is False else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
