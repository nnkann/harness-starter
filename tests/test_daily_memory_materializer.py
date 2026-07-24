from datetime import datetime
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/daily_memory_materializer.py"
SCHEMA = ROOT / "contracts/daily-memory-declaration.v1.schema.json"
spec = importlib.util.spec_from_file_location("daily_memory_materializer", TOOL)
assert spec is not None and spec.loader is not None
materializer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = materializer
spec.loader.exec_module(materializer)


class DailyMemoryMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 24, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    def test_actual_bounded_sources_emit_only_refs_hashes_and_unavailable_layers(self):
        now = datetime(2026, 7, 24, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        value = materializer.materialize(now)
        Draft202012Validator(json.loads(SCHEMA.read_text())).validate(value)
        self.assertEqual((value["collection_ref"], value["materialized_date"]), ("daily:2026-07-24", "2026-07-24"))
        layers = {layer["layer_id"]: layer for layer in value["layers"]}
        harness_brain = layers["harness_brain"]
        self.assertEqual(
            harness_brain["canonical_revision"],
            "sha256:" + hashlib.sha256(materializer.EQUATION.read_bytes()).hexdigest(),
        )
        self.assertEqual(harness_brain["pointer_digest"], hashlib.sha256(materializer.HANDOFF.read_bytes()).hexdigest())
        self.assertEqual(
            harness_brain["canonical_index_revision"],
            "sha256:" + hashlib.sha256(materializer.MANIFEST.read_bytes()).hexdigest(),
        )
        self.assertEqual((harness_brain["pointer_integrity"], harness_brain["canonical_index_aligned"]), ("valid", True))
        for layer_id in ("honcho", "gbrain"):
            self.assertEqual(layers[layer_id]["availability"], "unavailable")
            self.assertIsNone(layers[layer_id]["canonical_revision"])
        encoded = materializer.canonical_bytes(value)
        for prohibited in (b"raw_content", b"raw_log", b"transcript", b"# CPS", b"SIA Memory Stewardship"):
            self.assertNotIn(prohibited, encoded)

    def test_freshness_uses_asia_seoul_and_stale_fails_closed(self):
        seoul = ZoneInfo("Asia/Seoul")
        value = materializer.materialize(datetime(2026, 7, 24, 0, 1, tzinfo=seoul))
        materializer.validate_fresh(value, datetime(2026, 7, 24, 23, 59, tzinfo=seoul))
        with self.assertRaises(materializer.MaterializationError):
            materializer.validate_fresh(value, datetime(2026, 7, 25, 0, 0, tzinfo=seoul))

    def test_atomic_write_fsync_replace_and_digest_readback(self):
        value = materializer.materialize(datetime(2026, 7, 24, 12, 0, tzinfo=ZoneInfo("Asia/Seoul")))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "declaration.json"
            verification = materializer.atomic_write(value, destination)
            readback = destination.read_bytes()
            self.assertEqual(verification["sha256"], hashlib.sha256(readback).hexdigest())
            self.assertTrue(verification["readback_verified"])
            self.assertFalse(destination.with_name(destination.name + ".tmp").exists())

    def test_unavailable_canonical_input_fails_without_replacing_prior(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "declaration.json"
            destination.write_bytes(b"prior\n")
            missing = Path(directory) / "missing.md"
            with mock.patch.object(materializer, "EQUATION", missing), self.assertRaises(materializer.MaterializationError):
                materializer.run(destination)
            self.assertEqual(destination.read_bytes(), b"prior\n")

    def test_schema_and_runtime_reject_layer_set_and_availability_shape_mutations(self):
        valid = materializer.materialize(self.now)
        validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
        mutations = {}

        duplicate = deepcopy(valid)
        duplicate["layers"][2] = deepcopy(duplicate["layers"][1])
        mutations["duplicate layer"] = duplicate

        missing = deepcopy(valid)
        missing["layers"].pop()
        mutations["missing layer"] = missing

        unknown = deepcopy(valid)
        unknown["layers"][2]["layer_id"] = "unknown"
        mutations["unknown layer"] = unknown

        available_null = deepcopy(valid)
        available_null["layers"][0]["canonical_source_ref"] = None
        mutations["available null field"] = available_null

        available_unknown_integrity = deepcopy(valid)
        available_unknown_integrity["layers"][0]["pointer_integrity"] = "unknown"
        mutations["available unknown integrity"] = available_unknown_integrity

        unavailable_value = deepcopy(valid)
        unavailable_value["layers"][1]["canonical_source_ref"] = "/unexpected"
        mutations["unavailable non-null field"] = unavailable_value

        unavailable_valid_integrity = deepcopy(valid)
        unavailable_valid_integrity["layers"][1]["pointer_integrity"] = "valid"
        mutations["unavailable valid integrity"] = unavailable_valid_integrity

        conflicts = deepcopy(valid)
        conflicts["layers"][0]["conflicts"] = ["unexpected"]
        mutations["non-empty conflicts"] = conflicts

        for name, mutation in mutations.items():
            with self.subTest(name=name, validator="schema"):
                self.assertFalse(validator.is_valid(mutation))
            with self.subTest(name=name, validator="runtime"):
                with self.assertRaises(materializer.MaterializationError):
                    materializer.validate_declaration(mutation)

    def test_invalid_declaration_preserves_prior_destination(self):
        invalid = materializer.materialize(self.now)
        invalid["layers"][2] = deepcopy(invalid["layers"][1])
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "declaration.json"
            destination.write_bytes(b"prior\n")
            with mock.patch.object(materializer, "materialize", return_value=invalid):
                with self.assertRaises(materializer.MaterializationError):
                    materializer.run(destination, self.now)
            self.assertEqual(destination.read_bytes(), b"prior\n")


if __name__ == "__main__":
    unittest.main()
