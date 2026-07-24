import sys
import unittest
from pathlib import Path


CONTRACTS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "contracts"
sys.path.insert(0, str(CONTRACTS))

import cps_advisory_reader_contract as contract


DIGEST = "a" * 64


class CpsAdvisoryReaderContractTests(unittest.TestCase):
    def binding(self, response, revision="r17"):
        return contract.AdvisoryReaderBinding(
            producer_ref="memory://producer/42",
            source_identity="source-neutral-memory",
            source_revision=revision,
            reader=lambda request: response(request),
        )

    def response(self, state, evidence=None, **extra):
        return {
            "state": state,
            "producer_ref": "memory://producer/42",
            "source_identity": "source-neutral-memory",
            "source_revision": "r17",
            "evidence": {"record_count": 0} if evidence is None else evidence,
            "reader_context": {"request_ref": "C:resumed-linked"},
            **extra,
        }

    def retrieve(self, response):
        return contract.retrieve_advisory(
            self.binding(response), "reuse advisory", {"request_ref": "C:resumed-linked"}
        )

    def test_explicit_states_preserve_real_producer_and_context_readback(self):
        cases = {
            "available": {"record_count": 0, "source_receipt": "reader-ready"},
            "unavailable": {"record_count": 0, "source_receipt": "offline"},
            "query_error": {"record_count": 0, "source_receipt": "invalid-query"},
            "match": {"record_count": 2, "content_digest": DIGEST},
            "no_match": {"record_count": 0},
        }
        for state, evidence in cases.items():
            with self.subTest(state=state):
                result = self.retrieve(lambda request, state=state, evidence=evidence: self.response(state, evidence))
                self.assertEqual(result.state, state)
                self.assertEqual(result.producer_ref, "memory://producer/42")
                self.assertEqual(result.source_identity, "source-neutral-memory")
                self.assertEqual(result.source_revision, "r17")
                self.assertEqual(result.reader_context, {"request_ref": "C:resumed-linked"})
                self.assertEqual(result.evidence, evidence)

    def test_unavailable_is_distinct_from_no_match(self):
        unavailable = self.retrieve(lambda request: self.response("unavailable", {"record_count": 0, "source_receipt": "offline"}))
        no_match = self.retrieve(lambda request: self.response("no_match", {"record_count": 0}))
        self.assertNotEqual(unavailable.state, no_match.state)

    def test_bounded_direct_readback_candidate_preserves_candidate_lifecycle(self):
        receipt = "session=source-neutral-memory"
        candidate = {
            "clue": "bounded semantic clue",
            "source_ref": "source-neutral-memory",
            "source_receipt": receipt,
            "lifecycle": "candidate",
            "observed_at": "2026-07-24T03:00:00Z",
        }
        result = self.retrieve(lambda request: self.response(
            "available",
            {"record_count": 1, "content_digest": DIGEST, "source_receipt": receipt},
            candidate=candidate,
        ))
        self.assertEqual(result.candidate, candidate)

        for invalid in (
            {**candidate, "clue": "x" * 257},
            {**candidate, "lifecycle": "accepted"},
            {**candidate, "source_receipt": "other"},
            {**candidate, "source_ref": "other"},
            {**candidate, "observed_at": "not-a-time"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(contract.AdvisoryContractError):
                self.retrieve(lambda request, invalid=invalid: self.response(
                    "available",
                    {"record_count": 1, "content_digest": DIGEST, "source_receipt": receipt},
                    candidate=invalid,
                ))

    def test_rejects_missing_binding_fixture_status_command_and_none_placeholder(self):
        with self.assertRaises(contract.AdvisoryContractError):
            contract.retrieve_advisory(None, "q", {})
        fixture = contract.AdvisoryReaderBinding("fixture://prior", "fixture-source", lambda request: {})
        with self.assertRaises(contract.AdvisoryContractError):
            contract.retrieve_advisory(fixture, "q", {})
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: {"state": "available"})
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: None)

    def test_rejects_unbound_or_semantic_evidence_and_wrong_context_readback(self):
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: self.response("match", {"record_count": 1, "content_digest": DIGEST}, route="ptah"))
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: self.response("match", {"record_count": 1, "content_digest": DIGEST, "route": "ptah"}))
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: {**self.response("no_match"), "reader_context": {"request_ref": "other"}})

    def test_rejects_match_without_producer_evidence_and_nonzero_no_match(self):
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: self.response("match", {"record_count": 0}))
        with self.assertRaises(contract.AdvisoryContractError):
            self.retrieve(lambda request: self.response("no_match", {"record_count": 1}))


if __name__ == "__main__":
    unittest.main()
