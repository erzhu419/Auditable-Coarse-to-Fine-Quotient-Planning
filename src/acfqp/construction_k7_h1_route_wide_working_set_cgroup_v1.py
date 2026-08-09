"""Bounded E5A route-wide working-set cgroup admission.

E5A creates and pins a fresh four-cgroup hierarchy and issues one prelaunch
allowed-cap envelope.  It deliberately performs no route-process placement,
does not observe a route-wide actual peak and does not mint any formal Phase
3E accounting object.  The retained lease is intended for a later E5B
integrated-launch consumer.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import os
import re
import signal
import stat
import sys
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_e3_bound_output_ordinal_continuation_v1 as e4_v1
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5A"
PROFILE_KEY = "construction_k7_h1_route_wide_working_set_cgroup_v1"
READINESS = "PRELAUNCH_ONLY"
UPPER_KIND = "PRELAUNCH_ENFORCED_ALLOWED_CAP"
COMPARISON_AXIS = "peak_working_bytes"

CGROUP2_SUPER_MAGIC = 0x63677270
_KCMP_FILE = 0
_SYS_KCMP = {
    "x86_64": 312,
    "aarch64": 272,
}.get(os.uname().machine)
OUTER_PIDS_MAX = 3
OUTER_MAX_DEPTH = 1
OUTER_MAX_DESCENDANTS = 3
MAX_PLANNED_CONCURRENCY = 3
MAX_CAP_BYTES = (1 << 63) - 1
CONTROL_NAMES = MappingProxyType(
    {
        "CONTROL": "CONTROL",
        "WORKER": "WORKER",
        "BUSINESS": "BUSINESS",
    }
)
ROLE_PIDS_MAX = MappingProxyType({"CONTROL": 2, "WORKER": 1, "BUSINESS": 1})
ROLE_ORDER = tuple(CONTROL_NAMES)

ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_PRESENT = True
ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT = False
RUNTIME_PROCESS_PLACEMENT_PRESENT = False
E5B_INTEGRATED_LAUNCH_PRESENT = False
E3_CHILD_PEAK_RELABELLED = False
POSTRUN_PEAK_USED_FOR_UPPER = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_F_DUPFD_CLOEXEC = getattr(fcntl, "F_DUPFD_CLOEXEC", 1030)
_OS_OPEN = os.open
_OS_CLOSE = os.close
_FCNTL_FCNTL = fcntl.fcntl
_PTHREAD_SIGMASK = signal.pthread_sigmask
_SIG_BLOCK = signal.SIG_BLOCK
_SIG_SETMASK = signal.SIG_SETMASK
_UNSAFE_SYNCHRONOUS_SIGNALS = frozenset(
    getattr(signal, name)
    for name in ("SIGBUS", "SIGFPE", "SIGILL", "SIGSEGV", "SIGSYS", "SIGTRAP")
    if hasattr(signal, name)
)
_SAFE_FD_PUBLICATION_SIGNALS = frozenset(
    signal.valid_signals()
    - {signal.SIGKILL, signal.SIGSTOP}
    - _UNSAFE_SYNCHRONOUS_SIGNALS
)
_ID = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ISSUER = object()
_PLAN_ISSUER = object()
_ENVELOPE_ISSUER = object()
_CLOSURE_ISSUER = object()
_LEASE_ISSUER = object()

_PARENT_FD_SLOT = "parent"
_OUTER_FD_SLOT = "outer"
_PEAK_FD_SLOT = "memory_peak"
_PEAK_WITNESS_FD_SLOT = "memory_peak_witness"


def _role_fd_slot(role: str) -> str:
    return f"role:{role}"


_CANONICAL_FD_SLOTS = (
    *(_role_fd_slot(role) for role in ROLE_ORDER),
    _PEAK_WITNESS_FD_SLOT,
    _PEAK_FD_SLOT,
    _OUTER_FD_SLOT,
    _PARENT_FD_SLOT,
)


def _retry_witness_fd_slot(slot: str) -> str:
    return f"retry-witness:{slot}"


_RETRY_WITNESS_FD_SLOTS = tuple(
    _retry_witness_fd_slot(slot) for slot in _CANONICAL_FD_SLOTS
)
_ALL_OWNED_FD_SLOTS = (
    *_CANONICAL_FD_SLOTS,
    *_RETRY_WITNESS_FD_SLOTS,
)


@dataclass(frozen=True, slots=True)
class _OwnedFDRecordV1:
    owner: Any = field(repr=False, compare=False)
    slot: str
    identity: tuple[int, int, int, int, int] | None


class _ConstructionFDOwnerV1:
    """Mutable construction slots retained until transfer or rollback."""

    __slots__ = ("_owner_pid", "_fd_slots", "_state")

    def __init__(self) -> None:
        self._owner_pid = os.getpid()
        self._fd_slots = {slot: -1 for slot in _ALL_OWNED_FD_SLOTS}
        self._state = "CONSTRUCTING"


_FD_OWNERSHIP_LOCK = threading.RLock()
_OWNED_FDS: dict[int, _OwnedFDRecordV1] = {}
_CONSTRUCTION_FD_OWNERS: dict[int, _ConstructionFDOwnerV1] = {}
_FORK_FORBIDDEN_LOCAL = threading.local()


class ConstructionK7H1RouteWideWorkingSetCgroupV1Error(ValueError):
    """An E5A delegation, topology, identity or cap invariant crossed."""


class H1RouteWideWorkingSetCgroupFaultV1(str, Enum):
    """Construction-only rollback attacks used by the E5A tests."""

    NONE = "NONE"
    AFTER_OUTER_CREATION = "AFTER_OUTER_CREATION"
    AFTER_FIRST_LEAF = "AFTER_FIRST_LEAF"
    AFTER_COMPLETE_HIERARCHY = "AFTER_COMPLETE_HIERARCHY"
    CLEANUP_BEFORE_SECOND_CHILD_RMDIR = "CLEANUP_BEFORE_SECOND_CHILD_RMDIR"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(message)


def _fork_forbidden_depth() -> int:
    value = getattr(_FORK_FORBIDDEN_LOCAL, "depth", 0)
    return value if type(value) is int and value >= 0 else 0


def _enter_fork_forbidden() -> None:
    _FORK_FORBIDDEN_LOCAL.depth = _fork_forbidden_depth() + 1


def _leave_fork_forbidden() -> None:
    depth = _fork_forbidden_depth()
    if depth <= 1:
        try:
            del _FORK_FORBIDDEN_LOCAL.depth
        except AttributeError:  # pragma: no cover - defensive only
            pass
    else:
        _FORK_FORBIDDEN_LOCAL.depth = depth - 1


def _block_fd_publication_signals() -> frozenset[signal.Signals]:
    try:
        return frozenset(
            _PTHREAD_SIGMASK(_SIG_BLOCK, _SAFE_FD_PUBLICATION_SIGNALS)
        )
    except (OSError, ValueError) as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            "E5A could not block signals for canonical FD publication"
        ) from error


def _restore_fd_publication_signals(
    original_mask: frozenset[signal.Signals],
) -> None:
    """Restore exactly, even when pending-signal delivery raises once."""

    first_error: BaseException | None = None
    try:
        _PTHREAD_SIGMASK(_SIG_SETMASK, original_mask)
    except BaseException as error:
        # pthread_sigmask has already changed the mask before Python dispatches
        # a newly unblocked pending handler.  Replay once to prove restoration
        # while preserving the handler exception as the primary outcome.
        first_error = error
    if first_error is not None:
        try:
            _PTHREAD_SIGMASK(_SIG_SETMASK, original_mask)
        except BaseException as replay_error:
            raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
                "E5A could not restore the pre-publication signal mask"
            ) from replay_error
        raise first_error


def _reject_fork_audit_during_unpublished_fd(
    event: str,
    _arguments: tuple[Any, ...],
) -> None:
    # CPython ignores exceptions raised by register_at_fork callbacks.  The
    # audit event precedes the syscall and is therefore the synchronous guard
    # that actually refuses a same-thread fork in the open->register window.
    if event in {"os.fork", "os.forkpty"} and _fork_forbidden_depth() > 0:
        _fail("E5A fork is forbidden during canonical FD publication")


sys.addaudithook(_reject_fork_audit_during_unpublished_fd)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"{label} is not one exact lowercase content ID"
        ) from error


def _positive_cap(value: Any, label: str) -> int:
    if type(value) is not int or not 1 <= value <= MAX_CAP_BYTES:
        _fail(f"{label} must be one exact finite positive byte cap")
    return value


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v12.extension_content_id_v12(domain, payload)


def _with_id(payload: Mapping[str, Any], *, domain: str, id_field: str) -> dict[str, Any]:
    document = dict(payload)
    document[id_field] = _domain_id(domain, payload)
    return document


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _verify_content_object(
    document: Any,
    *,
    domain: str,
    id_field: str,
    label: str,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = _cid(payload.pop(id_field, None), label)
    if _domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return payload


def _locked_claims() -> dict[str, Any]:
    return {
        "route_wide_actual_peak_authority_present": False,
        "runtime_process_placement_present": False,
        "e5b_integrated_launch_present": False,
        "e3_child_peak_relabelled": False,
        "postrun_peak_used_for_upper": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "fq11_counter_completeness_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_actual_projection_proof_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def _upstream_profile_ids() -> tuple[str, str]:
    return (
        _cid(
            e3_v1.official_h1_exclusive_broker_profile_v1().profile_id,
            "current E3 profile",
        ),
        _cid(
            e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id,
            "current E4 profile",
        ),
    )


@dataclass(frozen=True, slots=True)
class H1RouteWideWorkingSetCgroupProfileV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("E5A profile is caller-minted")
        payload = _canonical_document(self.canonical_bytes, "E5A profile")
        object.__setattr__(
            self,
            "profile_id",
            _domain_id(
                domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_PROFILE_V1_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.canonical_bytes, "E5A profile"),
            "h1_route_wide_working_set_cgroup_profile_id": self.profile_id,
        }


@dataclass(frozen=True, slots=True)
class H1RouteWideWorkingSetCgroupTopologyPlanV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    plan_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PLAN_ISSUER:
            _fail("E5A topology plan is caller-minted")
        payload = _canonical_document(self.canonical_bytes, "E5A topology plan")
        object.__setattr__(
            self,
            "plan_id",
            _domain_id(
                domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_TOPOLOGY_PLAN_V1_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.canonical_bytes, "E5A topology plan"),
            "h1_route_wide_cgroup_topology_plan_id": self.plan_id,
        }


def _topology_plan_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_route_wide_cgroup_topology_plan.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "outer": {
            "symbol": "A",
            "memory_max": "DERIVED_ALLOWED_CAP_U",
            "memory_swap_max": 0,
            "pids_max": OUTER_PIDS_MAX,
            "cgroup_max_depth": OUTER_MAX_DEPTH,
            "cgroup_max_descendants": OUTER_MAX_DESCENDANTS,
            "subtree_controllers": ["memory", "pids"],
        },
        "leaves": [
            {
                "role": role,
                "name": CONTROL_NAMES[role],
                "pids_max": ROLE_PIDS_MAX[role],
                "cgroup_max_depth": 0,
                "cgroup_max_descendants": 0,
            }
            for role in ROLE_ORDER
        ],
        "planned_phase_role_occupancy": [
            {
                "phase": "ROUTE_SUPERVISOR_AND_IN_PROCESS_E4_WRITER",
                "role": "CONTROL",
                "concurrency": 1,
            },
            {
                "phase": "PIDFD_CAPABILITY_PROBE",
                "role": "CONTROL",
                "concurrency": 2,
            },
            {
                "phase": "E3_BROKER_WITH_ONE_NONOVERLAPPING_ROLE",
                "roles": ["CONTROL", "WORKER_OR_BUSINESS"],
                "concurrency": 3,
            },
        ],
        "worker_business_overlap_forbidden": True,
        "pidfd_probe_broker_overlap_forbidden": True,
        "strict_nonoverlap_max_concurrency": MAX_PLANNED_CONCURRENCY,
        "outer_memory_peak_single_ofd_retained": True,
        "memory_peak_reset_only_at_fresh_empty_baseline": True,
        "route_cgroup_memory_current_admission_snapshot_required": True,
        "delegated_parent_memory_current_is_not_route_operand": True,
        "post_admission_memory_current_equality_required": False,
        "readiness": READINESS,
        **_locked_claims(),
    }


_TOPOLOGY_PLAN = H1RouteWideWorkingSetCgroupTopologyPlanV1(
    _PLAN_ISSUER,
    canonical_json_bytes(_topology_plan_payload()),
)


def _profile_payload() -> dict[str, Any]:
    e3_profile_id, e4_profile_id = _upstream_profile_ids()
    return {
        "schema": "acfqp.k7_h1_route_wide_working_set_cgroup_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "upper_kind": UPPER_KIND,
        "comparison_axis": COMPARISON_AXIS,
        "current_h1_exclusive_broker_profile_id": e3_profile_id,
        "current_h1_e3_bound_output_continuation_profile_id": e4_profile_id,
        "h1_route_wide_cgroup_topology_plan_id": _TOPOLOGY_PLAN.plan_id,
        "fresh_delegated_hierarchy_required": True,
        "one_shot_retained_lease_required": True,
        "atfork_safe_cloexec_fds_required": True,
        "identity_bound_cleanup_retry_required": True,
        "route_cgroup_memory_current_admission_snapshot_required": True,
        "delegated_parent_memory_current_is_not_route_operand": True,
        "post_admission_memory_current_equality_required": False,
        "postrun_peak_may_define_upper": False,
        "e3_child_max_may_be_relabelled_route_peak": False,
        "route_wide_prelaunch_allowed_cap_present": True,
        **_locked_claims(),
    }


_PROFILE = H1RouteWideWorkingSetCgroupProfileV1(
    _PROFILE_ISSUER,
    canonical_json_bytes(_profile_payload()),
)


def official_h1_route_wide_working_set_cgroup_profile_v1(
) -> H1RouteWideWorkingSetCgroupProfileV1:
    return _PROFILE


def official_h1_route_wide_working_set_cgroup_topology_plan_v1(
) -> H1RouteWideWorkingSetCgroupTopologyPlanV1:
    return _TOPOLOGY_PLAN


class _StatFSV12(ctypes.Structure):
    _fields_ = [
        ("f_type", ctypes.c_long),
        ("f_bsize", ctypes.c_long),
        ("f_blocks", ctypes.c_ulong),
        ("f_bfree", ctypes.c_ulong),
        ("f_bavail", ctypes.c_ulong),
        ("f_files", ctypes.c_ulong),
        ("f_ffree", ctypes.c_ulong),
        ("f_fsid", ctypes.c_int * 2),
        ("f_namelen", ctypes.c_long),
        ("f_frsize", ctypes.c_long),
        ("f_flags", ctypes.c_long),
        ("f_spare", ctypes.c_long * 4),
    ]


_LIBC = ctypes.CDLL(None, use_errno=True)


def _fstatfs_magic(descriptor: int) -> int:
    value = _StatFSV12()
    if _LIBC.fstatfs(ctypes.c_int(descriptor), ctypes.byref(value)) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return int(value.f_type)


def _mount_id(descriptor: int) -> int:
    try:
        with open(f"/proc/self/fdinfo/{descriptor}", "rb", buffering=0) as stream:
            raw = stream.read(65537)
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            "E5A could not replay descriptor mount identity"
        ) from error
    if len(raw) > 65536:
        _fail("E5A descriptor fdinfo exceeded its cap")
    rows = [
        line.split("\t", 1)[1]
        for line in raw.decode("ascii").splitlines()
        if line.startswith("mnt_id:\t")
    ]
    if len(rows) != 1 or not rows[0].isdigit():
        _fail("E5A descriptor fdinfo lacks one mount identity")
    return int(rows[0])


def _registry_fd_identity(descriptor: int) -> tuple[int, int, int, int, int]:
    """Return the exact kernel identity guarded by the ownership registry."""

    metadata = os.fstat(descriptor)
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(metadata.st_rdev),
        _mount_id(descriptor),
    )


def _owner_slot_unlocked(owner: Any, slot: str) -> int:
    slots = getattr(owner, "_fd_slots", None)
    if type(slots) is not dict or slot not in slots:
        raise RuntimeError("E5A FD owner lacks one canonical slot")
    value = slots[slot]
    if type(value) is not int:
        raise RuntimeError("E5A FD owner slot is malformed")
    return value


def _set_owner_slot_unlocked(owner: Any, slot: str, descriptor: int) -> None:
    slots = getattr(owner, "_fd_slots", None)
    if type(slots) is not dict or slot not in slots or type(descriptor) is not int:
        raise RuntimeError("E5A FD owner slot update is malformed")
    slots[slot] = descriptor


def _publish_provisional_fd_unlocked(owner: Any, slot: str, descriptor: int) -> None:
    """Publish an opened FD before any fallible identity derivation."""

    if _owner_slot_unlocked(owner, slot) != -1:
        raise RuntimeError("E5A canonical FD slot was already occupied")
    if type(descriptor) is not int or descriptor < 0:
        raise RuntimeError("E5A opened descriptor crossed its ownership registry")
    displaced = _OWNED_FDS.pop(descriptor, None)
    if displaced is not None:
        # The kernel cannot return one still-open registered number.  If an
        # external actor closed/reused it, retire the stale slot rather than
        # allowing two owners to claim the same live integer.
        if _owner_slot_unlocked(displaced.owner, displaced.slot) == descriptor:
            _set_owner_slot_unlocked(displaced.owner, displaced.slot, -1)
    _set_owner_slot_unlocked(owner, slot, descriptor)
    _OWNED_FDS[descriptor] = _OwnedFDRecordV1(
        owner=owner,
        slot=slot,
        identity=None,
    )


def _close_provisional_owned_fd_unlocked(
    owner: Any,
    slot: str,
) -> OSError | None:
    """Close an identity-less canonical FD without trusting its numeric reuse.

    A registered same-OFD duplicate exists before the close attempt.  If a
    non-EBADF close result leaves the canonical number live, kcmp decides
    whether that number is still the original OFD or an unrelated replacement.
    """

    descriptor = _owner_slot_unlocked(owner, slot)
    if descriptor < 0:
        return None
    record = _OWNED_FDS.get(descriptor)
    if (
        record is None
        or record.owner is not owner
        or record.slot != slot
        or record.identity is not None
    ):
        raise RuntimeError("E5A provisional FD ownership registry changed")
    if slot in _RETRY_WITNESS_FD_SLOTS:
        # A witness identity-upgrade failure uses the bounded final-witness
        # close rule; nested retry-witness slots are never minted.
        return _close_retry_witness_unlocked(owner, slot)
    if slot not in _CANONICAL_FD_SLOTS:
        raise RuntimeError("E5A provisional FD occupied an unknown slot")
    witness_slot = _retry_witness_fd_slot(slot)
    witness = _owner_slot_unlocked(owner, witness_slot)
    if witness < 0:
        witness = _duplicate_provisional_retry_witness_unlocked(
            owner, witness_slot, descriptor
        )
    witness_record = _OWNED_FDS.get(witness)
    if (
        witness_record is None
        or witness_record.owner is not owner
        or witness_record.slot != witness_slot
    ):
        raise RuntimeError("E5A provisional retry-witness registry changed")
    if not _same_open_file_description_for_close(descriptor, witness):
        # A prior ambiguous close already retired the original descriptor and
        # the number was reused.  Never close that replacement.
        _retire_owned_fd_unlocked(owner, slot, descriptor)
        return _close_retry_witness_unlocked(owner, witness_slot)
    try:
        os.close(descriptor)
    except OSError as error:
        if error.errno == errno.EBADF:
            _retire_owned_fd_unlocked(owner, slot, descriptor)
            return _close_retry_witness_unlocked(owner, witness_slot)
        # Inode metadata cannot distinguish close-then-reuse.  Retain the
        # canonical mapping only when it still denotes the witness OFD.
        if _same_open_file_description_for_close(descriptor, witness):
            return error
        _retire_owned_fd_unlocked(owner, slot, descriptor)
        return _close_retry_witness_unlocked(owner, witness_slot)
    _retire_owned_fd_unlocked(owner, slot, descriptor)
    return _close_retry_witness_unlocked(owner, witness_slot)


def _duplicate_provisional_retry_witness_unlocked(
    owner: Any,
    witness_slot: str,
    descriptor: int,
) -> int:
    """Publish a same-OFD close witness without requiring fallible identity."""

    if _owner_slot_unlocked(owner, witness_slot) != -1:
        raise RuntimeError("E5A provisional retry-witness slot was occupied")
    _enter_fork_forbidden()
    try:
        original_mask = _block_fd_publication_signals()
        witness = -1
        published = False
        try:
            try:
                try:
                    witness = int(
                        _FCNTL_FCNTL(descriptor, _F_DUPFD_CLOEXEC, 3)
                    )
                except OSError as error:
                    raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
                        "E5A could not pin a provisional close witness"
                    ) from error
                _publish_provisional_fd_unlocked(owner, witness_slot, witness)
                published = True
            finally:
                _restore_fd_publication_signals(original_mask)
        except BaseException:
            if witness >= 0:
                record = _OWNED_FDS.get(witness)
                published = (
                    record is not None
                    and record.owner is owner
                    and record.slot == witness_slot
                )
                if not published:
                    _publish_provisional_fd_unlocked(
                        owner, witness_slot, witness
                    )
            # The witness is deliberately retained.  Closing it in this
            # exception window would need another witness and recreate the
            # same unregistered-close ambiguity.
            raise
        return witness
    finally:
        _leave_fork_forbidden()


def _quarantine_and_close_provisional_unlocked(owner: Any, slot: str) -> None:
    if type(owner) is _ConstructionFDOwnerV1:
        owner._state = "OPEN_QUARANTINED"
    _close_provisional_owned_fd_unlocked(owner, slot)


def _upgrade_provisional_fd_identity_unlocked(
    owner: Any,
    slot: str,
    descriptor: int,
) -> int:
    record = _OWNED_FDS.get(descriptor)
    if (
        record is None
        or record.owner is not owner
        or record.slot != slot
        or record.identity is not None
    ):
        raise RuntimeError("E5A provisional FD disappeared before identity upgrade")
    try:
        identity = _registry_fd_identity(descriptor)
    except BaseException:
        _quarantine_and_close_provisional_unlocked(owner, slot)
        raise
    _OWNED_FDS[descriptor] = _OwnedFDRecordV1(
        owner=owner,
        slot=slot,
        identity=identity,
    )
    return descriptor


def _open_owned_path_fd(
    owner: Any,
    slot: str,
    path: str,
    flags: int,
    *,
    dir_fd: int | None = None,
) -> int:
    """Concrete open, provisional publish, then exact identity upgrade."""

    with _FD_OWNERSHIP_LOCK:
        if _owner_slot_unlocked(owner, slot) != -1:
            raise RuntimeError("E5A canonical FD slot was already occupied")
        _enter_fork_forbidden()
        try:
            original_mask = _block_fd_publication_signals()
            descriptor = -1
            published = False
            try:
                try:
                    descriptor = (
                        _OS_OPEN(path, flags)
                        if dir_fd is None
                        else _OS_OPEN(path, flags, dir_fd=dir_fd)
                    )
                    _publish_provisional_fd_unlocked(owner, slot, descriptor)
                    published = True
                finally:
                    _restore_fd_publication_signals(original_mask)
            except BaseException:
                if descriptor >= 0:
                    record = _OWNED_FDS.get(descriptor)
                    published = (
                        record is not None
                        and record.owner is owner
                        and record.slot == slot
                    )
                    if not published:
                        _publish_provisional_fd_unlocked(owner, slot, descriptor)
                        published = True
                    if published:
                        _quarantine_and_close_provisional_unlocked(owner, slot)
                raise
            return _upgrade_provisional_fd_identity_unlocked(
                owner, slot, descriptor
            )
        finally:
            _leave_fork_forbidden()


def _duplicate_owned_fd(owner: Any, slot: str, descriptor: int) -> int:
    """Concrete F_DUPFD_CLOEXEC, provisional publish, exact upgrade."""

    with _FD_OWNERSHIP_LOCK:
        if _owner_slot_unlocked(owner, slot) != -1:
            raise RuntimeError("E5A canonical FD slot was already occupied")
        _enter_fork_forbidden()
        try:
            original_mask = _block_fd_publication_signals()
            duplicate = -1
            published = False
            try:
                try:
                    try:
                        duplicate = int(
                            _FCNTL_FCNTL(descriptor, _F_DUPFD_CLOEXEC, 3)
                        )
                    except OSError as error:
                        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
                            "E5A could not pin a close-on-exec descriptor"
                        ) from error
                    _publish_provisional_fd_unlocked(owner, slot, duplicate)
                    published = True
                finally:
                    _restore_fd_publication_signals(original_mask)
            except BaseException:
                if duplicate >= 0:
                    record = _OWNED_FDS.get(duplicate)
                    published = (
                        record is not None
                        and record.owner is owner
                        and record.slot == slot
                    )
                    if not published:
                        _publish_provisional_fd_unlocked(owner, slot, duplicate)
                        published = True
                    if published:
                        _quarantine_and_close_provisional_unlocked(owner, slot)
                raise
            return _upgrade_provisional_fd_identity_unlocked(
                owner, slot, duplicate
            )
        finally:
            _leave_fork_forbidden()


def _registered_fd_still_exact_unlocked(
    descriptor: int,
    record: _OwnedFDRecordV1,
) -> bool:
    if record.identity is None:
        return False
    try:
        return _registry_fd_identity(descriptor) == record.identity
    except OSError as error:
        if error.errno == errno.EBADF:
            return False
        raise


def _retire_owned_fd_unlocked(owner: Any, slot: str, descriptor: int) -> None:
    record = _OWNED_FDS.get(descriptor)
    if record is not None and record.owner is owner and record.slot == slot:
        _OWNED_FDS.pop(descriptor, None)
    if _owner_slot_unlocked(owner, slot) == descriptor:
        _set_owner_slot_unlocked(owner, slot, -1)


def _close_retry_witness_unlocked(owner: Any, witness_slot: str) -> OSError | None:
    """Close one internal OFD witness with the unpatched kernel close wrapper."""

    witness = _owner_slot_unlocked(owner, witness_slot)
    if witness < 0:
        return None
    record = _OWNED_FDS.get(witness)
    if record is None or record.owner is not owner or record.slot != witness_slot:
        raise RuntimeError("E5A retry-witness ownership registry changed")
    try:
        _OS_CLOSE(witness)
    except OSError as error:
        if error.errno == errno.EBADF:
            _retire_owned_fd_unlocked(owner, witness_slot, witness)
            return None
        if record.identity is None:
            # This is the registered original-OFD witness, not the ambiguous
            # canonical number.  A failed trusted close keeps it quarantined;
            # it is never reinterpreted as a canonical replacement.
            try:
                os.fstat(witness)
            except OSError as replay_error:
                if replay_error.errno == errno.EBADF:
                    _retire_owned_fd_unlocked(owner, witness_slot, witness)
                    return None
            return error
        try:
            still_exact = _registered_fd_still_exact_unlocked(witness, record)
        except OSError:
            return error
        if still_exact:
            return error
    _retire_owned_fd_unlocked(owner, witness_slot, witness)
    return None


def _close_owned_fd_slot(owner: Any, slot: str) -> OSError | None:
    """Close a canonical FD, retaining exact ownership if it remains live.

    A private duplicate proves OFD continuity across a non-EBADF error.  It is
    retained in the same registry across retries when the original remains
    live, so even same-inode/new-OFD numeric reuse is distinguished.  A reused
    unrelated descriptor is never closed.
    """

    with _FD_OWNERSHIP_LOCK:
        if slot not in _CANONICAL_FD_SLOTS:
            raise RuntimeError("E5A canonical close received a witness slot")
        witness_slot = _retry_witness_fd_slot(slot)
        descriptor = _owner_slot_unlocked(owner, slot)
        if descriptor < 0:
            witness = _owner_slot_unlocked(owner, witness_slot)
            if witness < 0:
                return None
            witness_record = _OWNED_FDS.get(witness)
            if (
                witness_record is None
                or witness_record.owner is not owner
                or witness_record.slot != witness_slot
            ):
                raise RuntimeError("E5A retry-witness registry changed")
            _OWNED_FDS[witness] = _OwnedFDRecordV1(
                owner=owner,
                slot=slot,
                identity=witness_record.identity,
            )
            _set_owner_slot_unlocked(owner, witness_slot, -1)
            _set_owner_slot_unlocked(owner, slot, witness)
            descriptor = witness
        record = _OWNED_FDS.get(descriptor)
        if record is None or record.owner is not owner or record.slot != slot:
            raise RuntimeError("E5A canonical FD ownership registry changed")
        if record.identity is None:
            return _close_provisional_owned_fd_unlocked(owner, slot)
        try:
            exact_before = _registered_fd_still_exact_unlocked(descriptor, record)
        except OSError as error:
            return error
        if not exact_before:
            _retire_owned_fd_unlocked(owner, slot, descriptor)
            return None
        witness = _owner_slot_unlocked(owner, witness_slot)
        if witness >= 0:
            witness_record = _OWNED_FDS.get(witness)
            if (
                witness_record is None
                or witness_record.owner is not owner
                or witness_record.slot != witness_slot
                or not _registered_fd_still_exact_unlocked(witness, witness_record)
            ):
                raise RuntimeError("E5A retained retry-witness identity changed")
            if not _same_open_file_description_for_close(descriptor, witness):
                # The numeric canonical FD was replaced after an earlier
                # failure.  Retire it without closing it; the witness still
                # owns the original OFD and can be closed safely.
                _retire_owned_fd_unlocked(owner, slot, descriptor)
                return _close_retry_witness_unlocked(owner, witness_slot)
        else:
            witness = _duplicate_owned_fd(owner, witness_slot, descriptor)
        try:
            os.close(descriptor)
        except OSError as error:
            if error.errno == errno.EBADF:
                _retire_owned_fd_unlocked(owner, slot, descriptor)
                return _close_retry_witness_unlocked(owner, witness_slot)
            # The retained duplicate, not inode metadata alone, distinguishes
            # one still-live original OFD from same-inode/new-OFD reuse.
            if _same_open_file_description_for_close(descriptor, witness):
                return error
            _retire_owned_fd_unlocked(owner, slot, descriptor)
            return _close_retry_witness_unlocked(owner, witness_slot)
        _retire_owned_fd_unlocked(owner, slot, descriptor)
        return _close_retry_witness_unlocked(owner, witness_slot)


def _owned_fd_slots_remaining(owner: Any) -> tuple[str, ...]:
    with _FD_OWNERSHIP_LOCK:
        return tuple(
            slot
            for slot in _ALL_OWNED_FD_SLOTS
            if _owner_slot_unlocked(owner, slot) >= 0
        )


def _fd_identity(descriptor: int, *, directory: bool) -> dict[str, int]:
    try:
        metadata = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            "E5A pinned descriptor is no longer live"
        ) from error
    if directory and not stat.S_ISDIR(metadata.st_mode):
        _fail("E5A pinned cgroup descriptor is not a directory")
    if not directory and not stat.S_ISREG(metadata.st_mode):
        _fail("E5A pinned memory.peak descriptor is not a control file")
    return {
        "device": int(metadata.st_dev),
        "inode": int(metadata.st_ino),
        "mode": stat.S_IMODE(metadata.st_mode),
        "mount_id": _mount_id(descriptor),
    }


def _same_open_file_description(left: int, right: int) -> bool:
    """Prove a retained duplicate still shares the same seek position."""

    try:
        left_position = os.lseek(left, 0, os.SEEK_CUR)
        right_position = os.lseek(right, 0, os.SEEK_CUR)
        if left_position != right_position:
            return False
        probe = 1 if left_position == 0 else 0
        os.lseek(left, probe, os.SEEK_SET)
        shared = os.lseek(right, 0, os.SEEK_CUR) == probe
        os.lseek(left, left_position, os.SEEK_SET)
        return shared and os.lseek(right, 0, os.SEEK_CUR) == left_position
    except OSError:
        return False


def _same_open_file_description_for_close(left: int, right: int) -> bool:
    """Compare OFDs after cgroup removal, where kernfs lseek returns ENODEV."""

    if _SYS_KCMP is None:
        raise RuntimeError("E5A close retry lacks a registered kcmp syscall")
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
    raise RuntimeError("E5A could not compare retained close-retry OFDs") from OSError(
        code, os.strerror(code)
    )


def _read_all_fd(descriptor: int, *, cap: int = 65536) -> bytes:
    try:
        raw = os.pread(descriptor, cap + 1, 0)
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            "E5A could not read a pinned cgroup control"
        ) from error
    if len(raw) > cap:
        _fail("E5A cgroup control exceeded its read cap")
    return raw


def _read_control(directory_fd: int, name: str) -> bytes:
    descriptor = -1
    try:
        descriptor = _OS_OPEN(
            name,
            os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        return _read_all_fd(descriptor)
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A could not read cgroup control {name}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_control(directory_fd: int, name: str, value: str) -> None:
    if type(value) is not str or not value or "\x00" in value:
        _fail("E5A refused a malformed cgroup control write")
    descriptor = -1
    try:
        descriptor = _OS_OPEN(
            name,
            os.O_WRONLY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        raw = value.encode("ascii")
        if os.write(descriptor, raw) != len(raw):
            _fail(f"E5A short-wrote cgroup control {name}")
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A could not write delegated cgroup control {name}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _control_text(directory_fd: int, name: str) -> str:
    try:
        text = _read_control(directory_fd, name).decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A cgroup control {name} is not ASCII"
        ) from error
    if not text or "\x00" in text:
        _fail(f"E5A cgroup control {name} is malformed")
    return text


def _exact_nonnegative_control(directory_fd: int, name: str) -> int:
    text = _control_text(directory_fd, name)
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        _fail(f"E5A cgroup control {name} is not one exact finite integer")
    return int(text)


def _limit_control(directory_fd: int, name: str) -> int | None:
    text = _control_text(directory_fd, name)
    if text == "max":
        return None
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        _fail(f"E5A cgroup limit {name} is malformed")
    return int(text)


def _tokens_control(directory_fd: int, name: str) -> frozenset[str]:
    try:
        text = _read_control(directory_fd, name).decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A token control {name} is not ASCII"
        ) from error
    if "\x00" in text:
        _fail(f"E5A token control {name} is malformed")
    if not text:
        return frozenset()
    tokens = text.split()
    if len(tokens) != len(set(tokens)) or any(not token.isidentifier() for token in tokens):
        _fail(f"E5A token control {name} is malformed")
    return frozenset(tokens)


def _cgroup_populated(directory_fd: int) -> int:
    rows: dict[str, str] = {}
    for row in _control_text(directory_fd, "cgroup.events").splitlines():
        parts = row.split()
        if len(parts) != 2 or parts[0] in rows:
            _fail("E5A cgroup.events is malformed")
        rows[parts[0]] = parts[1]
    if rows.get("populated") not in {"0", "1"}:
        _fail("E5A cgroup.events lacks canonical populated state")
    return int(rows["populated"])


def _require_empty_cgroup(directory_fd: int, label: str, *, memory: bool) -> int | None:
    procs = _read_control(directory_fd, "cgroup.procs").strip()
    if procs:
        _fail(f"{label} contains a process")
    if _cgroup_populated(directory_fd) != 0:
        _fail(f"{label} remains populated")
    if memory:
        # A process-empty cgroup may retain controller metadata or delayed
        # kernel charges.  Emptiness is the kernel's procs/populated property;
        # memory.current is recorded and bounded by the retained peak, never
        # falsely required to be zero.
        return _exact_nonnegative_control(directory_fd, "memory.current")
    return None


def _child_directories(directory_fd: int) -> tuple[str, ...]:
    try:
        names = os.listdir(directory_fd)
    except (OSError, TypeError) as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            "E5A could not inventory cgroup children"
        ) from error
    children: list[str] = []
    for name in names:
        if type(name) is not str or name in {".", ".."}:
            _fail("E5A cgroup child inventory is malformed")
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            _fail("E5A cgroup child inventory changed during replay")
        if stat.S_ISDIR(metadata.st_mode):
            children.append(name)
    return tuple(sorted(children))


def _require_parent_delegation(parent_fd: int) -> dict[str, Any]:
    if _fstatfs_magic(parent_fd) != CGROUP2_SUPER_MAGIC:
        _fail("E5A delegated parent is not a cgroup-v2 directory")
    identity = _fd_identity(parent_fd, directory=True)
    _require_empty_cgroup(parent_fd, "E5A delegated parent", memory=True)
    if _child_directories(parent_fd):
        _fail("E5A delegated parent is not a fresh child-free baseline")
    controllers = _tokens_control(parent_fd, "cgroup.controllers")
    enabled = _tokens_control(parent_fd, "cgroup.subtree_control")
    if not {"memory", "pids"} <= controllers or not {"memory", "pids"} <= enabled:
        _fail("E5A delegated parent lacks enabled memory+pids authority")
    cgroup_type = _control_text(parent_fd, "cgroup.type")
    if cgroup_type != "domain":
        _fail("E5A delegated parent is not a domain cgroup")
    parent_depth = _limit_control(parent_fd, "cgroup.max.depth")
    parent_descendants = _limit_control(parent_fd, "cgroup.max.descendants")
    if parent_depth is not None and parent_depth < 2:
        _fail("E5A delegated parent depth cannot host the planned hierarchy")
    if parent_descendants is not None and parent_descendants < 4:
        _fail("E5A delegated parent descendant cap is too small")
    parent_pids = _limit_control(parent_fd, "pids.max")
    if parent_pids is not None and parent_pids < OUTER_PIDS_MAX:
        _fail("E5A delegated parent pids cap is too small")
    return {
        "identity": identity,
        "controllers": sorted(controllers),
        "subtree_controllers": sorted(enabled),
        "fresh_empty_child_free": True,
        "memory_current_scope": "DELEGATION_PREREQUISITE_NOT_ROUTE_OPERAND",
        "memory_current_value_content_bound": False,
    }


def _open_child_directory(parent_fd: int, name: str) -> int:
    try:
        return _OS_OPEN(
            name,
            os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A could not pin fresh cgroup {name}"
        ) from error


def _assert_named_identity(parent_fd: int, name: str, identity: Mapping[str, int]) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        raise ConstructionK7H1RouteWideWorkingSetCgroupV1Error(
            f"E5A named cgroup {name} disappeared"
        ) from error
    if not stat.S_ISDIR(metadata.st_mode) or (
        int(metadata.st_dev),
        int(metadata.st_ino),
    ) != (identity["device"], identity["inode"]):
        _fail(f"E5A named cgroup {name} crossed its pinned identity")


def _configure_outer(outer_fd: int, allowed_cap_bytes: int) -> None:
    _write_control(outer_fd, "memory.max", str(allowed_cap_bytes))
    _write_control(outer_fd, "memory.swap.max", "0")
    _write_control(outer_fd, "pids.max", str(OUTER_PIDS_MAX))
    _write_control(outer_fd, "cgroup.max.depth", str(OUTER_MAX_DEPTH))
    _write_control(outer_fd, "cgroup.max.descendants", str(OUTER_MAX_DESCENDANTS))
    _write_control(outer_fd, "cgroup.subtree_control", "+memory +pids")


def _configure_leaf(leaf_fd: int, role: str) -> None:
    _write_control(leaf_fd, "pids.max", str(ROLE_PIDS_MAX[role]))
    _write_control(leaf_fd, "cgroup.max.depth", "0")
    _write_control(leaf_fd, "cgroup.max.descendants", "0")


def _verify_outer_controls(outer_fd: int, allowed_cap_bytes: int) -> None:
    if _limit_control(outer_fd, "memory.max") != allowed_cap_bytes:
        _fail("E5A outer memory.max changed or became infinite")
    if _exact_nonnegative_control(outer_fd, "memory.swap.max") != 0:
        _fail("E5A outer memory.swap.max changed")
    if _exact_nonnegative_control(outer_fd, "pids.max") != OUTER_PIDS_MAX:
        _fail("E5A outer pids.max changed")
    if _exact_nonnegative_control(outer_fd, "cgroup.max.depth") != OUTER_MAX_DEPTH:
        _fail("E5A outer cgroup.max.depth changed")
    if (
        _exact_nonnegative_control(outer_fd, "cgroup.max.descendants")
        != OUTER_MAX_DESCENDANTS
    ):
        _fail("E5A outer cgroup.max.descendants changed")
    if _tokens_control(outer_fd, "cgroup.subtree_control") != frozenset(
        {"memory", "pids"}
    ):
        _fail("E5A outer subtree controller set changed")


def _verify_leaf_controls(leaf_fd: int, role: str) -> None:
    if _exact_nonnegative_control(leaf_fd, "pids.max") != ROLE_PIDS_MAX[role]:
        _fail(f"E5A {role} pids.max changed")
    if _exact_nonnegative_control(leaf_fd, "cgroup.max.depth") != 0:
        _fail(f"E5A {role} cgroup.max.depth changed")
    if _exact_nonnegative_control(leaf_fd, "cgroup.max.descendants") != 0:
        _fail(f"E5A {role} cgroup.max.descendants changed")
    if _child_directories(leaf_fd):
        _fail(f"E5A {role} unexpectedly gained descendants")


def _open_and_reset_memory_peak(
    outer_fd: int,
    owner: _ConstructionFDOwnerV1,
) -> tuple[int, int, dict[str, int], int, int]:
    try:
        peak_fd = _open_owned_path_fd(
            owner,
            _PEAK_FD_SLOT,
            "memory.peak",
            os.O_RDWR | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=outer_fd,
        )
        # A fresh process-empty hierarchy may be reset once, and only here.
        # Linux resets memory.peak to the current charge, which need not be
        # zero because controller metadata can remain charged.
        os.lseek(peak_fd, 0, os.SEEK_SET)
        if os.write(peak_fd, b"0") != 1:
            _fail("E5A short-wrote the fresh memory.peak reset")
        os.lseek(peak_fd, 0, os.SEEK_SET)
        baseline_text = _read_all_fd(peak_fd).decode("ascii").strip()
        if not re.fullmatch(r"0|[1-9][0-9]*", baseline_text):
            _fail("E5A fresh memory.peak baseline is malformed")
        baseline_peak_bytes = int(baseline_text)
        outer_current_bytes_at_reset = _exact_nonnegative_control(
            outer_fd, "memory.current"
        )
        if baseline_peak_bytes < outer_current_bytes_at_reset:
            _fail("E5A reset memory.peak is below memory.current")
        os.lseek(peak_fd, 0, os.SEEK_SET)
        witness_fd = _duplicate_owned_fd(owner, _PEAK_WITNESS_FD_SLOT, peak_fd)
        if not _same_open_file_description(peak_fd, witness_fd):
            _fail("E5A memory.peak retained descriptors do not share one OFD")
        return (
            peak_fd,
            witness_fd,
            _fd_identity(peak_fd, directory=False),
            baseline_peak_bytes,
            outer_current_bytes_at_reset,
        )
    except BaseException:
        for slot in (_PEAK_WITNESS_FD_SLOT, _PEAK_FD_SLOT):
            _close_owned_fd_slot(owner, slot)
        raise


def _hierarchy_payload(
    *,
    nonce: str,
    caller_ids: Mapping[str, str],
    parent: Mapping[str, Any],
    outer_name: str,
    outer_identity: Mapping[str, int],
    role_identities: Mapping[str, Mapping[str, int]],
    peak_identity: Mapping[str, int],
    baseline_peak_bytes: int,
    memory_current_bytes_at_admission: Mapping[str, int],
    registered_hard_cap_bytes: int,
    requested_outer_memory_max_bytes: int,
    allowed_cap_bytes: int,
) -> dict[str, Any]:
    e3_profile_id, e4_profile_id = _upstream_profile_ids()
    return {
        "schema": "acfqp.k7_h1_route_wide_cgroup_hierarchy.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_route_wide_working_set_cgroup_profile_id": _PROFILE.profile_id,
        "h1_route_wide_cgroup_topology_plan_id": _TOPOLOGY_PLAN.plan_id,
        **caller_ids,
        "current_h1_exclusive_broker_profile_id": e3_profile_id,
        "current_h1_e3_bound_output_continuation_profile_id": e4_profile_id,
        "hierarchy_nonce": nonce,
        "delegated_parent": parent,
        "outer": {
            "symbol": "A",
            "name": outer_name,
            "identity": dict(outer_identity),
            "memory_max_bytes": allowed_cap_bytes,
            "memory_swap_max_bytes": 0,
            "pids_max": OUTER_PIDS_MAX,
            "cgroup_max_depth": OUTER_MAX_DEPTH,
            "cgroup_max_descendants": OUTER_MAX_DESCENDANTS,
            "subtree_controllers": ["memory", "pids"],
            "fresh_empty_baseline_verified": True,
            "memory_current_bytes_at_admission": (
                memory_current_bytes_at_admission["OUTER"]
            ),
            "memory_current_observation_ordinal": 1,
            "memory_current_observation_phase": (
                "IMMEDIATELY_AFTER_SINGLE_OUTER_PEAK_RESET"
            ),
        },
        "leaves": [
            {
                "role": role,
                "name": CONTROL_NAMES[role],
                "identity": dict(role_identities[role]),
                "pids_max": ROLE_PIDS_MAX[role],
                "cgroup_max_depth": 0,
                "cgroup_max_descendants": 0,
                "fresh_empty_baseline_verified": True,
                "memory_current_bytes_at_admission": (
                    memory_current_bytes_at_admission[role]
                ),
                "memory_current_observation_ordinal": 2 + ROLE_ORDER.index(role),
                "memory_current_observation_phase": (
                    "POST_RESET_SEQUENTIAL_ROUTE_CGROUP_SNAPSHOT"
                ),
            }
            for role in ROLE_ORDER
        ],
        "outer_memory_peak": {
            "identity": dict(peak_identity),
            "single_open_file_description_retained_with_witness": True,
            "reset_count": 1,
            "reset_only_at_fresh_empty_baseline": True,
            "baseline_peak_bytes": baseline_peak_bytes,
            "baseline_not_below_recorded_outer_memory_current": True,
        },
        "registered_hard_cap_bytes": registered_hard_cap_bytes,
        "requested_outer_memory_max_bytes": requested_outer_memory_max_bytes,
        "enforced_outer_memory_max_bytes": allowed_cap_bytes,
        "strict_nonoverlap_max_concurrency": MAX_PLANNED_CONCURRENCY,
        "no_route_process_placed": True,
        "admission_memory_current_values_are_frozen_timepoint_observations": True,
        "later_memory_current_values_may_differ": True,
        "readiness": READINESS,
        **_locked_claims(),
    }


@dataclass(frozen=True, slots=True)
class H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    envelope_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("E5A allowed-cap envelope is caller-minted")
        document = _canonical_document(self.canonical_bytes, "E5A allowed-cap envelope")
        payload = dict(document)
        supplied = _cid(
            payload.pop("h1_route_wide_prelaunch_allowed_cap_envelope_id", None),
            "E5A allowed-cap envelope",
        )
        if _domain_id(
            domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN,
            payload,
        ) != supplied:
            _fail("E5A allowed-cap envelope content ID changed")
        object.__setattr__(self, "envelope_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(self.canonical_bytes, "E5A allowed-cap envelope")


@dataclass(frozen=True, slots=True)
class H1RouteWideWorkingSetCgroupCleanupClosureV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    closure_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CLOSURE_ISSUER:
            _fail("E5A cleanup closure is caller-minted")
        document = _canonical_document(self.canonical_bytes, "E5A cleanup closure")
        payload = dict(document)
        supplied = _cid(
            payload.pop("h1_route_wide_cgroup_cleanup_closure_id", None),
            "E5A cleanup closure",
        )
        if _domain_id(
            domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN,
            payload,
        ) != supplied:
            _fail("E5A cleanup closure content ID changed")
        object.__setattr__(self, "closure_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(self.canonical_bytes, "E5A cleanup closure")


class H1RouteWideWorkingSetCgroupLeaseV1:
    """Issuer-owned, PID-bound retained E5A hierarchy lease."""

    __slots__ = (
        "_owner_pid",
        "_fd_slots",
        "_outer_name",
        "_hierarchy_document",
        "_hierarchy_id",
        "_envelope",
        "_lock",
        "_state",
        "_cleanup_attempts",
        "_removed_roles",
        "_outer_removed",
        "_closure",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        owner_pid: int,
        parent_fd: int,
        outer_fd: int,
        role_fds: Mapping[str, int],
        memory_peak_fd: int,
        memory_peak_witness_fd: int,
        outer_name: str,
        hierarchy_document: Mapping[str, Any],
        hierarchy_id: str,
        envelope: H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1,
    ) -> None:
        if _issuer is not _LEASE_ISSUER:
            _fail("E5A retained lease is caller-minted")
        self._owner_pid = owner_pid
        self._fd_slots = {
            _PARENT_FD_SLOT: parent_fd,
            _OUTER_FD_SLOT: outer_fd,
            _PEAK_FD_SLOT: memory_peak_fd,
            _PEAK_WITNESS_FD_SLOT: memory_peak_witness_fd,
            **{
                _role_fd_slot(role): role_fds[role]
                for role in ROLE_ORDER
            },
            **{
                _retry_witness_fd_slot(slot): -1
                for slot in _CANONICAL_FD_SLOTS
            },
        }
        self._outer_name = outer_name
        self._hierarchy_document = dict(hierarchy_document)
        self._hierarchy_id = hierarchy_id
        self._envelope = envelope
        self._lock = threading.RLock()
        self._state = "ACTIVE"
        self._cleanup_attempts = 0
        self._removed_roles: set[str] = set()
        self._outer_removed = False
        self._closure: H1RouteWideWorkingSetCgroupCleanupClosureV1 | None = None

    @property
    def _parent_fd(self) -> int:
        return self._fd_slots[_PARENT_FD_SLOT]

    @_parent_fd.setter
    def _parent_fd(self, value: int) -> None:
        self._fd_slots[_PARENT_FD_SLOT] = value

    @property
    def _outer_fd(self) -> int:
        return self._fd_slots[_OUTER_FD_SLOT]

    @_outer_fd.setter
    def _outer_fd(self, value: int) -> None:
        self._fd_slots[_OUTER_FD_SLOT] = value

    @property
    def _memory_peak_fd(self) -> int:
        return self._fd_slots[_PEAK_FD_SLOT]

    @_memory_peak_fd.setter
    def _memory_peak_fd(self, value: int) -> None:
        self._fd_slots[_PEAK_FD_SLOT] = value

    @property
    def _memory_peak_witness_fd(self) -> int:
        return self._fd_slots[_PEAK_WITNESS_FD_SLOT]

    @_memory_peak_witness_fd.setter
    def _memory_peak_witness_fd(self, value: int) -> None:
        self._fd_slots[_PEAK_WITNESS_FD_SLOT] = value

    @property
    def _role_fds(self) -> dict[str, int]:
        return {
            role: self._fd_slots[_role_fd_slot(role)]
            for role in ROLE_ORDER
        }

    @_role_fds.setter
    def _role_fds(self, values: Mapping[str, int]) -> None:
        for role in ROLE_ORDER:
            self._fd_slots[_role_fd_slot(role)] = values[role]

    @property
    def hierarchy_id(self) -> str:
        return self._hierarchy_id

    @property
    def envelope(self) -> H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1:
        return self._envelope

    @property
    def readiness(self) -> str:
        return READINESS

    @property
    def state(self) -> str:
        return self._state

    def hierarchy_document(self) -> dict[str, Any]:
        return loads_canonical_json(canonical_json_bytes(self._hierarchy_document))

    def _poison_after_fork_child(self) -> None:
        # Registered descriptors are closed by the single ownership callback.
        for slot in _ALL_OWNED_FD_SLOTS:
            self._fd_slots[slot] = -1
        self._state = "FORK_POISONED"

    def __reduce__(self) -> NoReturn:
        _fail("E5A retained lease cannot be copied or pickled")


_LIVE_LEASES: dict[int, H1RouteWideWorkingSetCgroupLeaseV1] = {}
_QUARANTINED_LEASES: dict[int, H1RouteWideWorkingSetCgroupLeaseV1] = {}


def _e5a_before_fork() -> None:
    # The same lock covers open/register, close/drop and every owner-slot/state
    # transition, so the child receives one exact registry snapshot.
    if _fork_forbidden_depth() > 0:
        # Defense in depth for alternate runtimes.  CPython's audit hook above
        # is the authoritative synchronous refusal because at-fork callback
        # exceptions alone are otherwise reported as unraisable.
        _fail("E5A fork crossed an unpublished opened FD")
    _FD_OWNERSHIP_LOCK.acquire()


def _e5a_after_fork_parent() -> None:
    _FD_OWNERSHIP_LOCK.release()


def _e5a_after_fork_child() -> None:
    """Close exactly the registered construction/live/quarantine descriptors."""

    global _FD_OWNERSHIP_LOCK
    inherited_records = tuple(_OWNED_FDS.items())
    inherited_leases = tuple(
        {**_LIVE_LEASES, **_QUARANTINED_LEASES}.values()
    )
    inherited_constructions = tuple(_CONSTRUCTION_FD_OWNERS.values())
    for descriptor, record in inherited_records:
        # before-fork held the ownership lock across every canonical open,
        # close, slot update and registry drop.  The snapshot therefore has no
        # internal reuse window; the child callback performs only raw close
        # syscalls and in-memory poisoning (no fstat, fdinfo or /proc opens).
        try:
            _OS_CLOSE(descriptor)
        except OSError:
            pass
        if _owner_slot_unlocked(record.owner, record.slot) == descriptor:
            _set_owner_slot_unlocked(record.owner, record.slot, -1)
    for lease in inherited_leases:
        lease._poison_after_fork_child()
    for construction in inherited_constructions:
        for slot in _ALL_OWNED_FD_SLOTS:
            construction._fd_slots[slot] = -1
        construction._state = "FORK_POISONED"
    _OWNED_FDS.clear()
    _CONSTRUCTION_FD_OWNERS.clear()
    _LIVE_LEASES.clear()
    _QUARANTINED_LEASES.clear()
    _FD_OWNERSHIP_LOCK = threading.RLock()


os.register_at_fork(
    before=_e5a_before_fork,
    after_in_parent=_e5a_after_fork_parent,
    after_in_child=_e5a_after_fork_child,
)


def _require_live_lease(
    lease: H1RouteWideWorkingSetCgroupLeaseV1,
    *,
    allow_cleanup_pending: bool = False,
) -> H1RouteWideWorkingSetCgroupLeaseV1:
    if type(lease) is not H1RouteWideWorkingSetCgroupLeaseV1:
        _fail("E5A operation requires one exact retained lease")
    if lease._owner_pid != os.getpid():
        _fail("E5A retained lease crossed its owner process")
    with _FD_OWNERSHIP_LOCK:
        allowed_states = (
            {"ACTIVE", "CLEANUP_PENDING"}
            if allow_cleanup_pending
            else {"ACTIVE"}
        )
        if lease._state not in allowed_states:
            _fail("E5A retained lease is not in an allowed live state")
        registry = (
            _LIVE_LEASES
            if lease._state == "ACTIVE"
            else _QUARANTINED_LEASES
        )
        if registry.get(id(lease)) is not lease:
            _fail("E5A retained lease is not live in this process")
    return lease


def _verify_live_hierarchy(lease: H1RouteWideWorkingSetCgroupLeaseV1) -> dict[str, Any]:
    hierarchy = lease._hierarchy_document
    _verify_content_object(
        hierarchy,
        domain=domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN,
        id_field="h1_route_wide_cgroup_hierarchy_id",
        label="E5A hierarchy",
    )
    if (
        hierarchy.get("readiness") != READINESS
        or hierarchy.get("no_route_process_placed") is not True
        or hierarchy.get("h1_route_wide_working_set_cgroup_profile_id")
        != _PROFILE.profile_id
        or hierarchy.get("h1_route_wide_cgroup_topology_plan_id") != _TOPOLOGY_PLAN.plan_id
    ):
        _fail("E5A hierarchy profile or readiness changed")
    delegated_parent = hierarchy.get("delegated_parent")
    if (
        type(delegated_parent) is not dict
        or _fstatfs_magic(lease._parent_fd) != CGROUP2_SUPER_MAGIC
        or _fd_identity(lease._parent_fd, directory=True)
        != delegated_parent.get("identity")
        or sorted(_tokens_control(lease._parent_fd, "cgroup.controllers"))
        != delegated_parent.get("controllers")
        or sorted(_tokens_control(lease._parent_fd, "cgroup.subtree_control"))
        != delegated_parent.get("subtree_controllers")
        or delegated_parent.get("memory_current_scope")
        != "DELEGATION_PREREQUISITE_NOT_ROUTE_OPERAND"
        or delegated_parent.get("memory_current_value_content_bound") is not False
    ):
        _fail("E5A delegated parent identity or controller authority changed")
    outer = hierarchy.get("outer")
    leaves = hierarchy.get("leaves")
    if type(outer) is not dict or type(leaves) is not list or len(leaves) != 3:
        _fail("E5A hierarchy topology document changed")
    outer_identity = _fd_identity(lease._outer_fd, directory=True)
    if outer_identity != outer.get("identity"):
        _fail("E5A outer pinned identity changed")
    _assert_named_identity(lease._parent_fd, lease._outer_name, outer_identity)
    if _child_directories(lease._parent_fd) != (lease._outer_name,):
        _fail("E5A delegated parent gained a foreign or transplanted child")
    allowed_cap = hierarchy.get("enforced_outer_memory_max_bytes")
    if type(allowed_cap) is not int or allowed_cap <= 0:
        _fail("E5A hierarchy allowed cap changed")
    _verify_outer_controls(lease._outer_fd, allowed_cap)
    if _child_directories(lease._outer_fd) != tuple(sorted(CONTROL_NAMES.values())):
        _fail("E5A outer child topology changed")
    live_outer_current = _require_empty_cgroup(
        lease._outer_fd, "E5A outer", memory=True
    )
    assert live_outer_current is not None
    recorded_outer_current = outer.get("memory_current_bytes_at_admission")
    if (
        type(recorded_outer_current) is not int
        or recorded_outer_current < 0
        or outer.get("memory_current_observation_ordinal") != 1
        or outer.get("memory_current_observation_phase")
        != "IMMEDIATELY_AFTER_SINGLE_OUTER_PEAK_RESET"
    ):
        _fail("E5A recorded outer memory.current snapshot changed")
    rows = {row.get("role"): row for row in leaves if type(row) is dict}
    if set(rows) != set(ROLE_ORDER):
        _fail("E5A leaf role rows changed")
    seen: set[tuple[int, int]] = {
        (outer_identity["device"], outer_identity["inode"])
    }
    live_leaf_currents: dict[str, int] = {}
    recorded_leaf_currents: dict[str, int] = {}
    for role in ROLE_ORDER:
        leaf_fd = lease._role_fds[role]
        identity = _fd_identity(leaf_fd, directory=True)
        if identity != rows[role].get("identity"):
            _fail(f"E5A {role} pinned identity changed")
        _assert_named_identity(lease._outer_fd, CONTROL_NAMES[role], identity)
        key = (identity["device"], identity["inode"])
        if key in seen:
            _fail("E5A cgroup identities overlap")
        seen.add(key)
        _verify_leaf_controls(leaf_fd, role)
        live_current = _require_empty_cgroup(
            leaf_fd, f"E5A {role}", memory=True
        )
        assert live_current is not None
        recorded_current = rows[role].get("memory_current_bytes_at_admission")
        if (
            type(recorded_current) is not int
            or recorded_current < 0
            or rows[role].get("memory_current_observation_ordinal")
            != 2 + ROLE_ORDER.index(role)
            or rows[role].get("memory_current_observation_phase")
            != "POST_RESET_SEQUENTIAL_ROUTE_CGROUP_SNAPSHOT"
        ):
            _fail(f"E5A recorded {role} memory.current snapshot changed")
        live_leaf_currents[role] = live_current
        recorded_leaf_currents[role] = recorded_current
    peak_identity = _fd_identity(lease._memory_peak_fd, directory=False)
    peak = hierarchy.get("outer_memory_peak")
    live_peak_text = _read_all_fd(lease._memory_peak_fd).decode("ascii").strip()
    if not re.fullmatch(r"0|[1-9][0-9]*", live_peak_text):
        _fail("E5A live outer memory.peak is malformed")
    live_peak_bytes = int(live_peak_text)
    baseline_peak_bytes = peak.get("baseline_peak_bytes") if type(peak) is dict else None
    if (
        type(peak) is not dict
        or peak_identity != peak.get("identity")
        or _fd_identity(lease._memory_peak_witness_fd, directory=False) != peak_identity
        or not _same_open_file_description(
            lease._memory_peak_fd, lease._memory_peak_witness_fd
        )
        or type(baseline_peak_bytes) is not int
        or baseline_peak_bytes < recorded_outer_current
        or peak.get("baseline_not_below_recorded_outer_memory_current") is not True
        or baseline_peak_bytes > allowed_cap
        or live_peak_bytes < baseline_peak_bytes
        or live_peak_bytes < live_outer_current
        or live_peak_bytes > allowed_cap
        or live_outer_current > allowed_cap
        or any(value > allowed_cap for value in live_leaf_currents.values())
        or any(value > allowed_cap for value in recorded_leaf_currents.values())
        or hierarchy.get(
            "admission_memory_current_values_are_frozen_timepoint_observations"
        )
        is not True
        or hierarchy.get("later_memory_current_values_may_differ") is not True
    ):
        _fail("E5A retained peak or memory.current snapshot semantics changed")
    return hierarchy


def _envelope_payload(
    *,
    hierarchy: Mapping[str, Any],
    hierarchy_id: str,
) -> dict[str, Any]:
    hard_cap = hierarchy["registered_hard_cap_bytes"]
    outer_cap = hierarchy["outer"]["memory_max_bytes"]
    allowed = min(hard_cap, outer_cap)
    return {
        "schema": "acfqp.k7_h1_route_wide_prelaunch_allowed_cap_envelope.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_route_wide_working_set_cgroup_profile_id": _PROFILE.profile_id,
        "h1_route_wide_cgroup_topology_plan_id": _TOPOLOGY_PLAN.plan_id,
        "h1_route_wide_cgroup_hierarchy_id": hierarchy_id,
        "logical_occurrence_id": hierarchy["logical_occurrence_id"],
        "route_attempt_id": hierarchy["route_attempt_id"],
        "decision_point_id": hierarchy["decision_point_id"],
        "BuildEpoch_id": hierarchy["BuildEpoch_id"],
        "current_h1_exclusive_broker_profile_id": hierarchy[
            "current_h1_exclusive_broker_profile_id"
        ],
        "current_h1_e3_bound_output_continuation_profile_id": hierarchy[
            "current_h1_e3_bound_output_continuation_profile_id"
        ],
        "comparison_axis": COMPARISON_AXIS,
        "upper_kind": UPPER_KIND,
        "formula_id": "min_registered_hard_cap_and_enforced_outer_memory_max_v1",
        "registered_hard_cap_bytes": hard_cap,
        "outer_memory_max_bytes": outer_cap,
        "allowed_cap_bytes": allowed,
        "outer_memory_max_enforced_before_launch": True,
        "postrun_peak_used_for_upper": False,
        "e3_child_peak_relabelled": False,
        "runtime_process_placement_present": False,
        "actual_peak_present": False,
        "readiness": READINESS,
        **_locked_claims(),
    }


def prepare_h1_route_wide_working_set_cgroup_v1(
    *,
    delegated_parent_cgroup_fd: int,
    registered_hard_cap_bytes: int,
    requested_outer_memory_max_bytes: int,
    logical_occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    build_epoch_id: str,
    fault: H1RouteWideWorkingSetCgroupFaultV1 = H1RouteWideWorkingSetCgroupFaultV1.NONE,
) -> H1RouteWideWorkingSetCgroupLeaseV1:
    """Create one fresh prelaunch-only E5A hierarchy and retained lease."""

    hard_cap = _positive_cap(registered_hard_cap_bytes, "registered hard cap")
    requested_cap = _positive_cap(
        requested_outer_memory_max_bytes, "requested outer memory.max"
    )
    caller_ids = {
        "logical_occurrence_id": _cid(logical_occurrence_id, "logical occurrence"),
        "route_attempt_id": _cid(route_attempt_id, "route attempt"),
        "decision_point_id": _cid(decision_point_id, "decision point"),
        "BuildEpoch_id": _cid(build_epoch_id, "BuildEpoch"),
    }
    if type(fault) is not H1RouteWideWorkingSetCgroupFaultV1 or fault not in {
        H1RouteWideWorkingSetCgroupFaultV1.NONE,
        H1RouteWideWorkingSetCgroupFaultV1.AFTER_OUTER_CREATION,
        H1RouteWideWorkingSetCgroupFaultV1.AFTER_FIRST_LEAF,
        H1RouteWideWorkingSetCgroupFaultV1.AFTER_COMPLETE_HIERARCHY,
    }:
        _fail("E5A fault injection is not exact")
    if type(delegated_parent_cgroup_fd) is not int or delegated_parent_cgroup_fd < 0:
        _fail("E5A requires one delegated parent cgroup FD")
    allowed_cap = min(hard_cap, requested_cap)
    construction = _ConstructionFDOwnerV1()
    with _FD_OWNERSHIP_LOCK:
        _CONSTRUCTION_FD_OWNERS[id(construction)] = construction
    lease: H1RouteWideWorkingSetCgroupLeaseV1 | None = None
    transferred = False
    outer_created = False
    created_roles: list[str] = []
    nonce = os.urandom(32).hex()
    if _ID.fullmatch(nonce) is None:  # pragma: no cover - OS invariant
        with _FD_OWNERSHIP_LOCK:
            _CONSTRUCTION_FD_OWNERS.pop(id(construction), None)
        _fail("E5A hierarchy nonce is malformed")
    outer_name = f"acfqp-e5a-A-{nonce}"
    try:
        parent_fd = _duplicate_owned_fd(
            construction,
            _PARENT_FD_SLOT,
            delegated_parent_cgroup_fd,
        )
        parent = _require_parent_delegation(parent_fd)
        os.mkdir(outer_name, mode=0o755, dir_fd=parent_fd)
        outer_created = True
        outer_fd = _open_owned_path_fd(
            construction,
            _OUTER_FD_SLOT,
            outer_name,
            os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        if fault is H1RouteWideWorkingSetCgroupFaultV1.AFTER_OUTER_CREATION:
            raise RuntimeError("injected E5A failure after outer creation")
        _require_empty_cgroup(outer_fd, "fresh E5A outer", memory=True)
        if _child_directories(outer_fd):
            _fail("fresh E5A outer unexpectedly contains a child")
        _configure_outer(outer_fd, allowed_cap)
        _verify_outer_controls(outer_fd, allowed_cap)
        for role in ROLE_ORDER:
            name = CONTROL_NAMES[role]
            os.mkdir(name, mode=0o755, dir_fd=outer_fd)
            created_roles.append(role)
            role_fd = _open_owned_path_fd(
                construction,
                _role_fd_slot(role),
                name,
                os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
                dir_fd=outer_fd,
            )
            _configure_leaf(role_fd, role)
            _verify_leaf_controls(role_fd, role)
            _require_empty_cgroup(role_fd, f"fresh E5A {role}", memory=True)
            if (
                role == ROLE_ORDER[0]
                and fault is H1RouteWideWorkingSetCgroupFaultV1.AFTER_FIRST_LEAF
            ):
                raise RuntimeError("injected E5A failure after first leaf")
        _require_empty_cgroup(outer_fd, "fresh configured E5A outer", memory=True)
        (
            peak_fd,
            peak_witness_fd,
            peak_identity,
            baseline_peak_bytes,
            outer_memory_current_bytes_at_admission,
        ) = _open_and_reset_memory_peak(outer_fd, construction)
        role_fds = {
            role: _owner_slot_unlocked(construction, _role_fd_slot(role))
            for role in ROLE_ORDER
        }
        memory_current_bytes_at_admission = {
            "OUTER": outer_memory_current_bytes_at_admission,
            **{
                role: _exact_nonnegative_control(role_fds[role], "memory.current")
                for role in ROLE_ORDER
            },
        }
        if (
            baseline_peak_bytes > allowed_cap
            or any(
                value > allowed_cap
                for value in memory_current_bytes_at_admission.values()
            )
        ):
            _fail("E5A admission memory baseline exceeds the enforced cap")
        if fault is H1RouteWideWorkingSetCgroupFaultV1.AFTER_COMPLETE_HIERARCHY:
            raise RuntimeError("injected E5A failure after complete hierarchy")
        outer_identity = _fd_identity(outer_fd, directory=True)
        role_identities = {
            role: _fd_identity(role_fds[role], directory=True) for role in ROLE_ORDER
        }
        if len(
            {
                (outer_identity["device"], outer_identity["inode"]),
                *(
                    (identity["device"], identity["inode"])
                    for identity in role_identities.values()
                ),
            }
        ) != 4:
            _fail("E5A created overlapping cgroup identities")
        hierarchy_payload = _hierarchy_payload(
            nonce=nonce,
            caller_ids=caller_ids,
            parent=parent,
            outer_name=outer_name,
            outer_identity=outer_identity,
            role_identities=role_identities,
            peak_identity=peak_identity,
            baseline_peak_bytes=baseline_peak_bytes,
            memory_current_bytes_at_admission=memory_current_bytes_at_admission,
            registered_hard_cap_bytes=hard_cap,
            requested_outer_memory_max_bytes=requested_cap,
            allowed_cap_bytes=allowed_cap,
        )
        hierarchy_document = _with_id(
            hierarchy_payload,
            domain=domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN,
            id_field="h1_route_wide_cgroup_hierarchy_id",
        )
        hierarchy_id = hierarchy_document["h1_route_wide_cgroup_hierarchy_id"]
        envelope_document = _with_id(
            _envelope_payload(hierarchy=hierarchy_document, hierarchy_id=hierarchy_id),
            domain=(
                domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN
            ),
            id_field="h1_route_wide_prelaunch_allowed_cap_envelope_id",
        )
        envelope = H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1(
            _ENVELOPE_ISSUER,
            canonical_json_bytes(envelope_document),
        )
        lease = H1RouteWideWorkingSetCgroupLeaseV1(
            _LEASE_ISSUER,
            owner_pid=os.getpid(),
            parent_fd=parent_fd,
            outer_fd=outer_fd,
            role_fds=role_fds,
            memory_peak_fd=peak_fd,
            memory_peak_witness_fd=peak_witness_fd,
            outer_name=outer_name,
            hierarchy_document=hierarchy_document,
            hierarchy_id=hierarchy_id,
            envelope=envelope,
        )
        with _FD_OWNERSHIP_LOCK:
            if _CONSTRUCTION_FD_OWNERS.get(id(construction)) is not construction:
                raise RuntimeError("E5A construction ownership disappeared")
            if any(
                _owner_slot_unlocked(
                    construction, _retry_witness_fd_slot(slot)
                )
                >= 0
                for slot in _CANONICAL_FD_SLOTS
            ):
                raise RuntimeError(
                    "E5A construction transfer retained a close-retry witness"
                )
            transfer_records: list[
                tuple[str, int, _OwnedFDRecordV1]
            ] = []
            for slot in _CANONICAL_FD_SLOTS:
                descriptor = _owner_slot_unlocked(construction, slot)
                record = _OWNED_FDS.get(descriptor)
                if (
                    descriptor < 0
                    or record is None
                    or record.owner is not construction
                    or record.slot != slot
                    or record.identity is None
                ):
                    raise RuntimeError("E5A construction FD transfer was incomplete")
                transfer_records.append((slot, descriptor, record))
            for slot, descriptor, record in transfer_records:
                _OWNED_FDS[descriptor] = _OwnedFDRecordV1(
                    owner=lease,
                    slot=slot,
                    identity=record.identity,
                )
                _set_owner_slot_unlocked(construction, slot, -1)
            construction._state = "TRANSFERRED"
            _CONSTRUCTION_FD_OWNERS.pop(id(construction), None)
            _LIVE_LEASES[id(lease)] = lease
            transferred = True
        try:
            verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(lease)
        except BaseException:
            close_h1_route_wide_working_set_cgroup_lease_v1(lease)
            raise
        return lease
    except BaseException as primary:
        if transferred:
            raise
        cleanup_errors: list[BaseException] = []
        for slot in (_PEAK_WITNESS_FD_SLOT, _PEAK_FD_SLOT):
            error = _close_owned_fd_slot(construction, slot)
            if error is not None:
                cleanup_errors.append(error)
        outer_fd = _owner_slot_unlocked(construction, _OUTER_FD_SLOT)
        if outer_fd >= 0:
            for role in reversed(created_roles):
                try:
                    os.rmdir(CONTROL_NAMES[role], dir_fd=outer_fd)
                except OSError as error:
                    cleanup_errors.append(error)
        for role in ROLE_ORDER:
            error = _close_owned_fd_slot(construction, _role_fd_slot(role))
            if error is not None:
                cleanup_errors.append(error)
        parent_fd = _owner_slot_unlocked(construction, _PARENT_FD_SLOT)
        if outer_created and parent_fd >= 0:
            try:
                os.rmdir(outer_name, dir_fd=parent_fd)
            except OSError as error:
                cleanup_errors.append(error)
        for slot in (_OUTER_FD_SLOT, _PARENT_FD_SLOT):
            error = _close_owned_fd_slot(construction, slot)
            if error is not None:
                cleanup_errors.append(error)
        outstanding = _owned_fd_slots_remaining(construction)
        with _FD_OWNERSHIP_LOCK:
            if outstanding:
                construction._state = "ROLLBACK_QUARANTINED"
            else:
                construction._state = "ROLLED_BACK"
                _CONSTRUCTION_FD_OWNERS.pop(id(construction), None)
        if cleanup_errors:
            raise RuntimeError("E5A construction rollback did not close cleanly") from primary
        raise


def verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(
    lease: H1RouteWideWorkingSetCgroupLeaseV1,
) -> dict[str, Any]:
    """Revalidate the live hierarchy and exact prelaunch envelope."""

    lease = _require_live_lease(lease)
    with lease._lock:
        hierarchy = _verify_live_hierarchy(lease)
        if type(lease._envelope) is not H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1:
            _fail("E5A retained allowed-cap envelope changed type")
        envelope = lease._envelope.to_document()
        payload = _verify_content_object(
            envelope,
            domain=(
                domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN
            ),
            id_field="h1_route_wide_prelaunch_allowed_cap_envelope_id",
            label="E5A allowed-cap envelope",
        )
        expected = _envelope_payload(
            hierarchy=hierarchy,
            hierarchy_id=lease._hierarchy_id,
        )
        if payload != expected:
            _fail("E5A allowed-cap envelope changed or crossed its live hierarchy")
        if (
            payload["upper_kind"] != UPPER_KIND
            or payload["readiness"] != READINESS
            or payload["allowed_cap_bytes"]
            != min(
                payload["registered_hard_cap_bytes"],
                payload["outer_memory_max_bytes"],
            )
            or payload["postrun_peak_used_for_upper"] is not False
            or payload["e3_child_peak_relabelled"] is not False
            or payload["runtime_process_placement_present"] is not False
            or payload["actual_peak_present"] is not False
        ):
            _fail("E5A allowed-cap semantics changed")
        return envelope


def _name_missing(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    return False


def _verify_peak_retention_before_outer_removal(
    lease: H1RouteWideWorkingSetCgroupLeaseV1,
    hierarchy: Mapping[str, Any],
) -> None:
    """Re-prove the two retained peak handles immediately before outer rmdir."""

    peak = hierarchy.get("outer_memory_peak")
    if type(peak) is not dict or type(peak.get("identity")) is not dict:
        _fail("E5A cleanup frozen memory.peak identity changed")
    frozen_identity = peak["identity"]
    with _FD_OWNERSHIP_LOCK:
        primary = lease._memory_peak_fd
        witness = lease._memory_peak_witness_fd
        for slot, descriptor in (
            (_PEAK_FD_SLOT, primary),
            (_PEAK_WITNESS_FD_SLOT, witness),
        ):
            if descriptor < 0:
                _fail("E5A cleanup lost one retained memory.peak descriptor")
            record = _OWNED_FDS.get(descriptor)
            if (
                record is None
                or record.owner is not lease
                or record.slot != slot
                or not _registered_fd_still_exact_unlocked(descriptor, record)
                or _fd_identity(descriptor, directory=False) != frozen_identity
            ):
                _fail("E5A cleanup retained memory.peak identity changed")
        if not _same_open_file_description(primary, witness):
            _fail("E5A cleanup retained memory.peak OFD changed")


def close_h1_route_wide_working_set_cgroup_lease_v1(
    lease: H1RouteWideWorkingSetCgroupLeaseV1,
    *,
    fault: H1RouteWideWorkingSetCgroupFaultV1 = H1RouteWideWorkingSetCgroupFaultV1.NONE,
) -> H1RouteWideWorkingSetCgroupCleanupClosureV1:
    """Identity-check, remove and close one E5A lease; failures are retryable."""

    if type(lease) is not H1RouteWideWorkingSetCgroupLeaseV1:
        _fail("E5A cleanup requires one exact retained lease")
    if type(fault) is not H1RouteWideWorkingSetCgroupFaultV1 or fault not in {
        H1RouteWideWorkingSetCgroupFaultV1.NONE,
        H1RouteWideWorkingSetCgroupFaultV1.CLEANUP_BEFORE_SECOND_CHILD_RMDIR,
    }:
        _fail("E5A cleanup fault injection is not exact")
    if lease._owner_pid != os.getpid():
        _fail("E5A cleanup crossed its owner process")
    if lease._state == "CLOSED" and lease._closure is not None:
        return lease._closure
    lease = _require_live_lease(lease, allow_cleanup_pending=True)
    with lease._lock:
        if lease._state == "CLOSED" and lease._closure is not None:
            return lease._closure
        with _FD_OWNERSHIP_LOCK:
            if lease._state == "ACTIVE":
                if _LIVE_LEASES.get(id(lease)) is not lease:
                    _fail("E5A active cleanup lease left its live registry")
                _LIVE_LEASES.pop(id(lease), None)
                _QUARANTINED_LEASES[id(lease)] = lease
            elif _QUARANTINED_LEASES.get(id(lease)) is not lease:
                _fail("E5A pending cleanup lease left its quarantine registry")
            lease._cleanup_attempts += 1
            lease._state = "CLEANUP_PENDING"
        hierarchy = lease._hierarchy_document
        rows = {row["role"]: row for row in hierarchy["leaves"]}
        removed_this_attempt = 0
        if not lease._outer_removed:
            try:
                # Cleanup deliberately does not trust cap readback: a changed
                # cap invalidates admission but cannot authorize deletion of a
                # foreign identity.
                if (
                    _fstatfs_magic(lease._parent_fd) != CGROUP2_SUPER_MAGIC
                    or _fd_identity(lease._parent_fd, directory=True)
                    != hierarchy["delegated_parent"]["identity"]
                ):
                    _fail("E5A cleanup delegated parent identity changed")
                _require_empty_cgroup(
                    lease._outer_fd, "E5A cleanup outer", memory=True
                )
                for role in reversed(ROLE_ORDER):
                    leaf_fd = lease._role_fds[role]
                    if role in lease._removed_roles:
                        if not _name_missing(lease._outer_fd, CONTROL_NAMES[role]):
                            _fail(f"E5A previously removed {role} name reappeared")
                        continue
                    _require_empty_cgroup(
                        leaf_fd, f"E5A cleanup {role}", memory=True
                    )
                    identity = _fd_identity(leaf_fd, directory=True)
                    if identity != rows[role]["identity"]:
                        _fail(f"E5A cleanup {role} identity changed")
                    _assert_named_identity(
                        lease._outer_fd, CONTROL_NAMES[role], identity
                    )
                    if (
                        fault
                        is H1RouteWideWorkingSetCgroupFaultV1.CLEANUP_BEFORE_SECOND_CHILD_RMDIR
                        and removed_this_attempt == 1
                    ):
                        raise BlockingIOError(
                            errno.EAGAIN,
                            "injected transient E5A second-child rmdir failure",
                        )
                    os.rmdir(CONTROL_NAMES[role], dir_fd=lease._outer_fd)
                    if not _name_missing(lease._outer_fd, CONTROL_NAMES[role]):
                        _fail(f"E5A cleanup did not remove {role}")
                    lease._removed_roles.add(role)
                    removed_this_attempt += 1
                if _child_directories(lease._outer_fd):
                    _fail("E5A cleanup outer retains a child")
                outer_identity = _fd_identity(lease._outer_fd, directory=True)
                if outer_identity != hierarchy["outer"]["identity"]:
                    _fail("E5A cleanup outer identity changed")
                _assert_named_identity(
                    lease._parent_fd, lease._outer_name, outer_identity
                )
                _verify_peak_retention_before_outer_removal(lease, hierarchy)
                os.rmdir(lease._outer_name, dir_fd=lease._parent_fd)
                if not _name_missing(lease._parent_fd, lease._outer_name):
                    _fail("E5A cleanup did not remove the outer cgroup")
                lease._outer_removed = True
            except BaseException:
                with _FD_OWNERSHIP_LOCK:
                    lease._state = "CLEANUP_PENDING"
                raise

        close_errors: list[OSError] = []
        for slot in _CANONICAL_FD_SLOTS:
            error = _close_owned_fd_slot(lease, slot)
            if error is not None:
                close_errors.append(error)
        outstanding = _owned_fd_slots_remaining(lease)
        if close_errors or outstanding:
            with _FD_OWNERSHIP_LOCK:
                lease._state = "CLEANUP_PENDING"
                lease._closure = None
                _QUARANTINED_LEASES[id(lease)] = lease
            first = close_errors[0] if close_errors else None
            raise RuntimeError(
                "E5A hierarchy removed but retained FD close remains live"
            ) from first

        with _FD_OWNERSHIP_LOCK:
            if any(record.owner is lease for record in _OWNED_FDS.values()):
                raise RuntimeError("E5A closed lease retained an FD registry record")
            closure_payload = {
                "schema": "acfqp.k7_h1_route_wide_cgroup_cleanup_closure.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "h1_route_wide_working_set_cgroup_profile_id": _PROFILE.profile_id,
                "h1_route_wide_cgroup_hierarchy_id": lease._hierarchy_id,
                "h1_route_wide_prelaunch_allowed_cap_envelope_id": (
                    lease._envelope.envelope_id
                ),
                "logical_occurrence_id": hierarchy["logical_occurrence_id"],
                "route_attempt_id": hierarchy["route_attempt_id"],
                "decision_point_id": hierarchy["decision_point_id"],
                "BuildEpoch_id": hierarchy["BuildEpoch_id"],
                "cleanup_attempt_count": lease._cleanup_attempts,
                "identity_bound_children_removed": True,
                "identity_bound_outer_removed": True,
                "all_cgroups_empty_before_removal": True,
                "memory_peak_ofd_retained_until_outer_removal": True,
                "memory_peak_reset_repeated": False,
                "actual_peak_issued": False,
                "readiness": READINESS,
                **_locked_claims(),
            }
            closure_document = _with_id(
                closure_payload,
                domain=(
                    domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN
                ),
                id_field="h1_route_wide_cgroup_cleanup_closure_id",
            )
            closure = H1RouteWideWorkingSetCgroupCleanupClosureV1(
                _CLOSURE_ISSUER,
                canonical_json_bytes(closure_document),
            )
            lease._closure = closure
            lease._state = "CLOSED"
            _QUARANTINED_LEASES.pop(id(lease), None)
            _LIVE_LEASES.pop(id(lease), None)
        return closure


if set(
    (
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_PROFILE_V1_DOMAIN,
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_TOPOLOGY_PLAN_V1_DOMAIN,
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN,
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_V1_DOMAIN,
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN,
    )
) != set(domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12):  # pragma: no cover
    raise RuntimeError("E5A source domains crossed the V12 registry")


__all__ = (
    "COMPARISON_AXIS",
    "COUNTER_COMPLETENESS_GATE",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "ConstructionK7H1RouteWideWorkingSetCgroupV1Error",
    "E3_CHILD_PEAK_RELABELLED",
    "E5B_INTEGRATED_LAUNCH_PRESENT",
    "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "FQ11_COUNTER_COMPLETENESS_PRESENT",
    "H1RouteWideWorkingSetCgroupCleanupClosureV1",
    "H1RouteWideWorkingSetCgroupFaultV1",
    "H1RouteWideWorkingSetCgroupLeaseV1",
    "H1RouteWideWorkingSetCgroupProfileV1",
    "H1RouteWideWorkingSetCgroupTopologyPlanV1",
    "H1RouteWideWorkingSetPrelaunchAllowedCapEnvelopeV1",
    "MAX_PLANNED_CONCURRENCY",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OUTER_MAX_DEPTH",
    "OUTER_MAX_DESCENDANTS",
    "OUTER_PIDS_MAX",
    "POSTRUN_PEAK_USED_FOR_UPPER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "ROLE_ORDER",
    "ROLE_PIDS_MAX",
    "ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT",
    "ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_PRESENT",
    "RUNTIME_PROCESS_PLACEMENT_PRESENT",
    "SCHEMA_VERSION",
    "UPPER_KIND",
    "WORKLOAD_ECONOMICS_GATE",
    "close_h1_route_wide_working_set_cgroup_lease_v1",
    "official_h1_route_wide_working_set_cgroup_profile_v1",
    "official_h1_route_wide_working_set_cgroup_topology_plan_v1",
    "prepare_h1_route_wide_working_set_cgroup_v1",
    "verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1",
)
