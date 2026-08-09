from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import pickle
import signal
import tempfile

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_guardian_runtime_genesis_v1 as b2b_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import phase3e_ids as ids_v1


DELEGATED_PARENT = os.environ.get("ACFQP_E5A_DELEGATED_PARENT_CGROUP")
requires_delegated_parent = pytest.mark.skipif(
    not DELEGATED_PARENT,
    reason="one fresh delegated E5A parent cgroup was not registered",
)
MIB = 1024 * 1024
PERSIST_FAULT_PHASES = (
    "AFTER_OPEN",
    "AFTER_PARTIAL_WRITE",
    "AFTER_FULL_WRITE",
    "AFTER_FILE_FSYNC",
    "AFTER_DIRECTORY_FSYNC",
)


def _id(label: str) -> str:
    return hashlib.sha256(f"b2b-test:{label}".encode()).hexdigest()


def _prepare(parent_fd: int, ordinal: int):
    lease = e5a_v1.prepare_h1_route_wide_working_set_cgroup_v1(
        delegated_parent_cgroup_fd=parent_fd,
        registered_hard_cap_bytes=96 * MIB,
        requested_outer_memory_max_bytes=64 * MIB,
        logical_occurrence_id=_id(f"occurrence:{ordinal}"),
        route_attempt_id=_id(f"attempt:{ordinal}"),
        decision_point_id=_id(f"decision:{ordinal}"),
        build_epoch_id=_id(f"epoch:{ordinal}"),
    )
    return b2a_v1.consume_h1_e5a_runtime_lease_successor_v1(lease)


@pytest.fixture
def delegated_parent_fd():
    assert DELEGATED_PARENT is not None
    descriptor = os.open(
        Path(DELEGATED_PARENT),
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    assert e5a_v1._child_directories(descriptor) == ()
    try:
        yield descriptor
    finally:
        assert e5a_v1._child_directories(descriptor) == ()
        os.close(descriptor)


@pytest.fixture
def private_journal():
    path = Path(tempfile.mkdtemp(prefix="acfqp-b2b-", dir="/tmp"))
    path.chmod(0o700)
    try:
        yield path
    finally:
        for child in path.iterdir():
            child.unlink()
        path.rmdir()


def test_claims_stop_at_bounded_running_unconsumed_permit() -> None:
    for name in (
        "BOUNDED_GUARDIAN_SOURCE_CLOSURE_PRESENT",
        "GUARDIAN_SESSION_PRESENT",
        "OUTER_CGROUP_KILL_PIN_PRESENT",
        "RUNTIME_RUNNING_STATE_PRESENT",
        "UNCONSUMED_SUPERVISOR_BIRTH_PERMIT_PRESENT",
        "DISTINCT_CONTROL_OPATH_GRANT_PRESENT",
        "AUDIT_ONLY_TRAMPOLINE_SOURCE_CLOSED",
    ):
        assert getattr(b2b_v1, name) is True
    for name in (
        "PRODUCTION_FULL_EXECUTION_SOURCE_CLOSURE_PRESENT",
        "EXTERNAL_PREREGISTRATION_ANCHOR_PRESENT",
        "ASSEMBLED_OR_EXECUTABLE_TRAMPOLINE_PRESENT",
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
        assert getattr(b2b_v1, name) is False
    assert b2b_v1.OFFICIAL_SCALAR_COST is None
    assert b2b_v1.OFFICIAL_N_BREAK_EVEN is None
    assert b2b_v1.COUNTER_COMPLETENESS_GATE == "NOT_RUN"
    assert b2b_v1.WORKLOAD_ECONOMICS_GATE == "NOT_RUN"


def test_preregistration_redacts_arbitrary_argv_and_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "b2b-never-persist-this-secret-value"
    monkeypatch.setenv("ACFQP_TEST_SECRET_TOKEN", secret)
    monkeypatch.setattr(b2b_v1.sys, "argv", ["runner", secret])
    document = b2b_v1._prereg_payload(
        guardian={"pid": 1}, namespaces={"pid": "pid:[1]"}
    )
    raw = ids_v1.canonical_json_bytes(document)
    assert secret.encode() not in raw
    assert b"ACFQP_TEST_SECRET_TOKEN" not in raw
    assert document["argv_environment_input_allowlist"] == []
    assert document["argv_observed_or_used"] is False
    assert document["environment_observed_or_used"] is False
    assert document["argv_environment_values_or_digests_persisted"] is False


def test_clone_abi_includes_parent_settid_but_audit_source_has_no_instruction() -> None:
    abi = b2b_v1._platform_contract()
    assert abi["registered_clone_flags"] & 0x00100000
    assert abi["clone_args_field_offsets"]["parent_tid"] == 24
    assert abi["clone_args_size"] == 88
    raw = b2b_v1._TRAMPOLINE_SOURCE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "83ee8434bd99cf046fe85d6975886c6cbeb2b8cadd5c19edf1bc2bd4deacbf91"
    )
    assert b"syscall" not in b"\n".join(
        line.strip() for line in raw.splitlines() if not line.lstrip().startswith(b"*")
    ).lower()


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (b2a_v1, "_verify_source_lease_retired"),
        (domains_v15, "extension_content_id_v15"),
        (ids_v1, "canonical_json_bytes"),
        (e5a_v1, "_same_open_file_description_for_close"),
    ],
)
def test_live_code_monkeypatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch, module, name: str
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(module, name, lambda *_args, **_kwargs: None)
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="callable identity changed",
        ):
            b2b_v1._validate_live_code_closure()
    b2b_v1._validate_live_code_closure()


def test_in_place_upstream_code_replacement_fails_closed() -> None:
    target = b2a_v1._verify_source_lease_retired
    original_code = target.__code__

    def replacement(_runtime) -> None:
        return None

    try:
        target.__code__ = replacement.__code__
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="callable identity changed",
        ):
            b2b_v1._validate_live_code_closure()
    finally:
        target.__code__ = original_code
    b2b_v1._validate_live_code_closure()


def test_transaction_recovery_helper_monkeypatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_resume_pending_record", lambda *_args: None)
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="self live-code callable identity changed",
        ):
            b2b_v1._validate_live_code_closure()
    b2b_v1._validate_live_code_closure()


def test_caller_minted_and_copy_objects_fail_closed() -> None:
    with pytest.raises(
        b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
        match="caller-minted",
    ):
        b2b_v1.H1GuardianRuntimeGenesisPreregistrationV1(b"{}")
    fake = object.__new__(b2b_v1.H1GuardianRuntimeGenesisV1)
    with pytest.raises(
        b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
        match="caller-minted",
    ):
        b2b_v1.H1GuardianRuntimeGenesisV1(
            None,
            runtime=None,  # type: ignore[arg-type]
            preregistration=None,  # type: ignore[arg-type]
            journal_path=Path("/tmp"),
            start_token=object(),
        )
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error
        ):
            operation(fake)


def test_b2b_fd_publication_rejects_e5a_registry_collision() -> None:
    session = object.__new__(b2b_v1.H1GuardianRuntimeGenesisV1)
    session._fd_slots = {"collision": -1, "retry-witness:collision": -1}
    descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    owner = object()
    e5a_v1._OWNED_FDS[descriptor] = e5a_v1._OwnedFDRecordV1(
        owner=owner,
        slot="foreign",
        identity=e5a_v1._registry_fd_identity(descriptor),
    )
    try:
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="collided with registered ownership",
        ):
            b2b_v1._publish_fd(session, "collision", descriptor)
        assert e5a_v1._OWNED_FDS[descriptor].owner is owner
        assert session._fd_slots["collision"] == -1
    finally:
        e5a_v1._OWNED_FDS.pop(descriptor, None)
        os.close(descriptor)


@requires_delegated_parent
def test_precommit_failure_rolls_back_and_preserves_exact_prepared(
    delegated_parent_fd: int,
) -> None:
    runtime = _prepare(delegated_parent_fd, 1)
    preregistration = b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
    path = Path(tempfile.mkdtemp(prefix="acfqp-b2b-insecure-", dir="/tmp"))
    path.chmod(0o755)
    try:
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="private and empty",
        ):
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=preregistration,
                journal_directory=path,
            )
        assert runtime.state == "PREPARED_SUCCESSOR"
        assert b2a_v1._LIVE_RUNTIME_LEASES[id(runtime)] is runtime
        assert not b2b_v1._LIVE_SESSIONS
        assert not b2b_v1._QUARANTINED_SESSIONS
        assert not b2b_v1._MANAGED_FDS
    finally:
        path.chmod(0o700)
        path.rmdir()
        b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_preexisting_b2a_candidate_rejects_b2b_pristine_handoff(
    delegated_parent_fd: int,
    private_journal: Path,
) -> None:
    runtime = _prepare(delegated_parent_fd, 101)
    candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
        runtime, slot="SUPERVISOR"
    )
    with pytest.raises(
        b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
        match="pristine B2-A runtime",
    ):
        b2b_v1.start_h1_guardian_runtime_genesis_v1(
            runtime,
            preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
            journal_directory=private_journal,
        )
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert candidate.state == "ISSUED"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    assert not tuple(private_journal.iterdir())
    b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_guardian_credential_change_after_preregistration_fails_before_reservation(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 102)
    preregistration = b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
    identity = preregistration.to_document()["expected_guardian_identity"]
    assert identity["kernel_boot_id"]
    assert identity["effective_uid"] == os.geteuid()
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1.os, "geteuid", lambda: identity["effective_uid"] + 1)
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="identity, ABI, or namespace changed",
        ):
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=preregistration,
                journal_directory=private_journal,
            )
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_durable_permit_precommit_failure_persists_abort_before_reuse(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 11)
    monkeypatch.setattr(b2b_v1, "_TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT", True)
    with pytest.raises(RuntimeError, match="after durable permit"):
        b2b_v1.start_h1_guardian_runtime_genesis_v1(
            runtime,
            preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
            journal_directory=private_journal,
        )
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert len(tuple(private_journal.iterdir())) == 5
    abort = sorted(private_journal.iterdir())[-1].read_bytes()
    assert b"ABORTED_BEFORE_RUNNING_COMMIT" in abort
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_precommit_abort_failure_reserves_runtime_until_exact_retry(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 12)
    preregistration = b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT", True)
        patch.setattr(b2b_v1, "_TEST_ONLY_PRECOMMIT_ABORT_FAILURE", True)
        with pytest.raises(
            b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
            match="retryable cleanup quarantine",
        ) as captured:
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=preregistration,
                journal_directory=private_journal,
            )
    handle = captured.value.cleanup_handle
    assert handle is not None
    assert runtime.state == "B2B_PRECOMMIT_QUARANTINED"
    assert b2b_v1._RUNTIME_RESERVATIONS[id(runtime)] is handle
    with pytest.raises(
        b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
        match="already has",
    ):
        b2b_v1.start_h1_guardian_runtime_genesis_v1(
            runtime,
            preregistration=preregistration,
            journal_directory=private_journal,
        )
    b2b_v1.retry_h1_guardian_runtime_precommit_cleanup_v1(handle)
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
@pytest.mark.parametrize("phase", PERSIST_FAULT_PHASES)
def test_pending_permit_record_recovers_before_exact_precommit_abort(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    runtime = _prepare(delegated_parent_fd, 120)
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_TEST_ONLY_PERSIST_FAULT_PHASE", phase)
        patch.setattr(
            b2b_v1,
            "_TEST_ONLY_PERSIST_FAULT_EVENT",
            "SUPERVISOR_BIRTH_PERMIT",
        )
        with pytest.raises(RuntimeError, match="journal fault"):
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
                journal_directory=private_journal,
            )
    records = sorted(private_journal.iterdir())
    assert len(records) == 5
    assert [path.name.split("_", 2)[1] for path in records] == [
        "SOURCE",
        "GUARDIAN",
        "SUPERVISOR",
        "SUPERVISOR",
        "PRECOMMIT",
    ]
    documents = [ids_v1.loads_canonical_json(path.read_bytes()) for path in records]
    for path, document in zip(records, documents, strict=True):
        assert ids_v1.canonical_json_bytes(document) == path.read_bytes()
    permit_id = documents[3]["actual_process_birth_permit_id"]
    abort = documents[4]
    assert abort["actual_process_birth_permit_id"] == permit_id
    assert abort["terminal_state"] == "ABORTED_BEFORE_RUNNING_COMMIT"
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    assert not b2b_v1._MANAGED_FDS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_pending_intent_record_recovers_before_abort_payload_is_built(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 121)
    with monkeypatch.context() as patch:
        patch.setattr(
            b2b_v1, "_TEST_ONLY_PERSIST_FAULT_PHASE", "AFTER_FULL_WRITE"
        )
        patch.setattr(
            b2b_v1,
            "_TEST_ONLY_PERSIST_FAULT_EVENT",
            "SUPERVISOR_BIRTH_INTENT",
        )
        with pytest.raises(RuntimeError, match="journal fault"):
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
                journal_directory=private_journal,
            )
    records = sorted(private_journal.iterdir())
    assert len(records) == 4
    documents = [ids_v1.loads_canonical_json(path.read_bytes()) for path in records]
    intent_id = documents[2]["actual_process_birth_intent_id"]
    abort = documents[3]
    assert abort["actual_process_birth_intent_id"] == intent_id
    assert abort["actual_process_birth_permit_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "PERMIT_NOT_PERSISTED",
    }
    assert runtime.state == "PREPARED_SUCCESSOR"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    assert not b2b_v1._MANAGED_FDS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_precommit_cleanup_defers_reentrant_signal_until_exact_terminal_state(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 122)
    holder: dict[str, object] = {}
    observations: list[tuple[str, str, bool, bool]] = []
    sent = False

    def handler(_signum, _frame) -> None:
        session = holder["session"]
        assert isinstance(session, b2b_v1.H1GuardianRuntimeGenesisV1)
        retry_rejected = False
        try:
            b2b_v1.retry_h1_guardian_runtime_precommit_cleanup_v1(session)
        except b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error:
            retry_rejected = True
        observations.append(
            (
                session.state,
                runtime.state,
                id(runtime) in b2b_v1._RUNTIME_RESERVATIONS,
                retry_rejected,
            )
        )
        raise RuntimeError("deferred precommit cleanup signal")

    def hook(phase: str, session, _slot: str | None) -> None:
        nonlocal sent
        if phase == "AFTER_PRECOMMIT_RUNTIME_QUARANTINE" and not sent:
            sent = True
            holder["session"] = session
            os.kill(os.getpid(), signal.SIGUSR1)

    previous = signal.signal(signal.SIGUSR1, handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                b2b_v1, "_TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT", True
            )
            patch.setattr(b2b_v1, "_TEST_ONLY_CLEANUP_BOUNDARY_HOOK", hook)
            # The deferred handler raises only after exact cleanup.  The public
            # wrapper preserves the original construction error.
            with pytest.raises(RuntimeError, match="after durable permit"):
                b2b_v1.start_h1_guardian_runtime_genesis_v1(
                    runtime,
                    preregistration=(
                        b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
                    ),
                    journal_directory=private_journal,
                )
    finally:
        signal.signal(signal.SIGUSR1, previous)
    assert sent
    assert observations == [
        ("ABORTED_PRECOMMIT", "PREPARED_SUCCESSOR", False, True)
    ]
    assert not b2b_v1._MANAGED_FDS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_start_cleanup_entry_window_is_covered_by_outer_signal_shield(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 123)
    observed: list[tuple[str, str, bool]] = []
    sent = False
    holder: dict[str, b2b_v1.H1GuardianRuntimeGenesisV1] = {}

    def handler(_signum, _frame) -> None:
        session = holder["session"]
        observed.append(
            (
                session.state,
                runtime.state,
                id(runtime) in b2b_v1._RUNTIME_RESERVATIONS,
            )
        )
        raise RuntimeError("deferred cleanup-entry signal")

    def hook(phase: str, session, _slot: str | None) -> None:
        nonlocal sent
        if phase == "AFTER_STARTING_SESSION_DISCOVERY" and not sent:
            sent = True
            holder["session"] = session
            os.kill(os.getpid(), signal.SIGUSR1)

    previous = signal.signal(signal.SIGUSR1, handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                b2b_v1, "_TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT", True
            )
            patch.setattr(b2b_v1, "_TEST_ONLY_CLEANUP_BOUNDARY_HOOK", hook)
            with pytest.raises(RuntimeError, match="after durable permit"):
                b2b_v1.start_h1_guardian_runtime_genesis_v1(
                    runtime,
                    preregistration=(
                        b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
                    ),
                    journal_directory=private_journal,
                )
    finally:
        signal.signal(signal.SIGUSR1, previous)
    assert sent
    assert observed == [("ABORTED_PRECOMMIT", "PREPARED_SUCCESSOR", False)]
    assert not b2b_v1._MANAGED_FDS
    b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)


@requires_delegated_parent
def test_running_intent_permit_kill_pin_and_exact_cleanup(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 2)
    writes: list[int] = []
    original_write = b2b_v1._OS_WRITE

    def observed_write(descriptor: int, raw: bytes) -> int:
        writes.append(descriptor)
        return original_write(descriptor, raw)

    monkeypatch.setattr(b2b_v1, "_OS_WRITE", observed_write)
    preregistration = b2b_v1.preregister_h1_guardian_runtime_genesis_v1()
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=preregistration,
        journal_directory=private_journal,
    )
    assert runtime.state == session.state == "RUNNING"
    permit = session.permit
    assert permit.state == "ISSUED_UNCONSUMED"
    assert permit.launch_authority_in_this_slice is False
    assert len(session._records) == 4
    assert len(tuple(private_journal.iterdir())) == 4
    kill_fd = session._fd_slots["cgroup:kill"]
    grant_fd = session._fd_slots["grant:SUPERVISOR:CONTROL"]
    control_fd = runtime._role_fds["CONTROL"]
    assert kill_fd not in writes
    assert fcntl.fcntl(kill_fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_WRONLY
    assert grant_fd != control_fd
    assert not e5a_v1._same_open_file_description_for_close(grant_fd, control_fd)
    document = b2b_v1.verify_h1_guardian_runtime_genesis_v1(session)
    assert document["runtime_live_state"] == "RUNNING"
    assert document["permit_live_state"] == "ISSUED_UNCONSUMED"
    closure = b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert kill_fd not in writes
    assert session.state == runtime.state == "CLOSED"
    assert permit.state == "REVOKED_OR_CLOSED"
    assert closure.to_document()["actual_process_birth_present"] is False
    assert len(tuple(private_journal.iterdir())) == 5


@requires_delegated_parent
def test_commit_fault_finishes_forward_without_birth(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 3)
    monkeypatch.setattr(b2b_v1, "_TEST_ONLY_COMMIT_FAULT_AFTER_STEP", 1)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    assert session.state == runtime.state == "RUNNING"
    assert session.permit.to_document()["clone_or_process_birth_performed"] is False
    b2b_v1.close_h1_guardian_runtime_genesis_v1(session)


@requires_delegated_parent
def test_post_starting_pop_fault_uses_exact_reservation_and_cleans(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 32)
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_TEST_ONLY_POST_STARTING_POP_FAULT", True)
        with pytest.raises(RuntimeError, match="starting-map pop"):
            b2b_v1.start_h1_guardian_runtime_genesis_v1(
                runtime,
                preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
                journal_directory=private_journal,
            )
    assert runtime.state == "CLOSED"
    assert id(runtime) not in b2b_v1._RUNTIME_RESERVATIONS
    assert not b2b_v1._MANAGED_FDS


@requires_delegated_parent
def test_b2a_closed_then_exception_finishes_b2b_closed_idempotently(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 31)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    original = b2a_v1.close_h1_e5a_runtime_lease_successor_v1

    def close_then_raise(target):
        original(target)
        raise RuntimeError("injected post-B2A-close signal error")

    with monkeypatch.context() as patch:
        patch.setattr(
            b2a_v1,
            "close_h1_e5a_runtime_lease_successor_v1",
            close_then_raise,
        )
        with pytest.raises(RuntimeError, match="post-B2A-close"):
            b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session.state == runtime.state == "CLOSED"
    assert b2b_v1.close_h1_guardian_runtime_genesis_v1(session) is runtime._closure


@requires_delegated_parent
def test_close_failure_quarantines_then_retries_without_kill_write(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 4)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    grant_fd = session._fd_slots["grant:SUPERVISOR:CONTROL"]
    kill_fd = session._fd_slots["cgroup:kill"]
    original_close = b2b_v1._OS_CLOSE
    failed = False

    def fail_once(descriptor: int) -> None:
        nonlocal failed
        if descriptor == grant_fd and not failed:
            failed = True
            raise OSError(errno.EIO, "injected ambiguous close")
        original_close(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_OS_CLOSE", fail_once)
        with pytest.raises(RuntimeError, match="close quarantine"):
            b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session.state == "CLEANUP_PENDING"
    assert runtime.state == "RUNNING"
    assert session._fd_slots["cgroup:kill"] == -1
    assert kill_fd not in b2b_v1._MANAGED_FDS
    b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session.state == runtime.state == "CLOSED"


@requires_delegated_parent
@pytest.mark.parametrize("phase", PERSIST_FAULT_PHASES)
def test_pending_revoke_record_resumes_and_close_retry_reaches_closed(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    runtime = _prepare(delegated_parent_fd, 140)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    with monkeypatch.context() as patch:
        patch.setattr(b2b_v1, "_TEST_ONLY_PERSIST_FAULT_PHASE", phase)
        patch.setattr(
            b2b_v1,
            "_TEST_ONLY_PERSIST_FAULT_EVENT",
            "SUPERVISOR_PERMIT_REVOKED",
        )
        with pytest.raises(RuntimeError, match="journal fault"):
            b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
        pending = session._pending_record
        assert pending is not None
        assert pending.event == "SUPERVISOR_PERMIT_REVOKED"
        assert pending.filename in os.listdir(session._fd_slots["journal:directory"])
        assert session.state == runtime.state == "RUNNING"
        # The same fault registration remains active.  Per-transaction replay
        # still progresses because the exact pending interruption is one-shot.
        closure = b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session._pending_record is None
    assert session.state == runtime.state == "CLOSED"
    assert closure.to_document()["actual_process_birth_present"] is False
    records = sorted(private_journal.iterdir())
    assert len(records) == 5
    for path in records:
        document = ids_v1.loads_canonical_json(path.read_bytes())
        assert ids_v1.canonical_json_bytes(document) == path.read_bytes()


@requires_delegated_parent
def test_post_close_signal_reenters_only_after_retire_and_finishes_closed(
    delegated_parent_fd: int,
    private_journal: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _prepare(delegated_parent_fd, 141)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    sent = False
    reentrant_closures = []

    def handler(_signum, _frame) -> None:
        assert session.state == "CLEANUP_PENDING"
        assert runtime.state == "CLEANUP_PENDING"
        assert all(value < 0 for value in session._fd_slots.values())
        assert not any(
            record.owner is session for record in b2b_v1._MANAGED_FDS.values()
        )
        reentrant_closures.append(
            b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
        )
        raise RuntimeError("deferred normal cleanup signal")

    def hook(phase: str, _session, slot: str | None) -> None:
        nonlocal sent
        if (
            phase == "AFTER_CANONICAL_CLOSE_BEFORE_RETIRE"
            and slot == "grant:SUPERVISOR:CONTROL"
            and not sent
        ):
            sent = True
            os.kill(os.getpid(), signal.SIGUSR1)

    previous = signal.signal(signal.SIGUSR1, handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(b2b_v1, "_TEST_ONLY_CLEANUP_BOUNDARY_HOOK", hook)
            with pytest.raises(RuntimeError, match="deferred normal cleanup"):
                b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    finally:
        signal.signal(signal.SIGUSR1, previous)
    assert sent
    assert len(reentrant_closures) == 1
    assert session.state == runtime.state == "CLOSED"
    assert b2b_v1.close_h1_guardian_runtime_genesis_v1(session) is (
        reentrant_closures[0]
    )


@requires_delegated_parent
def test_namespace_same_target_reuse_is_replayed_and_never_closed_on_mismatch(
    delegated_parent_fd: int,
    private_journal: Path,
) -> None:
    runtime = _prepare(delegated_parent_fd, 41)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    slot = "namespace:pid"
    canonical = session._fd_slots[slot]
    witness = session._fd_slots[f"retry-witness:{slot}"]
    source_path = session._context_facts[slot]["proc_path"]
    os.close(canonical)
    replacement = os.open(source_path, os.O_RDONLY | os.O_CLOEXEC)
    if replacement != canonical:
        os.dup2(replacement, canonical, inheritable=False)
        os.close(replacement)
    assert not e5a_v1._same_open_file_description_for_close(canonical, witness)
    with pytest.raises(RuntimeError, match="close quarantine"):
        b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    os.fstat(canonical)  # B2-B did not close the same-target replacement.
    assert session._fd_slots[slot] == canonical
    assert session._fd_slots[f"retry-witness:{slot}"] == witness
    os.close(canonical)
    restored = fcntl.fcntl(witness, fcntl.F_DUPFD_CLOEXEC, canonical)
    assert restored == canonical
    b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session.state == runtime.state == "CLOSED"


@requires_delegated_parent
def test_record_tamper_is_primary_error_but_cannot_block_cleanup(
    delegated_parent_fd: int,
    private_journal: Path,
) -> None:
    runtime = _prepare(delegated_parent_fd, 5)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    target = sorted(private_journal.iterdir())[0]
    target.chmod(0o600)
    with target.open("r+b", buffering=0) as stream:
        stream.write(b"X")
    with pytest.raises(
        b2b_v1.ConstructionK7H1GuardianRuntimeGenesisV1Error,
        match="managed descriptor identity changed|record identity or bytes changed",
    ):
        b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
    assert session.state == runtime.state == "CLOSED"
    assert not b2b_v1._MANAGED_FDS


@requires_delegated_parent
def test_fork_child_is_poisoned_parent_remains_live(
    delegated_parent_fd: int,
    private_journal: Path,
) -> None:
    runtime = _prepare(delegated_parent_fd, 6)
    session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
        runtime,
        preregistration=b2b_v1.preregister_h1_guardian_runtime_genesis_v1(),
        journal_directory=private_journal,
    )
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:
        try:
            os.close(read_fd)
            raw = f"{session.state}|{runtime.state}|{len(b2b_v1._MANAGED_FDS)}".encode()
            os.write(write_fd, raw)
        finally:
            os._exit(0)
    os.close(write_fd)
    raw = os.read(read_fd, 256)
    os.close(read_fd)
    waited, status = os.waitpid(child, 0)
    assert waited == child and os.waitstatus_to_exitcode(status) == 0
    assert raw == b"FORK_POISONED|FORK_POISONED|0"
    assert b2b_v1.verify_h1_guardian_runtime_genesis_v1(session)[
        "runtime_live_state"
    ] == "RUNNING"
    b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
