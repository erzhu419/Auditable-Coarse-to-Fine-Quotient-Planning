from __future__ import annotations

import ast
import copy
from dataclasses import replace
import errno
import fcntl
import linecache
import os
from pathlib import Path
import pickle
import signal
import socket
import sys
import threading
import types

import pytest

from acfqp import construction_k7_h1_lease_bound_three_birth_runtime_v1 as v19


HANDOFF = {
    "guardian_runtime_v2_public_handoff_id": "1" * 64,
    "h1_e5a_runtime_lease_successor_id": "2" * 64,
    "handoff_state": "HANDOFF_ESCROWED_UNCONSUMED",
}


class _Cancellation:
    def __init__(self) -> None:
        self._document = {
            "guardian_runtime_v2_cancellation_id": "3" * 64,
            "terminal_code": "UNCONSUMED_HANDOFF_CANCELLED",
            "process_birth_count": 0,
        }

    def to_document(self) -> dict[str, object]:
        return dict(self._document)


class _DocumentObject:
    def __init__(self, document: dict[str, object]) -> None:
        self._document = document
        self.adapter_id = document.get("guardian_runtime_v2_consumer_adapter_id")

    def to_document(self) -> dict[str, object]:
        return dict(self._document)


def _install_fake_guardian(monkeypatch: pytest.MonkeyPatch) -> object:
    handoff = object()
    adapter_document = v19._with_id(  # noqa: SLF001
        {
            "schema": "acfqp.k7_h1_guardian_runtime_v2_consumer_adapter.v1",
            "adapter_state": "REGISTERED_PREPARATION_ONLY",
        },
        domain=v19.domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
        id_field="guardian_runtime_v2_consumer_adapter_id",
    )
    adapter = _DocumentObject(adapter_document)
    monkeypatch.setattr(v19.guardian_v2, "_V19_TEST_HANDOFF", handoff, raising=False)
    monkeypatch.setattr(v19.guardian_v2, "_V19_TEST_ADAPTER", adapter, raising=False)
    monkeypatch.setattr(v19.guardian_v2, "HANDOFF", HANDOFF, raising=False)
    monkeypatch.setattr(v19.guardian_v2, "v19", v19, raising=False)
    monkeypatch.setattr(
        v19.guardian_v2, "_DocumentObject", _DocumentObject, raising=False
    )
    monkeypatch.setattr(
        v19.guardian_v2, "_Cancellation", _Cancellation, raising=False
    )

    def module_owned(function):
        return types.FunctionType(
            function.__code__, v19.guardian_v2.__dict__, function.__name__
        )

    def verify_handoff(candidate):
        return dict(HANDOFF) if candidate is _V19_TEST_HANDOFF else None

    def register(**_kwargs):
        return _V19_TEST_ADAPTER

    def prepare(candidate, **kwargs):
        assert candidate is _V19_TEST_HANDOFF
        assert kwargs["adapter"] is _V19_TEST_ADAPTER
        document = v19._with_id(  # noqa: SLF001
            {
                "schema": "acfqp.k7_h1_guardian_runtime_v2_takeover_preparation.v1",
                "guardian_runtime_v2_public_handoff_id": HANDOFF[
                    "guardian_runtime_v2_public_handoff_id"
                ],
                "guardian_runtime_v2_consumer_adapter_id": _V19_TEST_ADAPTER.adapter_id,
                "consumer_preparation_id": kwargs["consumer_preparation_id"],
                "launch_preparation_id": kwargs["launch_preparation_id"],
                "takeover_state": "PREPARED_UNCONSUMED_NONLAUNCHABLE",
            },
            domain=getattr(
                v19.domains_v19,
                "CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_TAKEOVER_PREPARATION_V1_DOMAIN",
            ),
            id_field="guardian_runtime_v2_takeover_preparation_id",
        )
        return _DocumentObject(document)

    def cancel_handoff(candidate):
        return _Cancellation() if candidate is _V19_TEST_HANDOFF else None

    def cancel_takeover(_candidate):
        return _Cancellation()

    def verify_cancellation(candidate):
        return candidate.to_document()

    monkeypatch.setattr(
        v19.guardian_v2,
        "verify_h1_guardian_runtime_permit_handoff_v2",
        module_owned(verify_handoff),
    )
    monkeypatch.setattr(
        v19.guardian_v2,
        "register_h1_guardian_runtime_consumer_adapter_v2",
        module_owned(register),
    )
    monkeypatch.setattr(
        v19.guardian_v2,
        "prepare_h1_guardian_runtime_consumer_takeover_v2",
        module_owned(prepare),
    )
    monkeypatch.setattr(
        v19.guardian_v2,
        "cancel_h1_guardian_runtime_permit_handoff_v2",
        module_owned(cancel_handoff),
    )
    monkeypatch.setattr(
        v19.guardian_v2,
        "cancel_h1_guardian_runtime_prepared_takeover_v2",
        module_owned(cancel_takeover),
    )
    monkeypatch.setattr(
        v19.guardian_v2,
        "verify_h1_guardian_runtime_cancellation_v2",
        module_owned(verify_cancellation),
    )
    pinned = dict(v19._UPSTREAM_CALLABLES)  # noqa: SLF001
    for name in (
        "verify_h1_guardian_runtime_permit_handoff_v2",
        "register_h1_guardian_runtime_consumer_adapter_v2",
        "prepare_h1_guardian_runtime_consumer_takeover_v2",
        "cancel_h1_guardian_runtime_prepared_takeover_v2",
        "cancel_h1_guardian_runtime_permit_handoff_v2",
        "verify_h1_guardian_runtime_cancellation_v2",
    ):
        function = getattr(v19.guardian_v2, name)
        pinned[("guardian", name)] = (function, function.__code__)
    monkeypatch.setattr(v19, "_UPSTREAM_CALLABLES", types.MappingProxyType(pinned))
    return handoff


def test_surface_is_source_closed_and_non_authoritative() -> None:
    evidence = v19.verify_lease_bound_three_birth_runtime_surface_v1()
    assert evidence["readiness"] == v19.READINESS
    assert len(evidence["source_digests"]) == 10
    assert evidence["public_prebound_capsule_binding_seam_present"] is True
    assert evidence["prebound_capsule_duplicate_owns_inputs"] is True
    assert evidence["raw_descriptor_accessor_present"] is False
    assert evidence["b2c_private_api_imported_or_used"] is False
    assert evidence["guardian_public_seam"]["preparation_complete"] is True
    assert evidence["guardian_public_seam"]["activation_complete"] is False
    assert evidence["clone_syscall_performed"] is False
    assert evidence["memory_peak_read_count"] == 0
    assert evidence["three_birth_prefix_authority_present"] is False
    assert evidence["formal_v7_authority_present"] is False
    assert evidence["official_execution_allowed"] is False


def test_module_imports_no_b2c_or_frozen_guardian_v1() -> None:
    source = Path(v19.__file__).read_text(encoding="utf-8")
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
    assert not any("actual_observed_supervisor_birth_v1" in name for name in imported)
    assert not any("guardian_runtime_genesis_v1" in name for name in imported)
    assert "._LIVE_HANDOFFS" not in source
    assert "._RUNTIME_RESERVATIONS" not in source
    assert "._fd_slots" not in source


def test_public_seam_status_never_accepts_unexported_callables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = v19.REQUIRED_GUARDIAN_ACTIVATION_SEAM[0]
    monkeypatch.setattr(v19.guardian_v2, name, lambda: None, raising=False)
    status = v19.guardian_public_consumer_seam_status_v1()
    row = next(row for row in status["activation_rows"] if row["name"] == name)
    assert row["callable"] is True
    assert row["exported"] is False
    assert row["owned_by_guardian_v2"] is False
    assert status["activation_complete"] is False


def test_preparation_freezes_eight_fds_and_three_durable_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(
        handoff, journal_path=tmp_path
    )
    try:
        verified = v19.verify_lease_bound_three_birth_preparation_v1(handle)
        assert handle.state == "DURABLE_PREPARED_AWAITING_PUBLIC_ATOMIC_TAKEOVER"
        assert verified["descriptor_count"] == 8
        assert verified["clone_syscall_performed"] is False
        assert verified["memory_peak_read_count"] == 0
        assert list(sorted(path.name for path in tmp_path.iterdir())) == [
            "0001_CONSUMER_ADAPTER.json",
            "0002_LAUNCH_PREPARATION.json",
            "0003_TAKEOVER_PREPARATION.json",
        ]
        graph = handle.artifact_graph()
        facts = graph["launch_preparation"]["descriptor_facts_without_fd_numbers"]
        assert len(facts) == 8
        assert len({(row["device"], row["inode"]) for row in facts}) == 8
        assert {row["role"] for row in facts} == set(v19._DESCRIPTOR_ROLES)  # noqa: SLF001
        assert all(row["cloexec"] is True for row in facts)
        channels = [row for row in facts if row["fd_kind"] == "AF_UNIX_SOCK_SEQPACKET"]
        assert len(channels) == 4
        assert all(row["socket_type"] == socket.SOCK_SEQPACKET for row in channels)
        assert all(row["passcred"] == 1 for row in channels)
        assert graph["takeover_preparation"]["takeover_state"] == (
            "PREPARED_UNCONSUMED_NONLAUNCHABLE"
        )
        assert graph["launch_preparation"]["next_legal_action"] == (
            "PUBLIC_ATOMIC_PERMIT_CONSUMPTION"
        )
        assert graph["launch_preparation"]["launch_preparation_state"] == (
            "DURABLE_NO_CLONE"
        )
    finally:
        closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["process_birth_count"] == 0
    assert closure["guardian_handoff_cancelled_unconsumed"] is True
    assert closure["all_prepared_descriptors_closed"] is True
    assert not any(key.startswith("prebound_capsule_") for key in closure)
    assert handle.state == "CLOSED_OR_FORK_POISONED"
    assert (tmp_path / "0004_PROTOCOL_FAILURE_CLOSURE.json").is_file()


def test_missing_public_seam_fails_before_clone_and_retains_cleanup_handle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(
        handoff, journal_path=tmp_path
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="no clone occurred",
    ) as caught:
        v19.begin_lease_bound_three_birth_v1(handle)
    assert caught.value.cleanup_handle is handle
    assert handle.state == "DURABLE_PREPARED_AWAITING_PUBLIC_ATOMIC_TAKEOVER"
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["failure_stage"] == "BEFORE_PUBLIC_ATOMIC_PERMIT_CONSUMPTION"
    assert closure["clone_syscall_performed"] is False


def test_preparation_is_not_copyable_or_pickleable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(
        handoff, journal_path=tmp_path
    )
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="cannot be copied",
        ):
            copy.copy(handle)
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="cannot be copied",
        ):
            copy.deepcopy(handle)
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="cannot be copied or pickled",
        ):
            pickle.dumps(handle)
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_wrong_thread_cannot_verify_or_abort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(
        handoff, journal_path=tmp_path
    )
    errors: list[BaseException] = []

    def cross_owner() -> None:
        for action in (
            v19.verify_lease_bound_three_birth_preparation_v1,
            v19.abort_lease_bound_three_birth_preparation_v1,
        ):
            try:
                action(handle)
            except BaseException as error:  # noqa: BLE001
                errors.append(error)

    thread = threading.Thread(target=cross_owner)
    thread.start()
    thread.join()
    try:
        assert len(errors) == 2
        assert all("crossed its exact owner" in str(error) for error in errors)
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_artifact_tamper_is_detected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(
        handoff, journal_path=tmp_path
    )
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    record.documents["launch_preparation"]["memory_peak_read_count"] = 1
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="durable journal bytes changed|content ID changed",
        ):
            v19.verify_lease_bound_three_birth_preparation_v1(handle)
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_mutated_owner_fields_cannot_transfer_to_wrong_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    original = (handle._owner_pid, handle._owner_thread, handle._owner_thread_id)
    errors: list[BaseException] = []

    def attack() -> None:
        handle._owner_pid = os.getpid()
        handle._owner_thread = threading.current_thread()
        handle._owner_thread_id = threading.get_ident()
        try:
            v19.verify_lease_bound_three_birth_preparation_v1(handle)
        except BaseException as error:  # noqa: BLE001
            errors.append(error)

    thread = threading.Thread(target=attack)
    thread.start()
    thread.join()
    handle._owner_pid, handle._owner_thread, handle._owner_thread_id = original
    try:
        assert len(errors) == 1
        assert "not live" in str(errors[0])
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_mutated_issuer_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    handle._issuer = object()
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="crossed its exact owner",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    handle._issuer = v19._ISSUER  # noqa: SLF001
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


@pytest.mark.parametrize(
    "role", ("supervisor_role", "broker_role")
)
def test_sealed_non_elf_role_memfd_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    role: str,
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001

    os.close(record.descriptors[role])
    descriptor = os.memfd_create(
        "acfqp-v19-bogus-role", v19.MFD_CLOEXEC | v19.MFD_ALLOW_SEALING
    )
    os.write(descriptor, b"NOT-AN-ELF")
    fcntl.fcntl(descriptor, v19.F_ADD_SEALS, v19.REQUIRED_SEALS)
    record.descriptors[role] = descriptor
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="exact sealed role image changed",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_pid_cell_seal_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    pid_cell = record.descriptors["supervisor_pid_cell"]
    fcntl.fcntl(pid_cell, v19.F_ADD_SEALS, v19.REQUIRED_SEALS)
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="writable pristine PID cell changed",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_socket_passcred_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    channel_fd = record.descriptors["supervisor_guardian_channel"]
    with socket.socket(fileno=os.dup(channel_fd)) as channel:
        channel.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="socket properties",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_crossed_socketpair_peer_identity_is_rejected_without_blocking(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    supervisor_role = "supervisor_child_channel"
    broker_role = "broker_child_channel"
    record.descriptors[supervisor_role], record.descriptors[broker_role] = (
        record.descriptors[broker_role],
        record.descriptors[supervisor_role],
    )
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="peer identity changed",
        ):
            v19.verify_lease_bound_three_birth_preparation_v1(handle)
    finally:
        record.descriptors[supervisor_role], record.descriptors[broker_role] = (
            record.descriptors[broker_role],
            record.descriptors[supervisor_role],
        )
        # Remove the marker left in the true supervisor child queue by the
        # deliberately crossed peer proof before restoring normal validation.
        with socket.socket(
            fileno=os.dup(record.descriptors[supervisor_role])
        ) as endpoint:
            assert endpoint.recv(64, socket.MSG_DONTWAIT) == b"acfqp-v19-peer-left"
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_deep_document_copy_cannot_mutate_live_graph(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    graph = handle.artifact_graph()
    graph["launch_preparation"]["descriptor_facts_without_fd_numbers"][0][
        "role"
    ] = "FORGED"
    document = handle.to_document()
    document["descriptor_facts_without_fd_numbers"].clear()
    try:
        verified = v19.verify_lease_bound_three_birth_preparation_v1(handle)
        assert verified["descriptor_count"] == 8
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_local_callable_and_domain_rebinding_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    original_fact = v19._fd_fact  # noqa: SLF001
    monkeypatch.setattr(v19, "_fd_fact", lambda *_args, **_kwargs: {})
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="local callable changed",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    monkeypatch.setattr(v19, "_fd_fact", original_fact)
    domain_name = "CONSTRUCTION_K7_H1_SUPERVISOR_V2_LAUNCH_PREPARATION_V1_DOMAIN"
    original_domain = getattr(v19.domains_v19, domain_name)
    monkeypatch.setattr(v19.domains_v19, domain_name, "acfqp:forged:v1")
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="domain registry globals changed",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    monkeypatch.setattr(v19.domains_v19, domain_name, original_domain)
    creator_name = "create_sealed_nested_creator_supervisor_memfd_v2"
    original_creator = getattr(v19.supervisor_v2, creator_name)
    monkeypatch.setattr(v19.supervisor_v2, creator_name, lambda: -1)
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="upstream callable changed",
    ):
        v19.verify_lease_bound_three_birth_preparation_v1(handle)
    monkeypatch.setattr(v19.supervisor_v2, creator_name, original_creator)
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_prebound_binding_issuer_rebinding_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = v19._PREBOUND_BINDING_ISSUER  # noqa: SLF001
    monkeypatch.setattr(v19, "_PREBOUND_BINDING_ISSUER", object())
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="static|dependency",
    ):
        v19.verify_lease_bound_three_birth_runtime_surface_v1()
    monkeypatch.setattr(v19, "_PREBOUND_BINDING_ISSUER", original)


def test_terminal_closure_finishes_forward_after_durable_fault(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    monkeypatch.setattr(
        v19, "_TEST_ONLY_JOURNAL_FAULT_AFTER_DURABLE", "0004_PROTOCOL_FAILURE_CLOSURE.json"
    )
    with pytest.raises(RuntimeError, match="post-durable journal fault"):
        v19.abort_lease_bound_three_birth_preparation_v1(handle)
    durable = (tmp_path / "0004_PROTOCOL_FAILURE_CLOSURE.json").read_bytes()
    monkeypatch.setattr(v19, "_TEST_ONLY_JOURNAL_FAULT_AFTER_DURABLE", None)
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert (tmp_path / "0004_PROTOCOL_FAILURE_CLOSURE.json").read_bytes() == durable
    assert closure["guardian_runtime_v2_typed_cancellation"]["terminal_code"] == (
        "UNCONSUMED_HANDOFF_CANCELLED"
    )
    assert len(closure["prepared_descriptor_closures"]) == 8


@pytest.mark.parametrize(
    "boundary",
    (
        "0001_CONSUMER_ADAPTER.json",
        "0002_LAUNCH_PREPARATION.json",
        "0003_TAKEOVER_PREPARATION.json",
    ),
)
def test_each_preparation_o_excl_boundary_closes_without_birth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, boundary: str
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    monkeypatch.setattr(v19, "_TEST_ONLY_JOURNAL_FAULT_AFTER_DURABLE", boundary)
    with pytest.raises(RuntimeError, match="post-durable journal fault"):
        v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    closure = v19.ids_v1.loads_canonical_json(
        (tmp_path / "0004_PROTOCOL_FAILURE_CLOSURE.json").read_bytes()
    )
    assert closure["process_birth_count"] == 0
    assert closure["all_prepared_descriptors_closed"] is True
    assert not v19._LIVE  # noqa: SLF001


def test_fork_child_cannot_reuse_parent_preparation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted by parent bytes
        os.close(read_fd)
        try:
            v19.verify_lease_bound_three_birth_preparation_v1(handle)
        except BaseException as error:  # noqa: BLE001
            os.write(write_fd, str(error).encode())
        finally:
            os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    message = os.read(read_fd, 4096).decode()
    os.close(read_fd)
    os.waitpid(child, 0)
    try:
        assert "crossed its exact owner" in message or "not live" in message
        assert v19.verify_lease_bound_three_birth_preparation_v1(handle)[
            "descriptor_count"
        ] == 8
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_public_prebound_binding_exactly_joins_four_duplicate_owned_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    source_identities = {
        role: (os.fstat(record.descriptors[role]).st_dev, os.fstat(record.descriptors[role]).st_ino)
        for role in (
            "supervisor_pid_cell",
            "supervisor_child_channel",
            "supervisor_guardian_channel",
            "supervisor_role",
        )
    }
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    try:
        binding = v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
            handle, prebound_capsule=capsule
        )
        assert binding["binding_state"] == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
        assert binding["owner_local_live_typed_proof_only"] is True
        assert binding["durable_artifact_present"] is False
        assert binding["content_id"]["kind"] == "NOT_APPLICABLE"
        assert binding["source_descriptors_retained_by_v19"] is True
        assert binding["capsule_descriptors_are_owned_duplicates"] is True
        assert binding["raw_descriptor_exposed"] is False
        assert binding["permit_consumed"] is False
        assert binding["native_entry_invoked"] is False
        assert binding["clone_syscall_performed"] is False
        assert len(binding["outer_nonce_hex"]) == 32
        assert len(binding["outer_frame_facts"]) == 3
        assert len({row["sha256"] for row in binding["outer_frame_facts"]}) == 3
        assert {
            row["launch_role"]: (row["device"], row["inode"])
            for row in binding["descriptor_identity_joins"]
        } == source_identities
        assert v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle) is capsule
        for descriptor in record.descriptors.values():
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
    finally:
        tombstone = v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    assert tombstone["binding_state_after"] == "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
    assert tombstone["owner_local_live_typed_proof_only"] is True
    assert tombstone["durable_artifact_present"] is False
    assert tombstone["capsule_duplicates_closed_before_v19_source_release"] is True
    assert v19.cancel_lease_bound_three_birth_prebound_clone_v1(
        handle, prebound_capsule=capsule
    ) == tombstone
    assert v19.verify_lease_bound_three_birth_preparation_v1(handle)["descriptor_count"] == 8
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True


def test_abort_automatically_cancels_prebound_duplicates_before_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    capsule_id = v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
        handle, prebound_capsule=capsule
    )["prebound_native_edge_capsule_id"]
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    typed = v19.prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1(
        capsule
    )
    assert typed["prebound_native_edge_capsule_id"] == capsule_id
    assert typed["state_after"] == "CANCELLED_UNACTIVATED"
    assert closure["all_prepared_descriptors_closed"] is True
    assert closure["process_birth_count"] == 0
    with pytest.raises(v19.prebound_v20.ConstructionK7H1SupervisorV2PreboundCloneV1Error):
        v19.prebound_v20.verify_h1_supervisor_v2_prebound_native_clone_v1(capsule)


def test_prebound_binding_rejects_wrong_thread_forgery_and_document_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    errors: list[str] = []

    def attack() -> None:
        for operation in (
            lambda: v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=capsule
            ),
            lambda: v19.cancel_lease_bound_three_birth_prebound_clone_v1(
                handle, prebound_capsule=capsule
            ),
        ):
            try:
                operation()
            except BaseException as error:  # noqa: BLE001
                errors.append(str(error))

    thread = threading.Thread(target=attack)
    thread.start()
    thread.join()
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    try:
        assert len(errors) == 2
        assert all("exact owner" in error for error in errors)
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="exact binding",
        ):
            v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=object()  # type: ignore[arg-type]
            )
        original_lifecycle = record.prebound
        changed = v19.ids_v1.loads_canonical_json(
            original_lifecycle.binding_bytes
        )
        changed["supervisor_v2_launch_preparation_id"] = "0" * 64
        record.prebound = replace(
            original_lifecycle,
            binding_bytes=v19.ids_v1.canonical_json_bytes(changed),
        )
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="binding document changed",
        ):
            v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=capsule
            )
        record.prebound = original_lifecycle
        changed = v19.ids_v1.loads_canonical_json(
            original_lifecycle.binding_bytes
        )
        changed["source_descriptors_retained_by_v19"] = 1
        record.prebound = replace(
            original_lifecycle,
            binding_bytes=v19.ids_v1.canonical_json_bytes(changed),
        )
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="binding document changed",
        ):
            v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=capsule
            )
        record.prebound = original_lifecycle
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_crossed_capsule_cancellation_closes_duplicates_and_retains_v19_abort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    os.pwrite(record.descriptors["supervisor_pid_cell"], b"X", 7)
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstoned after duplicate closure",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    tombstone = v19.cancel_lease_bound_three_birth_prebound_clone_v1(
        handle, prebound_capsule=capsule
    )
    assert tombstone["prebound_native_edge_cancellation"][
        "all_capsule_owned_resources_closed"
    ] is True
    assert fcntl.fcntl(
        record.descriptors["supervisor_pid_cell"], fcntl.F_GETFD
    ) & fcntl.FD_CLOEXEC
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True
    assert closure["process_birth_count"] == 0


def test_cancel_tombstone_prevents_capsule_reissue_and_fd_identity_reuse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    v19.cancel_lease_bound_three_birth_prebound_clone_v1(
        handle, prebound_capsule=capsule
    )
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    assert record.prebound.terminal_capsule is capsule
    original_lifecycle = record.prebound
    changed = v19.ids_v1.loads_canonical_json(
        original_lifecycle.cancellation_bytes
    )
    changed["capsule_duplicates_closed_before_v19_source_release"] = False
    record.prebound = replace(
        original_lifecycle,
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(changed),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstone (semantics|contains unknown) changed|tombstone contains unknown",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    record.prebound = original_lifecycle
    changed = v19.ids_v1.loads_canonical_json(
        original_lifecycle.cancellation_bytes
    )
    changed["binding_state_before"] = "PREBOUND_CAPSULE_CLEANUP_REQUIRED"
    changed["capsule_was_crossed_before_cancellation"] = not (
        original_lifecycle.capsule_was_crossed
    )
    record.prebound = replace(
        original_lifecycle,
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(changed),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstone semantics changed",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    record.prebound = original_lifecycle
    changed = v19.ids_v1.loads_canonical_json(
        original_lifecycle.cancellation_bytes
    )
    changed["unexpected_attack_field"] = "FORGED"
    record.prebound = replace(
        original_lifecycle,
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(changed),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="contains unknown",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    record.prebound = original_lifecycle
    changed = v19.ids_v1.loads_canonical_json(
        original_lifecycle.cancellation_bytes
    )
    changed["prebound_native_edge_capsule_id"] = "0" * 64
    changed["prebound_native_edge_cancellation"][
        "prebound_native_edge_capsule_id"
    ] = "0" * 64
    record.prebound = replace(
        original_lifecycle,
        capsule_id="0" * 64,
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(changed),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstone (semantics|contains unknown) changed|tombstone contains unknown",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle, prebound_capsule=capsule
        )
    record.prebound = original_lifecycle
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="terminal and cannot be reissued",
    ):
        v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


@pytest.mark.parametrize(
    "fault_name",
    (
        "_TEST_ONLY_FAIL_AFTER_PREBOUND_PREPARE",
        "_TEST_ONLY_FAIL_DURING_PREBOUND_COMMIT",
    ),
)
def test_prebound_fault_closes_duplicates_and_retains_cleanup_handle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault_name: str
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    monkeypatch.setattr(v19, fault_name, True)
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="failed to establish",
    ) as captured:
        v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    assert captured.value.cleanup_handle is handle
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    assert record.prebound.state == "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
    tombstone = v19.ids_v1.loads_canonical_json(
        record.prebound.cancellation_bytes
    )
    assert tombstone["capsule_duplicates_closed_before_v19_source_release"] is True
    assert v19.verify_lease_bound_three_birth_preparation_v1(handle)[
        "descriptor_count"
    ] == 8
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True
    assert closure["process_birth_count"] == 0


def test_orphaned_in_progress_state_without_capsule_recovers_to_abort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    record.prebound = v19._PreboundLifecycleV1(  # noqa: SLF001
        issuer=v19._PREBOUND_BINDING_ISSUER,  # noqa: SLF001
        state="PREBOUND_PREPARE_CALL_IN_PROGRESS",
        launch_id=record.documents["launch_preparation"][
            "supervisor_v2_launch_preparation_id"
        ],
    )
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True
    assert closure["process_birth_count"] == 0
    assert id(handle) not in v19._LIVE  # noqa: SLF001


def test_trace_reentrant_abort_cannot_cross_active_prebound_prepare(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    observed: list[str] = []

    def trace(frame, event, _arg):
        if (
            event == "line"
            and frame.f_code
            is v19.prepare_lease_bound_three_birth_prebound_clone_v1.__code__
            and not observed
        ):
            record = v19._LIVE.get(id(handle))  # noqa: SLF001
            if (
                record is not None
                and record.prebound.state == "PREBOUND_CAPSULE_PREPARING"
            ):
                try:
                    v19.abort_lease_bound_three_birth_preparation_v1(handle)
                except BaseException as error:  # noqa: BLE001
                    observed.append(str(error))
        return trace

    sys.settrace(trace)
    try:
        capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    finally:
        sys.settrace(None)
    assert observed and "before prebound prepare returns" in observed[0]
    assert v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
        handle, prebound_capsule=capsule
    )["binding_state"] == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_trace_exception_after_in_progress_transition_rolls_back_or_closes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code
            is v19.prepare_lease_bound_three_birth_prebound_clone_v1.__code__
        ):
            record = v19._LIVE.get(id(handle))  # noqa: SLF001
            if (
                record is not None
                and record.prebound.state == "PREBOUND_PREPARE_CALL_IN_PROGRESS"
                and frame.f_locals.get("capsule") is None
            ):
                fired = True
                raise RuntimeError("injected trace before V20 capsule return")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="failed to establish",
        ):
            v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    finally:
        sys.settrace(None)
    assert fired is True
    assert v19._LIVE[id(handle)].prebound.state == "ABSENT"  # noqa: SLF001
    assert v19.verify_lease_bound_three_birth_preparation_v1(handle)[
        "descriptor_count"
    ] == 8
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_trace_exception_before_signal_restore_is_finish_forward(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, frozenset())
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code
            is v19.prepare_lease_bound_three_birth_prebound_clone_v1.__code__
            and linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
            == "_restore_signal_mask_finish_forward_v1(old_signal_mask)"
        ):
            fired = True
            raise RuntimeError("injected trace immediately before signal restore")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="failed to establish",
        ):
            v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    finally:
        sys.settrace(None)
    observed_mask = signal.pthread_sigmask(signal.SIG_BLOCK, frozenset())
    assert fired is True
    assert observed_mask == original_mask
    assert v19._LIVE[id(handle)].prebound.state == (  # noqa: SLF001
        "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
    )
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_trace_exception_inside_signal_restore_is_deferred_until_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, frozenset())
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code is v19._restore_signal_mask_finish_forward_v1.__code__  # noqa: SLF001
            and linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
            == "_RAW_PTHREAD_SIGMASK(signal.SIG_SETMASK, expected_mask)"
        ):
            fired = True
            raise RuntimeError("injected trace inside signal restoration")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(
            v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
            match="failed to establish",
        ):
            v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    finally:
        sys.settrace(None)
    observed_mask = signal.pthread_sigmask(signal.SIG_BLOCK, frozenset())
    assert fired is True
    assert observed_mask == original_mask
    assert v19._LIVE[id(handle)].prebound.state == (  # noqa: SLF001
        "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
    )
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_trace_interruption_before_source_close_is_retryable_without_orphan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    original_facts = {
        role: (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        for role, fd in record.descriptors.items()
    }
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code
            is v19._close_prepared_descriptors_finish_forward_v1.__code__  # noqa: SLF001
            and "os.close(descriptor)" in linecache.getline(
                frame.f_code.co_filename, frame.f_lineno
            )
        ):
            fired = True
            raise RuntimeError("injected trace before source close commit")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match="before source close commit"):
            v19.abort_lease_bound_three_birth_preparation_v1(handle)
    finally:
        sys.settrace(None)
    assert fired is True
    active_facts = {
        role: (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        for role, fd in record.descriptors.items()
    }
    pending_facts = {
        role: (os.fstat(row[0]).st_dev, os.fstat(row[0]).st_ino)
        for role, row in record.closing_descriptors.items()
    }
    assert active_facts | pending_facts == original_facts
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True
    assert id(handle) not in v19._LIVE  # noqa: SLF001


def test_trace_interruption_after_one_source_close_resumes_remaining_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code
            is v19._close_prepared_descriptors_finish_forward_v1.__code__  # noqa: SLF001
                and len(record.closed_roles) == 1
                and linecache.getline(frame.f_code.co_filename, frame.f_lineno)
                .strip()
                .startswith("for role in roles")
        ):
            fired = True
            raise RuntimeError("injected trace after one source close commit")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match="after one source close commit"):
            v19.abort_lease_bound_three_birth_preparation_v1(handle)
    finally:
        sys.settrace(None)
    assert fired is True
    assert len(record.closed_roles) == 1
    assert len(record.descriptors) == 7
    closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
    assert closure["all_prepared_descriptors_closed"] is True
    assert len(closure["prepared_descriptor_closures"]) == 8


def test_opcode_interruption_after_close_replays_pending_identity_without_misclose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, frozenset())
    target = v19._close_prepared_descriptors_finish_forward_v1.__code__  # noqa: SLF001
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if frame.f_code is target and event == "call":
            frame.f_trace_opcodes = True
        if frame.f_code is target and event == "opcode" and not fired:
            for role, pending in record.closing_descriptors.items():
                descriptor = pending[0]
                if role in record.descriptors or role in record.closed_roles:
                    continue
                try:
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                except OSError as error:
                    if error.errno == errno.EBADF:
                        fired = True
                        raise RuntimeError("injected opcode after kernel close")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match="after kernel close"):
            v19.abort_lease_bound_three_birth_preparation_v1(handle)
    finally:
        sys.settrace(None)
    assert fired is True
    assert signal.pthread_sigmask(signal.SIG_BLOCK, frozenset()) == original_mask
    assert len(record.closing_descriptors) == 1
    pending_descriptor = next(iter(record.closing_descriptors.values()))[0]
    replacement = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    if replacement != pending_descriptor:
        os.dup2(replacement, pending_descriptor, inheritable=False)
    try:
        closure = v19.abort_lease_bound_three_birth_preparation_v1(handle)
        assert closure["all_prepared_descriptors_closed"] is True
        assert fcntl.fcntl(pending_descriptor, fcntl.F_GETFD) >= 0
    finally:
        if replacement != pending_descriptor:
            os.close(replacement)
        os.close(pending_descriptor)


def test_trace_reentrant_abort_cannot_invalidate_outer_cancel_claim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    observed: list[BaseException] = []
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code is v19._cancel_prebound_clone_v1.__code__  # noqa: SLF001
        ):
            fired = True
            try:
                v19.abort_lease_bound_three_birth_preparation_v1(handle)
            except BaseException as error:  # noqa: BLE001
                observed.append(error)
        return trace

    sys.settrace(trace)
    try:
        tombstone = v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle,
            prebound_capsule=capsule,
        )
    finally:
        sys.settrace(None)
    assert fired is True
    assert len(observed) == 1
    assert "cannot reenter active cancel" in str(observed[0])
    assert tombstone["source_descriptors_retained_by_v19"] is True
    assert id(handle) in v19._LIVE  # noqa: SLF001
    assert len(v19._LIVE[id(handle)].descriptors) == 8  # noqa: SLF001
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_terminal_tombstone_rejoins_authoritative_launch_and_exact_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    v19.cancel_lease_bound_three_birth_prebound_clone_v1(
        handle,
        prebound_capsule=capsule,
    )
    record = v19._LIVE[id(handle)]  # noqa: SLF001
    original = record.prebound
    forged_launch_id = "f" * 64
    binding = v19.ids_v1.loads_canonical_json(original.binding_bytes)
    binding["supervisor_v2_launch_preparation_id"] = forged_launch_id
    tombstone = v19.ids_v1.loads_canonical_json(original.cancellation_bytes)
    tombstone["supervisor_v2_launch_preparation_id"] = forged_launch_id
    record.prebound = replace(
        original,
        launch_id=forged_launch_id,
        binding_bytes=v19.ids_v1.canonical_json_bytes(binding),
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(tombstone),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstone semantics changed",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle,
            prebound_capsule=capsule,
        )
    record.prebound = original
    binding = v19.ids_v1.loads_canonical_json(original.binding_bytes)
    binding["unexpected_terminal_binding_field"] = "FORGED"
    record.prebound = replace(
        original,
        binding_bytes=v19.ids_v1.canonical_json_bytes(binding),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="live-binding schema changed",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle,
            prebound_capsule=capsule,
        )
    record.prebound = original
    tombstone = v19.ids_v1.loads_canonical_json(original.cancellation_bytes)
    tombstone["binding_state_before"] = "PREBOUND_CAPSULE_CLEANUP_REQUIRED"
    record.prebound = replace(
        original,
        terminal_state_before="PREBOUND_CAPSULE_CLEANUP_REQUIRED",
        cancellation_bytes=v19.ids_v1.canonical_json_bytes(tombstone),
    )
    with pytest.raises(
        v19.ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error,
        match="tombstone semantics changed",
    ):
        v19.cancel_lease_bound_three_birth_prebound_clone_v1(
            handle,
            prebound_capsule=capsule,
        )
    record.prebound = original
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_trace_exception_after_v20_terminal_replays_to_v19_tombstone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    fired = False

    def trace(frame, event, _arg):
        nonlocal fired
        if (
            not fired
            and event == "line"
            and frame.f_code is v19._cancel_prebound_clone_v1.__code__  # noqa: SLF001
            and capsule in v19.prebound_v20._TERMINAL  # noqa: SLF001
        ):
            fired = True
            raise RuntimeError("injected trace after V20 terminal commit")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match="after V20 terminal commit"):
            v19.cancel_lease_bound_three_birth_prebound_clone_v1(
                handle, prebound_capsule=capsule
            )
    finally:
        sys.settrace(None)
    assert fired is True
    tombstone = v19.cancel_lease_bound_three_birth_prebound_clone_v1(
        handle, prebound_capsule=capsule
    )
    assert tombstone["binding_state_after"] == (
        "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
    )
    v19.abort_lease_bound_three_birth_preparation_v1(handle)


def test_fork_child_cannot_reuse_parent_prebound_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handoff = _install_fake_guardian(monkeypatch)
    handle = v19.prepare_lease_bound_three_birth_v1(handoff, journal_path=tmp_path)
    capsule = v19.prepare_lease_bound_three_birth_prebound_clone_v1(handle)
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted by parent bytes
        os.close(read_fd)
        try:
            v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=capsule
            )
        except BaseException as error:  # noqa: BLE001
            os.write(write_fd, str(error).encode())
        finally:
            os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    message = os.read(read_fd, 4096).decode()
    os.close(read_fd)
    os.waitpid(child, 0)
    try:
        assert "exact owner" in message or "not live" in message
        assert v19.verify_lease_bound_three_birth_prebound_clone_binding_v1(
            handle, prebound_capsule=capsule
        )["binding_state"] == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
    finally:
        v19.abort_lease_bound_three_birth_preparation_v1(handle)
