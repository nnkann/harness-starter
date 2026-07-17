from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import ReceiptValidationError, analysis_input, execute, readback, schema_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness-runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema")
    run = commands.add_parser("run")
    run.add_argument("--case", required=True)
    run.add_argument("--consumer", required=True)
    run.add_argument("--body-file", required=True, type=Path)
    run.add_argument("--worktree-cwd", required=True, type=Path)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    read = commands.add_parser("readback")
    read.add_argument("--case", required=True)
    read.add_argument("--consumer")
    analysis = commands.add_parser("analysis-input")
    analysis.add_argument("--case", required=True)
    analysis.add_argument("--consumer", default="anubis")
    analysis.add_argument("--output-limit", type=int, default=16384)
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(schema_text(), end="")
        elif args.command == "run":
            command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            print(
                json.dumps(
                    execute(
                        args.case,
                        args.consumer,
                        args.body_file.read_bytes(),
                        command,
                        worktree_cwd=args.worktree_cwd,
                    ),
                    sort_keys=True,
                )
            )
        elif args.command == "readback":
            print(json.dumps(readback(args.case, args.consumer), sort_keys=True))
        else:
            print(json.dumps(analysis_input(args.case, args.consumer, args.output_limit), sort_keys=True))
    except (OSError, ReceiptValidationError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
