"""Additive B2-B V2 public handoff without any process birth.

The frozen B2-B V1/B2-C implementation cannot be extended in place because
B2-C pins the exact V1 source digest.  This module therefore starts from one
issuer-live B2-A ``PREPARED_SUCCESSOR`` and creates an entirely separate V2
registry, journal, source closure, five-slot nonlaunchable grant escrow, and
public owner-bound handoff.  The only implemented terminal transition is a
durable unconsumed revoke followed by exact B2-A/E5A cleanup.

It also exposes a source-pinned future-consumer adapter and durable typed
takeover-preparation seam.  That seam neither invokes the consumer nor exposes
any grant and therefore does not consume the permit or authorize a launch.

No V1 guardian module or B2-C module is imported.  No clone, exec, process,
PID cell, pidfd, cgroup placement, peak read, three-birth, accounting, or
official authority is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys
import threading
from types import FunctionType, MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v19 as domains_v19
from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-B-V2"
PROFILE_KEY = "construction_k7_h1_guardian_runtime_genesis_v2"
READINESS = "PUBLIC_FIVE_GRANT_HANDOFF_ESCROWED_UNCONSUMED_NO_BIRTH"

ADDITIVE_GUARDIAN_RUNTIME_V2_PRESENT = True
EXACT_B2A_PREPARED_INPUT_PRESENT = True
FIVE_DISTINCT_NONLAUNCHABLE_GRANTS_ESCROWED = True
PUBLIC_TYPED_HANDOFF_PRESENT = True
UNCONSUMED_REVOKE_AND_CLEANUP_PRESENT = True
DURABLE_SOURCE_AND_HANDOFF_GRAPH_PRESENT = True
PUBLIC_PREPARED_TAKEOVER_SEAM_PRESENT = True

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
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
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

SLOT_ORDER = tuple(b2a_v1.SLOT_ORDER)
SLOT_TO_LEAF = MappingProxyType(dict(b2a_v1.SLOT_TO_LEAF))

_PREREG_ISSUER = object()
_HANDOFF_ISSUER = object()
_CANCELLATION_ISSUER = object()
_ADAPTER_ISSUER = object()
_TAKEOVER_ISSUER = object()
_V2_LOCK = threading.RLock()
_LIVE_HANDOFFS: dict[int, "_LiveHandoffRecordV2"] = {}
_QUARANTINED_HANDOFFS: dict[int, "_LiveHandoffRecordV2"] = {}
_RUNTIME_RESERVATIONS: dict[int, "_LiveHandoffRecordV2"] = {}
_STARTING_BY_THREAD: dict[int, "_LiveHandoffRecordV2"] = {}
_TERMINAL_CANCELLATIONS: dict[int, "_TerminalTombstoneV2"] = {}
_CANCELLATION_TOMBSTONES: dict[int, "_TerminalTombstoneV2"] = {}
_LIVE_CONSUMER_ADAPTERS: dict[int, "_LiveAdapterRecordV2"] = {}
_LIVE_TAKEOVERS: dict[int, "_LiveTakeoverRecordV2"] = {}

_TEST_ONLY_START_FAULT_AFTER_EVENT: str | None = None
_TEST_ONLY_START_FAULT_AFTER_GRANT: int | None = None
_TEST_ONLY_CANCEL_FAULT_AFTER_GRANT: int | None = None
_TEST_ONLY_JOURNAL_FAULT_EVENT: str | None = None
_TEST_ONLY_JOURNAL_FAULT_STAGE: str | None = None
_TEST_ONLY_SIGNAL_RESTORE_FAULT = False

_SELF_PATH = Path(__file__).resolve(strict=True)
_SOURCE_PATHS = MappingProxyType(
    {
        "guardian_runtime_genesis_v2": _SELF_PATH,
        "b2a_runtime_successor_v1": Path(b2a_v1.__file__).resolve(strict=True),
        "e5a_working_set_v1": Path(e5a_v1.__file__).resolve(strict=True),
        "domain_registry_v19": Path(domains_v19.__file__).resolve(strict=True),
        "phase3e_ids": Path(ids_v1.__file__).resolve(strict=True),
        "domain_registry_v15": Path(domains_v15.__file__).resolve(strict=True),
    }
)


def _source_fact(path: Path) -> tuple[int, int, int, int, str]:
    status = path.stat()
    raw = path.read_bytes()
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        hashlib.sha256(raw).hexdigest(),
    )


_IMPORT_SOURCE_FACTS = MappingProxyType(
    {label: _source_fact(path) for label, path in _SOURCE_PATHS.items()}
)
_EXPECTED_UPSTREAM_SHA256 = MappingProxyType(
    {
        "b2a_runtime_successor_v1": (
            "c4340e95901ba41c9ba686b56a2f81a39958f4bd2003e736524285723cf9d3c4"
        ),
        "e5a_working_set_v1": (
            "70a32237ba72bf33aa924b65e8b45ee285090dd800ed049e66636e882d969287"
        ),
        "phase3e_ids": (
            "3eb435bfec4692961d61b4edf6e067cc128810509b5e35ec1d7348079288c4c2"
        ),
        "domain_registry_v15": (
            "a54493f6431e0a5fa57afdc18bd185802f434ef88d88299285d0e1f40e0e0469"
        ),
    }
)
_UPSTREAM_MODULES = MappingProxyType(
    {
        "b2a": b2a_v1,
        "e5a": e5a_v1,
        "v19": domains_v19,
        "v15": domains_v15,
        "ids": ids_v1,
    }
)


def _callable_fact(function: Any) -> tuple[Any, Any, Any, Any]:
    return (
        function,
        function.__code__,
        function.__defaults__,
        dict(function.__kwdefaults__) if function.__kwdefaults__ else None,
    )


# B2-A and E5A public operations dispatch through private module helpers.  Pin
# the complete module-local Python callable inventories so a dependency swap
# cannot preserve a reviewed top-level code object while changing its behavior.
_UPSTREAM_CALLABLES = MappingProxyType(
    {
        (module_name, name): _callable_fact(value)
        for module_name, module in _UPSTREAM_MODULES.items()
        for name, value in vars(module).items()
        if type(value) is FunctionType and value.__globals__ is module.__dict__
    }
)
_EXPECTED_V19_DOMAIN_GLOBALS = MappingProxyType(
    {
        name: getattr(domains_v19, name)
        for name in dir(domains_v19)
        if name.endswith("_DOMAIN")
        or name in {
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19",
            "K7_H1_DOMAIN_TAG_EXTENSION_V19",
        }
    }
)
_LOCAL_CALLABLES: Mapping[str, tuple[Any, Any, Any, Any]] = MappingProxyType({})
_UPSTREAM_GLOBALS = MappingProxyType(
    {
        ("b2a", "H1E5ARuntimeLeaseSuccessorV1"): (
            b2a_v1.H1E5ARuntimeLeaseSuccessorV1
        ),
        ("b2a", "H1E5ANonlaunchableLeafCandidateV1"): (
            b2a_v1.H1E5ANonlaunchableLeafCandidateV1
        ),
        ("b2a", "SLOT_ORDER"): b2a_v1.SLOT_ORDER,
        ("b2a", "SLOT_TO_LEAF"): b2a_v1.SLOT_TO_LEAF,
        ("e5a", "_OWNED_FDS"): e5a_v1._OWNED_FDS,  # noqa: SLF001
        ("v15", "CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN"): (
            domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN
        ),
        ("v15", "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15"): (
            domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15
        ),
    }
)


class ConstructionK7H1GuardianRuntimeGenesisV2Error(ValueError):
    """The additive V2 handoff, identity, journal, or cleanup was crossed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_handle: "H1GuardianRuntimePermitHandoffV2 | None" = None,
        primary_error: BaseException | None = None,
        cleanup_error: BaseException | None = None,
        restoration_error: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_handle = cleanup_handle
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error
        self.restoration_error = restoration_error


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1GuardianRuntimeGenesisV2Error(message)


def _locked_claims() -> dict[str, Any]:
    return {
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
        "three_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "actual_observed_e3_v2_completion_present": False,
        "e4_v2_completion_present": False,
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


def _validate_live_code_closure() -> None:
    modules = _UPSTREAM_MODULES
    for (
        module_name,
        name,
    ), (
        expected,
        expected_code,
        expected_defaults,
        expected_kwdefaults,
    ) in _UPSTREAM_CALLABLES.items():
        live = getattr(modules[module_name], name, None)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not modules[module_name].__dict__
            or getattr(live, "__code__", None) is not expected_code
            or getattr(live, "__defaults__", None) != expected_defaults
            or getattr(live, "__kwdefaults__", None) != expected_kwdefaults
        ):
            _fail(f"guardian V2 live-code callable identity changed: {module_name}.{name}")
    for (module_name, name), expected in _UPSTREAM_GLOBALS.items():
        if getattr(modules[module_name], name, None) is not expected:
            _fail(f"guardian V2 live-code global identity changed: {module_name}.{name}")
    for name, expected in _EXPECTED_V19_DOMAIN_GLOBALS.items():
        if getattr(domains_v19, name, None) is not expected:
            _fail(f"guardian V2 V19 domain identity changed: {name}")
    module_globals = globals()
    for name, (expected, expected_code, expected_defaults, expected_kwdefaults) in (
        _LOCAL_CALLABLES.items()
    ):
        live = module_globals.get(name)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not module_globals
            or getattr(live, "__code__", None) is not expected_code
            or getattr(live, "__defaults__", None) != expected_defaults
            or getattr(live, "__kwdefaults__", None) != expected_kwdefaults
        ):
            _fail(f"guardian V2 local callable identity changed: {name}")
    if SLOT_ORDER != (
        "SUPERVISOR",
        "PIDFD_PROBE",
        "BROKER",
        "WORKER",
        "BUSINESS",
    ) or dict(SLOT_TO_LEAF) != {
        "SUPERVISOR": "CONTROL",
        "PIDFD_PROBE": "CONTROL",
        "BROKER": "CONTROL",
        "WORKER": "WORKER",
        "BUSINESS": "BUSINESS",
    }:
        _fail("guardian V2 five-slot registry changed")
    for label, path in _SOURCE_PATHS.items():
        try:
            observed = _source_fact(path)
        except OSError as error:
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 source closure is unavailable"
            ) from error
        if observed != _IMPORT_SOURCE_FACTS[label]:
            _fail(f"guardian V2 source identity changed after import: {label}")
        expected_sha = _EXPECTED_UPSTREAM_SHA256.get(label)
        if expected_sha is not None and observed[-1] != expected_sha:
            _fail(f"guardian V2 reviewed upstream source changed: {label}")


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v19.extension_content_id_v19(domain, payload)


def _with_id(
    payload: Mapping[str, Any], *, domain: str, id_field: str
) -> dict[str, Any]:
    result = dict(payload)
    result[id_field] = _domain_id(domain, payload)
    return result


def _verify_content_document(
    document: Mapping[str, Any], *, domain: str, id_field: str, label: str
) -> str:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if type(supplied) is not str or _domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return supplied


def _process_start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    close = raw.rfind(")")
    if close < 0:
        _fail("guardian V2 process stat is malformed")
    return int(raw[close + 2 :].split()[19])


def _guardian_identity() -> dict[str, Any]:
    if len(tuple(Path("/proc/self/task").iterdir())) != 1:
        _fail("guardian V2 requires one single-threaded owner at preregistration")
    namespaces = {
        name: os.readlink(f"/proc/self/ns/{name}")
        for name in ("cgroup", "ipc", "mnt", "net", "pid", "user", "uts")
    }
    return {
        "pid": os.getpid(),
        "process_start_ticks": _process_start_ticks(os.getpid()),
        "thread_id": threading.get_ident(),
        "effective_uid": os.geteuid(),
        "effective_gid": os.getegid(),
        "kernel_boot_id": Path("/proc/sys/kernel/random/boot_id")
        .read_text(encoding="ascii")
        .strip(),
        "namespace_links": dict(sorted(namespaces.items())),
    }


def _source_digest_summary() -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "sha256": _IMPORT_SOURCE_FACTS[label][-1],
            "byte_count": _IMPORT_SOURCE_FACTS[label][3],
        }
        for label in sorted(_SOURCE_PATHS)
    ]


@dataclass(frozen=True, slots=True)
class H1GuardianRuntimeGenesisPreregistrationV2:
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str = field(init=False)
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._issuer is not _PREREG_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("guardian V2 preregistration is caller-minted")
        document = ids_v1.loads_canonical_json(self.canonical_bytes)
        supplied = _verify_content_document(
            document,
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_PREREGISTRATION_V1_DOMAIN,
            id_field="guardian_runtime_v2_preregistration_id",
            label="guardian V2 preregistration",
        )
        object.__setattr__(self, "preregistration_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


def preregister_h1_guardian_runtime_genesis_v2() -> H1GuardianRuntimeGenesisPreregistrationV2:
    _validate_live_code_closure()
    payload = {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "expected_guardian_identity": _guardian_identity(),
        "expected_source_digests": _source_digest_summary(),
        "argv_environment_observed_or_used": False,
        "b2b_v1_imported_or_started": False,
        "b2c_private_api_imported_or_used": False,
        **_locked_claims(),
    }
    document = _with_id(
        payload,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_PREREGISTRATION_V1_DOMAIN,
        id_field="guardian_runtime_v2_preregistration_id",
    )
    return H1GuardianRuntimeGenesisPreregistrationV2(
        ids_v1.canonical_json_bytes(document), _issuer=_PREREG_ISSUER
    )


def _verify_preregistration(
    preregistration: H1GuardianRuntimeGenesisPreregistrationV2,
) -> dict[str, Any]:
    _validate_live_code_closure()
    if type(preregistration) is not H1GuardianRuntimeGenesisPreregistrationV2:
        _fail("guardian V2 requires one exact preregistration")
    document = preregistration.to_document()
    _verify_content_document(
        document,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_PREREGISTRATION_V1_DOMAIN,
        id_field="guardian_runtime_v2_preregistration_id",
        label="guardian V2 preregistration",
    )
    if (
        document.get("expected_guardian_identity") != _guardian_identity()
        or document.get("expected_source_digests") != _source_digest_summary()
        or document.get("b2b_v1_imported_or_started") is not False
        or document.get("b2c_private_api_imported_or_used") is not False
    ):
        _fail("guardian V2 preregistration identity or source changed")
    return document


@dataclass(frozen=True, slots=True)
class _JournalEntryV2:
    event: str
    filename: str
    domain: str
    id_field: str
    record_id: str
    canonical_bytes: bytes = field(repr=False)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


@dataclass(slots=True)
class _LiveHandoffRecordV2:
    handle: "H1GuardianRuntimePermitHandoffV2"
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1
    preregistration: H1GuardianRuntimeGenesisPreregistrationV2
    journal_path: Path
    directory_fd: int
    owner_pid: int
    owner_thread: threading.Thread
    owner_thread_id: int
    state: str = "PREPARING"
    candidates: dict[str, b2a_v1.H1E5ANonlaunchableLeafCandidateV1] = field(
        default_factory=dict
    )
    grant_facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    entries: dict[str, _JournalEntryV2] = field(default_factory=dict)
    filenames: list[str] = field(default_factory=list)
    next_index: int = 1
    cancellation: "H1GuardianRuntimeCancellationV2 | None" = None
    pending_entry: "_PendingJournalEntryV2 | None" = None
    takeover: "H1GuardianRuntimePreparedTakeoverV2 | None" = None
    revoke_state_before: str | None = None


@dataclass(frozen=True, slots=True)
class _PendingJournalEntryV2:
    event: str
    filename: str
    domain: str
    id_field: str
    record_id: str
    canonical_bytes: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class _TerminalTombstoneV2:
    handle: "H1GuardianRuntimePermitHandoffV2"
    cancellation: "H1GuardianRuntimeCancellationV2"
    cancellation_id: str
    canonical_bytes: bytes = field(repr=False)
    owner_pid: int
    owner_thread: threading.Thread = field(repr=False)
    owner_thread_id: int


@dataclass(frozen=True, slots=True)
class _LiveTakeoverRecordV2:
    takeover: "H1GuardianRuntimePreparedTakeoverV2"
    handoff_record: _LiveHandoffRecordV2
    adapter: "H1GuardianRuntimeConsumerAdapterV2"


@dataclass(frozen=True, slots=True)
class _LiveAdapterRecordV2:
    adapter: "H1GuardianRuntimeConsumerAdapterV2"
    owner_pid: int
    owner_thread: threading.Thread = field(repr=False)
    owner_thread_id: int
    adapter_id: str
    document_bytes: bytes = field(repr=False)


class H1GuardianRuntimePermitHandoffV2:
    """Issuer-only process-local typed escrow; it contains no launch API."""

    __slots__ = ("_owner_pid", "_owner_thread", "_owner_thread_id", "_issuer")

    def __init__(self, issuer: object) -> None:
        if issuer is not _HANDOFF_ISSUER:
            _fail("guardian V2 public handoff is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._issuer = issuer

    @property
    def state(self) -> str:
        record = _LIVE_HANDOFFS.get(id(self)) or _QUARANTINED_HANDOFFS.get(id(self))
        if record is not None and record.handle is self:
            return record.state
        tombstone = _TERMINAL_CANCELLATIONS.get(id(self))
        if tombstone is not None and tombstone.handle is self:
            return "CLOSED_CANCELLED_UNCONSUMED"
        return "FORK_POISONED_OR_INVALID"

    @property
    def handoff_id(self) -> str:
        _validate_live_code_closure()
        record = _LIVE_HANDOFFS.get(id(self)) or _QUARANTINED_HANDOFFS.get(id(self))
        if record is None or record.handle is not self:
            _fail("guardian V2 handoff ID is unavailable outside its live lifecycle")
        return record.entries["PUBLIC_HANDOFF"].record_id

    def to_document(self) -> dict[str, Any]:
        _validate_live_code_closure()
        record = _require_handoff(self, cleanup=True)
        return record.entries["PUBLIC_HANDOFF"].to_document()

    def artifact_graph(self) -> dict[str, dict[str, Any]]:
        _validate_live_code_closure()
        record = _require_handoff(self, cleanup=True)
        return {
            event: entry.to_document()
            for event, entry in sorted(record.entries.items())
        }

    def __copy__(self) -> NoReturn:
        _fail("guardian V2 public handoff cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("guardian V2 public handoff cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("guardian V2 public handoff cannot be copied or pickled")


class H1GuardianRuntimeConsumerAdapterV2:
    """Source-pinned identity for a later nonlaunching consumer boundary."""

    __slots__ = (
        "_owner_pid",
        "_owner_thread",
        "_owner_thread_id",
        "_issuer",
        "_consumer_key",
        "_consumer_source_path",
        "_consumer_source_fact",
        "_consumer_callable",
        "_consumer_code",
        "_consumer_globals",
        "_consumer_defaults",
        "_consumer_kwdefaults",
        "_document_bytes",
        "adapter_id",
    )

    def __init__(
        self,
        issuer: object,
        *,
        consumer_key: str,
        consumer_source_path: Path,
        consumer_source_fact: tuple[int, int, int, int, str],
        consumer_callable: Any,
        document_bytes: bytes,
        adapter_id: str,
    ) -> None:
        if issuer is not _ADAPTER_ISSUER:
            _fail("guardian V2 consumer adapter is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._issuer = issuer
        self._consumer_key = consumer_key
        self._consumer_source_path = consumer_source_path
        self._consumer_source_fact = consumer_source_fact
        self._consumer_callable = consumer_callable
        self._consumer_code = consumer_callable.__code__
        self._consumer_globals = consumer_callable.__globals__
        self._consumer_defaults = consumer_callable.__defaults__
        self._consumer_kwdefaults = (
            dict(consumer_callable.__kwdefaults__)
            if consumer_callable.__kwdefaults__
            else None
        )
        self._document_bytes = document_bytes
        self.adapter_id = adapter_id

    def to_document(self) -> dict[str, Any]:
        _validate_live_code_closure()
        _require_consumer_adapter(self)
        return ids_v1.loads_canonical_json(self._document_bytes)

    def __copy__(self) -> NoReturn:
        _fail("guardian V2 consumer adapter cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("guardian V2 consumer adapter cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("guardian V2 consumer adapter cannot be copied or pickled")


class H1GuardianRuntimePreparedTakeoverV2:
    """Typed preparation only: no permit consumption and no grant accessor."""

    __slots__ = ("_owner_pid", "_owner_thread", "_owner_thread_id", "_issuer")

    def __init__(self, issuer: object) -> None:
        if issuer is not _TAKEOVER_ISSUER:
            _fail("guardian V2 prepared takeover is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._issuer = issuer

    def to_document(self) -> dict[str, Any]:
        _validate_live_code_closure()
        live = _require_takeover(self)
        return live.handoff_record.entries["TAKEOVER_PREPARATION"].to_document()

    def __copy__(self) -> NoReturn:
        _fail("guardian V2 prepared takeover cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("guardian V2 prepared takeover cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("guardian V2 prepared takeover cannot be copied or pickled")


@dataclass(frozen=True, slots=True)
class H1GuardianRuntimeCancellationV2:
    canonical_bytes: bytes = field(repr=False)
    cancellation_id: str = field(init=False)
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._issuer is not _CANCELLATION_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("guardian V2 cancellation is caller-minted")
        document = ids_v1.loads_canonical_json(self.canonical_bytes)
        supplied = _verify_content_document(
            document,
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CANCELLATION_V1_DOMAIN,
            id_field="guardian_runtime_v2_cancellation_id",
            label="guardian V2 cancellation",
        )
        object.__setattr__(self, "cancellation_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


def _exact_write(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        count = os.write(descriptor, raw[offset:])
        if count <= 0:
            _fail("guardian V2 journal write made no progress")
        offset += count


def _restore_signal_mask(original_mask: Any) -> None:
    e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001
    if _TEST_ONLY_SIGNAL_RESTORE_FAULT:
        raise RuntimeError("injected guardian V2 signal-restore boundary fault")


def _append_record(
    record: _LiveHandoffRecordV2,
    *,
    event: str,
    domain: str,
    id_field: str,
    payload: Mapping[str, Any],
) -> _JournalEntryV2:
    if event in record.entries or record.directory_fd < 0:
        _fail("guardian V2 journal event is duplicate or closed")
    document = _with_id(payload, domain=domain, id_field=id_field)
    raw = ids_v1.canonical_json_bytes(document)
    filename = f"{record.next_index:04d}_{event}.json"
    pending = record.pending_entry
    if pending is None:
        pending = _PendingJournalEntryV2(
            event, filename, domain, id_field, document[id_field], raw
        )
        record.pending_entry = pending
        try:
            descriptor = os.open(
                filename,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
                dir_fd=record.directory_fd,
            )
        except FileExistsError:
            descriptor = os.open(
                filename,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=record.directory_fd,
            )
    else:
        if (
            pending.event != event
            or pending.filename != filename
            or pending.domain != domain
            or pending.id_field != id_field
            or pending.record_id != document[id_field]
            or pending.canonical_bytes != raw
        ):
            _fail("guardian V2 journal has a different unfinished event")
        try:
            descriptor = os.open(
                filename,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=record.directory_fd,
            )
        except FileNotFoundError:
            descriptor = os.open(
                filename,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
                dir_fd=record.directory_fd,
            )
    try:
        status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(status.st_mode)
            or status.st_uid != os.geteuid()
            or status.st_nlink != 1
            or stat.S_IMODE(status.st_mode) != 0o600
        ):
            _fail("guardian V2 pending journal inode changed")
        if (
            _TEST_ONLY_JOURNAL_FAULT_EVENT == event
            and _TEST_ONLY_JOURNAL_FAULT_STAGE == "O_EXCL"
        ):
            raise RuntimeError("injected guardian V2 journal O_EXCL boundary fault")
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        if (
            _TEST_ONLY_JOURNAL_FAULT_EVENT == event
            and _TEST_ONLY_JOURNAL_FAULT_STAGE == "WRITE"
        ):
            _exact_write(descriptor, raw[: max(1, len(raw) // 2)])
            raise RuntimeError("injected guardian V2 journal write boundary fault")
        _exact_write(descriptor, raw)
        if (
            _TEST_ONLY_JOURNAL_FAULT_EVENT == event
            and _TEST_ONLY_JOURNAL_FAULT_STAGE == "FILE_FSYNC"
        ):
            raise RuntimeError("injected guardian V2 journal file-fsync boundary fault")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if (
        _TEST_ONLY_JOURNAL_FAULT_EVENT == event
        and _TEST_ONLY_JOURNAL_FAULT_STAGE == "DIR_FSYNC"
    ):
        raise RuntimeError("injected guardian V2 journal dir-fsync boundary fault")
    os.fsync(record.directory_fd)
    entry = _JournalEntryV2(
        event,
        filename,
        domain,
        id_field,
        document[id_field],
        raw,
    )
    record.entries[event] = entry
    record.filenames.append(filename)
    record.next_index += 1
    record.pending_entry = None
    if _TEST_ONLY_START_FAULT_AFTER_EVENT == event:
        raise RuntimeError(f"injected guardian V2 start fault after {event}")
    return entry


def _finish_pending_record(record: _LiveHandoffRecordV2) -> None:
    pending = record.pending_entry
    if pending is None:
        return
    document = ids_v1.loads_canonical_json(pending.canonical_bytes)
    payload = dict(document)
    supplied = payload.pop(pending.id_field, None)
    if supplied != pending.record_id:
        _fail("guardian V2 pending journal ID changed")
    _append_record(
        record,
        event=pending.event,
        domain=pending.domain,
        id_field=pending.id_field,
        payload=payload,
    )


def _source_closure_payload(
    preregistration: H1GuardianRuntimeGenesisPreregistrationV2,
    runtime_document: Mapping[str, Any],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for label in sorted(_SOURCE_PATHS):
        path = _SOURCE_PATHS[label]
        raw = path.read_bytes()
        fact = _IMPORT_SOURCE_FACTS[label]
        sources.append(
            {
                "label": label,
                "repository_relative_path": os.fspath(path.relative_to(_SELF_PATH.parents[2])),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "device": fact[0],
                "inode": fact[1],
                "mode": fact[2],
                "source_bytes_hex": raw.hex(),
            }
        )
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_source_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_runtime_v2_preregistration_id": preregistration.preregistration_id,
        "h1_e5a_runtime_lease_successor_id": runtime_document[
            "h1_e5a_runtime_lease_successor_id"
        ],
        "logical_occurrence_id": runtime_document["logical_occurrence_id"],
        "route_attempt_id": runtime_document["route_attempt_id"],
        "decision_point_id": runtime_document["decision_point_id"],
        "BuildEpoch_id": runtime_document["BuildEpoch_id"],
        "retained_source_bytes": sources,
        "source_frozen_before_any_v2_grant_issuance": True,
        "b2b_v1_source_or_registry_used": False,
        "b2c_source_or_private_api_used": False,
        **_locked_claims(),
    }


def _candidate_fact(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    candidate: b2a_v1.H1E5ANonlaunchableLeafCandidateV1,
    slot: str,
) -> dict[str, Any]:
    leaf = SLOT_TO_LEAF[slot]
    canonical_slot = e5a_v1._role_fd_slot(leaf)  # noqa: SLF001
    descriptor = candidate._fd_slots[canonical_slot]  # noqa: SLF001
    source_descriptor = runtime._role_fds[leaf]  # noqa: SLF001
    if descriptor < 0 or source_descriptor < 0:
        _fail("guardian V2 candidate lost its exact descriptor support")
    try:
        status = os.fstat(descriptor)
        identity = e5a_v1._registry_fd_identity(descriptor)  # noqa: SLF001
        source_identity = e5a_v1._registry_fd_identity(source_descriptor)  # noqa: SLF001
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        fd_flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
    except OSError as error:
        raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
            "guardian V2 candidate descriptor support is unavailable"
        ) from error
    owner_record = e5a_v1._OWNED_FDS.get(descriptor)  # noqa: SLF001
    if (
        type(candidate) is not b2a_v1.H1E5ANonlaunchableLeafCandidateV1
        or candidate.slot != slot
        or candidate.leaf != leaf
        or candidate.state != "ISSUED"
        or candidate.launch_authority is not False
        or candidate._runtime_id != id(runtime)  # noqa: SLF001
        or descriptor < 0
        or identity != source_identity
        or owner_record is None
        or owner_record.owner is not candidate
        or owner_record.slot != canonical_slot
        or not stat.S_ISDIR(status.st_mode)
        or descriptor_flags & os.O_PATH != os.O_PATH
        or fd_flags & fcntl.FD_CLOEXEC == 0
        or sum(value >= 0 for value in candidate._fd_slots.values()) != 1  # noqa: SLF001
    ):
        _fail("guardian V2 candidate identity or exact support changed")
    return {
        "slot": slot,
        "leaf": leaf,
        "candidate_runtime_object_id": id(runtime),
        "candidate_object_id": id(candidate),
        "descriptor_identity": list(identity),
        "source_identity": list(source_identity),
        "same_cgroup_inode": True,
        "distinct_open_file_description": True,
        "cloexec": True,
        "open_mode": "O_PATH|O_DIRECTORY",
        "launch_authority": False,
    }


def _open_private_empty_journal(path: Path) -> int:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    status = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(status.st_mode)
        or status.st_uid != os.geteuid()
        or stat.S_IMODE(status.st_mode) & 0o077
        or os.listdir(descriptor)
    ):
        os.close(descriptor)
        _fail("guardian V2 journal directory must be private and empty")
    return descriptor


def _same_owner(handle: H1GuardianRuntimePermitHandoffV2) -> bool:
    return (
        handle._owner_pid == os.getpid()  # noqa: SLF001
        and handle._owner_thread_id == threading.get_ident()  # noqa: SLF001
        and handle._owner_thread is threading.current_thread()  # noqa: SLF001
    )


def _same_owner_object(value: Any) -> bool:
    return (
        getattr(value, "_owner_pid", None) == os.getpid()
        and getattr(value, "_owner_thread_id", None) == threading.get_ident()
        and getattr(value, "_owner_thread", None) is threading.current_thread()
    )


def _require_consumer_adapter(
    adapter: H1GuardianRuntimeConsumerAdapterV2,
) -> H1GuardianRuntimeConsumerAdapterV2:
    live = _LIVE_CONSUMER_ADAPTERS.get(id(adapter))
    if (
        type(adapter) is not H1GuardianRuntimeConsumerAdapterV2
        or adapter._issuer is not _ADAPTER_ISSUER  # noqa: SLF001
        or not _same_owner_object(adapter)
        or live is None
        or live.adapter is not adapter
        or live.owner_pid != adapter._owner_pid  # noqa: SLF001
        or live.owner_thread is not adapter._owner_thread  # noqa: SLF001
        or live.owner_thread_id != adapter._owner_thread_id  # noqa: SLF001
        or live.adapter_id != adapter.adapter_id
        or live.document_bytes != adapter._document_bytes  # noqa: SLF001
        or getattr(adapter._consumer_callable, "__code__", None)  # noqa: SLF001
        is not adapter._consumer_code  # noqa: SLF001
        or getattr(adapter._consumer_callable, "__globals__", None)  # noqa: SLF001
        is not adapter._consumer_globals  # noqa: SLF001
        or getattr(adapter._consumer_callable, "__defaults__", None)  # noqa: SLF001
        != adapter._consumer_defaults  # noqa: SLF001
        or getattr(adapter._consumer_callable, "__kwdefaults__", None)  # noqa: SLF001
        != adapter._consumer_kwdefaults  # noqa: SLF001
        or _source_fact(adapter._consumer_source_path)  # noqa: SLF001
        != adapter._consumer_source_fact  # noqa: SLF001
    ):
        _fail("guardian V2 consumer adapter identity or source changed")
    document = ids_v1.loads_canonical_json(adapter._document_bytes)  # noqa: SLF001
    supplied = _verify_content_document(
        document,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
        id_field="guardian_runtime_v2_consumer_adapter_id",
        label="guardian V2 consumer adapter",
    )
    if supplied != adapter.adapter_id:
        _fail("guardian V2 consumer adapter ID changed")
    try:
        retained_source = bytes.fromhex(document.get("consumer_source_bytes_hex"))
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
            "guardian V2 consumer adapter retained source is malformed"
        ) from error
    if (
        retained_source != adapter._consumer_source_path.read_bytes()  # noqa: SLF001
        or document.get("consumer_source_sha256")
        != hashlib.sha256(retained_source).hexdigest()
        or document.get("consumer_source_byte_count") != len(retained_source)
        or document.get("adapter_state") != "REGISTERED_PREPARATION_ONLY"
        or document.get("consumer_invoked") is not False
    ):
        _fail("guardian V2 consumer adapter source or semantics changed")
    return adapter


def register_h1_guardian_runtime_consumer_adapter_v2(
    *, consumer_key: str, consumer_source_path: Path | str, consumer_callable: Any
) -> H1GuardianRuntimeConsumerAdapterV2:
    """Register exact future-consumer preparation code without invoking it."""

    _validate_live_code_closure()
    if (
        type(consumer_key) is not str
        or not consumer_key
        or len(consumer_key) > 128
        or not callable(consumer_callable)
        or getattr(consumer_callable, "__code__", None) is None
    ):
        _fail("guardian V2 consumer adapter registration is malformed")
    path = Path(consumer_source_path).resolve(strict=True)
    fact = _source_fact(path)
    callable_globals = getattr(consumer_callable, "__globals__", None)
    callable_source = (
        Path(callable_globals.get("__file__")).resolve(strict=True)
        if type(callable_globals) is dict
        and type(callable_globals.get("__file__")) is str
        else None
    )
    if callable_source != path:
        _fail("guardian V2 consumer callable is not owned by its pinned source")
    payload = {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_consumer_adapter.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "consumer_key": consumer_key,
        "consumer_source_sha256": fact[-1],
        "consumer_source_byte_count": fact[3],
        "consumer_source_bytes_hex": path.read_bytes().hex(),
        "consumer_callable_module": consumer_callable.__module__,
        "consumer_callable_qualname": consumer_callable.__qualname__,
        "adapter_state": "REGISTERED_PREPARATION_ONLY",
        "consumer_invoked": False,
        **_locked_claims(),
    }
    document = _with_id(
        payload,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
        id_field="guardian_runtime_v2_consumer_adapter_id",
    )
    raw = ids_v1.canonical_json_bytes(document)
    adapter = H1GuardianRuntimeConsumerAdapterV2(
        _ADAPTER_ISSUER,
        consumer_key=consumer_key,
        consumer_source_path=path,
        consumer_source_fact=fact,
        consumer_callable=consumer_callable,
        document_bytes=raw,
        adapter_id=document["guardian_runtime_v2_consumer_adapter_id"],
    )
    _LIVE_CONSUMER_ADAPTERS[id(adapter)] = _LiveAdapterRecordV2(
        adapter,
        adapter._owner_pid,  # noqa: SLF001
        adapter._owner_thread,  # noqa: SLF001
        adapter._owner_thread_id,  # noqa: SLF001
        adapter.adapter_id,
        adapter._document_bytes,  # noqa: SLF001
    )
    _require_consumer_adapter(adapter)
    return adapter


def _require_takeover(
    takeover: H1GuardianRuntimePreparedTakeoverV2,
) -> _LiveTakeoverRecordV2:
    if (
        type(takeover) is not H1GuardianRuntimePreparedTakeoverV2
        or takeover._issuer is not _TAKEOVER_ISSUER  # noqa: SLF001
        or not _same_owner_object(takeover)
    ):
        _fail("guardian V2 takeover requires its exact owner object")
    live = _LIVE_TAKEOVERS.get(id(takeover))
    if (
        live is None
        or live.takeover is not takeover
        or live.handoff_record.owner_pid != takeover._owner_pid  # noqa: SLF001
        or live.handoff_record.owner_thread is not takeover._owner_thread  # noqa: SLF001
        or live.handoff_record.owner_thread_id != takeover._owner_thread_id  # noqa: SLF001
        or live.handoff_record.takeover is not takeover
        or live.handoff_record.state != "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED"
    ):
        _fail("guardian V2 prepared takeover is not issuer-live")
    _require_consumer_adapter(live.adapter)
    return live


def _require_handoff(
    handle: H1GuardianRuntimePermitHandoffV2, *, cleanup: bool = False
) -> _LiveHandoffRecordV2:
    if (
        type(handle) is not H1GuardianRuntimePermitHandoffV2
        or handle._issuer is not _HANDOFF_ISSUER  # noqa: SLF001
        or not _same_owner(handle)
    ):
        _fail("guardian V2 operation requires one exact owner-bound handoff")
    record = _LIVE_HANDOFFS.get(id(handle))
    if record is None and cleanup:
        record = _QUARANTINED_HANDOFFS.get(id(handle))
    allowed = (
        {
            "HANDOFF_ESCROWED_UNCONSUMED",
            "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED",
            "REVOKE_DURABLE",
            "CANCEL_CLEANUP_PENDING",
        }
        if cleanup
        else {
            "HANDOFF_ESCROWED_UNCONSUMED",
            "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED",
        }
    )
    if (
        record is None
        or record.handle is not handle
        or record.owner_pid != handle._owner_pid  # noqa: SLF001
        or record.owner_thread is not handle._owner_thread  # noqa: SLF001
        or record.owner_thread_id != handle._owner_thread_id  # noqa: SLF001
        or record.owner_pid != os.getpid()
        or record.owner_thread is not threading.current_thread()
        or record.owner_thread_id != threading.get_ident()
        or record.state not in allowed
        or _RUNTIME_RESERVATIONS.get(id(record.runtime)) is not record
    ):
        _fail("guardian V2 handoff is not issuer-live in an allowed state")
    return record


def _verify_source_closure(entry: _JournalEntryV2) -> dict[str, Any]:
    document = entry.to_document()
    _verify_content_document(
        document,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_SOURCE_CLOSURE_V1_DOMAIN,
        id_field="guardian_runtime_v2_source_closure_id",
        label="guardian V2 source closure",
    )
    if (
        document.get("schema")
        != "acfqp.k7_h1_guardian_runtime_v2_source_closure.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("source_frozen_before_any_v2_grant_issuance") is not True
        or document.get("b2b_v1_source_or_registry_used") is not False
        or document.get("b2c_source_or_private_api_used") is not False
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("guardian V2 source closure schema or claim locks changed")
    rows = document.get("retained_source_bytes")
    if type(rows) is not list or len(rows) != len(_SOURCE_PATHS):
        _fail("guardian V2 source closure inventory changed")
    by_label = {row.get("label"): row for row in rows if type(row) is dict}
    if set(by_label) != set(_SOURCE_PATHS):
        _fail("guardian V2 source closure labels changed")
    for label, path in _SOURCE_PATHS.items():
        row = by_label[label]
        try:
            raw = bytes.fromhex(row.get("source_bytes_hex"))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 embedded source bytes are malformed"
            ) from error
        fact = _IMPORT_SOURCE_FACTS[label]
        if (
            raw != path.read_bytes()
            or row.get("sha256") != hashlib.sha256(raw).hexdigest()
            or row.get("byte_count") != len(raw)
            or (row.get("device"), row.get("inode"), row.get("mode"))
            != fact[:3]
        ):
            _fail("guardian V2 embedded source identity changed")
    return document


def _verify_journal(record: _LiveHandoffRecordV2) -> None:
    if record.directory_fd < 0 or set(os.listdir(record.directory_fd)) != set(
        record.filenames
    ):
        _fail("guardian V2 journal inventory changed")
    for entry in record.entries.values():
        raw = os.open(
            entry.filename,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=record.directory_fd,
        )
        try:
            observed = os.read(raw, len(entry.canonical_bytes) + 1)
        finally:
            os.close(raw)
        if observed != entry.canonical_bytes:
            _fail("guardian V2 durable journal bytes changed")
        document = entry.to_document()
        if ids_v1.canonical_json_bytes(document) != entry.canonical_bytes:
            _fail("guardian V2 journal record is not canonical")
        if (
            _verify_content_document(
                document,
                domain=entry.domain,
                id_field=entry.id_field,
                label=f"guardian V2 {entry.event}",
            )
            != entry.record_id
        ):
            _fail("guardian V2 journal record identity changed")


def _verify_live_record(record: _LiveHandoffRecordV2) -> dict[str, Any]:
    _validate_live_code_closure()
    runtime_document = b2a_v1.verify_h1_e5a_runtime_lease_successor_v1(record.runtime)
    _verify_journal(record)
    source = _verify_source_closure(record.entries["SOURCE_CLOSURE"])
    prereg = _verify_preregistration(record.preregistration)
    if (
        source.get("guardian_runtime_v2_preregistration_id")
        != record.preregistration.preregistration_id
        or source.get("h1_e5a_runtime_lease_successor_id")
        != record.runtime.successor_id
        or prereg.get("expected_guardian_identity") != _guardian_identity()
    ):
        _fail("guardian V2 source/preregistration/runtime join changed")
    current_facts: list[dict[str, Any]] = []
    for slot in SLOT_ORDER:
        candidate = record.candidates.get(slot)
        if candidate is None:
            _fail("guardian V2 live handoff lost one slot grant")
        fact = _candidate_fact(record.runtime, candidate, slot)
        if fact != record.grant_facts.get(slot):
            _fail("guardian V2 slot grant was swapped or changed")
        current_facts.append(fact)
    genesis = record.entries["GENESIS"].to_document()
    intent = record.entries["BIRTH_INTENT"].to_document()
    permit = record.entries["BIRTH_PERMIT"].to_document()
    handoff = record.entries["PUBLIC_HANDOFF"].to_document()
    identity_fields = (
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "BuildEpoch_id",
    )
    if any(handoff.get(key) != runtime_document.get(key) for key in identity_fields):
        _fail("guardian V2 handoff crossed its occurrence identity")
    if (
        genesis.get("guardian_runtime_v2_source_closure_id")
        != record.entries["SOURCE_CLOSURE"].record_id
        or genesis.get("h1_e5a_runtime_lease_successor_id") != record.runtime.successor_id
        or intent.get("guardian_runtime_v2_genesis_id")
        != record.entries["GENESIS"].record_id
        or permit.get("guardian_runtime_v2_birth_intent_id")
        != record.entries["BIRTH_INTENT"].record_id
        or handoff.get("guardian_runtime_v2_birth_permit_id")
        != record.entries["BIRTH_PERMIT"].record_id
        or handoff.get("grant_facts") != current_facts
        or handoff.get("handoff_state") != "HANDOFF_ESCROWED_UNCONSUMED"
        or handoff.get("launch_authority_present") is not False
        or any(handoff.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("guardian V2 handoff artifact graph changed")
    if record.state == "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED":
        if record.takeover is None:
            _fail("guardian V2 takeover state lost its typed owner")
        live = _require_takeover(record.takeover)
        takeover_document = record.entries["TAKEOVER_PREPARATION"].to_document()
        if (
            takeover_document.get("guardian_runtime_v2_public_handoff_id")
            != record.entries["PUBLIC_HANDOFF"].record_id
            or takeover_document.get("guardian_runtime_v2_consumer_adapter_id")
            != live.adapter.adapter_id
            or takeover_document.get("consumer_adapter")
            != live.adapter.to_document()
            or takeover_document.get("takeover_state")
            != "PREPARED_UNCONSUMED_NONLAUNCHABLE"
            or takeover_document.get("consumer_invoked") is not False
            or takeover_document.get("grant_access_exposed") is not False
        ):
            _fail("guardian V2 takeover preparation graph changed")
    return handoff


def start_and_handoff_h1_guardian_runtime_genesis_v2(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    preregistration: H1GuardianRuntimeGenesisPreregistrationV2,
    journal_directory: Path | str,
) -> H1GuardianRuntimePermitHandoffV2:
    """Create five nonlaunchable grants and return no intermediate session."""

    prereg = _verify_preregistration(preregistration)
    if type(runtime) is not b2a_v1.H1E5ARuntimeLeaseSuccessorV1:
        _fail("guardian V2 requires one exact B2-A runtime")
    runtime_document = b2a_v1.verify_h1_e5a_runtime_lease_successor_v1(runtime)
    if runtime.state != "PREPARED_SUCCESSOR" or runtime.grant_states() != {
        slot: "AVAILABLE" for slot in SLOT_ORDER
    }:
        _fail("guardian V2 requires one pristine B2-A PREPARED_SUCCESSOR")
    path = Path(os.path.abspath(os.fspath(journal_directory)))
    directory_fd = _open_private_empty_journal(path)
    handle = H1GuardianRuntimePermitHandoffV2(_HANDOFF_ISSUER)
    record = _LiveHandoffRecordV2(
        handle,
        runtime,
        preregistration,
        path,
        directory_fd,
        os.getpid(),
        threading.current_thread(),
        threading.get_ident(),
    )
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    primary: BaseException | None = None
    cleanup_failure: BaseException | None = None
    try:
        with _V2_LOCK:
            if id(runtime) in _RUNTIME_RESERVATIONS:
                _fail("guardian V2 runtime already has one reservation")
            if threading.get_ident() in _STARTING_BY_THREAD:
                _fail("guardian V2 owner thread already has one starting handoff")
            _RUNTIME_RESERVATIONS[id(runtime)] = record
            _STARTING_BY_THREAD[threading.get_ident()] = record
        source_entry = _append_record(
            record,
            event="SOURCE_CLOSURE",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_SOURCE_CLOSURE_V1_DOMAIN,
            id_field="guardian_runtime_v2_source_closure_id",
            payload=_source_closure_payload(preregistration, runtime_document),
        )
        for index, slot in enumerate(SLOT_ORDER, start=1):
            candidate = b2a_v1.issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
                runtime, slot=slot
            )
            record.candidates[slot] = candidate
            record.grant_facts[slot] = _candidate_fact(runtime, candidate, slot)
            if _TEST_ONLY_START_FAULT_AFTER_GRANT == index:
                raise RuntimeError(
                    f"injected guardian V2 start fault after grant {index}"
                )
        common = {
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "guardian_runtime_v2_source_closure_id": source_entry.record_id,
            "h1_e5a_runtime_lease_successor_id": runtime.successor_id,
            "logical_occurrence_id": runtime_document["logical_occurrence_id"],
            "route_attempt_id": runtime_document["route_attempt_id"],
            "decision_point_id": runtime_document["decision_point_id"],
            "BuildEpoch_id": runtime_document["BuildEpoch_id"],
        }
        genesis = _append_record(
            record,
            event="GENESIS",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_GENESIS_V1_DOMAIN,
            id_field="guardian_runtime_v2_genesis_id",
            payload={
                "schema": "acfqp.k7_h1_guardian_runtime_v2_genesis.v1",
                **common,
                "guardian_runtime_v2_preregistration_id": preregistration.preregistration_id,
                "guardian_identity": prereg["expected_guardian_identity"],
                "five_slot_grants_issued": True,
                "grant_facts": [record.grant_facts[slot] for slot in SLOT_ORDER],
                "intermediate_running_session_exposed": False,
                **_locked_claims(),
            },
        )
        intent = _append_record(
            record,
            event="BIRTH_INTENT",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_BIRTH_INTENT_V1_DOMAIN,
            id_field="guardian_runtime_v2_birth_intent_id",
            payload={
                "schema": "acfqp.k7_h1_guardian_runtime_v2_birth_intent.v1",
                **common,
                "guardian_runtime_v2_genesis_id": genesis.record_id,
                "slot": "SUPERVISOR",
                "leaf": "CONTROL",
                "intent_state": "PREPARED_DURABLE_NO_LAUNCH",
                "permit_issued": False,
                **_locked_claims(),
            },
        )
        permit = _append_record(
            record,
            event="BIRTH_PERMIT",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_BIRTH_PERMIT_V1_DOMAIN,
            id_field="guardian_runtime_v2_birth_permit_id",
            payload={
                "schema": "acfqp.k7_h1_guardian_runtime_v2_birth_permit.v1",
                **common,
                "guardian_runtime_v2_genesis_id": genesis.record_id,
                "guardian_runtime_v2_birth_intent_id": intent.record_id,
                "permit_state": "ISSUED_UNCONSUMED_NONLAUNCHABLE_IN_THIS_SLICE",
                "all_five_grants_escrowed": True,
                "permit_consumable_in_this_slice": False,
                **_locked_claims(),
            },
        )
        _append_record(
            record,
            event="PUBLIC_HANDOFF",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_PUBLIC_HANDOFF_V1_DOMAIN,
            id_field="guardian_runtime_v2_public_handoff_id",
            payload={
                "schema": "acfqp.k7_h1_guardian_runtime_v2_public_handoff.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "readiness": READINESS,
                "guardian_runtime_v2_source_closure_id": source_entry.record_id,
                "guardian_runtime_v2_genesis_id": genesis.record_id,
                "guardian_runtime_v2_birth_intent_id": intent.record_id,
                "guardian_runtime_v2_birth_permit_id": permit.record_id,
                "h1_e5a_runtime_lease_successor_id": runtime.successor_id,
                "logical_occurrence_id": runtime_document["logical_occurrence_id"],
                "route_attempt_id": runtime_document["route_attempt_id"],
                "decision_point_id": runtime_document["decision_point_id"],
                "BuildEpoch_id": runtime_document["BuildEpoch_id"],
                "handoff_state": "HANDOFF_ESCROWED_UNCONSUMED",
                "grant_facts": [record.grant_facts[slot] for slot in SLOT_ORDER],
                "intermediate_running_session_exposed": False,
                "launch_authority_present": False,
                "b2b_v1_imported_or_started": False,
                "b2c_private_api_imported_or_used": False,
                **_locked_claims(),
            },
        )
        with _V2_LOCK:
            record.state = "HANDOFF_ESCROWED_UNCONSUMED"
            _LIVE_HANDOFFS[id(handle)] = record
            _STARTING_BY_THREAD.pop(threading.get_ident(), None)
        _verify_live_record(record)
        return handle
    except BaseException as error:
        primary = error
        try:
            _recover_failed_start_record(record, primary_reason=type(error).__name__)
        except BaseException as cleanup_error:
            cleanup_failure = cleanup_error
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 start failed with retryable cleanup quarantine",
                cleanup_handle=handle,
                primary_error=primary,
                cleanup_error=cleanup_error,
            ) from cleanup_error
        raise
    finally:
        try:
            _restore_signal_mask(original_mask)
        except BaseException as restoration_error:
            if primary is None:
                try:
                    cancel_h1_guardian_runtime_permit_handoff_v2(handle)
                except BaseException as error:
                    cleanup_failure = error
            recoverable = (
                handle
                if id(handle) in _LIVE_HANDOFFS
                or id(handle) in _QUARANTINED_HANDOFFS
                else None
            )
            compound = ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 start signal restoration failed",
                cleanup_handle=recoverable,
                primary_error=primary,
                cleanup_error=cleanup_failure,
                restoration_error=restoration_error,
            )
            raise compound from (cleanup_failure or restoration_error)


def verify_h1_guardian_runtime_permit_handoff_v2(
    handle: H1GuardianRuntimePermitHandoffV2,
) -> dict[str, Any]:
    _validate_live_code_closure()
    record = _require_handoff(handle)
    with _V2_LOCK:
        return _verify_live_record(record)


def _exact_identity(value: str, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"guardian V2 {label} is not one exact identity")
    return value


def prepare_h1_guardian_runtime_consumer_takeover_v2(
    handle: H1GuardianRuntimePermitHandoffV2,
    *,
    adapter: H1GuardianRuntimeConsumerAdapterV2,
    consumer_preparation_id: str,
    launch_preparation_id: str,
) -> H1GuardianRuntimePreparedTakeoverV2:
    """Freeze a public next-consumer boundary without consuming the permit."""

    _validate_live_code_closure()
    record = _require_handoff(handle)
    adapter = _require_consumer_adapter(adapter)
    consumer_preparation_id = _exact_identity(
        consumer_preparation_id, label="consumer preparation ID"
    )
    launch_preparation_id = _exact_identity(
        launch_preparation_id, label="launch preparation ID"
    )
    if record.takeover is not None:
        live = _require_takeover(record.takeover)
        document = live.takeover.to_document()
        if (
            live.adapter is not adapter
            or document.get("consumer_preparation_id") != consumer_preparation_id
            or document.get("launch_preparation_id") != launch_preparation_id
        ):
            _fail("guardian V2 takeover preparation was already frozen differently")
        return live.takeover
    runtime_document = record.runtime.to_document()
    payload = {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_takeover_preparation.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_runtime_v2_public_handoff_id": record.entries[
            "PUBLIC_HANDOFF"
        ].record_id,
        "guardian_runtime_v2_birth_permit_id": record.entries[
            "BIRTH_PERMIT"
        ].record_id,
        "guardian_runtime_v2_consumer_adapter_id": adapter.adapter_id,
        "consumer_adapter": adapter.to_document(),
        "consumer_preparation_id": consumer_preparation_id,
        "launch_preparation_id": launch_preparation_id,
        "h1_e5a_runtime_lease_successor_id": record.runtime.successor_id,
        "logical_occurrence_id": runtime_document["logical_occurrence_id"],
        "route_attempt_id": runtime_document["route_attempt_id"],
        "decision_point_id": runtime_document["decision_point_id"],
        "BuildEpoch_id": runtime_document["BuildEpoch_id"],
        "takeover_state": "PREPARED_UNCONSUMED_NONLAUNCHABLE",
        "consumer_invoked": False,
        "grant_access_exposed": False,
        **_locked_claims(),
    }
    expected = _with_id(
        payload,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_TAKEOVER_PREPARATION_V1_DOMAIN,
        id_field="guardian_runtime_v2_takeover_preparation_id",
    )
    if "TAKEOVER_PREPARATION" in record.entries:
        if record.entries["TAKEOVER_PREPARATION"].to_document() != expected:
            _fail("guardian V2 durable takeover preparation changed")
    else:
        _append_record(
            record,
            event="TAKEOVER_PREPARATION",
            domain=(
                domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_TAKEOVER_PREPARATION_V1_DOMAIN
            ),
            id_field="guardian_runtime_v2_takeover_preparation_id",
            payload=payload,
        )
    takeover = H1GuardianRuntimePreparedTakeoverV2(_TAKEOVER_ISSUER)
    live = _LiveTakeoverRecordV2(takeover, record, adapter)
    with _V2_LOCK:
        if record.state != "HANDOFF_ESCROWED_UNCONSUMED":
            _fail("guardian V2 handoff state changed before takeover freeze")
        record.takeover = takeover
        record.state = "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED"
        _LIVE_TAKEOVERS[id(takeover)] = live
    _require_takeover(takeover)
    return takeover


def cancel_h1_guardian_runtime_prepared_takeover_v2(
    takeover: H1GuardianRuntimePreparedTakeoverV2,
) -> H1GuardianRuntimeCancellationV2:
    live = _require_takeover(takeover)
    return cancel_h1_guardian_runtime_permit_handoff_v2(live.handoff_record.handle)


def _close_candidates(record: _LiveHandoffRecordV2) -> None:
    closed_count = sum(
        candidate.state == "CLOSED" for candidate in record.candidates.values()
    )
    for slot in reversed(SLOT_ORDER):
        candidate = record.candidates.get(slot)
        if candidate is None or candidate.state == "CLOSED":
            continue
        b2a_v1.close_h1_e5a_nonlaunchable_leaf_candidate_v1(candidate)
        closed_count += 1
        if _TEST_ONLY_CANCEL_FAULT_AFTER_GRANT == closed_count:
            raise RuntimeError(
                f"injected guardian V2 cancel fault after grant {closed_count}"
            )


def _failure_payload(
    record: _LiveHandoffRecordV2,
    *,
    primary_reason: str,
    b2a_closure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    runtime_document = record.runtime.to_document()
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_failure_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e5a_runtime_lease_successor_id": record.runtime.successor_id,
        "logical_occurrence_id": runtime_document["logical_occurrence_id"],
        "route_attempt_id": runtime_document["route_attempt_id"],
        "decision_point_id": runtime_document["decision_point_id"],
        "BuildEpoch_id": runtime_document["BuildEpoch_id"],
        "guardian_runtime_v2_public_handoff_id": (
            record.entries.get("PUBLIC_HANDOFF").record_id
            if "PUBLIC_HANDOFF" in record.entries
            else {"kind": "NOT_APPLICABLE", "reason": "HANDOFF_NOT_PERSISTED"}
        ),
        "primary_failure_reason": primary_reason,
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "issued_grant_count": len(record.candidates),
        "consumed_grant_count": len(record.candidates),
        "unissued_grant_count": len(SLOT_ORDER) - len(record.candidates),
        "all_issued_grants_closed": True,
        "runtime_returned_to_pristine_prepared": not record.candidates,
        "runtime_and_e5a_hierarchy_closed": bool(record.candidates),
        "b2a_runtime_cleanup_closure": (
            dict(b2a_closure)
            if b2a_closure is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_GRANT_WAS_ISSUED"}
        ),
        "process_birth_count": 0,
        **_locked_claims(),
    }


def _finish_record_terminal(record: _LiveHandoffRecordV2) -> None:
    if record.directory_fd >= 0:
        os.close(record.directory_fd)
        record.directory_fd = -1
    with _V2_LOCK:
        if record.takeover is not None:
            _LIVE_TAKEOVERS.pop(id(record.takeover), None)
        _LIVE_HANDOFFS.pop(id(record.handle), None)
        _QUARANTINED_HANDOFFS.pop(id(record.handle), None)
        _STARTING_BY_THREAD.pop(record.owner_thread_id, None)
        _RUNTIME_RESERVATIONS.pop(id(record.runtime), None)


def _recover_failed_start_record(
    record: _LiveHandoffRecordV2, *, primary_reason: str
) -> None:
    with _V2_LOCK:
        record.state = "START_CLEANUP_PENDING"
        _LIVE_HANDOFFS.pop(id(record.handle), None)
        _QUARANTINED_HANDOFFS[id(record.handle)] = record
    _finish_pending_record(record)
    _close_candidates(record)
    if record.runtime.state != "PREPARED_SUCCESSOR" or record.runtime.grant_states() != {
        slot: ("CONSUMED" if slot in record.candidates else "AVAILABLE")
        for slot in SLOT_ORDER
    }:
        _fail("guardian V2 failed start did not restore candidate terminal states")
    closure_document: Mapping[str, Any] | None = None
    if record.candidates:
        if record.runtime.state == "CLOSED":
            closure = record.runtime._closure  # noqa: SLF001
            if closure is None:
                _fail("guardian V2 failed start lost its B2-A closure")
        else:
            closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(record.runtime)
        closure_document = closure.to_document()
    if "FAILURE_CLOSURE" not in record.entries:
        _append_record(
            record,
            event="FAILURE_CLOSURE",
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_FAILURE_CLOSURE_V1_DOMAIN,
            id_field="guardian_runtime_v2_failure_closure_id",
            payload=_failure_payload(
                record,
                primary_reason=primary_reason,
                b2a_closure=closure_document,
            ),
        )
    record.state = "ABORTED_PRECOMMIT"
    _finish_record_terminal(record)


def recover_h1_guardian_runtime_genesis_v2_failure_v1(
    handle: H1GuardianRuntimePermitHandoffV2,
) -> dict[str, Any]:
    if type(handle) is not H1GuardianRuntimePermitHandoffV2 or not _same_owner(handle):
        _fail("guardian V2 failure recovery requires its exact owner handle")
    record = _QUARANTINED_HANDOFFS.get(id(handle))
    if record is None or record.handle is not handle or record.state != "START_CLEANUP_PENDING":
        _fail("guardian V2 failure recovery handle is not retryable")
    _recover_failed_start_record(record, primary_reason="RECOVERED_START_FAILURE")
    return record.entries["FAILURE_CLOSURE"].to_document()


def _revoke_payload(record: _LiveHandoffRecordV2) -> dict[str, Any]:
    handoff = record.entries["PUBLIC_HANDOFF"]
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_unconsumed_revoke.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_runtime_v2_public_handoff_id": handoff.record_id,
        "guardian_runtime_v2_birth_permit_id": record.entries["BIRTH_PERMIT"].record_id,
        "h1_e5a_runtime_lease_successor_id": record.runtime.successor_id,
        "permit_state_before": record.revoke_state_before,
        "permit_state_after": "REVOKED_BEFORE_CONSUMPTION",
        "durable_revoke_precedes_grant_and_runtime_cleanup": True,
        "process_birth_count": 0,
        **_locked_claims(),
    }


def _cancellation_payload(
    record: _LiveHandoffRecordV2,
    *,
    b2a_closure: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = {
        event.lower(): entry.to_document()
        for event, entry in sorted(record.entries.items())
    }
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_cancellation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": "CLOSED_CANCELLED_UNCONSUMED_NO_BIRTH",
        "guardian_runtime_v2_public_handoff_id": record.entries[
            "PUBLIC_HANDOFF"
        ].record_id,
        "guardian_runtime_v2_unconsumed_revoke_id": record.entries[
            "UNCONSUMED_REVOKE"
        ].record_id,
        "h1_e5a_runtime_lease_successor_id": record.runtime.successor_id,
        "b2a_runtime_cleanup_closure": dict(b2a_closure),
        "embedded_artifacts": artifacts,
        "all_five_grants_closed": True,
        "runtime_and_e5a_hierarchy_closed": True,
        "process_birth_count": 0,
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "UNCONSUMED_HANDOFF_CANCELLED",
        **_locked_claims(),
    }


def cancel_h1_guardian_runtime_permit_handoff_v2(
    handle: H1GuardianRuntimePermitHandoffV2,
) -> H1GuardianRuntimeCancellationV2:
    _validate_live_code_closure()
    tombstone = _TERMINAL_CANCELLATIONS.get(id(handle))
    if tombstone is not None:
        if (
            type(handle) is not H1GuardianRuntimePermitHandoffV2
            or not _same_owner(handle)
            or tombstone.owner_pid != handle._owner_pid  # noqa: SLF001
            or tombstone.owner_thread is not handle._owner_thread  # noqa: SLF001
            or tombstone.owner_thread_id != handle._owner_thread_id  # noqa: SLF001
        ):
            _fail("guardian V2 terminal cancellation crossed its owner")
        if tombstone.handle is not handle:
            _fail("guardian V2 terminal cancellation key was reused")
        cancellation = tombstone.cancellation
        if (
            _CANCELLATION_TOMBSTONES.get(id(cancellation)) is not tombstone
            or cancellation.canonical_bytes != tombstone.canonical_bytes
            or cancellation.cancellation_id != tombstone.cancellation_id
        ):
            _fail("guardian V2 terminal cancellation object was mutated")
        _verify_cancellation_document(
            cancellation.to_document(),
            expected_canonical_bytes=tombstone.canonical_bytes,
            expected_cancellation_id=tombstone.cancellation_id,
        )
        return cancellation
    record = _require_handoff(handle, cleanup=True)
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _V2_LOCK:
            if "UNCONSUMED_REVOKE" not in record.entries:
                if record.revoke_state_before is None:
                    record.revoke_state_before = record.state
                _append_record(
                    record,
                    event="UNCONSUMED_REVOKE",
                    domain=(
                        domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_UNCONSUMED_REVOKE_V1_DOMAIN
                    ),
                    id_field="guardian_runtime_v2_unconsumed_revoke_id",
                    payload=_revoke_payload(record),
                )
            if record.state in {
                "HANDOFF_ESCROWED_UNCONSUMED",
                "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED",
                "CANCEL_CLEANUP_PENDING",
            }:
                record.state = "REVOKE_DURABLE"
                _LIVE_HANDOFFS.pop(id(handle), None)
                _QUARANTINED_HANDOFFS[id(handle)] = record
            record.state = "CANCEL_CLEANUP_PENDING"
        _close_candidates(record)
        if record.runtime.state == "CLOSED":
            closure = record.runtime._closure  # noqa: SLF001
            if closure is None:
                _fail("guardian V2 closed runtime lost its closure")
        else:
            closure = b2a_v1.close_h1_e5a_runtime_lease_successor_v1(record.runtime)
        if "CANCELLATION" not in record.entries:
            entry = _append_record(
                record,
                event="CANCELLATION",
                domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CANCELLATION_V1_DOMAIN,
                id_field="guardian_runtime_v2_cancellation_id",
                payload=_cancellation_payload(record, b2a_closure=closure.to_document()),
            )
            record.cancellation = H1GuardianRuntimeCancellationV2(
                entry.canonical_bytes, _issuer=_CANCELLATION_ISSUER
            )
        assert record.cancellation is not None
        record.state = "CLOSED_CANCELLED_UNCONSUMED"
        _verify_cancellation_document(
            record.cancellation.to_document(),
            expected_canonical_bytes=record.cancellation.canonical_bytes,
            expected_cancellation_id=record.cancellation.cancellation_id,
        )
        _finish_record_terminal(record)
        tombstone = _TerminalTombstoneV2(
            handle,
            record.cancellation,
            record.cancellation.cancellation_id,
            record.cancellation.canonical_bytes,
            record.owner_pid,
            record.owner_thread,
            record.owner_thread_id,
        )
        _TERMINAL_CANCELLATIONS[id(handle)] = tombstone
        _CANCELLATION_TOMBSTONES[id(record.cancellation)] = tombstone
        return record.cancellation
    except BaseException as error:
        if record.state != "CLOSED_CANCELLED_UNCONSUMED":
            record.state = "CANCEL_CLEANUP_PENDING"
            _LIVE_HANDOFFS.pop(id(handle), None)
            _QUARANTINED_HANDOFFS[id(handle)] = record
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 cancellation retained retryable cleanup",
                cleanup_handle=handle,
            ) from error
        raise
    finally:
        try:
            _restore_signal_mask(original_mask)
        except BaseException as restore_error:
            if record.state != "CLOSED_CANCELLED_UNCONSUMED":
                raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                    "guardian V2 cancellation signal restore retained cleanup",
                    cleanup_handle=handle,
                    restoration_error=restore_error,
                ) from restore_error
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 cancellation signal restoration failed after cleanup",
                restoration_error=restore_error,
            ) from restore_error


def _verify_b2a_cleanup_document(
    document: Mapping[str, Any], *, expected_successor_id: str
) -> None:
    if type(document) is not dict:
        _fail("guardian V2 B2-A cleanup closure is not exact")
    payload = dict(document)
    supplied = payload.pop("h1_route_wide_runtime_lease_closure_id", None)
    expected = domains_v15.extension_content_id_v15(
        domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN,
        payload,
    )
    if (
        type(supplied) is not str
        or supplied != expected
        or document.get("schema")
        != "acfqp.k7_h1_route_wide_runtime_lease_closure.v1"
        or document.get("h1_e5a_runtime_lease_successor_id") != expected_successor_id
        or type(document.get("source_e5a_cleanup_closure_id")) is not str
        or document.get("all_one_shot_grants_closed_or_never_issued") is not True
        or document.get("identity_bound_children_removed") is not True
        or document.get("identity_bound_outer_removed") is not True
        or document.get("all_cgroups_empty_before_removal") is not True
        or document.get("construction_only_cleanup_without_route_birth") is not True
        or document.get("route_peak_read_performed") is not False
        or document.get("actual_peak_issued") is not False
        or document.get("readiness") != "CLOSED_WITHOUT_PROCESS_BIRTH_OR_PEAK_READ"
    ):
        _fail("guardian V2 B2-A cleanup semantics or content ID changed")


def _verify_cancellation_document(
    document: Mapping[str, Any],
    *,
    expected_canonical_bytes: bytes,
    expected_cancellation_id: str,
) -> None:
    supplied = _verify_content_document(
        document,
        domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CANCELLATION_V1_DOMAIN,
        id_field="guardian_runtime_v2_cancellation_id",
        label="guardian V2 cancellation",
    )
    if (
        supplied != expected_cancellation_id
        or ids_v1.canonical_json_bytes(document) != expected_canonical_bytes
        or document.get("schema") != "acfqp.k7_h1_guardian_runtime_v2_cancellation.v1"
        or document.get("terminal_class") != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or document.get("terminal_code") != "UNCONSUMED_HANDOFF_CANCELLED"
        or document.get("readiness") != "CLOSED_CANCELLED_UNCONSUMED_NO_BIRTH"
    ):
        _fail("guardian V2 cancellation exact terminal identity changed")
    artifacts = document.get("embedded_artifacts")
    if type(artifacts) is not dict:
        _fail("guardian V2 cancellation artifact graph changed")
    required = {
        "source_closure",
        "genesis",
        "birth_intent",
        "birth_permit",
        "public_handoff",
        "unconsumed_revoke",
    }
    allowed = required | {"takeover_preparation"}
    if not required.issubset(artifacts) or not set(artifacts).issubset(allowed):
        _fail("guardian V2 cancellation embedded artifact inventory changed")
    domains = {
        "source_closure": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_SOURCE_CLOSURE_V1_DOMAIN,
            "guardian_runtime_v2_source_closure_id",
        ),
        "genesis": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_GENESIS_V1_DOMAIN,
            "guardian_runtime_v2_genesis_id",
        ),
        "birth_intent": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_BIRTH_INTENT_V1_DOMAIN,
            "guardian_runtime_v2_birth_intent_id",
        ),
        "birth_permit": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_BIRTH_PERMIT_V1_DOMAIN,
            "guardian_runtime_v2_birth_permit_id",
        ),
        "public_handoff": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_PUBLIC_HANDOFF_V1_DOMAIN,
            "guardian_runtime_v2_public_handoff_id",
        ),
        "unconsumed_revoke": (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_UNCONSUMED_REVOKE_V1_DOMAIN,
            "guardian_runtime_v2_unconsumed_revoke_id",
        ),
    }
    if "takeover_preparation" in artifacts:
        domains["takeover_preparation"] = (
            domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_TAKEOVER_PREPARATION_V1_DOMAIN,
            "guardian_runtime_v2_takeover_preparation_id",
        )
    ids = {
        name: _verify_content_document(
            artifacts[name], domain=domain, id_field=id_field, label=name
        )
        for name, (domain, id_field) in domains.items()
    }
    handoff = artifacts["public_handoff"]
    revoke = artifacts["unconsumed_revoke"]
    cleanup = document.get("b2a_runtime_cleanup_closure")
    _verify_b2a_cleanup_document(
        cleanup,
        expected_successor_id=document.get("h1_e5a_runtime_lease_successor_id"),
    )
    if "takeover_preparation" in artifacts:
        takeover = artifacts["takeover_preparation"]
        adapter_document = takeover.get("consumer_adapter")
        adapter_id = _verify_content_document(
            adapter_document,
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
            id_field="guardian_runtime_v2_consumer_adapter_id",
            label="guardian V2 embedded consumer adapter",
        )
        try:
            adapter_source = bytes.fromhex(
                adapter_document.get("consumer_source_bytes_hex")
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1GuardianRuntimeGenesisV2Error(
                "guardian V2 embedded consumer source is malformed"
            ) from error
        if (
            takeover.get("guardian_runtime_v2_consumer_adapter_id") != adapter_id
            or adapter_document.get("consumer_source_sha256")
            != hashlib.sha256(adapter_source).hexdigest()
            or adapter_document.get("consumer_source_byte_count")
            != len(adapter_source)
            or adapter_document.get("consumer_invoked") is not False
        ):
            _fail("guardian V2 embedded consumer adapter graph changed")
    if (
        handoff.get("guardian_runtime_v2_birth_permit_id") != ids["birth_permit"]
        or revoke.get("guardian_runtime_v2_public_handoff_id") != ids["public_handoff"]
        or document.get("guardian_runtime_v2_public_handoff_id") != ids["public_handoff"]
        or document.get("guardian_runtime_v2_unconsumed_revoke_id")
        != ids["unconsumed_revoke"]
        or document.get("all_five_grants_closed") is not True
        or document.get("runtime_and_e5a_hierarchy_closed") is not True
        or document.get("process_birth_count") != 0
        or (
            "takeover_preparation" in ids
            and artifacts["takeover_preparation"].get(
                "guardian_runtime_v2_public_handoff_id"
            )
            != ids["public_handoff"]
        )
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("guardian V2 cancellation semantics or joins changed")


def verify_h1_guardian_runtime_cancellation_v2(
    cancellation: H1GuardianRuntimeCancellationV2,
) -> dict[str, Any]:
    _validate_live_code_closure()
    if type(cancellation) is not H1GuardianRuntimeCancellationV2:
        _fail("guardian V2 cancellation verifier requires its exact type")
    tombstone = _CANCELLATION_TOMBSTONES.get(id(cancellation))
    if (
        tombstone is None
        or tombstone.cancellation is not cancellation
        or cancellation._issuer is not _CANCELLATION_ISSUER  # noqa: SLF001
    ):
        _fail("guardian V2 cancellation is absent from trusted terminal ownership")
    document = cancellation.to_document()
    _verify_cancellation_document(
        document,
        expected_canonical_bytes=tombstone.canonical_bytes,
        expected_cancellation_id=tombstone.cancellation_id,
    )
    if cancellation.cancellation_id != tombstone.cancellation_id:
        _fail("guardian V2 cancellation property ID changed")
    return document


def _before_fork() -> None:
    _V2_LOCK.acquire()


def _after_fork_parent() -> None:
    _V2_LOCK.release()


def _after_fork_child() -> None:
    global _V2_LOCK
    for record in tuple(
        {**_LIVE_HANDOFFS, **_QUARANTINED_HANDOFFS}.values()
    ):
        if record.directory_fd >= 0:
            try:
                os.close(record.directory_fd)
            except OSError:
                pass
            record.directory_fd = -1
        record.state = "FORK_POISONED"
    _LIVE_HANDOFFS.clear()
    _QUARANTINED_HANDOFFS.clear()
    _RUNTIME_RESERVATIONS.clear()
    _STARTING_BY_THREAD.clear()
    _TERMINAL_CANCELLATIONS.clear()
    _CANCELLATION_TOMBSTONES.clear()
    _LIVE_CONSUMER_ADAPTERS.clear()
    _LIVE_TAKEOVERS.clear()
    _V2_LOCK = threading.RLock()


def _freeze_local_callable_closure() -> None:
    global _LOCAL_CALLABLES
    module_globals = globals()
    captured = {
        name: _callable_fact(function)
        for name, function in module_globals.items()
        if type(function) is FunctionType
        and function.__globals__ is module_globals
        and name != "_callable_fact"
    }
    captured["_callable_fact"] = _callable_fact(_callable_fact)
    _LOCAL_CALLABLES = MappingProxyType(captured)


_freeze_local_callable_closure()


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
                "preregister_h1_guardian_runtime_genesis_v2",
                "register_h1_guardian_runtime_consumer_adapter_v2",
                "start_and_handoff_h1_guardian_runtime_genesis_v2",
                "verify_h1_guardian_runtime_permit_handoff_v2",
                "prepare_h1_guardian_runtime_consumer_takeover_v2",
                "cancel_h1_guardian_runtime_prepared_takeover_v2",
                "cancel_h1_guardian_runtime_permit_handoff_v2",
                "recover_h1_guardian_runtime_genesis_v2_failure_v1",
                "verify_h1_guardian_runtime_cancellation_v2",
            }
        )
        and not name.startswith("_")
    )
)
