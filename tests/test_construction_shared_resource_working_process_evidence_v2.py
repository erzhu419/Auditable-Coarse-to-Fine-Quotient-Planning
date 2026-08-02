from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
from typing import Any

import pytest

from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_working_process_evidence_v2 as evidence_v2
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def test_working_process_domains_are_central_and_role_separated() -> None:
    assert set(evidence_v2.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert len(evidence_v2.REQUESTED_PHASE3E_DOMAIN_TAGS) == len(
        set(evidence_v2.REQUESTED_PHASE3E_DOMAIN_TAGS)
    )


def _id(label: str) -> str:
    return hashlib.sha256(b"acfqp:test:working-process:v2\x00" + label.encode()).hexdigest()


def _binding() -> ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
    return ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        _id("request"),
        _id("route"),
        _id("execution-spec"),
        _id("session-nonce"),
    )


def _postexec_filter_sha256() -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            [list(row) for row in sandbox_v2.postexec_seccomp_filter_rows_v2()]
        )
    ).hexdigest()


class _FakeCgroup:
    def __init__(self, root: Path) -> None:
        root.mkdir()
        self.root = root
        self.peak_path = root / "memory.peak"
        self.procs_path = root / "cgroup.procs"
        self.stat_path = root / "cgroup.stat"
        self.peak_path.write_bytes(b"0\n")
        self.procs_path.write_bytes(b"")
        self.stat_path.write_text(
            "nr_descendants 0\nnr_dying_descendants 0\n",
            encoding="ascii",
        )
        self.peak_fd = os.open(
            self.peak_path,
            os.O_RDWR | os.O_CLOEXEC,
        )
        self.directory_fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )

    def set_procs(self, *pids: int) -> None:
        self.procs_path.write_text(
            "".join(f"{pid}\n" for pid in pids),
            encoding="ascii",
        )

    def set_peak(self, value: int) -> None:
        raw = f"{value}\n".encode("ascii")
        os.pwrite(self.peak_fd, raw, 0)
        os.ftruncate(self.peak_fd, len(raw))

    def close(self) -> None:
        for descriptor in (self.peak_fd, self.directory_fd):
            if descriptor >= 0:
                os.close(descriptor)
        self.peak_fd = -1
        self.directory_fd = -1


class _Child:
    def __init__(
        self,
        *,
        binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
        role: str,
    ) -> None:
        if not hasattr(os, "pidfd_open") or not hasattr(os, "P_PIDFD"):
            pytest.skip("pidfd lifecycle support is unavailable")
        if role == "WORKER":
            frame_role = ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY
            payload: dict[str, Any] = {"worker_replay_id": _id("worker-replay")}
        else:
            frame_role = ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT
            payload = {"business_result_id": _id("business-result")}
        raw = ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
            binding=binding,
            role=frame_role,
            payload=payload,
        )
        broker, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        broker.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        broker.set_inheritable(False)
        child.set_inheritable(False)
        gate_read, gate_write = os.pipe2(os.O_CLOEXEC)
        pid = os.fork()
        if pid == 0:  # pragma: no cover - fixed child syscall path
            try:
                broker.close()
                os.close(gate_write)
                sent = child.send(raw)
                if sent != len(raw):
                    os._exit(91)
                os.read(gate_read, 1)
                os._exit(0)
            except BaseException:
                os._exit(92)
        child.close()
        os.close(gate_read)
        self.role = role
        self.frame_role = frame_role
        self.binding = binding
        self.broker = broker
        self.pid = pid
        self.pidfd = os.pidfd_open(pid, 0)
        self.gate_write = gate_write
        self.reaped = False

    def observation(self) -> channel_v2.K7AuthenticatedBrokerFrameV2:
        return channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
            endpoint=self.broker,
            expected_pid=self.pid,
            expected_pidfd=self.pidfd,
            expected_binding=self.binding,
            expected_role=self.frame_role,
        )

    def release(self) -> None:
        if self.gate_write >= 0:
            os.write(self.gate_write, b"x")
            os.close(self.gate_write)
            self.gate_write = -1

    def close_after_session_reap(self) -> None:
        self.reaped = True
        self.close()

    def close(self) -> None:
        self.broker.close()
        if self.gate_write >= 0:
            try:
                os.write(self.gate_write, b"x")
            except OSError:
                pass
            os.close(self.gate_write)
            self.gate_write = -1
        if not self.reaped and self.pid > 0:
            try:
                os.kill(self.pid, 9)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass
            self.reaped = True
        if self.pidfd >= 0:
            os.close(self.pidfd)
            self.pidfd = -1


def _open_session(cgroup: _FakeCgroup) -> evidence_v2.WorkingProcessEvidenceSessionV2:
    return evidence_v2.open_working_process_evidence_session_v2(
        live_envelope_id=_id("live-envelope"),
        occurrence_id=_id("occurrence"),
        route_attempt_id=_id("attempt"),
        decision_point_id=_id("decision"),
        measurement_window_id=_id("window"),
        measurement_start_sequence=17,
        memory_peak_fd=cgroup.peak_fd,
        cgroup_directory_fd=cgroup.directory_fd,
    )


def _record_role(
    session: evidence_v2.WorkingProcessEvidenceSessionV2,
    cgroup: _FakeCgroup,
    child: _Child,
    all_pids: tuple[int, ...],
) -> None:
    cgroup.set_procs(*all_pids)
    session.record_native_positive_clone_v2(
        role=child.role,
        expected_pid=child.pid,
        pidfd=child.pidfd,
        native_clone_result=child.pid,
        native_write_ahead_edge=1,
    )
    session.record_postexec_no_spawn_v2(
        role=child.role,
        attestation_source_id=_id(f"no-spawn-{child.role}"),
        attested_pid=child.pid,
        attested_pidfd=child.pidfd,
        postexec_filter_sha256=_postexec_filter_sha256(),
        clone_fork_vfork_denied=True,
        execve_execveat_denied=True,
        seccomp_tsync_completed=True,
    )
    session.record_authenticated_frame_v2(child.observation())


def _raw_arguments(
    bundle: evidence_v2.WorkingProcessRawEvidenceBundleV2,
) -> dict[str, bytes]:
    return {
        "cgroup_empty_bytes": bundle.cgroup_empty_component.raw_bytes,
        "memory_peak_post_read_bytes": bundle.memory_post_component.raw_bytes,
        "memory_peak_pre_read_bytes": bundle.memory_pre_component.raw_bytes,
        "same_ofd_attestation_bytes": bundle.same_ofd_component.raw_bytes,
        "cutoff_attestation_bytes": bundle.cutoff_component.raw_bytes,
        "no_spawn_attestation_bytes": bundle.no_spawn_component.raw_bytes,
        "pidfd_reap_attestation_bytes": bundle.pidfd_reap_component.raw_bytes,
        "process_lifecycle_journal_bytes": bundle.process_journal_component.raw_bytes,
    }


def _tamper(raw: bytes, mutator: Any) -> bytes:
    document = loads_canonical_json(raw)
    assert type(document) is dict
    mutator(document)
    return canonical_json_bytes(document)


def _exact_bundle(tmp_path: Path) -> evidence_v2.WorkingProcessRawEvidenceBundleV2:
    cgroup = _FakeCgroup(tmp_path / "cgroup")
    session = _open_session(cgroup)
    binding = _binding()
    worker = _Child(binding=binding, role="WORKER")
    business = _Child(binding=binding, role="BUSINESS")
    children = (worker, business)
    try:
        cgroup.set_procs(worker.pid)
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="PID/pidfd edge",
        ):
            session.record_native_positive_clone_v2(
                role="WORKER",
                expected_pid=business.pid,
                pidfd=worker.pidfd,
                native_clone_result=business.pid,
                native_write_ahead_edge=1,
            )
        session.record_native_positive_clone_v2(
            role="WORKER",
            expected_pid=worker.pid,
            pidfd=worker.pidfd,
            native_clone_result=worker.pid,
            native_write_ahead_edge=1,
        )
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="forged|crossed",
        ):
            session.record_postexec_no_spawn_v2(
                role="WORKER",
                attestation_source_id=_id("crossed-pidfd"),
                attested_pid=worker.pid,
                attested_pidfd=business.pidfd,
                postexec_filter_sha256=_postexec_filter_sha256(),
                clone_fork_vfork_denied=True,
                execve_execveat_denied=True,
                seccomp_tsync_completed=True,
            )
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="forged|crossed",
        ):
            session.record_postexec_no_spawn_v2(
                role="WORKER",
                attestation_source_id=_id("forged-no-spawn"),
                attested_pid=worker.pid,
                attested_pidfd=worker.pidfd,
                postexec_filter_sha256=_postexec_filter_sha256(),
                clone_fork_vfork_denied=False,
                execve_execveat_denied=True,
                seccomp_tsync_completed=True,
            )
        session.record_postexec_no_spawn_v2(
            role="WORKER",
            attestation_source_id=_id("no-spawn-WORKER"),
            attested_pid=worker.pid,
            attested_pidfd=worker.pidfd,
            postexec_filter_sha256=_postexec_filter_sha256(),
            clone_fork_vfork_denied=True,
            execve_execveat_denied=True,
            seccomp_tsync_completed=True,
        )
        session.record_authenticated_frame_v2(worker.observation())
        _record_role(
            session,
            cgroup,
            business,
            (worker.pid, business.pid),
        )
        session.record_output_committed_v2(output_commit_id=_id("output"))
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="complete two-role lifecycle",
        ):
            session.close_exact_v2()
        for child in children:
            child.release()
        session.reap_direct_child_v2(role="WORKER")
        session.reap_direct_child_v2(role="BUSINESS")
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="not empty",
        ):
            session.close_exact_v2()
        cgroup.set_procs()
        cgroup.set_peak(8192)
        bundle = session.close_exact_v2()
        for child in children:
            child.close_after_session_reap()
        return bundle
    finally:
        session.close()
        for child in children:
            child.close()
        cgroup.close()


def test_exact_same_ofd_peak_and_two_native_launches_replay_raw_only(
    tmp_path: Path,
) -> None:
    bundle = _exact_bundle(tmp_path)
    replay = bundle.raw_replay
    assert replay.memory_peak_max_bytes == 8192
    assert replay.process_launches_sum == 2
    assert replay.process_launches_lower_bound == 2
    assert replay.semantic_source_verified is False
    assert replay.counter_record_issuance_authorized is False
    assert evidence_v2.replay_working_process_raw_evidence_v2(
        **_raw_arguments(bundle)
    ) == replay

    contracts = {
        item.path: item
        for item in resolution_v2.official_shared_resource_resolution_catalogue_v2()
    }
    sources = {item.path: item for item in bundle.live_sources_v2()}
    assert set(sources) == {evidence_v2.MEMORY_PATH, evidence_v2.PROCESS_PATH}
    for path, source in sources.items():
        assert tuple(
            (item.component_key, item.source_schema_id)
            for item in source.components
        ) == tuple(
            (item.component_key, item.source_schema_id)
            for item in contracts[path].required_components
        )
    # A third/stale memory read cannot be obtained from a closed session.  The
    # only exact post read emitted by a complete session has ordinal two.
    closed_cgroup = _FakeCgroup(tmp_path / "closed-cgroup")
    bundle_session = _open_session(closed_cgroup)
    try:
        prefix = bundle_session.close_failure_prefix_v2(failure_reason="closed")
        assert prefix.raw_replay.memory_peak_max_bytes is None
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="cannot be reused",
        ):
            bundle_session.close_failure_prefix_v2(failure_reason="second-read")
    finally:
        bundle_session.close()
        closed_cgroup.close()


def test_failure_prefix_keeps_positive_lower_bound_but_cannot_be_exact(
    tmp_path: Path,
) -> None:
    cgroup = _FakeCgroup(tmp_path / "cgroup")
    session = _open_session(cgroup)
    child = _Child(binding=_binding(), role="WORKER")
    try:
        cgroup.set_procs(child.pid)
        session.record_native_positive_clone_v2(
            role="WORKER",
            expected_pid=child.pid,
            pidfd=child.pidfd,
            native_clone_result=child.pid,
            native_write_ahead_edge=1,
        )
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="duplicated",
        ):
            session.record_native_positive_clone_v2(
                role="WORKER",
                expected_pid=child.pid,
                pidfd=child.pidfd,
                native_clone_result=child.pid,
                native_write_ahead_edge=1,
            )
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="complete two-role lifecycle",
        ):
            session.close_exact_v2()
        prefix = session.close_failure_prefix_v2(failure_reason="worker bootstrap failed")
        assert prefix.raw_replay.process_launches_lower_bound == 1
        assert prefix.raw_replay.process_launches_sum is None
        assert prefix.raw_replay.memory_peak_max_bytes is None
        assert prefix.exact_values_eligible_for_semantic_replay is False
        assert evidence_v2.replay_working_process_raw_evidence_v2(
            **_raw_arguments(prefix)
        ) == prefix.raw_replay
    finally:
        session.close()
        child.close()
        cgroup.close()


def test_retained_memory_peak_ofd_replacement_fails_closed(tmp_path: Path) -> None:
    cgroup = _FakeCgroup(tmp_path / "cgroup")
    session = _open_session(cgroup)
    # Reopen the same inode to get a different open-file description.  An
    # inode-only check would miss this replacement.
    replacement = os.open(cgroup.peak_path, os.O_RDWR | os.O_CLOEXEC)
    try:
        os.dup2(replacement, session._peak_fd, inheritable=False)  # noqa: SLF001
        with pytest.raises(
            evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
            match="replaced",
        ):
            session.close_failure_prefix_v2(failure_reason="attacked")
    finally:
        os.close(replacement)
        session.close()
        cgroup.close()


def test_raw_replay_rejects_stale_read_pid_scm_crossing_and_cutoff_hiding(
    tmp_path: Path,
) -> None:
    bundle = _exact_bundle(tmp_path)
    original = _raw_arguments(bundle)

    stale = dict(original)
    stale["memory_peak_post_read_bytes"] = _tamper(
        stale["memory_peak_post_read_bytes"],
        lambda document: document.__setitem__("read_ordinal", 3),
    )
    with pytest.raises(
        evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
        match="same-OFD|post-read",
    ):
        evidence_v2.replay_working_process_raw_evidence_v2(**stale)

    crossed = dict(original)

    def cross_sender(document: dict[str, Any]) -> None:
        for event in document["events"]:
            if event["kind"] == "AUTHENTICATED_SCM_FRAME":
                event["scm_sender_pid"] += 1
                payload = dict(event)
                payload.pop("raw_event_id")
                event["raw_event_id"] = content_id(
                    evidence_v2.WORKING_PROCESS_EVENT_V2_DOMAIN,
                    payload,
                )
                return
        raise AssertionError("authenticated event absent")

    crossed["process_lifecycle_journal_bytes"] = _tamper(
        crossed["process_lifecycle_journal_bytes"],
        cross_sender,
    )
    with pytest.raises(
        evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
        match="SCM frame crossed",
    ):
        evidence_v2.replay_working_process_raw_evidence_v2(**crossed)

    hidden_documents = {key: loads_canonical_json(raw) for key, raw in original.items()}
    assert all(type(document) is dict for document in hidden_documents.values())
    for document in hidden_documents.values():
        document["operational_cutoff_sequence"] -= 1
    journal = hidden_documents["process_lifecycle_journal_bytes"]
    journal["events"].pop()
    journal["event_count"] -= 1
    journal["last_event_sequence"] -= 1
    cutoff = hidden_documents["cutoff_attestation_bytes"]
    cutoff["last_included_event_sequence"] -= 1
    cutoff["included_event_count"] -= 1
    reference = hidden_documents["memory_peak_pre_read_bytes"]
    cutoff_identity_payload = {
        "schema": evidence_v2.CUTOFF_SCHEMA_ID,
        "schema_version": evidence_v2.SCHEMA_VERSION,
        "live_envelope_id": reference["live_envelope_id"],
        "occurrence_id": reference["occurrence_id"],
        "route_attempt_id": reference["route_attempt_id"],
        "decision_point_id": reference["decision_point_id"],
        "measurement_window_id": reference["measurement_window_id"],
        "measurement_start_sequence": reference["measurement_start_sequence"],
        "operational_cutoff_sequence": reference["operational_cutoff_sequence"],
        "last_included_event_sequence": cutoff["last_included_event_sequence"],
        "included_event_count": cutoff["included_event_count"],
        "closure_kind": reference["closure_kind"],
        "failure_reason": reference["failure_reason"],
    }
    hidden_cutoff_id = content_id(
        evidence_v2._COMPONENT_DOMAIN[evidence_v2.CUTOFF_SCHEMA_ID],  # noqa: SLF001
        cutoff_identity_payload,
    )
    for document in hidden_documents.values():
        document["operational_cutoff_id"] = hidden_cutoff_id
    hidden = {
        key: canonical_json_bytes(document)
        for key, document in hidden_documents.items()
    }
    with pytest.raises(
        evidence_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
        match="post-read",
    ):
        evidence_v2.replay_working_process_raw_evidence_v2(**hidden)
