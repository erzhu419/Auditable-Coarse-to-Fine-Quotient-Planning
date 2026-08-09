"""Bounded B2-B guardian-runtime genesis without any process birth.

The bridge consumes the exact B2-A ``PREPARED_SUCCESSOR`` state in place,
seals the sources and guardian context actually used by this session, pins the
outer ``cgroup.kill`` file, persists one SUPERVISOR intent and one unconsumed
permit, and ends in ``RUNNING``.  It deliberately exposes no clone operation.

The source replay binding is exact for the retained files and process context of this
session, but it is not a production full-source closure: this module can be
fresh-imported and can therefore mint its own self-source expectation without
an independently registered external anchor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import signal
import stat
import struct
import sys
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn
import uuid

from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-B"
PROFILE_KEY = "construction_k7_h1_guardian_runtime_genesis_v1"
READINESS = "BOUNDED_GUARDIAN_RUNTIME_GENESIS_NO_BIRTH"

BOUNDED_GUARDIAN_SOURCE_CLOSURE_PRESENT = True
GUARDIAN_SESSION_PRESENT = True
OUTER_CGROUP_KILL_PIN_PRESENT = True
RUNTIME_RUNNING_STATE_PRESENT = True
UNCONSUMED_SUPERVISOR_BIRTH_PERMIT_PRESENT = True
DISTINCT_CONTROL_OPATH_GRANT_PRESENT = True
AUDIT_ONLY_TRAMPOLINE_SOURCE_CLOSED = True

PRODUCTION_FULL_EXECUTION_SOURCE_CLOSURE_PRESENT = False
EXTERNAL_PREREGISTRATION_ANCHOR_PRESENT = False
ASSEMBLED_OR_EXECUTABLE_TRAMPOLINE_PRESENT = False
PERMIT_CONSUMPTION_PATH_PRESENT = False
CLONE_SYSCALL_PERFORMED = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
PROCESS_LAUNCH_COUNT_AUTHORITY_PRESENT = False
SHARED_PID_CELL_PRESENT = False
PIDFD_ESCROW_PRESENT = False
CGROUP_MEMBERSHIP_OBSERVATION_PRESENT = False
PROCESS_DEATH_OR_REAP_PRESENT = False
PEAK_READ_PRESENT = False
ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

_EXPECTED_UPSTREAM_SHA256 = MappingProxyType(
    {
        "b2a": "4277e529079b71c2fa48b7bd845b757b16af4fa163b589964dcfafe9b31ec11e",
        "e5a": "768b3cae4d7ed5edadb6596e3463e54022e54cacb3522a91381c751aaefe7d56",
        "v15": "a54493f6431e0a5fa57afdc18bd185802f434ef88d88299285d0e1f40e0e0469",
        "phase3e_ids": "3eb435bfec4692961d61b4edf6e067cc128810509b5e35ec1d7348079288c4c2",
        "trampoline_audit_source": "83ee8434bd99cf046fe85d6975886c6cbeb2b8cadd5c19edf1bc2bd4deacbf91",
    }
)
_SELF_SOURCE_PATH = Path(__file__).resolve(strict=True)
_TRAMPOLINE_SOURCE_PATH = (
    _SELF_SOURCE_PATH.parent
    / "native"
    / "h1_guardian_clone3_trampoline_x86_64_v1.S"
).resolve(strict=True)
_SOURCE_PATHS = MappingProxyType(
    {
        "guardian_b2b": _SELF_SOURCE_PATH,
        "b2a": Path(b2a_v1.__file__).resolve(strict=True),
        "e5a": Path(e5a_v1.__file__).resolve(strict=True),
        "v15": Path(domains_v15.__file__).resolve(strict=True),
        "phase3e_ids": Path(ids_v1.__file__).resolve(strict=True),
        "trampoline_audit_source": _TRAMPOLINE_SOURCE_PATH,
    }
)
_SELF_IMPORT_STATUS = _SELF_SOURCE_PATH.stat()
_SELF_IMPORT_FACT = MappingProxyType(
    {
        "sha256": hashlib.sha256(_SELF_SOURCE_PATH.read_bytes()).hexdigest(),
        "device": _SELF_IMPORT_STATUS.st_dev,
        "inode": _SELF_IMPORT_STATUS.st_ino,
        "mode": _SELF_IMPORT_STATUS.st_mode,
        "size": _SELF_IMPORT_STATUS.st_size,
    }
)

_CLONE3_SYSCALL_X86_64 = 435
_CLONE_ARGS_SIZE = 88
_CLONE_ARGS_FIELDS = (
    "flags",
    "pidfd",
    "child_tid",
    "parent_tid",
    "exit_signal",
    "stack",
    "stack_size",
    "tls",
    "set_tid",
    "set_tid_size",
    "cgroup",
)
_CLONE_PIDFD = 0x00001000
_CLONE_PARENT_SETTID = 0x00100000
_CLONE_CLEAR_SIGHAND = 0x100000000
_CLONE_INTO_CGROUP = 0x200000000
_REGISTERED_CLONE_FLAGS = (
    _CLONE_PIDFD
    | _CLONE_PARENT_SETTID
    | _CLONE_CLEAR_SIGHAND
    | _CLONE_INTO_CGROUP
)
_ARGV_ENVIRONMENT_INPUT_ALLOWLIST: tuple[str, ...] = ()

_SESSION_ISSUER = object()
_PREREG_ISSUER = object()
_PERMIT_ISSUER = object()
_RECORD_ISSUER = object()
_B2B_LOCK = threading.RLock()
_LIVE_SESSIONS: dict[int, "H1GuardianRuntimeGenesisV1"] = {}
_QUARANTINED_SESSIONS: dict[int, "H1GuardianRuntimeGenesisV1"] = {}
_STARTING_BY_THREAD: dict[int, "H1GuardianRuntimeGenesisV1"] = {}
_RUNTIME_RESERVATIONS: dict[int, "H1GuardianRuntimeGenesisV1"] = {}

_RAW_OS_CLOSE = os.close
_OS_CLOSE = os.close
_OS_OPEN = os.open
_OS_WRITE = os.write
_FCNTL_FCNTL = fcntl.fcntl
_TEST_ONLY_COMMIT_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT = False
_TEST_ONLY_PRECOMMIT_ABORT_FAILURE = False
_TEST_ONLY_CLOSURE_COMMIT_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_POST_STARTING_POP_FAULT = False
_TEST_ONLY_PERSIST_FAULT_PHASE: str | None = None
_TEST_ONLY_PERSIST_FAULT_EVENT: str | None = None
_TEST_ONLY_CLEANUP_BOUNDARY_HOOK: Any = None

_UPSTREAM_CALLABLES = MappingProxyType(
    {
        ("b2a", name): (
            getattr(b2a_v1, name),
            getattr(b2a_v1, name).__code__,
        )
        for name in (
            "_same_owner_context",
            "_validate_e5a_bridge",
            "_verify_source_lease_retired",
            "_verify_runtime_fd_registry_unlocked",
            "close_h1_e5a_runtime_lease_successor_v1",
        )
    }
    | {
        ("e5a", name): (
            getattr(e5a_v1, name),
            getattr(e5a_v1, name).__code__,
        )
        for name in (
            "_registry_fd_identity",
            "_registered_fd_still_exact_unlocked",
            "_enter_fork_forbidden",
            "_leave_fork_forbidden",
            "_block_fd_publication_signals",
            "_restore_fd_publication_signals",
            "_verify_live_hierarchy",
            "_same_open_file_description_for_close",
        )
    }
    | {
        ("v15", "extension_content_id_v15"): (
            domains_v15.extension_content_id_v15,
            domains_v15.extension_content_id_v15.__code__,
        ),
        ("ids", "parse_content_id"): (
            ids_v1.parse_content_id,
            ids_v1.parse_content_id.__code__,
        ),
        ("ids", "canonical_json_bytes"): (
            ids_v1.canonical_json_bytes,
            ids_v1.canonical_json_bytes.__code__,
        ),
        ("ids", "loads_canonical_json"): (
            ids_v1.loads_canonical_json,
            ids_v1.loads_canonical_json.__code__,
        ),
    }
)
_UPSTREAM_GLOBALS = MappingProxyType(
    {
        ("b2a", "_ADAPTER_LOCK"): b2a_v1._ADAPTER_LOCK,
        ("b2a", "_LIVE_RUNTIME_LEASES"): b2a_v1._LIVE_RUNTIME_LEASES,
        ("b2a", "_QUARANTINED_RUNTIME_LEASES"): b2a_v1._QUARANTINED_RUNTIME_LEASES,
        ("b2a", "_LIVE_GRANTS"): b2a_v1._LIVE_GRANTS,
        ("b2a", "H1E5ARuntimeLeaseSuccessorV1"): b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
        ("e5a", "_FD_OWNERSHIP_LOCK"): e5a_v1._FD_OWNERSHIP_LOCK,
        ("e5a", "_OWNED_FDS"): e5a_v1._OWNED_FDS,
    }
)
_EXPECTED_B2A_RUNTIME_SLOTS = tuple(b2a_v1.H1E5ARuntimeLeaseSuccessorV1.__slots__)
_SELF_CALLABLES: Mapping[str, tuple[Any, Any]] = MappingProxyType({})


class ConstructionK7H1GuardianRuntimeGenesisV1Error(ValueError):
    """The B2-B source, identity, descriptor, or one-way state was crossed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_handle: "H1GuardianRuntimeGenesisV1 | None" = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_handle = cleanup_handle


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1GuardianRuntimeGenesisV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return ids_v1.parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
            f"{label} is not one exact lowercase content ID"
        ) from error


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v15.extension_content_id_v15(domain, payload)


def _validate_live_code_closure() -> None:
    modules = {
        "b2a": b2a_v1,
        "e5a": e5a_v1,
        "v15": domains_v15,
        "ids": ids_v1,
    }
    for (module_name, name), (expected, expected_code) in _UPSTREAM_CALLABLES.items():
        live = getattr(modules[module_name], name, None)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not modules[module_name].__dict__
            or getattr(live, "__code__", None) is not expected_code
        ):
            _fail(f"B2-B live-code callable identity changed: {module_name}.{name}")
    for (module_name, name), expected in _UPSTREAM_GLOBALS.items():
        if getattr(modules[module_name], name, None) is not expected:
            _fail(f"B2-B live-code global identity changed: {module_name}.{name}")
    for name, (expected, expected_code) in _SELF_CALLABLES.items():
        live = globals().get(name)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not globals()
            or getattr(live, "__code__", None) is not expected_code
        ):
            _fail(f"B2-B self live-code callable identity changed: {name}")
    if tuple(b2a_v1.H1E5ARuntimeLeaseSuccessorV1.__slots__) != _EXPECTED_B2A_RUNTIME_SLOTS:
        _fail("B2-B source runtime layout changed")
    for label, expected_digest in _EXPECTED_UPSTREAM_SHA256.items():
        path = _SOURCE_PATHS[label]
        try:
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                "B2-B could not replay one externally expected source"
            ) from error
        if observed != expected_digest:
            _fail(f"B2-B externally expected source changed: {label}")
    self_status = _SELF_SOURCE_PATH.stat()
    if (
        hashlib.sha256(_SELF_SOURCE_PATH.read_bytes()).hexdigest()
        != _SELF_IMPORT_FACT["sha256"]
        or (
            self_status.st_dev,
            self_status.st_ino,
            self_status.st_mode,
            self_status.st_size,
        )
        != (
            _SELF_IMPORT_FACT["device"],
            _SELF_IMPORT_FACT["inode"],
            _SELF_IMPORT_FACT["mode"],
            _SELF_IMPORT_FACT["size"],
        )
    ):
        _fail("B2-B self source changed after import")


def _locked_claims() -> dict[str, Any]:
    return {
        "production_full_execution_source_closure_present": False,
        "fresh_import_self_minting_externally_anchored": False,
        "external_preregistration_anchor_present": False,
        "assembled_or_executable_trampoline_present": False,
        "permit_consumption_path_present": False,
        "clone_syscall_performed": False,
        "actual_process_birth_present": False,
        "process_launch_count_authority_present": False,
        "shared_pid_cell_present": False,
        "pidfd_escrow_present": False,
        "cgroup_membership_observation_present": False,
        "process_death_or_reap_present": False,
        "peak_read_present": False,
        "route_wide_actual_peak_authority_present": False,
        "actual_observed_e3_v2_completion_present": False,
        "production_shared_resource_receipts_present": False,
        "fq11_counter_completeness_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_actual_projection_proof_issued": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def _read_process_start_ticks() -> int:
    raw = Path("/proc/self/stat").read_bytes()
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split() if close >= 0 else []
    if len(fields) < 20 or not fields[19].isdigit():
        _fail("guardian process start-tick identity is unavailable")
    return int(fields[19])


def _single_thread_identity() -> dict[str, Any]:
    native_id = threading.get_native_id()
    task_ids = sorted(
        int(name) for name in os.listdir("/proc/self/task") if name.isdigit()
    )
    if task_ids != [native_id] or threading.active_count() != 1:
        _fail("B2-B guardian genesis requires one exact live thread")
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii"
        ).strip()
        if str(uuid.UUID(boot_id)) != boot_id:
            _fail("guardian boot identity is not one canonical UUID")
    except (OSError, ValueError) as error:
        raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
            "guardian boot identity is unavailable"
        ) from error
    return {
        "pid": os.getpid(),
        "process_start_ticks": _read_process_start_ticks(),
        "python_thread_ident": threading.get_ident(),
        "native_thread_id": native_id,
        "thread_name": threading.current_thread().name,
        "single_thread_task_ids": task_ids,
        "real_uid": os.getuid(),
        "effective_uid": os.geteuid(),
        "real_gid": os.getgid(),
        "effective_gid": os.getegid(),
        "supplementary_groups": sorted(os.getgroups()),
        "kernel_boot_id": boot_id,
    }


def _namespace_links() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in ("cgroup", "mnt", "pid", "user"):
        try:
            result[name] = os.readlink(f"/proc/self/ns/{name}")
        except OSError as error:
            raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                "guardian namespace identity is unavailable"
            ) from error
    return result


def _platform_contract() -> dict[str, Any]:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        _fail("B2-B audit contract is registered only for Linux x86_64")
    if sys.byteorder != "little" or struct.calcsize("P") != 8:
        _fail("B2-B guardian ABI is not little-endian LP64")
    return {
        "operating_system": "Linux",
        "machine": "x86_64",
        "byteorder": "little",
        "pointer_size": 8,
        "python_implementation": platform.python_implementation(),
        "python_cache_tag": sys.implementation.cache_tag,
        "clone3_syscall_number": _CLONE3_SYSCALL_X86_64,
        "clone_args_size": _CLONE_ARGS_SIZE,
        "clone_args_field_order": list(_CLONE_ARGS_FIELDS),
        "clone_args_field_offsets": {
            name: index * 8 for index, name in enumerate(_CLONE_ARGS_FIELDS)
        },
        "registered_clone_flags": _REGISTERED_CLONE_FLAGS,
        "registered_exit_signal": int(signal.SIGCHLD),
        "audit_source_is_not_assembled_or_executable": True,
    }


def _prereg_payload(
    *,
    guardian: Mapping[str, Any],
    namespaces: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_genesis_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "argv_environment_input_allowlist": list(
            _ARGV_ENVIRONMENT_INPUT_ALLOWLIST
        ),
        "argv_observed_or_used": False,
        "environment_observed_or_used": False,
        "argv_environment_values_or_digests_persisted": False,
        "expected_guardian_identity": dict(guardian),
        "expected_namespace_links": dict(sorted(namespaces.items())),
        "platform_and_clone_abi": _platform_contract(),
        "trampoline_audit_source_sha256": _EXPECTED_UPSTREAM_SHA256[
            "trampoline_audit_source"
        ],
        "preregistration_is_externally_anchored": False,
        **_locked_claims(),
    }


@dataclass(frozen=True, slots=True)
class H1GuardianRuntimeGenesisPreregistrationV1:
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str = field(init=False)
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._issuer is not _PREREG_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("B2-B preregistration is caller-minted")
        document = ids_v1.loads_canonical_json(self.canonical_bytes)
        supplied = document.pop("guardian_runtime_genesis_preregistration_id", None)
        if type(supplied) is not str or _domain_id(
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN,
            document,
        ) != supplied:
            _fail("B2-B preregistration content changed")
        object.__setattr__(self, "preregistration_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


def preregister_h1_guardian_runtime_genesis_v1() -> H1GuardianRuntimeGenesisPreregistrationV1:
    """Freeze the current single-thread context; this is not an external anchor."""

    _validate_live_code_closure()
    payload = _prereg_payload(
        guardian=_single_thread_identity(),
        namespaces=_namespace_links(),
    )
    document = dict(payload)
    document["guardian_runtime_genesis_preregistration_id"] = _domain_id(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN,
        payload,
    )
    return H1GuardianRuntimeGenesisPreregistrationV1(
        ids_v1.canonical_json_bytes(document), _issuer=_PREREG_ISSUER
    )


def _verify_preregistration(
    preregistration: H1GuardianRuntimeGenesisPreregistrationV1,
) -> dict[str, Any]:
    _validate_live_code_closure()
    if type(preregistration) is not H1GuardianRuntimeGenesisPreregistrationV1:
        _fail("B2-B requires one exact preregistration")
    document = preregistration.to_document()
    payload = dict(document)
    supplied = payload.pop("guardian_runtime_genesis_preregistration_id")
    if _domain_id(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN,
        payload,
    ) != supplied:
        _fail("B2-B preregistration ID changed")
    expected = _prereg_payload(
        guardian=_single_thread_identity(),
        namespaces=_namespace_links(),
    )
    if payload != expected:
        _fail("B2-B guardian argv, environment, identity, ABI, or namespace changed")
    return document


@dataclass(frozen=True, slots=True)
class _ManagedFDRecordV1:
    owner: Any = field(repr=False, compare=False)
    slot: str
    identity: tuple[int, int, int, int, int] | None


_MANAGED_FDS: dict[int, _ManagedFDRecordV1] = {}


@dataclass(frozen=True, slots=True)
class H1GuardianRuntimeRecordV1:
    canonical_bytes: bytes = field(repr=False)
    record_id: str
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RECORD_ISSUER
            or type(self.canonical_bytes) is not bytes
            or type(self.record_id) is not str
        ):
            _fail("B2-B durable record is caller-minted")

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


@dataclass(slots=True)
class _PendingJournalRecordV1:
    """Exact in-memory truth for one opened but not yet frozen record."""

    index: int
    event: str
    filename: str
    slot: str
    target_field: str
    raw: bytes = field(repr=False)
    record: H1GuardianRuntimeRecordV1 = field(repr=False)
    injected_fault_phase: str | None = None


class H1SupervisorBirthPermitV1:
    """Uncopyable unconsumed permit; B2-B intentionally has no consumer."""

    __slots__ = ("_session_id", "_canonical_bytes", "_issuer")

    def __init__(self, issuer: object, session: "H1GuardianRuntimeGenesisV1", raw: bytes) -> None:
        if issuer is not _PERMIT_ISSUER:
            _fail("B2-B SUPERVISOR permit is caller-minted")
        self._session_id = id(session)
        self._canonical_bytes = raw
        self._issuer = issuer

    @property
    def state(self) -> str:
        session = _LIVE_SESSIONS.get(self._session_id)
        if session is None:
            session = _QUARANTINED_SESSIONS.get(self._session_id)
        if session is None or session._permit is not self:
            return "REVOKED_OR_CLOSED"
        return "ISSUED_UNCONSUMED" if session._state == "RUNNING" else "REVOKED"

    @property
    def launch_authority_in_this_slice(self) -> bool:
        return False

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self._canonical_bytes)

    def __copy__(self) -> NoReturn:
        _fail("B2-B SUPERVISOR permit cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-B SUPERVISOR permit cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-B SUPERVISOR permit cannot be copied or pickled")


class H1GuardianRuntimeGenesisV1:
    __slots__ = (
        "_owner_pid",
        "_owner_thread",
        "_owner_thread_id",
        "_runtime",
        "_preregistration",
        "_journal_path",
        "_fd_slots",
        "_fd_order",
        "_source_facts",
        "_context_facts",
        "_record_facts",
        "_journal_names",
        "_records",
        "_pending_record",
        "_state",
        "_source_closure",
        "_genesis",
        "_intent",
        "_permit_record",
        "_permit",
        "_revoke",
        "_b2a_closure",
        "_start_token",
    )

    def __init__(
        self,
        issuer: object,
        *,
        runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
        preregistration: H1GuardianRuntimeGenesisPreregistrationV1,
        journal_path: Path,
        start_token: object,
    ) -> None:
        if issuer is not _SESSION_ISSUER:
            _fail("B2-B guardian session is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._runtime = runtime
        self._preregistration = preregistration
        self._journal_path = journal_path
        self._fd_slots: dict[str, int] = {}
        self._fd_order: list[str] = []
        self._source_facts: dict[str, dict[str, Any]] = {}
        self._context_facts: dict[str, dict[str, Any]] = {}
        self._record_facts: dict[str, dict[str, Any]] = {}
        self._journal_names: set[str] = set()
        self._records: list[H1GuardianRuntimeRecordV1] = []
        self._pending_record: _PendingJournalRecordV1 | None = None
        self._state = "PREPARING"
        self._source_closure: H1GuardianRuntimeRecordV1 | None = None
        self._genesis: H1GuardianRuntimeRecordV1 | None = None
        self._intent: H1GuardianRuntimeRecordV1 | None = None
        self._permit_record: H1GuardianRuntimeRecordV1 | None = None
        self._permit: H1SupervisorBirthPermitV1 | None = None
        self._revoke: H1GuardianRuntimeRecordV1 | None = None
        self._b2a_closure: b2a_v1.H1E5ARuntimeLeaseClosureV1 | None = None
        self._start_token = start_token

    @property
    def state(self) -> str:
        return self._state

    @property
    def permit(self) -> H1SupervisorBirthPermitV1:
        if self._state != "RUNNING" or self._permit is None:
            _fail("B2-B session has no live unconsumed permit")
        return self._permit

    @property
    def session_id(self) -> str:
        if self._genesis is None:
            _fail("B2-B session genesis is unavailable")
        return self._genesis.record_id

    def _poison_after_fork_child(self) -> None:
        for slot in self._fd_slots:
            self._fd_slots[slot] = -1
        self._state = "FORK_POISONED"

    def __copy__(self) -> NoReturn:
        _fail("B2-B guardian session cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-B guardian session cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-B guardian session cannot be copied or pickled")


def _same_owner(session: H1GuardianRuntimeGenesisV1) -> bool:
    return (
        session._owner_pid == os.getpid()
        and session._owner_thread_id == threading.get_ident()
        and session._owner_thread is threading.current_thread()
    )


def _add_slot(session: H1GuardianRuntimeGenesisV1, slot: str) -> None:
    if slot in session._fd_slots or f"retry-witness:{slot}" in session._fd_slots:
        _fail("B2-B descriptor slot is duplicate")
    session._fd_slots[slot] = -1
    session._fd_slots[f"retry-witness:{slot}"] = -1
    session._fd_order.append(slot)


def _publish_fd(session: H1GuardianRuntimeGenesisV1, slot: str, descriptor: int) -> None:
    if session._fd_slots.get(slot) != -1 or descriptor < 0:
        _fail("B2-B descriptor publication crossed its slot")
    if descriptor in _MANAGED_FDS or descriptor in e5a_v1._OWNED_FDS:
        # A returned number can overlap a registry entry only after external
        # close/reuse corruption.  Never transfer or silently retire the old
        # authority here.
        _fail("B2-B opened descriptor collided with registered ownership")
    session._fd_slots[slot] = descriptor
    # Publish before the first fallible fstat/fdinfo identity derivation.  A
    # fork child and precommit rollback can therefore always see the opened
    # number, even if identity upgrade fails.
    _MANAGED_FDS[descriptor] = _ManagedFDRecordV1(session, slot, None)
    identity = e5a_v1._registry_fd_identity(descriptor)
    _MANAGED_FDS[descriptor] = _ManagedFDRecordV1(session, slot, identity)


def _open_managed_fd(
    session: H1GuardianRuntimeGenesisV1,
    slot: str,
    path: str | Path,
    flags: int,
    *,
    mode: int | None = None,
    dir_fd: int | None = None,
) -> int:
    _add_slot(session, slot)
    e5a_v1._enter_fork_forbidden()
    try:
        original_mask = e5a_v1._block_fd_publication_signals()
        descriptor = -1
        witness = -1
        try:
            try:
                if dir_fd is None and mode is None:
                    descriptor = _OS_OPEN(path, flags)
                elif dir_fd is None:
                    descriptor = _OS_OPEN(path, flags, mode)
                elif mode is None:
                    descriptor = _OS_OPEN(path, flags, dir_fd=dir_fd)
                else:
                    descriptor = _OS_OPEN(path, flags, mode, dir_fd=dir_fd)
                _publish_fd(session, slot, descriptor)
                witness_slot = f"retry-witness:{slot}"
                witness = int(
                    _FCNTL_FCNTL(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
                )
                _publish_fd(session, witness_slot, witness)
                if not e5a_v1._same_open_file_description_for_close(
                    descriptor, witness
                ):
                    _fail("B2-B lifetime witness is not the same OFD")
            finally:
                e5a_v1._restore_fd_publication_signals(original_mask)
        except BaseException:
            if witness >= 0:
                witness_record = _MANAGED_FDS.get(witness)
                if (
                    witness_record is None
                    or witness_record.owner is not session
                    or witness_record.slot != f"retry-witness:{slot}"
                ):
                    try:
                        _RAW_OS_CLOSE(witness)
                    except OSError:
                        pass
            if descriptor >= 0:
                record = _MANAGED_FDS.get(descriptor)
                if descriptor in e5a_v1._OWNED_FDS:
                    try:
                        _RAW_OS_CLOSE(descriptor)
                    except OSError:
                        pass
                elif record is None:
                    _publish_fd(session, slot, descriptor)
                elif record.owner is not session or record.slot != slot:
                    # The syscall returned a number whose stale registry entry
                    # belongs elsewhere.  The just-opened FD is still inside
                    # the fork/signal exclusion window and can be raw-closed;
                    # the displaced authority remains quarantined unchanged.
                    try:
                        _RAW_OS_CLOSE(descriptor)
                    except OSError:
                        pass
            raise
        return descriptor
    finally:
        e5a_v1._leave_fork_forbidden()


def _verify_managed_fd(session: H1GuardianRuntimeGenesisV1, slot: str) -> int:
    descriptor = session._fd_slots.get(slot, -1)
    record = _MANAGED_FDS.get(descriptor)
    witness_slot = f"retry-witness:{slot}"
    witness = session._fd_slots.get(witness_slot, -1)
    witness_record = _MANAGED_FDS.get(witness)
    if (
        descriptor < 0
        or record is None
        or record.owner is not session
        or record.slot != slot
        or not e5a_v1._registered_fd_still_exact_unlocked(descriptor, record)
        or witness < 0
        or witness_record is None
        or witness_record.owner is not session
        or witness_record.slot != witness_slot
        or not e5a_v1._registered_fd_still_exact_unlocked(
            witness, witness_record
        )
        or not e5a_v1._same_open_file_description_for_close(
            descriptor, witness
        )
    ):
        _fail("B2-B managed descriptor identity changed")
    return descriptor


def _read_all(descriptor: int, cap: int = 4 * 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while True:
        chunk = os.pread(descriptor, min(65536, cap + 1 - offset), offset)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        offset += len(chunk)
        if offset > cap:
            _fail("B2-B retained source or record exceeded its cap")


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = _OS_WRITE(descriptor, raw[offset:])
        if written <= 0:
            _fail("B2-B durable journal write made no progress")
        offset += written


def _cleanup_boundary(
    phase: str,
    session: H1GuardianRuntimeGenesisV1,
    slot: str | None = None,
) -> None:
    hook = _TEST_ONLY_CLEANUP_BOUNDARY_HOOK
    if hook is not None:
        hook(phase, session, slot)


def _inject_persist_fault_if_registered(
    pending: _PendingJournalRecordV1, phase: str
) -> None:
    if (
        _TEST_ONLY_PERSIST_FAULT_PHASE == phase
        and _TEST_ONLY_PERSIST_FAULT_EVENT == pending.event
        and pending.injected_fault_phase is None
    ):
        # Mark first.  The retry exercises recovery rather than repeatedly
        # replaying the same synthetic interruption forever.
        pending.injected_fault_phase = phase
        raise RuntimeError(f"injected B2-B journal fault {phase}")


def _ensure_pending_record_fd(
    session: H1GuardianRuntimeGenesisV1,
    pending: _PendingJournalRecordV1,
    directory_fd: int,
) -> int:
    """Open once with O_EXCL, or replay the exact retained OFD after failure."""

    if pending.slot not in session._fd_slots:
        descriptor = _open_managed_fd(
            session,
            pending.slot,
            pending.filename,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            mode=0o400,
            dir_fd=directory_fd,
        )
        _inject_persist_fault_if_registered(pending, "AFTER_OPEN")
        return descriptor

    descriptor = session._fd_slots[pending.slot]
    witness_slot = f"retry-witness:{pending.slot}"
    witness = session._fd_slots[witness_slot]
    if descriptor < 0:
        if witness >= 0:
            _fail("B2-B pending journal record lost its canonical descriptor")
        # The first open failed before publishing any descriptor.  Reuse only
        # the exact empty slots and repeat O_EXCL; an existing name is never
        # guessed to be ours and therefore fails closed.
        session._fd_slots.pop(pending.slot)
        session._fd_slots.pop(witness_slot)
        if not session._fd_order or session._fd_order[-1] != pending.slot:
            _fail("B2-B pending journal slot order changed")
        session._fd_order.pop()
        return _ensure_pending_record_fd(session, pending, directory_fd)

    record = _MANAGED_FDS.get(descriptor)
    if record is None or record.owner is not session or record.slot != pending.slot:
        _fail("B2-B pending journal descriptor ownership changed")
    identity = e5a_v1._registry_fd_identity(descriptor)
    _MANAGED_FDS[descriptor] = _ManagedFDRecordV1(
        session, pending.slot, identity
    )
    if witness < 0:
        e5a_v1._enter_fork_forbidden()
        try:
            original_mask = e5a_v1._block_fd_publication_signals()
            opened_witness = -1
            try:
                opened_witness = int(
                    _FCNTL_FCNTL(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
                )
                _publish_fd(session, witness_slot, opened_witness)
            finally:
                e5a_v1._restore_fd_publication_signals(original_mask)
        except BaseException:
            if opened_witness >= 0 and opened_witness not in _MANAGED_FDS:
                _publish_fd(session, witness_slot, opened_witness)
            raise
        finally:
            e5a_v1._leave_fork_forbidden()
    return _verify_managed_fd(session, pending.slot)


def _finish_pending_record(
    session: H1GuardianRuntimeGenesisV1,
    pending: _PendingJournalRecordV1,
    fact: dict[str, Any],
) -> H1GuardianRuntimeRecordV1:
    """Finish-forward the in-memory record publication idempotently."""

    if session._pending_record is not pending:
        _fail("B2-B pending journal transaction identity changed")
    existing_fact = session._record_facts.get(pending.filename)
    if existing_fact is not None and existing_fact != fact:
        _fail("B2-B pending journal facts changed during finish-forward")
    session._journal_names.add(pending.filename)
    session._record_facts[pending.filename] = fact
    if len(session._records) == pending.index:
        session._records.append(pending.record)
    elif (
        len(session._records) <= pending.index
        or session._records[pending.index] is not pending.record
    ):
        _fail("B2-B pending journal record order changed")
    current = getattr(session, pending.target_field)
    if current is None:
        setattr(session, pending.target_field, pending.record)
    elif current is not pending.record:
        _fail("B2-B pending journal target field changed")
    session._pending_record = None
    return pending.record


def _resume_pending_record(
    session: H1GuardianRuntimeGenesisV1,
) -> H1GuardianRuntimeRecordV1:
    """Recover one exact partial/full record without unlinking or name adoption."""

    pending = session._pending_record
    if pending is None:
        _fail("B2-B has no pending journal transaction to resume")
    directory_fd = _verify_managed_fd(session, "journal:directory")
    descriptor = _ensure_pending_record_fd(session, pending, directory_fd)
    status = os.fstat(descriptor)
    named = os.stat(pending.filename, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(status.st_mode)
        or stat.S_IMODE(status.st_mode) != 0o400
        or status.st_nlink != 1
        or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
    ):
        _fail("B2-B pending durable record identity changed")

    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    if (
        _TEST_ONLY_PERSIST_FAULT_PHASE == "AFTER_PARTIAL_WRITE"
        and _TEST_ONLY_PERSIST_FAULT_EVENT == pending.event
        and pending.injected_fault_phase is None
    ):
        prefix_length = max(1, len(pending.raw) // 2)
        _write_all(descriptor, pending.raw[:prefix_length])
        _inject_persist_fault_if_registered(pending, "AFTER_PARTIAL_WRITE")
    _write_all(descriptor, pending.raw)
    _inject_persist_fault_if_registered(pending, "AFTER_FULL_WRITE")
    os.fsync(descriptor)
    _inject_persist_fault_if_registered(pending, "AFTER_FILE_FSYNC")
    os.fsync(directory_fd)
    _inject_persist_fault_if_registered(pending, "AFTER_DIRECTORY_FSYNC")
    status = os.fstat(descriptor)
    named = os.stat(pending.filename, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(status.st_mode)
        or stat.S_IMODE(status.st_mode) != 0o400
        or status.st_nlink != 1
        or status.st_size != len(pending.raw)
        or os.pread(descriptor, len(pending.raw) + 1, 0) != pending.raw
        or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
    ):
        _fail("B2-B durable record changed before freeze")
    fact = {
        "slot": pending.slot,
        "sha256": hashlib.sha256(pending.raw).hexdigest(),
        "byte_count": len(pending.raw),
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": status.st_mode,
        "nlink": status.st_nlink,
        "size": status.st_size,
    }
    return _finish_pending_record(session, pending, fact)


def _seal_source_files(session: H1GuardianRuntimeGenesisV1) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for label, path in _SOURCE_PATHS.items():
        slot = f"source:{label}"
        descriptor = _open_managed_fd(
            session,
            slot,
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        metadata = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
        raw = _read_all(descriptor)
        digest = hashlib.sha256(raw).hexdigest()
        expected = (
            _SELF_IMPORT_FACT["sha256"]
            if label == "guardian_b2b"
            else _EXPECTED_UPSTREAM_SHA256.get(label)
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != (named.st_dev, named.st_ino)
            or (expected is not None and digest != expected)
        ):
            _fail("B2-B retained execution source changed")
        line_count = len(raw.splitlines())
        fact = {
            "label": label,
            "resolved_path": str(path),
            "sha256": digest,
            "byte_count": len(raw),
            "read_line_start": 1,
            "read_line_end": line_count,
            "whole_retained_file_was_read": True,
            "externally_expected_sha256": expected,
            "self_source_import_time_bound_but_external_anchor_present": (
                label != "guardian_b2b"
            ),
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": metadata.st_mode,
            "size": metadata.st_size,
        }
        session._source_facts[slot] = fact
        entries.append(fact)
    return entries


def _pin_guardian_context(session: H1GuardianRuntimeGenesisV1) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name in ("cgroup", "mnt", "pid", "user"):
        slot = f"namespace:{name}"
        descriptor = _open_managed_fd(
            session, slot, f"/proc/self/ns/{name}", os.O_RDONLY | os.O_CLOEXEC
        )
        fact = {
            "slot": slot,
            "name": name,
            "proc_path": f"/proc/self/ns/{name}",
            "link": os.readlink(f"/proc/self/ns/{name}"),
            "identity": list(e5a_v1._registry_fd_identity(descriptor)),
        }
        session._context_facts[slot] = fact
        entries.append(fact)
    exe = _open_managed_fd(
        session, "guardian:exe", "/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC
    )
    fact = {
        "slot": "guardian:exe",
        "name": "executable",
        "proc_path": "/proc/self/exe",
        "link": os.readlink("/proc/self/exe"),
        "identity": list(e5a_v1._registry_fd_identity(exe)),
    }
    session._context_facts["guardian:exe"] = fact
    entries.append(fact)
    return entries


def _persist_record(
    session: H1GuardianRuntimeGenesisV1,
    *,
    domain: str,
    id_field: str,
    event: str,
    target_field: str,
    payload: Mapping[str, Any],
) -> H1GuardianRuntimeRecordV1:
    if target_field not in {
        "_source_closure",
        "_genesis",
        "_intent",
        "_permit_record",
        "_revoke",
    }:
        _fail("B2-B durable record target field is not registered")
    document = dict(payload)
    record_id = _domain_id(domain, document)
    document[id_field] = record_id
    raw = ids_v1.canonical_json_bytes(document)
    pending = session._pending_record
    if pending is not None:
        if (
            pending.raw == raw
            and pending.record.record_id == record_id
            and pending.event == event
            and pending.target_field == target_field
        ):
            return _resume_pending_record(session)
        _resume_pending_record(session)
    current = getattr(session, target_field)
    if current is not None:
        if current.record_id == record_id and current.canonical_bytes == raw:
            return current
        _fail("B2-B durable record target is already occupied")
    index = len(session._records)
    filename = f"{index:04d}_{event}_{record_id}.json"
    record = H1GuardianRuntimeRecordV1(raw, record_id, _issuer=_RECORD_ISSUER)
    session._pending_record = _PendingJournalRecordV1(
        index=index,
        event=event,
        filename=filename,
        slot=f"journal-record:{filename}",
        target_field=target_field,
        raw=raw,
        record=record,
    )
    return _resume_pending_record(session)


def _verify_retained_sources_and_records(session: H1GuardianRuntimeGenesisV1) -> None:
    if session._pending_record is not None:
        _fail("B2-B retained journal has an unfinished exact transaction")
    for slot, fact in session._source_facts.items():
        descriptor = _verify_managed_fd(session, slot)
        raw = _read_all(descriptor)
        status = os.fstat(descriptor)
        named = os.stat(fact["resolved_path"], follow_symlinks=False)
        if (
            hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or len(raw) != fact["byte_count"]
            or (
                status.st_dev,
                status.st_ino,
                status.st_mode,
                status.st_size,
            )
            != (fact["device"], fact["inode"], fact["mode"], fact["size"])
            or (named.st_dev, named.st_ino, named.st_mode, named.st_size)
            != (fact["device"], fact["inode"], fact["mode"], fact["size"])
        ):
            _fail("B2-B retained execution source bytes changed")
    for slot, fact in session._context_facts.items():
        descriptor = _verify_managed_fd(session, slot)
        if (
            list(e5a_v1._registry_fd_identity(descriptor)) != fact["identity"]
            or os.readlink(fact["proc_path"]) != fact["link"]
        ):
            _fail("B2-B retained guardian context identity changed")
    directory_fd = _verify_managed_fd(session, "journal:directory")
    if set(os.listdir(directory_fd)) != session._journal_names:
        _fail("B2-B durable journal inventory changed")
    for filename, fact in session._record_facts.items():
        descriptor = _verify_managed_fd(session, fact["slot"])
        raw = _read_all(descriptor)
        named = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        status = os.fstat(descriptor)
        if (
            hashlib.sha256(raw).hexdigest() != fact["sha256"]
            or len(raw) != fact["byte_count"]
            or (status.st_dev, status.st_ino) != (fact["device"], fact["inode"])
            or (named.st_dev, named.st_ino) != (fact["device"], fact["inode"])
            or (status.st_mode, status.st_nlink, status.st_size)
            != (fact["mode"], fact["nlink"], fact["size"])
            or (named.st_mode, named.st_nlink, named.st_size)
            != (fact["mode"], fact["nlink"], fact["size"])
        ):
            _fail("B2-B durable record identity or bytes changed")


def _require_exact_prepared_runtime(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    _validate_live_code_closure()
    if (
        type(runtime) is not b2a_v1.H1E5ARuntimeLeaseSuccessorV1
        or not b2a_v1._same_owner_context(runtime)
        or runtime._state != "PREPARED_SUCCESSOR"
        or b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime
    ):
        _fail("B2-B requires one exact issuer-live PREPARED_SUCCESSOR")
    b2a_v1._validate_e5a_bridge()
    b2a_v1._verify_source_lease_retired(runtime)
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)
    _require_pristine_b2a_grants(runtime)
    e5a_v1._verify_live_hierarchy(runtime)


def _require_pristine_b2a_grants(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    if runtime._grant_states != {
        slot: "AVAILABLE" for slot in b2a_v1.SLOT_ORDER
    } or any(
        grant._runtime_id == id(runtime)
        for grant in b2a_v1._LIVE_GRANTS.values()
    ):
        _fail("B2-B requires a pristine B2-A runtime with zero live candidates")


def _require_session(
    session: H1GuardianRuntimeGenesisV1, *, cleanup: bool = False
) -> H1GuardianRuntimeGenesisV1:
    if type(session) is not H1GuardianRuntimeGenesisV1 or not _same_owner(session):
        _fail("B2-B operation requires one exact owner-bound guardian session")
    allowed = {"RUNNING", "CLEANUP_PENDING"} if cleanup else {"RUNNING"}
    registry = _LIVE_SESSIONS if session._state == "RUNNING" else _QUARANTINED_SESSIONS
    if session._state not in allowed or registry.get(id(session)) is not session:
        _fail("B2-B guardian session is not issuer-live in an allowed state")
    if _RUNTIME_RESERVATIONS.get(id(session._runtime)) is not session:
        _fail("B2-B guardian session lost its exclusive runtime reservation")
    return session


def _verify_running_under_locks(session: H1GuardianRuntimeGenesisV1) -> dict[str, Any]:
    _validate_live_code_closure()
    _require_session(session)
    runtime = session._runtime
    if (
        runtime._state != "RUNNING"
        or b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime
        or runtime._source_lease._state != "RUNTIME_TRANSFERRED"
    ):
        _fail("B2-B exact B2-A runtime left RUNNING ownership")
    b2a_v1._validate_e5a_bridge()
    b2a_v1._verify_source_lease_retired(runtime)
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)
    e5a_v1._verify_live_hierarchy(runtime)
    _verify_preregistration(session._preregistration)
    _verify_retained_sources_and_records(session)
    kill_fd = _verify_managed_fd(session, "cgroup:kill")
    grant_fd = _verify_managed_fd(session, "grant:SUPERVISOR:CONTROL")
    outer_fd = runtime._outer_fd
    control_fd = runtime._role_fds["CONTROL"]
    kill_named = os.stat("cgroup.kill", dir_fd=outer_fd, follow_symlinks=False)
    kill_status = os.fstat(kill_fd)
    grant_status = os.fstat(grant_fd)
    control_status = os.fstat(control_fd)
    if (
        not stat.S_ISREG(kill_status.st_mode)
        or (kill_status.st_dev, kill_status.st_ino) != (kill_named.st_dev, kill_named.st_ino)
        or fcntl.fcntl(kill_fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_WRONLY
        or fcntl.fcntl(kill_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
        or grant_fd == control_fd
        or not stat.S_ISDIR(grant_status.st_mode)
        or (grant_status.st_dev, grant_status.st_ino)
        != (control_status.st_dev, control_status.st_ino)
        or e5a_v1._same_open_file_description_for_close(grant_fd, control_fd)
        or fcntl.fcntl(grant_fd, fcntl.F_GETFL) & os.O_PATH != os.O_PATH
        or fcntl.fcntl(grant_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
    ):
        _fail("B2-B cgroup.kill pin or distinct CONTROL O_PATH grant changed")
    assert session._genesis is not None
    assert session._permit is not None
    return {
        **session._genesis.to_document(),
        "runtime_live_state": "RUNNING",
        "permit_live_state": session._permit.state,
    }


def _start_h1_guardian_runtime_genesis_impl_v1(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    preregistration: H1GuardianRuntimeGenesisPreregistrationV1,
    journal_directory: Path | str,
    _call_token: object,
) -> H1GuardianRuntimeGenesisV1:
    """Create the bounded RUNNING session and exactly one unconsumed permit."""

    prereg = _verify_preregistration(preregistration)
    with _B2B_LOCK:
        if id(runtime) in _RUNTIME_RESERVATIONS:
            _fail("B2-B runtime already has a starting/live/quarantined session")
    if (
        type(runtime) is not b2a_v1.H1E5ARuntimeLeaseSuccessorV1
        or not b2a_v1._same_owner_context(runtime)
        or runtime._state != "PREPARED_SUCCESSOR"
        or b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime
    ):
        _fail("B2-B requires one exact PREPARED runtime before reservation")
    _require_pristine_b2a_grants(runtime)
    path = Path(os.path.abspath(os.fspath(journal_directory)))
    session = H1GuardianRuntimeGenesisV1(
        _SESSION_ISSUER,
        runtime=runtime,
        preregistration=preregistration,
        journal_path=path,
        start_token=_call_token,
    )
    with _B2B_LOCK:
        thread_id = threading.get_ident()
        if thread_id in _STARTING_BY_THREAD:
            _fail("B2-B guardian thread already has a starting session")
        if id(runtime) in _RUNTIME_RESERVATIONS:
            _fail("B2-B runtime already has a starting/live/quarantined session")
        _STARTING_BY_THREAD[thread_id] = session
        _RUNTIME_RESERVATIONS[id(runtime)] = session
    source = runtime._source_lease
    committed = False
    with _B2B_LOCK:
        with b2a_v1._ADAPTER_LOCK:
            with source._lock:
                with runtime._lock:
                    with e5a_v1._FD_OWNERSHIP_LOCK:
                        _require_exact_prepared_runtime(runtime)
                        original_mask = e5a_v1._block_fd_publication_signals()
                        try:
                            _LIVE_SESSIONS[id(session)] = session
                            journal_fd = _open_managed_fd(
                                session,
                                "journal:directory",
                                path,
                                os.O_RDONLY
                                | os.O_DIRECTORY
                                | os.O_CLOEXEC
                                | os.O_NOFOLLOW,
                            )
                            journal_status = os.fstat(journal_fd)
                            if (
                                not stat.S_ISDIR(journal_status.st_mode)
                                or journal_status.st_uid != os.geteuid()
                                or stat.S_IMODE(journal_status.st_mode) & 0o077
                                or os.listdir(journal_fd)
                            ):
                                _fail("B2-B journal directory must be private and empty")
                            sources = _seal_source_files(session)
                            context_pins = _pin_guardian_context(session)
                            kill_fd = _open_managed_fd(
                                session,
                                "cgroup:kill",
                                "cgroup.kill",
                                os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                                dir_fd=runtime._outer_fd,
                            )
                            grant_fd = _open_managed_fd(
                                session,
                                "grant:SUPERVISOR:CONTROL",
                                ".",
                                os.O_PATH
                                | os.O_DIRECTORY
                                | os.O_CLOEXEC
                                | os.O_NOFOLLOW,
                                dir_fd=runtime._role_fds["CONTROL"],
                            )
                            source_payload = {
                                "schema": "acfqp.k7_h1_bounded_execution_source_closure.v1",
                                "schema_version": SCHEMA_VERSION,
                                "profile_key": PROFILE_KEY,
                                "preregistration_id": preregistration.preregistration_id,
                                "retained_whole_source_files": sources,
                                "retained_guardian_context_pins": context_pins,
                                "guardian_identity": prereg["expected_guardian_identity"],
                                "argv_environment_input_allowlist": [],
                                "argv_observed_or_used": False,
                                "environment_observed_or_used": False,
                                "argv_environment_values_or_digests_persisted": False,
                                "namespace_allowlist": prereg["expected_namespace_links"],
                                "platform_and_clone_abi": prereg["platform_and_clone_abi"],
                                "bounded_session_source_closure_present": True,
                                "source_closure_is_production_full_closure": False,
                                **_locked_claims(),
                            }
                            session._source_closure = _persist_record(
                                session,
                                domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
                                id_field="execution_source_closure_id",
                                event="SOURCE_CLOSURE",
                                target_field="_source_closure",
                                payload=source_payload,
                            )
                            genesis_payload = {
                                "schema": "acfqp.k7_h1_guardian_runtime_genesis.v1",
                                "schema_version": SCHEMA_VERSION,
                                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                                "profile_key": PROFILE_KEY,
                                "readiness": READINESS,
                                "execution_source_closure_id": session._source_closure.record_id,
                                "h1_e5a_runtime_lease_successor_id": runtime.successor_id,
                                "preregistration_id": preregistration.preregistration_id,
                                "guardian_identity": prereg["expected_guardian_identity"],
                                "outer_cgroup_kill_identity": list(e5a_v1._registry_fd_identity(kill_fd)),
                                "outer_cgroup_kill_access_mode": "O_WRONLY",
                                "outer_cgroup_kill_is_future_prefrozen_capability": True,
                                "supervisor_control_grant_identity": list(e5a_v1._registry_fd_identity(grant_fd)),
                                "supervisor_control_source_identity": list(e5a_v1._registry_fd_identity(runtime._role_fds["CONTROL"])),
                                "distinct_control_open_file_description": True,
                                "runtime_state_after_genesis": "RUNNING",
                                "cgroup_kill_write_performed": False,
                                "clone_or_process_birth_performed": False,
                                **_locked_claims(),
                            }
                            session._genesis = _persist_record(
                                session,
                                domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_GUARDIAN_SESSION_GENESIS_V1_DOMAIN,
                                id_field="guardian_session_genesis_id",
                                event="GUARDIAN_GENESIS",
                                target_field="_genesis",
                                payload=genesis_payload,
                            )
                            intent_payload = {
                                "schema": "acfqp.k7_h1_actual_process_birth_intent.v1",
                                "schema_version": SCHEMA_VERSION,
                                "profile_key": PROFILE_KEY,
                                "guardian_session_genesis_id": session._genesis.record_id,
                                "execution_source_closure_id": session._source_closure.record_id,
                                "slot": "SUPERVISOR",
                                "leaf": "CONTROL",
                                "intent_state": "PREPARED_DURABLE",
                                "permit_issued": False,
                                "control_grant_private_to_guardian": True,
                                "clone_or_process_birth_performed": False,
                                **_locked_claims(),
                            }
                            session._intent = _persist_record(
                                session,
                                domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_INTENT_V1_DOMAIN,
                                id_field="actual_process_birth_intent_id",
                                event="SUPERVISOR_BIRTH_INTENT",
                                target_field="_intent",
                                payload=intent_payload,
                            )
                            permit_payload = {
                                "schema": "acfqp.k7_h1_actual_process_birth_permit.v1",
                                "schema_version": SCHEMA_VERSION,
                                "profile_key": PROFILE_KEY,
                                "guardian_session_genesis_id": session._genesis.record_id,
                                "execution_source_closure_id": session._source_closure.record_id,
                                "actual_process_birth_intent_id": session._intent.record_id,
                                "slot": "SUPERVISOR",
                                "leaf": "CONTROL",
                                "permit_state": "ISSUED_UNCONSUMED",
                                "intent_persisted_before_permit": True,
                                "private_distinct_control_grant_bound": True,
                                "registered_clone_flags": _REGISTERED_CLONE_FLAGS,
                                "registered_clone_args_size": _CLONE_ARGS_SIZE,
                                "permit_consumable_in_this_slice": False,
                                "clone_or_process_birth_performed": False,
                                **_locked_claims(),
                            }
                            session._permit_record = _persist_record(
                                session,
                                domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN,
                                id_field="actual_process_birth_permit_id",
                                event="SUPERVISOR_BIRTH_PERMIT",
                                target_field="_permit_record",
                                payload=permit_payload,
                            )
                            session._permit = H1SupervisorBirthPermitV1(
                                _PERMIT_ISSUER,
                                session,
                                session._permit_record.canonical_bytes,
                            )
                            if _TEST_ONLY_PRECOMMIT_FAULT_AFTER_PERMIT:
                                raise RuntimeError(
                                    "injected B2-B precommit fault after durable permit"
                                )
                            _verify_retained_sources_and_records(session)
                            if e5a_v1._same_open_file_description_for_close(
                                grant_fd, runtime._role_fds["CONTROL"]
                            ):
                                _fail("B2-B CONTROL grant is not a distinct OFD")

                            def finish_commit(*, inject_fault: bool) -> None:
                                step = 0

                                def boundary() -> None:
                                    nonlocal step
                                    step += 1
                                    if inject_fault and _TEST_ONLY_COMMIT_FAULT_AFTER_STEP == step:
                                        raise RuntimeError(
                                            f"injected B2-B commit fault after step {step}"
                                        )

                                runtime._state = "RUNNING"
                                boundary()
                                session._state = "RUNNING"
                                boundary()
                                _LIVE_SESSIONS[id(session)] = session

                            try:
                                finish_commit(inject_fault=True)
                            except BaseException:
                                finish_commit(inject_fault=False)
                            committed = True
                        finally:
                            e5a_v1._restore_fd_publication_signals(original_mask)
    if not committed:
        _fail("B2-B genesis did not reach its one-way RUNNING commit")
    verify_h1_guardian_runtime_genesis_v1(session)
    with _B2B_LOCK:
        _STARTING_BY_THREAD.pop(threading.get_ident(), None)
    if _TEST_ONLY_POST_STARTING_POP_FAULT:
        raise RuntimeError("injected B2-B fault after starting-map pop")
    return session


def _persist_precommit_abort_if_needed_v1(
    session: H1GuardianRuntimeGenesisV1,
) -> None:
    if session._pending_record is not None:
        _resume_pending_record(session)
    if session._revoke is not None or not session._records:
        return
    if _TEST_ONLY_PRECOMMIT_ABORT_FAILURE:
        raise RuntimeError("injected B2-B precommit abort persistence failure")
    payload = {
        "schema": "acfqp.k7_h1_guardian_runtime_precommit_abort.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_session_genesis_id": (
            session._genesis.record_id
            if session._genesis is not None
            else {"kind": "NOT_APPLICABLE", "reason": "GENESIS_NOT_PERSISTED"}
        ),
        "actual_process_birth_intent_id": (
            session._intent.record_id
            if session._intent is not None
            else {"kind": "NOT_APPLICABLE", "reason": "INTENT_NOT_PERSISTED"}
        ),
        "actual_process_birth_permit_id": (
            session._permit_record.record_id
            if session._permit_record is not None
            else {"kind": "NOT_APPLICABLE", "reason": "PERMIT_NOT_PERSISTED"}
        ),
        "terminal_state": "ABORTED_BEFORE_RUNNING_COMMIT",
        "durable_intent_or_permit_has_no_live_authority": True,
        "permit_consumed": False,
        "clone_or_process_birth_performed": False,
        "cgroup_kill_write_performed": False,
        **_locked_claims(),
    }
    session._revoke = _persist_record(
        session,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_NATIVE_CLEANUP_BARRIER_V1_DOMAIN,
        id_field="native_cleanup_barrier_id",
        event="PRECOMMIT_ABORT",
        target_field="_revoke",
        payload=payload,
    )


def _cleanup_precommit_session_v1(session: H1GuardianRuntimeGenesisV1) -> None:
    """Close a failed PREPARING session while preserving B2-A PREPARED."""

    runtime = session._runtime
    source = runtime._source_lease
    original_mask = e5a_v1._block_fd_publication_signals()
    try:
        with _B2B_LOCK:
            with b2a_v1._ADAPTER_LOCK:
                with source._lock:
                    with runtime._lock:
                        with e5a_v1._FD_OWNERSHIP_LOCK:
                            if session._state not in {
                                "PREPARING",
                                "PRECOMMIT_ABORT_PENDING",
                                "PRECOMMIT_CLEANUP_PENDING",
                            }:
                                _fail("B2-B precommit cleanup crossed its state")
                            if runtime._state not in {
                                "PREPARED_SUCCESSOR",
                                "B2B_PRECOMMIT_QUARANTINED",
                            }:
                                _fail("B2-B precommit runtime quarantine changed")
                            runtime._state = "B2B_PRECOMMIT_QUARANTINED"
                            _cleanup_boundary(
                                "AFTER_PRECOMMIT_RUNTIME_QUARANTINE",
                                session,
                            )
                            session._state = "PRECOMMIT_ABORT_PENDING"
                            _LIVE_SESSIONS.pop(id(session), None)
                            _QUARANTINED_SESSIONS[id(session)] = session
                            try:
                                _persist_precommit_abort_if_needed_v1(session)
                            except BaseException as error:
                                raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                                    "B2-B precommit durable abort is retryable",
                                    cleanup_handle=session,
                                ) from error
                            session._state = "PRECOMMIT_CLEANUP_PENDING"
                            first_error: OSError | None = None
                            for slot in reversed(session._fd_order):
                                error = _close_managed_slot(session, slot)
                                if first_error is None and error is not None:
                                    first_error = error
                            if first_error is not None or any(
                                descriptor >= 0
                                for descriptor in session._fd_slots.values()
                            ):
                                raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                                    "B2-B precommit rollback retained close quarantine",
                                    cleanup_handle=session,
                                ) from first_error
                            if any(
                                record.owner is session
                                for record in _MANAGED_FDS.values()
                            ):
                                _fail("B2-B precommit rollback retained FD ownership")
                            if b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime:
                                _fail("B2-B precommit rollback changed B2-A issuer registry")
                            runtime._state = "PREPARED_SUCCESSOR"
                            session._state = "ABORTED_PRECOMMIT"
                            _QUARANTINED_SESSIONS.pop(id(session), None)
                            _RUNTIME_RESERVATIONS.pop(id(runtime), None)
    finally:
        # Restore only after every project lock is released.  A pending
        # reentrant handler therefore observes one exact retryable or terminal
        # state, never a half-published registry transition.
        e5a_v1._restore_fd_publication_signals(original_mask)


def retry_h1_guardian_runtime_precommit_cleanup_v1(
    session: H1GuardianRuntimeGenesisV1,
) -> None:
    """Retry only a handle explicitly returned on precommit close quarantine."""

    if (
        type(session) is not H1GuardianRuntimeGenesisV1
        or not _same_owner(session)
        or session._state
        not in {"PRECOMMIT_ABORT_PENDING", "PRECOMMIT_CLEANUP_PENDING"}
        or _QUARANTINED_SESSIONS.get(id(session)) is not session
    ):
        _fail("B2-B precommit retry requires one exact quarantine handle")
    _cleanup_precommit_session_v1(session)


def _precommit_cleanup_is_exactly_terminal(
    session: H1GuardianRuntimeGenesisV1,
) -> bool:
    runtime = session._runtime
    return (
        session._state == "ABORTED_PRECOMMIT"
        and runtime._state == "PREPARED_SUCCESSOR"
        and b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is runtime
        and id(session) not in _LIVE_SESSIONS
        and id(session) not in _QUARANTINED_SESSIONS
        and id(runtime) not in _RUNTIME_RESERVATIONS
        and session._pending_record is None
        and all(descriptor < 0 for descriptor in session._fd_slots.values())
        and not any(
            record.owner is session for record in _MANAGED_FDS.values()
        )
    )


def start_h1_guardian_runtime_genesis_v1(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    preregistration: H1GuardianRuntimeGenesisPreregistrationV1,
    journal_directory: Path | str,
) -> H1GuardianRuntimeGenesisV1:
    """Exception-safe public genesis wrapper around the one-way commit."""

    call_token = object()
    original_mask = e5a_v1._block_fd_publication_signals()
    result: H1GuardianRuntimeGenesisV1 | None = None
    original: BaseException | None = None
    cleanup_error: BaseException | None = None
    cleanup_session: H1GuardianRuntimeGenesisV1 | None = None
    try:
        try:
            result = _start_h1_guardian_runtime_genesis_impl_v1(
                runtime,
                preregistration=preregistration,
                journal_directory=journal_directory,
                _call_token=call_token,
            )
        except BaseException as error:
            original = error
            with _B2B_LOCK:
                cleanup_session = _STARTING_BY_THREAD.pop(
                    threading.get_ident(), None
                )
                if cleanup_session is None:
                    candidate = _RUNTIME_RESERVATIONS.get(id(runtime))
                    if (
                        type(candidate) is H1GuardianRuntimeGenesisV1
                        and candidate._start_token is call_token
                    ):
                        cleanup_session = candidate
            if cleanup_session is not None:
                _cleanup_boundary(
                    "AFTER_STARTING_SESSION_DISCOVERY", cleanup_session
                )
                try:
                    if cleanup_session._state in {
                        "PREPARING",
                        "PRECOMMIT_CLEANUP_PENDING",
                    }:
                        _cleanup_precommit_session_v1(cleanup_session)
                    else:
                        close_h1_guardian_runtime_genesis_v1(cleanup_session)
                except BaseException as error:
                    cleanup_error = error
    finally:
        restore_error: BaseException | None = None
        try:
            # The outer mask spans session discovery and cleanup entry.  A
            # pending handler can run only after an exact terminal/retryable
            # state is visible and every project lock is released.
            e5a_v1._restore_fd_publication_signals(original_mask)
        except BaseException as error:
            restore_error = error

    if original is not None:
        if cleanup_session is not None and (
            cleanup_session._state == "CLOSED"
            or _precommit_cleanup_is_exactly_terminal(cleanup_session)
        ):
            raise original
        if cleanup_error is not None and cleanup_session is not None:
            raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                "B2-B genesis failed with retryable cleanup quarantine",
                cleanup_handle=cleanup_session,
            ) from cleanup_error
        if restore_error is not None:
            raise original from restore_error
        raise original

    if result is None:
        _fail("B2-B genesis produced neither a result nor an exception")
    if restore_error is not None:
        # Successful construction followed by deferred handler failure must
        # not strand an undisclosed live session.
        try:
            close_h1_guardian_runtime_genesis_v1(result)
        except BaseException as error:
            if result._state != "CLOSED":
                raise ConstructionK7H1GuardianRuntimeGenesisV1Error(
                    "B2-B deferred start signal left retryable cleanup quarantine",
                    cleanup_handle=result,
                ) from error
        raise restore_error
    return result


def verify_h1_guardian_runtime_genesis_v1(
    session: H1GuardianRuntimeGenesisV1,
) -> dict[str, Any]:
    session = _require_session(session)
    runtime = session._runtime
    source = runtime._source_lease
    with _B2B_LOCK:
        with b2a_v1._ADAPTER_LOCK:
            with source._lock:
                with runtime._lock:
                    with e5a_v1._FD_OWNERSHIP_LOCK:
                        return _verify_running_under_locks(session)


def _retire_fd(session: H1GuardianRuntimeGenesisV1, slot: str, descriptor: int) -> None:
    record = _MANAGED_FDS.get(descriptor)
    if record is not None and record.owner is session and record.slot == slot:
        _MANAGED_FDS.pop(descriptor, None)
    if session._fd_slots.get(slot) == descriptor:
        session._fd_slots[slot] = -1


def _close_final_witness(session: H1GuardianRuntimeGenesisV1, slot: str) -> OSError | None:
    witness_slot = f"retry-witness:{slot}"
    witness = session._fd_slots.get(witness_slot, -1)
    if witness < 0:
        return None
    record = _MANAGED_FDS.get(witness)
    if record is None or record.owner is not session or record.slot != witness_slot:
        _fail("B2-B final close witness registry changed")
    try:
        _RAW_OS_CLOSE(witness)
    except OSError as error:
        if error.errno == errno.EBADF:
            _retire_fd(session, witness_slot, witness)
            return None
        if record.identity is None:
            try:
                os.fstat(witness)
            except OSError as replay_error:
                if replay_error.errno == errno.EBADF:
                    _retire_fd(session, witness_slot, witness)
                    return None
            return error
        try:
            if e5a_v1._registry_fd_identity(witness) == record.identity:
                return error
        except OSError:
            pass
    _retire_fd(session, witness_slot, witness)
    return None


def _close_managed_slot(session: H1GuardianRuntimeGenesisV1, slot: str) -> OSError | None:
    descriptor = session._fd_slots.get(slot, -1)
    witness_slot = f"retry-witness:{slot}"
    if descriptor < 0:
        return _close_final_witness(session, slot)
    record = _MANAGED_FDS.get(descriptor)
    if record is None or record.owner is not session or record.slot != slot:
        _fail("B2-B canonical close ownership changed")
    witness = session._fd_slots[witness_slot]
    witness_record = _MANAGED_FDS.get(witness)
    if witness < 0 or witness_record is None:
        # Only construction faults before lifetime-witness publication can
        # reach this path; ordinary live descriptors always retain a witness.
        e5a_v1._enter_fork_forbidden()
        try:
            original_mask = e5a_v1._block_fd_publication_signals()
            try:
                try:
                    witness = int(_FCNTL_FCNTL(descriptor, fcntl.F_DUPFD_CLOEXEC, 3))
                    _publish_fd(session, witness_slot, witness)
                finally:
                    e5a_v1._restore_fd_publication_signals(original_mask)
            except BaseException:
                if witness >= 0 and witness not in _MANAGED_FDS:
                    _publish_fd(session, witness_slot, witness)
                raise
        finally:
            e5a_v1._leave_fork_forbidden()
        witness_record = _MANAGED_FDS.get(witness)
    if (
        witness_record is None
        or witness_record.owner is not session
        or witness_record.slot != witness_slot
    ):
        _fail("B2-B lifetime close witness ownership changed")
    try:
        canonical_identity = e5a_v1._registry_fd_identity(descriptor)
        witness_identity = e5a_v1._registry_fd_identity(witness)
        same_ofd = e5a_v1._same_open_file_description_for_close(
            descriptor, witness
        )
    except OSError:
        same_ofd = False
    if not same_ofd:
        # There is no sound way to decide which same-target numeric reuse is
        # still ours.  Preserve both registered numbers; never close/retire
        # either based only on inode-like identity.
        return OSError(errno.ESTALE, "B2-B lifetime OFD pair is ambiguous")
    # Metadata/content mutation is an audit failure but does not erase the
    # lifetime OFD proof.  Refresh close-only identities for final-witness
    # handling; this never changes the durable audit facts.
    _MANAGED_FDS[descriptor] = _ManagedFDRecordV1(
        session, slot, canonical_identity
    )
    _MANAGED_FDS[witness] = _ManagedFDRecordV1(
        session, witness_slot, witness_identity
    )
    try:
        _OS_CLOSE(descriptor)
    except OSError as error:
        if error.errno != errno.EBADF:
            try:
                if e5a_v1._same_open_file_description_for_close(descriptor, witness):
                    return error
            except BaseException:
                return error
    _cleanup_boundary(
        "AFTER_CANONICAL_CLOSE_BEFORE_RETIRE", session, slot
    )
    _retire_fd(session, slot, descriptor)
    return _close_final_witness(session, slot)


def _persist_revoke_if_needed(session: H1GuardianRuntimeGenesisV1) -> None:
    if session._revoke is not None:
        return
    assert session._permit_record is not None
    assert session._intent is not None
    assert session._genesis is not None
    payload = {
        "schema": "acfqp.k7_h1_guardian_runtime_native_cleanup_barrier.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_session_genesis_id": session._genesis.record_id,
        "actual_process_birth_intent_id": session._intent.record_id,
        "actual_process_birth_permit_id": session._permit_record.record_id,
        "permit_state_before_revoke": "ISSUED_UNCONSUMED",
        "permit_state_after_revoke": "REVOKED_BEFORE_CONSUMPTION",
        "durable_revoke_precedes_descriptor_cleanup": True,
        "clone_or_process_birth_performed": False,
        "cgroup_kill_write_performed": False,
        **_locked_claims(),
    }
    session._revoke = _persist_record(
        session,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_NATIVE_CLEANUP_BARRIER_V1_DOMAIN,
        id_field="native_cleanup_barrier_id",
        event="SUPERVISOR_PERMIT_REVOKED",
        target_field="_revoke",
        payload=payload,
    )


def close_h1_guardian_runtime_genesis_v1(
    session: H1GuardianRuntimeGenesisV1,
) -> b2a_v1.H1E5ARuntimeLeaseClosureV1:
    """Revoke before any birth, close B2-B pins, then delegate to B2-A."""

    if type(session) is not H1GuardianRuntimeGenesisV1 or not _same_owner(session):
        _fail("B2-B cleanup requires one exact owner-bound guardian session")
    if session._state == "CLOSED" and session._b2a_closure is not None:
        return session._b2a_closure
    session = _require_session(session, cleanup=True)
    runtime = session._runtime
    source = runtime._source_lease
    ready_for_b2a = False
    primary_audit_error: BaseException | None = None
    already_closed_closure: b2a_v1.H1E5ARuntimeLeaseClosureV1 | None = None
    original_mask = e5a_v1._block_fd_publication_signals()
    try:
        with _B2B_LOCK:
            with b2a_v1._ADAPTER_LOCK:
                with source._lock:
                    with runtime._lock:
                        with e5a_v1._FD_OWNERSHIP_LOCK:
                            _require_session(session, cleanup=True)
                            if session._state == "RUNNING":
                                if session._pending_record is not None:
                                    _resume_pending_record(session)
                                try:
                                    _verify_running_under_locks(session)
                                except BaseException as error:
                                    # Audit failure is evidence, never permission
                                    # to leak the writable kill/grant/source pins.
                                    primary_audit_error = error
                                _persist_revoke_if_needed(session)
                                session._state = "CLEANUP_PENDING"
                                _LIVE_SESSIONS.pop(id(session), None)
                                _QUARANTINED_SESSIONS[id(session)] = session
                            close_order = ["grant:SUPERVISOR:CONTROL"]
                            close_order.extend(
                                slot
                                for slot in session._fd_order
                                if slot.startswith("source:")
                                or slot.startswith("namespace:")
                                or slot == "guardian:exe"
                            )
                            close_order.extend(
                                slot
                                for slot in session._fd_order
                                if slot.startswith("journal-record:")
                            )
                            close_order.append("journal:directory")
                            close_order.append("cgroup:kill")
                            first_error: OSError | None = None
                            seen: set[str] = set()
                            for slot in close_order:
                                if slot in seen:
                                    continue
                                seen.add(slot)
                                error = _close_managed_slot(session, slot)
                                if first_error is None and error is not None:
                                    first_error = error
                            if first_error is not None or any(
                                descriptor >= 0
                                for descriptor in session._fd_slots.values()
                            ):
                                raise RuntimeError(
                                    "B2-B cleanup retained same-OFD close quarantine"
                                ) from first_error
                            if any(
                                record.owner is session
                                for record in _MANAGED_FDS.values()
                            ):
                                _fail("B2-B cleanup left a descriptor ownership record")
                            if runtime._state == "RUNNING":
                                runtime._state = "CLEANUP_PENDING"
                                b2a_v1._LIVE_RUNTIME_LEASES.pop(id(runtime), None)
                                b2a_v1._QUARANTINED_RUNTIME_LEASES[
                                    id(runtime)
                                ] = runtime
                            if (
                                runtime._state == "CLOSED"
                                and runtime._closure is not None
                            ):
                                already_closed_closure = runtime._closure
                            elif (
                                runtime._state != "CLEANUP_PENDING"
                                or b2a_v1._QUARANTINED_RUNTIME_LEASES.get(
                                    id(runtime)
                                )
                                is not runtime
                            ):
                                _fail(
                                    "B2-B cleanup did not hand B2-A exact CLEANUP_PENDING"
                                )
                            ready_for_b2a = True
    finally:
        # Pending handlers run only after all B2-B/B2-A/E5A locks are out and
        # every canonical close has been paired with its registry retirement.
        e5a_v1._restore_fd_publication_signals(original_mask)
    if not ready_for_b2a:
        _fail("B2-B cleanup did not reach B2-A handoff")
    b2a_error: BaseException | None = None
    if already_closed_closure is not None:
        closure = already_closed_closure
    else:
        try:
            closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(runtime)
        except BaseException as error:
            if runtime._state != "CLOSED" or runtime._closure is None:
                raise
            closure = runtime._closure
            b2a_error = error
    with _B2B_LOCK:
        if runtime._state != "CLOSED":
            _fail("B2-A cleanup did not close the transferred runtime")
        original_mask = e5a_v1._block_fd_publication_signals()
        try:
            def finish_closed(*, inject_fault: bool) -> None:
                step = 0

                def boundary() -> None:
                    nonlocal step
                    step += 1
                    if (
                        inject_fault
                        and _TEST_ONLY_CLOSURE_COMMIT_FAULT_AFTER_STEP == step
                    ):
                        raise RuntimeError(
                            f"injected B2-B closure commit fault after step {step}"
                        )

                session._b2a_closure = closure
                boundary()
                session._state = "CLOSED"
                boundary()
                _QUARANTINED_SESSIONS.pop(id(session), None)
                _LIVE_SESSIONS.pop(id(session), None)
                _RUNTIME_RESERVATIONS.pop(id(runtime), None)

            try:
                finish_closed(inject_fault=True)
            except BaseException:
                finish_closed(inject_fault=False)
        finally:
            e5a_v1._restore_fd_publication_signals(original_mask)
    if b2a_error is not None:
        raise b2a_error
    if primary_audit_error is not None:
        raise primary_audit_error
    return closure


def _before_fork() -> None:
    # Registration order makes the full before-chain B2-B -> B2-A -> E5A.
    _B2B_LOCK.acquire()


def _after_fork_parent() -> None:
    _B2B_LOCK.release()


def _after_fork_child() -> None:
    global _B2B_LOCK
    for descriptor in tuple(_MANAGED_FDS):
        try:
            _RAW_OS_CLOSE(descriptor)
        except OSError:
            pass
    for session in tuple({**_LIVE_SESSIONS, **_QUARANTINED_SESSIONS}.values()):
        session._poison_after_fork_child()
    _MANAGED_FDS.clear()
    _LIVE_SESSIONS.clear()
    _QUARANTINED_SESSIONS.clear()
    _STARTING_BY_THREAD.clear()
    _RUNTIME_RESERVATIONS.clear()
    _B2B_LOCK = threading.RLock()


_SELF_CALLABLES = MappingProxyType(
    {
        name: (globals()[name], globals()[name].__code__)
        for name in (
            "_open_managed_fd",
            "_ensure_pending_record_fd",
            "_finish_pending_record",
            "_resume_pending_record",
            "_cleanup_boundary",
            "_persist_record",
            "_verify_retained_sources_and_records",
            "_require_pristine_b2a_grants",
            "_close_managed_slot",
            "_persist_revoke_if_needed",
            "_cleanup_precommit_session_v1",
            "_precommit_cleanup_is_exactly_terminal",
        )
    }
)


os.register_at_fork(
    before=_before_fork,
    after_in_parent=_after_fork_parent,
    after_in_child=_after_fork_child,
)


__all__ = tuple(
    sorted(
        name
        for name in globals()
        if (
            name.isupper()
            or name.startswith("H1")
            or name.startswith("ConstructionK7")
            or name
            in {
                "preregister_h1_guardian_runtime_genesis_v1",
                "start_h1_guardian_runtime_genesis_v1",
                "retry_h1_guardian_runtime_precommit_cleanup_v1",
                "verify_h1_guardian_runtime_genesis_v1",
                "close_h1_guardian_runtime_genesis_v1",
            }
        )
        and not name.startswith("_")
    )
)
