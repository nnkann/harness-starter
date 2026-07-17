import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/cps_expression_lint.py"
spec = importlib.util.spec_from_file_location("cps_expression_lint", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def packet_with_mapping_order(reverse: bool):
    step_items = [
        ("order", 1),
        ("p", ["P:one"]),
        ("s", ["S:one"]),
        ("role_in_expression", "review"),
        ("judgment_function", "invalid.judgment"),
        ("review_or_audit", {"type": "different.judgment"}),
        ("actor_binding", {}),
        ("consumes", "not-a-list"),
        ("emits", []),
    ]
    packet_items = [
        ("root_goal_id", "goal-1"),
        ("flow_graph_id", "graph-1"),
        ("root_goal", "deterministic diagnostics"),
        ("source_refs", ["source-1"]),
        ("c", {"id": "C:one", "concern": "ordering"}),
        ("flow_expression", [dict(reversed(step_items) if reverse else step_items)]),
    ]
    return dict(reversed(packet_items) if reverse else packet_items)


class CpsExpressionLintTests(unittest.TestCase):
    def test_diagnostics_are_byte_equivalent_across_mapping_insertion_orders(self):
        forward = module.validate(packet_with_mapping_order(False))
        reverse = module.validate(packet_with_mapping_order(True))

        self.assertGreater(len(forward), 1)
        self.assertEqual(forward, sorted(forward))
        self.assertEqual(
            json.dumps(forward, ensure_ascii=False, separators=(",", ":")).encode(),
            json.dumps(reverse, ensure_ascii=False, separators=(",", ":")).encode(),
        )


if __name__ == "__main__":
    unittest.main()