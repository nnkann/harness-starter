from pathlib import Path
import re

import pytest


HERMES_ROOT = Path("/Users/kann/.hermes")
ROOT_AGENTS = HERMES_ROOT / "AGENTS.md"
PROFILE_AGENTS = {
    name: HERMES_ROOT / "profiles" / name / "AGENTS.md"
    for name in ("anubis", "khonsu", "sekhmet", "seshat")
}
THOTH_AGENTS = HERMES_ROOT / "profiles" / "thoth" / "AGENTS.md"
SEKHMET_SOUL = HERMES_ROOT / "profiles" / "sekhmet" / "SOUL.md"
LEGACY_TEST = (
    HERMES_ROOT
    / "profiles/sekhmet/artifacts/sekhmet-native-policy/test_sekhmet_atomic_verification_steps.py"
)
POLICY_START = "<!-- agy-native-atomic-verification-policy:start -->"
POLICY_END = "<!-- agy-native-atomic-verification-policy:end -->"


def canonical_policy(text):
    match = re.search(
        re.escape(POLICY_START) + r"(.*?)" + re.escape(POLICY_END),
        text,
        re.DOTALL,
    )
    assert match, "root canonical AGY-native atomic verification policy is missing"
    return match.group(1)


def is_atomic(command):
    prohibited = (
        "\n",
        ";",
        "&&",
        "||",
        "|",
        ">",
        "<",
        "$(",
        "`",
        "sh -c",
        "bash -c",
        "for ",
        "while ",
        "if ",
        "wrapper ",
        "aggregate ",
    )
    return not any(shape in command for shape in prohibited)


class ObservationSelection:
    def __init__(self, permitted=()):
        self.permitted = set(permitted)
        self.command_issued = 0
        self.commands = []

    def select_before_disposition(self, candidates):
        for command in candidates:
            if command in self.permitted and is_atomic(command):
                self.command_issued += 1
                self.commands.append(command)
                return {"command": command, "awaiting_disposition": True}
        return {"command_issued": 0, "status": "need_local_body"}

    def deny(self, command, followups=()):
        self.command_issued += 1
        self.commands.append(command)
        return {
            "denied_command": command,
            "status": "verification_carrier_gap",
            "followups": [],
        }


def test_root_workflow_is_the_single_canonical_policy_surface():
    root = ROOT_AGENTS.read_text(encoding="utf-8")
    assert root.count(POLICY_START) == 1
    assert root.count(POLICY_END) == 1
    body = canonical_policy(root)
    required = (
        "AGY-native read-only multi-observation verification/research",
        "Anubis, Khonsu, Sekhmet, Seshat",
        "behaviorally",
        "Thoth",
        "text-only/no-tool",
        "non-AGY profiles",
        "generic implementation scripting",
        "one independently meaningful command maximum per step",
        "result and permission disposition",
        "multiline/composite scripts",
        "shell control flow",
        "`;`",
        "`&&`",
        "`||`",
        "pipes",
        "redirection",
        "substitution",
        "`sh -c`",
        "`bash -c`",
        "wrappers",
        "equivalent aggregation",
        "first denial",
        "exact denied command",
        "verification_carrier_gap",
        "zero followups",
        "concatenation, retry, or rewrite",
        "allow rule",
        "permission bypass",
        "per-command approval proposal",
        "no known-permitted atomic carrier",
        "command_issued=0",
        "need_local_body",
        "hold",
    )
    for phrase in required:
        assert phrase in body, f"canonical policy is missing {phrase!r}"

    workflow = root.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    assert POLICY_START in workflow
    executor_rule = workflow.index("`custom:agy`")
    policy_rule = workflow.index(POLICY_START)
    assert policy_rule > executor_rule


def test_read_only_agy_profiles_reference_root_without_policy_duplication():
    canonical = "AGY-native read-only multi-observation verification/research"
    for name, path in PROFILE_AGENTS.items():
        text = path.read_text(encoding="utf-8")
        assert "root `~/.hermes/AGENTS.md`" in text, name
        assert "`Workflow`" in text, name
        assert POLICY_START not in text, name
        assert POLICY_END not in text, name
        assert canonical not in text, name

    soul = SEKHMET_SOUL.read_text(encoding="utf-8")
    assert "root `~/.hermes/AGENTS.md`" in soul
    assert "`Workflow`" in soul
    assert POLICY_START not in soul
    assert "one independently meaningful command maximum per step" not in soul


def test_thoth_text_only_no_tool_exclusion_remains():
    text = THOTH_AGENTS.read_text(encoding="utf-8")
    assert "AGY text-only lane" in text
    assert "uses no internal or Hermes tool" in text


@pytest.mark.parametrize(
    ("shape", "command"),
    (
        ("multiline", "pwd\ngit status --short"),
        ("composite", "aggregate pwd git-status"),
        ("shell-control-for", "for x in a; do pwd; done"),
        ("shell-control-while", "while true; do pwd; done"),
        ("shell-control-if", "if true; then pwd; fi"),
        ("semicolon", "pwd; git status --short"),
        ("and", "pwd && git status --short"),
        ("or", "pwd || git status --short"),
        ("pipe", "git status --short | wc -l"),
        ("redirect-out", "git status --short > status.txt"),
        ("redirect-in", "wc -l < status.txt"),
        ("substitution-dollar", "printf '%s' $(pwd)"),
        ("substitution-backtick", "printf '%s' `pwd`"),
        ("sh-c", "sh -c 'pwd'"),
        ("bash-c", "bash -c 'pwd'"),
        ("wrapper", "wrapper git status --short"),
    ),
)
def test_compound_and_aggregate_command_shapes_are_rejected(shape, command):
    assert not is_atomic(command), shape


def test_one_atomic_selection_waits_for_disposition():
    selection = ObservationSelection({"pwd", "git status --short"})
    result = selection.select_before_disposition(("pwd", "git status --short"))
    assert result == {"command": "pwd", "awaiting_disposition": True}
    assert selection.command_issued == 1
    assert selection.commands == ["pwd"]


def test_first_denial_reports_exact_command_and_has_zero_followups():
    denied = "git status --short"
    selection = ObservationSelection({denied, "git diff --stat"})
    result = selection.deny(
        denied,
        followups=(denied, "git status", "wrapper git status --short"),
    )
    assert result == {
        "denied_command": denied,
        "status": "verification_carrier_gap",
        "followups": [],
    }
    assert selection.command_issued == 1
    assert selection.commands == [denied]


def test_no_known_permitted_carrier_issues_nothing_and_requests_boundary():
    selection = ObservationSelection()
    result = selection.select_before_disposition(("pwd",))
    assert result["command_issued"] == 0
    assert result["status"] in {"need_local_body", "hold"}
    assert selection.command_issued == 0
    assert selection.commands == []


def test_policy_has_no_allow_bypass_approval_or_rewrite_route():
    body = canonical_policy(ROOT_AGENTS.read_text(encoding="utf-8"))
    assert "no allow rule, permission bypass, or per-command approval proposal" in body
    assert "no concatenation, retry, or rewrite" in body


def test_legacy_sekhmet_policy_test_is_retired():
    assert not LEGACY_TEST.exists()
