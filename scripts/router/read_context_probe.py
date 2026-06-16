#!/usr/bin/env python3
"""Read-only router context probe for Harness + Honcho.

This is the first integration seam between Harness project memory and Honcho
conversation/profile/session memory. It intentionally does not write to
Supabase, Harness memory tables, or Honcho conclusions. The only Honcho-side
state touch is the Hermes Honcho client's idempotent session resolution path
when a session key must be materialized to read context.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DEFAULT_REPO = Path(__file__).resolve().parents[2]
DEFAULT_CANDIDATES = DEFAULT_REPO / ".harness/project/reports/harness_memory_candidates.jsonl"
DEFAULT_HERMES_AGENT_ROOT = Path.home() / ".hermes/hermes-agent"


@dataclass
class RouterProbeResult:
    query: str
    repo: str
    harness: dict[str, Any]
    honcho: dict[str, Any]
    router_preamble: str
    merge_rule: str


def _read_text(path: Path, max_chars: int = 5000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    return text[:max_chars]


def _jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            rows.append({"_parse_error": True, "raw_preview": raw[:300]})
        if len(rows) >= limit:
            break
    return rows


def _extract_candidate_summary(row: dict[str, Any]) -> dict[str, Any]:
    content = str(row.get("content_for_embedding") or row.get("content") or "")
    source_refs = row.get("source_refs") or row.get("sourceRefs") or []
    if not source_refs and row.get("source_ref"):
        source_refs = [row.get("source_ref")]
    return {
        "title": row.get("title") or row.get("metadata", {}).get("title"),
        "kind": row.get("kind"),
        "domain": row.get("domain"),
        "status": row.get("status"),
        "source_refs": source_refs,
        "content_preview": content[:700],
    }


def read_harness(repo: Path, candidates_path: Path, limit: int) -> dict[str, Any]:
    agents = repo / "AGENTS.md"
    readme = repo / "README.md"
    migration = repo / "supabase/migrations/202606150001_harness_cps_semantic_memory.sql"
    cron_contract = repo / ".harness/project/cron/harness_cps_memory_cron.yaml"
    rows = _jsonl(candidates_path, limit)
    return {
        "source": "harness-local-repo",
        "repo": str(repo),
        "repo_exists": repo.exists(),
        "canonical_branch_hint": "hermes/harness-starter-baseline",
        "agents_md_present": agents.exists(),
        "agents_md_preview": _read_text(agents, 2200),
        "readme_present": readme.exists(),
        "readme_preview": _read_text(readme, 1200),
        "cps_migration_present": migration.exists(),
        "cps_migration_tables": [
            "public.cps_memory_items",
            "public.memory_source_refs",
            "public.cps_inventory_snapshots",
            "public.memory_ingest_runs",
        ] if migration.exists() else [],
        "cron_contract_present": cron_contract.exists(),
        "cron_contract_preview": _read_text(cron_contract, 1800),
        "candidates_path": str(candidates_path),
        "candidate_count_read": len(rows),
        "candidate_summaries": [_extract_candidate_summary(r) for r in rows],
    }


def _run(cmd: list[str], cwd: Path, timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout, check=False)
        return {"returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-1000:]}
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__, "message": str(exc)}


def _load_hermes_env_for_honcho() -> dict[str, bool]:
    """Load only enough runtime env for the Hermes Honcho client.

    Hermes CLI loads ~/.hermes/.env before resolving Honcho config. A standalone
    project script does not, so mirror that behavior without printing values.
    """
    loaded = {"dotenv_available": False, "hermes_env_present": False, "loaded": False}
    env_path = Path.home() / ".hermes/.env"
    loaded["hermes_env_present"] = env_path.exists()
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return loaded
    loaded["dotenv_available"] = True
    if env_path.exists():
        # The user's .env currently contains unrelated malformed shell lines;
        # suppress parser warnings because this probe only reports presence
        # booleans and must keep stdout machine-readable.
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            load_dotenv(env_path, override=False)
        loaded["loaded"] = True
    return loaded


def read_honcho(repo: Path, query: str, max_tokens: int, hermes_agent_root: Path, session_key_override: str | None) -> dict[str, Any]:
    env_load = _load_hermes_env_for_honcho()
    result: dict[str, Any] = {
        "source": "honcho-hermes-plugin",
        "env_load": env_load,
        "enabled": None,
        "session_key": session_key_override,
        "status_probe": _run(["hermes", "honcho", "status"], cwd=repo, timeout=45),
        "context": {},
        "search_excerpt": "",
        "errors": [],
    }

    if hermes_agent_root.exists():
        sys.path.insert(0, str(hermes_agent_root))

    try:
        from plugins.memory.honcho.client import HonchoClientConfig, get_honcho_client  # type: ignore
        from plugins.memory.honcho.session import HonchoSessionManager  # type: ignore
    except Exception as exc:  # noqa: BLE001
        result["errors"].append({"stage": "import", "type": type(exc).__name__, "message": str(exc)})
        return result

    old_cwd = Path.cwd()
    try:
        os.chdir(repo)
        cfg = HonchoClientConfig.from_global_config()
        result.update({
            "enabled": bool(getattr(cfg, "enabled", False)),
            "workspace": getattr(cfg, "workspace_id", None),
            "host": getattr(cfg, "host", None),
            "base_url_present": bool(getattr(cfg, "base_url", None)),
            "api_key_present": bool(getattr(cfg, "api_key", None)),
            "recall_mode": getattr(cfg, "recall_mode", None),
            "write_frequency": getattr(cfg, "write_frequency", None),
            "session_strategy": getattr(cfg, "session_strategy", None),
        })
        session_key = session_key_override or cfg.resolve_session_name()
        result["session_key"] = session_key
        if not getattr(cfg, "enabled", False):
            result["errors"].append({"stage": "config", "message": "Honcho disabled"})
            return result
        client = get_honcho_client(cfg)
        mgr = HonchoSessionManager(honcho=client, config=cfg)
        # Idempotent session resolution only; no conclusions/write-back.
        mgr.get_or_create(session_key)
        result["context"] = mgr.get_session_context(session_key, peer="user")
        result["search_excerpt"] = mgr.search_context(session_key, query=query, max_tokens=max_tokens, peer="user")
        return result
    except Exception as exc:  # noqa: BLE001
        result["errors"].append({"stage": "read", "type": type(exc).__name__, "message": str(exc)})
        return result
    finally:
        os.chdir(old_cwd)


def _compact_context(ctx: dict[str, Any]) -> str:
    if not ctx:
        return "(empty)"
    parts: list[str] = []
    for key in ["summary", "representation", "card"]:
        val = ctx.get(key)
        if val:
            parts.append(f"{key}: {str(val)[:1200]}")
    recent = ctx.get("recent_messages") or []
    if recent:
        lines = []
        for msg in recent[:5]:
            lines.append(f"- {msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:300]}")
        parts.append("recent_messages:\n" + "\n".join(lines))
    return "\n\n".join(parts) if parts else "(empty)"


def build_preamble(query: str, harness: dict[str, Any], honcho: dict[str, Any]) -> str:
    candidate_lines = []
    for c in harness.get("candidate_summaries", [])[:5]:
        title = c.get("title") or "untitled"
        refs = c.get("source_refs") or []
        candidate_lines.append(f"- {title}: {c.get('content_preview', '')[:350]} source_refs={refs}")
    candidates = "\n".join(candidate_lines) if candidate_lines else "(no candidates read)"
    honcho_text = _compact_context(honcho.get("context") or {})
    search_excerpt = (honcho.get("search_excerpt") or "")[:1500] or "(empty)"
    return f"""[ROUTER_QUERY]
{query}

[HARNESS_POLICY]
{(harness.get('agents_md_preview') or '')[:1800]}

[HARNESS_CPS_CONTEXT]
repo={harness.get('repo')}
cps_migration_present={harness.get('cps_migration_present')}
cps_tables={harness.get('cps_migration_tables')}
cron_contract_present={harness.get('cron_contract_present')}

[HARNESS_MEMORY_CANDIDATES]
{candidates}

[HONCHO_USER_CONTEXT]
{honcho_text}

[HONCHO_SEARCH_EXCERPT]
{search_excerpt}

[MERGE_RULE]
Harness policy/CPS/source_ref evidence is authoritative for project execution. Honcho user/session context may tune reporting, routing hints, and conversational continuity, but must not override Harness policy, accepted CPS records, owner approval holds, or source_ref evidence.
""".strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Read Harness + Honcho context and emit a labeled router preamble.")
    ap.add_argument("--repo", default=str(DEFAULT_REPO))
    ap.add_argument("--query", default="Harness Honcho read-only router context probe")
    ap.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    ap.add_argument("--candidate-limit", type=int, default=8)
    ap.add_argument("--honcho-max-tokens", type=int, default=800)
    ap.add_argument("--honcho-session-key", default=None)
    ap.add_argument("--hermes-agent-root", default=str(DEFAULT_HERMES_AGENT_ROOT))
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    candidates = Path(args.candidates)
    if not candidates.is_absolute():
        candidates = repo / candidates

    harness = read_harness(repo, candidates, args.candidate_limit)
    honcho = read_honcho(repo, args.query, args.honcho_max_tokens, Path(args.hermes_agent_root), args.honcho_session_key)
    preamble = build_preamble(args.query, harness, honcho)
    result = RouterProbeResult(
        query=args.query,
        repo=str(repo),
        harness=harness,
        honcho=honcho,
        router_preamble=preamble,
        merge_rule="Honcho context cannot override Harness policy/CPS/source_ref/owner-approval holds.",
    )

    if args.format == "markdown":
        print(preamble)
    else:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not honcho.get("errors") else 2


if __name__ == "__main__":
    raise SystemExit(main())
