from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime


HELPER = Path(__file__).with_name(
    "_nested_creator_two_birth_live_prefix_subprocess.py"
)


def _run_real_helper(mode: str) -> dict[str, object]:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--scope",
            "--collect",
            "-p",
            "Delegate=yes",
            "-p",
            "TasksMax=infinity",
            f"--working-directory={repository}",
            "env",
            f"PYTHONPATH={repository / 'src'}",
            sys.executable,
            os.fspath(HELPER),
            mode,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )
    return json.loads(completed.stdout.splitlines()[-1])


def test_live_prefix_handle_is_not_caller_mintable_copyable_or_pickleable() -> None:
    handle = object.__new__(runtime.BoundedNestedCreatorTwoBirthLivePrefixV1)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        copy.copy(handle)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        copy.deepcopy(handle)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        pickle.dumps(handle)


@pytest.mark.parametrize(
    "name",
    (
        "begin_bounded_nested_creator_two_birth_live_prefix_v1",
        "close_bounded_nested_creator_two_birth_live_prefix_v1",
        "abort_bounded_nested_creator_two_birth_live_prefix_v1",
        "run_bounded_nested_creator_two_birth_runtime_v1",
        "snapshot_bounded_nested_creator_two_birth_live_prefix_v1",
    ),
)
def test_live_prefix_public_api_is_explicit(name: str) -> None:
    assert name in runtime.__all__
    assert callable(getattr(runtime, name))


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_begin_stops_live_and_close_returns_compatible_closed_result() -> None:
    result = _run_real_helper("BEGIN_CLOSE")
    assert result["live_state"] == "PROBE_REAPED_SUPERVISOR_LIVE"
    assert result["live_population"] == 1
    assert result["supervisor_pid"] > 0
    assert result["probe_pid"] > 0
    assert result["supervisor_pid"] != result["probe_pid"]
    assert result["fd_delta_while_live"] == 3
    assert result["signal_mask_restored_after_begin"] is True
    assert result["outer_live_prefix_count_while_live"] == 1
    assert result["inner_live_session_count_while_live"] == 1
    assert result["v2_raw_facts_identity_retained"] is True
    assert (
        result["v2_schema"]
        == "acfqp.k7_h1_nested_creator_probe_observed_facts.v2"
    )
    assert result["v2_protocol_receive_observation_count"] > 0
    assert (
        result["snapshot_schema"]
        == "acfqp.k7_h1_two_birth_live_observation.v1"
    )
    assert result["snapshot_entry_populations"] == [0, 0]
    assert result["snapshot_current_populations"] == [1, 1]
    assert result["snapshot_birth_order"] == ["SUPERVISOR", "PIDFD_PROBE"]
    assert result["snapshot_broker_supported"] is False
    assert result["snapshot_exact_topology"] is False
    assert result["snapshot_authority"] is False
    assert result["snapshot_peak_read_count"] == 0
    assert result["snapshot_mutation_errors"] == ["TypeError", "TypeError"]
    assert result["snapshot_repeat_equal"] is True
    assert result["terminal_state"] == "CLOSED"
    assert result["result_type"] == "BoundedNestedCreatorTwoBirthRawResultV1"
    assert (
        result["result_schema"]
        == "acfqp.k7_h1_nested_creator_two_birth_raw_result.v1"
    )
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    assert result["result_probe_pid"] == result["probe_pid"]
    assert result["result_final_population"] == 0
    assert result["result_birth_order"] == ["SUPERVISOR", "PIDFD_PROBE"]
    assert result["repeated_close_same_result"] is True
    assert result["abort_after_close_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["snapshot_after_close_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["v2_identity_retained_after_close"] is True
    assert result["v2_document_retained_after_close"] is True
    assert result["legacy_result_type"] == (
        "BoundedNestedCreatorTwoBirthRawResultV1"
    )
    assert result["legacy_document_shape_equal"] is True
    assert result["legacy_static_fields_equal"] is True
    assert result["legacy_dynamic_identities_distinct"] is True
    assert result["legacy_final_population"] == 0
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_explicit_abort_closes_live_prefix_exactly() -> None:
    result = _run_real_helper("EXPLICIT_ABORT")
    assert result["live_state"] == "PROBE_REAPED_SUPERVISOR_LIVE"
    assert result["live_population"] == 1
    assert result["abort_state"] == "ABORTED_CLOSED"
    assert result["terminal_state"] == "ABORTED_CLOSED"
    assert result["signal_mask_restored_after_begin"] is True
    assert result["v2_raw_facts_identity_retained"] is True
    assert result["repeated_abort_facts_equal"] is True
    assert result["close_after_abort_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["snapshot_after_abort_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_wrong_thread_cannot_consume_live_prefix() -> None:
    result = _run_real_helper("WRONG_THREAD")
    assert result["wrong_thread_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["wrong_thread_snapshot_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["state_after_wrong_thread"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["terminal_state"] == "CLOSED"
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_second_begin_is_rejected_without_consuming_first_prefix() -> None:
    result = _run_real_helper("SECOND_BEGIN")
    assert result["second_begin_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["state_after_second_begin"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["terminal_state"] == "CLOSED"
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_atfork_poison_is_child_only_and_parent_remains_live() -> None:
    result = _run_real_helper("ATFORK")
    child = result["child_document"]
    assert result["child_wait_pid"] == result["child_pid"]
    assert result["child_wait_exited_zero"] is True
    assert "child_internal_error" not in child
    assert child["outer_registry_empty"] is True
    assert child["inner_registry_empty"] is True
    assert child["handle_state"] == "FORK_CHILD_POISONED"
    assert child["session_state"] == "FORK_CHILD_POISONED"
    assert child["handle_control_fd_field"] == -1
    assert child["session_control_fd_field"] == -1
    assert child["session_pidfd_field"] == -1
    assert child["inherited_fds_closed"] == [True, True, True]
    assert child["close_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert child["abort_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert child["snapshot_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert child["effect_calls"] == {"kill": 0, "reap": 0, "subreaper": 0}
    assert child["supervisor_still_live"] is True
    assert child["direct_children"] == ""

    assert result["parent_outer_registry_intact"] is True
    assert result["parent_inner_registry_intact"] is True
    assert result["parent_handle_state_after_fork"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["parent_session_state_after_fork"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["parent_live_fds_unchanged"] is True
    assert result["parent_effect_calls_during_fork"] == {
        "kill": 0,
        "reap": 0,
        "subreaper": 0,
    }
    assert result["parent_supervisor_still_live"] is True
    assert result["parent_subreaper_unchanged_during_fork"] is True
    assert result["terminal_state"] == "CLOSED"
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    _assert_exact_terminal_cleanup(result)


@pytest.mark.parametrize(
    "phase,expected_terminal",
    (
        ("AFTER_PREFIX_REGISTER", "NO_HANDLE_CLOSED"),
        ("AFTER_SHUTDOWN_ECHO", "ABORTED_CLOSED"),
        ("AFTER_SUPERVISOR_REAP", "ABORTED_CLOSED"),
        ("BEFORE_SUBREAPER_RESTORE", "ABORTED_CLOSED"),
    ),
)
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_fault_phases_close_without_leaking_authority(
    phase: str, expected_terminal: str
) -> None:
    result = _run_real_helper(phase)
    assert result["error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["terminal_state"] == expected_terminal
    if phase == "AFTER_PREFIX_REGISTER":
        assert result["handle_returned"] is False
        assert result["signal_mask_restored"] is True
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_begin_cleanup_failure_is_quarantined_then_recovered() -> None:
    result = _run_real_helper("BEGIN_CLEANUP_QUARANTINE_RECOVERY")
    assert result["begin_error_type"] == "RuntimeError"
    assert result["abort_call_count"] == 2
    assert result["quarantine_present_before_recovery"] is True
    assert result["quarantine_state_before_recovery"] == (
        "BEGIN_CLEANUP_FAILED_QUARANTINED"
    )
    assert result["population_before_recovery"] >= 1
    assert result["recovery_state"] == "BEGIN_FAILURE_RECOVERED_CLOSED"
    assert result["signal_mask_restored"] is True
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_abort_terminal_failure_quarantines_then_retry_closes() -> None:
    result = _run_real_helper("ABORT_QUARANTINE_RETRY")
    assert result["first_error_type"] == "RuntimeError"
    assert result["finish_call_count"] == 2
    assert result["quarantined_state"] == "ABORT_FAILED_QUARANTINED"
    assert result["quarantined_outer_registry_count"] == 1
    assert result["quarantined_inner_registry_count"] == 0
    assert result["quarantined_population"] == 0
    assert result["quarantined_fd_delta"] == 1
    assert result["retry_state"] == "ABORTED_CLOSED"
    assert result["terminal_state"] == "ABORTED_CLOSED"
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_construction_entry_fork_child_exits_190_and_parent_continues() -> None:
    result = _run_real_helper("BEGIN_ENTRY_FORK")
    assert result["entry_fork_count"] == 1
    assert result["entry_fork_pid"] > 0
    assert result["entry_fork_exit_code"] == 190
    assert result["live_state"] == "PROBE_REAPED_SUPERVISOR_LIVE"
    assert result["live_population"] == 1
    assert result["terminal_state"] == "CLOSED"
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_hidden_registered_begin_cleanup_recovers_on_third_retry() -> None:
    result = _run_real_helper("HIDDEN_BEGIN_CLEANUP_THREE_RECOVERIES")
    assert result["begin_error_type"] == "RuntimeError"
    assert result["finish_call_count"] == 4
    assert result["hidden_after_begin"] == [True]
    assert result["recovery_error_types"] == ["RuntimeError", "RuntimeError"]
    assert result["states_after_failed_recovery"] == [
        "ABORT_FAILED_QUARANTINED",
        "ABORT_FAILED_QUARANTINED",
    ]
    assert result["recovered_state"] == "ABORTED_CLOSED"
    assert result["terminal_state"] == "ABORTED_CLOSED"
    _assert_exact_terminal_cleanup(result)


@pytest.mark.parametrize(
    "phase,expected_state,expected_replay",
    (
        ("AFTER_CONTROL_CLOSE", "ABORTED_CLOSED", "ABORTED_CLOSED"),
        (
            "AFTER_REGISTRY_DELETE",
            "CLOSED",
            "BoundedNestedCreatorTwoBirthRawResultV1",
        ),
    ),
)
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_terminal_commit_interruption_is_replayable(
    phase: str, expected_state: str, expected_replay: str
) -> None:
    result = _run_real_helper(phase)
    assert result["first_close_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["state_after_interruption"] == expected_state
    assert result["replay_kind"] == expected_replay
    assert result["terminal_state"] == expected_state
    _assert_exact_terminal_cleanup(result)


@pytest.mark.parametrize(
    "phase",
    (
        "AFTER_BEGIN_RECOVERY_CONTROL_CLOSE",
        "AFTER_BEGIN_RECOVERY_REGISTRY_CLEAR",
    ),
)
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_begin_failure_recovery_commit_interruption_is_replayable(
    phase: str,
) -> None:
    result = _run_real_helper(phase)
    assert result["begin_error_type"] == "RuntimeError"
    assert result["abort_call_count"] == 1
    assert result["first_recovery_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["replayed_recovery_state"] == (
        "BEGIN_FAILURE_RECOVERED_CLOSED"
    )
    assert result["terminal_state"] == "BEGIN_FAILURE_RECOVERED_CLOSED"
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_live_handle_private_tampering_cannot_change_authoritative_record() -> None:
    result = _run_real_helper("HANDLE_PRIVATE_TAMPER")
    assert result["public_record_authoritative"] is True
    assert result["snapshot_record_authoritative"] is True
    assert result["terminal_state"] == "CLOSED"
    assert result["result_supervisor_pid"] == result["expected_supervisor_pid"]
    assert result["result_supervisor_pid"] == result["supervisor_pid"]
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_abort_rejects_unrelated_child_before_effects_and_does_not_consume_it() -> None:
    result = _run_real_helper("UNRELATED_CHILD_ABORT_GUARD")
    assert result["unrelated_pid"] > 0
    assert result["rejection_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["effects_before_caller_reap"] == {
        "kill": 0,
        "waitid": 0,
        "inner_abort": 0,
    }
    assert result["state_after_rejection"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["population_after_rejection"] == 1
    assert result["unrelated_waited_pid"] == result["unrelated_pid"]
    assert result["unrelated_waited_exit_code"] == 0
    assert result["abort_state"] == "ABORTED_CLOSED"
    assert result["terminal_state"] == "ABORTED_CLOSED"
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_pending_sigint_at_final_mask_restore_hides_handle_for_recovery() -> None:
    result = _run_real_helper("PENDING_SIGINT_FINAL_MASK_RESTORE")
    assert result["sigint_send_count"] == 1
    assert result["begin_error_type"] == "KeyboardInterrupt"
    assert result["handle_returned"] is False
    assert result["hidden_record_count"] == 1
    assert result["hidden_states"] == [
        "BEGIN_RETURN_SIGNAL_FAILED_QUARANTINED"
    ]
    assert result["signal_mask_restored_after_begin"] is True
    assert result["recovery_state"] == "ABORTED_CLOSED"
    assert result["terminal_state"] == "ABORTED_CLOSED"
    _assert_exact_terminal_cleanup(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_begin_quarantine_recovery_rejects_unrelated_child_before_effects() -> None:
    result = _run_real_helper("BEGIN_QUARANTINE_UNRELATED_CHILD_GUARD")
    assert result["begin_error_type"] == "RuntimeError"
    assert result["abort_call_count"] == 1
    assert result["unrelated_pid"] > 0
    assert result["rejection_error_type"] == (
        "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error"
    )
    assert result["effects_before_caller_reap"] == {
        "kill": 0,
        "waitid": 0,
        "inner_abort": 0,
    }
    assert result["state_after_rejection"] == (
        "BEGIN_CLEANUP_FAILED_QUARANTINED"
    )
    assert result["population_after_rejection"] >= 1
    assert result["unrelated_waited_pid"] == result["unrelated_pid"]
    assert result["unrelated_waited_exit_code"] == 0
    assert result["recovery_state"] == "BEGIN_FAILURE_RECOVERED_CLOSED"
    assert result["terminal_state"] == "BEGIN_FAILURE_RECOVERED_CLOSED"
    _assert_exact_terminal_cleanup(result)


def _assert_exact_terminal_cleanup(result: dict[str, object]) -> None:
    assert result["final_population"] == 0
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["outer_live_prefix_count"] == 0
    assert result["inner_live_session_count"] == 0
    assert result["begin_failure_quarantine_present"] is False
