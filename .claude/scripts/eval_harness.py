#!/usr/bin/env python3
"""eval --harness CLI 백엔드 단일 진입점.

SKILL.md 본문이 LLM 해석에 의존하던 결정적 측정 항목을 스크립트로 이전.
LLM 해석 영역(모호성·모순·부패·강제력 배치)은 SKILL.md에 잔존.

본 백엔드 책임:
1. CPS 무결성 (eval_cps_integrity.py 호출 — 항목 5)
2. 방어 활성 기록 (signal_defense_success.md — 항목 6)
3. 피드백 리포트 (eval_cps_integrity가 처리 — 항목 7)
4. 검증 도구 정렬 진단 (LSP/lint/tsc 산출물 vs src — 항목 8 신규)

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

    # cps_integrity가 차단 exit하면 본 백엔드도 차단
    return 2 if cps_exit == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
