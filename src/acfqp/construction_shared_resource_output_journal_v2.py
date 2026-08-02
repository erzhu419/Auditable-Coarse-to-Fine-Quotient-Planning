"""Raw durable-output evidence for ``io.output_bytes``.

The production worker V1 first commits ``operational-output.json`` with its
existing no-replace and durability protocol.  This journal adopts that exact
inode from an authenticated ``PARENT_OUTPUT`` observation: it neither copies,
renames, nor requires the worker output to pretend it has an ``artifact_role``
field.  Only after two direct-child reap observations, an empty-child-cgroup
observation, and an exclusive broker-writer observation are bound may the
broker remove its write bits, fsync the file and directory, and open suffix
finalization.

The broker pins and reads the worker result as ``P``, solves an exact
eight-role byte-count fixed point in memory (``P`` plus seven broker-rendered
roles), writes the seven suffix roles outside the measured child cgroup, and
performs file/directory fsync plus inode-pinned readback.  It then rereads the
same pinned result descriptor and requires ``P' == P`` and that the directory
entry still names the same inode.

Only exact newly written file extents are summed.  Nested model/epoch/
serialized-byte fields are never charged again.  The emitted four components
match the exact schemas required by
:mod:`construction_shared_resource_resolution_v2`.

The legacy construction helper remains available only as an explicitly
synthetic, nonproduction first role and cannot produce an exact-semantic live
source.

This module emits raw evidence only.  Kernel observation IDs and source
completeness still require later semantic verification; no CounterRecord or
formal actual is issued.  Every identity uses a centrally registered,
role-separated Phase 3E domain.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import os
import re
import stat
import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_DURABLE_WRITE_EVENT_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FINALIZATION_SESSION_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FIXED_POINT_ITERATION_V2_DOMAIN,
    V075_K7_DURABLE_OUTPUT_FIXED_POINT_V2_DOMAIN,
    V075_K7_EIGHT_ROLE_OUTPUT_MANIFEST_V2_DOMAIN,
    V075_K7_EXCLUSIVE_WRITER_ATTESTATION_V2_DOMAIN,
    V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.20"
PROFILE_KEY = "construction_shared_resource_output_journal_v2"
OUTPUT_PATH = "io.output_bytes"

FIXED_POINT_SCHEMA_ID = "acfqp.v075_k7_durable_output_fixed_point.v2"
EXCLUSIVE_WRITER_SCHEMA_ID = (
    "acfqp.v075_k7_exclusive_writer_attestation.v2"
)
CUTOFF_SCHEMA_ID = "acfqp.v075_k7_operational_cutoff_attestation.v2"
OUTPUT_MANIFEST_SCHEMA_ID = "acfqp.v075_k7_eight_role_output_manifest.v2"

ROLE_ORDER = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
BUSINESS_ROLE = fixed_v1.OperationalArtifactRoleV1.BUSINESS_RESULT.value
MANIFEST_ROLE = fixed_v1.OperationalArtifactRoleV1.OUTPUT_MANIFEST.value
BROKER_ROLE_ORDER = tuple(role for role in ROLE_ORDER if role != BUSINESS_ROLE)

ROLE_FILENAMES = {
    "BUSINESS_RESULT": worker_v1.OUTPUT_NAME,
    "OPERATIONAL_TRACE": "operational_trace.json",
    "TERMINAL_ARTIFACT": "terminal_artifact.json",
    "COUNTER_RECORD_SET": "counter_record_set.json",
    "WORK_VECTOR": "work_vector.json",
    "COMPARISON_VECTOR": "comparison_vector.json",
    "ACTUAL_PROJECTION_PROOF": "actual_projection_proof.json",
    "OUTPUT_MANIFEST": "output_manifest.json",
}

MAX_ROLE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_FIXED_POINT_ITERATIONS = 64

OUTPUT_FINALIZATION_SESSION_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FINALIZATION_SESSION_V2_DOMAIN
)
DURABLE_WRITE_EVENT_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_DURABLE_WRITE_EVENT_V2_DOMAIN
)
FIXED_POINT_ITERATION_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FIXED_POINT_ITERATION_V2_DOMAIN
)
_COMPONENT_DOMAIN = {
    FIXED_POINT_SCHEMA_ID: V075_K7_DURABLE_OUTPUT_FIXED_POINT_V2_DOMAIN,
    EXCLUSIVE_WRITER_SCHEMA_ID: V075_K7_EXCLUSIVE_WRITER_ATTESTATION_V2_DOMAIN,
    CUTOFF_SCHEMA_ID: V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    OUTPUT_MANIFEST_SCHEMA_ID: V075_K7_EIGHT_ROLE_OUTPUT_MANIFEST_V2_DOMAIN,
}
_COMPONENT_ID_FIELD = {
    FIXED_POINT_SCHEMA_ID: "durable_output_fixed_point_id",
    EXCLUSIVE_WRITER_SCHEMA_ID: "exclusive_writer_attestation_id",
    CUTOFF_SCHEMA_ID: "operational_cutoff_attestation_id",
    OUTPUT_MANIFEST_SCHEMA_ID: "eight_role_output_manifest_id",
}

REQUESTED_PHASE3E_DOMAIN_TAGS = tuple(
    sorted(
        {
            OUTPUT_FINALIZATION_SESSION_V2_DOMAIN,
            DURABLE_WRITE_EVENT_V2_DOMAIN,
            FIXED_POINT_ITERATION_V2_DOMAIN,
            *_COMPONENT_DOMAIN.values(),
        }
    )
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BUSINESS_ISSUER = object()
_FINALIZATION_ISSUER = object()
_BUNDLE_ISSUER = object()
_REPLAY_ISSUER = object()
_DIRECTORY_LEASE_LOCK = threading.Lock()
_CONSUMED_DIRECTORY_IDENTITIES: set[tuple[int, int, int]] = set()
_PARENT_OUTPUT_CONSUMPTION_LOCK = threading.Lock()
_CONSUMED_PARENT_OUTPUT_OBSERVATION_IDS: set[str] = set()

RendererV2 = Callable[[int], Mapping[str, bytes]]


class ConstructionSharedResourceOutputJournalV2Error(ValueError):
    """The durable output, fixed point, or raw replay is invalid."""


class OutputFinalizationStateV2(str, Enum):
    OPEN = "OPEN"
    FINALIZED = "FINALIZED"
    FAILED = "FAILED"


class OutputFirstRoleAuthorityV2(str, Enum):
    PRODUCTION_WORKER_V1_ADOPTED = "PRODUCTION_WORKER_V1_ADOPTED"
    SYNTHETIC_CONSTRUCTION_ONLY = "SYNTHETIC_CONSTRUCTION_ONLY"


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceOutputJournalV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 digest")
    return value


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("output evidence used an undeclared central domain")
    return content_id(domain, dict(payload))


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _exact_fields(document: Any, fields: set[str], label: str) -> None:
    try:
        require_exact_fields(document, fields, context=label)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            f"{label} fields are not exact"
        ) from error


def _hash_payload(raw: bytes) -> tuple[str, int]:
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _identity_document(
    *,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
) -> dict[str, str]:
    return {
        "live_envelope_id": live_envelope_id,
        "occurrence_id": occurrence_id,
        "route_attempt_id": route_attempt_id,
        "decision_point_id": decision_point_id,
        "measurement_window_id": measurement_window_id,
    }


_IDENTITY_FIELDS = {
    "live_envelope_id",
    "occurrence_id",
    "route_attempt_id",
    "decision_point_id",
    "measurement_window_id",
}
_COMMON_COMPONENT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "raw_evidence_only",
    "semantic_source_verified",
    "counter_record_issued",
    "formal_value_authorized",
}
_ELIGIBILITY_FIELDS = {
    "first_role_authority",
    "production_semantic_eligible",
    "synthetic_construction_only",
}


def _fd_identity(fd: int, *, directory: bool | None = None) -> dict[str, int]:
    if type(fd) is not int or fd < 0:
        _fail("output descriptor is mistyped")
    try:
        status = os.fstat(fd)
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "output descriptor is unavailable"
        ) from error
    if directory is True and not stat.S_ISDIR(status.st_mode):
        _fail("output directory descriptor is not a directory")
    if directory is False and not stat.S_ISREG(status.st_mode):
        _fail("output artifact descriptor is not a regular file")
    return {
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": status.st_mode,
        "owner_uid": status.st_uid,
        "owner_gid": status.st_gid,
        "link_count": status.st_nlink,
        "byte_extent": status.st_size,
        "ctime_ns": status.st_ctime_ns,
    }


def _same_inode(first: Mapping[str, int], second: Mapping[str, int]) -> bool:
    return (first["device"], first["inode"]) == (
        second["device"],
        second["inode"],
    )


def _read_exact(fd: int, expected_size: int) -> bytes:
    _nonnegative(expected_size, "readback size")
    try:
        raw = os.pread(fd, expected_size + 1, 0)
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "inode-pinned readback failed"
        ) from error
    if len(raw) != expected_size:
        _fail("inode-pinned readback extent changed")
    return raw


def _open_readonly_at(directory_fd: int, filename: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        result = os.open(filename, flags, dir_fd=directory_fd)
        os.set_inheritable(result, False)
        return result
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "output artifact cannot be opened without following links"
        ) from error


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        try:
            written = os.write(fd, raw[offset:])
        except OSError as error:
            raise ConstructionSharedResourceOutputJournalV2Error(
                "durable artifact write failed"
            ) from error
        if written <= 0:
            _fail("durable artifact write made no progress")
        offset += written


def _validate_role_bytes(role: str, raw: bytes, candidate: int | None) -> None:
    if type(raw) is not bytes or not raw or len(raw) > MAX_ROLE_BYTES:
        _fail("operational role bytes are empty, mistyped, or over cap")
    document = _canonical_object(raw, f"{role} role bytes")
    if role == BUSINESS_ROLE:
        _fail("production first-role bytes require the worker V1 verifier")
    if document.get("artifact_role") != role:
        _fail("operational artifact role label differs from its role")
    embedded = document.get("io.output_bytes")
    if role == MANIFEST_ROLE:
        if type(embedded) is not int or embedded != candidate:
            _fail("OUTPUT_MANIFEST does not embed the fixed-point candidate")
    elif "io.output_bytes" in document and embedded != candidate:
        _fail("broker role embeds a stale output-byte candidate")


def _validate_synthetic_first_role_bytes(raw: bytes) -> None:
    if type(raw) is not bytes or not raw or len(raw) > MAX_ROLE_BYTES:
        _fail("synthetic first-role bytes are empty, mistyped, or over cap")
    document = _canonical_object(raw, "synthetic BUSINESS_RESULT role bytes")
    if (
        document.get("artifact_role") != BUSINESS_ROLE
        or "io.output_bytes" in document
    ):
        _fail("synthetic BUSINESS_RESULT role label or output claim changed")


def _durable_create(
    *, directory_fd: int, filename: str, raw: bytes
) -> tuple[dict[str, int], bytes]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    writer = -1
    reader = -1
    try:
        writer = os.open(filename, flags, 0o600, dir_fd=directory_fd)
        os.set_inheritable(writer, False)
        _write_all(writer, raw)
        os.fchmod(writer, 0o400)
        os.fsync(writer)
        before = _fd_identity(writer, directory=False)
        if before["byte_extent"] != len(raw) or before["link_count"] != 1:
            _fail("new output extent or link count changed before close")
        os.close(writer)
        writer = -1
        reader = _open_readonly_at(directory_fd, filename)
        after = _fd_identity(reader, directory=False)
        if not _same_inode(before, after) or after["byte_extent"] != len(raw):
            _fail("new output inode was replaced before readback")
        readback = _read_exact(reader, len(raw))
        if readback != raw:
            _fail("new output readback differs from written bytes")
        return after, readback
    except FileExistsError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "O_EXCL/no-replace output role already exists"
        ) from error
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "durable O_EXCL output commit failed"
        ) from error
    finally:
        if writer >= 0:
            os.close(writer)
        if reader >= 0:
            os.close(reader)


def _component_payload(
    schema_id: str, body: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema": schema_id,
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        **dict(body),
        "raw_evidence_only": True,
        "semantic_source_verified": False,
        "counter_record_issued": False,
        "formal_value_authorized": False,
    }


def _freeze_component_bytes(
    schema_id: str, body: Mapping[str, Any]
) -> tuple[str, bytes]:
    payload = _component_payload(schema_id, body)
    artifact_id = _hash(_COMPONENT_DOMAIN[schema_id], payload)
    return artifact_id, canonical_json_bytes(
        {**payload, _COMPONENT_ID_FIELD[schema_id]: artifact_id}
    )


def _replay_component(raw: bytes, schema_id: str) -> dict[str, Any]:
    document = _canonical_object(raw, schema_id)
    if document.get("schema") != schema_id:
        _fail("output component crossed its catalogue schema")
    id_field = _COMPONENT_ID_FIELD[schema_id]
    artifact_id = _cid(document.get(id_field), id_field)
    payload = {key: value for key, value in document.items() if key != id_field}
    if _hash(_COMPONENT_DOMAIN[schema_id], payload) != artifact_id:
        _fail("output component content ID does not replay")
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("proposed_contract_version")
        != PROPOSED_CONTRACT_VERSION
        or payload.get("profile_key") != PROFILE_KEY
        or payload.get("raw_evidence_only") is not True
        or payload.get("semantic_source_verified") is not False
        or payload.get("counter_record_issued") is not False
        or payload.get("formal_value_authorized") is not False
    ):
        _fail("output raw component attempted to claim formal authority")
    return document


@dataclass(frozen=True, slots=True)
class WorkerBusinessResultCommitV2:
    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    measurement_start_sequence: int
    worker_commit_observation_id: str
    output_directory_identity: Mapping[str, int]
    artifact_identity: Mapping[str, int]
    artifact_sha256: str
    artifact_byte_extent: int
    commit_event_id: str
    first_role_authority: OutputFirstRoleAuthorityV2
    authenticated_parent_output_observation_id: str | None
    parent_output_frame_id: str | None
    broker_operational_output_id: str | None
    _payload_bytes: bytes = field(repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUSINESS_ISSUER:
            _fail("worker BUSINESS_RESULT commit is caller-minted")
        for value, label in (
            (self.live_envelope_id, "business envelope"),
            (self.occurrence_id, "business occurrence"),
            (self.route_attempt_id, "business attempt"),
            (self.decision_point_id, "business decision"),
            (self.measurement_window_id, "business window"),
            (self.operational_cutoff_id, "business cutoff"),
            (self.worker_commit_observation_id, "worker commit observation"),
            (self.commit_event_id, "worker commit event"),
        ):
            _cid(value, label)
        _nonnegative(self.measurement_start_sequence, "measurement start")
        _sha256(self.artifact_sha256, "BUSINESS_RESULT digest")
        _positive(self.artifact_byte_extent, "BUSINESS_RESULT extent")
        try:
            authority = OutputFirstRoleAuthorityV2(self.first_role_authority)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceOutputJournalV2Error(
                "first-role authority is invalid"
            ) from error
        object.__setattr__(self, "first_role_authority", authority)
        production = (
            authority
            is OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
        )
        authority_ids = (
            self.authenticated_parent_output_observation_id,
            self.parent_output_frame_id,
            self.broker_operational_output_id,
        )
        if production:
            for value, label in zip(
                authority_ids,
                (
                    "authenticated PARENT_OUTPUT observation",
                    "PARENT_OUTPUT frame",
                    "broker operational output",
                ),
            ):
                _cid(value, label)
        elif any(value is not None for value in authority_ids):
            _fail("synthetic first-role commit retained production authority")
        if (
            type(self._payload_bytes) is not bytes
            or len(self._payload_bytes) != self.artifact_byte_extent
            or hashlib.sha256(self._payload_bytes).hexdigest()
            != self.artifact_sha256
        ):
            _fail("BUSINESS_RESULT receipt differs from retained P")
        object.__setattr__(
            self,
            "output_directory_identity",
            MappingProxyType(dict(self.output_directory_identity)),
        )
        object.__setattr__(
            self,
            "artifact_identity",
            MappingProxyType(dict(self.artifact_identity)),
        )

    @property
    def commit_sequence(self) -> int:
        return self.measurement_start_sequence + 1

    @property
    def production_semantic_eligible(self) -> bool:
        return (
            self.first_role_authority
            is OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
        )

    def _event_document_after_reap_v2(
        self,
        issuer: object,
        *,
        session_id: str,
        pre_seal_identity: Mapping[str, int],
        sealed_identity: Mapping[str, int],
        broker_removed_write_bits: bool,
    ) -> dict[str, Any]:
        if issuer is not _FINALIZATION_ISSUER:
            _fail("first-role post-reap event is finalizer-owned")
        production = self.production_semantic_eligible
        if (
            not _same_inode(pre_seal_identity, self.artifact_identity)
            or not _same_inode(sealed_identity, self.artifact_identity)
            or sealed_identity["byte_extent"] != self.artifact_byte_extent
            or stat.S_IMODE(sealed_identity["mode"]) & 0o222
            or broker_removed_write_bits is not production
        ):
            _fail("first-role post-reap sealing facts are inconsistent")
        row = {
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "global_sequence": self.commit_sequence,
            "artifact_role": BUSINESS_ROLE,
            "filename": ROLE_FILENAMES[BUSINESS_ROLE],
            "artifact_sha256": self.artifact_sha256,
            "artifact_byte_extent": self.artifact_byte_extent,
            "artifact_identity": dict(sealed_identity),
            "writer_role": "WORKER" if production else "CONSTRUCTION_SYNTHETIC",
            "first_role_authority": self.first_role_authority.value,
            "authenticated_parent_output_observation_id": (
                self.authenticated_parent_output_observation_id
            ),
            "parent_output_frame_id": self.parent_output_frame_id,
            "broker_operational_output_id": self.broker_operational_output_id,
            "worker_created_and_durably_committed": production,
            "broker_post_reap_write_bits_removed": broker_removed_write_bits,
            "broker_post_reap_file_fsync_completed": production,
            "broker_post_reap_directory_fsync_completed": production,
            "pre_seal_artifact_identity": dict(pre_seal_identity),
            "sealed_artifact_identity": dict(sealed_identity),
            "production_semantic_eligible": production,
            "synthetic_construction_only": not production,
            "o_excl_no_replace": True,
            "file_fsync_completed": True,
            "directory_fsync_completed": True,
            "inode_pinned_readback_equal": True,
        }
        core = {
            "schema": "acfqp.construction_shared_resource_durable_write_event.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "session_id": session_id,
            **row,
        }
        return {
            **row,
            "durable_write_event_id": _hash(DURABLE_WRITE_EVENT_V2_DOMAIN, core),
        }


def commit_synthetic_construction_first_role_v2(
    *,
    output_directory_fd: int,
    payload_bytes: bytes,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
    operational_cutoff_id: str,
    measurement_start_sequence: int,
    worker_commit_observation_id: str,
) -> WorkerBusinessResultCommitV2:
    """Create a synthetic construction P; never production-eligible."""

    for value, label in (
        (live_envelope_id, "business envelope"),
        (occurrence_id, "business occurrence"),
        (route_attempt_id, "business attempt"),
        (decision_point_id, "business decision"),
        (measurement_window_id, "business window"),
        (operational_cutoff_id, "business cutoff"),
        (worker_commit_observation_id, "worker commit observation"),
    ):
        _cid(value, label)
    _nonnegative(measurement_start_sequence, "measurement start")
    directory_identity = _fd_identity(output_directory_fd, directory=True)
    if os.get_inheritable(output_directory_fd):
        _fail("worker output-directory descriptor must be CLOEXEC")
    if os.listdir(output_directory_fd):
        _fail("worker BUSINESS_RESULT requires one fresh empty output directory")
    _validate_synthetic_first_role_bytes(payload_bytes)
    artifact_identity, readback = _durable_create(
        directory_fd=output_directory_fd,
        filename=ROLE_FILENAMES[BUSINESS_ROLE],
        raw=payload_bytes,
    )
    try:
        os.fsync(output_directory_fd)
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "worker output-directory fsync failed"
        ) from error
    digest, extent = _hash_payload(readback)
    core = {
        "schema": "acfqp.construction_shared_resource_business_result_commit.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        **_identity_document(
            live_envelope_id=live_envelope_id,
            occurrence_id=occurrence_id,
            route_attempt_id=route_attempt_id,
            decision_point_id=decision_point_id,
            measurement_window_id=measurement_window_id,
        ),
        "operational_cutoff_id": operational_cutoff_id,
        "measurement_start_sequence": measurement_start_sequence,
        "global_sequence": measurement_start_sequence + 1,
        "worker_commit_observation_id": worker_commit_observation_id,
        "output_directory_identity": directory_identity,
        "artifact_role": BUSINESS_ROLE,
        "filename": ROLE_FILENAMES[BUSINESS_ROLE],
        "first_role_authority": (
            OutputFirstRoleAuthorityV2.SYNTHETIC_CONSTRUCTION_ONLY.value
        ),
        "production_semantic_eligible": False,
        "synthetic_construction_only": True,
        "artifact_identity": artifact_identity,
        "artifact_sha256": digest,
        "artifact_byte_extent": extent,
        "o_excl_no_replace": True,
        "file_fsync_completed": True,
        "directory_fsync_completed": True,
        "inode_pinned_readback_equal": True,
    }
    event_id = _hash(DURABLE_WRITE_EVENT_V2_DOMAIN, core)
    return WorkerBusinessResultCommitV2(
        _BUSINESS_ISSUER,
        live_envelope_id=live_envelope_id,
        occurrence_id=occurrence_id,
        route_attempt_id=route_attempt_id,
        decision_point_id=decision_point_id,
        measurement_window_id=measurement_window_id,
        operational_cutoff_id=operational_cutoff_id,
        measurement_start_sequence=measurement_start_sequence,
        worker_commit_observation_id=worker_commit_observation_id,
        output_directory_identity=directory_identity,
        artifact_identity=artifact_identity,
        artifact_sha256=digest,
        artifact_byte_extent=extent,
        commit_event_id=event_id,
        first_role_authority=(
            OutputFirstRoleAuthorityV2.SYNTHETIC_CONSTRUCTION_ONLY
        ),
        authenticated_parent_output_observation_id=None,
        parent_output_frame_id=None,
        broker_operational_output_id=None,
        _payload_bytes=readback,
    )


# Historical construction-only spelling.  It is an alias to the explicitly
# synthetic API and cannot issue production semantic eligibility.
commit_worker_business_result_v2 = commit_synthetic_construction_first_role_v2


def adopt_production_worker_operational_output_v2(
    *,
    output_directory_fd: int,
    authenticated_parent_output: channel_v2.K7AuthenticatedBrokerFrameV2,
    expected_request_replay: Any,
    expected_binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
    operational_cutoff_id: str,
    measurement_start_sequence: int,
) -> WorkerBusinessResultCommitV2:
    """Adopt the existing worker V1 output inode without copying or renaming."""

    for value, label in (
        (live_envelope_id, "adopted envelope"),
        (occurrence_id, "adopted occurrence"),
        (route_attempt_id, "adopted attempt"),
        (decision_point_id, "adopted decision"),
        (measurement_window_id, "adopted window"),
        (operational_cutoff_id, "adopted cutoff"),
    ):
        _cid(value, label)
    _nonnegative(measurement_start_sequence, "measurement start")
    if (
        type(authenticated_parent_output)
        is not channel_v2.K7AuthenticatedBrokerFrameV2
        or type(expected_binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
    ):
        _fail("production adoption requires exact authenticated frame authority")
    frame = authenticated_parent_output.frame
    if (
        frame.role is not ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT
        or frame.binding != expected_binding
    ):
        _fail("authenticated PARENT_OUTPUT crossed its role or binding")
    observation_id = authenticated_parent_output.observation_id
    frame_id = frame.frame_id
    directory_identity = _fd_identity(output_directory_fd, directory=True)
    if os.get_inheritable(output_directory_fd):
        _fail("production adoption output-directory descriptor must be CLOEXEC")
    try:
        names = tuple(sorted(os.listdir(output_directory_fd)))
    except OSError as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "production output directory cannot be enumerated"
        ) from error
    if names != (worker_v1.OUTPUT_NAME,):
        _fail("production adoption requires one exact worker operational output")
    reader = _open_readonly_at(output_directory_fd, worker_v1.OUTPUT_NAME)
    try:
        before = _fd_identity(reader, directory=False)
        if (
            before["link_count"] != 1
            or not 0 < before["byte_extent"] <= worker_v1.MAX_OUTPUT_BYTES
        ):
            _fail("production operational output inode is invalid")
        raw = _read_exact(reader, before["byte_extent"])
        after = _fd_identity(reader, directory=False)
        named = os.stat(
            worker_v1.OUTPUT_NAME,
            dir_fd=output_directory_fd,
            follow_symlinks=False,
        )
        if (
            before != after
            or (named.st_dev, named.st_ino)
            != (before["device"], before["inode"])
        ):
            _fail("production operational output mutated or was replaced")
        try:
            verified = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=raw,
                expected_request_replay=expected_request_replay,
                expected_binding=expected_binding,
            )
        except Exception as error:
            raise ConstructionSharedResourceOutputJournalV2Error(
                "worker V1 operational-output semantic replay failed"
            ) from error
        digest, extent = _hash_payload(raw)
        if (
            frame.payload["output_byte_count"] != extent
            or frame.payload["output_sha256"] != digest
        ):
            _fail("authenticated PARENT_OUTPUT crossed its output count or SHA")
        core = {
            "schema": "acfqp.construction_shared_resource_business_result_commit.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            **_identity_document(
                live_envelope_id=live_envelope_id,
                occurrence_id=occurrence_id,
                route_attempt_id=route_attempt_id,
                decision_point_id=decision_point_id,
                measurement_window_id=measurement_window_id,
            ),
            "operational_cutoff_id": operational_cutoff_id,
            "measurement_start_sequence": measurement_start_sequence,
            "global_sequence": measurement_start_sequence + 1,
            "worker_commit_observation_id": observation_id,
            "authenticated_parent_output_observation_id": observation_id,
            "parent_output_frame_id": frame_id,
            "broker_operational_output_id": verified.output_id,
            "output_directory_identity": directory_identity,
            "artifact_role": BUSINESS_ROLE,
            "filename": worker_v1.OUTPUT_NAME,
            "first_role_authority": (
                OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED.value
            ),
            "production_semantic_eligible": True,
            "synthetic_construction_only": False,
            "artifact_identity": before,
            "artifact_sha256": digest,
            "artifact_byte_extent": extent,
            "worker_created_and_durably_committed": True,
            "broker_post_reap_write_bits_removed": False,
        }
        event_id = _hash(DURABLE_WRITE_EVENT_V2_DOMAIN, core)
        adopted = WorkerBusinessResultCommitV2(
            _BUSINESS_ISSUER,
            live_envelope_id=live_envelope_id,
            occurrence_id=occurrence_id,
            route_attempt_id=route_attempt_id,
            decision_point_id=decision_point_id,
            measurement_window_id=measurement_window_id,
            operational_cutoff_id=operational_cutoff_id,
            measurement_start_sequence=measurement_start_sequence,
            worker_commit_observation_id=observation_id,
            output_directory_identity=directory_identity,
            artifact_identity=before,
            artifact_sha256=digest,
            artifact_byte_extent=extent,
            commit_event_id=event_id,
            first_role_authority=(
                OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
            ),
            authenticated_parent_output_observation_id=observation_id,
            parent_output_frame_id=frame_id,
            broker_operational_output_id=verified.output_id,
            _payload_bytes=raw,
        )
    finally:
        os.close(reader)
    with _PARENT_OUTPUT_CONSUMPTION_LOCK:
        if observation_id in _CONSUMED_PARENT_OUTPUT_OBSERVATION_IDS:
            _fail("authenticated PARENT_OUTPUT observation was already consumed")
        _CONSUMED_PARENT_OUTPUT_OBSERVATION_IDS.add(observation_id)
    return adopted


@dataclass(frozen=True, slots=True)
class OutputRawReplayV2:
    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    raw_output_bytes: int
    first_role_authority: OutputFirstRoleAuthorityV2
    production_semantic_eligible: bool
    synthetic_construction_only: bool
    semantic_source_verified: bool = False
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("output raw replay is caller-minted")
        for value in (
            self.live_envelope_id,
            self.occurrence_id,
            self.route_attempt_id,
            self.decision_point_id,
            self.measurement_window_id,
            self.operational_cutoff_id,
        ):
            _cid(value, "output replay identity")
        _positive(self.raw_output_bytes, "raw output bytes")
        try:
            authority = OutputFirstRoleAuthorityV2(self.first_role_authority)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceOutputJournalV2Error(
                "raw output first-role authority is invalid"
            ) from error
        object.__setattr__(self, "first_role_authority", authority)
        production = (
            authority
            is OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
        )
        if (
            self.production_semantic_eligible is not production
            or self.synthetic_construction_only is production
            or self.semantic_source_verified is not False
            or self.counter_record_issuance_authorized is not False
        ):
            _fail("output raw replay cannot claim formal authority")


@dataclass(frozen=True, slots=True)
class OutputRawEvidenceBundleV2:
    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    measurement_start_sequence: int
    operational_cutoff_sequence: int
    fixed_point_component: resolution_v2.SharedResourceEvidenceComponentV2
    exclusive_writer_component: resolution_v2.SharedResourceEvidenceComponentV2
    cutoff_component: resolution_v2.SharedResourceEvidenceComponentV2
    output_manifest_component: resolution_v2.SharedResourceEvidenceComponentV2
    raw_replay: OutputRawReplayV2

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("output raw evidence bundle is caller-minted")
        components = (
            self.fixed_point_component,
            self.exclusive_writer_component,
            self.cutoff_component,
            self.output_manifest_component,
        )
        if any(
            type(item) is not resolution_v2.SharedResourceEvidenceComponentV2
            for item in components
        ) or type(self.raw_replay) is not OutputRawReplayV2:
            _fail("output bundle contains a mistyped component")

    def live_source_v2(self) -> resolution_v2.SharedResourceLiveSourceV2:
        if not self.raw_replay.production_semantic_eligible:
            _fail("synthetic construction output cannot become an exact live source")
        contract = next(
            row
            for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
            if row.path == OUTPUT_PATH
        )
        components = tuple(
            sorted(
                (
                    self.fixed_point_component,
                    self.exclusive_writer_component,
                    self.cutoff_component,
                    self.output_manifest_component,
                ),
                key=lambda item: item.component_key,
            )
        )
        return resolution_v2.SharedResourceLiveSourceV2(
            self.live_envelope_id,
            self.occurrence_id,
            self.route_attempt_id,
            self.decision_point_id,
            self.measurement_window_id,
            self.operational_cutoff_id,
            OUTPUT_PATH,
            contract.exact_source_kind,
            contract.required_provenance,
            self.measurement_start_sequence,
            self.operational_cutoff_sequence,
            components,
        )


class BrokerDurableOutputSessionV2:
    """Exclusive process-local broker writer and finalization authority."""

    def __init__(
        self,
        *,
        output_directory_fd: int,
        business_commit: WorkerBusinessResultCommitV2,
        worker_reap_observation_id: str,
        business_reap_observation_id: str,
        child_cgroup_empty_observation_id: str,
        broker_outside_child_cgroup_observation_id: str,
        exclusive_writer_observation_id: str,
    ) -> None:
        if type(business_commit) is not WorkerBusinessResultCommitV2:
            _fail("broker finalization lacks an issued BUSINESS_RESULT commit")
        observations = (
            worker_reap_observation_id,
            business_reap_observation_id,
            child_cgroup_empty_observation_id,
            broker_outside_child_cgroup_observation_id,
            exclusive_writer_observation_id,
        )
        for value in observations:
            _cid(value, "broker finalization observation")
        if len(set(observations)) != len(observations):
            _fail("broker finalization observations are duplicated")
        directory_identity = _fd_identity(output_directory_fd, directory=True)
        if os.get_inheritable(output_directory_fd):
            _fail("broker output-directory descriptor must be CLOEXEC")
        if not _same_inode(directory_identity, business_commit.output_directory_identity):
            _fail("broker output directory crossed the worker commit")
        if set(os.listdir(output_directory_fd)) != {ROLE_FILENAMES[BUSINESS_ROLE]}:
            _fail("broker finalization requires exactly the worker BUSINESS_RESULT")
        lease = (
            directory_identity["device"],
            directory_identity["inode"],
            directory_identity["ctime_ns"],
        )
        with _DIRECTORY_LEASE_LOCK:
            if lease in _CONSUMED_DIRECTORY_IDENTITIES:
                _fail("output directory has an overlapping or prior broker writer")
            _CONSUMED_DIRECTORY_IDENTITIES.add(lease)
        result_fd = -1
        try:
            result_fd = _open_readonly_at(
                output_directory_fd, ROLE_FILENAMES[BUSINESS_ROLE]
            )
            result_identity = _fd_identity(result_fd, directory=False)
            if (
                result_identity != business_commit.artifact_identity
                or result_identity["link_count"] != 1
            ):
                _fail("broker-pinned P differs from the adopted first-role inode")
            pre_read = _read_exact(result_fd, result_identity["byte_extent"])
            if (
                pre_read != business_commit._payload_bytes
                or hashlib.sha256(pre_read).hexdigest()
                != business_commit.artifact_sha256
            ):
                _fail("broker pre-read P differs from the worker commit")
            pre_seal_identity = result_identity
            production = business_commit.production_semantic_eligible
            pre_mode = stat.S_IMODE(pre_seal_identity["mode"])
            if production:
                if pre_mode != 0o600:
                    _fail(
                        "production P must retain exact worker write bits until reaps"
                    )
                os.fchmod(result_fd, pre_mode & ~0o222)
                os.fsync(result_fd)
                os.fsync(output_directory_fd)
                result_identity = _fd_identity(result_fd, directory=False)
                named = os.stat(
                    ROLE_FILENAMES[BUSINESS_ROLE],
                    dir_fd=output_directory_fd,
                    follow_symlinks=False,
                )
                sealed_read = _read_exact(
                    result_fd, result_identity["byte_extent"]
                )
                if (
                    not _same_inode(pre_seal_identity, result_identity)
                    or (named.st_dev, named.st_ino)
                    != (result_identity["device"], result_identity["inode"])
                    or stat.S_IMODE(result_identity["mode"]) != 0o400
                    or sealed_read != pre_read
                ):
                    _fail("broker post-reap P sealing or pinned reread failed")
                broker_removed_write_bits = True
            else:
                if pre_mode & 0o222:
                    _fail("synthetic construction P unexpectedly remains writable")
                broker_removed_write_bits = False
        except BaseException:
            if result_fd >= 0:
                os.close(result_fd)
            raise
        self._directory_fd = output_directory_fd
        self._directory_identity = directory_identity
        self._result_fd = result_fd
        self._result_identity = result_identity
        self._result_identity_pre_seal = pre_seal_identity
        self._broker_removed_write_bits = broker_removed_write_bits
        self._business_commit = business_commit
        self._pre_read_p = pre_read
        self._worker_reap_observation_id = worker_reap_observation_id
        self._business_reap_observation_id = business_reap_observation_id
        self._child_cgroup_empty_observation_id = child_cgroup_empty_observation_id
        self._broker_outside_observation_id = (
            broker_outside_child_cgroup_observation_id
        )
        self._exclusive_writer_observation_id = exclusive_writer_observation_id
        session_payload = {
            "schema": "acfqp.construction_shared_resource_output_finalization_session.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            **_identity_document(
                live_envelope_id=business_commit.live_envelope_id,
                occurrence_id=business_commit.occurrence_id,
                route_attempt_id=business_commit.route_attempt_id,
                decision_point_id=business_commit.decision_point_id,
                measurement_window_id=business_commit.measurement_window_id,
            ),
            "operational_cutoff_id": business_commit.operational_cutoff_id,
            "worker_commit_event_id": business_commit.commit_event_id,
            "worker_reap_observation_id": worker_reap_observation_id,
            "business_reap_observation_id": business_reap_observation_id,
            "child_cgroup_empty_observation_id": child_cgroup_empty_observation_id,
            "broker_outside_child_cgroup_observation_id": (
                broker_outside_child_cgroup_observation_id
            ),
            "exclusive_writer_observation_id": exclusive_writer_observation_id,
            "output_directory_identity": directory_identity,
            "business_result_pre_seal_identity": pre_seal_identity,
            "business_result_sealed_identity": result_identity,
            "first_role_authority": business_commit.first_role_authority.value,
            "production_semantic_eligible": (
                business_commit.production_semantic_eligible
            ),
            "broker_post_reap_write_bits_removed": broker_removed_write_bits,
        }
        self._session_id = _hash(
            OUTPUT_FINALIZATION_SESSION_V2_DOMAIN, session_payload
        )
        self._state = OutputFinalizationStateV2.OPEN
        self._bundle: OutputRawEvidenceBundleV2 | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> OutputFinalizationStateV2:
        return self._state

    def _render_once(
        self, renderer: RendererV2, candidate: int
    ) -> dict[str, bytes]:
        try:
            rendered = renderer(candidate)
        except Exception as error:
            raise ConstructionSharedResourceOutputJournalV2Error(
                "seven-role renderer raised"
            ) from error
        if type(rendered) is not dict or tuple(rendered) != BROKER_ROLE_ORDER:
            _fail("renderer has a duplicate, missing, extra, or reordered role")
        result: dict[str, bytes] = {}
        total = self._business_commit.artifact_byte_extent
        for role in BROKER_ROLE_ORDER:
            raw = rendered[role]
            _validate_role_bytes(role, raw, candidate)
            total += len(raw)
            if total > MAX_TOTAL_BYTES:
                _fail("eight-role rendered output exceeds its total cap")
            result[role] = raw
        return result

    def _solve_fixed_point(
        self, renderer: RendererV2
    ) -> tuple[int, dict[str, bytes], list[dict[str, Any]]]:
        if not callable(renderer):
            _fail("seven-role renderer is not callable")
        candidate = 0
        iterations: list[dict[str, Any]] = []
        for index in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
            first = self._render_once(renderer, candidate)
            second = self._render_once(renderer, candidate)
            if first != second:
                _fail("self-reference renderer is unstable for one candidate")
            total = self._business_commit.artifact_byte_extent + sum(
                len(first[role]) for role in BROKER_ROLE_ORDER
            )
            if total < candidate:
                _fail("output fixed-point recurrence decreased")
            role_counts = {
                BUSINESS_ROLE: self._business_commit.artifact_byte_extent,
                **{role: len(first[role]) for role in BROKER_ROLE_ORDER},
            }
            iteration_payload = {
                "schema": "acfqp.construction_shared_resource_output_fixed_point_iteration.v2",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "session_id": self._session_id,
                "iteration_index": index,
                "candidate_output_bytes": candidate,
                "rendered_total_bytes": total,
                "role_byte_extents": [
                    {"artifact_role": role, "byte_extent": role_counts[role]}
                    for role in ROLE_ORDER
                ],
            }
            iterations.append(
                {
                    **iteration_payload,
                    "iteration_id": _hash(
                        FIXED_POINT_ITERATION_V2_DOMAIN, iteration_payload
                    ),
                    "converged": total == candidate,
                }
            )
            if total == candidate:
                replay_one = self._render_once(renderer, candidate)
                replay_two = self._render_once(renderer, candidate)
                if replay_one != first or replay_two != first:
                    _fail("converged self-reference replay is unstable")
                return candidate, first, iterations
            candidate = total
        _fail("output fixed point did not converge within its finite cap")

    def _entry_identity(self, filename: str) -> dict[str, int]:
        reader = _open_readonly_at(self._directory_fd, filename)
        try:
            return _fd_identity(reader, directory=False)
        finally:
            os.close(reader)

    @staticmethod
    def _component(
        schema_id: str, component_key: str, body: Mapping[str, Any]
    ) -> resolution_v2.SharedResourceEvidenceComponentV2:
        artifact_id, raw = _freeze_component_bytes(schema_id, body)
        return resolution_v2.SharedResourceEvidenceComponentV2(
            component_key,
            schema_id,
            artifact_id,
            hashlib.sha256(raw).hexdigest(),
            raw,
        )

    def finalize_v2(self, *, renderer: RendererV2) -> OutputRawEvidenceBundleV2:
        with self._lock:
            if self._state is OutputFinalizationStateV2.FINALIZED:
                assert self._bundle is not None
                return self._bundle
            if self._state is not OutputFinalizationStateV2.OPEN:
                _fail("failed output finalization cannot be reused")
            try:
                fixed_total, suffix, iterations = self._solve_fixed_point(renderer)
                role_rows = [
                    self._business_commit._event_document_after_reap_v2(  # noqa: SLF001
                        _FINALIZATION_ISSUER,
                        session_id=self._session_id,
                        pre_seal_identity=self._result_identity_pre_seal,
                        sealed_identity=self._result_identity,
                        broker_removed_write_bits=self._broker_removed_write_bits,
                    )
                ]
                for ordinal, role in enumerate(BROKER_ROLE_ORDER, start=2):
                    raw = suffix[role]
                    identity, readback = _durable_create(
                        directory_fd=self._directory_fd,
                        filename=ROLE_FILENAMES[role],
                        raw=raw,
                    )
                    digest, extent = _hash_payload(readback)
                    core = {
                        "schema": "acfqp.construction_shared_resource_durable_write_event.v2",
                        "schema_version": SCHEMA_VERSION,
                        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                        "session_id": self._session_id,
                        "global_sequence": (
                            self._business_commit.measurement_start_sequence
                            + ordinal
                        ),
                        "artifact_role": role,
                        "filename": ROLE_FILENAMES[role],
                        "artifact_sha256": digest,
                        "artifact_byte_extent": extent,
                        "artifact_identity": identity,
                        "writer_role": "BROKER",
                        "o_excl_no_replace": True,
                        "file_fsync_completed": True,
                        "directory_fsync_completed": False,
                        "inode_pinned_readback_equal": True,
                    }
                    event_id = _hash(DURABLE_WRITE_EVENT_V2_DOMAIN, core)
                    role_rows.append(
                        {
                            key: value
                            for key, value in core.items()
                            if key not in {"schema", "schema_version", "session_id"}
                        }
                        | {"durable_write_event_id": event_id}
                    )
                os.fsync(self._directory_fd)
                for row in role_rows[1:]:
                    row["directory_fsync_completed"] = True
                    core = {
                        "schema": "acfqp.construction_shared_resource_durable_write_event.v2",
                        "schema_version": SCHEMA_VERSION,
                        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                        "session_id": self._session_id,
                        **{
                            key: value
                            for key, value in row.items()
                            if key != "durable_write_event_id"
                        },
                    }
                    row["durable_write_event_id"] = _hash(
                        DURABLE_WRITE_EVENT_V2_DOMAIN, core
                    )
                expected_names = {ROLE_FILENAMES[role] for role in ROLE_ORDER}
                if set(os.listdir(self._directory_fd)) != expected_names:
                    _fail("durable output directory has a missing or extra role")
                inode_keys = {
                    (
                        row["artifact_identity"]["device"],
                        row["artifact_identity"]["inode"],
                    )
                    for row in role_rows
                }
                if len(inode_keys) != len(ROLE_ORDER):
                    _fail("durable output roles alias or double-charge one inode")
                current_p_identity = self._entry_identity(
                    ROLE_FILENAMES[BUSINESS_ROLE]
                )
                post_read_p = _read_exact(
                    self._result_fd,
                    self._business_commit.artifact_byte_extent,
                )
                if (
                    post_read_p != self._pre_read_p
                    or not _same_inode(current_p_identity, self._result_identity)
                    or current_p_identity["byte_extent"]
                    != self._result_identity["byte_extent"]
                    or current_p_identity != self._result_identity
                    or stat.S_IMODE(current_p_identity["mode"]) & 0o222
                ):
                    _fail("P mutation or replacement detected between P and P'")
                raw_total = sum(row["artifact_byte_extent"] for row in role_rows)
                if raw_total != fixed_total:
                    _fail("durable extents under-count or double-count fixed output")
                identity = _identity_document(
                    live_envelope_id=self._business_commit.live_envelope_id,
                    occurrence_id=self._business_commit.occurrence_id,
                    route_attempt_id=self._business_commit.route_attempt_id,
                    decision_point_id=self._business_commit.decision_point_id,
                    measurement_window_id=self._business_commit.measurement_window_id,
                )
                cutoff_sequence = (
                    self._business_commit.measurement_start_sequence
                    + len(ROLE_ORDER)
                )
                authority = self._business_commit.first_role_authority.value
                production_eligible = (
                    self._business_commit.production_semantic_eligible
                )
                eligibility = {
                    "first_role_authority": authority,
                    "production_semantic_eligible": production_eligible,
                    "synthetic_construction_only": not production_eligible,
                }
                manifest_body = {
                    **identity,
                    **eligibility,
                    "operational_cutoff_id": self._business_commit.operational_cutoff_id,
                    "session_id": self._session_id,
                    "path": OUTPUT_PATH,
                    "required_role_order": list(ROLE_ORDER),
                    "role_artifacts": role_rows,
                    "raw_derived_output_bytes": raw_total,
                    "nested_serialized_aliases_charged_separately": False,
                    "exact_new_inode_extents_only": True,
                }
                fixed_body = {
                    **identity,
                    **eligibility,
                    "operational_cutoff_id": self._business_commit.operational_cutoff_id,
                    "session_id": self._session_id,
                    "path": OUTPUT_PATH,
                    "business_result_sha256": self._business_commit.artifact_sha256,
                    "business_result_byte_extent": (
                        self._business_commit.artifact_byte_extent
                    ),
                    "iterations": iterations,
                    "terminal_candidate_output_bytes": fixed_total,
                    "terminal_role_byte_extents": [
                        {
                            "artifact_role": row["artifact_role"],
                            "byte_extent": row["artifact_byte_extent"],
                            "sha256": row["artifact_sha256"],
                        }
                        for row in role_rows
                    ],
                    "same_candidate_double_rendered": True,
                    "terminal_candidate_double_replayed": True,
                    "business_result_pre_post_equal": True,
                }
                writer_body = {
                    **identity,
                    **eligibility,
                    "operational_cutoff_id": self._business_commit.operational_cutoff_id,
                    "session_id": self._session_id,
                    "path": OUTPUT_PATH,
                    "worker_reap_observation_id": self._worker_reap_observation_id,
                    "business_reap_observation_id": self._business_reap_observation_id,
                    "child_cgroup_empty_observation_id": (
                        self._child_cgroup_empty_observation_id
                    ),
                    "broker_outside_child_cgroup_observation_id": (
                        self._broker_outside_observation_id
                    ),
                    "exclusive_writer_observation_id": (
                        self._exclusive_writer_observation_id
                    ),
                    "output_directory_identity": self._directory_identity,
                    "business_result_pre_identity": (
                        self._result_identity_pre_seal
                    ),
                    "business_result_post_identity": current_p_identity,
                    "durable_write_events": role_rows,
                    "direct_children_reaped_before_broker_suffix": True,
                    "exclusive_broker_writer_before_suffix": True,
                    "broker_suffix_outside_measured_child_cgroup": True,
                    "o_excl_no_replace_all_roles": True,
                    "file_fsync_all_roles": True,
                    "directory_fsync_after_complete_set": True,
                    "inode_pinned_readback_all_roles": True,
                    "business_result_pre_post_equal": True,
                    "worker_created_and_durably_committed_first_role": (
                        production_eligible
                    ),
                    "broker_post_reap_sealed_first_role": production_eligible,
                    "first_role_filename_is_worker_operational_output": True,
                }
                cutoff_body = {
                    **identity,
                    **eligibility,
                    "operational_cutoff_id": self._business_commit.operational_cutoff_id,
                    "session_id": self._session_id,
                    "measurement_start_sequence": (
                        self._business_commit.measurement_start_sequence
                    ),
                    "operational_cutoff_sequence": cutoff_sequence,
                    "global_event_count": len(ROLE_ORDER),
                    "global_event_index": [
                        {
                            "global_sequence": row["global_sequence"],
                            "artifact_role": row["artifact_role"],
                            "durable_write_event_id": row[
                                "durable_write_event_id"
                            ],
                        }
                        for row in role_rows
                    ],
                    "window_closed": True,
                    "cutoff_is_inclusive": True,
                }
                fixed_component = self._component(
                    FIXED_POINT_SCHEMA_ID,
                    "durable_output_fixed_point",
                    fixed_body,
                )
                writer_component = self._component(
                    EXCLUSIVE_WRITER_SCHEMA_ID,
                    "exclusive_writer_attestation",
                    writer_body,
                )
                cutoff_component = self._component(
                    CUTOFF_SCHEMA_ID,
                    "operational_cutoff_attestation",
                    cutoff_body,
                )
                manifest_component = self._component(
                    OUTPUT_MANIFEST_SCHEMA_ID,
                    "output_manifest",
                    manifest_body,
                )
                replay = replay_output_raw_evidence_v2(
                    fixed_point_bytes=fixed_component.raw_bytes,
                    exclusive_writer_bytes=writer_component.raw_bytes,
                    cutoff_bytes=cutoff_component.raw_bytes,
                    output_manifest_bytes=manifest_component.raw_bytes,
                )
                bundle = OutputRawEvidenceBundleV2(
                    _BUNDLE_ISSUER,
                    self._business_commit.live_envelope_id,
                    self._business_commit.occurrence_id,
                    self._business_commit.route_attempt_id,
                    self._business_commit.decision_point_id,
                    self._business_commit.measurement_window_id,
                    self._business_commit.operational_cutoff_id,
                    self._business_commit.measurement_start_sequence,
                    cutoff_sequence,
                    fixed_component,
                    writer_component,
                    cutoff_component,
                    manifest_component,
                    replay,
                )
                self._bundle = bundle
                self._state = OutputFinalizationStateV2.FINALIZED
                return bundle
            except BaseException:
                self._state = OutputFinalizationStateV2.FAILED
                raise

    def close(self) -> None:
        with self._lock:
            if self._result_fd >= 0:
                os.close(self._result_fd)
                self._result_fd = -1

    def __enter__(self) -> "BrokerDurableOutputSessionV2":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


def open_broker_durable_output_session_v2(
    **kwargs: Any,
) -> BrokerDurableOutputSessionV2:
    return BrokerDurableOutputSessionV2(**kwargs)


def _identity_tuple(document: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(_cid(document.get(key), key) for key in sorted(_IDENTITY_FIELDS)) + (
        _cid(document.get("operational_cutoff_id"), "output cutoff"),
        _cid(document.get("session_id"), "output session"),
    )


def _replay_inode(row: Any) -> dict[str, int]:
    fields = {
        "device",
        "inode",
        "mode",
        "owner_uid",
        "owner_gid",
        "link_count",
        "byte_extent",
        "ctime_ns",
    }
    _exact_fields(row, fields, "output inode identity")
    result = dict(row)
    for key, value in result.items():
        _nonnegative(value, f"inode {key}")
    if result["link_count"] != 1 or not stat.S_ISREG(result["mode"]):
        _fail("output inode is aliased or not a regular file")
    return result


def _replay_role_rows(
    rows: Any, *, session_id: str
) -> tuple[list[dict[str, Any]], int]:
    if type(rows) is not list or len(rows) != len(ROLE_ORDER):
        _fail("output manifest has a missing or extra role")
    result: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    inode_keys: set[tuple[int, int]] = set()
    total = 0
    common_fields = {
        "proposed_contract_version",
        "global_sequence",
        "artifact_role",
        "filename",
        "artifact_sha256",
        "artifact_byte_extent",
        "artifact_identity",
        "durable_write_event_id",
        "writer_role",
        "o_excl_no_replace",
        "file_fsync_completed",
        "directory_fsync_completed",
        "inode_pinned_readback_equal",
    }
    first_fields = common_fields | {
        "first_role_authority",
        "authenticated_parent_output_observation_id",
        "parent_output_frame_id",
        "broker_operational_output_id",
        "worker_created_and_durably_committed",
        "broker_post_reap_write_bits_removed",
        "broker_post_reap_file_fsync_completed",
        "broker_post_reap_directory_fsync_completed",
        "pre_seal_artifact_identity",
        "sealed_artifact_identity",
        "production_semantic_eligible",
        "synthetic_construction_only",
    }
    for raw, role in zip(rows, ROLE_ORDER):
        _exact_fields(
            raw,
            first_fields if role == BUSINESS_ROLE else common_fields,
            "durable role row",
        )
        row = dict(raw)
        if (
            row["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
            or row["artifact_role"] != role
            or row["filename"] != ROLE_FILENAMES[role]
            or row["global_sequence"] <= 0
            or row["o_excl_no_replace"] is not True
            or row["file_fsync_completed"] is not True
            or row["directory_fsync_completed"] is not True
            or row["inode_pinned_readback_equal"] is not True
        ):
            _fail("durable role writer, order, or fsync evidence changed")
        _sha256(row["artifact_sha256"], "durable role digest")
        _positive(row["artifact_byte_extent"], "durable role extent")
        identity = _replay_inode(row["artifact_identity"])
        if identity["byte_extent"] != row["artifact_byte_extent"]:
            _fail("durable role inode extent differs from its charge")
        event_id = _cid(row["durable_write_event_id"], "durable write event")
        event_core = {
            "schema": "acfqp.construction_shared_resource_durable_write_event.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "session_id": session_id,
            **{
                key: value
                for key, value in row.items()
                if key != "durable_write_event_id"
            },
        }
        if event_id != _hash(DURABLE_WRITE_EVENT_V2_DOMAIN, event_core):
            _fail("durable role event ID does not replay")
        if role == BUSINESS_ROLE:
            try:
                authority = OutputFirstRoleAuthorityV2(
                    row["first_role_authority"]
                )
            except (TypeError, ValueError) as error:
                raise ConstructionSharedResourceOutputJournalV2Error(
                    "first-role authority is invalid"
                ) from error
            production = (
                authority
                is OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
            )
            pre_seal = _replay_inode(row["pre_seal_artifact_identity"])
            sealed = _replay_inode(row["sealed_artifact_identity"])
            authority_ids = (
                row["authenticated_parent_output_observation_id"],
                row["parent_output_frame_id"],
                row["broker_operational_output_id"],
            )
            if production:
                for value in authority_ids:
                    _cid(value, "production first-role authority")
            elif any(value is not None for value in authority_ids):
                _fail("synthetic first role retained production IDs")
            if (
                row["writer_role"]
                != ("WORKER" if production else "CONSTRUCTION_SYNTHETIC")
                or row["worker_created_and_durably_committed"] is not production
                or row["broker_post_reap_write_bits_removed"] is not production
                or row["broker_post_reap_file_fsync_completed"] is not production
                or row["broker_post_reap_directory_fsync_completed"]
                is not production
                or row["production_semantic_eligible"] is not production
                or row["synthetic_construction_only"] is production
                or not _same_inode(pre_seal, sealed)
                or sealed != identity
                or stat.S_IMODE(sealed["mode"]) & 0o222
                or (
                    production
                    and (
                        stat.S_IMODE(pre_seal["mode"]) != 0o600
                        or stat.S_IMODE(sealed["mode"]) != 0o400
                    )
                )
                or ((not production) and pre_seal != sealed)
            ):
                _fail("first-role adoption or post-reap sealing evidence changed")
        elif row["writer_role"] != "BROKER":
            _fail("durable broker suffix writer role changed")
        inode_key = (identity["device"], identity["inode"])
        if event_id in event_ids or inode_key in inode_keys:
            _fail("durable roles duplicate an event or alias one inode")
        event_ids.add(event_id)
        inode_keys.add(inode_key)
        total += row["artifact_byte_extent"]
        result.append(row)
    return result, total


def replay_output_raw_evidence_v2(
    *,
    fixed_point_bytes: bytes,
    exclusive_writer_bytes: bytes,
    cutoff_bytes: bytes,
    output_manifest_bytes: bytes,
) -> OutputRawReplayV2:
    fixed = _replay_component(fixed_point_bytes, FIXED_POINT_SCHEMA_ID)
    writer = _replay_component(
        exclusive_writer_bytes, EXCLUSIVE_WRITER_SCHEMA_ID
    )
    cutoff = _replay_component(cutoff_bytes, CUTOFF_SCHEMA_ID)
    manifest = _replay_component(
        output_manifest_bytes, OUTPUT_MANIFEST_SCHEMA_ID
    )
    fixed_fields = (
        _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | _ELIGIBILITY_FIELDS | {
        "durable_output_fixed_point_id",
        "operational_cutoff_id",
        "session_id",
        "path",
        "business_result_sha256",
        "business_result_byte_extent",
        "iterations",
        "terminal_candidate_output_bytes",
        "terminal_role_byte_extents",
        "same_candidate_double_rendered",
        "terminal_candidate_double_replayed",
        "business_result_pre_post_equal",
        }
    )
    writer_fields = (
        _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | _ELIGIBILITY_FIELDS | {
        "exclusive_writer_attestation_id",
        "operational_cutoff_id",
        "session_id",
        "path",
        "worker_reap_observation_id",
        "business_reap_observation_id",
        "child_cgroup_empty_observation_id",
        "broker_outside_child_cgroup_observation_id",
        "exclusive_writer_observation_id",
        "output_directory_identity",
        "business_result_pre_identity",
        "business_result_post_identity",
        "durable_write_events",
        "direct_children_reaped_before_broker_suffix",
        "exclusive_broker_writer_before_suffix",
        "broker_suffix_outside_measured_child_cgroup",
        "o_excl_no_replace_all_roles",
        "file_fsync_all_roles",
        "directory_fsync_after_complete_set",
        "inode_pinned_readback_all_roles",
        "business_result_pre_post_equal",
        "worker_created_and_durably_committed_first_role",
        "broker_post_reap_sealed_first_role",
        "first_role_filename_is_worker_operational_output",
        }
    )
    cutoff_fields = (
        _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | _ELIGIBILITY_FIELDS | {
        "operational_cutoff_attestation_id",
        "operational_cutoff_id",
        "session_id",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "global_event_count",
        "global_event_index",
        "window_closed",
        "cutoff_is_inclusive",
        }
    )
    manifest_fields = (
        _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | _ELIGIBILITY_FIELDS | {
        "eight_role_output_manifest_id",
        "operational_cutoff_id",
        "session_id",
        "path",
        "required_role_order",
        "role_artifacts",
        "raw_derived_output_bytes",
        "nested_serialized_aliases_charged_separately",
        "exact_new_inode_extents_only",
        }
    )
    _exact_fields(fixed, fixed_fields, "output fixed point")
    _exact_fields(writer, writer_fields, "exclusive writer")
    _exact_fields(cutoff, cutoff_fields, "output cutoff")
    _exact_fields(manifest, manifest_fields, "output manifest")
    identity = _identity_tuple(fixed)
    if any(_identity_tuple(row) != identity for row in (writer, cutoff, manifest)):
        _fail("output raw components crossed occurrence/window identity")
    try:
        authority = OutputFirstRoleAuthorityV2(fixed["first_role_authority"])
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceOutputJournalV2Error(
            "output components name an invalid first-role authority"
        ) from error
    production = (
        authority is OutputFirstRoleAuthorityV2.PRODUCTION_WORKER_V1_ADOPTED
    )
    if any(
        row["first_role_authority"] != authority.value
        or row["production_semantic_eligible"] is not production
        or row["synthetic_construction_only"] is production
        for row in (fixed, writer, cutoff, manifest)
    ):
        _fail("output components crossed first-role semantic eligibility")
    if any(
        row["path"] != OUTPUT_PATH for row in (fixed, writer, manifest)
    ):
        _fail("output raw component crossed its counter path")
    role_rows, total = _replay_role_rows(
        manifest["role_artifacts"], session_id=manifest["session_id"]
    )
    if (
        manifest["required_role_order"] != list(ROLE_ORDER)
        or manifest["raw_derived_output_bytes"] != total
        or manifest["nested_serialized_aliases_charged_separately"] is not False
        or manifest["exact_new_inode_extents_only"] is not True
    ):
        _fail("output bytes are under-counted, double-counted, or alias-charged")
    writer_rows, writer_total = _replay_role_rows(
        writer["durable_write_events"], session_id=writer["session_id"]
    )
    if writer_rows != role_rows or writer_total != total:
        _fail("exclusive writer rows differ from the output manifest")
    observation_fields = (
        "worker_reap_observation_id",
        "business_reap_observation_id",
        "child_cgroup_empty_observation_id",
        "broker_outside_child_cgroup_observation_id",
        "exclusive_writer_observation_id",
    )
    observations = tuple(_cid(writer[key], key) for key in observation_fields)
    if len(set(observations)) != len(observations):
        _fail("exclusive writer/reap observations are duplicated")
    required_true = (
        "direct_children_reaped_before_broker_suffix",
        "exclusive_broker_writer_before_suffix",
        "broker_suffix_outside_measured_child_cgroup",
        "o_excl_no_replace_all_roles",
        "file_fsync_all_roles",
        "directory_fsync_after_complete_set",
        "inode_pinned_readback_all_roles",
        "business_result_pre_post_equal",
    )
    if any(writer[key] is not True for key in required_true):
        _fail("exclusive writer, reap, fsync, or P equality evidence is absent")
    pre_identity = _replay_inode(writer["business_result_pre_identity"])
    post_identity = _replay_inode(writer["business_result_post_identity"])
    first_row = role_rows[0]
    if (
        not _same_inode(pre_identity, post_identity)
        or post_identity != first_row["artifact_identity"]
        or writer["worker_created_and_durably_committed_first_role"]
        is not production
        or writer["broker_post_reap_sealed_first_role"] is not production
        or writer["first_role_filename_is_worker_operational_output"] is not True
        or first_row["production_semantic_eligible"] is not production
    ):
        _fail("P adoption or post-reap sealing identity changed")
    iterations = fixed["iterations"]
    if type(iterations) is not list or not iterations:
        _fail("output fixed point lacks its iteration trace")
    candidate = 0
    for index, row in enumerate(iterations, start=1):
        fields = {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "session_id",
            "iteration_index",
            "candidate_output_bytes",
            "rendered_total_bytes",
            "role_byte_extents",
            "iteration_id",
            "converged",
        }
        _exact_fields(row, fields, "fixed-point iteration")
        if (
            row["schema_version"] != SCHEMA_VERSION
            or row["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
            or row["iteration_index"] != index
            or row["candidate_output_bytes"] != candidate
        ):
            _fail("output fixed-point recurrence is missing or reordered")
        extents = row["role_byte_extents"]
        if (
            type(extents) is not list
            or [item.get("artifact_role") for item in extents] != list(ROLE_ORDER)
            or any(set(item) != {"artifact_role", "byte_extent"} for item in extents)
        ):
            _fail("fixed-point iteration role set is incomplete")
        rendered = sum(item["byte_extent"] for item in extents)
        if row["rendered_total_bytes"] != rendered or rendered < candidate:
            _fail("fixed-point iteration total is unstable")
        payload = {
            key: value
            for key, value in row.items()
            if key not in {"iteration_id", "converged"}
        }
        if row["iteration_id"] != _hash(FIXED_POINT_ITERATION_V2_DOMAIN, payload):
            _fail("fixed-point iteration ID does not replay")
        converged = rendered == candidate
        if row["converged"] is not converged or (converged and index != len(iterations)):
            _fail("fixed-point convergence position changed")
        candidate = rendered
    terminal_extents = fixed["terminal_role_byte_extents"]
    expected_terminal = [
        {
            "artifact_role": row["artifact_role"],
            "byte_extent": row["artifact_byte_extent"],
            "sha256": row["artifact_sha256"],
        }
        for row in role_rows
    ]
    if (
        candidate != total
        or fixed["terminal_candidate_output_bytes"] != total
        or terminal_extents != expected_terminal
        or fixed["business_result_sha256"] != role_rows[0]["artifact_sha256"]
        or fixed["business_result_byte_extent"]
        != role_rows[0]["artifact_byte_extent"]
        or fixed["same_candidate_double_rendered"] is not True
        or fixed["terminal_candidate_double_replayed"] is not True
        or fixed["business_result_pre_post_equal"] is not True
    ):
        _fail("terminal output fixed point differs from durable role extents")
    start = _nonnegative(cutoff["measurement_start_sequence"], "output start")
    end = _nonnegative(cutoff["operational_cutoff_sequence"], "output cutoff")
    if (
        cutoff["window_closed"] is not True
        or cutoff["cutoff_is_inclusive"] is not True
        or cutoff["global_event_count"] != len(ROLE_ORDER)
        or end != start + len(ROLE_ORDER)
        or cutoff["global_event_index"]
        != [
            {
                "global_sequence": row["global_sequence"],
                "artifact_role": row["artifact_role"],
                "durable_write_event_id": row["durable_write_event_id"],
            }
            for row in role_rows
        ]
        or [row["global_sequence"] for row in role_rows]
        != list(range(start + 1, end + 1))
    ):
        _fail("output cutoff hides, duplicates, or reorders a durable role")
    return OutputRawReplayV2(
        _REPLAY_ISSUER,
        fixed["live_envelope_id"],
        fixed["occurrence_id"],
        fixed["route_attempt_id"],
        fixed["decision_point_id"],
        fixed["measurement_window_id"],
        fixed["operational_cutoff_id"],
        total,
        authority,
        production,
        not production,
        False,
        False,
    )


def replay_production_output_exact_semantic_evidence_v2(
    *,
    fixed_point_bytes: bytes,
    exclusive_writer_bytes: bytes,
    cutoff_bytes: bytes,
    output_manifest_bytes: bytes,
) -> OutputRawReplayV2:
    """Replay raw output and reject synthetic construction promotion."""

    replay = replay_output_raw_evidence_v2(
        fixed_point_bytes=fixed_point_bytes,
        exclusive_writer_bytes=exclusive_writer_bytes,
        cutoff_bytes=cutoff_bytes,
        output_manifest_bytes=output_manifest_bytes,
    )
    if not replay.production_semantic_eligible:
        _fail("synthetic construction output is not exact-semantic eligible")
    return replay


__all__ = [
    "BROKER_ROLE_ORDER",
    "BUSINESS_ROLE",
    "BrokerDurableOutputSessionV2",
    "CUTOFF_SCHEMA_ID",
    "ConstructionSharedResourceOutputJournalV2Error",
    "EXCLUSIVE_WRITER_SCHEMA_ID",
    "FIXED_POINT_SCHEMA_ID",
    "MANIFEST_ROLE",
    "MAX_FIXED_POINT_ITERATIONS",
    "OUTPUT_MANIFEST_SCHEMA_ID",
    "OUTPUT_PATH",
    "OutputFirstRoleAuthorityV2",
    "OutputFinalizationStateV2",
    "OutputRawEvidenceBundleV2",
    "OutputRawReplayV2",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "ROLE_FILENAMES",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "WorkerBusinessResultCommitV2",
    "adopt_production_worker_operational_output_v2",
    "commit_synthetic_construction_first_role_v2",
    "commit_worker_business_result_v2",
    "open_broker_durable_output_session_v2",
    "replay_output_raw_evidence_v2",
    "replay_production_output_exact_semantic_evidence_v2",
]
