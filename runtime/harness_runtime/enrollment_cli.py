from __future__ import annotations

import argparse
import json
from pathlib import Path

from .project_enrollment import (
    EnrollmentAdapters,
    EnrollmentError,
    EnrollmentRequest,
    HermesConfig,
    LocalFilesystem,
    LocalSubprocess,
    apply_enrollment,
    plan_enrollment,
)


def _add_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", required=True)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument("--discord-parent-channel-id", required=True)
    parser.add_argument("--hermes-executable", required=True, type=Path)
    parser.add_argument("--hermes-config-target", required=True, type=Path)
    parser.add_argument("--idempotency-key", required=True)


def _request(args: argparse.Namespace) -> EnrollmentRequest:
    return EnrollmentRequest(
        version=args.version,
        project_slug=args.project_slug,
        canonical_root=args.canonical_root,
        discord_parent_channel_id=args.discord_parent_channel_id,
        hermes_executable=args.hermes_executable,
        hermes_config_target=args.hermes_config_target,
        idempotency_key=args.idempotency_key,
    )


def _local_adapters() -> EnrollmentAdapters:
    subprocess_adapter = LocalSubprocess()
    return EnrollmentAdapters(
        filesystem=LocalFilesystem(),
        subprocess=subprocess_adapter,
        config=HermesConfig(subprocess_adapter),
    )


def main(
    argv: list[str] | None = None,
    *,
    adapters: EnrollmentAdapters | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="harness-project-enroll",
        description="Plan or apply an explicit trusted Harness project enrollment event.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        _add_request_arguments(commands.add_parser(name))
    args = parser.parse_args(argv)

    try:
        operation = plan_enrollment if args.command == "plan" else apply_enrollment
        result = operation(_request(args), adapters or _local_adapters())
    except (EnrollmentError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())