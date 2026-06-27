#!/usr/bin/env python3
"""LazyCodex doc_ops LLM Wiki & Abbreviation Matcher.
Implements S3: Domain abbreviation (abbr) lookup, high-speed LLM Wiki context injection,
and doc_ops manifest integration, fully indexing real project docs for high-speed local search.
"""

from __future__ import annotations
import argparse
import json
import os
import re
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
DOCS_DIR = REPO_ROOT / ".harness" / "project" / "docs"
GUIDES_DIR = DOCS_DIR / "guides"
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

def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parses frontmatter from a markdown file content."""
    meta: dict[str, Any] = {}
    if not content.startswith("---"):
        return meta
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return meta
        
    frontmatter_text = parts[1]
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        
        # Handle lists like [val1, val2] or yaml lists
        if val.startswith("[") and val.endswith("]"):
            # Parse list: [a, b] -> ['a', 'b']
            items = [item.strip().strip("'\"") for item in val[1:-1].split(",")]
            meta[key] = [i for i in items if i]
        else:
            meta[key] = val.strip("'\"")
            
    return meta

def index_project_docs() -> list[dict[str, Any]]:
    """Recursively scans the project docs directory and indexes all markdown files."""
    indexed_docs: list[dict[str, Any]] = []
    if not DOCS_DIR.exists():
        return indexed_docs
        
    for md_path in DOCS_DIR.rglob("*.md"):
        # Skip archived unless explicitly matched or historical review
        if "archived" in md_path.parts:
            continue
            
        try:
            content = md_path.read_text(encoding="utf-8")
            meta = parse_frontmatter(content)
            
            # 1차: 파일명에서 약어(abbr) 추출
            # 예: hn_doc_naming.md -> hn
            # 패턴: {abbr}_{slug}.md 또는 {폴더}--{abbr}_{slug}.md
            name = md_path.name
            abbr = None
            
            # Strip routing tag if present (e.g. decisions--hn_slug.md)
            clean_name = name.partition("--")[-1] if "--" in name else name
            
            # Match standard naming convention: {abbr}_{slug}.md
            match = re.match(r"^([a-z]{2,3})_", clean_name)
            if match:
                abbr = match.group(1)
                
            indexed_docs.append({
                "path": md_path,
                "rel_path": md_path.relative_to(REPO_ROOT),
                "name": name,
                "abbr": abbr or meta.get("domain", "global"),
                "title": meta.get("title", md_path.stem),
                "domain": meta.get("domain", "global"),
                "problem": meta.get("problem", []),
                "s": meta.get("s", []),
                "tags": meta.get("tags", []),
                "status": meta.get("status", "unknown"),
                "content": content
            })
        except Exception as e:
            sys.stderr.write(f"[LLM Wiki] Error indexing doc {md_path.name}: {e}\n")
            
    return indexed_docs

def search_wiki(query: str) -> dict[str, Any]:
    """Scans the abbreviation dictionary AND indexed project docs for high-speed matching."""
    query_lower = query.strip().lower()
    results: dict[str, Any] = {
        "abbreviations": {},
        "documents": []
    }
    
    # 1. Check abbreviation dictionary
    abbrs = load_abbreviation_dictionary()
    for key, val in abbrs.items():
        if (key.lower() == query_lower or 
            query_lower in key.lower() or 
            any(word in val.lower() for word in query_lower.split())):
            results["abbreviations"][key] = val
            
    # 2. Index and search project docs (1차 도메인/약어 및 2차 CPS/태그 검색)
    docs = index_project_docs()
    
    # Track CPS specific query patterns (e.g., P7, S9, P11)
    is_cps_query = bool(re.match(r"^[ps]\d+$", query_lower))
    
    for doc in docs:
        score = 0
        
        # Helper to convert meta field to list of strings
        def to_list(field: Any) -> list[str]:
            if isinstance(field, list):
                return [str(x).lower() for x in field]
            return [str(field).lower()] if field else []
            
        problems = to_list(doc["problem"])
        solutions = to_list(doc["s"])
        tags = to_list(doc["tags"])
        
        # Match priority 1: Exact CPS match (2차 분류 핵심)
        if is_cps_query:
            if query_lower in problems:
                score += 100
            elif query_lower in solutions:
                score += 100
        else:
            # Match priority 2: Domain/Abbr match (1차 분류 핵심)
            if query_lower == doc["abbr"]:
                score += 80
            elif query_lower == doc["domain"]:
                score += 60
                
            # Match priority 3: Title or Tags match
            if query_lower in doc["title"].lower():
                score += 50
            for tag in tags:
                if query_lower == tag:
                    score += 40
                elif query_lower in tag:
                    score += 20
                    
            # Match priority 4: Problem/Solution mention in other contexts
            for p in problems:
                if query_lower in p:
                    score += 30
            for s in solutions:
                if query_lower in s:
                    score += 30
                    
            # Match priority 5: Body content match (3차)
            if query_lower in doc["content"].lower():
                score += 10
                
        if score > 0:
            # Extract short snippet if not a perfect meta match
            snippet = ""
            lines = doc["content"].splitlines()
            # Find first occurrence of query
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    snippet = "\n".join(lines[start:end])
                    break
                    
            results["documents"].append({
                "name": doc["name"],
                "rel_path": str(doc["rel_path"]),
                "title": doc["title"],
                "domain": doc["domain"],
                "abbr": doc["abbr"],
                "problem": doc["problem"],
                "s": doc["s"],
                "tags": doc["tags"],
                "status": doc["status"],
                "score": score,
                "snippet": snippet
            })
            
    # Sort documents by score descending
    results["documents"].sort(key=lambda x: x["score"], reverse=True)
    return results

def inject_context_block(query: str, results: dict[str, Any]) -> str:
    """Builds a structured high-speed prompt context block from matches."""
    block = [
        f"## [LLM Wiki] Active Domain & Document Context for: '{query}'",
        "The following validated domain terms, CPS classifications, and documents are active:"
    ]
    
    # Add matched abbreviations
    if results["abbreviations"]:
        block.append("\n### Matched Abbreviations:")
        for key, val in results["abbreviations"].items():
            block.append(f"- **{key}**: {val}")
            
    # Add matched documents
    if results["documents"]:
        block.append("\n### Relevant Project Documents (Indexed by doc_ops):")
        for i, doc in enumerate(results["documents"][:5]): # Limit to top 5 for speed and low token count
            tags_str = ", ".join(doc["tags"]) if doc["tags"] else "none"
            cps_str = ""
            if doc["problem"]:
                cps_str += f" | Problem: {doc['problem']}"
            if doc["s"]:
                cps_str += f" | Solution: {doc['s']}"
                
            block.append(f"{i+1}. **[{doc['title']}]({Path(REPO_ROOT / doc['rel_path']).as_uri()})**")
            block.append(f"   - **Path**: `{doc['rel_path']}` | **Domain**: `{doc['domain']}` (`{doc['abbr']}`){cps_str} | **Tags**: `{tags_str}`")
            if doc["snippet"]:
                indented_snippet = "\n".join(f"     > {line}" for line in doc["snippet"].splitlines())
                block.append(f"   - **Snippet**:\n{indented_snippet}")
                
    block.append("\n*Reference Authority: Harness doc_ops LLM Wiki System. High-speed 1st/2nd tier index verified.*")
    return "\n".join(block)

def main() -> int:
    parser = argparse.ArgumentParser(description="LazyCodex doc_ops LLM Wiki & High-Speed Search")
    parser.add_argument("query", nargs="?", default="", help="Query to analyze for abbreviation and CPS matching")
    parser.add_argument("--json", action="store_true", help="Output results in raw JSON format")
    args = parser.parse_args()
    
    if not args.query:
        # Index all and dump summary
        abbrs = load_abbreviation_dictionary()
        docs = index_project_docs()
        if args.json:
            print(json.dumps({
                "abbreviations": abbrs,
                "document_count": len(docs),
                "documents": [{k: v for k, v in d.items() if k != "content"} for d in docs]
            }, indent=2, ensure_ascii=False, default=str))
        else:
            print("=== Active LLM Wiki Abbreviation Dictionary ===")
            for k, v in abbrs.items():
                print(f"  - {k:10}: {v}")
            print(f"\n=== Indexed Project Documents ({len(docs)} files via doc_ops) ===")
            for d in docs[:15]:
                print(f"  - [{d['abbr']}] {d['title']} ({d['rel_path']})")
            if len(docs) > 15:
                print(f"    ... and {len(docs) - 15} more documents.")
        return 0
        
    results = search_wiki(args.query)
    
    if args.json:
        # Convert Path objects to string for JSON serialization
        serialized = json.loads(json.dumps(results, default=str))
        print(json.dumps(serialized, indent=2, ensure_ascii=False))
    else:
        if results["abbreviations"] or results["documents"]:
            print(inject_context_block(args.query, results))
        else:
            print(f"[LLM Wiki] No domain abbreviation, CPS, or document matches found for query: '{args.query}'")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())
