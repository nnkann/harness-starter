#!/usr/bin/env python3
"""eval --harness CLI 백엔드 단일 진입점.

SKILL.md 본문이 LLM 해석에 의존하던 결정적 측정 항목을 스크립트로 이전.
LLM 해석 영역(모호성·모순·부패·강제력 배치)은 SKILL.md에 잔존.

본 백엔드 책임:
1. CPS 무결성 (eval_cps_integrity.py 호출 — 항목 5)
2. 방어 활성 기록 (signal_defense_success.md — 항목 6)
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
import subprocess
import sys
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
    r"(폐기|흡수|삭제|removed|deprecated|MIGRATIONS|변경 이력|회고)"
)

# 스캔 대상 — starter 본문 (rules·skills·agents·README)
_DEAD_REF_SCAN_GLOBS = [
    ".claude/skills/**/*.md",
    ".claude/agents/**/*.md",
    ".claude/rules/**/*.md",
    "README.md",
]


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


def section_defense_record() -> None:
    """signal_defense_success.md 존재·최근 기록 보고."""
    print("")
    print("## 방어 활성 기록")
    sig = REPO_ROOT / ".claude/memory/signal_defense_success.md"
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
            fm = {}
            try:
                fm = parse_wip_file(path).frontmatter
            except Exception:
                fm = {}
            has_c = bool(str(fm.get("c", "")).strip())
            has_rationale = (
                "## CPS Rationale" in text
                and "C → P" in text
                and "P → S" in text
                and "S → AC" in text
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
# main
# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("# eval --harness CLI 백엔드 보고")

    # 항목 5·7: CPS 무결성 + 피드백 리포트 (eval_cps_integrity.py 위임)
    cps_exit = run_cps_integrity()

    # 항목 6: 방어 활성 기록
    section_defense_record()

    # 항목 8: 검증 도구 정렬 진단
    section_alignment_diagnostics()

    # 항목 9: starter 본문 dead reference (P11 첫 누적 case 박제 후 추가)
    section_dead_reference()

    # 항목 10: 느슨한 결합 관측
    section_loose_coupling_observability()

    # 항목 11: 토큰 다이어트 관측
    section_token_diet_observability()

    # 항목 12: C 보강·회귀 루프 관측
    section_c_reinforcement_observability()

    # cps_integrity가 차단 exit하면 본 백엔드도 차단
    return 2 if cps_exit == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
