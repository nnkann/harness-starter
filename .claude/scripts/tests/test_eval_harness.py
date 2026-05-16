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


@pytest.mark.eval
def test_feedback_reports_inline_header_severity(tmp_path):
    """v0.42.4 — 헤더 인라인 `(심각도: medium ...)` 양식 검출 (FR-007 응답).

    다운스트림 양식: `#### FR-NNN ... (심각도: medium — ...)` 헤더 인라인 +
    본문에 별도 `**심각도**:` 라인 없음. v0.42.3까지는 substring 검사라
    `**심각도**` 마커 부재 시 6건 오경보 발생.
    """
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.0 → v0.42.1 (2026-05-10)

### Feedback Reports

#### FR-007 (2026-05-10) — 헤더 인라인 양식 (심각도: medium — 부분 효과)

**관점**: 헤더 인라인 검증.
**약점**: 본문 별도 심각도 라인 없음.
**실천**: 양면 매칭 보강.
""")
    result = mod.check_feedback_reports(docs_root)
    assert result == ["FR-007 ✅"]


@pytest.mark.eval
def test_feedback_reports_bold_inner_paren(tmp_path):
    """v0.42.6 — bold 마커 내부 괄호 보강어 양식 검출 (FR-010 응답).

    다운스트림 실측 양식: `**약점 (부분 작동)**:` — 필드명 뒤에 괄호로
    보강 설명을 붙이는 자연스러운 변형. v0.42.4까지는 bold 정규식이
    `**X**:`로 좁아 미매칭 → 약점·실천·심각도 1건 누락 오경보 발생.
    """
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.5 → v0.42.6 (2026-05-11)

### Feedback Reports

#### FR-010 (2026-05-11)

**관점 (다운스트림 검증)**: 양식 자율성 검증.
**약점 (부분 작동)**: bold 내부 괄호 보강어 미인식.
**실천 (정규식 보강)**: 필드명 뒤 선택적 괄호 그룹 허용.
**심각도 (medium)**: 양식 갭으로 오경보 누적.
""")
    result = mod.check_feedback_reports(docs_root)
    assert result == ["FR-010 ✅"]


@pytest.mark.eval
def test_feedback_reports_bold_inner_paren_does_not_match_prose(tmp_path):
    """false-positive 가드 — 단순 산문 표현은 여전히 미매칭."""
    mod = _load_eval_cps_integrity()
    docs_root = _write_log(tmp_path, """# migration-log

## v0.42.5 → v0.42.6 (2026-05-11)

### Feedback Reports

#### FR-011 (2026-05-11)

이 FR은 약점에 대해 설명만 하고 필드 마커는 없다.
관점이라는 단어가 산문에 들어가 있어도 필드로 인식되면 안 된다.
""")
    result = mod.check_feedback_reports(docs_root)
    # 필드 마커 없음 → 4개 필드 모두 missing
    assert len(result) == 1
    assert result[0].startswith("⚠️ FR-011:")
    for field in ["관점", "약점", "실천", "심각도"]:
        assert field in result[0]


# ────────────────────────────────────────────────────────────────────────
# 항목 9 — section_dead_reference (P11 첫 누적 case)
# ────────────────────────────────────────────────────────────────────────


@pytest.mark.eval
def test_dead_reference_function_exists():
    """section_dead_reference 함수가 노출돼야 한다."""
    mod = _load_eval_harness()
    assert hasattr(mod, "section_dead_reference")
    assert hasattr(mod, "_DEAD_REF_PATTERNS")
    assert hasattr(mod, "_DEAD_REF_EXEMPT")


@pytest.mark.eval
def test_dead_reference_exempt_matches_archive_phrases():
    """폐기·흡수·삭제 박제 표현은 면제 정규식으로 통과해야 한다."""
    mod = _load_eval_harness()
    exempt = mod._DEAD_REF_EXEMPT
    assert exempt.search("orchestrator.py 696줄 전면 삭제")
    assert exempt.search("doc-health 흡수")
    assert exempt.search("check-existing 스킬 폐기")
    assert exempt.search("MIGRATIONS.md v0.47.7 (deprecated)")
    # 일반 라인은 면제 X
    assert not exempt.search(".claude/rules/anti-defer.md")


@pytest.mark.eval
def test_dead_reference_patterns_cover_known_deprecations():
    """v0.47.x 폐기 파일이 검출 패턴에 모두 등재돼야 한다."""
    mod = _load_eval_harness()
    expected = {
        "anti-defer.md", "bug-interrupt.md", "external-experts.md",
        "pipeline-design.md", "rules/staging.md", "orchestrator.py",
        "debug-guard.sh", "check-existing/", "doc-health/",
    }
    actual = set(mod._DEAD_REF_PATTERNS)
    assert expected.issubset(actual), f"누락 패턴: {expected - actual}"


# ────────────────────────────────────────────────────────────────────────
# scan_dead_reference_paths — pre-check 게이트 재사용 함수 (v0.47.10)
# ────────────────────────────────────────────────────────────────────────


@pytest.mark.eval
def test_scan_dead_reference_paths_detects(tmp_path):
    """scan_dead_reference_paths가 staged 경로 리스트만 받아 hit 반환."""
    mod = _load_eval_harness()
    f = tmp_path / "fake.md"
    f.write_text("docs reference .claude/rules/anti-defer.md here\n", encoding="utf-8")
    hits = mod.scan_dead_reference_paths([f])
    assert len(hits) == 1
    assert hits[0][2] == "anti-defer.md"


@pytest.mark.eval
def test_scan_dead_reference_paths_exempts_archive_phrase(tmp_path):
    """박제 표현(폐기·흡수·삭제) 동반 라인은 면제 — 검출 0건."""
    mod = _load_eval_harness()
    f = tmp_path / "fake.md"
    f.write_text("anti-defer.md 폐기 (v0.47.1)\n", encoding="utf-8")
    hits = mod.scan_dead_reference_paths([f])
    assert hits == []


@pytest.mark.eval
def test_scan_dead_reference_paths_empty_full_scan(tmp_path):
    """빈 list 전달 시 REPO_ROOT 전체 글롭 스캔 (eval --harness 동작)."""
    mod = _load_eval_harness()
    # 현 starter 상태는 dead ref 0건 (v0.47.9 정비 후)
    hits = mod.scan_dead_reference_paths([])
    # archived/ 같은 경로는 _DEAD_REF_SCAN_GLOBS 밖이라 면제
    # 박제 표현 면제 적용 후 0건
    assert hits == [] or all("폐기" not in h[3] for h in hits)


# ────────────────────────────────────────────────────────────────────────
# eval_cps_integrity P10/P11 카운트 회귀 (v0.47.10 §C)
# ────────────────────────────────────────────────────────────────────────


def _load_eval_cps_integrity():
    spec = importlib.util.spec_from_file_location(
        "eval_cps_integrity", SCRIPTS_DIR / "eval_cps_integrity.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.eval
def test_cps_problem_regex_matches_two_digit():
    """CPS_REF_PATTERNS 정규식이 P10·P11 두자리수 P# 캡처해야 한다."""
    mod = _load_eval_cps_integrity()
    body = "P11 → S11 cascade. P10 충족 보고. P11 연관."
    refs = mod.detect_cps_problem_refs(body)
    assert "P10" in refs
    assert "P11" in refs


@pytest.mark.eval
def test_cps_frontmatter_list_format_parsed(tmp_path):
    """frontmatter problem: [P7, P11] list 형식이 카운트에 잡혀야 한다."""
    mod = _load_eval_cps_integrity()
    doc = tmp_path / "fake.md"
    doc.write_text(
        "---\ntitle: fake\nproblem: [P7, P11]\n---\n\nbody\n",
        encoding="utf-8",
    )
    refs: dict = {}
    mod.scan_doc(doc, "P11 — 동형 패턴", refs)
    assert refs.get("P7") == 1
    assert refs.get("P11") == 1
