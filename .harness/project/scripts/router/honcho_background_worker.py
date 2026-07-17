#!/usr/bin/env python3
"""Honcho & GBrain background worker and learning writeback loop.
Provides ingest, check-drift, and writeback actions for Harness.
"""
from __future__ import annotations
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import yaml

DEFAULT_REPO = Path(__file__).resolve().parents[4]
DEFAULT_HERMES_AGENT_ROOT = Path.home() / ".hermes/hermes-agent"

def get_file_commit_sha(repo: Path, path: Path) -> str:
    try:
        sha = subprocess.check_output(["git", "log", "-1", "--format=%H", "--", str(path)], cwd=repo, stderr=subprocess.DEVNULL).decode().strip()
        return f"{sha}-dirty" if subprocess.run(["git", "diff", "--quiet", "--", str(path)], cwd=repo).returncode != 0 else (sha or "unknown")
    except Exception: return "working-tree"

def parse_markdown_doc(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="replace")
    fm, body = {}, content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2]
    secs = [v for k, v in [("c", "C"), ("problem", "P"), ("s", "S"), ("owner_approval_boundary", "owner_approval_boundary"), ("prohibited_actions", "prohibited_actions")] if k in fm or v.lower() in body.lower() or v.replace("_", " ").lower() in body.lower()]
    desc, probs, sols = fm.get("description", ""), fm.get("problem", []), fm.get("s", [])
    prob_str = "\n- ".join(probs) if isinstance(probs, list) else str(probs)
    sol_str = "\n- ".join(sols) if isinstance(sols, list) else str(sols)
    digest = f"Description: {desc}\n\nProblems:\n- {prob_str}\n\nSolutions:\n- {sol_str}" if desc or prob_str or sol_str else body[:1000]
    return {"frontmatter": fm, "sections_present": sorted(list(set(secs))), "digest": digest}

def _init_honcho(repo: Path, agent_root: Path, session_key: str | None):
    try:
        from dotenv import load_dotenv
        load_dotenv(Path.home() / ".hermes/.env")
    except Exception: pass
    if agent_root.exists() and str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))
    from plugins.memory.honcho.client import HonchoClientConfig, get_honcho_client
    from plugins.memory.honcho.session import HonchoSessionManager
    cfg = HonchoClientConfig.from_global_config()
    res_key = session_key or cfg.resolve_session_name()
    return HonchoSessionManager(honcho=get_honcho_client(cfg), config=cfg) if cfg.enabled else None, res_key, cfg


class HonchoUnavailable(RuntimeError):
    pass


class HonchoAnchorAdapter:
    def __init__(self, manager, session_key: str):
        if manager is None or not session_key:
            raise HonchoUnavailable("honcho-unavailable-or-disabled")
        self.manager = manager
        self.session_key = session_key
        session = manager.get_or_create(session_key)
        self.identity = "%s:%s:%s" % (id(manager), id(manager._honcho), session.honcho_session_id)
        self._session = session

    def _scope(self):
        target = self._session.user_peer_id
        observer = self.manager._get_or_create_peer(self._session.assistant_peer_id)
        return observer.conclusions_of(target)

    @staticmethod
    def _id(value):
        if isinstance(value, (list, tuple)) and value:
            value = value[0]
        if isinstance(value, dict):
            return value.get("id") or value.get("conclusion_id")
        return getattr(value, "id", None) or getattr(value, "conclusion_id", None)

    @staticmethod
    def _content(value):
        if isinstance(value, dict):
            return value.get("content")
        return getattr(value, "content", None)

    def write_anchor(self, anchor):
        payload = json.dumps({"cps_compact_anchor": dict(anchor)}, sort_keys=True, separators=(",", ":"))
        result = self._scope().create([{"content": payload, "session_id": self._session.honcho_session_id}])
        conclusion_id = self._id(result)
        if not conclusion_id:
            raise HonchoUnavailable("honcho-write-returned-no-real-id")
        return "honcho:%s" % conclusion_id

    def read_anchor(self, anchor_ref):
        conclusion_id = anchor_ref.removeprefix("honcho:")
        scope = self._scope()
        getter = getattr(scope, "get", None)
        if getter is None:
            raise HonchoUnavailable("honcho-independent-readback-api-unavailable")
        value = getter(conclusion_id)
        content = self._content(value)
        if not content:
            raise HonchoUnavailable("honcho-independent-readback-empty")
        parsed = json.loads(content)
        return parsed["cps_compact_anchor"]

    def deactivate_anchor(self, anchor_ref, superseded_by):
        marker = {
            "anchor_key": "supersession:%s" % anchor_ref,
            "superseded_ref": anchor_ref,
            "superseded_by": superseded_by,
        }
        return bool(self.write_anchor(marker))


def create_production_stage_adapters(repo: Path = DEFAULT_REPO, agent_root: Path = DEFAULT_HERMES_AGENT_ROOT):
    from cps_memory_lifecycle import ProductionStageAdapters
    from plugins.memory.honcho.client import reset_honcho_client

    writer_manager, _, writer_cfg = _init_honcho(repo, agent_root, "cps-anchor-writer")
    if writer_manager is None or not writer_cfg.enabled:
        raise HonchoUnavailable("honcho-unavailable-or-disabled")
    writer = HonchoAnchorAdapter(writer_manager, "cps-anchor-writer")
    reset_honcho_client()
    reader_manager, _, reader_cfg = _init_honcho(repo, agent_root, "cps-anchor-readback")
    if reader_manager is None or not reader_cfg.enabled:
        raise HonchoUnavailable("honcho-readback-unavailable-or-disabled")
    reader = HonchoAnchorAdapter(reader_manager, "cps-anchor-readback")
    return ProductionStageAdapters(
        repo,
        repo / ".harness/project/runs/cps_memory_lifecycle.sqlite3",
        writer,
        reader,
    )

def find_manifest(repo: Path, arg: str | None) -> Path:
    if arg: return Path(arg) if Path(arg).is_absolute() else repo / Path(arg)
    for p in [repo / "honcho_ingest_manifest.yaml", repo / ".harness/project/runs/honcho_ingest_manifest.yaml", repo / ".harness/project/runs/_template/honcho_ingest_manifest.yaml"]:
        if p.exists():
            if "_template" in p.parts:
                act = repo / ".harness/project/runs/honcho_ingest_manifest.yaml"
                if not act.exists():
                    act.parent.mkdir(parents=True, exist_ok=True)
                    act.write_bytes(p.read_bytes())
                return act
            return p
    raise FileNotFoundError("Manifest not found")

def handle_ingest(args: argparse.Namespace) -> int:
    repo, manifest_path = Path(args.repo).resolve(), find_manifest(Path(args.repo).resolve(), args.manifest)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    docs = data.get("honcho_ingest_manifest", {}).get("docs", [])
    mgr, s_key, cfg = _init_honcho(repo, Path(args.hermes_agent_root), args.honcho_session_key)
    session = mgr.get_or_create(s_key) if (mgr and cfg.enabled) else None
    
    # Load local fallback cache
    cache_file = repo / ".harness/project/runs/honcho_digests_cache.json"
    cache_data = {}
    if cache_file.exists():
        try: cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception: pass
        
    updated = False
    for doc in docs:
        if doc.get("status") != "pending": continue
        f_path = repo / doc["source_path"]
        if not f_path.exists():
            doc["status"] = "failed"
            updated = True
            continue
        parsed = parse_markdown_doc(f_path)
        digest = {
            "project_id": data.get("honcho_ingest_manifest", {}).get("project_id", "harness-starter"),
            "source_path": doc["source_path"], "source_commit": get_file_commit_sha(repo, f_path),
            "doc_type": doc.get("doc_type", "document"), "frontmatter_summary": parsed["frontmatter"],
            "digest": parsed["digest"], "required_sections_present": parsed["sections_present"],
            "line_refs": parsed["frontmatter"].get("source_refs", []), "artifact_refs": parsed["frontmatter"].get("artifact_refs", []),
            "status": "ingested", "updated_at": datetime.now().isoformat()
        }
        if session:
            session.add_message("assistant", f"<honcho_doc_digest>\n{json.dumps({'honcho_doc_digest': digest}, ensure_ascii=False, indent=2)}\n</honcho_doc_digest>")
        cache_data[doc["source_path"]] = digest
        doc["status"] = "ingested"
        updated = True
        print(f"[Ingest] Ingested: {doc['source_path']}")
    if updated:
        if session:
            mgr.save(session)
            mgr.flush_all()
        # Save manifest
        manifest_path.write_text(yaml.safe_dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        # Save local cache fallback
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
    return 0

def handle_check_drift(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    docs = yaml.safe_load(find_manifest(repo, args.manifest).read_text(encoding="utf-8")).get("honcho_ingest_manifest", {}).get("docs", [])
    mgr, s_key, cfg = _init_honcho(repo, Path(args.hermes_agent_root), args.honcho_session_key)
    digests = {}
    if mgr and cfg.enabled:
        for msg in mgr.get_or_create(s_key).messages:
            c = msg.get("content", "")
            if c.startswith("<honcho_doc_digest>") and c.endswith("</honcho_doc_digest>"):
                try:
                    d = json.loads(c[19:-20].strip()).get("honcho_doc_digest", {})
                    if d.get("source_path"): digests[d["source_path"]] = d
                except Exception: pass
    if not digests:
        # Load from local cache fallback
        cache_file = repo / ".harness/project/runs/honcho_digests_cache.json"
        if cache_file.exists():
            try: digests = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception: pass
            
    print("\n--- Drift QA Report ---")
    tot, ok, drift, miss = 0, 0, 0, 0
    for doc in docs:
        p = doc["source_path"]
        if not (repo / p).exists(): continue
        tot += 1
        curr = get_file_commit_sha(repo, repo / p)
        if p not in digests:
            print(f"[MISSING] doc: {p}"); miss += 1
        elif curr != digests[p].get("source_commit"):
            print(f"[DRIFTED] doc: {p}. Honcho: {digests[p].get('source_commit')}, Local: {curr}"); drift += 1
        else:
            print(f"[OK] doc: {p}"); ok += 1
    print(f"\nSummary: Total {tot}, OK {ok}, Drifted {drift}, Missing {miss}")
    return 0

def handle_writeback(args: argparse.Namespace) -> int:
    from session_close_lifecycle import request_close, stage_snapshot, verify_snapshot_readback

    repo = Path(args.repo).resolve()
    s_id = args.session_id or "sim_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = {
        "session_id": s_id,
        "thread_id": args.thread_id or f"thread_{s_id}",
        "root_goal_id": args.root_goal_id or "root_goal_harness_init",
        "task_AC_result": args.task_ac_result,
        "changed_policy_or_procedure": args.changed_policy_or_procedure or "None",
        "source_refs": [r.strip() for r in args.source_refs.split(",")] if args.source_refs else [],
        "artifact_refs": [r.strip() for r in args.artifact_refs.split(",")] if args.artifact_refs else [],
        "unresolved_holds": [h.strip() for h in args.unresolved_holds.split(",")] if args.unresolved_holds else [],
        "timestamp": datetime.now().isoformat(),
    }
    target_fields = (args.target_repository, args.target_remote_ref, args.target_relative_path)
    if not all(isinstance(value, str) and value for value in target_fields):
        raise ValueError("writeback requires an explicit canonical target")
    canonical_target = {
        "repository": args.target_repository,
        "remote_ref": args.target_remote_ref,
        "relative_path": args.target_relative_path,
    }
    state = request_close(repo, s_id, snapshot, canonical_target)
    state = stage_snapshot(state)
    state = verify_snapshot_readback(state)
    print(
        f"[Writeback] Snapshot staged at {state['snapshot']['relative_path']}; "
        f"state={state['state']} snapshot_id={state['snapshot']['snapshot_id']}"
    )
    return 0

def main() -> int:
    ap = argparse.ArgumentParser(description="Harness Honcho Background Worker")
    ap.add_argument("--action", choices=["ingest", "check-drift", "writeback"], required=True)
    ap.add_argument("--manifest"); ap.add_argument("--honcho-session-key"); ap.add_argument("--session-id")
    ap.add_argument("--repo", default=str(DEFAULT_REPO)); ap.add_argument("--hermes-agent-root", default=str(DEFAULT_HERMES_AGENT_ROOT))
    ap.add_argument("--thread-id"); ap.add_argument("--root-goal-id"); ap.add_argument("--task-ac-result", default="passed")
    ap.add_argument("--changed-policy-or-procedure"); ap.add_argument("--source-refs"); ap.add_argument("--artifact-refs"); ap.add_argument("--unresolved-holds")
    ap.add_argument("--target-repository"); ap.add_argument("--target-remote-ref"); ap.add_argument("--target-relative-path")
    args = ap.parse_args()
    return {"ingest": handle_ingest, "check-drift": handle_check_drift, "writeback": handle_writeback}[args.action](args)

if __name__ == "__main__":
    sys.exit(main())
