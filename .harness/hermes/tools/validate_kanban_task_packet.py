#!/usr/bin/env python3
"""Validate Harness Kanban promotion artifacts and compact task-node markers."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any
try:
    import yaml
except Exception:
    yaml = None

REQUIRED_PACKET = ["root_goal_id","flow_graph_id","CPS","task_AC","owner_approval_boundary","prohibited_actions","evidence_acquisition","required_docs","doc_ops_needed","source_refs","artifact_refs","doc_refs"]
REQUIRED_EVIDENCE = ["C","P","S"]
REQUIRED_NODE_MARKERS = ["packet_ref","root_goal_id","flow_graph_id","node_id","actor_binding","task_AC","expected_evidence","source_refs","artifact_refs","owner_approval_boundary","prohibited_actions","evidence_acquisition","doc_refs"]
PROHIBITED_RAW = ["full git diff", "full sqlite", "full test output", "raw stdout", "full raw transcript"]

def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        # Dependency-free fallback: collect top-level mapping keys only. This is
        # sufficient for marker/field-presence validation in constrained worker
        # environments where PyYAML is unavailable.
        data: dict[str, Any] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(" ") and ":" in line:
                key, _, value = line.partition(":")
                data[key.strip()] = value.strip() or {}
        return data
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}

def validate_packet(path: Path) -> list[str]:
    text_raw = path.read_text(encoding="utf-8")
    data = load_yaml(path)
    errors = [f"missing packet field: {k}" for k in REQUIRED_PACKET if k not in data]
    ev_text = text_raw[text_raw.find("evidence_acquisition:"):] if "evidence_acquisition:" in text_raw else ""
    for k in REQUIRED_EVIDENCE:
        if not re.search(rf"^\s+{re.escape(k)}\s*:", ev_text, re.MULTILINE):
            errors.append(f"missing evidence_acquisition.{k}")
    if "digest-first" not in ev_text:
        errors.append("evidence_acquisition must declare digest-first mode/strategy")
    text = text_raw.lower()
    if any(term in text and "prohibited" not in text[max(0, text.find(term)-80):text.find(term)+80] for term in PROHIBITED_RAW):
        errors.append("packet appears to request raw corpus evidence outside prohibited policy")
    return errors

def validate_doc(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not text.startswith("---\n"):
        errors.append("markdown document missing YAML frontmatter")
        return errors
    end = text.find("\n---", 4)
    if end == -1:
        errors.append("markdown document frontmatter is not closed")
        return errors
    fm = text[4:end]
    for field in ["title:","description:","domain:","status:","c:","problem:","s:","tags:","owner_approval_boundary:","prohibited_actions:"]:
        if field not in fm:
            errors.append(f"frontmatter missing {field.rstrip(':')}")
    return errors

def validate_node(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = [f"compact task node missing marker: {m}" for m in REQUIRED_NODE_MARKERS if not re.search(rf"(^|\n){re.escape(m)}\s*:", text)]
    if "Do not close the root goal" not in text:
        errors.append("compact task node missing root-closure warning")
    if len(text.splitlines()) > 120:
        errors.append("task node body is too large; use compact packet_ref + node-local task_AC")
    return errors

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["packet","doc","node"])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    all_errors: dict[str, list[str]] = {}
    for raw in args.paths:
        path = Path(raw)
        if args.mode == "packet":
            errors = validate_packet(path)
        elif args.mode == "doc":
            errors = validate_doc(path)
        else:
            errors = validate_node(path)
        if errors:
            all_errors[str(path)] = errors
    result = {"schema":"harness-task-packet-doc-marker-validation", "ok": not all_errors, "errors": all_errors}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if all_errors else 0
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
