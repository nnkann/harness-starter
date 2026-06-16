#!/usr/bin/env python3
"""Seed Honcho with initial harness-starter project context.

This is deliberately separate from read_context_probe.py. The router probe stays
read-only by default; this script performs the explicit initial Honcho write that
anchors a project session with repo-derived context.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_REPO = Path(__file__).resolve().parents[2]
DEFAULT_HERMES_AGENT_ROOT = Path.home() / ".hermes/hermes-agent"
DEFAULT_CANDIDATES = DEFAULT_REPO / ".harness/project/reports/harness_memory_candidates.jsonl"


def _load_hermes_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    env_path = Path.home() / ".hermes/.env"
    if env_path.exists():
        with contextlib.redirect_stderr(io.StringIO()):
            load_dotenv(env_path, override=False)


def _read(path: Path, max_chars: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except FileNotFoundError:
        return ""


def _read_candidates(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        refs = row.get("source_refs") or []
        rows.append({
            "title": row.get("title"),
            "domain": row.get("domain"),
            "kind": row.get("kind"),
            "status": row.get("status"),
            "source_refs": refs[:2],
            "summary": str(row.get("summary") or row.get("content_for_embedding") or "")[:500],
        })
        if len(rows) >= limit:
            break
    return rows


def build_seed(repo: Path, candidates_path: Path, candidate_limit: int) -> str:
    agents = _read(repo / "AGENTS.md", 2600)
    readme = _read(repo / "README.md", 2600)
    cron = _read(repo / ".harness/project/cron/harness_cps_memory_cron.yaml", 1800)
    candidates = _read_candidates(candidates_path, candidate_limit)
    payload = {
        "project": "harness-starter",
        "repo": str(repo),
        "purpose": "AI coding agent Harness template. Separates common Harness contracts from runtime adapters for Claude, Codex, Hermes, Agy, and related agent stacks.",
        "active_branch": "hermes/harness-starter-baseline",
        "authoritative_policy": {
            "branch": "hermes/harness-starter-baseline is the SSOT branch for Harness/Hermes adapter contracts, reference packs, and baseline docs.",
            "main": "main is an upstream/default anchor only; do not mutate main unless owner explicitly approves.",
            "completion": "Final completion requires graph closure evidence and trace keys, not a role checklist.",
            "owner_holds": "remote migration apply, Supabase writes, cron creation, and dashboard rename remain owner-approval holds unless explicitly approved.",
        },
        "harness_memory_boundary": {
            "honcho": "conversation/profile/session memory and continuity",
            "harness": "CPS/project/routing/policy/source_ref memory",
            "merge_rule": "Honcho context may tune reporting/routing hints but cannot override Harness policy, accepted CPS records, owner approval holds, or source_ref evidence.",
        },
        "readme_excerpt": readme,
        "agents_policy_excerpt": agents,
        "memory_cron_contract_excerpt": cron,
        "candidate_source_ref_samples": candidates,
    }
    return "<harness_project_context_seed>\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n</harness_project_context_seed>"


def seed_honcho(repo: Path, session_key: str | None, seed_text: str, hermes_agent_root: Path) -> dict[str, Any]:
    _load_hermes_env()
    if hermes_agent_root.exists():
        sys.path.insert(0, str(hermes_agent_root))
    from plugins.memory.honcho.client import HonchoClientConfig, get_honcho_client  # type: ignore
    from plugins.memory.honcho.session import HonchoSessionManager  # type: ignore

    old_cwd = Path.cwd()
    try:
        os.chdir(repo)
        cfg = HonchoClientConfig.from_global_config()
        resolved_session_key = session_key or cfg.resolve_session_name()
        if not cfg.enabled:
            return {"ok": False, "error": "Honcho disabled", "session_key": resolved_session_key}
        client = get_honcho_client(cfg)
        mgr = HonchoSessionManager(honcho=client, config=cfg)
        session = mgr.get_or_create(resolved_session_key)
        session.add_message("assistant", seed_text)
        mgr.save(session)
        mgr.flush_all()
        ctx = mgr.get_session_context(resolved_session_key, peer="ai")
        return {
            "ok": True,
            "workspace": cfg.workspace_id,
            "host": cfg.host,
            "session_key": resolved_session_key,
            "seed_chars": len(seed_text),
            "context_keys_after_seed": sorted(ctx.keys()),
            "recent_message_count_after_seed": len(ctx.get("recent_messages") or []),
        }
    finally:
        os.chdir(old_cwd)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed Honcho with actual harness-starter project context.")
    ap.add_argument("--repo", default=str(DEFAULT_REPO))
    ap.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    ap.add_argument("--candidate-limit", type=int, default=5)
    ap.add_argument("--honcho-session-key", default=None)
    ap.add_argument("--hermes-agent-root", default=str(DEFAULT_HERMES_AGENT_ROOT))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    candidates = Path(args.candidates)
    if not candidates.is_absolute():
        candidates = repo / candidates
    seed = build_seed(repo, candidates, args.candidate_limit)
    if args.dry_run:
        print(seed)
        return 0
    result = seed_honcho(repo, args.honcho_session_key, seed, Path(args.hermes_agent_root))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
