#!/usr/bin/env python3
"""Effectful V180r12r4 WORKER target.

The retained bootstrap executes this source only for its authenticated
``worker`` internal target.  This module owns the two sealed-stage reads, the
134/137/15 producer-free replay operations, and the direct write to the
preopened subject descriptor.  It owns no repository descriptor, cgroup
controller, journal directory, output directory, or commit primitive.

All lifecycle callbacks are synchronous: an INTENT callback must return only
after the outer observer has durably fsynced and ACKed that event.  An OUTCOME
callback likewise returns only after its typed evidence and canonical event
are durable.  Focused tests inject callbacks and descriptors; they never
launch this target or execute a campaign authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import hmac
import os
import socket
import stat
import sys
import types
from typing import Any, Mapping, NoReturn, Protocol, Sequence

from acfqp import construction_k7_campaign_measurement_worker_v180r12r4 as core
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r4 as supervisor_core
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as identity_domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PROFILE_KEY = "work_v180r12r4_campaign_measurement"
READ_CHUNK_BYTES = 64 * 1024
WRITE_CHUNK_BYTES = 64 * 1024
# The subject is embedded as a supporting canonical JSON document in the
# authenticated SUBJECT_WRITE_OUTCOME proposal.  Keep enough headroom for the
# direct IO receipt and the signed frame envelope under the frozen 1 MiB frame
# cap, then still measure the exact prospective frame before touching the FD.
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
MAX_SUBJECT_BYTES = SUBJECT_RESULT_RUNTIME_BYTE_CAP
FRAME_BYTE_CAP = 1024 * 1024
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEAL_MASK = F_SEAL_GROW | F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_WRITE
PRECOMPILED_SOURCE_BUNDLE_FD = 240
INTERNAL_IPC_FD = 241
INTERNAL_MAC_KEY_FD = 242
INTERNAL_CONTEXT_FD = 243
TERMINAL_STAGE_FD = 246
VERIFICATION_STAGE_FD = 247
SUBJECT_RESULT_FD = 248
SUPERVISOR_WORKER_HANDOFF_SCHEMA = (
    "acfqp.v180r12r4_supervisor_worker_handoff.v1"
)
SUPERVISOR_WORKER_HANDOFF_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_attempt_record_id",
    "execution_slot_id",
    "execution_nonce",
    "logical_occurrence_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "terminal_snapshot_document",
    "verification_snapshot_document",
    "terminal_memfd_stage_document",
    "verification_memfd_stage_document",
    "terminal_open_visibility_document",
    "verification_open_visibility_document",
    "stage_semantic_receipt_documents",
    "terminal_stage_binding",
    "verification_stage_binding",
    "subject_output_binding",
    "worker_birth_operation_id",
    "worker_birth_receipt_id",
    "worker_birth_document",
    "worker_birth_event_id",
    "worker_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_handoff",
)
STAGE_FD_BINDING_FIELDS = (
    "fd", "device", "inode", "byte_count", "memfd_stage_receipt_id",
    "open_visibility_receipt_id",
)
SUBJECT_OUTPUT_BINDING_FIELDS = (
    "fd", "device", "inode", "mode", "nlink", "initial_byte_count",
)
_VERIFIED_CONTEXT_KEYS = frozenset(
    {
        "schema", "target", "actor_role", "parent_actor_role", "protocol_id",
        "authorization_id", "authorization_evidence_id", "attempt_id",
        "campaign_measurement_execution_slot_id", "logical_occurrence_id",
        "execution_nonce", "prelaunch_materialization_terminal_id",
        "prelaunch_launch_rule_id", "measurement_launch_attempt_id",
        "launch_operation_id", "manifest_sha256",
        "precompiled_source_bundle_sha256", "inherited_fd_roles",
        "target_payload", "parent_to_child_mac_key", "parent_context_mac",
        "context_consumed_once",
    }
)
_EXPECTED_FD_ROLES = (
    (PRECOMPILED_SOURCE_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
    (INTERNAL_IPC_FD, "SUPERVISOR_WORKER_SOCK_SEQPACKET"),
    (INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
    (INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
    (TERMINAL_STAGE_FD, "TERMINAL_STAGE_READ_ONLY_MEMFD"),
    (VERIFICATION_STAGE_FD, "VERIFICATION_STAGE_READ_ONLY_MEMFD"),
    (SUBJECT_RESULT_FD, "SUBJECT_RESULT_WRITE_ONLY_FD"),
)


class V180R12R4WorkerRuntimeError(RuntimeError):
    """The effectful worker escaped its frozen inherited-FD contract."""


def _fail(message: str) -> NoReturn:
    raise V180R12R4WorkerRuntimeError(message)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) in {tuple, list}:
        return [_thaw(item) for item in value]
    return value


def _content_id(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _canonical_object_v180r12r4(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(label + " must be nonempty exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V180R12R4WorkerRuntimeError(label + " is not canonical JSON") from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(label + " must be one canonical JSON object")
    return value


def _validate_evidence_document(
    value: Mapping[str, Any], *, expected_schema: str
) -> tuple[dict[str, Any], str]:
    contracts = {
        schema: (domain, identity_field)
        for _kind, schema, domain, identity_field in (
            *core.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
            *supervisor_core.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
        )
    }
    keysets = {
        schema: keyset
        for _kind, schema, _identity_field, keyset in (
            *core.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *supervisor_core.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *supervisor_core.ledger.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
        )
    }
    document = _thaw(value)
    if (
        type(document) is not dict
        or document.get("schema") != expected_schema
        or expected_schema not in contracts
        or expected_schema not in keysets
        or set(document) != keysets[expected_schema]
    ):
        _fail("WORKER handoff evidence schema or exact keyset changed")
    domain, identity_field = contracts[expected_schema]
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    expected = core.domains.extension_content_id_v180r12r4e(domain, payload)
    if identity != expected:
        _fail("WORKER handoff evidence content identity changed")
    return document, identity


@dataclass(frozen=True, slots=True)
class SealedPayloadBindingV180R12R4:
    role: core.CampaignInputRoleV180R12R4
    descriptor: int
    expected_device: int
    expected_inode: int
    expected_byte_count: int

    def __post_init__(self) -> None:
        if (
            type(self.role) is not core.CampaignInputRoleV180R12R4
            or type(self.descriptor) is not int
            or self.descriptor < 3
            or type(self.expected_device) is not int
            or self.expected_device <= 0
            or type(self.expected_inode) is not int
            or self.expected_inode <= 0
            or type(self.expected_byte_count) is not int
            or self.expected_byte_count <= 0
        ):
            _fail("sealed payload binding is malformed")


@dataclass(frozen=True, slots=True)
class SealedPayloadReadV180R12R4:
    binding: SealedPayloadBindingV180R12R4
    returned_bytes: bytes = field(repr=False, compare=False)
    returned_chunk_byte_counts: tuple[int, ...]
    observed_device: int
    observed_inode: int
    observed_mode: int
    observed_link_count: int
    observed_seal_mask: int

    @property
    def returned_byte_count(self) -> int:
        return len(self.returned_bytes)

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not SealedPayloadBindingV180R12R4
            or type(self.returned_bytes) is not bytes
            or len(self.returned_bytes) != self.binding.expected_byte_count
            or type(self.returned_chunk_byte_counts) is not tuple
            or not self.returned_chunk_byte_counts
            or any(
                type(value) is not int or value <= 0
                for value in self.returned_chunk_byte_counts
            )
            or sum(self.returned_chunk_byte_counts) != len(self.returned_bytes)
            or self.observed_device != self.binding.expected_device
            or self.observed_inode != self.binding.expected_inode
            or stat.S_IFMT(self.observed_mode) != stat.S_IFREG
            or stat.S_IMODE(self.observed_mode) != 0o400
            or self.observed_link_count != 0
            or self.observed_seal_mask != REQUIRED_SEAL_MASK
        ):
            _fail("sealed payload read observation is malformed")


@dataclass(frozen=True, slots=True)
class SubjectWriteObservationV180R12R4:
    descriptor: int
    returned_chunk_byte_counts: tuple[int, ...]
    returned_byte_count: int
    device: int
    inode: int
    mode_before_commit: int
    link_count: int

    def __post_init__(self) -> None:
        if (
            type(self.descriptor) is not int
            or self.descriptor < 3
            or not self.returned_chunk_byte_counts
            or any(
                type(value) is not int or value <= 0
                for value in self.returned_chunk_byte_counts
            )
            or sum(self.returned_chunk_byte_counts) != self.returned_byte_count
            or self.returned_byte_count <= 0
            or self.returned_byte_count > MAX_SUBJECT_BYTES
            or self.device <= 0
            or self.inode <= 0
            or stat.S_IFMT(self.mode_before_commit) != stat.S_IFREG
            or stat.S_IMODE(self.mode_before_commit) != 0o600
            or self.link_count != 1
        ):
            _fail("subject write observation is malformed")


def _stable_stat_identity(before: os.stat_result, after: os.stat_result) -> bool:
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
    return all(getattr(before, name) == getattr(after, name) for name in fields)


def read_inherited_sealed_payload_v180r12r4(
    binding: SealedPayloadBindingV180R12R4,
    *,
    chunk_bytes: int = READ_CHUNK_BYTES,
) -> SealedPayloadReadV180R12R4:
    """Read one inherited memfd without hashing or changing its shared offset."""

    if type(binding) is not SealedPayloadBindingV180R12R4:
        _fail("worker payload binding is mistyped")
    if type(chunk_bytes) is not int or chunk_bytes <= 0 or chunk_bytes > 1024 * 1024:
        _fail("worker read chunk cap is malformed")
    flags = fcntl.fcntl(binding.descriptor, fcntl.F_GETFL)
    descriptor_flags = fcntl.fcntl(binding.descriptor, fcntl.F_GETFD)
    before = os.fstat(binding.descriptor)
    seals = fcntl.fcntl(binding.descriptor, F_GET_SEALS)
    if (
        flags & os.O_ACCMODE != os.O_RDONLY
        or flags & os.O_APPEND
        or not descriptor_flags & fcntl.FD_CLOEXEC
        or before.st_dev != binding.expected_device
        or before.st_ino != binding.expected_inode
        or before.st_size != binding.expected_byte_count
        or not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_nlink != 0
        or seals != REQUIRED_SEAL_MASK
    ):
        _fail("worker inherited FD is not the exact sealed read-only memfd")
    chunks: list[bytes] = []
    counts: list[int] = []
    offset = 0
    while offset < binding.expected_byte_count:
        raw = os.pread(
            binding.descriptor,
            min(chunk_bytes, binding.expected_byte_count - offset),
            offset,
        )
        if not raw:
            _fail("worker sealed payload read made no progress")
        chunks.append(raw)
        counts.append(len(raw))
        offset += len(raw)
    if os.pread(binding.descriptor, 1, binding.expected_byte_count):
        _fail("worker sealed payload exceeded its exact byte denominator")
    after = os.fstat(binding.descriptor)
    if not _stable_stat_identity(before, after):
        _fail("worker sealed payload identity changed during read")
    return SealedPayloadReadV180R12R4(
        binding,
        b"".join(chunks),
        tuple(counts),
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        seals,
    )


def write_subject_result_v180r12r4(
    descriptor: int,
    subject_bytes: bytes,
    *,
    chunk_bytes: int = WRITE_CHUNK_BYTES,
) -> SubjectWriteObservationV180R12R4:
    """Write the canonical result directly to the inherited O_EXCL subject FD."""

    if (
        type(descriptor) is not int
        or descriptor < 3
        or type(subject_bytes) is not bytes
        or not subject_bytes
        or len(subject_bytes) > MAX_SUBJECT_BYTES
        or type(chunk_bytes) is not int
        or chunk_bytes <= 0
        or chunk_bytes > 1024 * 1024
    ):
        _fail("worker subject write arguments are malformed")
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    before = os.fstat(descriptor)
    if (
        flags & os.O_ACCMODE not in {os.O_WRONLY, os.O_RDWR}
        or flags & os.O_APPEND
        or not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
        or before.st_size != 0
        or os.lseek(descriptor, 0, os.SEEK_CUR) != 0
    ):
        _fail("worker subject FD is not one empty preopened regular file")
    counts: list[int] = []
    offset = 0
    while offset < len(subject_bytes):
        chunk = subject_bytes[offset : offset + chunk_bytes]
        written = os.write(descriptor, chunk)
        if written != len(chunk):
            _fail("worker subject write differed from its preregistered chunk schedule")
        counts.append(written)
        offset += written
    after = os.fstat(descriptor)
    if (
        after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_mode != before.st_mode
        or stat.S_IMODE(after.st_mode) != 0o600
        or after.st_nlink != before.st_nlink
        or after.st_size != len(subject_bytes)
    ):
        _fail("worker subject FD identity or final byte count changed")
    return SubjectWriteObservationV180R12R4(
        descriptor,
        tuple(counts),
        len(subject_bytes),
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
    )


class WorkerLifecycleBridgeV180R12R4(Protocol):
    def before_stage_read(
        self, binding: SealedPayloadBindingV180R12R4
    ) -> None: ...
    def after_stage_read(self, observation: SealedPayloadReadV180R12R4) -> None: ...
    def before_operation(
        self,
        kind: core.SemanticOperationKindV180R12R4,
        label: str,
        phase: str,
        actor_role: str,
    ) -> None: ...
    def after_operation(self, result: core.ReplayOperationResultV180R12R4) -> None: ...
    def before_subject_write(self, subject_result_id: str, byte_count: int) -> None: ...
    def preflight_subject_write(
        self, result: core.WorkerReplayResultV180R12R4
    ) -> None: ...
    def after_subject_write(
        self,
        observation: SubjectWriteObservationV180R12R4,
        result: core.WorkerReplayResultV180R12R4,
    ) -> None: ...


@dataclass(slots=True)
class _OperationHooksV180R12R4:
    bridge: WorkerLifecycleBridgeV180R12R4
    open_label: str | None = None

    def before_operation(self, kind, label, phase, actor_role) -> None:
        if self.open_label is not None:
            _fail("worker attempted to overlap two semantic operations")
        self.bridge.before_operation(kind, label, phase, actor_role)
        self.open_label = label

    def after_operation(self, result) -> None:
        if self.open_label != result.label:
            _fail("worker semantic outcome crossed its ACKed intent")
        self.bridge.after_operation(result)
        self.open_label = None


@dataclass(frozen=True, slots=True)
class WorkerEffectResultV180R12R4:
    terminal_read: SealedPayloadReadV180R12R4
    verification_read: SealedPayloadReadV180R12R4
    replay_result: core.WorkerReplayResultV180R12R4
    subject_write: SubjectWriteObservationV180R12R4


@dataclass(frozen=True, slots=True)
class ValidatedWorkerHandoffV180R12R4:
    """Authenticated, metadata-only replay of the supervisor handoff.

    Construction never reads, seeks, or hashes the staged payload bytes.  The
    first payload access remains behind ``before_stage_read`` and its durable
    observer ACK in ``run_validated_worker_handoff_v180r12r4``.
    """

    document: Mapping[str, Any] = field(repr=False, compare=False)
    terminal_binding: SealedPayloadBindingV180R12R4
    verification_binding: SealedPayloadBindingV180R12R4
    terminal_stage_receipt: core.MemfdStageReceiptV180R12R4
    verification_stage_receipt: core.MemfdStageReceiptV180R12R4
    stage_hash_results: tuple[core.ReplayOperationResultV180R12R4, ...]
    stage_integrity_results: tuple[core.ReplayOperationResultV180R12R4, ...]
    execution_context: core.ReplayExecutionContextV180R12R4


def _memfd_receipt_from_document_v180r12r4(
    document: Mapping[str, Any],
) -> core.MemfdStageReceiptV180R12R4:
    role = core.CampaignInputRoleV180R12R4(document["role"])
    receipt = core.MemfdStageReceiptV180R12R4(
        document["input_snapshot_id"],
        role,
        document["supervisor_fd"],
        document["worker_fd"],
        document["device"],
        document["inode"],
        document["byte_count"],
        document["sha256"],
        tuple(document["observed_seals"]),
        document["supervisor_cloexec"],
        document["worker_read_only"],
        document["anonymous_inode"],
        document["link_count"],
        document["write_probe_errno"],
    )
    if receipt.to_document() != dict(document):
        _fail("WORKER handoff memfd receipt did not round-trip exactly")
    return receipt


def _stage_result_from_receipt_document_v180r12r4(
    document: Mapping[str, Any],
) -> core.ReplayOperationResultV180R12R4:
    kind = core.SemanticOperationKindV180R12R4(document["kind"])
    auxiliary = document["auxiliary_values"]
    expected_auxiliary_name = (
        "observed_sha256"
        if kind is core.SemanticOperationKindV180R12R4.SEMANTIC_HASH
        else "check_passed"
    )
    if (
        type(auxiliary) is not list
        or len(auxiliary) != 1
        or set(auxiliary[0]) != {"name", "value"}
        or auxiliary[0]["name"] != expected_auxiliary_name
        or (
            kind is not core.SemanticOperationKindV180R12R4.SEMANTIC_HASH
            and auxiliary[0]["value"] is not True
        )
    ):
        _fail("WORKER handoff STAGE semantic auxiliary evidence changed")
    family, family_ordinal, global_ordinal, phase, actor_role = (
        core._operation_coordinates(kind, document["label"])
    )
    if (
        document["family"] != family
        or document["family_ordinal"] != family_ordinal
        or document["ordinal"] != global_ordinal
    ):
        _fail("WORKER handoff STAGE semantic coordinates changed")
    return core.ReplayOperationResultV180R12R4(
        kind,
        document["label"],
        family,
        family_ordinal,
        global_ordinal,
        phase,
        actor_role,
        document["outcome_code"],
        document["measured_value"],
        auxiliary[0]["value"],
    )


def _proc_starttime_ticks_v180r12r4(pid: int) -> int:
    raw = open(f"/proc/{pid}/stat", "rb", buffering=0).read(16 * 1024)
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split()
    if close < 0 or len(fields) < 20:
        _fail("WORKER /proc stat observation is malformed")
    return int(fields[19])


def _proc_cgroup_line_v180r12r4(pid: int) -> str:
    raw = open(f"/proc/{pid}/cgroup", "rb", buffering=0).read(64 * 1024)
    lines = [line for line in raw.decode("ascii", "strict").splitlines() if line]
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        _fail("WORKER cgroup-v2 membership observation is malformed")
    return lines[0]


def _validate_worker_birth_placement_ownership_v180r12r4(
    document: Mapping[str, Any],
) -> None:
    if document.get("production_runtime_placement_t3") is not None:
        _fail("WORKER birth must not own the supervisor-only T3 placement receipt")


def validate_supervisor_worker_handoff_v180r12r4(
    value: Mapping[str, Any],
    *,
    verified_context: Mapping[str, Any],
) -> ValidatedWorkerHandoffV180R12R4:
    """Validate the full authenticated handoff without touching payload bytes."""

    context = _validate_verified_context_v180r12r4(verified_context)
    document = _thaw(value)
    if (
        type(document) is not dict
        # Canonical JSON sorts object keys on the wire.  Field order is a
        # construction-time assertion in the supervisor, never wire authority.
        or set(document) != set(SUPERVISOR_WORKER_HANDOFF_FIELDS)
        or document.get("schema") != SUPERVISOR_WORKER_HANDOFF_SCHEMA
    ):
        _fail("WORKER handoff schema or exact keyset changed")
    for field_name in (
        "protocol_id", "authorization_id", "authorization_evidence_id",
        "attempt_id", "campaign_attempt_record_id", "execution_slot_id",
        "execution_nonce", "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256", "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id", "operation_manifest_id",
        "native_zero_source_manifest_id", "native_zero_import_inventory_id",
        "worker_birth_operation_id", "worker_birth_receipt_id",
        "worker_birth_event_id",
    ):
        _content_id(document.get(field_name), "WORKER handoff " + field_name)
    expected_manifest = (
        supervisor_core.ledger.campaign_operation_manifest_v180r12r4(
            context["attempt_id"]
        )
    )
    if not (
        document["protocol_id"] == context["protocol_id"]
        and document["authorization_id"] == context["authorization_id"]
        and document["authorization_evidence_id"]
        == context["authorization_evidence_id"]
        and document["attempt_id"] == context["attempt_id"]
        and document["execution_slot_id"]
        == context["campaign_measurement_execution_slot_id"]
        and document["logical_occurrence_id"] == context["logical_occurrence_id"]
        and document["execution_nonce"] == context["execution_nonce"]
        and document["prelaunch_materialization_terminal_id"]
        == context["prelaunch_materialization_terminal_id"]
        and document["prelaunch_launch_manifest_sha256"]
        == context["manifest_sha256"]
        and document["prelaunch_launch_rule_id"]
        == context["prelaunch_launch_rule_id"]
        and document["measurement_launch_attempt_id"]
        == context["measurement_launch_attempt_id"]
        and document["worker_birth_operation_id"]
        == context["launch_operation_id"]
        and document["operation_manifest_id"]
        == expected_manifest["campaign_operation_manifest_id"]
        and document["one_shot_handoff"] is True
    ):
        _fail("WORKER handoff context, transport, or manifest join changed")

    snapshots = []
    memfds = []
    visibility = []
    bindings = []
    for index, (role, stage_fd) in enumerate(
        (
            (core.CampaignInputRoleV180R12R4.TERMINAL, TERMINAL_STAGE_FD),
            (
                core.CampaignInputRoleV180R12R4.VERIFICATION,
                VERIFICATION_STAGE_FD,
            ),
        )
    ):
        prefix = "terminal" if index == 0 else "verification"
        snapshot, snapshot_id = _validate_evidence_document(
            document[f"{prefix}_snapshot_document"],
            expected_schema="acfqp.campaign_stable_input_snapshot.v180r12r4",
        )
        memfd, memfd_id = _validate_evidence_document(
            document[f"{prefix}_memfd_stage_document"],
            expected_schema="acfqp.campaign_memfd_stage_receipt.v180r12r4",
        )
        visible, visible_id = _validate_evidence_document(
            document[f"{prefix}_open_visibility_document"],
            expected_schema="acfqp.campaign_fd_visibility_receipt.v180r12r4",
        )
        binding = document[f"{prefix}_stage_binding"]
        metadata = os.fstat(stage_fd)
        flags = fcntl.fcntl(stage_fd, fcntl.F_GETFL)
        seals = fcntl.fcntl(stage_fd, F_GET_SEALS)
        fact = core.FROZEN_INPUT_FACTS_V180R12R4[index]
        if not (
            type(binding) is dict
            and set(binding) == set(STAGE_FD_BINDING_FIELDS)
            and binding["fd"] == stage_fd
            and binding["device"] == metadata.st_dev == memfd["device"]
            and binding["inode"] == metadata.st_ino == memfd["inode"]
            and binding["byte_count"] == metadata.st_size == fact.byte_count
            and binding["memfd_stage_receipt_id"] == memfd_id
            and binding["open_visibility_receipt_id"] == visible_id
            and stat.S_ISREG(metadata.st_mode)
            and stat.S_IMODE(metadata.st_mode) == 0o400
            and metadata.st_nlink == 0
            and flags & os.O_ACCMODE == os.O_RDONLY
            and seals == REQUIRED_SEAL_MASK
            and snapshot["role"] == role.value
            and snapshot["stable_input_fact_id"] == fact.fact_id
            and snapshot["observed_byte_count"] == fact.byte_count
            and snapshot["observed_sha256"] == fact.sha256
            and snapshot["observed_content_id"] == fact.content_id
            and memfd["input_snapshot_id"] == snapshot_id
            and memfd["role"] == role.value
            and memfd["worker_fd"] == stage_fd
            and memfd["sha256"] == fact.sha256
            and visible["attempt_id"] == context["attempt_id"]
            and visible["stage_receipt_id"] == memfd_id
            and visible["role"] == role.value
            and visible["state"] == "OPEN"
            and visible["designated_worker_fd"] == stage_fd
            and visible["expected_device"] == metadata.st_dev
            and visible["expected_inode"] == metadata.st_ino
            and visible["visible"] is True
            and visible["read_only"] is True
        ):
            _fail("WORKER handoff stage FD/snapshot/visibility join changed")
        snapshots.append((snapshot, snapshot_id))
        memfds.append((memfd, memfd_id))
        visibility.append((visible, visible_id))
        bindings.append(
            SealedPayloadBindingV180R12R4(
                role,
                stage_fd,
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
            )
        )

    semantic_documents = document["stage_semantic_receipt_documents"]
    expected_labels = (
        *core.SEMANTIC_HASH_OPERATION_LABELS[:2],
        *core.INTEGRITY_CHECK_OPERATION_LABELS[:6],
    )
    if type(semantic_documents) is not list or len(semantic_documents) != 8:
        _fail("WORKER handoff requires the exact eight STAGE semantic receipts")
    stage_results = []
    for supplied, label in zip(semantic_documents, expected_labels):
        semantic, _semantic_id = _validate_evidence_document(
            supplied,
            expected_schema="acfqp.campaign_semantic_operation_receipt.v180r12r4",
        )
        if not (
            semantic["attempt_id"] == context["attempt_id"]
            and semantic["label"] == label
            and semantic["operation_manifest_id"] == document["operation_manifest_id"]
            and semantic["native_zero_source_manifest_id"]
            == document["native_zero_source_manifest_id"]
            and semantic["native_zero_import_inventory_id"]
            == document["native_zero_import_inventory_id"]
            and semantic["evidence_subject_id"]
            == document["campaign_attempt_record_id"]
        ):
            _fail("WORKER handoff STAGE semantic receipt join changed")
        stage_results.append(_stage_result_from_receipt_document_v180r12r4(semantic))

    birth, birth_id = _validate_evidence_document(
        document["worker_birth_document"],
        expected_schema="acfqp.campaign_pidfd_birth_receipt.v180r12r4",
    )
    _validate_worker_birth_placement_ownership_v180r12r4(birth)
    schedule = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r4(
        context["attempt_id"]
    )
    sequence = document["worker_birth_event_sequence"]
    if not (
        birth_id == document["worker_birth_receipt_id"]
        and birth["attempt_id"] == context["attempt_id"]
        and birth["operation_id"] == context["launch_operation_id"]
        and birth["process_role"] == "WORKER"
        and birth["pid"] == os.getpid()
        and birth["proc_starttime_ticks"]
        == _proc_starttime_ticks_v180r12r4(os.getpid())
        and birth["cgroup_membership_line"]
        == _proc_cgroup_line_v180r12r4(os.getpid())
        and type(sequence) is int
        and sequence in range(len(schedule))
        and schedule[sequence].event_kind == "PROCESS_BIRTH_OUTCOME"
        and schedule[sequence].actor_role == "SUPERVISOR"
        and schedule[sequence].phase == "WORKER"
        and schedule[sequence].operation_id == birth["operation_id"]
        and document["next_campaign_event_sequence"] == sequence + 1
    ):
        _fail("WORKER handoff birth/process/event join changed")

    subject_binding = document["subject_output_binding"]
    subject = os.fstat(SUBJECT_RESULT_FD)
    subject_flags = fcntl.fcntl(SUBJECT_RESULT_FD, fcntl.F_GETFL)
    if not (
        type(subject_binding) is dict
        and set(subject_binding) == set(SUBJECT_OUTPUT_BINDING_FIELDS)
        and subject_binding["fd"] == SUBJECT_RESULT_FD
        and subject_binding["device"] == subject.st_dev
        and subject_binding["inode"] == subject.st_ino
        and subject_binding["mode"] == subject.st_mode
        and subject_binding["nlink"] == subject.st_nlink == 1
        and subject_binding["initial_byte_count"] == subject.st_size == 0
        and stat.S_ISREG(subject.st_mode)
        and stat.S_IMODE(subject.st_mode) == 0o600
        and subject_flags & os.O_ACCMODE == os.O_WRONLY
    ):
        _fail("WORKER handoff subject output binding changed")

    execution_context = core.ReplayExecutionContextV180R12R4(
        protocol_id=context["protocol_id"],
        authorization_id=context["authorization_id"],
        authorization_evidence_id=context["authorization_evidence_id"],
        attempt_id=context["attempt_id"],
        campaign_attempt_record_id=document["campaign_attempt_record_id"],
        execution_slot_id=document["execution_slot_id"],
        execution_nonce=document["execution_nonce"],
        logical_occurrence_id=document["logical_occurrence_id"],
        prelaunch_materialization_terminal_id=document[
            "prelaunch_materialization_terminal_id"
        ],
        prelaunch_launch_manifest_sha256=document[
            "prelaunch_launch_manifest_sha256"
        ],
        prelaunch_launch_rule_id=document["prelaunch_launch_rule_id"],
        measurement_launch_attempt_id=document["measurement_launch_attempt_id"],
        terminal_snapshot_id=snapshots[0][1],
        verification_snapshot_id=snapshots[1][1],
        open_visibility_receipt_ids=(visibility[0][1], visibility[1][1]),
        worker_birth_receipt_id=birth_id,
        operation_manifest_id=document["operation_manifest_id"],
        native_zero_source_manifest_id=document["native_zero_source_manifest_id"],
        native_zero_import_inventory_id=document[
            "native_zero_import_inventory_id"
        ],
    )
    return ValidatedWorkerHandoffV180R12R4(
        document,
        bindings[0],
        bindings[1],
        _memfd_receipt_from_document_v180r12r4(memfds[0][0]),
        _memfd_receipt_from_document_v180r12r4(memfds[1][0]),
        tuple(stage_results[:2]),
        tuple(stage_results[2:]),
        execution_context,
    )


def reconstruct_stage_result_after_acked_reads_v180r12r4(
    handoff: ValidatedWorkerHandoffV180R12R4,
    *,
    terminal_bytes: bytes,
    verification_bytes: bytes,
) -> core.StageMeasurementResultV180R12R4:
    """Join ACKed bytes to already-authenticated STAGE results without SHA calls."""

    if type(handoff) is not ValidatedWorkerHandoffV180R12R4:
        _fail("WORKER stage reconstruction requires one validated handoff")
    terminal_document = loads_canonical_json(terminal_bytes)
    verification_document = loads_canonical_json(verification_bytes)
    if (
        type(terminal_document) is not dict
        or type(verification_document) is not dict
        or canonical_json_bytes(terminal_document) != terminal_bytes
        or canonical_json_bytes(verification_document) != verification_bytes
    ):
        _fail("WORKER ACKed staged bytes are not canonical JSON documents")
    return core.StageMeasurementResultV180R12R4(
        core.EXACT_REPLAY_CONTRACT_V180R12R4,
        terminal_bytes,
        verification_bytes,
        terminal_document,
        verification_document,
        handoff.terminal_stage_receipt.sha256,
        handoff.verification_stage_receipt.sha256,
        handoff.terminal_stage_receipt,
        handoff.verification_stage_receipt,
        handoff.stage_hash_results,
        handoff.stage_integrity_results,
    )


def run_validated_worker_handoff_v180r12r4(
    handoff: ValidatedWorkerHandoffV180R12R4,
    *,
    bridge: WorkerLifecycleBridgeV180R12R4,
) -> WorkerEffectResultV180R12R4:
    """Execute WORKER only from the full validated, authenticated handoff."""

    if type(handoff) is not ValidatedWorkerHandoffV180R12R4:
        _fail("WORKER driver requires one validated handoff")
    bridge.before_stage_read(handoff.terminal_binding)
    terminal = read_inherited_sealed_payload_v180r12r4(handoff.terminal_binding)
    bridge.after_stage_read(terminal)
    bridge.before_stage_read(handoff.verification_binding)
    verification = read_inherited_sealed_payload_v180r12r4(
        handoff.verification_binding
    )
    bridge.after_stage_read(verification)
    stage = reconstruct_stage_result_after_acked_reads_v180r12r4(
        handoff,
        terminal_bytes=terminal.returned_bytes,
        verification_bytes=verification.returned_bytes,
    )
    hooks = _OperationHooksV180R12R4(bridge)
    replay = core.replay_campaign_subject_worker_v180r12r4(
        stage,
        execution_context=handoff.execution_context,
        operation_observer=hooks,
    )
    if hooks.open_label is not None:
        _fail("worker semantic operation remained unacknowledged")
    bridge.before_subject_write(replay.subject_id, len(replay.subject_bytes))
    bridge.preflight_subject_write(replay)
    write = write_subject_result_v180r12r4(SUBJECT_RESULT_FD, replay.subject_bytes)
    bridge.after_subject_write(write, replay)
    return WorkerEffectResultV180R12R4(terminal, verification, replay, write)


def run_worker_effects_v180r12r4(
    *,
    terminal_binding: SealedPayloadBindingV180R12R4,
    verification_binding: SealedPayloadBindingV180R12R4,
    stage_result: core.StageMeasurementResultV180R12R4,
    execution_context: core.ReplayExecutionContextV180R12R4,
    subject_descriptor: int,
    bridge: WorkerLifecycleBridgeV180R12R4,
) -> WorkerEffectResultV180R12R4:
    """Run the WORKER window only after its birth event has been ACKed."""

    if (
        terminal_binding.role is not core.CampaignInputRoleV180R12R4.TERMINAL
        or verification_binding.role
        is not core.CampaignInputRoleV180R12R4.VERIFICATION
        or terminal_binding.descriptor == verification_binding.descriptor
        or type(stage_result) is not core.StageMeasurementResultV180R12R4
        or type(execution_context) is not core.ReplayExecutionContextV180R12R4
    ):
        _fail("worker effect inputs are mistyped or role-crossed")
    bridge.before_stage_read(terminal_binding)
    terminal = read_inherited_sealed_payload_v180r12r4(terminal_binding)
    bridge.after_stage_read(terminal)
    bridge.before_stage_read(verification_binding)
    verification = read_inherited_sealed_payload_v180r12r4(verification_binding)
    bridge.after_stage_read(verification)
    if (
        terminal.returned_bytes != stage_result.terminal_bytes
        or verification.returned_bytes != stage_result.verification_bytes
    ):
        _fail("worker inherited bytes disagree with the ACKed STAGE handoff")
    hooks = _OperationHooksV180R12R4(bridge)
    replay = core.replay_campaign_subject_worker_v180r12r4(
        stage_result,
        execution_context=execution_context,
        operation_observer=hooks,
    )
    if hooks.open_label is not None:
        _fail("worker semantic operation remained unacknowledged")
    bridge.before_subject_write(replay.subject_id, len(replay.subject_bytes))
    bridge.preflight_subject_write(replay)
    write = write_subject_result_v180r12r4(
        subject_descriptor, replay.subject_bytes
    )
    bridge.after_subject_write(write, replay)
    return WorkerEffectResultV180R12R4(terminal, verification, replay, write)


def _validate_verified_context_v180r12r4(
    value: Mapping[str, Any],
) -> types.MappingProxyType:
    if type(value) is not types.MappingProxyType or set(value) != _VERIFIED_CONTEXT_KEYS:
        _fail("worker requires the exact bootstrap-verified immutable context")
    ids = (
        value["protocol_id"], value["authorization_id"],
        value["authorization_evidence_id"], value["attempt_id"],
        value["campaign_measurement_execution_slot_id"],
        value["logical_occurrence_id"], value["execution_nonce"],
        value["prelaunch_materialization_terminal_id"],
        value["prelaunch_launch_rule_id"],
        value["measurement_launch_attempt_id"], value["launch_operation_id"],
        value["manifest_sha256"], value["precompiled_source_bundle_sha256"],
        value["parent_context_mac"],
    )
    target_payload = value["target_payload"]
    expected_attempt_id = identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
        protocol_id=value["protocol_id"],
        authorization_id=value["authorization_id"],
        authorization_evidence_id=value["authorization_evidence_id"],
        campaign_measurement_execution_slot_id=value[
            "campaign_measurement_execution_slot_id"
        ],
        logical_occurrence_id=value["logical_occurrence_id"],
        execution_nonce=value["execution_nonce"],
    )
    expected_launch_operation_id = next(
        row.operation_id
        for row in supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r4(
            expected_attempt_id
        )
        if row.event_kind == "PROCESS_BIRTH_INTENT"
        and row.actor_role == "SUPERVISOR"
        and row.phase == "WORKER"
    )
    if not (
        value["schema"] == "acfqp.v180r12r4_verified_internal_launch_context.v1"
        and value["target"] == "worker"
        and value["actor_role"] == "WORKER"
        and value["parent_actor_role"] == "SUPERVISOR"
        and value["attempt_id"] == expected_attempt_id
        and value["launch_operation_id"] == expected_launch_operation_id
        and all(type(item) is str and len(item) == 64 and all(char in "0123456789abcdef" for char in item) for item in ids)
        and value["inherited_fd_roles"] == _EXPECTED_FD_ROLES
        and type(target_payload) is types.MappingProxyType
        and dict(target_payload)
        == {
            "terminal_stage_byte_count": 199_755,
            "verification_stage_byte_count": 2_752,
            "subject_result_initial_byte_count": 0,
        }
        and type(value["parent_to_child_mac_key"]) is bytes
        and len(value["parent_to_child_mac_key"]) == 32
        and value["context_consumed_once"] is True
    ):
        _fail("worker verified context role/identity/MAC binding changed")
    for closed in (INTERNAL_MAC_KEY_FD, INTERNAL_CONTEXT_FD):
        try:
            os.fstat(closed)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
        else:
            _fail("bootstrap key/context FD remained open at worker dispatch")
    for descriptor in (
        PRECOMPILED_SOURCE_BUNDLE_FD, INTERNAL_IPC_FD, TERMINAL_STAGE_FD,
        VERIFICATION_STAGE_FD, SUBJECT_RESULT_FD,
    ):
        if os.get_inheritable(descriptor):
            _fail("worker operational FD is not CLOEXEC at runner dispatch")
    duplicate = socket.fromfd(INTERNAL_IPC_FD, socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        if duplicate.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
            _fail("worker IPC descriptor is not SOCK_SEQPACKET")
    finally:
        duplicate.close()
    bundle = os.fstat(PRECOMPILED_SOURCE_BUNDLE_FD)
    bundle_flags = fcntl.fcntl(PRECOMPILED_SOURCE_BUNDLE_FD, fcntl.F_GETFL)
    if not (
        stat.S_ISREG(bundle.st_mode)
        and bundle.st_nlink == 0
        and bundle.st_size > 0
        and stat.S_IMODE(bundle.st_mode) == 0o400
        and bundle_flags & os.O_ACCMODE == os.O_RDONLY
        and fcntl.fcntl(PRECOMPILED_SOURCE_BUNDLE_FD, F_GET_SEALS)
        == REQUIRED_SEAL_MASK
    ):
        _fail("worker precompiled bundle FD changed")
    for descriptor, expected_size in (
        (TERMINAL_STAGE_FD, 199_755), (VERIFICATION_STAGE_FD, 2_752)
    ):
        metadata = os.fstat(descriptor)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 0
            or metadata.st_size != expected_size
            or flags & os.O_ACCMODE != os.O_RDONLY
            or fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEAL_MASK
        ):
            _fail("worker inherited staged payload FD changed")
    subject = os.fstat(SUBJECT_RESULT_FD)
    subject_flags = fcntl.fcntl(SUBJECT_RESULT_FD, fcntl.F_GETFL)
    if not (
        stat.S_ISREG(subject.st_mode)
        and subject.st_nlink == 1
        and subject.st_size == 0
        and stat.S_IMODE(subject.st_mode) == 0o600
        and subject_flags & os.O_ACCMODE == os.O_WRONLY
    ):
        _fail("worker subject-result inherited FD changed")
    return value


_RUNTIME_FRAME_SCHEMA = "acfqp.v180r12r4_runtime_ipc_frame.v1"
_EVENT_PROPOSAL_SCHEMA = "acfqp.v180r12r4_event_proposal.v1"
_EVENT_ACK_SCHEMA = "acfqp.v180r12r4_event_ack.v1"
_RUNTIME_FRAME_FIELDS = {
    "schema", "channel_id", "direction", "sender_actor_role",
    "recipient_actor_role", "frame_type", "sequence", "body", "mac",
}
_EVENT_ACK_FIELDS = {
    "schema", "protocol_id", "authorization_id",
    "authorization_evidence_id", "attempt_id", "campaign_event_sequence",
    "event_id", "event_file_sha256",
    "durable_file_and_directory_fsync_complete",
}


class _AuthenticatedWorkerChannelV180R12R4:
    """Exact WORKER side of the frozen supervisor/worker seqpacket channel."""

    def __init__(
        self,
        channel: socket.socket,
        secret: bytes,
        context: Mapping[str, Any],
    ) -> None:
        if type(secret) is not bytes or len(secret) != 32:
            _fail("WORKER channel secret changed")
        if channel.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET:
            _fail("WORKER channel is not SOCK_SEQPACKET")
        self.channel = channel
        self.context = context
        self.channel_id = _content_id(
            context["launch_operation_id"], "WORKER channel ID"
        )
        expected = next(
            row.operation_id
            for row in supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r4(
                context["attempt_id"]
            )
            if row.event_kind == "PROCESS_BIRTH_INTENT"
            and row.actor_role == "SUPERVISOR"
            and row.phase == "WORKER"
        )
        if self.channel_id != expected:
            _fail("WORKER channel ID differs from its birth operation")
        self.send_key = self._direction_key(secret, "CHILD_TO_PARENT")
        self.receive_key = self._direction_key(secret, "PARENT_TO_CHILD")
        self.next_send_sequence = 0
        self.next_receive_sequence = 0

    def _direction_key(self, secret: bytes, direction: str) -> bytes:
        document = {
            "schema": "acfqp.v180r12r4_runtime_channel_key_context.v1",
            "channel_id": self.channel_id,
            "protocol_id": self.context["protocol_id"],
            "authorization_id": self.context["authorization_id"],
            "authorization_evidence_id": self.context[
                "authorization_evidence_id"
            ],
            "attempt_id": self.context["attempt_id"],
            "parent_actor_role": "SUPERVISOR",
            "child_actor_role": "WORKER",
            "direction": direction,
        }
        return hashlib.blake2s(
            canonical_json_bytes(document), key=secret, digest_size=32
        ).digest()

    def _common_body(self, body: Mapping[str, Any]) -> bool:
        return (
            body.get("protocol_id") == self.context["protocol_id"]
            and body.get("authorization_id") == self.context["authorization_id"]
            and body.get("authorization_evidence_id")
            == self.context["authorization_evidence_id"]
            and body.get("attempt_id") == self.context["attempt_id"]
        )

    def _validate_received_body(
        self, frame_type: str, body: Mapping[str, Any]
    ) -> dict[str, Any]:
        document = _thaw(body)
        if type(document) is not dict or not self._common_body(document):
            _fail("WORKER received frame context changed")
        if frame_type == "WORKER_HANDOFF":
            if not (
                self.next_receive_sequence == 0
                and set(document) == set(SUPERVISOR_WORKER_HANDOFF_FIELDS)
                and document.get("schema") == SUPERVISOR_WORKER_HANDOFF_SCHEMA
                and document.get("one_shot_handoff") is True
            ):
                _fail("WORKER first frame is not the exact one-shot HANDOFF")
            return document
        if frame_type == "EVENT_ACK":
            if not (
                self.next_receive_sequence >= 1
                and set(document) == _EVENT_ACK_FIELDS
                and document.get("schema") == _EVENT_ACK_SCHEMA
                and type(document.get("campaign_event_sequence")) is int
                and document.get("durable_file_and_directory_fsync_complete")
                is True
            ):
                _fail("WORKER event ACK body changed")
            _content_id(document.get("event_id"), "WORKER ACK event ID")
            _content_id(
                document.get("event_file_sha256"), "WORKER ACK event SHA-256"
            )
            return document
        _fail("WORKER received an unregistered frame type")

    def receive(self) -> tuple[str, dict[str, Any]]:
        raw, ancillary, flags, address = self.channel.recvmsg(FRAME_BYTE_CAP + 1)
        if (
            flags != 0
            or ancillary
            or address not in (None, "", b"")
            or not raw
            or len(raw) > FRAME_BYTE_CAP
        ):
            _fail("WORKER frame carried flags, ancillary, address, or bad size")
        frame = _canonical_object_v180r12r4(raw, "WORKER IPC frame")
        if set(frame) != _RUNTIME_FRAME_FIELDS:
            _fail("WORKER IPC frame keyset changed")
        unsigned_fields = (
            "schema", "channel_id", "direction", "sender_actor_role",
            "recipient_actor_role", "frame_type", "sequence", "body",
        )
        unsigned = {name: frame[name] for name in unsigned_fields}
        expected_mac = hashlib.blake2s(
            canonical_json_bytes(unsigned), key=self.receive_key, digest_size=32
        ).hexdigest()
        if not (
            frame["schema"] == _RUNTIME_FRAME_SCHEMA
            and frame["channel_id"] == self.channel_id
            and frame["direction"] == "PARENT_TO_CHILD"
            and frame["sender_actor_role"] == "SUPERVISOR"
            and frame["recipient_actor_role"] == "WORKER"
            and type(frame["frame_type"]) is str
            and frame["sequence"] == self.next_receive_sequence
            and type(frame["body"]) is dict
            and hmac.compare_digest(frame["mac"], expected_mac)
        ):
            _fail("WORKER IPC frame MAC, role, channel, or sequence changed")
        body = self._validate_received_body(frame["frame_type"], frame["body"])
        self.next_receive_sequence += 1
        return frame["frame_type"], body

    def _encoded_proposal(self, body: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
        document = _thaw(body)
        if not (
            type(document) is dict
            and set(document)
            == {
                "schema", "protocol_id", "authorization_id",
                "authorization_evidence_id", "attempt_id",
                "campaign_event_sequence", "phase", "actor_role",
                "event_kind", "operation_id", "payload", "evidence_documents",
            }
            and document.get("schema") == _EVENT_PROPOSAL_SCHEMA
            and self._common_body(document)
        ):
            _fail("WORKER proposal body changed")
        unsigned = {
            "schema": _RUNTIME_FRAME_SCHEMA,
            "channel_id": self.channel_id,
            "direction": "CHILD_TO_PARENT",
            "sender_actor_role": "WORKER",
            "recipient_actor_role": "SUPERVISOR",
            "frame_type": "EVENT_PROPOSAL",
            "sequence": self.next_send_sequence,
            "body": document,
        }
        mac = hashlib.blake2s(
            canonical_json_bytes(unsigned), key=self.send_key, digest_size=32
        ).hexdigest()
        raw = canonical_json_bytes({**unsigned, "mac": mac})
        if len(raw) > FRAME_BYTE_CAP:
            _fail("WORKER proposal exceeds the exact frame byte cap")
        return document, raw

    def preflight_proposal(self, body: Mapping[str, Any]) -> bytes:
        """Return the exact next signed frame bytes without sending them."""

        _document, raw = self._encoded_proposal(body)
        return raw

    def send_proposal(
        self,
        body: Mapping[str, Any],
        *,
        preflight_raw: bytes | None = None,
    ) -> None:
        _document, raw = self._encoded_proposal(body)
        if preflight_raw is not None and (
            type(preflight_raw) is not bytes or preflight_raw != raw
        ):
            _fail("WORKER proposal differs from its pre-effect exact preflight")
        written = self.channel.send(raw)
        if written != len(raw):
            _fail("WORKER proposal made a partial seqpacket write")
        self.next_send_sequence += 1


@dataclass(slots=True)
class _AuthenticatedWorkerBridgeV180R12R4:
    channel: _AuthenticatedWorkerChannelV180R12R4
    handoff: ValidatedWorkerHandoffV180R12R4
    campaign_event_sequence: int
    open_event: tuple[str, str] | None = None
    pending_subject_outcome: tuple[
        dict[str, Any], bytes, tuple[int, ...], str
    ] | None = None

    @property
    def context(self) -> core.ReplayExecutionContextV180R12R4:
        return self.handoff.execution_context

    def _planned(self):
        schedule = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r4(
            self.context.attempt_id
        )
        if self.campaign_event_sequence >= len(schedule):
            _fail("WORKER attempted to emit beyond the success schedule")
        return schedule[self.campaign_event_sequence]

    def _proposal_body(
        self,
        *,
        event_kind: str,
        evidence_documents: Sequence[Mapping[str, Any]] = (),
        measured_value: int | None = None,
    ) -> dict[str, Any]:
        planned = self._planned()
        rows = [_thaw(row) for row in evidence_documents]
        direct_id = None
        if rows:
            schema = rows[0].get("schema")
            _direct, direct_id = _validate_evidence_document(
                rows[0], expected_schema=schema
            )
        if not (
            planned.event_kind == event_kind
            and planned.actor_role == "WORKER"
            and planned.phase == "WORKER"
        ):
            _fail("WORKER callback differs from the exact next event")
        payload = supervisor_core.campaign_event_payload_v180r12r4(
            event_kind=event_kind,
            evidence_id=direct_id,
            measured_value=measured_value,
            auxiliary_values=(),
        )
        return {
            "schema": _EVENT_PROPOSAL_SCHEMA,
            "protocol_id": self.context.protocol_id,
            "authorization_id": self.context.authorization_id,
            "authorization_evidence_id": self.context.authorization_evidence_id,
            "attempt_id": self.context.attempt_id,
            "campaign_event_sequence": self.campaign_event_sequence,
            "phase": planned.phase,
            "actor_role": planned.actor_role,
            "event_kind": planned.event_kind,
            "operation_id": planned.operation_id,
            "payload": payload,
            "evidence_documents": rows,
        }

    def _propose_and_ack(
        self,
        *,
        event_kind: str,
        evidence_documents: Sequence[Mapping[str, Any]] = (),
        measured_value: int | None = None,
        preflight_raw: bytes | None = None,
    ) -> None:
        body = self._proposal_body(
            event_kind=event_kind,
            evidence_documents=evidence_documents,
            measured_value=measured_value,
        )
        self.channel.send_proposal(body, preflight_raw=preflight_raw)
        frame_type, ack = self.channel.receive()
        if not (
            frame_type == "EVENT_ACK"
            and ack["campaign_event_sequence"] == self.campaign_event_sequence
        ):
            _fail("WORKER ACK crossed its exact proposed event")
        self.campaign_event_sequence += 1

    def _intent(self, event_kind: str) -> None:
        if self.open_event is not None:
            _fail("WORKER attempted overlapping registered operations")
        planned = self._planned()
        self.open_event = (event_kind.removesuffix("_INTENT"), planned.operation_id)
        self._propose_and_ack(event_kind=event_kind)

    def _outcome(
        self,
        event_kind: str,
        document: Mapping[str, Any],
        *,
        measured_value: int,
        supporting: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        planned = self._planned()
        stem = event_kind.removesuffix("_OUTCOME")
        if self.open_event != (stem, planned.operation_id):
            _fail("WORKER outcome crossed its ACKed intent operation")
        self._propose_and_ack(
            event_kind=event_kind,
            evidence_documents=(document, *supporting),
            measured_value=measured_value,
        )
        self.open_event = None

    def before_stage_read(self, binding: SealedPayloadBindingV180R12R4) -> None:
        planned = self._planned()
        expected = (
            self.handoff.terminal_binding
            if planned.operation_id
            == next(
                row.operation_id
                for row in supervisor_core.ledger.build_campaign_operation_schedule_v180r12r4(
                    self.context.attempt_id
                )
                if row.slot == "INPUT_READ"
                and row.family == "SEALED_STAGE"
                and row.ordinal == 0
            )
            else self.handoff.verification_binding
        )
        if binding != expected:
            _fail("WORKER sealed-stage read role/order changed")
        self._intent("INPUT_READ_INTENT")

    def after_stage_read(self, observation: SealedPayloadReadV180R12R4) -> None:
        planned = self._planned()
        source_id = (
            self.handoff.terminal_stage_receipt.stage_receipt_id
            if observation.binding.role is core.CampaignInputRoleV180R12R4.TERMINAL
            else self.handoff.verification_stage_receipt.stage_receipt_id
        )
        receipt = supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r4(
            protocol_id=self.context.protocol_id,
            authorization_id=self.context.authorization_id,
            attempt_id=self.context.attempt_id,
            operation_id=planned.operation_id,
            event_kind="INPUT_READ_OUTCOME",
            measured_value=observation.returned_byte_count,
            returned_chunk_byte_counts=observation.returned_chunk_byte_counts,
            source_evidence_id=source_id,
            target_evidence_id=self.context.worker_birth_receipt_id,
        )
        self._outcome(
            "INPUT_READ_OUTCOME",
            receipt,
            measured_value=observation.returned_byte_count,
        )

    def before_operation(self, kind, label, phase, actor_role) -> None:
        if phase != "WORKER" or actor_role != "WORKER":
            _fail("WORKER semantic callback crossed its process role")
        expected_kind = kind.value + "_INTENT"
        planned = self._planned()
        family, family_ordinal, _ordinal, _phase, _actor = core._operation_coordinates(
            kind, label
        )
        expected_operation_id = core.domains.extension_content_id_v180r12r4e(
            core.domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R4E_DOMAIN,
            {
                "schema": "acfqp.campaign_operation_identity.v180r12r4",
                "schema_version": core.SCHEMA_VERSION,
                "attempt_id": self.context.attempt_id,
                "slot": kind.value,
                "family": family,
                "ordinal": family_ordinal,
            },
        )
        if planned.operation_id != expected_operation_id:
            _fail("WORKER semantic label differs from the next manifest operation")
        self._intent(expected_kind)

    def after_operation(self, result: core.ReplayOperationResultV180R12R4) -> None:
        receipt = core.semantic_operation_receipt_v180r12r4(
            attempt_id=self.context.attempt_id,
            operation_manifest_id=self.context.operation_manifest_id,
            native_zero_source_manifest_id=self.context.native_zero_source_manifest_id,
            native_zero_import_inventory_id=(
                self.context.native_zero_import_inventory_id
            ),
            evidence_subject_id=self.context.campaign_attempt_record_id,
            result=result,
        )
        self._outcome(
            result.kind.value + "_OUTCOME",
            receipt.to_document(),
            measured_value=1,
        )

    def before_subject_write(self, subject_result_id: str, byte_count: int) -> None:
        _content_id(subject_result_id, "WORKER subject-result ID")
        if type(byte_count) is not int or byte_count <= 0 or byte_count > MAX_SUBJECT_BYTES:
            _fail("WORKER subject byte count changed")
        self._intent("SUBJECT_WRITE_INTENT")

    def preflight_subject_write(
        self, result: core.WorkerReplayResultV180R12R4
    ) -> None:
        """Freeze the exact seq608 bytes before the first subject write syscall."""

        if (
            type(result) is not core.WorkerReplayResultV180R12R4
            or self.pending_subject_outcome is not None
            or self.open_event is None
        ):
            _fail("WORKER subject preflight state changed")
        subject_document = _canonical_object_v180r12r4(
            result.subject_bytes, "WORKER subject-result bytes"
        )
        counts = tuple(
            min(WRITE_CHUNK_BYTES, len(result.subject_bytes) - offset)
            for offset in range(0, len(result.subject_bytes), WRITE_CHUNK_BYTES)
        )
        planned = self._planned()
        receipt = supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r4(
            protocol_id=self.context.protocol_id,
            authorization_id=self.context.authorization_id,
            attempt_id=self.context.attempt_id,
            operation_id=planned.operation_id,
            event_kind="SUBJECT_WRITE_OUTCOME",
            measured_value=len(result.subject_bytes),
            returned_chunk_byte_counts=counts,
            source_evidence_id=result.subject_id,
            target_evidence_id=self.context.worker_birth_receipt_id,
        )
        body = self._proposal_body(
            event_kind="SUBJECT_WRITE_OUTCOME",
            evidence_documents=(receipt, subject_document),
            measured_value=len(result.subject_bytes),
        )
        raw = self.channel.preflight_proposal(body)
        self.pending_subject_outcome = (body, raw, counts, result.subject_id)

    def after_subject_write(
        self,
        observation: SubjectWriteObservationV180R12R4,
        result: core.WorkerReplayResultV180R12R4,
    ) -> None:
        pending = self.pending_subject_outcome
        if pending is None:
            _fail("WORKER subject write has no exact pre-effect proposal")
        body, raw, counts, subject_id = pending
        if (
            subject_id != result.subject_id
            or counts != observation.returned_chunk_byte_counts
            or observation.returned_byte_count != len(result.subject_bytes)
        ):
            _fail("WORKER subject write differed from its exact preflight")
        planned = self._planned()
        if self.open_event != ("SUBJECT_WRITE", planned.operation_id):
            _fail("WORKER subject outcome crossed its ACKed intent operation")
        expected_body = self._proposal_body(
            event_kind="SUBJECT_WRITE_OUTCOME",
            evidence_documents=tuple(body["evidence_documents"]),
            measured_value=observation.returned_byte_count,
        )
        if expected_body != body:
            _fail("WORKER subject outcome body changed after the physical write")
        self.channel.send_proposal(body, preflight_raw=raw)
        frame_type, ack = self.channel.receive()
        if not (
            frame_type == "EVENT_ACK"
            and ack["campaign_event_sequence"] == self.campaign_event_sequence
        ):
            _fail("WORKER subject outcome ACK crossed its exact event")
        self.campaign_event_sequence += 1
        self.open_event = None
        self.pending_subject_outcome = None


def _run_bootstrap_verified_worker_v180r12r4(
    context: types.MappingProxyType,
) -> None:
    duplicate = socket.fromfd(
        INTERNAL_IPC_FD, socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    try:
        channel = _AuthenticatedWorkerChannelV180R12R4(
            duplicate, context["parent_to_child_mac_key"], context
        )
        frame_type, body = channel.receive()
        if frame_type != "WORKER_HANDOFF":
            _fail("WORKER first authenticated frame is not HANDOFF")
        handoff = validate_supervisor_worker_handoff_v180r12r4(
            body, verified_context=context
        )
        bridge = _AuthenticatedWorkerBridgeV180R12R4(
            channel,
            handoff,
            handoff.document["next_campaign_event_sequence"],
        )
        run_validated_worker_handoff_v180r12r4(handoff, bridge=bridge)
        if bridge.open_event is not None:
            _fail("WORKER returned with an unclosed registered operation")
        expected_next = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r4(
            context["attempt_id"]
        )[bridge.campaign_event_sequence]
        if not (
            expected_next.event_kind == "PROCESS_REAP"
            and expected_next.actor_role == "SUPERVISOR"
            and expected_next.phase == "WORKER"
        ):
            _fail("WORKER did not stop exactly before supervisor-owned reap")
        duplicate.shutdown(socket.SHUT_WR)
    finally:
        duplicate.close()


def bootstrap_entrypoint_v180r12r4(verified_context: Mapping[str, Any]) -> None:
    context = _validate_verified_context_v180r12r4(verified_context)
    _run_bootstrap_verified_worker_v180r12r4(context)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    raise V180R12R4WorkerRuntimeError(
        "direct worker invocation is forbidden; the retained bootstrap must "
        "supply its authenticated internal launch context and bridge"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise
