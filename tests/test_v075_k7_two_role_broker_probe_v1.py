from __future__ import annotations

import ctypes
import errno
import hashlib
import inspect
import os
from pathlib import Path
import signal
import struct
from types import SimpleNamespace

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_v1
from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as prep_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_v1
from acfqp import v075_k7_two_role_broker_probe_v1 as probe_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _successor_request
from tests.test_v075_k7_outer_attempt_broker_preparation_v1 import _fake_lease
from tests.test_v075_k7_parent_atomic_executor_v1 import _delegated_scope_parent_fd


def _bootstrap(label: str, raw: bytes = b"sealed-fake-executable"):
    fd = atomic_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw, name=f"acfqp-{label}"
    )
    try:
        return atomic_v1.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=fd,
            executable_sha256=hashlib.sha256(raw).hexdigest(),
            argv=(label,),
            environment={},
        )
    finally:
        os.close(fd)


def _fake_runtime(monkeypatch, returns):
    observed = []
    sequence = iter(returns)
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "probe_v075_k7_atomic_pidfd_capability_v1",
        lambda: SimpleNamespace(
            admitted=True, architecture="x86_64", landlock_abi_version=1
        ),
    )
    monkeypatch.setattr(probe_v1.atomic_v1, "_thread_count", lambda: 1)
    monkeypatch.setattr(
        probe_v1,
        "_pidfd_matches_child_v1",
        lambda pidfd, _pid: pidfd >= 0,
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_create_write_denial_landlock_ruleset_v1",
        lambda _abi: os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC),
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_wait_pidfd",
        lambda *_args, **_kwargs: SimpleNamespace(
            si_code=os.CLD_EXITED, si_status=0
        ),
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1, "_send_pidfd_signal", lambda *_args: None
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1, "_kill_and_reap_direct_child", lambda *_args: None
    )

    def trampoline(pointer):
        launch = ctypes.cast(
            pointer, ctypes.POINTER(probe_v1._NativeTwoRoleLaunchArgsV1)  # noqa: SLF001
        ).contents
        clone = atomic_v1.CloneArgsV1.from_address(launch.clone_args)
        result, pidfd = next(sequence)
        observed.append((clone.cgroup, clone.flags, launch.role_edge_cell))
        ctypes.c_long.from_address(launch.clone_result_cell).value = result
        if result > 0:
            ctypes.c_int.from_address(clone.pidfd).value = pidfd
            ctypes.c_uint64.from_address(launch.role_edge_cell).value = 1
            os.write(
                launch.setup_status_fd,
                struct.pack(
                    "<QQ", atomic_v1.K7AtomicPidfdSetupStageV1.READY_FOR_EXEC, 0
                ),
            )
        return result

    monkeypatch.setattr(probe_v1, "_native_two_role_trampoline_v1", lambda: trampoline)
    return observed


def _prepared(tmp_path, monkeypatch, label):
    context = _fake_lease(tmp_path, monkeypatch, label)
    lease, request, parent, outer, worker, rmdir = context.__enter__()
    session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
    return context, session, request, parent, outer, worker, rmdir


def test_profile_and_native_source_freeze_nonformal_two_role_contract() -> None:
    assert probe_v1.PROPOSED_CONTRACT_VERSION == "2.0.6"
    assert probe_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    document = probe_v1.official_v075_k7_two_role_broker_probe_profile_v1().to_document()
    assert document["readiness_level"] == "PREPARED_SESSION_CONSUMED_LIVE_PROBE"
    assert document["role_order"] == ["WORKER", "BUSINESS"]
    assert document["allowed_role_prefixes"] == [[0, 0], [1, 0], [1, 1]]
    assert document["native_role_edge_before_python_return"] is True
    assert document["bootstrap_authority"] == "CALLER_SUPPLIED_SEALED_PROBE_INPUT"
    assert document["role_manifest_bound"] is False
    assert all(value is False for value in probe_v1._locks().values())  # noqa: SLF001
    assert canonical_json_bytes(document)
    assembly = Path(probe_v1.__file__).with_name(
        "v075_k7_two_role_broker_trampoline_x86_64.S"
    ).read_text(encoding="utf-8")
    assert "role_edge_cell" in assembly
    assert assembly.index("movq    $1, (%rdx)") < assembly.index(".Lchild:")
    assert ctypes.sizeof(probe_v1._NativeTwoRoleLaunchArgsV1) == 88  # noqa: SLF001
    assert probe_v1._NativeTwoRoleLaunchArgsV1.role_edge_cell.offset == 72  # noqa: SLF001
    assert probe_v1._NativeTwoRoleLaunchArgsV1.clone_result_cell.offset == 80  # noqa: SLF001
    assert "movq    80(%r12), %rdx" in assembly
    assert hashlib.sha256(probe_v1._TRAMPOLINE_BYTES).hexdigest() == (  # noqa: SLF001
        probe_v1.TRAMPOLINE_SHA256
    )
    source = inspect.getsource(probe_v1)
    assert "os.fork(" not in source
    filters, _program = atomic_v1._seccomp_no_spawn_program_v1()  # noqa: SLF001
    denied = {row.k for row in filters if row.code == atomic_v1._BPF_JMP_JEQ_K}  # noqa: SLF001
    assert {56, 57, 58, 435} <= denied


def test_success_uses_worker_then_business_cgroups_and_two_pidfds(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-success"
    )
    observed = _fake_runtime(monkeypatch, ((1001, 901), (1002, 902)))
    expected_leaf_fds = (
        session.guardian._worker_fd,  # noqa: SLF001
        session.guardian._business_fd,  # noqa: SLF001
    )
    worker = _bootstrap("worker")
    business = _bootstrap("business")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.SUCCESS
        assert (result.worker_edge, result.business_edge) == (1, 1)
        assert (result.worker_pid, result.business_pid) == (1001, 1002)
        assert result.worker_reaped and result.business_reaped
        assert result.cleanup_complete is True
        assert result.failure_prefix is None
        assert tuple(row[0] for row in observed) == expected_leaf_fds
        assert all(row[1] == atomic_v1.REQUIRED_CLONE_FLAGS for row in observed)
        assert worker.consumed and worker.closed
        assert business.consumed and business.closed
        assert tuple(parent.iterdir()) == ()
        assert result.to_document()["process_launches_counter_record"] is None
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


@pytest.mark.parametrize(
    ("returns", "expected", "outcome"),
    (
        (
            ((-errno.EPERM, -1),),
            (0, 0),
            probe_v1.K7TwoRoleBrokerProbeOutcomeV1.WORKER_CLONE_REJECTED,
        ),
        (
            ((1101, 911), (-errno.EPERM, -1)),
            (1, 0),
            probe_v1.K7TwoRoleBrokerProbeOutcomeV1.BUSINESS_CLONE_REJECTED,
        ),
        (
            ((1102, 912), (1103, -1)),
            (1, 1),
            probe_v1.K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE,
        ),
    ),
)
def test_rejected_clone_preserves_exact_native_prefix(
    tmp_path, monkeypatch, returns, expected, outcome
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, f"probe-prefix-{expected[0]}-{expected[1]}"
    )
    _fake_runtime(monkeypatch, returns)
    worker = _bootstrap("worker-prefix")
    business = _bootstrap("business-prefix")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is outcome
        assert (result.worker_edge, result.business_edge) == expected
        assert result.failure_prefix is not None
        assert (
            result.failure_prefix.worker_edge,
            result.failure_prefix.business_edge,
        ) == expected
        assert result.cleanup_complete is True
        assert worker.consumed and business.consumed
        assert worker.closed and business.closed
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_post_clone_helper_failure_recovers_published_edge_pid_and_pidfd(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, _parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-post-edge"
    )
    _fake_runtime(monkeypatch, ((1201, 921),))
    original = probe_v1._launch_one_role  # noqa: SLF001

    def fail_after_publish(**kwargs):
        original(**kwargs)
        raise OSError("injected post-clone cleanup failure")

    monkeypatch.setattr(probe_v1, "_launch_one_role", fail_after_publish)
    worker = _bootstrap("worker-post-edge")
    business = _bootstrap("business-post-edge")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert (result.worker_edge, result.business_edge) == (1, 0)
        assert result.worker_pid == 1201
        assert result.worker_reaped is True
        assert result.failure_prefix is not None
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_native_cells_survive_exception_before_helper_return(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, _parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-native-cell-window"
    )
    _fake_runtime(monkeypatch, ((1251, 925),))
    native = probe_v1._native_two_role_trampoline_v1()  # noqa: SLF001

    def fail_after_native_cells(pointer):
        native(pointer)
        raise MemoryError("injected before helper return")

    monkeypatch.setattr(
        probe_v1,
        "_native_two_role_trampoline_v1",
        lambda: fail_after_native_cells,
    )
    worker = _bootstrap("worker-native-cell-window")
    business = _bootstrap("business-native-cell-window")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert (result.worker_edge, result.business_edge) == (1, 0)
        assert result.worker_pid == 1251
        assert result.worker_reaped is True
        assert result.failure_prefix is not None
        assert "MemoryError" in result.failure_prefix.failure_code
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_role_helper_pretry_failure_closes_both_setup_pipe_ends(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-helper-pretry-fd"
    )
    _fake_runtime(monkeypatch, ((1271, 927),))
    real_pipe2 = probe_v1.os.pipe2
    created_pipe_fds = []

    def tracked_pipe2(flags):
        pair = real_pipe2(flags)
        created_pipe_fds.extend(pair)
        return pair

    monkeypatch.setattr(probe_v1.os, "pipe2", tracked_pipe2)
    monkeypatch.setattr(
        probe_v1.os,
        "set_blocking",
        lambda *_args: (_ for _ in ()).throw(
            OSError("injected set_blocking failure")
        ),
    )
    worker = _bootstrap("worker-helper-pretry-fd")
    business = _bootstrap("business-helper-pretry-fd")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
        assert (result.worker_edge, result.business_edge) == (0, 0)
        assert result.cleanup_complete is True
        assert len(created_pipe_fds) == 2
        for descriptor in created_pipe_fds:
            with pytest.raises(OSError):
                os.fstat(descriptor)
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_positive_clone_without_pidfd_retains_edge_and_direct_reap(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, _parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-no-pidfd"
    )
    _fake_runtime(monkeypatch, ((1301, -1),))
    direct = []
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_kill_and_reap_direct_child",
        lambda pid: direct.append(pid),
    )
    worker = _bootstrap("worker-no-pidfd")
    business = _bootstrap("business-no-pidfd")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert (result.worker_edge, result.business_edge) == (1, 0)
        assert result.worker_pid == 1301
        assert result.worker_reaped is True
        assert direct == [1301]
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_capability_blocker_leaves_session_and_bootstraps_unconsumed(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-capability-blocked"
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "probe_v075_k7_atomic_pidfd_capability_v1",
        lambda: SimpleNamespace(admitted=False),
    )
    worker = _bootstrap("worker-capability-blocked")
    business = _bootstrap("business-capability-blocked")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.CAPABILITY_BLOCKED
        assert result.cleanup_complete is False
        assert worker.consumed is False and worker.closed is False
        assert business.consumed is False and business.closed is False
        assert session.guardian.closed is False
        session.close_prelaunch()
        assert tuple(parent.iterdir()) == ()
    finally:
        worker.close()
        business.close()
        context.__exit__(None, None, None)


def test_cleanup_partial_guardian_cannot_reach_clone(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-partial-guardian"
    )
    observed = _fake_runtime(monkeypatch, ((1601, 951),))
    session.guardian._state = prep_v1.K7PreparedBrokerCleanupStateV1.CLEANUP_PARTIAL  # noqa: SLF001
    worker = _bootstrap("worker-partial-guardian")
    business = _bootstrap("business-partial-guardian")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
        assert (result.worker_edge, result.business_edge) == (0, 0)
        assert observed == []
        assert session.guardian.closed is True
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_nonnegative_mismatched_pidfd_falls_back_to_direct_reap(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, _parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-mismatched-pidfd"
    )
    _fake_runtime(monkeypatch, ((1701, 961),))
    monkeypatch.setattr(probe_v1, "_pidfd_matches_child_v1", lambda *_args: False)
    direct = []
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_kill_and_reap_direct_child",
        lambda pid: direct.append(pid),
    )
    worker = _bootstrap("worker-mismatched-pidfd")
    business = _bootstrap("business-mismatched-pidfd")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
        assert (result.worker_edge, result.business_edge) == (1, 0)
        assert result.worker_reaped is True
        assert direct == [1701]
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_reap_failure_retains_retryable_pidfds_and_guardian(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-reap-retry"
    )
    _fake_runtime(monkeypatch, ((1401, 931), (1402, 932)))
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_wait_pidfd",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected reap failure")
        ),
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_kill_and_reap_direct_child",
        lambda *_args: (_ for _ in ()).throw(
            RuntimeError("injected direct reap failure")
        ),
    )
    worker = _bootstrap("worker-reap-retry")
    business = _bootstrap("business-reap-retry")
    try:
        with pytest.raises(
            probe_v1.V075K7TwoRoleBrokerProbeCleanupV1Error
        ) as caught:
            probe_v1.run_v075_k7_two_role_broker_probe_v1(
                prepared_session=session,
                worker_bootstrap=worker,
                business_bootstrap=business,
                deadline_milliseconds=1_000,
            )
        error = caught.value
        assert error.cleanup_complete is False
        assert error.unresolved_roles == ("WORKER", "BUSINESS")
        assert type(error.cleanup_authority) is probe_v1.K7TwoRoleBrokerCleanupAuthorityV1
        assert session.guardian.closed is False
        assert (error.prefix.worker_edge, error.prefix.business_edge) == (1, 1)
        monkeypatch.setattr(
            probe_v1.atomic_v1,
            "_wait_pidfd",
            lambda *_args, **_kwargs: SimpleNamespace(
                si_code=os.CLD_EXITED, si_status=0
            ),
        )
        monkeypatch.setattr(
            probe_v1.atomic_v1,
            "_kill_and_reap_direct_child",
            lambda *_args: None,
        )
        assert error.cleanup_authority.retry_cleanup() >= 0
        assert error.cleanup_authority.closed is True
        reused = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        try:
            error.cleanup_authority._native_cells["WORKER"].pidfd.value = reused  # noqa: SLF001
            error.cleanup_authority._refresh_native_facts()  # noqa: SLF001
            assert error.cleanup_authority._pidfds["WORKER"] == -1  # noqa: SLF001
            os.fstat(reused)
        finally:
            os.close(reused)
        assert session.guardian.closed is True
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_prefix_hash_failure_cannot_erase_preinstalled_cleanup_authority(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-prefix-hash-retry"
    )
    _fake_runtime(monkeypatch, ((1451, 941), (1452, 942)))
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_wait_pidfd",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected reap failure")
        ),
    )
    monkeypatch.setattr(
        probe_v1.atomic_v1,
        "_kill_and_reap_direct_child",
        lambda *_args: (_ for _ in ()).throw(
            RuntimeError("injected direct reap failure")
        ),
    )
    original_hash = probe_v1._hash  # noqa: SLF001

    def fail_failure_prefix_hash(domain, payload):
        if domain == probe_v1.V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN:
            raise MemoryError("injected prefix hash failure")
        return original_hash(domain, payload)

    monkeypatch.setattr(probe_v1, "_hash", fail_failure_prefix_hash)
    worker = _bootstrap("worker-prefix-hash-retry")
    business = _bootstrap("business-prefix-hash-retry")
    try:
        with pytest.raises(
            probe_v1.V075K7TwoRoleBrokerProbeCleanupV1Error
        ) as caught:
            probe_v1.run_v075_k7_two_role_broker_probe_v1(
                prepared_session=session,
                worker_bootstrap=worker,
                business_bootstrap=business,
                deadline_milliseconds=1_000,
            )
        error = caught.value
        assert error.prefix is None
        assert error.unresolved_roles == ("WORKER", "BUSINESS")
        assert type(error.cleanup_authority) is probe_v1.K7TwoRoleBrokerCleanupAuthorityV1
        assert session.guardian._two_role_cleanup_authority is error.cleanup_authority  # noqa: SLF001
        monkeypatch.setattr(probe_v1, "_hash", original_hash)
        monkeypatch.setattr(
            probe_v1.atomic_v1,
            "_wait_pidfd",
            lambda *_args, **_kwargs: SimpleNamespace(
                si_code=os.CLD_EXITED, si_status=0
            ),
        )
        monkeypatch.setattr(
            probe_v1.atomic_v1,
            "_kill_and_reap_direct_child",
            lambda *_args: None,
        )
        assert error.cleanup_authority.retry_cleanup() >= 0
        assert error.cleanup_authority.closed is True
        assert session.guardian._two_role_cleanup_authority is None  # noqa: SLF001
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_tree_only_cleanup_failure_retains_guard_and_rekills_on_retry(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-tree-only-retry"
    )
    _fake_runtime(monkeypatch, ((1471, 947), (1472, 948)))
    kill_calls = []
    original_kill = probe_v1._ancestor_kill  # noqa: SLF001

    def tracked_kill(guardian):
        kill_calls.append(guardian)
        return original_kill(guardian)

    monkeypatch.setattr(probe_v1, "_ancestor_kill", tracked_kill)
    original_close = session.guardian._close_prelaunch_locked  # noqa: SLF001
    close_calls = 0

    def fail_tree_cleanup_once():
        nonlocal close_calls
        close_calls += 1
        if close_calls == 1:
            raise RuntimeError("injected unknown populated-tree failure")
        return original_close()

    monkeypatch.setattr(
        session.guardian,
        "_close_prelaunch_locked",
        fail_tree_cleanup_once,
    )
    worker = _bootstrap("worker-tree-only-retry")
    business = _bootstrap("business-tree-only-retry")
    try:
        with pytest.raises(
            probe_v1.V075K7TwoRoleBrokerProbeCleanupV1Error
        ) as caught:
            probe_v1.run_v075_k7_two_role_broker_probe_v1(
                prepared_session=session,
                worker_bootstrap=worker,
                business_bootstrap=business,
                deadline_milliseconds=1_000,
            )
        error = caught.value
        assert error.unresolved_roles == ()
        assert type(error.cleanup_authority) is probe_v1.K7TwoRoleBrokerCleanupAuthorityV1
        assert session.guardian._two_role_cleanup_authority is error.cleanup_authority  # noqa: SLF001
        assert len(kill_calls) == 1
        assert error.cleanup_authority.retry_cleanup() >= 0
        assert len(kill_calls) == 2
        assert session.guardian.closed is True
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


def test_signal_restore_failure_occurs_after_native_guard_and_still_cleans(
    tmp_path, monkeypatch
) -> None:
    context, session, _request, parent, _outer, _worker, _rmdir = _prepared(
        tmp_path, monkeypatch, "probe-signal-restore"
    )
    _fake_runtime(monkeypatch, ((1501, 951), (1502, 952)))
    native = probe_v1._native_two_role_trampoline_v1()  # noqa: SLF001

    def guarded_native(pointer):
        assert type(
            session.guardian._two_role_cleanup_authority  # noqa: SLF001
        ) is probe_v1.K7TwoRoleBrokerCleanupAuthorityV1
        return native(pointer)

    monkeypatch.setattr(
        probe_v1,
        "_native_two_role_trampoline_v1",
        lambda: guarded_native,
    )

    def fail_only_restore(how, _mask):
        if how == signal.SIG_BLOCK:
            return set()
        assert how == signal.SIG_SETMASK
        raise RuntimeError("injected signal restore failure")

    monkeypatch.setattr(probe_v1.signal, "pthread_sigmask", fail_only_restore)
    worker = _bootstrap("worker-signal-restore")
    business = _bootstrap("business-signal-restore")
    try:
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=1_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
        assert (result.worker_edge, result.business_edge) == (1, 1)
        assert result.worker_reaped and result.business_reaped
        assert result.cleanup_complete is True
        assert result.failure_prefix is not None
        assert result.failure_prefix.failure_stage == "SIGNAL_RESTORE"
        assert session.guardian._two_role_cleanup_authority is None  # noqa: SLF001
        assert tuple(parent.iterdir()) == ()
    finally:
        if not worker.closed:
            worker.close()
        if not business.closed:
            business.close()
        context.__exit__(None, None, None)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_delegated_two_true_processes_launch_from_sibling_cgroups() -> None:
    if atomic_v1._thread_count() != 1:  # noqa: SLF001
        pytest.skip("positive clone3 path requires an exact single-thread parent")
    request = _successor_request("two-role-real")
    with _delegated_scope_parent_fd() as parent_fd:
        admission = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=parent_fd
        )
        token = outer_v1.official_v075_k7_outer_attempt_cgroup_nonce_service_v1().issue(
            request=request,
            admission_result=admission,
            delegated_parent_fd=parent_fd,
        )
        lease = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission,
            delegated_parent_fd=parent_fd,
            nonce_token=token,
        )
        assert type(lease) is outer_v1.K7OuterAttemptCgroupLeaseV1
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        true_raw = Path("/bin/true").read_bytes()
        worker = _bootstrap("true-worker", true_raw)
        business = _bootstrap("true-business", true_raw)
        result = probe_v1.run_v075_k7_two_role_broker_probe_v1(
            prepared_session=session,
            worker_bootstrap=worker,
            business_bootstrap=business,
            deadline_milliseconds=5_000,
        )
        assert result.outcome is probe_v1.K7TwoRoleBrokerProbeOutcomeV1.SUCCESS
        assert (result.worker_edge, result.business_edge) == (1, 1)
        assert result.worker_reaped and result.business_reaped
        assert result.final_memory_peak >= session.prelaunch_memory_peak
