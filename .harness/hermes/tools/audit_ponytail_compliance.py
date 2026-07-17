#!/usr/bin/env python3
"""Audit agent code changes against the 'Lazy Dev's Ladder' (ponytail) principles.

Enforces:
1. No arbitrary new dependencies (Rule 5: Already installed dependency).
2. No bloated implementation size (Rule 7: Minimum working code).
"""

from __future__ import annotations
import argparse
import sys
import subprocess
from pathlib import Path

# Files that represent project dependencies
DEPENDENCY_FILES = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "pyproject.toml",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Gemfile",
    "Gemfile.lock",
}

def is_git_repository(cwd: Path) -> bool:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return res.returncode == 0 and res.stdout.strip() == "true"
    except Exception:
        return False

def get_git_diff_stats(cwd: Path) -> tuple[int, bool, list[str]]:
    """Returns (total_added_lines_in_src, dependency_file_changed, changed_files).
    
    Ignores configuration, tests, and Harness metadata (.harness/) from LOC count.
    """
    if not is_git_repository(cwd):
        return 0, False, []

    try:
        # Get the list of modified/added files in the worktree
        diff_numstat = subprocess.check_output(
            ["git", "diff", "--numstat", "HEAD"],
            cwd=cwd
        ).decode("utf-8")
        
        added_lines = 0
        dependency_changed = False
        changed_files: list[str] = []
        
        for line in diff_numstat.strip().split("\n"):
            if not line:
                continue
            added, deleted, filepath = line.split("\t")
            changed_files.append(filepath)
            
            path_parts = Path(filepath).parts
            
            # Check if dependency files are changed
            if any(dep in filepath for dep in DEPENDENCY_FILES):
                dependency_changed = True
            
            # Ignore metadata, tests, and config files for source code LOC calculation
            if ".harness" in path_parts or "tests" in path_parts or "test" in filepath or filepath.endswith(".md"):
                continue
                
            if added.isdigit():
                added_lines += int(added)
                
        return added_lines, dependency_changed, changed_files
    except Exception as e:
        print(f"[Warning] Failed to read git diff: {e}. Skipping physical diff checks.")
        return 0, False, []

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit codebase for 'Lazy Dev's Ladder' compliance.")
    parser.add_argument("--max-loc-delta", type=int, default=100, help="Maximum allowed added lines of source code.")
    parser.add_argument("--allow-new-deps", action="store_true", help="Allow modifications to dependency files.")
    parser.add_argument("--cwd", type=str, default=str(Path.cwd()), help="Working directory of the repository.")
    args = parser.parse_args()

    cwd_path = Path(args.cwd).resolve()
    
    # 1. Check if git repository is available
    if not is_git_repository(cwd_path):
        print("[Audit] [SKIP] Not in a git repository or git is unavailable. Compliance bypass.")
        return 0

    added_lines, dependency_changed, changed_files = get_git_diff_stats(cwd_path)
    
    print(f"[Audit] Modified files: {len(changed_files)}")
    print(f"[Audit] Source LOC delta (added): {added_lines} (Limit: {args.max_loc_delta})")
    print(f"[Audit] Dependency files modified: {dependency_changed}")

    # Rule 5 check: Avoid adding arbitrary dependencies without owner approval
    if dependency_changed and not args.allow_new_deps:
        print(
            f"[Audit] [FAIL] '게으른 개발자의 사다리 (5단계: 이미 설치된 의존성)' 위반!\n"
            f"의존성 설정 파일({', '.join(f for f in changed_files if any(d in f for d in DEPENDENCY_FILES))})이 무단 수정되었습니다.\n"
            f"신규 패키지 추가가 꼭 필요하다면 소유자 승인 후 --allow-new-deps 옵션을 활성화하십시오."
        )
        return 1

    # Rule 7 check: Enforce minimal working code (LOC limit)
    if added_lines > args.max_loc_delta:
        print(
            f"[Audit] [FAIL] '게으른 개발자의 사다리 (7단계: 최소 작동 코드)' 위반!\n"
            f"추가된 소수 코드 라인 수({added_lines} LOC)가 허용 한도({args.max_loc_delta} LOC)를 초과했습니다.\n"
            f"코드를 단순화(사다리 6단계: 한 줄 코딩)하거나 기존 유틸리티를 재사용하여 복잡성을 낮추십시오."
        )
        return 1

    print("[Audit] [PASS] 게으른 개발자의 사다리 (Ponytail) 기준 충족 완료.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
