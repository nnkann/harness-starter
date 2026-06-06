#!/usr/bin/env python3
"""eval --harness CLI 백엔드 단일 진입점.

SKILL.md 본문이 LLM 해석에 의존하던 결정적 측정 항목을 스크립트로 이전.
LLM 해석 영역(모호성·모순·부패·강제력 배치)은 SKILL.md에 잔존.

본 백엔드 책임:
1. CPS 무결성 (eval_cps_integrity.py 호출 — 항목 5)
2. 방어 활성 기록 (reminder_defense_success.md — 항목 6)
3. 피드백 리포트 (eval_cps_integrity가 처리 — 항목 7)
4. 검증 도구 정렬 진단 (LSP/lint/tsc 산출물 vs src — 항목 8 신규)
5. 느슨한 결합 관측 (스킬 라우팅·WIP 파일명 계약 drift — 항목 10)

eval_cps_integrity.py를 deprecated 처리하지 않고 호출 대상으로 유지
(코드 중복 0). pre_commit_check 헬퍼·wip_util은 직접 import 재사용.

출력:
  stdout: 구조화 보고 (SKILL.md가 파싱)
  stderr: 사람용 경고
  exit 0: 보고 완료 (신호 hit건 무관 — 진단 채널)
  exit 2: 형식 위반·필수 파일 Read 실패
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# Windows cp949 안전 처리 (eval_cps_integrity.py 답습)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# 본 wave 후속 의무: wip_util.py SSOT import (4중 파편화 방지 — sh_self_replication_audit + wip_util_ssot 결정)
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from utils.wip_util import parse_wip_file  # noqa: E402

REPO_ROOT = SCRIPTS_DIR.parent.parent
SELF_DIAGNOSTIC_SCRIPTS = {
    ".claude/scripts/eval_harness.py",
    ".claude/scripts/eval_cps_integrity.py",
}


# ──────────────────────────────────────────────────────────────────────
# 항목 5·7. CPS 무결성 + 피드백 리포트 — eval_cps_integrity.py 위임
# ──────────────────────────────────────────────────────────────────────

def run_cps_integrity() -> int:
    """eval_cps_integrity.py 호출 (subprocess — 출력 channel 그대로 노출).

    return: subprocess exit code (0 정상, 2 차단)
    """
    script = SCRIPTS_DIR / "eval_cps_integrity.py"
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=False,
            text=True,
            encoding="utf-8",
        )
        return r.returncode
    except Exception as e:
        print(f"❌ eval_cps_integrity.py 호출 실패: {e}", file=sys.stderr)
        return 2


# ──────────────────────────────────────────────────────────────────────
# 항목 6. 방어 활성 기록
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# 항목 9. starter 본문 dead reference (P11 첫 누적 case 박제 후 추가)
# ──────────────────────────────────────────────────────────────────────

# 폐기 패턴 — 의도적 박제(폐기·흡수·삭제) 표현은 면제 정규식 처리.
# starter 고유 경로/파일명만 등재. 일반 단어(`staging.md` 등)는
# 다운스트림 false positive 회피를 위해 경로 prefix로 좁힌다.
# (v0.47.11 — `staging.md`만 단순 basename → `rules/staging.md` prefix화)
# (v0.47.13 — 본문 표현(eval 모드·rel 타입) 등록 시도 → 사용자 우려로 폐기.
#  본문 표현은 SSOT 인용 원칙(rules/docs.md "SSOT 인용 원칙")으로 차단.
#  파일/경로만 hardcoded — git tree와 1:1 매핑이라 SSOT 자기 일치)
_DEAD_REF_PATTERNS = [
    "anti-defer.md",
    "bug-interrupt.md",
    "external-experts.md",
    "pipeline-design.md",
    "rules/staging.md",        # 일반 단어 `staging` false positive 차단
    "orchestrator.py",
    "debug-guard.sh",
    "check-existing/",
    "doc-health/",
    "HARNESS_MAP.md",
]

# 박제 표현 — 의도적 폐기 인용. 라인 안에 있으면 면제.
_DEAD_REF_EXEMPT = re.compile(
    r"(폐기|흡수|삭제|removed|deprecated|MIGRATIONS|변경 이력|회고|legacy|fallback|archive|history|이전|박제|다운스트림|예시|샘플|example|sample)",
    re.IGNORECASE,
)

# 스캔 대상 — starter 본문 (rules·skills·agents·README)
_DEAD_REF_SCAN_GLOBS = [
    ".claude/skills/**/*.md",
    ".claude/agents/**/*.md",
    ".claude/rules/**/*.md",
    "README.md",
]

_PATH_CONTRACT_SCAN_GLOBS = [
    "CLAUDE.md",
    "AGENTS.md",
    "README.md",
    "docs/harness/MIGRATIONS.md",
    ".claude/skills/**/*.md",
    ".agents/skills/**/*.md",
    ".claude/agents/**/*.md",
    ".claude/rules/**/*.md",
    ".claude/scripts/**/*.py",
    ".claude/scripts/**/*.sh",
]

_PATH_CONTRACT_TOKEN_RE = re.compile(
    r"(?P<path>(?:\.claude|\.agents|docs)/(?:[A-Za-z0-9_.@{}*?+\-=]+/)*[A-Za-z0-9_.@{}*?+\-=]+\.(?:md|mdx|py|sh|json|toml|ya?ml))"
)
_PATH_CONTRACT_TRAILING = ".,:;)]}>`'\""
_PATH_CONTRACT_ALLOWED_GLOBS = (
    ".claude/memory/reminders/reminder_*.md",
    ".claude/memory/reminders/signal_*.md",
    ".claude/memory/reminder_*.md",
    ".claude/memory/signal_*.md",
)
_PATH_CONTRACT_OPTIONAL_PATHS = {
    ".claude/.upgrade/UPGRADE_REPORT.md",
    ".claude/harness-overrides.md",
    "docs/harness/migration-log.md",
}


def _is_path_contract_scan_target(path: Path) -> bool:
    try:
        rel = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.is_file()
    if rel == "docs/harness/MIGRATIONS-archive.md":
        return False
    if rel in {"CLAUDE.md", "AGENTS.md", "README.md", "docs/harness/MIGRATIONS.md"}:
        return True
    if rel.startswith(".claude/scripts/tests/"):
        return False
    return rel.startswith(
        (
            ".claude/skills/",
            ".agents/skills/",
            ".claude/agents/",
            ".claude/rules/",
            ".claude/scripts/",
        )
    )


def scan_path_contracts(
    paths: list[Path],
) -> list[tuple[str, int, str, str]]:
    """라이브 안내·스크립트의 하네스 경로 문자열이 실제 파일과 맞는지 검출한다.

    paths가 빈 list면 라이브 계약 파일만 전체 스캔한다. MIGRATIONS archive와
    legacy/fallback/폐기 박제 라인은 history로 간주해 면제한다.
    각 hit: (rel_path, lineno, missing_path, line_snippet).
    """
    hits: list[tuple[str, int, str, str]] = []
    if not paths:
        targets = [
            p
            for glob in _PATH_CONTRACT_SCAN_GLOBS
            for p in REPO_ROOT.glob(glob)
            if p.is_file() and _is_path_contract_scan_target(p)
        ]
    else:
        targets = [
            p
            for p in paths
            if p.is_file() and _is_path_contract_scan_target(p)
        ]

    for path in targets:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        for lineno, line in enumerate(lines, start=1):
            if _DEAD_REF_EXEMPT.search(line):
                continue
            for match in _PATH_CONTRACT_TOKEN_RE.finditer(line):
                token = match.group("path").replace("\\", "/").rstrip(_PATH_CONTRACT_TRAILING)
                if not token or token.endswith("/"):
                    continue
                token = token.split("#", 1)[0]
                if "{" in token or "}" in token:
                    continue
                if token in _PATH_CONTRACT_OPTIONAL_PATHS:
                    continue
                if rel.startswith((".claude/skills/", ".agents/skills/")) and token.startswith("docs/"):
                    continue
                if "*" in token or "?" in token:
                    continue
                if not (REPO_ROOT / token).exists():
                    hits.append((rel, lineno, token, line.strip()[:100]))
    return hits


def scan_dead_reference_paths(
    paths: list[Path],
) -> list[tuple[str, int, str, str]]:
    """주어진 파일 경로 list에서 dead reference 검출 (pre-check 재사용용).

    paths가 빈 list면 _DEAD_REF_SCAN_GLOBS 전체 스캔 (eval --harness 동작).
    각 hit: (rel_path, lineno, dead_pattern, line_snippet).
    """
    hits: list[tuple[str, int, str, str]] = []
    if not paths:
        targets = [
            p
            for glob in _DEAD_REF_SCAN_GLOBS
            for p in REPO_ROOT.glob(glob)
            if p.is_file()
        ]
    else:
        targets = [p for p in paths if p.is_file()]
    for path in targets:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        for lineno, line in enumerate(lines, start=1):
            if _DEAD_REF_EXEMPT.search(line):
                continue
            for dead in _DEAD_REF_PATTERNS:
                if dead in line:
                    hits.append((rel, lineno, dead, line.strip()[:80]))
                    break
    return hits


def section_dead_reference() -> None:
    """폐기 파일을 본문 예시·안내로 참조하는 dead reference 검출."""
    print("")
    print("## starter 본문 dead reference 검사")
    hits = scan_dead_reference_paths([])
    if not hits:
        print("- 검출 0건 ✅")
        return
    print(f"- ⚠ 검출 {len(hits)}건 (폐기·흡수·삭제 박제 표현은 면제)")
    for rel, lineno, dead, snippet in hits[:10]:
        print(f"  - {rel}:{lineno} | `{dead}` | {snippet}")
    if len(hits) > 10:
        print(f"  ... 외 {len(hits) - 10}건")
    print("  대응: harness-dev SKILL.md '폐기 절차' 참조 — 본문 예시 갱신 또는 박제 표현 명시")


def section_tool_availability() -> None:
    """검증 도구가 실제로 PATH에 있는지 관측한다."""
    print("")
    print("## 검증 도구 가용성")
    tools = ("ruff", "pyright", "mypy", "shellcheck")
    missing: list[str] = []
    for tool in tools:
        resolved = shutil.which(tool)
        if resolved:
            print(f"- {tool}: {resolved}")
        else:
            missing.append(tool)
            print(f"- {tool}: missing (검사 미실행 가능성 관측)")
    if not missing:
        print("- 누락 0건 ✅")
    else:
        print(f"- 관측 누락 {len(missing)}건: {', '.join(missing)}")


def section_path_contract_lint() -> None:
    """라이브 하네스 안내의 경로 문자열 drift를 관측한다."""
    print("")
    print("## path contract lint")
    hits = scan_path_contracts([])
    if not hits:
        print("- 검출 0건 ✅")
        return
    print(f"- ⚠ 검출 {len(hits)}건 (archive/history/legacy/fallback 라인은 면제)")
    for rel, lineno, missing, snippet in hits[:10]:
        print(f"  - {rel}:{lineno} | `{missing}` | {snippet}")
    if len(hits) > 10:
        print(f"  ... 외 {len(hits) - 10}건")
    print("  대응: 경로 문자열을 현재 파일 트리로 갱신하거나 history/legacy 박제 표현을 명시")


def section_defense_record() -> None:
    """reminder_defense_success.md 존재·최근 기록 보고."""
    print("")
    print("## 방어 활성 기록")
    sig = reminder_file_path("reminder_defense_success.md")
    if not sig.exists():
        print("- 방어 기록 없음 (한 번도 차단 없었거나 Wave A 이전 버전)")
        return
    try:
        text = sig.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"- ⚠ Read 실패: {e}")
        return
    # 항목 라인: "- YYYY-MM-DD | <reason>"
    items = [l for l in text.splitlines() if re.match(r"^- \d{4}-\d{2}-\d{2}", l)]
    print(f"- 총 {len(items)}건")
    if items:
        print("- 최근 3건:")
        for line in items[-3:]:
            print(f"  {line}")


# ──────────────────────────────────────────────────────────────────────
# 항목 6.5. memory/reminder frontmatter lint
# ──────────────────────────────────────────────────────────────────────

_KV_GROUP_RE = re.compile(r"^[a-z0-9][a-z0-9-]*/P\d+/[a-z0-9][a-z0-9-]*$")


def reminder_file_path(name: str) -> Path:
    """신규 reminders/ 경로 우선, 없으면 루트 legacy 경로를 반환한다."""
    mem_dir = REPO_ROOT / ".claude" / "memory"
    preferred = mem_dir / "reminders" / name
    if preferred.exists():
        return preferred
    return mem_dir / name


def iter_reminder_paths() -> list[Path]:
    """신규 reminders/ 우선, 루트 reminder/signal은 legacy fallback으로 읽는다."""
    mem_dir = REPO_ROOT / ".claude" / "memory"
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


def parse_simple_frontmatter(text: str) -> dict[str, str]:
    """단순 frontmatter key:value 파서. eval warning용이라 list 정규화는 하지 않는다."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def analyze_reminder_frontmatter() -> dict[str, list[str]]:
    """reminder/signal frontmatter 보강 후보를 보고용으로 분류한다.

    hard block이 아니라 eval --harness warning/report 채널이다.
    """
    report = {
        "missing_kv_group": [],
        "invalid_kv_group": [],
        "overbroad_kv_group": [],
        "oversplit_kv_group": [],
        "candidate_mismatch": [],
        "stale_candidates": [],
        "legacy_signals": [],
        "missing_status": [],
    }
    for path in iter_reminder_paths():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_simple_frontmatter(text)
        name = path.name
        is_legacy = name.startswith("signal_")
        if is_legacy:
            report["legacy_signals"].append(name)

        reminder = fm.get("reminder") or fm.get("signal")
        if not reminder:
            continue
        status = fm.get("status", "")
        strength = fm.get("strength", "weak")
        candidate_p = fm.get("candidate_p", "")
        kv_group = fm.get("kv_group", "")

        if not status and not is_legacy:
            report["missing_status"].append(name)
        if not kv_group and (not is_legacy or strength == "strong"):
            report["missing_kv_group"].append(name)
        if kv_group:
            parts = kv_group.split("/")
            if len(parts) < 3:
                report["overbroad_kv_group"].append(f"{name}: {kv_group}")
            elif len(parts) > 3:
                report["oversplit_kv_group"].append(f"{name}: {kv_group}")
            if not _KV_GROUP_RE.match(kv_group):
                report["invalid_kv_group"].append(f"{name}: {kv_group}")
            elif candidate_p and len(parts) == 3 and parts[1] != candidate_p:
                report["candidate_mismatch"].append(
                    f"{name}: candidate_p={candidate_p}, kv_group={kv_group}"
                )

        valid_until = fm.get("valid_until", "")
        if valid_until:
            try:
                if date.fromisoformat(valid_until) < date.today():
                    report["stale_candidates"].append(f"{name}: valid_until={valid_until}")
            except ValueError:
                report["stale_candidates"].append(f"{name}: valid_until={valid_until} (invalid)")

    return report


def analyze_reminder_promotion_candidates() -> list[str]:
    """관련 WIP 흡수 또는 정식 WIP 승격 후보 reminder를 보고한다.

    reminder는 backlog가 아니라 routing signal이다. 길거나 강하거나 근거 owner가
    약한 항목은 관련 작업에 흡수하거나 WIP를 거쳐 decision/incident/rules로
    승격할 후보로 본다.
    """
    candidates: list[str] = []
    group_counts: dict[str, list[str]] = {}
    for path in iter_reminder_paths():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_simple_frontmatter(text)
        name = path.name
        reminder = fm.get("reminder") or fm.get("signal")
        if not reminder:
            continue
        status = fm.get("status", "active")
        if status in {"archived", "suppressed"}:
            continue
        strength = fm.get("strength", "weak")
        source = fm.get("source", "")
        kv_group = fm.get("kv_group", "")
        if kv_group:
            group_counts.setdefault(kv_group, []).append(name)

        body_lines = [
            line for line in text.splitlines()
            if line.strip() and line.strip() != "---"
        ]
        if len(body_lines) > 35:
            candidates.append(f"{name}: 본문 {len(body_lines)}줄 — 관련 WIP 흡수 또는 WIP 승격 후보")
        if strength == "strong" and source in {"", "user", "audit"}:
            candidates.append(f"{name}: strong + source={source or 'none'} — SSOT owner 필요")

    for group, names in sorted(group_counts.items()):
        active_names = sorted(names)
        if len(active_names) > 3:
            candidates.append(
                f"{group}: active reminder {len(active_names)}건 — 관련 WIP 흡수·병합 또는 WIP 승격 후보"
            )

    return candidates


def section_reminder_frontmatter_lint() -> None:
    """reminder frontmatter 보강 후보를 eval --harness에서 보고한다."""
    print("")
    print("## memory/reminder frontmatter lint")
    report = analyze_reminder_frontmatter()
    promotion = analyze_reminder_promotion_candidates()
    total = sum(len(v) for v in report.values())
    if total == 0 and not promotion:
        print("- 보강 후보 0건 ✅")
        return

    print("- pre-check hard block 아님. 신규/strong/stale/legacy 순서로 보강 권장.")
    labels = {
        "missing_kv_group": "kv_group 누락",
        "invalid_kv_group": "kv_group 형식 오류",
        "overbroad_kv_group": "과대 group",
        "oversplit_kv_group": "과소 group",
        "candidate_mismatch": "candidate_p 불일치",
        "stale_candidates": "stale 후보",
        "legacy_signals": "legacy signal",
        "missing_status": "status 누락",
    }
    for key, label in labels.items():
        items = report[key]
        if not items:
            continue
        print(f"- ⚠ {label}: {len(items)}건")
        for item in items[:8]:
            print(f"  - {item}")
        if len(items) > 8:
            print(f"  ... 외 {len(items) - 8}건")

    if promotion:
        print("- ⚠ 관련 WIP 흡수/승격 후보:")
        for item in promotion[:8]:
            print(f"  - {item}")
        if len(promotion) > 8:
            print(f"  ... 외 {len(promotion) - 8}건")
        print("  대응: 관련 WIP가 있으면 흡수하고, 없으면 docs/WIP/ 정식 작업으로 승격 후 decision/incident/rules로 이동")


# ──────────────────────────────────────────────────────────────────────
# 항목 8. 검증 도구 정렬 진단 — Phase 2·3
# ──────────────────────────────────────────────────────────────────────

def detect_typescript_signals() -> dict:
    """4신호(A/B/C/D) 검출 — 패키지별.

    A: 워크스페이스 모노레포 (루트 package.json에 workspaces)
    B: 자동 생성 타입 의존 (특정 의존성 또는 스키마 파일)
    C: 패키지 빌드 후 자체 소비 (exports가 ./dist/* + 동일 모노레포 import)
    D: 컴파일러 실행 디렉토리 분리 (tsconfig outDir이 rootDir 밖)

    Returns: {"signals": {pkg_name: [signal_codes]}, "skipped": bool}
    """
    root_pkg = REPO_ROOT / "package.json"
    if not root_pkg.exists():
        return {"signals": {}, "skipped": True, "reason": "TypeScript 프로젝트 아님 (package.json 없음)"}

    try:
        root_data = json.loads(root_pkg.read_text(encoding="utf-8"))
    except Exception as e:
        return {"signals": {}, "skipped": True, "reason": f"package.json 파싱 실패: {e}"}

    signals: dict[str, list[str]] = {}

    # ── 신호 A: workspaces 필드 ─────────────────────────────────────
    workspaces = root_data.get("workspaces") or []
    if isinstance(workspaces, dict):
        workspaces = workspaces.get("packages", [])
    has_workspace = bool(workspaces)
    if has_workspace:
        signals.setdefault("<root>", []).append("A")

    # 패키지 후보 수집 (모노레포면 workspaces 패턴 따라, 아니면 루트만)
    pkg_paths: list[Path] = [REPO_ROOT]
    if has_workspace:
        for pattern in workspaces:
            for path in REPO_ROOT.glob(f"{pattern}/package.json"):
                pkg_paths.append(path.parent)

    # ── 각 패키지 신호 검사 ─────────────────────────────────────────
    for pkg_path in pkg_paths:
        pkg_json = pkg_path / "package.json"
        if not pkg_json.exists():
            continue
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        pkg_name = pkg_data.get("name", str(pkg_path.relative_to(REPO_ROOT)) or "<root>")

        # 신호 B: codegen 의존성 또는 스키마 파일
        deps = {**(pkg_data.get("dependencies") or {}), **(pkg_data.get("devDependencies") or {})}
        codegen_deps = {"@supabase/supabase-js", "@prisma/client"}
        if any(d in deps for d in codegen_deps) or any(k.startswith("@graphql-codegen/") for k in deps):
            signals.setdefault(pkg_name, []).append("B")
        elif (pkg_path / "prisma" / "schema.prisma").exists():
            signals.setdefault(pkg_name, []).append("B")

        # 신호 C: exports가 ./dist/*
        exports = pkg_data.get("exports")
        if isinstance(exports, dict):
            for v in exports.values():
                if isinstance(v, str) and v.startswith("./dist/"):
                    signals.setdefault(pkg_name, []).append("C")
                    break
                if isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, str) and vv.startswith("./dist/"):
                            signals.setdefault(pkg_name, []).append("C")
                            break
        elif isinstance(exports, str) and exports.startswith("./dist/"):
            signals.setdefault(pkg_name, []).append("C")

        # 신호 D: tsconfig outDir이 rootDir 밖
        tsconfig = pkg_path / "tsconfig.json"
        if tsconfig.exists():
            try:
                ts_data = json.loads(tsconfig.read_text(encoding="utf-8"))
                opts = ts_data.get("compilerOptions") or {}
                out_dir = opts.get("outDir", "")
                root_dir = opts.get("rootDir", "")
                # outDir이 ../ 시작이거나 rootDir과 prefix 다르면 분리
                if out_dir and (out_dir.startswith("..") or
                                (root_dir and not out_dir.startswith(root_dir))):
                    signals.setdefault(pkg_name, []).append("D")
            except Exception:
                pass

    return {"signals": signals, "skipped": False}


def measure_alignment(pkg_path: Path) -> dict:
    """단일 패키지의 검증 도구 정렬 측정.

    측정 항목:
    - tsconfig paths: src 직접 매핑 / dist 매핑 / 매핑 없음
    - package.json exports: src 노출 / dist 노출 / 양쪽 / 미노출
    - eslint resolver (있을 때): src / dist / 미설정

    Returns: {"tsconfig_paths": str, "exports": str, "eslint_resolver": str}
    """
    result = {"tsconfig_paths": "매핑 없음", "exports": "미노출", "eslint_resolver": "없음"}

    # tsconfig paths
    tsconfig = pkg_path / "tsconfig.json"
    if tsconfig.exists():
        try:
            ts_data = json.loads(tsconfig.read_text(encoding="utf-8"))
            paths = (ts_data.get("compilerOptions") or {}).get("paths") or {}
            if paths:
                src_hit = any(any("src" in p for p in v) for v in paths.values() if isinstance(v, list))
                dist_hit = any(any("dist" in p for p in v) for v in paths.values() if isinstance(v, list))
                if src_hit and not dist_hit:
                    result["tsconfig_paths"] = "src 직접 매핑"
                elif dist_hit:
                    result["tsconfig_paths"] = "dist 매핑"
        except Exception:
            pass

    # package.json exports
    pkg_json = pkg_path / "package.json"
    if pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
            exports = pkg_data.get("exports")
            src_hit = False
            dist_hit = False
            if isinstance(exports, str):
                if "src" in exports:
                    src_hit = True
                if "dist" in exports:
                    dist_hit = True
            elif isinstance(exports, dict):
                flat = json.dumps(exports)
                src_hit = '"./src' in flat or '/src/' in flat
                dist_hit = '"./dist' in flat or '/dist/' in flat
            if src_hit and dist_hit:
                result["exports"] = "양쪽"
            elif src_hit:
                result["exports"] = "src 노출"
            elif dist_hit:
                result["exports"] = "dist 노출"
        except Exception:
            pass

    # eslint resolver — package.json 또는 .eslintrc*에서 import-resolver 검사
    eslintrc_candidates = [pkg_path / ".eslintrc.json", pkg_path / ".eslintrc.js", pkg_path / "eslint.config.js"]
    for cfg in eslintrc_candidates:
        if not cfg.exists():
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="replace")
            if "import/resolver" in text or "import-resolver" in text:
                if "src" in text and "dist" not in text:
                    result["eslint_resolver"] = "src"
                elif "dist" in text:
                    result["eslint_resolver"] = "dist"
                else:
                    result["eslint_resolver"] = "설정됨 (방향 불명)"
                break
        except Exception:
            pass

    return result


def section_alignment_diagnostics() -> None:
    """LSP/검증 도구 정렬 진단 보고."""
    print("")
    print("## 검증 도구 정렬 진단 (LSP/lint/tsc src vs dist)")

    detection = detect_typescript_signals()
    if detection.get("skipped"):
        print(f"- skip ✅ ({detection.get('reason', '')})")
        return

    signals = detection["signals"]
    if not signals:
        print("- 신호 0건 ✅ (TypeScript 프로젝트지만 정렬 위험 신호 없음)")
        return

    # 신호 보고
    print("- 신호 검출:")
    for pkg, sigs in sorted(signals.items()):
        print(f"  - `{pkg}`: {', '.join(sorted(set(sigs)))}")

    # 정렬 측정 (신호 hit 패키지 한정)
    overrides_path = REPO_ROOT / ".claude/harness-overrides.md"
    overrides_text = ""
    if overrides_path.exists():
        try:
            overrides_text = overrides_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("- 정렬 상태:")
    for pkg in sorted(signals.keys()):
        if pkg == "<root>":
            pkg_path = REPO_ROOT
        else:
            # workspaces 추적
            pkg_path = None
            for cand in REPO_ROOT.rglob("package.json"):
                try:
                    if json.loads(cand.read_text(encoding="utf-8")).get("name") == pkg:
                        pkg_path = cand.parent
                        break
                except Exception:
                    continue
            if pkg_path is None:
                continue
        align = measure_alignment(pkg_path)
        intentional = pkg in overrides_text
        marker = " (의도적 비정렬 ✅)" if intentional else ""
        print(f"  - `{pkg}`{marker}:")
        print(f"      tsconfig paths: {align['tsconfig_paths']}")
        print(f"      exports: {align['exports']}")
        print(f"      eslint resolver: {align['eslint_resolver']}")


# ──────────────────────────────────────────────────────────────────────
# 항목 10. 느슨한 결합 관측 — 스킬 라우팅·도구 계약 drift
# ──────────────────────────────────────────────────────────────────────

def observe_loose_coupling_contracts() -> list[str]:
    """느슨하게 결합된 스킬 문서와 도구 계약의 drift를 검출한다."""
    hits: list[str] = []
    files = {
        "docs_ops": REPO_ROOT / ".claude/scripts/docs_ops.py",
        "naming": REPO_ROOT / ".claude/rules/naming.md",
        "implementation": REPO_ROOT / ".claude/skills/implementation/SKILL.md",
        "write-doc": REPO_ROOT / ".claude/skills/write-doc/SKILL.md",
        "commit": REPO_ROOT / ".claude/skills/commit/SKILL.md",
    }
    texts: dict[str, str] = {}
    for name, path in files.items():
        try:
            texts[name] = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            hits.append(f"{name}: read 실패 ({e})")

    if not hits:
        expected = "{대상폴더}--{abbr}_{slug}.md"
        if "접두사 없음 (decisions--/guides--/cps--/... 필요)" in texts["docs_ops"]:
            for name in ("naming", "implementation", "write-doc", "commit"):
                if expected not in texts[name]:
                    hits.append(f"{name}: WIP 파일명 계약 누락 ({expected})")
        for name in ("implementation", "write-doc", "commit"):
            if "라우팅 태그 폐기" in texts[name]:
                hits.append(f"{name}: docs_ops.py move 계약과 반대되는 '라우팅 태그 폐기' 표현")

        if "코드·테스트·스크립트·룰 감사/개선을 위한 계획 문서" not in texts["implementation"]:
            hits.append("implementation: 계획 문서→코드/테스트 개선 라우팅 trigger 누락")
        if "write-doc이 아니라 implementation" not in texts["write-doc"]:
            hits.append("write-doc: 계획 문서→implementation 제외 규칙 누락")

    return hits


def section_loose_coupling_observability() -> None:
    """스킬/스크립트 사이 문서 계약 drift를 주기적으로 보고한다."""
    print("")
    print("## 느슨한 결합 관측")
    hits = observe_loose_coupling_contracts()
    if not hits:
        print("- 스킬 라우팅·WIP 파일명 계약 drift 0건 ✅")
        return
    print(f"- ⚠ drift 후보 {len(hits)}건")
    for hit in hits:
        print(f"  - {hit}")


# ──────────────────────────────────────────────────────────────────────
# 항목 11. 토큰 다이어트 관측 — 반복 실행·과도 라우팅 후보
# ──────────────────────────────────────────────────────────────────────

def observe_token_diet() -> dict[str, object]:
    """반복 스캔·반복 subprocess·라우팅 과잉 후보를 정적으로 관측한다."""
    eval_cps = REPO_ROOT / ".claude/scripts/eval_cps_integrity.py"
    docs_ops = REPO_ROOT / ".claude/scripts/docs_ops.py"
    implementation = REPO_ROOT / ".claude/skills/implementation/SKILL.md"
    write_doc = REPO_ROOT / ".claude/skills/write-doc/SKILL.md"
    commit = REPO_ROOT / ".claude/skills/commit/SKILL.md"

    def _safe_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    eval_cps_text = _safe_text(eval_cps)
    docs_ops_text = _safe_text(docs_ops)
    skill_text = "\n".join(_safe_text(p) for p in (implementation, write_doc, commit))

    docs_rglob_passes = eval_cps_text.count('docs_root.rglob("*.md")')
    wip_glob_passes = docs_ops_text.count('wip_dir.glob("*.md")')
    cluster_update_calls = docs_ops_text.count('"cluster-update"')

    candidates: list[str] = []
    improvements: list[str] = []
    if docs_rglob_passes > 1:
        candidates.append(
            f"eval_cps_integrity docs 전체 스캔 {docs_rglob_passes}회 — 통합 scan 후보"
        )
    if wip_glob_passes > 2:
        candidates.append(
            f"docs_ops wip-sync WIP glob {wip_glob_passes}회 — 후보 목록 재사용 검토"
        )
    if "write-doc이 아니라 implementation" in skill_text:
        improvements.append("계획 문서→코드 작업 라우팅은 implementation으로 정리됨")
    if "needs_cluster_update" in docs_ops_text:
        improvements.append("wip-sync cluster-update는 이동 후 1회로 batch 처리")
    elif cluster_update_calls > 2:
        candidates.append("wip-sync cluster-update 반복 실행 가능성 — batch 처리 후보")

    return {
        "eval_cps_docs_rglob_passes": docs_rglob_passes,
        "docs_ops_wip_glob_passes": wip_glob_passes,
        "docs_ops_cluster_update_calls": cluster_update_calls,
        "candidates": candidates,
        "improvements": improvements,
    }


def section_token_diet_observability() -> None:
    """토큰·실행 비용 다이어트 후보를 주기적으로 보고한다."""
    print("")
    print("## 토큰 다이어트 관측")
    report = observe_token_diet()
    print(f"- eval_cps_integrity docs 전체 스캔: {report['eval_cps_docs_rglob_passes']}회")
    print(f"- docs_ops wip-sync WIP glob: {report['docs_ops_wip_glob_passes']}회")
    print(f"- docs_ops cluster-update 호출 지점: {report['docs_ops_cluster_update_calls']}개")
    candidates = report["candidates"]
    improvements = report["improvements"]
    if improvements:
        print("- 적용된 다이어트:")
        for item in improvements:
            print(f"  - {item}")
    if not candidates:
        print("- 남은 후보 0건 ✅")
        return
    print("- 남은 후보:")
    for item in candidates:
        print(f"  - {item}")


# ──────────────────────────────────────────────────────────────────────
# 항목 12. C 보강·회귀 루프 관측
# ──────────────────────────────────────────────────────────────────────

def observe_c_reinforcement() -> dict[str, list[str]]:
    """C 신호 누락 WIP와 조용히 삼키는 예외 후보를 관측한다."""
    c_missing: list[str] = []
    wip_dir = REPO_ROOT / "docs/WIP"
    if wip_dir.is_dir():
        for path in sorted(wip_dir.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                c_missing.append(f"{path.relative_to(REPO_ROOT).as_posix()}: read 실패 ({e})")
                continue
            fm = parse_simple_frontmatter(text)
            has_c = bool(str(fm.get("c", "")).strip())
            has_rationale = (
                "## CPS Rationale" in text
                and ("C → P" in text or "C -> P" in text)
                and ("P → S" in text or "P -> S" in text)
                and ("S → AC" in text or "S -> AC" in text)
            )
            if not (has_c or has_rationale):
                c_missing.append(path.relative_to(REPO_ROOT).as_posix())

    silent_exceptions: list[str] = []
    scripts_dir = REPO_ROOT / ".claude/scripts"
    if scripts_dir.is_dir():
        pat = re.compile(r"except Exception(?::|\s+as\s+\w+:)\n\s+(pass|continue)\b")
        for path in sorted(scripts_dir.glob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in SELF_DIAGNOSTIC_SCRIPTS:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lines = text.splitlines()
            for m in pat.finditer(text):
                lineno = text[:m.start()].count("\n") + 1
                snippet = lines[lineno - 1].strip() if lineno <= len(lines) else "except Exception"
                silent_exceptions.append(f"{rel}:{lineno} | {snippet}")

    return {
        "c_missing": c_missing,
        "silent_exceptions": silent_exceptions,
    }


def section_c_reinforcement_observability() -> None:
    """오류·미흡 발견이 C 보강과 회귀 후보로 이어지는지 보고한다."""
    print("")
    print("## C 보강·회귀 루프 관측")
    report = observe_c_reinforcement()
    c_missing = report["c_missing"]
    silent_exceptions = report["silent_exceptions"]
    if not c_missing:
        print("- WIP C 신호 누락 0건 ✅")
    else:
        print(f"- ⚠ WIP C 신호 누락 {len(c_missing)}건")
        for item in c_missing[:10]:
            print(f"  - {item}")
    if not silent_exceptions:
        print("- silent exception 후보 0건 ✅")
    else:
        print(f"- ⚠ silent exception 후보 {len(silent_exceptions)}건")
        for item in silent_exceptions[:10]:
            print(f"  - {item}")
        if len(silent_exceptions) > 10:
            print(f"  ... 외 {len(silent_exceptions) - 10}건")


# ──────────────────────────────────────────────────────────────────────
# 항목 13. policy drift + dispatcher drift 관측
# ──────────────────────────────────────────────────────────────────────

_POLICY_DRIFT_PATTERNS = [
    (
        "worktree blanket ban",
        re.compile(r"(worktree 생성 금지|git worktree add 금지|isolation:\s*[\"']worktree[\"'] 사용 금지)"),
    ),
    (
        "sandbox without permission-ready",
        re.compile(r"sandbox", re.IGNORECASE),
    ),
]

_POLICY_DRIFT_EXEMPT = re.compile(
    r"(archive|archived|MIGRATIONS-archive|history|과거|이전|incident|박제|supersede|supersedes|폐기|blanket ban을 유지하는 근거로 쓰지 않는다|rg -n)",
    re.IGNORECASE,
)

_POLICY_SCAN_GLOBS = [
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/skills/**/*.md",
    ".agents/skills/**/*.md",
    ".claude/rules/**/*.md",
    "docs/WIP/**/*.md",
]


def scan_policy_drift(paths: list[Path]) -> list[tuple[str, int, str, str]]:
    """현재 active 정책과 충돌하는 라이브 문구를 관측한다."""
    hits: list[tuple[str, int, str, str]] = []
    if paths:
        targets = [p for p in paths if p.is_file()]
    else:
        targets = [
            p
            for glob in _POLICY_SCAN_GLOBS
            for p in REPO_ROOT.glob(glob)
            if p.is_file()
        ]

    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _POLICY_DRIFT_EXEMPT.search(line):
                continue
            for label, pattern in _POLICY_DRIFT_PATTERNS:
                if not pattern.search(line):
                    continue
                if label == "sandbox without permission-ready":
                    if "완료 증거" not in line:
                        continue
                    if re.search(r"(permission-ready|권한|조건|않|아니다|아니|대체)", line):
                        continue
                hits.append((rel, lineno, label, line.strip()[:100]))
    return hits


def scan_dispatcher_drift() -> list[str]:
    """safe_command.py의 허용 명령과 AGENTS.md 안내 예시 drift를 관측한다."""
    script = REPO_ROOT / ".claude/scripts/safe_command.py"
    agents = REPO_ROOT / "AGENTS.md"
    if not script.exists() or not agents.exists():
        return ["safe_command.py 또는 AGENTS.md 없음"]

    text = script.read_text(encoding="utf-8", errors="replace")
    agents_text = agents.read_text(encoding="utf-8", errors="replace")
    allowed = set(re.findall(r'"([a-z][a-z0-9-]*)"', text.split("ALLOWED_COMMANDS", 1)[1].split("}", 1)[0]))
    documented = set(re.findall(r"safe_command\.py\s+([a-z][a-z0-9-]*)", agents_text))
    required_documented = {"status", "cps-list", "verify-relates", "eval-harness", "precheck"}

    drift: list[str] = []
    missing_doc = sorted(required_documented - documented)
    if missing_doc:
        drift.append(f"AGENTS.md 예시 누락: {', '.join(missing_doc)}")
    undocumented = sorted((documented & required_documented) - allowed)
    if undocumented:
        drift.append(f"AGENTS.md 예시가 dispatcher에 없음: {', '.join(undocumented)}")
    if "eval-harness" not in allowed:
        drift.append("dispatcher eval-harness 명령 누락")
    return drift


def section_policy_dispatcher_drift() -> None:
    """현재 정책과 dispatcher 안내 drift를 eval --harness에서 보고한다."""
    print("")
    print("## policy/dispatcher drift")
    policy_hits = scan_policy_drift([])
    dispatcher_hits = scan_dispatcher_drift()
    if not policy_hits:
        print("- policy drift 0건 ✅")
    else:
        print(f"- ⚠ policy drift {len(policy_hits)}건")
        for rel, lineno, label, snippet in policy_hits[:10]:
            print(f"  - {rel}:{lineno} | {label} | {snippet}")
        if len(policy_hits) > 10:
            print(f"  ... 외 {len(policy_hits) - 10}건")
    if not dispatcher_hits:
        print("- dispatcher drift 0건 ✅")
    else:
        print(f"- ⚠ dispatcher drift {len(dispatcher_hits)}건")
        for item in dispatcher_hits:
            print(f"  - {item}")


# ──────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("# eval --harness CLI 백엔드 보고")

    # 항목 5·7: CPS 무결성 + 피드백 리포트 (eval_cps_integrity.py 위임)
    cps_exit = run_cps_integrity()

    # 항목 6: 방어 활성 기록
    section_defense_record()

    # 항목 6.5: memory/reminder frontmatter lint
    section_reminder_frontmatter_lint()

    # 항목 8: 검증 도구 정렬 진단
    section_alignment_diagnostics()

    # 항목 8.5: 검증 도구 설치 가용성 관측
    section_tool_availability()

    # 항목 9: starter 본문 dead reference (P11 첫 누적 case 박제 후 추가)
    section_dead_reference()

    # 항목 9.5: 라이브 경로 문자열 계약 drift
    section_path_contract_lint()

    # 항목 10: 느슨한 결합 관측
    section_loose_coupling_observability()

    # 항목 11: 토큰 다이어트 관측
    section_token_diet_observability()

    # 항목 12: C 보강·회귀 루프 관측
    section_c_reinforcement_observability()

    # 항목 13: policy/dispatcher drift
    section_policy_dispatcher_drift()

    # cps_integrity가 차단 exit하면 본 백엔드도 차단
    return 2 if cps_exit == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
