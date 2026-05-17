#!/usr/bin/env python3
"""cascade boundary helper — projection-safe frontmatter rewriter.

starter `docs/decisions/hn_*.md`는 rules·skills·agents·CLAUDE.md·README.md
본문에서 grep으로 참조되는 것만 다운스트림에 cascade된다 (v0.47.7 정책).

cascade되는 decision이 `relates-to`로 비-cascade target(다른 decision 또는
`docs/harness/`)을 가리키면 다운스트림에 영구 dead link 발생 (FR-002).

이 helper는 두 역할:
1. **compute_cascade_set()**: 현재 cascade되는 decisions 경로 집합 계산
2. **rewrite_frontmatter_for_downstream()**: 비-cascade target을 가리키는
   relates-to 항목을 frontmatter에서 제거 (의미 drift X, projection drift O)

projection drift 정당화: upstream 그래프는 전체 진실, downstream은 cascade
정책에 맞춘 부분 그래프. 투영 밖 노드로 향하는 edge는 downstream에서 무의미.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path.cwd().resolve()


def _import_docs_ops():
    """`_resolve_relates_path` SSOT를 docs_ops에서 동적 로드.

    cascade_docs는 helper script로 docs_ops와 같은 디렉토리에 산다.
    SSOT 단일화: 본 모듈은 자체 정의 안 함 — 본문 복제 금지 원칙(rules/docs.md).
    """
    spec = importlib.util.spec_from_file_location(
        "docs_ops", Path(__file__).parent / "docs_ops.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_docs_ops = _import_docs_ops()
_resolve_relates_path_ssot = _docs_ops._resolve_relates_path

# cascade 정책 SSOT — harness-upgrade SKILL.md Step 3과 정합
SCAN_ROOTS = (
    Path(".claude/rules"),
    Path(".claude/skills"),
    Path(".claude/agents"),
)
SCAN_FILES = (Path("CLAUDE.md"), Path("README.md"))

# rules 본문에서 docs/decisions/*.md 패턴 추출
REFERENCED_PATTERN = re.compile(r"docs/(?:guides|decisions)/[a-z0-9_-]+\.md")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def compute_cascade_set() -> set[str]:
    """현재 cascade되는 decisions 경로 집합.

    rules·skills·agents·CLAUDE.md·README.md 본문에서 `docs/decisions/*.md`
    패턴을 grep으로 추출. 실제 존재 파일만 포함 (오탐 방어).

    Returns: repo-root 기준 경로 문자열 set ("docs/decisions/hn_x.md" 형식).
    """
    referenced: set[str] = set()

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            for m in REFERENCED_PATTERN.findall(_read(md)):
                if Path(m).exists():
                    referenced.add(m)

    for f in SCAN_FILES:
        if f.exists():
            for m in REFERENCED_PATTERN.findall(_read(f)):
                if Path(m).exists():
                    referenced.add(m)

    return referenced


def find_rule_referenced_decisions() -> set[str]:
    """compute_cascade_set의 별칭 (의도 명확화용 — rules 본문 grep)."""
    return compute_cascade_set()


def _resolve_relates_path(source_path: str, rel_path: str) -> str:
    """relates-to.path 해석 — docs_ops SSOT 위임.

    절대경로 source(테스트 환경 tmp_path) 호환을 위해 docs/ 하위 정규화만
    추가하고, 본 해석 로직은 docs_ops._resolve_relates_path 단일 정의 사용.
    """
    src_norm = source_path.replace("\\", "/")
    # 절대경로 + /docs/ 포함 → 상대경로 정규화 후 SSOT에 위임
    if not src_norm.startswith(("docs/", ".claude/")) and "/docs/" in src_norm:
        idx = src_norm.find("/docs/") + 1
        src_norm = src_norm[idx:]
    return _resolve_relates_path_ssot(Path(src_norm), rel_path)


def _is_decisions_target(resolved: str) -> bool:
    """resolved 경로가 cascade 정책상 다운스트림 미전파 영역인지.

    검사 대상: docs/decisions/, docs/harness/, docs/archived/
    - decisions: rules 본문 grep으로 결정되는 동적 cascade (일부만)
    - harness: starter 내부 회고, never cascade (v0.47.7)
    - archived: starter 보존용, never cascade
    """
    norm = resolved.replace("\\", "/")
    return (
        norm.startswith("docs/decisions/")
        or norm.startswith("docs/harness/")
        or norm.startswith("docs/archived/")
    )


def strip_non_cascading_relates(
    frontmatter_text: str, source_path: str, cascade_set: set[str]
) -> tuple[str, int]:
    """frontmatter 텍스트에서 비-cascade target relates-to 항목 제거.

    Args:
        frontmatter_text: '---' 사이 본문 (앞뒤 '---' 제외)
        source_path: 본 파일의 repo-root 기준 경로 (상대경로 해석용)
        cascade_set: 현재 cascade되는 decisions 경로 set

    Returns:
        (rewritten_text, stripped_count)
    """
    lines = frontmatter_text.splitlines()
    out: list[str] = []
    stripped = 0
    in_relates = False
    relates_indent = 0
    pending_entry: list[str] = []
    relates_kept_any = False
    relates_header_idx = -1

    def _flush_pending(keep: bool) -> None:
        """pending entry를 out에 keep 여부에 따라 합류."""
        nonlocal stripped, relates_kept_any
        if not pending_entry:
            return
        if keep:
            out.extend(pending_entry)
            relates_kept_any = True
        else:
            stripped += 1
        pending_entry.clear()

    def _entry_target(entry_lines: list[str]) -> str:
        """entry 라인들에서 path: 값 추출."""
        for ln in entry_lines:
            m = re.match(r"\s*-?\s*path:\s*(.+?)\s*$", ln)
            if m:
                return m.group(1).strip().strip("'\"")
        return ""

    def _entry_targets_decisions_or_harness(entry_lines: list[str]) -> bool:
        target = _entry_target(entry_lines)
        if not target:
            return False
        resolved = _resolve_relates_path(source_path, target)
        return _is_decisions_target(resolved)

    def _entry_in_cascade(entry_lines: list[str]) -> bool:
        target = _entry_target(entry_lines)
        resolved = _resolve_relates_path(source_path, target)
        return resolved in cascade_set

    for line in lines:
        if not in_relates:
            if re.match(r"^relates-to:\s*$", line):
                in_relates = True
                relates_indent = len(line) - len(line.lstrip())
                relates_header_idx = len(out)
                out.append(line)
                continue
            out.append(line)
            continue

        # in_relates 영역
        stripped_line = line.rstrip()
        if not stripped_line:
            # 빈 줄 — entry 종결
            _flush_pending(
                not _entry_targets_decisions_or_harness(pending_entry)
                or _entry_in_cascade(pending_entry)
            )
            out.append(line)
            continue

        current_indent = len(line) - len(line.lstrip())

        # relates-to 블록 밖으로 나감 (들여쓰기 회귀)
        if current_indent <= relates_indent and not re.match(r"^\s*-\s", line):
            _flush_pending(
                not _entry_targets_decisions_or_harness(pending_entry)
                or _entry_in_cascade(pending_entry)
            )
            in_relates = False
            out.append(line)
            continue

        # 새 entry 시작 (- path: ...)
        if re.match(r"^\s*-\s+path:", line):
            # 이전 entry flush
            _flush_pending(
                not _entry_targets_decisions_or_harness(pending_entry)
                or _entry_in_cascade(pending_entry)
            )
            pending_entry = [line]
            continue

        # entry 계속 (rel: 등)
        if pending_entry:
            pending_entry.append(line)
            continue

        out.append(line)

    # 파일 끝에서 남은 pending 처리
    _flush_pending(
        not _entry_targets_decisions_or_harness(pending_entry)
        or _entry_in_cascade(pending_entry)
    )

    # relates-to 블록이 비었으면 header 자체 제거
    if relates_header_idx >= 0 and not relates_kept_any:
        # 헤더 라인 + 뒤따르던 빈 줄 1개까지 제거 (자연스러운 정리)
        del out[relates_header_idx]
        if relates_header_idx < len(out) and out[relates_header_idx].strip() == "":
            del out[relates_header_idx]

    return "\n".join(out), stripped


def rewrite_frontmatter_for_downstream(
    file_path: str, cascade_set: set[str]
) -> str:
    """단일 파일의 frontmatter rewrite 후 전체 내용 반환.

    파일 자체는 변경하지 않음 (호출자가 결과 문자열을 처리 — 다운스트림
    artifact 생성 또는 dry-run 검증).
    """
    text = _read(Path(file_path))
    if not text.startswith("---"):
        return text

    end = text.find("\n---", 3)
    if end < 0:
        return text

    fm_text = text[3:end].lstrip("\n")
    body = text[end + 4 :]  # "\n---" 다음

    new_fm, _ = strip_non_cascading_relates(fm_text, file_path, cascade_set)
    return f"---\n{new_fm}\n---{body}"


def check_cascade_boundary_violations() -> list[tuple[str, str, str]]:
    """cascade decisions의 비-cascade target relates-to를 전수 감사.

    Returns: [(source_path, target_resolved, rel), ...]
    """
    cascade_set = compute_cascade_set()
    violations: list[tuple[str, str, str]] = []

    for src in sorted(cascade_set):
        if not src.startswith("docs/decisions/"):
            continue
        text = _read(Path(src))
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end < 0:
            continue
        fm_text = text[3:end]

        # relates-to 영역 파싱 (단순 line-by-line, _strip 로직과 동일 규칙)
        in_relates = False
        pending: list[str] = []

        def _check(entry_lines: list[str]) -> None:
            target = ""
            rel = ""
            for ln in entry_lines:
                m = re.match(r"\s*-?\s*path:\s*(.+?)\s*$", ln)
                if m:
                    target = m.group(1).strip().strip("'\"")
                m = re.match(r"\s*rel:\s*(.+?)\s*$", ln)
                if m:
                    rel = m.group(1).strip().strip("'\"")
            if not target:
                return
            resolved = _resolve_relates_path(src, target)
            if _is_decisions_target(resolved) and resolved not in cascade_set:
                violations.append((src, resolved, rel))

        for line in fm_text.splitlines():
            if re.match(r"^relates-to:\s*$", line):
                in_relates = True
                continue
            if not in_relates:
                continue
            if re.match(r"^[a-zA-Z_-]+:", line):
                # 다른 top-level key — relates-to 종결
                _check(pending)
                pending = []
                in_relates = False
                continue
            if re.match(r"^\s*-\s+path:", line):
                _check(pending)
                pending = [line]
                continue
            if pending:
                pending.append(line)

        _check(pending)

    return violations


# ──────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────

def _cmd_check() -> int:
    """starter 측 lint — cascade boundary 위반 보고."""
    violations = check_cascade_boundary_violations()
    if not violations:
        print("✅ cascade boundary 정합: 위반 0건")
        return 0
    for src, target, rel in violations:
        print(
            f"❌ {src}: relates-to '{target}' (rel: {rel}) → 비-cascade target. "
            f"다운스트림 dead link 발생"
        )
    print(f"\n결과: cascade boundary 위반 {len(violations)} 건")
    print("대응: rel을 'references'로 격하 후 본문 인용 또는 frontmatter 항목 제거")
    return 1


def _cmd_rewrite(paths: list[str], dry_run: bool = False) -> int:
    """파일들의 frontmatter rewrite (다운스트림 artifact 생성용)."""
    cascade_set = compute_cascade_set()
    total_stripped = 0
    for p in paths:
        if not Path(p).exists():
            print(f"⚠️  {p}: 파일 없음", file=sys.stderr)
            continue
        original = _read(Path(p))
        rewritten = rewrite_frontmatter_for_downstream(p, cascade_set)
        if original == rewritten:
            continue
        # stripped 카운트 계산 (frontmatter만 비교)
        if dry_run:
            print(f"[dry-run] {p}: frontmatter rewrite 예정")
        else:
            Path(p).write_text(rewritten, encoding="utf-8")
            print(f"✓ {p}: frontmatter rewritten")
        total_stripped += 1
    print(f"\nrewritten: {total_stripped} 파일")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  cascade_docs.py check                 # starter lint (boundary 위반 보고)\n"
            "  cascade_docs.py rewrite <path>...     # 파일 frontmatter rewrite\n"
            "  cascade_docs.py rewrite --dry-run <path>...  # dry-run"
        )
        return 0
    cmd = argv[0]
    if cmd == "check":
        return _cmd_check()
    if cmd == "rewrite":
        rest = argv[1:]
        dry = False
        if rest and rest[0] == "--dry-run":
            dry = True
            rest = rest[1:]
        return _cmd_rewrite(rest, dry_run=dry)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
