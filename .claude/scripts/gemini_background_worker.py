#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemini CLI background worker.

PreToolUse hook은 빨리 반환해야 한다. Gemini CLI 실행, stdin 전달,
stdout/stderr 기록은 이 worker가 별도 프로세스에서 맡는다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: gemini_background_worker.py <gemini-path> <prompt-path> <result-path>",
            file=sys.stderr,
        )
        return 2

    gemini_path = argv[1]
    prompt_path = Path(argv[2])
    result_path = Path(argv[3])

    prompt_arg = "stdin의 CPS Solution 맥락 diff를 검토하라."
    try:
        with (
            prompt_path.open("r", encoding="utf-8") as prompt_in,
            result_path.open("a", encoding="utf-8") as out,
        ):
            result = subprocess.run(
                [
                    gemini_path,
                    "--skip-trust",
                    "--extensions", "none",
                    "--output-format", "text",
                    "-p", prompt_arg,
                ],
                stdin=prompt_in,
                stdout=out,
                stderr=out,
                text=True,
                cwd=str(Path(__file__).resolve().parent.parent.parent),
                timeout=180,
            )
            return result.returncode
    except subprocess.TimeoutExpired:
        with result_path.open("a", encoding="utf-8") as out:
            out.write("\n[gemini-timeout] 180초 안에 응답하지 않아 종료됨.\n")
        return 124
    except OSError as exc:
        with result_path.open("a", encoding="utf-8") as out:
            out.write(f"\n[gemini-error] {exc}\n")
        return 1
    finally:
        try:
            prompt_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
