from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import pickle
import signal
import stat
import threading

import pytest

from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1


DELEGATED_PARENT = os.environ.get("ACFQP_E5A_DELEGATED_PARENT_CGROUP")
requires_delegated_parent = pytest.mark.skipif(
    not DELEGATED_PARENT,
    reason="one fresh delegated E5A parent cgroup was not registered",
)
MIB = 1024 * 1024


def _id(label: str) -> str:
    return hashlib.sha256(f"b2a-test:{label}".encode("utf-8")).hexdigest()


def _prepare(parent_fd: int, ordinal: int = 0):
    return e5a_v1.prepare_h1_route_wide_working_set_cgroup_v1(
        delegated_parent_cgroup_fd=parent_fd,
        registered_hard_cap_bytes=96 * MIB,
        requested_outer_memory_max_bytes=64 * MIB,
        logical_occurrence_id=_id(f"occurrence:{ordinal}"),
        route_attempt_id=_id(f"attempt:{ordinal}"),
        decision_point_id=_id(f"decision:{ordinal}"),
        build_epoch_id=_id(f"epoch:{ordinal}"),
    )


def _open_parent() -> int:
    assert DELEGATED_PARENT is not None
    return os.open(
        Path(DELEGATED_PARENT),
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )


@pytest.fixture
def delegated_parent_fd():
    descriptor = _open_parent()
    assert e5a_v1._child_directories(descriptor) == ()
    try:
        yield descriptor
    finally:
        assert e5a_v1._child_directories(descriptor) == ()
        os.close(descriptor)


def test_bridge_manifest_freezes_exact_reviewed_e5a_source_and_layout() -> None:
    manifest = b2a_v1.frozen_e5a_runtime_bridge_manifest_v1()
    assert manifest["expected_e5a_source_sha256"] == (
        "70a32237ba72bf33aa924b65e8b45ee285090dd800ed049e66636e882d969287"
    )
    assert manifest["exact_lease_slots"] == list(
        b2a_v1._EXPECTED_E5A_LEASE_SLOTS
    )
    assert manifest["exact_canonical_fd_slots"] == list(
        e5a_v1._CANONICAL_FD_SLOTS
    )
    assert manifest["bridge_checks_live_object_identity"] is True
    assert manifest["bridge_runs_under_e5a_fd_ownership_lock"] is True
    assert manifest[
        "companion_adapter_must_be_in_future_execution_source_closure"
    ] is True
    assert manifest["public_api_forgery_rejected"] is True
    assert manifest["hostile_python_private_mutation_excluded_from_threat_boundary"] is True


def test_claims_stop_at_prepared_nonlaunchable_candidate_boundary() -> None:
    assert b2a_v1.PREPARED_E5A_SUCCESSOR_PRESENT is True
    assert b2a_v1.NONLAUNCHABLE_ONE_SHOT_LEAF_CANDIDATES_PRESENT is True
    assert b2a_v1.COMPANION_ADAPTER_IN_FUTURE_SOURCE_CLOSURE_REQUIRED is True
    for name in (
        "E5A_RUNTIME_LEASE_SUCCESSOR_PRESENT",
        "PURPOSE_BUILT_ONE_SHOT_LEAF_GRANTS_PRESENT",
        "EXECUTION_SOURCE_CLOSURE_PRESENT",
        "GUARDIAN_SESSION_PRESENT",
        "ACTUAL_PROCESS_BIRTH_PRESENT",
        "GUARDIAN_GATED_FIVE_ACTUAL_BIRTHS_PRESENT",
        "ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT",
        "PEAK_READ_PRESENT",
        "ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT",
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
        assert getattr(b2a_v1, name) is False
    assert b2a_v1.OFFICIAL_SCALAR_COST is None
    assert b2a_v1.OFFICIAL_N_BREAK_EVEN is None
    assert b2a_v1.COUNTER_COMPLETENESS_GATE == "NOT_RUN"
    assert b2a_v1.WORKLOAD_ECONOMICS_GATE == "NOT_RUN"


def test_registered_slot_map_is_exact_but_not_launch_authority() -> None:
    assert b2a_v1.SLOT_ORDER == (
        "SUPERVISOR",
        "PIDFD_PROBE",
        "BROKER",
        "WORKER",
        "BUSINESS",
    )
    assert dict(b2a_v1.SLOT_TO_LEAF) == {
        "SUPERVISOR": "CONTROL",
        "PIDFD_PROBE": "CONTROL",
        "BROKER": "CONTROL",
        "WORKER": "WORKER",
        "BUSINESS": "BUSINESS",
    }


def test_public_mapping_lookalike_and_caller_minted_objects_fail_closed() -> None:
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="exact E5A lease",
    ):
        b2a_v1.consume_h1_e5a_runtime_lease_successor_v1({})  # type: ignore[arg-type]
    fake = object.__new__(b2a_v1.H1E5ARuntimeLeaseSuccessorV1)
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="owner PID or thread",
    ):
        b2a_v1.verify_h1_e5a_runtime_lease_successor_v1(fake)
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="caller-minted",
    ):
        b2a_v1.H1E5ARuntimeLeaseSuccessorV1(
            None,
            source_lease=None,  # type: ignore[arg-type]
            hierarchy={},
            envelope={},
            fd_slots={},
            successor_document={},
        )
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="caller-minted",
    ):
        b2a_v1.H1E5ANonlaunchableLeafCandidateV1(
            None,
            runtime=fake,
            slot="SUPERVISOR",
            leaf="CONTROL",
        )
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="caller-minted",
    ):
        b2a_v1.H1E5ARuntimeLeaseClosureV1(b"{}")


def test_bridge_rejects_callable_or_global_monkeypatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(e5a_v1, "_verify_live_hierarchy", lambda _lease: {})
        with pytest.raises(
            b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
            match="callable identity changed",
        ):
            b2a_v1.frozen_e5a_runtime_bridge_manifest_v1()
    with monkeypatch.context() as patch:
        patch.setattr(e5a_v1, "_OWNED_FDS", {})
        with pytest.raises(
            b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
            match="global identity changed",
        ):
            b2a_v1.frozen_e5a_runtime_bridge_manifest_v1()
    b2a_v1.frozen_e5a_runtime_bridge_manifest_v1()


@pytest.mark.parametrize(
    "slot", [None, True, 1, "", "CONTROL", "OTHER", "supervisor"]
)
def test_candidate_slot_inputs_are_exact_before_runtime_use(slot) -> None:
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="registered exact slot",
    ):
        b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
            None, slot=slot  # type: ignore[arg-type]
        )


@requires_delegated_parent
def test_exact_transfer_verify_all_candidates_and_cleanup_handoff(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 1)
    original_fds = {
        slot: lease._fd_slots[slot] for slot in e5a_v1._CANONICAL_FD_SLOTS
    }
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert lease.state == "RUNTIME_TRANSFERRED"
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert all(
        lease._fd_slots[slot] == -1 for slot in e5a_v1._ALL_OWNED_FD_SLOTS
    )
    for slot, descriptor in original_fds.items():
        assert runtime._fd_slots[slot] == descriptor
        record = e5a_v1._OWNED_FDS[descriptor]
        assert record.owner is runtime and record.slot == slot
    with pytest.raises(
        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error
    ):
        e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
    with pytest.raises(
        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error
    ):
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)

    document = b2a_v1.verify_h1_e5a_runtime_lease_successor_v1(runtime)
    assert document["successor_state_at_issuance"] == "PREPARED_SUCCESSOR"
    assert document["source_e5a_state_after_transfer"] == "RUNTIME_TRANSFERRED"
    assert document["candidate_authorizes_clone_or_process_placement"] is False
    assert document["actual_process_birth_present"] is False
    assert document["route_wide_actual_peak_authority_present"] is False

    for expected_slot in b2a_v1.SLOT_ORDER:
        candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
            runtime, slot=expected_slot
        )
        leaf = b2a_v1.SLOT_TO_LEAF[expected_slot]
        descriptor = candidate._fd_slots[e5a_v1._role_fd_slot(leaf)]
        assert candidate.slot == expected_slot
        assert candidate.leaf == leaf
        assert candidate.launch_authority is False
        assert not hasattr(candidate, "fileno")
        assert not hasattr(candidate, "fd")
        assert candidate.state == "ISSUED"
        assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_PATH
        assert stat.S_ISDIR(os.fstat(descriptor).st_mode)
        assert e5a_v1._registry_fd_identity(descriptor) == (
            e5a_v1._registry_fd_identity(runtime._role_fds[leaf])
        )
        assert sum(value >= 0 for value in candidate._fd_slots.values()) == 1
        with pytest.raises(
            b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
            match="available exactly once",
        ):
            b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
                runtime, slot=expected_slot
            )
        b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
        assert candidate.state == "CLOSED"
        assert candidate._fd_slots[e5a_v1._role_fd_slot(leaf)] == -1
    assert set(runtime.grant_states().values()) == {"CONSUMED"}

    closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    closure_document = closure.to_document()
    assert runtime.state == "CLOSED"
    assert lease.state == "CLOSED"
    assert closure_document["source_e5a_lease_restored_active"] is False
    assert closure_document["source_e5a_cleanup_only_handoff"] is True
    assert closure_document["construction_only_cleanup_without_route_birth"] is True
    assert closure_document["route_peak_read_performed"] is False
    assert closure_document["actual_peak_issued"] is False
    assert closure_document["source_e5a_cleanup_closure_id"] == (
        lease._closure.closure_id
    )
    assert id(runtime) not in b2a_v1._LIVE_RUNTIME_LEASES
    assert id(runtime) not in b2a_v1._QUARANTINED_RUNTIME_LEASES
    assert not any(
        record.owner in {lease, runtime}
        for record in e5a_v1._OWNED_FDS.values()
    )


@requires_delegated_parent
def test_consume_racing_v1_cleanup_has_one_winner_and_no_deadlock(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 6)
    barrier = threading.Barrier(2)
    allow_successor_cleanup = threading.Event()
    consume_ready = threading.Event()
    outcomes: dict[str, object] = {}

    def consume() -> None:
        barrier.wait()
        try:
            runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
            outcomes["consume"] = runtime
            consume_ready.set()
            assert allow_successor_cleanup.wait(5)
            b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
        except BaseException as error:
            outcomes["consume"] = error
            consume_ready.set()

    def cleanup() -> None:
        barrier.wait()
        try:
            outcomes["cleanup"] = (
                e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
            )
        except BaseException as error:
            outcomes["cleanup"] = error

    consume_thread = threading.Thread(target=consume)
    cleanup_thread = threading.Thread(target=cleanup)
    consume_thread.start()
    cleanup_thread.start()
    cleanup_thread.join(5)
    assert not cleanup_thread.is_alive()
    allow_successor_cleanup.set()
    consume_thread.join(5)
    assert not consume_thread.is_alive()
    consume_won = isinstance(
        outcomes.get("consume"), b2a_v1.H1E5ARuntimeLeaseSuccessorV1
    )
    cleanup_won = isinstance(
        outcomes.get("cleanup"),
        e5a_v1.H1RouteWideWorkingSetCgroupCleanupClosureV1,
    )
    assert consume_won ^ cleanup_won
    assert lease.state == "CLOSED"
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert id(lease) not in e5a_v1._QUARANTINED_LEASES
    assert not any(record.owner is lease for record in e5a_v1._OWNED_FDS.values())


@requires_delegated_parent
def test_consume_racing_v1_verify_is_serialized_without_deadlock(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 7)
    barrier = threading.Barrier(2)
    allow_successor_cleanup = threading.Event()
    consume_ready = threading.Event()
    outcomes: dict[str, object] = {}

    def consume() -> None:
        barrier.wait()
        try:
            runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
            outcomes["consume"] = runtime
            consume_ready.set()
            assert allow_successor_cleanup.wait(5)
            b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
        except BaseException as error:
            outcomes["consume"] = error
            consume_ready.set()

    def verify() -> None:
        barrier.wait()
        try:
            outcomes["verify"] = (
                e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(
                    lease
                )
            )
        except BaseException as error:
            outcomes["verify"] = error

    consume_thread = threading.Thread(target=consume)
    verify_thread = threading.Thread(target=verify)
    consume_thread.start()
    verify_thread.start()
    verify_thread.join(5)
    assert not verify_thread.is_alive()
    assert consume_ready.wait(5)
    assert isinstance(
        outcomes.get("verify"),
        (dict, e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error),
    )
    assert isinstance(
        outcomes.get("consume"), b2a_v1.H1E5ARuntimeLeaseSuccessorV1
    )
    allow_successor_cleanup.set()
    consume_thread.join(5)
    assert not consume_thread.is_alive()
    assert lease.state == "CLOSED"


@requires_delegated_parent
def test_transfer_commit_defers_cleanup_reentrancy_until_old_is_retired(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(signal, "SIGUSR1"):
        pytest.skip("SIGUSR1 is unavailable")
    lease = _prepare(delegated_parent_fd, 9)
    observations: list[tuple[str, str]] = []
    previous = signal.getsignal(signal.SIGUSR1)

    def handler(_signum, _frame) -> None:
        try:
            e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
        except BaseException:
            observations.append(("REJECTED", lease.state))
        else:  # pragma: no cover - must be impossible
            observations.append(("CLOSED", lease.state))

    signal.signal(signal.SIGUSR1, handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                b2a_v1,
                "_TEST_ONLY_TRANSFER_COMMIT_HOOK",
                lambda _lease: os.kill(os.getpid(), signal.SIGUSR1),
            )
            runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
        assert observations == [("REJECTED", "RUNTIME_TRANSFERRED")]
        assert runtime.state == "PREPARED_SUCCESSOR"
        b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    finally:
        signal.signal(signal.SIGUSR1, previous)


@requires_delegated_parent
@pytest.mark.parametrize("fault_step", range(1, 12))
def test_each_transfer_commit_fault_finishes_forward_before_unmask(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
    fault_step: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 300 + fault_step)
    with monkeypatch.context() as patch:
        patch.setattr(
            b2a_v1, "_TEST_ONLY_TRANSFER_FAULT_AFTER_STEP", fault_step
        )
        runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    assert lease.state == "RUNTIME_TRANSFERRED"
    assert runtime.state == "PREPARED_SUCCESSOR"
    for slot in e5a_v1._CANONICAL_FD_SLOTS:
        descriptor = runtime._fd_slots[slot]
        assert descriptor >= 0
        assert e5a_v1._OWNED_FDS[descriptor].owner is runtime
        assert lease._fd_slots[slot] == -1
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_candidate_reservation_defers_same_slot_signal_reentrancy(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(signal, "SIGUSR1"):
        pytest.skip("SIGUSR1 is unavailable")
    lease = _prepare(delegated_parent_fd, 10)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    observations: list[str] = []
    previous = signal.getsignal(signal.SIGUSR1)
    candidate: b2a_v1.H1E5ANonlaunchableLeafCandidateV1 | None = None

    def handler(_signum, _frame) -> None:
        try:
            b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
                runtime, slot="SUPERVISOR"
            )
        except BaseException:
            observations.append(runtime.grant_states()["SUPERVISOR"])
        else:  # pragma: no cover - must be impossible
            observations.append("DUPLICATE_ISSUED")

    signal.signal(signal.SIGUSR1, handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                b2a_v1,
                "_TEST_ONLY_CANDIDATE_RESERVATION_HOOK",
                lambda _runtime, _slot: os.kill(os.getpid(), signal.SIGUSR1),
            )
            candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
                runtime, slot="SUPERVISOR"
            )
        assert observations in (["ISSUE_PENDING"], ["ISSUED"])
        assert sum(
            grant._runtime_id == id(runtime)
            for grant in b2a_v1._LIVE_GRANTS.values()
        ) == 1
    finally:
        signal.signal(signal.SIGUSR1, previous)
        if candidate is not None and candidate.state in {"ISSUED", "CLOSE_PENDING"}:
            b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
        if runtime.state in {"PREPARED_SUCCESSOR", "CLEANUP_PENDING"}:
            b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_runtime_and_candidate_are_uncopyable_and_thread_bound(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 2)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
        runtime, slot="SUPERVISOR"
    )
    try:
        for obj in (runtime, candidate):
            with pytest.raises(
                b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
                match="cannot be copied",
            ):
                copy.copy(obj)
            with pytest.raises(
                b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
                match="cannot be copied",
            ):
                copy.deepcopy(obj)
            with pytest.raises(
                b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
                match="cannot be copied or pickled",
            ):
                pickle.dumps(obj)
        errors: list[BaseException] = []

        def cross_thread() -> None:
            for operation in (
                lambda: b2a_v1.verify_h1_e5a_runtime_lease_successor_v1(runtime),
                lambda: b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(
                    candidate
                ),
            ):
                try:
                    operation()
                except BaseException as error:
                    errors.append(error)

        thread = threading.Thread(target=cross_thread)
        thread.start()
        thread.join()
        assert len(errors) == 2
        assert all(
            isinstance(
                error,
                b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
            )
            for error in errors
        )
    finally:
        if candidate.state in {"ISSUED", "CLOSE_PENDING"}:
            b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
        b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_candidate_close_failure_is_quarantined_and_never_reissued(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = _prepare(delegated_parent_fd, 3)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
        runtime, slot="WORKER"
    )
    target = candidate._fd_slots[e5a_v1._role_fd_slot("WORKER")]
    original_close = e5a_v1._OS_CLOSE

    def refuse_target(descriptor: int) -> None:
        if descriptor == target:
            raise OSError(errno.EIO, "injected candidate close failure")
        original_close(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(e5a_v1.os, "close", refuse_target)
        with pytest.raises(RuntimeError, match="close-only quarantine"):
            b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
    assert candidate.state == "CLOSE_PENDING"
    assert runtime.grant_states()["WORKER"] == "CLOSE_PENDING"
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="available exactly once",
    ):
        b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
            runtime, slot="WORKER"
        )
    b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
    assert candidate.state == "CLOSED"
    assert runtime.grant_states()["WORKER"] == "CONSUMED"
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_candidate_validation_exception_never_leaves_unreachable_owner(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = _prepare(delegated_parent_fd, 8)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    original_fcntl = b2a_v1.fcntl.fcntl

    def fail_candidate_flag_read(*_args, **_kwargs):
        raise OSError(errno.EIO, "injected candidate validation failure")

    with monkeypatch.context() as patch:
        patch.setattr(b2a_v1.fcntl, "fcntl", fail_candidate_flag_read)
        with pytest.raises(OSError, match="candidate validation failure"):
            b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
                runtime, slot="PIDFD_PROBE"
            )
    assert b2a_v1.fcntl.fcntl is original_fcntl
    assert runtime.grant_states()["PIDFD_PROBE"] == "CONSUMED"
    assert not any(
        grant._runtime_id == id(runtime)
        for grant in b2a_v1._LIVE_GRANTS.values()
    )
    assert not any(
        type(record.owner) is b2a_v1.H1E5ANonlaunchableLeafCandidateV1
        and record.owner._runtime_id == id(runtime)
        for record in e5a_v1._OWNED_FDS.values()
    )
    with pytest.raises(
        b2a_v1.ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error,
        match="available exactly once",
    ):
        b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
            runtime, slot="PIDFD_PROBE"
        )
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
@pytest.mark.parametrize("fault_step", range(1, 12))
def test_each_handoff_commit_fault_finishes_forward_to_v1_cleanup(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
    fault_step: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 100 + fault_step)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    with monkeypatch.context() as patch:
        patch.setattr(
            b2a_v1, "_TEST_ONLY_HANDOFF_FAULT_AFTER_STEP", fault_step
        )
        closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    assert closure.to_document()["source_e5a_lease_restored_active"] is False
    assert runtime._handoff_phase == "COMPLETE"
    assert runtime.state == "CLOSED"
    assert lease.state == "CLOSED"
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert id(lease) not in e5a_v1._QUARANTINED_LEASES
    assert id(runtime) not in b2a_v1._LIVE_RUNTIME_LEASES
    assert id(runtime) not in b2a_v1._QUARANTINED_RUNTIME_LEASES


@requires_delegated_parent
@pytest.mark.parametrize("fault_step", (1, 2))
def test_each_closure_commit_fault_finishes_before_unmask(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
    fault_step: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 200 + fault_step)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    with monkeypatch.context() as patch:
        patch.setattr(
            b2a_v1, "_TEST_ONLY_CLOSURE_FAULT_AFTER_STEP", fault_step
        )
        closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    assert runtime.state == "CLOSED"
    assert runtime._closure is closure
    assert id(runtime) not in b2a_v1._LIVE_RUNTIME_LEASES
    assert id(runtime) not in b2a_v1._QUARANTINED_RUNTIME_LEASES
    assert b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime) is closure


@requires_delegated_parent
def test_fork_child_raw_closes_and_poisons_successor_and_candidate(
    delegated_parent_fd: int,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    lease = _prepare(delegated_parent_fd, 4)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
        runtime, slot="BUSINESS"
    )
    retained = tuple(
        runtime._fd_slots[slot] for slot in e5a_v1._CANONICAL_FD_SLOTS
    ) + (candidate._fd_slots[e5a_v1._role_fd_slot("BUSINESS")],)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through parent packet
        os.close(read_fd)
        ok = runtime.state == "FORK_POISONED"
        ok = ok and candidate.state == "FORK_POISONED"
        ok = ok and not b2a_v1._LIVE_RUNTIME_LEASES
        ok = ok and not b2a_v1._LIVE_GRANTS
        for descriptor in retained:
            try:
                os.fstat(descriptor)
            except OSError as error:
                ok = ok and error.errno == errno.EBADF
            else:
                ok = False
        os.write(write_fd, b"1" if ok else b"0")
        os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    try:
        assert os.read(read_fd, 1) == b"1"
        waited, status = os.waitpid(child, 0)
        assert waited == child and os.waitstatus_to_exitcode(status) == 0
        assert runtime.state == "PREPARED_SUCCESSOR"
        assert candidate.state == "ISSUED"
        assert all(os.fstat(descriptor) for descriptor in retained)
    finally:
        os.close(read_fd)
        b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
        b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_cleanup_handoff_close_failure_stays_e5a_quarantined_then_retries(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = _prepare(delegated_parent_fd, 5)
    runtime = b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)
    target = runtime._memory_peak_fd
    original_close = e5a_v1._OS_CLOSE

    def refuse_target(descriptor: int) -> None:
        if descriptor == target:
            raise OSError(errno.EIO, "injected runtime handoff close failure")
        original_close(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(e5a_v1.os, "close", refuse_target)
        with pytest.raises(RuntimeError, match="retained FD close remains live"):
            b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    assert runtime.state == "CLEANUP_PENDING"
    assert runtime._source_handed_back is True
    assert lease.state == "CLEANUP_PENDING"
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert e5a_v1._QUARANTINED_LEASES[id(lease)] is lease
    assert id(runtime) not in b2a_v1._LIVE_RUNTIME_LEASES
    assert b2a_v1._QUARANTINED_RUNTIME_LEASES[id(runtime)] is runtime
    closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
    assert runtime.state == "CLOSED"
    assert lease.state == "CLOSED"
    assert closure.to_document()["cleanup_attempt_count"] == 2
    assert closure.to_document()["source_e5a_lease_restored_active"] is False
