from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import types

import pytest

from acfqp import construction_k7_campaign_measurement_worker_v180r12r3 as core


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


work = _load("_test_work_v180r12r3", "scripts/work_v180r12r3_campaign_measurement.py")
supervise = _load(
    "_test_supervise_for_work_v180r12r3",
    "scripts/supervise_v180r12r3_campaign_measurement.py",
)
run = _load(
    "_test_run_for_work_v180r12r3",
    "scripts/run_v180r12r3_campaign_measurement.py",
)


def _close_if_open(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _sealed_read_only(raw: bytes) -> int:
    writable = supervise._memfd_create("v180r12r3-bundle")
    os.write(writable, raw)
    os.fchmod(writable, 0o400)
    fcntl.fcntl(writable, supervise.F_ADD_SEALS, work.REQUIRED_SEAL_MASK)
    readonly = os.open(f"/proc/self/fd/{writable}", os.O_RDONLY | os.O_CLOEXEC)
    os.close(writable)
    return readonly


def test_worker_reads_exact_readonly_sealed_memfds_and_rejects_swap() -> None:
    terminal_stage = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.TERMINAL, b"t" * 199_755
    )
    verification_stage = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.VERIFICATION, b"v" * 2_752
    )
    try:
        binding = work.SealedPayloadBindingV180R12R3(
            core.CampaignInputRoleV180R12R3.TERMINAL,
            terminal_stage.worker_source_descriptor,
            terminal_stage.device,
            terminal_stage.inode,
            terminal_stage.byte_count,
        )
        observed = work.read_inherited_sealed_payload_v180r12r3(binding)
        assert observed.returned_bytes == b"t" * 199_755
        foreign = work.SealedPayloadBindingV180R12R3(
            core.CampaignInputRoleV180R12R3.TERMINAL,
            terminal_stage.worker_source_descriptor,
            verification_stage.device,
            verification_stage.inode,
            terminal_stage.byte_count,
        )
        with pytest.raises(work.V180R12R3WorkerRuntimeError):
            work.read_inherited_sealed_payload_v180r12r3(foreign)
        os.fchmod(terminal_stage.supervisor_descriptor, 0o600)
        with pytest.raises(
            work.V180R12R3WorkerRuntimeError, match="sealed read-only memfd"
        ):
            work.read_inherited_sealed_payload_v180r12r3(binding)
    finally:
        supervise.close_sealed_stage_v180r12r3(verification_stage)
        supervise.close_sealed_stage_v180r12r3(terminal_stage)


def test_subject_write_is_exact_and_zero_progress_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del tmp_path
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        local = Path(local_text)
        path = local / "subject.partial"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            observed = work.write_subject_result_v180r12r3(descriptor, b"subject")
            assert observed.returned_chunk_byte_counts == (7,)
        finally:
            os.close(descriptor)

        second = local / "short.partial"
        descriptor = os.open(
            second,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        original_write = work.os.write

        def no_progress(fd: int, raw: bytes) -> int:
            if fd == descriptor:
                return 0
            return original_write(fd, raw)

        monkeypatch.setattr(work.os, "write", no_progress)
        try:
            with pytest.raises(
                work.V180R12R3WorkerRuntimeError,
                match="preregistered chunk schedule",
            ):
                work.write_subject_result_v180r12r3(descriptor, b"subject")
        finally:
            os.close(descriptor)


def test_subject_write_stops_at_first_preregistered_chunk_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        path = Path(local_text) / "partial-second-chunk.partial"
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        original_write = work.os.write
        calls = 0

        def partial_second(fd: int, raw: bytes) -> int:
            nonlocal calls
            if fd != descriptor:
                return original_write(fd, raw)
            calls += 1
            if calls == 2:
                return original_write(fd, raw[: len(raw) // 2])
            return original_write(fd, raw)

        monkeypatch.setattr(work.os, "write", partial_second)
        payload = b"x" * (2 * work.WRITE_CHUNK_BYTES + 7)
        try:
            with pytest.raises(
                work.V180R12R3WorkerRuntimeError,
                match="preregistered chunk schedule",
            ):
                work.write_subject_result_v180r12r3(descriptor, payload)
            assert calls == 2
            assert os.fstat(descriptor).st_size == (
                work.WRITE_CHUNK_BYTES + work.WRITE_CHUNK_BYTES // 2
            )
        finally:
            os.close(descriptor)


def test_subject_runtime_cap_is_narrower_than_frame_and_rejected_before_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert work.SUBJECT_RESULT_RUNTIME_BYTE_CAP == 768 * 1024
    assert work.SUBJECT_RESULT_RUNTIME_BYTE_CAP < work.FRAME_BYTE_CAP
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        path = Path(local_text) / "over-cap.partial"
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        writes: list[int] = []
        original_write = work.os.write

        def observed_write(fd: int, raw: bytes) -> int:
            if fd == descriptor:
                writes.append(len(raw))
            return original_write(fd, raw)

        monkeypatch.setattr(work.os, "write", observed_write)
        try:
            with pytest.raises(work.V180R12R3WorkerRuntimeError):
                work.write_subject_result_v180r12r3(
                    descriptor,
                    b"x" * (work.SUBJECT_RESULT_RUNTIME_BYTE_CAP + 1),
                )
            assert writes == []
            assert os.fstat(descriptor).st_size == 0
        finally:
            os.close(descriptor)


def test_subject_outcome_signed_frame_is_preflighted_without_sending() -> None:
    fixture = _load(
        "_test_worker_core_fixture_for_subject_preflight",
        "tests/test_construction_k7_campaign_measurement_worker_v180r12r3.py",
    )
    _stage, replay, execution_context = fixture._run_synthetic()
    schedule = work.supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3(
        execution_context.attempt_id
    )
    birth_operation_id = next(
        row.operation_id
        for row in schedule
        if row.event_kind == "PROCESS_BIRTH_INTENT"
        and row.actor_role == "SUPERVISOR"
        and row.phase == "WORKER"
    )
    outcome_sequence = next(
        index
        for index, row in enumerate(schedule)
        if row.event_kind == "SUBJECT_WRITE_OUTCOME"
    )
    planned = schedule[outcome_sequence]
    local, peer = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    peer.setblocking(False)
    try:
        observations = supervise.configure_seqpacket_pair_v180r12r3(local, peer)
        assert supervise.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES == work.FRAME_BYTE_CAP
        assert supervise.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES == 2 * work.FRAME_BYTE_CAP
        assert min(value for row in observations for value in row) >= (
            supervise.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        )
        channel = work._AuthenticatedWorkerChannelV180R12R3(
            local,
            b"p" * 32,
            {
                "launch_operation_id": birth_operation_id,
                "protocol_id": execution_context.protocol_id,
                "authorization_id": execution_context.authorization_id,
                "authorization_evidence_id": (
                    execution_context.authorization_evidence_id
                ),
                "attempt_id": execution_context.attempt_id,
            },
        )
        bridge = work._AuthenticatedWorkerBridgeV180R12R3(
            channel,
            types.SimpleNamespace(execution_context=execution_context),
            outcome_sequence,
            open_event=("SUBJECT_WRITE", planned.operation_id),
        )
        bridge.preflight_subject_write(replay)
        body, raw, counts, subject_id = bridge.pending_subject_outcome
        assert body["campaign_event_sequence"] == outcome_sequence
        assert body["event_kind"] == "SUBJECT_WRITE_OUTCOME"
        assert len(raw) <= work.FRAME_BYTE_CAP
        assert sum(counts) == len(replay.subject_bytes)
        assert subject_id == replay.subject_id
        assert channel.next_send_sequence == 0
        with pytest.raises(BlockingIOError):
            peer.recv(1)
        # The exact preflighted subject outcome, not a filler packet, must be
        # interoperable over the provisioned supervisor/worker seqpacket pair.
        peer.setblocking(True)
        assert local.send(raw) == len(raw)
        assert peer.recv(work.FRAME_BYTE_CAP + 1) == raw
    finally:
        local.close()
        peer.close()


def test_real_worker_phase_preflights_subject_before_first_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _load(
        "_test_worker_core_fixture_for_effect_order",
        "tests/test_construction_k7_campaign_measurement_worker_v180r12r3.py",
    )
    terminal, verification, _contract, _tr, _vr, execution_context = (
        fixture._synthetic_replay_inputs()
    )
    stage, _replay, _context = fixture._run_synthetic()
    terminal_memfd = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.TERMINAL, terminal
    )
    verification_memfd = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.VERIFICATION, verification
    )
    terminal_binding = work.SealedPayloadBindingV180R12R3(
        core.CampaignInputRoleV180R12R3.TERMINAL,
        terminal_memfd.worker_source_descriptor,
        terminal_memfd.device,
        terminal_memfd.inode,
        terminal_memfd.byte_count,
    )
    verification_binding = work.SealedPayloadBindingV180R12R3(
        core.CampaignInputRoleV180R12R3.VERIFICATION,
        verification_memfd.worker_source_descriptor,
        verification_memfd.device,
        verification_memfd.inode,
        verification_memfd.byte_count,
    )
    trace: list[str] = []

    class Bridge:
        def before_stage_read(self, binding):
            trace.append("read_intent:" + binding.role.value)

        def after_stage_read(self, observation):
            trace.append("read_outcome:" + observation.binding.role.value)

        def before_operation(self, kind, label, phase, actor_role):
            del kind, label, phase, actor_role

        def after_operation(self, result):
            del result

        def before_subject_write(self, subject_result_id, byte_count):
            del subject_result_id, byte_count
            trace.append("subject_intent_ack")

        def preflight_subject_write(self, result):
            assert len(result.subject_bytes) <= work.SUBJECT_RESULT_RUNTIME_BYTE_CAP
            trace.append("subject_frame_preflight")

        def after_subject_write(self, observation, result):
            del observation, result
            trace.append("subject_outcome")

    original_write = work.write_subject_result_v180r12r3

    def observed_write(descriptor, raw, **kwargs):
        trace.append("subject_write")
        return original_write(descriptor, raw, **kwargs)

    monkeypatch.setattr(work, "write_subject_result_v180r12r3", observed_write)
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        subject_fd = os.open(
            Path(local_text) / "subject.partial",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        os.fchmod(subject_fd, 0o600)
        try:
            work.run_worker_effects_v180r12r3(
                terminal_binding=terminal_binding,
                verification_binding=verification_binding,
                stage_result=stage,
                execution_context=execution_context,
                subject_descriptor=subject_fd,
                bridge=Bridge(),
            )
            assert trace[-4:] == [
                "subject_intent_ack",
                "subject_frame_preflight",
                "subject_write",
                "subject_outcome",
            ]
        finally:
            os.close(subject_fd)
            supervise.close_sealed_stage_v180r12r3(verification_memfd)
            supervise.close_sealed_stage_v180r12r3(terminal_memfd)


def test_subject_write_rejects_post_bootstrap_mode_drift(tmp_path: Path) -> None:
    path = tmp_path / "mode-drift.partial"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o400)
        with pytest.raises(work.V180R12R3WorkerRuntimeError):
            work.write_subject_result_v180r12r3(descriptor, b"subject")
    finally:
        os.close(descriptor)


def test_bootstrap_context_dispatch_checks_exact_worker_fd_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _sealed_read_only(b"precompiled")
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    terminal = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.TERMINAL, b"t" * 199_755
    )
    verification = supervise.stage_sealed_memfd_v180r12r3(
        core.CampaignInputRoleV180R12R3.VERIFICATION, b"v" * 2_752
    )
    local = tempfile.TemporaryDirectory(dir="/tmp")
    subject_path = Path(local.name) / "subject.partial"
    subject = os.open(subject_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    for descriptor in (242, 243):
        _close_if_open(descriptor)
    try:
        for source, target in (
            (bundle, 240), (child.fileno(), 241),
            (terminal.worker_source_descriptor, 246),
            (verification.worker_source_descriptor, 247), (subject, 248),
        ):
            os.dup2(source, target, inheritable=False)
        payload = types.MappingProxyType(
            {
                "terminal_stage_byte_count": 199_755,
                "verification_stage_byte_count": 2_752,
                "subject_result_initial_byte_count": 0,
            }
        )
        protocol_id = "1" * 64
        authorization_id = "2" * 64
        authorization_evidence_id = "3" * 64
        execution_slot_id = "4" * 64
        logical_occurrence_id = "5" * 64
        execution_nonce = "6" * 64
        attempt_id = work.identity_domains.derive_campaign_measurement_attempt_id_v180r12r3(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            campaign_measurement_execution_slot_id=execution_slot_id,
            logical_occurrence_id=logical_occurrence_id,
            execution_nonce=execution_nonce,
        )
        launch_operation_id = next(
            row.operation_id
            for row in work.supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3(
                attempt_id
            )
            if row.event_kind == "PROCESS_BIRTH_INTENT"
            and row.actor_role == "SUPERVISOR"
            and row.phase == "WORKER"
        )
        context = types.MappingProxyType(
            {
                "schema": "acfqp.v180r12r3_verified_internal_launch_context.v1",
                "target": "worker",
                "actor_role": "WORKER",
                "parent_actor_role": "SUPERVISOR",
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": authorization_evidence_id,
                "attempt_id": attempt_id,
                "campaign_measurement_execution_slot_id": execution_slot_id,
                "logical_occurrence_id": logical_occurrence_id,
                "execution_nonce": execution_nonce,
                "prelaunch_materialization_terminal_id": "7" * 64,
                "prelaunch_launch_rule_id": "8" * 64,
                "measurement_launch_attempt_id": "9" * 64,
                "launch_operation_id": launch_operation_id,
                "manifest_sha256": "a" * 64,
                "precompiled_source_bundle_sha256": "b" * 64,
                "inherited_fd_roles": work._EXPECTED_FD_ROLES,
                "target_payload": payload,
                "parent_to_child_mac_key": b"k" * 32,
                "parent_context_mac": "c" * 64,
                "context_consumed_once": True,
            }
        )
        seen = []
        monkeypatch.setattr(
            work, "_run_bootstrap_verified_worker_v180r12r3",
            lambda value: seen.append(value),
        )
        assert work.bootstrap_entrypoint_v180r12r3(context) is None
        assert seen == [context]
        bad = dict(context)
        bad["inherited_fd_roles"] = tuple(reversed(work._EXPECTED_FD_ROLES))
        with pytest.raises(work.V180R12R3WorkerRuntimeError):
            work.bootstrap_entrypoint_v180r12r3(types.MappingProxyType(bad))
    finally:
        for descriptor in (240, 241, 246, 247, 248):
            _close_if_open(descriptor)
        for descriptor in (bundle, subject):
            _close_if_open(descriptor)
        parent.close()
        child.close()
        supervise.close_sealed_stage_v180r12r3(verification)
        supervise.close_sealed_stage_v180r12r3(terminal)
        local.cleanup()


def test_direct_main_is_forbidden() -> None:
    with pytest.raises(work.V180R12R3WorkerRuntimeError):
        work.main([])


def test_real_worker_bootstrap_driver_authenticates_handoff_proposals_and_acks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol_id = "1" * 64
    authorization_id = "2" * 64
    authorization_evidence_id = "3" * 64
    execution_slot_id = "4" * 64
    logical_occurrence_id = "5" * 64
    execution_nonce = "6" * 64
    attempt_id = work.identity_domains.derive_campaign_measurement_attempt_id_v180r12r3(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        campaign_measurement_execution_slot_id=execution_slot_id,
        logical_occurrence_id=logical_occurrence_id,
        execution_nonce=execution_nonce,
    )
    schedule = work.supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3(
        attempt_id
    )
    birth_sequence = next(
        index
        for index, row in enumerate(schedule)
        if row.event_kind == "PROCESS_BIRTH_OUTCOME"
        and row.actor_role == "SUPERVISOR"
        and row.phase == "WORKER"
    )
    first_read_sequence = birth_sequence + 1
    reap_sequence = next(
        index
        for index, row in enumerate(schedule)
        if row.event_kind == "PROCESS_REAP"
        and row.actor_role == "SUPERVISOR"
        and row.phase == "WORKER"
    )
    channel_id = schedule[birth_sequence].operation_id
    secret = b"k" * 32
    parent_socket, child_socket = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    source_fd = child_socket.fileno()
    _close_if_open(work.INTERNAL_IPC_FD)
    os.dup2(source_fd, work.INTERNAL_IPC_FD, inheritable=False)
    context = types.MappingProxyType(
        {
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "authorization_evidence_id": authorization_evidence_id,
            "attempt_id": attempt_id,
            "launch_operation_id": channel_id,
            "parent_to_child_mac_key": secret,
        }
    )
    handoff_body = {
        field: "a" * 64 for field in work.SUPERVISOR_WORKER_HANDOFF_FIELDS
    }
    handoff_body.update(
        {
            "schema": work.SUPERVISOR_WORKER_HANDOFF_SCHEMA,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "authorization_evidence_id": authorization_evidence_id,
            "attempt_id": attempt_id,
            "worker_birth_event_sequence": birth_sequence,
            "next_campaign_event_sequence": first_read_sequence,
            "one_shot_handoff": True,
        }
    )
    fake_context = types.SimpleNamespace(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        attempt_id=attempt_id,
    )
    fake_handoff = types.SimpleNamespace(
        document=handoff_body,
        execution_context=fake_context,
    )
    monkeypatch.setattr(
        work,
        "validate_supervisor_worker_handoff_v180r12r3",
        lambda body, *, verified_context: fake_handoff,
    )

    def synthetic_effect(handoff, *, bridge):
        del handoff
        bridge._intent("INPUT_READ_INTENT")
        outcome_plan = schedule[bridge.campaign_event_sequence]
        receipt = work.supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r3(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            operation_id=outcome_plan.operation_id,
            event_kind="INPUT_READ_OUTCOME",
            measured_value=1,
            returned_chunk_byte_counts=(1,),
            source_evidence_id="b" * 64,
            target_evidence_id="c" * 64,
        )
        bridge._outcome("INPUT_READ_OUTCOME", receipt, measured_value=1)
        bridge.campaign_event_sequence = reap_sequence

    monkeypatch.setattr(
        work, "run_validated_worker_handoff_v180r12r3", synthetic_effect
    )
    parent = run.AuthenticatedFrameChannelV180R12R3(
        parent_socket,
        secret,
        channel_id=channel_id,
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        attempt_id=attempt_id,
        parent_actor_role="SUPERVISOR",
        child_actor_role="WORKER",
        local_actor_role="SUPERVISOR",
    )
    failures: list[BaseException] = []

    def target() -> None:
        try:
            work._run_bootstrap_verified_worker_v180r12r3(context)
        except BaseException as error:  # captured for the test thread
            failures.append(error)

    try:
        parent.send("WORKER_HANDOFF", 0, handoff_body)
        thread = threading.Thread(target=target)
        thread.start()
        frame_type, _sequence, intent = parent.receive()
        assert frame_type == "EVENT_PROPOSAL"
        assert intent["campaign_event_sequence"] == first_read_sequence
        assert intent["event_kind"] == "INPUT_READ_INTENT"
        parent.send(
            "EVENT_ACK",
            1,
            {
                "schema": run.EVENT_ACK_BODY_SCHEMA,
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": authorization_evidence_id,
                "attempt_id": attempt_id,
                "campaign_event_sequence": first_read_sequence,
                "event_id": "d" * 64,
                "event_file_sha256": "e" * 64,
                "durable_file_and_directory_fsync_complete": True,
            },
        )
        frame_type, _sequence, outcome = parent.receive()
        assert frame_type == "EVENT_PROPOSAL"
        assert outcome["campaign_event_sequence"] == first_read_sequence + 1
        assert outcome["event_kind"] == "INPUT_READ_OUTCOME"
        assert outcome["payload"]["measured_value"] == 1
        assert outcome["evidence_documents"][0]["io_transfer_receipt_id"] == (
            outcome["payload"]["evidence_id"]
        )
        parent.send(
            "EVENT_ACK",
            2,
            {
                "schema": run.EVENT_ACK_BODY_SCHEMA,
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": authorization_evidence_id,
                "attempt_id": attempt_id,
                "campaign_event_sequence": first_read_sequence + 1,
                "event_id": "f" * 64,
                "event_file_sha256": "0" * 64,
                "durable_file_and_directory_fsync_complete": True,
            },
        )
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert failures == []
        assert parent_socket.recv(1) == b""
    finally:
        _close_if_open(work.INTERNAL_IPC_FD)
        parent_socket.close()
        child_socket.close()
