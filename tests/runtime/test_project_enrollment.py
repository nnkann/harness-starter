import json
import os
from pathlib import Path

import pytest

from harness_runtime.project_enrollment import (
    CommandResult,
    EnrollmentAdapters,
    EnrollmentError,
    EnrollmentRequest,
    HermesConfig,
    LocalFilesystem,
    apply_enrollment,
    plan_enrollment,
)


class FakeHermes:
    def __init__(self, config_target: Path):
        self.config_target = config_target
        self.projects = {}
        self.config_values = {}
        self.commands = []
        self.create_failures = 0
        self.readback_failures_after_create = 0

    def run(self, argv: list[str]) -> CommandResult:
        self.commands.append(argv)
        action = argv[1:]
        if action == ["config", "path"]:
            return CommandResult(0, f"{self.config_target}\n", "")
        if action[:2] == ["config", "get"]:
            json_output = action[2] == "--json"
            key = action[3] if json_output else action[2]
            if key not in self.config_values:
                return CommandResult(1, "", f"Config key not set: {key}\n")
            value = self.config_values[key]
            output = json.dumps(value) if json_output else str(value)
            return CommandResult(0, f"{output}\n", "")
        if action[:3] == ["config", "set", "--force"]:
            self.config_values[action[3]] = action[4]
            return CommandResult(0, "updated\n", "")
        if action == ["project", "list"]:
            output = "".join(
                f"  {slug:<24} {slug}  [1 folder(s)]\n" for slug in self.projects
            )
            return CommandResult(0, output, "")
        if action[:2] == ["project", "show"]:
            if self.readback_failures_after_create and any(
                command[1:3] == ["project", "create"] for command in self.commands
            ):
                self.readback_failures_after_create -= 1
                return CommandResult(4, "", "injected readback failure\n")
            project = self.projects.get(action[2])
            if project is None:
                return CommandResult(1, "", f"project: no such project: {action[2]}\n")
            return CommandResult(0, project, "")
        if action[:2] == ["project", "create"]:
            if self.create_failures:
                self.create_failures -= 1
                return CommandResult(3, "", "injected create failure\n")
            slug = action[action.index("--slug") + 1]
            root = action[action.index("--primary") + 1]
            self.projects[slug] = project_output(slug, root)
            return CommandResult(0, f"Created project {slug}\n", "")
        raise AssertionError(argv)


class FakeConfig:
    def __init__(self):
        self.values = {}
        self.writes = []

    def get(self, executable: Path, key: str) -> str | None:
        return self.values.get(key)

    def set(self, executable: Path, key: str, value: str) -> None:
        self.writes.append((executable, key, value))
        self.values[key] = value


class RacingFilesystem(LocalFilesystem):
    def __init__(self, winner: bytes):
        self.winner = winner

    def create_exclusive(self, path: Path, content: bytes) -> None:
        path.write_bytes(self.winner)
        raise FileExistsError(path)


class FailingReadFilesystem(LocalFilesystem):
    def read_bytes(self, path: Path) -> bytes:
        raise OSError("injected manifest read failure")


def project_output(slug: str, root: str) -> str:
    return (
        f"{slug}  [project-id]\n"
        f"  name:    {slug}\n"
        f"  primary: {root}\n"
        "  folders:\n"
        f"    * {root}\n"
    )


def request(root: Path, executable: Path, config_target: Path) -> EnrollmentRequest:
    return EnrollmentRequest(
        version="1",
        project_slug="project-test",
        canonical_root=root,
        discord_parent_channel_id="123456789",
        hermes_executable=executable,
        hermes_config_target=config_target,
        idempotency_key="event-1",
    )


def adapters(tmp_path: Path):
    config_target = (tmp_path / "config.yaml").resolve()
    executable = tmp_path / "hermes"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    hermes = FakeHermes(config_target)
    config = FakeConfig()
    return executable.resolve(), config_target, hermes, config, EnrollmentAdapters(
        filesystem=LocalFilesystem(),
        subprocess=hermes,
        config=config,
    )


@pytest.mark.parametrize("project_slug", ["123", "true", "false", "yes", "no", "on", "off"])
def test_apply_rejects_project_slug_that_config_writer_coerces_to_non_string_before_mutation(
    tmp_path, project_slug
):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    enrollment = request(root, executable, config_target)
    enrollment = EnrollmentRequest(
        version=enrollment.version,
        project_slug=project_slug,
        canonical_root=enrollment.canonical_root,
        discord_parent_channel_id=enrollment.discord_parent_channel_id,
        hermes_executable=enrollment.hermes_executable,
        hermes_config_target=enrollment.hermes_config_target,
        idempotency_key=enrollment.idempotency_key,
    )

    with pytest.raises(EnrollmentError, match="project_slug"):
        apply_enrollment(enrollment, injected)

    assert not (root / "manifest.yml").exists()
    assert hermes.commands == []
    assert hermes.projects == {}
    assert config.writes == []


def test_apply_absent_state_creates_manifest_registry_and_parent_mapping(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert {
        name: {key: value for key, value in component.items() if key not in {"observations", "receipts"}}
        for name, component in result["components"].items()
        if name != "config_target"
    } == {
        "manifest": {"operation": "create", "path": str(root / "manifest.yml")},
        "registry": {"operation": "create", "project_slug": "project-test"},
        "mapping": {
            "operation": "create",
            "key": "platforms.discord.extra.channel_project_bindings.123456789",
        },
    }
    assert (root / "manifest.yml").read_text(encoding="utf-8") == (
        "schema: harness.project-manifest.v2\n"
        "project_slug: project-test\n"
        "workspace:\n"
        f"  canonical_cwd: {root}\n"
    )
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.values["platforms.discord.extra.channel_project_bindings.123456789"] == "project-test"
    assert result["idempotency_key"] == "event-1"


def test_apply_quotes_yaml_sensitive_canonical_root(tmp_path):
    root = (tmp_path / "project # one").resolve()
    root.mkdir()
    executable, config_target, _, _, injected = adapters(tmp_path)

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert plan_enrollment(request(root, executable, config_target), injected)["status"] == "planned"
    assert (root / "manifest.yml").read_bytes() == (
        "schema: harness.project-manifest.v2\n"
        "project_slug: project-test\n"
        "workspace:\n"
        f"  canonical_cwd: '{root}'\n"
    ).encode()


def test_plan_classifies_absent_state_without_writes(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)

    result = plan_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "planned"
    assert [
        result["components"][name]["operation"] for name in ("manifest", "registry", "mapping")
    ] == [
        "create",
        "create",
        "create",
    ]
    assert not (root / "manifest.yml").exists()
    assert hermes.projects == {}
    assert config.writes == []


def test_apply_accepts_valid_existing_manifest_with_extra_keys_without_changing_bytes(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    manifest = root / "manifest.yml"
    original = (
        "description: preserved\n"
        "schema: harness.project-manifest.v2\n"
        "project_slug: project-test\n"
        "workspace:\n"
        f"  canonical_cwd: {root}\n"
        "  extra: true\n"
    ).encode()
    manifest.write_bytes(original)
    hermes.projects["project-test"] = project_output("project-test", str(root))
    config.values["platforms.discord.extra.channel_project_bindings.123456789"] = "project-test"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "noop"
    assert {item["operation"] for item in result["components"].values()} == {"noop"}
    assert manifest.read_bytes() == original
    assert config.writes == []


@pytest.mark.parametrize(
    "case",
    ["malformed", "duplicate", "root", "symlink", "nonregular"],
)
def test_apply_observes_invalid_or_nonregular_existing_manifest_without_rewriting_it(tmp_path, case):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    manifest = root / "manifest.yml"
    valid = (
        "schema: harness.project-manifest.v2\n"
        "project_slug: project-test\n"
        "workspace:\n"
        f"  canonical_cwd: {root}\n"
    )
    if case == "malformed":
        manifest.write_text("workspace: [unterminated\n", encoding="utf-8")
    elif case == "duplicate":
        manifest.write_text("project_slug: wrong\n" + valid, encoding="utf-8")
    elif case == "root":
        manifest.write_text(valid.replace(str(root), str(tmp_path / "other")), encoding="utf-8")
    elif case == "symlink":
        target = tmp_path / "outside.yml"
        target.write_text(valid, encoding="utf-8")
        manifest.symlink_to(target)
    else:
        manifest.mkdir()

    original = None if manifest.is_dir() else manifest.read_bytes()

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["manifest"]["operation"] == "noop"
    assert result["components"]["manifest"]["observations"]
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.writes
    if original is None:
        assert manifest.is_dir()
    else:
        assert manifest.read_bytes() == original


@pytest.mark.parametrize("matching_winner", [True, False])
def test_manifest_exclusive_create_race_rereads_winner_before_other_mutation(tmp_path, matching_winner):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, _ = adapters(tmp_path)
    desired = (
        "schema: harness.project-manifest.v2\n"
        "project_slug: project-test\n"
        "workspace:\n"
        f"  canonical_cwd: {root}\n"
    ).encode()
    winner = desired if matching_winner else b"schema: conflicting.v1\n"
    injected = EnrollmentAdapters(
        filesystem=RacingFilesystem(winner),
        subprocess=hermes,
        config=config,
    )

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert (root / "manifest.yml").read_bytes() == winner
    if not matching_winner:
        assert result["components"]["manifest"]["observations"]
        assert hermes.projects["project-test"] == project_output("project-test", str(root))
        assert config.writes


def test_wrong_caller_config_path_is_recorded_without_blocking_mutation(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, _, hermes, config, injected = adapters(tmp_path)
    requested_target = (tmp_path / "different-config.yaml").resolve()

    result = apply_enrollment(request(root, executable, requested_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["config_target"]["observations"] == ["target_mismatch"]
    assert (root / "manifest.yml").exists()
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.writes


@pytest.mark.parametrize("component", ["registry", "mapping"])
def test_registry_or_mapping_difference_is_reconciled(tmp_path, component):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    if component == "registry":
        hermes.projects["project-test"] = project_output("project-test", str(tmp_path))
    else:
        config.values["platforms.discord.extra.channel_project_bindings.123456789"] = "other-project"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    expected_operation = "create" if component == "registry" else "reconcile"
    assert result["components"][component]["operation"] == expected_operation
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.values["platforms.discord.extra.channel_project_bindings.123456789"] == "project-test"


def test_empty_existing_registry_readback_is_reconciled(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    hermes.projects["project-test"] = ""

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["registry"]["operation"] == "create"
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.writes


def test_apply_uses_injected_hermes_config_cli_and_direct_readback(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, _, _ = adapters(tmp_path)
    injected = EnrollmentAdapters(
        filesystem=LocalFilesystem(),
        subprocess=hermes,
        config=HermesConfig(hermes),
    )

    result = apply_enrollment(request(root, executable, config_target), injected)

    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    set_command = [str(executable), "config", "set", "--force", mapping_key, "project-test"]
    assert result["status"] == "applied"
    assert set_command in hermes.commands
    set_index = hermes.commands.index(set_command)
    assert [str(executable), "config", "get", "--json", mapping_key] in hermes.commands[set_index + 1 :]
    create_index = next(
        index for index, command in enumerate(hermes.commands) if command[1:3] == ["project", "create"]
    )
    assert [str(executable), "project", "show", "project-test"] in hermes.commands[create_index + 1 :]


@pytest.mark.parametrize("mapping_value", [123, True, None, ["project-test"], {"slug": "project-test"}])
def test_apply_reconciles_non_string_json_mapping_readback(tmp_path, mapping_value):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, _, _ = adapters(tmp_path)
    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    hermes.config_values[mapping_key] = mapping_value
    injected = EnrollmentAdapters(
        filesystem=LocalFilesystem(),
        subprocess=hermes,
        config=HermesConfig(hermes),
    )

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["mapping"]["operation"] == "reconcile"
    assert [str(executable), "config", "get", "--json", mapping_key] in hermes.commands
    assert hermes.config_values[mapping_key] == "project-test"


def test_partial_registry_failure_reports_actual_state_and_reapply_converges_idempotently(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    hermes.create_failures = 1

    partial = apply_enrollment(request(root, executable, config_target), injected)

    assert partial["status"] == "partial"
    assert [
        partial["components"][name]["operation"] for name in ("manifest", "registry", "mapping")
    ] == [
        "create",
        "create",
        "create",
    ]
    assert config.writes == []

    converged = apply_enrollment(request(root, executable, config_target), injected)
    writes_after_convergence = len(config.writes)
    create_commands_after_convergence = len(
        [command for command in hermes.commands if command[1:3] == ["project", "create"]]
    )
    second_event = request(root, executable, config_target)
    second_event = EnrollmentRequest(
        version=second_event.version,
        project_slug=second_event.project_slug,
        canonical_root=second_event.canonical_root,
        discord_parent_channel_id=second_event.discord_parent_channel_id,
        hermes_executable=second_event.hermes_executable,
        hermes_config_target=second_event.hermes_config_target,
        idempotency_key="event-2",
    )
    reapplied = apply_enrollment(second_event, injected)

    assert converged["status"] == "applied"
    assert reapplied["status"] == "noop"
    assert reapplied["idempotency_key"] == "event-2"
    assert len(config.writes) == writes_after_convergence
    assert len(
        [command for command in hermes.commands if command[1:3] == ["project", "create"]]
    ) == create_commands_after_convergence


@pytest.mark.parametrize("case", ["malformed", "nonregular"])
def test_manifest_observation_preserves_object_and_does_not_block_registry_reconcile(tmp_path, case):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    manifest = root / "manifest.yml"
    if case == "malformed":
        manifest.write_text("workspace: [unterminated\n", encoding="utf-8")
    else:
        manifest.mkdir()
    original = None if manifest.is_dir() else manifest.read_bytes()

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["manifest"]["operation"] == "noop"
    assert result["components"]["manifest"]["observations"]
    assert hermes.projects["project-test"] == project_output("project-test", str(root))
    assert config.values["platforms.discord.extra.channel_project_bindings.123456789"] == "project-test"
    if original is None:
        assert manifest.is_dir()
    else:
        assert manifest.read_bytes() == original


def test_config_target_mismatch_does_not_block_registry_reconcile(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, _, hermes, _, injected = adapters(tmp_path)
    requested_target = (tmp_path / "different-config.yaml").resolve()

    result = apply_enrollment(request(root, executable, requested_target), injected)

    assert result["status"] == "applied"
    assert result["components"]["config_target"]["observations"] == ["target_mismatch"]
    assert hermes.projects["project-test"] == project_output("project-test", str(root))


def test_stale_mapping_is_rewritten_only_after_resolved_registry_slug_readback(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    config.values[mapping_key] = "other-project"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "applied"
    assert config.writes == [(executable, mapping_key, "project-test")]
    create_index = next(i for i, command in enumerate(hermes.commands) if command[1:3] == ["project", "create"])
    assert any(command[1:3] == ["project", "show"] for command in hermes.commands[create_index + 1 :])


def test_same_root_different_native_slug_does_not_create(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, _, injected = adapters(tmp_path)
    hermes.projects["native-project"] = project_output("native-project", str(root))

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["components"]["registry"]["operation"] == "noop"
    assert not any(command[1:3] == ["project", "create"] for command in hermes.commands)


def test_same_root_different_mapping_label_is_not_rewritten(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    hermes.projects["native-project"] = project_output("native-project", str(root))
    config.values[mapping_key] = "native-project"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["components"]["mapping"]["operation"] == "noop"
    assert config.writes == []


def test_manifest_slug_mismatch_is_ignored(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    (root / "manifest.yml").write_text(
        "schema: harness.project-manifest.v2\n"
        "project_slug: unrelated-label\n"
        "workspace:\n"
        f"  canonical_cwd: {root}\n",
        encoding="utf-8",
    )
    hermes.projects["native-project"] = project_output("native-project", str(root))
    config.values[mapping_key] = "native-project"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "noop"
    assert result["components"]["manifest"]["observations"] == []


def test_different_root_mapping_rewrites_only_to_root_resolved_native_slug(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    other_root = (tmp_path / "other-project").resolve()
    other_root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    mapping_key = "platforms.discord.extra.channel_project_bindings.123456789"
    hermes.projects["root-native"] = project_output("root-native", str(root))
    hermes.projects["mapped-elsewhere"] = project_output("mapped-elsewhere", str(other_root))
    config.values[mapping_key] = "mapped-elsewhere"

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["components"]["registry"]["operation"] == "noop"
    assert config.writes == [(executable, mapping_key, "root-native")]
    assert not any(command[1:3] == ["project", "create"] for command in hermes.commands)


def test_registry_readback_failure_records_partial_receipt_without_guessed_mapping(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)
    hermes.readback_failures_after_create = 1

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "partial"
    assert result["components"]["registry"]["receipts"] == [
        {"status": "partial", "error": "Hermes project read failed: injected readback failure"}
    ]
    assert config.writes == []


def test_manifest_read_failure_records_partial_receipt_without_blocking_registry(tmp_path):
    root = (tmp_path / "project").resolve()
    root.mkdir()
    (root / "manifest.yml").write_text("present\n", encoding="utf-8")
    executable, config_target, hermes, config, _ = adapters(tmp_path)
    injected = EnrollmentAdapters(
        filesystem=FailingReadFilesystem(),
        subprocess=hermes,
        config=config,
    )

    result = apply_enrollment(request(root, executable, config_target), injected)

    assert result["status"] == "partial"
    assert result["components"]["manifest"]["receipts"] == [
        {"status": "partial", "error": "injected manifest read failure"}
    ]
    assert hermes.projects["project-test"] == project_output("project-test", str(root))


def test_enrollment_cli_requires_explicit_inputs_and_uses_injected_adapters(tmp_path, capsys):
    from harness_runtime.enrollment_cli import main

    root = (tmp_path / "project").resolve()
    root.mkdir()
    executable, config_target, hermes, config, injected = adapters(tmp_path)

    exit_code = main(
        [
            "plan",
            "--version",
            "1",
            "--project-slug",
            "project-test",
            "--canonical-root",
            str(root),
            "--discord-parent-channel-id",
            "123456789",
            "--hermes-executable",
            str(executable),
            "--hermes-config-target",
            str(config_target),
            "--idempotency-key",
            "event-1",
        ],
        adapters=injected,
    )

    assert exit_code == 0
    assert '"status": "planned"' in capsys.readouterr().out
    assert not (root / "manifest.yml").exists()
    assert hermes.projects == {}
    assert config.writes == []
