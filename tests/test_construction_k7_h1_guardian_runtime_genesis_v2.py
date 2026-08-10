from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import construction_k7_h1_domain_registry_extension_v19 as domains_v19
from acfqp import construction_k7_h1_guardian_runtime_genesis_v2 as v2


HELPER = Path(__file__).with_name("_guardian_runtime_genesis_v2_subprocess.py")


def test_v2_is_additive_and_claims_stop_before_any_birth() -> None:
    for name in (
        "ADDITIVE_GUARDIAN_RUNTIME_V2_PRESENT",
        "EXACT_B2A_PREPARED_INPUT_PRESENT",
        "FIVE_DISTINCT_NONLAUNCHABLE_GRANTS_ESCROWED",
        "PUBLIC_TYPED_HANDOFF_PRESENT",
        "UNCONSUMED_REVOKE_AND_CLEANUP_PRESENT",
        "DURABLE_SOURCE_AND_HANDOFF_GRAPH_PRESENT",
        "PUBLIC_PREPARED_TAKEOVER_SEAM_PRESENT",
    ):
        assert getattr(v2, name) is True
    for name in (
        "PERMIT_CONSUMPTION_PATH_PRESENT",
        "CLONE_SYSCALL_PERFORMED",
        "ACTUAL_PROCESS_BIRTH_PRESENT",
        "PROCESS_LAUNCH_COUNT_AUTHORITY_PRESENT",
        "SHARED_PID_CELL_PRESENT",
        "PIDFD_ESCROW_PRESENT",
        "CGROUP_MEMBERSHIP_OBSERVATION_PRESENT",
        "PROCESS_DEATH_OR_REAP_PRESENT",
        "PEAK_READ_PRESENT",
        "ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT",
        "THREE_BIRTH_PREFIX_AUTHORITY_PRESENT",
        "FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT",
        "ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT",
        "E4_V2_COMPLETION_PRESENT",
        "PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT",
        "FQ11_COUNTER_COMPLETENESS_PRESENT",
        "FORMAL_COUNTER_RECORDS_ISSUED",
        "FORMAL_WORK_VECTOR_ISSUED",
        "FORMAL_COMPARISON_VECTOR_ISSUED",
        "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
        "CURRENT_ACCESS_AUTHORITY_PRESENT",
        "FORMAL_V7_AUTHORITY_PRESENT",
        "OFFICIAL_EXECUTION_ALLOWED",
    ):
        assert getattr(v2, name) is False
    assert v2.OFFICIAL_SCALAR_COST is None
    assert v2.OFFICIAL_N_BREAK_EVEN is None
    assert v2.COUNTER_COMPLETENESS_GATE == "NOT_RUN"
    assert v2.WORKLOAD_ECONOMICS_GATE == "NOT_RUN"


def test_v2_does_not_import_frozen_v1_or_b2c_private_authority() -> None:
    source = Path(v2.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("guardian_runtime_genesis_v1" in name for name in imported)
    assert not any("actual_observed_supervisor_birth_v1" in name for name in imported)
    repository = Path(v2.__file__).parents[2]
    assert hashlib.sha256(
        (repository / "src/acfqp/construction_k7_h1_guardian_runtime_genesis_v1.py").read_bytes()
    ).hexdigest() == "c3641be8cd43b6a56208d7ed99bd2f687b00a6f3961d0fa0641230497ab4b3cf"
    assert hashlib.sha256(
        (repository / "src/acfqp/construction_k7_h1_actual_observed_supervisor_birth_v1.py").read_bytes()
    ).hexdigest() == "5af883d34e0f021a726e6c6becd31a09a6a9437b4371a171133068288aa38a1f"


def test_preregistration_and_public_objects_are_not_caller_mintable_or_copyable() -> None:
    with pytest.raises(v2.ConstructionK7H1GuardianRuntimeGenesisV2Error, match="caller-minted"):
        v2.H1GuardianRuntimeGenesisPreregistrationV2(b"{}")
    with pytest.raises(v2.ConstructionK7H1GuardianRuntimeGenesisV2Error, match="caller-minted"):
        v2.H1GuardianRuntimePermitHandoffV2(object())
    with pytest.raises(v2.ConstructionK7H1GuardianRuntimeGenesisV2Error, match="caller-minted"):
        v2.H1GuardianRuntimeCancellationV2(b"{}")
    fake = object.__new__(v2.H1GuardianRuntimePermitHandoffV2)
    fake_adapter = object.__new__(v2.H1GuardianRuntimeConsumerAdapterV2)
    fake_takeover = object.__new__(v2.H1GuardianRuntimePreparedTakeoverV2)
    for value in (fake, fake_adapter, fake_takeover):
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(v2.ConstructionK7H1GuardianRuntimeGenesisV2Error):
                operation(value)


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (b2a_v1, "verify_h1_e5a_runtime_lease_successor_v1"),
        (b2a_v1, "issue_h1_e5a_nonlaunchable_leaf_candidate_v1"),
        (e5a_v1, "_registry_fd_identity"),
        (e5a_v1, "_restore_fd_publication_signals"),
    ],
)
def test_live_upstream_callable_substitution_fails_closed(
    monkeypatch: pytest.MonkeyPatch, module, name: str
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(module, name, lambda *_args, **_kwargs: None)
        with pytest.raises(
            v2.ConstructionK7H1GuardianRuntimeGenesisV2Error,
            match="callable identity changed",
        ):
            v2.preregister_h1_guardian_runtime_genesis_v2()
    v2._validate_live_code_closure()  # noqa: SLF001


def test_v19_domain_constant_substitution_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(
            domains_v19,
            "CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CANCELLATION_V1_DOMAIN",
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_FAILURE_CLOSURE_V1_DOMAIN,
        )
        with pytest.raises(
            v2.ConstructionK7H1GuardianRuntimeGenesisV2Error,
            match="domain identity changed",
        ):
            v2.preregister_h1_guardian_runtime_genesis_v2()
    v2._validate_live_code_closure()  # noqa: SLF001


@pytest.mark.parametrize(
    "name",
    [
        "_source_closure_payload",
        "_source_fact",
        "_source_digest_summary",
        "_open_private_empty_journal",
        "_same_owner",
        "_same_owner_object",
        "_exact_write",
        "_exact_identity",
        "_process_start_ticks",
    ],
)
def test_every_local_helper_boundary_substitution_fails_closed(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(v2, name, lambda *_args, **_kwargs: None)
        with pytest.raises(
            v2.ConstructionK7H1GuardianRuntimeGenesisV2Error,
            match="local callable identity changed",
        ):
            v2._validate_live_code_closure()  # noqa: SLF001
    v2._validate_live_code_closure()  # noqa: SLF001


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (b2a_v1, "_issue_candidate_under_signal_shield_unlocked"),
        (b2a_v1, "_close_grant_unlocked"),
        (b2a_v1, "_close_h1_e5a_runtime_lease_successor_impl_v1"),
        (e5a_v1, "_duplicate_owned_fd"),
        (e5a_v1, "_close_owned_fd_slot"),
    ],
)
def test_recursive_b2a_e5a_dependency_substitution_fails_closed(
    monkeypatch: pytest.MonkeyPatch, module, name: str
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(module, name, lambda *_args, **_kwargs: None)
        with pytest.raises(
            v2.ConstructionK7H1GuardianRuntimeGenesisV2Error,
            match="callable identity changed",
        ):
            v2.preregister_h1_guardian_runtime_genesis_v2()
    v2._validate_live_code_closure()  # noqa: SLF001


def test_public_future_consumer_boundary_is_exported_but_nonconsuming() -> None:
    assert "register_h1_guardian_runtime_consumer_adapter_v2" in v2.__all__
    assert "prepare_h1_guardian_runtime_consumer_takeover_v2" in v2.__all__
    assert "cancel_h1_guardian_runtime_prepared_takeover_v2" in v2.__all__
    assert v2.PERMIT_CONSUMPTION_PATH_PRESENT is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_GUARDIAN_V2") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_exact_b2a_to_v2_handoff_attacks_and_cleanup() -> None:
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
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result == {
        "atfork_child_rejected": True,
        "basic_cancel_replay_equal": True,
        "basic_cancellation_verified": True,
        "basic_grant_count": 5,
        "basic_handoff_state": "HANDOFF_ESCROWED_UNCONSUMED",
        "basic_journal_event_count": 8,
        "basic_runtime_state": "CLOSED",
        "cancel_fault_recovered": True,
        "cancel_fault_retryable_state": "CANCEL_CLEANUP_PENDING",
        "cancel_fsync_finish_forward": True,
        "copy_attack_count": 3,
        "compound_restore_failure_recovered": True,
        "failure_closure_present": True,
        "grant_swap_rejected": True,
        "identity_swap_rejected": True,
        "journal_tamper_rejected": True,
        "journal_boundary_finish_forward_count": 4,
        "local_callable_substitution_rejected": True,
        "partial_start_fault_closed": True,
        "parent_survived_atfork": True,
        "reservations_after_all_cases": 0,
        "start_fault_runtime_reusable": True,
        "start_boundary_finish_forward": True,
        "takeover_copy_attack_count": 6,
        "takeover_prepared": True,
        "terminal_mutation_rejected": True,
        "terminal_replay_mutation_rejected": True,
        "wrong_thread_cancel_rejected": True,
        "wrong_thread_verify_rejected": True,
    }
