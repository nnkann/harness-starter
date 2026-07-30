import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


READERS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "readers"
sys.path.insert(0, str(READERS))

import gbrain_search_reader as search_reader
import gbrain_skill_reference_resolver as resolver


class GBrainSearchReaderTests(unittest.TestCase):
    def test_invokes_only_bounded_search_with_path_and_timeout(self):
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(
                returncode=0,
                stdout="[0.75] projects/demo/skill.md -- candidate text\n",
                stderr="",
            )

        read = search_reader.create_gbrain_search_reader(limit=3, timeout=2.5, runner=run)
        result = read("live reference")

        command, kwargs = calls[0]
        self.assertEqual(
            command,
            ["/Users/kann/.bun/bin/gbrain", "search", "live reference", "--limit", "3"],
        )
        self.assertEqual(kwargs["timeout"], 2.5)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertTrue(kwargs["PATH"] if "PATH" in kwargs else kwargs["env"]["PATH"].startswith("/Users/kann/.bun/bin:"))
        self.assertEqual(result["status"], "match")
        self.assertEqual(result["candidates"][0]["lifecycle"], "candidate")
        self.assertEqual(result["candidates"][0]["source_ref"], "projects/demo/skill.md")

    def test_query_limit_and_timeout_fail_closed(self):
        runner = mock.Mock(side_effect=subprocess.TimeoutExpired(["gbrain"], 1))
        result = search_reader.create_gbrain_search_reader(runner=runner)("query")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["candidates"], [])

        never = mock.Mock()
        result = search_reader.create_gbrain_search_reader(runner=never)(" bad ")
        self.assertEqual(result["status"], "query_error")
        never.assert_not_called()
        for limit in (0, 11, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                search_reader.create_gbrain_search_reader(limit=limit)


class CanonicalDereferencerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "harness-brain"
        self.root.mkdir()
        self.source = self.root / "projects" / "demo" / "skill.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("canonical skill\n", encoding="utf-8")
        self.revision = lambda root: "a" * 40

    def tearDown(self):
        self.temp.cleanup()

    def dereference(self, source_ref):
        return resolver.dereference_harness_brain_source(
            source_ref,
            harness_brain_root=self.root,
            revision_reader=self.revision,
        )

    def test_success_carries_canonical_identity_digest_count_and_receipt(self):
        result = self.dereference("projects/demo/skill.md")
        content = self.source.read_bytes()

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["canonical_repo"], "harness-brain")
        self.assertEqual(result["repo_relative_path"], "projects/demo/skill.md")
        self.assertEqual(result["current_source_revision"], "a" * 40)
        self.assertEqual(result["content_digest"], hashlib.sha256(content).hexdigest())
        self.assertEqual(result["byte_count"], len(content))
        self.assertIn("repo=harness-brain", result["source_receipt"])
        self.assertEqual(result["usable_clue"], "canonical skill\n")

        absolute = self.dereference(str(self.source))
        self.assertEqual(absolute["repo_relative_path"], "projects/demo/skill.md")

        slug = self.dereference("projects/demo/skill")
        self.assertEqual(slug["repo_relative_path"], "projects/demo/skill.md")

    def test_rejects_absolute_escape_traversal_malformed_and_missing(self):
        cases = {
            str(Path(self.temp.name) / "outside.md"): "absolute_escape",
            "projects/../outside.md": "traversal_ref",
            " projects/demo/skill.md": "malformed_ref",
            "projects\\demo\\skill.md": "malformed_ref",
            "projects/demo/./skill.md": "malformed_ref",
            "https://example.invalid/skill.md": "malformed_ref",
            "projects/demo/missing.md": "missing_target",
        }
        for source_ref, reason in cases.items():
            with self.subTest(source_ref=source_ref):
                result = self.dereference(source_ref)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["reason"], reason)
                self.assertIsNone(result["usable_clue"])

    def test_rejects_symlink_escape(self):
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("not canonical", encoding="utf-8")
        link = self.root / "projects" / "demo" / "escape.md"
        link.symlink_to(outside)
        result = self.dereference("projects/demo/escape.md")
        self.assertEqual(result["reason"], "symlink_escape")
        self.assertIsNone(result["usable_clue"])

    def test_no_canonical_read_means_no_usable_clue(self):
        read = lambda query: {
            "status": "match",
            "candidates": [{
                "source_ref": "projects/demo/missing.md",
                "excerpt": "GBrain text is not a fact",
                "score": 0.5,
                "lifecycle": "candidate",
                "source_receipt": "search-receipt",
            }],
            "evidence": {"record_count": 1, "source_receipt": "search"},
        }
        result = resolver.resolve_skill_live_reference(
            "query", search_reader=read, harness_brain_root=self.root
        )
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["usable_clues"], [])
        self.assertIsNone(result["observations"][0]["usable_clue"])
        self.assertEqual(result["observations"][0]["lifecycle"], "candidate")

    def test_gbrain_and_harness_brain_trees_are_not_written(self):
        gbrain_root = Path(self.temp.name) / "gbrain"
        gbrain_root.mkdir()
        executable = gbrain_root / "gbrain"
        executable.write_text(
            "#!/bin/sh\nprintf '[0.90] projects/demo/skill.md -- indexed candidate\\n'\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
            check=True,
        )
        before_gbrain = _tree_fingerprint(gbrain_root)
        before_brain = _tree_fingerprint(self.root)

        read = search_reader.create_gbrain_search_reader(executable=str(executable), limit=1)
        result = resolver.resolve_skill_live_reference(
            "skill", search_reader=read, harness_brain_root=self.root
        )

        self.assertEqual(result["status"], "match")
        self.assertEqual(before_gbrain, _tree_fingerprint(gbrain_root))
        self.assertEqual(before_brain, _tree_fingerprint(self.root))


def _tree_fingerprint(root):
    rows = []
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        rows.append((relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns, digest))
    return rows


if __name__ == "__main__":
    unittest.main()
