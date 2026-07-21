from __future__ import annotations

import argparse
import json
from pathlib import Path

from .project_binding import BindingError, BindingInputs, apply_binding, inspect_binding, plan_binding, reconcile_legacy
from .sandbox import SandboxError, run_sandbox


def _binding_inputs(args: argparse.Namespace) -> BindingInputs:
    return BindingInputs(
        project_id=args.project_id,
        project_root=args.project_root,
        protected_branch=args.protected_branch,
        railway_service=args.railway_service,
        runtime_version=args.runtime_version,
        railway_project_id=args.railway_project_id,
        railway_environment_id=args.railway_environment_id,
        railway_service_id=args.railway_service_id,
        vercel_org_id=args.vercel_org_id,
        vercel_project_id=args.vercel_project_id,
        vercel_target=args.vercel_target,
        supabase_project_ref=args.supabase_project_ref,
        supabase_schema_migration_scope_id=args.supabase_schema_migration_scope_id,
        supabase_privileged_data_mutation_boundary_id=args.supabase_privileged_data_mutation_boundary_id,
        n8n_instance_host=args.n8n_instance_host,
        n8n_workflow_id=args.n8n_workflow_id,
        n8n_webhook_endpoint_sha256=args.n8n_webhook_endpoint_sha256,
        n8n_webhook_path_sha256=args.n8n_webhook_path_sha256,
        n8n_callback_consumer_id=args.n8n_callback_consumer_id,
    )


def _add_binding_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--protected-branch", required=True)
    parser.add_argument("--railway-service", required=True)
    parser.add_argument("--railway-project-id")
    parser.add_argument("--railway-environment-id")
    parser.add_argument("--railway-service-id")
    parser.add_argument("--vercel-org-id")
    parser.add_argument("--vercel-project-id")
    parser.add_argument("--vercel-target")
    parser.add_argument("--supabase-project-ref")
    parser.add_argument("--supabase-schema-migration-scope-id")
    parser.add_argument("--supabase-privileged-data-mutation-boundary-id")
    parser.add_argument("--n8n-instance-host")
    parser.add_argument("--n8n-workflow-id")
    parser.add_argument("--n8n-webhook-endpoint-sha256")
    parser.add_argument("--n8n-webhook-path-sha256")
    parser.add_argument("--n8n-callback-consumer-id")
    parser.add_argument("--runtime-version", default="1")
    parser.add_argument("project_root", type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness-project-binding",
        description="Reconcile the minimal Harness project binding desired state.",
        epilog=(
            "The sandbox command constrains only the subprocess launched through sandbox-exec. "
            "It cannot constrain ambient Hermes patch/write tools. Network is denied unless --network is supplied, "
            "and provider mutation commands remain blocked."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("project_root", type=Path)
    for name in ("plan", "apply"):
        _add_binding_arguments(commands.add_parser(name))
    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("project_root", type=Path)
    reconcile.add_argument("--apply", action="store_true", help="remove only unchanged files in the tool ownership manifest")
    sandbox = commands.add_parser("sandbox")
    sandbox.add_argument("--worktree", required=True, type=Path)
    sandbox.add_argument("--state-dir", required=True, type=Path)
    sandbox.add_argument(
        "--network",
        action="store_true",
        help="permit network only for exact Railway/Vercel/Supabase read-only discovery/status commands",
    )
    sandbox.add_argument("--allow-write", action="append", default=[], type=Path)
    sandbox.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            result = inspect_binding(args.project_root)
        elif args.command == "plan":
            result = plan_binding(_binding_inputs(args))
        elif args.command == "apply":
            result = apply_binding(_binding_inputs(args))
        elif args.command == "reconcile":
            result = reconcile_legacy(args.project_root, apply=args.apply)
        else:
            command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            return run_sandbox(
                args.worktree,
                args.state_dir,
                command,
                network=args.network,
                allow_write=args.allow_write,
            )
    except (BindingError, SandboxError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())