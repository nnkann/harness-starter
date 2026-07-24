import copy
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / ".harness/hermes/tools/daily_memory_daily.py"
COLLECTOR = ROOT / ".harness/hermes/tools/daily_memory_collector.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


daily = load("daily_memory_daily", ENTRY)
collector = load("daily_memory_collector_for_daily", COLLECTOR)


def declaration(revision="sha256:" + "a" * 64):
    return {
        "schema": collector.DECLARATION_SCHEMA,
        "collection_ref": "daily:2026-07-24",
        "materialized_date": "2026-07-24",
        "layers": [{
            "layer_id": "harness_brain",
            "availability": "available",
            "canonical_source_ref": "/canonical/source.md",
            "canonical_revision": revision,
            "pointer_ref": "/canonical/pointer.md",
            "pointer_digest": "b" * 64,
            "pointer_integrity": "valid",
            "canonical_index_ref": "/canonical/index.yml",
            "canonical_index_revision": "sha256:" + "c" * 64,
            "canonical_index_aligned": True,
            "verified_outcome_eligible": False,
            "conflicts": [],
        }, {
            "layer_id": "honcho", "availability": "unavailable",
            "canonical_source_ref": None, "canonical_revision": None,
            "pointer_ref": None, "pointer_digest": None,
            "pointer_integrity": "unknown", "canonical_index_ref": None,
            "canonical_index_revision": None, "canonical_index_aligned": None,
            "verified_outcome_eligible": None, "conflicts": [],
        }, {
            "layer_id": "gbrain", "availability": "unavailable",
            "canonical_source_ref": None, "canonical_revision": None,
            "pointer_ref": None, "pointer_digest": None,
            "pointer_integrity": "unknown", "canonical_index_ref": None,
            "canonical_index_revision": None, "canonical_index_aligned": None,
            "verified_outcome_eligible": None, "conflicts": [],
        }],
    }


class DailyMemoryEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        state = Path(self.directory.name)
        self.declaration_path = state / "declaration.json"
        self.c2_path = state / "c2.json"
        self.c3_path = state / "c3.json"
        self.current = declaration()
        self.driver_calls = []

    def modules(self, driver_result=0, stale=False):
        def materialize(path):
            Path(path).write_bytes(collector.canonical_bytes(copy.deepcopy(self.current)))

        def validate(value):
            if stale:
                raise ValueError("stale")
            if value["materialized_date"] != "2026-07-24":
                raise ValueError("stale")

        materializer = SimpleNamespace(run=materialize, validate_fresh=validate)

        def dispatch(input_path, receipt_path):
            self.driver_calls.append(Path(input_path).read_bytes())
            if driver_result:
                return driver_result
            receipt = json.loads(Path(input_path).read_text())
            packet_digest = receipt["consumer"]["packet"]["packet_digest"]
            Path(receipt_path).write_text(json.dumps({
                "schema": "harness.memory.daily-dispatch-receipt.v1",
                "packet_digest": packet_digest,
                "terminal_status": "succeeded",
                "exit_code": 0,
            }))
            return 0

        driver = SimpleNamespace(run=dispatch)
        return {"daily_memory_materializer": materializer, "daily_memory_collector": collector, "daily_memory_audit_driver": driver}

    def execute(self, modules):
        with mock.patch.object(daily, "_load", side_effect=lambda name: modules[name]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                result = daily.run(self.declaration_path, self.c2_path, self.c3_path)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_clean_is_silent_exit_zero_and_never_invokes_driver(self):
        result, stdout, stderr = self.execute(self.modules())
        self.assertEqual((result, stdout, stderr), (0, "", ""))
        self.assertEqual(self.driver_calls, [])
        result, stdout, stderr = self.execute(self.modules())
        self.assertEqual((result, stdout, stderr), (0, "", ""))
        self.assertEqual(self.driver_calls, [])
        settled = self.c2_path.read_bytes()
        self.assertEqual(self.execute(self.modules())[0], 0)
        self.assertEqual(self.c2_path.read_bytes(), settled)

    def test_one_delta_invokes_driver_once_then_replay_is_clean(self):
        self.assertEqual(self.execute(self.modules())[0], 0)
        self.current = declaration("sha256:" + "d" * 64)
        result, stdout, stderr = self.execute(self.modules())
        self.assertEqual((result, stdout, stderr), (0, "", ""))
        self.assertEqual(len(self.driver_calls), 1)
        promoted = self.c2_path.read_bytes()
        receipt = json.loads(promoted)
        self.assertTrue(receipt["comparison"]["meaningful_delta"])
        self.assertEqual(self.execute(self.modules())[0], 0)
        self.assertEqual(len(self.driver_calls), 1)

    def test_dispatch_failure_is_nonzero_and_preserves_prior_c2(self):
        self.assertEqual(self.execute(self.modules())[0], 0)
        prior = self.c2_path.read_bytes()
        self.current = declaration("sha256:" + "e" * 64)
        result, stdout, stderr = self.execute(self.modules(driver_result=23))
        self.assertEqual((result, stdout, stderr), (1, "", ""))
        self.assertEqual(len(self.driver_calls), 1)
        self.assertEqual(self.c2_path.read_bytes(), prior)

    def test_stale_materialization_fails_closed_and_preserves_prior_c2(self):
        self.assertEqual(self.execute(self.modules())[0], 0)
        prior = self.c2_path.read_bytes()
        with self.assertRaises(ValueError):
            self.execute(self.modules(stale=True))
        self.assertEqual(self.c2_path.read_bytes(), prior)
        self.assertEqual(self.driver_calls, [])


if __name__ == "__main__":
    unittest.main()
