from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import stat
import subprocess
import threading
import time

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_e3_bound_output_ordinal_continuation_v1 as e4_v1
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp.phase3e_ids import canonical_json_bytes


DELEGATED_PARENT = os.environ.get("ACFQP_E5A_DELEGATED_PARENT_CGROUP")
requires_delegated_parent = pytest.mark.skipif(
    not DELEGATED_PARENT,
    reason="one fresh delegated E5A parent cgroup was not registered",
)
MIB = 1024 * 1024


def _id(label: str) -> str:
    return hashlib.sha256(f"e5a-test:{label}".encode("utf-8")).hexdigest()


def _ids(ordinal: int = 0) -> dict[str, str]:
    return {
        "logical_occurrence_id": _id(f"occurrence:{ordinal}"),
        "route_attempt_id": _id(f"attempt:{ordinal}"),
        "decision_point_id": _id(f"decision:{ordinal}"),
        "build_epoch_id": _id(f"epoch:{ordinal}"),
    }


def _prepare(parent_fd: int, ordinal: int = 0, **overrides):
    arguments = {
        "delegated_parent_cgroup_fd": parent_fd,
        "registered_hard_cap_bytes": 96 * MIB,
        "requested_outer_memory_max_bytes": 64 * MIB,
        **_ids(ordinal),
    }
    arguments.update(overrides)
    return e5a_v1.prepare_h1_route_wide_working_set_cgroup_v1(**arguments)


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


def test_v12_registry_is_additive_disjoint_and_domain_separated() -> None:
    assert len(domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V12) == 5
    assert len(domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12) == 5
    assert domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12.isdisjoint(
        domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
    )
    assert domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12.isdisjoint(
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
    )
    payload = {"schema": "acfqp.e5a.domain_separation.test.v1"}
    ids = {
        domains_v12.extension_content_id_v12(domain, payload)
        for domain in domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12
    }
    assert len(ids) == 5
    with pytest.raises(ValueError, match="absent"):
        domains_v12.extension_content_id_v12(
            domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_PROFILE_V1_DOMAIN,
            payload,
        )


def test_profile_and_topology_freeze_only_prelaunch_authority() -> None:
    profile = e5a_v1.official_h1_route_wide_working_set_cgroup_profile_v1()
    plan = e5a_v1.official_h1_route_wide_working_set_cgroup_topology_plan_v1()
    document = profile.to_document()
    topology = plan.to_document()
    assert document["proposed_contract_version"] == "2.0.59-E-C-E5A"
    assert document["profile_key"] == e5a_v1.PROFILE_KEY
    assert document["readiness"] == "PRELAUNCH_ONLY"
    assert document["upper_kind"] == "PRELAUNCH_ENFORCED_ALLOWED_CAP"
    assert document["current_h1_exclusive_broker_profile_id"] == (
        e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
    )
    assert document["current_h1_e3_bound_output_continuation_profile_id"] == (
        e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id
    )
    assert topology["outer"] == {
        "symbol": "A",
        "memory_max": "DERIVED_ALLOWED_CAP_U",
        "memory_swap_max": 0,
        "pids_max": 3,
        "cgroup_max_depth": 1,
        "cgroup_max_descendants": 3,
        "subtree_controllers": ["memory", "pids"],
    }
    assert [row["pids_max"] for row in topology["leaves"]] == [2, 1, 1]
    assert topology["strict_nonoverlap_max_concurrency"] == 3
    assert topology["worker_business_overlap_forbidden"] is True
    assert topology["pidfd_probe_broker_overlap_forbidden"] is True
    for locked in (
        "route_wide_actual_peak_authority_present",
        "runtime_process_placement_present",
        "e5b_integrated_launch_present",
        "e3_child_peak_relabelled",
        "postrun_peak_used_for_upper",
        "current_access_authority_present",
        "formal_v7_authority_present",
        "fq11_counter_completeness_present",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_actual_projection_proof_issued",
        "official_execution_allowed",
    ):
        assert document[locked] is False
        assert topology[locked] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_fd_publication_mask_excludes_unsafe_synchronous_signals() -> None:
    safe = e5a_v1._SAFE_FD_PUBLICATION_SIGNALS
    assert signal.SIGALRM in safe
    assert safe <= frozenset(signal.valid_signals())
    assert signal.SIGKILL not in safe
    assert signal.SIGSTOP not in safe
    for name in ("SIGBUS", "SIGFPE", "SIGILL", "SIGSEGV", "SIGSYS", "SIGTRAP"):
        if hasattr(signal, name):
            assert getattr(signal, name) not in safe


def test_issuer_owned_objects_cannot_be_caller_minted() -> None:
    with pytest.raises(e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error):
        e5a_v1.H1RouteWideWorkingSetCgroupProfileV1(
            None,
            canonical_json_bytes({"schema": "caller"}),
        )
    with pytest.raises(e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error):
        e5a_v1.H1RouteWideWorkingSetCgroupTopologyPlanV1(
            None,
            canonical_json_bytes({"schema": "caller"}),
        )
    with pytest.raises(e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error):
        e5a_v1.H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1(
            None,
            canonical_json_bytes({"schema": "caller"}),
        )
    with pytest.raises(e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error):
        e5a_v1.H1RouteWideWorkingSetCgroupCleanupClosureV1(
            None,
            canonical_json_bytes({"schema": "caller"}),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("logical_occurrence_id", "a" * 63),
        ("route_attempt_id", "A" * 64),
        ("decision_point_id", "g" * 64),
        ("build_epoch_id", None),
    ],
)
def test_identity_inputs_are_exact(field: str, value, tmp_path: Path) -> None:
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="content ID",
        ):
            _prepare(descriptor, **{field: value})
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(descriptor)


@pytest.mark.parametrize("value", [0, -1, True, "max", None, 1 << 63])
def test_infinite_noninteger_or_out_of_range_caps_fail_before_cgroup_use(
    value,
    tmp_path: Path,
) -> None:
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="finite positive byte cap",
        ):
            _prepare(descriptor, registered_hard_cap_bytes=value)
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="finite positive byte cap",
        ):
            _prepare(descriptor, requested_outer_memory_max_bytes=value)
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(descriptor)


def test_missing_fd_and_ordinary_directory_never_form_positive_fixture(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
        match="delegated parent cgroup FD",
    ):
        _prepare(-1)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="not a cgroup-v2",
        ):
            _prepare(descriptor)
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(descriptor)


def test_post_open_fork_audit_exception_escapes_without_unregistered_fd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    owner = e5a_v1._ConstructionFDOwnerV1()
    with e5a_v1._FD_OWNERSHIP_LOCK:
        e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
    observed = {"opened": -1}

    def fork_during_identity_upgrade(descriptor: int):
        observed["opened"] = descriptor
        os.fork()  # must raise before a child or syscall exists
        pytest.fail("post-open fork audit refusal did not escape")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                e5a_v1,
                "_registry_fd_identity",
                fork_during_identity_upgrade,
            )
            with pytest.raises(
                e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
                match="canonical FD publication",
            ):
                e5a_v1._open_owned_path_fd(
                    owner,
                    e5a_v1._PARENT_FD_SLOT,
                    "/dev/null",
                    os.O_RDONLY | os.O_CLOEXEC,
                )
        descriptor = observed["opened"]
        assert descriptor >= 0
        assert e5a_v1._fork_forbidden_depth() == 0
        assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == -1
        assert descriptor not in e5a_v1._OWNED_FDS
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF
    finally:
        with e5a_v1._FD_OWNERSHIP_LOCK:
            e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)
    assert e5a_v1._fork_forbidden_depth() == 0
    assert not any(record.owner is owner for record in e5a_v1._OWNED_FDS.values())


def test_identity_failure_with_live_close_stays_registered_and_fork_closable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    owner = e5a_v1._ConstructionFDOwnerV1()
    with e5a_v1._FD_OWNERSHIP_LOCK:
        e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
    original_close = e5a_v1._OS_CLOSE
    observed = {"opened": -1}

    def fail_identity(descriptor: int):
        observed["opened"] = descriptor
        raise RuntimeError("injected identity upgrade failure")

    def refuse_provisional_close(descriptor: int) -> None:
        if descriptor == observed["opened"]:
            raise OSError(errno.EIO, "injected provisional close failure")
        original_close(descriptor)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1, "_registry_fd_identity", fail_identity)
            patch.setattr(e5a_v1.os, "close", refuse_provisional_close)
            with pytest.raises(RuntimeError, match="identity upgrade failure"):
                e5a_v1._open_owned_path_fd(
                    owner,
                    e5a_v1._PARENT_FD_SLOT,
                    "/dev/null",
                    os.O_RDONLY | os.O_CLOEXEC,
                )
        descriptor = observed["opened"]
        assert descriptor >= 0 and os.fstat(descriptor)
        assert e5a_v1._fork_forbidden_depth() == 0
        assert owner._state == "OPEN_QUARANTINED"
        assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == descriptor
        record = e5a_v1._OWNED_FDS[descriptor]
        assert record.owner is owner
        assert record.slot == e5a_v1._PARENT_FD_SLOT
        assert record.identity is None
        retry_slot = e5a_v1._retry_witness_fd_slot(e5a_v1._PARENT_FD_SLOT)
        retry_witness = owner._fd_slots[retry_slot]
        assert retry_witness >= 0
        retry_record = e5a_v1._OWNED_FDS[retry_witness]
        assert retry_record.owner is owner
        assert retry_record.slot == retry_slot
        assert retry_record.identity is None
        assert e5a_v1._retry_witness_fd_slot(retry_slot) not in owner._fd_slots
        assert e5a_v1._same_open_file_description_for_close(
            descriptor, retry_witness
        )

        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        child = os.fork()
        if child == 0:  # pragma: no cover - asserted by parent packet
            original_close(read_fd)
            ok = owner._state == "FORK_POISONED"
            ok = ok and not e5a_v1._OWNED_FDS
            try:
                os.fstat(descriptor)
            except OSError as error:
                ok = ok and error.errno == errno.EBADF
            else:
                ok = False
            try:
                os.fstat(retry_witness)
            except OSError as error:
                ok = ok and error.errno == errno.EBADF
            else:
                ok = False
            os.write(write_fd, b"1" if ok else b"0")
            original_close(write_fd)
            os._exit(0)
        original_close(write_fd)
        try:
            assert os.read(read_fd, 1) == b"1"
            waited, status = os.waitpid(child, 0)
            assert waited == child
            assert os.waitstatus_to_exitcode(status) == 0
        finally:
            original_close(read_fd)
        assert os.fstat(descriptor)
        assert (
            e5a_v1._close_owned_fd_slot(owner, e5a_v1._PARENT_FD_SLOT)
            is None
        )
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF
    finally:
        with e5a_v1._FD_OWNERSHIP_LOCK:
            e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)
    assert not any(record.owner is owner for record in e5a_v1._OWNED_FDS.values())


def test_provisional_close_reuse_does_not_close_or_register_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = e5a_v1._ConstructionFDOwnerV1()
    with e5a_v1._FD_OWNERSHIP_LOCK:
        e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
    original_close = e5a_v1._OS_CLOSE
    observed = {"canonical": -1, "witness": -1, "replacement": -1}

    def fail_identity(descriptor: int):
        observed["canonical"] = descriptor
        raise RuntimeError("injected provisional identity failure")

    def close_reuse_then_raise(descriptor: int) -> None:
        target = observed["canonical"]
        if descriptor != target or observed["replacement"] >= 0:
            original_close(descriptor)
            return
        witness_slot = e5a_v1._retry_witness_fd_slot(
            e5a_v1._PARENT_FD_SLOT
        )
        witness = owner._fd_slots[witness_slot]
        assert witness >= 0
        assert e5a_v1._OWNED_FDS[witness].identity is None
        assert e5a_v1._same_open_file_description_for_close(target, witness)
        observed["witness"] = witness
        original_close(target)
        source = os.open("/dev/zero", os.O_RDONLY | os.O_CLOEXEC)
        if source != target:
            os.dup2(source, target, inheritable=False)
            original_close(source)
        observed["replacement"] = target
        raise OSError(errno.EIO, "injected provisional close reuse")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1, "_registry_fd_identity", fail_identity)
            patch.setattr(e5a_v1.os, "close", close_reuse_then_raise)
            with pytest.raises(
                RuntimeError, match="provisional identity failure"
            ):
                e5a_v1._open_owned_path_fd(
                    owner,
                    e5a_v1._PARENT_FD_SLOT,
                    "/dev/null",
                    os.O_RDONLY | os.O_CLOEXEC,
                )
        canonical = observed["canonical"]
        witness = observed["witness"]
        assert canonical >= 0
        assert witness >= 0
        assert observed["replacement"] == canonical
        assert owner._state == "OPEN_QUARANTINED"
        assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == -1
        assert owner._fd_slots[
            e5a_v1._retry_witness_fd_slot(e5a_v1._PARENT_FD_SLOT)
        ] == -1
        assert canonical not in e5a_v1._OWNED_FDS
        assert witness not in e5a_v1._OWNED_FDS
        replacement = os.fstat(canonical)
        assert stat.S_ISCHR(replacement.st_mode)
        assert replacement.st_rdev == os.stat("/dev/zero").st_rdev
        with pytest.raises(OSError) as closed_witness:
            os.fstat(witness)
        assert closed_witness.value.errno == errno.EBADF
        assert not any(
            record.owner is owner for record in e5a_v1._OWNED_FDS.values()
        )
    finally:
        replacement = observed["replacement"]
        if replacement >= 0:
            original_close(replacement)
        with e5a_v1._FD_OWNERSHIP_LOCK:
            for slot in e5a_v1._CANONICAL_FD_SLOTS:
                e5a_v1._close_owned_fd_slot(owner, slot)
            e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)


def test_retry_witness_identity_failure_never_mints_nested_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = e5a_v1._ConstructionFDOwnerV1()
    with e5a_v1._FD_OWNERSHIP_LOCK:
        e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
    source = e5a_v1._open_owned_path_fd(
        owner,
        e5a_v1._PARENT_FD_SLOT,
        "/dev/null",
        os.O_RDONLY | os.O_CLOEXEC,
    )
    witness_slot = e5a_v1._retry_witness_fd_slot(e5a_v1._PARENT_FD_SLOT)

    def fail_witness_identity(_descriptor: int):
        raise RuntimeError("injected retry-witness identity failure")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1, "_registry_fd_identity", fail_witness_identity)
            with pytest.raises(RuntimeError, match="retry-witness identity failure"):
                e5a_v1._duplicate_owned_fd(owner, witness_slot, source)
        assert owner._fd_slots[witness_slot] == -1
        assert e5a_v1._retry_witness_fd_slot(witness_slot) not in owner._fd_slots
        assert all(
            record.owner is not owner or descriptor == source
            for descriptor, record in e5a_v1._OWNED_FDS.items()
        )
    finally:
        e5a_v1._close_owned_fd_slot(owner, e5a_v1._PARENT_FD_SLOT)
        with e5a_v1._FD_OWNERSHIP_LOCK:
            e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)


@pytest.mark.parametrize("operation", ["OPEN", "DUP"])
def test_pending_sigalrm_from_syscall_return_waits_for_provisional_publication(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if (
        not hasattr(os, "fork")
        or not hasattr(signal, "pthread_sigmask")
        or not hasattr(signal, "pthread_kill")
    ):
        pytest.skip("fork, pthread_sigmask, or pthread_kill is unavailable")
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    helper_entry_mask = frozenset(signal.pthread_sigmask(signal.SIG_BLOCK, set()))
    original_open = e5a_v1._OS_OPEN
    original_fcntl = e5a_v1._FCNTL_FCNTL
    original_publish = e5a_v1._publish_provisional_fd_unlocked
    opened: list[int] = []
    handled = {"count": 0}
    phase = {
        "in_syscall_wrapper": False,
        "signal_queued": False,
        "published": False,
    }

    def alarm_handler(_signum: int, _frame) -> None:
        assert phase["signal_queued"] is True
        assert phase["in_syscall_wrapper"] is False
        assert phase["published"] is True
        handled["count"] += 1
        os.fork()  # must be rejected by the active publication guard
        pytest.fail("SIGALRM handler created a child during FD publication")

    def queue_before_syscall_wrapper_return(descriptor: int) -> int:
        opened.append(descriptor)
        phase["in_syscall_wrapper"] = True
        phase["signal_queued"] = True
        count_before = handled["count"]
        signal.pthread_kill(threading.get_ident(), signal.SIGALRM)
        assert handled["count"] == count_before
        phase["in_syscall_wrapper"] = False
        return descriptor

    def open_then_queue(*args, **kwargs) -> int:
        return queue_before_syscall_wrapper_return(original_open(*args, **kwargs))

    def dup_then_queue(*args, **kwargs) -> int:
        duplicate = int(original_fcntl(*args, **kwargs))
        if phase["signal_queued"]:
            return duplicate
        return queue_before_syscall_wrapper_return(duplicate)

    def track_provisional_publication(owner, slot: str, descriptor: int) -> None:
        assert phase["signal_queued"] is True
        original_publish(owner, slot, descriptor)
        phase["published"] = True

    source_fd = -1
    signal.signal(signal.SIGALRM, alarm_handler)
    try:
        if operation == "DUP":
            source_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        with monkeypatch.context() as patch:
            patch.setattr(
                e5a_v1,
                "_publish_provisional_fd_unlocked",
                track_provisional_publication,
            )
            patch.setattr(
                e5a_v1,
                "_OS_OPEN" if operation == "OPEN" else "_FCNTL_FCNTL",
                open_then_queue if operation == "OPEN" else dup_then_queue,
            )
            for expected_count in range(1, 17):
                phase.update(
                    in_syscall_wrapper=False,
                    signal_queued=False,
                    published=False,
                )
                owner = e5a_v1._ConstructionFDOwnerV1()
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
                try:
                    try:
                        if operation == "OPEN":
                            e5a_v1._open_owned_path_fd(
                                owner,
                                e5a_v1._PARENT_FD_SLOT,
                                "/dev/null",
                                os.O_RDONLY | os.O_CLOEXEC,
                            )
                        else:
                            e5a_v1._duplicate_owned_fd(
                                owner,
                                e5a_v1._PARENT_FD_SLOT,
                                source_fd,
                            )
                    except e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error as error:
                        assert "canonical FD publication" in str(error)
                    else:
                        pytest.fail(
                            "pending SIGALRM was not delivered during restore: "
                            f"iteration={expected_count}, handled={handled['count']}, "
                            f"pending={signal.sigpending()}, phase={phase}, "
                            "mask="
                            f"{signal.pthread_sigmask(signal.SIG_BLOCK, set())}"
                        )
                    descriptor = opened[-1]
                    assert handled["count"] == expected_count
                    assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == -1
                    assert descriptor not in e5a_v1._OWNED_FDS
                    with pytest.raises(OSError) as closed:
                        os.fstat(descriptor)
                    assert closed.value.errno == errno.EBADF
                    assert e5a_v1._fork_forbidden_depth() == 0
                    assert frozenset(
                        signal.pthread_sigmask(signal.SIG_BLOCK, set())
                    ) == helper_entry_mask
                finally:
                    with e5a_v1._FD_OWNERSHIP_LOCK:
                        e5a_v1._close_owned_fd_slot(
                            owner, e5a_v1._PARENT_FD_SLOT
                        )
                        e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)
        assert handled["count"] == 16
        assert len(opened) == 16
    finally:
        signal.signal(signal.SIGALRM, previous_handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if source_fd >= 0:
            os.close(source_fd)
    assert not e5a_v1._OWNED_FDS


@pytest.mark.parametrize("operation", ["OPEN", "DUP"])
def test_pending_sigalrm_after_provisional_publication_is_cleaned(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if (
        not hasattr(os, "fork")
        or not hasattr(signal, "pthread_sigmask")
        or not hasattr(signal, "pthread_kill")
    ):
        pytest.skip("fork, pthread_sigmask, or pthread_kill is unavailable")
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    helper_entry_mask = frozenset(signal.pthread_sigmask(signal.SIG_BLOCK, set()))
    original_publish = e5a_v1._publish_provisional_fd_unlocked
    opened: list[int] = []
    handled = {"count": 0}

    def alarm_handler(_signum: int, _frame) -> None:
        handled["count"] += 1
        os.fork()  # must be rejected by the active publication guard
        pytest.fail("SIGALRM handler created a child during FD publication")

    def publish_then_queue_alarm(owner, slot: str, descriptor: int) -> None:
        original_publish(owner, slot, descriptor)
        if slot != e5a_v1._PARENT_FD_SLOT:
            return
        opened.append(descriptor)
        signal.pthread_kill(threading.get_ident(), signal.SIGALRM)

    source_fd = -1
    signal.signal(signal.SIGALRM, alarm_handler)
    try:
        if operation == "DUP":
            source_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        with monkeypatch.context() as patch:
            patch.setattr(
                e5a_v1,
                "_publish_provisional_fd_unlocked",
                publish_then_queue_alarm,
            )
            for _ in range(16):
                owner = e5a_v1._ConstructionFDOwnerV1()
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
                try:
                    with pytest.raises(
                        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
                        match="canonical FD publication",
                    ):
                        if operation == "OPEN":
                            e5a_v1._open_owned_path_fd(
                                owner,
                                e5a_v1._PARENT_FD_SLOT,
                                "/dev/null",
                                os.O_RDONLY | os.O_CLOEXEC,
                            )
                        else:
                            e5a_v1._duplicate_owned_fd(
                                owner,
                                e5a_v1._PARENT_FD_SLOT,
                                source_fd,
                            )
                    descriptor = opened[-1]
                    assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == -1
                    assert descriptor not in e5a_v1._OWNED_FDS
                    with pytest.raises(OSError) as closed:
                        os.fstat(descriptor)
                    assert closed.value.errno == errno.EBADF
                    assert e5a_v1._fork_forbidden_depth() == 0
                    assert frozenset(
                        signal.pthread_sigmask(signal.SIG_BLOCK, set())
                    ) == helper_entry_mask
                finally:
                    with e5a_v1._FD_OWNERSHIP_LOCK:
                        e5a_v1._close_owned_fd_slot(
                            owner, e5a_v1._PARENT_FD_SLOT
                        )
                        e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)
        assert handled["count"] == 16
        assert len(opened) == 16
    finally:
        signal.signal(signal.SIGALRM, previous_handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if source_fd >= 0:
            os.close(source_fd)
    assert not e5a_v1._OWNED_FDS


def test_open_syscall_failure_restores_exact_signal_mask_and_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    helper_entry_mask = frozenset(signal.pthread_sigmask(signal.SIG_BLOCK, set()))
    owner = e5a_v1._ConstructionFDOwnerV1()

    def fail_open(*_args, **_kwargs):
        raise OSError(errno.EMFILE, "injected open exhaustion")

    with e5a_v1._FD_OWNERSHIP_LOCK:
        e5a_v1._CONSTRUCTION_FD_OWNERS[id(owner)] = owner
    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1, "_OS_OPEN", fail_open)
            with pytest.raises(OSError) as failed:
                e5a_v1._open_owned_path_fd(
                    owner,
                    e5a_v1._PARENT_FD_SLOT,
                    "/dev/null",
                    os.O_RDONLY | os.O_CLOEXEC,
                )
        assert failed.value.errno == errno.EMFILE
        assert owner._fd_slots[e5a_v1._PARENT_FD_SLOT] == -1
        assert not any(record.owner is owner for record in e5a_v1._OWNED_FDS.values())
        assert e5a_v1._fork_forbidden_depth() == 0
        assert frozenset(
            signal.pthread_sigmask(signal.SIG_BLOCK, set())
        ) == helper_entry_mask
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        with e5a_v1._FD_OWNERSHIP_LOCK:
            e5a_v1._CONSTRUCTION_FD_OWNERS.pop(id(owner), None)


@requires_delegated_parent
def test_real_delegated_prelaunch_envelope_and_cleanup(
    delegated_parent_fd: int,
) -> None:
    ids = _ids(1)
    lease = _prepare(delegated_parent_fd, 1)
    assert all(
        lease._fd_slots[e5a_v1._retry_witness_fd_slot(slot)] == -1
        for slot in e5a_v1._CANONICAL_FD_SLOTS
    )
    outer_name = lease.hierarchy_document()["outer"]["name"]
    try:
        envelope = e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(
            lease
        )
        hierarchy = lease.hierarchy_document()
        assert lease.readiness == "PRELAUNCH_ONLY"
        assert lease.state == "ACTIVE"
        assert hierarchy["logical_occurrence_id"] == ids["logical_occurrence_id"]
        assert hierarchy["route_attempt_id"] == ids["route_attempt_id"]
        assert hierarchy["decision_point_id"] == ids["decision_point_id"]
        assert hierarchy["BuildEpoch_id"] == ids["build_epoch_id"]
        assert hierarchy["registered_hard_cap_bytes"] == 96 * MIB
        assert hierarchy["requested_outer_memory_max_bytes"] == 64 * MIB
        assert hierarchy["enforced_outer_memory_max_bytes"] == 64 * MIB
        assert hierarchy["outer"]["memory_max_bytes"] == 64 * MIB
        assert hierarchy["outer"]["memory_swap_max_bytes"] == 0
        assert hierarchy["outer"]["pids_max"] == 3
        assert hierarchy["delegated_parent"]["memory_current_scope"] == (
            "DELEGATION_PREREQUISITE_NOT_ROUTE_OPERAND"
        )
        assert (
            hierarchy["delegated_parent"]["memory_current_value_content_bound"]
            is False
        )
        assert type(hierarchy["outer"]["memory_current_bytes_at_admission"]) is int
        assert hierarchy["outer"]["memory_current_bytes_at_admission"] >= 0
        assert hierarchy["outer"]["memory_current_observation_ordinal"] == 1
        assert [row["role"] for row in hierarchy["leaves"]] == list(
            e5a_v1.ROLE_ORDER
        )
        assert [row["pids_max"] for row in hierarchy["leaves"]] == [2, 1, 1]
        assert [
            row["memory_current_observation_ordinal"]
            for row in hierarchy["leaves"]
        ] == [2, 3, 4]
        assert all(
            type(row["memory_current_bytes_at_admission"]) is int
            and row["memory_current_bytes_at_admission"] >= 0
            for row in hierarchy["leaves"]
        )
        assert len(
            {
                (hierarchy["outer"]["identity"]["device"], hierarchy["outer"]["identity"]["inode"]),
                *(
                    (row["identity"]["device"], row["identity"]["inode"])
                    for row in hierarchy["leaves"]
                ),
            }
        ) == 4
        assert envelope["upper_kind"] == "PRELAUNCH_ENFORCED_ALLOWED_CAP"
        assert envelope["comparison_axis"] == "peak_working_bytes"
        assert envelope["allowed_cap_bytes"] == min(
            envelope["registered_hard_cap_bytes"], envelope["outer_memory_max_bytes"]
        )
        assert envelope["postrun_peak_used_for_upper"] is False
        assert envelope["e3_child_peak_relabelled"] is False
        assert envelope["runtime_process_placement_present"] is False
        assert envelope["actual_peak_present"] is False
        assert envelope["current_h1_exclusive_broker_profile_id"] == (
            e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
        )
        assert envelope["current_h1_e3_bound_output_continuation_profile_id"] == (
            e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id
        )
        assert e5a_v1._same_open_file_description(
            lease._memory_peak_fd, lease._memory_peak_witness_fd
        )
        assert hierarchy["outer_memory_peak"]["baseline_peak_bytes"] >= (
            hierarchy["outer"]["memory_current_bytes_at_admission"]
        )
        assert (
            hierarchy["outer_memory_peak"][
                "baseline_not_below_recorded_outer_memory_current"
            ]
            is True
        )
        assert (
            hierarchy[
                "admission_memory_current_values_are_frozen_timepoint_observations"
            ]
            is True
        )
        assert hierarchy["later_memory_current_values_may_differ"] is True
        for descriptor in (
            lease._parent_fd,
            lease._outer_fd,
            lease._memory_peak_fd,
            lease._memory_peak_witness_fd,
            *lease._role_fds.values(),
        ):
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert e5a_v1._read_control(lease._outer_fd, "cgroup.procs").strip() == b""
        assert all(
            e5a_v1._read_control(fd, "cgroup.procs").strip() == b""
            for fd in lease._role_fds.values()
        )
    finally:
        closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    document = closure.to_document()
    assert lease.state == "CLOSED"
    assert all(
        lease._fd_slots[slot] == -1 for slot in e5a_v1._ALL_OWNED_FD_SLOTS
    )
    assert document["identity_bound_children_removed"] is True
    assert document["identity_bound_outer_removed"] is True
    assert document["memory_peak_ofd_retained_until_outer_removal"] is True
    assert document["actual_peak_issued"] is False
    assert e5a_v1._child_directories(delegated_parent_fd) == ()
    with pytest.raises(FileNotFoundError):
        os.stat(outer_name, dir_fd=delegated_parent_fd)
    assert (
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease).closure_id
        == closure.closure_id
    )


@requires_delegated_parent
@pytest.mark.parametrize(
    "fault",
    [
        e5a_v1.H1RouteWideWorkingSetCgroupFaultV1.AFTER_OUTER_CREATION,
        e5a_v1.H1RouteWideWorkingSetCgroupFaultV1.AFTER_FIRST_LEAF,
        e5a_v1.H1RouteWideWorkingSetCgroupFaultV1.AFTER_COMPLETE_HIERARCHY,
    ],
)
def test_construction_faults_roll_back_fresh_hierarchy(
    delegated_parent_fd: int,
    fault: e5a_v1.H1RouteWideWorkingSetCgroupFaultV1,
) -> None:
    with pytest.raises(RuntimeError, match="injected E5A failure"):
        _prepare(delegated_parent_fd, 2, fault=fault)
    assert e5a_v1._child_directories(delegated_parent_fd) == ()


@requires_delegated_parent
def test_changed_or_infinite_outer_cap_invalidates_but_does_not_block_cleanup(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 3)
    try:
        e5a_v1._write_control(lease._outer_fd, "memory.max", "max")
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="memory.max changed or became infinite",
        ):
            e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
    finally:
        closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert closure.to_document()["identity_bound_outer_removed"] is True


@requires_delegated_parent
def test_old_two_leaf_transplant_and_missing_subdelegation_fail(
    delegated_parent_fd: int,
) -> None:
    legacy_name = f"legacy-e3-{os.urandom(8).hex()}"
    undelegated_name = f"undelegated-{os.urandom(8).hex()}"
    os.mkdir(legacy_name, dir_fd=delegated_parent_fd)
    legacy_fd = e5a_v1._open_child_directory(delegated_parent_fd, legacy_name)
    try:
        e5a_v1._write_control(legacy_fd, "cgroup.subtree_control", "+memory +pids")
        for name in ("worker", "business"):
            os.mkdir(name, dir_fd=legacy_fd)
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="child-free baseline",
        ):
            _prepare(legacy_fd, 4)
    finally:
        for name in ("business", "worker"):
            try:
                os.rmdir(name, dir_fd=legacy_fd)
            except FileNotFoundError:
                pass
        os.close(legacy_fd)
        os.rmdir(legacy_name, dir_fd=delegated_parent_fd)

    os.mkdir(undelegated_name, dir_fd=delegated_parent_fd)
    undelegated_fd = e5a_v1._open_child_directory(
        delegated_parent_fd, undelegated_name
    )
    try:
        assert e5a_v1._tokens_control(
            undelegated_fd, "cgroup.subtree_control"
        ) == frozenset()
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match=r"lacks enabled memory\+pids authority",
        ):
            _prepare(undelegated_fd, 5)
    finally:
        os.close(undelegated_fd)
        os.rmdir(undelegated_name, dir_fd=delegated_parent_fd)


@requires_delegated_parent
def test_live_envelope_and_hierarchy_tampering_fail_closed(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 6)
    original_hierarchy = lease.hierarchy_document()
    original_envelope = lease._envelope
    try:
        lease._hierarchy_document["outer"][
            "memory_current_bytes_at_admission"
        ] += 1
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="content ID changed",
        ):
            e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
        lease._hierarchy_document = copy.deepcopy(original_hierarchy)
        lease._hierarchy_document["readiness"] = "RUNTIME"
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="content ID changed",
        ):
            e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
        lease._hierarchy_document = original_hierarchy
        lease._envelope = object()
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="changed type",
        ):
            e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
    finally:
        lease._hierarchy_document = copy.deepcopy(original_hierarchy)
        lease._envelope = original_envelope
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)


@requires_delegated_parent
def test_atfork_child_poison_closes_canonical_fds_without_harming_parent(
    delegated_parent_fd: int,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    lease = _prepare(delegated_parent_fd, 7)
    retained = (
        lease._parent_fd,
        lease._outer_fd,
        lease._memory_peak_fd,
        lease._memory_peak_witness_fd,
        *lease._role_fds.values(),
    )
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted by parent packet
        os.close(read_fd)
        ok = lease.state == "FORK_POISONED"
        for descriptor in retained:
            try:
                os.fstat(descriptor)
            except OSError as error:
                ok = ok and error.errno == errno.EBADF
            else:
                ok = False
        try:
            e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
        except e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error:
            pass
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
        assert all(os.fstat(descriptor) for descriptor in retained)
        e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
    finally:
        os.close(read_fd)
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)


@requires_delegated_parent
def test_atfork_during_construction_closes_registered_prelease_fds(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    original_configure_outer = e5a_v1._configure_outer
    observed = {"ran": False}

    def fork_before_configure(outer_fd: int, allowed_cap_bytes: int) -> None:
        if not observed["ran"]:
            observed["ran"] = True
            with e5a_v1._FD_OWNERSHIP_LOCK:
                snapshot = tuple(e5a_v1._OWNED_FDS)
                assert len(snapshot) == 2
                assert len(e5a_v1._CONSTRUCTION_FD_OWNERS) == 1
            read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
            child = os.fork()
            if child == 0:  # pragma: no cover - asserted by parent packet
                e5a_v1._OS_CLOSE(read_fd)
                ok = not e5a_v1._OWNED_FDS
                ok = ok and not e5a_v1._CONSTRUCTION_FD_OWNERS
                for descriptor in snapshot:
                    try:
                        os.fstat(descriptor)
                    except OSError as error:
                        ok = ok and error.errno == errno.EBADF
                    else:
                        ok = False
                os.write(write_fd, b"1" if ok else b"0")
                e5a_v1._OS_CLOSE(write_fd)
                os._exit(0)
            e5a_v1._OS_CLOSE(write_fd)
            try:
                assert os.read(read_fd, 1) == b"1"
                waited, status = os.waitpid(child, 0)
                assert waited == child
                assert os.waitstatus_to_exitcode(status) == 0
            finally:
                e5a_v1._OS_CLOSE(read_fd)
        original_configure_outer(outer_fd, allowed_cap_bytes)

    monkeypatch.setattr(e5a_v1, "_configure_outer", fork_before_configure)
    lease = _prepare(delegated_parent_fd, 11)
    assert observed["ran"] is True
    assert lease.state == "ACTIVE"
    e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)


@requires_delegated_parent
def test_cleanup_rejects_same_inode_distinct_peak_ofd_before_outer_rmdir(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 12)
    frozen_identity = lease.hierarchy_document()["outer_memory_peak"]["identity"]
    assert (
        e5a_v1._close_owned_fd_slot(lease, e5a_v1._PEAK_WITNESS_FD_SLOT)
        is None
    )
    e5a_v1._open_owned_path_fd(
        lease,
        e5a_v1._PEAK_WITNESS_FD_SLOT,
        "memory.peak",
        os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=lease._outer_fd,
    )
    assert e5a_v1._fd_identity(
        lease._memory_peak_witness_fd, directory=False
    ) == frozen_identity
    assert not e5a_v1._same_open_file_description(
        lease._memory_peak_fd, lease._memory_peak_witness_fd
    )
    with pytest.raises(
        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
        match="memory.peak OFD changed",
    ):
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert lease.state == "CLEANUP_PENDING"
    assert lease._outer_removed is False
    os.stat(lease._outer_name, dir_fd=lease._parent_fd)
    assert (
        e5a_v1._close_owned_fd_slot(lease, e5a_v1._PEAK_WITNESS_FD_SLOT)
        is None
    )
    e5a_v1._duplicate_owned_fd(
        lease,
        e5a_v1._PEAK_WITNESS_FD_SLOT,
        lease._memory_peak_fd,
    )
    closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert closure.to_document()["cleanup_attempt_count"] == 2


@requires_delegated_parent
def test_post_close_raise_and_fork_window_are_definitive_and_safe(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    lease = _prepare(delegated_parent_fd, 13)
    target = lease._parent_fd
    original_close = e5a_v1._OS_CLOSE
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    observed = {"ran": False}

    def close_then_raise(descriptor: int) -> None:
        if descriptor != target or observed["ran"]:
            original_close(descriptor)
            return
        observed["ran"] = True
        witness = lease._fd_slots[
            e5a_v1._retry_witness_fd_slot(e5a_v1._PARENT_FD_SLOT)
        ]
        assert witness >= 0
        original_close(descriptor)
        child = os.fork()
        if child == 0:  # pragma: no cover - asserted by parent packet
            original_close(read_fd)
            ok = lease.state == "FORK_POISONED"
            ok = ok and not e5a_v1._OWNED_FDS
            for inherited in (target, witness):
                try:
                    os.fstat(inherited)
                except OSError as error:
                    ok = ok and error.errno == errno.EBADF
                else:
                    ok = False
            os.write(write_fd, b"1" if ok else b"0")
            original_close(write_fd)
            os._exit(0)
        waited, status = os.waitpid(child, 0)
        assert waited == child
        assert os.waitstatus_to_exitcode(status) == 0
        raise OSError(errno.EIO, "injected post-close raise")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1.os, "close", close_then_raise)
            closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(
                lease
            )
        original_close(write_fd)
        assert os.read(read_fd, 1) == b"1"
    finally:
        original_close(read_fd)
    assert observed["ran"] is True
    assert closure.to_document()["cleanup_attempt_count"] == 1
    assert lease.state == "CLOSED"
    assert lease._closure is closure
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert id(lease) not in e5a_v1._QUARANTINED_LEASES


@requires_delegated_parent
def test_persistent_live_close_enters_quarantine_and_retries_without_closure(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = _prepare(delegated_parent_fd, 14)
    target = lease._memory_peak_fd
    original_identity = e5a_v1._registry_fd_identity(target)
    original_close = e5a_v1._OS_CLOSE

    def refuse_live_target(descriptor: int) -> None:
        if descriptor == target:
            raise OSError(errno.EIO, "injected persistent live close")
        original_close(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(e5a_v1.os, "close", refuse_live_target)
        with pytest.raises(RuntimeError, match="retained FD close remains live"):
            e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    witness_slot = e5a_v1._retry_witness_fd_slot(e5a_v1._PEAK_FD_SLOT)
    witness = lease._fd_slots[witness_slot]
    assert lease.state == "CLEANUP_PENDING"
    assert lease._outer_removed is True
    assert lease._closure is None
    assert id(lease) not in e5a_v1._LIVE_LEASES
    assert e5a_v1._QUARANTINED_LEASES[id(lease)] is lease
    assert e5a_v1._registry_fd_identity(target) == original_identity
    assert witness >= 0
    assert e5a_v1._same_open_file_description_for_close(target, witness)
    assert e5a_v1._OWNED_FDS[target].owner is lease
    assert e5a_v1._OWNED_FDS[witness].owner is lease
    closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert closure.to_document()["cleanup_attempt_count"] == 2
    assert lease.state == "CLOSED"
    assert lease._closure is closure
    assert not any(record.owner is lease for record in e5a_v1._OWNED_FDS.values())
    assert id(lease) not in e5a_v1._QUARANTINED_LEASES


@requires_delegated_parent
def test_same_inode_new_ofd_reuse_after_close_error_is_never_closed(
    delegated_parent_fd: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DELEGATED_PARENT is not None
    lease = _prepare(delegated_parent_fd, 15)
    target = lease._parent_fd
    frozen = e5a_v1._registry_fd_identity(target)
    original_close = e5a_v1._OS_CLOSE
    observed = {"ran": False}

    def close_reopen_same_inode_then_raise(descriptor: int) -> None:
        if descriptor != target or observed["ran"]:
            original_close(descriptor)
            return
        observed["ran"] = True
        original_close(descriptor)
        source = os.open(
            Path(DELEGATED_PARENT),
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        if source != target:
            os.dup2(source, target, inheritable=False)
            original_close(source)
        assert e5a_v1._registry_fd_identity(target) == frozen
        raise OSError(errno.EIO, "injected same-inode new-OFD reuse")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(e5a_v1.os, "close", close_reopen_same_inode_then_raise)
            closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(
                lease
            )
        assert observed["ran"] is True
        assert lease.state == "CLOSED"
        assert closure.to_document()["cleanup_attempt_count"] == 1
        assert e5a_v1._registry_fd_identity(target) == frozen
        assert target not in e5a_v1._OWNED_FDS
    finally:
        original_close(target)


@requires_delegated_parent
def test_cleanup_retry_replays_removed_role_before_dead_cgroup_fd(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 9)
    with pytest.raises(
        BlockingIOError,
        match="transient E5A second-child rmdir failure",
    ):
        e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(
            lease,
            fault=(
                e5a_v1.H1RouteWideWorkingSetCgroupFaultV1.CLEANUP_BEFORE_SECOND_CHILD_RMDIR
            ),
        )
    assert lease.state == "CLEANUP_PENDING"
    assert lease._removed_roles == {"BUSINESS"}
    assert e5a_v1._child_directories(lease._outer_fd) == ("CONTROL", "WORKER")
    # The retained BUSINESS directory FD now names a removed/dead cgroup.
    # Retry must replay the missing name before touching that dead control FD.
    with pytest.raises(
        e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error
    ):
        e5a_v1._read_control(lease._role_fds["BUSINESS"], "cgroup.procs")
    closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert closure.to_document()["cleanup_attempt_count"] == 2
    assert lease.state == "CLOSED"
    assert e5a_v1._child_directories(delegated_parent_fd) == ()


@requires_delegated_parent
def test_closed_lease_atfork_handler_cannot_close_reused_fd(
    delegated_parent_fd: int,
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("fork is unavailable")
    lease = _prepare(delegated_parent_fd, 10)
    retired_fd = lease._parent_fd
    e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert lease.state == "CLOSED"
    assert id(lease) not in e5a_v1._LIVE_LEASES
    source_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    target_fd = retired_fd
    if source_fd != target_fd:
        os.dup2(source_fd, target_fd, inheritable=False)
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through wait status
        ok = lease.state == "CLOSED"
        try:
            metadata = os.fstat(target_fd)
            ok = ok and stat.S_ISCHR(metadata.st_mode)
        except OSError:
            ok = False
        os._exit(0 if ok else 91)
    try:
        waited, status = os.waitpid(child, 0)
        assert waited == child
        assert os.waitstatus_to_exitcode(status) == 0
        assert stat.S_ISCHR(os.fstat(target_fd).st_mode)
    finally:
        if source_fd != target_fd:
            os.close(target_fd)
        os.close(source_fd)


@requires_delegated_parent
def test_populated_cleanup_failure_is_identity_bound_and_retryable(
    delegated_parent_fd: int,
) -> None:
    lease = _prepare(delegated_parent_fd, 8)
    process = subprocess.Popen(
        ["/bin/sleep", "30"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    try:
        e5a_v1._write_control(
            lease._role_fds["WORKER"], "cgroup.procs", str(process.pid)
        )
        with pytest.raises(
            e5a_v1.ConstructionK7H1RouteWideWorkingSetCgroupV1Error,
            match="populated",
        ):
            e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
        assert lease.state == "CLEANUP_PENDING"
    finally:
        process.terminate()
        process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if (
            not e5a_v1._read_control(
                lease._role_fds["WORKER"], "cgroup.procs"
            ).strip()
            and e5a_v1._cgroup_populated(lease._outer_fd) == 0
        ):
            break
        time.sleep(0.01)
    closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(lease)
    assert closure.to_document()["cleanup_attempt_count"] == 2
    assert lease.state == "CLOSED"
