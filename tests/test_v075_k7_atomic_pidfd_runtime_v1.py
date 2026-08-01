from __future__ import annotations

import ctypes
from dataclasses import asdict
import hashlib
import inspect
import os
from pathlib import Path
import pickle
import resource
import stat
import struct
from types import SimpleNamespace

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime
from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_cgroup_lease_v1 as lease_module
from acfqp import v075_k7_os_supervisor_admission_v1 as admission
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_public_campaign_authority_v1 as public_authority


def _sealed_memfd(raw: bytes, name: str = "acfqp-k7-runtime-test") -> int:
    return runtime.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw,
        name=name,
    )


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-atomic-pidfd-runtime-test:v1\x00" + label.encode()
    ).hexdigest()


def _successor_request(label: str):
    old_profile = accounted.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    profile = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
        accounted_profile=old_profile
    )
    registry = public_authority.V075TrustedSignerRegistryV1(
        public_authority.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY", (1 << 2047) + 1
        ),
        public_authority.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE", (1 << 2047) + 3
        ),
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id(f"workload-{label}"), _id(f"protocol-{label}"), 1,
        _id(f"structural-{label}"), _id(f"query-{label}"),
        _id(f"plan-{label}"), _id(f"threshold-{label}"),
        _id(f"epoch-{label}"), _id(f"rebuild-{label}"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id(f"prereg-{label}"), occurrence.protocol_id,
        old_profile.comparison_profile_id, old_profile.counter_registry_id,
        occurrence.structural_id, occurrence.query_id,
        occurrence.selected_plan_id, occurrence.threshold_profile_id,
        attempt.build_epoch_id, occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id, 1, _id(f"frontier-{label}"),
        _id(f"causal-{label}"), _id(f"prefix-{label}"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id, attempt.route_attempt_id,
        decision.decision_point_id, 1, decision.frontier_snapshot_id,
        _id(f"cap-{label}"),
    )
    route = accounted.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=old_profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    return successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=profile,
        route_identity=route,
        signer_registry=registry,
        opaque_environment_commitment_id=_id(f"opaque-{label}"),
        sealed_secret_commitment_id=_id(f"secret-{label}"),
        session_external_id=_id(f"session-{label}"),
        request_nonce=_id(f"nonce-{label}"),
        scientific_occurrence_id=_id(f"science-{label}"),
        schedule_id=_id(f"schedule-{label}"),
    )


def test_clone_args_matches_stable_linux_uapi_layout() -> None:
    assert ctypes.sizeof(runtime.CloneArgsV1) == 88
    assert [name for name, _ in runtime.CloneArgsV1._fields_] == [
        "flags",
        "pidfd",
        "child_tid",
        "parent_tid",
        "exit_signal",
        "stack",
        "stack_size",
        "tls",
        "set_tid",
        "set_tid_size",
        "cgroup",
    ]
    assert [getattr(runtime.CloneArgsV1, name).offset for name, _ in runtime.CloneArgsV1._fields_] == list(range(0, 88, 8))
    assert runtime.REQUIRED_CLONE_FLAGS == (
        runtime.CLONE_PIDFD
        | runtime.CLONE_CLEAR_SIGHAND
        | runtime.CLONE_INTO_CGROUP
    )


def test_capability_is_runtime_issued_and_nonformal() -> None:
    capability = runtime.probe_v075_k7_atomic_pidfd_capability_v1()
    document = capability.to_document()
    assert document["single_thread_required"] is True
    assert document["official_execution_allowed"] is False
    assert document["counter_record_authorized"] is False
    assert document["attempt_terminal_authorized"] is False
    assert document["unprivileged_parent_verified"] is True
    with pytest.raises(runtime.V075K7AtomicPidfdRuntimeV1Error, match="runtime-issued"):
        runtime.K7AtomicPidfdCapabilityV1(
            object(), "x86_64", 1, 22, 9, 9, 7, None, ()
        )


def test_capability_fails_closed_for_multithread_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "_thread_count", lambda: 2)
    capability = runtime.probe_v075_k7_atomic_pidfd_capability_v1()
    assert capability.admitted is False
    assert runtime.K7AtomicPidfdBlockerV1.MULTITHREADED_PARENT in capability.blockers


def test_capability_fails_closed_for_privileged_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    privileged = (
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (0,),
        (("CapInh", 0), ("CapPrm", 1), ("CapEff", 1), ("CapBnd", 1), ("CapAmb", 0)),
    )
    monkeypatch.setattr(runtime, "_parent_privilege_status", lambda: privileged)
    capability = runtime.probe_v075_k7_atomic_pidfd_capability_v1()
    assert capability.admitted is False
    assert runtime.K7AtomicPidfdBlockerV1.PRIVILEGED_PARENT in capability.blockers


def test_sealed_bootstrap_is_owned_bounded_and_unpickleable() -> None:
    executable_raw = b"not-an-elf-but-an-immutable-exec-fixture"
    executable_fd = _sealed_memfd(executable_raw)
    input_fd = _sealed_memfd(b"sealed-input")
    try:
        bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
            argv=("fixture", "--exact"),
            environment={"LANG": "C"},
            sealed_input_fds=(input_fd,),
        )
    finally:
        os.close(executable_fd)
        os.close(input_fd)
    with bootstrap:
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(bootstrap)


def test_sealed_bootstrap_has_no_caller_mutable_authority_state() -> None:
    executable_raw = b"sealed-bootstrap-authority"
    executable_fd = _sealed_memfd(executable_raw)
    try:
        bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
            argv=("fixture",),
            environment={},
        )
    finally:
        os.close(executable_fd)
    try:
        assert bootstrap.consumed is False
        assert bootstrap.closed is False
        with pytest.raises(AttributeError):
            bootstrap._argv = ("forged",)  # type: ignore[attr-defined]  # noqa: SLF001
        with pytest.raises(AttributeError):
            object.__setattr__(bootstrap, "_closed", True)
        with pytest.raises(TypeError):
            asdict(bootstrap)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(bootstrap)
        assert not hasattr(bootstrap, "__dict__")
        assert bootstrap.consumed is False
        assert bootstrap.closed is False
    finally:
        bootstrap.close()
    assert bootstrap.closed is True
    tombstone = runtime._BOOTSTRAP_RECORDS[bootstrap]  # noqa: SLF001
    assert tombstone.argv == ()
    assert tombstone.environment == ()
    assert tombstone.executable_sha256 == ""


def test_bootstrap_copies_executable_into_runtime_private_inode() -> None:
    executable_raw = b"runtime-private-executable-inode"
    executable_fd = _sealed_memfd(executable_raw)
    bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
        executable_fd=executable_fd,
        executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
        argv=("fixture",),
        environment={},
    )
    try:
        os.fchmod(executable_fd, 0)
        private_fd, _inputs, _argv, _environment = bootstrap._consume()  # noqa: SLF001
        assert stat.S_IMODE(os.fstat(private_fd).st_mode) == 0o500
        assert os.fstat(private_fd).st_ino != os.fstat(executable_fd).st_ino
    finally:
        os.close(executable_fd)
        bootstrap.close()


def test_unsealed_executable_is_rejected() -> None:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"mutable")
        os.close(write_fd)
        write_fd = -1
        with pytest.raises(
            runtime.V075K7AtomicPidfdRuntimeV1Error,
            match="regular file|sealed memfd",
        ):
            runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
                executable_fd=read_fd,
                executable_sha256=hashlib.sha256(b"mutable").hexdigest(),
                argv=("fixture",),
                environment={},
            )
    finally:
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)


def test_bootstrap_rejects_unregistered_environment_and_unbounded_argv() -> None:
    executable_raw = b"sealed-executable"
    executable_fd = _sealed_memfd(executable_raw)
    try:
        with pytest.raises(
            runtime.V075K7AtomicPidfdRuntimeV1Error,
            match="unregistered key",
        ):
            runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
                executable_fd=executable_fd,
                executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
                argv=("fixture",),
                environment={"LD_PRELOAD": "/tmp/forged.so"},
            )
        with pytest.raises(
            runtime.V075K7AtomicPidfdRuntimeV1Error,
            match="argv",
        ):
            runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
                executable_fd=executable_fd,
                executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
                argv=tuple("x" for _ in range(runtime.MAX_ARGV_COUNT + 1)),
                environment={},
            )
    finally:
        os.close(executable_fd)


def test_consumed_bootstrap_failure_closes_lease_and_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable_raw = b"sealed-executable"
    executable_fd = _sealed_memfd(executable_raw)
    try:
        bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
            argv=("fixture",),
            environment={},
        )
    finally:
        os.close(executable_fd)

    class FakeLease:
        lease_id = _id("cleanup-lease")
        leaf_fd = 99

        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    lease = FakeLease()
    mask_events: list[int] = []

    def signal_mask(how, _signals):
        mask_events.append(how)
        if how == runtime.signal.SIG_BLOCK:
            return set()
        assert lease.closed is True
        assert bootstrap.closed is True
        return set()

    monkeypatch.setattr(lease_module, "K7CgroupAttemptLeaseV1", FakeLease)
    monkeypatch.setattr(runtime.signal, "pthread_sigmask", signal_mask)
    monkeypatch.setattr(
        runtime,
        "probe_v075_k7_atomic_pidfd_capability_v1",
        lambda: SimpleNamespace(admitted=True, architecture="x86_64"),
    )
    monkeypatch.setattr(
        runtime.K7SealedBootstrapExecV1,
        "_consume",
        lambda _self: (_ for _ in ()).throw(
            runtime.V075K7AtomicPidfdRuntimeV1Error("injected consume failure")
        ),
    )
    with pytest.raises(
        runtime.V075K7AtomicPidfdRuntimeV1Error,
        match="injected consume failure",
    ):
        runtime.run_v075_k7_atomic_pidfd_runtime_v1(
            lease=lease,
            bootstrap=bootstrap,
            deadline_milliseconds=100,
            memory_max_bytes=runtime.MIN_MEMORY_MAX_BYTES,
        )
    assert lease.closed is True
    assert bootstrap.closed is True
    assert mask_events == [runtime.signal.SIG_BLOCK, runtime.signal.SIG_SETMASK]
    assert all(key[1] != id(lease) for key in runtime._CONSUMED_LEASES)  # noqa: SLF001


@pytest.mark.parametrize(
    "raw",
    (
        b"nr_descendants 0\nnr_dying_descendants 0\n",
        b"nr_descendants 0\nnr_dying_descendants 0\nother 4\n",
    ),
)
def test_cgroup_stat_parser_accepts_exact_nonnegative_rows(raw: bytes) -> None:
    parsed = runtime._parse_cgroup_stat(raw)  # noqa: SLF001
    assert parsed["nr_descendants"] == 0
    assert parsed["nr_dying_descendants"] == 0


@pytest.mark.parametrize(
    "raw",
    (
        b"nr_descendants 0\n",
        b"nr_descendants 0\nnr_descendants 0\nnr_dying_descendants 0\n",
        b"nr_descendants -1\nnr_dying_descendants 0\n",
        b"nr_descendants nope\nnr_dying_descendants 0\n",
    ),
)
def test_cgroup_stat_parser_rejects_missing_duplicate_or_invalid_rows(raw: bytes) -> None:
    with pytest.raises(runtime.V075K7AtomicPidfdRuntimeV1Error):
        runtime._parse_cgroup_stat(raw)  # noqa: SLF001


def test_exact_inheritable_fd_audit_rejects_unregistered_descriptor() -> None:
    read_fd, write_fd = os.pipe()
    try:
        os.set_inheritable(read_fd, True)
        with pytest.raises(
            runtime.V075K7AtomicPidfdRuntimeV1Error,
            match="unexpected inheritable",
        ):
            runtime._assert_exact_inheritable_fds({0, 1, 2})  # noqa: SLF001
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_descriptor_role_audit_rejects_fd_number_reuse() -> None:
    first_read, first_write = os.pipe()
    second_read, second_write = os.pipe()
    try:
        os.set_inheritable(first_read, True)
        identities = (runtime._descriptor_identity(first_read),)  # noqa: SLF001
        os.dup2(second_read, first_read, inheritable=True)
        with pytest.raises(
            runtime.V075K7AtomicPidfdRuntimeV1Error,
            match="identity or inheritance",
        ):
            runtime._assert_descriptor_roles_current(  # noqa: SLF001
                descriptors=(first_read,),
                identities=identities,
                required_inheritable=(first_read,),
            )
    finally:
        os.close(first_read)
        os.close(first_write)
        os.close(second_read)
        os.close(second_write)


def test_public_run_rejects_forged_lease_before_any_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def forbidden(*_args):
        nonlocal calls
        calls += 1
        raise AssertionError("clone syscall must not be reached")

    monkeypatch.setattr(runtime, "_raw_syscall", forbidden)
    with pytest.raises(runtime.V075K7AtomicPidfdRuntimeV1Error, match="exact cgroup lease"):
        runtime.run_v075_k7_atomic_pidfd_runtime_v1(
            lease=object(),  # type: ignore[arg-type]
            bootstrap=object(),  # type: ignore[arg-type]
            deadline_milliseconds=100,
            memory_max_bytes=runtime.MIN_MEMORY_MAX_BYTES,
        )
    assert calls == 0


def test_source_has_no_fork_or_popen_fallback_and_uses_pidfd_primitives() -> None:
    source = inspect.getsource(runtime)
    forbidden_tokens = ("subprocess" + ".Popen", "os" + ".fork(", "fork" + "server")
    assert all(token not in source for token in forbidden_tokens)
    assert "CLONE_INTO_CGROUP" in source
    assert "CLONE_PIDFD" in source
    assert "os.waitid(P_PIDFD" in source
    assert "pidfd_send_signal" in source
    assert "cgroup.stat" in source
    assert "_native_trampoline_v1" in source
    assert "clone_result == 0" not in source
    assert runtime.MAX_DEADLINE_MILLISECONDS == 12 * 60 * 60 * 1000
    assert source.index("trampoline = _native_trampoline_v1()") < source.index(
        "if _thread_count() == 1"
    )
    assert "signal.pthread_sigmask" in source
    critical = inspect.getsource(runtime.run_v075_k7_atomic_pidfd_runtime_v1)
    assert critical.index("signal.SIG_BLOCK") < critical.index(
        "_assert_descriptor_roles_current"
    ) < critical.index("if _thread_count() == 1")

    assembly = (
        Path(runtime.__file__).with_name("v075_k7_atomic_trampoline_x86_64.S")
    ).read_text(encoding="utf-8")
    assert "landlock_restrict_self" in assembly
    assert "PR_SET_PDEATHSIG" in assembly
    assert "PR_SET_SECCOMP" in assembly
    assert "setup_status_fd" in assembly
    assert "READY_FOR_EXEC" in assembly
    assert "execveat" in assembly
    assert hashlib.sha256(runtime._X86_64_TRAMPOLINE_BYTES).hexdigest() == (  # noqa: SLF001
        runtime.X86_64_TRAMPOLINE_SHA256
    )


def test_seccomp_filter_denies_spawn_escape_and_parent_tampering() -> None:
    filters, program = runtime._seccomp_no_spawn_program_v1()  # noqa: SLF001
    assert program.length == len(filters)
    for syscall_number in (
        16, 56, 57, 58, 76, 77, 90, 91, 92, 93, 94, 132,
        141, 142, 144, 157, 188, 189, 190, 197, 198, 199, 203,
        235, 248, 249, 250, 251, 256, 260, 261, 268, 272, 279,
        280, 302, 308, 310, 311, 312, 314, 424, 434, 435, 438, 452,
    ):
        assert syscall_number in runtime._SECCOMP_DENIED_X86_64_SYSCALLS  # noqa: SLF001

    def evaluate(syscall_number: int, architecture: int, argument1: int = 0) -> int:
        accumulator = 0
        pc = 0
        while True:
            row = filters[pc]
            if row.code == runtime._BPF_LD_W_ABS:  # noqa: SLF001
                accumulator = {
                    0: syscall_number,
                    4: architecture,
                    24: argument1,
                }[row.k]
                pc += 1
            elif row.code == runtime._BPF_JMP_JEQ_K:  # noqa: SLF001
                pc += 1 + (row.jt if accumulator == row.k else row.jf)
            elif row.code == runtime._BPF_JMP_JSET_K:  # noqa: SLF001
                pc += 1 + (row.jt if accumulator & row.k else row.jf)
            elif row.code == runtime._BPF_RET_K:  # noqa: SLF001
                return row.k
            else:  # pragma: no cover - closed filter instruction set
                raise AssertionError(f"unknown BPF instruction {row.code}")

    assert evaluate(435, runtime._AUDIT_ARCH_X86_64) == (  # noqa: SLF001
        runtime._SECCOMP_RET_ERRNO | 1  # noqa: SLF001
    )
    assert evaluate(435 | 0x40000000, runtime._AUDIT_ARCH_X86_64) == (  # noqa: SLF001
        runtime._SECCOMP_RET_KILL_PROCESS  # noqa: SLF001
    )
    assert evaluate(39, 0) == runtime._SECCOMP_RET_KILL_PROCESS  # noqa: SLF001
    assert evaluate(72, runtime._AUDIT_ARCH_X86_64, 8) == (  # noqa: SLF001
        runtime._SECCOMP_RET_ERRNO | 1  # noqa: SLF001
    )
    assert evaluate(72, runtime._AUDIT_ARCH_X86_64, 1034) == (  # noqa: SLF001
        runtime._SECCOMP_RET_ALLOW  # noqa: SLF001
    )


def test_pidfd_wait_probe_distinguishes_unknown_idtype_from_non_pidfd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.os, "open", lambda *_args, **_kwargs: 77)
    monkeypatch.setattr(runtime.os, "close", lambda _fd: None)
    monkeypatch.setattr(
        runtime.os,
        "waitid",
        lambda *_args: (_ for _ in ()).throw(OSError(22, "EINVAL")),
    )
    assert runtime._pidfd_wait_available() is False  # noqa: SLF001
    monkeypatch.setattr(
        runtime.os,
        "waitid",
        lambda *_args: (_ for _ in ()).throw(OSError(9, "EBADF")),
    )
    assert runtime._pidfd_wait_available() is True  # noqa: SLF001


def test_native_setup_status_distinguishes_ready_exec_and_setup_failure() -> None:
    ready = struct.pack("<QQ", 0, 0)
    assert runtime._parse_setup_status(ready) == (True, None, None)  # noqa: SLF001
    failed = struct.pack("<QQ", 4, 13)
    assert runtime._parse_setup_status(failed) == (  # noqa: SLF001
        False,
        runtime.K7AtomicPidfdSetupStageV1.LANDLOCK_RESTRICTION,
        13,
    )
    exec_failed = ready + struct.pack("<QQ", 10, 8)
    assert runtime._parse_setup_status(exec_failed) == (  # noqa: SLF001
        False,
        runtime.K7AtomicPidfdSetupStageV1.EXECVEAT,
        8,
    )
    with pytest.raises(runtime.V075K7AtomicPidfdRuntimeV1Error):
        runtime._parse_setup_status(b"partial")  # noqa: SLF001


def test_memory_and_swap_caps_require_exact_readback_and_cgroup_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[int, str, str]] = []
    closed: list[int] = []
    monkeypatch.setattr(
        lease_module,
        "_write_control",
        lambda fd, name, value: writes.append((fd, name, value)),
    )
    monkeypatch.setattr(
        lease_module,
        "_read_control",
        lambda _fd, name: {
            "memory.max": str(runtime.MIN_MEMORY_MAX_BYTES).encode(),
            "memory.swap.max": b"0",
        }[name],
    )
    monkeypatch.setattr(runtime.os, "open", lambda *_args, **_kwargs: 91)
    monkeypatch.setattr(
        runtime.os,
        "fstat",
        lambda _fd: SimpleNamespace(st_mode=stat.S_IFREG),
    )
    monkeypatch.setattr(runtime.os, "close", closed.append)
    runtime._configure_leaf_runtime_controls(  # noqa: SLF001
        leaf_fd=17,
        memory_max_bytes=runtime.MIN_MEMORY_MAX_BYTES,
    )
    assert writes == [
        (17, "memory.max", str(runtime.MIN_MEMORY_MAX_BYTES)),
        (17, "memory.swap.max", "0"),
    ]
    assert closed == [91]


def test_cgroup_kill_cleanup_is_invoked_until_leaf_is_proven_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter((False, True))
    writes: list[tuple[int, str, str]] = []
    monkeypatch.setattr(
        runtime,
        "_leaf_is_empty_and_descendant_free",
        lambda _fd: next(states),
    )
    monkeypatch.setattr(
        lease_module,
        "_write_control",
        lambda fd, name, value: writes.append((fd, name, value)),
    )
    runtime._kill_leaf_and_wait_empty(23)  # noqa: SLF001
    assert writes == [(23, "cgroup.kill", "1")]


def test_forced_status_reports_observed_exit_not_assumed_kill() -> None:
    exited = SimpleNamespace(si_code=os.CLD_EXITED, si_status=0)
    outcome, exit_code, terminating_signal = runtime._status(  # noqa: SLF001
        exited, "OUTPUT_CAP"
    )
    assert outcome is runtime.K7AtomicPidfdOutcomeV1.OUTPUT_CAP_EXCEEDED
    assert exit_code == 0
    assert terminating_signal is None

    killed = SimpleNamespace(si_code=os.CLD_KILLED, si_status=9)
    outcome, exit_code, terminating_signal = runtime._status(  # noqa: SLF001
        killed, "DEADLINE"
    )
    assert outcome is runtime.K7AtomicPidfdOutcomeV1.DEADLINE_KILLED
    assert exit_code is None
    assert terminating_signal == 9


def test_output_counter_preserves_observed_bytes_beyond_captured_prefix() -> None:
    counters = runtime.K7AtomicPidfdCountersV1(
        1, 1, 1, 3, 11, 8, runtime.SUCCESS_PATH_CGROUP_CONTROL_READS
    )
    result = runtime.K7AtomicPidfdRunResultV1(
        runtime._RESULT_ISSUER,  # noqa: SLF001
        lease_id=_id("result-lease"),
        child_pid=123,
        outcome=runtime.K7AtomicPidfdOutcomeV1.OUTPUT_CAP_KILLED,
        exit_code=None,
        terminating_signal=9,
        setup_succeeded=True,
        setup_failure_stage=None,
        setup_errno=None,
        output=b"12345678",
        output_truncated=True,
        memory_max_bytes=runtime.MIN_MEMORY_MAX_BYTES,
        memory_peak_bytes=4096,
        cgroup_empty_verified=True,
        no_descendants_verified=True,
        elapsed_nanoseconds=100,
        counters=counters,
    )
    assert result.to_document()["total_observed_output_byte_count"] == 11
    assert result.to_document()["output_byte_count"] == 8


def test_preflight_blocker_preserves_caller_authority_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable_raw = b"sealed-preflight-executable"
    executable_fd = _sealed_memfd(executable_raw)
    try:
        bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(executable_raw).hexdigest(),
            argv=("fixture",),
            environment={},
        )
    finally:
        os.close(executable_fd)

    class FakeLease:
        pass

    lease = FakeLease()
    monkeypatch.setattr(lease_module, "K7CgroupAttemptLeaseV1", FakeLease)
    monkeypatch.setattr(
        runtime,
        "probe_v075_k7_atomic_pidfd_capability_v1",
        lambda: SimpleNamespace(
            admitted=False,
            blockers=(runtime.K7AtomicPidfdBlockerV1.LANDLOCK_UNAVAILABLE,),
        ),
    )
    result = runtime.run_v075_k7_atomic_pidfd_runtime_v1(
        lease=lease,
        bootstrap=bootstrap,
        deadline_milliseconds=100,
        memory_max_bytes=runtime.MIN_MEMORY_MAX_BYTES,
    )
    assert type(result) is runtime.K7AtomicPidfdBlockedResultV1
    assert result.lease_consumed is False
    assert result.lease_closed is False
    assert result.bootstrap_consumed is False
    assert result.bootstrap_closed is False
    assert bootstrap.closed is False
    bootstrap.close()


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_delegated_scope_executes_sealed_true_and_reaps_by_pidfd() -> None:
    """Opt-in positive integration; it never substitutes a fake cgroup tree.

    Run this test inside ``systemd-run --user --scope -p Delegate=yes``.  It
    moves itself into a supervisor sibling before enabling the scope-root
    controllers, then restores and removes that sibling in ``finally``.
    """

    if runtime._thread_count() != 1:  # noqa: SLF001
        pytest.skip("positive clone3 path requires an exact single-thread parent")

    relative = next(
        row.removeprefix("0::").strip()
        for row in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if row.startswith("0::")
    )
    parent_path = Path(
        os.environ.get(
            "ACFQP_K7_DELEGATED_PARENT",
            str(Path("/sys/fs/cgroup") / relative.lstrip("/")),
        )
    )
    assert parent_path.is_dir()
    assert parent_path.as_posix().startswith("/sys/fs/cgroup/")
    supervisor_name = f"acfqp-supervisor-{os.getpid()}"
    supervisor_path = parent_path / supervisor_name
    parent_fd = os.open(parent_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    moved = False
    controllers_enabled = False
    executable_fd = -1
    attempt_lease = None
    bootstrap = None
    second_lease = None
    second_bootstrap = None
    failure_lease = None
    failure_bootstrap = None
    mutation_probe = Path(f"/tmp/acfqp-landlock-probe-{os.getpid()}")
    try:
        os.mkdir(supervisor_name, mode=0o700, dir_fd=parent_fd)
        (supervisor_path / "cgroup.procs").write_text(
            f"{os.getpid()}\n", encoding="ascii"
        )
        moved = True
        (parent_path / "cgroup.subtree_control").write_text(
            "+memory +pids\n", encoding="ascii"
        )
        controllers_enabled = True
        assert {"memory", "pids"} <= set(
            (parent_path / "cgroup.subtree_control")
            .read_text(encoding="ascii")
            .split()
        )

        request = _successor_request("real-delegated")
        admission_result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=parent_fd
        )
        token = lease_module.official_v075_k7_cgroup_lease_nonce_service_v1().issue(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
        )
        attempt_lease = lease_module.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
            nonce_token=token,
        )
        assert type(attempt_lease) is lease_module.K7CgroupAttemptLeaseV1

        executable = Path("/bin/true").read_bytes()
        executable_fd = _sealed_memfd(executable, "acfqp-sealed-true")
        bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(executable).hexdigest(),
            argv=("true",),
            environment={},
        )
        os.close(executable_fd)
        executable_fd = -1
        result = runtime.run_v075_k7_atomic_pidfd_runtime_v1(
            lease=attempt_lease,
            bootstrap=bootstrap,
            deadline_milliseconds=5_000,
            memory_max_bytes=512 * 1024 * 1024,
        )
        if type(result) is runtime.K7AtomicPidfdBlockedResultV1:
            attempt_lease.close()
        assert type(result) is runtime.K7AtomicPidfdRunResultV1
        assert result.outcome is runtime.K7AtomicPidfdOutcomeV1.EXITED
        assert result.exit_code == 0
        assert result.setup_succeeded is True
        assert result.output == b""
        assert result.counters.process_launches == 1
        assert result.counters.pidfd_waits == 1
        assert result.memory_peak_bytes >= 0
        assert result.cgroup_empty_verified is True
        assert result.no_descendants_verified is True
        assert result.to_document()["counter_record_issued"] is False

        # A second real child proves the installed seccomp/Landlock policy,
        # rather than merely proving that /bin/true can start under it.
        mutation_probe.write_bytes(b"parent-owned")
        request = _successor_request("real-sandbox-denial")
        token = lease_module.official_v075_k7_cgroup_lease_nonce_service_v1().issue(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
        )
        second_lease = lease_module.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
            nonce_token=token,
        )
        assert type(second_lease) is lease_module.K7CgroupAttemptLeaseV1
        python_path = Path(os.path.realpath(__import__("sys").executable))
        python_raw = python_path.read_bytes()
        executable_fd = _sealed_memfd(python_raw, "acfqp-sealed-python")
        child_code = (
            "import errno,fcntl,os,resource,socket,sys;"
            "fd=int(os.environ['ACFQP_K7_PARENT_CHANNEL_FD']);"
            "rows=[];"
            "\ntry: os.fork(); rows.append('fork=allowed')"
            "\nexcept OSError as e: rows.append('fork='+str(e.errno));"
            "\ntry: x=os.open(sys.argv[1],os.O_WRONLY);"
            " os.close(x); rows.append('file=allowed')"
            "\nexcept OSError as e: rows.append('file='+str(e.errno));"
            "\ntry: os.chmod(sys.argv[1],0); rows.append('chmod=allowed')"
            "\nexcept OSError as e: rows.append('chmod='+str(e.errno));"
            "\nrel=next(x[3:].strip() for x in open('/proc/self/cgroup') if x.startswith('0::'));"
            " target='/sys/fs/cgroup/'+rel.strip('/').rsplit('/',1)[0]+'/cgroup.procs';"
            "\ntry: x=os.open(target,os.O_WRONLY); os.close(x); rows.append('cgroup=allowed')"
            "\nexcept OSError as e: rows.append('cgroup='+str(e.errno));"
            "\ntry: socket.socket(); rows.append('socket=allowed')"
            "\nexcept OSError as e: rows.append('socket='+str(e.errno));"
            "\ntry: resource.prlimit(os.getppid(),resource.RLIMIT_NOFILE,"
            "(int(sys.argv[2]),int(sys.argv[3]))); rows.append('prlimit=allowed')"
            "\nexcept OSError as e: rows.append('prlimit='+str(e.errno));"
            "\ntry: fcntl.fcntl(fd,fcntl.F_SETOWN,os.getppid());"
            " rows.append('fcntl_owner=allowed')"
            "\nexcept OSError as e: rows.append('fcntl_owner='+str(e.errno));"
            "\nos.write(fd,(','.join(rows)).encode())"
        )
        nofile_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        second_bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(python_raw).hexdigest(),
            argv=(
                str(python_path),
                "-I",
                "-S",
                "-c",
                child_code,
                str(mutation_probe),
                str(nofile_limit[0]),
                str(nofile_limit[1]),
            ),
            environment={"PYTHONHASHSEED": "0"},
        )
        os.close(executable_fd)
        executable_fd = -1
        denied = runtime.run_v075_k7_atomic_pidfd_runtime_v1(
            lease=second_lease,
            bootstrap=second_bootstrap,
            deadline_milliseconds=10_000,
            memory_max_bytes=512 * 1024 * 1024,
        )
        assert type(denied) is runtime.K7AtomicPidfdRunResultV1
        assert denied.outcome is runtime.K7AtomicPidfdOutcomeV1.EXITED
        assert denied.exit_code == 0
        assert denied.setup_succeeded is True
        assert denied.output == (
            b"fork=1,file=13,chmod=1,cgroup=13,socket=1,prlimit=1,fcntl_owner=1"
        )
        assert stat.S_IMODE(mutation_probe.stat().st_mode) != 0

        # A non-executable sealed image proves the dedicated setup channel can
        # distinguish execveat failure from a program that exits 127 itself.
        request = _successor_request("real-exec-failure")
        token = lease_module.official_v075_k7_cgroup_lease_nonce_service_v1().issue(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
        )
        failure_lease = lease_module.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
            nonce_token=token,
        )
        assert type(failure_lease) is lease_module.K7CgroupAttemptLeaseV1
        invalid_raw = b"not-an-executable-image"
        executable_fd = _sealed_memfd(invalid_raw, "acfqp-sealed-invalid-exec")
        failure_bootstrap = runtime.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=hashlib.sha256(invalid_raw).hexdigest(),
            argv=("invalid",),
            environment={},
        )
        os.close(executable_fd)
        executable_fd = -1
        failed = runtime.run_v075_k7_atomic_pidfd_runtime_v1(
            lease=failure_lease,
            bootstrap=failure_bootstrap,
            deadline_milliseconds=5_000,
            memory_max_bytes=512 * 1024 * 1024,
        )
        assert type(failed) is runtime.K7AtomicPidfdRunResultV1
        assert failed.outcome is runtime.K7AtomicPidfdOutcomeV1.SETUP_FAILED
        assert failed.exit_code == 127
        assert failed.setup_succeeded is False
        assert failed.setup_failure_stage is runtime.K7AtomicPidfdSetupStageV1.EXECVEAT
        assert failed.setup_errno == 8
        assert failed.output == b""
    finally:
        if executable_fd >= 0:
            os.close(executable_fd)
        for owned_bootstrap in (bootstrap, second_bootstrap, failure_bootstrap):
            if owned_bootstrap is not None and not owned_bootstrap.closed:
                owned_bootstrap.close()
        for owned_lease in (attempt_lease, second_lease, failure_lease):
            if owned_lease is not None and not owned_lease._closed:  # noqa: SLF001
                owned_lease.close()
        if controllers_enabled:
            (parent_path / "cgroup.subtree_control").write_text(
                "-memory -pids\n", encoding="ascii"
            )
        if moved:
            (parent_path / "cgroup.procs").write_text(
                f"{os.getpid()}\n", encoding="ascii"
            )
        try:
            os.rmdir(supervisor_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
        mutation_probe.unlink(missing_ok=True)
