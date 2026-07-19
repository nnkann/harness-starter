from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DECISION = REPO_ROOT / ".harness/project/docs/decisions/hn_honcho_workspace_continuity.md"
ROLE_DOCS = {
    "maat": REPO_ROOT / "docs/harness/agents/maat.md",
    "ptah": REPO_ROOT / "docs/harness/agents/ptah.md",
    "anubis": REPO_ROOT / "docs/harness/agents/anubis.md",
    "sia": REPO_ROOT / "docs/harness/agents/sia.md",
}
CANONICAL_REFERENCE = ".harness/project/docs/decisions/hn_honcho_workspace_continuity.md"
SHARED_HEADING = "# Honcho workspace 기반 cross-session continuity"
SHARED_HANDOFF_FIELDS = (
    "`message_id`, `thread_id`",
    "`current owner` / `next holder` / `phase`",
    "`required outcomes`",
    "`active acceptance constraints`",
    "`hard boundaries` / `hold conditions`",
    "`authority references`",
    "`required evidence`",
    "`decision needed`",
)
SIA_ONLY_FIELDS = ("`C/P/S`", "`local_body_ref`")
RUNTIME_CONFIG_ROWS = (
    ("shared root", "`peerName`", "`kann`"),
    ("shared root", "`pinUserPeer`", "`true`"),
    ("role host", "`workspace`", "`hermes`"),
    ("role host", "`recallMode`", "`tools`"),
    ("role host", "`sessionStrategy`", "`per-repo`"),
    ("role host", "`aiPeer`", "role-specific"),
)


def test_canonical_honcho_continuity_contract_and_role_pointers_remain_distinct() -> None:
    documentation = {
        path: path.read_text(encoding="utf-8")
        for root in (REPO_ROOT / "docs", REPO_ROOT / ".harness/project/docs")
        for path in root.rglob("*.md")
    }
    canonical = documentation[CANONICAL_DECISION]

    runtime_boundary = canonical.split("## Runtime configuration boundary", maxsplit=1)[1].split(
        "\n## ", maxsplit=1
    )[0]
    runtime_rows = tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in runtime_boundary.splitlines()
        if line.startswith(("| shared root |", "| role host |"))
    )
    assert runtime_rows == RUNTIME_CONFIG_ROWS
    assert "`/Users/kann/.hermes/honcho.json`" in runtime_boundary
    assert "project Git 밖의 runtime prerequisite" in runtime_boundary
    assert "profile-local override는 금지한다" in runtime_boundary
    assert "`peer=\"user\"`는 Honcho tool alias" in runtime_boundary
    assert "resolved physical shared user peer는 `kann`" in runtime_boundary

    guarantee_heading = "### Effective continuity guarantee"
    assert canonical.count(guarantee_heading) == 1
    guarantee_boundary = runtime_boundary.split(guarantee_heading, maxsplit=1)[1]
    assert "configured named profiles" in guarantee_boundary
    assert "`/Users/kann/projects/harness-starter` session override" in guarantee_boundary
    assert "generic plain-fresh-profile inheritance" in guarantee_boundary
    assert "strict same-basename multi-repo isolation" in guarantee_boundary
    assert "fresh-process config-resolution acceptance" in guarantee_boundary

    non_goals = canonical.split("## 비목표", maxsplit=1)[1]
    assert "profile config 변경" not in non_goals
    assert "Hermes core 수정" in non_goals
    assert "live gateway 수정 또는 재시작" in non_goals
    assert "새 task database/schema/daemon" in non_goals

    shared_contract_docs = [
        path
        for path, text in documentation.items()
        if SHARED_HEADING in text or all(field in text for field in SHARED_HANDOFF_FIELDS)
    ]
    assert shared_contract_docs == [CANONICAL_DECISION]
    assert all(field in canonical for field in SHARED_HANDOFF_FIELDS)
    assert "Maat-indexed Honcho context" in canonical
    assert "continuity를 찾기 위한 pivot/candidate reference" in canonical
    assert "Discord에서 이미 제공하는 immutable identity" in canonical
    assert "thread_id: 작업이 속한 Discord thread ID" in canonical
    assert "message_id: 이 work unit을 시작한 최초 사용자 지시 message ID" in canonical
    assert "사실·범위·실행 권위는 원본 source/evidence와 현재 local body에 있다" in canonical
    assert "prior Maat handoff note가 없다는 사실만으로 HOLD하지 않는다" in canonical
    assert "per-repo session의 공통 Honcho retrieval substrate" in canonical
    assert "role host의 role-specific `aiPeer`는 서로 구분된 채 유지된다" in canonical
    assert "shared peer/session binding은 startup-read다" in canonical
    assert "`peerName`, `pinUserPeer`, `sessionStrategy`" in canonical
    assert "fresh Hermes session 또는 fresh CLI process" in canonical
    assert "stale binding evidence" in canonical
    assert "candidate absence나 HOLD 조건이 아니다" in canonical
    assert "Maat의 indexed context는 role-specific candidate pivot" in canonical
    assert "둘만으로 locator와 active obligation이 충분하면 Honcho semantic retrieval을 생략한다" in canonical
    assert "locator/obligation이 빠졌거나 continuity conflict를 해소해야 할 때만" in canonical
    assert "SIA는 retrieval proxy, broker, mandatory call path가 아니다" in canonical
    assert "SIA의 exclusive role은 closure 이후" in canonical
    assert "source-backed durable promotion/conflict scanning" in canonical
    assert "shared CPS work를 다시 증명하거나 재구성하지 않는다" in canonical
    assert "SIA promotion만을 위한 source-backed compact CPS index record" in canonical
    assert "semantic candidate content" in canonical
    assert "semantic candidate retrieval" in canonical
    assert "exact identity/source readback" in canonical
    assert "실행 authority도 task registry도 아니다" in canonical
    assert "local body가 없거나 모호한 경우" in canonical
    assert "Honcho candidate와 source/evidence가 불일치하는 경우" in canonical
    assert "authority가 충돌하는 경우" in canonical
    assert "`need_local_body` 또는 HOLD를 유지한다" in canonical

    promotion_heading = "### Durable promotion route boundary"
    assert canonical.count(promotion_heading) == 1
    promotion_boundary = canonical.split(promotion_heading, maxsplit=1)[1].split(
        "### SIA promotion용 compact CPS index", maxsplit=1
    )[0]
    assert "named-profile selection" in promotion_boundary
    assert "source/evidence review" in promotion_boundary
    assert "route/role-contract boundary" in promotion_boundary
    assert "per-tool Honcho ACL이 아니다" in promotion_boundary
    assert "`honcho_conclude`" in promotion_boundary
    assert "existing general plugin capability" in promotion_boundary
    assert "technical prevention" in promotion_boundary
    assert "out-of-contract incident" in promotion_boundary
    assert "HOLD" in promotion_boundary
    assert "Maat escalation" in promotion_boundary

    sia_index = canonical.split("### SIA promotion용 compact CPS index", maxsplit=1)[1].split(
        "## 비목표", maxsplit=1
    )[0]
    sia_fields = tuple(
        line.split("|", maxsplit=2)[1].strip()
        for line in sia_index.splitlines()
        if line.startswith("| `")
    )
    assert len(sia_fields) == len(set(sia_fields))
    assert set(sia_fields) == set((*SHARED_HANDOFF_FIELDS, *SIA_ONLY_FIELDS))

    for path in ROLE_DOCS.values():
        text = documentation[path]
        pointer = text.split("## Honcho continuity pointer", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
        assert pointer.count(CANONICAL_REFERENCE) == 1
        assert SHARED_HEADING not in text
        assert not all(field in pointer for field in SHARED_HANDOFF_FIELDS)
