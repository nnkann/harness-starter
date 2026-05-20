#!/usr/bin/env python3
"""
세션 시작 시 프로젝트 상태를 실제로 확인한다.
기존 shell hook을 Python hook으로 전환 — bash spawn 비용 제거.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# cwd 보정 — hook 실행 시 cwd가 .claude/scripts/로 들어오는 케이스
# 안전망 (stop-guard.py와 동일 패턴).
os.chdir(Path(__file__).resolve().parents[2])

# wip_util SSOT (parse_wip_file). __init__.py 통한 패키지 import.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.wip_util import parse_wip_file  # noqa: E402

# Windows cp949 콘솔에서 emoji 출력 시 UnicodeEncodeError 차단.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


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

    for f in md_files:
        status, title, _bit_count, _has_new = parse_wip_file(f)
        print(f"  - [{status}] {title} ({f.name})")


def section_memory() -> None:
    mem = Path(".claude/memory/MEMORY.md")
    if not mem.is_file():
        return
    try:
        count = sum(
            1 for line in mem.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ")
        )
    except Exception:
        count = 0
    print()
    if count:
        print(f"🧠 memory index: {count} links available; content not injected")
    else:
        print("🧠 memory index: empty; content not injected")


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


@dataclass(frozen=True)
class WipContext:
    domains: set[str]
    problems: set[str]
    tokens: set[str]


@dataclass(frozen=True)
class ReminderItem:
    line: str
    strength: str
    stale: bool
    kv_group: str
    group_hit: bool
    cross_domain: bool


def iter_reminder_paths(mem_dir: Path) -> list[Path]:
    """신규 reminders/ 우선, 루트 reminder/signal은 legacy fallback으로 읽는다."""
    paths: list[Path] = []
    seen: set[str] = set()
    for directory in (mem_dir / "reminders", mem_dir):
        if not directory.is_dir():
            continue
        for path in sorted({*directory.glob("reminder_*.md"), *directory.glob("signal_*.md")}):
            if path.name in seen:
                continue
            seen.add(path.name)
            paths.append(path)
    return paths


def _frontmatter_value(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _frontmatter_ids(text: str, key: str, prefix: str) -> set[str]:
    value = _frontmatter_value(text, key)
    if not value:
        return set()
    return set(re.findall(rf"\b{re.escape(prefix)}\d+\b", value))


def _frontmatter_list_tokens(text: str, key: str) -> set[str]:
    value = _frontmatter_value(text, key)
    if not value:
        return set()
    tokens = re.findall(r"[a-z0-9][a-z0-9-]*", value.lower())
    return set(tokens)


def _slug_tokens(path: Path) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9-]*", path.name.lower()))


def get_wip_context() -> WipContext:
    """현재 WIP의 domain/problem/tags/slug로 reminder query context 생성."""
    domains: set[str] = set()
    problems: set[str] = set()
    tokens: set[str] = set()
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir():
        return WipContext(domains, problems, tokens)
    for f in wip_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            domain = _frontmatter_value(text, "domain")
            if domain:
                domains.add(domain)
                tokens.add(domain.lower())
            problems.update(_frontmatter_ids(text, "problem", "P"))
            tokens.update(_frontmatter_list_tokens(text, "tags"))
            tokens.update(_slug_tokens(f))
        except Exception:
            pass
    changed = run(["git", "diff", "--name-only"])
    changed_cached = run(["git", "diff", "--cached", "--name-only"])
    for path in (changed + "\n" + changed_cached).splitlines():
        tokens.update(re.findall(r"[a-z0-9][a-z0-9-]*", path.lower()))
    return WipContext(domains, problems, tokens)


def get_wip_domains() -> set[str]:
    """현재 WIP 파일들의 frontmatter domain 값 수집. 없으면 빈 set."""
    return get_wip_context().domains


def derive_kv_query_groups(context: WipContext) -> set[str]:
    """WIP context에서 보수적인 grouped active reminder query 후보 생성."""
    groups: set[str] = set()
    if not context.domains or not context.problems:
        return groups

    family_rules = {
        "review-commit": {"review", "commit", "pre-check", "precheck", "stage", "staged"},
        "stale-memory": {"memory", "reminder", "signal", "stale", "valid", "valid-until"},
        "session-start": {"session-start", "session", "start", "hook", "hooks"},
        "ssot-validation": {"ssot", "rules", "docs", "validation", "verify", "cps"},
    }
    families = {
        family for family, markers in family_rules.items()
        if context.tokens & markers
    }
    for domain in context.domains:
        for problem in context.problems:
            for family in families:
                groups.add(f"{domain}/{problem}/{family}")
    return groups


def section_reminders() -> None:
    """현재 WIP domain과 매칭되는 reminder만 출력. signal_*은 legacy alias."""
    mem_dir = Path(".claude/memory")
    if not mem_dir.is_dir():
        return
    reminders = iter_reminder_paths(mem_dir)
    if not reminders:
        return
    context = get_wip_context()
    domains = context.domains
    query_groups = derive_kv_query_groups(context)
    matched: list[ReminderItem] = []
    cross_domain_strong: list[ReminderItem] = []
    for f in reminders:
        try:
            text = f.read_text(encoding="utf-8")
            m_sig = re.search(r"^(?:reminder|signal):\s*(.+)", text, re.MULTILINE)
            m_dom = re.search(r"^domain:\s*(\S+)", text, re.MULTILINE)
            m_str = re.search(r"^strength:\s*(\S+)", text, re.MULTILINE)
            m_status = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
            m_valid = re.search(r"^valid_until:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
            m_legacy_arc = re.search(r"^archived:\s*(true|True|TRUE)", text, re.MULTILINE)
            m_group = re.search(r"^kv_group:\s*(\S+)", text, re.MULTILINE)
            if not m_sig:
                continue
            sig_domain = m_dom.group(1).strip() if m_dom else ""
            strength = m_str.group(1).strip() if m_str else "weak"
            status = m_status.group(1).strip() if m_status else "active"
            if m_legacy_arc:
                status = "archived"
            if status in {"archived", "suppressed"}:
                continue

            stale = False
            if m_valid:
                try:
                    stale = date.fromisoformat(m_valid.group(1).strip()) < date.today()
                except ValueError:
                    stale = True

            icon = {"weak": "🔸", "medium": "🔶", "strong": "🔴"}.get(strength, "🔸")
            suffix = " (stale 후보 — 재확인 필요)" if stale else ""
            line = f"  {icon} {m_sig.group(1).strip()}{suffix}"
            kv_group = m_group.group(1).strip() if m_group else ""
            group_hit = bool(kv_group and kv_group in query_groups)
            item = ReminderItem(
                line=line,
                strength=strength,
                stale=stale,
                kv_group=kv_group,
                group_hit=group_hit,
                cross_domain=False,
            )

            if domains and sig_domain and sig_domain not in domains:
                if strength == "strong" and len(cross_domain_strong) < 2:
                    cross_domain_strong.append(
                        ReminderItem(
                            line=line,
                            strength=strength,
                            stale=stale,
                            kv_group=kv_group,
                            group_hit=group_hit,
                            cross_domain=True,
                        )
                    )
                continue
            matched.append(item)
        except Exception:
            pass
    matched.extend(cross_domain_strong)
    if matched:
        strength_rank = {"strong": 3, "medium": 2, "weak": 1}
        matched.sort(
            key=lambda item: (
                not item.group_hit,
                item.stale,
                -strength_rank.get(item.strength, 0),
                item.kv_group,
                item.line,
            )
        )
        if len(matched) > 8:
            shown: list[ReminderItem] = []
            group_counts: dict[str, int] = {}
            for item in matched:
                if item.group_hit and item.kv_group:
                    count = group_counts.get(item.kv_group, 0)
                    if count >= 2:
                        continue
                    group_counts[item.kv_group] = count + 1
                shown.append(item)
                if len(shown) >= 8:
                    break
            hidden = len(matched) - len(shown)
        else:
            shown = matched
            hidden = 0

        print()
        print("📌 리마인더 (memory):")
        for item in shown:
            print(item.line)
        if hidden:
            print(f"  · 추가 후보 {hidden}건은 memory index에서 확인")


def section_signals() -> None:
    # 기존 호출자 호환용 진입점. 새 개념명은 reminder.
    section_reminders()


def section_incidents() -> None:
    """현재 WIP domain과 일치하는 최근 30일 incident 자동 출력 (D-Lite, P8 Phase 3).

    advisor 권고: tags ∩ symptom-keywords 매칭은 복잡도·소급 적용 부담으로 Phase 4 유보.
    1차는 도메인 매칭 + created 30일 + 최대 3건.
    """
    inc_dir = Path("docs/incidents")
    if not inc_dir.is_dir():
        return
    domains = get_wip_domains()
    if not domains:
        return  # WIP 없으면 침묵
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=30)
    matched: list[tuple[str, str]] = []  # (created, title)
    for f in sorted(inc_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            m_dom = re.search(r"^domain:\s*(\S+)", text, re.MULTILINE)
            m_title = re.search(r"^title:\s*(.+)", text, re.MULTILINE)
            m_created = re.search(r"^created:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
            if not (m_dom and m_title and m_created):
                continue
            if m_dom.group(1).strip() not in domains:
                continue
            try:
                d = date.fromisoformat(m_created.group(1).strip())
            except ValueError:
                continue
            if d < cutoff:
                continue
            matched.append((m_created.group(1).strip(), m_title.group(1).strip()))
        except Exception:
            pass
    if not matched:
        return
    matched.sort(reverse=True)  # 최신순
    print()
    print("📜 최근 30일 incident (현재 WIP domain 매칭, 최대 3건):")
    for created, title in matched[:3]:
        print(f"  · [{created}] {title}")


def section_harness_map() -> None:
    # HARNESS_MAP.md 폐기 (§S-1 CPS 재설계). 본 함수 no-op 유지 (호출자 호환).
    return


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
    repeated_sorted = sorted(repeated)
    shown = repeated_sorted[:5]
    hidden = len(repeated_sorted) - len(shown)
    print()
    print(f"⛔ 연속 동일 파일 수정 감지: 최근 2커밋 공통 {len(repeated_sorted)}개")
    print(f"  HEAD:   {msg1}")
    print(f"  HEAD~1: {msg2}")
    for f in shown:
        print(f"  - {f}")
    if hidden:
        print(f"  ... {hidden}개 더 있음")
    print("  action: 같은 원인인지 확인. 불명확하면 debug-specialist 호출.")


def section_rules() -> None:
    print()
    print("═══ RULES ═══")
    print("1. 린터 에러 0에서만 커밋.")
    print("2. 새 파일 생성 전 naming.md 확인.")
    print("3. 새 함수 전 LSP + Grep으로 중복 확인.")
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
    section_signals()
    section_incidents()
    section_repeated_files(in_git)
    section_rules()


if __name__ == "__main__":
    main()
