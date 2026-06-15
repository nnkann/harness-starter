#!/usr/bin/env python3
"""Read-only Supabase inventory for Harness CPS memory repurpose.

Loads existing ai-prompter Supabase runtime keys by default, but never prints
secret values. This script only performs metadata reads.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ENV = Path(__file__).resolve().parents[2] / ".env"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def safe_jwt_claims(token: str) -> dict[str, Any]:
    if token.count(".") != 2:
        return {"jwt_like": False}
    try:
        payload = token.split(".")[1] + "==="
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except Exception as exc:  # noqa: BLE001
        return {"decode_error": type(exc).__name__}
    return {k: claims.get(k) for k in ["role", "iss", "ref", "aud", "exp", "iat"] if k in claims}


def request_json(url: str, key: str, path: str) -> tuple[int | None, Any]:
    req = urllib.request.Request(
        url.rstrip("/") + path,
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(body) if body else None
            except json.JSONDecodeError:
                return resp.status, {"non_json_bytes": len(body)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, {"http_error_bytes": len(body)}
    except Exception as exc:  # noqa: BLE001
        return None, {"error": type(exc).__name__, "message": str(exc)}


def main() -> int:
    env_path = Path(os.environ.get("HARNESS_MEMORY_ENV_FILE", DEFAULT_ENV))
    vals = load_env(env_path)
    url = vals.get("HARNESS_MEMORY_SUPABASE_URL") or vals.get("PHE_SUPABASE_URL")
    ref = vals.get("HARNESS_MEMORY_SUPABASE_PROJECT_REF") or vals.get("PHE_SUPABASE_PROJECT_REF")
    region = vals.get("HARNESS_MEMORY_SUPABASE_REGION") or vals.get("PHE_SUPABASE_REGION")
    service_key = vals.get("HARNESS_MEMORY_SUPABASE_SERVICE_ROLE_KEY") or vals.get("PHE_SUPABASE_SERVICE_ROLE_KEY")
    anon_key = vals.get("HARNESS_MEMORY_SUPABASE_ANON_KEY") or vals.get("PHE_SUPABASE_ANON_KEY")

    report: dict[str, Any] = {
        "env_file": str(env_path),
        "env_present": env_path.exists(),
        "project_ref_present": bool(ref),
        "region_present": bool(region),
        "url_present": bool(url),
        "url_matches_ref": bool(url and ref and url.rstrip("/") == f"https://{ref}.supabase.co"),
        "service_key_present": bool(service_key),
        "anon_key_present": bool(anon_key),
        "service_key_claims": safe_jwt_claims(service_key or ""),
        "anon_key_claims": safe_jwt_claims(anon_key or ""),
        "checks": {},
    }

    if not url or not service_key:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    status, data = request_json(url, service_key, "/rest/v1/")
    exposed: list[str] = []
    if status == 200 and isinstance(data, dict):
        defs = data.get("definitions") or data.get("components", {}).get("schemas") or {}
        if isinstance(defs, dict):
            exposed = sorted(defs.keys())
    report["checks"]["rest_openapi"] = {"status": status, "exposed_tables": exposed, "exposed_table_count": len(exposed)}

    status, data = request_json(url, service_key, "/storage/v1/bucket")
    bucket_count: int | str | None = None
    bucket_names: list[str] = []
    if status == 200 and isinstance(data, list):
        bucket_count = len(data)
        bucket_names = [str(x.get("name")) for x in data if isinstance(x, dict) and x.get("name")]
    report["checks"]["storage_buckets"] = {"status": status, "bucket_count": bucket_count, "bucket_names": bucket_names}

    status, data = request_json(url, service_key, "/auth/v1/admin/users?page=1&per_page=1")
    users_returned: int | None = None
    if status == 200 and isinstance(data, dict) and isinstance(data.get("users"), list):
        users_returned = len(data["users"])
    report["checks"]["auth_admin_users_sample"] = {"status": status, "users_returned": users_returned}

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
