from __future__ import annotations

import json
import copy
from types import SimpleNamespace

import pytest

from acfqp import (
    construction_k7_standard_2048_formal_transport_v42r1 as formal,
)
from scripts import v42_standard_2048_formal_transport_receiver as receiver
from scripts import run_v42_standard_2048_formal_transport_driver as driver
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)


def _tool(path: str, token: str) -> dict[str, object]:
    return {
        "path": path,
        "sha256": token * 64,
        "byte_count": 1000,
        "mode": 0o755,
        "uid": 0,
        "gid": 0,
        "st_nlink": 1,
    }


def _binding() -> dict[str, object]:
    return {
        "protocol": formal.ACTIVATION_TERMINAL_PROTOCOL,
        "activation_terminal_id": "a" * 64,
        "preactivation_resource_result_id": "b" * 64,
        "source_commit": "c" * 40,
        "source_tree": "d" * 40,
        "source_manifest_id": "e" * 64,
        "transport_manifest_id": "f" * 64,
        "local_materialization_attempt_id": "1" * 64,
        "remote_materialization_attempt_id": "2" * 64,
        "materialization_terminal_id": "3" * 64,
        "materialization_activation_final_evidence_index_id": "0" * 64,
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified": True,
        "bootstrap_terminal_exact_shared_materialization_ids_verified": True,
        "bootstrap_launcher_consumed_activation_transport_terminal_id": False,
        "downstream_launcher_terminal_id_join_remains_defense_in_depth": True,
        "formal_evidence_bundle_complete_under_bounded_successor_claim": True,
        "same_uid_coordinated_replacement_of_named_activation_evidence_root_and_all_persistent_anchors_excluded_from_claim": True,
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "fixed_source_root": str(authority.REMOTE_SOURCE_ROOT),
        "remote_target_alias": authority.REMOTE_HOST_ALIAS,
        "remote_hostname": authority.REMOTE_HOSTNAME,
        "remote_user": authority.REMOTE_USER,
        "remote_uid": authority.REMOTE_UID,
        "kernel_boot_id": "11111111-2222-4333-8444-555555555555",
        "linger_enabled": True,
        "linger_path": f"/var/lib/systemd/linger/{authority.REMOTE_USER}",
        "user_manager_invocation_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        "user_manager_main_pid": 1234,
        "user_manager_control_group": (
            "/user.slice/user-1000.slice/user@1000.service"
        ),
        "cgroup_contract_id": "4" * 64,
        "remote_tool_facts": {
            "env": _tool(formal.ENV, "5"),
            "python": _tool(authority.REMOTE_PYTHON_REALPATH, "6"),
            "systemctl": _tool(formal.SYSTEMCTL, "7"),
            "systemd_run": _tool(formal.SYSTEMD_RUN, "8"),
        },
        "fixed_root_publish_complete": True,
        "formal_prepare_authorized": True,
    }


def _validator(raw: bytes) -> dict[str, object]:
    assert raw == b"activation-terminal\n"
    return _binding()


def _plan() -> dict[str, object]:
    return formal.build_formal_transport_plan_v42r1(
        activation_terminal_raw=b"activation-terminal\n",
        activation_terminal_validator=_validator,
        receiver_source_raw=b"receiver\n",
        driver_source_raw=b"driver\n",
        formal_authority_source_raw=b"formal-authority\n",
    )


def _prepare_receipt(plan: dict[str, object]) -> dict[str, object]:
    return {
        "prepare_receipt_id": "9" * 64,
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
    }


def _local_launch(plan: dict[str, object]) -> dict[str, object]:
    return {
        "local_launch_attempt_id": "a" * 64,
        "prepare_receipt_id": "9" * 64,
        "transport_target_alias": authority.REMOTE_HOST_ALIAS,
    }


def _manager(*, boot: str | None = None) -> dict[str, object]:
    binding = _binding()
    return {
        "kernel_boot_id": binding["kernel_boot_id"] if boot is None else boot,
        "linger_enabled": True,
        "user_manager_invocation_id": binding["user_manager_invocation_id"],
        "user_manager_main_pid": binding["user_manager_main_pid"],
        "user_manager_control_group": binding["user_manager_control_group"],
        "cgroup_contract_id": binding["cgroup_contract_id"],
    }


def _unit(attempt_id: str, *, state: str = "active", sub: str = "running") -> dict[str, object]:
    plan = _plan()
    systemd_argv = formal.build_systemd_run_argv_v42r1(
        plan=plan, local_launch_attempt={"local_launch_attempt_id": attempt_id}
    )
    invocation = "12345678-1234-4234-8234-123456789abc"
    control_group = "/user.slice/user-1000.slice/user@1000.service/app.slice/" + formal.unit_name_v42r1(attempt_id)
    return {
        "Id": formal.unit_name_v42r1(attempt_id),
        "LoadState": "loaded",
        "ActiveState": state,
        "SubState": sub,
        "Result": "success",
        "InvocationID": invocation,
        "MainPID": 9876 if sub != "exited" else 0,
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
        "WorkingDirectory": str(authority.REMOTE_SOURCE_ROOT),
        "Slice": formal.SYSTEMD_SLICE,
        "FragmentPath": (
            f"/run/user/{authority.REMOTE_UID}/systemd/transient/"
            + formal.unit_name_v42r1(attempt_id)
        ),
        "LiveMainPIDArgv": (
            []
            if sub == "exited"
            else list(
                formal._receiver_python_argv(
                    plan=plan,
                    mode="--formal-launch-service-wrapper",
                    attempt_id=attempt_id,
                    runtime_invocation_id=invocation,
                    runtime_control_group=control_group,
                )
            )
        ),
        "LiveMainPIDArgvSource": (
            "UNAVAILABLE_NO_MAINPID" if sub == "exited" else "PROC_MAINPID_CMDLINE"
        ),
        "Environment": "",
    }


def _absent_unit(attempt_id: str) -> dict[str, object]:
    unit = _unit(attempt_id, state="inactive", sub="dead")
    unit.update(
        {
            "LoadState": "not-found",
            "Result": "",
            "InvocationID": "",
            "MainPID": 0,
            "ControlGroup": "",
            "Type": "",
            "Restart": "",
            "RemainAfterExit": "",
            "SuccessExitStatus": "",
            "UMask": "",
            "KillMode": "",
            "TimeoutStopUSec": "",
            "RuntimeMaxUSec": "",
            "StandardInput": "",
            "StandardOutput": "",
            "StandardError": "",
            "WorkingDirectory": "",
            "Slice": "",
            "FragmentPath": "",
            "LiveMainPIDArgv": [],
            "LiveMainPIDArgvSource": "ABSENT_UNIT",
            "Environment": "",
        }
    )
    return unit


def _states(**changes: str) -> dict[str, str]:
    result = {
        "prepare_receipt": "EXACT",
        "prepare_failure": "ABSENT",
        "remote_launch_transport_attempt": "EXACT",
        "remote_launch_admission_receipt": "EXACT",
        "service_wrapper_attestation": "EXACT",
        "launch_attempt_journal": "ABSENT",
        "runner_failure": "ABSENT",
        "scientific_terminal": "ABSENT",
    }
    result.update(changes)
    return result


def test_activation_requires_explicit_validator_and_plan_is_exact() -> None:
    with pytest.raises(formal.V42FormalTransportError, match="validator adapter"):
        formal.validate_activation_terminal_protocol_v42r1(
            b"activation-terminal\n", validator=None  # type: ignore[arg-type]
        )
    plan = _plan()
    assert plan["local_journal_root"] == str(formal.LOCAL_FORMAL_JOURNAL_ROOT)
    assert str(plan["local_journal_root"]).startswith("/")
    assert plan["activation_binding"]["activation_terminal_id"] == "a" * 64
    assert plan["activation_terminal_schema_is_owned_by_explicit_validator_adapter"]
    verified = formal.verify_formal_transport_plan_v42r1(
        json.loads(json.dumps(plan)),
        activation_terminal_raw=b"activation-terminal\n",
        activation_terminal_validator=_validator,
        receiver_source_raw=b"receiver\n",
        driver_source_raw=b"driver\n",
        formal_authority_source_raw=b"formal-authority\n",
    )
    assert verified == plan


def test_expected_activation_final_index_id_is_cryptographically_in_plan() -> None:
    first = _plan()

    def changed_validator(raw: bytes) -> dict[str, object]:
        assert raw == b"activation-terminal\n"
        changed = _binding()
        changed["materialization_activation_final_evidence_index_id"] = "9" * 64
        return changed

    second = formal.build_formal_transport_plan_v42r1(
        activation_terminal_raw=b"activation-terminal\n",
        activation_terminal_validator=changed_validator,
        receiver_source_raw=b"receiver\n",
        driver_source_raw=b"driver\n",
        formal_authority_source_raw=b"formal-authority\n",
    )
    assert first["formal_transport_plan_id"] != second["formal_transport_plan_id"]
    assert second["activation_binding"][
        "materialization_activation_final_evidence_index_id"
    ] == "9" * 64


def test_systemd_launch_contract_is_detached_exact_and_full_id_named() -> None:
    plan = _plan()
    local = _local_launch(plan)
    argv = formal.build_systemd_run_argv_v42r1(
        plan=plan, local_launch_attempt=local
    )
    expected_unit = (
        "acfqp-v42-remote-ordinal2-" + "a" * 64 + ".service"
    )
    assert f"--unit={expected_unit}" in argv
    assert "--service-type=exec" in argv
    assert "--slice=app.slice" in argv
    assert "--property=Restart=no" in argv
    assert "--property=RemainAfterExit=yes" in argv
    assert "--property=SuccessExitStatus=2" in argv
    assert "--property=UMask=0077" in argv
    assert "--property=KillMode=mixed" in argv
    assert "--property=TimeoutStopSec=30s" in argv
    assert "--property=RuntimeMaxSec=606300s" in argv
    assert all(f"--property=Standard{role}=null" in argv for role in ("Input", "Output", "Error"))
    assert not formal.FORBIDDEN_SYSTEMD_OPTIONS.intersection(argv)
    assert not any(item.startswith("--property=BindsTo=") for item in argv)
    assert "--formal-launch-service-bootstrap" in argv
    assert argv[-1] == "a" * 64
    assert formal.ENV not in argv


@pytest.mark.parametrize(
    "forbidden", ["--wait", "--pipe", "--pty", "--scope", "--collect"]
)
def test_systemd_validator_rejects_every_ssh_lifecycle_coupling(forbidden: str) -> None:
    plan = _plan()
    local = _local_launch(plan)
    argv = list(formal.build_systemd_run_argv_v42r1(plan=plan, local_launch_attempt=local))
    argv.insert(1, forbidden)
    with pytest.raises(formal.V42FormalTransportError, match="forbidden"):
        formal.validate_systemd_run_argv_v42r1(
            argv, plan=plan, local_launch_attempt=local
        )
    argv.remove(forbidden)
    argv.insert(1, "--property=BindsTo=sshd.service")
    with pytest.raises(formal.V42FormalTransportError, match="SSH session"):
        formal.validate_systemd_run_argv_v42r1(
            argv, plan=plan, local_launch_attempt=local
        )


def test_prepare_and_launch_attempts_join_and_ssh_templates_are_pinned() -> None:
    plan = _plan()
    prepare_attempt = formal.build_prepare_attempt_v42r1(plan)
    assert formal.verify_prepare_attempt_v42r1(
        prepare_attempt, plan=plan
    ) == prepare_attempt
    launch = formal.build_launch_transport_attempt_v42r1(
        plan=plan,
        prepare_receipt=_prepare_receipt(plan),
        local_launch_attempt=_local_launch(plan),
    )
    assert launch["unit_name"].endswith("a" * 64 + ".service")
    for operation in (
        "prepare_once", "inspect_prepare", "admit_launch", "inspect_launch"
    ):
        argv = formal.materialize_ssh_argv_v42r1(plan, operation)
        assert argv[0] == "/usr/bin/ssh"
        assert "-T" in argv
        assert "-oRequestTTY=no" in argv
        assert plan["formal_transport_plan_id"] in argv[-1]
        assert not any("{acfqp_v42_" in item for item in argv)


def test_marker_three_state_gate_never_replays_after_marker_or_disconnect() -> None:
    plan = _plan()
    attempt = formal.build_prepare_attempt_v42r1(plan)
    attempt_id = attempt["formal_prepare_attempt_id"]
    before = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id,
        marker_present=False,
        exact_receipt_present=False,
        inspection=None,
    )
    complete = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=True,
        inspection=None,
    )
    disconnected = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=None,
    )
    assert before["classification"] == formal.CLASS_PRE_NETWORK_RETRYABLE
    assert before["same_effect_replay_allowed"] is True
    assert complete["classification"] == formal.CLASS_PREPARE_COMPLETE
    assert disconnected["classification"] == formal.CLASS_AMBIGUOUS
    assert complete["same_effect_replay_allowed"] is False
    assert disconnected["same_effect_replay_allowed"] is False
    assert disconnected["only_read_only_inspection_allowed"] is True


def test_launch_inspection_active_absent_terminal_and_failure_classify_exactly() -> None:
    plan = _plan()
    attempt_id = "a" * 64
    active = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=1,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id),
        artifact_states=_states(),
    )
    absent = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=2,
        manager_binding=_manager(),
        unit_observation=_absent_unit(attempt_id),
        artifact_states=_states(remote_launch_admission_receipt="ABSENT"),
    )
    success = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=3,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id, sub="exited"),
        artifact_states=_states(
            launch_attempt_journal="EXACT",
            scientific_terminal="EXACT_SUCCESS",
        ),
    )
    failure = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=4,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id, sub="exited"),
        artifact_states=_states(
            launch_attempt_journal="EXACT", runner_failure="EXACT"
        ),
    )
    expected = (
        (active, formal.CLASS_IN_PROGRESS),
        (absent, formal.CLASS_AMBIGUOUS),
        (success, formal.CLASS_COMPLETE_SUCCESS),
        (failure, formal.CLASS_COMPLETE_FAILURE),
    )
    for inspection, classification in expected:
        observed = formal.classify_formal_operation_v42r1(
            plan=plan,
            operation=formal.OPERATION_LAUNCH,
            attempt_id=attempt_id,
            marker_present=True,
            exact_receipt_present=False,
            inspection=inspection,
        )
        assert observed["classification"] == classification
        assert observed["same_effect_replay_allowed"] is False
        assert observed["unit_absence_used_as_never_started_proof"] is False


@pytest.mark.parametrize(
    "boot",
    [
        "99999999-2222-4333-8444-555555555555",
        "77777777-2222-4333-8444-555555555555",
    ],
)
def test_boot_or_user_manager_epoch_drift_permanently_closes_replay(boot: str) -> None:
    plan = _plan()
    attempt_id = "a" * 64
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=1,
        manager_binding=_manager(boot=boot),
        unit_observation=_unit(attempt_id),
        artifact_states=_states(),
    )
    result = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=inspection,
    )
    assert result["classification"] == formal.CLASS_AMBIGUOUS
    assert result["reason_codes"] == ["BOOT_OR_USER_MANAGER_OR_CGROUP_DRIFT"]
    assert result["same_effect_replay_allowed"] is False


def test_admission_receipt_binds_unit_process_manager_argv_environment_and_tools() -> None:
    plan = _plan()
    local = _local_launch(plan)
    transport_attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan,
        prepare_receipt=_prepare_receipt(plan),
        local_launch_attempt=local,
    )
    argv = formal.build_systemd_run_argv_v42r1(
        plan=plan, local_launch_attempt=local
    )
    receipt = formal.build_launch_admission_receipt_v42r1(
        plan=plan,
        launch_transport_attempt=transport_attempt,
        manager_binding=_manager(),
        unit_observation=_unit("a" * 64),
        systemd_run_argv=argv,
    )
    assert receipt["unit_name"].endswith("a" * 64 + ".service")
    assert receipt["unit_main_pid"] == 9876
    assert receipt["service_lifetime_is_independent_of_ssh"] is True
    assert receipt["same_admission_retry_forbidden"] is True
    assert receipt["systemd_client_environment"] == formal.SYSTEMD_CLIENT_ENVIRONMENT
    assert receipt["remote_tool_facts"] == plan["activation_binding"]["remote_tool_facts"]


def test_service_wrapper_attests_invocation_cgroup_exact_env_and_null_stdio() -> None:
    plan = _plan()
    local = _local_launch(plan)
    transport_attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan,
        prepare_receipt=_prepare_receipt(plan),
        local_launch_attempt=local,
    )
    pid = 9876
    invocation = "12345678-1234-4234-8234-123456789abc"
    environment = dict(formal.FORMAL_SERVICE_ENVIRONMENT)
    stdio = [
        {
            "descriptor": descriptor,
            "target": "/dev/null",
            "node_type": "CHARACTER_DEVICE",
            "isatty": False,
        }
        for descriptor in range(3)
    ]
    attestation = formal.build_service_wrapper_attestation_v42r1(
        plan=plan,
        launch_transport_attempt=transport_attempt,
        manager_binding=_manager(),
        unit_observation=_unit("a" * 64),
        service_pid=pid,
        service_cgroup=(
            _binding()["user_manager_control_group"]
            + "/app.slice/"
            + formal.unit_name_v42r1("a" * 64)
        ),
        service_environment=environment,
        stdio_facts=stdio,
        live_file_descriptors=[0, 1, 2],
        live_tool_facts=plan["activation_binding"]["remote_tool_facts"],
    )
    assert attestation["formal_runner_invocation_authorized"] is True
    assert attestation["formal_execution_performed"] is False
    assert attestation["all_three_stdio_descriptors_are_dev_null"] is True
    forged = dict(environment)
    forged["EXTRA"] = "forbidden"
    with pytest.raises(formal.V42FormalTransportError, match="environment"):
        formal.build_service_wrapper_attestation_v42r1(
            plan=plan,
            launch_transport_attempt=transport_attempt,
            manager_binding=_manager(),
            unit_observation=_unit("a" * 64),
            service_pid=pid,
            service_cgroup=(
                _binding()["user_manager_control_group"]
                + "/app.slice/"
                + formal.unit_name_v42r1("a" * 64)
            ),
            service_environment=forged,
            stdio_facts=stdio,
            live_file_descriptors=[0, 1, 2],
            live_tool_facts=plan["activation_binding"]["remote_tool_facts"],
        )


def test_fail_closed_scientific_terminal_is_never_reported_as_success() -> None:
    plan = _plan()
    attempt_id = "a" * 64
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=9,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id, sub="exited"),
        artifact_states=_states(
            launch_attempt_journal="EXACT",
            scientific_terminal="EXACT_FAIL_CLOSED",
        ),
    )
    result = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=inspection,
    )
    assert result["classification"] == formal.CLASS_COMPLETE_FAILURE
    assert result["reason_codes"] == ["SCIENTIFIC_TERMINAL_FAIL_CLOSED"]


@pytest.mark.parametrize(
    "changes",
    [
        {"runner_failure": "PRESENT_INVALID"},
        {"scientific_terminal": "PRESENT_INVALID"},
        {"remote_launch_admission_receipt": "PRESENT_INVALID"},
        {"service_wrapper_attestation": "PRESENT_INVALID"},
    ],
)
def test_any_invalid_launch_artifact_precedes_success_or_progress(
    changes: dict[str, str],
) -> None:
    plan = _plan()
    attempt_id = "a" * 64
    states = _states(**{"scientific_terminal": "EXACT_SUCCESS", **changes})
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        inspection_ordinal=10,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id),
        artifact_states=states,
    )
    result = formal.classify_formal_operation_v42r1(
        plan=plan,
        operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=False,
        inspection=inspection,
    )
    assert result["classification"] == formal.CLASS_AMBIGUOUS
    assert result["reason_codes"] == ["PRESENT_INVALID_REMOTE_ARTIFACT"]


@pytest.mark.parametrize(
    "missing",
    [
        "prepare_receipt",
        "remote_launch_transport_attempt",
        "remote_launch_admission_receipt",
        "service_wrapper_attestation",
        "launch_attempt_journal",
    ],
)
def test_success_requires_every_exact_reachable_predecessor(missing: str) -> None:
    plan = _plan()
    attempt_id = "a" * 64
    states = _states(
        launch_attempt_journal="EXACT", scientific_terminal="EXACT_SUCCESS"
    )
    states[missing] = "ABSENT"
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id, inspection_ordinal=11,
        manager_binding=_manager(),
        unit_observation=_unit(attempt_id, sub="exited"),
        artifact_states=states,
    )
    result = formal.classify_formal_operation_v42r1(
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=attempt_id, marker_present=True,
        exact_receipt_present=False, inspection=inspection,
    )
    assert result["classification"] == formal.CLASS_AMBIGUOUS
    assert result["reason_codes"] == [
        "LAUNCH_TERMINAL_PREDECESSOR_CHAIN_NOT_EXACT"
    ]


def _bootstrap_unit(plan: dict[str, object], attempt_id: str) -> dict[str, object]:
    unit = _unit(attempt_id)
    unit["LiveMainPIDArgv"] = list(
        formal._receiver_python_argv(  # noqa: SLF001
            plan=plan,
            mode="--formal-launch-service-bootstrap",
            attempt_id=attempt_id,
        )
    )
    return unit


def test_type_exec_poll_accepts_delayed_bootstrap_to_clean_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    attempt_id = "a" * 64
    sequence = iter(
        [_bootstrap_unit(plan, attempt_id), _bootstrap_unit(plan, attempt_id), _unit(attempt_id)]
    )
    calls = 0

    def observed(_plan: dict[str, object], _attempt: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return next(sequence)

    monkeypatch.setattr(receiver, "_unit", observed)
    monkeypatch.setattr(receiver.time, "sleep", lambda _seconds: None)
    result = receiver._await_clean_wrapper_unit(plan, attempt_id)  # noqa: SLF001
    assert result["LiveMainPIDArgv"][6] == str(
        authority.REMOTE_SOURCE_ROOT / formal.FORMAL_RECEIVER_RELATIVE
    )
    assert "--formal-launch-service-wrapper" in result["LiveMainPIDArgv"]
    assert calls == 3


def test_type_exec_poll_closes_on_never_clean_and_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    attempt_id = "a" * 64
    bootstrap = _bootstrap_unit(plan, attempt_id)
    monkeypatch.setattr(receiver, "_unit", lambda *_args: copy.deepcopy(bootstrap))
    monkeypatch.setattr(receiver, "CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS", 0.0)
    with pytest.raises(receiver.V42FormalTransportReceiverError, match="did not reach"):
        receiver._await_clean_wrapper_unit(plan, attempt_id)  # noqa: SLF001

    drift = copy.deepcopy(bootstrap)
    drift["MainPID"] = int(drift["MainPID"]) + 1
    sequence = iter((copy.deepcopy(bootstrap), drift))
    monkeypatch.setattr(receiver, "CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS", 30.0)
    monkeypatch.setattr(receiver, "_unit", lambda *_args: next(sequence))
    monkeypatch.setattr(receiver.time, "sleep", lambda _seconds: None)
    with pytest.raises(receiver.V42FormalTransportReceiverError, match="identity drifted"):
        receiver._await_clean_wrapper_unit(plan, attempt_id)  # noqa: SLF001


def test_admit_launch_runs_systemd_once_while_polling_bootstrap_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    receipt = _prepare_receipt(plan)
    local = _local_launch(plan)
    attempt = formal.build_launch_transport_attempt_v42r1(
        plan=plan, prepare_receipt=receipt, local_launch_attempt=local
    )
    ingress = {
        "formal_transport_plan": plan,
        "prepare_receipt": receipt,
        "local_launch_attempt": local,
        "formal_launch_transport_attempt": attempt,
    }
    monkeypatch.setattr(receiver, "_ingress", lambda *_args, **_kwargs: ingress)
    monkeypatch.setattr(receiver, "_plan", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(receiver, "_verify_program_self", lambda *_args: None)
    monkeypatch.setattr(receiver.processio, "require_isolated_python", lambda: None)
    monkeypatch.setattr(
        receiver, "_prepare_receipt", lambda *_args: (receipt, b"receipt")
    )
    monkeypatch.setattr(
        authority, "verify_local_launch_attempt_v42r1",
        lambda *_args, **_kwargs: local,
    )
    monkeypatch.setattr(
        authority, "verify_remote_control_phase_inventory_v42r1",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(receiver, "_require_live_epoch", lambda *_args: _manager())
    monkeypatch.setattr(receiver, "_create_remote_journal", lambda *_args: None)
    monkeypatch.setattr(receiver.processio, "write_once", lambda *_args: None)

    class Pin:
        def close(self) -> None:
            pass

    monkeypatch.setattr(receiver, "_open_tool_pin", lambda *_args: Pin())
    effects = 0

    def one_systemd_effect(*_args: object, **_kwargs: object) -> tuple[int, bytes, bytes]:
        nonlocal effects
        effects += 1
        return 0, b"", b""

    monkeypatch.setattr(receiver, "_run_bounded", one_systemd_effect)
    sequence = iter(
        [_bootstrap_unit(plan, "a" * 64), _bootstrap_unit(plan, "a" * 64), _unit("a" * 64)]
    )
    polls = 0

    def observed(*_args: object) -> dict[str, object]:
        nonlocal polls
        polls += 1
        return next(sequence)

    monkeypatch.setattr(receiver, "_unit", observed)
    monkeypatch.setattr(receiver.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(receiver, "_write_stdout", lambda *_args: 0)
    assert receiver._admit_launch(plan["formal_transport_plan_id"]) == 0  # noqa: SLF001
    assert effects == 1
    assert polls == 3


def test_disconnect_inspection_recovers_prepare_receipt_without_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object,
) -> None:
    from pathlib import Path

    root = Path(str(tmp_path)) / "journal"
    monkeypatch.setattr(formal, "LOCAL_FORMAL_JOURNAL_ROOT", root)
    driver._ensure_journal_root()  # noqa: SLF001
    plan = _plan()
    attempt = formal.build_prepare_attempt_v42r1(plan)
    attempt_id = attempt["formal_prepare_attempt_id"]
    receipt = _prepare_receipt(plan)
    receipt_raw = formal.canonical_json_bytes(receipt)
    driver._publish_or_verify(  # noqa: SLF001
        root / formal.LOCAL_PREPARE_ATTEMPT_NAME,
        formal.canonical_json_bytes(attempt),
    )
    retained = driver._publish_outcome(  # noqa: SLF001
        plan=plan, operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id,
        outcome_class=formal.OUTCOME_POST_MARKER_AMBIGUOUS,
        receipt_raw=None,
    )
    states = _states(
        prepare_receipt="EXACT", prepare_failure="ABSENT",
        remote_launch_transport_attempt="ABSENT",
        remote_launch_admission_receipt="ABSENT",
        service_wrapper_attestation="ABSENT",
    )
    inspection = formal.build_read_only_inspection_v42r1(
        plan=plan, operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id, inspection_ordinal=1,
        manager_binding=_manager(), unit_observation=None,
        artifact_states=states,
        recovered_documents={"prepare_receipt": receipt},
    )
    stdout = formal.canonical_json_bytes(inspection) + b"\n"
    observation = SimpleNamespace(
        exec_succeeded=True, returncode=0, timed_out=False,
        stdin_complete=True, stdin_sent_byte_count=2,
        stdin_expected_byte_count=2, stdout_overflow=False,
        stdout_eof=True, stdout_total_byte_count=len(stdout),
        stdout_raw=stdout, stderr_total_byte_count=0, stderr_eof=True,
    )
    monkeypatch.setattr(driver, "_dispatch_read_only", lambda **_kwargs: observation)
    monkeypatch.setattr(
        authority, "verify_prepare_receipt_v42",
        lambda *_args, **_kwargs: receipt,
    )
    observed = driver.inspect_read_only_v42r1(
        plan=plan, operation=formal.OPERATION_PREPARE,
        attempt_id=attempt_id, ordinal=1,
    )
    assert observed == inspection
    assert (root / formal.LOCAL_PREPARE_RECEIPT_NAME).read_bytes() == receipt_raw
    effects = 0

    def forbidden_effect(**_kwargs: object) -> object:
        nonlocal effects
        effects += 1
        raise AssertionError("prepare effect replayed")

    monkeypatch.setattr(driver, "_dispatch_effect_once", forbidden_effect)
    resumed = driver.execute_prepare_once_v42r1(plan)
    assert resumed["receipt"] == receipt
    assert resumed["outcome"] == retained
    assert effects == 0
