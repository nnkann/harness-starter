#!/usr/bin/env python3
"""
git log → commit별 stage·problem·solution-ref·시간 간격 추출.

§H-1 (v0.44.1~)에서 commit 메시지 본문에 자동 포함된 추적성 라인
(`🔍 review: <stage> | problem: P# | solution-ref: S#`) 을 파싱.

사용:
  python3 .claude/scripts/measure_commit_latency.py             # 최근 20개
  python3 .claude/scripts/measure_commit_latency.py 50          # 최근 50개
  python3 .claude/scripts/measure_commit_latency.py --since main # main 이후

출력 (TSV):
  sha    ts    stage    problem    files+/-    title
"""

import re
import subprocess
import sys
from datetime import datetime


REVIEW_PAT = re.compile(
    r"🔍\s*review:\s*(?P<stage>\S+)\s*\|\s*"
    r"problem:\s*(?P<problem>\S+)\s*\|\s*"
    r"solution-ref:\s*(?P<solref>[^\n]+)"
)


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.stdout or ""


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--since" and len(args) > 1:
        rev = f"{args[1]}..HEAD"
        limit_args = []
    else:
        n = int(args[0]) if args else 20
        rev = "HEAD"
        limit_args = [f"-{n}"]

    # %H | %at | %s | %b 형식 (구분자 \x1e, end \x1f)
    log = run([
        "git", "log", *limit_args, rev,
        "--format=%H%x1e%at%x1e%s%x1e%b%x1f",
    ])

    rows: list[dict] = []
    for entry in log.split("\x1f"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\x1e")
        if len(parts) < 4:
            continue
        sha, ts, subject, body = parts[0][:7], parts[1], parts[2], parts[3]
        m = REVIEW_PAT.search(body)
        if m:
            stage = m.group("stage")
            problem = m.group("problem")
            solref = m.group("solref")[:30]
        else:
            stage = "?"
            problem = "?"
            solref = "?"
        # diff stat
        stat = run(["git", "show", "--shortstat", "--format=", parts[0]]).strip()
        m_files = re.search(r"(\d+) files? changed", stat)
        m_ins = re.search(r"(\d+) insertions?", stat)
        m_del = re.search(r"(\d+) deletions?", stat)
        files = m_files.group(1) if m_files else "0"
        ins = m_ins.group(1) if m_ins else "0"
        deletes = m_del.group(1) if m_del else "0"
        rows.append({
            "sha": sha,
            "ts": int(ts),
            "stage": stage,
            "problem": problem,
            "solref": solref,
            "files": files,
            "ins": ins,
            "del": deletes,
            "title": subject[:60],
        })

    if not rows:
        print("no commits", file=sys.stderr)
        return 1

    # 시간 역순 → 정렬 (오래된 순)
    rows.sort(key=lambda r: r["ts"])

    # 출력
    print(f"{'sha':<8} {'time':<19} {'stage':<10} {'problem':<8} {'+/-':<13} {'title'}")
    print("-" * 100)
    prev_ts = None
    intervals: list[int] = []
    for r in rows:
        t = datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        plus_minus = f"{r['files']}f +{r['ins']}/-{r['del']}"
        print(f"{r['sha']:<8} {t:<19} {r['stage']:<10} {r['problem']:<8} {plus_minus:<13} {r['title']}")
        if prev_ts is not None:
            intervals.append(r["ts"] - prev_ts)
        prev_ts = r["ts"]

    # 집계
    print()
    print(f"총 commit: {len(rows)}")
    stages: dict[str, int] = {}
    problems: dict[str, int] = {}
    for r in rows:
        stages[r["stage"]] = stages.get(r["stage"], 0) + 1
        problems[r["problem"]] = problems.get(r["problem"], 0) + 1
    print(f"stage 분포: {dict(sorted(stages.items()))}")
    print(f"problem 분포: {dict(sorted(problems.items()))}")
    if intervals:
        avg = sum(intervals) / len(intervals)
        print(f"commit 간격 평균: {avg:.0f}s ({avg/60:.1f}분), 최소 {min(intervals)}s, 최대 {max(intervals)}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
