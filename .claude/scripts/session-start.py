#!/usr/bin/env python3
"""
세션 시작 시 프로젝트 상태를 실제로 확인한다.
session-start.sh의 Python 재작성 — bash spawn 비용 제거.
"""

import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, stderr=False) -> str:
    """git 등 외부 명령 실행. 실패 시 빈 문자열 반환."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return (r.stdout + (r.stderr if stderr else "")).strip()
    except Exception:
        return ""


def is_git_repo() -> bool:
    return run(["git", "rev-parse", "--is-inside-work-tree"]) == "true"


def section_git(in_git: bool) -> None:
    if not in_git:
        return
    print()
    print("🔀 Git 상태:")

    # 최근 커밋 3개 + 경과시간 — git 호출 2회로 통합
    log3 = run(["git", "log", "--oneline", "-3"])
    if log3:
        print("  최근 커밋:")
        for line in log3.splitlines():
            print(f"    {line}")

    last_time = run(["git", "log", "-1", "--format=%ar"])
    if last_time:
        print(f"  마지막 커밋: {last_time}")

    # staged / unstaged diff stat — 2회 호출
    staged = run(["git", "diff", "--cached", "--stat"])
    changes = run(["git", "diff", "--stat"])
    if staged or changes:
        print("  미커밋 변경:")
        if staged:
            last = staged.splitlines()[-1]
            print(f"    [staged]")
            print(f"    {last}")
        if changes:
            last = changes.splitlines()[-1]
            print(f"    [unstaged]")
            print(f"    {last}")

    # prior-session 신호용 저장
    unstaged_files = run(["git", "diff", "--name-only"])
    mem_dir = Path(".claude/memory")
    if mem_dir.is_dir():
        (mem_dir / "session-start-unstaged.txt").write_text(
            unstaged_files, encoding="utf-8"
        )


def parse_wip_file(path: Path) -> tuple[str, str, int, bool]:
    """WIP 파일에서 (status, title, bit_count, has_new) 반환."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", path.stem, 0, False

    lines = text.splitlines()
    status = title = ""
    in_fm = fm_done = False
    in_bit = False
    bit_count = 0
    has_new = False

    for line in lines:
        if line.strip() == "---":
            if in_fm:
                in_fm = False
                fm_done = True
            elif not fm_done:
                in_fm = True
            continue
        if in_fm:
            if line.startswith("status:"):
                status = line[7:].strip()
            elif line.startswith("title:"):
                title = line[6:].strip()
        elif fm_done:
            if not status and line.startswith("> status:"):
                status = line[9:].strip()
            if not title and line.startswith("# "):
                title = line[2:].strip()
            if line.startswith("## 발견된 스코프 외 이슈"):
                in_bit = True
                continue
            if in_bit:
                if line.startswith("## "):
                    in_bit = False
                elif line.startswith("- "):
                    bit_count += 1
                    if re.search(r"P#:.*NEW", line):
                        has_new = True

    return status, title, bit_count, has_new


def section_wip() -> None:
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir():
        print()
        print("📋 진행 중인 작업: 없음")
        return

    md_files = sorted(wip_dir.glob("*.md"))
    if not md_files:
        print()
        print("📋 진행 중인 작업: 없음")
        return

    print()
    print("📋 진행 중인 작업:")
    bit_entries: list[str] = []
    has_any_new = False

    for f in md_files:
        status, title, bit_count, has_new = parse_wip_file(f)
        print(f"  - [{status}] {title} ({f.name})")
        if bit_count > 0:
            suffix = " ⚠️ NEW P# 포함" if has_new else ""
            bit_entries.append(f"  {f.name}: {bit_count}건{suffix}")
            if has_new:
                has_any_new = True

    if bit_entries:
        print()
        print("🐛 발견된 스코프 외 이슈 (bug-interrupt.md Q3 기록):")
        for entry in bit_entries:
            print(entry)
        if has_any_new:
            print()
            print("  ⚠️  CPS 신규 P# 검토 필요 — implementation Step 0에서 project_kickoff.md 갱신")


def section_memory() -> None:
    mem = Path(".claude/memory/MEMORY.md")
    if not mem.is_file():
        return
    try:
        count = sum(1 for line in mem.read_text(encoding="utf-8").splitlines()
                    if line.startswith("- "))
    except Exception:
        count = 0
    print()
    print(f"🧠 메모리: {count}개 항목 로드됨")


def section_todo() -> None:
    src = Path("src")
    if not src.is_dir():
        return
    exts = {".ts", ".tsx", ".js", ".jsx", ".py"}
    pattern = re.compile(r"TODO|FIXME|HACK")
    count = 0
    for f in src.rglob("*"):
        if f.suffix not in exts:
            continue
        try:
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if pattern.search(line):
                    count += 1
        except Exception:
            pass
    if count > 0:
        print()
        print(f"⚠️ 코드에 TODO/FIXME/HACK {count}개 발견. docs/WIP/에 옮겨야 함.")


def section_zombie() -> None:
    result = run(["pgrep", "-f", "(node|python).*test"])
    count = len([l for l in result.splitlines() if l.strip()]) if result else 0
    if count > 0:
        print()
        print(f"⚠️ 테스트 관련 좀비 프로세스 {count}개 발견.")


def section_upgrade(in_git: bool) -> None:
    if not in_git:
        return

    # harness-upstream remote 존재 여부 — git remote get-url 1회
    upstream_url = run(["git", "remote", "get-url", "harness-upstream"])
    if not upstream_url:
        return

    harness_json = Path(".claude/HARNESS.json")
    if harness_json.is_file():
        try:
            import json
            installed = json.loads(harness_json.read_text(encoding="utf-8")).get("version", "")
            remote_json = run(["git", "show", "harness-upstream/main:.claude/HARNESS.json"])
            latest = json.loads(remote_json).get("version", "") if remote_json else ""
            if installed and latest and installed != latest:
                cwd = Path(".").resolve()
                print()
                print("╔════════════════════════════════════════════════════════════╗")
                print(f"║  🔄 하네스 업그레이드 가능: {installed} → {latest}  ║")
                print("║                                                            ║")
                print("║  harness-starter에서 실행:                                ║")
                print(f"║    bash h-setup.sh --upgrade {cwd}")
                print("╚════════════════════════════════════════════════════════════╝")
        except Exception:
            pass

    if Path(".claude/.upgrade").is_dir() and Path(".claude/.upgrade/UPGRADE_REPORT.md").is_file():
        print()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  ⚠️  미완료 업그레이드 감지                               ║")
        print("║                                                            ║")
        print("║  .claude/.upgrade/에 스테이징된 파일이 있습니다.          ║")
        print("║  'harness-upgrade 스킬을 실행해줘' 로 병합하세요.        ║")
        print("╚════════════════════════════════════════════════════════════╝")


def section_harness_map() -> None:
    if not Path(".claude/HARNESS_MAP.md").exists():
        print("\n⚠️  HARNESS_MAP.md 없음 — 하네스 신경망 허브 미생성")
        print("   `/eval --harness` 실행 후 HARNESS_MAP.md 확인 권장")


def section_repeated_files(in_git: bool) -> None:
    if not in_git:
        return

    # git log --name-only -2 한 번으로 두 커밋 파일 목록 취득
    log = run(["git", "log", "--name-only", "--format=COMMIT:%s", "-2", "HEAD"])
    if not log:
        return

    META = re.compile(
        r"^(\.claude/HARNESS\.json|README\.md|docs/harness/MIGRATIONS\.md|docs/clusters/.+\.md)$"
    )

    commits: list[tuple[str, set[str]]] = []
    current_msg = ""
    current_files: set[str] = set()

    for line in log.splitlines():
        if line.startswith("COMMIT:"):
            if current_msg:
                commits.append((current_msg, current_files))
                current_files = set()
            current_msg = line[7:]
        elif line.strip() and not META.match(line.strip()):
            current_files.add(line.strip())
    if current_msg:
        commits.append((current_msg, current_files))

    if len(commits) < 2:
        return

    repeated = commits[0][1] & commits[1][1]
    if not repeated:
        return

    msg1, msg2 = commits[0][0], commits[1][0]
    print()
    print("⛔ 연속 동일 파일 수정 감지: 아래 파일이 최근 2 커밋 연속 수정됐습니다.", file=sys.stderr)
    print()
    print("⛔ 연속 동일 파일 수정 감지: 아래 파일이 최근 2 커밋 연속 수정됐습니다.")
    print(f"  HEAD:   {msg1}")
    print(f"  HEAD~1: {msg2}")
    for f in sorted(repeated):
        print(f"  - {f}")
    print()
    print("<important>")
    print('동일 영역 반복 수정 = no-speculation.md "동일 수정 2회 이상" 트리거.')
    print("직접 수정 전 debug-specialist 에이전트를 즉시 호출하라.")
    print('Agent 도구로 subagent_type: "debug-specialist" 호출 — 호출 전에 증상·재현 조건·직전 수정 내용을 명시하라.')
    print()
    print("예외: 메타 파일(HARNESS.json·README.md·MIGRATIONS.md·clusters)은 이미 제외됨.")
    print("그 외에도 단순 docs 갱신·버전 범프 동반 변경이 명확하면 사용자에게 알리고 진행 가능.")
    print("</important>")


def section_rules() -> None:
    print()
    print("═══ RULES ═══")
    print("1. 린터 에러 0에서만 커밋.")
    print("2. 새 파일 생성 전 naming.md 확인.")
    print("3. 새 함수 전 check-existing으로 중복 확인.")
    print("4. 검증 없이 '완료'라고 말하지 마.")
    print("═════════════")


def main() -> None:
    print("═══ SESSION START ═══")
    in_git = is_git_repo()
    section_git(in_git)
    section_wip()
    section_memory()
    section_todo()
    section_zombie()
    section_upgrade(in_git)
    section_harness_map()
    section_repeated_files(in_git)
    section_rules()


if __name__ == "__main__":
    main()
