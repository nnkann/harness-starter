import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/cps_learning_candidate.py"
SCHEMA = ROOT / ".harness/hermes/schemas/learning-candidate.schema.yaml"
spec = importlib.util.spec_from_file_location("cps_learning_candidate", TOOL)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def eligible_input():
    return {
        "identity": {"namespace": "harness", "name": "compact-route-gate", "revision": 1},
        "pattern": {
            "C": "bind one immutable project scope",
            "P": ["compile compact local body"],
            "S": ["admit only independent terminal evidence"],
            "AC": ["result is deterministic and closed"],
        },
        "outcome": {
            "outcome_ref": "maat:outcome:42",
            "digest": DIGEST_A,
            "state": "verified",
            "terminal": True,
            "verifier": {"kind": "maat", "independent": True},
        },
        "execution_evidence": [{
            "evidence_ref": "execution:evidence:42",
            "digest": DIGEST_B,
            "state": "verified",
            "terminal": True,
            "verifier": {"kind": "maat", "independent": True},
        }],
        "source_refs": ["source:packet:42"],
        "lifecycle": "candidate",
    }


class LearningCandidateTests(unittest.TestCase):
    def test_ac1_closed_schema_and_compact_required_body(self):
        schema = json.loads(SCHEMA.read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {"candidate_id", "identity", "pattern", "outcome_binding", "execution_evidence", "source_refs", "lifecycle", "dedupe_key"},
        )
        for name in ("identity", "pattern"):
            self.assertFalse(schema["properties"][name]["additionalProperties"])
        self.assertFalse(schema["$defs"]["outcomeProof"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["executionProof"]["additionalProperties"])
        self.assertLess(SCHEMA.stat().st_size, 12000)

    def test_ac2_eligible_projection_binds_verified_terminal_evidence(self):
        result = module.admit_learning_candidate(eligible_input())
        self.assertEqual(result["result"], "eligible")
        body = result["candidate"]
        self.assertEqual(body["outcome_binding"]["outcome_ref"], "maat:outcome:42")
        self.assertEqual(body["execution_evidence"][0]["evidence_ref"], "execution:evidence:42")
        self.assertRegex(body["candidate_id"], r"^lc_[0-9a-f]{64}$")
        self.assertRegex(body["dedupe_key"], r"^[0-9a-f]{64}$")

    def test_ac3_rejects_ineligible_states_nonterminal_and_unverified(self):
        for field, value in (("state", "hold"), ("state", "failed"), ("state", "partial"),
                             ("state", "cancelled"), ("state", "stale"), ("state", "pending"),
                             ("state", "unverified"), ("terminal", False)):
            packet = eligible_input()
            packet["outcome"][field] = value
            with self.subTest(field=field, value=value):
                self.assertEqual(module.admit_learning_candidate(packet)["result"], "rejected")
        packet = eligible_input()
        packet["execution_evidence"][0]["state"] = "partial"
        self.assertEqual(module.admit_learning_candidate(packet)["result"], "rejected")

    def test_ac4_rejects_missing_refs_digests_and_self_claims(self):
        mutations = [
            lambda p: p["outcome"].pop("outcome_ref"),
            lambda p: p["outcome"].pop("digest"),
            lambda p: p["execution_evidence"][0].pop("evidence_ref"),
            lambda p: p["execution_evidence"][0].pop("digest"),
            lambda p: p["outcome"].update(verifier={"kind": "worker", "independent": True}),
            lambda p: p["execution_evidence"][0].update(verifier={"kind": "test", "independent": True}),
            lambda p: p["outcome"].update(verifier={"kind": "maat", "independent": False}),
        ]
        for mutate in mutations:
            packet = eligible_input(); mutate(packet)
            self.assertEqual(module.admit_learning_candidate(packet)["result"], "rejected")

    def test_ac5_rejects_fixture_live_route_projection_and_raw_operational_fields(self):
        packet = eligible_input(); packet["fixture"] = {"live": True}
        self.assertEqual(module.admit_learning_candidate(packet)["result"], "rejected")
        for prohibited in module.PROHIBITED_FIELDS:
            packet = eligible_input(); packet[prohibited] = {"raw": True}
            with self.subTest(prohibited=prohibited):
                self.assertEqual(module.admit_learning_candidate(packet)["result"], "rejected")

    def test_ac6_projection_is_deterministic_and_excludes_transport_noise(self):
        first = eligible_input()
        second = eligible_input()
        first["timestamp"] = "2025-01-01T00:00:00Z"; first["polling"] = {"attempt": 1}
        second["timestamp"] = "2026-01-01T00:00:00Z"; second["polling"] = {"attempt": 99}
        a = module.project_learning_candidate(first)
        b = module.project_learning_candidate(second)
        self.assertEqual(a, b)

    def test_ac7_equivalent_candidate_is_duplicate_without_second_body(self):
        body = module.admit_learning_candidate(eligible_input())["candidate"]
        result = module.admit_learning_candidate(eligible_input(), existing=[body])
        self.assertEqual(result, {"result": "duplicate", "reasons": ["equivalent_candidate_exists"], "candidate_ref": body["candidate_id"]})

    def test_ac8_material_change_supersedes_by_ref_without_history_embedding(self):
        previous = module.admit_learning_candidate(eligible_input())["candidate"]
        changed = eligible_input(); changed["pattern"]["AC"] = ["changed material criterion"]
        result = module.admit_learning_candidate(changed, supersedes_ref=previous["candidate_id"], existing=[previous])
        self.assertEqual(result["result"], "superseding")
        self.assertEqual(result["candidate"]["supersedes_ref"], previous["candidate_id"])
        self.assertNotIn("history", result["candidate"])
        self.assertNotIn("prior_body", result["candidate"])

    def test_ac9_supersession_rejects_missing_same_or_unknown_reference(self):
        previous = module.admit_learning_candidate(eligible_input())["candidate"]
        changed = eligible_input(); changed["pattern"]["S"] = ["materially changed"]
        self.assertEqual(module.admit_learning_candidate(changed, existing=[previous])["result"], "rejected")
        self.assertEqual(module.admit_learning_candidate(eligible_input(), supersedes_ref=previous["candidate_id"], existing=[previous])["result"], "duplicate")
        self.assertEqual(module.admit_learning_candidate(changed, supersedes_ref="lc_" + "f" * 64, existing=[previous])["result"], "rejected")

    def test_ac10_input_immutable_bounded_result_and_no_writers(self):
        packet = eligible_input(); original = copy.deepcopy(packet)
        with patch("builtins.open", side_effect=AssertionError("writer called")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("writer called")), \
             patch("pathlib.Path.write_bytes", side_effect=AssertionError("writer called")):
            result = module.admit_learning_candidate(packet)
        self.assertEqual(packet, original)
        self.assertIn(result["result"], {"eligible", "rejected", "duplicate", "superseding"})
        self.assertLessEqual(len(result["reasons"]), module.MAX_REASONS)
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("timestamp", encoded)
        self.assertNotIn("logs", encoded)
        self.assertEqual(result["candidate"]["outcome_binding"]["digest"], DIGEST_A)

    def test_repo_scope_names_only_three_allowed_paths(self):
        self.assertEqual(
            {SCHEMA.relative_to(ROOT).as_posix(), TOOL.relative_to(ROOT).as_posix(), Path(__file__).resolve().relative_to(ROOT).as_posix()},
            {".harness/hermes/schemas/learning-candidate.schema.yaml", ".harness/hermes/tools/cps_learning_candidate.py", "tests/test_cps_learning_candidate.py"},
        )


if __name__ == "__main__":
    unittest.main()
