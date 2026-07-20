from __future__ import annotations

import argparse
import json
from pathlib import Path

from .guided_capability import (
    CapabilityError,
    apply_capability,
    discover_capability,
    plan_capability,
    status_capability,
)


def _add_scope(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("capability_id")
    parser.add_argument("project_root", type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness-guided-capability",
        description="Inspect and gate typed provider capabilities without generic command input.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("discovery", "status"):
        readonly = commands.add_parser(name)
        _add_scope(readonly)
        readonly.add_argument("--state-dir", required=True, type=Path)
    _add_scope(commands.add_parser("plan"))
    apply = commands.add_parser("apply")
    _add_scope(apply)
    apply.add_argument("--approval-file", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "discovery":
            result = discover_capability(args.project_root, args.capability_id, state_dir=args.state_dir)
        elif args.command == "plan":
            result = plan_capability(args.project_root, args.capability_id)
        elif args.command == "status":
            result = status_capability(args.project_root, args.capability_id, state_dir=args.state_dir)
        else:
            approval = json.loads(args.approval_file.read_text(encoding="utf-8"))
            result = apply_capability(args.project_root, args.capability_id, approval=approval, executors={})
    except (CapabilityError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
