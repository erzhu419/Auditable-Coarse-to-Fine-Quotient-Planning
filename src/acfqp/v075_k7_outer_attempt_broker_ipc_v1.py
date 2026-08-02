"""Strict canonical IPC framing for a future K7 outer-attempt broker.

This module freezes only a byte protocol.  It does not launch a process,
authenticate an operating-system broker, or turn any payload into accounting
evidence.  A complete stream contains exactly five role-separated frames in
the order frozen by :data:`FRAME_ROLES`.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.4"
PROFILE_KEY = "v075_k7_outer_attempt_broker_ipc_v1"
FRAME_WIDTH = 8
MAX_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_FRAME_BYTES = MAX_PAYLOAD_BYTES + 1024 * 1024
MAX_STREAM_BYTES = len(tuple(range(5))) * (FRAME_WIDTH + MAX_FRAME_BYTES)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("outer-attempt broker IPC domains are unregistered")

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN",
)

_PROFILE_ISSUER = object()
_FRAME_ISSUER = object()
_TRANSCRIPT_ISSUER = object()


class V075K7OuterAttemptBrokerIPCV1Error(ValueError):
    """A binding, frame, payload, or complete stream is invalid."""


class K7OuterAttemptBrokerFrameRoleV1(str, Enum):
    WORKER_READY = "WORKER_READY"
    BUSINESS_REQUEST = "BUSINESS_REQUEST"
    BUSINESS_RESULT = "BUSINESS_RESULT"
    PARENT_OUTPUT = "PARENT_OUTPUT"
    WORKER_EOF = "WORKER_EOF"


FRAME_ROLES = tuple(K7OuterAttemptBrokerFrameRoleV1)
_ROLE_INDEX = {role: index for index, role in enumerate(FRAME_ROLES)}
_ROLE_PAYLOAD_FIELDS = {
    K7OuterAttemptBrokerFrameRoleV1.WORKER_READY: ("worker_replay_id",),
    K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST: ("request_ordinal",),
    K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT: ("business_result_id",),
    K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT: (
        "output_byte_count",
        "output_sha256",
    ),
    K7OuterAttemptBrokerFrameRoleV1.WORKER_EOF: ("clean_close",),
}


def _fail(message: str) -> NoReturn:
    raise V075K7OuterAttemptBrokerIPCV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("outer-attempt broker IPC used an undeclared domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "broker_os_provenance_verified": False,
        "process_launches_verified": False,
        "complete_attempt_memory_window_verified": False,
        "shared_resource_resolution_authorized": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "actual_projection_proof_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class K7OuterAttemptBrokerIPCProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("outer-attempt broker IPC profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_broker_ipc_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "frame_width_bytes": FRAME_WIDTH,
            "max_payload_bytes": MAX_PAYLOAD_BYTES,
            "max_frame_bytes": MAX_FRAME_BYTES,
            "max_stream_bytes": MAX_STREAM_BYTES,
            "frame_roles": [role.value for role in FRAME_ROLES],
            "binding_fields": [
                "request_id",
                "route_identity_id",
                "broker_execution_spec_id",
                "session_nonce",
            ],
            "role_payload_fields": {
                role.value: list(_ROLE_PAYLOAD_FIELDS[role])
                for role in FRAME_ROLES
            },
            "caller_sequence_accepted": False,
            "caller_constructed_binding_allowed": True,
            "live_session_nonce_consumption_implemented": False,
            "live_peer_role_ownership_verified": False,
            "offline_stream_replay_rejected": False,
            "launch_authority": False,
            "canonical_json_required": True,
            "canonical_lowercase_hex_length_prefix_required": True,
            "role_payload_schema_verified": True,
            "payload_semantics_verified": False,
            "structural_ipc_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("outer-attempt broker IPC profile changed after freeze")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "outer_attempt_broker_ipc_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7OuterAttemptBrokerIPCProfileV1(_PROFILE_ISSUER)


def official_v075_k7_outer_attempt_broker_ipc_profile_v1(
) -> K7OuterAttemptBrokerIPCProfileV1:
    return _OFFICIAL_PROFILE


def _identity(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonce(value: Any) -> str:
    # The session nonce intentionally has the same exact wire shape as an ID,
    # but is not reinterpreted as a content-derived identity.
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail("broker session nonce must be 64 lowercase hexadecimal characters")
    return value


def _canonical_payload(payload: Any) -> tuple[dict[str, Any], bytes]:
    if type(payload) is not dict:
        _fail("broker IPC payload must be one exact canonical object")
    try:
        raw = canonical_json_bytes(payload)
        replayed = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC payload is outside canonical JSON"
        ) from error
    if type(replayed) is not dict or replayed != payload:
        _fail("broker IPC payload changed under canonical replay")
    if len(raw) > MAX_PAYLOAD_BYTES:
        _fail("broker IPC payload exceeds its byte cap")
    return replayed, raw


def _exact_digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be 64 lowercase hexadecimal characters")
    return value


def _validate_role_payload(
    role: K7OuterAttemptBrokerFrameRoleV1,
    payload: dict[str, Any],
) -> None:
    if tuple(sorted(payload)) != tuple(sorted(_ROLE_PAYLOAD_FIELDS[role])):
        _fail("broker IPC role payload fields are incomplete or unknown")
    if role is K7OuterAttemptBrokerFrameRoleV1.WORKER_READY:
        _identity(payload["worker_replay_id"], "worker replay")
    elif role is K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST:
        if (
            type(payload["request_ordinal"]) is not int
            or payload["request_ordinal"] != 0
        ):
            _fail("business request ordinal must be the exact integer zero")
    elif role is K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT:
        _identity(payload["business_result_id"], "business result")
    elif role is K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT:
        if (
            type(payload["output_byte_count"]) is not int
            or not 0 <= payload["output_byte_count"] <= MAX_PAYLOAD_BYTES
        ):
            _fail("parent output byte count is outside its exact integer cap")
        _exact_digest(payload["output_sha256"], "parent output digest")
    elif (
        type(payload["clean_close"]) is not bool
        or payload["clean_close"] is not True
    ):
        _fail("worker EOF must carry the exact clean-close boolean")


@dataclass(frozen=True, slots=True)
class K7OuterAttemptBrokerIPCBindingV1:
    request_id: str
    route_identity_id: str
    broker_execution_spec_id: str
    session_nonce: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _identity(self.request_id, "request"))
        object.__setattr__(
            self,
            "route_identity_id",
            _identity(self.route_identity_id, "route identity"),
        )
        object.__setattr__(
            self,
            "broker_execution_spec_id",
            _identity(
                self.broker_execution_spec_id,
                "broker execution spec",
            ),
        )
        object.__setattr__(self, "session_nonce", _nonce(self.session_nonce))

    def to_document(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "broker_execution_spec_id": self.broker_execution_spec_id,
            "session_nonce": self.session_nonce,
        }


@dataclass(frozen=True, slots=True)
class K7OuterAttemptBrokerIPCFrameV1:
    _issuer: InitVar[object]
    binding: K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    role: K7OuterAttemptBrokerFrameRoleV1
    sequence: int
    payload: Mapping[str, Any] = field(repr=False)
    _payload_bytes: bytes = field(init=False, repr=False, compare=False)
    _frame_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _FRAME_ISSUER
            or type(self.binding) is not K7OuterAttemptBrokerIPCBindingV1
        ):
            _fail("broker IPC frame is caller-minted or crossed")
        try:
            role = K7OuterAttemptBrokerFrameRoleV1(self.role)
        except (TypeError, ValueError) as error:
            raise V075K7OuterAttemptBrokerIPCV1Error(
                "broker IPC frame role is unknown"
            ) from error
        if type(self.sequence) is not int or self.sequence != _ROLE_INDEX[role]:
            _fail("broker IPC frame sequence differs from its fixed role")
        payload, payload_bytes = _canonical_payload(self.payload)
        _validate_role_payload(role, payload)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "payload", MappingProxyType(dict(payload)))
        object.__setattr__(self, "_payload_bytes", payload_bytes)
        object.__setattr__(
            self,
            "_frame_id",
            _hash(
                V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_broker_ipc_frame.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_attempt_broker_ipc_profile_id": _OFFICIAL_PROFILE.profile_id,
            "frame_role": self.role.value,
            "sequence": self.sequence,
            **self.binding.to_document(),
            "payload_sha256": hashlib.sha256(self._payload_bytes).hexdigest(),
            "payload_byte_count": len(self._payload_bytes),
            "payload": dict(self.payload),
            "formal_locks": _formal_locks(),
        }

    @property
    def frame_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN,
            self._payload(),
        ) != self._frame_id:
            _fail("broker IPC frame changed after issuance")
        return self._frame_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(
            {**self._payload(), "outer_attempt_broker_ipc_frame_id": self.frame_id}
        )
        if not raw or len(raw) > MAX_FRAME_BYTES:
            _fail("broker IPC frame exceeds its byte cap")
        return raw

    @property
    def framed_bytes(self) -> bytes:
        raw = self.canonical_bytes
        return f"{len(raw):0{FRAME_WIDTH}x}".encode("ascii") + raw

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        assert type(value) is dict
        return value


def encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
    *,
    binding: K7OuterAttemptBrokerIPCBindingV1,
    role: K7OuterAttemptBrokerFrameRoleV1,
    payload: dict[str, Any],
) -> bytes:
    """Encode one role-bound frame; sequence is derived, never caller supplied."""

    if type(binding) is not K7OuterAttemptBrokerIPCBindingV1:
        _fail("broker IPC encoder requires one exact binding")
    try:
        exact_role = K7OuterAttemptBrokerFrameRoleV1(role)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC encoder received an unknown role"
        ) from error
    return K7OuterAttemptBrokerIPCFrameV1(
        _FRAME_ISSUER,
        binding,
        exact_role,
        _ROLE_INDEX[exact_role],
        payload,
    ).framed_bytes


def encode_v075_k7_outer_attempt_broker_ipc_stream_v1(
    *,
    binding: K7OuterAttemptBrokerIPCBindingV1,
    frames: tuple[tuple[K7OuterAttemptBrokerFrameRoleV1, dict[str, Any]], ...],
) -> bytes:
    """Encode exactly the complete five-role protocol in its frozen order."""

    if (
        type(frames) is not tuple
        or len(frames) != len(FRAME_ROLES)
        or any(type(item) is not tuple or len(item) != 2 for item in frames)
    ):
        _fail("broker IPC stream requires exactly five role/payload pairs")
    try:
        roles = tuple(K7OuterAttemptBrokerFrameRoleV1(item[0]) for item in frames)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC stream contains an unknown role"
        ) from error
    if roles != FRAME_ROLES:
        _fail("broker IPC stream roles are duplicated, omitted, or out of order")
    raw = b"".join(
        encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
            binding=binding,
            role=role,
            payload=payload,
        )
        for role, payload in frames
    )
    if len(raw) > MAX_STREAM_BYTES:  # pragma: no cover - implied by frame caps
        _fail("broker IPC stream exceeds its byte cap")
    return raw


_FRAME_DOCUMENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "outer_attempt_broker_ipc_profile_id",
        "frame_role",
        "sequence",
        "request_id",
        "route_identity_id",
        "broker_execution_spec_id",
        "session_nonce",
        "payload_sha256",
        "payload_byte_count",
        "payload",
        "formal_locks",
        "outer_attempt_broker_ipc_frame_id",
    }
)


def _parse_frame_body(
    raw: bytes,
    *,
    expected_binding: K7OuterAttemptBrokerIPCBindingV1,
    expected_role: K7OuterAttemptBrokerFrameRoleV1,
) -> K7OuterAttemptBrokerIPCFrameV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC frame is not canonical JSON"
        ) from error
    if type(document) is not dict or frozenset(document) != _FRAME_DOCUMENT_FIELDS:
        _fail("broker IPC frame fields are incomplete or unknown")
    if (
        document["schema"]
        != "acfqp.v075_k7_outer_attempt_broker_ipc_frame.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["outer_attempt_broker_ipc_profile_id"]
        != _OFFICIAL_PROFILE.profile_id
        or document["formal_locks"] != _formal_locks()
    ):
        _fail("broker IPC frame schema or formal locks changed")
    if type(document["sequence"]) is not int:
        _fail("broker IPC frame sequence must be an exact integer")
    try:
        role = K7OuterAttemptBrokerFrameRoleV1(document["frame_role"])
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC frame role is unknown"
        ) from error
    if role is not expected_role or document["sequence"] != _ROLE_INDEX[role]:
        _fail("broker IPC frame is duplicated, omitted, or out of order")
    binding = K7OuterAttemptBrokerIPCBindingV1(
        document["request_id"],
        document["route_identity_id"],
        document["broker_execution_spec_id"],
        document["session_nonce"],
    )
    if binding != expected_binding:
        _fail("broker IPC frame crossed its attempt binding")
    payload, payload_bytes = _canonical_payload(document["payload"])
    if (
        type(document["payload_byte_count"]) is not int
        or document["payload_byte_count"] != len(payload_bytes)
        or type(document["payload_sha256"]) is not str
        or document["payload_sha256"]
        != hashlib.sha256(payload_bytes).hexdigest()
    ):
        _fail("broker IPC payload digest or exact byte count differs")
    frame = K7OuterAttemptBrokerIPCFrameV1(
        _FRAME_ISSUER,
        binding,
        role,
        document["sequence"],
        payload,
    )
    if (
        document["outer_attempt_broker_ipc_frame_id"] != frame.frame_id
        or frame.canonical_bytes != raw
    ):
        _fail("broker IPC frame identity or canonical replay differs")
    return frame


def _parse_header(header: bytes) -> int:
    if type(header) is not bytes or len(header) != FRAME_WIDTH:
        _fail("broker IPC frame header is truncated")
    try:
        size = int(header, 16)
    except ValueError as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC frame header is not hexadecimal"
        ) from error
    if (
        header != f"{size:0{FRAME_WIDTH}x}".encode("ascii")
        or not 0 < size <= MAX_FRAME_BYTES
    ):
        _fail("broker IPC frame header is noncanonical or over cap")
    return size


@dataclass(frozen=True, slots=True)
class V075K7OuterAttemptBrokerIPCTranscriptV1:
    _issuer: InitVar[object]
    binding: K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    frames: tuple[K7OuterAttemptBrokerIPCFrameV1, ...] = field(repr=False)
    stream_sha256: str
    stream_byte_count: int
    _transcript_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TRANSCRIPT_ISSUER
            or type(self.binding) is not K7OuterAttemptBrokerIPCBindingV1
            or type(self.frames) is not tuple
            or tuple(frame.role for frame in self.frames) != FRAME_ROLES
            or any(
                type(frame) is not K7OuterAttemptBrokerIPCFrameV1
                or frame.binding != self.binding
                or frame.sequence != index
                for index, frame in enumerate(self.frames)
            )
        ):
            _fail("broker IPC transcript is caller-minted or incomplete")
        stream = b"".join(frame.framed_bytes for frame in self.frames)
        if (
            type(self.stream_sha256) is not str
            or self.stream_sha256 != hashlib.sha256(stream).hexdigest()
            or type(self.stream_byte_count) is not int
            or self.stream_byte_count != len(stream)
        ):
            _fail("broker IPC transcript stream commitment differs")
        object.__setattr__(
            self,
            "_transcript_id",
            _hash(
                V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_broker_ipc_transcript.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_attempt_broker_ipc_profile_id": _OFFICIAL_PROFILE.profile_id,
            **self.binding.to_document(),
            "frame_roles": [role.value for role in FRAME_ROLES],
            "frame_ids": [frame.frame_id for frame in self.frames],
            "frame_count": len(self.frames),
            "stream_sha256": self.stream_sha256,
            "stream_byte_count": self.stream_byte_count,
            "fixed_sequence_verified": True,
            "canonical_length_prefix_verified": True,
            "role_payload_schema_verified": True,
            "payload_semantics_verified": False,
            "structural_ipc_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def transcript_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN,
            self._payload(),
        ) != self._transcript_id:
            _fail("broker IPC transcript changed after issuance")
        return self._transcript_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "outer_attempt_broker_ipc_transcript_id": self.transcript_id,
        }


def verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
    *,
    raw: bytes,
    expected_binding: K7OuterAttemptBrokerIPCBindingV1,
) -> V075K7OuterAttemptBrokerIPCTranscriptV1:
    """Strictly replay one complete five-frame stream."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_STREAM_BYTES:
        _fail("broker IPC stream is empty, mistyped, or over cap")
    if type(expected_binding) is not K7OuterAttemptBrokerIPCBindingV1:
        _fail("broker IPC verifier requires one exact expected binding")
    offset = 0
    frames: list[K7OuterAttemptBrokerIPCFrameV1] = []
    for role in FRAME_ROLES:
        header_end = offset + FRAME_WIDTH
        if header_end > len(raw):
            _fail("broker IPC stream is missing a required frame header")
        size = _parse_header(raw[offset:header_end])
        frame_end = header_end + size
        if frame_end > len(raw):
            _fail("broker IPC stream contains a truncated frame body")
        frames.append(
            _parse_frame_body(
                raw[header_end:frame_end],
                expected_binding=expected_binding,
                expected_role=role,
            )
        )
        offset = frame_end
    if offset != len(raw):
        _fail("broker IPC stream has a duplicate, extra, or trailing frame")
    return V075K7OuterAttemptBrokerIPCTranscriptV1(
        _TRANSCRIPT_ISSUER,
        expected_binding,
        tuple(frames),
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
    *,
    raw: bytes,
    expected_binding: K7OuterAttemptBrokerIPCBindingV1,
    expected_role: K7OuterAttemptBrokerFrameRoleV1,
) -> K7OuterAttemptBrokerIPCFrameV1:
    """Strictly replay one complete length-prefixed role frame.

    Live role endpoints need the same canonical parser as the final five-frame
    transcript without accepting a caller-supplied sequence or a partial body.
    This additive reader does not change the historical structural authority of
    the V1 frame/transcript schemas.
    """

    if type(raw) is not bytes or len(raw) <= FRAME_WIDTH or len(raw) > (
        FRAME_WIDTH + MAX_FRAME_BYTES
    ):
        _fail("broker IPC single-frame bytes are empty, mistyped, or over cap")
    if type(expected_binding) is not K7OuterAttemptBrokerIPCBindingV1:
        _fail("broker IPC single-frame verifier requires one exact binding")
    try:
        role = K7OuterAttemptBrokerFrameRoleV1(expected_role)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerIPCV1Error(
            "broker IPC single-frame verifier received an unknown role"
        ) from error
    size = _parse_header(raw[:FRAME_WIDTH])
    if len(raw) != FRAME_WIDTH + size:
        _fail("broker IPC single frame is truncated or has trailing bytes")
    return _parse_frame_body(
        raw[FRAME_WIDTH:],
        expected_binding=expected_binding,
        expected_role=role,
    )


__all__ = (
    "FRAME_ROLES",
    "FRAME_WIDTH",
    "K7OuterAttemptBrokerFrameRoleV1",
    "K7OuterAttemptBrokerIPCBindingV1",
    "K7OuterAttemptBrokerIPCFrameV1",
    "K7OuterAttemptBrokerIPCProfileV1",
    "LOCAL_DOMAIN_TAGS",
    "MAX_FRAME_BYTES",
    "MAX_PAYLOAD_BYTES",
    "MAX_STREAM_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7OuterAttemptBrokerIPCV1Error",
    "V075K7OuterAttemptBrokerIPCTranscriptV1",
    "encode_v075_k7_outer_attempt_broker_ipc_frame_v1",
    "encode_v075_k7_outer_attempt_broker_ipc_stream_v1",
    "official_v075_k7_outer_attempt_broker_ipc_profile_v1",
    "verify_v075_k7_outer_attempt_broker_ipc_stream_v1",
    "verify_v075_k7_outer_attempt_broker_ipc_frame_v1",
)
