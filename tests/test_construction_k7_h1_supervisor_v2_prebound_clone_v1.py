from __future__ import annotations

import copy
import ctypes
from dataclasses import FrozenInstanceError
import dis
import errno
import fcntl
import inspect
import json
import os
from pathlib import Path
import pickle
import signal
import socket
import subprocess
import sys
import threading
import shutil
from types import FunctionType

import pytest

from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as role_v2
from acfqp import construction_k7_h1_supervisor_v2_prebound_clone_v1 as binding


HELPER = Path(__file__).with_name("_supervisor_v2_prebound_clone_subprocess.py")


def _resources() -> tuple[int, socket.socket, int, int]:
    pid_cell = os.memfd_create(
        "acfqp-v20-test-pid-cell", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
    )
    os.ftruncate(pid_cell, 4096)
    parent, child = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    parent.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    child.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    child_fd = child.detach()
    role_fd = role_v2.create_sealed_nested_creator_supervisor_memfd_v2()
    return pid_cell, parent, child_fd, role_fd


def _prepare() -> tuple[
    binding.H1SupervisorV2PreboundNativeCloneV1,
    socket.socket,
    tuple[int, int, int],
]:
    pid_cell, parent, child_fd, role_fd = _resources()
    try:
        handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"ACFQP:V20:CELL",
            gate_ready_frame=b"ACFQP:V20:READY",
            release_frame=b"ACFQP:V20:RELEASE",
        )
    except BaseException:
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise
    return handle, parent, (pid_cell, child_fd, role_fd)


def test_surface_is_exact_preparation_only_and_exports_no_raw_accessor() -> None:
    assert binding.READINESS == (
        "BUILD_LOCAL_SOURCE_CLOSED_PREBOUND_NATIVE_EDGE_NO_ACTIVATION_NO_CLONE"
    )
    assert binding.ACTIVATION_SUCCESSOR_ISSUER_PRESENT is False
    assert binding.NATIVE_ENTRY_INVOKED is False
    assert binding.CLONE_SYSCALL_PERFORMED is False
    assert binding.OFFICIAL_EXECUTION_ALLOWED is False
    exports = set(binding.__all__)
    assert "execute_h1_supervisor_v2_prebound_native_clone_v1" in exports
    assert not any("fd" in name.lower() or "grant" in name.lower() for name in exports)


def test_prepare_verify_join_fields_and_cancel_retains_caller_inputs() -> None:
    handle, parent, descriptors = _prepare()
    try:
        document = binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert document["state"] == "PREBOUND_NO_ACTIVATION"
        assert len(document["prebound_native_edge_capsule_id"]) == 64
        assert len(document["prebound_native_edge_source_closure_id"]) == 64
        assert document["supervisor_v2_elf_sha256"] == role_v2.ELF_SHA256
        assert [row["role"] for row in document["fd_facts"]] == [
            "creator_pid_cell_fd",
            "child_gate_fd",
            "child_gate_peer_fd",
            "supervisor_executable_fd",
        ]
        assert document["source_fd_facts"] == document["fd_facts"]
        assert all(type(row["device"]) is int and type(row["inode"]) is int for row in document["fd_facts"])
        assert document["clone_args_template"]["flags"] == binding.REQUIRED_CLONE_FLAGS
        assert document["clone_args_template"]["cgroup"]["kind"] == "NOT_BOUND"
        assert document["raw_descriptor_accessor_present"] is False
        assert document["raw_native_callable_accessor_present"] is False
        assert document["external_expected_self_source_digest_present"] is False
        assert document["build_local_self_source_mutation_detection_present"] is True
        assert document["different_kernel_identity_reuse_left_open"] is True
        assert (
            document["same_open_file_description_fd_generation_reuse_detectable"]
            is False
        )
        assert document["same_process_private_fd_table_mutation_in_scope"] is False
        assert document["upstream_native_trampoline_unmapped"] is True
        assert document["input_ownership"] == {
            "caller_retains_original_descriptors": 4,
            "capsule_owns_f_dupfd_cloexec_duplicates": True,
            "duplicates_preserve_kernel_identity": True,
        }
        cancellation = binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(
            handle
        )
        assert cancellation["state_after"] == "CANCELLED_UNACTIVATED"
        assert cancellation["all_capsule_owned_resources_closed"] is True
        assert cancellation["permit_consumed"] is False
        assert cancellation["clone_syscall_performed"] is False
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
            == cancellation
        )
        for descriptor in descriptors:
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_public_execute_is_the_only_entry_and_fails_before_native_or_socket_activity() -> None:
    handle, parent, descriptors = _prepare()
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="activation successor issuer is absent",
        ):
            binding.execute_h1_supervisor_v2_prebound_native_clone_v1(
                handle, activation_successor=object()
            )
        document = binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert document["state"] == "PREBOUND_NO_ACTIVATION"
        assert document["native_entry_invoked"] is False
        assert document["clone_syscall_performed"] is False
        with pytest.raises(BlockingIOError):
            parent.recv(1, socket.MSG_DONTWAIT)
        assert os.pread(descriptors[0], 4097, 0) == bytes(4096)
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_documents_are_deep_copies_and_capsule_rejects_copy_pickle_and_forgery() -> None:
    handle, parent, descriptors = _prepare()
    try:
        first = binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        first["fd_facts"][0]["inode"] = -1
        second = binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert second["fd_facts"][0]["inode"] > 0
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            copy.copy(handle)
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            copy.deepcopy(handle)
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            pickle.dumps(handle)
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            binding.H1SupervisorV2PreboundNativeCloneV1()

        class Forged(binding.H1SupervisorV2PreboundNativeCloneV1):
            pass

        forged = object.__new__(Forged)
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(forged)  # type: ignore[arg-type]
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_wrong_thread_cannot_verify_or_cancel_owner_capsule() -> None:
    handle, parent, descriptors = _prepare()
    observed: list[str] = []

    def attack() -> None:
        for operation in (
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1,
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1,
        ):
            try:
                operation(handle)
            except binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error as error:
                observed.append(str(error))

    thread = threading.Thread(target=attack)
    thread.start()
    thread.join()
    try:
        assert len(observed) == 2
        assert all("owner process or thread" in row for row in observed)
        binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_fd_attacks_fail_closed_and_cancellation_preserves_caller_inputs() -> None:
    handle, parent, descriptors = _prepare()
    os.pwrite(descriptors[0], b"X", 17)
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="PID cell",
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="crossed capsule was closed",
        ) as captured:
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert captured.value.cleanup_document["all_capsule_owned_resources_closed"] is True
        for descriptor in descriptors:
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize(
    "attack",
    [
        "sealed_pid",
        "wrong_role",
        "queued_gate",
        "outbound_gate",
        "nonblocking_gate",
        "peer_shutdown_read",
    ],
)
def test_preparation_rejects_nonexact_fd_inputs(attack: str) -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    try:
        if attack == "sealed_pid":
            fcntl.fcntl(pid_cell, fcntl.F_ADD_SEALS, fcntl.F_SEAL_GROW)
        elif attack == "wrong_role":
            role_fd, old = pid_cell, role_fd
            os.close(old)
        elif attack == "queued_gate":
            parent.send(b"early")
        elif attack == "outbound_gate":
            temporary = socket.socket(fileno=child_fd)
            try:
                temporary.send(b"early-to-peer")
            finally:
                temporary.detach()
        elif attack == "nonblocking_gate":
            flags = fcntl.fcntl(child_fd, fcntl.F_GETFL)
            fcntl.fcntl(child_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        else:
            parent.shutdown(socket.SHUT_RD)
        with pytest.raises(binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
            binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
    finally:
        parent.close()
        for descriptor in {pid_cell, child_fd, role_fd}:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_live_code_global_rebinding_is_detected() -> None:
    handle, parent, descriptors = _prepare()
    original = binding._RAW_OS_FSTAT  # noqa: SLF001
    try:
        binding._RAW_OS_FSTAT = lambda _fd: None  # type: ignore[assignment]  # noqa: SLF001
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="static global identity changed",
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        binding._RAW_OS_FSTAT = original  # noqa: SLF001
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_fork_child_is_invalidated_while_parent_remains_live() -> None:
    completed = subprocess.run(
        [sys.executable, str(HELPER)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    document = json.loads(completed.stdout)
    assert document["child_outcome"] == "INVALIDATED"
    assert document["waited_pid_matches"] is True
    assert document["child_exit_status"] == 0
    assert document["parent_state"] == "PREBOUND_NO_ACTIVATION"
    assert len(document["parent_capsule_id"]) == 64
    assert document["caller_fds_live_after_cancel"] is True
    assert document["cancellation_closed"] is True


def test_authority_record_is_frozen_and_owner_is_document_bound() -> None:
    handle, parent, descriptors = _prepare()
    try:
        record = binding._LIVE[handle]  # noqa: SLF001
        with pytest.raises(FrozenInstanceError):
            record.owner_thread_id = -1  # type: ignore[misc]
        assert binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)[
            "owner_identity"
        ]["thread_id"] == threading.get_ident()
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize("attack", ["frame", "argv", "envp", "launch_pointer"])
def test_pointer_graph_pointee_mutations_fail_closed(attack: str) -> None:
    handle, parent, descriptors = _prepare()
    record = binding._LIVE[handle]  # noqa: SLF001
    if attack == "frame":
        record.cell_buffer.raw = b"X" * len(record.frames[0])
    elif attack == "argv":
        record.argv[0] = b"forged-argv"
    elif attack == "envp":
        record.envp[0] = b"FORGED=1"
    else:
        object.__setattr__(
            record,
            "launch_args_pointer",
            ctypes.pointer(binding._LAUNCH_ARGS_TYPE()),  # noqa: SLF001
        )
    try:
        with pytest.raises(
            (binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error, TypeError)
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error
        ) as captured:
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert captured.value.cleanup_document[
            "all_capsule_owned_resources_closed"
        ] is True
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_different_identity_fd_reuse_is_not_closed_by_finish_forward_cancellation() -> None:
    handle, parent, descriptors = _prepare()
    record = binding._LIVE[handle]  # noqa: SLF001
    victim = record.child_gate_fd
    os.close(victim)
    replacement = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    assert replacement == victim
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error
        ) as captured:
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        cleanup = captured.value.cleanup_document
        assert cleanup["different_kernel_identity_reused_descriptors_left_open"] is True
        assert fcntl.fcntl(replacement, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
            == cleanup
        )
    finally:
        os.close(replacement)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_forged_terminal_registry_entry_cannot_pop_live_or_leak_resources() -> None:
    handle, parent, descriptors = _prepare()
    record = binding._LIVE[handle]  # noqa: SLF001
    forged_bytes = binding._CANONICAL_JSON_BYTES(  # noqa: SLF001
        {
            "forged_terminal": True,
            "all_capsule_owned_resources_closed": True,
        }
    )
    forged = binding._TerminalCancellationRecordV1(  # noqa: SLF001
        issuer=binding._ISSUER,  # noqa: SLF001
        handle=handle,
        live_record=record,
        owner=binding._record_owner_tuple(record),  # noqa: SLF001
        document_bytes=forged_bytes,
        document_sha256=binding._RAW_SHA256(forged_bytes).hexdigest(),  # noqa: SLF001
        cancellation_id="0" * 64,
        parent_capsule_id=record.capsule_id,
        close_outcomes=(),
        input_integrity_valid_before_cleanup=False,
        historical_input_integrity_valid=False,
    )
    binding._TERMINAL[handle] = forged  # noqa: SLF001
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="terminal replay anchor is absent",
        ):
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert binding._LIVE[handle] is record  # noqa: SLF001
        assert record.creator_mapping.closed is False
        for _role, descriptor, _device, _inode, _mode in record.owned_fd_identities:
            os.fstat(descriptor)

        binding._TERMINAL.pop(handle)  # noqa: SLF001
        terminal = binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert terminal["all_capsule_owned_resources_closed"] is True
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
            == terminal
        )
    finally:
        binding._TERMINAL.pop(handle, None)  # noqa: SLF001
        if handle in binding._LIVE:  # noqa: SLF001
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_terminal_replay_rejects_document_mutation() -> None:
    handle, parent, descriptors = _prepare()
    try:
        terminal = binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        trusted = binding._TERMINAL[handle]  # noqa: SLF001
        original = trusted.document_bytes
        crossed = dict(terminal)
        crossed["unknown_injected_field"] = True
        object.__setattr__(
            trusted,
            "document_bytes",
            binding._CANONICAL_JSON_BYTES(crossed),  # noqa: SLF001
        )
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="authoritative document bytes changed|content ID changed|semantics changed",
        ):
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        object.__setattr__(trusted, "document_bytes", original)
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
            == terminal
        )
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize(
    "attack",
    ("source_unknown", "capsule_unknown", "capsule_claim_flip"),
)
def test_fully_resigned_live_documents_fail_exact_regeneration(
    attack: str,
) -> None:
    handle, parent, descriptors = _prepare()
    record = binding._LIVE[handle]  # noqa: SLF001
    original_source_bytes = record.source_document_bytes
    original_source_sha256 = record.source_document_sha256
    original_source_id = record.source_closure_id
    original_capsule_bytes = record.capsule_document_bytes
    original_capsule_sha256 = record.capsule_document_sha256
    original_capsule_id = record.capsule_id
    try:
        crossed_source = binding._LOADS_CANONICAL_JSON(  # noqa: SLF001
            original_source_bytes
        )
        crossed = binding._LOADS_CANONICAL_JSON(  # noqa: SLF001
            original_capsule_bytes
        )
        if attack == "source_unknown":
            crossed_source["unknown_resigned_source_field"] = "FORGED"
            source_payload = dict(crossed_source)
            source_payload.pop("prebound_native_edge_source_closure_id")
            crossed_source["prebound_native_edge_source_closure_id"] = (
                binding._local_domain_id(  # noqa: SLF001
                    binding.domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_SOURCE_CLOSURE_V1_DOMAIN,
                    source_payload,
                )
            )
            crossed["prebound_native_edge_source_closure_id"] = crossed_source[
                "prebound_native_edge_source_closure_id"
            ]
        elif attack == "capsule_unknown":
            crossed["unknown_resigned_capsule_field"] = "FORGED"
        else:
            crossed["raw_descriptor_accessor_present"] = True
        payload = dict(crossed)
        payload.pop("prebound_native_edge_capsule_id")
        crossed["prebound_native_edge_capsule_id"] = binding._local_domain_id(  # noqa: SLF001
            binding.domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CAPSULE_V1_DOMAIN,
            payload,
        )
        crossed_source_bytes = binding._CANONICAL_JSON_BYTES(  # noqa: SLF001
            crossed_source
        )
        crossed_capsule_bytes = binding._CANONICAL_JSON_BYTES(crossed)  # noqa: SLF001
        for name, value in (
            ("source_document_bytes", crossed_source_bytes),
            (
                "source_document_sha256",
                binding._RAW_SHA256(crossed_source_bytes).hexdigest(),  # noqa: SLF001
            ),
            (
                "source_closure_id",
                crossed_source["prebound_native_edge_source_closure_id"],
            ),
            ("capsule_document_bytes", crossed_capsule_bytes),
            (
                "capsule_document_sha256",
                binding._RAW_SHA256(crossed_capsule_bytes).hexdigest(),  # noqa: SLF001
            ),
            ("capsule_id", crossed["prebound_native_edge_capsule_id"]),
        ):
            object.__setattr__(record, name, value)
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="exact regenerated prebound document changed",
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        for name, value in (
            ("source_document_bytes", original_source_bytes),
            ("source_document_sha256", original_source_sha256),
            ("source_closure_id", original_source_id),
            ("capsule_document_bytes", original_capsule_bytes),
            ("capsule_document_sha256", original_capsule_sha256),
            ("capsule_id", original_capsule_id),
        ):
            object.__setattr__(record, name, value)
        if handle in binding._LIVE:  # noqa: SLF001
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_import_time_anchor_rejects_builder_and_registry_rebaseline() -> None:
    handle, parent, descriptors = _prepare()
    record = binding._LIVE[handle]  # noqa: SLF001
    original_builder = binding._capsule_document  # noqa: SLF001
    original_registry = binding._LOCAL_CALLABLES  # noqa: SLF001
    original_bytes = record.capsule_document_bytes
    original_sha256 = record.capsule_document_sha256
    original_id = record.capsule_id
    replacement = FunctionType(
        (lambda **_kwargs: {"forged": True}).__code__,
        binding.__dict__,
        name="_capsule_document",
    )
    try:
        binding._capsule_document = replacement  # type: ignore[assignment]  # noqa: SLF001
        binding._freeze_local_callable_closure()  # noqa: SLF001
        crossed = binding._LOADS_CANONICAL_JSON(original_bytes)  # noqa: SLF001
        crossed["raw_descriptor_accessor_present"] = True
        payload = dict(crossed)
        payload.pop("prebound_native_edge_capsule_id")
        crossed["prebound_native_edge_capsule_id"] = binding._local_domain_id(  # noqa: SLF001
            binding.domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CAPSULE_V1_DOMAIN,
            payload,
        )
        crossed_bytes = binding._CANONICAL_JSON_BYTES(crossed)  # noqa: SLF001
        object.__setattr__(record, "capsule_document_bytes", crossed_bytes)
        object.__setattr__(
            record,
            "capsule_document_sha256",
            binding._RAW_SHA256(crossed_bytes).hexdigest(),  # noqa: SLF001
        )
        object.__setattr__(
            record,
            "capsule_id",
            crossed["prebound_native_edge_capsule_id"],
        )
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="import-time expectation registry changed",
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        binding._capsule_document = original_builder  # noqa: SLF001
        binding._LOCAL_CALLABLES = original_registry  # noqa: SLF001
        object.__setattr__(record, "capsule_document_bytes", original_bytes)
        object.__setattr__(record, "capsule_document_sha256", original_sha256)
        object.__setattr__(record, "capsule_id", original_id)
        if handle in binding._LIVE:  # noqa: SLF001
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize(
    "attack",
    (
        "close_row_unknown",
        "descriptor_closed_flip",
        "historical_integrity_flip",
        "historical_integrity_rebind",
        "parent_capsule_rebind",
        "close_outcome_rebind",
        "all_terminal_copies_rebind",
    ),
)
def test_fully_resigned_terminal_documents_fail_exact_regeneration(
    attack: str,
) -> None:
    handle, parent, descriptors = _prepare()
    try:
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        terminal = binding._TERMINAL[handle]  # noqa: SLF001
        original_terminal_bytes = terminal.document_bytes
        original_terminal_sha256 = terminal.document_sha256
        original_cancellation_id = terminal.cancellation_id
        original_record_capsule_id = terminal.live_record.capsule_id
        original_parent_capsule_id = terminal.parent_capsule_id
        original_input_integrity = terminal.input_integrity_valid_before_cleanup
        original_historical_integrity = terminal.historical_input_integrity_valid
        original_close_outcomes = terminal.close_outcomes
        crossed_terminal = binding._LOADS_CANONICAL_JSON(  # noqa: SLF001
            original_terminal_bytes
        )
        if attack == "close_row_unknown":
            crossed_terminal["close_rows"][0]["unknown_resigned_field"] = True
        elif attack == "descriptor_closed_flip":
            crossed_terminal["close_rows"][0]["descriptor_closed_by_module"] = (
                not crossed_terminal["close_rows"][0][
                    "descriptor_closed_by_module"
                ]
            )
        elif attack in {
            "historical_integrity_flip",
            "historical_integrity_rebind",
        }:
            crossed_terminal["input_integrity_valid_before_cleanup"] = (
                not crossed_terminal["input_integrity_valid_before_cleanup"]
            )
            if attack == "historical_integrity_rebind":
                object.__setattr__(
                    terminal,
                    "input_integrity_valid_before_cleanup",
                    not original_input_integrity,
                )
        elif attack == "parent_capsule_rebind":
            forged_parent = "f" * 64
            assert forged_parent != terminal.parent_capsule_id
            object.__setattr__(terminal.live_record, "capsule_id", forged_parent)
            crossed_terminal["prebound_native_edge_capsule_id"] = forged_parent
        elif attack == "close_outcome_rebind":
            crossed_terminal["close_rows"][0] = {
                "role": "creator_pid_cell_mapping",
                "capsule_owned_resource_closed_or_absent": True,
                "closed": True,
                "descriptor_closed_by_module": False,
                "already_absent": True,
            }
            rebound_outcomes = list(terminal.close_outcomes)
            rebound_outcomes[0] = binding._CloseOutcomeV1(  # noqa: SLF001
                "creator_pid_cell_mapping",
                "ALREADY_ABSENT",
            )
            object.__setattr__(terminal, "close_outcomes", tuple(rebound_outcomes))
        else:
            forged_parent = "f" * 64
            assert forged_parent != terminal.parent_capsule_id
            object.__setattr__(terminal.live_record, "capsule_id", forged_parent)
            object.__setattr__(terminal, "parent_capsule_id", forged_parent)
            object.__setattr__(
                terminal,
                "input_integrity_valid_before_cleanup",
                not original_input_integrity,
            )
            object.__setattr__(
                terminal,
                "historical_input_integrity_valid",
                not original_historical_integrity,
            )
            crossed_terminal["prebound_native_edge_capsule_id"] = forged_parent
            crossed_terminal["input_integrity_valid_before_cleanup"] = (
                not crossed_terminal["input_integrity_valid_before_cleanup"]
            )
        terminal_payload = dict(crossed_terminal)
        terminal_payload.pop("prebound_native_edge_cancellation_id")
        crossed_terminal["prebound_native_edge_cancellation_id"] = (
            binding._local_domain_id(  # noqa: SLF001
                binding.domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CANCELLATION_V1_DOMAIN,
                terminal_payload,
            )
        )
        crossed_terminal_bytes = binding._CANONICAL_JSON_BYTES(  # noqa: SLF001
            crossed_terminal
        )
        object.__setattr__(terminal, "document_bytes", crossed_terminal_bytes)
        object.__setattr__(
            terminal,
            "document_sha256",
            binding._RAW_SHA256(crossed_terminal_bytes).hexdigest(),  # noqa: SLF001
        )
        object.__setattr__(
            terminal,
            "cancellation_id",
            crossed_terminal["prebound_native_edge_cancellation_id"],
        )
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match=(
                "terminal parent capsule anchor changed|"
                "terminal historical input-integrity anchor changed|"
                "terminal cancellation replay found|"
                "terminal cancellation semantics changed"
            ),
        ):
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        object.__setattr__(
            terminal.live_record,
            "capsule_id",
            original_record_capsule_id,
        )
        object.__setattr__(
            terminal,
            "input_integrity_valid_before_cleanup",
            original_input_integrity,
        )
        object.__setattr__(
            terminal,
            "historical_input_integrity_valid",
            original_historical_integrity,
        )
        object.__setattr__(
            terminal,
            "parent_capsule_id",
            original_parent_capsule_id,
        )
        object.__setattr__(terminal, "close_outcomes", original_close_outcomes)
        object.__setattr__(terminal, "document_bytes", original_terminal_bytes)
        object.__setattr__(terminal, "document_sha256", original_terminal_sha256)
        object.__setattr__(terminal, "cancellation_id", original_cancellation_id)
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)[
                "prebound_native_edge_cancellation_id"
            ]
            == terminal.cancellation_id
        )
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize(
    "site",
    ("pair_child", "pair_peer", "queue_child"),
)
def test_interrupted_owned_socket_wrapper_adoption_preserves_borrowed_fds(
    site: str,
) -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    before_fds = set(os.listdir("/proc/self/fd"))
    before_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    target_fd = child_fd
    caller_code = (
        binding._socket_queue_is_empty.__code__  # noqa: SLF001
        if site == "queue_child"
        else binding._socket_pair_facts.__code__  # noqa: SLF001
    )
    fired = False

    def interrupt_after_owned_wrapper(frame: object, event: str, _arg: object) -> object:
        nonlocal fired
        local_values = getattr(frame, "f_locals")
        pair_child_ready = (
            site == "pair_child"
            and local_values.get("child") is not None
            and local_values.get("peer") is None
        )
        pair_peer_ready = (
            site == "pair_peer"
            and local_values.get("child") is not None
            and local_values.get("peer") is not None
            and "endpoints" not in local_values
        )
        queue_ready = (
            site == "queue_child"
            and local_values.get("descriptor") == target_fd
            and local_values.get("endpoint") is not None
        )
        if (
            not fired
            and event == "line"
            and getattr(frame, "f_code", None) is caller_code
            and (pair_child_ready or pair_peer_ready or queue_ready)
        ):
            fired = True
            raise KeyboardInterrupt(f"injected after {site} owned wrapper adoption")
        return interrupt_after_owned_wrapper

    sys.settrace(interrupt_after_owned_wrapper)
    try:
        with pytest.raises(KeyboardInterrupt, match="owned wrapper adoption"):
            binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
    finally:
        sys.settrace(None)
    child = socket.socket(fileno=child_fd)
    try:
        assert fired is True
        assert set(os.listdir("/proc/self/fd")) == before_fds
        assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == before_signal_mask
        for descriptor in (pid_cell, child_fd, parent.fileno(), role_fd):
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert binding._socket_queue_is_empty(parent.fileno())  # noqa: SLF001
        assert binding._socket_queue_is_empty(child_fd)  # noqa: SLF001
        assert not binding._LIVE  # noqa: SLF001
        assert not binding._PRECOMMIT  # noqa: SLF001
        handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"A",
            gate_ready_frame=b"B",
            release_frame=b"C",
        )
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        child.detach()
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_dup_call_to_store_opcode_seam_is_untraceable_and_leak_free() -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    before_fds = set(os.listdir("/proc/self/fd"))
    before_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    instructions = list(
        dis.get_instructions(binding._owned_socket_inspection_duplicate)  # noqa: SLF001
    )
    duplicate_store_offset = next(
        instruction.offset
        for index, instruction in enumerate(instructions)
        if instruction.opname == "STORE_FAST"
        and instruction.argval == "duplicate_fd"
        and index > 0
        and instructions[index - 1].opname.startswith("CALL")
    )
    helper_calls = 0
    seam_seen = False

    def interrupt_at_raw_dup_store(frame: object, event: str, _arg: object) -> object:
        nonlocal helper_calls, seam_seen
        if (
            event == "call"
            and getattr(frame, "f_code", None)
            is binding._owned_socket_inspection_duplicate.__code__  # noqa: SLF001
        ):
            helper_calls += 1
            setattr(frame, "f_trace_opcodes", True)
        elif (
            event == "opcode"
            and getattr(frame, "f_code", None)
            is binding._owned_socket_inspection_duplicate.__code__  # noqa: SLF001
            and getattr(frame, "f_lasti", None) == duplicate_store_offset
        ):
            seam_seen = True
            raise KeyboardInterrupt("raw duplicate reached CALL-to-STORE trace seam")
        return interrupt_at_raw_dup_store

    sys.settrace(interrupt_at_raw_dup_store)
    try:
        handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"A",
            gate_ready_frame=b"B",
            release_frame=b"C",
        )
    finally:
        sys.settrace(None)
    try:
        assert helper_calls >= 3
        assert seam_seen is False
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        assert set(os.listdir("/proc/self/fd")) == before_fds
        assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == before_signal_mask
    finally:
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            os.close(descriptor)


@pytest.mark.parametrize(
    "probe_payload",
    (
        binding._PAIR_PROBE_CHILD_TO_PEER,  # noqa: SLF001
        binding._PAIR_PROBE_PEER_TO_CHILD,  # noqa: SLF001
    ),
)
def test_interrupted_pair_probe_restores_borrowed_queues_and_allows_retry(
    probe_payload: bytes,
) -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    fired = False

    def interrupt_after_probe_send(frame: object, event: str, _arg: object) -> object:
        nonlocal fired
        if (
            not fired
            and event == "line"
            and getattr(frame, "f_code", None)
            is binding._round_trip_pair_probe.__code__  # noqa: SLF001
            and getattr(frame, "f_locals").get("payload") == probe_payload
            and getattr(frame, "f_locals").get("send_completed") is True
            and getattr(frame, "f_locals").get("receive_completed") is False
        ):
            fired = True
            raise KeyboardInterrupt("injected after pair-probe send")
        return interrupt_after_probe_send

    sys.settrace(interrupt_after_probe_send)
    try:
        with pytest.raises(KeyboardInterrupt, match="after pair-probe send"):
            binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
    finally:
        sys.settrace(None)
    child = socket.socket(fileno=child_fd)
    try:
        assert fired is True
        assert binding._socket_queue_is_empty(parent.fileno())  # noqa: SLF001
        assert binding._socket_queue_is_empty(child_fd)  # noqa: SLF001
        assert not binding._LIVE  # noqa: SLF001
        assert not binding._PRECOMMIT  # noqa: SLF001
        handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"A",
            gate_ready_frame=b"B",
            release_frame=b"C",
        )
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        child.detach()
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_live_hashlib_rebinding_is_detected_before_replay() -> None:
    handle, parent, descriptors = _prepare()
    original = binding.hashlib.sha256
    try:
        binding.hashlib.sha256 = lambda raw=b"": original(raw)  # type: ignore[assignment]
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="hash primitive",
        ):
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        binding.hashlib.sha256 = original  # type: ignore[assignment]
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_prepare_registry_commit_is_interrupt_atomic_and_closes_private_fds() -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    before = set(os.listdir("/proc/self/fd"))
    source_lines, source_start = inspect.getsourcelines(
        binding.prepare_h1_supervisor_v2_prebound_native_clone_v1
    )
    insertion_index = next(
        index for index, line in enumerate(source_lines) if "_LIVE[handle] = record" in line
    )
    target_index = next(
        index
        for index in range(insertion_index + 1, len(source_lines))
        if "_PRECOMMIT.pop(token" in source_lines[index]
    )
    target_line = source_start + target_index

    def interrupt_after_commit(frame: object, event: str, _arg: object) -> object:
        if (
            getattr(frame, "f_code", None)
            is binding.prepare_h1_supervisor_v2_prebound_native_clone_v1.__code__
            and event == "line"
            and getattr(frame, "f_lineno", None) == target_line
        ):
            sys.settrace(None)
            raise KeyboardInterrupt("injected after live-registry commit")
        return interrupt_after_commit

    sys.settrace(interrupt_after_commit)
    try:
        with pytest.raises(KeyboardInterrupt):
            binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
    finally:
        sys.settrace(None)
    try:
        assert not binding._LIVE  # noqa: SLF001
        assert not binding._PRECOMMIT  # noqa: SLF001
        assert not binding._CLOSING  # noqa: SLF001
        assert set(os.listdir("/proc/self/fd")) == before
    finally:
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            os.close(descriptor)


def test_double_interrupt_precommit_cleanup_is_tracked_and_next_prepare_recovers() -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    original_close = binding._RAW_OS_CLOSE  # noqa: SLF001
    close_calls = 0

    def close_then_interrupt(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        original_close(descriptor)
        if close_calls == 1:
            raise KeyboardInterrupt("injected during failed-precommit cleanup")

    source_lines, source_start = inspect.getsourcelines(
        binding.prepare_h1_supervisor_v2_prebound_native_clone_v1
    )
    target_line = source_start + next(
        index
        for index, line in enumerate(source_lines)
        if "_verify_record(record)" in line
    )

    def fail_after_resources(frame: object, event: str, _arg: object) -> object:
        if (
            getattr(frame, "f_code", None)
            is binding.prepare_h1_supervisor_v2_prebound_native_clone_v1.__code__
            and event == "line"
            and getattr(frame, "f_lineno", None) == target_line
        ):
            binding._RAW_OS_CLOSE = close_then_interrupt  # type: ignore[assignment]  # noqa: SLF001
            raise RuntimeError("injected primary after private resources")
        return fail_after_resources

    sys.settrace(fail_after_resources)
    try:
        with pytest.raises(KeyboardInterrupt, match="failed-precommit cleanup"):
            binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
    finally:
        sys.settrace(None)
        binding._RAW_OS_CLOSE = original_close  # type: ignore[assignment]  # noqa: SLF001
    try:
        assert len(binding._PRECOMMIT) == 1  # noqa: SLF001
        assert binding._LIVE == {}  # noqa: SLF001
        recovered = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"D",
            gate_ready_frame=b"E",
            release_frame=b"F",
        )
        assert binding._PRECOMMIT == {}  # noqa: SLF001
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(recovered)
    finally:
        for descriptor in (pid_cell, child_fd, role_fd):
            os.close(descriptor)
        parent.close()


def test_fork_during_precommit_closes_child_private_fd_only() -> None:
    pid_cell, parent, child_fd, role_fd = _resources()
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    source_lines, source_start = inspect.getsourcelines(
        binding.prepare_h1_supervisor_v2_prebound_native_clone_v1
    )
    target_index = next(
        index
        for index, line in enumerate(source_lines)
        if "owned_child_gate_fd = _duplicate_into_pending" in line
    )
    target_line = source_start + target_index
    child_pids: list[int] = []

    def fork_after_first_private_fd(frame: object, event: str, _arg: object) -> object:
        if (
            not child_pids
            and getattr(frame, "f_code", None)
            is binding.prepare_h1_supervisor_v2_prebound_native_clone_v1.__code__
            and event == "line"
            and getattr(frame, "f_lineno", None) == target_line
        ):
            sys.settrace(None)
            private_fd = int(getattr(frame, "f_locals")["owned_pid_cell_fd"])
            child_pid = os.fork()
            if child_pid == 0:
                os.close(read_fd)
                try:
                    fcntl.fcntl(private_fd, fcntl.F_GETFD)
                except OSError as error:
                    private_closed = error.errno == errno.EBADF
                else:
                    private_closed = False
                caller_live = bool(
                    fcntl.fcntl(pid_cell, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
                )
                os.write(
                    write_fd,
                    json.dumps(
                        {
                            "private_closed": private_closed,
                            "caller_live": caller_live,
                            "precommit_empty": not binding._PRECOMMIT,  # noqa: SLF001
                        }
                    ).encode("ascii"),
                )
                os.close(write_fd)
                os._exit(0)
            child_pids.append(child_pid)
        return fork_after_first_private_fd

    sys.settrace(fork_after_first_private_fd)
    try:
        handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child_fd,
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"A",
            gate_ready_frame=b"B",
            release_frame=b"C",
        )
    finally:
        sys.settrace(None)
    os.close(write_fd)
    child_document = json.loads(os.read(read_fd, 1024).decode("ascii"))
    os.close(read_fd)
    waited, status = os.waitpid(child_pids[0], 0)
    try:
        assert waited == child_pids[0]
        assert os.waitstatus_to_exitcode(status) == 0
        assert child_document == {
            "private_closed": True,
            "caller_live": True,
            "precommit_empty": True,
        }
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            os.close(descriptor)


def test_interrupted_cleanup_is_finish_forward_and_terminal_replayable() -> None:
    handle, parent, descriptors = _prepare()
    original = binding._identity_safe_close_row  # noqa: SLF001
    injected = False

    def close_then_interrupt(identity: object) -> dict[str, object]:
        nonlocal injected
        row = original(identity)  # type: ignore[arg-type]
        if not injected:
            injected = True
            raise KeyboardInterrupt("injected after one identity-safe close")
        return row

    binding._identity_safe_close_row = close_then_interrupt  # type: ignore[assignment]  # noqa: SLF001
    try:
        with pytest.raises(KeyboardInterrupt):
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
    finally:
        binding._identity_safe_close_row = original  # noqa: SLF001
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error
        ) as captured:
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        terminal = captured.value.cleanup_document
        assert terminal["all_capsule_owned_resources_closed"] is True
        assert (
            binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
            == terminal
        )
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


def test_domain_encoder_rebinding_before_issuance_is_rejected() -> None:
    handle = None
    pid_cell, parent, child_fd, role_fd = _resources()
    original = binding.domains_v20.canonical_json_bytes
    binding.domains_v20.canonical_json_bytes = lambda _payload: b"COLLAPSED"  # type: ignore[assignment]
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="domain global identity changed",
        ):
            handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                creator_pid_cell_fd=pid_cell,
                child_gate_fd=child_fd,
                child_gate_peer_fd=parent.fileno(),
                supervisor_executable_fd=role_fd,
                cell_withdrawn_frame=b"A",
                gate_ready_frame=b"B",
                release_frame=b"C",
            )
        assert handle is None
        assert not binding._PRECOMMIT  # noqa: SLF001
    finally:
        binding.domains_v20.canonical_json_bytes = original
        parent.close()
        for descriptor in (pid_cell, child_fd, role_fd):
            os.close(descriptor)


def test_execute_is_source_level_unconditional_failure_even_if_helpers_rebound() -> None:
    handle, parent, descriptors = _prepare()
    original_verify = binding._verify_record  # noqa: SLF001
    original_fail = binding._fail  # noqa: SLF001
    binding._verify_record = lambda _record: {}  # type: ignore[assignment]  # noqa: SLF001
    binding._fail = lambda _message: None  # type: ignore[assignment]  # noqa: SLF001
    try:
        with pytest.raises(
            binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error,
            match="activation successor issuer is absent",
        ):
            binding.execute_h1_supervisor_v2_prebound_native_clone_v1(
                handle, activation_successor=object()
            )
    finally:
        binding._verify_record = original_verify  # noqa: SLF001
        binding._fail = original_fail  # noqa: SLF001
        binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(handle)
        for descriptor in descriptors:
            os.close(descriptor)
        parent.close()


@pytest.mark.parametrize("mode", ["rx-preload", "source-mutation"])
def test_subprocess_rejects_preloaded_rx_and_post_import_source_mutation(
    mode: str, tmp_path: Path
) -> None:
    environment = dict(os.environ)
    if mode == "source-mutation":
        copied_root = tmp_path / "copy"
        copied_package = copied_root / "acfqp"
        copied_package.mkdir(parents=True)
        (copied_package / "__init__.py").write_text(
            "from pkgutil import extend_path\n__path__ = extend_path(__path__, __name__)\n",
            encoding="utf-8",
        )
        shutil.copy2(
            Path(binding.__file__).resolve(strict=True),
            copied_package / Path(binding.__file__).name,
        )
        project_src = Path(__file__).resolve().parents[1] / "src"
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(copied_root), str(project_src))
        )
    completed = subprocess.run(
        [sys.executable, str(HELPER), mode],
        cwd=tmp_path if mode == "source-mutation" else Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )
    document = json.loads(completed.stdout)
    assert document["outcome"] == "REJECTED_BEFORE_CAPSULE"
    assert document["live_registry_empty"] is True
    assert document["caller_fds_remained_live"] is True
