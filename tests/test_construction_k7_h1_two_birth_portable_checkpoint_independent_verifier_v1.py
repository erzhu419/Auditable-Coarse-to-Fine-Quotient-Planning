from __future__ import annotations

import ast
import copy
import errno
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import struct
import sys
from typing import Any

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v18 as domains
from acfqp import construction_k7_h1_two_birth_portable_checkpoint_independent_verifier_v1 as verifier
from acfqp import construction_k7_h1_two_birth_portable_checkpoint_v1 as producer
from acfqp.phase3e_ids import canonical_json_bytes


FRAME = struct.Struct("<QIIQ16sqiIQ")
UCRED = struct.Struct("=iII")
RIGHT = struct.Struct("=i")
MAGIC = 0x31564E5043514641
VERSION = 1

GUARDIAN = 1001
SUPERVISOR = 2001
PROBE = 2002
UID = 1000
GID = 1000
CONTROL = {"device": 17, "inode": 23, "mode": 0o040700}
REAL_HELPER = Path(__file__).with_name(
    "_two_birth_portable_checkpoint_independent_verifier_subprocess.py"
)


def _rehash(document: dict[str, Any], domain: str, field: str) -> None:
    payload = dict(document)
    payload.pop(field, None)
    document[field] = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _frame(
    opcode: int,
    nonce: str,
    pid: int,
    *,
    sequence: int = 1,
    status: int = 0,
    flags: int = 0,
    fact_a: int = 0,
) -> dict[str, Any]:
    return {
        "opcode": opcode,
        "sequence": sequence,
        "nonce_hex": nonce,
        "pid": pid,
        "status": status,
        "flags": flags,
        "fact_a": fact_a,
    }


def _observation(
    event_index: int,
    frame: dict[str, Any],
    *,
    credential_pid: int,
    rights: bool = False,
) -> dict[str, Any]:
    raw = FRAME.pack(
        MAGIC,
        VERSION,
        frame["opcode"],
        frame["sequence"],
        bytes.fromhex(frame["nonce_hex"]),
        frame["pid"],
        frame["status"],
        frame["flags"],
        frame["fact_a"],
    )
    ancillary = [
        {
            "level": socket.SOL_SOCKET,
            "kind": socket.SCM_CREDENTIALS,
            "byte_count": UCRED.size,
            "data_hex": UCRED.pack(credential_pid, UID, GID).hex(),
        }
    ]
    installed: list[dict[str, Any]] = []
    if rights:
        ancillary.append(
            {
                "level": socket.SOL_SOCKET,
                "kind": socket.SCM_RIGHTS,
                "byte_count": RIGHT.size,
                "data_hex": RIGHT.pack(41).hex(),
            }
        )
        installed.append(
            {
                "pid": PROBE,
                "nspid": PROBE,
                "device": 0,
                "inode": 101,
                "descriptor_flags": 1,
                "cloexec": True,
            }
        )
    return {
        "event_index": event_index,
        "opcode": frame["opcode"],
        "sequence": frame["sequence"],
        "frame_pid": frame["pid"],
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_byte_count": len(raw),
        "raw_payload_hex": raw.hex(),
        "decoded_frame": copy.deepcopy(frame),
        "credentials": {"pid": credential_pid, "uid": UID, "gid": GID},
        "rights_count": int(rights),
        "installed_pidfd_facts": installed,
        "recv_flags": 0,
        "address": {"kind": "NONE"},
        "connected_peer_address": {"kind": "NONE"},
        "ancillary": ancillary,
    }


def _snapshot(sequence: int, pids: list[int]) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "directory_device": CONTROL["device"],
        "directory_inode": CONTROL["inode"],
        "first_cgroup_procs": pids,
        "events": {"frozen": 0, "populated": int(bool(pids))},
        "pids_current": len(pids),
        "second_cgroup_procs": pids,
    }


def _nested_v2() -> dict[str, Any]:
    nonce = "ab" * 16
    parent = _frame(3, nonce, PROBE, flags=0x1F, fact_a=SUPERVISOR)
    withdrawn = _frame(9, nonce, PROBE)
    ready = _frame(10, nonce, PROBE)
    echo = _frame(12, nonce, PROBE)
    reap = _frame(5, nonce, PROBE, flags=1, fact_a=errno.ECHILD)
    raw = {
        "schema": "acfqp.k7_h1_nested_creator_probe_raw_facts.v1",
        "schema_version": "1.0.0",
        "profile_key": "construction_k7_h1_nested_creator_probe_native_v1",
        "supervisor_pid": SUPERVISOR,
        "supervisor_start_ticks": 301,
        "probe_pid": PROBE,
        "probe_start_ticks": 302,
        "nonce_hex": nonce,
        "parent_return_frame": parent,
        "child_withdrawn_frame": withdrawn,
        "child_ready_frame": ready,
        "child_release_echo_frame": echo,
        "creator_reap_frame": reap,
        "pid_cell_value": PROBE,
        "pidfd_fact": {
            "pid": PROBE,
            "nspid": PROBE,
            "device": 0,
            "inode": 101,
        },
        "live_cgroup_snapshots": [
            _snapshot(1, [SUPERVISOR, PROBE]),
            _snapshot(2, [SUPERVISOR, PROBE]),
        ],
        "post_reap_cgroup_snapshots": [
            _snapshot(3, [SUPERVISOR]),
            _snapshot(4, [SUPERVISOR]),
        ],
        "guardian_waitid_errno": errno.ECHILD,
        "actual_nested_pidfd_probe_birth_present": True,
        "actual_non_guardian_creator_reap_present": True,
        "guardian_independent_pid_cell_pidfd_cgroup_join_present": True,
        "gated_supervisor_birth_authority_present": False,
        "two_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "production_shared_resource_receipts_present": False,
        "official_execution_allowed": False,
    }
    supervisor_ready = _frame(
        1,
        "00" * 16,
        SUPERVISOR,
        sequence=0,
        fact_a=GUARDIAN,
    )
    return {
        "schema": "acfqp.k7_h1_nested_creator_probe_observed_facts.v2",
        "schema_version": "2.0.0",
        "profile_key": "construction_k7_h1_nested_creator_probe_observed_v2",
        "raw_facts_v1": raw,
        "supervisor_ready_observation": _observation(
            0, supervisor_ready, credential_pid=SUPERVISOR
        ),
        "protocol_receive_observations": [
            _observation(0, parent, credential_pid=SUPERVISOR, rights=True),
            _observation(1, withdrawn, credential_pid=PROBE),
            _observation(2, ready, credential_pid=PROBE),
            _observation(3, echo, credential_pid=PROBE),
            _observation(4, reap, credential_pid=SUPERVISOR),
        ],
        "nested_receive_credential_observations_present": True,
        "nested_receive_rights_observations_present": True,
        "portable_checkpoint_authority_present": False,
        "two_birth_prefix_authority_present": False,
        "official_execution_allowed": False,
    }


def _live_observation() -> dict[str, Any]:
    outer_nonce = "cd" * 16
    outer_frames = (
        (
            "CELL_WITHDRAWN",
            b"ACFQP:EXEC_CELL_WITHDRAWN:v1:" + outer_nonce.encode(),
        ),
        ("GATE_READY", b"ACFQP:EXEC_GATE_READY:v1:" + outer_nonce.encode()),
        ("RELEASE_ECHO", b"ACFQP:EXEC_RELEASE:v1:" + outer_nonce.encode()),
    )
    registered = [
        {
            "kind": kind,
            "payload_hex": raw.hex(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
        }
        for kind, raw in outer_frames
    ]
    received = [
        {
            "kind": kind,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
            "credential_pid": SUPERVISOR,
            "credential_uid": UID,
            "credential_gid": GID,
            "message_flags": 0,
        }
        for kind, raw in outer_frames
    ]
    supervisor_pidfd = {
        "pid": SUPERVISOR,
        "nspid": SUPERVISOR,
        "device": 0,
        "inode": 99,
    }
    document = {
        "schema": "acfqp.k7_h1_two_birth_live_observation.v1",
        "schema_version": "1.0.0",
        "profile_key": "construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "readiness": "ACTUAL_TWO_BIRTH_RAW_RUNTIME_ONLY",
        "live_prefix_state_at_issuance": "PROBE_REAPED_SUPERVISOR_LIVE",
        "guardian_identity": {
            "pid": GUARDIAN,
            "process_start_ticks": 300,
            "thread_id": 400,
            "native_thread_id": 401,
        },
        "control_cgroup_identity": copy.deepcopy(CONTROL),
        "birth_order": ["SUPERVISOR", "PIDFD_PROBE"],
        "creator_by_role": {
            "SUPERVISOR": "GUARDIAN",
            "PIDFD_PROBE": "SUPERVISOR",
        },
        "supervisor_pid": SUPERVISOR,
        "supervisor_start_ticks": 301,
        "probe_pid": PROBE,
        "probe_start_ticks": 302,
        "outer_pid_cell_value": SUPERVISOR,
        "outer_parent_edge": {
            "clone_result": SUPERVISOR,
            "status_bits": 123,
            "first_cleanup_error": 0,
            "reserved_zero": 0,
        },
        "outer_nonce_hex": outer_nonce,
        "outer_registered_expected_frames": registered,
        "outer_receive_facts": received,
        "outer_pidfd_fact": supervisor_pidfd,
        "outer_seal_set": 15,
        "outer_role_source_fact": {
            "elf_sha256": "18656f1efabf4e7229c5f5a7676f557bd2d28b17bb3eaf81d37953fd21578c05",
            "elf_byte_count": 8272,
            "source_device": 21,
            "source_inode": 22,
            "witness_device": 21,
            "witness_inode": 22,
            "source_witness_same_identity": True,
        },
        "entry_empty_control_snapshots": [
            _snapshot(7000, []),
            _snapshot(7001, []),
        ],
        "outer_supervisor_live_snapshots": [
            _snapshot(1, [SUPERVISOR]),
            _snapshot(2, [SUPERVISOR]),
        ],
        "checkpoint_current_control_snapshots": [
            _snapshot(8000, [SUPERVISOR]),
            _snapshot(8001, [SUPERVISOR]),
        ],
        "live_session_verification": {
            "profile_key": "construction_k7_h1_nested_creator_probe_native_v1",
            "session_state": "PROBE_REAPED_SUPERVISOR_LIVE",
            "supervisor_pid": SUPERVISOR,
            "supervisor_start_ticks": 301,
            "supervisor_pidfd_fact": supervisor_pidfd,
            "supervisor_pidfd_cloexec": True,
            "control_socket_fact": {
                "device": 0,
                "inode": 77,
                "socket_type": int(getattr(socket, "SOCK_SEQPACKET", 5)),
                "passcred": 1,
                "descriptor_flags": 1,
                "cloexec": True,
                "connected_peer_address": {"kind": "NONE"},
                "peer_credentials": {
                    "pid": GUARDIAN,
                    "uid": UID,
                    "gid": GID,
                },
            },
            "owner_pid": GUARDIAN,
            "owner_thread_id": 400,
            "active_probe_pid": -1,
            "live_session_verified": True,
            "verification_mutated_session": False,
        },
        "nested_probe_observed_facts_v2": _nested_v2(),
        "retained_descriptor_roles": [
            "CONTROL_CGROUP",
            "SUPERVISOR_CONTROL_SOCKET",
            "SUPERVISOR_PIDFD",
        ],
        "retained_live_descriptor_numbers_serialized": False,
        "historical_scm_rights_descriptor_number_observation_present": True,
        "historical_descriptor_numbers_are_not_resume_capability": True,
        "memory_peak_read_count": 0,
        "supervisor_v1_only_accepts_shutdown_after_probe": True,
        "broker_launch_supported_by_live_process": False,
        "target_two_birth_creator_chain_observed": True,
        "exact_creator_reap_ownership_observed": True,
        "portable_observation_checkpoint_present": False,
        "durable_two_birth_artifact_graph_present": False,
        "live_continuation_capability_portable": False,
    }
    document.update(producer._locked_claims())  # noqa: SLF001
    return document


def _success_documents() -> list[dict[str, Any]]:
    lease, source = producer._freeze_source_closure()  # noqa: SLF001
    try:
        source = copy.deepcopy(source)
    finally:
        lease.close()
    live = _live_observation()
    source_id = source["two_birth_execution_source_closure_id"]
    credentials = {
        "schema": "acfqp.k7_h1_nested_probe_credential_observation_bundle.v1",
        "schema_version": "1.0.0",
        "profile_key": "construction_k7_h1_two_birth_portable_checkpoint_v1",
        "readiness": "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY",
        "two_birth_execution_source_closure_id": source_id,
        "journal_sequence": 2,
        "previous_record_id": source_id,
        "guardian_identity": copy.deepcopy(live["guardian_identity"]),
        "control_cgroup_identity": copy.deepcopy(live["control_cgroup_identity"]),
        "supervisor_pid": live["supervisor_pid"],
        "supervisor_start_ticks": live["supervisor_start_ticks"],
        "probe_pid": live["probe_pid"],
        "probe_start_ticks": live["probe_start_ticks"],
        "outer_registered_expected_frames": copy.deepcopy(live["outer_registered_expected_frames"]),
        "outer_receive_facts": copy.deepcopy(live["outer_receive_facts"]),
        "nested_probe_observed_facts_v2": copy.deepcopy(live["nested_probe_observed_facts_v2"]),
        "nested_receive_credential_observations_present": True,
        "nested_receive_rights_observations_present": True,
        "credential_observations_are_not_lease_authority": True,
    }
    credentials.update(producer._locked_claims())  # noqa: SLF001
    _rehash(
        credentials,
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
        "nested_probe_credential_observation_bundle_id",
    )
    credential_id = credentials["nested_probe_credential_observation_bundle_id"]
    root = {
        "schema": "acfqp.k7_h1_live_two_birth_prefix_checkpoint.v1",
        "schema_version": "1.0.0",
        "profile_key": "construction_k7_h1_two_birth_portable_checkpoint_v1",
        "readiness": "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY",
        "issuance_state": "PROBE_REAPED_SUPERVISOR_LIVE",
        "runtime_state_at_root_commit": "PROBE_REAPED_SUPERVISOR_LIVE",
        "expected_success_return_runtime_state": "CLOSED",
        "producer_success_return_not_yet_observed": True,
        "producer_protocol_after_checkpoint": "V1_SHUTDOWN_ONLY",
        "journal_sequence": 3,
        "previous_record_id": credential_id,
        "checkpoint_durable_before_runtime_shutdown": True,
        "execution_source_closure": copy.deepcopy(source),
        "credential_observation_bundle": copy.deepcopy(credentials),
        "live_observation": copy.deepcopy(live),
        "root_embeds_complete_child_documents": True,
        "two_birth_execution_source_closure_id": source_id,
        "nested_probe_credential_observation_bundle_id": credential_id,
        "portable_observation_checkpoint_present": True,
        "durable_portable_observation_graph_present": True,
        "checkpoint_bytes_describe_historical_live_observation": True,
        "checkpoint_bytes_encode_resume_capability": False,
        "live_continuation_capability_portable": False,
    }
    root.update(producer._locked_claims())  # noqa: SLF001
    _rehash(
        root,
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    return [source, credentials, root]


def _bytes(documents: list[dict[str, Any]]) -> tuple[bytes, ...]:
    return tuple(canonical_json_bytes(document) for document in documents)


def _run_real_verifier_helper(mode: str) -> dict[str, Any]:
    repository = REAL_HELPER.parent.parent
    completed = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--scope",
            "--collect",
            "-p",
            "Delegate=yes",
            "-p",
            "TasksMax=infinity",
            f"--working-directory={repository}",
            "env",
            f"PYTHONPATH={repository / 'src'}",
            sys.executable,
            os.fspath(REAL_HELPER),
            mode,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(completed.stdout.splitlines()[-1])


def _cascade(documents: list[dict[str, Any]]) -> None:
    source, credentials, root = documents
    _rehash(
        source,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        "two_birth_execution_source_closure_id",
    )
    source_id = source["two_birth_execution_source_closure_id"]
    credentials["two_birth_execution_source_closure_id"] = source_id
    credentials["previous_record_id"] = source_id
    _rehash(
        credentials,
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
        "nested_probe_credential_observation_bundle_id",
    )
    credential_id = credentials["nested_probe_credential_observation_bundle_id"]
    root["execution_source_closure"] = copy.deepcopy(source)
    root["credential_observation_bundle"] = copy.deepcopy(credentials)
    root["two_birth_execution_source_closure_id"] = source_id
    root["nested_probe_credential_observation_bundle_id"] = credential_id
    root["previous_record_id"] = credential_id
    _rehash(
        root,
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )


def _failure_document(
    prefix: list[dict[str, Any]], prefix_raw: tuple[bytes, ...]
) -> dict[str, Any]:
    labels = (
        "EXECUTION_SOURCE_CLOSURE",
        "CREDENTIAL_OBSERVATION_BUNDLE",
        "LIVE_PREFIX_CHECKPOINT",
    )
    id_fields = (
        "two_birth_execution_source_closure_id",
        "nested_probe_credential_observation_bundle_id",
        "live_two_birth_prefix_checkpoint_id",
    )
    facts = []
    for index, (document, raw, label, id_field) in enumerate(
        zip(prefix, prefix_raw, labels, id_fields), start=1
    ):
        record_id = document[id_field]
        facts.append(
            {
                "sequence": index,
                "label": label,
                "record_id": record_id,
                "filename": f"{index:06d}_{label}_{record_id}.json",
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "file_fsync_complete": True,
                "directory_fsync_complete": True,
            }
        )
    previous: Any = (
        facts[-1]["record_id"]
        if facts
        else {"kind": "GENESIS", "reason": "NO_PREDECESSOR_RECORD"}
    )
    raw_begin_returned = bool(prefix)
    if raw_begin_returned:
        reaped = [
            {
                "si_pid": SUPERVISOR,
                "si_uid": UID,
                "si_signo": 17,
                "si_status": 109,
                "si_code": 1,
            }
        ]
        terminal_method = "PUBLIC_ABORT"
        terminal_document: dict[str, Any] = {
            "empty_snapshots": [
                _snapshot(9996, []),
                _snapshot(9997, []),
            ],
            "inner_abort": {
                "active_probe_pid": -1,
                "children_before": [SUPERVISOR],
                "empty_snapshots": [
                    _snapshot(9001, []),
                    _snapshot(9002, []),
                ],
                "reaped": reaped,
                "state": "ABORTED_CLOSED",
                "supervisor_pid": SUPERVISOR,
            },
            "probe_pid": PROBE,
            "state": "ABORTED_CLOSED",
            "supervisor_pid": SUPERVISOR,
        }
        recovery_document: dict[str, Any] = {
            "kind": "NOT_APPLICABLE",
            "reason": "NO_QUARANTINE",
        }
    else:
        terminal_method = "NO_HANDLE_RUNTIME_ALREADY_CLOSED"
        terminal_document = {
            "kind": "NOT_APPLICABLE",
            "reason": "NO_ABORT_RESULT",
        }
        recovery_document = {
            "kind": "NOT_APPLICABLE",
            "reason": "NO_QUARANTINE",
        }
    closure = {
        "schema": "acfqp.k7_h1_two_birth_protocol_failure_closure.v1",
        "schema_version": "1.0.0",
        "profile_key": "construction_k7_h1_two_birth_portable_checkpoint_v1",
        "readiness": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "source_closure": (
            copy.deepcopy(prefix[0])
            if prefix
            else {"kind": "NOT_AVAILABLE", "reason": "SOURCE_FREEZE_DID_NOT_COMPLETE"}
        ),
        "journal_sequence": len(prefix) + 1,
        "previous_record_id": previous,
        "raw_begin_returned": raw_begin_returned,
        "failure_type": "InjectedFailure",
        "failure_message": "injected",
        "cleanup": {
            "raw_cleanup_completely_closed": True,
            "terminal_method": terminal_method,
            "terminal_document": terminal_document,
            "begin_failure_recovery_document": recovery_document,
            "empty_control_snapshots": [
                _snapshot(18001, []),
                _snapshot(18002, []),
            ],
            "direct_children_after_cleanup": [],
            "ambient_fd_inventory_restored": True,
            "subreaper_state_restored": True,
        },
        "journal_records_before_failure_closure": facts,
        "failure_closure_is_not_infeasibility": True,
        "failure_closure_is_not_plan_certificate": True,
    }
    closure.update(producer._locked_claims())  # noqa: SLF001
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    return closure


def test_success_graph_verifies_only_as_non_authoritative_observation() -> None:
    result = verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
        _bytes(_success_documents())
    )
    assert result.outcome == verifier.SUCCESS_OUTCOME
    assert result.success_observation_verified is True
    assert result.typed_noncertificate_verified is False
    assert result.journal_record_count == 3
    assert result.source_closure_id is not None
    assert result.credential_bundle_id is not None
    assert result.live_checkpoint_id is not None
    assert result.failure_closure_id is None
    assert result.portable_checkpoint_authority_present is False
    assert result.two_birth_prefix_authority_present is False
    assert result.official_execution_allowed is False


def test_verifier_does_not_import_producer_or_runtime_modules() -> None:
    tree = ast.parse(inspect.getsource(verifier))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
            imported.update(
                f"{node.module}.{alias.name}" for alias in node.names
            )
    assert not any(
        "two_birth_portable_checkpoint_v1" in name
        or "nested_creator_two_birth_runtime" in name
        or "nested_creator_probe_native" in name
        for name in imported
    )


def test_embedded_source_bytes_hash_is_recomputed_before_content_ids() -> None:
    documents = _success_documents()
    entry = documents[0]["source_entries"][0]
    raw = bytes.fromhex(entry["source_bytes_hex"])
    entry["source_bytes_hex"] = (raw + b"attack").hex()
    _cascade(documents)
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="source bytes byte count changed|embedded source hash",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_same_length_source_constant_tamper_fully_resigned_is_rejected() -> None:
    documents = _success_documents()
    source = documents[0]
    entry = next(
        item
        for item in source["source_entries"]
        if item["role"] == "V18_DOMAIN_REGISTRY_PYTHON"
    )
    old_raw = bytes.fromhex(entry["source_bytes_hex"])
    old = b"domain tag is absent from the K7 H1 V18 registry"
    new = b"domain tag is voided from the K7 H1 V18 registry"
    assert len(old) == len(new) and old_raw.count(old) == 1
    new_raw = old_raw.replace(old, new, 1)
    assert len(new_raw) == len(old_raw)

    # Re-sign every producer-controlled layer, including the new recursive
    # code/default fingerprint, to demonstrate why the verifier-side source
    # anchor is a necessary second trust layer.
    entry["source_bytes_hex"] = new_raw.hex()
    entry["byte_count"] = len(new_raw)
    entry["sha256"] = hashlib.sha256(new_raw).hexdigest()
    binding = next(
        item
        for item in source["callable_authority_bindings"]
        if item["role"] == "V18_CONTENT_ID"
    )
    compiled = compile(
        new_raw,
        entry["repository_relative_path"],
        "exec",
        dont_inherit=True,
    )
    (
        code_document,
        defaults_document,
        kwdefaults_document,
        code_sha256,
        callable_sha256,
        code,
    ) = verifier._callable_semantic_documents_from_source(  # noqa: SLF001
        new_raw,
        path=entry["repository_relative_path"],
        qualname=binding["qualname"],
        compiled_root=compiled,
    )
    binding.update(
        {
            "code_first_line": code.co_firstlineno,
            "code_fingerprint_document": code_document,
            "defaults_fingerprint_document": defaults_document,
            "kwdefaults_fingerprint_document": kwdefaults_document,
            "code_fingerprint_sha256": code_sha256,
            "callable_semantic_fingerprint_sha256": callable_sha256,
        }
    )
    _cascade(documents)
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="external source anchor changed for V18_DOMAIN_REGISTRY_PYTHON",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_domain_swap_is_rejected_even_when_entire_chain_is_rehashed() -> None:
    documents = _success_documents()
    source = documents[0]
    payload = dict(source)
    payload.pop("two_birth_execution_source_closure_id")
    source["two_birth_execution_source_closure_id"] = hashlib.sha256(
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    source_id = source["two_birth_execution_source_closure_id"]
    documents[1]["two_birth_execution_source_closure_id"] = source_id
    documents[1]["previous_record_id"] = source_id
    _rehash(
        documents[1],
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
        "nested_probe_credential_observation_bundle_id",
    )
    documents[2]["execution_source_closure"] = copy.deepcopy(source)
    documents[2]["credential_observation_bundle"] = copy.deepcopy(documents[1])
    documents[2]["two_birth_execution_source_closure_id"] = source_id
    documents[2]["nested_probe_credential_observation_bundle_id"] = documents[1][
        "nested_probe_credential_observation_bundle_id"
    ]
    documents[2]["previous_record_id"] = documents[1][
        "nested_probe_credential_observation_bundle_id"
    ]
    _rehash(
        documents[2],
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="domain changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_semantic_tamper_rehashed_under_correct_domain_is_rejected() -> None:
    documents = _success_documents()
    documents[2]["live_observation"]["birth_order"] = [
        "PIDFD_PROBE",
        "SUPERVISOR",
    ]
    _rehash(
        documents[2],
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="creator chain changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_authority_flip_rehashed_under_correct_domain_is_rejected() -> None:
    documents = _success_documents()
    documents[2]["official_execution_allowed"] = True
    _rehash(
        documents[2],
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="locked claim official_execution_allowed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_frozen_cgroup_attack_rehashed_under_correct_domain_is_rejected() -> None:
    documents = _success_documents()
    documents[2]["live_observation"]["entry_empty_control_snapshots"][0][
        "events"
    ]["frozen"] = 1
    _rehash(
        documents[2],
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="events changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_installed_pidfd_identity_tamper_resigned_is_rejected() -> None:
    documents = _success_documents()
    installed = documents[2]["live_observation"][
        "nested_probe_observed_facts_v2"
    ]["protocol_receive_observations"][0]["installed_pidfd_facts"][0]
    installed["inode"] += 1
    _rehash(
        documents[2],
        domains.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
        "live_two_birth_prefix_checkpoint_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="installed/raw pidfd identity join changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


def test_typed_null_cannot_substitute_for_a_content_id() -> None:
    documents = _success_documents()
    documents[1]["two_birth_execution_source_closure_id"] = {
        "kind": "NOT_APPLICABLE",
        "reason": "ATTACK",
    }
    documents[1]["previous_record_id"] = documents[1][
        "two_birth_execution_source_closure_id"
    ]
    _rehash(
        documents[1],
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
        "nested_probe_credential_observation_bundle_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="source chain changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents)
        )


@pytest.mark.parametrize("prefix_count", (0, 1, 2, 3))
def test_failure_closure_is_verified_only_as_noncertificate(
    prefix_count: int,
) -> None:
    documents = _success_documents()[:prefix_count]
    prefix_raw = _bytes(documents)
    closure = _failure_document(documents, prefix_raw)
    result = verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
        (*prefix_raw, canonical_json_bytes(closure))
    )
    assert result.outcome == verifier.NONCERTIFICATE_OUTCOME
    assert result.success_observation_verified is False
    assert result.typed_noncertificate_verified is True
    assert result.failure_closure_id is not None
    assert result.portable_checkpoint_authority_present is False
    assert result.official_execution_allowed is False


def test_failure_closure_authority_flip_is_rejected() -> None:
    documents = _success_documents()[:1]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    closure["portable_checkpoint_authority_present"] = True
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="locked claim portable_checkpoint_authority_present",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_prefix_two_credential_v2_semantics_are_verified_without_root() -> None:
    documents = _success_documents()[:2]
    credentials = documents[1]
    credentials["nested_probe_observed_facts_v2"]["raw_facts_v1"][
        "guardian_waitid_errno"
    ] = 0
    _rehash(
        credentials,
        domains.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
        "nested_probe_credential_observation_bundle_id",
    )
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="nested PID-cell or reap ownership changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_failure_cleanup_frozen_snapshot_resigned_is_rejected() -> None:
    documents = _success_documents()[:1]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    closure["cleanup"]["empty_control_snapshots"][1]["events"]["frozen"] = 1
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="events changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_failure_cleanup_terminal_semantics_resigned_is_rejected() -> None:
    documents = _success_documents()[:1]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    closure["cleanup"]["terminal_document"]["probe_pid"] = SUPERVISOR
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="process state changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_live_public_abort_cannot_claim_empty_child_and_reap_inventories() -> None:
    documents = _success_documents()[:1]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    inner = closure["cleanup"]["terminal_document"]["inner_abort"]
    inner["children_before"] = []
    inner["reaped"] = []
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="live PUBLIC_ABORT child inventory changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_nonempty_failure_prefix_cannot_deny_raw_begin_return_resigned() -> None:
    documents = _success_documents()[:1]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    closure["raw_begin_returned"] = False
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="before raw begin returned",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def _rewrite_cleanup_snapshot_identity(value: Any, *, device: int, inode: int) -> None:
    if type(value) is dict:
        if "directory_device" in value and "directory_inode" in value:
            value["directory_device"] = device
            value["directory_inode"] = inode
        for item in value.values():
            _rewrite_cleanup_snapshot_identity(item, device=device, inode=inode)
    elif type(value) is list:
        for item in value:
            _rewrite_cleanup_snapshot_identity(item, device=device, inode=inode)


def test_failure_cleanup_identity_group_resigned_cannot_escape_credential() -> None:
    documents = _success_documents()[:2]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    _rewrite_cleanup_snapshot_identity(
        closure["cleanup"], device=CONTROL["device"] + 1, inode=CONTROL["inode"] + 1
    )
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="cleanup/credential CONTROL identity join changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_failure_cleanup_pid_group_resigned_cannot_escape_credential() -> None:
    documents = _success_documents()[:2]
    raw = _bytes(documents)
    closure = _failure_document(documents, raw)
    terminal = closure["cleanup"]["terminal_document"]
    new_supervisor = SUPERVISOR + 10
    new_probe = PROBE + 10
    terminal["supervisor_pid"] = new_supervisor
    terminal["probe_pid"] = new_probe
    terminal["inner_abort"]["supervisor_pid"] = new_supervisor
    terminal["inner_abort"]["children_before"] = [new_supervisor]
    for row in terminal["inner_abort"]["reaped"]:
        row["si_pid"] = new_supervisor
    _rehash(
        closure,
        domains.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        "two_birth_protocol_failure_closure_id",
    )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="cleanup/credential process identity join changed",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (*raw, canonical_json_bytes(closure))
        )


def test_noncanonical_and_partial_success_inventories_are_rejected() -> None:
    documents = _success_documents()
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="canonical JSON",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            (b" " + canonical_json_bytes(documents[0]),)
        )
    with pytest.raises(
        verifier.TwoBirthPortableCheckpointIndependentVerificationViolation,
        match="neither the exact success graph",
    ):
        verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
            _bytes(documents[:2])
        )


@pytest.mark.parametrize(
    ("mode", "expected_count", "expected_success"),
    (
        ("SUCCESS", 3, True),
        ("SOURCE_CLOSURE_FROZEN", 1, False),
        ("RAW_BEGIN_RETURNED", 1, False),
        ("LIVE_SNAPSHOT_FROZEN", 1, False),
        ("SOURCE_RECORD_FILE_FSYNC", 2, False),
        ("CREDENTIAL_RECORD_FILE_FSYNC", 3, False),
        ("CHECKPOINT_RECORD_FILE_FSYNC", 4, False),
        ("CHECKPOINT_RECORD_DIRECTORY_FSYNC", 4, False),
        ("ROOT_DURABLE_COMMIT", 4, False),
        ("RUNTIME_CLOSED", 4, False),
    ),
)
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_producer_journal_bytes_verify_independently(
    mode: str,
    expected_count: int,
    expected_success: bool,
) -> None:
    result = _run_real_verifier_helper(mode)
    assert result["producer_success"] is expected_success
    assert result["record_count"] == expected_count
    assert result["portable_checkpoint_authority_present"] is False
    assert result["official_execution_allowed"] is False
    assert result["final_population"] == 0
    assert result["direct_children"] == ""
    if expected_success:
        assert result["verifier_outcome"] == verifier.SUCCESS_OUTCOME
        assert result["success_observation_verified"] is True
        assert result["typed_noncertificate_verified"] is False
    else:
        assert result["verifier_outcome"] == verifier.NONCERTIFICATE_OUTCOME
        assert result["success_observation_verified"] is False
        assert result["typed_noncertificate_verified"] is True
