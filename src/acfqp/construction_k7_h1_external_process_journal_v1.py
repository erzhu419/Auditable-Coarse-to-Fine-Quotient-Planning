"""Guardian-owned external process record journal for the H1 E5B boundary.

This module is deliberately smaller than an E3 V2 executor.  It freezes two
creator channels, persists an intent before each escrow-record permit,
and authenticates one pidfd escrow packet for each of five fixed process
slots.  It supplies construction evidence only: no integrated E5B route,
authenticated supervisor, crash-durable log, process counter, or terminal
authority is issued here.
"""

from __future__ import annotations

import array
import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import select
import signal
import socket
import stat
import struct
import threading
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_h1_domain_registry_extension_v14 as domains_v14
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B1"
PROFILE_KEY = "construction_k7_h1_external_process_journal_v1"
READINESS = "E5B_EXTERNAL_JOURNAL_PREREQUISITE_ONLY"

EXTERNAL_PROCESS_JOURNAL_PRESENT = True
ORDERED_FIVE_SLOT_ESCROW_RECORD_PROTOCOL_PRESENT = True
FIXED_FIVE_SLOT_WRITE_AHEAD_PROTOCOL_PRESENT = False
PIDFD_SCM_ESCROW_PROTOCOL_PRESENT = True
ACTUAL_PROCESS_BIRTH_ORDER_VERIFIED = False
LAUNCH_GATE_PRESENT = False
CGROUP_MEMBERSHIP_VERIFIED = False
SHARED_PID_CELL_GUARDIAN_READ_PRESENT = False
REAL_E3_V2_INTEGRATION_PRESENT = False
AUTHENTICATED_SUPERVISOR_PRESENT = False
MACHINE_CRASH_DURABILITY_PRESENT = False
PID_CELL_UNTAMPERABILITY_PRESENT = False
NORMAL_GUARDIAN_REAP_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

MAX_PACKET_BYTES = 16 * 1024
MAX_FDINFO_BYTES = 16 * 1024
MAX_PROC_STAT_BYTES = 64 * 1024
UCRED_STRUCT = struct.Struct("=3i")
_MSG_CMSG_CLOEXEC = getattr(socket, "MSG_CMSG_CLOEXEC", 0x40000000)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_P_PIDFD = getattr(os, "P_PIDFD", 3)
_PIDFD_OPEN_SYSCALL = {
    "x86_64": 434,
    "amd64": 434,
    "aarch64": 434,
    "arm64": 434,
}
_KCMP_FILE = 0
_SYS_KCMP = {
    "x86_64": 312,
    "amd64": 312,
    "aarch64": 272,
    "arm64": 272,
}.get(platform.machine().lower())
_F_DUPFD_CLOEXEC = getattr(fcntl, "F_DUPFD_CLOEXEC", 1030)
_OS_CLOSE = os.close
_FCNTL_FCNTL = fcntl.fcntl
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.syscall.restype = ctypes.c_long

_PROFILE_ISSUER = object()
_CHANNEL_ISSUER = object()
_RECORD_ISSUER = object()
_JOURNAL_ISSUER = object()
_FORK_LOCK = threading.RLock()
_LIVE_JOURNALS: dict[int, "H1ExternalProcessJournalV1"] = {}


class ExternalProcessSlotV1(str, Enum):
    SUPERVISOR = "SUPERVISOR"
    PIDFD_PROBE = "PIDFD_PROBE"
    BROKER = "BROKER"
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


SLOT_ORDER: tuple[ExternalProcessSlotV1, ...] = (
    ExternalProcessSlotV1.SUPERVISOR,
    ExternalProcessSlotV1.PIDFD_PROBE,
    ExternalProcessSlotV1.BROKER,
    ExternalProcessSlotV1.WORKER,
    ExternalProcessSlotV1.BUSINESS,
)


class CreatorChannelKindV1(str, Enum):
    SUPERVISOR_CREATOR = "SUPERVISOR_CREATOR"
    BROKER_CREATOR = "BROKER_CREATOR"


CREATOR_FOR_SLOT: Mapping[ExternalProcessSlotV1, CreatorChannelKindV1] = {
    ExternalProcessSlotV1.SUPERVISOR: CreatorChannelKindV1.SUPERVISOR_CREATOR,
    ExternalProcessSlotV1.PIDFD_PROBE: CreatorChannelKindV1.SUPERVISOR_CREATOR,
    ExternalProcessSlotV1.BROKER: CreatorChannelKindV1.SUPERVISOR_CREATOR,
    ExternalProcessSlotV1.WORKER: CreatorChannelKindV1.BROKER_CREATOR,
    ExternalProcessSlotV1.BUSINESS: CreatorChannelKindV1.BROKER_CREATOR,
}


class ExternalProcessJournalStageV1(str, Enum):
    EMPTY = "EMPTY"
    INTENT_PREPARED = "INTENT_PREPARED"
    PERMIT_ISSUED = "PERMIT_ISSUED"
    PIDFD_ESCROWED = "PIDFD_ESCROWED"
    ACK_PERSISTED_SEND_FAILED = "ACK_PERSISTED_SEND_FAILED"
    ACK_PREPARED_AND_SENT = "ACK_PREPARED_AND_SENT"
    RELEASE_PREPARED_UNSENT = "RELEASE_PREPARED_UNSENT"
    RELEASE_SENT_AUTHORIZATION_PERSIST_FAILED = (
        "RELEASE_SENT_AUTHORIZATION_PERSIST_FAILED"
    )
    CREATOR_RELEASE_AUTHORIZED = "CREATOR_RELEASE_AUTHORIZED"
    DEATH_READINESS_OBSERVED = "DEATH_READINESS_OBSERVED"
    CREATOR_REAP_REPORTED = "CREATOR_REAP_REPORTED"
    GUARDIAN_DIRECT_REAP_CONSUMED = "GUARDIAN_DIRECT_REAP_CONSUMED"


class ConstructionK7H1ExternalProcessJournalV1Error(RuntimeError):
    """The external journal, channel, ordering, or pidfd join failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ExternalProcessJournalV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            f"{label} is not one exact lowercase content ID"
        ) from error


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v14.extension_content_id_v14(domain, payload)


def _locked_claims() -> dict[str, Any]:
    return {
        "real_e3_v2_integration_present": False,
        "authenticated_supervisor_present": False,
        "machine_crash_durability_present": False,
        "pid_cell_untamperability_present": False,
        "shared_pid_cell_guardian_read_present": False,
        "cgroup_membership_verified": False,
        "actual_process_birth_order_verified": False,
        "launch_gate_present": False,
        "normal_guardian_reap_present": False,
        "creator_relationship_proven_by_scm_credentials": False,
        "complete_attempt_process_window_present": False,
        "closed_record_disk_replay_is_authority": False,
        "close_retry_same_ofd_witness_present": True,
        "close_retry_inode_identity_only": False,
        "fq11_counter_completeness_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "construction_only": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def _identity(descriptor: int) -> tuple[int, int, int, int, int, int]:
    if type(descriptor) is not int or descriptor < 0:
        _fail("descriptor is not one exact nonnegative integer")
    try:
        status = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "descriptor identity is unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _identity_document(identity: Sequence[int]) -> dict[str, int]:
    if type(identity) not in {tuple, list} or len(identity) != 6:
        _fail("native identity is malformed")
    return {
        "device": int(identity[0]),
        "inode": int(identity[1]),
        "mode": int(identity[2]),
        "owner_uid": int(identity[3]),
        "owner_gid": int(identity[4]),
        "rdev": int(identity[5]),
    }


def _same_open_file_description_for_close(left: int, right: int) -> bool:
    """Use Linux KCMP_FILE; inode-like metadata is not OFD identity."""

    if _SYS_KCMP is None:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "close retry lacks a registered kcmp syscall"
        )
    ctypes.set_errno(0)
    result = int(
        _LIBC.syscall(
            ctypes.c_long(_SYS_KCMP),
            ctypes.c_int(os.getpid()),
            ctypes.c_int(os.getpid()),
            ctypes.c_int(_KCMP_FILE),
            ctypes.c_ulong(left),
            ctypes.c_ulong(right),
        )
    )
    if result == 0:
        return True
    if result > 0:
        return False
    code = ctypes.get_errno()
    if code == errno.EBADF:
        return False
    raise ConstructionK7H1ExternalProcessJournalV1Error(
        "retained close-retry OFDs could not be compared"
    ) from OSError(code, os.strerror(code))


def _assert_endpoint(endpoint: socket.socket) -> tuple[int, int, int, int, int, int]:
    if type(endpoint) is not socket.socket:
        _fail("creator channel requires one exact socket object")
    descriptor = endpoint.fileno()
    try:
        identity = _identity(descriptor)
        domain = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
        socket_type = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        passcred = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        endpoint.getpeername()
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator channel cannot be inspected"
        ) from error
    if (
        not stat.S_ISSOCK(identity[2])
        or domain != socket.AF_UNIX
        or socket_type != socket.SOCK_SEQPACKET
        or passcred != 1
        or flags & os.O_NONBLOCK
        or os.get_inheritable(descriptor)
    ):
        _fail("creator channel lost blocking SEQPACKET/SO_PASSCRED/CLOEXEC state")
    return identity


def _read_bounded_proc(path: str, cap: int, label: str) -> bytes:
    flags = os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            f"{label} is unavailable"
        ) from error
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(4096, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                _fail(f"{label} exceeds its fixed byte cap")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _pidfd_pid(pidfd: int) -> int:
    if type(pidfd) is not int or pidfd < 3:
        _fail("pidfd is not one exact live descriptor")
    _identity(pidfd)
    raw = _read_bounded_proc(
        f"/proc/self/fdinfo/{pidfd}", MAX_FDINFO_BYTES, "pidfd fdinfo"
    )
    try:
        rows = raw.decode("ascii", errors="strict").splitlines()
    except UnicodeError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "pidfd fdinfo is not strict ASCII"
        ) from error
    values = [row.split(":", 1)[1].strip() for row in rows if row.startswith("Pid:")]
    if len(values) != 1 or not values[0].isdigit() or int(values[0]) <= 0:
        _fail("pidfd fdinfo lacks one exact positive PID")
    return int(values[0])


def _pidfd_open(pid: int) -> int:
    """Open a pidfd without depending on the interpreter's optional wrapper."""

    if type(pid) is not int or pid <= 0:
        _fail("pidfd_open PID is not one exact positive integer")
    function = getattr(os, "pidfd_open", None)
    if callable(function):
        return int(function(pid, 0))
    number = _PIDFD_OPEN_SYSCALL.get(platform.machine().lower())
    if number is None:
        raise OSError(errno.ENOSYS, "pidfd_open is unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = int(
        libc.syscall(ctypes.c_long(number), ctypes.c_int(pid), ctypes.c_uint(0))
    )
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return result


def _process_start_ticks(pid: int) -> int:
    if type(pid) is not int or pid <= 0:
        _fail("process PID is not one exact positive integer")
    raw = _read_bounded_proc(f"/proc/{pid}/stat", MAX_PROC_STAT_BYTES, "process stat")
    try:
        text = raw.decode("ascii", errors="strict").strip()
    except UnicodeError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "process stat is not strict ASCII"
        ) from error
    close = text.rfind(")")
    if close <= 0:
        _fail("process stat comm field is malformed")
    suffix = text[close + 1 :].strip().split()
    # suffix[0] is field 3 (state), therefore suffix[19] is field 22.
    if len(suffix) <= 19 or not suffix[19].isdigit() or int(suffix[19]) <= 0:
        _fail("process stat lacks one exact positive start time")
    return int(suffix[19])


def _profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_external_process_journal_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "ordered_escrow_record_slot_order": [slot.value for slot in SLOT_ORDER],
        "fixed_slot_order_is_process_birth_order": False,
        "creator_channels": [kind.value for kind in CreatorChannelKindV1],
        "creator_channel_for_slot": {
            slot.value: CREATOR_FOR_SLOT[slot].value for slot in SLOT_ORDER
        },
        "supervisor_channel_pid_binding": (
            "SUPERVISOR_SELF_ESCROW_THEN_FIXED_FOR_PIDFD_PROBE_AND_BROKER"
        ),
        "broker_channel_pid_binding": "BROKER_ESCROW_PID_THEN_FIXED_FOR_WORKER_AND_BUSINESS",
        "intent_must_be_persisted_before_escrow_record_permit": True,
        "permit_is_a_real_launch_gate": False,
        "post_permit_pid_birth_verified": False,
        "probe_creator_reap_required_before_broker_record": True,
        "worker_creator_reap_required_before_business_record": True,
        "pidfd_rights_count": 1,
        "scm_credentials_count": 1,
        "escrow_join_fields": [
            "slot",
            "intent_id",
            "permit_id",
            "launch_identity_id",
            "cgroup_identity_id",
            "creator_channel_binding_id",
            "fdinfo_pid",
            "shared_pid_cell_observed_pid",
            "process_start_ticks",
            "sender_pid",
            "sender_uid",
            "sender_gid",
        ],
        "creator_release_requires_persisted_and_sent_ack": True,
        "pidfd_poll_death_observation_separate_from_creator_reap_report": True,
        "creator_reap_report_authenticated_by_scm_sender": True,
        "creator_reap_report_is_guardian_independent_reap_proof": False,
        "cgroup_identity_is_opaque_binding": True,
        "shared_pid_cell_value_is_sender_observation": True,
        "filesystem_records_fsynced_without_machine_crash_durability_claim": True,
        **_locked_claims(),
    }


@dataclass(frozen=True, slots=True)
class H1ExternalProcessJournalProfileV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("external process journal profile is caller-minted")
        try:
            document = loads_canonical_json(self.canonical_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "external process journal profile is not canonical"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("external process journal profile is not one canonical object")
        object.__setattr__(
            self,
            "profile_id",
            _domain_id(
                domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_PROFILE_V1_DOMAIN,
                document,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        assert type(document) is dict
        return {**document, "external_process_journal_profile_id": self.profile_id}


_PROFILE = H1ExternalProcessJournalProfileV1(
    _PROFILE_ISSUER, canonical_json_bytes(_profile_payload())
)


def official_h1_external_process_journal_profile_v1(
) -> H1ExternalProcessJournalProfileV1:
    return _PROFILE


@dataclass(frozen=True, slots=True, eq=False)
class H1ExternalProcessCreatorChannelV1:
    _issuer: InitVar[object]
    kind: CreatorChannelKindV1
    channel_identity_id: str
    expected_sender_uid: int
    expected_sender_gid: int
    endpoint_identity: tuple[int, int, int, int, int, int]
    _endpoint: socket.socket = field(repr=False, compare=False)
    _owner_pid: int = field(repr=False, compare=False)
    binding_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CHANNEL_ISSUER
            or type(self.kind) is not CreatorChannelKindV1
            or type(self.expected_sender_uid) is not int
            or self.expected_sender_uid < 0
            or type(self.expected_sender_gid) is not int
            or self.expected_sender_gid < 0
            or self._owner_pid != os.getpid()
            or type(self.endpoint_identity) is not tuple
            or len(self.endpoint_identity) != 6
        ):
            _fail("creator channel binding is caller-minted or malformed")
        object.__setattr__(self, "channel_identity_id", _cid(self.channel_identity_id, "channel identity"))
        object.__setattr__(
            self,
            "binding_id",
            _domain_id(
                domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CREATOR_CHANNEL_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _assert_live(self) -> None:
        if self._owner_pid != os.getpid() or _assert_endpoint(self._endpoint) != self.endpoint_identity:
            _fail("creator channel binding crossed process or endpoint identity")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_external_process_creator_channel.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "external_process_journal_profile_id": _PROFILE.profile_id,
            "creator_channel_kind": self.kind.value,
            "channel_identity_id": self.channel_identity_id,
            "endpoint_identity": _identity_document(self.endpoint_identity),
            "expected_sender_uid": self.expected_sender_uid,
            "expected_sender_gid": self.expected_sender_gid,
            "sender_pid_binding": "DERIVED_FROM_EARLIER_ESCROW_SLOT",
            "so_passcred_required": True,
            **_locked_claims(),
        }

    def to_document(self) -> dict[str, Any]:
        self._assert_live()
        return {**self._payload(), "creator_channel_binding_id": self.binding_id}


def prebind_h1_external_process_creator_channel_v1(
    *,
    kind: CreatorChannelKindV1,
    channel_identity_id: str,
    endpoint: socket.socket,
    expected_sender_uid: int | None = None,
    expected_sender_gid: int | None = None,
) -> H1ExternalProcessCreatorChannelV1:
    try:
        exact_kind = CreatorChannelKindV1(kind)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "unknown creator channel kind"
        ) from error
    uid = os.geteuid() if expected_sender_uid is None else expected_sender_uid
    gid = os.getegid() if expected_sender_gid is None else expected_sender_gid
    identity = _assert_endpoint(endpoint)
    return H1ExternalProcessCreatorChannelV1(
        _CHANNEL_ISSUER,
        exact_kind,
        _cid(channel_identity_id, "channel identity"),
        uid,
        gid,
        identity,
        endpoint,
        os.getpid(),
    )


@dataclass(frozen=True, slots=True)
class H1ExternalProcessJournalRecordV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    domain: str
    id_field: str
    record_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECORD_ISSUER:
            _fail("external process journal record is caller-minted")
        try:
            document = loads_canonical_json(self.canonical_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "external process journal record is not canonical"
            ) from error
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get(self.id_field) != self.record_id
        ):
            _fail("external process journal record bytes or ID changed")
        payload = dict(document)
        supplied = _cid(payload.pop(self.id_field, None), "journal record")
        try:
            recomputed = _domain_id(self.domain, payload)
        except ValueError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "external process journal record uses an unregistered domain"
            ) from error
        if supplied != recomputed:
            _fail("external process journal record content ID changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        assert type(document) is dict
        payload = dict(document)
        supplied = _cid(payload.pop(self.id_field, None), "journal record")
        if _domain_id(self.domain, payload) != supplied or supplied != self.record_id:
            _fail("external process journal record changed after issuance")
        return dict(document)


@dataclass(slots=True)
class _SlotStateV1:
    slot: ExternalProcessSlotV1
    stage: ExternalProcessJournalStageV1 = ExternalProcessJournalStageV1.EMPTY
    intent: H1ExternalProcessJournalRecordV1 | None = None
    permit: H1ExternalProcessJournalRecordV1 | None = None
    receipt: H1ExternalProcessJournalRecordV1 | None = None
    ack: H1ExternalProcessJournalRecordV1 | None = None
    release_preparation: H1ExternalProcessJournalRecordV1 | None = None
    release_authorization: H1ExternalProcessJournalRecordV1 | None = None
    death: H1ExternalProcessJournalRecordV1 | None = None
    reap: H1ExternalProcessJournalRecordV1 | None = None
    pidfd: int | None = None
    pidfd_identity: tuple[int, int, int, int, int, int] | None = None
    observed_pid: int | None = None
    process_start_ticks: int | None = None


@dataclass(frozen=True, slots=True)
class _CloseQuarantineEntryV1:
    """One private original-OFD witness and its optional canonical number."""

    canonical_descriptor: int | None
    expected_identity: tuple[int, int, int, int, int, int]
    witness_descriptor: int


def _verify_content_document(
    document: Any, *, domain: str, id_field: str, label: str
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = _cid(payload.pop(id_field, None), label)
    if _domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return payload


def _exact_write(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        try:
            written = os.write(descriptor, raw[offset:])
        except InterruptedError:
            continue
        if written <= 0:
            _fail("journal record write made no progress")
        offset += written


class H1ExternalProcessJournalV1:
    """Process/thread-bound mutable guardian protocol; never serializable authority."""

    __slots__ = (
        "_owner_pid",
        "_owner_thread",
        "_directory_path",
        "_directory_fd",
        "_directory_identity",
        "_channels",
        "_attempt_identity_id",
        "_route_attempt_id",
        "_build_epoch_id",
        "_genesis",
        "_records",
        "_filenames",
        "_record_file_facts",
        "_record_fds",
        "_previous_record_id",
        "_sequence",
        "_next_slot_index",
        "_states",
        "_creator_pids",
        "_closed",
        "_poisoned",
        "_fork_poison_reason",
        "_close_quarantine",
        "_closure",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        directory_path: Path,
        directory_fd: int,
        directory_identity: tuple[int, int, int, int, int, int],
        channels: Mapping[CreatorChannelKindV1, H1ExternalProcessCreatorChannelV1],
        attempt_identity_id: str,
        route_attempt_id: str,
        build_epoch_id: str,
    ) -> None:
        if _issuer is not _JOURNAL_ISSUER:
            _fail("external process journal is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._directory_path = directory_path
        self._directory_fd = directory_fd
        self._directory_identity = directory_identity
        self._channels = dict(channels)
        self._attempt_identity_id = _cid(attempt_identity_id, "attempt identity")
        self._route_attempt_id = _cid(route_attempt_id, "route attempt")
        self._build_epoch_id = _cid(build_epoch_id, "BuildEpoch")
        self._records: list[H1ExternalProcessJournalRecordV1] = []
        self._filenames: set[str] = set()
        self._record_file_facts: dict[
            str, tuple[int, int, int, int, int, int, int, str]
        ] = {}
        self._record_fds: dict[str, int] = {}
        self._previous_record_id: str | None = None
        self._sequence = 0
        self._next_slot_index = 0
        self._states = {slot: _SlotStateV1(slot) for slot in SLOT_ORDER}
        self._creator_pids: dict[CreatorChannelKindV1, int | None] = {
            kind: None for kind in CreatorChannelKindV1
        }
        self._closed = False
        self._poisoned = False
        self._fork_poison_reason: str | None = None
        self._close_quarantine: dict[int, _CloseQuarantineEntryV1] = {}
        self._closure: H1ExternalProcessJournalRecordV1 | None = None
        genesis_payload = {
            "schema": "acfqp.k7_h1_external_process_journal_genesis.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "external_process_journal_profile_id": _PROFILE.profile_id,
            "attempt_identity_id": self._attempt_identity_id,
            "route_attempt_id": self._route_attempt_id,
            "BuildEpoch_id": self._build_epoch_id,
            "ordered_escrow_record_slot_order": [slot.value for slot in SLOT_ORDER],
            "fixed_slot_order_is_process_birth_order": False,
            "creator_channels": [
                self._channels[kind].to_document() for kind in CreatorChannelKindV1
            ],
            "sequence": 0,
            "previous_record_id": {"kind": "GENESIS", "reason": "NO_PREDECESSOR"},
            **_locked_claims(),
        }
        with _FORK_LOCK:
            _LIVE_JOURNALS[id(self)] = self
        try:
            self._genesis = self._persist_object(
                domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_GENESIS_V1_DOMAIN,
                id_field="external_process_journal_genesis_id",
                payload=genesis_payload,
                event_label="GENESIS",
            )
        except BaseException:
            self._poison_after_fork_child()
            with _FORK_LOCK:
                _LIVE_JOURNALS.pop(id(self), None)
            raise

    def _assert_current(self, *, allow_closed: bool = False) -> None:
        if (
            self._owner_pid != os.getpid()
            or self._owner_thread is not threading.current_thread()
        ):
            _fail("external process journal crossed its guardian process/thread")
        if self._poisoned:
            _fail("external process journal is poisoned")
        if self._closed:
            if allow_closed:
                return
            _fail("external process journal is closed")
        try:
            current_path = os.stat(self._directory_path, follow_symlinks=False)
        except OSError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "journal directory path disappeared"
            ) from error
        if (
            _identity(self._directory_fd) != self._directory_identity
            or (current_path.st_dev, current_path.st_ino) != self._directory_identity[:2]
            or set(os.listdir(self._directory_fd)) != self._filenames
        ):
            _fail("journal directory identity or exact inventory changed")
        if set(self._record_fds) != self._filenames:
            _fail("journal retained-record FD inventory changed")
        for filename, expected in self._record_file_facts.items():
            descriptor = self._record_fds.get(filename, -1)
            try:
                status = os.fstat(descriptor)
                if fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0:
                    _fail("retained journal record FD lost CLOEXEC")
                initial_metadata = (
                    status.st_dev,
                    status.st_ino,
                    status.st_mode,
                    status.st_uid,
                    status.st_gid,
                    status.st_nlink,
                    status.st_size,
                )
                if initial_metadata != expected[:7]:
                    _fail("persisted journal record identity or extent changed")
                chunks: list[bytes] = []
                remaining = expected[6]
                offset = 0
                while remaining:
                    chunk = os.pread(descriptor, min(4096, remaining), offset)
                    if not chunk:
                        _fail("persisted journal record ended during revalidation")
                    chunks.append(chunk)
                    remaining -= len(chunk)
                    offset += len(chunk)
                if os.pread(descriptor, 1, offset):
                    _fail("persisted journal record grew during revalidation")
                final_status = os.fstat(descriptor)
                observed = (
                    final_status.st_dev,
                    final_status.st_ino,
                    final_status.st_mode,
                    final_status.st_uid,
                    final_status.st_gid,
                    final_status.st_nlink,
                    final_status.st_size,
                    hashlib.sha256(b"".join(chunks)).hexdigest(),
                )
                named = os.stat(
                    filename,
                    dir_fd=self._directory_fd,
                    follow_symlinks=False,
                )
                if observed != expected or (named.st_dev, named.st_ino) != expected[:2]:
                    _fail("persisted journal record identity or bytes changed")
            except OSError as error:
                raise ConstructionK7H1ExternalProcessJournalV1Error(
                    "persisted journal record cannot be revalidated"
                ) from error
        for channel in self._channels.values():
            channel._assert_live()  # noqa: SLF001

    def _persist_object(
        self,
        *,
        domain: str,
        id_field: str,
        payload: Mapping[str, Any],
        event_label: str,
    ) -> H1ExternalProcessJournalRecordV1:
        with _FORK_LOCK:
            return self._persist_object_under_fork_barrier(
                domain=domain,
                id_field=id_field,
                payload=payload,
                event_label=event_label,
            )

    def _persist_object_under_fork_barrier(
        self,
        *,
        domain: str,
        id_field: str,
        payload: Mapping[str, Any],
        event_label: str,
    ) -> H1ExternalProcessJournalRecordV1:
        document = dict(payload)
        record_id = _domain_id(domain, document)
        document[id_field] = record_id
        raw = canonical_json_bytes(document)
        filename = f"{self._sequence:06d}_{event_label}_{record_id}.json"
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW
        descriptor = -1
        try:
            descriptor = os.open(filename, flags, 0o400, dir_fd=self._directory_fd)
            _exact_write(descriptor, raw)
            os.fsync(descriptor)
            status = os.fstat(descriptor)
            if (
                not stat.S_ISREG(status.st_mode)
                or stat.S_IMODE(status.st_mode) != 0o400
                or status.st_nlink != 1
                or status.st_size != len(raw)
            ):
                _fail("persisted journal record extent or mode changed")
            replay = os.pread(descriptor, len(raw) + 1, 0)
            if replay != raw:
                _fail("persisted journal record bytes changed")
            os.fsync(self._directory_fd)
            final_status = os.fstat(descriptor)
            named = os.stat(
                filename,
                dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
            if (
                (
                    final_status.st_dev,
                    final_status.st_ino,
                    final_status.st_mode,
                    final_status.st_uid,
                    final_status.st_gid,
                    final_status.st_nlink,
                    final_status.st_size,
                )
                != (
                    status.st_dev,
                    status.st_ino,
                    status.st_mode,
                    status.st_uid,
                    status.st_gid,
                    status.st_nlink,
                    status.st_size,
                )
                or (named.st_dev, named.st_ino) != (status.st_dev, status.st_ino)
                or set(os.listdir(self._directory_fd)) != self._filenames | {filename}
            ):
                _fail("new journal record changed before persist freeze")
        except BaseException:
            self._poisoned = True
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
        self._filenames.add(filename)
        self._record_file_facts[filename] = (
            status.st_dev,
            status.st_ino,
            status.st_mode,
            status.st_uid,
            status.st_gid,
            status.st_nlink,
            status.st_size,
            hashlib.sha256(raw).hexdigest(),
        )
        self._record_fds[filename] = descriptor
        record = H1ExternalProcessJournalRecordV1(
            _RECORD_ISSUER, raw, domain, id_field, record_id
        )
        self._records.append(record)
        self._previous_record_id = record_id
        self._sequence += 1
        try:
            self._assert_current()
        except BaseException:
            self._poisoned = True
            raise
        return record

    def _event_payload(self, schema: str) -> dict[str, Any]:
        assert self._previous_record_id is not None
        return {
            "schema": schema,
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "external_process_journal_profile_id": _PROFILE.profile_id,
            "external_process_journal_genesis_id": self._genesis.record_id,
            "attempt_identity_id": self._attempt_identity_id,
            "route_attempt_id": self._route_attempt_id,
            "BuildEpoch_id": self._build_epoch_id,
            "sequence": self._sequence,
            "previous_record_id": self._previous_record_id,
            **_locked_claims(),
        }

    @property
    def genesis(self) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        return self._genesis

    def records(self) -> tuple[H1ExternalProcessJournalRecordV1, ...]:
        self._assert_current(allow_closed=True)
        return tuple(self._records)

    def _close_or_quarantine(
        self,
        descriptor: int,
        identity: tuple[int, int, int, int, int, int],
    ) -> None:
        """Close one owned FD with a pre-close same-OFD retry witness."""

        if descriptor < 0:
            return
        witness = -1
        try:
            witness = int(
                _FCNTL_FCNTL(descriptor, _F_DUPFD_CLOEXEC, 3)
            )
            if (
                witness == descriptor
                or os.get_inheritable(witness)
                or _identity(witness) != identity
                or not _same_open_file_description_for_close(descriptor, witness)
            ):
                _fail("close retry witness is not one distinct same-OFD duplicate")
        except BaseException:
            if witness >= 0:
                try:
                    _OS_CLOSE(witness)
                except OSError:
                    pass
            raise
        entry = _CloseQuarantineEntryV1(descriptor, identity, witness)
        # Publish both numbers before the fallible close.  This also makes a
        # fork triggered inside a test/fault hook visible to the at-fork child
        # raw-close inventory despite the re-entrant process-wide RLock.
        self._close_quarantine[witness] = entry
        try:
            os.close(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                try:
                    if _same_open_file_description_for_close(descriptor, witness):
                        return
                except ConstructionK7H1ExternalProcessJournalV1Error:
                    # Without an OFD decision neither numeric descriptor may
                    # be retried; preserve both behind the fork barrier.
                    return
            # EBADF, close-then-raise, and same-target replacement all retire
            # the ambiguous canonical number without ever closing it again.
        self._close_final_witness_or_quarantine(entry)

    def _close_final_witness_or_quarantine(
        self, entry: _CloseQuarantineEntryV1
    ) -> None:
        """Bounded final-witness close; never mint a nested witness."""

        witness = entry.witness_descriptor
        witness_only = _CloseQuarantineEntryV1(
            None, entry.expected_identity, witness
        )
        try:
            _OS_CLOSE(witness)
        except OSError as error:
            if error.errno == errno.EBADF:
                self._close_quarantine.pop(witness, None)
                return
            try:
                current = _identity(witness)
            except ConstructionK7H1ExternalProcessJournalV1Error:
                self._close_quarantine.pop(witness, None)
                return
            if current != entry.expected_identity:
                _fail("private close witness changed identity")
            self._close_quarantine[witness] = witness_only
            return
        self._close_quarantine.pop(witness, None)

    def _retire_pidfd(self, state: _SlotStateV1) -> None:
        with _FORK_LOCK:
            if state.pidfd is None or state.pidfd_identity is None:
                return
            descriptor = state.pidfd
            identity = state.pidfd_identity
            state.pidfd = None
            self._close_or_quarantine(descriptor, identity)

    def close_quarantine_count(self) -> int:
        if self._owner_pid != os.getpid() or self._owner_thread is not threading.current_thread():
            _fail("close quarantine crossed its guardian process/thread")
        return len(self._close_quarantine)

    def retry_quarantined_close(self) -> int:
        """Retry only a kcmp-proven original OFD, never a numeric replacement."""

        with _FORK_LOCK:
            return self._retry_quarantined_close_under_fork_barrier()

    def _retry_quarantined_close_under_fork_barrier(self) -> int:

        if self._owner_pid != os.getpid() or self._owner_thread is not threading.current_thread():
            _fail("close-only retry crossed its guardian process/thread")
        for witness, entry in tuple(self._close_quarantine.items()):
            if witness != entry.witness_descriptor:
                _fail("close quarantine witness registry changed")
            try:
                witness_identity = _identity(witness)
            except ConstructionK7H1ExternalProcessJournalV1Error:
                _fail("private close witness disappeared before close-only retry")
            if witness_identity != entry.expected_identity:
                _fail("private close witness changed before close-only retry")
            descriptor = entry.canonical_descriptor
            if descriptor is not None:
                try:
                    same_ofd = _same_open_file_description_for_close(
                        descriptor, witness
                    )
                except ConstructionK7H1ExternalProcessJournalV1Error:
                    continue
                if same_ofd:
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        if error.errno != errno.EBADF:
                            try:
                                if _same_open_file_description_for_close(
                                    descriptor, witness
                                ):
                                    continue
                            except ConstructionK7H1ExternalProcessJournalV1Error:
                                continue
                # If kcmp says distinct before or after close, the canonical
                # number is a replacement (or already dead).  Never close it.
                self._close_quarantine[witness] = _CloseQuarantineEntryV1(
                    None, entry.expected_identity, witness
                )
            self._close_final_witness_or_quarantine(
                self._close_quarantine[witness]
            )
        if self._closed and not self._close_quarantine:
            with _FORK_LOCK:
                _LIVE_JOURNALS.pop(id(self), None)
        return len(self._close_quarantine)

    def _poison_after_fork_child(self) -> None:
        """Raw-close guardian-owned copies in a fork child and poison the copy."""

        descriptors: set[int] = set()
        for entry in self._close_quarantine.values():
            descriptors.add(entry.witness_descriptor)
            if entry.canonical_descriptor is not None:
                descriptors.add(entry.canonical_descriptor)
        for state in self._states.values():
            if state.pidfd is not None:
                descriptors.add(state.pidfd)
                state.pidfd = None
        descriptors.update(self._record_fds.values())
        self._record_fds.clear()
        if self._directory_fd >= 0:
            descriptors.add(self._directory_fd)
            self._directory_fd = -1
        for channel in self._channels.values():
            endpoint = channel._endpoint  # noqa: SLF001
            if endpoint.fileno() >= 0:
                descriptors.add(endpoint.detach())
        for descriptor in sorted(descriptors, reverse=True):
            try:
                _OS_CLOSE(descriptor)
            except OSError:
                pass
        self._close_quarantine.clear()
        self._poisoned = True
        self._fork_poison_reason = "GUARDIAN_JOURNAL_COPY_IN_FORK_CHILD"

    def prepare_intent(
        self,
        *,
        slot: ExternalProcessSlotV1,
        launch_identity_id: str,
        cgroup_identity_id: str,
        shared_pid_cell_identity_id: str,
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        try:
            exact_slot = ExternalProcessSlotV1(slot)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "unknown external process slot"
            ) from error
        if self._next_slot_index >= len(SLOT_ORDER) or SLOT_ORDER[self._next_slot_index] is not exact_slot:
            _fail("external process intent crossed the ordered five-slot record protocol")
        completed_stages = {
            ExternalProcessJournalStageV1.CREATOR_RELEASE_AUTHORIZED,
            ExternalProcessJournalStageV1.CREATOR_REAP_REPORTED,
            ExternalProcessJournalStageV1.GUARDIAN_DIRECT_REAP_CONSUMED,
        }
        if (
            self._next_slot_index
            and self._states[SLOT_ORDER[self._next_slot_index - 1]].stage
            not in completed_stages
        ):
            _fail("previous slot lacks its required escrow/reap record boundary")
        if (
            exact_slot is ExternalProcessSlotV1.BROKER
            and self._states[ExternalProcessSlotV1.PIDFD_PROBE].stage
            is not ExternalProcessJournalStageV1.CREATOR_REAP_REPORTED
        ):
            _fail("BROKER record requires PIDFD_PROBE death and creator reap report")
        if (
            exact_slot is ExternalProcessSlotV1.BUSINESS
            and self._states[ExternalProcessSlotV1.WORKER].stage
            is not ExternalProcessJournalStageV1.CREATOR_REAP_REPORTED
        ):
            _fail("BUSINESS record requires WORKER death and creator reap report")
        state = self._states[exact_slot]
        if state.stage is not ExternalProcessJournalStageV1.EMPTY:
            _fail("external process slot intent is duplicate")
        channel = self._channels[CREATOR_FOR_SLOT[exact_slot]]
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_intent.v1"),
            "event_kind": "ESCROW_RECORD_INTENT_PREPARED",
            "slot": exact_slot.value,
            "slot_ordinal": self._next_slot_index + 1,
            "creator_channel_binding_id": channel.binding_id,
            "launch_identity_id": _cid(launch_identity_id, "opaque launch identity"),
            "cgroup_identity_id": _cid(cgroup_identity_id, "opaque cgroup identity"),
            "shared_pid_cell_identity_id": _cid(
                shared_pid_cell_identity_id, "shared PID cell identity"
            ),
            "escrow_record_permit_issued": False,
            "intent_persisted_before_escrow_record_permit": True,
            "permit_is_a_real_launch_gate": False,
            "process_birth_after_permit_verified": False,
            "cgroup_membership_verified": False,
            "shared_pid_cell_guardian_read_present": False,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_INTENT_V1_DOMAIN,
            id_field="external_process_intent_id",
            payload=payload,
            event_label=f"{exact_slot.value}_INTENT_PREPARED",
        )
        state.intent = record
        state.stage = ExternalProcessJournalStageV1.INTENT_PREPARED
        return record

    def issue_permit(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        state = self._states[exact_slot]
        if state.stage is not ExternalProcessJournalStageV1.INTENT_PREPARED or state.intent is None:
            _fail("slot permit requires one already-persisted INTENT_PREPARED")
        intent = state.intent.to_document()
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_permit.v1"),
            "event_kind": "ESCROW_RECORD_SLOT_PERMIT_ISSUED",
            "slot": exact_slot.value,
            "slot_ordinal": SLOT_ORDER.index(exact_slot) + 1,
            "external_process_intent_id": state.intent.record_id,
            "creator_channel_binding_id": intent["creator_channel_binding_id"],
            "launch_identity_id": intent["launch_identity_id"],
            "cgroup_identity_id": intent["cgroup_identity_id"],
            "shared_pid_cell_identity_id": intent["shared_pid_cell_identity_id"],
            "intent_record_sequence": intent["sequence"],
            "permit_record_sequence": self._sequence,
            "intent_persistence_precedes_permit": intent["sequence"] < self._sequence,
            "permit_is_a_real_launch_gate": False,
            "process_birth_after_permit_verified": False,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_PERMIT_V1_DOMAIN,
            id_field="external_process_permit_id",
            payload=payload,
            event_label=f"{exact_slot.value}_PERMIT",
        )
        state.permit = record
        state.stage = ExternalProcessJournalStageV1.PERMIT_ISSUED
        return record

    def receive_pidfd_escrow(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        state = self._states[exact_slot]
        if state.stage is not ExternalProcessJournalStageV1.PERMIT_ISSUED or state.permit is None or state.intent is None:
            _fail("pidfd escrow requires the current slot permit")
        channel_kind = CREATOR_FOR_SLOT[exact_slot]
        channel = self._channels[channel_kind]
        channel._assert_live()  # noqa: SLF001
        endpoint = channel._endpoint  # noqa: SLF001
        rights: list[int] = []
        credentials: list[tuple[int, int, int]] = []
        ancillary_invalid = False
        _FORK_LOCK.acquire()
        try:
            raw, ancillary, flags, address = endpoint.recvmsg(
                MAX_PACKET_BYTES + 1,
                socket.CMSG_SPACE(16 * array.array("i").itemsize)
                + socket.CMSG_SPACE(UCRED_STRUCT.size),
                _MSG_CMSG_CLOEXEC,
            )
            for level, kind, data in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    if len(data) % array.array("i").itemsize:
                        ancillary_invalid = True
                    values = array.array("i")
                    values.frombytes(
                        data[: len(data) - (len(data) % values.itemsize)]
                    )
                    rights.extend(int(value) for value in values)
                elif (
                    level == socket.SOL_SOCKET
                    and kind == socket.SCM_CREDENTIALS
                    and len(data) == UCRED_STRUCT.size
                ):
                    credentials.append(UCRED_STRUCT.unpack(data))
                else:
                    ancillary_invalid = True
            if (
                not raw
                or len(raw) > MAX_PACKET_BYTES
                or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
                or address not in {None, "", b""}
                or ancillary_invalid
                or len(rights) != 1
                or len(credentials) != 1
            ):
                _fail("pidfd escrow packet, credential, or exact-one right changed")
            try:
                packet = loads_canonical_json(raw)
            except (TypeError, ValueError) as error:
                raise ConstructionK7H1ExternalProcessJournalV1Error(
                    "pidfd escrow packet is not canonical JSON"
                ) from error
            if type(packet) is not dict or canonical_json_bytes(packet) != raw:
                _fail("pidfd escrow packet is not one canonical object")
            permitted = state.permit.to_document()
            required_packet = {
                "schema": "acfqp.k7_h1_external_process_pidfd_escrow_packet.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "slot": exact_slot.value,
                "external_process_intent_id": state.intent.record_id,
                "external_process_permit_id": state.permit.record_id,
                "creator_channel_binding_id": channel.binding_id,
                "launch_identity_id": permitted["launch_identity_id"],
                "cgroup_identity_id": permitted["cgroup_identity_id"],
                "shared_pid_cell_identity_id": permitted["shared_pid_cell_identity_id"],
            }
            if set(packet) != set(required_packet) | {
                "fdinfo_pid",
                "shared_pid_cell_observed_pid",
                "process_start_ticks",
            } or any(packet.get(key) != value for key, value in required_packet.items()):
                _fail("pidfd escrow packet crossed slot/permit/launch/cgroup identities")
            pidfd = rights[0]
            if fcntl.fcntl(pidfd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0:
                _fail("received pidfd is not close-on-exec")
            fdinfo_pid = _pidfd_pid(pidfd)
            shared_pid = packet.get("shared_pid_cell_observed_pid")
            packet_fdinfo_pid = packet.get("fdinfo_pid")
            start_ticks = packet.get("process_start_ticks")
            if (
                type(shared_pid) is not int
                or type(packet_fdinfo_pid) is not int
                or type(start_ticks) is not int
                or shared_pid <= 0
                or start_ticks <= 0
                or packet_fdinfo_pid != fdinfo_pid
                or shared_pid != fdinfo_pid
                or _process_start_ticks(fdinfo_pid) != start_ticks
            ):
                _fail("pidfd/shared-PID/start-ticks observation join changed")
            sender_pid, sender_uid, sender_gid = credentials[0]
            expected_creator_pid = self._creator_pids[channel_kind]
            if exact_slot is ExternalProcessSlotV1.SUPERVISOR:
                if expected_creator_pid is not None or sender_pid != fdinfo_pid:
                    _fail("SUPERVISOR self-escrow sender/PID binding changed")
            elif expected_creator_pid is None or sender_pid != expected_creator_pid:
                _fail("creator SCM sender PID differs from its earlier escrow binding")
            if sender_uid != channel.expected_sender_uid or sender_gid != channel.expected_sender_gid:
                _fail("creator SCM sender UID/GID changed")
            if any(other.observed_pid == fdinfo_pid for other in self._states.values()):
                _fail("two external process slots resolved to one PID")
            before_identity = _identity(pidfd)
            if (
                _assert_endpoint(endpoint) != channel.endpoint_identity
                or _identity(pidfd) != before_identity
                or _pidfd_pid(pidfd) != fdinfo_pid
                or _process_start_ticks(fdinfo_pid) != start_ticks
            ):
                _fail("pidfd, endpoint, or process incarnation changed during escrow")
            payload = {
                **self._event_payload("acfqp.k7_h1_external_process_escrow_receipt.v1"),
                "event_kind": "PIDFD_ESCROW_RECEIVED",
                **required_packet,
                "fdinfo_pid": fdinfo_pid,
                "shared_pid_cell_observed_pid": shared_pid,
                "process_start_ticks": start_ticks,
                "sender_pid": sender_pid,
                "sender_uid": sender_uid,
                "sender_gid": sender_gid,
                "pidfd_identity": _identity_document(before_identity),
                "pidfd_rights_count": 1,
                "scm_credentials_count": 1,
                "message_and_control_not_truncated": True,
                "shared_pid_cell_is_observation_not_untamperability_proof": True,
                "shared_pid_cell_guardian_read_present": False,
                "cgroup_identity_is_opaque_binding": True,
                "cgroup_membership_verified": False,
                "process_birth_after_permit_verified": False,
                "pidfd_death_readiness_observed": False,
                "creator_reap_report_received": False,
            }
            record = self._persist_object(
                domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_RECEIPT_V1_DOMAIN,
                id_field="external_process_escrow_receipt_id",
                payload=payload,
                event_label=f"{exact_slot.value}_ESCROW",
            )
            state.receipt = record
            state.pidfd = pidfd
            state.pidfd_identity = before_identity
            state.observed_pid = fdinfo_pid
            state.process_start_ticks = start_ticks
            state.stage = ExternalProcessJournalStageV1.PIDFD_ESCROWED
            rights.clear()
            if exact_slot is ExternalProcessSlotV1.SUPERVISOR:
                self._creator_pids[CreatorChannelKindV1.SUPERVISOR_CREATOR] = fdinfo_pid
            elif exact_slot is ExternalProcessSlotV1.BROKER:
                self._creator_pids[CreatorChannelKindV1.BROKER_CREATOR] = fdinfo_pid
            return record
        except BaseException:
            for descriptor in rights:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
        finally:
            _FORK_LOCK.release()

    def acknowledge_escrow(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        state = self._states[exact_slot]
        if state.stage is not ExternalProcessJournalStageV1.PIDFD_ESCROWED or state.receipt is None:
            _fail("escrow ACK requires one retained pidfd receipt")
        channel = self._channels[CREATOR_FOR_SLOT[exact_slot]]
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_escrow_ack.v1"),
            "event_kind": "ESCROW_ACK_PREPARED",
            "slot": exact_slot.value,
            "external_process_escrow_receipt_id": state.receipt.record_id,
            "creator_channel_binding_id": channel.binding_id,
            "ack_persisted_before_send": True,
            "creator_release_authorized": False,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_ACK_V1_DOMAIN,
            id_field="external_process_escrow_ack_id",
            payload=payload,
            event_label=f"{exact_slot.value}_ACK",
        )
        state.ack = record
        state.stage = ExternalProcessJournalStageV1.ACK_PERSISTED_SEND_FAILED
        self._assert_current()
        wire = canonical_json_bytes(
            {
                "schema": "acfqp.k7_h1_external_process_guardian_ack.v1",
                "slot": exact_slot.value,
                "external_process_escrow_ack_id": record.record_id,
            }
        )
        try:
            sent = channel._endpoint.send(  # noqa: SLF001
                wire,
                getattr(socket, "MSG_NOSIGNAL", 0)
                | getattr(socket, "MSG_DONTWAIT", 0),
            )
        except OSError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "persisted escrow ACK could not be sent"
            ) from error
        if sent != len(wire):
            _fail("persisted escrow ACK send was not exact")
        state.stage = ExternalProcessJournalStageV1.ACK_PREPARED_AND_SENT
        return record

    def authorize_creator_release(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        state = self._states[exact_slot]
        if state.stage is not ExternalProcessJournalStageV1.ACK_PREPARED_AND_SENT or state.ack is None or state.receipt is None:
            _fail("creator release requires one persisted and sent escrow ACK")
        channel = self._channels[CREATOR_FOR_SLOT[exact_slot]]
        preparation_payload = {
            **self._event_payload("acfqp.k7_h1_external_process_release_preparation.v1"),
            "event_kind": "CREATOR_RELEASE_PREPARED_UNSENT",
            "slot": exact_slot.value,
            "external_process_escrow_receipt_id": state.receipt.record_id,
            "external_process_escrow_ack_id": state.ack.record_id,
            "creator_channel_binding_id": channel.binding_id,
            "guardian_retains_escrow_pidfd": True,
            "ack_persisted_and_sent_before_release": True,
            "release_message_sent": False,
            "creator_release_authorized": False,
        }
        preparation = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_PREPARATION_V1_DOMAIN,
            id_field="external_process_release_preparation_id",
            payload=preparation_payload,
            event_label=f"{exact_slot.value}_RELEASE_PREPARED",
        )
        state.release_preparation = preparation
        state.stage = ExternalProcessJournalStageV1.RELEASE_PREPARED_UNSENT
        self._assert_current()
        wire = canonical_json_bytes(
            {
                "schema": "acfqp.k7_h1_external_process_creator_release.v1",
                "slot": exact_slot.value,
                "external_process_release_preparation_id": preparation.record_id,
            }
        )
        try:
            sent = channel._endpoint.send(  # noqa: SLF001
                wire,
                getattr(socket, "MSG_NOSIGNAL", 0)
                | getattr(socket, "MSG_DONTWAIT", 0),
            )
        except OSError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "prepared creator release could not be sent"
            ) from error
        if sent != len(wire):
            _fail("prepared creator release send was not exact")
        state.stage = (
            ExternalProcessJournalStageV1.RELEASE_SENT_AUTHORIZATION_PERSIST_FAILED
        )
        authorization_payload = {
            **self._event_payload("acfqp.k7_h1_external_process_release_authorization.v1"),
            "event_kind": "CREATOR_RELEASE_SENT_AND_AUTHORIZED",
            "slot": exact_slot.value,
            "external_process_escrow_receipt_id": state.receipt.record_id,
            "external_process_escrow_ack_id": state.ack.record_id,
            "external_process_release_preparation_id": preparation.record_id,
            "creator_channel_binding_id": channel.binding_id,
            "guardian_retains_escrow_pidfd": True,
            "ack_persisted_and_sent_before_release": True,
            "release_message_sent": True,
            "creator_release_authorized": True,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_AUTHORIZATION_V1_DOMAIN,
            id_field="external_process_release_authorization_id",
            payload=authorization_payload,
            event_label=f"{exact_slot.value}_RELEASE_AUTHORIZED",
        )
        state.release_authorization = record
        state.stage = ExternalProcessJournalStageV1.CREATOR_RELEASE_AUTHORIZED
        self._next_slot_index += 1
        return record

    def observe_pidfd_death(
        self,
        *,
        slot: ExternalProcessSlotV1,
        timeout_milliseconds: int = 0,
    ) -> H1ExternalProcessJournalRecordV1:
        """Record pidfd poll readiness without assuming child ownership/status."""

        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        state = self._states[exact_slot]
        if (
            state.stage is not ExternalProcessJournalStageV1.CREATOR_RELEASE_AUTHORIZED
            or state.pidfd is None
            or state.pidfd_identity is None
            or state.observed_pid is None
            or state.receipt is None
        ):
            _fail("pidfd death observation requires ACK-gated retained escrow")
        if (
            type(timeout_milliseconds) is not int
            or not 0 <= timeout_milliseconds <= 60_000
        ):
            _fail("pidfd death poll timeout is invalid")
        poller = select.poll()
        poller.register(
            state.pidfd,
            select.POLLIN | select.POLLHUP | select.POLLERR,
        )
        try:
            events = poller.poll(timeout_milliseconds)
        except OSError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "pidfd death readiness poll failed"
            ) from error
        matching = [mask for descriptor, mask in events if descriptor == state.pidfd]
        if len(matching) != 1 or matching[0] & select.POLLIN == 0:
            _fail("pidfd has no non-consuming death readiness observation")
        if _identity(state.pidfd) != state.pidfd_identity:
            _fail("pidfd identity changed at death readiness")
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_death_observation.v1"),
            "event_kind": "PIDFD_DEATH_READINESS_OBSERVED_NONCONSUMING",
            "slot": exact_slot.value,
            "external_process_escrow_receipt_id": state.receipt.record_id,
            "observed_pid": state.observed_pid,
            "process_start_ticks": state.process_start_ticks,
            "pidfd_identity": _identity_document(state.pidfd_identity),
            "poll_mask": matching[0],
            "pollin_present": True,
            "exit_status_observed": False,
            "exit_status_consumed": False,
            "guardian_child_ownership_assumed": False,
            "creator_reap_report_received": False,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_TERMINAL_OBSERVATION_V1_DOMAIN,
            id_field="external_process_death_observation_id",
            payload=payload,
            event_label=f"{exact_slot.value}_DEATH_READY",
        )
        state.death = record
        state.stage = ExternalProcessJournalStageV1.DEATH_READINESS_OBSERVED
        if exact_slot is not ExternalProcessSlotV1.SUPERVISOR:
            channel = self._channels[CREATOR_FOR_SLOT[exact_slot]]
            self._assert_current()
            wire = canonical_json_bytes(
                {
                    "schema": "acfqp.k7_h1_external_process_death_observed.v1",
                    "slot": exact_slot.value,
                    "external_process_death_observation_id": record.record_id,
                    "escrow_receipt": state.receipt.to_document(),
                    "death_observation": record.to_document(),
                }
            )
            try:
                sent = channel._endpoint.send(  # noqa: SLF001
                    wire,
                    getattr(socket, "MSG_NOSIGNAL", 0)
                    | getattr(socket, "MSG_DONTWAIT", 0),
                )
            except OSError as error:
                raise ConstructionK7H1ExternalProcessJournalV1Error(
                    "persisted death observation notification could not be sent"
                ) from error
            if sent != len(wire):
                _fail("death observation notification send was not exact")
        return record

    def receive_creator_reap_report(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        """Receive a creator-submitted consuming-reap report over its bound channel."""

        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        if exact_slot is ExternalProcessSlotV1.SUPERVISOR:
            _fail("SUPERVISOR uses only the optional guardian-direct test path")
        state = self._states[exact_slot]
        if (
            state.stage is not ExternalProcessJournalStageV1.DEATH_READINESS_OBSERVED
            or state.death is None
            or state.receipt is None
            or state.observed_pid is None
        ):
            _fail("creator reap report requires a prior pidfd death observation")
        channel_kind = CREATOR_FOR_SLOT[exact_slot]
        channel = self._channels[channel_kind]
        expected_sender_pid = self._creator_pids[channel_kind]
        if expected_sender_pid is None:
            _fail("creator reap report lacks an earlier sender PID binding")
        rights: list[int] = []
        credentials: list[tuple[int, int, int]] = []
        ancillary_invalid = False
        _FORK_LOCK.acquire()
        try:
            raw, ancillary, flags, address = channel._endpoint.recvmsg(  # noqa: SLF001
                MAX_PACKET_BYTES + 1,
                socket.CMSG_SPACE(16 * array.array("i").itemsize)
                + socket.CMSG_SPACE(UCRED_STRUCT.size),
                _MSG_CMSG_CLOEXEC,
            )
            for level, kind, data in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    values = array.array("i")
                    values.frombytes(
                        data[: len(data) - (len(data) % values.itemsize)]
                    )
                    rights.extend(int(value) for value in values)
                    ancillary_invalid = True
                elif (
                    level == socket.SOL_SOCKET
                    and kind == socket.SCM_CREDENTIALS
                    and len(data) == UCRED_STRUCT.size
                ):
                    credentials.append(UCRED_STRUCT.unpack(data))
                else:
                    ancillary_invalid = True
            if (
                not raw
                or len(raw) > MAX_PACKET_BYTES
                or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
                or address not in {None, "", b""}
                or ancillary_invalid
                or rights
                or len(credentials) != 1
            ):
                _fail("creator reap report packet, credentials, or ancillary changed")
            try:
                packet = loads_canonical_json(raw)
            except (TypeError, ValueError) as error:
                raise ConstructionK7H1ExternalProcessJournalV1Error(
                    "creator reap report is not canonical JSON"
                ) from error
            expected = {
                "schema": "acfqp.k7_h1_external_process_creator_reap_report_packet.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "slot": exact_slot.value,
                "external_process_escrow_receipt_id": state.receipt.record_id,
                "external_process_death_observation_id": state.death.record_id,
                "creator_channel_binding_id": channel.binding_id,
                "observed_pid": state.observed_pid,
                "process_start_ticks": state.process_start_ticks,
                "waitid_idtype": "P_PID",
                "waitid_options": ["WEXITED", "WNOHANG"],
            }
            status_fields = {"observed_uid", "si_signo", "si_status", "si_code"}
            if (
                type(packet) is not dict
                or canonical_json_bytes(packet) != raw
                or set(packet) != set(expected) | status_fields
                or any(packet.get(key) != value for key, value in expected.items())
                or any(type(packet.get(key)) is not int for key in status_fields)
                or packet.get("observed_uid") != channel.expected_sender_uid
                or packet.get("si_signo") != int(signal.SIGCHLD)
                or packet.get("si_status", -1) < 0
                or packet.get("si_code", 0) <= 0
            ):
                _fail("creator reap report crossed identity or typed status fields")
            sender_pid, sender_uid, sender_gid = credentials[0]
            if (
                sender_pid != expected_sender_pid
                or sender_uid != channel.expected_sender_uid
                or sender_gid != channel.expected_sender_gid
            ):
                _fail("creator reap report SCM sender identity changed")
            payload = {
                **self._event_payload("acfqp.k7_h1_external_process_creator_reap_report.v1"),
                "event_kind": "CREATOR_DIRECT_PARENT_REAP_REPORTED",
                **expected,
                **{key: packet[key] for key in sorted(status_fields)},
                "sender_pid": sender_pid,
                "sender_uid": sender_uid,
                "sender_gid": sender_gid,
                "scm_credentials_count": 1,
                "scm_rights_count": 0,
                "exit_status_consumed_by_creator_claimed": True,
                "guardian_independent_reap_proof": False,
                "creator_relationship_proven_by_scm_credentials": False,
            }
            record = self._persist_object(
                domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_DIRECT_REAP_V1_DOMAIN,
                id_field="external_process_creator_reap_report_id",
                payload=payload,
                event_label=f"{exact_slot.value}_CREATOR_REAP_REPORT",
            )
            state.reap = record
            state.stage = ExternalProcessJournalStageV1.CREATOR_REAP_REPORTED
            self._retire_pidfd(state)
            return record
        finally:
            for descriptor in rights:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            _FORK_LOCK.release()

    def consume_guardian_direct_parent_reap_optional(
        self, *, slot: ExternalProcessSlotV1
    ) -> H1ExternalProcessJournalRecordV1:
        """Construction test seam for a real guardian direct child only."""

        self._assert_current()
        exact_slot = ExternalProcessSlotV1(slot)
        if exact_slot is not ExternalProcessSlotV1.SUPERVISOR:
            _fail("guardian direct-parent waitid is limited to SUPERVISOR test seam")
        state = self._states[exact_slot]
        if (
            state.stage is not ExternalProcessJournalStageV1.DEATH_READINESS_OBSERVED
            or state.death is None
            or state.pidfd is None
            or state.observed_pid is None
        ):
            _fail("guardian direct reap requires a separate pidfd death observation")
        try:
            observed = os.waitid(_P_PIDFD, state.pidfd, os.WEXITED | os.WNOHANG)
        except OSError as error:
            raise ConstructionK7H1ExternalProcessJournalV1Error(
                "optional guardian direct-child consuming reap failed"
            ) from error
        if observed is None or observed.si_pid != state.observed_pid:
            _fail("optional guardian direct-child reap has no matching status")
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_guardian_direct_reap.v1"),
            "event_kind": "GUARDIAN_DIRECT_CHILD_REAP_CONSUMED_OPTIONAL_TEST",
            "slot": exact_slot.value,
            "external_process_death_observation_id": state.death.record_id,
            "observed_pid": observed.si_pid,
            "observed_uid": observed.si_uid,
            "si_signo": observed.si_signo,
            "si_status": observed.si_status,
            "si_code": observed.si_code,
            "waitid_idtype": "P_PIDFD",
            "waitid_options": ["WEXITED", "WNOHANG"],
            "exit_status_consumed": True,
            "normal_guardian_reap_present": False,
            "construction_test_seam_only": True,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_DIRECT_REAP_V1_DOMAIN,
            id_field="external_process_guardian_direct_reap_id",
            payload=payload,
            event_label=f"{exact_slot.value}_GUARDIAN_DIRECT_REAP",
        )
        state.reap = record
        state.stage = ExternalProcessJournalStageV1.GUARDIAN_DIRECT_REAP_CONSUMED
        self._retire_pidfd(state)
        return record

    def close_crash(
        self, *, reason_code: str
    ) -> H1ExternalProcessJournalRecordV1:
        with _FORK_LOCK:
            return self._close_crash_under_fork_barrier(reason_code=reason_code)

    def _close_crash_under_fork_barrier(
        self, *, reason_code: str
    ) -> H1ExternalProcessJournalRecordV1:
        self._assert_current()
        if (
            type(reason_code) is not str
            or not reason_code
            or len(reason_code) > 128
            or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in reason_code)
        ):
            _fail("crash closure reason code is malformed")
        payload = {
            **self._event_payload("acfqp.k7_h1_external_process_crash_closure.v1"),
            "event_kind": "CRASH_CLOSURE_CONSTRUCTION_ONLY",
            "reason_code": reason_code,
            "slot_prefix": [
                {
                    "slot": slot.value,
                    "stage": self._states[slot].stage.value,
                    "observed_pid": self._states[slot].observed_pid,
                    "intent_id": self._states[slot].intent.record_id if self._states[slot].intent else None,
                    "permit_id": self._states[slot].permit.record_id if self._states[slot].permit else None,
                    "receipt_id": self._states[slot].receipt.record_id if self._states[slot].receipt else None,
                    "ack_id": self._states[slot].ack.record_id if self._states[slot].ack else None,
                    "release_preparation_id": (
                        self._states[slot].release_preparation.record_id
                        if self._states[slot].release_preparation
                        else None
                    ),
                    "release_authorization_id": (
                        self._states[slot].release_authorization.record_id
                        if self._states[slot].release_authorization
                        else None
                    ),
                    "death_observation_id": (
                        self._states[slot].death.record_id
                        if self._states[slot].death
                        else None
                    ),
                    "creator_or_guardian_reap_id": (
                        self._states[slot].reap.record_id
                        if self._states[slot].reap
                        else None
                    ),
                }
                for slot in SLOT_ORDER
            ],
            "pidfd_descriptor_close_is_not_process_termination_or_reap": True,
            "runtime_descriptor_close_outcome_not_claimed_by_record": True,
            "close_failure_uses_process_local_identity_bound_quarantine": True,
            "close_retry_requires_distinct_same_ofd_witness_and_kcmp": True,
            "inode_identity_alone_authorizes_close_retry": False,
            "closed_record_disk_replay_is_authority": False,
            "crash_cleanup_complete": False,
            "attempt_terminal_authorized": False,
            "process_launch_counter_authorized": False,
        }
        record = self._persist_object(
            domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CRASH_CLOSURE_V1_DOMAIN,
            id_field="external_process_crash_closure_id",
            payload=payload,
            event_label="CRASH_CLOSURE",
        )
        self._closure = record
        self._closed = True
        for state in self._states.values():
            self._retire_pidfd(state)
        for channel in self._channels.values():
            endpoint = channel._endpoint  # noqa: SLF001
            if endpoint.fileno() >= 0:
                descriptor = endpoint.detach()
                self._close_or_quarantine(descriptor, channel.endpoint_identity)
        for filename, descriptor in tuple(self._record_fds.items()):
            self._record_fds.pop(filename, None)
            self._close_or_quarantine(descriptor, _identity(descriptor))
        if self._directory_fd >= 0:
            descriptor = self._directory_fd
            self._directory_fd = -1
            self._close_or_quarantine(descriptor, self._directory_identity)
        if not self._close_quarantine:
            with _FORK_LOCK:
                _LIVE_JOURNALS.pop(id(self), None)
        return record


def _external_journal_before_fork_v1() -> None:
    _FORK_LOCK.acquire()


def _external_journal_after_fork_parent_v1() -> None:
    _FORK_LOCK.release()


def _external_journal_after_fork_child_v1() -> None:
    try:
        for journal in tuple(_LIVE_JOURNALS.values()):
            journal._poison_after_fork_child()  # noqa: SLF001
        _LIVE_JOURNALS.clear()
    finally:
        _FORK_LOCK.release()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_external_journal_before_fork_v1,
        after_in_parent=_external_journal_after_fork_parent_v1,
        after_in_child=_external_journal_after_fork_child_v1,
    )


def open_h1_external_process_journal_v1(
    *,
    journal_directory: Path | str,
    attempt_identity_id: str,
    route_attempt_id: str,
    build_epoch_id: str,
    supervisor_creator_channel: H1ExternalProcessCreatorChannelV1,
    broker_creator_channel: H1ExternalProcessCreatorChannelV1,
) -> H1ExternalProcessJournalV1:
    if (
        type(supervisor_creator_channel) is not H1ExternalProcessCreatorChannelV1
        or type(broker_creator_channel) is not H1ExternalProcessCreatorChannelV1
        or supervisor_creator_channel.kind is not CreatorChannelKindV1.SUPERVISOR_CREATOR
        or broker_creator_channel.kind is not CreatorChannelKindV1.BROKER_CREATOR
        or supervisor_creator_channel is broker_creator_channel
        or supervisor_creator_channel._endpoint is broker_creator_channel._endpoint  # noqa: SLF001
        or supervisor_creator_channel.endpoint_identity
        == broker_creator_channel.endpoint_identity
        or supervisor_creator_channel.channel_identity_id
        == broker_creator_channel.channel_identity_id
    ):
        _fail("journal requires two distinct, correctly typed creator channels")
    supervisor_creator_channel._assert_live()  # noqa: SLF001
    broker_creator_channel._assert_live()  # noqa: SLF001
    path = Path(os.path.abspath(os.fspath(journal_directory)))
    flags = os.O_RDONLY | _O_CLOEXEC | _O_DIRECTORY | _O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "journal directory is unavailable"
        ) from error
    try:
        identity = _identity(descriptor)
        if (
            not stat.S_ISDIR(identity[2])
            or identity[3] != os.geteuid()
            or stat.S_IMODE(identity[2]) & 0o077
            or os.listdir(descriptor)
        ):
            _fail("journal directory must be owned, private, and empty")
        return H1ExternalProcessJournalV1(
            _JOURNAL_ISSUER,
            directory_path=path,
            directory_fd=descriptor,
            directory_identity=identity,
            channels={
                CreatorChannelKindV1.SUPERVISOR_CREATOR: supervisor_creator_channel,
                CreatorChannelKindV1.BROKER_CREATOR: broker_creator_channel,
            },
            attempt_identity_id=attempt_identity_id,
            route_attempt_id=route_attempt_id,
            build_epoch_id=build_epoch_id,
        )
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            # Constructor failure cleanup may already have raw-closed the
            # directory descriptor while poisoning the partial journal.
            pass
        raise


def send_h1_external_process_pidfd_escrow_v1(
    *,
    endpoint: socket.socket,
    permit_document: Mapping[str, Any],
    pidfd: int,
    shared_pid_cell_observed_pid: int,
) -> dict[str, Any]:
    """Creator-side packet renderer/sender; it confers no guardian authority."""

    if type(endpoint) is not socket.socket:
        _fail("creator send endpoint is not one exact socket")
    try:
        if (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN) != socket.AF_UNIX
            or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET
            or os.get_inheritable(endpoint.fileno())
        ):
            _fail("creator send endpoint lost SEQPACKET/CLOEXEC state")
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator send endpoint is unavailable"
        ) from error
    permit = _verify_content_document(
        permit_document,
        domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_PERMIT_V1_DOMAIN,
        id_field="external_process_permit_id",
        label="external process permit",
    )
    fdinfo_pid = _pidfd_pid(pidfd)
    if (
        type(shared_pid_cell_observed_pid) is not int
        or shared_pid_cell_observed_pid != fdinfo_pid
    ):
        _fail("creator shared PID observation differs from pidfd fdinfo")
    packet = {
        "schema": "acfqp.k7_h1_external_process_pidfd_escrow_packet.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "slot": permit["slot"],
        "external_process_intent_id": permit["external_process_intent_id"],
        "external_process_permit_id": permit_document["external_process_permit_id"],
        "creator_channel_binding_id": permit["creator_channel_binding_id"],
        "launch_identity_id": permit["launch_identity_id"],
        "cgroup_identity_id": permit["cgroup_identity_id"],
        "shared_pid_cell_identity_id": permit["shared_pid_cell_identity_id"],
        "fdinfo_pid": fdinfo_pid,
        "shared_pid_cell_observed_pid": shared_pid_cell_observed_pid,
        "process_start_ticks": _process_start_ticks(fdinfo_pid),
    }
    raw = canonical_json_bytes(packet)
    descriptors = array.array("i", [pidfd])
    try:
        sent = endpoint.sendmsg(
            [raw],
            [(socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors.tobytes())],
            getattr(socket, "MSG_NOSIGNAL", 0),
        )
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator pidfd escrow send failed"
        ) from error
    if sent != len(raw):
        _fail("creator pidfd escrow send was not exact")
    return packet


def consume_and_send_h1_external_process_creator_reap_report_v1(
    *,
    endpoint: socket.socket,
    receipt_document: Mapping[str, Any],
    death_observation_document: Mapping[str, Any],
    pid: int,
) -> dict[str, Any]:
    """Creator-side direct-child waitid plus typed report; guardian replays SCM."""

    if type(endpoint) is not socket.socket:
        _fail("creator reap-report endpoint is not one exact socket")
    try:
        if (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN) != socket.AF_UNIX
            or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            != socket.SOCK_SEQPACKET
            or os.get_inheritable(endpoint.fileno())
        ):
            _fail("creator reap-report endpoint lost SEQPACKET/CLOEXEC state")
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator reap-report endpoint is unavailable"
        ) from error
    receipt = _verify_content_document(
        receipt_document,
        domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_RECEIPT_V1_DOMAIN,
        id_field="external_process_escrow_receipt_id",
        label="external process escrow receipt",
    )
    death = _verify_content_document(
        death_observation_document,
        domain=domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_TERMINAL_OBSERVATION_V1_DOMAIN,
        id_field="external_process_death_observation_id",
        label="external process death observation",
    )
    if (
        type(pid) is not int
        or pid <= 0
        or receipt.get("fdinfo_pid") != pid
        or death.get("observed_pid") != pid
        or death.get("external_process_escrow_receipt_id")
        != receipt_document.get("external_process_escrow_receipt_id")
        or receipt.get("slot") != death.get("slot")
    ):
        _fail("creator reap-report receipt/death/PID join changed")
    try:
        observed = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG)
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator direct-child consuming waitid failed"
        ) from error
    if observed is None or observed.si_pid != pid:
        _fail("creator direct-child waitid has no matching terminal status")
    packet = {
        "schema": "acfqp.k7_h1_external_process_creator_reap_report_packet.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "slot": receipt["slot"],
        "external_process_escrow_receipt_id": receipt_document[
            "external_process_escrow_receipt_id"
        ],
        "external_process_death_observation_id": death_observation_document[
            "external_process_death_observation_id"
        ],
        "creator_channel_binding_id": receipt["creator_channel_binding_id"],
        "observed_pid": pid,
        "process_start_ticks": receipt["process_start_ticks"],
        "waitid_idtype": "P_PID",
        "waitid_options": ["WEXITED", "WNOHANG"],
        "observed_uid": observed.si_uid,
        "si_signo": observed.si_signo,
        "si_status": observed.si_status,
        "si_code": observed.si_code,
    }
    raw = canonical_json_bytes(packet)
    try:
        sent = endpoint.send(raw, getattr(socket, "MSG_NOSIGNAL", 0))
    except OSError as error:
        raise ConstructionK7H1ExternalProcessJournalV1Error(
            "creator reap report send failed after consuming waitid"
        ) from error
    if sent != len(raw):
        _fail("creator reap report send was not exact")
    return packet


__all__ = (
    "ACTUAL_PROCESS_BIRTH_ORDER_VERIFIED",
    "AUTHENTICATED_SUPERVISOR_PRESENT",
    "CGROUP_MEMBERSHIP_VERIFIED",
    "CREATOR_FOR_SLOT",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "ConstructionK7H1ExternalProcessJournalV1Error",
    "CreatorChannelKindV1",
    "EXTERNAL_PROCESS_JOURNAL_PRESENT",
    "ExternalProcessJournalStageV1",
    "ExternalProcessSlotV1",
    "FIXED_FIVE_SLOT_WRITE_AHEAD_PROTOCOL_PRESENT",
    "FQ11_COUNTER_COMPLETENESS_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1ExternalProcessCreatorChannelV1",
    "H1ExternalProcessJournalProfileV1",
    "H1ExternalProcessJournalRecordV1",
    "H1ExternalProcessJournalV1",
    "LAUNCH_GATE_PRESENT",
    "MACHINE_CRASH_DURABILITY_PRESENT",
    "NORMAL_GUARDIAN_REAP_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "ORDERED_FIVE_SLOT_ESCROW_RECORD_PROTOCOL_PRESENT",
    "PIDFD_SCM_ESCROW_PROTOCOL_PRESENT",
    "PID_CELL_UNTAMPERABILITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "REAL_E3_V2_INTEGRATION_PRESENT",
    "SCHEMA_VERSION",
    "SHARED_PID_CELL_GUARDIAN_READ_PRESENT",
    "SLOT_ORDER",
    "consume_and_send_h1_external_process_creator_reap_report_v1",
    "open_h1_external_process_journal_v1",
    "official_h1_external_process_journal_profile_v1",
    "prebind_h1_external_process_creator_channel_v1",
    "send_h1_external_process_pidfd_escrow_v1",
)
