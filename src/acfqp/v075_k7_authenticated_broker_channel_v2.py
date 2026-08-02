"""Kernel-credential authentication for one K7 broker frame.

The broker receives every worker/business packet on a dedicated
``AF_UNIX/SOCK_SEQPACKET`` endpoint with ``SO_PASSCRED`` enabled.  This module
joins the packet's single ``SCM_CREDENTIALS`` record to an expected native PID
and a live matching pidfd before replaying the canonical five-frame protocol.
It neither launches a process nor treats a partial sequence as a complete
attempt transcript or accounting artifact.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import fcntl
import hashlib
import os
import socket
import stat
import struct
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN,
    V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.13"
PROFILE_KEY = "v075_k7_authenticated_broker_channel_v2"
UCRED_STRUCT = struct.Struct("=3i")
MAX_PIDFDINFO_BYTES = 8192
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN,
        V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("authenticated broker-channel domains are unregistered")

_PROFILE_ISSUER = object()
_FRAME_ISSUER = object()


class V075K7AuthenticatedBrokerChannelV2Error(RuntimeError):
    """The endpoint, pidfd, credentials or canonical frame failed closed."""


def _fail(message: str) -> NoReturn:
    raise V075K7AuthenticatedBrokerChannelV2Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("authenticated broker channel used an undeclared domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "complete_five_frame_transcript_verified": False,
        "direct_children_reaped": False,
        "complete_attempt_memory_window_verified": False,
        "process_launches_counter_authorized": False,
        "shared_resource_receipts_issued": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


def _descriptor_identity(descriptor: int) -> tuple[int, int, int, int, int, int]:
    try:
        status = os.fstat(descriptor)
    except OSError as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated broker descriptor is unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _identity_document(
    identity: tuple[int, int, int, int, int, int]
) -> dict[str, int]:
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "rdev": identity[5],
    }


def _assert_broker_endpoint(endpoint: socket.socket) -> tuple[int, ...]:
    if type(endpoint) is not socket.socket:
        _fail("authenticated receive requires one exact socket object")
    descriptor = endpoint.fileno()
    try:
        identity = _descriptor_identity(descriptor)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        domain = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
        socket_type = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        passcred = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED)
        endpoint.getpeername()
    except OSError as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated broker endpoint cannot be inspected"
        ) from error
    if (
        not stat.S_ISSOCK(identity[2])
        or domain != socket.AF_UNIX
        or socket_type != socket.SOCK_SEQPACKET
        or passcred != 1
        or flags & os.O_NONBLOCK
        or os.get_inheritable(descriptor)
    ):
        _fail("broker endpoint lost blocking SEQPACKET/SO_PASSCRED/CLOEXEC state")
    return identity


def _pid_from_pidfdinfo(pidfd: int) -> int:
    if type(pidfd) is not int or pidfd < 3:
        _fail("authenticated frame requires one live pidfd")
    _descriptor_identity(pidfd)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        info_fd = os.open(f"/proc/self/fdinfo/{pidfd}", flags)
    except OSError as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated frame pidfd info is unavailable"
        ) from error
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                info_fd,
                min(4096, MAX_PIDFDINFO_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_PIDFDINFO_BYTES:
                _fail("pidfd info exceeds its fixed byte cap")
    finally:
        os.close(info_fd)
    try:
        rows = b"".join(chunks).decode("ascii", errors="strict").splitlines()
    except UnicodeError as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "pidfd info is not strict ASCII"
        ) from error
    values = [
        row.split(":", 1)[1].strip()
        for row in rows
        if row.startswith("Pid:")
    ]
    if len(values) != 1 or not values[0].isdigit() or int(values[0]) <= 0:
        _fail("pidfd info lacks one exact positive PID")
    return int(values[0])


@dataclass(frozen=True, slots=True)
class K7AuthenticatedBrokerChannelProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("authenticated broker-channel profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_authenticated_broker_channel_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transport": "AF_UNIX_SOCK_SEQPACKET",
            "broker_receive_so_passcred": True,
            "required_ancillary_records": ["SCM_CREDENTIALS"],
            "ancillary_record_count": 1,
            "so_peercred_substitution_allowed": False,
            "credential_fields": ["pid", "uid", "gid"],
            "pid_join": ["native_expected_pid", "pidfd_info_pid", "scm_pid"],
            "uid_gid_joined_to_broker_effective_identity": True,
            "msg_truncation_allowed": False,
            "canonical_protocol_replay_required": True,
            "partial_sequence_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("authenticated broker-channel profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authenticated_broker_channel_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7AuthenticatedBrokerChannelProfileV2(_PROFILE_ISSUER)


def official_v075_k7_authenticated_broker_channel_profile_v2(
) -> K7AuthenticatedBrokerChannelProfileV2:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7AuthenticatedBrokerFrameV2:
    _issuer: InitVar[object]
    endpoint_identity: tuple[int, int, int, int, int, int]
    pidfd_identity: tuple[int, int, int, int, int, int]
    sender_pid: int
    sender_uid: int
    sender_gid: int
    frame: ipc_v1.K7OuterAttemptBrokerIPCFrameV1 = field(
        repr=False, compare=False
    )
    raw_sha256: str
    raw_byte_count: int
    _observation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _FRAME_ISSUER
            or type(self.endpoint_identity) is not tuple
            or len(self.endpoint_identity) != 6
            or type(self.pidfd_identity) is not tuple
            or len(self.pidfd_identity) != 6
            or type(self.frame) is not ipc_v1.K7OuterAttemptBrokerIPCFrameV1
            or type(self.sender_pid) is not int
            or self.sender_pid <= 0
            or type(self.sender_uid) is not int
            or self.sender_uid < 0
            or type(self.sender_gid) is not int
            or self.sender_gid < 0
            or type(self.raw_sha256) is not str
            or len(self.raw_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.raw_sha256)
            or type(self.raw_byte_count) is not int
            or not 0 < self.raw_byte_count <= ipc_v1.MAX_FRAME_BYTES
        ):
            _fail("authenticated broker frame is caller-minted or malformed")
        object.__setattr__(
            self,
            "_observation_id",
            _hash(
                V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_authenticated_broker_frame.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authenticated_broker_channel_profile_id": _OFFICIAL_PROFILE.profile_id,
            "endpoint_identity": _identity_document(self.endpoint_identity),
            "pidfd_identity": _identity_document(self.pidfd_identity),
            "sender_pid": self.sender_pid,
            "sender_uid": self.sender_uid,
            "sender_gid": self.sender_gid,
            "frame_role": self.frame.role.value,
            "frame_sequence": self.frame.sequence,
            "frame_id": self.frame.frame_id,
            "raw_sha256": self.raw_sha256,
            "raw_byte_count": self.raw_byte_count,
            "scm_credentials_record_count": 1,
            "pid_pidfd_scm_join_verified": True,
            "uid_gid_match_verified": True,
            "message_and_control_not_truncated": True,
            "partial_sequence_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def observation_id(self) -> str:
        if _hash(
            V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN,
            self._payload(),
        ) != self._observation_id:
            _fail("authenticated broker-frame observation changed")
        return self._observation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authenticated_broker_frame_id": self.observation_id,
        }


def receive_v075_k7_authenticated_broker_frame_v2(
    *,
    endpoint: socket.socket,
    expected_pid: int,
    expected_pidfd: int,
    expected_binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    expected_role: ipc_v1.K7OuterAttemptBrokerFrameRoleV1,
    expected_uid: int | None = None,
    expected_gid: int | None = None,
) -> K7AuthenticatedBrokerFrameV2:
    """Receive and authenticate exactly one role-bound canonical packet."""

    if (
        type(expected_pid) is not int
        or expected_pid <= 0
        or type(expected_pidfd) is not int
        or expected_pidfd < 3
        or type(expected_binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
    ):
        _fail("authenticated receive has invalid expected process/binding authority")
    try:
        exact_role = ipc_v1.K7OuterAttemptBrokerFrameRoleV1(expected_role)
    except (TypeError, ValueError) as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated receive expected an unknown frame role"
        ) from error
    uid = os.geteuid() if expected_uid is None else expected_uid
    gid = os.getegid() if expected_gid is None else expected_gid
    if type(uid) is not int or uid < 0 or type(gid) is not int or gid < 0:
        _fail("authenticated receive expected UID/GID is invalid")
    endpoint_identity = _assert_broker_endpoint(endpoint)
    pidfd_identity = _descriptor_identity(expected_pidfd)
    if _pid_from_pidfdinfo(expected_pidfd) != expected_pid:
        _fail("expected native PID does not match its pidfd")
    try:
        raw, ancillary, flags, address = endpoint.recvmsg(
            ipc_v1.MAX_FRAME_BYTES + 1,
            socket.CMSG_SPACE(UCRED_STRUCT.size),
        )
    except OSError as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated broker receive failed"
        ) from error
    if (
        not raw
        or len(raw) > ipc_v1.MAX_FRAME_BYTES
        or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
        or address not in {None, "", b""}
        or len(ancillary) != 1
    ):
        _fail("broker packet or ancillary data is empty, truncated or injected")
    level, kind, credential_raw = ancillary[0]
    if (
        level != socket.SOL_SOCKET
        or kind != socket.SCM_CREDENTIALS
        or len(credential_raw) != UCRED_STRUCT.size
    ):
        _fail("broker packet lacks one exact SCM_CREDENTIALS record")
    sender_pid, sender_uid, sender_gid = UCRED_STRUCT.unpack(credential_raw)
    if (
        sender_pid != expected_pid
        or sender_uid != uid
        or sender_gid != gid
        or _descriptor_identity(endpoint.fileno()) != endpoint_identity
        or _descriptor_identity(expected_pidfd) != pidfd_identity
        or _pid_from_pidfdinfo(expected_pidfd) != expected_pid
    ):
        _fail("SCM credentials, PID, pidfd or endpoint identity crossed")
    try:
        frame = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=raw,
            expected_binding=expected_binding,
            expected_role=exact_role,
        )
    except Exception as error:
        raise V075K7AuthenticatedBrokerChannelV2Error(
            "authenticated packet failed canonical role/binding replay"
        ) from error
    return K7AuthenticatedBrokerFrameV2(
        _FRAME_ISSUER,
        endpoint_identity,
        pidfd_identity,
        sender_pid,
        sender_uid,
        sender_gid,
        frame,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


__all__ = (
    "K7AuthenticatedBrokerChannelProfileV2",
    "K7AuthenticatedBrokerFrameV2",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "UCRED_STRUCT",
    "V075K7AuthenticatedBrokerChannelV2Error",
    "official_v075_k7_authenticated_broker_channel_profile_v2",
    "receive_v075_k7_authenticated_broker_frame_v2",
)
