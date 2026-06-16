#!/usr/bin/env python3
"""Dry-run candidate builder for Harness CPS semantic memory.

Default mode is read-only dry-run. It scans repo docs with YAML-ish frontmatter
and emits candidate memory JSONL with source refs. It does not write to Supabase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TITLE_RE = re.compile(r"^#\s+(.+)$", re.M)


@dataclass
class SourceRef:
    repo: str
    path: str
    line_start: int
    line_end: int
    commit_sha: str | None
    source_type: str = "doc"


@dataclass
class Candidate:
    namespace: str
    project: str | None
    domain: str | None
    kind: str
    title: str
    summary: str | None
    content_for_embedding: str
    metadata: dict[str, Any]
    status: str
    fingerprint: str
    source_refs: list[SourceRef]


def git_sha(repo: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def parse_frontmatter(text: str) -> dict[str, Any]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    meta: dict[str, Any] = {}
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.startswith(" ") or raw.startswith("-") or ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        v = v.strip().strip('"').strip("'")
        meta[k.strip()] = v
    return meta


def first_heading(text: str, fallback: str) -> str:
    m = TITLE_RE.search(text)
    return m.group(1).strip() if m else fallback


def infer_kind(path: Path, meta: dict[str, Any]) -> str:
    p = str(path).lower()
    tags = str(meta.get("tags", "")).lower()
    if "decision" in p or "decisions" in p:
        return "case"
    if "template" in p or "workflow" in tags:
        return "workflow_template"
    if "feedback" in p or "downstream" in tags:
        return "downstream_feedback"
    if "negative" in tags or "failure" in tags:
        return "negative_evidence"
    if "actor" in tags or "routing" in tags:
        return "actor_routing_pattern"
    if "ac" in tags or "acceptance" in tags:
        return "ac_pattern"
    return "case"


def summarize(text: str) -> str:
    body = FRONTMATTER_RE.sub("", text).strip()
    lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    joined = " ".join(lines)
    return joined[:500]


def build_content(title: str, meta: dict[str, Any], summary: str, rel_path: str) -> str:
    context = meta.get("c") or meta.get("description") or title
    problem = meta.get("problem") or "not-explicit"
    solution = meta.get("s") or "not-explicit"
    return "\n".join(
        [
            f"Context: {context}",
            f"Problem: {problem}",
            f"Solution: {solution}",
            "AC: Reuse only after checking source_refs and owner-approved Harness CPS boundaries.",
            f"Evidence: {rel_path}",
            f"Reusable when: A future Harness/downstream task matches this CPS shape or operational boundary. Summary: {summary}",
        ]
    )


def candidate_for(repo: Path, path: Path, commit: str | None) -> Candidate | None:
    text = path.read_text(errors="replace")
    meta = parse_frontmatter(text)
    if not meta and ".harness/project/docs" not in str(path):
        return None
    rel = path.relative_to(repo).as_posix()
    title = str(meta.get("title") or first_heading(text, path.stem))
    domain = str(meta.get("domain") or "harness")
    summary = str(meta.get("description") or summarize(text))
    content = build_content(title, meta, summary, rel)
    fp = hashlib.sha256((rel + "\n" + title + "\n" + content).encode()).hexdigest()
    line_count = text.count("\n") + 1
    return Candidate(
        namespace="harness",
        project="harness-starter",
        domain=domain,
        kind=infer_kind(path, meta),
        title=title,
        summary=summary,
        content_for_embedding=content,
        metadata={
            "frontmatter": meta,
            "dry_run": True,
            "source_path": rel,
            "review_required": True,
        },
        status="candidate",
        fingerprint=fp,
        source_refs=[SourceRef(repo=str(repo), path=rel, line_start=1, line_end=line_count, commit_sha=commit)],
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/Users/kann/projects/harness-starter")
    ap.add_argument("--out", default=".harness/project/reports/harness_memory_candidates.jsonl")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--mode", choices=["dry-run"], default="dry-run")
    ap.add_argument("--include-archived", action="store_true", help="Include archived docs. Default excludes them.")
    ap.add_argument("--include-clusters", action="store_true", help="Include generated cluster index docs. Default excludes them.")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    out = (repo / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    commit = git_sha(repo)
    candidates: list[Candidate] = []
    skipped = {"archived": 0, "clusters": 0}
    for base in [repo / ".harness/project/docs"]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            rel_for_filter = path.relative_to(repo).as_posix()
            if not args.include_archived and "/archived/" in f"/{rel_for_filter}":
                skipped["archived"] += 1
                continue
            if not args.include_clusters and "/clusters/" in f"/{rel_for_filter}":
                skipped["clusters"] += 1
                continue
            cand = candidate_for(repo, path, commit)
            if cand:
                candidates.append(cand)
            if len(candidates) >= args.limit:
                break
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for cand in candidates:
            f.write(json.dumps(asdict(cand), ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "mode": args.mode,
        "repo": str(repo),
        "out": str(out),
        "candidate_count": len(candidates),
        "skipped": skipped,
        "write_to_supabase": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
