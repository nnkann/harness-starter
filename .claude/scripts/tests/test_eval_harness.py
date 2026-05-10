"""eval_harness.py 회귀 가드.

검증 범위:
- 모듈 import 성공 (wip_util 의존성 정합)
- detect_typescript_signals: package.json 없으면 skip 반환
- measure_alignment: 빈 패키지 디렉토리에서 기본값 반환
- main 실행 시 exit 0 (starter는 TypeScript 없음 → 정렬 진단 SKIP 정상)
"""

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_eval_harness():
    spec = importlib.util.spec_from_file_location(
        "eval_harness", SCRIPTS_DIR / "eval_harness.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.eval
def test_module_imports():
    """eval_harness.py가 wip_util 포함 의존성을 정상 import."""
    mod = _load_eval_harness()
    assert hasattr(mod, "detect_typescript_signals")
    assert hasattr(mod, "measure_alignment")
    assert hasattr(mod, "section_alignment_diagnostics")
    assert hasattr(mod, "main")


@pytest.mark.eval
def test_signal_detection_no_package_json(tmp_path, monkeypatch):
    """package.json 없으면 skip 반환."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    result = mod.detect_typescript_signals()
    assert result["skipped"] is True
    assert "package.json" in result.get("reason", "")


@pytest.mark.eval
def test_signal_detection_basic_workspace(tmp_path, monkeypatch):
    """workspaces 필드 있으면 신호 A 검출."""
    mod = _load_eval_harness()
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "root", "workspaces": ["packages/*"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    result = mod.detect_typescript_signals()
    assert result["skipped"] is False
    # 워크스페이스 패키지 0개라 패키지 자체 신호는 없지만 root 신호 A는 hit
    assert "A" in result["signals"].get("<root>", [])


@pytest.mark.eval
def test_signal_detection_codegen_dependency(tmp_path, monkeypatch):
    """@supabase/supabase-js 의존성 있으면 신호 B 검출."""
    mod = _load_eval_harness()
    (tmp_path / "package.json").write_text(
        json.dumps({
            "name": "app",
            "dependencies": {"@supabase/supabase-js": "^2.0.0"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    result = mod.detect_typescript_signals()
    assert "B" in result["signals"].get("app", [])


@pytest.mark.eval
def test_alignment_metrics_empty(tmp_path):
    """tsconfig·exports·eslint 없으면 기본값 반환."""
    mod = _load_eval_harness()
    align = mod.measure_alignment(tmp_path)
    assert align["tsconfig_paths"] == "매핑 없음"
    assert align["exports"] == "미노출"
    assert align["eslint_resolver"] == "없음"


@pytest.mark.eval
def test_alignment_metrics_src_paths(tmp_path):
    """tsconfig paths가 src를 가리키면 'src 직접 매핑' 반환."""
    mod = _load_eval_harness()
    (tmp_path / "tsconfig.json").write_text(
        json.dumps({
            "compilerOptions": {
                "paths": {"@app/*": ["./src/*"]},
            }
        }),
        encoding="utf-8",
    )
    align = mod.measure_alignment(tmp_path)
    assert align["tsconfig_paths"] == "src 직접 매핑"


@pytest.mark.eval
def test_alignment_metrics_dist_paths(tmp_path):
    """tsconfig paths가 dist를 가리키면 'dist 매핑' 반환."""
    mod = _load_eval_harness()
    (tmp_path / "tsconfig.json").write_text(
        json.dumps({
            "compilerOptions": {
                "paths": {"@app/*": ["./dist/*"]},
            }
        }),
        encoding="utf-8",
    )
    align = mod.measure_alignment(tmp_path)
    assert align["tsconfig_paths"] == "dist 매핑"


def _load_eval_cps_integrity():
    spec = importlib.util.spec_from_file_location(
        "eval_cps_integrity", SCRIPTS_DIR / "eval_cps_integrity.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_log(tmp_path: Path, content: str) -> Path:
    docs_root = tmp_path / "docs"
    (docs_root / "harness").mkdir(parents=True)
    (docs_root / "harness" / "migration-log.md").write_text(content, encoding="utf-8")
    return docs_root


@pytest.mark.eval
def test_feedback_reports_top_level_section(tmp_path):
    """## Feedback Reports (top-level) 양식 — 기존 형식 회귀 가드."""
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.0 → v0.42.1 (2026-05-10)

### 충돌
- merge 1건

## Feedback Reports

### FR-001 (2026-05-10)

**관점**: top-level 양식 검증.
**약점**: 없음.
**실천**: 회귀 가드.
**심각도**: low
""")
    result = mod.check_feedback_reports(docs_root)
    assert result == ["FR-001 ✅"]


@pytest.mark.eval
def test_feedback_reports_subheader_in_version_section(tmp_path):
    """### Feedback Reports (버전 섹션 내 서브헤더) 양식 — v0.42.3 보강 대상.

    다운스트림 양식: 각 버전 섹션 안에 ### Feedback Reports + #### FR-NNN.
    구버전 코드는 top-level만 잡아 미인식 → "없음 ✅" 오출력했던 결함.
    """
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.0 → v0.42.1 (2026-05-10)

### 충돌
- merge 1건

### Feedback Reports

#### FR-005 (2026-05-10)

**관점**: 측정.
**약점**: 발화 0건.
**실천**: negative-test 권고.
**심각도**: low

#### FR-006 (2026-05-10)

**관점**: 정합성 검증.
**약점**: 미도달 29건.
**실천**: rules 디렉토리 확장.
**심각도**: low
""")
    result = mod.check_feedback_reports(docs_root)
    assert "FR-005 ✅" in result
    assert "FR-006 ✅" in result
    assert len(result) == 2


@pytest.mark.eval
def test_feedback_reports_missing_field_warning(tmp_path):
    """FR 항목에 필수 필드 누락 시 경고 메시지 반환."""
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.0 → v0.42.1 (2026-05-10)

### Feedback Reports

#### FR-007 (2026-05-10)

**관점**: 누락 검증.
**약점**: 실천·심각도 없음.
""")
    result = mod.check_feedback_reports(docs_root)
    assert len(result) == 1
    assert result[0].startswith("⚠️ FR-007:")
    assert "**실천**" in result[0]
    assert "**심각도**" in result[0]


@pytest.mark.eval
def test_feedback_reports_no_log_file_returns_none(tmp_path):
    """migration-log.md 없으면 None 반환 (다운스트림 전용 파일 skip)."""
    mod = _load_eval_cps_integrity()
    docs_root = tmp_path / "docs"
    (docs_root / "harness").mkdir(parents=True)
    result = mod.check_feedback_reports(docs_root)
    assert result is None
