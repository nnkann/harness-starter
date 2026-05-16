#!/usr/bin/env python3
"""PostCompact hook — 컴팩션 후 컨텍스트 재주입.

post-compact-guard.sh의 Python 재작성 (자기증식 차단 + sed/grep/awk 혼재
제거 + wip_util.py SSOT 사용). 6개 동작 절 1:1 포팅:

1. 컴팩션 카운터 증가 (.claude/.compact_count)
2. 진행 중인 WIP 목록 + in-progress 항목의 결정 사항 5줄 재주입
3. staged 변경 stat
4. WIP 진행률 (completed/abandoned 비율)
5. 컴팩션 3회 이상 경고
6. 규칙 재주입

session-start.py·stop-guard.py 패턴 답습 (frontmatter 파싱은 wip_util,
cp949 안전 처리, cwd 보정).
"""

import os
import subprocess
import sys
from pathlib import Path

# cwd 보정 — hook 실행 시 cwd가 .claude/scripts/로 들어오는 케이스 안전망
os.chdir(Path(__file__).resolve().parents[2])

# Windows cp949 콘솔 안전 처리 (session-start.py 답습)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# wip_util SSOT
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.wip_util import parse_wip_file  # noqa: E402


def run(cmd: list[str]) -> str:
    """외부 명령 실행. 실패 시 빈 문자열."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return r.stdout.strip()
    except Exception:
        return ""


def increment_compact_count() -> int:
    """1. 컴팩션 카운터 증가."""
    counter = Path(".claude/.compact_count")
    try:
        count = int(counter.read_text().strip()) + 1 if counter.exists() else 1
    except (ValueError, OSError):
        count = 1
    try:
        counter.write_text(f"{count}\n", encoding="utf-8")
    except OSError:
        pass
    return count


def extract_decisions(text: str) -> list[str]:
    """`## 결정 사항` 섹션 본문 추출 (다음 `## ` 헤더 전까지, placeholder 제외).

    sh 원본의 `sed -n '/^## 결정 사항/,/^## /{ /^## /d; /^$/d; p; }'` 동등.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## 결정 사항"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.strip() == "":
                continue
            out.append(line)
    # placeholder 제거 (sh의 != "(작업 중 기록)" / "(작업하면서 채움)" 동등)
    placeholders = {"(작업 중 기록)", "(작업하면서 채움)"}
    if all(line.strip() in placeholders for line in out):
        return []
    return out


def section_wip_list() -> None:
    """2. 진행 중인 WIP 목록 + 결정 사항 재주입."""
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir() or not any(wip_dir.glob("*.md")):
        print()
        print("📋 진행 중인 작업: 없음")
        return

    print()
    print("📋 진행 중인 작업:")
    for f in sorted(wip_dir.glob("*.md")):
        status, title, _, _ = parse_wip_file(f)
        print(f"  - [{status}] {title}")

        if status.strip() == "in-progress":
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            decisions = extract_decisions(text)
            if decisions:
                print("    📌 결정 사항:")
                for line in decisions[:5]:
                    print(f"      {line}")


def section_staged() -> None:
    """3. staged 변경 stat."""
    staged = run(["git", "diff", "--cached", "--stat"])
    if staged:
        last = staged.splitlines()[-1]
        print()
        print("📦 Staged 변경:")
        print(f"  {last}")


def section_progress() -> None:
    """4. WIP 진행률."""
    wip_dir = Path("docs/WIP")
    if not wip_dir.is_dir():
        return
    total = 0
    done = 0
    for f in wip_dir.glob("*.md"):
        status, _, _, _ = parse_wip_file(f)
        total += 1
        if status.strip() in ("completed", "abandoned"):
            done += 1
    if total > 0:
        print()
        print(f"📊 WIP 진행률: {done}/{total} 완료")


def section_compact_warning(count: int) -> None:
    """5. 컴팩션 3회 이상 경고."""
    if count >= 3:
        print()
        print(f"⚠️ 컴팩션 {count}회. 작업이 너무 큼. 커밋 후 분할을 고려하라.")


def section_rules() -> None:
    """6. 규칙 재주입."""
    print()
    print("═══ RULES ═══")
    print("1. 린터 에러 0에서만 커밋.")
    print("2. 새 파일 생성 전 naming.md 확인.")
    print("3. 새 함수 전 LSP + Grep으로 중복 확인.")
    print("4. 테스트는 tests/ 폴더에만.")
    print("5. 문서는 docs/ 하위에만.")
    print("6. grep 대신 LSP 우선.")
    print("7. 검증 없이 '완료'라고 말하지 마.")
    print("═════════════")


def main() -> None:
    count = increment_compact_count()
    print(f"⚠️ COMPACTION #{count} — 컨텍스트 재주입")
    section_wip_list()
    section_staged()
    section_progress()
    section_compact_warning(count)
    section_rules()


if __name__ == "__main__":
    main()
