#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orchestrator.py — P 진입 조건 신호 detect + Claude 강제 인지

defends: P9
serves: S9
trigger:
  - frontmatter-problem-mismatch
  - consecutive-error-count
  - wip-problem-target-misalign

본 스크립트는 PreToolUse hook으로 실행되어 매 도구 호출 직전에 객관 신호를 detect.
Critical 신호(P9 cascade 깨짐)는 exit 2로 강제 중단, Info 신호(P1 에러 카운터)는
exit 0 + additionalContext stdout 주입.

이중 안전장치: stdout JSON + .claude/session_signal.json 파일 쓰기.
Issue #13912 (UserPromptSubmit stdout 불안정) 대비.

근거:
- docs/decisions/hn_cps_entry_signal_layering.md (3층 책임 분리)
- docs/decisions/hn_bit_cascade_objectification.md (P9 신설)
- docs/WIP/decisions--hn_orchestrator_mechanism.md (본 결정)
- Praetorian "Deterministic AI Orchestration"
- Anthropic Building Effective AI Agents (orchestrator-workers 패턴)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIGNAL_PATH = Path(os.environ.get(
    "ORCHESTRATOR_SIGNAL_PATH",
    REPO_ROOT / ".claude" / "session_signal.json",
))
WIP_DIR = REPO_ROOT / "docs" / "WIP"

# P1 임계 (Layer 2 trigger 자격 요건)
CONSECUTIVE_ERROR_LIMIT = 3
SAME_FILE_EDIT_LIMIT = 3


# ---------------------------------------------------------------------------
# 상태 파일 I/O
# ---------------------------------------------------------------------------

def load_signal() -> dict:
    """session_signal.json 읽기. 없으면 빈 구조 반환."""
    if not SIGNAL_PATH.exists():
        return new_signal_state()
    try:
        with open(SIGNAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return new_signal_state()


def new_signal_state() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": now,
        "active_signals": [],
        "counter": {
            "consecutive_errors": 0,
            "tool_use_count": 0,
            "last_modified_files": [],
        },
        "last_updated": now,
    }


def save_signal(state: dict) -> None:
    SIGNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(SIGNAL_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# WIP frontmatter 파싱
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(path: Path) -> dict:
    """간이 YAML frontmatter 파서. PyYAML 의존 회피."""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    fm: dict = {}
    current_key = None
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  -") and current_key:
            fm.setdefault(current_key, []).append(stripped.lstrip("- ").strip())
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                current_key = key
                fm[key] = []
            else:
                fm[key] = value
                current_key = None
    return fm


def find_active_wips() -> list[Path]:
    """docs/WIP/ 내 in-progress WIP 목록."""
    if not WIP_DIR.exists():
        return []
    wips = []
    for path in WIP_DIR.glob("*.md"):
        fm = parse_frontmatter(path)
        status = fm.get("status", "")
        if status == "in-progress":
            wips.append(path)
    return wips


# ---------------------------------------------------------------------------
# Hook 입력 파싱
# ---------------------------------------------------------------------------

def parse_hook_input() -> dict:
    """PreToolUse hook stdin (Claude Code JSON spec)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return {}


def extract_target_paths(hook_input: dict) -> list[str]:
    """도구 호출에서 영향 받는 파일 경로 추출."""
    tool_input = hook_input.get("tool_input") or {}
    paths: list[str] = []
    for key in ("file_path", "path", "notebook_path"):
        v = tool_input.get(key)
        if isinstance(v, str):
            paths.append(v)
    # MultiEdit·edits 배열
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                p = edit.get("file_path")
                if isinstance(p, str):
                    paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# P9 detect — WIP frontmatter ↔ 작업 파일 매칭
# ---------------------------------------------------------------------------

def detect_p9_misalign(hook_input: dict, state: dict) -> list[dict]:
    """
    P9 진입 조건:
    - in-progress WIP frontmatter `problem` 필드는 있는데
    - 현재 도구 호출이 그 WIP가 다루는 영역과 무관한 파일 수정

    완화: WIP가 명시적으로 작업 파일을 specify하지 않으면 skip
    (현재 단계는 frontmatter problem 매칭 정합성만 체크)
    """
    signals: list[dict] = []
    tool_name = hook_input.get("tool_name", "")

    # WIP 자체 수정·docs 작업은 skip (자기 참조 회피)
    target_paths = extract_target_paths(hook_input)
    if not target_paths:
        return signals
    if any("docs/WIP/" in p or "docs/decisions/" in p for p in target_paths):
        return signals

    wips = find_active_wips()
    if not wips:
        return signals

    # WIP frontmatter `problem` 필드 ↔ CPS Problems 매칭 검증
    cps_path = REPO_ROOT / "docs" / "guides" / "project_kickoff.md"
    if not cps_path.exists():
        return signals
    cps_text = cps_path.read_text(encoding="utf-8", errors="ignore")

    for wip in wips:
        fm = parse_frontmatter(wip)
        problem = fm.get("problem", "")
        if not problem or not isinstance(problem, str):
            continue
        # CPS Problems 섹션에 P# 등록 확인
        pid = problem.strip()
        if not re.match(r"^P\d+$", pid):
            continue
        pattern = rf"^###\s+{pid}\."
        if not re.search(pattern, cps_text, re.MULTILINE):
            signals.append({
                "p_id": "P9",
                "severity": "CRITICAL",
                "message": f"WIP {wip.name}의 problem={pid}가 CPS Problems에 미등록",
                "action_required": f"docs/guides/project_kickoff.md에 {pid} 등록 또는 WIP frontmatter 수정",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "wip": str(wip.relative_to(REPO_ROOT)),
            })

    return signals


CPS_REL_PATH = "docs/guides/project_kickoff.md"
GEMINI_RESULT_PATH = REPO_ROOT / ".claude" / "memory" / "gemini-solution-review.md"


# ---------------------------------------------------------------------------
# Phase 1 — Solution 변경 detect + Gemini 의견 호출 (gemini_delegation_pipeline)
# ---------------------------------------------------------------------------

def gemini_cli_path() -> str | None:
    """gemini CLI 실행 파일 경로 반환.

    Windows npm shim(`gemini.cmd`)은 `subprocess(["gemini", ...])`로 직접
    실행되지 않을 수 있어 `shutil.which`가 해석한 경로를 사용한다.
    """
    import shutil
    return shutil.which("gemini")


def gemini_cli_available() -> bool:
    """gemini CLI 설치 여부. 미설치 시 graceful skip (다운스트림 cascade 보호)."""
    return gemini_cli_path() is not None


def _solutions_range(cps_text: str) -> tuple[int, int] | None:
    """CPS 본문에서 `## Solutions` 섹션의 (시작 라인, 끝 라인) 반환.

    끝 라인은 다음 `## ` 헤더 직전 라인. 없으면 EOF.
    1-indexed (git diff hunk 라인 번호와 정합).
    """
    lines = cps_text.splitlines()
    start = None
    for i, line in enumerate(lines, start=1):
        if line.startswith("## Solutions"):
            start = i
            continue
        if start is not None and line.startswith("## ") and not line.startswith("## Solutions"):
            return (start, i - 1)
    if start is not None:
        return (start, len(lines))
    return None


def _parse_hunk_header(line: str) -> tuple[int, int] | None:
    """git diff hunk 헤더 `@@ -A,B +C,D @@` → (C 새 파일 시작 라인, D 라인 수).

    `-U0` 출력 호환. B·D 생략(`+C`) 시 1로 처리.
    """
    m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
    if not m:
        return None
    new_start = int(m.group(1))
    new_count = int(m.group(2)) if m.group(2) else 1
    return (new_start, new_count)


def staged_solutions_changed_from_diff(diff_text: str, cps_text: str) -> bool:
    """staged diff에 CPS Solutions 섹션 영역 변경이 있는가.

    diff hunk 헤더 위치 + Solutions 섹션 라인 범위 매칭으로 정밀 판정.
    헤더 라인 추가만 보는 게 아니라 **본문 라인 변경**도 detect.

    회귀 가드 가능 — diff_text·cps_text 인자로 fixture 주입.
    """
    if not diff_text:
        return False
    sol_range = _solutions_range(cps_text)
    if not sol_range:
        return False
    sol_start, sol_end = sol_range

    for line in diff_text.splitlines():
        if not line.startswith("@@"):
            continue
        parsed = _parse_hunk_header(line)
        if not parsed:
            continue
        new_start, new_count = parsed
        # `-U0` 출력에서 hunk가 차지하는 새 파일 라인 범위
        hunk_start = new_start
        hunk_end = new_start + max(new_count - 1, 0)
        # Solutions 영역과 겹치는지
        if hunk_start <= sol_end and hunk_end >= sol_start:
            return True
    return False


def staged_solutions_changed() -> bool:
    """진짜 동작 — git diff + CPS 본문 읽고 위 함수 호출."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "-U0", CPS_REL_PATH],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if result.returncode != 0 or not result.stdout:
        return False
    cps_path = REPO_ROOT / CPS_REL_PATH
    if not cps_path.exists():
        return False
    cps_text = cps_path.read_text(encoding="utf-8", errors="ignore")
    return staged_solutions_changed_from_diff(result.stdout, cps_text)


def call_gemini_background(prompt: str) -> None:
    """gemini CLI를 background로 호출 → 결과를 GEMINI_RESULT_PATH에 저장.

    PreToolUse hook은 차단 없이 빠르게 반환해야 하므로 자식 프로세스 detach.
    """
    import subprocess
    gemini_path = gemini_cli_path()
    if not gemini_path:
        return
    GEMINI_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # detach background: stdout·stderr 리다이렉트, hook return 비대기
    try:
        with open(GEMINI_RESULT_PATH, "w", encoding="utf-8") as out:
            out.write(f"# Gemini Solution Review (in progress)\n\nprompt:\n{prompt[:200]}...\n")
        # 실제 호출은 별 프로세스로 detach
        subprocess.Popen(
            [gemini_path, "-p", prompt],
            stdout=open(GEMINI_RESULT_PATH, "a", encoding="utf-8"),
            stderr=subprocess.DEVNULL,
            cwd=str(REPO_ROOT),
            # Windows·Unix 공통 detach
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            if os.name == "nt" else 0,
            start_new_session=(os.name != "nt"),
        )
    except OSError:
        return


def detect_solution_change(hook_input: dict, state: dict) -> list[dict]:
    """CPS Solution 변경 staged → Gemini 의견 호출 트리거.

    Phase 1 (gemini_delegation_pipeline 본 wave 합의). 신호 severity INFO —
    Critical 아님, 권고 수준.

    중복 호출 방지: session 동안 한 번만 호출 (state에 플래그 저장).
    """
    signals: list[dict] = []
    counter = state.setdefault("counter", {})
    if counter.get("gemini_solution_review_called"):
        return signals  # 이미 호출됨
    if not staged_solutions_changed():
        return signals
    if not gemini_cli_available():
        # graceful skip — 다운스트림 영향 0
        return signals

    # 호출
    prompt = (
        "다음은 Claude Code harness-starter의 CPS Solutions 섹션 변경 diff다. "
        "변경이 기존 Solution 충족 기준을 약화시키지 않는지·다른 P를 깨지 않는지·"
        "객관 신호 cascade에 정합한지 비판적으로 짚어라. 길이 제한 없음. 한국어. "
        "diff:\n\n" + _read_staged_diff()
    )
    call_gemini_background(prompt)
    counter["gemini_solution_review_called"] = True

    signals.append({
        "p_id": "Phase1",
        "severity": "INFO",
        "key": "gemini-solution-review",
        "message": f"CPS Solutions 변경 staged — Gemini 의견 호출 (background). 결과: {GEMINI_RESULT_PATH.relative_to(REPO_ROOT)}",
        "action_required": "commit 전 Gemini 의견 파일 확인 권장",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    })
    return signals


def _read_staged_diff() -> str:
    """staged diff 본문 읽기 (Gemini 컨텍스트용, 크기 제한)."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", CPS_REL_PATH],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    diff = result.stdout
    # Gemini CLI argv 제한 회피 — 8000자 cap
    return diff[:8000] if len(diff) > 8000 else diff


# ---------------------------------------------------------------------------
# P1 detect — 동일 파일 연속 수정 카운터
# ---------------------------------------------------------------------------

def detect_p1_same_file(hook_input: dict, state: dict) -> list[dict]:
    """
    P1 진입 조건:
    - 동일 파일이 같은 세션에서 SAME_FILE_EDIT_LIMIT회 이상 수정

    counter.last_modified_files 추적.
    """
    signals: list[dict] = []
    tool_name = hook_input.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return signals

    target_paths = extract_target_paths(hook_input)
    if not target_paths:
        return signals

    counter = state.setdefault("counter", {})
    history: list[str] = counter.setdefault("last_modified_files", [])

    for p in target_paths:
        # 자기 참조 파일 제외
        if "session_signal.json" in p:
            continue
        history.append(p)

    # 최근 N개만 보관 (메모리 보호)
    counter["last_modified_files"] = history[-50:]

    # 카운트
    from collections import Counter
    file_counts = Counter(history[-30:])  # 최근 30번 내
    for fpath, count in file_counts.items():
        if count >= SAME_FILE_EDIT_LIMIT:
            signals.append({
                "p_id": "P1",
                "severity": "INFO",
                "key": f"P1:{fpath}",  # upsert 키 — count 변화 시 기존 신호 교체
                "message": f"동일 파일 연속 수정 감지: {fpath} ({count}회)",
                "action_required": "추측 수정 패턴인지 확인. internal-first.md 적용 권장",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

    counter["tool_use_count"] = counter.get("tool_use_count", 0) + 1
    return signals


# ---------------------------------------------------------------------------
# 신호 통합·필터
# ---------------------------------------------------------------------------

def _signal_key(s: dict) -> tuple:
    """신호 식별자.

    `key` 필드가 있으면 그것을 식별자로 사용 (upsert 동작 — 같은 key는 갱신).
    예: P1은 "P1:{file_path}" 키 — count 변화 시 기존 신호 교체로 stale 누적 차단.

    없으면 (p_id, message) fallback — 기존 동작 호환.
    """
    k = s.get("key")
    if k:
        return ("k", k)
    return ("m", s.get("p_id"), s.get("message"))


def deduplicate_signals(new_signals: list[dict], existing: list[dict]) -> list[dict]:
    """동일 신호 upsert + dedup.

    `key` 보유 신호는 기존 같은 key 신호를 **교체** (P1 count 갱신).
    `key` 없는 신호는 (p_id, message) 기반 dedup (P9 등 정적 신호).
    """
    out: list[dict] = []
    index: dict[tuple, int] = {}
    for s in existing:
        index[_signal_key(s)] = len(out)
        out.append(s)
    for s in new_signals:
        k = _signal_key(s)
        if k in index:
            out[index[k]] = s  # upsert: 기존 신호 교체
        else:
            index[k] = len(out)
            out.append(s)
    return out


def has_critical(signals: list[dict]) -> bool:
    return any(s.get("severity") == "CRITICAL" for s in signals)


# ---------------------------------------------------------------------------
# 출력 — stdout (additionalContext) + 파일 쓰기
# ---------------------------------------------------------------------------

def format_context(signals: list[dict]) -> str:
    if not signals:
        return ""
    lines = ["", "=== ORCHESTRATOR SIGNALS ==="]
    for s in signals:
        sev = s.get("severity", "INFO")
        pid = s.get("p_id", "?")
        msg = s.get("message", "")
        act = s.get("action_required", "")
        lines.append(f"[{sev}] {pid}: {msg}")
        if act:
            lines.append(f"  → 조치: {act}")
    lines.append("=========================")
    return "\n".join(lines)


def emit_output(signals: list[dict], block: bool) -> None:
    """stdout JSON (Claude Code hook spec) — additionalContext + 차단 신호."""
    context = format_context(signals)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    if block:
        output["decision"] = "block"
        output["reason"] = context
    print(json.dumps(output, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> int:
    hook_input = parse_hook_input()
    state = load_signal()

    # detect
    p9_signals = detect_p9_misalign(hook_input, state)
    p1_signals = detect_p1_same_file(hook_input, state)
    phase1_signals = detect_solution_change(hook_input, state)

    new_signals = p9_signals + p1_signals + phase1_signals

    # 기존 신호와 통합 (중복 제거)
    active = state.setdefault("active_signals", [])
    merged = deduplicate_signals(new_signals, active)
    state["active_signals"] = merged

    # 파일 쓰기 (이중 안전장치)
    save_signal(state)

    # 출력 — 이번 호출에서 새로 감지된 신호만 주입한다.
    # 기존 active_signals 전체 재출력은 긴 세션에서 컨텍스트 노이즈가 된다.
    if not new_signals:
        # 침묵 (false-positive 마찰 회피)
        return 0

    critical_now = has_critical(new_signals)
    emit_output(new_signals, block=critical_now)

    # exit code: critical은 2 (강제 중단), 그 외 0
    return 2 if critical_now else 0


if __name__ == "__main__":
    sys.exit(main())
