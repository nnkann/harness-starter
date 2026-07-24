import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/daily_memory_collector.py"
SCHEMA = ROOT / "contracts/daily-memory-receipt.v1.schema.json"
spec = importlib.util.spec_from_file_location("daily_memory_collector", TOOL)
assert spec is not None and spec.loader is not None
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
spec.loader.exec_module(collector)

A = "a" * 64
B = "b" * 64


def declaration():
    return {
        "schema": collector.DECLARATION_SCHEMA,
        "collection_ref": "daily:2026-07-24",
        "timestamp": "2026-07-24T00:00:00Z",
        "raw_logs": "must not survive",
        "layers": [
            {
                "layer_id": "honcho",
                "availability": "available",
                "canonical_source_ref": "source:honcho",
                "canonical_revision": "sha256:" + A,
                "pointer_ref": "pointer:honcho",
                "pointer_digest": A,
                "pointer_integrity": "valid",
                "canonical_index_ref": "index:honcho",
                "canonical_index_revision": "sha256:" + B,
                "canonical_index_aligned": True,
                "verified_outcome_eligible": False,
                "conflicts": [],
                "ranking": ["ignored"],
            },
            {
                "layer_id": "harness_brain",
                "availability": "unavailable",
                "canonical_source_ref": None,
                "canonical_revision": None,
                "pointer_ref": None,
                "pointer_digest": None,
                "pointer_integrity": "unknown",
                "canonical_index_ref": None,
                "canonical_index_revision": None,
                "canonical_index_aligned": None,
                "verified_outcome_eligible": None,
                "conflicts": [],
            },
            {
                "layer_id": "gbrain",
                "availability": "unavailable",
                "canonical_source_ref": None,
                "canonical_revision": None,
                "pointer_ref": None,
                "pointer_digest": None,
                "pointer_integrity": "unknown",
                "canonical_index_ref": None,
                "canonical_index_revision": None,
                "canonical_index_aligned": None,
                "verified_outcome_eligible": None,
                "conflicts": [],
            },
        ],
    }


class DailyMemoryCollectorTests(unittest.TestCase):
    def test_same_fixture_is_byte_identical_and_first_run_is_clean(self):
        first = collector.collect(declaration())
        second = collector.collect(copy.deepcopy(declaration()))
        self.assertEqual(collector.canonical_bytes(first), collector.canonical_bytes(second))
        self.assertEqual(first["comparison"], {
            "baseline": True,
            "meaningful_delta": False,
            "delta_classes": [],
            "disposition": "clean",
        })
        self.assertEqual(first["consumer"], {"intent": None, "invocation_count": 0, "packet": None})

    def test_clean_receipt_is_durable_and_digest_readback_is_verified(self):
        receipt = collector.collect(declaration())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            verification = collector.write_receipt(receipt, path)
            readback = path.read_bytes()
        self.assertTrue(verification["readback_verified"])
        self.assertEqual(verification["receipt_sha256"], hashlib.sha256(readback).hexdigest())
        self.assertEqual(readback, collector.canonical_bytes(receipt))

    def test_one_allowed_delta_emits_one_compact_packet_and_one_intent(self):
        prior = collector.collect(declaration())
        changed = declaration()
        changed["layers"][0]["pointer_integrity"] = "invalid"
        receipt = collector.collect(changed, prior)
        self.assertTrue(receipt["comparison"]["meaningful_delta"])
        self.assertEqual(receipt["comparison"]["delta_classes"], ["pointer_integrity_transition"])
        self.assertEqual(receipt["consumer"]["invocation_count"], 1)
        packet = receipt["consumer"]["packet"]
        self.assertEqual(packet["changes"], [
            {"layer_id": "gbrain", "classes": []},
            {"layer_id": "harness_brain", "classes": []},
            {"layer_id": "honcho", "classes": ["pointer_integrity_transition"]},
        ])
        self.assertEqual(
            packet["packet_digest"],
            hashlib.sha256(collector.canonical_bytes({key: packet[key] for key in ("intent", "collection_ref", "changes")})).hexdigest(),
        )

    def test_transport_noise_repeated_no_match_identical_unavailable_and_ranking_stay_clean(self):
        prior_declaration = declaration()
        prior_declaration["layers"][0]["match_state"] = "no_match"
        prior = collector.collect(prior_declaration)
        current = declaration()
        current["timestamp"] = "2099-01-01T00:00:00Z"
        current["raw_logs"] = "x" * 100000
        current["layers"][0].update(match_state="no_match", ranking=["changed"], raw_transcript="secret")
        current["layers"][1]["raw_content"] = "unavailable detail"
        receipt = collector.collect(current, prior)
        self.assertFalse(receipt["comparison"]["meaningful_delta"])
        self.assertEqual(receipt["consumer"]["invocation_count"], 0)
        encoded = collector.canonical_bytes(receipt)
        for prohibited in (b"raw_logs", b"raw_transcript", b"raw_content", b"secret", b"ranking"):
            self.assertNotIn(prohibited, encoded)

    def test_only_declared_meaningful_classes_trigger(self):
        mutations = {
            "canonical_source_change": lambda d: d["layers"][0].update(canonical_revision="sha256:" + B),
            "pointer_integrity_transition": lambda d: d["layers"][0].update(pointer_integrity="invalid"),
            "canonical_index_alignment_change": lambda d: d["layers"][0].update(canonical_index_aligned=False),
            "verified_outcome_eligibility": lambda d: d["layers"][0].update(verified_outcome_eligible=True),
            (
                "canonical_source_change", "pointer_integrity_transition",
                "canonical_index_alignment_change", "verified_outcome_eligibility",
                "layer_availability_transition",
            ): lambda d: d["layers"][0].update(
                availability="unavailable",
                canonical_source_ref=None,
                canonical_revision=None,
                pointer_ref=None,
                pointer_digest=None,
                pointer_integrity="unknown",
                canonical_index_ref=None,
                canonical_index_revision=None,
                canonical_index_aligned=None,
                verified_outcome_eligible=None,
            ),
            "new_source_backed_conflict": lambda d: d["layers"][0].update(conflicts=[{"conflict_ref": "conflict:1", "source_digest": B}]),
        }
        prior = collector.collect(declaration())
        for expected, mutate in mutations.items():
            current = declaration(); mutate(current)
            with self.subTest(expected=expected):
                self.assertEqual(
                    collector.collect(current, prior)["comparison"]["delta_classes"],
                    sorted(expected if isinstance(expected, tuple) else [expected]),
                )

        conflicted = declaration()
        conflicted["layers"][0]["conflicts"] = [{"conflict_ref": "conflict:1", "source_digest": B}]
        resolved = collector.collect(declaration(), collector.collect(conflicted))
        self.assertEqual(resolved["comparison"]["delta_classes"], ["resolved_source_backed_conflict"])

    def test_every_unavailable_layer_is_preserved_without_raw_material(self):
        value = declaration()
        receipt = collector.collect(value)
        unavailable = [layer["layer_id"] for layer in receipt["state"]["layers"] if layer["availability"] == "unavailable"]
        self.assertEqual(unavailable, ["gbrain", "harness_brain"])
        self.assertNotIn("content", json.dumps(receipt))
        self.assertNotIn("transcript", json.dumps(receipt))
        self.assertNotIn("logs", json.dumps(receipt))

    def test_schema_is_closed_bounded_and_matches_delta_classes(self):
        schema = json.loads(SCHEMA.read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["state"]["additionalProperties"])
        self.assertFalse(schema["properties"]["consumer"]["additionalProperties"])
        self.assertEqual(tuple(schema["$defs"]["deltaClass"]["enum"]), collector.MEANINGFUL_DELTA_CLASSES)
        self.assertEqual(schema["properties"]["consumer"]["properties"]["invocation_count"]["maximum"], 1)

    def test_repo_scope_names_exactly_one_tool_one_schema_one_test(self):
        self.assertEqual(
            {TOOL.relative_to(ROOT).as_posix(), SCHEMA.relative_to(ROOT).as_posix(), Path(__file__).resolve().relative_to(ROOT).as_posix()},
            {".harness/hermes/tools/daily_memory_collector.py", "contracts/daily-memory-receipt.v1.schema.json", "tests/test_daily_memory_collector.py"},
        )


if __name__ == "__main__":
    unittest.main()
