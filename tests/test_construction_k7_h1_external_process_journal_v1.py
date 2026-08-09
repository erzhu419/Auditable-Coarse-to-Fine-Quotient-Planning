from __future__ import annotations

import array
import hashlib
import os
from pathlib import Path
import signal
import socket
import time

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v14 as domains_v14
from acfqp import construction_k7_h1_external_process_journal_v1 as journal_v1
from acfqp.phase3e_ids import canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-h1-external-process-journal-test:v1\x00" + label.encode()
    ).hexdigest()


def _channel_pair() -> tuple[socket.socket, socket.socket]:
    receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    for endpoint in (receiver, sender):
        endpoint.setblocking(True)
        os.set_inheritable(endpoint.fileno(), False)
    return receiver, sender


def _open_case(tmp_path: Path, suffix: str = "case"):
    supervisor_receiver, supervisor_sender = _channel_pair()
    broker_receiver, broker_sender = _channel_pair()
    supervisor = journal_v1.prebind_h1_external_process_creator_channel_v1(
        kind=journal_v1.CreatorChannelKindV1.SUPERVISOR_CREATOR,
        channel_identity_id=_id(f"{suffix}:supervisor-channel"),
        endpoint=supervisor_receiver,
    )
    broker = journal_v1.prebind_h1_external_process_creator_channel_v1(
        kind=journal_v1.CreatorChannelKindV1.BROKER_CREATOR,
        channel_identity_id=_id(f"{suffix}:broker-channel"),
        endpoint=broker_receiver,
    )
    directory = tmp_path / suffix
    directory.mkdir(mode=0o700)
    os.chmod(directory, 0o700)
    journal = journal_v1.open_h1_external_process_journal_v1(
        journal_directory=directory,
        attempt_identity_id=_id(f"{suffix}:attempt"),
        route_attempt_id=_id(f"{suffix}:route-attempt"),
        build_epoch_id=_id(f"{suffix}:epoch"),
        supervisor_creator_channel=supervisor,
        broker_creator_channel=broker,
    )
    return journal, directory, supervisor_sender, broker_sender


def _prepare(
    journal: journal_v1.H1ExternalProcessJournalV1,
    slot: journal_v1.ExternalProcessSlotV1,
    suffix: str,
):
    intent = journal.prepare_intent(
        slot=slot,
        launch_identity_id=_id(f"{suffix}:launch"),
        cgroup_identity_id=_id(f"{suffix}:cgroup"),
        shared_pid_cell_identity_id=_id(f"{suffix}:pid-cell"),
    )
    permit = journal.issue_permit(slot=slot)
    return intent, permit


def _packet(permit_document: dict[str, object], pid: int) -> dict[str, object]:
    return {
        "schema": "acfqp.k7_h1_external_process_pidfd_escrow_packet.v1",
        "schema_version": journal_v1.SCHEMA_VERSION,
        "profile_key": journal_v1.PROFILE_KEY,
        "slot": permit_document["slot"],
        "external_process_intent_id": permit_document["external_process_intent_id"],
        "external_process_permit_id": permit_document["external_process_permit_id"],
        "creator_channel_binding_id": permit_document["creator_channel_binding_id"],
        "launch_identity_id": permit_document["launch_identity_id"],
        "cgroup_identity_id": permit_document["cgroup_identity_id"],
        "shared_pid_cell_identity_id": permit_document["shared_pid_cell_identity_id"],
        "fdinfo_pid": pid,
        "shared_pid_cell_observed_pid": pid,
        "process_start_ticks": journal_v1._process_start_ticks(pid),  # noqa: SLF001
    }


def _creator_reap_packet(
    receipt: dict[str, object], death: dict[str, object]
) -> dict[str, object]:
    return {
        "schema": "acfqp.k7_h1_external_process_creator_reap_report_packet.v1",
        "schema_version": journal_v1.SCHEMA_VERSION,
        "profile_key": journal_v1.PROFILE_KEY,
        "slot": receipt["slot"],
        "external_process_escrow_receipt_id": receipt[
            "external_process_escrow_receipt_id"
        ],
        "external_process_death_observation_id": death[
            "external_process_death_observation_id"
        ],
        "creator_channel_binding_id": receipt["creator_channel_binding_id"],
        "observed_pid": receipt["fdinfo_pid"],
        "process_start_ticks": receipt["process_start_ticks"],
        "waitid_idtype": "P_PID",
        "waitid_options": ["WEXITED", "WNOHANG"],
        "observed_uid": os.geteuid(),
        "si_signo": int(signal.SIGCHLD),
        "si_status": int(signal.SIGKILL),
        "si_code": 2,
    }


def _send_packet(
    endpoint: socket.socket,
    packet: dict[str, object],
    rights: tuple[int, ...],
) -> None:
    ancillary = []
    if rights:
        descriptors = array.array("i", rights)
        ancillary.append((socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors.tobytes()))
    raw = canonical_json_bytes(packet)
    assert endpoint.sendmsg([raw], ancillary) == len(raw)


def _drain_control(endpoint: socket.socket) -> tuple[dict[str, object], dict[str, object]]:
    import json

    first = json.loads(endpoint.recv(journal_v1.MAX_PACKET_BYTES).decode())
    second = json.loads(endpoint.recv(journal_v1.MAX_PACKET_BYTES).decode())
    assert first["schema"] == "acfqp.k7_h1_external_process_guardian_ack.v1"
    assert second["schema"] == "acfqp.k7_h1_external_process_creator_release.v1"
    return first, second


def _receive_death_control(
    endpoint: socket.socket,
) -> tuple[dict[str, object], dict[str, object]]:
    import json

    message = json.loads(endpoint.recv(journal_v1.MAX_PACKET_BYTES).decode())
    assert message["schema"] == "acfqp.k7_h1_external_process_death_observed.v1"
    return message["escrow_receipt"], message["death_observation"]


def test_profile_and_v14_domains_are_stable_and_all_claims_remain_locked() -> None:
    assert journal_v1.ORDERED_FIVE_SLOT_ESCROW_RECORD_PROTOCOL_PRESENT is True
    assert journal_v1.FIXED_FIVE_SLOT_WRITE_AHEAD_PROTOCOL_PRESENT is False
    assert journal_v1.ACTUAL_PROCESS_BIRTH_ORDER_VERIFIED is False
    assert journal_v1.LAUNCH_GATE_PRESENT is False
    assert journal_v1.CGROUP_MEMBERSHIP_VERIFIED is False
    assert journal_v1.SHARED_PID_CELL_GUARDIAN_READ_PRESENT is False
    profile = journal_v1.official_h1_external_process_journal_profile_v1()
    document = profile.to_document()
    assert document["ordered_escrow_record_slot_order"] == [
        slot.value for slot in journal_v1.SLOT_ORDER
    ]
    assert document["fixed_slot_order_is_process_birth_order"] is False
    assert document["creator_channels"] == [
        "SUPERVISOR_CREATOR",
        "BROKER_CREATOR",
    ]
    assert document["intent_must_be_persisted_before_escrow_record_permit"] is True
    assert document["permit_is_a_real_launch_gate"] is False
    assert document["post_permit_pid_birth_verified"] is False
    assert document["cgroup_membership_verified"] is False
    assert document["shared_pid_cell_guardian_read_present"] is False
    assert document["close_retry_same_ofd_witness_present"] is True
    assert document["close_retry_inode_identity_only"] is False
    for field in (
        "real_e3_v2_integration_present",
        "authenticated_supervisor_present",
        "machine_crash_durability_present",
        "pid_cell_untamperability_present",
        "normal_guardian_reap_present",
        "fq11_counter_completeness_present",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "current_access_authority_present",
        "formal_v7_authority_present",
        "official_execution_allowed",
    ):
        assert document[field] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    payload = {"same": "payload"}
    values = {
        domains_v14.extension_content_id_v14(domain, payload)
        for domain in domains_v14.K7_H1_DOMAIN_TAG_EXTENSION_V14
    }
    assert len(values) == len(domains_v14.K7_H1_DOMAIN_TAG_EXTENSION_V14)
    with pytest.raises(ValueError, match="absent"):
        domains_v14.extension_content_id_v14("acfqp:foreign:v1", payload)


def test_intent_is_persisted_before_permit_and_record_order_is_enforced(
    tmp_path: Path,
) -> None:
    journal, directory, supervisor_sender, broker_sender = _open_case(tmp_path)
    try:
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal.issue_permit(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal.prepare_intent(
                slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE,
                launch_identity_id=_id("bad-launch"),
                cgroup_identity_id=_id("bad-cgroup"),
                shared_pid_cell_identity_id=_id("bad-cell"),
            )
        intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "supervisor"
        )
        intent_document = intent.to_document()
        permit_document = permit.to_document()
        assert intent_document["event_kind"] == "ESCROW_RECORD_INTENT_PREPARED"
        assert permit_document["intent_persistence_precedes_permit"] is True
        assert intent_document["sequence"] == 1
        assert permit_document["sequence"] == 2
        assert permit_document["previous_record_id"] == intent.record_id
        files = sorted(directory.iterdir())
        assert len(files) == 3
        assert all(path.stat().st_mode & 0o777 == 0o400 for path in files)
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal.prepare_intent(
                slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE,
                launch_identity_id=_id("early-launch"),
                cgroup_identity_id=_id("early-cgroup"),
                shared_pid_cell_identity_id=_id("early-cell"),
            )
        closure = journal.close_crash(reason_code="TEST_PARTIAL_PREFIX")
        closure_document = closure.to_document()
        assert closure_document["process_launch_counter_authorized"] is False
        assert closure_document["crash_cleanup_complete"] is False
        assert closure_document["slot_prefix"][0]["stage"] == "PERMIT_ISSUED"
    finally:
        supervisor_sender.close()
        broker_sender.close()


def test_two_distinct_prebound_creator_channels_are_required(tmp_path: Path) -> None:
    receiver, sender = _channel_pair()
    other_receiver, other_sender = _channel_pair()
    try:
        supervisor = journal_v1.prebind_h1_external_process_creator_channel_v1(
            kind=journal_v1.CreatorChannelKindV1.SUPERVISOR_CREATOR,
            channel_identity_id=_id("same-channel"),
            endpoint=receiver,
        )
        directory = tmp_path / "same"
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal_v1.open_h1_external_process_journal_v1(
                journal_directory=directory,
                attempt_identity_id=_id("attempt"),
                route_attempt_id=_id("route"),
                build_epoch_id=_id("epoch"),
                supervisor_creator_channel=supervisor,
                broker_creator_channel=supervisor,
            )
        duplicate_endpoint = socket.socket(fileno=os.dup(receiver.fileno()))
        os.set_inheritable(duplicate_endpoint.fileno(), False)
        duplicate = journal_v1.prebind_h1_external_process_creator_channel_v1(
            kind=journal_v1.CreatorChannelKindV1.BROKER_CREATOR,
            channel_identity_id=_id("duplicated-physical-channel"),
            endpoint=duplicate_endpoint,
        )
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="two distinct",
        ):
            journal_v1.open_h1_external_process_journal_v1(
                journal_directory=directory,
                attempt_identity_id=_id("attempt"),
                route_attempt_id=_id("route"),
                build_epoch_id=_id("epoch"),
                supervisor_creator_channel=supervisor,
                broker_creator_channel=duplicate,
            )
        duplicate_endpoint.close()
        other_receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal_v1.prebind_h1_external_process_creator_channel_v1(
                kind=journal_v1.CreatorChannelKindV1.BROKER_CREATOR,
                channel_identity_id=_id("no-passcred"),
                endpoint=other_receiver,
            )
    finally:
        for endpoint in (receiver, sender, other_receiver, other_sender):
            endpoint.close()


def test_real_pidfd_scm_ack_death_poll_and_optional_direct_reap_are_separate(
    tmp_path: Path,
) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "real-pidfd"
    )
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through parent observations
        try:
            os.close(write_fd)
            # The child must not retain guardian receive endpoints.
            for channel in journal._channels.values():  # noqa: SLF001
                try:
                    channel._endpoint.close()  # noqa: SLF001
                except OSError:
                    pass
            chunks = []
            while True:
                chunk = os.read(read_fd, 4096)
                if not chunk:
                    break
                chunks.append(chunk)
            os.close(read_fd)
            import json

            permit = json.loads(b"".join(chunks).decode())
            pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
            journal_v1.send_h1_external_process_pidfd_escrow_v1(
                endpoint=supervisor_sender,
                permit_document=permit,
                pidfd=pidfd,
                shared_pid_cell_observed_pid=os.getpid(),
            )
            _drain_control(supervisor_sender)
            os.close(pidfd)
            supervisor_sender.close()
            broker_sender.close()
            os._exit(7)
        except BaseException:
            os._exit(91)
    os.close(read_fd)
    try:
        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "real-supervisor"
        )
        raw_permit = canonical_json_bytes(permit.to_document())
        assert os.write(write_fd, raw_permit) == len(raw_permit)
        os.close(write_fd)
        write_fd = -1
        receipt = journal.receive_pidfd_escrow(
            slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
        )
        receipt_document = receipt.to_document()
        assert receipt_document["fdinfo_pid"] == child
        assert receipt_document["shared_pid_cell_observed_pid"] == child
        assert receipt_document["sender_pid"] == child
        assert receipt_document["pidfd_rights_count"] == 1
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal.authorize_creator_release(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
            )
        ack = journal.acknowledge_escrow(
            slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
        )
        release = journal.authorize_creator_release(
            slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
        )
        assert ack.to_document()["creator_release_authorized"] is False
        assert release.to_document()["ack_persisted_and_sent_before_release"] is True
        death = journal.observe_pidfd_death(
            slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR,
            timeout_milliseconds=5_000,
        )
        assert death.to_document()["exit_status_observed"] is False
        reap = journal.consume_guardian_direct_parent_reap_optional(
            slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
        )
        reap_document = reap.to_document()
        assert reap_document["exit_status_consumed"] is True
        assert reap_document["si_status"] == 7
        assert reap_document["external_process_death_observation_id"] == death.record_id
        assert reap_document["normal_guardian_reap_present"] is False
        with pytest.raises(ChildProcessError):
            os.waitpid(child, os.WNOHANG)
        journal.close_crash(reason_code="TEST_AFTER_DIRECT_REAP")
    finally:
        if write_fd >= 0:
            os.close(write_fd)
        supervisor_sender.close()
        broker_sender.close()
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(child, 0)
        except ChildProcessError:
            pass


@pytest.mark.parametrize("attack", ["NO_RIGHT", "TWO_RIGHTS", "CROSSED_CGROUP", "CROSSED_START"])
def test_pidfd_escrow_packet_attacks_fail_closed(tmp_path: Path, attack: str) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, f"attack-{attack.lower()}"
    )
    pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
    duplicate = os.dup(pidfd)
    try:
        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, f"attack-{attack}"
        )
        packet = _packet(permit.to_document(), os.getpid())
        rights = (pidfd,)
        if attack == "NO_RIGHT":
            rights = ()
        elif attack == "TWO_RIGHTS":
            rights = (pidfd, duplicate)
        elif attack == "CROSSED_CGROUP":
            packet["cgroup_identity_id"] = _id("foreign-cgroup")
        elif attack == "CROSSED_START":
            packet["process_start_ticks"] = int(packet["process_start_ticks"]) + 1
        _send_packet(supervisor_sender, packet, rights)
        with pytest.raises(journal_v1.ConstructionK7H1ExternalProcessJournalV1Error):
            journal.receive_pidfd_escrow(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
            )
        journal.close_crash(reason_code=f"ATTACK_{attack}")
    finally:
        os.close(pidfd)
        os.close(duplicate)
        supervisor_sender.close()
        broker_sender.close()


def test_wrong_scm_sender_cannot_self_escrow_another_process(tmp_path: Path) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "wrong-sender"
    )
    child = os.fork()
    if child == 0:  # pragma: no cover
        time.sleep(30)
        os._exit(0)
    pidfd = journal_v1._pidfd_open(child)  # noqa: SLF001
    try:
        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "wrong-sender"
        )
        packet = _packet(permit.to_document(), child)
        # Kernel credentials name this parent, while the escrow pidfd names child.
        _send_packet(supervisor_sender, packet, (pidfd,))
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="self-escrow sender",
        ):
            journal.receive_pidfd_escrow(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
            )
        journal.close_crash(reason_code="WRONG_SCM_SENDER")
    finally:
        os.close(pidfd)
        supervisor_sender.close()
        broker_sender.close()
        os.kill(child, signal.SIGKILL)
        os.waitpid(child, 0)


def test_persisted_but_unsent_ack_can_close_as_noncertificate_prefix(
    tmp_path: Path,
) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "ack-send-failure"
    )
    pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
    try:
        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "ack-send-failure"
        )
        journal_v1.send_h1_external_process_pidfd_escrow_v1(
            endpoint=supervisor_sender,
            permit_document=permit.to_document(),
            pidfd=pidfd,
            shared_pid_cell_observed_pid=os.getpid(),
        )
        journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        supervisor_sender.close()
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="ACK could not be sent",
        ):
            journal.acknowledge_escrow(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
            )
        closure = journal.close_crash(reason_code="ACK_SEND_FAILED")
        prefix = closure.to_document()["slot_prefix"]
        assert prefix[0]["stage"] == "ACK_PERSISTED_SEND_FAILED"
        assert prefix[0]["ack_id"] is not None
        assert prefix[0]["release_preparation_id"] is None
        assert prefix[0]["release_authorization_id"] is None
        assert closure.to_document()["crash_cleanup_complete"] is False
    finally:
        os.close(pidfd)
        supervisor_sender.close()
        broker_sender.close()


def test_release_send_failure_remains_prepared_unsent(tmp_path: Path) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "release-send-failure"
    )
    pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
    try:
        _intent, permit = _prepare(
            journal,
            journal_v1.ExternalProcessSlotV1.SUPERVISOR,
            "release-send-failure",
        )
        journal_v1.send_h1_external_process_pidfd_escrow_v1(
            endpoint=supervisor_sender,
            permit_document=permit.to_document(),
            pidfd=pidfd,
            shared_pid_cell_observed_pid=os.getpid(),
        )
        journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        # Consume the ACK, then make the release send fail after PREPARED persists.
        import json

        ack = json.loads(supervisor_sender.recv(journal_v1.MAX_PACKET_BYTES).decode())
        assert ack["schema"] == "acfqp.k7_h1_external_process_guardian_ack.v1"
        supervisor_sender.close()
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="prepared creator release could not be sent",
        ):
            journal.authorize_creator_release(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR
            )
        closure = journal.close_crash(reason_code="RELEASE_SEND_FAILED")
        row = closure.to_document()["slot_prefix"][0]
        assert row["stage"] == "RELEASE_PREPARED_UNSENT"
        assert row["release_preparation_id"] is not None
        assert row["release_authorization_id"] is None
    finally:
        os.close(pidfd)
        supervisor_sender.close()
        broker_sender.close()


def test_fork_child_closes_guardian_copies_but_sender_endpoints_survive(
    tmp_path: Path,
) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "atfork"
    )
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:  # pragma: no cover - parent checks the one-byte result
        try:
            os.close(read_fd)
            guardian_closed = (
                journal._directory_fd == -1  # noqa: SLF001
                and not journal._record_fds  # noqa: SLF001
                and all(
                    channel._endpoint.fileno() == -1  # noqa: SLF001
                    for channel in journal._channels.values()  # noqa: SLF001
                )
                and journal._poisoned  # noqa: SLF001
            )
            senders_live = (
                supervisor_sender.fileno() >= 0 and broker_sender.fileno() >= 0
            )
            rejected = False
            try:
                journal.prepare_intent(
                    slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR,
                    launch_identity_id=_id("fork-launch"),
                    cgroup_identity_id=_id("fork-cgroup"),
                    shared_pid_cell_identity_id=_id("fork-cell"),
                )
            except journal_v1.ConstructionK7H1ExternalProcessJournalV1Error:
                rejected = True
            os.write(write_fd, b"1" if guardian_closed and senders_live and rejected else b"0")
            os.close(write_fd)
            supervisor_sender.close()
            broker_sender.close()
            os._exit(0)
        except BaseException:
            os._exit(95)
    os.close(write_fd)
    try:
        assert os.read(read_fd, 1) == b"1"
        os.close(read_fd)
        read_fd = -1
        waited, status = os.waitpid(child, 0)
        assert waited == child and os.waitstatus_to_exitcode(status) == 0
        # Parent journal and retained record FD remain live and usable.
        assert journal._record_fds  # noqa: SLF001
        _prepare(journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "fork-parent")
        journal.close_crash(reason_code="ATFORK_PARENT_UNCHANGED")
    finally:
        if read_fd >= 0:
            os.close(read_fd)
        supervisor_sender.close()
        broker_sender.close()
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(child, 0)
        except ChildProcessError:
            pass


def test_close_failure_retains_same_ofd_witness_then_close_only_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "close-quarantine"
    )
    pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
    _intent, permit = _prepare(
        journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "close-quarantine"
    )
    journal_v1.send_h1_external_process_pidfd_escrow_v1(
        endpoint=supervisor_sender,
        permit_document=permit.to_document(),
        pidfd=pidfd,
        shared_pid_cell_observed_pid=os.getpid(),
    )
    journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    journal.authorize_creator_release(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    _drain_control(supervisor_sender)
    retained_pidfd = journal._states[  # noqa: SLF001
        journal_v1.ExternalProcessSlotV1.SUPERVISOR
    ].pidfd
    assert retained_pidfd is not None
    real_close = os.close
    failed = False

    def injected_close(descriptor: int) -> None:
        nonlocal failed
        if descriptor == retained_pidfd and not failed:
            failed = True
            raise OSError(5, "injected retained-pidfd close failure")
        real_close(descriptor)

    monkeypatch.setattr(journal_v1.os, "close", injected_close)
    closure = journal.close_crash(reason_code="INJECTED_CLOSE_FAILURE")
    assert closure.to_document()["crash_cleanup_complete"] is False
    assert journal.close_quarantine_count() == 1
    entry = next(iter(journal._close_quarantine.values()))  # noqa: SLF001
    assert entry.canonical_descriptor == retained_pidfd
    assert journal_v1._same_open_file_description_for_close(  # noqa: SLF001
        retained_pidfd, entry.witness_descriptor
    )
    monkeypatch.setattr(journal_v1.os, "close", real_close)
    assert journal.retry_quarantined_close() == 0
    real_close(pidfd)
    supervisor_sender.close()
    broker_sender.close()


def test_same_target_new_ofd_reuse_after_close_error_is_never_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "same-target-new-ofd"
    )
    sender_pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
    _intent, permit = _prepare(
        journal,
        journal_v1.ExternalProcessSlotV1.SUPERVISOR,
        "same-target-new-ofd",
    )
    journal_v1.send_h1_external_process_pidfd_escrow_v1(
        endpoint=supervisor_sender,
        permit_document=permit.to_document(),
        pidfd=sender_pidfd,
        shared_pid_cell_observed_pid=os.getpid(),
    )
    journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    journal.authorize_creator_release(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
    _drain_control(supervisor_sender)
    retained_pidfd = journal._states[  # noqa: SLF001
        journal_v1.ExternalProcessSlotV1.SUPERVISOR
    ].pidfd
    assert retained_pidfd is not None
    frozen_identity = journal_v1._identity(retained_pidfd)  # noqa: SLF001
    real_close = journal_v1._OS_CLOSE  # noqa: SLF001
    replacement = -1
    attacked = False

    def close_reopen_same_target_then_raise(descriptor: int) -> None:
        nonlocal attacked, replacement
        if descriptor != retained_pidfd or attacked:
            real_close(descriptor)
            return
        attacked = True
        entry = next(
            item
            for item in journal._close_quarantine.values()  # noqa: SLF001
            if item.canonical_descriptor == retained_pidfd
        )
        assert entry.witness_descriptor != retained_pidfd
        assert not os.get_inheritable(entry.witness_descriptor)
        assert journal_v1._same_open_file_description_for_close(  # noqa: SLF001
            retained_pidfd, entry.witness_descriptor
        )
        real_close(descriptor)
        opened = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
        if opened != retained_pidfd:
            os.dup2(opened, retained_pidfd, inheritable=False)
            real_close(opened)
        replacement = retained_pidfd
        assert journal_v1._identity(replacement) == frozen_identity  # noqa: SLF001
        assert not journal_v1._same_open_file_description_for_close(  # noqa: SLF001
            replacement, sender_pidfd
        )
        raise OSError(5, "injected same-target new-OFD reuse")

    try:
        monkeypatch.setattr(journal_v1.os, "close", close_reopen_same_target_then_raise)
        journal.close_crash(reason_code="SAME_TARGET_NEW_OFD_REUSE")
        assert attacked is True
        assert replacement == retained_pidfd
        assert journal.close_quarantine_count() == 0
        assert journal_v1._identity(replacement) == frozen_identity  # noqa: SLF001
        assert journal_v1._pidfd_pid(replacement) == os.getpid()  # noqa: SLF001
        monkeypatch.setattr(journal_v1.os, "close", real_close)
        assert journal.retry_quarantined_close() == 0
        assert journal_v1._pidfd_pid(replacement) == os.getpid()  # noqa: SLF001
    finally:
        monkeypatch.setattr(journal_v1.os, "close", real_close)
        if replacement >= 0:
            real_close(replacement)
        real_close(sender_pidfd)
        supervisor_sender.close()
        broker_sender.close()


def _write_framed(descriptor: int, raw: bytes) -> None:
    framed = len(raw).to_bytes(4, "big") + raw
    offset = 0
    while offset < len(framed):
        written = os.write(descriptor, framed[offset:])
        assert written > 0
        offset += written


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            raise EOFError("framed control pipe closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_framed(descriptor: int) -> bytes:
    size = int.from_bytes(_read_exact(descriptor, 4), "big")
    if not 0 < size <= journal_v1.MAX_PACKET_BYTES:
        raise ValueError("framed permit extent changed")
    return _read_exact(descriptor, size)


def test_real_two_creator_channels_complete_ordered_five_slot_record_prefix(
    tmp_path: Path,
) -> None:
    import json

    journal, _directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "five-slot"
    )
    broker_control_read, broker_control_write = os.pipe2(os.O_CLOEXEC)
    probe = os.fork()
    if probe == 0:  # pragma: no cover - parent validates its pidfd
        try:
            os.close(broker_control_read)
            os.close(broker_control_write)
            supervisor_sender.close()
            broker_sender.close()
            for channel in journal._channels.values():  # noqa: SLF001
                channel._endpoint.close()  # noqa: SLF001
            signal.pause()
        finally:
            os._exit(0)
    broker = os.fork()
    if broker == 0:  # pragma: no cover - asserted by guardian receipt joins
        try:
            os.close(broker_control_write)
            supervisor_sender.close()
            for channel in journal._channels.values():  # noqa: SLF001
                channel._endpoint.close()  # noqa: SLF001
            for _slot in ("WORKER", "BUSINESS"):
                permit = json.loads(_read_framed(broker_control_read).decode())
                role = os.fork()
                if role == 0:
                    broker_sender.close()
                    os.close(broker_control_read)
                    signal.pause()
                    os._exit(0)
                role_pidfd = journal_v1._pidfd_open(role)  # noqa: SLF001
                journal_v1.send_h1_external_process_pidfd_escrow_v1(
                    endpoint=broker_sender,
                    permit_document=permit,
                    pidfd=role_pidfd,
                    shared_pid_cell_observed_pid=role,
                )
                _drain_control(broker_sender)
                os.close(role_pidfd)
                os.kill(role, signal.SIGKILL)
                receipt_document, death_document = _receive_death_control(
                    broker_sender
                )
                journal_v1.consume_and_send_h1_external_process_creator_reap_report_v1(
                    endpoint=broker_sender,
                    receipt_document=receipt_document,
                    death_observation_document=death_document,
                    pid=role,
                )
            os.close(broker_control_read)
            broker_sender.close()
            os._exit(0)
        except BaseException:
            os._exit(93)
    os.close(broker_control_read)
    broker_sender.close()
    original_pidfds: list[int] = []
    try:
        # SUPERVISOR is a self-escrow in this local protocol test.  This is not
        # an authenticated-supervisor integration claim.
        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.SUPERVISOR, "five-supervisor"
        )
        supervisor_pidfd = journal_v1._pidfd_open(os.getpid())  # noqa: SLF001
        original_pidfds.append(supervisor_pidfd)
        journal_v1.send_h1_external_process_pidfd_escrow_v1(
            endpoint=supervisor_sender,
            permit_document=permit.to_document(),
            pidfd=supervisor_pidfd,
            shared_pid_cell_observed_pid=os.getpid(),
        )
        journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        journal.authorize_creator_release(slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR)
        _drain_control(supervisor_sender)

        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.PIDFD_PROBE, "five-probe"
        )
        probe_pidfd = journal_v1._pidfd_open(probe)  # noqa: SLF001
        original_pidfds.append(probe_pidfd)
        journal_v1.send_h1_external_process_pidfd_escrow_v1(
            endpoint=supervisor_sender,
            permit_document=permit.to_document(),
            pidfd=probe_pidfd,
            shared_pid_cell_observed_pid=probe,
        )
        journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE)
        journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE)
        journal.authorize_creator_release(slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE)
        _drain_control(supervisor_sender)
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="PIDFD_PROBE death",
        ):
            _prepare(
                journal,
                journal_v1.ExternalProcessSlotV1.BROKER,
                "five-broker-too-early",
            )
        os.kill(probe, signal.SIGKILL)
        journal.observe_pidfd_death(
            slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE,
            timeout_milliseconds=5_000,
        )
        probe_receipt, probe_death = _receive_death_control(supervisor_sender)
        forged_reporter = os.fork()
        if forged_reporter == 0:  # pragma: no cover - SCM PID checked by parent
            try:
                raw = canonical_json_bytes(
                    _creator_reap_packet(probe_receipt, probe_death)
                )
                supervisor_sender.send(raw)
                os._exit(0)
            except BaseException:
                os._exit(96)
        waited_forged, forged_status = os.waitpid(forged_reporter, 0)
        assert waited_forged == forged_reporter
        assert os.waitstatus_to_exitcode(forged_status) == 0
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="SCM sender identity",
        ):
            journal.receive_creator_reap_report(
                slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE
            )
        journal_v1.consume_and_send_h1_external_process_creator_reap_report_v1(
            endpoint=supervisor_sender,
            receipt_document=probe_receipt,
            death_observation_document=probe_death,
            pid=probe,
        )
        journal.receive_creator_reap_report(
            slot=journal_v1.ExternalProcessSlotV1.PIDFD_PROBE
        )

        _intent, permit = _prepare(
            journal, journal_v1.ExternalProcessSlotV1.BROKER, "five-broker"
        )
        broker_pidfd = journal_v1._pidfd_open(broker)  # noqa: SLF001
        original_pidfds.append(broker_pidfd)
        journal_v1.send_h1_external_process_pidfd_escrow_v1(
            endpoint=supervisor_sender,
            permit_document=permit.to_document(),
            pidfd=broker_pidfd,
            shared_pid_cell_observed_pid=broker,
        )
        journal.receive_pidfd_escrow(slot=journal_v1.ExternalProcessSlotV1.BROKER)
        journal.acknowledge_escrow(slot=journal_v1.ExternalProcessSlotV1.BROKER)
        journal.authorize_creator_release(slot=journal_v1.ExternalProcessSlotV1.BROKER)
        _drain_control(supervisor_sender)

        for slot in (
            journal_v1.ExternalProcessSlotV1.WORKER,
            journal_v1.ExternalProcessSlotV1.BUSINESS,
        ):
            _intent, permit = _prepare(journal, slot, f"five-{slot.value.lower()}")
            _write_framed(broker_control_write, canonical_json_bytes(permit.to_document()))
            receipt = journal.receive_pidfd_escrow(slot=slot)
            assert receipt.to_document()["sender_pid"] == broker
            journal.acknowledge_escrow(slot=slot)
            journal.authorize_creator_release(slot=slot)
            if slot is journal_v1.ExternalProcessSlotV1.WORKER:
                with pytest.raises(
                    journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
                    match="WORKER death",
                ):
                    _prepare(
                        journal,
                        journal_v1.ExternalProcessSlotV1.BUSINESS,
                        "five-business-too-early",
                    )
            journal.observe_pidfd_death(slot=slot, timeout_milliseconds=5_000)
            journal.receive_creator_reap_report(slot=slot)
        os.close(broker_control_write)
        broker_control_write = -1
        journal.observe_pidfd_death(
            slot=journal_v1.ExternalProcessSlotV1.BROKER,
            timeout_milliseconds=5_000,
        )
        broker_receipt, broker_death = _receive_death_control(supervisor_sender)
        journal_v1.consume_and_send_h1_external_process_creator_reap_report_v1(
            endpoint=supervisor_sender,
            receipt_document=broker_receipt,
            death_observation_document=broker_death,
            pid=broker,
        )
        journal.receive_creator_reap_report(
            slot=journal_v1.ExternalProcessSlotV1.BROKER
        )
        with pytest.raises(ChildProcessError):
            os.waitpid(broker, os.WNOHANG)
        closure = journal.close_crash(reason_code="FIVE_SLOT_PREFIX_ONLY")
        prefix = closure.to_document()["slot_prefix"]
        assert [row["slot"] for row in prefix] == [slot.value for slot in journal_v1.SLOT_ORDER]
        assert prefix[0]["stage"] == "CREATOR_RELEASE_AUTHORIZED"
        assert all(
            row["stage"] == "CREATOR_REAP_REPORTED" for row in prefix[1:]
        )
        assert len({row["observed_pid"] for row in prefix}) == 5
        assert closure.to_document()["process_launch_counter_authorized"] is False
    finally:
        if broker_control_write >= 0:
            os.close(broker_control_write)
        for descriptor in original_pidfds:
            try:
                os.close(descriptor)
            except OSError:
                pass
        supervisor_sender.close()
        for pid in (probe, broker):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass


def test_foreign_journal_inventory_mutation_fails_before_next_record(tmp_path: Path) -> None:
    journal, directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "inventory"
    )
    try:
        foreign = directory / "foreign"
        foreign.touch(mode=0o400)
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="inventory changed",
        ):
            journal.prepare_intent(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR,
                launch_identity_id=_id("inventory-launch"),
                cgroup_identity_id=_id("inventory-cgroup"),
                shared_pid_cell_identity_id=_id("inventory-cell"),
            )
        foreign.unlink()
        journal.close_crash(reason_code="RESTORED_AFTER_INVENTORY_ATTACK")
    finally:
        supervisor_sender.close()
        broker_sender.close()


def test_existing_persisted_record_mutation_fails_before_next_record(
    tmp_path: Path,
) -> None:
    journal, directory, supervisor_sender, broker_sender = _open_case(
        tmp_path, "record-mutation"
    )
    genesis_path = next(directory.iterdir())
    original = genesis_path.read_bytes()
    try:
        os.chmod(genesis_path, 0o600)
        genesis_path.write_bytes(original + b"x")
        os.chmod(genesis_path, 0o400)
        with pytest.raises(
            journal_v1.ConstructionK7H1ExternalProcessJournalV1Error,
            match="identity or (extent|bytes) changed",
        ):
            journal.prepare_intent(
                slot=journal_v1.ExternalProcessSlotV1.SUPERVISOR,
                launch_identity_id=_id("mutation-launch"),
                cgroup_identity_id=_id("mutation-cgroup"),
                shared_pid_cell_identity_id=_id("mutation-cell"),
            )
        os.chmod(genesis_path, 0o600)
        genesis_path.write_bytes(original)
        os.chmod(genesis_path, 0o400)
        journal.close_crash(reason_code="RESTORED_AFTER_TEST_MUTATION")
    finally:
        supervisor_sender.close()
        broker_sender.close()
