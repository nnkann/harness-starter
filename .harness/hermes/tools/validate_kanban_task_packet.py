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
from cps_runtime_navigation import validate_semantic_provenance

REQUIRED_PACKET = ["root_goal_id","flow_graph_id","CPS","task_AC","owner_approval_boundary","prohibited_actions","evidence_acquisition","required_docs","doc_ops_needed","source_refs","artifact_refs","doc_refs"]
REQUIRED_EVIDENCE = ["C","P","S"]
REQUIRED_NODE_MARKERS = ["packet_ref","root_goal_id","flow_graph_id","node_id","actor_binding","task_AC","expected_evidence","source_refs","artifact_refs","owner_approval_boundary","prohibited_actions","evidence_acquisition","doc_refs"]
PROHIBITED_RAW = ["full git diff", "full sqlite", "full test output", "raw stdout", "full raw transcript"]

def _fallback_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return {}
    if value in {"null", "~"}:
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_fallback_scalar(item) for item in inner.split(",")]
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip("'\"")


def _fallback_yaml(text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

    def parse(index: int, indent: int) -> tuple[Any, int]:
        is_list = lines[index].lstrip().startswith("- ")
        result: Any = [] if is_list else {}
        while index < len(lines):
            raw = lines[index]
            current = len(raw) - len(raw.lstrip())
            if current < indent or current == indent and raw.lstrip().startswith("- ") != is_list:
                break
            if current > indent:
                break
            line = raw.strip()
            if is_list:
                item = line[2:].strip()
                if ":" in item:
                    key, value = item.split(":", 1)
                    entry = {key.strip(): _fallback_scalar(value)}
                    if index + 1 < len(lines) and len(lines[index + 1]) - len(lines[index + 1].lstrip()) > indent:
                        nested, index = parse(index + 1, indent + 2)
                        if isinstance(nested, dict):
                            entry.update(nested)
                    else:
                        index += 1
                    result.append(entry)
                    continue
                result.append(_fallback_scalar(item))
                index += 1
                continue
            key, value = line.split(":", 1)
            if value.strip():
                result[key.strip()] = _fallback_scalar(value)
                index += 1
                continue
            if index + 1 < len(lines) and len(lines[index + 1]) - len(lines[index + 1].lstrip()) > indent:
                result[key.strip()], index = parse(index + 1, len(lines[index + 1]) - len(lines[index + 1].lstrip()))
            else:
                result[key.strip()] = {}
                index += 1
        return result, index

    parsed, _ = parse(0, 0)
    return parsed if isinstance(parsed, dict) else {}


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return _fallback_yaml(text)
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}

def validate_packet(path: Path) -> list[str]:
    text_raw = path.read_text(encoding="utf-8")
    data = load_yaml(path)
    errors = [f"missing packet field: {k}" for k in REQUIRED_PACKET if k not in data]
    anchor_semantics = "semantic_anchor" in data or "semantic_provenance_binding" in data
    provenance = validate_semantic_provenance(data.get("semantic_provenance_binding"), data.get("semantic_anchor"))
    if anchor_semantics and provenance["status"] != "pass":
        errors.append("HOLD_UNMAPPED_SEMANTIC_FIELD")
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
