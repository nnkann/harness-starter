import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/daily_memory_audit_driver.py"
SCHEMA = ROOT / "contracts/daily-memory-dispatch-receipt.v1.schema.json"
spec = importlib.util.spec_from_file_location("daily_memory_audit_driver", TOOL)
assert spec is not None and spec.loader is not None
driver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = driver
spec.loader.exec_module(driver)


def packet():
    body = {
        "intent": driver.INTENT,
        "collection_ref": "daily:2026-07-24",
        "changes": [
            {"layer_id": "gbrain", "classes": []},
            {"layer_id": "harness_brain", "classes": []},
            {"layer_id": "honcho", "classes": ["pointer_integrity_transition"]},
        ],
    }
    return {**body, "packet_digest": hashlib.sha256(driver.canonical_bytes(body)).hexdigest()}


def input_receipt(delta=True):
    value = {
        "schema": driver.INPUT_SCHEMA,
        "state": {
            "collection_ref": "daily:2026-07-24",
            "layers": [{
                "layer_id": "honcho", "availability": "available",
                "canonical_source_ref": "source:honcho", "canonical_revision": "sha256:" + "a" * 64,
                "pointer_ref": "pointer:honcho", "pointer_digest": "a" * 64,
                "pointer_integrity": "invalid", "canonical_index_ref": "index:honcho",
                "canonical_index_revision": "sha256:" + "b" * 64, "canonical_index_aligned": True,
                "verified_outcome_eligible": False, "source_backed_conflicts": [],
            }, {
                "layer_id": "harness_brain", "availability": "unavailable",
                "canonical_source_ref": None, "canonical_revision": None,
                "pointer_ref": None, "pointer_digest": None,
                "pointer_integrity": "unknown", "canonical_index_ref": None,
                "canonical_index_revision": None, "canonical_index_aligned": None,
                "verified_outcome_eligible": None, "source_backed_conflicts": [],
            }, {
                "layer_id": "gbrain", "availability": "unavailable",
                "canonical_source_ref": None, "canonical_revision": None,
                "pointer_ref": None, "pointer_digest": None,
                "pointer_integrity": "unknown", "canonical_index_ref": None,
                "canonical_index_revision": None, "canonical_index_aligned": None,
                "verified_outcome_eligible": None, "source_backed_conflicts": [],
            }],
        },
        "comparison": {
            "baseline": False, "meaningful_delta": delta,
            "delta_classes": ["pointer_integrity_transition"] if delta else [],
            "disposition": "delta" if delta else "clean",
        },
        "consumer": {
            "intent": driver.INTENT if delta else None,
            "invocation_count": 1 if delta else 0,
            "packet": packet() if delta else None,
        },
    }
    return value


class DailyMemoryAuditDriverTests(unittest.TestCase):
    def execute(self, value, existing=None, returncode=0, run_error=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        input_path = Path(directory.name) / "c2.json"
        receipt_path = Path(directory.name) / "c3.json"
        input_path.write_bytes(driver.canonical_bytes(value))
        if existing is not None:
            receipt_path.write_bytes(driver.canonical_bytes(existing))
        completed = subprocess.CompletedProcess(driver.ARGV, returncode)
        run_effect = run_error if run_error is not None else None
        with mock.patch.object(driver.subprocess, "run", return_value=completed, side_effect=run_effect) as run:
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                result = driver.run(input_path, receipt_path)
        return result, run, input_path, receipt_path, stdout.getvalue(), stderr.getvalue()

    def test_clean_exits_zero_silent_without_dispatch_or_receipt(self):
        result, run, _, receipt, stdout, stderr = self.execute(input_receipt(False))
        self.assertEqual((result, stdout, stderr), (0, "", ""))
        run.assert_not_called()
        self.assertFalse(receipt.exists())

    def test_delta_writes_predispatch_then_exact_argv_with_compact_packet_only(self):
        writes = []
        original = driver.atomic_write
        with mock.patch.object(driver, "atomic_write", side_effect=lambda value, path: (writes.append(copy.deepcopy(value)), original(value, path))[1]):
            result, run, input_path, receipt_path, stdout, stderr = self.execute(input_receipt())
        self.assertEqual((result, stdout, stderr), (0, "", ""))
        run.assert_called_once_with(
            ["hermes", "-p", "sia"], input=driver.canonical_bytes(packet()),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        self.assertEqual(writes[0]["terminal_status"], "pending")
        self.assertIsNone(writes[0]["exit_code"])
        final = json.loads(receipt_path.read_text())
        self.assertEqual(final["terminal_status"], "succeeded")
        self.assertEqual(final["exit_code"], 0)
        self.assertEqual(final["input_receipt_digest"], hashlib.sha256(input_path.read_bytes()).hexdigest())
        self.assertNotIn("state", final)
        self.assertNotIn("stderr", final)

    def test_invalid_packet_digest_fails_closed(self):
        value = input_receipt()
        value["consumer"]["packet"]["packet_digest"] = "0" * 64
        with self.assertRaises(driver.DispatchError):
            self.execute(value)

    def test_same_packet_digest_is_never_dispatched_twice(self):
        first = input_receipt()
        result, run, input_path, receipt_path, _, _ = self.execute(first)
        self.assertEqual(result, 0)
        existing = json.loads(receipt_path.read_text())
        result, replay_run, _, replay_receipt, _, _ = self.execute(first, existing=existing)
        self.assertEqual(result, 0)
        replay_run.assert_not_called()
        self.assertEqual(json.loads(replay_receipt.read_text()), existing)
        run.assert_called_once()

    def test_child_outcomes_store_only_normalized_exit_codes(self):
        for returncode, expected_result, expected_status, expected_exit_code in (
            (0, 0, "succeeded", 0),
            (1, 1, "failed", 1),
            (255, 255, "failed", 255),
            (-9, 1, "failed", None),
            (256, 1, "failed", None),
        ):
            with self.subTest(returncode=returncode):
                result, run, _, receipt_path, stdout, stderr = self.execute(
                    input_receipt(), returncode=returncode,
                )
                self.assertEqual((result, stdout, stderr), (expected_result, "", ""))
                run.assert_called_once()
                receipt = json.loads(receipt_path.read_text())
                self.assertEqual(
                    (receipt["terminal_status"], receipt["exit_code"]),
                    (expected_status, expected_exit_code),
                )
                self.assertNotIn("returncode", receipt)
                self.assertNotIn("signal", receipt)

    def test_oserror_branch_records_failed_with_null_exit_code(self):
        result, run, _, receipt_path, stdout, stderr = self.execute(
            input_receipt(), run_error=OSError("launch failed"),
        )
        self.assertEqual((result, stdout, stderr), (1, "", ""))
        run.assert_called_once()
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual((receipt["terminal_status"], receipt["exit_code"]), ("failed", None))

    def test_predispatch_crash_state_becomes_unknown_without_retry(self):
        value = input_receipt()
        raw = driver.canonical_bytes(value)
        prepared = driver._dispatch_receipt(hashlib.sha256(raw).hexdigest(), packet()["packet_digest"], "pending", None)
        result, run, _, receipt_path, _, _ = self.execute(value, existing=prepared)
        self.assertEqual(result, 0)
        run.assert_not_called()
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual((receipt["terminal_status"], receipt["exit_code"]), ("unknown", None))

    def test_existing_receipt_validator_enforces_status_exit_code_matrix(self):
        valid = driver._dispatch_receipt("a" * 64, "b" * 64, "failed", 255)
        self.assertEqual(driver._validate_dispatch_receipt(valid), valid)
        for status, exit_code in (
            ("succeeded", 1),
            ("failed", 0),
            ("failed", -9),
            ("failed", 256),
            ("pending", 1),
            ("unknown", 1),
        ):
            with self.subTest(status=status, exit_code=exit_code), self.assertRaises(driver.DispatchError):
                driver._validate_dispatch_receipt({
                    **valid, "terminal_status": status, "exit_code": exit_code,
                })

    def test_schema_is_closed_and_runtime_receipt_is_not_source_artifact(self):
        schema = json.loads(SCHEMA.read_text())
        validator = Draft202012Validator(schema)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["argv"]["maxItems"], 3)
        valid = driver._dispatch_receipt("a" * 64, "b" * 64, "succeeded", 0)
        validator.validate(valid)
        for status, exit_code in (
            ("succeeded", 1),
            ("failed", 0),
            ("pending", 1),
            ("unknown", 1),
        ):
            with self.subTest(status=status, exit_code=exit_code):
                fixture = {**valid, "terminal_status": status, "exit_code": exit_code}
                self.assertFalse(validator.is_valid(fixture))
        self.assertFalse((ROOT / ".harness/hermes/state/daily-memory/c3-dispatch-receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
