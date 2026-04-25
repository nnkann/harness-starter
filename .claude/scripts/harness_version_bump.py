#!/usr/bin/env python3
"""
staged 변경 분석 → minor/patch/none 범프 타입 제안 출력.
      실제 HARNESS.json 수정은 Claude/사용자가 수행.

버전 자리수 규칙: patch 0~9 (10이상→minor 올림), minor 0~99
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HARNESS_JSON = Path(".claude/HARNESS.json")


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def next_version(current: str, bump_type: str) -> str:
    parts = current.split(".")
    if len(parts) != 3:
        return ""
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump_type == "patch":
        patch += 1
        if patch >= 10:
            minor += 1
            patch = 0
            if minor >= 100:
                major += 1; minor = 0
    elif bump_type == "minor":
        minor += 1
        if minor >= 100:
            major += 1; minor = 0
        patch = 0
    return f"{major}.{minor}.{patch}"


def main() -> int:
    # 1. is_starter 판정
    if not HARNESS_JSON.exists():
        return 0
    try:
        data = json.loads(HARNESS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not data.get("is_starter"):
        return 0  # 다운스트림: 조용히 skip

    # 2. staged 파일 수집
    name_status = run(["git", "diff", "--cached", "--name-status"])
    if not name_status:
        print("version_bump: none (staged 없음)")
        return 0

    # (status, path) 파싱
    staged: list[tuple[str, str]] = []
    for line in name_status.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            staged.append((parts[0], parts[1]))

    # 3. 범프 타입 결정
    MINOR_PATTERNS = re.compile(
        r"^(\.claude/skills/[^/]+/SKILL\.md"
        r"|\.claude/agents/[^/]+\.md"
        r"|\.claude/rules/[^/]+\.md"
        r"|\.claude/scripts/[^/]+\.(sh|py))$"
    )
    PATCH_PATTERNS = re.compile(
        r"^(\.claude/scripts/[^/]+\.(sh|py)"
        r"|\.claude/skills/[^/]+/SKILL\.md"
        r"|\.claude/rules/[^/]+\.md"
        r"|\.claude/agents/[^/]+\.md"
        r"|CLAUDE\.md)$"
    )

    bump_type = "none"
    reasons: list[str] = []

    # minor: 신규 핵심 파일 추가
    new_critical = [path for status, path in staged
                    if status == "A" and MINOR_PATTERNS.match(path)]
    if new_critical:
        bump_type = "minor"
        reasons.append(f"신규 핵심 파일: {','.join(new_critical[:3])}")

    # patch: 기존 핵심 파일 수정
    if bump_type == "none":
        modified_critical = [path for status, path in staged
                              if status != "A" and PATCH_PATTERNS.match(path)]
        if modified_critical:
            bump_type = "patch"
            reasons.append(f"기존 핵심 파일 수정: {','.join(modified_critical[:3])}")

    # 4. 출력
    current = data.get("version", "unknown")
    print(f"version_bump: {bump_type}")
    print(f"current_version: {current}")
    if bump_type != "none" and current != "unknown":
        nv = next_version(current, bump_type)
        if nv:
            print(f"next_version: {nv}")
    if reasons:
        print(f"reasons:\n   - " + "\n   - ".join(reasons), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
