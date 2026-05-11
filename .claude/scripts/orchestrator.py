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
SIGNAL_PATH = REPO_ROOT / ".claude" / "session_signal.json"
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

    new_signals = p9_signals + p1_signals

    # 기존 신호와 통합 (중복 제거)
    active = state.setdefault("active_signals", [])
    merged = deduplicate_signals(new_signals, active)
    state["active_signals"] = merged

    # 파일 쓰기 (이중 안전장치)
    save_signal(state)

    # 출력 — Critical이면 차단
    if not merged:
        # 침묵 (false-positive 마찰 회피)
        return 0

    critical_now = has_critical(new_signals)
    emit_output(merged, block=critical_now)

    # exit code: critical은 2 (강제 중단), 그 외 0
    return 2 if critical_now else 0


if __name__ == "__main__":
    sys.exit(main())
