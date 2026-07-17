import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))

import cps_runtime_navigation as navigation


class CpsRuntimeNavigationTests(unittest.TestCase):
    def anchor_source(self, root: Path):
        del root
        source = ROOT.parent / "harness-brain" / "projects" / ROOT.name / "decisions" / "cps-memory-lifecycle-and-honcho-anchor.md"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        revision = subprocess.check_output(["git", "-C", str(source.parent), "rev-parse", "HEAD"], text=True).strip()
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        binding = {
            "canonical_source_locator": str(source),
            "canonical_source_readback": f"{source}:1-{line_count}",
            "current_source_revision": revision,
            "current_content_hash": digest,
            "canonical_section": f"{source}:75-108",
            "semantic_field_definition_coverage": {
                "schema": f"{source}:78",
                "C.shape": f"{source}:85",
            },
        }
        body = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        return source, binding, body

    def test_six_proof_binding_reads_exact_anchor_section_and_maps_every_present_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, binding, body = self.anchor_source(Path(tmp))
            result = navigation.validate_semantic_provenance(binding, body)
        self.assertEqual(result, {"status": "pass", "failure_codes": []})

    def test_complete_canonical_body_preserves_p_to_s_targets_with_exact_coverage(self):
        _, binding, _ = self.anchor_source(Path("unused"))
        source = Path(binding["canonical_source_locator"])
        _, definitions = navigation._anchor_definition_refs(source, source.read_text(encoding="utf-8"))
        body = {
            "schema": "harness.honcho.cps_cluster.v1",
            "cluster_key": "harness-starter/anchor/decision",
            "source_id": str(source),
            "source_revision": "revision",
            "content_hash": "hash",
            "C": {"shape": "bounded", "boundary_hint": "single", "domain": ["harness-starter"]},
            "P_order": [{"id": "P1", "statement": "definition proof required"}],
            "S_mapping": [{"id": "S1", "targets": ["P1"], "operator": "validate before action"}],
            "AC_anchor": ["hold on mismatch"],
            "goal_state": "partial",
            "source_refs": [str(source)],
            "gbrain_pointers": [],
            "lifecycle": "validated",
            "freshness": "current",
            "expires_at": None,
            "supersedes": None,
        }
        binding["semantic_field_definition_coverage"] = definitions
        before = json.loads(json.dumps(body))

        self.assertEqual(
            navigation.validate_semantic_provenance(binding, body),
            {"status": "pass", "failure_codes": []},
        )
        self.assertEqual(body, before)
        self.assertEqual(body["S_mapping"][0]["targets"], [body["P_order"][0]["id"]])

    def test_semantic_provenance_holds_on_each_proof_mismatch_and_unmapped_or_undefined_leaf(self):
        mutations = {
            "missing": lambda value: value.pop("canonical_source_locator"),
            "unreadable": lambda value: value.__setitem__("canonical_source_locator", "/missing/canonical-source.md"),
            "readback": lambda value: value.__setitem__("canonical_source_readback", "prior route readback"),
            "revision": lambda value: value.__setitem__("current_source_revision", "0" * 40),
            "hash": lambda value: value.__setitem__("current_content_hash", "0" * 64),
            "section": lambda value: value.__setitem__("canonical_section", "Prior Maat message"),
            "map": lambda value: value["semantic_field_definition_coverage"].pop("C.shape"),
            "empty_map": lambda value: value.__setitem__("semantic_field_definition_coverage", {}),
            "typo_map": lambda value: value.__setitem__("semantic_field_definition_coverage", {"schema_typo": "source:78"}),
            "outside_section": lambda value: value["semantic_field_definition_coverage"].__setitem__("C.shape", f"{value['canonical_source_locator']}:1"),
            "prior_maat": lambda value: value["semantic_field_definition_coverage"].__setitem__("C.shape", "prior Maat route.C"),
            "prior_stdout": lambda value: value["semantic_field_definition_coverage"].__setitem__("C.shape", "prior Maat stdout"),
            "prior_session": lambda value: value["semantic_field_definition_coverage"].__setitem__("C.shape", "prior Maat session"),
            "prior_receipt": lambda value: value["semantic_field_definition_coverage"].__setitem__("C.shape", "prior receipt authority"),
            "default_synthesis": lambda value: value.__setitem__("current_source_revision", "default-synthesized-revision"),
        }
        for case, mutate in mutations.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                _, binding, body = self.anchor_source(Path(tmp))
                mutate(binding)
                result = navigation.validate_semantic_provenance(binding, body)
                self.assertEqual(result["status"], "hold")
                self.assertEqual(result["failure_codes"], ["HOLD_UNMAPPED_SEMANTIC_FIELD"])
        with tempfile.TemporaryDirectory() as tmp:
            _, binding, body = self.anchor_source(Path(tmp))
            body["invented"] = "must not synthesize"
            binding["semantic_field_definition_coverage"]["invented"] = f"{binding['canonical_source_locator']}:85"
            self.assertEqual(
                navigation.validate_semantic_provenance(binding, body)["failure_codes"],
                ["HOLD_UNMAPPED_SEMANTIC_FIELD"],
            )
        with tempfile.TemporaryDirectory() as tmp:
            _, binding, body = self.anchor_source(Path(tmp))
            body["S_mapping"] = [{"id": "S1", "targets": ["P1"], "operator": "map"}]
            binding["semantic_field_definition_coverage"].update({
                "S_mapping[].id": f"{binding['canonical_source_locator']}:94",
                "S_mapping[].targets": f"{binding['canonical_source_locator']}:95",
            })
            self.assertEqual(
                navigation.validate_semantic_provenance(binding, body)["failure_codes"],
                ["HOLD_UNMAPPED_SEMANTIC_FIELD"],
            )
    def make_project(self, root: Path):
        repo = root / "harness-starter"
        authority = root / "harness-brain" / "projects" / repo.name
        repo.mkdir(parents=True)
        authority.mkdir(parents=True)
        (repo / "README.md").write_text(
            "# starter\n\n## Project entry point\n\nCanonical authority is `harness-brain`.\n\n## Other\n",
            encoding="utf-8",
        )
        refs = {
            "source": authority / "decisions" / "source.md",
            "contract": authority / "contracts" / "contract.md",
            "working_graph": authority / "working-graphs" / "graph.json",
            "runtime": repo / ".harness" / "hermes" / "tools" / "runtime.py",
            "test": repo / "tests" / "test_runtime.py",
            "receipt": repo / ".harness" / "project" / "runs" / "receipt.json",
        }
        for path in refs.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("CANONICAL-CPS-BODY-MUST-NOT-LEAK", encoding="utf-8")
        return repo, authority, refs

    def request(self, target: str, ref: Path, **entry):
        return {
            "requested_target": target,
            "requested_refs": [{"ref": str(ref), "source_revision": "r1", **entry}],
        }

    def test_resolves_each_bounded_target_from_readme_authority_without_raw_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, authority, refs = self.make_project(Path(tmp))
            for target, ref in refs.items():
                with self.subTest(target=target):
                    receipt = navigation.navigate_cps_runtime(repo, self.request(target, ref))
                    self.assertEqual(set(receipt), {
                        "schema", "entry_source_ref", "canonical_authority_ref", "requested_target",
                        "resolved_refs", "source_revisions", "source_digests", "status",
                        "diagnostic_codes", "c1_runtime_closure",
                    })
                    self.assertEqual(receipt["schema"], "harness.cps_runtime_navigation_receipt.v1")
                    self.assertEqual(receipt["entry_source_ref"], f"{repo / 'README.md'}#Project-entry-point")
                    self.assertEqual(receipt["canonical_authority_ref"], str(authority))
                    self.assertEqual(receipt["requested_target"], target)
                    self.assertEqual(receipt["resolved_refs"], [str(ref)])
                    self.assertEqual(receipt["source_revisions"], {str(ref): "r1"})
                    self.assertEqual(len(receipt["source_digests"][str(ref)]), 64)
                    self.assertEqual(receipt["status"], "resolved")
                    self.assertEqual(receipt["diagnostic_codes"], [])
                    self.assertIs(receipt["c1_runtime_closure"], False)
                    self.assertNotIn("CANONICAL-CPS-BODY-MUST-NOT-LEAK", json.dumps(receipt))

    def test_holds_each_navigation_boundary_failure(self):
        cases = (
            ("missing_entry", "HOLD_RUNTIME_NAVIGATION_ENTRY_MISSING"),
            ("missing_authority", "HOLD_RUNTIME_NAVIGATION_AUTHORITY_MISSING"),
            ("ambiguous_target", "HOLD_RUNTIME_NAVIGATION_TARGET_AMBIGUOUS"),
            ("revision_mismatch", "HOLD_RUNTIME_NAVIGATION_REVISION_MISMATCH"),
            ("path_escape", "HOLD_RUNTIME_NAVIGATION_PATH_ESCAPE"),
            ("unapproved_root", "HOLD_RUNTIME_NAVIGATION_UNAPPROVED_ROOT"),
        )
        for case, diagnostic in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, authority, refs = self.make_project(root)
                request = self.request("contract", refs["contract"])
                if case == "missing_entry":
                    (repo / "README.md").write_text("# no entry\n", encoding="utf-8")
                elif case == "missing_authority":
                    for path in sorted(authority.rglob("*"), reverse=True):
                        path.unlink() if path.is_file() else path.rmdir()
                    authority.rmdir()
                elif case == "ambiguous_target":
                    request["requested_target"] = ["contract", "runtime"]
                elif case == "revision_mismatch":
                    request["requested_refs"][0]["expected_revision"] = "r2"
                elif case == "path_escape":
                    escaped = authority / "secret.md"
                    escaped.write_text("secret", encoding="utf-8")
                    request["requested_refs"][0]["ref"] = "contracts/../secret.md"
                elif case == "unapproved_root":
                    outside = root / "outside.md"
                    outside.write_text("outside", encoding="utf-8")
                    request["requested_refs"][0]["ref"] = str(outside)

                receipt = navigation.navigate_cps_runtime(repo, request)
                self.assertEqual(receipt["status"], "hold")
                self.assertIn(diagnostic, receipt["diagnostic_codes"])
                self.assertEqual(receipt["resolved_refs"], [])
                self.assertIs(receipt["c1_runtime_closure"], False)


if __name__ == "__main__":
    unittest.main()
