from __future__ import annotations

import ctypes
import fcntl
import hashlib
import inspect
import os
from pathlib import Path
import signal
import socket
import stat
import struct
import tempfile
from types import SimpleNamespace

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_v1
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_broker_resource_session_v2 as resource_v2
from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as prep_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_v1
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_launch_authority_v2 as launch_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2
from acfqp import v075_signer_owning_complete_observer_lifecycle_ipc_v1 as lifecycle
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id
from tests.test_v075_k7_parent_atomic_executor_v1 import (
    _delegated_scope_parent_fd,
    _production_request,
)
from tests.test_v075_production_private_signer_runtime_v1 import (
    REPOSITORY_ROOT,
    _key_document,
    _registry,
    _write_private_key,
)


def _binding(label: str) -> ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
    return ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        _id(f"runtime-{label}-request"),
        _id(f"runtime-{label}-route"),
        _id(f"runtime-{label}-spec"),
        _id(f"runtime-{label}-nonce"),
    )


def _seqpacket_pair() -> tuple[socket.socket, socket.socket]:
    broker, child = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
    )
    broker.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    broker.set_inheritable(False)
    child.set_inheritable(False)
    return broker, child


def _child_send(endpoint: socket.socket, raw: bytes) -> None:
    if endpoint.send(raw, getattr(socket, "MSG_NOSIGNAL", 0)) != len(raw):
        os._exit(90)


def _fork_worker(
    *,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    broker: socket.socket,
    child: socket.socket,
    output_raw: bytes,
) -> tuple[int, int]:
    pid = os.fork()
    if pid == 0:  # pragma: no cover - child outcome checked by parent
        try:
            broker.close()
            role = ipc_v1.K7OuterAttemptBrokerFrameRoleV1
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=role.WORKER_READY,
                    payload={"worker_replay_id": _id("runtime-worker-replay")},
                ),
            )
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=role.BUSINESS_REQUEST,
                    payload={"request_ordinal": 0},
                ),
            )
            relayed = child.recv(ipc_v1.FRAME_WIDTH + ipc_v1.MAX_FRAME_BYTES)
            if not relayed or child.recv(1) != b"":
                os._exit(91)
            ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
                raw=relayed,
                expected_binding=binding,
                expected_role=role.BUSINESS_RESULT,
            )
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=role.PARENT_OUTPUT,
                    payload={
                        "output_byte_count": len(output_raw),
                        "output_sha256": hashlib.sha256(output_raw).hexdigest(),
                    },
                ),
            )
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=role.WORKER_EOF,
                    payload={"clean_close": True},
                ),
            )
            child.close()
            os._exit(0)
        except BaseException:
            os._exit(92)
    child.close()
    return pid, os.pidfd_open(pid, 0)


def _fork_business(
    *,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    broker: socket.socket,
    child: socket.socket,
    result_id: str,
) -> tuple[int, int]:
    pid = os.fork()
    if pid == 0:  # pragma: no cover - child outcome checked by parent
        try:
            broker.close()
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT,
                    payload={"business_result_id": result_id},
                ),
            )
            child.close()
            os._exit(0)
        except BaseException:
            os._exit(93)
    child.close()
    return pid, os.pidfd_open(pid, 0)


def _launch_row(role: str, pid: int, pidfd: int) -> runtime_v2._LaunchOutcomeV2:  # noqa: SLF001
    return runtime_v2._LaunchOutcomeV2(  # noqa: SLF001
        role,
        pid,
        pidfd,
        runtime_v2._descriptor_identity(pidfd),  # noqa: SLF001
        1,
        hashlib.sha256(b"setup").hexdigest(),
        len(b"setup"),
    )


def test_profile_exposes_nonformal_output_role_mismatch_and_no_receipts() -> None:
    document = (
        runtime_v2.official_v075_k7_production_broker_runtime_profile_v2()
        .to_document()
    )
    assert document["output_role"] == "PRE_REAP_OPERATIONAL_RESULT"
    assert document["registered_eight_role_business_result_claimed"] is False
    assert document["failure_never_deletes_nonempty_output"] is True
    assert document["native_clone3_into_fixed_sibling_cgroups"] is True
    assert document["success_output_post_reap_sealed_readonly"] is True
    assert document["central_domain_registration_pending"] is False
    assert runtime_v2.RUNTIME_PROFILE_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert runtime_v2.RUNTIME_ENVELOPE_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert runtime_v2.RUNTIME_PROFILE_DOMAIN != runtime_v2.RUNTIME_ENVELOPE_DOMAIN
    assert all(value is False for value in document["formal_locks"].values())
    with pytest.raises(runtime_v2.V075K7ProductionBrokerRuntimeV2Error):
        runtime_v2.K7ProductionBrokerRuntimeProfileV2(object())


@pytest.mark.skipif(
    not hasattr(os, "pidfd_open"),
    reason="pidfd lifecycle support is unavailable",
)
def test_fake_protocol_authentication_and_private_envelope_invariants() -> None:
    binding = _binding("five-frame")
    output_raw = canonical_json_bytes({"fake": "pre-reap-operational-output"})
    result_id = _id("runtime-fake-business-result")
    worker_broker, worker_child = _seqpacket_pair()
    business_broker, business_child = _seqpacket_pair()
    worker_pid = worker_pidfd = business_pid = business_pidfd = -1
    try:
        worker_pid, worker_pidfd = _fork_worker(
            binding=binding,
            broker=worker_broker,
            child=worker_child,
            output_raw=output_raw,
        )
        worker = _launch_row("WORKER", worker_pid, worker_pidfd)
        deadline = runtime_v2.time.monotonic_ns() + 10_000_000_000
        roles = ipc_v1.K7OuterAttemptBrokerFrameRoleV1
        observations = [
            runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                endpoint=worker_broker,
                launch=worker,
                binding=binding,
                role=roles.WORKER_READY,
                deadline_ns=deadline,
            ),
            runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                endpoint=worker_broker,
                launch=worker,
                binding=binding,
                role=roles.BUSINESS_REQUEST,
                deadline_ns=deadline,
            ),
        ]
        business_pid, business_pidfd = _fork_business(
            binding=binding,
            broker=business_broker,
            child=business_child,
            result_id=result_id,
        )
        business = _launch_row("BUSINESS", business_pid, business_pidfd)
        observations.append(
            runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                endpoint=business_broker,
                launch=business,
                binding=binding,
                role=roles.BUSINESS_RESULT,
                deadline_ns=deadline,
            )
        )
        runtime_v2._send_exact_packet_and_half_close_v2(  # noqa: SLF001
            worker_broker,
            observations[2].frame.framed_bytes,
            deadline,
        )
        observations.extend(
            (
                runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                    endpoint=worker_broker,
                    launch=worker,
                    binding=binding,
                    role=roles.PARENT_OUTPUT,
                    deadline_ns=deadline,
                ),
                runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                    endpoint=worker_broker,
                    launch=worker,
                    binding=binding,
                    role=roles.WORKER_EOF,
                    deadline_ns=deadline,
                ),
            )
        )
        transcript = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=b"".join(item.frame.framed_bytes for item in observations),
            expected_binding=binding,
        )
        for pidfd, pid in (
            (worker_pidfd, worker_pid),
            (business_pidfd, business_pid),
        ):
            waited = os.waitid(atomic_v1.P_PIDFD, pidfd, os.WEXITED)
            assert waited.si_pid == pid
            assert waited.si_code == os.CLD_EXITED
            assert waited.si_status == 0
        role_rows = tuple(
            {
                "role": launch.role,
                "pid": launch.pid,
                "pidfd_identity": runtime_v2._identity_document(  # noqa: SLF001
                    launch.pidfd_identity
                ),
                "native_write_ahead_edge": 1,
                "setup_raw_sha256": launch.setup_raw_sha256,
                "setup_raw_byte_count": launch.setup_raw_byte_count,
                "authenticated_frame_ids": [
                    item.observation_id
                    for item in observations
                    if item.sender_pid == launch.pid
                ],
                "direct_pidfd_reaped": True,
                "exit_code": 0,
            }
            for launch in (worker, business)
        )
        peak_identity = runtime_v2._identity_document(  # noqa: SLF001
            runtime_v2._descriptor_identity(worker_pidfd)  # noqa: SLF001
        )
        output_identity = dict(peak_identity)
        output_identity["mode"] = stat.S_IFREG | 0o400
        envelope = runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2(
            runtime_v2._ENVELOPE_ISSUER,  # noqa: SLF001
            _id("runtime-prepared"),
            _id("runtime-resource"),
            _id("runtime-manifest"),
            _id("runtime-worker-authority"),
            _id("runtime-business-authority"),
            binding,
            role_rows,
            tuple(observations),
            transcript,
            result_id,
            hashlib.sha256(b"business").hexdigest(),
            len(b"business"),
            _id("runtime-operational-output"),
            hashlib.sha256(output_raw).hexdigest(),
            len(output_raw),
            output_identity,
            f"{runtime_v2.PROMOTED_OUTPUT_PREFIX}{_id('runtime-resource')}.json",
            4096,
            peak_identity,
            True,
            True,
        )
        document = envelope.to_document()
        assert document["frame_roles"] == list(runtime_v2.FRAME_ROLE_ORDER)
        assert document["authenticated_frame_count"] == 5
        assert document["direct_child_count"] == 2
        assert document["receipts"] is None
        assert document["counter_records"] is None
        assert document["durable_output_fixed_point_joined"] is False
        assert document["output_post_reap_write_bits_removed"] is True
    finally:
        worker_broker.close()
        business_broker.close()
        for pidfd in (worker_pidfd, business_pidfd):
            if pidfd >= 0:
                try:
                    os.close(pidfd)
                except OSError:
                    pass
        for pid in (worker_pid, business_pid):
            if pid > 0:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass


@pytest.mark.skipif(
    not hasattr(os, "pidfd_open"), reason="pidfd support is unavailable"
)
def test_authenticated_receive_rejects_wrong_first_role() -> None:
    binding = _binding("wrong-role")
    broker, child = _seqpacket_pair()
    pid = pidfd = -1
    try:
        pid = os.fork()
        if pid == 0:  # pragma: no cover - child outcome checked by parent
            broker.close()
            _child_send(
                child,
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST,
                    payload={"request_ordinal": 0},
                ),
            )
            child.close()
            os._exit(0)
        child.close()
        pidfd = os.pidfd_open(pid, 0)
        launch = _launch_row("WORKER", pid, pidfd)
        with pytest.raises(channel_v2.V075K7AuthenticatedBrokerChannelV2Error):
            runtime_v2._receive_authenticated_v2(  # noqa: SLF001
                endpoint=broker,
                launch=launch,
                binding=binding,
                role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
                deadline_ns=runtime_v2.time.monotonic_ns() + 5_000_000_000,
            )
        waited = os.waitid(atomic_v1.P_PIDFD, pidfd, os.WEXITED)
        assert waited.si_status == 0
    finally:
        broker.close()
        if pidfd >= 0:
            os.close(pidfd)
        if pid > 0:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass


def test_native_launch_seam_uses_write_ahead_cell_and_consumes_setup_eof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptors = [os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC) for _ in range(6)]
    executable, sealed, capability, pidfd, landlock, leaf = descriptors

    class Material:
        executable_fd = executable
        preexec_landlock_ruleset_fd = landlock
        preexec_seccomp_program_address = 12345

        def assert_current(self) -> None:
            return None

    def trampoline(pointer):
        launch = ctypes.cast(
            pointer,
            ctypes.POINTER(runtime_v2.probe_v1._NativeTwoRoleLaunchArgsV1),  # noqa: SLF001
        ).contents
        clone = atomic_v1.CloneArgsV1.from_address(launch.clone_args)
        ctypes.c_long.from_address(launch.clone_result_cell).value = 4321
        ctypes.c_int.from_address(clone.pidfd).value = pidfd
        ctypes.c_uint64.from_address(launch.role_edge_cell).value = 1
        os.write(
            launch.setup_status_fd,
            struct.pack(
                "<QQ",
                atomic_v1.K7AtomicPidfdSetupStageV1.READY_FOR_EXEC,
                0,
            ),
        )
        return 4321

    monkeypatch.setattr(
        runtime_v2.probe_v1,
        "_native_two_role_trampoline_v1",
        lambda: trampoline,
    )
    monkeypatch.setattr(
        runtime_v2.probe_v1,
        "_pidfd_matches_child_v1",
        lambda observed, pid: observed == pidfd and pid == 4321,
    )
    monkeypatch.setattr(runtime_v2.atomic_v1, "_thread_count", lambda: 1)
    cells = runtime_v2._RoleNativeCellsV2()  # noqa: SLF001
    try:
        outcome = runtime_v2._launch_production_role_v2(  # noqa: SLF001
            role="WORKER",
            leaf_fd=leaf,
            launch_record=(
                executable,
                (sealed,),
                (capability,),
                ("test-exec",),
                (("LANG", "C"),),
            ),
            sandbox_material=Material(),  # type: ignore[arg-type]
            native_cells=cells,
            deadline_ns=runtime_v2.time.monotonic_ns() + 5_000_000_000,
        )
        assert outcome.pid == 4321
        assert outcome.pidfd == pidfd
        assert outcome.native_edge == 1
        assert outcome.setup_raw_byte_count == 16
        assert cells.setup_read.value == -1
        assert all(not os.get_inheritable(fd) for fd in (executable, sealed, capability))
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_setup_status_and_relay_obey_one_absolute_deadline() -> None:
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        with pytest.raises(
            runtime_v2.V075K7ProductionBrokerRuntimeV2Error,
            match="timed out|deadline expired",
        ):
            runtime_v2._read_setup_status_until_v2(  # noqa: SLF001
                read_fd,
                runtime_v2.time.monotonic_ns() + 20_000_000,
            )
    finally:
        os.close(read_fd)
        os.close(write_fd)

    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        sender.setblocking(False)
        packet = b"x" * 4096
        while True:
            try:
                sender.send(packet)
            except BlockingIOError:
                break
        sender.setblocking(True)
        with pytest.raises(
            runtime_v2.V075K7ProductionBrokerRuntimeV2Error,
            match="timed out|deadline expired",
        ):
            runtime_v2._send_exact_packet_and_half_close_v2(  # noqa: SLF001
                sender,
                b"relay",
                runtime_v2.time.monotonic_ns() + 20_000_000,
            )
    finally:
        sender.close()
        receiver.close()


def test_cleanup_takes_and_retires_pinned_output_fd() -> None:
    descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    pinned = runtime_v2._PinnedOutputV2(  # noqa: SLF001
        descriptor,
        runtime_v2._descriptor_identity(descriptor),  # noqa: SLF001
        _id("pinned-cleanup-output"),
        b"raw",
    )
    cleanup = runtime_v2.K7ProductionBrokerRuntimeCleanupAuthorityV2(
        guardian=SimpleNamespace(),
        resource_session=SimpleNamespace(),
    )
    cleanup._take_pinned_output(pinned)  # noqa: SLF001
    cleanup._retire_launch_resources()  # noqa: SLF001
    assert cleanup._pinned_output_fd == -1  # noqa: SLF001
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_postreap_inode_pinned_output_replay_and_no_replace_promotion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = tempfile.TemporaryDirectory(dir="/tmp")
    parent = Path(temporary.name) / "parent"
    output = parent / "ephemeral"
    output.mkdir(parents=True)
    raw = canonical_json_bytes({"output": "wrapper"})
    (output / runtime_v2.worker_v1.OUTPUT_NAME).write_bytes(raw)
    (output / runtime_v2.worker_v1.OUTPUT_NAME).chmod(0o600)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    expected_id = _id("runtime-pinned-output")
    monkeypatch.setattr(
        runtime_v2.worker_v1,
        "verify_v075_k7_broker_operational_output_bytes_v1",
        lambda **kwargs: (
            SimpleNamespace(output_id=expected_id)
            if kwargs["raw"] == raw
            else (_ for _ in ()).throw(ValueError("crossed bytes"))
        ),
    )
    parent_frame = SimpleNamespace(
        frame=SimpleNamespace(
            payload={
                "output_byte_count": len(raw),
                "output_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    )
    try:
        pinned = runtime_v2._reread_operational_output_v2(  # noqa: SLF001
            output_directory_fd=output_fd,
            request_replay=object(),  # type: ignore[arg-type]
            binding=_binding("pinned-output"),
            parent_output=parent_frame,  # type: ignore[arg-type]
        )

        class Transfer:
            _guardian = SimpleNamespace(_output_parent_fd=parent_fd)

            def broker_descriptor(self, role: str) -> int:
                assert role == "OUTPUT_DIRECTORY"
                return output_fd

        promoted = runtime_v2._promote_output_v2(  # noqa: SLF001
            transfer=Transfer(),  # type: ignore[arg-type]
            pinned=pinned,
            resource_session_id=_id("runtime-output-resource"),
        )
        assert tuple(output.iterdir()) == ()
        assert (parent / promoted).read_bytes() == raw
        after = runtime_v2._descriptor_identity(pinned.descriptor)  # noqa: SLF001
        stable_identity_indices = (0, 1, 2, 3, 4, 5, 6, 7, 9, 10)
        assert tuple(after[index] for index in stable_identity_indices) == tuple(
            pinned.identity[index] for index in stable_identity_indices
        )
        assert os.pread(pinned.descriptor, len(raw), 0) == raw
        assert stat.S_IMODE(os.fstat(pinned.descriptor).st_mode) == 0o400
        os.close(pinned.descriptor)
    finally:
        os.close(output_fd)
        os.close(parent_fd)
        temporary.cleanup()


def test_output_extra_file_and_target_collision_fail_without_deleting_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = tempfile.TemporaryDirectory(dir="/tmp")
    parent = Path(temporary.name) / "parent"
    output = parent / "ephemeral"
    output.mkdir(parents=True)
    raw = b"preserve-me"
    (output / runtime_v2.worker_v1.OUTPUT_NAME).write_bytes(raw)
    (output / runtime_v2.worker_v1.OUTPUT_NAME).chmod(0o600)
    (output / "injected").write_bytes(b"attack")
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(runtime_v2.V075K7ProductionBrokerRuntimeV2Error):
            runtime_v2._reread_operational_output_v2(  # noqa: SLF001
                output_directory_fd=output_fd,
                request_replay=object(),  # type: ignore[arg-type]
                binding=_binding("extra-output"),
                parent_output=object(),  # type: ignore[arg-type]
            )
        assert (output / runtime_v2.worker_v1.OUTPUT_NAME).read_bytes() == raw
        assert (output / "injected").read_bytes() == b"attack"

        (output / "injected").unlink()
        monkeypatch.setattr(
            runtime_v2.worker_v1,
            "verify_v075_k7_broker_operational_output_bytes_v1",
            lambda **_kwargs: SimpleNamespace(output_id=_id("collision-output")),
        )
        frame = SimpleNamespace(
            frame=SimpleNamespace(
                payload={
                    "output_byte_count": len(raw),
                    "output_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        )
        pinned = runtime_v2._reread_operational_output_v2(  # noqa: SLF001
            output_directory_fd=output_fd,
            request_replay=object(),  # type: ignore[arg-type]
            binding=_binding("collision-output"),
            parent_output=frame,  # type: ignore[arg-type]
        )

        class Transfer:
            _guardian = SimpleNamespace(_output_parent_fd=parent_fd)

            def broker_descriptor(self, _role: str) -> int:
                return output_fd

        target = (
            runtime_v2.PROMOTED_OUTPUT_PREFIX
            + _id("collision-resource")
            + ".json"
        )
        (parent / target).write_bytes(b"existing")
        with pytest.raises(OSError):
            runtime_v2._promote_output_v2(  # noqa: SLF001
                transfer=Transfer(),  # type: ignore[arg-type]
                pinned=pinned,
                resource_session_id=_id("collision-resource"),
            )
        assert (output / runtime_v2.worker_v1.OUTPUT_NAME).read_bytes() == raw
        assert (parent / target).read_bytes() == b"existing"
        os.close(pinned.descriptor)
    finally:
        os.close(output_fd)
        os.close(parent_fd)
        temporary.cleanup()


def test_postrename_failure_retains_promoted_output_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = tempfile.TemporaryDirectory(dir="/tmp")
    parent = Path(temporary.name) / "parent"
    output = parent / "ephemeral"
    output.mkdir(parents=True)
    raw = b"sealed-promoted-output"
    source = output / runtime_v2.worker_v1.OUTPUT_NAME
    source.write_bytes(raw)
    source.chmod(0o400)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    pinned_fd = os.open(source, os.O_RDONLY | os.O_CLOEXEC)

    class Transfer:
        _guardian = SimpleNamespace(_output_parent_fd=parent_fd)

        def broker_descriptor(self, role: str) -> int:
            assert role == "OUTPUT_DIRECTORY"
            return output_fd

    transfer = Transfer()
    cleanup = runtime_v2.K7ProductionBrokerRuntimeCleanupAuthorityV2(
        guardian=SimpleNamespace(),
        resource_session=transfer,
    )
    cleanup._transfer = transfer  # noqa: SLF001
    pinned = runtime_v2._PinnedOutputV2(  # noqa: SLF001
        pinned_fd,
        runtime_v2._descriptor_identity(pinned_fd),  # noqa: SLF001
        _id("postrename-output"),
        raw,
    )
    monkeypatch.setattr(
        runtime_v2.os,
        "fsync",
        lambda _fd: (_ for _ in ()).throw(OSError("injected fsync failure")),
    )
    try:
        with pytest.raises(OSError, match="injected fsync failure"):
            runtime_v2._promote_output_v2(  # noqa: SLF001
                transfer=transfer,  # type: ignore[arg-type]
                pinned=pinned,
                resource_session_id=_id("postrename-resource"),
                on_renamed=cleanup._record_promoted_output,  # noqa: SLF001
            )
        assert cleanup.promoted_output_name is not None
        assert cleanup.output_preserved is True
        assert (parent / cleanup.promoted_output_name).read_bytes() == raw
        assert tuple(output.iterdir()) == ()
    finally:
        os.close(pinned_fd)
        os.close(output_fd)
        os.close(parent_fd)
        temporary.cleanup()


def test_public_boundary_rejects_caller_minted_inputs_before_consumption() -> None:
    with pytest.raises(
        runtime_v2.V075K7ProductionBrokerRuntimeV2Error,
        match="six exact issuer-owned inputs",
    ):
        runtime_v2.run_v075_k7_production_broker_runtime_v2(
            prepared_session=object(),  # type: ignore[arg-type]
            resource_session=object(),  # type: ignore[arg-type]
            worker_launch_authority=object(),  # type: ignore[arg-type]
            business_launch_authority=object(),  # type: ignore[arg-type]
            worker_sandbox_authority=object(),  # type: ignore[arg-type]
            business_sandbox_authority=object(),  # type: ignore[arg-type]
            deadline_milliseconds=1,
        )


def test_source_has_no_fork_popen_or_receipt_shortcut() -> None:
    source = inspect.getsource(runtime_v2)
    assert "os.fork(" not in source
    assert "subprocess" not in source
    assert "Popen" not in source
    assert source.count("CounterRecord") == 1  # explanatory docstring only
    for required in (
        "_native_two_role_trampoline_v1",
        "_receive_authenticated_v2",
        "_wait_pidfd",
        "_ancestor_kill",
        "_close_prelaunch_locked",
        "RENAME_NOREPLACE",
        "registered_eight_role_business_result_claimed",
    ):
        assert required in source


def _sealed_readonly(raw: bytes, label: str) -> int:
    writable = atomic_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw,
        name=label,
    )
    try:
        return os.open(
            f"/proc/self/fd/{writable}",
            os.O_RDONLY | os.O_CLOEXEC,
        )
    finally:
        os.close(writable)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_delegated_systemd_joined_production_broker_runtime(
    tmp_path: Path,
) -> None:
    if atomic_v1._thread_count() != 1:  # noqa: SLF001
        pytest.skip("positive clone3 path requires an exact single-thread parent")
    seed = hashlib.sha512(b"joined-runtime-generation").digest()
    salt = hashlib.sha512(b"joined-runtime-salt").digest()
    secret_raw = lifecycle._secret_raw_for_testing(  # noqa: SLF001
        generation_seed=seed,
        private_salt=salt,
    )
    request = _production_request("joined-runtime-real", secret_raw)
    private_root, private_key = _write_private_key(
        tmp_path,
        _key_document(_registry()),
    )
    output_parent = tmp_path / "joined-output"
    output_parent.mkdir(mode=0o700)
    owned_fds: set[int] = set()
    resource_session = None
    worker_sandbox = business_sandbox = None
    with _delegated_scope_parent_fd() as delegated_parent_fd:
        admission = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=delegated_parent_fd
        )
        token = outer_v1.official_v075_k7_outer_attempt_cgroup_nonce_service_v1().issue(
            request=request,
            admission_result=admission,
            delegated_parent_fd=delegated_parent_fd,
        )
        lease = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission,
            delegated_parent_fd=delegated_parent_fd,
            nonce_token=token,
        )
        prepared = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        manifest = manifest_v2.freeze_v075_k7_production_role_manifest_v2(
            request=request,
            repository_root=REPOSITORY_ROOT.resolve(),
            signer_private_root=private_root,
            signer_private_key_path=private_key,
        )
        worker_context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
            manifest=manifest,
            binding=prepared.binding,
            role=manifest_v2.K7ProductionBrokerRoleV2.WORKER,
        )
        business_context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
            manifest=manifest,
            binding=prepared.binding,
            role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
        )
        parent_fd = os.open(
            output_parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        try:
            resource_session = resource_v2.prepare_v075_k7_broker_resource_session_v2(
                manifest=manifest,
                worker_context=worker_context,
                business_context=business_context,
                output_parent_fd=parent_fd,
            )
        finally:
            os.close(parent_fd)
        expected_worker = launch_v2.derive_v075_k7_production_role_public_input_bytes_v2(
            manifest=manifest,
            launch_context=worker_context,
        )
        expected_business = launch_v2.derive_v075_k7_production_role_public_input_bytes_v2(
            manifest=manifest,
            launch_context=business_context,
        )
        worker_inputs = {
            name: _sealed_readonly(raw, f"joined-worker-{name.lower()}")
            for name, raw in expected_worker.items()
        }
        business_inputs = {
            name: _sealed_readonly(raw, f"joined-business-{name.lower()}")
            for name, raw in expected_business.items()
        }
        secret_fd = _sealed_readonly(secret_raw, "joined-secret")
        worker_executable = os.open(
            Path(os.sys.executable).resolve(strict=True),
            os.O_RDONLY | os.O_CLOEXEC,
        )
        business_executable = os.open(
            Path(os.sys.executable).resolve(strict=True),
            os.O_RDONLY | os.O_CLOEXEC,
        )
        owned_fds.update(
            (
                *worker_inputs.values(),
                *business_inputs.values(),
                secret_fd,
                worker_executable,
                business_executable,
            )
        )
        worker_launch = launch_v2.freeze_v075_k7_production_role_launch_authority_v2(
            manifest=manifest,
            launch_context=worker_context,
            capability_bundle=resource_session.worker_capabilities,
            public_sealed_input_fds=worker_inputs,
            interpreter_fd=worker_executable,
            repository_root=REPOSITORY_ROOT.resolve(),
        )
        business_launch = launch_v2.freeze_v075_k7_production_role_launch_authority_v2(
            manifest=manifest,
            launch_context=business_context,
            capability_bundle=resource_session.business_capabilities,
            public_sealed_input_fds=business_inputs,
            interpreter_fd=business_executable,
            repository_root=REPOSITORY_ROOT.resolve(),
            lifecycle_secret_fd=secret_fd,
            signer_private_root=private_root,
            signer_private_key_path=private_key,
        )
        worker_sandbox = sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
            role="WORKER",
            executable_fd=worker_executable,
            output_directory_fd=resource_session.worker_capabilities.descriptor(
                "OUTPUT_DIRECTORY"
            ),
        )
        business_sandbox = sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
            role="BUSINESS",
            executable_fd=business_executable,
        )
        envelope = runtime_v2.run_v075_k7_production_broker_runtime_v2(
            prepared_session=prepared,
            resource_session=resource_session,
            worker_launch_authority=worker_launch,
            business_launch_authority=business_launch,
            worker_sandbox_authority=worker_sandbox,
            business_sandbox_authority=business_sandbox,
            deadline_milliseconds=12 * 60 * 1000,
        )
    try:
        document = envelope.to_document()
        assert document["frame_roles"] == list(runtime_v2.FRAME_ROLE_ORDER)
        assert document["cgroup_cleanup_complete"] is True
        assert document["resource_cleanup_complete"] is True
        promoted = output_parent / document["promoted_output_name"]
        assert promoted.is_file()
        assert hashlib.sha256(promoted.read_bytes()).hexdigest() == document[
            "output_sha256"
        ]
    finally:
        if worker_sandbox is not None:
            worker_sandbox.close()
        if business_sandbox is not None:
            business_sandbox.close()
        for descriptor in owned_fds:
            try:
                os.close(descriptor)
            except OSError:
                pass
