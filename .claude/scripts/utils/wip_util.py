"""WIP frontmatter 파싱 SSOT.

session-start.py·stop-guard.py·post-compact-guard.py가 공유하는 단일
파서. 본 모듈로 통합하기 전엔 3곳에 파편화돼 있었다 (sed/grep/awk 혼재
+ Python 정교 파서 + 단일 책임 함수). 근거: docs/decisions/hn_wip_util_ssot.md.

호출자 책임:
- cp949 안전 처리(stdout/stderr reconfigure)는 호출 스크립트가 담당
- 본 모듈은 파일 I/O와 파싱만 — 부수 효과 없음
"""

from __future__ import annotations

import re
from pathlib import Path


def parse_wip_file(path: Path) -> tuple[str, str, int, bool]:
    """WIP 파일에서 (status, title, bit_count, has_new) 반환.

    파싱 규칙:
    - frontmatter `status:`/`title:` 우선
    - frontmatter 미존재 시 본문 `> status:`·첫 `# ` 헤더 fallback
    - `## 발견된 스코프 외 이슈` 섹션 안의 `- ` 항목 카운트 (bit_count)
    - 그 항목에 `P#:.*NEW` 패턴 있으면 has_new=True

    파일 없거나 읽기 실패 시 ("", path.stem, 0, False) 반환 (예외 미전파).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", path.stem, 0, False

    lines = text.splitlines()
    status = title = ""
    in_fm = fm_done = False
    in_bit = False
    bit_count = 0
    has_new = False

    for line in lines:
        if line.strip() == "---":
            if in_fm:
                in_fm = False
                fm_done = True
            elif not fm_done:
                in_fm = True
            continue
        if in_fm:
            if line.startswith("status:"):
                status = line[7:].strip()
            elif line.startswith("title:"):
                title = line[6:].strip()
        elif fm_done:
            if not status and line.startswith("> status:"):
                status = line[9:].strip()
            if not title and line.startswith("# "):
                title = line[2:].strip()
            if line.startswith("## 발견된 스코프 외 이슈"):
                in_bit = True
                continue
            if in_bit:
                if line.startswith("## "):
                    in_bit = False
                elif line.startswith("- "):
                    bit_count += 1
                    if re.search(r"P#:.*NEW", line):
                        has_new = True

    return status, title, bit_count, has_new


def is_in_progress(path: Path) -> bool:
    """WIP frontmatter `status: in-progress` 여부.

    stop-guard.py가 status만 필요로 해서 정의한 단일 책임 헬퍼. 본질은
    `parse_wip_file(path)[0] == "in-progress"`와 동등하지만 명시적 alias로
    제공해 호출자 가독성 유지.
    """
    status, _, _, _ = parse_wip_file(path)
    return status == "in-progress"
