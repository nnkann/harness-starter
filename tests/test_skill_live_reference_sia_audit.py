import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/skill_live_reference_sia_audit.py"
spec = importlib.util.spec_from_file_location("skill_live_reference_sia_audit", TOOL)
assert spec is not None and spec.loader is not None
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
spec.loader.exec_module(collector)

A = "a" * 64
B = "b" * 64


def result(schema, result_id, receipt, **overrides):
    value = {
        "schema": schema,
        "result_id": result_id,
        "source_receipt": receipt,
        "availability": "available",
        "pointer_digest": A,
        "pointer_integrity": "valid",
        "source_backed_conflicts": [],
        "verified_outcome_eligible": False,
    }
    value.update(overrides)
    return value


class SkillLiveReferenceSiaAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.brain = base / "harness-brain"
        self.brain.mkdir()
        (self.brain / "README.md").write_text("canonical\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.brain)], check=True)
        subprocess.run(["git", "-C", str(self.brain), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.brain), "-c", "user.name=test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture",
        ], check=True)
        self.revision = subprocess.run(
            ["git", "-C", str(self.brain), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        self.fake_root = base / "fake-gbrain"
        self.fake_root.mkdir()
        self.status_file = self.fake_root / "status.json"
        self.executable = self.fake_root / "gbrain"
        self.executable.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "assert sys.argv[1:3] == ['call', 'sources_status']\n"
            "assert json.loads(sys.argv[3]) == {'id': 'harness-brain'}\n"
            "print(pathlib.Path(os.environ['FAKE_GBRAIN_STATUS']).read_text())\n"
            "print('timestamp ranking token=top-secret', file=sys.stderr)\n",
            encoding="utf-8",
        )
        self.executable.chmod(0o755)
        self.write_status()
        os.environ["FAKE_GBRAIN_STATUS"] = str(self.status_file)
        self.state_dir = base / "external-state"
        self.c1_path = base / "c1.json"
        self.c2_path = base / "c2.json"
        self.c1 = result(collector.C1_SCHEMA, "c1:1", "receipt:c1:1")
        self.c2 = result(collector.C2_SCHEMA, "c2:1", "receipt:c2:1")
        self.write_inputs()

    def tearDown(self):
        os.environ.pop("FAKE_GBRAIN_STATUS", None)
        self.temp.cleanup()

    def write_status(self, *, revision=None, path=None, clone_state="healthy"):
        self.status_file.write_text(json.dumps({
            "id": "harness-brain",
            "name": "ignored",
            "local_path": str(path or self.brain),
            "page_count": 1,
            "last_sync_at": "2099-01-01T00:00:00Z",
            "last_commit": revision or self.revision,
            "clone_state": clone_state,
            "ranking": ["ignored"],
        }), encoding="utf-8")

    def write_inputs(self):
        self.c1_path.write_text(json.dumps(self.c1), encoding="utf-8")
        self.c2_path.write_text(json.dumps(self.c2), encoding="utf-8")

    def collect(self, second=0, **overrides):
        arguments = {
            "harness_brain_root": self.brain,
            "gbrain_executable": self.executable,
            "source_id": "harness-brain",
            "c1_result_path": self.c1_path,
            "c2_result_path": self.c2_path,
            "harness_state_dir": self.state_dir,
            "timeout": 2,
            "now": datetime(2026, 7, 30, 1, 2, second, tzinfo=timezone.utc),
        }
        arguments.update(overrides)
        return collector.collect(**arguments)

    def test_state_dir_is_required_and_rejects_repo_or_brain_descendants(self):
        repo_candidate = ROOT / ".maat-c3-forbidden-state-test"
        brain_candidate = self.brain / ".maat-c3-forbidden-state-test"
        before = (repo_candidate.exists(), brain_candidate.exists())
        for path in (None, repo_candidate, brain_candidate):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "HARNESS_STATE_DIR"):
                self.collect(harness_state_dir=path)
        self.assertEqual((repo_candidate.exists(), brain_candidate.exists()), before)

    def test_clean_has_false_flags_external_receipt_and_no_repo_runtime_write(self):
        receipt, code = self.collect()
        self.assertEqual(code, 0)
        self.assertFalse(receipt["delta"])
        self.assertFalse(receipt["sia_invoked"])
        self.assertIsNone(receipt["review_packet"])
        self.assertEqual(receipt["delta_classes"], [])
        persisted = list((self.state_dir / "receipts").glob("*.json"))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(json.loads(persisted[0].read_text())["receipt_id"], receipt["receipt_id"])
        self.assertTrue((self.state_dir / "state.json").is_file())

    def test_repeated_unavailable_and_receipt_timestamp_ranking_noise_stays_clean(self):
        self.c2 = result(
            collector.C2_SCHEMA, "c2:unavailable:1", "receipt:c2:unavailable:1",
            availability="unavailable", pointer_digest=None, pointer_integrity="unknown",
            verified_outcome_eligible=None,
        )
        self.write_inputs()
        first, _ = self.collect(0)
        self.c2["result_id"] = "c2:unavailable:2"
        self.c2["source_receipt"] = "receipt:c2:unavailable:2"
        self.write_inputs()
        second, code = self.collect(1)
        self.assertEqual(code, 0)
        self.assertFalse(first["delta"])
        self.assertFalse(second["delta"])
        encoded = json.dumps(second)
        self.assertNotIn("ranking", encoded)
        self.assertNotIn("top-secret", encoded)
        self.assertNotIn("last_sync", encoded)

    def test_honcho_availability_transition(self):
        self.collect(0)
        self.c2.update(
            availability="unavailable", pointer_digest=None, pointer_integrity="unknown",
            verified_outcome_eligible=None,
        )
        self.write_inputs()
        receipt, _ = self.collect(1)
        self.assertIn("honcho_availability_transition", receipt["delta_classes"])

    def test_pointer_integrity_change(self):
        self.collect(0)
        self.c1["pointer_integrity"] = "invalid"
        self.write_inputs()
        receipt, _ = self.collect(1)
        self.assertEqual(receipt["delta_classes"], ["pointer_integrity_change"])

    def test_source_backed_conflict_new_and_resolved(self):
        self.collect(0)
        conflict = {"conflict_id": "conflict:1", "source_receipt": "receipt:source:1", "source_digest": B}
        self.c1["source_backed_conflicts"] = [conflict]
        self.write_inputs()
        added, _ = self.collect(1)
        self.assertEqual(added["delta_classes"], ["source_backed_conflict_new"])
        self.c1["source_backed_conflicts"] = []
        self.write_inputs()
        resolved, _ = self.collect(2)
        self.assertEqual(resolved["delta_classes"], ["source_backed_conflict_resolved"])

    def test_verified_outcome_eligibility_change(self):
        self.collect(0)
        self.c2["verified_outcome_eligible"] = True
        self.write_inputs()
        receipt, _ = self.collect(1)
        self.assertEqual(receipt["delta_classes"], ["verified_outcome_eligibility_change"])

    def test_delta_packet_is_single_bounded_digest_and_receipt_only_without_side_effect(self):
        self.collect(0)
        self.c1["pointer_digest"] = B
        self.write_inputs()
        with patch.object(collector.subprocess, "run", wraps=subprocess.run) as run:
            receipt, code = self.collect(1)
        self.assertEqual(code, 0)
        self.assertTrue(receipt["delta"])
        self.assertFalse(receipt["sia_invoked"])
        self.assertEqual(set(receipt["review_packet"]), {"before_digest", "after_digest", "source_receipts"})
        self.assertTrue(all(len(receipt["review_packet"][key]) == 64 for key in ("before_digest", "after_digest")))
        self.assertLessEqual(len(receipt["review_packet"]["source_receipts"]), 4)
        self.assertEqual(len(run.call_args_list), 2)
        self.assertTrue(all(call.args[0][0] in {"git", str(self.executable)} for call in run.call_args_list))

    def test_projection_mismatch_and_source_path_mismatch_are_retained(self):
        self.write_status(revision="b" * 40, path=self.fake_root)
        receipt, code = self.collect()
        self.assertEqual(code, 0)
        self.assertEqual(receipt["delta_classes"], ["projection_canonical_mismatch", "resolver_audit_issue"])

    def test_strict_input_and_prior_state_fail_closed_without_secret_leak_or_state_advance(self):
        self.c1["raw_transcript"] = "token=top-secret"
        self.write_inputs()
        malformed, code = self.collect(0)
        self.assertEqual(code, 2)
        self.assertEqual(malformed["failure_reason"], "c1_result_malformed")
        self.assertNotIn("top-secret", json.dumps(malformed))
        self.assertFalse((self.state_dir / "state.json").exists())

        self.c1.pop("raw_transcript")
        self.write_inputs()
        self.collect(1)
        before = (self.state_dir / "state.json").read_bytes()
        state = json.loads(before)
        state["snapshot_digest"] = B
        (self.state_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
        failed, code = self.collect(2)
        self.assertEqual(code, 2)
        self.assertEqual(failed["failure_reason"], "prior_state_malformed")
        self.assertNotEqual((self.state_dir / "state.json").read_bytes(), before)
        self.assertEqual(json.loads((self.state_dir / "state.json").read_text())["snapshot_digest"], B)

    def test_input_receipt_contains_only_digests_and_source_receipt_ids_not_payload(self):
        receipt, _ = self.collect()
        self.assertEqual(receipt["source_receipts"], ["receipt:c1:1", "receipt:c2:1"])
        self.assertEqual(set(receipt["input_digests"]), {"c1", "c2"})
        self.assertNotIn("pointer_digest", receipt)
        self.assertNotIn("source_backed_conflicts", receipt)

    def test_cli_requires_environment_variable(self):
        with patch.dict(os.environ, {}, clear=True):
            code = collector.main([
                "--harness-brain-root", str(self.brain), "--gbrain-executable", str(self.executable),
                "--source-id", "harness-brain", "--c1-result", str(self.c1_path),
                "--c2-result", str(self.c2_path),
            ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
