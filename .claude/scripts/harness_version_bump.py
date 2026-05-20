#!/usr/bin/env python3
"""
staged 변경 분석 → minor/patch/none 범프 타입 제안 출력.
      실제 HARNESS.json 수정은 Claude/사용자가 수행.
      staged가 없지만 worktree 핵심 변경이 있으면 stage_required 신호 출력.

버전 자리수 규칙: patch 0~9 (10이상→minor 올림), minor 0~99
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HARNESS_JSON = Path(".claude/HARNESS.json")

MINOR_PATTERNS = re.compile(
    r"^(\.claude/skills/[^/]+/SKILL\.md"
    r"|\.claude/agents/[^/]+\.md"
    r"|\.claude/rules/[^/]+\.md"
    r"|\.claude/scripts/[^/]+\.(sh|py))$"
)
# Phase 2 (hn_harness_recovery_v0_41_baseline, 2026-05-13):
# patch 자동 트리거 좁힘. 9b29f23 이전 패턴은 .claude/scripts/*.{sh,py} 1줄
# 수정에도 patch를 강제했고, 그 결과 도돌이표 commit이 매번 patch를 발행.
# 본 wave 결정: patch는 사용자 명시 옵트인(HARNESS_BUMP=patch) 또는
# 다운스트림 직접 영향 영역(skills SKILL.md·rules·agents·CLAUDE.md)만.
# scripts/*.{sh,py} 단순 수정은 promotion=none (작성자 명시할 때만 patch).
PATCH_PATTERNS = re.compile(
    r"^(\.claude/skills/[^/]+/SKILL\.md"
    r"|\.claude/rules/[^/]+\.md"
    r"|\.claude/agents/[^/]+\.md"
    r"|CLAUDE\.md)$"
)


def run(cmd: list[str]) -> str:
    # Windows + 한글 환경 cp949 디코딩 결함 방지 (incident hn_upstream_anomalies G)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return (r.stdout or "").strip()


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


def parse_name_status(name_status: str) -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            # rename/copy는 마지막 경로가 현재 worktree 경로다.
            changes.append((parts[0], parts[-1]))
    return changes


def classify_bump(changes: list[tuple[str, str]]) -> tuple[str, list[str]]:
    bump_type = "none"
    reasons: list[str] = []

    # minor: 신규 핵심 파일 추가
    new_critical = [path for status, path in changes
                    if status == "A" and MINOR_PATTERNS.match(path)]
    if new_critical:
        bump_type = "minor"
        reasons.append(f"신규 핵심 파일: {','.join(new_critical[:3])}")

    # patch: 기존 핵심 파일 수정
    if bump_type == "none":
        modified_critical = [path for status, path in changes
                              if status != "A" and PATCH_PATTERNS.match(path)]
        if modified_critical:
            bump_type = "patch"
            reasons.append(f"기존 핵심 파일 수정: {','.join(modified_critical[:3])}")

    return bump_type, reasons


def collect_worktree_changes() -> list[tuple[str, str]]:
    changes = parse_name_status(run(["git", "diff", "--name-status"]))
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    for path in untracked.splitlines():
        if path:
            changes.append(("A", path))
    return changes


def print_stage_required(data: dict) -> int:
    pending_bump, reasons = classify_bump(collect_worktree_changes())
    print("version_bump: none")
    print(f"current_version: {data.get('version', 'unknown')}")
    if pending_bump != "none":
        print("stage_required: true")
        print(f"pending_bump: {pending_bump}")
        if reasons:
            print(f"reasons:\n   - " + "\n   - ".join(reasons), file=sys.stderr)
    else:
        print("stage_required: false")
    return 0


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
        return print_stage_required(data)

    # (status, path) 파싱
    staged = parse_name_status(name_status)

    # 3. 범프 타입 결정
    bump_type, reasons = classify_bump(staged)

    # 4. 출력
    # HEAD 버전: 범프 기준점 (디스크는 이미 범프됐을 수 있으므로 HEAD에서 읽음)
    head_harness = run(["git", "show", "HEAD:.claude/HARNESS.json"])
    if head_harness:
        try:
            current = json.loads(head_harness).get("version", data.get("version", "unknown"))
        except Exception:
            current = data.get("version", "unknown")
    else:
        # HEAD 없음 (첫 커밋) — 디스크 버전 사용
        current = data.get("version", "unknown")

    # staged HARNESS.json 버전 (이미 범프됐는지 감지용)
    staged_harness = run(["git", "show", ":0:.claude/HARNESS.json"])
    if staged_harness:
        try:
            staged_version = json.loads(staged_harness).get("version", current)
        except Exception:
            staged_version = current
    else:
        staged_version = data.get("version", current)

    if bump_type != "none" and current != "unknown":
        nv = next_version(current, bump_type)
        # staged HARNESS.json 버전이 이미 next_version과 같으면 범프 완료로 처리
        if nv and staged_version == nv:
            bump_type = "none"
            reasons = [f"이미 범프됨: {staged_version}"]

    print(f"version_bump: {bump_type}")
    print(f"current_version: {staged_version}")
    if bump_type != "none" and current != "unknown":
        nv = next_version(current, bump_type)
        if nv:
            print(f"next_version: {nv}")
    if reasons:
        print(f"reasons:\n   - " + "\n   - ".join(reasons), file=sys.stderr)
    return 0


def archive_old_versions(keep: int = 5) -> int:
    """MIGRATIONS.md에서 최신 `keep`개 본문 섹션만 유지, 나머지를 MIGRATIONS-archive.md 상단으로 이동.

    버전 섹션 식별: 라인이 정확히 `## v\\d+\\.\\d+\\.\\d+`로 시작.
    템플릿 예시(`## v0.X → v0.Y`)는 무시.

    이동된 섹션은 archive 파일의 헤더 직후에 prepend (최신 archive가 위).
    아무 변경 없으면 0 반환.
    """
    main_path = Path("docs/harness/MIGRATIONS.md")
    arch_path = Path("docs/harness/MIGRATIONS-archive.md")
    if not main_path.exists():
        print("archive: MIGRATIONS.md 없음", file=sys.stderr)
        return 0
    text = main_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    version_re = re.compile(r"^## v\d+\.\d+\.\d+\s")
    starts: list[int] = [i for i, l in enumerate(lines) if version_re.match(l)]
    if len(starts) <= keep:
        print(f"archive: 본문 {len(starts)}개 ≤ {keep}, 이동 불필요")
        return 0

    # keep개 유지 → keep번째 인덱스부터가 archive 대상
    cut_start = starts[keep]
    archive_block_lines = lines[cut_start:]
    main_block_lines    = lines[:cut_start]

    # 본문 끝 trailing `---` 정리
    while main_block_lines and main_block_lines[-1].strip() in ("", "---"):
        main_block_lines.pop()
    main_block_lines.append("")  # 끝 빈 줄 1개

    # archive 헤더 + 기존 archive 본문 합치기
    if arch_path.exists():
        arch_text = arch_path.read_text(encoding="utf-8")
        arch_lines = arch_text.splitlines()
        # frontmatter 끝 + 인트로 마지막 `---` 다음 위치 찾기
        sep_count = 0
        intro_end = 0
        for i, l in enumerate(arch_lines):
            if l.strip() == "---":
                sep_count += 1
                if sep_count == 3:  # frontmatter 2 + 인트로 끝 1
                    intro_end = i + 1
                    break
        if intro_end == 0:
            print("archive: 기존 archive 헤더 파싱 실패 — 수동 확인", file=sys.stderr)
            return 2
        new_arch = (
            arch_lines[:intro_end]
            + [""]
            + archive_block_lines
            + [""]
            + arch_lines[intro_end:]
        )
    else:
        # archive 신설
        header = [
            "---",
            "title: 다운스트림 마이그레이션 가이드 — 아카이브",
            "domain: harness",
            "tags: [migration, upgrade, downstream, archive]",
            "status: completed",
            "created: 2026-05-02",
            "---",
            "",
            "# 다운스트림 마이그레이션 가이드 — 아카이브",
            "",
            "MIGRATIONS.md는 최신 5개만 유지. 이전 버전은 본 파일에 누적.",
            "",
            "---",
        ]
        new_arch = header + [""] + archive_block_lines

    arch_path.write_text("\n".join(new_arch) + "\n", encoding="utf-8")
    main_path.write_text("\n".join(main_block_lines) + "\n", encoding="utf-8")

    moved = len(starts) - keep
    print(f"archive: {moved}개 섹션 이동 → MIGRATIONS-archive.md")
    return 0


def print_usage() -> None:
    print(
        "usage: harness_version_bump.py [--archive [KEEP]]\n"
        "       harness_version_bump.py --help",
        file=sys.stderr,
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(main())
    if args[0] in ("-h", "--help"):
        print_usage()
        sys.exit(0)
    if args[0] == "--archive":
        if len(args) > 2:
            print_usage()
            sys.exit(2)
        try:
            keep = int(args[1]) if len(args) == 2 else 5
        except ValueError:
            print_usage()
            sys.exit(2)
        sys.exit(archive_old_versions(keep))

    print(f"unsupported_arg: {args[0]}", file=sys.stderr)
    print_usage()
    sys.exit(2)
