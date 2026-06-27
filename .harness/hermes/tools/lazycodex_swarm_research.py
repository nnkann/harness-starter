#!/usr/bin/env python3
"""LazyCodex Swarm Research Engine.
Implements S1: GitHub API Token integration (5k rate limit), need-based async swarm channeling,
and research_notes.md synthesis, featuring fully operational Web Scraping & Local AST Search.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
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
OUTPUT_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "research_notes.md"

class DuckDuckGoParser(HTMLParser):
    """Minimal stdlib HTML parser to extract search results from DuckDuckGo HTML."""
    def __init__(self):
        super().__init__()
        self.results: list[dict[str, str]] = []
        self.in_result = False
        self.in_title = False
        self.in_snippet = False
        self.current_result: dict[str, str] = {}
        self.current_data = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        tag_class = attrs_dict.get("class", "")
        
        if tag == "div" and "result" in tag_class.split():
            self.in_result = True
            self.current_result = {"title": "", "link": "", "snippet": ""}
            
        elif self.in_result:
            if tag == "a" and "result__snippet" in tag_class.split():
                self.in_snippet = True
                self.current_result["link"] = attrs_dict.get("href", "")
            elif tag == "a" and "result__url" in tag_class.split():
                # fallback link
                if not self.current_result.get("link"):
                    self.current_result["link"] = attrs_dict.get("href", "")
            elif tag == "a" and "result__snippet" not in tag_class.split() and "result__url" not in tag_class.split() and not self.current_result.get("title"):
                # Usually the title link
                self.in_title = True
                self.current_result["link"] = attrs_dict.get("href", "")
            elif tag == "td" and "result-snippet" in tag_class.split():
                self.in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.in_result:
            # Save if valid
            if self.current_result.get("title") or self.current_result.get("link"):
                # Clean links (DuckDuckGo redirects like /l/?kh=-1&uddg=URL)
                link = self.current_result["link"]
                if "/l/?uddg=" in link:
                    parsed = urllib.parse.urlparse(link)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "uddg" in qs:
                        link = qs["uddg"][0]
                self.current_result["link"] = link
                self.results.append(self.current_result)
            self.in_result = False
            
        elif self.in_title and tag == "a":
            self.in_title = False
        elif self.in_snippet and (tag == "a" or tag == "td" or tag == "div"):
            self.in_snippet = False

    def handle_data(self, data: str) -> None:
        if self.in_result:
            clean_data = data.strip()
            if not clean_data:
                return
            if self.in_title:
                self.current_result["title"] += (" " if self.current_result["title"] else "") + clean_data
            elif self.in_snippet:
                self.current_result["snippet"] += (" " if self.current_result["snippet"] else "") + clean_data

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
            limit = e.headers.get("X-RateLimit-Limit")
            reset = e.headers.get("X-RateLimit-Reset")
            sys.stderr.write(f"[Swarm Research] ERROR: GitHub API Rate Limit exceeded (Limit: {limit}, Reset: {reset}).\n")
        else:
            sys.stderr.write(f"[Swarm Research] ERROR: HTTP Error {e.code} for URL {url}: {e.reason}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"[Swarm Research] ERROR: Failed to connect to GitHub API: {e}\n")
        return None

def fetch_local_ast_grep(query: str) -> str:
    """Performs a real AST-Grep-like structural/textual search over local workspace files."""
    print(f"[Swarm Research] Channeling Local AST-Grep for query: '{query}'")
    matches: list[str] = []
    scan_extensions = [".py", ".md", ".json", ".yaml", ".yml"]
    
    # Simple regex pattern for structural definitions matching query
    # e.g., class X, def X, function X, problem: X, s: X
    pattern = re.compile(rf"(def\s+\w*{re.escape(query)}\w*|class\s+\w*{re.escape(query)}\w*|{re.escape(query)}:)", re.IGNORECASE)
    
    try:
        # Search relevant subdirectories
        search_dirs = [REPO_ROOT / ".harness", REPO_ROOT / "docs"]
        count = 0
        for s_dir in search_dirs:
            if not s_dir.exists():
                continue
            for path in s_dir.rglob("*"):
                if path.is_file() and path.suffix.lower() in scan_extensions:
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        lines = content.splitlines()
                        for line_num, line in enumerate(lines, 1):
                            if pattern.search(line) or query.lower() in line.lower():
                                # Extract context
                                rel_path = path.relative_to(REPO_ROOT)
                                matches.append(f"  - `file://{path.as_posix()}#L{line_num}` - `{rel_path}:{line_num}`: `{line.strip()}`")
                                count += 1
                                if count >= 15:  # Cap at 15 matches to keep context clean & slim
                                    break
                        if count >= 15:
                            break
                    except Exception:
                        continue
            if count >= 15:
                break
    except Exception as e:
        return f"### Local AST-Grep Channel\n* Error executing local scan: {e}\n"
        
    if matches:
        return f"### Local AST-Grep Channel\n* Found structural/textual matches for query '{query}' in local files:\n" + "\n".join(matches) + "\n"
    return f"### Local AST-Grep Channel\n* No structural/textual matches found for query '{query}' in local workspace.\n"

def fetch_web_search(query: str) -> str:
    """Performs real DuckDuckGo HTML scraping to get external web research data without external deps."""
    print(f"[Swarm Research] Channeling Web Search for query: '{query}'")
    
    # DuckDuckGo HTML search URL
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode("utf-8", errors="ignore")
            
        parser = DuckDuckGoParser()
        parser.feed(html_content)
        
        if not parser.results:
            return f"### Web Search Channel\n* DuckDuckGo query executed but returned 0 structured results for '{query}'.\n"
            
        lines = [f"### Web Search Channel\n* Retrieved community documentation for '{query}':"]
        for i, res in enumerate(parser.results[:5]): # Limit to top 5 results
            title = res["title"].strip() or "No Title"
            link = res["link"].strip()
            snippet = res["snippet"].strip() or "No description available."
            lines.append(f"  {i+1}. **[{title}]({link})**")
            lines.append(f"     > {snippet}")
            
        return "\n".join(lines) + "\n"
        
    except Exception as e:
        sys.stderr.write(f"[Swarm Research] Web search failed: {e}\n")
        return f"### Web Search Channel\n* Web search failed to fetch external results due to: {e}\n"

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
    parser = argparse.ArgumentParser(description="LazyCodex Swarm Research Engine")
    parser.add_argument("--repo", default="code-yeongyu/lazycodex", help="Target GitHub repository slug (owner/name)")
    parser.add_argument("--query", default="ultrawork loop self correction", help="Search query context")
    parser.add_argument("--channels", default="github,ast,web", help="Comma-separated channels to activate (github, ast, web)")
    args = parser.parse_args()
    
    channels_list = [c.strip().lower() for c in args.channels.split(",")]
    run_swarm_research(args.repo, args.query, channels_list)
    return 0

if __name__ == "__main__":
    sys.exit(main())
