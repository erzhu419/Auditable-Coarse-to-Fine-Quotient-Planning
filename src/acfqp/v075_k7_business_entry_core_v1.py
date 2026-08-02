"""Bounded business-process entry core for one V0-075 K7 broker session.

This additive boundary performs exactly one existing child-business execution,
commits its public canonical bundle to one caller-owned empty sealable memfd,
and emits one role-bound ``BUSINESS_RESULT`` packet.  It deliberately stops
before the broker's parent-output/EOF protocol and before formal accounting.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import stat
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_child_business_bundle_v1 as business_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN,
    V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.7"
PROFILE_KEY = "v075_k7_business_entry_core_v1"
MAX_PUBLIC_BUNDLE_BYTES = min(
    business_v1.MAX_BUNDLE_BYTES,
    runtime_v1.MAX_CHILD_OUTPUT_BYTES,
    runtime_v1.MAX_SEALED_INPUT_BYTES,
)
BUSINESS_RESULT_ROLE = ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT
BUSINESS_RESULT_SEQUENCE = tuple(ipc_v1.FRAME_ROLES).index(BUSINESS_RESULT_ROLE)
SEND_FLAGS = getattr(socket, "MSG_NOSIGNAL", 0)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN,
        V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("business-entry core domains are unregistered")

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN",
    "V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN",
)

_PROFILE_ISSUER = object()
_EMISSION_ISSUER = object()


class V075K7BusinessEntryCoreV1Error(RuntimeError):
    """Business execution, immutable commit, or one-frame emission failed."""


class K7BusinessPublicationStageV1(str, Enum):
    DIRTY_UNSEALED = "DIRTY_UNSEALED"
    SEALED_UNANNOUNCED = "SEALED_UNANNOUNCED"
    SEND_OUTCOME_UNKNOWN = "SEND_OUTCOME_UNKNOWN"


class V075K7BusinessEntryBoundaryV1Error(V075K7BusinessEntryCoreV1Error):
    """Publication crossed an irreversible or non-clean boundary."""

    def __init__(
        self,
        message: str,
        *,
        stage: K7BusinessPublicationStageV1,
        bundle: business_v1.V075K7ChildBusinessBundleV1,
        binding_snapshot: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
        output_memfd: int,
        output_memfd_identity: tuple[int, int, int, int, int],
        endpoint_fd: int,
        endpoint_identity: tuple[int, int, int, int, int],
        output_memfd_seals: int,
        bytes_written: int,
        framed_packet: bytes | None,
        packet_delivery_verified: bool,
        rollback_complete: bool,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = K7BusinessPublicationStageV1(stage)
        self.bundle = bundle
        self.binding_snapshot = binding_snapshot
        self.output_memfd = output_memfd
        self.output_memfd_identity = output_memfd_identity
        self.endpoint_fd = endpoint_fd
        self.endpoint_identity = endpoint_identity
        self.output_memfd_seals = output_memfd_seals
        self.bytes_written = bytes_written
        self.framed_packet = framed_packet
        self.packet_delivery_verified = packet_delivery_verified
        self.rollback_complete = rollback_complete
        self.cause = cause

    def to_document(self) -> dict[str, Any]:
        raw = self.bundle.canonical_bytes
        return {
            "schema": "acfqp.v075_k7_business_entry_boundary_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "stage": self.stage.value,
            "ipc_binding": self.binding_snapshot.to_document(),
            "child_business_bundle_id": self.bundle.bundle_id,
            "child_business_bundle_sha256": hashlib.sha256(raw).hexdigest(),
            "child_business_bundle_byte_count": len(raw),
            "output_memfd": self.output_memfd,
            "output_memfd_identity": _descriptor_document(
                self.output_memfd_identity
            ),
            "output_memfd_seals": self.output_memfd_seals,
            "bytes_written": self.bytes_written,
            "endpoint_fd": self.endpoint_fd,
            "endpoint_identity": _descriptor_document(self.endpoint_identity),
            "framed_packet_sha256": (
                None
                if self.framed_packet is None
                else hashlib.sha256(self.framed_packet).hexdigest()
            ),
            "framed_packet_byte_count": (
                None if self.framed_packet is None else len(self.framed_packet)
            ),
            "packet_delivery_verified": self.packet_delivery_verified,
            "rollback_complete": self.rollback_complete,
            "formal_accounting_authority": False,
            "attempt_terminal_authority": False,
            **_formal_locks(),
        }


def _fail(message: str) -> NoReturn:
    raise V075K7BusinessEntryCoreV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("business-entry core used an undeclared content domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7BusinessEntryCoreV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _formal_locks() -> dict[str, bool]:
    return {
        "complete_five_frame_protocol_verified": False,
        "parent_output_committed": False,
        "worker_eof_verified": False,
        "exact_process_launches_signed": False,
        "complete_attempt_memory_window_verified": False,
        "shared_resource_value_issued": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "actual_projection_proof_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


def _descriptor_tuple(status: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
    )


def _descriptor_document(
    identity: tuple[int, int, int, int, int],
) -> dict[str, int]:
    device, inode, mode, owner_uid, owner_gid = identity
    return {
        "device": device,
        "inode": inode,
        "mode": mode,
        "owner_uid": owner_uid,
        "owner_gid": owner_gid,
    }


@dataclass(frozen=True, slots=True)
class K7BusinessEntryCoreProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("business-entry core profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_business_entry_core_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "business_executor": (
                "execute_v075_k7_child_business_bundle_from_"
                "sealed_descriptors_v1"
            ),
            "business_executor_invocations": 1,
            "max_public_bundle_bytes": MAX_PUBLIC_BUNDLE_BYTES,
            "caller_owned_empty_memfd_required": True,
            "output_memfd_initial_size": 0,
            "output_memfd_initial_seals": 0,
            "output_memfd_read_write_required": True,
            "output_memfd_cloexec_required": True,
            "positional_write_from_offset_zero": True,
            "fsync_before_sealing_required": True,
            "required_memfd_seals": runtime_v1.REQUIRED_MEMFD_SEALS,
            "sealed_memfd_runtime_replay_required": True,
            "public_bundle_replay_count": 2,
            "endpoint_family": "AF_UNIX",
            "endpoint_type": "SOCK_SEQPACKET",
            "blocking_endpoint_without_timeout_required": True,
            "kernel_o_nonblock_rejected": True,
            "business_result_role": BUSINESS_RESULT_ROLE.value,
            "business_result_sequence": BUSINESS_RESULT_SEQUENCE,
            "business_result_payload_fields": ["business_result_id"],
            "business_result_send_calls": 1,
            "ancillary_descriptors_sent": 0,
            "caller_descriptors_closed": 0,
            "owned_output_and_endpoint_duplicates_used": True,
            "production_role_manifest_joined": False,
            "binding_snapshot_revalidated_before_publication": True,
            "boundary_stages": [
                stage.value for stage in K7BusinessPublicationStageV1
            ],
            "preseal_rollback_required": True,
            "exact_ipc_binding_required": True,
            "ipc_binding_provenance_authority": False,
            "exclusive_endpoint_writer_verified": False,
            "complete_protocol_authority": False,
            "formal_accounting_authority": False,
            **_formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("business-entry core profile changed after issuance")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "business_entry_core_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7BusinessEntryCoreProfileV1(_PROFILE_ISSUER)


def official_v075_k7_business_entry_core_profile_v1(
) -> K7BusinessEntryCoreProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7BusinessEntryCoreEmissionV1:
    _issuer: InitVar[object]
    profile: K7BusinessEntryCoreProfileV1 = field(repr=False)
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    request_replay_id: str
    business_bundle: business_v1.V075K7ChildBusinessBundleV1 = field(repr=False)
    business_result_frame: ipc_v1.K7OuterAttemptBrokerIPCFrameV1 = field(
        repr=False
    )
    output_memfd: int
    output_memfd_identity: tuple[int, int, int, int, int]
    output_memfd_seals: int
    endpoint_fd: int
    endpoint_identity: tuple[int, int, int, int, int]
    bundle_sha256: str
    bundle_byte_count: int
    framed_packet_sha256: str
    framed_packet_byte_count: int
    sent_byte_count: int
    _emission_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EMISSION_ISSUER
            or self.profile is not _OFFICIAL_PROFILE
            or type(self.binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
            or type(self.business_bundle)
            is not business_v1.V075K7ChildBusinessBundleV1
            or type(self.business_result_frame)
            is not ipc_v1.K7OuterAttemptBrokerIPCFrameV1
        ):
            _fail("business-entry emission is caller-minted or crossed")
        _cid(self.request_replay_id, "request replay")
        bundle_raw = self.business_bundle.canonical_bytes
        bundle_document = self.business_bundle.to_document()
        frame_raw = self.business_result_frame.framed_bytes
        if (
            bundle_document["portable_request_replay_id"] != self.request_replay_id
            or bundle_document["request_id"] != self.binding.request_id
            or bundle_document["route_identity_id"] != self.binding.route_identity_id
            or self.business_result_frame.binding != self.binding
            or self.business_result_frame.role is not BUSINESS_RESULT_ROLE
            or self.business_result_frame.sequence != BUSINESS_RESULT_SEQUENCE
            or dict(self.business_result_frame.payload)
            != {"business_result_id": self.business_bundle.bundle_id}
        ):
            _fail("business-entry emission crossed its request, route, or frame")
        if (
            type(self.output_memfd) is not int
            or self.output_memfd < 0
            or type(self.endpoint_fd) is not int
            or self.endpoint_fd < 0
            or not _valid_descriptor_identity(self.output_memfd_identity)
            or not _valid_descriptor_identity(self.endpoint_identity)
            or type(self.output_memfd_seals) is not int
            or self.output_memfd_seals != runtime_v1.REQUIRED_MEMFD_SEALS
            or type(self.bundle_byte_count) is not int
            or self.bundle_byte_count != len(bundle_raw)
            or type(self.framed_packet_byte_count) is not int
            or self.framed_packet_byte_count != len(frame_raw)
            or type(self.sent_byte_count) is not int
            or self.sent_byte_count != len(frame_raw)
            or self.bundle_sha256 != hashlib.sha256(bundle_raw).hexdigest()
            or self.framed_packet_sha256 != hashlib.sha256(frame_raw).hexdigest()
        ):
            _fail("business-entry emission facts are invalid or incomplete")
        object.__setattr__(
            self,
            "_emission_id",
            _hash(
                V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_business_entry_core_emission.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "business_entry_core_profile_id": self.profile.profile_id,
            "ipc_binding": self.binding.to_document(),
            "portable_request_replay_id": self.request_replay_id,
            "child_business_bundle_id": self.business_bundle.bundle_id,
            "child_business_bundle_sha256": self.bundle_sha256,
            "child_business_bundle_byte_count": self.bundle_byte_count,
            "output_memfd": self.output_memfd,
            "output_memfd_identity": _descriptor_document(
                self.output_memfd_identity
            ),
            "output_memfd_seals": self.output_memfd_seals,
            "output_memfd_fsync_calls": 1,
            "output_memfd_seal_add_calls": 1,
            "sealed_memfd_runtime_replay_complete": True,
            "public_bundle_replay_count": 2,
            "endpoint_fd": self.endpoint_fd,
            "endpoint_identity": _descriptor_document(self.endpoint_identity),
            "frame_role": self.business_result_frame.role.value,
            "frame_sequence": self.business_result_frame.sequence,
            "outer_attempt_broker_ipc_frame_id": (
                self.business_result_frame.frame_id
            ),
            "framed_packet_sha256": self.framed_packet_sha256,
            "framed_packet_byte_count": self.framed_packet_byte_count,
            "business_result_send_calls": 1,
            "sent_byte_count": self.sent_byte_count,
            "ancillary_descriptors_sent": 0,
            "business_executor_invocations": 1,
            "output_memfd_caller_owned": True,
            "endpoint_caller_owned": True,
            "caller_descriptors_closed": 0,
            "publication_operated_on_owned_duplicates": True,
            "descriptor_numbers_are_historical_not_live_capabilities": True,
            "same_address_space_private_sentinel_is_security_capability": False,
            "issuer_owned_nonformal_historical_emission": True,
            "production_role_manifest_joined": False,
            "ipc_binding_provenance_authority": False,
            "exclusive_endpoint_writer_verified": False,
            "complete_protocol_authority": False,
            "formal_accounting_authority": False,
            **_formal_locks(),
        }

    @property
    def emission_id(self) -> str:
        if _hash(
            V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN,
            self._payload(),
        ) != self._emission_id:
            _fail("business-entry emission changed after issuance")
        return self._emission_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "business_entry_core_emission_id": self.emission_id,
        }

    def __reduce__(self) -> object:
        raise TypeError("business-entry emission is process-local and unpickleable")

    def __reduce_ex__(self, _protocol: int) -> object:
        raise TypeError("business-entry emission is process-local and unpickleable")


def _valid_descriptor_identity(value: Any) -> bool:
    return (
        type(value) is tuple
        and len(value) == 5
        and all(type(item) is int and item >= 0 for item in value)
    )


def _inspect_empty_output_memfd(
    descriptor: int,
) -> tuple[os.stat_result, tuple[int, int, int, int, int], int]:
    if type(descriptor) is not int or descriptor < 0:
        _fail("output memfd descriptor is invalid")
    try:
        status = os.fstat(descriptor)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
        inheritable = os.get_inheritable(descriptor)
    except OSError as error:
        raise V075K7BusinessEntryCoreV1Error(
            "output descriptor is not one inspectable sealable memfd"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_size != 0
        or flags & os.O_ACCMODE != os.O_RDWR
        or flags & os.O_APPEND
        or seals != 0
        or inheritable
    ):
        _fail("output memfd is not empty, read-write, unsealed, and CLOEXEC")
    return status, _descriptor_tuple(status), flags


def _inspect_endpoint(
    endpoint: socket.socket,
) -> tuple[int, os.stat_result, tuple[int, int, int, int, int]]:
    if type(endpoint) is not socket.socket:
        _fail("business-result endpoint must be one exact socket object")
    try:
        descriptor = endpoint.fileno()
        status = os.fstat(descriptor)
        socket_type = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        if not hasattr(socket, "SO_DOMAIN"):
            _fail("Linux SO_DOMAIN is unavailable for endpoint verification")
        kernel_domain = endpoint.getsockopt(
            socket.SOL_SOCKET, socket.SO_DOMAIN
        )
        endpoint.getpeername()
        inheritable = os.get_inheritable(descriptor)
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    except (OSError, ValueError) as error:
        raise V075K7BusinessEntryCoreV1Error(
            "business-result endpoint is closed or unconnected"
        ) from error
    if (
        descriptor < 0
        or endpoint.family != socket.AF_UNIX
        or kernel_domain != socket.AF_UNIX
        or socket_type != socket.SOCK_SEQPACKET
        or not stat.S_ISSOCK(status.st_mode)
        or endpoint.gettimeout() is not None
        or descriptor_flags & os.O_NONBLOCK
        or inheritable
    ):
        _fail("business-result endpoint is not blocking AF_UNIX SOCK_SEQPACKET")
    return descriptor, status, _descriptor_tuple(status)


def _snapshot_binding(
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
) -> ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
    if type(binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
        _fail("broker IPC binding is mistyped")
    try:
        snapshot = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
            binding.request_id,
            binding.route_identity_id,
            binding.broker_execution_spec_id,
            binding.session_nonce,
        )
    except Exception as error:
        raise V075K7BusinessEntryCoreV1Error(
            "broker IPC binding could not be snapshotted"
        ) from error
    if binding.to_document() != snapshot.to_document():
        _fail("broker IPC binding changed during snapshot")
    return snapshot


def _binding_matches_snapshot(
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    snapshot: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
) -> bool:
    try:
        return type(binding) is type(snapshot) and binding.to_document() == snapshot.to_document()
    except Exception:
        return False


def _dup_cloexec(descriptor: int, label: str) -> int:
    try:
        if hasattr(fcntl, "F_DUPFD_CLOEXEC"):
            duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
        else:  # pragma: no cover - Linux provides F_DUPFD_CLOEXEC
            duplicate = os.dup(descriptor)
            os.set_inheritable(duplicate, False)
    except OSError as error:
        raise V075K7BusinessEntryCoreV1Error(
            f"{label} descriptor could not be duplicated"
        ) from error
    return duplicate


def _rollback_unsealed_output(descriptor: int) -> bool:
    try:
        seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
        if seals != 0:
            return False
        os.ftruncate(descriptor, 0)
        os.fsync(descriptor)
        status = os.fstat(descriptor)
        return status.st_size == 0 and fcntl.fcntl(
            descriptor, runtime_v1.F_GET_SEALS
        ) == 0
    except OSError:
        return False


def _same_unmodified_empty_memfd(
    before: os.stat_result,
    after: os.stat_result,
    before_flags: int,
    after_flags: int,
) -> bool:
    return (
        _descriptor_tuple(before) == _descriptor_tuple(after)
        and before.st_size == after.st_size == 0
        and before.st_mtime_ns == after.st_mtime_ns
        and before.st_ctime_ns == after.st_ctime_ns
        and before_flags == after_flags
    )


class _PartialWriteError(RuntimeError):
    def __init__(self, message: str, *, bytes_written: int) -> None:
        super().__init__(message)
        self.bytes_written = bytes_written


def _write_all_at_start(descriptor: int, raw: bytes) -> int:
    offset = 0
    try:
        while offset < len(raw):
            written = os.pwrite(descriptor, raw[offset:], offset)
            if written <= 0:
                raise _PartialWriteError(
                    "output memfd positional write made no progress",
                    bytes_written=offset,
                )
            offset += written
    except OSError as error:
        failure = _PartialWriteError(
            "output memfd positional write failed",
            bytes_written=offset,
        )
        raise failure from error
    return offset


def execute_v075_k7_business_entry_core_v1(
    *,
    request_replay: business_v1.portable_replay.V075K7SuccessorPortableRequestReplayV1,
    source_archive_fd: int,
    sealed_secret_fd: int,
    repository_root: str | Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
    output_memfd: int,
    business_result_endpoint: socket.socket,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
) -> K7BusinessEntryCoreEmissionV1:
    """Execute, immutably publish, and announce exactly one business result."""

    if (
        type(request_replay)
        is not business_v1.portable_replay.V075K7SuccessorPortableRequestReplayV1
    ):
        _fail("business-entry core requires the exact request replay")
    request_replay.profile_closure._assert_current()  # noqa: SLF001
    request = request_replay.request
    request._assert_current()  # noqa: SLF001
    replay_id = _cid(request_replay.replay_id, "portable request replay")
    request_id = _cid(request.request_id, "request")
    route_identity_id = _cid(
        request.route_identity.route_identity_id,
        "route identity",
    )
    binding_snapshot = _snapshot_binding(binding)
    if (
        binding_snapshot.request_id != request_id
        or binding_snapshot.route_identity_id != route_identity_id
    ):
        _fail("broker IPC binding crossed the exact request or route")
    if (
        type(source_archive_fd) is not int
        or source_archive_fd < 0
        or type(sealed_secret_fd) is not int
        or sealed_secret_fd < 0
    ):
        _fail("sealed business input descriptors are invalid")

    output_before, output_identity, output_flags = _inspect_empty_output_memfd(
        output_memfd
    )
    endpoint_fd, endpoint_before, endpoint_identity = _inspect_endpoint(
        business_result_endpoint
    )
    if len(
        {
            source_archive_fd,
            sealed_secret_fd,
            output_memfd,
            endpoint_fd,
        }
    ) != 4:
        _fail("business input, output, and endpoint descriptor numbers must differ")

    try:
        bundle = (
            business_v1
            .execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1(
                request_replay=request_replay,
                source_archive_fd=source_archive_fd,
                sealed_secret_fd=sealed_secret_fd,
                repository_root=repository_root,
                signer_private_root=signer_private_root,
                signer_private_key_path=signer_private_key_path,
            )
        )
    except Exception as error:
        raise V075K7BusinessEntryCoreV1Error(
            "child business execution failed before result publication"
        ) from error
    if type(bundle) is not business_v1.V075K7ChildBusinessBundleV1:
        _fail("child business executor returned a caller-minted bundle")
    raw = bundle.canonical_bytes
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_PUBLIC_BUNDLE_BYTES:
        _fail("child business canonical bundle is empty, mistyped, or over cap")
    try:
        verified_before_commit = (
            business_v1.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=raw,
                expected_request_replay=request_replay,
            )
        )
    except Exception as error:
        raise V075K7BusinessEntryCoreV1Error(
            "child business bundle failed public replay before commit"
        ) from error
    if (
        type(verified_before_commit) is not business_v1.V075K7ChildBusinessBundleV1
        or verified_before_commit.bundle_id != bundle.bundle_id
        or verified_before_commit.canonical_bytes != raw
    ):
        _fail("child business public replay changed bundle identity")

    output_rechecked, rechecked_identity, rechecked_flags = (
        _inspect_empty_output_memfd(output_memfd)
    )
    if (
        rechecked_identity != output_identity
        or not _same_unmodified_empty_memfd(
            output_before,
            output_rechecked,
            output_flags,
            rechecked_flags,
        )
    ):
        _fail("output memfd changed during child business execution")
    endpoint_rechecked_fd, endpoint_rechecked, endpoint_rechecked_identity = (
        _inspect_endpoint(business_result_endpoint)
    )
    if (
        endpoint_rechecked_fd != endpoint_fd
        or endpoint_rechecked_identity != endpoint_identity
        or _descriptor_tuple(endpoint_rechecked) != _descriptor_tuple(endpoint_before)
    ):
        _fail("business-result endpoint changed during child business execution")

    if not _binding_matches_snapshot(binding, binding_snapshot):
        _fail("broker IPC binding changed during child business execution")

    owned_output_fd = _dup_cloexec(output_memfd, "output memfd")
    owned_endpoint: socket.socket | None = None
    try:
        try:
            owned_endpoint = business_result_endpoint.dup()
            owned_endpoint.set_inheritable(False)
        except (OSError, ValueError) as error:
            raise V075K7BusinessEntryCoreV1Error(
                "business-result endpoint could not be duplicated"
            ) from error
        owned_output_status, owned_output_identity, _owned_output_flags = (
            _inspect_empty_output_memfd(owned_output_fd)
        )
        (
            _owned_endpoint_fd,
            owned_endpoint_status,
            owned_endpoint_identity,
        ) = _inspect_endpoint(owned_endpoint)
        if (
            owned_output_identity != output_identity
            or _descriptor_tuple(owned_output_status) != output_identity
            or owned_endpoint_identity != endpoint_identity
            or _descriptor_tuple(owned_endpoint_status) != endpoint_identity
        ):
            _fail("owned publication descriptors crossed their caller identities")

        bytes_written = 0
        try:
            bytes_written = _write_all_at_start(owned_output_fd, raw)
            os.fsync(owned_output_fd)
        except Exception as error:
            partial = getattr(error, "bytes_written", bytes_written)
            rollback_complete = _rollback_unsealed_output(owned_output_fd)
            if rollback_complete:
                raise V075K7BusinessEntryCoreV1Error(
                    "business-result pre-seal publication failed and rolled back"
                ) from error
            try:
                observed_seals = fcntl.fcntl(
                    owned_output_fd, runtime_v1.F_GET_SEALS
                )
            except OSError:
                observed_seals = -1
            raise V075K7BusinessEntryBoundaryV1Error(
                "business-result memfd is dirty after failed pre-seal publication",
                stage=K7BusinessPublicationStageV1.DIRTY_UNSEALED,
                bundle=bundle,
                binding_snapshot=binding_snapshot,
                output_memfd=output_memfd,
                output_memfd_identity=output_identity,
                endpoint_fd=endpoint_fd,
                endpoint_identity=endpoint_identity,
                output_memfd_seals=observed_seals,
                bytes_written=partial,
                framed_packet=None,
                packet_delivery_verified=False,
                rollback_complete=False,
                cause=error,
            ) from error

        try:
            fcntl.fcntl(
                owned_output_fd,
                runtime_v1.F_ADD_SEALS,
                runtime_v1.REQUIRED_MEMFD_SEALS,
            )
        except Exception as error:
            rollback_complete = _rollback_unsealed_output(owned_output_fd)
            if rollback_complete:
                raise V075K7BusinessEntryCoreV1Error(
                    "business-result sealing failed and unsealed bytes rolled back"
                ) from error
            try:
                observed_seals = fcntl.fcntl(
                    owned_output_fd, runtime_v1.F_GET_SEALS
                )
            except OSError:
                observed_seals = -1
            stage = (
                K7BusinessPublicationStageV1.SEALED_UNANNOUNCED
                if observed_seals == runtime_v1.REQUIRED_MEMFD_SEALS
                else K7BusinessPublicationStageV1.DIRTY_UNSEALED
            )
            raise V075K7BusinessEntryBoundaryV1Error(
                "business-result seal transition left publication evidence",
                stage=stage,
                bundle=bundle,
                binding_snapshot=binding_snapshot,
                output_memfd=output_memfd,
                output_memfd_identity=output_identity,
                endpoint_fd=endpoint_fd,
                endpoint_identity=endpoint_identity,
                output_memfd_seals=observed_seals,
                bytes_written=bytes_written,
                framed_packet=None,
                packet_delivery_verified=False,
                rollback_complete=False,
                cause=error,
            ) from error

        framed_packet: bytes | None = None

        def sealed_boundary(
            message: str,
            error: BaseException | None,
            *,
            stage: K7BusinessPublicationStageV1 = (
                K7BusinessPublicationStageV1.SEALED_UNANNOUNCED
            ),
        ) -> V075K7BusinessEntryBoundaryV1Error:
            try:
                observed = fcntl.fcntl(
                    owned_output_fd, runtime_v1.F_GET_SEALS
                )
            except OSError:
                observed = -1
            return V075K7BusinessEntryBoundaryV1Error(
                message,
                stage=stage,
                bundle=bundle,
                binding_snapshot=binding_snapshot,
                output_memfd=output_memfd,
                output_memfd_identity=output_identity,
                endpoint_fd=endpoint_fd,
                endpoint_identity=endpoint_identity,
                output_memfd_seals=observed,
                bytes_written=bytes_written,
                framed_packet=framed_packet,
                packet_delivery_verified=False,
                rollback_complete=False,
                cause=error,
            )

        try:
            sealed_raw, sealed_status = runtime_v1._read_fd(  # noqa: SLF001
                owned_output_fd,
                MAX_PUBLIC_BUNDLE_BYTES,
                "business-entry public bundle memfd",
            )
            final_seals = fcntl.fcntl(
                owned_output_fd, runtime_v1.F_GET_SEALS
            )
        except Exception as error:
            raise sealed_boundary(
                "sealed business-result memfd replay failed", error
            ) from error
        if (
            sealed_raw != raw
            or final_seals != runtime_v1.REQUIRED_MEMFD_SEALS
            or _descriptor_tuple(sealed_status) != output_identity
            or sealed_status.st_size != len(raw)
        ):
            raise sealed_boundary(
                "sealed business-result memfd changed during immutable commit",
                None,
            )
        try:
            verified_after_commit = (
                business_v1.verify_v075_k7_child_business_bundle_public_bytes_v1(
                    raw=sealed_raw,
                    expected_request_replay=request_replay,
                )
            )
        except Exception as error:
            raise sealed_boundary(
                "sealed child business bundle failed public replay", error
            ) from error
        if (
            type(verified_after_commit)
            is not business_v1.V075K7ChildBusinessBundleV1
            or verified_after_commit.bundle_id != bundle.bundle_id
            or verified_after_commit.canonical_bytes != raw
        ):
            raise sealed_boundary(
                "sealed child business bundle replay changed identity", None
            )

        if not _binding_matches_snapshot(binding, binding_snapshot):
            raise sealed_boundary(
                "broker IPC binding changed before business-result emission", None
            )
        try:
            framed_packet = (
                ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
                    binding=binding_snapshot,
                    role=BUSINESS_RESULT_ROLE,
                    payload={"business_result_id": bundle.bundle_id},
                )
            )
            frame = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
                raw=framed_packet,
                expected_binding=binding_snapshot,
                expected_role=BUSINESS_RESULT_ROLE,
            )
        except Exception as error:
            raise sealed_boundary(
                "business-result frame construction or replay failed", error
            ) from error
        if (
            type(frame) is not ipc_v1.K7OuterAttemptBrokerIPCFrameV1
            or frame.sequence != BUSINESS_RESULT_SEQUENCE
            or dict(frame.payload) != {"business_result_id": bundle.bundle_id}
        ):
            raise sealed_boundary(
                "business-result frame replay changed role or payload", None
            )
        try:
            (
                _final_endpoint_fd,
                final_endpoint_status,
                final_endpoint_identity,
            ) = _inspect_endpoint(owned_endpoint)
        except Exception as error:
            raise sealed_boundary(
                "business-result endpoint changed before emission", error
            ) from error
        if (
            final_endpoint_identity != endpoint_identity
            or _descriptor_tuple(final_endpoint_status) != endpoint_identity
        ):
            raise sealed_boundary(
                "business-result endpoint changed before emission", None
            )

        # Freeze the complete historical DTO before the only send.  After a
        # successful atomic SEQPACKET send, returning this object and closing
        # owned duplicates are deliberately non-validating/nonfallible.
        candidate = K7BusinessEntryCoreEmissionV1(
            _EMISSION_ISSUER,
            _OFFICIAL_PROFILE,
            binding_snapshot,
            replay_id,
            bundle,
            frame,
            output_memfd,
            output_identity,
            final_seals,
            endpoint_fd,
            endpoint_identity,
            hashlib.sha256(raw).hexdigest(),
            len(raw),
            hashlib.sha256(framed_packet).hexdigest(),
            len(framed_packet),
            len(framed_packet),
        )
        try:
            sent = owned_endpoint.send(framed_packet, SEND_FLAGS)
        except OSError as error:
            raise sealed_boundary(
                "single BUSINESS_RESULT packet send outcome is unknown",
                error,
                stage=K7BusinessPublicationStageV1.SEND_OUTCOME_UNKNOWN,
            ) from error
        if sent != len(framed_packet):
            raise sealed_boundary(
                "single BUSINESS_RESULT packet send outcome is short or unknown",
                None,
                stage=K7BusinessPublicationStageV1.SEND_OUTCOME_UNKNOWN,
            )
        return candidate
    finally:
        if owned_endpoint is not None:
            try:
                owned_endpoint.close()
            except OSError:  # pragma: no cover - close cannot alter sent record
                pass
        try:
            os.close(owned_output_fd)
        except OSError:  # pragma: no cover - close cannot alter sealed caller OFD
            pass


__all__ = (
    "BUSINESS_RESULT_ROLE",
    "BUSINESS_RESULT_SEQUENCE",
    "K7BusinessPublicationStageV1",
    "K7BusinessEntryCoreEmissionV1",
    "K7BusinessEntryCoreProfileV1",
    "LOCAL_DOMAIN_TAGS",
    "MAX_PUBLIC_BUNDLE_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7BusinessEntryBoundaryV1Error",
    "V075K7BusinessEntryCoreV1Error",
    "execute_v075_k7_business_entry_core_v1",
    "official_v075_k7_business_entry_core_profile_v1",
)
