from __future__ import annotations

import copy
import hashlib
from types import MappingProxyType

import pytest

from acfqp import (
    construction_k7_standard_2048_formal_transport_successor_v42r3 as formal,
)
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import v42_standard_2048_formal_transport_loader_v42r3 as loader


def _source_fact(relative: str, index: int) -> dict[str, object]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": format(index + 1, "040x"),
        "byte_count": index + 1,
        "sha256": format(index + 1, "064x"),
    }


def _manifest() -> dict[str, object]:
    return formal.build_controller_source_manifest_v42r3(
        source_commit="a" * 40,
        source_tree="b" * 40,
        source_facts=[
            _source_fact(relative, index)
            for index, relative in enumerate(formal.CONTROLLER_TCB_PATHS)
        ],
    )


def _python_observation() -> dict[str, object]:
    return {
        "python_invocation_path": "/usr/bin/python3",
        "python_invocation_node_type": "SYMLINK",
        "python_invocation_link_target": "python3.12",
        "python_invocation_mode": 0o777,
        "python_invocation_uid": 0,
        "python_invocation_gid": 0,
        "python_invocation_nlink": 1,
        "python_realpath": "/usr/bin/python3.12",
        "python_realpath_node_type": "REGULAR_FILE",
        "python_realpath_mode": 0o755,
        "python_realpath_uid": 0,
        "python_realpath_gid": 0,
        "python_realpath_nlink": 1,
        "python_realpath_sha256": formal._PYTHON_REALPATH_SHA256,  # noqa: SLF001
        "python_realpath_byte_count": formal._PYTHON_REALPATH_BYTE_COUNT,  # noqa: SLF001
        "python_version": [3, 12, 3],
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }


def _root_memory_ancestry() -> list[dict[str, object]]:
    return [
        {
            "cgroup_path": "/",
            "memory_max_mode": "MAX",
            "memory_max_bytes": None,
            "memory_current_bytes": 1,
        }
    ]


def _native_inputs() -> dict[str, object]:
    id_fields = (
        "activation_successor_source_manifest_id",
        "activation_successor_read_only_plan_id",
        "activation_successor_path_provenance_receipt_id",
        "activation_successor_classification_id",
        "activation_successor_read_only_snapshot_id",
        "activation_successor_final_evidence_index_id",
        "predecessor_materialization_activation_plan_id",
        "predecessor_activation_read_only_snapshot_tail_id",
        "predecessor_activation_classification_id",
        "predecessor_remote_materialization_transport_terminal_id",
        "preactivation_resource_result_id",
        "source_manifest_id",
        "transport_manifest_id",
        "local_materialization_attempt_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "non_authoritative_compatibility_artifact_id",
    )
    values: dict[str, object] = {
        field: format(index, "064x")
        for index, field in enumerate(id_fields, start=1)
    }
    values.update(
        {
            "formal_identity": (
                "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
            ),
            "global_execution_ordinal": 2,
            "preactivation_observed_python": _python_observation(),
            "preactivation_cgroup_memory_ancestry": _root_memory_ancestry(),
            "preactivation_memory_total_bytes": 256 * 1024**3,
            "preactivation_memory_available_bytes": 128 * 1024**3,
            "preactivation_all_resource_gates_passed": True,
            "preactivation_read_only_observation_completed": True,
            "preactivation_remote_mutation_performed": False,
            "source_commit": "c" * 40,
            "source_tree": "d" * 40,
            "fixed_remote_root": (
                "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
            ),
            "remote_source_root": (
                "/home/erzhu419/mine_code/"
                ".acfqp-v42-remote-ordinal2/source"
            ),
            "remote_target_alias": "jtl110gpu2",
            "expected_remote_hostname": "erzhu419-Super-Server",
            "observed_remote_hostname": "erzhu419-Super-Server",
            "observed_remote_user": "erzhu419",
            "observed_remote_uid": 1000,
            "observed_remote_gid": 1000,
            "legacy_activation_final_evidence_index_claimed": False,
            "legacy_snapshot_or_final_synthesized": False,
            "activation_effect_replay_authorized": False,
            "native_nested_path_evidence_complete": True,
        }
    )
    return values


def _binding() -> dict[str, object]:
    return formal.build_native_activation_binding_v42r3(
        native_activation_inputs=_native_inputs()
    )


def _plan() -> dict[str, object]:
    return formal.build_formal_host_epoch_probe_plan_v42r3(
        controller_source_manifest=_manifest(),
        native_activation_binding=_binding(),
        legacy_execution_source_manifest_id="e" * 64,
    )


def _runtime() -> dict[str, object]:
    return {
        "hostname": "erzhu419-Super-Server",
        "user": "erzhu419",
        "uid": 1000,
        "gid": 1000,
        "python_invocation": "/usr/bin/python3",
        "python_realpath": "/usr/bin/python3.12",
        "python_version": [3, 12, 3],
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }


def _manager() -> dict[str, object]:
    return {
        "kernel_boot_id": "11111111-1111-4111-8111-111111111111",
        "linger_enabled": True,
        "linger_path": "/var/lib/systemd/linger/erzhu419",
        "user_manager_invocation_id": (
            "22222222-2222-4222-8222-222222222222"
        ),
        "user_manager_main_pid": 1234,
        "user_manager_control_group": (
            "/user.slice/user-1000.slice/user@1000.service"
        ),
    }


def _manager_memory_ancestry() -> list[dict[str, object]]:
    return [
        {
            "cgroup_path": "/user.slice/user-1000.slice/user@1000.service",
            "memory_max_mode": "MAX",
            "memory_max_bytes": None,
            "memory_current_bytes": 1,
        },
        {
            "cgroup_path": "/user.slice/user-1000.slice",
            "memory_max_mode": "MAX",
            "memory_max_bytes": None,
            "memory_current_bytes": 2,
        },
        {
            "cgroup_path": "/user.slice",
            "memory_max_mode": "MAX",
            "memory_max_bytes": None,
            "memory_current_bytes": 3,
        },
        {
            "cgroup_path": "/",
            "memory_max_mode": "MAX",
            "memory_max_bytes": None,
            "memory_current_bytes": 4,
        },
    ]


def _resources() -> dict[str, object]:
    return {
        "memory_total_bytes": 256 * 1024**3,
        "memory_available_bytes": 128 * 1024**3,
        "swap_total_bytes": 0,
        "swap_free_bytes": 0,
        "filesystem_available_bytes": 64 * 1024**3,
        "cgroup_mount_point": "/sys/fs/cgroup",
        "cgroup_mount_filesystem_type": "cgroup2",
        "cgroup_mount_root": "/",
        "cgroup_controllers": ["cpu", "memory", "pids"],
        "memory_limit_ancestry": _manager_memory_ancestry(),
    }


def _tools() -> dict[str, dict[str, object]]:
    paths = {
        "env": "/usr/bin/env",
        "python": "/usr/bin/python3.12",
        "systemctl": "/usr/bin/systemctl",
        "systemd_run": "/usr/bin/systemd-run",
    }
    return {
        name: {
            "path": path,
            "sha256": format(index, "064x"),
            "byte_count": index,
            "mode": 0o755,
            "uid": 0,
            "gid": 0,
            "st_nlink": 1,
        }
        for index, (name, path) in enumerate(paths.items(), start=1)
    }


def _effect_manifest() -> dict[str, object]:
    raw_by_relative = {
        formal.PROBE_LOADER_RELATIVE: b"loader source\n",
        formal.FORMAL_AUTHORITY_RELATIVE: b"authority source\n",
        formal.PROBE_RECEIVER_RELATIVE: b"receiver source\n",
    }
    facts = [
        _source_fact(relative, index)
        for index, relative in enumerate(formal.CONTROLLER_TCB_PATHS)
    ]
    for fact in facts:
        relative = str(fact["relative_path"])
        if relative in raw_by_relative:
            raw = raw_by_relative[relative]
            fact["byte_count"] = len(raw)
            fact["sha256"] = hashlib.sha256(raw).hexdigest()
    return formal.build_controller_source_manifest_v42r3(
        source_commit="a" * 40,
        source_tree="b" * 40,
        source_facts=facts,
    )


def _effect_probe_plan() -> dict[str, object]:
    return formal.build_formal_host_epoch_probe_plan_v42r3(
        controller_source_manifest=_effect_manifest(),
        native_activation_binding=_binding(),
        legacy_execution_source_manifest_id="e" * 64,
    )


def _host_receipt() -> dict[str, object]:
    return formal.build_formal_host_epoch_receipt_v42r3(
        probe_plan=_effect_probe_plan(),
        observed_runtime=_runtime(),
        manager_binding=_manager(),
        resource_observation=_resources(),
        remote_tool_facts=_tools(),
        formal_successor_journal_state="ABSENT",
    )


def _transport_plan() -> dict[str, object]:
    return formal.build_formal_transport_plan_v42r3(
        controller_source_manifest=_effect_manifest(),
        native_activation_binding=_binding(),
        host_epoch_probe_plan=_effect_probe_plan(),
        host_epoch_receipt=_host_receipt(),
        legacy_execution_source_manifest_id="e" * 64,
        known_hosts_path=str(
            formal.LOCAL_FORMAL_JOURNAL_ROOT / formal.LOCAL_KNOWN_HOSTS_NAME
        ),
        local_journal_root=str(formal.LOCAL_FORMAL_JOURNAL_ROOT),
        remote_journal_root=str(formal.REMOTE_FORMAL_JOURNAL_ROOT),
    )


def _scientific_prepare_receipt() -> dict[str, object]:
    plan = _transport_plan()
    return {
        "prepare_receipt_id": "9" * 64,
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
    }


def _local_launch_attempt() -> dict[str, object]:
    return {
        "local_launch_attempt_id": "8" * 64,
        "prepare_receipt_id": "9" * 64,
        "transport_target_alias": "jtl110gpu2",
    }


def _launch_transport_attempt() -> dict[str, object]:
    return formal.build_formal_launch_transport_attempt_v42r3(
        formal_transport_plan=_transport_plan(),
        prepare_receipt=_scientific_prepare_receipt(),
        local_launch_attempt=_local_launch_attempt(),
    )


def _service_bootstrap_argv() -> tuple[str, ...]:
    plan = _transport_plan()
    loader_raw = b"loader source\n"
    plan_raw = canonical_json_bytes(plan)
    return (
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-c",
        loader_raw.decode("utf-8"),
        formal.SERVICE_BOOTSTRAP_MODE,
        hashlib.sha256(loader_raw).hexdigest(),
        str(len(loader_raw)),
        "7" * 64,
        "123",
        plan["formal_authority_artifact"]["sha256"],
        str(plan["formal_authority_artifact"]["byte_count"]),
        plan["probe_receiver_artifact"]["sha256"],
        str(plan["probe_receiver_artifact"]["byte_count"]),
        hashlib.sha256(plan_raw).hexdigest(),
        str(len(plan_raw)),
        plan["formal_transport_plan_id"],
        plan["legacy_execution_source_manifest_id"],
        "8" * 64,
    )


def _unit_observation() -> dict[str, object]:
    attempt_id = "8" * 64
    invocation = "12345678-1234-4234-8234-123456789abc"
    name = formal.unit_name_v42r3(attempt_id)
    control_group = (
        str(_manager()["user_manager_control_group"])
        + "/app.slice/"
        + name
    )
    wrapper = list(_service_bootstrap_argv())
    wrapper[6] = formal.SERVICE_WRAPPER_MODE
    wrapper.extend((invocation, control_group))
    return {
        "Id": name,
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "Result": "success",
        "InvocationID": invocation,
        "MainPID": 9876,
        "ControlGroup": control_group,
        "Type": "exec",
        "Restart": "no",
        "RemainAfterExit": "yes",
        "SuccessExitStatus": "2",
        "UMask": "0077",
        "KillMode": "mixed",
        "TimeoutStopUSec": "30s",
        "RuntimeMaxUSec": "1w 25min",
        "StandardInput": "null",
        "StandardOutput": "null",
        "StandardError": "null",
        "WorkingDirectory": str(_transport_plan()["fixed_source_root"]),
        "Slice": formal.SYSTEMD_SLICE,
        "FragmentPath": "/run/user/1000/systemd/transient/" + name,
        "Environment": "",
        "LiveMainPIDArgv": wrapper,
        "LiveMainPIDArgvSource": "PROC_MAINPID_CMDLINE",
    }


def _admission_receipt() -> dict[str, object]:
    plan = _transport_plan()
    argv = formal.build_systemd_run_argv_v42r3(
        formal_transport_plan=plan,
        local_launch_attempt=_local_launch_attempt(),
        service_bootstrap_argv=_service_bootstrap_argv(),
    )
    return formal.build_launch_admission_receipt_v42r3(
        formal_transport_plan=plan,
        launch_transport_attempt=_launch_transport_attempt(),
        manager_binding=_manager(),
        unit_observation=_unit_observation(),
        systemd_run_argv=argv,
    )


def test_controller_manifest_is_exact_sorted_33_file_tcb_and_round_trips() -> None:
    manifest = _manifest()
    assert len(manifest["source_facts"]) == 33
    assert [row["relative_path"] for row in manifest["source_facts"]] == list(
        formal.CONTROLLER_TCB_PATHS
    )
    assert formal.verify_controller_source_manifest_v42r3(
        MappingProxyType(manifest)
    ) == manifest
    assert formal.verify_controller_source_manifest_v42r3(
        canonical_json_bytes(manifest)
    ) == manifest


def test_controller_manifest_rejects_inventory_and_noncanonical_bytes() -> None:
    facts = list(_manifest()["source_facts"])
    facts[0], facts[1] = facts[1], facts[0]
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_controller_source_manifest_v42r3(
            source_commit="a" * 40,
            source_tree="b" * 40,
            source_facts=facts,
        )
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_controller_source_manifest_v42r3(
            canonical_json_bytes(_manifest()) + b"\n"
        )


def test_native_binding_is_native_only_and_normalizes_fixed_source_root() -> None:
    binding = _binding()
    assert binding["fixed_source_root"] == (
        "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2/source"
    )
    assert "remote_source_root" not in binding
    assert "production_activation_core_id" not in binding
    assert "materialization_activation_final_evidence_index_id" not in binding
    assert "non_authoritative_compatibility_artifact_id" in binding
    assert binding["activation_effect_replay_authorized"] is False
    assert "preactivation_read_only_observation_completed" not in binding
    assert "preactivation_remote_mutation_performed" not in binding
    assert binding[
        "legacy_document_claim_preactivation_read_only_observation_completed"
    ] is True
    assert binding[
        "legacy_document_claim_preactivation_remote_mutation_performed"
    ] is False
    assert binding["legacy_end_to_end_mutation_absence_adopted"] is False
    assert binding[
        "legacy_ssh_ingress_noninterference_is_external_assumption"
    ] is True
    assert formal.verify_native_activation_binding_v42r3(
        canonical_json_bytes(binding)
    ) == binding


def test_native_binding_rejects_legacy_production_and_runtime_splices() -> None:
    production = _native_inputs()
    production["production_activation_core_id"] = "f" * 64
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_native_activation_binding_v42r3(
            native_activation_inputs=production
        )
    changed_runtime = _native_inputs()
    changed_runtime["preactivation_observed_python"] = copy.deepcopy(
        changed_runtime["preactivation_observed_python"]
    )
    changed_runtime["preactivation_observed_python"]["python_version"] = [
        3,
        12,
        4,
    ]
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_native_activation_binding_v42r3(
            native_activation_inputs=changed_runtime
        )


def test_probe_plan_binds_three_exact_controller_artifacts_and_native_final() -> None:
    manifest = _manifest()
    binding = _binding()
    plan = formal.build_formal_host_epoch_probe_plan_v42r3(
        controller_source_manifest=manifest,
        native_activation_binding=binding,
        legacy_execution_source_manifest_id="e" * 64,
    )
    facts = {row["relative_path"]: row for row in manifest["source_facts"]}
    assert plan["probe_loader_artifact"] == facts[formal.PROBE_LOADER_RELATIVE]
    assert plan["formal_authority_artifact"] == facts[
        formal.FORMAL_AUTHORITY_RELATIVE
    ]
    assert plan["probe_receiver_artifact"] == facts[
        formal.PROBE_RECEIVER_RELATIVE
    ]
    assert plan["native_activation_binding"] == binding
    local_stage0 = plan["external_local_stage0_assumption"]
    ssh_ingress = plan["external_ssh_ingress_assumption"]
    assert local_stage0["assumption_observed_or_attested_by_campaign"] is False
    assert local_stage0["actual_stage0_execution_observed_or_attested"] is False
    assert local_stage0[
        "root_owned_local_entry_broker_attestation_present"
    ] is False
    assert plan["external_local_stage0_assumption_id"] == local_stage0[
        "external_local_stage0_assumption_id"
    ]
    assert ssh_ingress["assumption_observed_or_attested_by_campaign"] is False
    assert ssh_ingress["root_controlled_ingress_attestation_present"] is False
    assert ssh_ingress[
        "root_owned_nonwritable_campaign_parent_attestation_present"
    ] is False
    assert ssh_ingress[
        "assumed_no_concurrent_parent_writable_actor_replaces_campaign_paths_"
        "during_authenticated_remote_operation"
    ] is True
    assert ssh_ingress[
        "admission_is_conditional_on_remote_path_noninterference"
    ] is True
    assert plan["external_ssh_ingress_assumption_id"] == ssh_ingress[
        "external_ssh_ingress_assumption_id"
    ]
    assert plan["authenticated_loader_and_receiver_probe_is_read_only"] is True
    assert plan[
        "authenticated_loader_and_receiver_remote_mutation_authorized"
    ] is False
    assert plan["end_to_end_remote_mutation_absence_claimed"] is False
    assert plan["activation_effect_replay_authorized"] is False
    assert formal.verify_formal_host_epoch_probe_plan_v42r3(
        canonical_json_bytes(plan)
    ) == plan


def test_host_epoch_receipt_round_trips_and_rejects_mutation_or_failed_gate() -> None:
    receipt = formal.build_formal_host_epoch_receipt_v42r3(
        probe_plan=_plan(),
        observed_runtime=_runtime(),
        manager_binding=_manager(),
        resource_observation=_resources(),
        remote_tool_facts=_tools(),
        formal_successor_journal_state="ABSENT",
    )
    assert receipt[
        "authenticated_loader_and_receiver_observation_was_read_only"
    ] is True
    assert receipt[
        "authenticated_loader_and_receiver_remote_mutation_performed"
    ] is False
    assert receipt[
        "authenticated_loader_and_receiver_systemd_lifecycle_mutation_performed"
    ] is False
    assert receipt["formal_successor_journal_state_at_probe"] == "ABSENT"
    assert receipt["end_to_end_remote_mutation_absence_claimed"] is False
    assert receipt["end_to_end_systemd_mutation_absence_claimed"] is False
    assert receipt["activation_effect_replay_authorized"] is False
    assert formal.verify_formal_host_epoch_receipt_v42r3(
        canonical_json_bytes(receipt)
    ) == receipt

    mutated = copy.deepcopy(receipt)
    mutated["authenticated_loader_and_receiver_remote_mutation_performed"] = True
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_formal_host_epoch_receipt_v42r3(mutated)

    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_formal_host_epoch_receipt_v42r3(
            probe_plan=_plan(),
            observed_runtime=_runtime(),
            manager_binding=_manager(),
            resource_observation=_resources(),
            remote_tool_facts=_tools(),
            formal_successor_journal_state="DIRECTORY",
        )

    resources = _resources()
    resources["memory_available_bytes"] = 1
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_formal_host_epoch_receipt_v42r3(
            probe_plan=_plan(),
            observed_runtime=_runtime(),
            manager_binding=_manager(),
            resource_observation=resources,
            remote_tool_facts=_tools(),
            formal_successor_journal_state="ABSENT",
        )


def test_probe_attempt_and_transport_observation_are_one_shot_and_auditable() -> None:
    plan = _plan()
    attempt = formal.build_formal_host_epoch_probe_attempt_v42r3r3(
        probe_plan=plan
    )
    assert attempt["controller_same_probe_dispatch_replay_allowed"] is False
    assert attempt["network_dispatch_started_at_publication"] is False
    assert formal.verify_formal_host_epoch_probe_attempt_v42r3r3(
        canonical_json_bytes(attempt), probe_plan=plan
    ) == attempt

    receipt = formal.build_formal_host_epoch_receipt_v42r3(
        probe_plan=plan,
        observed_runtime=_runtime(),
        manager_binding=_manager(),
        resource_observation=_resources(),
        remote_tool_facts=_tools(),
        formal_successor_journal_state="ABSENT",
    )
    receipt_raw = canonical_json_bytes(receipt)
    stdout = receipt_raw + b"\n"
    stdout_prefix = stdout[:4096]
    child = {
        "exec_succeeded": True,
        "returncode": 0,
        "timed_out": False,
        "stdin_expected_byte_count": 123,
        "stdin_sent_byte_count": 123,
        "stdin_complete": True,
        "stdout_retained_byte_count": len(stdout),
        "stdout_retained_sha256": hashlib.sha256(stdout).hexdigest(),
        "stdout_prefix_byte_count": len(stdout_prefix),
        "stdout_prefix_hex": stdout_prefix.hex(),
        "stdout_total_byte_count": len(stdout),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stdout_overflow": False,
        "stdout_eof": True,
        "stderr_prefix_byte_count": 0,
        "stderr_prefix_hex": "",
        "stderr_total_byte_count": 0,
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_overflow": False,
        "stderr_eof": True,
    }
    observation = (
        formal.build_formal_host_epoch_transport_observation_v42r3r3(
            probe_plan=plan,
            probe_attempt=attempt,
            child_observation=child,
        )
    )
    assert observation["process_closed_exactly"] is True
    assert observation["controller_same_probe_dispatch_replay_allowed"] is False
    assert observation[
        "formal_host_epoch_receipt_authenticated_by_this_observation"
    ] is False
    assert formal.verify_formal_host_epoch_transport_observation_v42r3r3(
        canonical_json_bytes(observation),
        probe_plan=plan,
        probe_attempt=attempt,
    ) == observation
    assert formal.verify_formal_host_epoch_transport_receipt_join_v42r3r3(
        transport_observation=observation,
        probe_plan=plan,
        probe_attempt=attempt,
        receipt_raw=receipt_raw,
    ) == receipt
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_formal_host_epoch_transport_receipt_join_v42r3r3(
            transport_observation=observation,
            probe_plan=plan,
            probe_attempt=attempt,
            receipt_raw=receipt_raw + b"\n",
        )

    failed_child = copy.deepcopy(child)
    failed_child.update(
        exec_succeeded=True,
        returncode=255,
        stderr_prefix_byte_count=11,
        stderr_prefix_hex=b"ssh failure".hex(),
        stderr_total_byte_count=11,
        stderr_sha256=hashlib.sha256(b"ssh failure").hexdigest(),
    )
    failed = formal.build_formal_host_epoch_transport_observation_v42r3r3(
        probe_plan=plan,
        probe_attempt=attempt,
        child_observation=failed_child,
    )
    assert failed["process_closed_exactly"] is False
    assert failed["end_to_end_remote_mutation_absence_claimed"] is False

    overflow_prefix = b"x" * 4096
    overflow_child = copy.deepcopy(child)
    overflow_child.update(
        stdout_retained_byte_count=64 * 1024**2 + 1,
        stdout_retained_sha256="1" * 64,
        stdout_prefix_byte_count=len(overflow_prefix),
        stdout_prefix_hex=overflow_prefix.hex(),
        stdout_total_byte_count=64 * 1024**2 + 1,
        stdout_sha256="2" * 64,
        stdout_overflow=True,
    )
    overflow = formal.build_formal_host_epoch_transport_observation_v42r3r3(
        probe_plan=plan,
        probe_attempt=attempt,
        child_observation=overflow_child,
    )
    assert overflow["process_closed_exactly"] is False
    malformed_overflow = copy.deepcopy(overflow_child)
    malformed_overflow["stdout_retained_byte_count"] = 64 * 1024**2
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_formal_host_epoch_transport_observation_v42r3r3(
            probe_plan=plan,
            probe_attempt=attempt,
            child_observation=malformed_overflow,
        )

    message = b"local dispatch failed"
    failure = formal.build_formal_host_epoch_dispatch_failure_v42r3r3(
        probe_plan=plan,
        probe_attempt=attempt,
        failure_fact={
            "failure_type": "builtins.RuntimeError",
            "message_byte_count": len(message),
            "message_sha256": hashlib.sha256(message).hexdigest(),
            "message_prefix_byte_count": len(message),
            "message_prefix_hex": message.hex(),
        },
    )
    assert failure["controller_same_probe_dispatch_replay_allowed"] is False
    assert failure["network_dispatch_may_have_started"] is True
    assert formal.verify_formal_host_epoch_dispatch_failure_v42r3r3(
        canonical_json_bytes(failure),
        probe_plan=plan,
        probe_attempt=attempt,
    ) == failure

    changed = copy.deepcopy(observation)
    changed["process_closed_exactly"] = False
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_formal_host_epoch_transport_observation_v42r3r3(
            changed, probe_plan=plan, probe_attempt=attempt
        )


def test_loader_failure_join_authenticates_exact_bounded_stderr_only() -> None:
    plan = _plan()
    attempt = formal.build_formal_host_epoch_probe_attempt_v42r3r3(
        probe_plan=plan
    )

    def _child(
        stderr: bytes, *, stdout: bytes = b"", returncode: int = 73,
    ) -> dict[str, object]:
        stderr_prefix = stderr[:4096]
        stdout_prefix = stdout[:4096]
        return {
            "exec_succeeded": True,
            "returncode": returncode,
            "timed_out": False,
            "stdin_expected_byte_count": 123,
            "stdin_sent_byte_count": 123,
            "stdin_complete": True,
            "stdout_retained_byte_count": len(stdout),
            "stdout_retained_sha256": hashlib.sha256(stdout).hexdigest(),
            "stdout_prefix_byte_count": len(stdout_prefix),
            "stdout_prefix_hex": stdout_prefix.hex(),
            "stdout_total_byte_count": len(stdout),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stdout_overflow": False,
            "stdout_eof": True,
            "stderr_prefix_byte_count": len(stderr_prefix),
            "stderr_prefix_hex": stderr_prefix.hex(),
            "stderr_total_byte_count": len(stderr),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stderr_overflow": False,
            "stderr_eof": True,
        }

    try:
        raise RuntimeError("authenticated receiver failure")
    except RuntimeError as error:
        diagnostic_raw = loader._loader_failure_stderr(error)  # noqa: SLF001
    observation = formal.build_formal_host_epoch_transport_observation_v42r3r3(
        probe_plan=plan,
        probe_attempt=attempt,
        child_observation=_child(diagnostic_raw),
    )
    diagnostic = formal.verify_formal_host_epoch_loader_failure_join_v42r3r3(
        transport_observation=observation,
        probe_plan=plan,
        probe_attempt=attempt,
    )
    assert diagnostic["schema"] == loader.LOADER_FAILURE_DIAGNOSTIC_SCHEMA
    assert diagnostic["diagnostic_builder_succeeded"] is True

    producer_invalid = []
    changed = copy.deepcopy(diagnostic)
    changed["message"]["scanned_character_count"] -= 1
    producer_invalid.append(changed)
    changed = copy.deepcopy(diagnostic)
    changed["exception_module"]["truncated"] = True
    producer_invalid.append(changed)
    changed = copy.deepcopy(diagnostic)
    changed["traceback_frames"] = changed["traceback_frames"][:-1]
    producer_invalid.append(changed)
    changed = copy.deepcopy(diagnostic)
    changed["exception_module"] = {
        "prefix_byte_count": 1,
        "prefix_hex": "ff",
        "truncated": False,
    }
    producer_invalid.append(changed)
    changed = copy.deepcopy(diagnostic)
    impossible_message = b"abcde"
    changed["message"] = {
        "character_count": 1,
        "scan_complete": True,
        "scanned_character_count": 1,
        "scanned_byte_count": len(impossible_message),
        "scanned_sha256": hashlib.sha256(impossible_message).hexdigest(),
        "prefix_byte_count": len(impossible_message),
        "prefix_hex": impossible_message.hex(),
        "prefix_truncated": False,
    }
    producer_invalid.append(changed)
    for impossible_byte_count in (6 * 4096 - 1, 6 * 4096):
        changed = copy.deepcopy(diagnostic)
        impossible_prefix = b"x" * 256
        changed["message"] = {
            "character_count": 5000,
            "scan_complete": False,
            "scanned_character_count": 4096,
            "scanned_byte_count": impossible_byte_count,
            "scanned_sha256": "0" * 64,
            "prefix_byte_count": len(impossible_prefix),
            "prefix_hex": impossible_prefix.hex(),
            "prefix_truncated": True,
        }
        producer_invalid.append(changed)
    for changed in producer_invalid:
        changed_raw = canonical_json_bytes(changed) + b"\n"
        changed_observation = (
            formal.build_formal_host_epoch_transport_observation_v42r3r3(
                probe_plan=plan,
                probe_attempt=attempt,
                child_observation=_child(changed_raw),
            )
        )
        with pytest.raises(formal.V42FormalTransportSuccessorError):
            formal.verify_formal_host_epoch_loader_failure_join_v42r3r3(
                transport_observation=changed_observation,
                probe_plan=plan,
                probe_attempt=attempt,
            )

    legal_diagnostics = []
    try:
        raise RuntimeError("\ud800")
    except RuntimeError as error:
        legal_diagnostics.append(
            loader._loader_failure_stderr(error)  # noqa: SLF001
        )
    for long_message in (
        "\ud800" * 5000,
        "\N{SNOWMAN}" * 5000,
        "x" * 5000,
    ):
        try:
            raise RuntimeError(long_message)
        except RuntimeError as error:
            legal_diagnostics.append(
                loader._loader_failure_stderr(error)  # noqa: SLF001
            )
    multibyte_type = type(
        "MultibyteError",
        (Exception,),
        {"__module__": "\N{SNOWMAN}" * 100},
    )
    try:
        raise multibyte_type("multibyte prefix cut")
    except Exception as error:
        legal_diagnostics.append(
            loader._loader_failure_stderr(error)  # noqa: SLF001
        )
    line_zero_code = compile(
        "raise RuntimeError('line zero')",
        "<line-zero>",
        "exec",
        flags=0,
        dont_inherit=True,
        optimize=0,
    ).replace(co_firstlineno=0)
    try:
        exec(line_zero_code, {})
    except RuntimeError as error:
        line_zero_raw = loader._loader_failure_stderr(error)  # noqa: SLF001
        legal_diagnostics.append(line_zero_raw)
    for legal_raw in legal_diagnostics:
        legal_observation = (
            formal.build_formal_host_epoch_transport_observation_v42r3r3(
                probe_plan=plan,
                probe_attempt=attempt,
                child_observation=_child(legal_raw),
            )
        )
        formal.verify_formal_host_epoch_loader_failure_join_v42r3r3(
            transport_observation=legal_observation,
            probe_plan=plan,
            probe_attempt=attempt,
        )
    line_zero = loader._canonical_document(  # noqa: SLF001
        line_zero_raw[:-1], "line-zero diagnostic"
    )
    assert any(
        frame["line_number"] == 0 for frame in line_zero["traceback_frames"]
    )

    fallback_observation = (
        formal.build_formal_host_epoch_transport_observation_v42r3r3(
            probe_plan=plan,
            probe_attempt=attempt,
            child_observation=_child(loader.GENERIC_LOADER_FAILURE),
        )
    )
    fallback = formal.verify_formal_host_epoch_loader_failure_join_v42r3r3(
        transport_observation=fallback_observation,
        probe_plan=plan,
        probe_attempt=attempt,
    )
    assert fallback["diagnostic_builder_succeeded"] is False

    rejected_children = (
        _child(b"not canonical\n"),
        _child(diagnostic_raw, stdout=b"noise"),
        _child(diagnostic_raw, returncode=74),
        _child(b"x" * 4097),
    )
    for rejected_child in rejected_children:
        rejected = formal.build_formal_host_epoch_transport_observation_v42r3r3(
            probe_plan=plan,
            probe_attempt=attempt,
            child_observation=rejected_child,
        )
        with pytest.raises(formal.V42FormalTransportSuccessorError):
            formal.verify_formal_host_epoch_loader_failure_join_v42r3r3(
                transport_observation=rejected,
                probe_plan=plan,
                probe_attempt=attempt,
            )


def test_effect_plan_round_trips_and_rejects_tamper_extra_and_root_drift() -> None:
    plan = _transport_plan()
    assert plan["local_journal_root"].endswith("-v42r3r3")
    assert plan["remote_journal_root"].endswith("-v42r3r3")
    assert plan[
        "ssh_daemon_login_shell_pam_and_startup_hooks_are_external_tcb"
    ] is True
    assert plan[
        "authenticated_remote_source_boundary_begins_after_login_shell_at_loader"
    ] is True
    assert plan["pre_loader_effect_freedom_claimed"] is False
    assert plan["root_owned_forced_command_entry_claimed"] is False
    assert plan[
        "local_network_marker_precedes_each_authorized_prepare_or_launch_"
        "ssh_dispatch"
    ] is True
    assert plan[
        "controller_authorizes_only_authenticated_inspection_after_marker"
    ] is True
    assert plan["host_epoch_drift_detection_uses_boundary_sampling"] is True
    assert plan[
        "atomic_host_epoch_lock_across_external_effect_claimed"
    ] is False
    assert plan["external_local_stage0_assumption_id"] == plan[
        "external_local_stage0_assumption"
    ]["external_local_stage0_assumption_id"]
    assert plan["external_ssh_ingress_assumption_id"] == plan[
        "external_ssh_ingress_assumption"
    ]["external_ssh_ingress_assumption_id"]
    assert formal.verify_formal_transport_plan_v42r3(
        canonical_json_bytes(plan)
    ) == plan

    for mutation in (
        lambda value: value.update(source_commit="0" * 40),
        lambda value: value.update(unexpected=True),
        lambda value: value.update(pre_loader_effect_freedom_claimed=True),
        lambda value: value.update(
            atomic_host_epoch_lock_across_external_effect_claimed=True
        ),
    ):
        changed = copy.deepcopy(plan)
        mutation(changed)
        with pytest.raises(formal.V42FormalTransportSuccessorError):
            formal.verify_formal_transport_plan_v42r3(changed)

    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.build_formal_transport_plan_v42r3(
            controller_source_manifest=_effect_manifest(),
            native_activation_binding=_binding(),
            host_epoch_probe_plan=_effect_probe_plan(),
            host_epoch_receipt=_host_receipt(),
            legacy_execution_source_manifest_id="e" * 64,
            known_hosts_path=str(
                formal.LOCAL_FORMAL_JOURNAL_ROOT
                / formal.LOCAL_KNOWN_HOSTS_NAME
            ),
            local_journal_root="/tmp/not-the-frozen-root",
            remote_journal_root=str(formal.REMOTE_FORMAL_JOURNAL_ROOT),
        )


def test_prepare_and_cross_version_gate_enforce_exact_phase_authority() -> None:
    plan = _transport_plan()
    attempt = formal.build_formal_prepare_attempt_v42r3(
        formal_transport_plan=plan
    )
    assert formal.verify_formal_prepare_attempt_v42r3(
        canonical_json_bytes(attempt), formal_transport_plan=plan
    ) == attempt
    extra = {**attempt, "extra": False}
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_formal_prepare_attempt_v42r3(
            extra, formal_transport_plan=plan
        )

    gate = formal.verify_cross_version_scientific_state_gate_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        legacy_scientific_phase={"phase": "POST_MATERIALIZATION_PREPARE"},
        effect_authorized=True,
    )
    assert gate["cross_version_scientific_state_gate_passed"] is True
    assert [key for key in gate if key.endswith("_gate_id")] == [
        "cross_version_scientific_state_gate_id"
    ]
    for phase, authorized in (
        ("POST_PREPARE_PRELAUNCH", True),
        ("POST_MATERIALIZATION_PREPARE", False),
    ):
        with pytest.raises(formal.V42FormalTransportSuccessorError):
            formal.verify_cross_version_scientific_state_gate_v42r3(
                formal_transport_plan=plan,
                operation="PREPARE",
                legacy_scientific_phase={"phase": phase},
                effect_authorized=authorized,
            )


def test_launch_attempt_and_systemd_argv_match_receiver_whitelist() -> None:
    plan = _transport_plan()
    launch = _launch_transport_attempt()
    assert formal.verify_formal_launch_transport_attempt_v42r3(
        canonical_json_bytes(launch),
        formal_transport_plan=plan,
        prepare_receipt=_scientific_prepare_receipt(),
        local_launch_attempt=_local_launch_attempt(),
    ) == launch
    argv = formal.build_systemd_run_argv_v42r3(
        formal_transport_plan=plan,
        local_launch_attempt=_local_launch_attempt(),
        service_bootstrap_argv=_service_bootstrap_argv(),
    )
    separator = argv.index("--")
    assert len(argv[1:separator]) == 17
    assert len(set(argv[1:separator])) == 17
    assert argv[separator + 1 :] == _service_bootstrap_argv()
    assert not formal.FORBIDDEN_SYSTEMD_OPTIONS.intersection(argv)
    assert formal.verify_systemd_run_argv_v42r3(
        argv,
        formal_transport_plan=plan,
        local_launch_attempt=_local_launch_attempt(),
        service_bootstrap_argv=_service_bootstrap_argv(),
    ) == argv

    injected = list(argv)
    injected.insert(1, "--wait")
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_systemd_run_argv_v42r3(
            injected,
            formal_transport_plan=plan,
            local_launch_attempt=_local_launch_attempt(),
            service_bootstrap_argv=_service_bootstrap_argv(),
        )


def test_admission_and_wrapper_round_trip_and_reject_identity_tamper() -> None:
    plan = _transport_plan()
    launch = _launch_transport_attempt()
    admission = _admission_receipt()
    assert formal.verify_launch_admission_receipt_v42r3(
        canonical_json_bytes(admission), formal_transport_plan=plan
    ) == admission
    assert formal.verify_launch_admission_receipt_v42r3(
        admission,
        formal_transport_plan=plan,
        launch_transport_attempt=launch,
    ) == admission
    changed = copy.deepcopy(admission)
    changed["unit_main_pid"] += 1
    with pytest.raises(formal.V42FormalTransportSuccessorError):
        formal.verify_launch_admission_receipt_v42r3(
            changed, formal_transport_plan=plan
        )

    gate = formal.verify_cross_version_scientific_state_gate_v42r3(
        formal_transport_plan=plan,
        operation="SERVICE_WRAPPER",
        legacy_scientific_phase={"phase": "POST_PREPARE_PRELAUNCH"},
        effect_authorized=True,
    )
    attestation = formal.build_service_wrapper_attestation_v42r3(
        formal_transport_plan=plan,
        launch_transport_attempt=launch,
        launch_admission_receipt=admission,
        cross_version_scientific_state_gate=gate,
        manager_binding=_manager(),
        unit_observation=_unit_observation(),
        service_pid=9876,
        service_cgroup=str(_unit_observation()["ControlGroup"]),
        service_environment=formal.FORMAL_SERVICE_ENVIRONMENT,
        stdio_facts=[
            {
                "descriptor": descriptor,
                "target": "/dev/null",
                "node_type": "CHARACTER_DEVICE",
                "isatty": False,
            }
            for descriptor in range(3)
        ],
        live_file_descriptors=[0, 1, 2],
        live_tool_facts=_tools(),
    )
    assert formal.verify_service_wrapper_attestation_v42r3(
        canonical_json_bytes(attestation),
        formal_transport_plan=plan,
        launch_transport_attempt=launch,
        launch_admission_receipt=admission,
        cross_version_scientific_state_gate=gate,
    ) == attestation
    recovered_inspection = formal.build_read_only_inspection_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=str(_local_launch_attempt()["local_launch_attempt_id"]),
        inspection_ordinal=1,
        manager_binding=_manager(),
        unit_observation=_unit_observation(),
        artifact_states={
            "formal_successor_journal": "DIRECTORY",
            "launch_transport_attempt": "REGULAR_FILE",
            "launch_admission_receipt": "REGULAR_FILE",
            "service_wrapper_attestation": "REGULAR_FILE",
            "scientific_launch_attempt": "ABSENT",
            "scientific_launch_failure": "ABSENT",
            "scientific_terminal": "ABSENT",
        },
        recovered_documents={
            "launch_transport_attempt": launch,
            "launch_admission_receipt": admission,
            "service_wrapper_attestation": attestation,
        },
    )
    assert formal.verify_read_only_inspection_v42r3(
        recovered_inspection, formal_transport_plan=plan
    ) == recovered_inspection


def test_read_only_inspection_and_local_documents_never_replay_after_marker() -> None:
    plan = _transport_plan()
    attempt_id = formal.build_formal_prepare_attempt_v42r3(
        formal_transport_plan=plan
    )["formal_prepare_attempt_id"]
    inspection = formal.build_read_only_inspection_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        inspection_ordinal=1,
        manager_binding=_manager(),
        unit_observation=None,
        artifact_states={
            "scientific_prepare_receipt": "REGULAR_FILE",
            "scientific_prepare_attempt": "REGULAR_FILE",
            "scientific_prepare_failure": "ABSENT",
            "formal_successor_journal": "ABSENT",
        },
        recovered_documents={
            "scientific_prepare_receipt": _scientific_prepare_receipt()
        },
    )
    assert inspection[
        "authenticated_loader_and_receiver_remote_mutation_performed"
    ] is False
    assert inspection[
        "authenticated_loader_and_receiver_systemd_lifecycle_mutation_performed"
    ] is False
    assert inspection["authenticated_controller_same_effect_reissued"] is False
    assert inspection["end_to_end_remote_mutation_absence_claimed"] is False
    assert inspection["end_to_end_systemd_mutation_absence_claimed"] is False
    assert formal.verify_read_only_inspection_v42r3(
        canonical_json_bytes(inspection), formal_transport_plan=plan
    ) == inspection
    before = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        marker_present=False,
        exact_receipt_present=False,
        inspection=None,
    )
    ambiguous = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=None,
    )
    complete = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=True,
        inspection=inspection,
    )
    assert before["controller_same_effect_dispatch_replay_allowed"] is True
    assert ambiguous["classification"] == formal.CLASS_AMBIGUOUS
    assert ambiguous["controller_same_effect_dispatch_replay_allowed"] is False
    assert complete["classification"] == formal.CLASS_PREPARE_COMPLETE
    assert complete["controller_same_effect_dispatch_replay_allowed"] is False

    marker = formal.build_network_start_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
    )
    assert marker[
        "published_o_excl_nofollow_mode_0400_and_fsynced_before_authorized_"
        "dispatch"
    ] is True
    assert marker[
        "controller_authorizes_only_authenticated_inspection_after_publication"
    ] is True
    assert formal.verify_network_start_v42r3(
        marker, formal_transport_plan=plan
    ) == marker
    raw_receipt = canonical_json_bytes(_scientific_prepare_receipt())
    outcome = formal.build_operation_outcome_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        outcome_class=formal.OUTCOME_COMPLETE_EXACT_RECEIPT,
        receipt_raw=raw_receipt,
    )
    assert formal.verify_operation_outcome_v42r3(
        outcome,
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        receipt_raw=raw_receipt,
    ) == outcome


def test_exact_launch_journal_admission_and_live_unit_classify_in_progress() -> None:
    plan = _transport_plan()
    attempt_id = str(_local_launch_attempt()["local_launch_attempt_id"])
    states = {
        "formal_successor_journal": "DIRECTORY",
        "launch_transport_attempt": "REGULAR_FILE",
        "launch_admission_receipt": "REGULAR_FILE",
        "service_wrapper_attestation": "ABSENT",
        "scientific_launch_attempt": "ABSENT",
        "scientific_launch_failure": "ABSENT",
        "scientific_terminal": "ABSENT",
    }
    inspection = formal.build_read_only_inspection_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
        inspection_ordinal=1,
        manager_binding=_manager(),
        unit_observation=_unit_observation(),
        artifact_states=states,
        recovered_documents={
            "launch_transport_attempt": _launch_transport_attempt(),
            "launch_admission_receipt": _admission_receipt(),
        },
    )
    classification = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=inspection,
    )
    assert classification["classification"] == formal.CLASS_IN_PROGRESS
    assert classification["reason_codes"] == []
    assert classification["controller_same_effect_dispatch_replay_allowed"] is False


def test_unverified_scientific_failure_or_terminal_never_claims_completion() -> None:
    plan = _transport_plan()
    prepare_id = formal.build_formal_prepare_attempt_v42r3(
        formal_transport_plan=plan
    )["formal_prepare_attempt_id"]
    prepare_inspection = formal.build_read_only_inspection_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=prepare_id,
        inspection_ordinal=1,
        manager_binding=_manager(),
        unit_observation=None,
        artifact_states={
            "scientific_prepare_receipt": "ABSENT",
            "scientific_prepare_attempt": "REGULAR_FILE",
            "scientific_prepare_failure": "REGULAR_FILE",
            "formal_successor_journal": "ABSENT",
        },
        recovered_documents={},
    )
    prepare_classification = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=prepare_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=prepare_inspection,
    )
    assert prepare_classification["classification"] == formal.CLASS_AMBIGUOUS
    assert prepare_classification["reason_codes"] == [
        "UNAUTHENTICATED_SCIENTIFIC_TERMINAL"
    ]

    launch_id = str(_local_launch_attempt()["local_launch_attempt_id"])
    launch_states = {
        "formal_successor_journal": "DIRECTORY",
        "launch_transport_attempt": "REGULAR_FILE",
        "launch_admission_receipt": "REGULAR_FILE",
        "service_wrapper_attestation": "ABSENT",
        "scientific_launch_attempt": "REGULAR_FILE",
        "scientific_launch_failure": "ABSENT",
        "scientific_terminal": "REGULAR_FILE",
    }
    launch_inspection = formal.build_read_only_inspection_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=launch_id,
        inspection_ordinal=2,
        manager_binding=_manager(),
        unit_observation=_unit_observation(),
        artifact_states=launch_states,
        recovered_documents={
            "launch_transport_attempt": _launch_transport_attempt(),
            "launch_admission_receipt": _admission_receipt(),
        },
    )
    launch_classification = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=launch_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=launch_inspection,
    )
    assert launch_classification["classification"] == formal.CLASS_AMBIGUOUS
    assert launch_classification["reason_codes"] == [
        "UNAUTHENTICATED_SCIENTIFIC_TERMINAL"
    ]
    assert not hasattr(formal, "CLASS_COMPLETE_SUCCESS")
    assert not hasattr(formal, "CLASS_COMPLETE_FAILURE")
