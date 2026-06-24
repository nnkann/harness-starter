#!/usr/bin/env python3
"""LazyCodex doc_ops LLM Wiki & Abbreviation Matcher.
Implements S3: Domain abbreviation (abbr) lookup, high-speed LLM Wiki context injection, and doc_ops manifest integration.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Find repository root
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".harness" / "hermes" / "loader.py").exists():
            return parent
    return Path("/Users/kann/projects/harness-starter")

REPO_ROOT = find_repo_root()
GUIDES_DIR = REPO_ROOT / ".harness" / "project" / "docs" / "guides"
ABBR_FILE = GUIDES_DIR / "abbr_dict.json"

# Default fallback abbreviation dictionary (Harness Domain Abbrs)
DEFAULT_ABBRS = {
    "CPS": "Context-Problem-Solution framework. Every Harness task compiles into C, P, S segments.",
    "AC": "Acceptance Criteria. Defines strict boundaries and checks for task completion.",
    "SSOT": "Single Source of Truth. The authoritative data schema or policy branch (hermes/harness-starter-baseline).",
    "LOC": "Lines of Code. Limit enforced by Ponytail (100 LOC maximum per task).",
    "LLM Wiki": "Low-token, high-speed wiki mapping domain schemas and decisions into active prompt context.",
    "Maat": "The Harness moderator profile acting as an absolute audit gatekeeper (T8) before task merge.",
    "Thoth": "The Harness orchestrator profile responsible for contract compilation (T4) and routing.",
    "Ptah": "The Harness implementation coder profile responsible for task execution.",
    "Sia": "The Harness cognitive analyzer profile responsible for perception diagnostics under minimal tool restrictions.",
    "Anubis": "The Harness reviewer/cleanup profile responsible for active session pruning and snapshot writebacks.",
    "Ponytail": "The Lazy Dev's Ladder principles limiting LOC, imports, and unnecessary try-catch code bloat."
}

def load_abbreviation_dictionary() -> dict[str, str]:
    """Loads abbreviation dictionary from file or falls back to defaults."""
    if not ABBR_FILE.exists():
        # Write defaults to establish file presence
        try:
            GUIDES_DIR.mkdir(parents=True, exist_ok=True)
            ABBR_FILE.write_text(json.dumps(DEFAULT_ABBRS, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[LLM Wiki] Failed to write default abbr_dict.json: {e}\n")
        return DEFAULT_ABBRS
    try:
        return json.loads(ABBR_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"[LLM Wiki] Error loading abbreviation file: {e}. Using defaults.\n")
        return DEFAULT_ABBRS

def search_wiki(query: str) -> dict[str, str]:
    """Scans the abbreviation dictionary and returns matched domain abbreviations."""
    abbrs = load_abbreviation_dictionary()
    query_lower = query.lower()
    matches = {}
    for key, val in abbrs.items():
        if key.lower() in query_lower or query_lower in key.lower() or any(word in val.lower() for word in query_lower.split()):
            matches[key] = val
    return matches

def inject_context_block(matches: dict[str, str]) -> str:
    """Builds a structured prompt context block from matches to inject into LLM prompt."""
    if not matches:
        return ""
    
    block = [
        "## [LLM Wiki] Active Domain Abbreviation & Schema Context",
        "The following validated domain terms are active in the current workspace context:",
    ]
    for key, val in matches.items():
        block.append(f"- **{key}**: {val}")
    block.append("\n*Reference Authority: Harness doc_ops LLM Wiki System.*")
    return "\n".join(block)

def main() -> int:
    parser = argparse.ArgumentParser(description="LazyCodex doc_ops LLM Wiki lookup tool")
    parser.add_argument("query", nargs="?", default="", help="Query or text to analyze for abbreviation matching")
    parser.add_argument("--json", action="store_true", help="Output results in raw JSON format")
    args = parser.parse_args()
    
    if not args.query:
        # Dump entire dictionary
        abbrs = load_abbreviation_dictionary()
        if args.json:
            print(json.dumps(abbrs, indent=2, ensure_ascii=False))
        else:
            print("=== Active LLM Wiki Abbreviation Dictionary ===")
            for k, v in abbrs.items():
                print(f"  - {k:10}: {v}")
        return 0
        
    matches = search_wiki(args.query)
    
    if args.json:
        print(json.dumps(matches, indent=2, ensure_ascii=False))
    else:
        if matches:
            print(inject_context_block(matches))
        else:
            print("[LLM Wiki] No domain abbreviation matches found in active dictionaries.")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())
