"""cascade boundary 검증 (FR-002, P11 방어).

cascade되는 starter decision이 비-cascade 동료 decision을 relates-to로
가리키면 다운스트림에 영구 dead link 발생. 본 테스트는 두 메커니즘 검증:

1. **starter lint** (작성 시점 차단): docs_ops.py `cmd_verify_relates`가
   cascade boundary 위반을 발견하면 ERROR 카운트 증가
2. **cascade-time rewrite**: cascade_docs.py가 비-cascade target을 가리키는
   relates-to 항목을 frontmatter에서 제거 (projection drift, 의미 drift 아님)
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load(modname: str):
    spec = importlib.util.spec_from_file_location(
        modname, SCRIPTS_DIR / f"{modname}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "harness").mkdir(parents=True)
    (tmp_path / "docs" / "WIP").mkdir(parents=True)
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / ".claude" / "agents").mkdir(parents=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _decision(title: str, relates: list[tuple[str, str]] = None) -> str:
    """test용 decision frontmatter+빈본문."""
    fm = [
        "---",
        f"title: {title}",
        "domain: harness",
        "problem: [P11]",
        "s: [S11]",
        "status: completed",
        "created: 2026-05-17",
    ]
    if relates:
        fm.append("relates-to:")
        for path, rel in relates:
            fm.append(f"  - path: {path}")
            fm.append(f"    rel: {rel}")
    fm.append("---")
    fm.append("")
    fm.append(f"# {title}\n")
    return "\n".join(fm)


# ──────────────────────────────────────────────────────
# compute_cascade_set
# ──────────────────────────────────────────────────────

@pytest.mark.docs_ops
def test_compute_cascade_set_collects_rules_referenced_decisions(tmp_path, monkeypatch):
    """rules 본문에서 docs/decisions/*.md 패턴이 cascade set에 포함."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    # rule이 hn_alpha를 참조 → cascade. hn_beta는 미참조 → 비-cascade
    _write(
        tmp_path / ".claude" / "rules" / "test.md",
        "# rule\n\n참고: [hn_alpha](../../docs/decisions/hn_alpha.md)\n",
    )
    _write(tmp_path / "docs" / "decisions" / "hn_alpha.md", _decision("alpha"))
    _write(tmp_path / "docs" / "decisions" / "hn_beta.md", _decision("beta"))

    mod = _load("cascade_docs")
    cascade_set = mod.compute_cascade_set()

    assert "docs/decisions/hn_alpha.md" in cascade_set
    assert "docs/decisions/hn_beta.md" not in cascade_set


@pytest.mark.docs_ops
def test_compute_cascade_set_excludes_docs_harness(tmp_path, monkeypatch):
    """docs/harness/hn_*.md는 cascade set에서 제외 (v0.47.7 정책)."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    _write(
        tmp_path / ".claude" / "rules" / "test.md",
        "# rule\n\n참고: [retro](../../docs/harness/hn_retro.md)\n",
    )
    _write(tmp_path / "docs" / "harness" / "hn_retro.md", _decision("retro"))

    mod = _load("cascade_docs")
    cascade_set = mod.compute_cascade_set()

    assert "docs/harness/hn_retro.md" not in cascade_set


# ──────────────────────────────────────────────────────
# strip_non_cascading_relates
# ──────────────────────────────────────────────────────

@pytest.mark.docs_ops
def test_strip_removes_non_cascading_targets(tmp_path, monkeypatch):
    """cascade decision이 비-cascade를 가리키면 relates-to에서 제거."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "docs" / "decisions" / "hn_src.md"
    _write(
        src,
        _decision(
            "src",
            relates=[
                ("decisions/hn_in_cascade.md", "references"),
                ("decisions/hn_not_in_cascade.md", "caused-by"),
                ("harness/hn_retro.md", "extends"),
            ],
        ),
    )

    mod = _load("cascade_docs")
    cascade_set = {"docs/decisions/hn_in_cascade.md", "docs/decisions/hn_src.md"}

    rewritten = mod.rewrite_frontmatter_for_downstream(str(src), cascade_set)

    assert "hn_in_cascade.md" in rewritten
    assert "hn_not_in_cascade.md" not in rewritten
    assert "hn_retro.md" not in rewritten


@pytest.mark.docs_ops
def test_strip_keeps_non_decision_relates(tmp_path, monkeypatch):
    """cascade decision이 rules/skills/agents 가리키는 건 유지 (decisions만 검사)."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "docs" / "decisions" / "hn_src.md"
    _write(
        src,
        _decision(
            "src",
            relates=[
                (".claude/rules/some_rule.md", "references"),
                ("decisions/hn_not_in_cascade.md", "caused-by"),
            ],
        ),
    )

    mod = _load("cascade_docs")
    cascade_set = {"docs/decisions/hn_src.md"}

    rewritten = mod.rewrite_frontmatter_for_downstream(str(src), cascade_set)

    assert "some_rule.md" in rewritten
    assert "hn_not_in_cascade.md" not in rewritten


@pytest.mark.docs_ops
def test_strip_empty_relates_removes_key(tmp_path, monkeypatch):
    """모든 relates-to가 stripped되면 relates-to: 키 자체를 제거."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "docs" / "decisions" / "hn_src.md"
    _write(
        src,
        _decision(
            "src",
            relates=[("decisions/hn_not_in_cascade.md", "caused-by")],
        ),
    )

    mod = _load("cascade_docs")
    cascade_set = {"docs/decisions/hn_src.md"}

    rewritten = mod.rewrite_frontmatter_for_downstream(str(src), cascade_set)

    assert "relates-to:" not in rewritten


# ──────────────────────────────────────────────────────
# verify_relates lint integration
# ──────────────────────────────────────────────────────

@pytest.mark.docs_ops
def test_verify_relates_flags_cascade_boundary_violation(tmp_path, monkeypatch):
    """starter에서 cascade decision이 비-cascade 가리키면 추가 경고."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    # rule이 hn_src를 참조 (hn_src는 cascade)
    _write(
        tmp_path / ".claude" / "rules" / "test.md",
        "# rule\n\n[hn_src](../../docs/decisions/hn_src.md)\n",
    )
    # hn_src가 hn_isolated (비-cascade)를 caused-by로 가리킴
    # 단 hn_isolated는 starter에 존재 (verify-relates 일반 dead link 검사 통과용)
    _write(
        tmp_path / "docs" / "decisions" / "hn_src.md",
        _decision(
            "src",
            relates=[("decisions/hn_isolated.md", "caused-by")],
        ),
    )
    _write(tmp_path / "docs" / "decisions" / "hn_isolated.md", _decision("isolated"))

    # is_starter=true 환경
    monkeypatch.setenv("HARNESS_IS_STARTER", "true")

    mod = _load("docs_ops")
    # cmd_verify_relates는 print만 하므로 capsys로 stdout 캡처
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.cmd_verify_relates()
    output = buf.getvalue()

    # cascade boundary 위반은 일반 dead link와 별개로 경고/차단
    assert "cascade" in output.lower() or "boundary" in output.lower() or rc != 0
