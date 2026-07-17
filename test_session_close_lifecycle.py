from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent
ROUTER = REPO / ".harness/project/scripts/router"
SCHEMA_PATH = REPO / ".harness/project/schemas/session_close_state.v1.schema.json"
if str(ROUTER) not in sys.path:
    sys.path.insert(0, str(ROUTER))

import session_close_lifecycle as lifecycle


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def rehash_history(state):
    previous = None
    for entry in state["transition_history"]:
        entry["previous_transition_hash"] = previous
        entry["transition_hash"] = hashlib.sha256(canonical_bytes({
            key: value for key, value in entry.items() if key != "transition_hash"
        })).hexdigest()
        previous = entry["transition_hash"]


class SessionCloseLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.home = Path(self.tmp.name) / "home"
        self.repo.mkdir()
        self.home.mkdir()
        self.snapshot = {
            "session_id": "session-1",
            "thread_id": "thread-1",
            "root_goal_id": "goal-1",
            "task_AC_result": "passed",
            "unresolved_holds": [],
        }
        self.target = {
            "repository": "nousresearch/harness-starter",
            "remote_ref": "refs/heads/session-close",
            "canonical_path": "session-close/session-1.json",
        }
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.schema_validator = Draft202012Validator(self.schema)
        self.target_validator = Draft202012Validator({
            "$schema": self.schema["$schema"],
            "$defs": self.schema["$defs"],
            "$ref": "#/$defs/canonicalTarget",
        })
        self.receipt_validators = {
            name: Draft202012Validator({
                "$schema": self.schema["$schema"],
                "$defs": self.schema["$defs"],
                "$ref": f"#/$defs/{name}",
            })
            for name in ("durableReceipt", "propagationReceipt")
        }

    def requested(self, lifecycle_id="close-1"):
        return lifecycle.request_close(self.repo, lifecycle_id, self.snapshot, self.target)

    def stage_to_pending(self, lifecycle_id="close-1"):
        state = self.requested(lifecycle_id)
        state = lifecycle.stage_snapshot(state)
        return lifecycle.verify_snapshot_readback(state)

    def canonical_tuple(self, state):
        snapshot = state["snapshot"]
        return {
            "repository": state["canonical_target"]["repository"],
            "remote_ref": state["canonical_target"]["remote_ref"],
            "pushed_sha": "a" * 40,
            "canonical_path": state["canonical_target"]["canonical_path"],
            "snapshot_id": snapshot["snapshot_id"],
            "snapshot_sha256": snapshot["sha256"],
            "independent_readback_sha256": snapshot["readback"]["sha256"],
        }

    def durable_receipt(self, state, **changes):
        receipt = {
            **self.canonical_tuple(state),
            "verified_at": "2026-07-16T12:00:00Z",
            "writer_identity": "git-push-writer",
            "reader_identity": "git-readback-reader",
        }
        receipt.update(changes)
        return receipt

    def propagation_receipt(self, state, **changes):
        receipt = {
            **self.canonical_tuple(state),
            "durable_receipt_hash": state["durable_receipt"]["receipt_hash"],
            "propagated_at": "2026-07-16T12:01:00Z",
            "propagator_identity": "external-propagator",
            "reader_identity": "external-canonical-reader",
        }
        receipt.update(changes)
        return receipt

    def component_receipts(self, state):
        return [
            {
                "component": component,
                "status": "preserved",
                "lifecycle_id": state["lifecycle_id"],
                "session_id": state["session_id"],
                "snapshot_id": state["snapshot"]["snapshot_id"],
                "snapshot_sha256": state["snapshot"]["sha256"],
                "verified_at": "2026-07-16T12:02:00Z",
            }
            for component in ("session", "database", "transcript", "route")
        ]

    def schema_accepts(self, state):
        return self.schema_validator.is_valid(state)

    def assert_valid(self, state):
        self.assertTrue(self.schema_accepts(state))
        self.assertEqual(state, lifecycle.load_and_validate_state(state))

    def test_canonical_target_nested_snapshot_and_state_sequence(self):
        requested = self.requested()
        self.assertEqual(self.target, requested["canonical_target"])
        self.assertEqual({"sha256": None, "byte_length": None}, requested["snapshot"]["readback"])
        self.assertIsNone(requested["snapshot"]["relative_path"])
        staged = lifecycle.stage_snapshot(requested)
        pending = lifecycle.verify_snapshot_readback(staged)
        candidate = self.repo / pending["snapshot"]["relative_path"]
        expected = canonical_bytes(self.snapshot)
        digest = hashlib.sha256(expected).hexdigest()
        self.assertEqual(expected, candidate.read_bytes())
        self.assertEqual(digest, pending["snapshot"]["snapshot_id"])
        self.assertEqual(digest, pending["snapshot"]["sha256"])
        self.assertEqual({"sha256": digest, "byte_length": len(expected)}, pending["snapshot"]["readback"])
        self.assertEqual("durable_pending", pending["state"])
        self.assertEqual(["requested", "snapshot_staged", "durable_pending"], [item["to_state"] for item in pending["transition_history"]])
        self.assertEqual(pending, lifecycle.load_and_validate_state(self.repo, "close-1"))
        self.assert_valid(pending)

    def test_canonical_target_jsonschema_accepts_heads_and_rejects_noncanonical_forms(self):
        self.target_validator.validate(self.target)
        invalid = {
            "tag": {**self.target, "remote_ref": "refs/tags/v1"},
            "url": {**self.target, "repository": "https://github.com/nousresearch/harness-starter"},
            "absolute": {**self.target, "canonical_path": "/tmp/snapshot.json"},
            "dot": {**self.target, "canonical_path": "session-close/./snapshot.json"},
            "dotdot": {**self.target, "canonical_path": "session-close/../snapshot.json"},
            "staging": {**self.target, "canonical_path": ".harness/project/runs/session_close_staging/snapshot.json"},
            "legacy_relative_path": {
                "repository": self.target["repository"],
                "remote_ref": self.target["remote_ref"],
                "relative_path": self.target["canonical_path"],
            },
            "extra": {**self.target, "extra": True},
        }
        for name, target in invalid.items():
            with self.subTest(name=name):
                self.assertFalse(self.target_validator.is_valid(target))
                with self.assertRaises((TypeError, ValueError)):
                    lifecycle.request_close(self.repo, f"bad-{name}", self.snapshot, target)

    def test_candidate_is_rehashed_for_mapping_and_every_reducer(self):
        pending = self.stage_to_pending()
        candidate = self.repo / pending["snapshot"]["relative_path"]
        candidate.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            lifecycle.load_and_validate_state(pending)
        for reducer in (
            lambda: lifecycle.record_durable_receipt(pending, self.durable_receipt(pending)),
            lambda: lifecycle.record_propagation_receipt(pending, {}),
            lambda: lifecycle.mark_close_eligible(pending, []),
            lambda: lifecycle.mark_prune_eligible(pending),
        ):
            with self.subTest(reducer=reducer), self.assertRaises(ValueError):
                reducer()

    def test_candidate_path_substitution_collision_and_nested_readback_fail_closed(self):
        requested = self.requested()
        staged = lifecycle.stage_snapshot(requested)
        candidate = self.repo / staged["snapshot"]["relative_path"]
        with self.assertRaises((FileExistsError, ValueError)):
            lifecycle.stage_snapshot(requested)
        escaped = copy.deepcopy(staged)
        escaped["snapshot"]["relative_path"] = "outside.json"
        with self.assertRaises(ValueError):
            lifecycle.verify_snapshot_readback(escaped)
        candidate.unlink()
        candidate.symlink_to(self.repo / "outside.json")
        with self.assertRaises(ValueError):
            lifecycle.verify_snapshot_readback(staged)

    def test_persisted_history_prefix_and_evidence_refs_are_immutable(self):
        pending = self.stage_to_pending()
        forged = copy.deepcopy(pending)
        forged["transition_history"][1]["transitioned_at"] = "2026-07-16T00:00:00Z"
        rehash_history(forged)
        forged["updated_at"] = forged["transition_history"][-1]["transitioned_at"]
        with self.assertRaises(ValueError):
            lifecycle.record_durable_receipt(forged, self.durable_receipt(forged))

        durable = lifecycle.record_durable_receipt(pending, self.durable_receipt(pending))
        changed_evidence = copy.deepcopy(durable)
        changed_evidence["durable_receipt"]["writer_identity"] = "replacement-writer"
        changed_evidence["durable_receipt"]["receipt_hash"] = lifecycle._receipt_hash(changed_evidence["durable_receipt"])
        with self.assertRaises(ValueError):
            lifecycle.record_propagation_receipt(changed_evidence, self.propagation_receipt(changed_evidence))

    def test_exact_seven_field_tuple_is_required_and_propagated_field_for_field(self):
        pending = self.stage_to_pending()
        tuple_fields = tuple(self.canonical_tuple(pending))
        self.assertEqual((
            "repository", "remote_ref", "pushed_sha", "canonical_path", "snapshot_id",
            "snapshot_sha256", "independent_readback_sha256",
        ), tuple_fields)
        for field in tuple_fields:
            receipt = self.durable_receipt(pending)
            receipt.pop(field)
            with self.subTest(stage="durable", field=field), self.assertRaises(ValueError):
                lifecycle.record_durable_receipt(pending, receipt)
        durable = lifecycle.record_durable_receipt(pending, self.durable_receipt(pending))
        durable_tuple = {field: durable["durable_receipt"][field] for field in tuple_fields}
        for field in tuple_fields:
            receipt = self.propagation_receipt(durable)
            receipt.pop(field)
            with self.subTest(stage="propagation", field=field), self.assertRaises(ValueError):
                lifecycle.record_propagation_receipt(durable, receipt)
        mismatches = {
            "repository": "other/repository",
            "remote_ref": "refs/heads/other",
            "pushed_sha": "b" * 40,
            "canonical_path": "other/snapshot.json",
            "snapshot_id": "0" * 64,
            "snapshot_sha256": "1" * 64,
            "independent_readback_sha256": "2" * 64,
        }
        for field, wrong_value in mismatches.items():
            with self.subTest(stage="durable-mismatch", field=field), self.assertRaises(ValueError):
                lifecycle.record_durable_receipt(pending, self.durable_receipt(pending, **{field: wrong_value}))
            with self.subTest(stage="propagation-mismatch", field=field), self.assertRaises(ValueError):
                lifecycle.record_propagation_receipt(durable, self.propagation_receipt(durable, **{field: wrong_value}))
        propagated = lifecycle.record_propagation_receipt(durable, self.propagation_receipt(durable))
        self.assertEqual(durable_tuple, {field: propagated["propagation_receipt"][field] for field in tuple_fields})
        self.assert_valid(propagated)

    def test_receipts_reject_legacy_byte_length_generic_fields_and_hash_mismatch(self):
        pending = self.stage_to_pending()
        durable = lifecycle.record_durable_receipt(pending, self.durable_receipt(pending))
        rejected_fields = (
            "snapshot_byte_length", "readback_sha256", "readback_byte_length", "sha256", "byte_length",
        )
        for field in rejected_fields:
            rejected_value = 1 if "length" in field else "0" * 64
            durable_receipt = {**durable["durable_receipt"], field: rejected_value}
            propagation_input = {**self.propagation_receipt(durable), field: rejected_value}
            propagation_receipt = dict(propagation_input)
            propagation_receipt["receipt_hash"] = lifecycle._receipt_hash(propagation_receipt)
            with self.subTest(kind="durable", field=field):
                self.assertFalse(self.receipt_validators["durableReceipt"].is_valid(durable_receipt))
                forged = copy.deepcopy(durable)
                forged["durable_receipt"] = durable_receipt
                with self.assertRaises(ValueError):
                    lifecycle.load_and_validate_state(forged)
            with self.subTest(kind="propagation", field=field):
                self.assertFalse(self.receipt_validators["propagationReceipt"].is_valid(propagation_receipt))
                with self.assertRaises(ValueError):
                    lifecycle.record_propagation_receipt(durable, propagation_input)

        propagated = lifecycle.record_propagation_receipt(durable, self.propagation_receipt(durable))
        for receipt_name in ("durable_receipt", "propagation_receipt"):
            forged = copy.deepcopy(propagated)
            forged[receipt_name]["receipt_hash"] = "0" * 64
            self.assertTrue(self.receipt_validators[
                "durableReceipt" if receipt_name == "durable_receipt" else "propagationReceipt"
            ].is_valid(forged[receipt_name]))
            with self.subTest(receipt=receipt_name), self.assertRaises(ValueError):
                lifecycle.load_and_validate_state(forged)

    def test_component_receipts_require_snapshot_sha_and_all_components(self):
        pending = self.stage_to_pending()
        durable = lifecycle.record_durable_receipt(pending, self.durable_receipt(pending))
        propagated = lifecycle.record_propagation_receipt(durable, self.propagation_receipt(durable))
        for mutation in ("missing", "wrong"):
            receipts = self.component_receipts(propagated)
            if mutation == "missing":
                receipts[0].pop("snapshot_sha256")
            else:
                receipts[0]["snapshot_sha256"] = "0" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                lifecycle.mark_close_eligible(propagated, receipts)
        close_eligible = lifecycle.mark_close_eligible(propagated, self.component_receipts(propagated))
        self.assertTrue(lifecycle.mark_prune_eligible(close_eligible))
        missing = copy.deepcopy(close_eligible)
        missing["component_close_receipts"].pop()
        self.assertFalse(lifecycle.mark_prune_eligible(missing))

    def test_schema_and_python_align_on_unknown_and_forged_states(self):
        pending = self.stage_to_pending()
        mutations = []
        for path in (("unknown",), ("canonical_target", "unknown"), ("snapshot", "unknown"), ("snapshot", "readback", "unknown"), ("transition_history", 0, "unknown")):
            value = copy.deepcopy(pending)
            target = value
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = True
            mutations.append(value)
        for value in mutations:
            with self.subTest(value=value):
                self.assertFalse(self.schema_accepts(value))
                with self.assertRaises(ValueError):
                    lifecycle.load_and_validate_state(value)
        for state_name in ("snapshot_staged", "propagated", "prune_eligible"):
            forged = copy.deepcopy(pending)
            forged["state"] = state_name
            self.assertFalse(self.schema_accepts(forged))
            with self.assertRaises(ValueError):
                lifecycle.load_and_validate_state(forged)

    def test_untouched_worker_legacy_target_is_rejected_without_live_effects(self):
        sessions = self.home / ".hermes/sessions/sessions.json"
        fixtures = [sessions, self.repo / "state.db", self.repo / "transcript.jsonl", self.repo / "route.json"]
        sessions.parent.mkdir(parents=True)
        sessions.write_text('{"session-1":{"completed":false}}', encoding="utf-8")
        sqlite3.connect(fixtures[1]).execute("create table fixture (value text)").connection.close()
        fixtures[2].write_text('{"event":"open"}\n', encoding="utf-8")
        fixtures[3].write_text('{"route_cleanup_state":"open"}', encoding="utf-8")
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixtures}
        spec = importlib.util.spec_from_file_location("session_close_worker_test", ROUTER / "honcho_background_worker.py")
        worker = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"yaml": mock.Mock()}):
            spec.loader.exec_module(worker)
        base = dict(repo=str(self.repo), hermes_agent_root=str(self.home / "missing"), session_id="session-1", thread_id="thread-1", root_goal_id="goal-1", task_ac_result="passed", changed_policy_or_procedure=None, source_refs=None, artifact_refs=None, unresolved_holds=None)
        worker_path = ROUTER / "honcho_background_worker.py"
        worker_digest = hashlib.sha256(worker_path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            worker.handle_writeback(argparse.Namespace(**base, target_repository=None, target_remote_ref=None, target_relative_path=None))
        args = argparse.Namespace(**base, target_repository=self.target["repository"], target_remote_ref=self.target["remote_ref"], target_relative_path=self.target["canonical_path"])
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}), self.assertRaises(ValueError):
            worker.handle_writeback(args)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixtures})
        self.assertEqual(worker_digest, hashlib.sha256(worker_path.read_bytes()).hexdigest())

    def test_actual_git_porcelain_baseline_excludes_only_allowed_paths(self):
        allowed = {
            ".harness/project/scripts/router/session_close_lifecycle.py",
            ".harness/project/scripts/router/honcho_background_worker.py",
            ".harness/project/schemas/session_close_state.v1.schema.json",
            "test_session_close_lifecycle.py",
        }
        expected = "604826365015a59bb547d1d9df6b876644c61b9130f3ed3af290dcd9061499c0"

        def scope_digest(output):
            entries = []
            for entry in (item for item in output.split(b"\0") if item):
                status = entry[:2].decode("utf-8")
                path = entry[3:].decode("utf-8")
                if path in allowed:
                    continue
                current = REPO / path
                sha256 = hashlib.sha256(current.read_bytes()).hexdigest() if current.exists() else "<deleted>"
                entries.append({"status": status, "path": path, "sha256": sha256})
            entries.sort(key=lambda item: item["path"])
            return hashlib.sha256(canonical_bytes(entries)).hexdigest()

        output = subprocess.check_output(["git", "status", "--porcelain=v1", "-z", "-uall"], cwd=REPO)
        self.assertEqual(expected, scope_digest(output))
        with self.assertRaises(AssertionError):
            self.assertEqual(expected, scope_digest(output + b"?? fake-out-of-scope\0"))


if __name__ == "__main__":
    unittest.main()
