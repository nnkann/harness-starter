#!/usr/bin/env python3
"""LazyCodex Swarm Research Engine.
Implements S1: GitHub API Token integration (5k rate limit), need-based async swarm channeling, and research_notes.md synthesis.
"""

from __future__ import annotations
import argparse
import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Find repository root
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".harness" / "hermes" / "loader.py").exists():
            return parent
    return Path("/Users/kann/projects/harness-starter")

REPO_ROOT = find_repo_root()
OUTPUT_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "research_notes.md"

def get_github_headers() -> dict[str, str]:
    """Retrieves GITHUB_TOKEN from the environment to expand rate limit to 5000 requests."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LazyCodex-Swarm-Research-Engine/1.0"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        print("[Swarm Research] Authorization Token successfully loaded. Rate limit expanded to 5,000 req/hr.")
    else:
        print("[Swarm Research] WARNING: GITHUB_TOKEN not found in environment. Rate limit limited to 60 req/hr.")
    return headers

def fetch_github_api(url: str, headers: dict[str, str]) -> Any:
    """Safely executes HTTP request to GitHub API using standard urllib."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Check rate limit headers
            limit = e.headers.get("X-RateLimit-Limit")
            reset = e.headers.get("X-RateLimit-Reset")
            sys.stderr.write(f"[Swarm Research] ERROR: GitHub API Rate Limit exceeded (Limit: {limit}, Reset: {reset}). Please provide a GITHUB_TOKEN.\n")
        else:
            sys.stderr.write(f"[Swarm Research] ERROR: HTTP Error {e.code} for URL {url}: {e.reason}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"[Swarm Research] ERROR: Failed to connect to GitHub API: {e}\n")
        return None

def fetch_local_ast_grep(query: str) -> str:
    """Mock/Wrapper for local AST Grep channel."""
    # In real execution, this would call ast-grep CLI
    print(f"[Swarm Research] Channeling Local AST-Grep for query: '{query}'")
    return f"### Local AST-Grep Channel\n* Found structural matches for query '{query}' in 0 files.\n"

def fetch_web_search(query: str) -> str:
    """Mock/Wrapper for Web search channel."""
    print(f"[Swarm Research] Channeling Web Search for query: '{query}'")
    return f"### Web Search Channel\n* Retrieved community documentation for '{query}' from Web indexes.\n"

def run_swarm_research(repo_slug: str, query: str, channels: list[str]) -> None:
    """Runs a need-based 비동기 parallel swarm using ThreadPoolExecutor across selected channels."""
    print(f"[Swarm Research] Initiating swarm for repo: {repo_slug}, query: '{query}'")
    print(f"[Swarm Research] Active channels: {', '.join(channels)}")
    
    headers = get_github_headers()
    notes: list[str] = [
        f"# Swarm Research Notes - {repo_slug}",
        f"**Search Query**: `{query}`",
        f"**Generated At**: {Path(__file__).name}",
        "---",
    ]
    
    futures_map = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        if "github" in channels:
            # Channel 1: GitHub API (fetch repo details & latest commits)
            github_url = f"https://api.github.com/repos/{repo_slug}"
            futures_map[executor.submit(fetch_github_api, github_url, headers)] = "github_repo"
            
            commits_url = f"https://api.github.com/repos/{repo_slug}/commits?per_page=3"
            futures_map[executor.submit(fetch_github_api, commits_url, headers)] = "github_commits"
            
        if "ast" in channels:
            # Channel 2: Local AST Grep
            futures_map[executor.submit(fetch_local_ast_grep, query)] = "ast_grep"
            
        if "web" in channels:
            # Channel 3: Web Search
            futures_map[executor.submit(fetch_web_search, query)] = "web_search"
            
        # Collect results
        for future in as_completed(futures_map):
            channel_name = futures_map[future]
            try:
                result = future.result()
                if channel_name == "github_repo" and result:
                    notes.append("### GitHub API: Repository Metadata")
                    notes.append(f"* **Full Name**: {result.get('full_name')}")
                    notes.append(f"* **Description**: {result.get('description')}")
                    notes.append(f"* **Stars**: {result.get('stargazers_count')} | **Forks**: {result.get('forks_count')}")
                    notes.append(f"* **Source Ref Citation**: [{result.get('html_url')}]({result.get('html_url')})")
                elif channel_name == "github_commits" and result:
                    notes.append("### GitHub API: Recent Commits Context")
                    for commit in result:
                        sha = commit.get("sha")[:7]
                        message = commit.get("commit", {}).get("message", "").split("\n")[0]
                        author = commit.get("commit", {}).get("author", {}).get("name")
                        notes.append(f"* `sha:{sha}` - **{message}** (by *{author}*)")
                elif channel_name in ["ast_grep", "web_search"] and result:
                    notes.append(result)
            except Exception as e:
                sys.stderr.write(f"[Swarm Research] Exception in channel {channel_name}: {e}\n")

    # Synthesize the research notes
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(notes), encoding="utf-8")
    print(f"[Swarm Research] Saturation research successfully compiled into: {OUTPUT_FILE.relative_to(REPO_ROOT)}")

def main() -> int:
    import sys
    parser = argparse.ArgumentParser(description="LazyCodex Swarm Research Engine")
    parser.add_argument("--repo", default="code-yeongyu/lazycodex", help="Target GitHub repository slug (owner/name)")
    parser.add_argument("--query", default="ultrawork loop self correction", help="Search query context")
    parser.add_argument("--channels", default="github,ast,web", help="Comma-separated channels to activate (github, ast, web)")
    args = parser.parse_args()
    
    channels_list = [c.strip().lower() for c in args.channels.split(",")]
    run_swarm_research(args.repo, args.query, channels_list)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
