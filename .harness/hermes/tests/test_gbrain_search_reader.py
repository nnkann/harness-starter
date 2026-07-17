"""Unit tests for the bounded GBrain search reader."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


_READER_PATH = (
    Path(__file__).resolve().parents[1] / "readers" / "gbrain_search_reader.py"
)
_SPEC = importlib.util.spec_from_file_location("gbrain_search_reader", _READER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
reader_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(reader_module)


class GBrainSearchReaderTests(unittest.TestCase):
    def test_uses_absolute_gbrain_executable_constant(self) -> None:
        self.assertEqual(reader_module._GBRAIN, "/Users/kann/.bun/bin/gbrain")
        self.assertTrue(Path(reader_module._GBRAIN).is_absolute())

    def test_invokes_search_with_query_and_preserves_process_result(self) -> None:
        completed = SimpleNamespace(
            stdout="search result",
            stderr="warning",
            returncode=7,
        )
        with patch.object(reader_module.subprocess, "run", return_value=completed) as run:
            result = reader_module.create_gbrain_search_reader(timeout=3.0)(
                "needle", ["--limit", "1"]
            )

        self.assertEqual(
            run.call_args.args[0][:3],
            [reader_module._GBRAIN, "search", "needle"],
        )
        self.assertEqual(result["stdout"], completed.stdout)
        self.assertEqual(result["returncode"], completed.returncode)


if __name__ == "__main__":
    unittest.main()
