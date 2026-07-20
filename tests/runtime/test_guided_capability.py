import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from harness_runtime.capability_cli import main as capability_cli
from harness_runtime.guided_capability import (
    CapabilityError,
    apply_capability,
    discover_capability,
    plan_capability,
    status_capability,
    validate_provider_identity,
)
from harness_runtime.project_binding import BindingInputs, apply_binding


def git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    (path / "README.md").write_text("project\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git", "-C", str(path), "-c", "user.name=Harness Test",
            "-c", "user.email=harness@example.invalid", "commit", "-qm", "initial",
        ],
        check=True,
    )
    return path


def bind(repo: Path) -> None:
    apply_binding(BindingInputs("project-test", repo, "main", "service-test"))


def commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo), "-c", "user.name=Harness Test",
            "-c", "user.email=harness@example.invalid", "commit", "-qm", message,
        ],
        check=True,
    )


def set_target_identity(repo: Path, capability_id: str, identity: dict[str, str | None]) -> None:
    path = repo / ".harness/project-binding.json"
    binding = json.loads(path.read_text(encoding="utf-8"))
    graph = binding["capability_graph"]
    capability = next(item for item in graph["capabilities"] if item["capability_id"] == capability_id)
    capability["target_identity"] = identity
    graph.pop("digest")
    canonical = json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8")
    graph["digest"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_plan_is_mutation_free_and_digest_tracks_current_source_snapshot(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    commit(repo, "bind")
    before = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout

    first = plan_capability(repo, "railway.deploy")
    after = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    (repo / "source.py").write_text("value = 1\n", encoding="utf-8")
    commit(repo, "source")
    second = plan_capability(repo, "railway.deploy")

    assert before == after == ""
    assert first["schema"] == "harness.capability-plan.v1"
    assert first["capability_id"] == "railway.deploy"
    assert first["source_snapshot"] != second["source_snapshot"]
    assert first["binding_scope_digest"] == second["binding_scope_digest"]
    assert first["plan_digest"] != second["plan_digest"]
    assert json.dumps(first, sort_keys=True) == json.dumps(first, sort_keys=True)


def test_missing_binding_and_invalid_capability_are_rejected(tmp_path):
    repo = git_repo(tmp_path / "project")
    with pytest.raises(CapabilityError, match="binding is missing"):
        plan_capability(repo, "railway.deploy")
    bind(repo)
    with pytest.raises(CapabilityError, match="unknown capability ID"):
        plan_capability(repo, "railway.arbitrary")


def test_runtime_contract_rejects_apply_and_local_operation_requires_approval(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)

    with pytest.raises(CapabilityError, match="runtime contracts cannot be applied"):
        apply_capability(repo, "vercel.revalidate-runtime", approval=None, executors={})
    with pytest.raises(CapabilityError, match="approval receipt is required"):
        apply_capability(repo, "railway.deploy", approval=None, executors={})


def test_provider_identity_validation_and_read_only_discovery_hold_without_linkage(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(repo, "vercel.deploy", {"org_id": "org_1", "project_id": "prj_1"})
    set_target_identity(
        repo,
        "n8n.workflow-publish-activation",
        {"instance_id": "instance_1", "workflow_id": "workflow_1", "contract_id": "contract_1"},
    )

    identity = validate_provider_identity("vercel", {"org_id": "org_1", "project_id": "prj_1"})
    discovery = discover_capability(
        repo,
        "vercel.deploy",
        state_dir=tmp_path / "state",
        executable_resolver=lambda _: None,
    )
    status = status_capability(repo, "n8n.workflow-publish-activation", state_dir=tmp_path / "state")

    assert identity == {"org_id": "org_1", "project_id": "prj_1"}
    with pytest.raises(CapabilityError, match="exact fields"):
        validate_provider_identity("vercel", {"project_id": "prj_1", "url": "https://example.invalid"})
    with pytest.raises(CapabilityError, match="non-empty strings"):
        validate_provider_identity("vercel", {"org_id": None, "project_id": "prj_1"})
    assert discovery["status"] == "hold"
    assert set(discovery["holds"]) == {
        "provider_client_unavailable",
        "credential_linkage_unresolved",
    }
    assert status["status"] == "hold"
    assert status["provider_client"] == {"mode": "source_config_only", "executable": None}


def test_vercel_missing_org_id_fails_closed_before_discovery_can_be_ready(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(repo, "vercel.deploy", {"project_id": "prj_1"})

    with pytest.raises(CapabilityError, match="exact fields"):
        discover_capability(
            repo,
            "vercel.deploy",
            state_dir=tmp_path / "state",
            executable_resolver=lambda _: "/fixed/vercel",
            sandbox_runner=lambda *args, **kwargs: 0,
        )


def test_vercel_empty_ids_fail_closed_before_status_can_be_ready(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(repo, "vercel.deploy", {"org_id": "", "project_id": ""})

    with pytest.raises(CapabilityError, match="non-empty strings"):
        status_capability(
            repo,
            "vercel.deploy",
            state_dir=tmp_path / "state",
            executable_resolver=lambda _: "/fixed/vercel",
            sandbox_runner=lambda *args, **kwargs: 0,
        )


def test_provider_discovery_requires_state_dir_and_runs_only_fixed_sandbox_commands(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(
        repo,
        "railway.deploy",
        {
            "project_id": "project_1",
            "environment_id": "environment_1",
            "service_id": "service_1",
            "service_name": "service-test",
        },
    )
    set_target_identity(repo, "vercel.deploy", {"org_id": "org_1", "project_id": "project_1"})
    set_target_identity(
        repo,
        "supabase.schema-migration",
        {"project_ref": "project_1", "boundary_id": "boundary_1"},
    )
    set_target_identity(
        repo,
        "supabase.privileged-data-mutation",
        {"project_ref": "project_1", "boundary_id": "boundary_1"},
    )
    commit(repo, "bind")
    calls = []

    def runner(worktree, state_dir, command, *, network, suppress_output):
        calls.append((Path(worktree), Path(state_dir), command, network, suppress_output))
        return 0

    with pytest.raises(CapabilityError, match="state directory is required"):
        discover_capability(repo, "railway.deploy", state_dir=None, sandbox_runner=runner)

    expected = {
        "railway.deploy": ["railway", "status"],
        "vercel.deploy": ["vercel", "whoami"],
        "supabase.schema-migration": ["supabase", "projects", "list"],
        "supabase.privileged-data-mutation": ["supabase", "projects", "list"],
    }
    for capability_id, command in expected.items():
        result = discover_capability(
            repo,
            capability_id,
            state_dir=tmp_path / "state",
            executable_resolver=lambda provider: f"/fixed/{provider}",
            sandbox_runner=runner,
        )
        assert result["provider_status"] == {"command": command, "exit_code": 0}

    assert [call[2] for call in calls] == list(expected.values())
    assert all(
        call[0] == repo
        and call[1] == tmp_path / "state"
        and call[3] is True
        and call[4] is True
        for call in calls
    )

    with pytest.raises(CapabilityError, match="external and non-overlapping"):
        status_capability(repo, "railway.deploy", state_dir=repo / "state", sandbox_runner=runner)


def test_runtime_contract_discovery_stays_source_only_and_provider_failure_holds(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(
        repo,
        "n8n.async-effects-runtime",
        {"instance_id": "instance_1", "workflow_id": "workflow_1", "contract_id": "contract_1"},
    )
    set_target_identity(
        repo,
        "railway.deploy",
        {
            "project_id": "project_1",
            "environment_id": "environment_1",
            "service_id": "service_1",
            "service_name": "service-test",
        },
    )
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        return 7

    runtime = status_capability(repo, "n8n.async-effects-runtime", state_dir=tmp_path / "state", sandbox_runner=runner)
    provider = status_capability(
        repo,
        "railway.deploy",
        state_dir=tmp_path / "state",
        executable_resolver=lambda _: "/fixed/railway",
        sandbox_runner=runner,
    )

    assert runtime["status"] == "hold"
    assert runtime["provider_status"] is None
    assert provider["status"] == "hold"
    assert "provider_status_failed" in provider["holds"]
    assert called is True


def test_serialized_manifest_plan_and_discovery_do_not_include_secret_values(tmp_path, monkeypatch):
    repo = git_repo(tmp_path / "project")
    monkeypatch.setenv("RAILWAY_TOKEN", "railway-secret-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "supabase-secret-value")
    bind(repo)
    set_target_identity(
        repo,
        "railway.deploy",
        {
            "project_id": "project_1",
            "environment_id": "environment_1",
            "service_id": "service_1",
            "service_name": "service-test",
        },
    )

    manifest = (repo / ".harness/project-binding.json").read_text(encoding="utf-8")
    plan = json.dumps(plan_capability(repo, "supabase.privileged-data-mutation"), sort_keys=True)
    discovery = json.dumps(
        discover_capability(
            repo,
            "railway.deploy",
            state_dir=tmp_path / "state",
            executable_resolver=lambda _: "/usr/local/bin/railway",
            sandbox_runner=lambda *args, **kwargs: 0,
        ),
        sort_keys=True,
    )

    serialized = manifest + plan + discovery
    assert os.environ["RAILWAY_TOKEN"] not in serialized
    assert os.environ["SUPABASE_SERVICE_ROLE_KEY"] not in serialized


def test_guided_capability_cli_has_fixed_namespace_without_generic_arguments(tmp_path, capsys):
    repo = git_repo(tmp_path / "project")
    bind(repo)

    assert capability_cli(["plan", "railway.deploy", str(repo)]) == 0
    assert json.loads(capsys.readouterr().out)["capability_id"] == "railway.deploy"
    with pytest.raises(SystemExit) as raised:
        capability_cli(["status", "railway.deploy", str(repo)])
    assert raised.value.code == 2
    assert "--state-dir" in capsys.readouterr().err
    with pytest.raises(SystemExit) as raised:
        capability_cli([
            "discovery", "railway.deploy", str(repo), "--state-dir", str(tmp_path / "state"),
            "--", "curl", "https://example.invalid",
        ])
    assert raised.value.code == 2


def test_approval_must_match_scope_and_executor_is_capability_specific(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    plan = plan_capability(repo, "railway.deploy")
    approval = {
        "schema": "harness.capability-approval.v1",
        "approval_receipt_id": "approval-1",
        "capability_id": plan["capability_id"],
        "operation": plan["operation"],
        "plan_digest": plan["plan_digest"],
        "binding_scope_digest": plan["binding_scope_digest"],
        "target_identity": plan["target_identity"],
    }

    with pytest.raises(CapabilityError, match="scope and plan digest"):
        apply_capability(repo, "railway.deploy", approval={**approval, "plan_digest": "wrong"}, executors={})
    with pytest.raises(CapabilityError, match="executor is unavailable"):
        apply_capability(repo, "railway.deploy", approval=approval, executors={})

    called = False

    def executor(current_plan, current_approval):
        nonlocal called
        called = True
        return {
            "schema": "harness.capability-execution-receipt.v1",
            "capability_id": current_plan["capability_id"],
            "plan_digest": current_plan["plan_digest"],
        }

    with pytest.raises(CapabilityError, match="non-empty strings"):
        apply_capability(repo, "railway.deploy", approval=approval, executors={"railway.deploy": executor})
    assert called is False


def test_railway_all_empty_identity_fails_closed_before_apply_can_execute(tmp_path):
    repo = git_repo(tmp_path / "project")
    bind(repo)
    set_target_identity(
        repo,
        "railway.deploy",
        {"project_id": "", "environment_id": "", "service_id": "", "service_name": ""},
    )
    plan = plan_capability(repo, "railway.deploy")
    approval = {
        "schema": "harness.capability-approval.v1",
        "approval_receipt_id": "approval-1",
        "capability_id": plan["capability_id"],
        "operation": plan["operation"],
        "plan_digest": plan["plan_digest"],
        "binding_scope_digest": plan["binding_scope_digest"],
        "target_identity": plan["target_identity"],
    }
    called = False

    def executor(current_plan, current_approval):
        nonlocal called
        called = True
        return {
            "schema": "harness.capability-execution-receipt.v1",
            "capability_id": current_plan["capability_id"],
            "plan_digest": current_plan["plan_digest"],
        }

    with pytest.raises(CapabilityError, match="non-empty strings"):
        apply_capability(repo, "railway.deploy", approval=approval, executors={"railway.deploy": executor})
    assert called is False
