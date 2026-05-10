#!/usr/bin/env python3
"""Stop hook — 에이전트 응답 완료 시 실행. 미커밋 변경/WIP 상태 경고.

stop-guard.sh의 Python 재작성 (자기증식 차단 + Git Bash 호환 자동 + 자매
hook session-start.py와 일관성). 4개 동작 절 1:1 포팅:

1. 미커밋 변경 카운트 (git status --porcelain)
2. in-progress WIP 카운트 (frontmatter 파싱)
3. 조건 A·B·C AND 발화 — git 수정 + WIP in-progress + (빈 체크박스 OR
   BIT 블록 부재). hit 시 stderr 1줄 + .claude/memory/stop_hook_audit.log
   append (P8 Phase 3 SSOT)
4. memory 환기 + .compact_count 정리

session-start.py `parse_wip_file()` 패턴 답습 (frontmatter 파싱 일관성).
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows cp949 콘솔 안전 처리 (session-start.py 답습)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def run(cmd: list[str]) -> str:
    """외부 명령 실행. 실패 시 빈 문자열."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return r.stdout.strip()
    except Exception:
        return ""


def is_in_progress(path: Path) -> bool:
    """WIP frontmatter status: in-progress 확인."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            if in_fm:
                return False
            in_fm = True
            continue
        if in_fm and re.match(r"^status:\s*in-progress", line):
            return True
    return False


def section_uncommitted() -> int:
    """1. 미커밋 변경 카운트. 반환값은 후속 조건 A 판정에 재사용."""
    porcelain = run(["git", "status", "--porcelain"])
    count = len([l for l in porcelain.splitlines() if l.strip()]) if porcelain else 0
    if count > 0:
        print(f"⚠️ 미커밋 변경 {count}개. 커밋 잊지 마.", file=sys.stderr)
    return count


def section_in_progress_wip() -> None:
    """2. in-progress WIP 카운트."""
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir():
        return
    count = sum(1 for f in wip_dir.glob("*.md") if is_in_progress(f))
    if count > 0:
        print(f"📋 in-progress 작업 {count}개 남아있음.", file=sys.stderr)


def section_abc_check(uncommitted: int) -> None:
    """3. 조건 A·B·C AND 발화 (P8 Phase 3 SSOT).

    A: uncommitted > 0
    B: 변경된 WIP 중 status: in-progress 있음
    C: 그 WIP에 빈 체크박스 `- [ ]` 또는 BIT 판단 블록 부재
    """
    if uncommitted == 0:
        return
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir():
        return

    # 변경된 파일 중 WIP만 추출 (조건 B 후보)
    porcelain = run(["git", "status", "--porcelain"])
    changed_wip: list[Path] = []
    for line in porcelain.splitlines():
        # porcelain 형식: "XY path" — 첫 두 글자 status, 이후 path
        if len(line) < 4:
            continue
        path_str = line[3:].strip().strip('"')
        if path_str.startswith("docs/WIP/") and path_str.endswith(".md"):
            p = Path(path_str)
            if p.is_file():
                changed_wip.append(p)
    if not changed_wip:
        return

    risk_files: list[str] = []
    for f in changed_wip:
        if not is_in_progress(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # 빈 체크박스 카운트
        empty_box = sum(
            1 for line in text.splitlines()
            if re.match(r"^\s*-\s*\[\s\]", line)
        )
        # BIT 블록 존재 여부
        has_bit = bool(re.search(r"^\[BIT 판단\]", text, re.MULTILINE))
        if empty_box > 0 or not has_bit:
            risk_files.append(str(f).replace("\\", "/"))

    if risk_files:
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        files_str = " ".join(risk_files)
        print(
            f"🛑 [stop-guard A·B·C] 미커밋 in-progress WIP에 미완료 신호 — {files_str}",
            file=sys.stderr,
        )
        mem_dir = Path(".claude/memory")
        mem_dir.mkdir(parents=True, exist_ok=True)
        log_path = mem_dir / "stop_hook_audit.log"
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(f"{ts} | A·B·C hit | {files_str}\n")


def section_memory_reminder() -> None:
    """4a. memory 저장 환기 (강제 아님)."""
    if Path(".claude/memory").is_dir():
        print(
            "💭 이번 세션에서 memory에 저장할 feedback·project 있나? (/clear 전 확인)",
            file=sys.stderr,
        )


def section_cleanup_compact_count() -> None:
    """4b. 컴팩션 카운터 리셋."""
    try:
        Path(".claude/.compact_count").unlink(missing_ok=True)
    except Exception:
        pass


def main() -> None:
    uncommitted = section_uncommitted()
    section_in_progress_wip()
    section_abc_check(uncommitted)
    section_memory_reminder()
    section_cleanup_compact_count()


if __name__ == "__main__":
    main()
