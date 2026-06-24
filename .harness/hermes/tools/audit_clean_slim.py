#!/usr/bin/env python3
"""LazyCodex Clean & Slim Code and Document Auditor.
Implements S4: Automated scans for defensive try-catch bloat, debug comment residue, and duplicate document emphasis.
"""

from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

# Find repository root
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".harness" / "hermes" / "loader.py").exists():
            return parent
    return Path("/Users/kann/projects/harness-starter")

REPO_ROOT = find_repo_root()

# Regex patterns for slop detection
EMPTY_CATCH_RE = re.compile(r"except\s+Exception\s*:\s*pass|catch\s*\(\s*Exception\s+\w+\s*\)\s*\{\s*\}")
DEFENSIVE_TRY_RE = re.compile(r"try\s*:\s*.*?\s*except\s*:\s*pass", re.DOTALL)
DEBUG_RESIDUE_RE = re.compile(r"#\s*(TODO|FIXME|XXX|DEBUG|TEMP|CHECKME)\b", re.IGNORECASE)
DUPLICATE_EMPHASIS_RE = re.compile(r"\*\*(.*?)\*\*")

def audit_source_code(file_path: Path) -> list[str]:
    """Scans code files for try-catch bloat and temporary debug comment residues."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read source file: {e}"]
        
    lines = content.splitlines()
    
    # 1. Empty/defensive try-catch search
    if EMPTY_CATCH_RE.search(content):
        # Locate specific line
        for i, line in enumerate(lines, 1):
            if "except" in line and "pass" in line:
                findings.append(f"Line {i}: Defensive try-except-pass block detected (empty slop exception catcher).")
                
    # 2. Debug comments residue search
    for i, line in enumerate(lines, 1):
        match = DEBUG_RESIDUE_RE.search(line)
        if match:
            findings.append(f"Line {i}: Debug/Temporary comment residue found ('{match.group(0)}').")
            
    return findings

def audit_markdown_document(file_path: Path) -> list[str]:
    """Scans markdown documents for duplicate emphasis and verbosity."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read markdown file: {e}"]
        
    # Find all bold/emphasized phrases
    emphases = DUPLICATE_EMPHASIS_RE.findall(content)
    
    # Analyze duplicate emphasis (same bold phrase repeated 3+ times)
    counts = {}
    for phrase in emphases:
        phrase_clean = phrase.strip().lower()
        if len(phrase_clean) > 3:  # Ignore very short markers like **1**
            counts[phrase_clean] = counts.get(phrase_clean, 0) + 1
            
    for phrase, count in counts.items():
        if count >= 3:
            findings.append(f"Document contains duplicate bold emphasis on '{phrase}' ({count} times). Reduce rhetorical repetition.")
            
    # Check for hyperbole/AI slops ("completely", "perfectly", "beautifully", "sophisticated", "seamlessly")
    slop_words = ["completely", "perfectly", "beautifully", "sophisticated", "seamlessly", "elegantly"]
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for word in slop_words:
            if word in line.lower():
                findings.append(f"Line {i}: Unnecessary flowery modifier '{word}' detected. Maintain factual, direct reporting.")
                
    return findings

def run_clean_slim_audit(target_dir: Path) -> int:
    """Scans target workspace files and prints Clean & Slim compliance reports."""
    print(f"[Clean & Slim Audit] Initiating scan across: {target_dir.relative_to(REPO_ROOT)}")
    
    source_extensions = {".py", ".ts", ".js", ".go", ".rs"}
    total_findings = 0
    scanned_files = 0
    
    # Walk directory avoiding metadata and builds
    for root, dirs, files in os.walk(target_dir):
        # Prune search tree
        dirs[:] = [d for d in dirs if d not in [".git", ".harness", ".venv", "__pycache__", "tests"]]
        
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            
            findings = []
            if ext in source_extensions:
                scanned_files += 1
                findings = audit_source_code(file_path)
            elif ext == ".md":
                scanned_files += 1
                findings = audit_markdown_document(file_path)
                
            if findings:
                total_findings += len(findings)
                print(f"\n[Compliance Alert] File: {file_path.relative_to(REPO_ROOT)}")
                for f in findings:
                    print(f"  - {f}")
                    
    print("\n--- Clean & Slim Audit Summary ---")
    print(f"Total Files Scanned: {scanned_files}")
    print(f"Total Compliance Findings: {total_findings}")
    
    if total_findings > 0:
        print(f"[Audit] [FAIL] Clean & Slim standards violated. Please clean up files before submitting.")
        return 1
        
    print("[Audit] [PASS] Clean & Slim standards met. Code and docs are crisp and clean.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="LazyCodex Clean & Slim Code and Document Auditor")
    parser.add_argument("--path", default=str(REPO_ROOT), help="Directory or file path to audit")
    args = parser.parse_args()
    
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        sys.stderr.write(f"Error: Path does not exist: {target_path}\n")
        return 2
        
    if target_path.is_file():
        # Audit single file
        ext = target_path.suffix.lower()
        findings = []
        if ext in {".py", ".ts", ".js", ".go", ".rs"}:
            findings = audit_source_code(target_path)
        elif ext == ".md":
            findings = audit_markdown_document(target_path)
            
        if findings:
            print(f"[Compliance Alert] File: {target_path.relative_to(REPO_ROOT)}")
            for f in findings:
                print(f"  - {f}")
            return 1
        print("[Audit] [PASS] File complies with Clean & Slim standards.")
        return 0
    else:
        return run_clean_slim_audit(target_path)

if __name__ == "__main__":
    sys.exit(main())
