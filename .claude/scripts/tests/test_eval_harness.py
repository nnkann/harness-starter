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
def test_cps_case_catalog_reports_undefined_retired_refs(tmp_path):
    """case frontmatter가 현행 CPS에 없는 P/S를 가리키면 학습 drift로 보고한다."""
    mod = _load_eval_cps_integrity()
    docs_root = tmp_path / "docs"
    cases = docs_root / "cps"
    cases.mkdir(parents=True)
    (cases / "cp_retired_p12.md").write_text(
        "---\n"
        "title: retired case\n"
        "domain: cps\n"
        "p: [P12]\n"
        "s: [S12]\n"
        "status: completed\n"
        "created: 2026-05-18\n"
        "---\n",
        encoding="utf-8",
    )

    report = mod.analyze_cps_case_catalog(docs_root, ["P11"], ["S11"])

    assert report["case_count"] == 1
    assert report["undefined_problem_refs"] == ["docs/cps/cp_retired_p12.md:P12"]
    assert report["undefined_solution_refs"] == ["docs/cps/cp_retired_p12.md:S12"]
    assert report["no_case_problems"] == ["P11"]


@pytest.mark.eval
def test_cps_case_catalog_quantifies_learning_signals(tmp_path):
    """case coverage·반복 Problem·P10·다중 P case를 정량화한다."""
    mod = _load_eval_cps_integrity()
    docs_root = tmp_path / "docs"
    cases = docs_root / "cps"
    cases.mkdir(parents=True)
    (cases / "cp_a.md").write_text(
        "---\np: [P1, P2]\ns: [S1]\n---\n",
        encoding="utf-8",
    )
    (cases / "cp_b.md").write_text(
        "---\np: [P2]\ns: [S2]\n---\n",
        encoding="utf-8",
    )
    (cases / "cp_catch_all.md").write_text(
        "---\np: [P10]\ns: [S10]\n---\n",
        encoding="utf-8",
    )

    report = mod.analyze_cps_case_catalog(
        docs_root,
        ["P1", "P2", "P10", "P11"],
        ["S1", "S2", "S10", "S11"],
    )

    assert report["case_count"] == 3
    assert report["case_covered_problems"] == ["P1", "P2", "P10"]
    assert report["no_case_problems"] == ["P11"]
    assert report["recurring_problem_cases"] == {"P2": 2}
    assert report["multi_problem_cases"] == ["docs/cps/cp_a.md"]
    assert report["p10_cases"] == ["docs/cps/cp_catch_all.md"]


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


@pytest.mark.eval
def test_reminder_frontmatter_lint_reports_kv_group_and_stale_candidates(
    tmp_path, monkeypatch
):
    """eval --harness가 reminder 보강 후보를 warning/report로 분류한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    mem = tmp_path / ".claude" / "memory"
    mem.mkdir(parents=True)
    reminders = mem / "reminders"
    reminders.mkdir()
    (reminders / "reminder_missing.md").write_text(
        "---\n"
        "reminder: 신규 reminder는 kv_group 보강 후보\n"
        "domain: harness\n"
        "strength: weak\n"
        "candidate_p: P8\n"
        "status: active\n"
        "---\n",
        encoding="utf-8",
    )
    (reminders / "reminder_stale.md").write_text(
        "---\n"
        "reminder: stale 후보\n"
        "domain: harness\n"
        "strength: strong\n"
        "candidate_p: P8\n"
        "kv_group: harness/P9/stale-memory\n"
        "status: active\n"
        "valid_until: 2000-01-01\n"
        "---\n",
        encoding="utf-8",
    )
    (mem / "signal_legacy.md").write_text(
        "---\n"
        "signal: legacy alias\n"
        "domain: harness\n"
        "strength: weak\n"
        "candidate_p: P8\n"
        "---\n",
        encoding="utf-8",
    )

    report = mod.analyze_reminder_frontmatter()

    assert report["missing_kv_group"] == ["reminder_missing.md"]
    assert report["candidate_mismatch"] == [
        "reminder_stale.md: candidate_p=P8, kv_group=harness/P9/stale-memory"
    ]
    assert report["stale_candidates"] == [
        "reminder_stale.md: valid_until=2000-01-01"
    ]
    assert report["legacy_signals"] == ["signal_legacy.md"]


@pytest.mark.eval
def test_reminder_frontmatter_lint_detects_group_shape(tmp_path, monkeypatch):
    """과대/과소/형식 오류 group은 eval 보고 대상이다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    mem = tmp_path / ".claude" / "memory"
    mem.mkdir(parents=True)
    reminders = mem / "reminders"
    reminders.mkdir()
    (reminders / "reminder_broad.md").write_text(
        "---\nreminder: broad\ndomain: harness\ncandidate_p: P8\n"
        "kv_group: harness/P8\nstatus: active\n---\n",
        encoding="utf-8",
    )
    (reminders / "reminder_split.md").write_text(
        "---\nreminder: split\ndomain: harness\ncandidate_p: P8\n"
        "kv_group: harness/P8/review/commit\nstatus: active\n---\n",
        encoding="utf-8",
    )

    report = mod.analyze_reminder_frontmatter()

    assert report["overbroad_kv_group"] == ["reminder_broad.md: harness/P8"]
    assert report["oversplit_kv_group"] == [
        "reminder_split.md: harness/P8/review/commit"
    ]
    assert "reminder_broad.md: harness/P8" in report["invalid_kv_group"]
    assert "reminder_split.md: harness/P8/review/commit" in report["invalid_kv_group"]


@pytest.mark.eval
def test_reminder_promotion_candidates_detect_heavy_and_strong_user_items(
    tmp_path, monkeypatch
):
    """무거운/강한 reminder는 관련 WIP 흡수 또는 정식 WIP 승격 후보로 보고한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    mem = tmp_path / ".claude" / "memory"
    mem.mkdir(parents=True)
    reminders = mem / "reminders"
    reminders.mkdir()
    heavy_body = "\n".join(f"- detail {i}" for i in range(36))
    (reminders / "reminder_heavy.md").write_text(
        "---\n"
        "reminder: 너무 긴 reminder\n"
        "domain: harness\n"
        "strength: medium\n"
        "candidate_p: P8\n"
        "kv_group: harness/P8/session-start\n"
        "status: active\n"
        "source: docs/decisions/x.md\n"
        "---\n\n"
        f"{heavy_body}\n",
        encoding="utf-8",
    )
    (reminders / "reminder_strong_user.md").write_text(
        "---\n"
        "reminder: strong user reminder\n"
        "domain: harness\n"
        "strength: strong\n"
        "candidate_p: P8\n"
        "kv_group: harness/P8/review-commit\n"
        "status: active\n"
        "source: user\n"
        "---\n",
        encoding="utf-8",
    )

    candidates = mod.analyze_reminder_promotion_candidates()

    assert any("reminder_heavy.md: 본문" in item for item in candidates)
    assert (
        "reminder_strong_user.md: strong + source=user — SSOT owner 필요"
        in candidates
    )


@pytest.mark.eval
def test_reminder_promotion_candidates_detect_dense_group(tmp_path, monkeypatch):
    """같은 kv_group active reminder 과밀은 관련 WIP 흡수/병합/승격 후보."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    mem = tmp_path / ".claude" / "memory"
    mem.mkdir(parents=True)
    reminders = mem / "reminders"
    reminders.mkdir()
    for idx in range(4):
        (reminders / f"reminder_dense_{idx}.md").write_text(
            "---\n"
            f"reminder: dense {idx}\n"
            "domain: harness\n"
            "strength: weak\n"
            "candidate_p: P8\n"
            "kv_group: harness/P8/review-commit\n"
            "status: active\n"
            "source: docs/decisions/x.md\n"
            "---\n",
            encoding="utf-8",
        )

    candidates = mod.analyze_reminder_promotion_candidates()

    assert candidates == [
        "harness/P8/review-commit: active reminder 4건 — 관련 WIP 흡수·병합 또는 WIP 승격 후보"
    ]


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


@pytest.mark.eval
def test_scan_path_contracts_detects_missing_live_path(tmp_path, monkeypatch):
    """라이브 안내의 현재 없는 하네스 경로를 검출한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    f = tmp_path / "README.md"
    f.write_text("hook은 .claude/scripts/session-start.sh 를 호출한다\n", encoding="utf-8")

    hits = mod.scan_path_contracts([f])

    assert len(hits) == 1
    assert hits[0][2] == ".claude/scripts/session-start.sh"


@pytest.mark.eval
def test_scan_path_contracts_exempts_archive_file(tmp_path, monkeypatch):
    """MIGRATIONS archive는 박제 영역이라 path contract lint 대상이 아니다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    f = tmp_path / "docs" / "harness" / "MIGRATIONS-archive.md"
    f.parent.mkdir(parents=True)
    f.write_text("old hook .claude/scripts/session-start.sh\n", encoding="utf-8")

    assert mod.scan_path_contracts([f]) == []


@pytest.mark.eval
def test_scan_path_contracts_accepts_existing_path(tmp_path, monkeypatch):
    """존재하는 하네스 경로는 drift로 보지 않는다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    target = tmp_path / ".claude" / "scripts" / "session-start.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('ok')\n", encoding="utf-8")
    f = tmp_path / "CLAUDE.md"
    f.write_text("hook은 .claude/scripts/session-start.py 를 호출한다\n", encoding="utf-8")

    assert mod.scan_path_contracts([f]) == []


@pytest.mark.eval
def test_loose_coupling_observability_contracts_clean():
    """eval --harness가 스킬 라우팅·WIP 파일명 drift를 주기 관찰한다."""
    mod = _load_eval_harness()
    assert mod.observe_loose_coupling_contracts() == []


@pytest.mark.eval
def test_token_diet_observability_reports_repeated_work_candidates():
    """eval --harness가 반복 스캔·batch 처리 상태를 토큰 다이어트 관점으로 보고한다."""
    mod = _load_eval_harness()
    report = mod.observe_token_diet()
    assert report["eval_cps_docs_rglob_passes"] == 1
    assert report["docs_ops_wip_glob_passes"] == 1
    assert report["candidates"] == []
    assert any("cluster-update" in item for item in report["improvements"])


@pytest.mark.eval
def test_c_reinforcement_observability_detects_missing_c_and_silent_exception(
    tmp_path, monkeypatch
):
    """C 보강 루프는 C 없는 WIP와 조용히 삼키는 except 후보를 드러낸다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    wip = tmp_path / "docs" / "WIP" / "decisions--hn_missing_c.md"
    wip.parent.mkdir(parents=True)
    wip.write_text(
        "---\ntitle: missing c\nproblem: P7\ns: [S7]\nstatus: in-progress\n---\n\n"
        "# Missing C\n",
        encoding="utf-8",
    )
    script = tmp_path / ".claude" / "scripts" / "quiet.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        "try:\n    risky()\nexcept Exception:\n    pass\n",
        encoding="utf-8",
    )
    self_script = tmp_path / ".claude" / "scripts" / "eval_harness.py"
    self_script.write_text(
        "try:\n    risky()\nexcept Exception:\n    pass\n",
        encoding="utf-8",
    )
    self_cps_script = tmp_path / ".claude" / "scripts" / "eval_cps_integrity.py"
    self_cps_script.write_text(
        "try:\n    risky()\nexcept Exception:\n    pass\n",
        encoding="utf-8",
    )

    report = mod.observe_c_reinforcement()
    assert report["c_missing"] == ["docs/WIP/decisions--hn_missing_c.md"]
    assert report["silent_exceptions"] == [
        ".claude/scripts/quiet.py:3 | except Exception:"
    ]


@pytest.mark.eval
def test_c_reinforcement_observability_accepts_frontmatter_c(tmp_path, monkeypatch):
    """frontmatter c:가 있으면 WIP C 신호 누락으로 보고하지 않는다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    wip = tmp_path / "docs" / "WIP" / "decisions--hn_has_c.md"
    wip.parent.mkdir(parents=True)
    wip.write_text(
        "---\n"
        "title: has c\n"
        "c: 사용자 발화 원문\n"
        "problem: P8\n"
        "s: [S8]\n"
        "status: in-progress\n"
        "---\n\n"
        "# Has C\n",
        encoding="utf-8",
    )

    report = mod.observe_c_reinforcement()
    assert report["c_missing"] == []


@pytest.mark.eval
def test_c_reinforcement_observability_accepts_ascii_cps_arrows(
    tmp_path, monkeypatch
):
    """CPS Rationale의 ASCII 화살표도 C 신호로 인정한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    wip = tmp_path / "docs" / "WIP" / "decisions--hn_ascii_arrows.md"
    wip.parent.mkdir(parents=True)
    wip.write_text(
        "---\n"
        "title: ascii arrows\n"
        "problem: P8\n"
        "s: [S8]\n"
        "status: in-progress\n"
        "---\n\n"
        "## CPS Rationale\n\n"
        "- C -> P: 관찰\n"
        "- P -> S: 해결\n"
        "- S -> AC: 검증\n",
        encoding="utf-8",
    )

    report = mod.observe_c_reinforcement()
    assert report["c_missing"] == []


@pytest.mark.eval
def test_policy_drift_detects_worktree_blanket_ban(tmp_path, monkeypatch):
    """active 문구의 worktree blanket ban은 policy drift로 보고한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    f = tmp_path / "AGENTS.md"
    f.write_text('Agent 호출 시 isolation: "worktree" 사용 금지.\n', encoding="utf-8")

    hits = mod.scan_policy_drift([f])

    assert hits == [
        ("AGENTS.md", 1, "worktree blanket ban", 'Agent 호출 시 isolation: "worktree" 사용 금지.')
    ]


@pytest.mark.eval
def test_policy_drift_allows_permission_ready_sandbox(tmp_path, monkeypatch):
    """permission-ready 조건이 붙은 sandbox 문구는 drift가 아니다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    f = tmp_path / "CLAUDE.md"
    f.write_text("sandbox는 permission-ready 조건에서만 완료 증거로 쓴다.\n", encoding="utf-8")

    assert mod.scan_policy_drift([f]) == []


@pytest.mark.eval
def test_policy_drift_detects_unqualified_sandbox(tmp_path, monkeypatch):
    """조건 없는 sandbox 완료 증거화 문구는 policy drift로 보고한다."""
    mod = _load_eval_harness()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    f = tmp_path / "CLAUDE.md"
    f.write_text("sandbox 실행 결과를 완료 증거로 삼는다.\n", encoding="utf-8")

    hits = mod.scan_policy_drift([f])

    assert hits == [
        ("CLAUDE.md", 1, "sandbox without permission-ready", "sandbox 실행 결과를 완료 증거로 삼는다.")
    ]


@pytest.mark.eval
def test_dispatcher_drift_clean_current_repo():
    """safe dispatcher의 필수 예시와 허용 명령이 정렬되어 있어야 한다."""
    mod = _load_eval_harness()
    assert mod.scan_dispatcher_drift() == []


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


@pytest.mark.eval
def test_solution_problem_map_from_kickoff_table():
    """Solutions 표의 S# → P# 매핑을 추출해야 한다."""
    mod = _load_eval_cps_integrity()
    cps = """
## Solutions

| ID | Problem | Mechanism |
|----|---------|-----------|
| S7 | P7 | 알림 |
| S8 | P8 | 자산화 |
| **S10** | **P10** | 본질 의심 |
"""
    assert mod.extract_solution_problem_map(cps) == {
        "S7": "P7",
        "S8": "P8",
        "S10": "P10",
    }
    assert mod.extract_cps_solution_ids(cps) == ["S7", "S8", "S10"]


@pytest.mark.eval
def test_solution_problem_map_from_solution_headers():
    """헤더형 Solutions도 S# → P# 매핑을 추출해야 한다."""
    mod = _load_eval_cps_integrity()
    cps = """
## Solutions

### S1 (for P1)
규칙 + 자동 차단.

### **S8** (for **P8**)
강제 트리거 우선.
"""
    assert mod.extract_solution_problem_map(cps) == {
        "S1": "P1",
        "S8": "P8",
    }


@pytest.mark.eval
def test_cps_problem_ids_from_header_and_bold_formats():
    """헤더형/굵은 글씨형 Problems도 P# 목록으로 추출해야 한다."""
    mod = _load_eval_cps_integrity()
    cps = """
## Problems

**P1 — 정보 파편화**

### P5. MCP·플러그인 컨텍스트 팽창

#### **P8** — reminder 의존 실패
"""
    assert mod.extract_cps_problem_ids(cps) == ["P1", "P5", "P8"]


@pytest.mark.eval
def test_solution_problem_map_from_dotted_solution_header():
    """`### S7. ... P8` 같은 헤더형 매핑을 추출해야 한다."""
    mod = _load_eval_cps_integrity()
    cps = """
## Solutions

### S7. 후행 자산화 (P8)
본문.

### **S8** — 자동 트리거 대상 **P8**
본문.
"""
    assert mod.extract_cps_solution_ids(cps) == ["S7", "S8"]
    assert mod.extract_solution_problem_map(cps) == {
        "S7": "P8",
        "S8": "P8",
    }


@pytest.mark.eval
def test_cps_solution_coupling_detects_orphan_and_dangling():
    """P#↔S# 결합도는 orphan Problem, unmapped Solution, dangling P#를 분리해 보여야 한다."""
    mod = _load_eval_cps_integrity()
    cps = """
## Problems

| ID | 1줄 요약 |
|----|---------|
| P1 | 활성 |
| **P2** | 장기 |

## Solutions

| ID | 대상 P# | 1줄 메커니즘 |
|----|---------|-------------|
| S1 | P1 | 해결 |
| S2 | P99 | 깨진 매핑 |
| S3 |  | 미매핑 |
"""
    problems = mod.extract_cps_problem_ids(cps)
    solutions = mod.extract_cps_solution_ids(cps)
    mapping = mod.extract_solution_problem_map(cps)

    coupling = mod.assess_cps_solution_coupling(problems, solutions, mapping)
    assert problems == ["P1", "P2"]
    assert coupling["orphan_problems"] == ["P2"]
    assert coupling["dangling_solutions"] == ["S2->P99"]
    assert coupling["unmapped_solutions"] == ["S3"]


@pytest.mark.eval
def test_solution_refs_count_supports_s_and_solution_ref(tmp_path):
    """solution-ref뿐 아니라 현재 frontmatter `s:` 필드도 S# 보조 신호로 센다."""
    mod = _load_eval_cps_integrity()
    docs_root = tmp_path / "docs"
    (docs_root / "decisions").mkdir(parents=True)
    (docs_root / "WIP").mkdir(parents=True)
    (docs_root / "decisions" / "a.md").write_text(
        "---\ntitle: a\ns: [S8]\n---\n\nbody\n",
        encoding="utf-8",
    )
    (docs_root / "WIP" / "b.md").write_text(
        "---\ntitle: b\nsolution-ref:\n  - S8 — 후행 자산화\n---\n\nbody\n",
        encoding="utf-8",
    )

    counts = mod.count_solution_refs(docs_root)
    assert counts["S8"] == 2


@pytest.mark.eval
def test_wip_problem_signals_count_related_solution(tmp_path):
    """진행 중 WIP의 관련 S# 언급은 primary problem 0건의 보조 신호다."""
    mod = _load_eval_cps_integrity()
    docs_root = tmp_path / "docs"
    (docs_root / "WIP").mkdir(parents=True)
    (docs_root / "WIP" / "decisions--mp_notification_system.md").write_text(
        "---\ntitle: 알림 시스템\nsolution-ref:\n  - S8 — 후행 자산화\n---\n\nLayer 1 이후 S8 독립 wave.\n",
        encoding="utf-8",
    )

    counts = mod.count_wip_problem_signals(docs_root, {"P8": ["S8"]})
    assert counts["P8"] == 1


@pytest.mark.eval
def test_cps_integrity_unreferenced_problem_with_solution_signal_is_not_strong_discard(
    tmp_path, monkeypatch, capsys
):
    """problem: 0이어도 관련 S# WIP 신호가 있으면 폐기·병합 강권으로 출력하지 않는다."""
    mod = _load_eval_cps_integrity()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "CPS_DOC", "docs/guides/project_kickoff.md")

    (tmp_path / "docs" / "guides").mkdir(parents=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "WIP").mkdir(parents=True)
    (tmp_path / "docs" / "guides" / "project_kickoff.md").write_text(
        """# Kickoff

## Problems

| P1 | 즉시 문제 |
| P2 | 장기 문제 |

## Solutions

| S1 | P1 | 즉시 해결 | 기준 |
| S2 | P2 | 후행 자산화 | 기준 |
""",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decisions" / "hn_now.md").write_text(
        "---\ntitle: now\nproblem: P1\ns: [S1]\n---\n\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "WIP" / "decisions--hn_later.md").write_text(
        "---\ntitle: later\nsolution-ref:\n  - S2 — 후행 자산화\n---\n\nLayer 1 이후 S2 독립 wave.\n",
        encoding="utf-8",
    )

    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "ℹ primary 인용 0건이나 보조 신호가 있는 Problem: P2" in out
    assert "related S: S2" in out
    assert "⚠ primary 인용 0건 Problem (정체 의심): P2" not in out


@pytest.mark.eval
def test_cps_integrity_signal_mute_secondary_only_prevents_destructive_warning(
    tmp_path, monkeypatch, capsys
):
    """primary problem 인용을 0으로 mute해도 related S#가 있으면 강한 폐기 문구로 가지 않는다."""
    mod = _load_eval_cps_integrity()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "CPS_DOC", "docs/guides/project_kickoff.md")

    (tmp_path / "docs" / "guides").mkdir(parents=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "guides" / "project_kickoff.md").write_text(
        """# Kickoff

## Problems

| P1 | 활성 문제 |
| P2 | 장기 문제 |

## Solutions

| S1 | P1 | 활성 해결 | 기준 |
| S2 | P2 | 장기 해결 | 기준 |
""",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decisions" / "hn_active.md").write_text(
        "---\ntitle: active\nproblem: P1\ns: [S1]\n---\n\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decisions" / "hn_secondary_only.md").write_text(
        "---\ntitle: secondary\ns: [S2]\n---\n\nbody\n",
        encoding="utf-8",
    )

    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "ℹ primary 인용 0건이나 보조 신호가 있는 Problem: P2" in out
    assert "solution refs: 1" in out
    assert "⚠ primary 인용 0건 Problem (정체 의심): P2" not in out
