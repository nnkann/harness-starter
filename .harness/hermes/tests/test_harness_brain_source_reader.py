import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "readers"
    / "harness_brain_source_reader.py"
)
SPEC = importlib.util.spec_from_file_location("harness_brain_source_reader", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HarnessBrainSourceReaderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "harness-brain"
        self.root.mkdir()
        self.source = self.root / "projects" / "contract.md"
        self.source.parent.mkdir()
        self.source.write_bytes(b"bounded source")
        self.outside = Path(self.tempdir.name) / "outside.md"
        self.outside.write_bytes(b"outside")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_reads_only_an_explicit_in_bound_source_and_preserves_identity(self):
        result = MODULE.read_harness_brain_source("projects/contract.md", self.root, max_bytes=32)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["source_ref"], "projects/contract.md")
        self.assertEqual(result["source_identity"], str(self.source.resolve()))
        self.assertEqual(result["readback"], {"content": b"bounded source", "byte_count": 14})
        self.assertNotIn("reason", result)

    def test_absent_unreadable_invalid_and_out_of_bound_are_explicitly_unavailable(self):
        cases = {
            "absent": ("projects/missing.md", self.root, 32),
            "unreadable": ("projects", self.root, 32),
            "invalid": ("../outside.md", self.root, 32),
            "out_of_bound": (str(self.outside), self.root, 32),
        }
        for expected_reason, (source_ref, root, max_bytes) in cases.items():
            with self.subTest(reason=expected_reason):
                result = MODULE.read_harness_brain_source(source_ref, root, max_bytes=max_bytes)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["source_ref"], source_ref)
                self.assertIsNone(result["readback"])
                self.assertEqual(result["reason"], expected_reason)

    def test_rejects_oversized_source_without_partial_readback(self):
        (self.root / "projects" / "large.md").write_bytes(b"0123456789")

        result = MODULE.read_harness_brain_source("projects/large.md", self.root, max_bytes=9)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "out_of_bound")
        self.assertIsNone(result["readback"])

    def test_invalid_ref_or_bound_returns_an_explicit_unavailable_receipt(self):
        for source_ref, max_bytes in (("", 32), ("projects/contract.md", 0)):
            with self.subTest(source_ref=source_ref, max_bytes=max_bytes):
                result = MODULE.read_harness_brain_source(source_ref, self.root, max_bytes=max_bytes)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["reason"], "invalid")
                self.assertIsNone(result["readback"])


if __name__ == "__main__":
    unittest.main()
