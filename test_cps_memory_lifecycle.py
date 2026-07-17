import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from dataclasses import replace
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parent
MODULE_PATH = REPO / ".harness" / "project" / "scripts" / "router" / "cps_memory_lifecycle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cps_memory_lifecycle", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lifecycle = load_module()


def load_runner_module():
    tools_dir = REPO / ".harness" / "hermes" / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        spec = importlib.util.spec_from_file_location("lifecycle_runner", tools_dir / "lifecycle_runner.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(tools_dir))


runner = load_runner_module()


def admitted_budget(estimate=100, remaining=100, context_remaining_pct=50, budget_age_seconds=0, actual_token_usage=None):
    return lifecycle.build_budget_decision(
        budget_source_ref="test:explicit-budget",
        token_estimate=estimate,
        token_budget_remaining=remaining,
        context_remaining_pct=context_remaining_pct,
        budget_age_seconds=budget_age_seconds,
        actual_token_usage=actual_token_usage,
    )


class FixtureAdapters:
    def __init__(self, budget_decision):
        self.calls = []
        self.remote_ok = True
        self.duplicate = False
        self.budget_decision = budget_decision
        self.import_error = None
        self.read_error = None
        self.source_graph_ref = lifecycle.CANONICAL_GRAPH_REF
        self.compare_error = None
        self.comparison = lifecycle.SiaComparison("revised")
        self.deactivate_ok = True
        self.write_error = None
        self.readback_error = None
        self.readback_matches = True
        self.readback_graph_ref = lifecycle.CANONICAL_GRAPH_REF
        self.writer_session_id = "writer-session"
        self.readback_session_id = "readback-session"
        self.durable_receipts = []
        self.persistence_calls = []
        self.reload_override = None
        self.initialization_claimed = True

    def confirm_remote(self, event):
        self.calls.append("N1")
        return self.remote_ok

    def is_duplicate(self, event):
        self.calls.append("N2")
        return self.duplicate

    def within_budget(self, event):
        self.calls.append("N3")
        return self.budget_decision

    def import_source(self, event):
        self.calls.append("N4.import")
        if self.import_error:
            raise self.import_error
        return "gbrain:import:1"

    def read_source(self, import_ref):
        self.calls.append("N4.read")
        if self.read_error:
            raise self.read_error
        source = {"source_ref": "source:decision", "source_revision": "rev-2", "content_hash": "hash-2"}
        if self.source_graph_ref is not None:
            source["graph_ref"] = self.source_graph_ref
        return source

    def compare(self, event, source):
        self.calls.append("N5")
        if self.compare_error:
            raise self.compare_error
        return self.comparison

    def deactivate(self, prior_ref, event):
        self.calls.append("N6")
        return self.deactivate_ok

    def claim_first_initialization(self, event):
        self.calls.append("N6.claim")
        return self.initialization_claimed

    def write(self, event, source, comparison):
        self.calls.append("N7")
        if self.write_error:
            raise self.write_error
        return "honcho:conclusion:2"

    def readback(self, conclusion_ref):
        self.calls.append("N8")
        if self.readback_error:
            raise self.readback_error
        if not self.readback_matches:
            return {"source_ref": "source:other", "source_revision": "rev-x", "content_hash": "wrong", "graph_ref": lifecycle.CANONICAL_GRAPH_REF}
        readback = {"source_ref": "source:decision", "source_revision": "rev-2", "content_hash": "hash-2"}
        if self.readback_graph_ref is not None:
            readback["graph_ref"] = self.readback_graph_ref
        return readback

    def persist_stage_receipt(self, receipt):
        self.persistence_calls.append(receipt.stage_id)
        self.durable_receipts.append(receipt)

    def reload_stage_receipts(self, event):
        if self.reload_override is not None:
            return tuple(self.reload_override)
        return tuple(self.durable_receipts)


class TestCpsMemoryLifecycle(unittest.TestCase):
    def event(self, **changes):
        source_ref = changes.get("source_ref", "source:decision")
        base = lifecycle.PushedShaEvent(
            event_id=f"push:main:abc123:{hashlib.sha256(source_ref.encode()).hexdigest()}",
            pushed_sha="abc123", source_ref=source_ref,
            source_revision="rev-2", content_hash="hash-2", lifecycle="revised",
            graph_ref=lifecycle.CANONICAL_GRAPH_REF,
            prior_ref="honcho:conclusion:1", attempt=1,
        )
        return replace(base, **changes)

    def run_stage(self, adapters=None, event=None):
        return lifecycle.run_stage_core(event or self.event(), adapters or FixtureAdapters(admitted_budget()))

    def test_graph_ref_propagates_exactly_to_every_successful_receipt(self):
        event = self.event()
        adapters = FixtureAdapters(admitted_budget())
        result = self.run_stage(adapters, event)

        self.assertTrue(result.closure_candidate)
        self.assertEqual([receipt.graph_ref for receipt in result.receipts], [event.graph_ref] * 9)

    def test_invalid_graph_ref_fails_closed_before_calls_or_receipts(self):
        invalid_refs = (None, "", "other-graph/C2@deadbeef")
        for graph_ref in invalid_refs:
            adapters = FixtureAdapters(admitted_budget())
            with self.subTest(graph_ref=graph_ref):
                result = self.run_stage(adapters, self.event(graph_ref=graph_ref))
                self.assertEqual(adapters.calls, [])
                self.assertEqual(result.receipts, ())
                self.assertFalse(result.closure_candidate)

    def test_receipt_construction_cannot_override_validated_event_graph_ref(self):
        event = self.event()
        receipt = lifecycle._receipt(
            event, "N1", "pass", "ok", {"graph_ref": "caller-controlled"}
        )

        self.assertEqual(receipt.graph_ref, event.graph_ref)
        self.assertNotIn("graph_ref", receipt.refs)

    def test_graph_ref_is_preserved_on_duplicate_readback_and_deactivation_paths(self):
        cases = []

        duplicate = FixtureAdapters(admitted_budget())
        duplicate.duplicate = True
        cases.append(self.run_stage(duplicate))

        readback = FixtureAdapters(admitted_budget())
        readback.readback_matches = False
        cases.append(self.run_stage(readback))

        deactivation = FixtureAdapters(admitted_budget())
        deactivation.deactivate_ok = False
        cases.append(self.run_stage(deactivation))

        for result in cases:
            with self.subTest(last_stage=result.receipts[-1].stage_id):
                self.assertTrue(result.receipts)
                self.assertTrue(all(receipt.graph_ref == lifecycle.CANONICAL_GRAPH_REF for receipt in result.receipts))

    def test_event_identity_must_match_source_ref_digest(self):
        original = self.event()
        mismatched = replace(original, source_ref="source:other")
        adapters = FixtureAdapters(admitted_budget())

        result = self.run_stage(adapters, mismatched)

        self.assertEqual(result.receipts[-1].reason, "malformed-source-event")
        self.assertEqual(adapters.calls, ["N1"])

    def test_duplicate_same_sha_is_noop_without_downstream_calls(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.duplicate = True
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].status, "noop")
        self.assertEqual(adapters.calls, ["N1", "N2"])
        self.assertFalse(result.closure_candidate)

    def test_remote_failure_is_blocked(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.remote_ok = False
        result = self.run_stage(adapters)
        self.assertEqual([(r.stage_id, r.status) for r in result.receipts], [("N1", "blocked")])
        self.assertEqual(adapters.calls, ["N1"])

    def test_budget_breach_blocks_without_partial_import(self):
        adapters = FixtureAdapters(admitted_budget(101, 100))
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].stage_id, "N3")
        self.assertEqual(result.receipts[-1].status, "blocked")
        self.assertEqual(result.receipts[-1].reason, "budget-breached")
        self.assertEqual(adapters.calls, ["N1", "N2", "N3"])

    def test_budget_unavailable_is_reloadable_and_blocks_all_n4_n9_side_effects(self):
        required = {
            "schema", "version", "budget_source_ref", "token_estimate",
            "token_budget_remaining_before", "context_remaining_pct", "decision",
            "budget_age_seconds", "actual_token_usage", "reason", "measurement_status",
        }
        for estimate, remaining in ((None, 100), ("10", 100), (-1, 100), (100, -1)):
            adapters = FixtureAdapters(lifecycle.build_budget_decision(
                budget_source_ref="test:caller-envelope",
                token_estimate=estimate,
                token_budget_remaining=remaining,
                context_remaining_pct=17,
                budget_age_seconds=0,
            ))
            with self.subTest(estimate=estimate, remaining=remaining):
                result = self.run_stage(adapters)
                receipt = result.receipts[-1]
                self.assertEqual((receipt.stage_id, receipt.status, receipt.reason), ("N3", "blocked", "budget-check-unavailable"))
                self.assertEqual(set(receipt.refs), required)
                self.assertEqual(receipt.refs["decision"], "blocked")
                self.assertEqual(receipt.refs["measurement_status"], "unavailable")
                self.assertEqual(adapters.calls, ["N1", "N2", "N3"])
                self.assertEqual(tuple(adapters.reload_stage_receipts(self.event())), result.receipts)

    def test_budget_equal_and_under_are_admitted_with_observational_context_pct(self):
        for estimate, remaining, context_pct in ((100, 100, 50), (99, 100, 150)):
            adapters = FixtureAdapters(admitted_budget(estimate, remaining, context_pct))
            with self.subTest(estimate=estimate, remaining=remaining):
                result = self.run_stage(adapters)
                receipt = result.receipts[2]
                self.assertEqual((receipt.stage_id, receipt.status, receipt.reason), ("N3", "pass", "budget-admitted"))
                self.assertEqual(receipt.refs["context_remaining_pct"], context_pct if context_pct <= 100 else None)
                self.assertTrue(result.closure_candidate)

    def test_actual_usage_measurement_is_independent_from_admission_envelope(self):
        for actual_usage, status in ((None, "unavailable"), (73, "measured"), ("73", "unavailable")):
            adapters = FixtureAdapters(admitted_budget(actual_token_usage=actual_usage))
            with self.subTest(actual_usage=actual_usage):
                result = self.run_stage(adapters)
                receipt = result.receipts[2]
                self.assertEqual((receipt.status, receipt.reason), ("pass", "budget-admitted"))
                self.assertEqual(receipt.refs["measurement_status"], status)
                self.assertEqual(receipt.refs["actual_token_usage"], actual_usage if isinstance(actual_usage, int) else None)
                self.assertTrue(result.closure_candidate)

    def test_budget_source_ref_and_freshness_fail_closed(self):
        cases = (
            (None, 0, "budget-check-unavailable"),
            ("", 0, "budget-check-unavailable"),
            ("source\nref", 0, "budget-check-unavailable"),
            ("test:source", None, "budget-check-unavailable"),
            ("test:source", lifecycle.MAX_BUDGET_ENVELOPE_AGE_SECONDS + 1, "budget-envelope-stale"),
        )
        for source_ref, age, reason in cases:
            decision = lifecycle.build_budget_decision(source_ref, 10, 100, 50, age)
            adapters = FixtureAdapters(decision)
            with self.subTest(source_ref=source_ref, age=age):
                result = self.run_stage(adapters)
                receipt = result.receipts[-1]
                self.assertEqual((receipt.stage_id, receipt.status, receipt.reason), ("N3", "blocked", reason))
                self.assertEqual(receipt.refs["schema"], "harness.cps_budget_decision_receipt.v1")
                self.assertEqual(adapters.calls, ["N1", "N2", "N3"])

    def test_inconsistent_budget_decision_fails_closed(self):
        inconsistent = replace(admitted_budget(100, 100), token_budget_remaining_before=99)
        adapters = FixtureAdapters(inconsistent)
        result = self.run_stage(adapters)
        receipt = result.receipts[-1]
        self.assertEqual((receipt.stage_id, receipt.status, receipt.reason), ("N3", "blocked", "budget-check-unavailable"))
        self.assertEqual(receipt.refs["measurement_status"], "unavailable")
        self.assertEqual(adapters.calls, ["N1", "N2", "N3"])

    def test_gbrain_import_failure_blocks_sia_and_honcho(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.import_error = RuntimeError("unavailable")
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].status, "blocked")
        self.assertEqual(adapters.calls, ["N1", "N2", "N3", "N4.import"])

    def test_gbrain_read_failure_blocks_sia_and_honcho(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.read_error = RuntimeError("unavailable")
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].status, "blocked")
        self.assertNotIn("N5", adapters.calls)
        self.assertNotIn("N7", adapters.calls)

    def test_n4_missing_graph_ref_blocks_without_n9_or_closure_candidate(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.source_graph_ref = None
        result = self.run_stage(adapters)
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N4", "blocked"))
        self.assertNotIn("N9", adapters.persistence_calls)
        self.assertFalse(result.closure_candidate)

    def test_n4_mismatched_graph_ref_blocks_without_n9_or_closure_candidate(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.source_graph_ref = "other-graph/C2@deadbeef"
        result = self.run_stage(adapters)
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N4", "blocked"))
        self.assertNotIn("N9", adapters.persistence_calls)
        self.assertFalse(result.closure_candidate)

    def test_revised_prior_is_deactivated_before_new_write(self):
        adapters = FixtureAdapters(admitted_budget())
        result = self.run_stage(adapters)
        self.assertLess(adapters.calls.index("N6"), adapters.calls.index("N7"))
        self.assertTrue(result.closure_candidate)

    def test_sia_disposition_is_normalized_to_exact_canonical_value(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("  ReViSeD  ", prior_ref="honcho:conclusion:1")
        result = self.run_stage(adapters)
        self.assertTrue(result.closure_candidate)
        self.assertEqual(adapters.calls.count("N7"), 1)

    def test_noncanonical_sia_disposition_is_ineligible(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("eligible")
        result = self.run_stage(adapters)
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N5", "blocked"))
        self.assertNotIn("N7", adapters.calls)

    def test_same_stale_conflict_and_withdrawn_never_write(self):
        for disposition in ("same", "stale", "conflict", "withdrawn"):
            adapters = FixtureAdapters(admitted_budget())
            adapters.comparison = lifecycle.SiaComparison(disposition, prior_ref="honcho:conclusion:1")
            with self.subTest(disposition=disposition):
                self.run_stage(adapters, self.event(lifecycle=disposition))
                self.assertNotIn("N7", adapters.calls)

    def test_same_is_no_change_without_deactivation(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("same", prior_ref="honcho:conclusion:1")
        result = self.run_stage(adapters, self.event(lifecycle="same"))
        self.assertNotIn("N6", adapters.calls)
        self.assertNotIn("N7", adapters.calls)
        self.assertTrue(result.closure_candidate)

    def test_revised_without_prior_deactivation_target_blocks_before_write(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("revised")
        result = self.run_stage(adapters, self.event(prior_ref=None))
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N6", "blocked"))
        self.assertNotIn("N7", adapters.calls)

    def test_explicit_first_anchor_initialization_admits_without_prior(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("revised")
        result = self.run_stage(adapters, self.event(prior_ref=None, first_anchor_initialization=True))
        self.assertTrue(result.closure_candidate)
        self.assertEqual(result.receipts[5].reason, "first-anchor-initialization-admitted")

    def test_initialization_with_prior_is_blocked(self):
        result = self.run_stage(FixtureAdapters(admitted_budget()), self.event(first_anchor_initialization=True))
        self.assertEqual(result.receipts[-1].reason, "initialization-prohibits-prior-ref")

    def test_second_initialization_blocks_even_when_sia_reports_same(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("same", "honcho:existing")
        result = self.run_stage(adapters, self.event(prior_ref=None, first_anchor_initialization=True))
        self.assertEqual(result.receipts[-1].reason, "initialization-prohibits-prior-ref")
        self.assertNotIn("N7", adapters.calls)

    def test_failed_initialization_claim_blocks_write(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("revised")
        adapters.initialization_claimed = False
        result = self.run_stage(adapters, self.event(prior_ref=None, first_anchor_initialization=True))
        self.assertEqual(result.receipts[-1].reason, "first-anchor-initialization-ineligible")
        self.assertNotIn("N7", adapters.calls)

    def test_deactivation_failure_blocks_new_write(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.deactivate_ok = False
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].stage_id, "N6")
        self.assertEqual(result.receipts[-1].status, "blocked")
        self.assertNotIn("N7", adapters.calls)

    def test_withdrawn_deactivates_prior_and_never_writes_active_conclusion(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.comparison = lifecycle.SiaComparison("withdrawn", prior_ref="honcho:conclusion:1")
        result = self.run_stage(adapters, self.event(lifecycle="withdrawn"))
        self.assertIn("N6", adapters.calls)
        self.assertNotIn("N7", adapters.calls)
        self.assertEqual(result.receipts[6].status, "noop")
        self.assertTrue(result.closure_candidate)

    def test_missing_or_malformed_source_is_blocked(self):
        malformed = (
            self.event(source_ref=""), self.event(source_revision=""),
            self.event(content_hash=""), self.event(pushed_sha=""),
            self.event(lifecycle="unknown"),
        )
        for event in malformed:
            adapters = FixtureAdapters(admitted_budget())
            with self.subTest(event=event):
                result = self.run_stage(adapters, event)
                self.assertEqual(result.receipts[-1].stage_id, "N2")
                self.assertEqual(result.receipts[-1].status, "blocked")
                self.assertEqual(adapters.calls, ["N1"])

    def test_same_writer_and_readback_session_fails(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.readback_session_id = adapters.writer_session_id
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].stage_id, "N8")
        self.assertEqual(result.receipts[-1].status, "failed")
        self.assertNotIn("N8", adapters.calls)

    def test_readback_mismatch_fails(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.readback_matches = False
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts[-1].stage_id, "N8")
        self.assertEqual(result.receipts[-1].status, "failed")
        self.assertFalse(result.closure_candidate)

    def test_n8_missing_graph_ref_fails_without_n9_or_closure_candidate(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.readback_graph_ref = None
        result = self.run_stage(adapters)
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N8", "failed"))
        self.assertNotIn("N9", adapters.persistence_calls)
        self.assertFalse(result.closure_candidate)

    def test_n8_mismatched_graph_ref_fails_without_n9_or_closure_candidate(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.readback_graph_ref = "other-graph/C2@deadbeef"
        result = self.run_stage(adapters)
        self.assertEqual((result.receipts[-1].stage_id, result.receipts[-1].status), ("N8", "failed"))
        self.assertNotIn("N9", adapters.persistence_calls)
        self.assertFalse(result.closure_candidate)

    def test_missing_receipt_prevents_closure(self):
        adapters = FixtureAdapters(admitted_budget())
        receipts = list(self.run_stage(adapters).receipts)
        receipts.pop(3)
        self.assertFalse(lifecycle.evaluate_closure(receipts, self.event()))

    def test_missing_durable_receipt_reload_blocks_n9_closure(self):
        adapters = FixtureAdapters(admitted_budget())
        adapters.reload_override = []
        result = self.run_stage(adapters)
        self.assertFalse(result.closure_candidate)
        self.assertEqual(result.receipts, ())
        self.assertNotIn("N9", adapters.persistence_calls)

    def test_nondurable_process_local_receipts_do_not_feed_n9(self):
        durable = FixtureAdapters(admitted_budget())
        reloaded = list(self.run_stage(durable).receipts)
        adapters = FixtureAdapters(admitted_budget())
        adapters.reload_override = [receipt for receipt in reloaded if receipt.stage_id != "N4"]
        result = self.run_stage(adapters)
        self.assertFalse(result.closure_candidate)
        self.assertNotEqual(len(result.receipts), 9)

    def test_reloaded_receipts_preserve_graph_ref_order_and_dependency(self):
        adapters = FixtureAdapters(admitted_budget())
        result = self.run_stage(adapters)
        self.assertEqual(result.receipts, tuple(adapters.durable_receipts))
        self.assertEqual([r.graph_ref for r in result.receipts], [self.event().graph_ref] * 9)
        self.assertEqual([r.stage_id for r in result.receipts], list(lifecycle.STAGE_IDS))
        self.assertEqual(
            [r.depends_on for r in result.receipts],
            [()] + [("N%d" % number,) for number in range(1, 9)],
        )

    def test_receipt_identity_is_event_stage_attempt_and_status_is_bounded(self):
        result = self.run_stage()
        self.assertEqual(len(result.receipts), 9)
        self.assertEqual(
            [(r.event_id, r.stage_id, r.attempt) for r in result.receipts],
            [(self.event().event_id, f"N{i}", 1) for i in range(1, 10)],
        )
        self.assertTrue({r.status for r in result.receipts} <= {"pass", "noop", "blocked", "failed"})

    def test_receipts_exclude_raw_payload_fields(self):
        forbidden = {"body", "raw_body", "stdout", "transcript"}
        for receipt in self.run_stage().receipts:
            self.assertTrue(forbidden.isdisjoint(receipt.__dataclass_fields__))
            self.assertTrue(forbidden.isdisjoint(receipt.refs))

        oversized = lifecycle.build_budget_decision(
            "x" * 257,
            lifecycle.MAX_BUDGET_COUNTER + 1,
            100,
            50,
            lifecycle.MAX_BUDGET_AGE_RECEIPT_SECONDS + 1,
            lifecycle.MAX_BUDGET_COUNTER + 1,
        ).receipt_fields()
        self.assertEqual(oversized["budget_source_ref"], "unavailable")
        self.assertIsNone(oversized["token_estimate"])
        self.assertIsNone(oversized["budget_age_seconds"])
        self.assertIsNone(oversized["actual_token_usage"])

    def test_protocol_surface_has_no_git_mutation_interface(self):
        names = set(dir(lifecycle.StageAdapters))
        self.assertTrue({"confirm_remote", "is_duplicate", "within_budget", "import_source", "read_source", "compare", "deactivate", "write", "readback", "persist_stage_receipt", "reload_stage_receipts"} <= names)
        self.assertTrue({"commit", "push", "checkout", "merge", "reset", "tag"}.isdisjoint(names))


class RecordingHoncho:
    def __init__(self, identity, shared, calls):
        self.identity, self.shared, self.calls = identity, shared, calls

    def write_anchor(self, anchor):
        self.calls.append(("write", anchor["anchor_key"]))
        self.shared["honcho:real:2"] = dict(anchor)
        return "honcho:real:2"

    def read_anchor(self, ref):
        self.calls.append(("read", self.identity))
        return dict(self.shared[ref])

    def deactivate_anchor(self, ref, superseded_by):
        self.calls.append(("deactivate", ref))
        return True


class TestProductionStageAdapters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "init", str(self.repo)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.remote)], cwd=self.repo, check=True)
        (self.repo / "memory.md").write_text("canonical\n", encoding="utf-8")
        (self.repo / "other.md").write_text("canonical\n", encoding="utf-8")
        subprocess.run(["git", "add", "memory.md", "other.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "source"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        self.sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        subprocess.run(["git", "push", "-u", "origin", "HEAD:main"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        self.db = Path(self.temp.name) / "lifecycle.sqlite3"
        self.shared, self.calls = {}, []

    def tearDown(self):
        self.temp.cleanup()

    def event(self):
        return lifecycle.PushedShaEvent(
            event_id=f"push:main:{self.sha}:{hashlib.sha256(b'memory.md').hexdigest()}", pushed_sha=self.sha, source_ref="memory.md",
            source_revision=self.sha, content_hash=hashlib.sha256(b"canonical\n").hexdigest(),
            lifecycle="revised", graph_ref=lifecycle.CANONICAL_GRAPH_REF,
            prior_ref="honcho:real:1", attempt=1,
        )

    def adapters(self):
        return lifecycle.ProductionStageAdapters(
            self.repo, self.db,
            RecordingHoncho("writer", self.shared, self.calls),
            RecordingHoncho("reader", self.shared, self.calls),
            admitted_budget(),
        )

    def test_remote_ref_containment_fails_without_origin_tracking_ref(self):
        subprocess.run(["git", "update-ref", "-d", "refs/remotes/origin/main"], cwd=self.repo, check=True)
        self.assertFalse(self.adapters().confirm_remote(self.event()))

    def test_canonical_blob_and_graph_ref_restore_after_reinstantiation(self):
        (self.repo / "memory.md").write_text("dirty\n", encoding="utf-8")
        import_ref = self.adapters().import_source(self.event())
        restored = self.adapters().read_source(import_ref)
        self.assertEqual(restored["content_hash"], hashlib.sha256(b"canonical\n").hexdigest())
        self.assertEqual(restored["graph_ref"], lifecycle.CANONICAL_GRAPH_REF)
        self.assertNotIn("dirty", json.dumps(restored))

    def test_eligibility_deactivation_write_and_independent_readback_order(self):
        adapters = self.adapters()
        source = adapters.read_source(adapters.import_source(self.event()))
        self.assertIn(adapters.compare(self.event(), source).disposition, lifecycle.SIA_DISPOSITIONS)
        result = lifecycle.run_stage_core(self.event(), adapters)
        self.assertTrue(result.closure_candidate)
        self.assertLess(self.calls.index(("deactivate", "honcho:real:1")), self.calls.index(("write", "memory.md@" + self.sha)))
        self.assertIn(("read", "reader"), self.calls)
        self.assertNotEqual(adapters.writer_session_id, adapters.readback_session_id)

    def test_receipts_and_active_anchor_reload_after_reinstantiation(self):
        event = self.event()
        result = lifecycle.run_stage_core(event, self.adapters())
        self.assertEqual(tuple(self.adapters().reload_stage_receipts(event)), result.receipts)
        with sqlite3.connect(self.db) as conn:
            active = conn.execute("SELECT anchor_ref, graph_ref FROM active_anchors WHERE source_ref=?", (event.source_ref,)).fetchone()
        self.assertEqual(active, ("honcho:real:2", event.graph_ref))
        probe = """
import importlib.util, json, sqlite3, sys
spec = importlib.util.spec_from_file_location('restart_lifecycle', sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
with sqlite3.connect(sys.argv[2]) as conn:
    graph_ref = conn.execute('SELECT graph_ref FROM gbrain_sources LIMIT 1').fetchone()[0]
    receipt_count = conn.execute('SELECT COUNT(*) FROM stage_receipts').fetchone()[0]
    supersession_count = conn.execute('SELECT COUNT(*) FROM anchor_supersessions').fetchone()[0]
print(json.dumps([graph_ref, receipt_count, supersession_count]))
"""
        restarted = subprocess.check_output(
            [sys.executable, "-c", probe, str(MODULE_PATH), str(self.db)], text=True,
        )
        self.assertEqual(json.loads(restarted), [event.graph_ref, 9, 1])

    def test_same_sha_distinct_source_refs_keep_distinct_receipt_history_and_reload(self):
        first = self.event()
        second = replace(
            first,
            source_ref="other.md",
            event_id=f"push:main:{self.sha}:{hashlib.sha256(b'other.md').hexdigest()}",
        )
        adapters = self.adapters()
        for event in (first, second):
            adapters.import_source(event)
            adapters.persist_stage_receipt(lifecycle._receipt(event, "N1", "pass", "source-specific"))

        first_reload = adapters.reload_stage_receipts(first)
        second_reload = self.adapters().reload_stage_receipts(second)

        self.assertNotEqual(first.event_id, second.event_id)
        self.assertEqual([receipt.event_id for receipt in first_reload], [first.event_id])
        self.assertEqual([receipt.event_id for receipt in second_reload], [second.event_id])
        with sqlite3.connect(self.db) as conn:
            identities = conn.execute("SELECT event_id FROM stage_receipts ORDER BY event_id").fetchall()
            sources = conn.execute("SELECT source_ref FROM gbrain_sources ORDER BY source_ref").fetchall()
        self.assertEqual(identities, sorted([(first.event_id,), (second.event_id,)]))
        self.assertEqual(sources, [("memory.md",), ("other.md",)])

    def test_first_initialization_claim_is_atomic_and_historical_rows_block_reinit(self):
        event = replace(self.event(), prior_ref=None, first_anchor_initialization=True)
        adapters = self.adapters()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda _: adapters.claim_first_initialization(event), range(2)))
        self.assertEqual(sorted(claims), [False, True])
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO active_anchors VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
                         ("inactive", "old-key", "other.md", "old", "hash", event.graph_ref, "new-key"))
        historical = replace(event, source_ref="other.md", source_revision="new")
        self.assertFalse(adapters.claim_first_initialization(historical))

    def test_real_runner_composition_enforces_unavailable_over_equal_and_under_budget(self):
        cases = (
            (None, 100, "budget-check-unavailable", False),
            (101, 100, "budget-breached", False),
            (100, 100, "budget-admitted", True),
            (99, 100, "budget-admitted", True),
        )
        for estimate, remaining, reason, admitted in cases:
            database = self.repo / ".harness" / "project" / "runs" / "cps_memory_lifecycle.sqlite3"
            database.unlink(missing_ok=True)
            self.shared.clear()
            self.calls.clear()
            args = Namespace(
                branch="main", pushed_sha=self.sha, source_ref="memory.md",
                lifecycle="revised", prior_ref="honcho:real:1",
                token_estimate=estimate, token_budget_remaining=remaining,
                context_remaining_pct=41, budget_source_ref="test:real-runner-envelope",
                budget_age_seconds=0, actual_token_usage=None,
            )
            ports = (
                RecordingHoncho("writer", self.shared, self.calls),
                RecordingHoncho("reader", self.shared, self.calls),
            )
            honcho_ports = mock.Mock(return_value=ports) if admitted else mock.Mock(side_effect=AssertionError("blocked N3 must not initialize Honcho"))
            with self.subTest(estimate=estimate, remaining=remaining), \
                 mock.patch.object(runner, "_build_honcho_ports", honcho_ports):
                code, evidence = runner.run_c2_memory(args, repo=self.repo)
                n3 = next(receipt for receipt in evidence["receipts"] if receipt["stage_id"] == "N3")
                self.assertEqual(n3["reason"], reason)
                self.assertEqual(n3["refs"]["budget_source_ref"], "test:real-runner-envelope")
                self.assertEqual(n3["refs"]["token_estimate"], estimate)
                self.assertEqual(n3["refs"]["token_budget_remaining_before"], remaining)
                self.assertEqual(n3["refs"]["schema"], "harness.cps_budget_decision_receipt.v1")
                self.assertEqual(n3["refs"]["measurement_status"], "unavailable")
                self.assertEqual(code == 0, admitted)
                if admitted:
                    self.assertEqual(evidence["receipts"][-1]["stage_id"], "N9")
                    honcho_ports.assert_called_once_with()
                else:
                    self.assertEqual(evidence["receipts"][-1]["stage_id"], "N3")
                    self.assertEqual(self.calls, [])
                    honcho_ports.assert_not_called()

    def test_real_runner_composition_blocks_invalid_source_and_stale_envelope(self):
        cases = (
            (None, 0, "budget-check-unavailable"),
            ("", 0, "budget-check-unavailable"),
            ("test\nsource", 0, "budget-check-unavailable"),
            ("test:source", lifecycle.MAX_BUDGET_ENVELOPE_AGE_SECONDS + 1, "budget-envelope-stale"),
        )
        for source_ref, age, reason in cases:
            database = self.repo / ".harness" / "project" / "runs" / "cps_memory_lifecycle.sqlite3"
            database.unlink(missing_ok=True)
            args = Namespace(
                branch="main", pushed_sha=self.sha, source_ref="memory.md",
                lifecycle="revised", prior_ref="honcho:real:1",
                token_estimate=10, token_budget_remaining=100,
                context_remaining_pct=41, budget_source_ref=source_ref,
                budget_age_seconds=age, actual_token_usage=None,
            )
            with self.subTest(source_ref=source_ref, age=age), \
                 mock.patch.object(runner, "_build_honcho_ports", side_effect=AssertionError("blocked N3 must not initialize Honcho")):
                code, evidence = runner.run_c2_memory(args, repo=self.repo)
                n3 = evidence["receipts"][-1]
                self.assertNotEqual(code, 0)
                self.assertEqual((n3["stage_id"], n3["status"], n3["reason"]), ("N3", "blocked", reason))
                self.assertEqual(n3["refs"]["schema"], "harness.cps_budget_decision_receipt.v1")
                self.assertEqual(n3["refs"]["measurement_status"], "unavailable")


class TestC2MemoryInvocation(unittest.TestCase):
    SHA = "a" * 40

    def test_runtime_interpreter_exists_and_imports_honcho(self):
        self.assertEqual(runner.PYTHON_EXEC, Path("/Users/kann/.hermes/hermes-agent/venv/bin/python"))
        self.assertTrue(runner.PYTHON_EXEC.is_file())
        self.assertTrue(runner._imports_honcho(runner.PYTHON_EXEC))

    def test_base_url_without_api_key_enables_and_builds_client(self):
        probe = """
import json, os, sys
sys.path.insert(0, sys.argv[1])
from plugins.memory.honcho.client import HonchoClientConfig, get_honcho_client, reset_honcho_client
os.environ['HONCHO_BASE_URL'] = 'http://127.0.0.1:8000'
os.environ.pop('HONCHO_API_KEY', None)
config = HonchoClientConfig.from_env()
client = get_honcho_client(config)
print(json.dumps({'enabled': config.enabled, 'api_key_unset': config.api_key is None, 'client': client is not None}))
reset_honcho_client()
"""
        env = dict(os.environ)
        env.pop("HONCHO_API_KEY", None)
        result = subprocess.run(
            [str(runner.PYTHON_EXEC), "-c", probe, str(runner.HERMES_AGENT_ROOT)],
            text=True, capture_output=True, check=False, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"enabled": True, "api_key_unset": True, "client": True})

    def test_api_key_absence_is_not_honcho_unavailable(self):
        manager = mock.Mock()
        manager.get_or_create.side_effect = lambda key: Namespace(
            honcho_session_id=key, assistant_peer_id="writer-observer", user_peer_id="target"
        )
        config = Namespace(enabled=True, api_key=None)
        adapter_type = mock.Mock(side_effect=lambda current, key: (current, key))
        worker = Namespace(
            _init_honcho=mock.Mock(side_effect=[(manager, "writer", config), (manager, "reader", config)]),
            HonchoAnchorAdapter=adapter_type,
        )
        reset = mock.Mock()
        client_module = mock.Mock(reset_honcho_client=reset)
        with mock.patch.object(runner, "_load_honcho_worker", return_value=worker), \
             mock.patch.dict(sys.modules, {"plugins.memory.honcho.client": client_module}):
            writer, reader = runner._build_honcho_ports()
        self.assertEqual(writer[1], "cps-anchor-writer")
        self.assertEqual(reader.identity, "readback:cps-anchor-readback")
        self.assertEqual(reader.observer, "writer-observer")
        reset.assert_called_once_with()

    def args(self, **changes):
        values = {
            "branch": "main", "pushed_sha": self.SHA, "source_ref": "memory.md",
            "lifecycle": "initialization", "prior_ref": None,
            "token_estimate": 100, "token_budget_remaining": 100,
            "context_remaining_pct": 50, "budget_source_ref": "test:explicit-runner-budget",
            "budget_age_seconds": 0, "actual_token_usage": None,
        }
        values.update(changes)
        return Namespace(**values)

    def test_parser_rejects_malformed_required_arguments(self):
        parser = runner.build_parser()
        invalid = (
            ["c2-memory", "--branch", "main", "--pushed-sha", "short", "--source-ref", "memory.md", "--lifecycle", "initialization"],
            ["c2-memory", "--branch", "main", "--pushed-sha", self.SHA, "--source-ref", "memory.md", "--lifecycle", "same"],
            ["c2-memory", "--pushed-sha", self.SHA, "--source-ref", "memory.md", "--lifecycle", "initialization"],
        )
        invalid += (["c2-memory", "--branch", "main", "--pushed-sha", self.SHA, "--source-ref", "memory.md", "--lifecycle", "eligible"],)
        for argv in invalid:
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                parser.parse_args(argv)

    def test_parser_accepts_only_authorized_lifecycles(self):
        parser = runner.build_parser()
        for name in ("initialization", "revised", "withdrawn"):
            parsed = parser.parse_args(["c2-memory", "--branch", "main", "--pushed-sha", self.SHA, "--source-ref", "memory.md", "--lifecycle", name])
            self.assertEqual(parsed.lifecycle, name)

    def test_build_event_normalizes_initialization_to_explicit_revised_event(self):
        blob = mock.Mock(returncode=0, stdout=b"source", stderr=b"")
        module = Namespace(PushedShaEvent=lifecycle.PushedShaEvent, CANONICAL_GRAPH_REF=lifecycle.CANONICAL_GRAPH_REF)
        with mock.patch.object(runner.subprocess, "run", return_value=blob):
            event = runner._build_event(module, REPO, self.args())
        self.assertEqual(event.lifecycle, "revised")
        self.assertTrue(event.first_anchor_initialization)
        self.assertEqual(
            event.event_id,
            f"push:main:{self.SHA}:{hashlib.sha256(b'memory.md').hexdigest()}",
        )
        with mock.patch.object(runner.subprocess, "run", return_value=blob):
            revised = runner._build_event(module, REPO, self.args(lifecycle="revised"))
        self.assertFalse(revised.first_anchor_initialization)

    def test_build_event_identity_is_source_specific_at_same_branch_and_sha(self):
        blob = mock.Mock(returncode=0, stdout=b"source", stderr=b"")
        module = Namespace(PushedShaEvent=lifecycle.PushedShaEvent, CANONICAL_GRAPH_REF=lifecycle.CANONICAL_GRAPH_REF)
        with mock.patch.object(runner.subprocess, "run", return_value=blob):
            first = runner._build_event(module, REPO, self.args(source_ref="memory.md"))
            second = runner._build_event(module, REPO, self.args(source_ref="other.md"))
        self.assertNotEqual(first.event_id, second.event_id)
        self.assertTrue(first.event_id.endswith(hashlib.sha256(b"memory.md").hexdigest()))
        self.assertTrue(second.event_id.endswith(hashlib.sha256(b"other.md").hexdigest()))

    def test_parser_rejects_initialization_with_prior_ref(self):
        with self.assertRaises(SystemExit):
            runner.build_parser().parse_args(["c2-memory", "--branch", "main", "--pushed-sha", self.SHA, "--source-ref", "memory.md", "--lifecycle", "initialization", "--prior-ref", "old"])

    def test_composition_constructs_production_adapter_only(self):
        event = mock.Mock()
        adapter = mock.Mock()
        module = mock.Mock(ProductionStageAdapters=mock.Mock(return_value=adapter), CANONICAL_GRAPH_REF="graph-ref")
        module.build_budget_decision.return_value = Namespace(decision="admitted")
        module.run_stage_core.return_value = mock.Mock(closure_candidate=True)
        module.evaluate_closure.return_value = True
        adapter.reload_stage_receipts.return_value = (
            Namespace(event_id="event", stage_id="N9", attempt=1, status="pass", reason="complete", refs={}),
        )
        with mock.patch.object(runner, "_load_cps_memory_lifecycle", return_value=module), \
             mock.patch.object(runner, "_remote_branch_contains", return_value=True), \
             mock.patch.object(runner, "_build_event", return_value=event), \
             mock.patch.object(runner, "_build_honcho_ports", return_value=(mock.Mock(), mock.Mock())):
            code, evidence = runner.run_c2_memory(self.args(), repo=REPO)
        self.assertEqual(code, 0)
        module.ProductionStageAdapters.assert_called_once()
        module.run_stage_core.assert_called_once_with(event, adapter)
        self.assertNotIn("fixture", json.dumps(evidence).lower())

    def test_remote_confirmation_failure_is_nonzero_without_writes(self):
        module = mock.Mock()
        with mock.patch.object(runner, "_load_cps_memory_lifecycle", return_value=module), \
             mock.patch.object(runner, "_remote_branch_contains", return_value=False):
            code, evidence = runner.run_c2_memory(self.args(), repo=REPO)
        self.assertNotEqual(code, 0)
        self.assertEqual(evidence["status"], "blocked")
        module.ProductionStageAdapters.assert_not_called()
        module.run_stage_core.assert_not_called()

    def test_receipt_reload_controls_exit(self):
        event = mock.Mock()
        adapter = mock.Mock()
        adapter.reload_stage_receipts.return_value = ()
        module = mock.Mock(ProductionStageAdapters=mock.Mock(return_value=adapter), CANONICAL_GRAPH_REF="graph-ref")
        module.build_budget_decision.return_value = Namespace(decision="admitted")
        module.run_stage_core.return_value = mock.Mock(closure_candidate=True)
        module.evaluate_closure.return_value = False
        with mock.patch.object(runner, "_load_cps_memory_lifecycle", return_value=module), \
             mock.patch.object(runner, "_remote_branch_contains", return_value=True), \
             mock.patch.object(runner, "_build_event", return_value=event), \
             mock.patch.object(runner, "_build_honcho_ports", return_value=(mock.Mock(), mock.Mock())):
            code, evidence = runner.run_c2_memory(self.args(), repo=REPO)
        self.assertNotEqual(code, 0)
        self.assertFalse(evidence["closure_candidate"])
        module.evaluate_closure.assert_called_once_with((), event)

    def test_unavailable_honcho_is_explicit_and_nonzero(self):
        module = mock.Mock()
        module.build_budget_decision.return_value = Namespace(decision="admitted")
        with mock.patch.object(runner, "_load_cps_memory_lifecycle", return_value=module), \
             mock.patch.object(runner, "_remote_branch_contains", return_value=True), \
             mock.patch.object(runner, "_build_event", return_value=mock.Mock()), \
             mock.patch.object(runner, "_build_honcho_ports", side_effect=runner.HonchoUnavailable("SDK missing")):
            code, evidence = runner.run_c2_memory(self.args(), repo=REPO)
        self.assertNotEqual(code, 0)
        self.assertEqual(evidence["status"], "blocked")
        self.assertIn("honcho-unavailable", evidence["reason"])
        module.ProductionStageAdapters.assert_not_called()

    def test_remote_probe_has_no_git_mutation_interface(self):
        with mock.patch.object(runner.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.assertTrue(runner._remote_branch_contains(REPO, "main", self.SHA))
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["git", "merge-base"])
        self.assertTrue({"fetch", "push", "commit", "update-ref", "checkout"}.isdisjoint(command))


if __name__ == "__main__":
    unittest.main()
