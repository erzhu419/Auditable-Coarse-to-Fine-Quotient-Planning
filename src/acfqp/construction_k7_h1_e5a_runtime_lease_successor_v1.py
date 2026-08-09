"""Exact E5A lease-to-runtime ownership successor, without process birth.

This module is the bounded B2-A prerequisite for actual-observed E3 V2.  It
consumes one exact live E5A lease under E5A's own ownership lock, retains its
canonical descriptors, and can issue one close-on-exec O_PATH leaf candidate
per registered route slot.  A candidate is deliberately nonlaunchable: this
module has no source closure, guardian session, birth permit, clone, process
placement, observation, reap, cgroup.kill pin, or post-run peak read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import hashlib
import os
from pathlib import Path
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-A"
PROFILE_KEY = "construction_k7_h1_e5a_runtime_lease_successor_v1"
READINESS = "RUNTIME_LEASE_SUCCESSOR_ONLY"

PREPARED_E5A_SUCCESSOR_PRESENT = True
NONLAUNCHABLE_ONE_SHOT_LEAF_CANDIDATES_PRESENT = True
COMPANION_ADAPTER_IN_FUTURE_SOURCE_CLOSURE_REQUIRED = True
E5A_RUNTIME_LEASE_SUCCESSOR_PRESENT = False
PURPOSE_BUILT_ONE_SHOT_LEAF_GRANTS_PRESENT = False
EXECUTION_SOURCE_CLOSURE_PRESENT = False
GUARDIAN_SESSION_PRESENT = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
GUARDIAN_GATED_FIVE_ACTUAL_BIRTHS_PRESENT = False
ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT = False
PEAK_READ_PRESENT = False
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

_EXPECTED_E5A_SOURCE_SHA256 = (
    "70a32237ba72bf33aa924b65e8b45ee285090dd800ed049e66636e882d969287"
)
_EXPECTED_E5A_SOURCE_PATH = Path(e5a_v1.__file__).resolve(strict=True)
_EXPECTED_E5A_LEASE_SLOTS = (
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
_EXPECTED_CANONICAL_SLOTS = (
    "role:CONTROL",
    "role:WORKER",
    "role:BUSINESS",
    "memory_peak_witness",
    "memory_peak",
    "outer",
    "parent",
)
_EXPECTED_ALL_SLOTS = (
    *_EXPECTED_CANONICAL_SLOTS,
    *(f"retry-witness:{slot}" for slot in _EXPECTED_CANONICAL_SLOTS),
)
_EXPECTED_ROLE_ORDER = ("CONTROL", "WORKER", "BUSINESS")
_EXPECTED_RECORD_FIELDS = ("owner", "slot", "identity")

_BRIDGE_CALLABLE_NAMES = (
    "_verify_live_hierarchy",
    "verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1",
    "_open_owned_path_fd",
    "_block_fd_publication_signals",
    "_restore_fd_publication_signals",
    "_close_owned_fd_slot",
    "_owned_fd_slots_remaining",
    "_registered_fd_still_exact_unlocked",
    "_registry_fd_identity",
    "_fd_identity",
    "_same_open_file_description",
    "_same_open_file_description_for_close",
    "_verify_peak_retention_before_outer_removal",
    "_require_empty_cgroup",
    "_child_directories",
    "_assert_named_identity",
    "_name_missing",
    "_fstatfs_magic",
    "close_h1_route_wide_working_set_cgroup_lease_postrun_v1",
    "close_h1_route_wide_working_set_cgroup_lease_failed_birth_v1",
    "verify_h1_route_wide_postrun_cleanup_evidence_v1",
    "verify_h1_route_wide_failed_birth_cleanup_evidence_v1",
)
_BRIDGE_CALLABLES = MappingProxyType(
    {name: getattr(e5a_v1, name) for name in _BRIDGE_CALLABLE_NAMES}
)
_BRIDGE_GLOBAL_NAMES = (
    "_FD_OWNERSHIP_LOCK",
    "_OWNED_FDS",
    "_LIVE_LEASES",
    "_QUARANTINED_LEASES",
    "_OwnedFDRecordV1",
    "H1RouteWideWorkingSetCgroupLeaseV1",
    "H1RouteWidePostrunCleanupEvidenceV1",
    "H1RouteWideFailedBirthCleanupEvidenceV1",
    "_PROFILE",
    "_TOPOLOGY_PLAN",
    "_OS_CLOSE",
    "_FCNTL_FCNTL",
    "_PTHREAD_SIGMASK",
)
_BRIDGE_GLOBALS = MappingProxyType(
    {name: getattr(e5a_v1, name) for name in _BRIDGE_GLOBAL_NAMES}
)

SLOT_ORDER = (
    "SUPERVISOR",
    "PIDFD_PROBE",
    "BROKER",
    "WORKER",
    "BUSINESS",
)
SLOT_TO_LEAF = MappingProxyType(
    {
        "SUPERVISOR": "CONTROL",
        "PIDFD_PROBE": "CONTROL",
        "BROKER": "CONTROL",
        "WORKER": "WORKER",
        "BUSINESS": "BUSINESS",
    }
)

_RUNTIME_ISSUER = object()
_GRANT_ISSUER = object()
_CLOSURE_ISSUER = object()
_ADAPTER_LOCK = threading.RLock()
_LIVE_RUNTIME_LEASES: dict[int, "H1E5ARuntimeLeaseSuccessorV1"] = {}
_QUARANTINED_RUNTIME_LEASES: dict[int, "H1E5ARuntimeLeaseSuccessorV1"] = {}
_LIVE_GRANTS: dict[int, "H1E5ANonlaunchableLeafCandidateV1"] = {}
_TEST_ONLY_HANDOFF_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_CLOSURE_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_TRANSFER_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_TRANSFER_COMMIT_HOOK: Any = None
_TEST_ONLY_CANDIDATE_RESERVATION_HOOK: Any = None


class ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error(ValueError):
    """The exact E5A bridge, runtime lease, or one-shot grant was crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error(message)


def _locked_claims() -> dict[str, Any]:
    return {
        "execution_source_closure_present": False,
        "guardian_session_present": False,
        "e5a_runtime_lease_successor_present": False,
        "launch_authorizing_leaf_grants_present": False,
        "actual_process_birth_present": False,
        "guardian_gated_five_actual_births_present": False,
        "route_wide_actual_peak_authority_present": False,
        "peak_read_present": False,
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


def _validate_e5a_bridge() -> None:
    """Fail closed unless the reviewed E5A implementation is still exact."""

    try:
        live_path = Path(e5a_v1.__file__).resolve(strict=True)
        source_sha = hashlib.sha256(live_path.read_bytes()).hexdigest()
    except (OSError, TypeError) as error:
        raise ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error(
            "B2-A could not re-read the frozen E5A implementation"
        ) from error
    if live_path != _EXPECTED_E5A_SOURCE_PATH or source_sha != _EXPECTED_E5A_SOURCE_SHA256:
        _fail("B2-A frozen E5A source identity changed")
    for name, expected in _BRIDGE_CALLABLES.items():
        live = getattr(e5a_v1, name, None)
        if live is not expected or getattr(live, "__globals__", None) is not e5a_v1.__dict__:
            _fail(f"B2-A frozen E5A callable identity changed: {name}")
    for name, expected in _BRIDGE_GLOBALS.items():
        if getattr(e5a_v1, name, None) is not expected:
            _fail(f"B2-A frozen E5A global identity changed: {name}")
    if (
        e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1.__slots__
        != _EXPECTED_E5A_LEASE_SLOTS
        or tuple(e5a_v1._CANONICAL_FD_SLOTS) != _EXPECTED_CANONICAL_SLOTS
        or tuple(e5a_v1._ALL_OWNED_FD_SLOTS) != _EXPECTED_ALL_SLOTS
        or tuple(e5a_v1.ROLE_ORDER) != _EXPECTED_ROLE_ORDER
        or tuple(e5a_v1.CONTROL_NAMES) != _EXPECTED_ROLE_ORDER
        or tuple(e5a_v1._OwnedFDRecordV1.__dataclass_fields__)
        != _EXPECTED_RECORD_FIELDS
    ):
        _fail("B2-A frozen E5A owner layout changed")
    if (
        e5a_v1.ROUTE_WIDE_PRELAUNCH_ALLOWED_CAP_PRESENT is not True
        or e5a_v1.RUNTIME_PROCESS_PLACEMENT_PRESENT is not False
        or e5a_v1.ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT is not False
        or e5a_v1.OFFICIAL_EXECUTION_ALLOWED is not False
    ):
        _fail("B2-A frozen E5A claim boundary changed")


def frozen_e5a_runtime_bridge_manifest_v1() -> dict[str, Any]:
    _validate_e5a_bridge()
    return {
        "schema": "acfqp.k7_h1_e5a_runtime_bridge_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "expected_e5a_source_sha256": _EXPECTED_E5A_SOURCE_SHA256,
        "exact_callable_names": list(_BRIDGE_CALLABLE_NAMES),
        "exact_global_names": list(_BRIDGE_GLOBAL_NAMES),
        "exact_lease_slots": list(_EXPECTED_E5A_LEASE_SLOTS),
        "exact_canonical_fd_slots": list(_EXPECTED_CANONICAL_SLOTS),
        "bridge_checks_live_object_identity": True,
        "bridge_runs_under_e5a_fd_ownership_lock": True,
        "companion_adapter_must_be_in_future_execution_source_closure": True,
        "public_api_forgery_rejected": True,
        "hostile_python_private_mutation_excluded_from_threat_boundary": True,
    }


def _runtime_successor_payload(
    *,
    hierarchy: Mapping[str, Any],
    envelope: Mapping[str, Any],
    owner_pid: int,
    owner_thread_id: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_e5a_runtime_lease_successor.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "h1_route_wide_cgroup_hierarchy_id": hierarchy[
            "h1_route_wide_cgroup_hierarchy_id"
        ],
        "h1_route_wide_prelaunch_allowed_cap_envelope_id": envelope[
            "h1_route_wide_prelaunch_allowed_cap_envelope_id"
        ],
        "logical_occurrence_id": hierarchy["logical_occurrence_id"],
        "route_attempt_id": hierarchy["route_attempt_id"],
        "decision_point_id": hierarchy["decision_point_id"],
        "BuildEpoch_id": hierarchy["BuildEpoch_id"],
        "owner_pid": owner_pid,
        "owner_thread_id": owner_thread_id,
        "source_e5a_module_sha256": _EXPECTED_E5A_SOURCE_SHA256,
        "source_e5a_exact_live_lease_consumed": True,
        "source_e5a_state_after_transfer": "RUNTIME_TRANSFERRED",
        "successor_state_at_issuance": "PREPARED_SUCCESSOR",
        "canonical_fd_ownership_transferred_atomically": True,
        "one_shot_slot_to_leaf": dict(SLOT_TO_LEAF),
        "one_shot_grants_issued_at_genesis": [],
        "candidate_contains_only_one_cloexec_opath_leaf_fd": True,
        "grant_child_atfork_raw_close_registered": True,
        "candidate_authorizes_clone_or_process_placement": False,
        "source_closure_and_guardian_session_required_before_runtime": True,
        "clone_or_process_placement_performed": False,
        "route_peak_read_performed": False,
        **_locked_claims(),
    }


def _with_successor_id(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["h1_e5a_runtime_lease_successor_id"] = (
        domains_v15.extension_content_id_v15(
            domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_SUCCESSOR_V1_DOMAIN,
            payload,
        )
    )
    return result


@dataclass(frozen=True, slots=True)
class H1E5ARuntimeLeaseClosureV1:
    canonical_bytes: bytes = field(repr=False)
    closure_id: str = field(init=False)
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._issuer is not _CLOSURE_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("B2-A runtime cleanup closure is caller-minted")
        document = loads_canonical_json(self.canonical_bytes)
        supplied = document.pop("h1_route_wide_runtime_lease_closure_id", None)
        if type(supplied) is not str or domains_v15.extension_content_id_v15(
            domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN,
            document,
        ) != supplied:
            _fail("B2-A runtime cleanup closure content ID changed")
        object.__setattr__(self, "closure_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


class H1E5ARuntimeLeaseSuccessorV1:
    """Uncopyable PID/thread-bound owner of one consumed E5A hierarchy."""

    __slots__ = (
        "_owner_pid",
        "_owner_thread",
        "_owner_thread_id",
        "_fd_slots",
        "_outer_name",
        "_hierarchy_document",
        "_hierarchy_id",
        "_envelope",
        "_lock",
        "_state",
        "_grant_states",
        "_removed_roles",
        "_outer_removed",
        "_cleanup_attempts",
        "_closure",
        "_successor_document",
        "_source_lease",
        "_source_handed_back",
        "_handoff_phase",
        "_postrun_cleanup_evidence",
        "_failed_birth_cleanup_evidence",
    )

    def __init__(
        self,
        issuer: object,
        *,
        source_lease: e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1,
        hierarchy: Mapping[str, Any],
        envelope: Mapping[str, Any],
        fd_slots: Mapping[str, int],
        successor_document: Mapping[str, Any],
    ) -> None:
        if issuer is not _RUNTIME_ISSUER:
            _fail("B2-A runtime lease is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._fd_slots = dict(fd_slots)
        self._outer_name = source_lease._outer_name
        self._hierarchy_document = dict(hierarchy)
        self._hierarchy_id = hierarchy["h1_route_wide_cgroup_hierarchy_id"]
        self._envelope = source_lease._envelope
        self._lock = threading.RLock()
        self._state = "PREPARED_SUCCESSOR"
        self._grant_states = {slot: "AVAILABLE" for slot in SLOT_ORDER}
        self._removed_roles: set[str] = set()
        self._outer_removed = False
        self._cleanup_attempts = 0
        self._closure: H1E5ARuntimeLeaseClosureV1 | None = None
        self._successor_document = dict(successor_document)
        self._source_lease = source_lease
        self._source_handed_back = False
        self._handoff_phase = "NOT_STARTED"
        self._postrun_cleanup_evidence: (
            e5a_v1.H1RouteWidePostrunCleanupEvidenceV1 | None
        ) = None
        self._failed_birth_cleanup_evidence: (
            e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1 | None
        ) = None

    @property
    def _parent_fd(self) -> int:
        return self._fd_slots[e5a_v1._PARENT_FD_SLOT]

    @property
    def _outer_fd(self) -> int:
        return self._fd_slots[e5a_v1._OUTER_FD_SLOT]

    @property
    def _memory_peak_fd(self) -> int:
        return self._fd_slots[e5a_v1._PEAK_FD_SLOT]

    @property
    def _memory_peak_witness_fd(self) -> int:
        return self._fd_slots[e5a_v1._PEAK_WITNESS_FD_SLOT]

    @property
    def _role_fds(self) -> dict[str, int]:
        return {
            role: self._fd_slots[e5a_v1._role_fd_slot(role)]
            for role in e5a_v1.ROLE_ORDER
        }

    @property
    def state(self) -> str:
        return self._state

    @property
    def successor_id(self) -> str:
        return self._successor_document["h1_e5a_runtime_lease_successor_id"]

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(canonical_json_bytes(self._successor_document))

    def grant_states(self) -> dict[str, str]:
        return dict(self._grant_states)

    def _poison_after_fork_child(self) -> None:
        for slot in e5a_v1._ALL_OWNED_FD_SLOTS:
            self._fd_slots[slot] = -1
        self._state = "FORK_POISONED"

    def __copy__(self) -> NoReturn:
        _fail("B2-A runtime lease cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-A runtime lease cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-A runtime lease cannot be copied or pickled")


class H1E5ANonlaunchableLeafCandidateV1:
    """One ephemeral candidate FD; it carries no clone authorization."""

    __slots__ = (
        "_owner_pid",
        "_owner_thread",
        "_owner_thread_id",
        "_fd_slots",
        "_state",
        "_slot",
        "_leaf",
        "_runtime_id",
    )

    def __init__(
        self,
        issuer: object,
        *,
        runtime: H1E5ARuntimeLeaseSuccessorV1,
        slot: str,
        leaf: str,
    ) -> None:
        if issuer is not _GRANT_ISSUER:
            _fail("B2-A leaf grant is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._fd_slots = {name: -1 for name in e5a_v1._ALL_OWNED_FD_SLOTS}
        self._state = "PREPARING"
        self._slot = slot
        self._leaf = leaf
        self._runtime_id = id(runtime)

    @property
    def slot(self) -> str:
        return self._slot

    @property
    def leaf(self) -> str:
        return self._leaf

    @property
    def state(self) -> str:
        return self._state

    @property
    def launch_authority(self) -> bool:
        return False

    def _poison_after_fork_child(self) -> None:
        for slot in e5a_v1._ALL_OWNED_FD_SLOTS:
            self._fd_slots[slot] = -1
        self._state = "FORK_POISONED"

    def __copy__(self) -> NoReturn:
        _fail("B2-A leaf grant cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-A leaf grant cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-A leaf grant cannot be copied or pickled")


def _same_owner_context(owner: Any) -> bool:
    try:
        return (
            type(owner._owner_pid) is int
            and owner._owner_pid == os.getpid()
            and type(owner._owner_thread_id) is int
            and owner._owner_thread_id == threading.get_ident()
            and owner._owner_thread is threading.current_thread()
        )
    except AttributeError:
        return False


def _require_runtime(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    *,
    cleanup: bool = False,
) -> H1E5ARuntimeLeaseSuccessorV1:
    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A operation requires one exact runtime lease")
    if not _same_owner_context(runtime):
        _fail("B2-A runtime lease crossed its owner PID or thread")
    allowed = (
        {"PREPARED_SUCCESSOR", "CLEANUP_PENDING"}
        if cleanup
        else {"PREPARED_SUCCESSOR"}
    )
    if runtime._state not in allowed:
        _fail("B2-A runtime lease is not in an allowed state")
    registry = (
        _LIVE_RUNTIME_LEASES
        if runtime._state == "PREPARED_SUCCESSOR"
        else _QUARANTINED_RUNTIME_LEASES
    )
    if registry.get(id(runtime)) is not runtime:
        _fail("B2-A runtime lease is not issuer-live")
    return runtime


def _require_postrun_runtime(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> H1E5ARuntimeLeaseSuccessorV1:
    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A postrun cleanup requires one exact runtime lease")
    if not _same_owner_context(runtime):
        _fail("B2-A postrun runtime crossed its owner PID or thread")
    if runtime._state == "PEAK_READ":
        registry = _LIVE_RUNTIME_LEASES
    elif runtime._state == "CLEANUP_PENDING":
        registry = _QUARANTINED_RUNTIME_LEASES
    else:
        _fail("B2-A postrun runtime is not at PEAK_READ or cleanup-pending")
    if registry.get(id(runtime)) is not runtime:
        _fail("B2-A postrun runtime is not issuer-live")
    return runtime


def _bind_postrun_evidence_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    evidence: e5a_v1.H1RouteWidePostrunCleanupEvidenceV1,
) -> None:
    if type(evidence) is not e5a_v1.H1RouteWidePostrunCleanupEvidenceV1:
        _fail("B2-A postrun cleanup requires exact typed evidence")
    document = evidence.to_document()
    if (
        document.get("runtime_successor_id") != runtime.successor_id
        or document.get("h1_route_wide_cgroup_hierarchy_id")
        != runtime._hierarchy_id
    ):
        _fail("B2-A postrun evidence crossed its runtime")
    if runtime._failed_birth_cleanup_evidence is not None:
        _fail("B2-A postrun evidence crossed failed-birth evidence")
    retained = runtime._postrun_cleanup_evidence
    if retained is None:
        runtime._postrun_cleanup_evidence = evidence
    elif (
        type(retained) is not e5a_v1.H1RouteWidePostrunCleanupEvidenceV1
        or retained.canonical_bytes != evidence.canonical_bytes
    ):
        _fail("B2-A postrun cleanup evidence changed during retry")


def _require_failed_birth_runtime(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> H1E5ARuntimeLeaseSuccessorV1:
    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A failed-birth cleanup requires one exact runtime lease")
    if not _same_owner_context(runtime):
        _fail("B2-A failed-birth runtime crossed its owner PID or thread")
    if runtime._state == "RUNNING":
        registry = _LIVE_RUNTIME_LEASES
    elif runtime._state == "CLEANUP_PENDING":
        registry = _QUARANTINED_RUNTIME_LEASES
    else:
        _fail("B2-A failed-birth runtime is not cleanup-eligible")
    if registry.get(id(runtime)) is not runtime:
        _fail("B2-A failed-birth runtime is not issuer-live")
    return runtime


def _bind_failed_birth_evidence_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    evidence: e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1,
) -> None:
    if type(evidence) is not e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1:
        _fail("B2-A failed-birth cleanup requires exact typed evidence")
    document = evidence.to_document()
    if (
        document.get("runtime_successor_id") != runtime.successor_id
        or document.get("h1_route_wide_cgroup_hierarchy_id")
        != runtime._hierarchy_id
    ):
        _fail("B2-A failed-birth evidence crossed its runtime")
    if runtime._postrun_cleanup_evidence is not None:
        _fail("B2-A failed-birth evidence crossed postrun evidence")
    retained = runtime._failed_birth_cleanup_evidence
    if retained is None:
        runtime._failed_birth_cleanup_evidence = evidence
    elif (
        type(retained) is not e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1
        or retained.canonical_bytes != evidence.canonical_bytes
    ):
        _fail("B2-A failed-birth cleanup evidence changed during retry")


def _require_live_grant(
    grant: H1E5ANonlaunchableLeafCandidateV1,
) -> H1E5ANonlaunchableLeafCandidateV1:
    if type(grant) is not H1E5ANonlaunchableLeafCandidateV1:
        _fail("B2-A operation requires one exact nonlaunchable candidate")
    if not _same_owner_context(grant):
        _fail("B2-A leaf grant crossed its owner PID or thread")
    if grant._state not in {"ISSUED", "CLOSE_PENDING"}:
        _fail("B2-A leaf grant is not live")
    if _LIVE_GRANTS.get(id(grant)) is not grant:
        _fail("B2-A leaf grant is absent from its issuer registry")
    runtime = _LIVE_RUNTIME_LEASES.get(grant._runtime_id)
    if runtime is None:
        runtime = _QUARANTINED_RUNTIME_LEASES.get(grant._runtime_id)
    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A leaf grant lost its exact runtime owner")
    return grant


def _verify_runtime_fd_registry_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    for slot in e5a_v1._CANONICAL_FD_SLOTS:
        descriptor = runtime._fd_slots[slot]
        record = e5a_v1._OWNED_FDS.get(descriptor)
        if (
            type(descriptor) is not int
            or descriptor < 0
            or record is None
            or record.owner is not runtime
            or record.slot != slot
            or record.identity is None
            or not e5a_v1._registered_fd_still_exact_unlocked(descriptor, record)
        ):
            _fail("B2-A runtime canonical FD ownership changed")
    if any(
        runtime._fd_slots[e5a_v1._retry_witness_fd_slot(slot)] >= 0
        for slot in e5a_v1._CANONICAL_FD_SLOTS
    ):
        _fail("B2-A live runtime unexpectedly retains a close witness")


def _verify_source_lease_retired(runtime: H1E5ARuntimeLeaseSuccessorV1) -> None:
    source = runtime._source_lease
    if (
        type(source) is not e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1
        or source._state != "RUNTIME_TRANSFERRED"
        or id(source) in e5a_v1._LIVE_LEASES
        or id(source) in e5a_v1._QUARANTINED_LEASES
        or any(source._fd_slots[slot] != -1 for slot in e5a_v1._ALL_OWNED_FD_SLOTS)
    ):
        _fail("B2-A consumed E5A source lease became independently live")


def _consume_under_signal_shield_unlocked(
    lease: e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1,
) -> H1E5ARuntimeLeaseSuccessorV1:
    if (
        lease._state != "ACTIVE"
        or e5a_v1._LIVE_LEASES.get(id(lease)) is not lease
        or id(lease) in e5a_v1._QUARANTINED_LEASES
    ):
        _fail("B2-A source E5A lease is not exact ACTIVE issuer ownership")
    if any(
        runtime._source_lease is lease
        for runtime in (
            *_LIVE_RUNTIME_LEASES.values(),
            *_QUARANTINED_RUNTIME_LEASES.values(),
        )
    ):
        _fail("B2-A source E5A lease was already consumed")
    hierarchy = e5a_v1._verify_live_hierarchy(lease)
    envelope = e5a_v1.verify_h1_route_wide_working_set_prelaunch_allowed_cap_v1(
        lease
    )
    fd_slots = {
        slot: lease._fd_slots[slot] for slot in e5a_v1._ALL_OWNED_FD_SLOTS
    }
    transfer_records: list[tuple[str, int, Any]] = []
    for slot in e5a_v1._CANONICAL_FD_SLOTS:
        descriptor = fd_slots[slot]
        record = e5a_v1._OWNED_FDS.get(descriptor)
        if (
            descriptor < 0
            or record is None
            or record.owner is not lease
            or record.slot != slot
            or record.identity is None
            or not e5a_v1._registered_fd_still_exact_unlocked(
                descriptor, record
            )
        ):
            _fail("B2-A source E5A canonical FD ownership changed")
        transfer_records.append((slot, descriptor, record))
    if any(
        fd_slots[e5a_v1._retry_witness_fd_slot(slot)] >= 0
        for slot in e5a_v1._CANONICAL_FD_SLOTS
    ):
        _fail("B2-A source E5A lease retained a close witness")
    successor_document = _with_successor_id(
        _runtime_successor_payload(
            hierarchy=hierarchy,
            envelope=envelope,
            owner_pid=os.getpid(),
            owner_thread_id=threading.get_ident(),
        )
    )
    runtime = H1E5ARuntimeLeaseSuccessorV1(
        _RUNTIME_ISSUER,
        source_lease=lease,
        hierarchy=hierarchy,
        envelope=envelope,
        fd_slots=fd_slots,
        successor_document=successor_document,
    )
    replacements = [
        (
            descriptor,
            e5a_v1._OwnedFDRecordV1(
                owner=runtime,
                slot=slot,
                identity=record.identity,
            ),
        )
        for slot, descriptor, record in transfer_records
    ]

    def finish_transfer(*, inject_fault: bool) -> None:
        step = 0

        def boundary() -> None:
            nonlocal step
            step += 1
            if inject_fault and _TEST_ONLY_TRANSFER_FAULT_AFTER_STEP == step:
                raise RuntimeError(
                    f"injected B2-A transfer fault after step {step}"
                )

        _LIVE_RUNTIME_LEASES[id(runtime)] = runtime
        hook = _TEST_ONLY_TRANSFER_COMMIT_HOOK
        if inject_fault and hook is not None:
            hook(lease)
        boundary()
        for descriptor, replacement in replacements:
            e5a_v1._OWNED_FDS[descriptor] = replacement
            boundary()
        for slot in e5a_v1._ALL_OWNED_FD_SLOTS:
            lease._fd_slots[slot] = -1
        boundary()
        e5a_v1._LIVE_LEASES.pop(id(lease), None)
        boundary()
        lease._state = "RUNTIME_TRANSFERRED"
        boundary()

    try:
        finish_transfer(inject_fault=True)
    except BaseException:
        finish_transfer(inject_fault=False)
    return runtime


def consume_h1_e5a_runtime_lease_successor_v1(
    lease: e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1,
) -> H1E5ARuntimeLeaseSuccessorV1:
    """Consume ACTIVE E5A into a nonlaunchable PREPARED_SUCCESSOR."""

    _validate_e5a_bridge()
    if type(lease) is not e5a_v1.H1RouteWideWorkingSetCgroupLeaseV1:
        _fail("B2-A bridge requires one exact E5A lease")
    if lease._owner_pid != os.getpid():
        _fail("B2-A source E5A lease crossed its owner process")
    runtime: H1E5ARuntimeLeaseSuccessorV1 | None = None
    try:
        with _ADAPTER_LOCK:
            with lease._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    _validate_e5a_bridge()
                    original_mask = e5a_v1._block_fd_publication_signals()
                    try:
                        runtime = _consume_under_signal_shield_unlocked(lease)
                    finally:
                        e5a_v1._restore_fd_publication_signals(original_mask)
        assert runtime is not None
        verify_h1_e5a_runtime_lease_successor_v1(runtime)
        return runtime
    except BaseException:
        if runtime is not None and runtime._state == "PREPARED_SUCCESSOR":
            # A post-commit signal-handler exception or verification failure
            # cannot strand an unreachable live successor.
            close_h1_e5a_runtime_lease_successor_v1(runtime)
        raise


def verify_h1_e5a_runtime_lease_successor_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> dict[str, Any]:
    """Read-only pre-birth revalidation of hierarchy, cap, OFD and ownership."""

    runtime = _require_runtime(runtime)
    source = runtime._source_lease
    with _ADAPTER_LOCK:
        with source._lock:
            with runtime._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    _validate_e5a_bridge()
                    _require_runtime(runtime)
                    _verify_source_lease_retired(runtime)
                    _verify_runtime_fd_registry_unlocked(runtime)
                    hierarchy = e5a_v1._verify_live_hierarchy(runtime)
                    envelope = runtime._envelope.to_document()
                    expected_document = _with_successor_id(
                        _runtime_successor_payload(
                            hierarchy=hierarchy,
                            envelope=envelope,
                            owner_pid=runtime._owner_pid,
                            owner_thread_id=runtime._owner_thread_id,
                        )
                    )
                    if runtime._successor_document != expected_document:
                        _fail("B2-A runtime successor content changed")
                    return runtime.to_document()


def _issue_candidate_under_signal_shield_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    slot: str,
) -> H1E5ANonlaunchableLeafCandidateV1:
    if runtime._grant_states.get(slot) != "AVAILABLE":
        _fail("B2-A slot grant is not available exactly once")
    leaf = SLOT_TO_LEAF[slot]
    canonical_slot = e5a_v1._role_fd_slot(leaf)
    source_fd = runtime._fd_slots[canonical_slot]
    grant = H1E5ANonlaunchableLeafCandidateV1(
        _GRANT_ISSUER,
        runtime=runtime,
        slot=slot,
        leaf=leaf,
    )
    try:
        # Persist the owner and reserve the slot before the first open.  The
        # surrounding safe-signal shield makes these two writes indivisible
        # to Python signal handlers.
        _LIVE_GRANTS[id(grant)] = grant
        runtime._grant_states[slot] = "ISSUE_PENDING"
        hook = _TEST_ONLY_CANDIDATE_RESERVATION_HOOK
        if hook is not None:
            hook(runtime, slot)
        descriptor = e5a_v1._open_owned_path_fd(
            grant,
            canonical_slot,
            ".",
            os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=source_fd,
        )
        record = e5a_v1._OWNED_FDS.get(descriptor)
        source_record = e5a_v1._OWNED_FDS.get(source_fd)
        if (
            record is None
            or record.owner is not grant
            or record.slot != canonical_slot
            or record.identity is None
            or source_record is None
            or source_record.owner is not runtime
            or record.identity != source_record.identity
            or not (fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC)
            or any(
                grant._fd_slots[name] >= 0
                for name in e5a_v1._CANONICAL_FD_SLOTS
                if name != canonical_slot
            )
        ):
            _fail("B2-A leaf candidate crossed its exact support")
    except BaseException:
        if e5a_v1._owned_fd_slots_remaining(grant):
            grant._state = "CLOSE_PENDING"
            runtime._grant_states[slot] = "CLOSE_PENDING"
            try:
                _close_grant_unlocked(runtime, grant)
            except BaseException:
                pass
        else:
            grant._state = "ABORTED"
            runtime._grant_states[slot] = "ABORTED"
            _LIVE_GRANTS.pop(id(grant), None)
        raise
    grant._state = "ISSUED"
    runtime._grant_states[slot] = "ISSUED"
    return grant


def issue_h1_e5a_nonlaunchable_leaf_candidate_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    *,
    slot: str,
) -> H1E5ANonlaunchableLeafCandidateV1:
    """Issue one O_PATH leaf candidate that cannot authorize a launch."""

    if type(slot) is not str or slot not in SLOT_TO_LEAF:
        _fail("B2-A grant slot is not one registered exact slot")
    runtime = _require_runtime(runtime)
    verify_h1_e5a_runtime_lease_successor_v1(runtime)
    source = runtime._source_lease
    with _ADAPTER_LOCK:
        with source._lock:
            with runtime._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    _validate_e5a_bridge()
                    _require_runtime(runtime)
                    original_mask = e5a_v1._block_fd_publication_signals()
                    try:
                        return _issue_candidate_under_signal_shield_unlocked(
                            runtime, slot
                        )
                    finally:
                        e5a_v1._restore_fd_publication_signals(original_mask)


def _close_grant_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    grant: H1E5ANonlaunchableLeafCandidateV1,
) -> None:
    if grant._runtime_id != id(runtime) or _LIVE_GRANTS.get(id(grant)) is not grant:
        _fail("B2-A leaf grant crossed its runtime owner")
    canonical_slot = e5a_v1._role_fd_slot(grant._leaf)
    error = e5a_v1._close_owned_fd_slot(grant, canonical_slot)
    outstanding = e5a_v1._owned_fd_slots_remaining(grant)
    if error is not None or outstanding:
        grant._state = "CLOSE_PENDING"
        runtime._grant_states[grant._slot] = "CLOSE_PENDING"
        raise RuntimeError("B2-A leaf grant retained a close-only quarantine FD") from error
    if any(record.owner is grant for record in e5a_v1._OWNED_FDS.values()):
        raise RuntimeError("B2-A closed leaf grant retained an ownership record")
    grant._state = "CLOSED"
    runtime._grant_states[grant._slot] = "CONSUMED"
    _LIVE_GRANTS.pop(id(grant), None)


def close_h1_e5a_nonlaunchable_leaf_candidate_v1(
    grant: H1E5ANonlaunchableLeafCandidateV1,
) -> None:
    """Close one grant; non-EBADF ambiguity remains retryable quarantine."""

    grant = _require_live_grant(grant)
    runtime = _LIVE_RUNTIME_LEASES.get(grant._runtime_id)
    if runtime is None:
        runtime = _QUARANTINED_RUNTIME_LEASES.get(grant._runtime_id)
    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A leaf grant lost its runtime registry")
    if not _same_owner_context(runtime):
        _fail("B2-A leaf grant runtime crossed its owner context")
    with _ADAPTER_LOCK:
        with runtime._source_lease._lock:
            with runtime._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    _validate_e5a_bridge()
                    _require_live_grant(grant)
                    _close_grant_unlocked(runtime, grant)


def _close_all_runtime_grants_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    for grant in tuple(_LIVE_GRANTS.values()):
        if grant._runtime_id == id(runtime):
            _close_grant_unlocked(runtime, grant)


def _runtime_cleanup_payload(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    source_closure: Mapping[str, Any],
    *,
    postrun_evidence: e5a_v1.H1RouteWidePostrunCleanupEvidenceV1 | None,
    failed_birth_evidence: (
        e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1 | None
    ),
) -> dict[str, Any]:
    hierarchy = runtime._hierarchy_document
    payload = {
        "schema": "acfqp.k7_h1_route_wide_runtime_lease_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e5a_runtime_lease_successor_id": runtime.successor_id,
        "h1_route_wide_cgroup_hierarchy_id": runtime._hierarchy_id,
        "source_e5a_cleanup_closure_id": source_closure[
            "h1_route_wide_cgroup_cleanup_closure_id"
        ],
        "logical_occurrence_id": hierarchy["logical_occurrence_id"],
        "route_attempt_id": hierarchy["route_attempt_id"],
        "decision_point_id": hierarchy["decision_point_id"],
        "BuildEpoch_id": hierarchy["BuildEpoch_id"],
        "cleanup_attempt_count": runtime._cleanup_attempts,
        "all_one_shot_grants_closed_or_never_issued": True,
        "identity_bound_children_removed": True,
        "identity_bound_outer_removed": True,
        "all_cgroups_empty_before_removal": True,
        "memory_peak_ofd_retained_until_outer_removal": True,
        "source_e5a_lease_restored_active": False,
        "source_e5a_cleanup_only_handoff": True,
        "construction_only_cleanup_without_route_birth": True,
        "route_peak_read_performed": False,
        "actual_peak_issued": False,
        "readiness": "CLOSED_WITHOUT_PROCESS_BIRTH_OR_PEAK_READ",
        **_locked_claims(),
    }
    if postrun_evidence is not None:
        evidence = postrun_evidence.to_document()
        payload.update(
            {
                "actual_process_birth_observation_id": evidence[
                    "actual_process_birth_observation_id"
                ],
                "actual_process_creator_reap_attestation_id": evidence[
                    "actual_process_creator_reap_attestation_id"
                ],
                "bounded_supervisor_birth_peak_observation_id": evidence[
                    "bounded_supervisor_birth_peak_observation_id"
                ],
                "construction_only_cleanup_without_route_birth": False,
                "bounded_single_supervisor_birth_present": True,
                "clone_or_process_placement_performed": True,
                "actual_process_birth_present": True,
                "process_death_or_reap_present": True,
                "peak_read_present": True,
                "route_peak_read_performed": True,
                "actual_peak_issued": True,
                "bounded_actual_peak_bytes": evidence["memory_peak_bytes"],
                "readiness": "POSTRUN_CLOSED_AFTER_BOUNDED_SUPERVISOR_PEAK",
            }
        )
    elif failed_birth_evidence is not None:
        evidence = failed_birth_evidence.to_document()
        payload.update(
            {
                "actual_process_birth_permit_consumption_id": evidence[
                    "actual_process_birth_permit_consumption_id"
                ],
                "actual_observed_e3_v2_protocol_failure_closure_id": evidence[
                    "actual_observed_e3_v2_protocol_failure_closure_id"
                ],
                "primary_failure_stage": evidence["primary_failure_stage"],
                "child_pid": evidence["child_pid"],
                "construction_only_cleanup_without_route_birth": False,
                "bounded_single_supervisor_birth_present": True,
                "clone_or_process_placement_performed": True,
                "actual_process_birth_present": True,
                "cgroup_kill_write_performed": True,
                "process_death_or_reap_present": True,
                "peak_read_started": False,
                "peak_read_present": False,
                "route_peak_read_performed": False,
                "actual_peak_issued": False,
                "memory_peak_read_count": 0,
                "memory_peak_witness_read_count": 0,
                "readiness": (
                    "POSTRUN_CLOSED_AFTER_BIRTH_FAILURE_KILL_REAP_NO_PEAK"
                ),
            }
        )
    return payload


def _handback_runtime_to_e5a_cleanup_unlocked(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    """Move exact ownership back only as E5A CLEANUP_PENDING authority."""

    source = runtime._source_lease
    if runtime._source_handed_back:
        if (
            source._state not in {"CLEANUP_PENDING", "CLOSED"}
            or id(source) in e5a_v1._LIVE_LEASES
            or runtime._handoff_phase != "COMPLETE"
        ):
            _fail("B2-A cleanup-only E5A handback changed state")
        return
    _verify_source_lease_retired(runtime)
    _verify_runtime_fd_registry_unlocked(runtime)
    replacements: list[tuple[str, int, Any]] = []
    for slot in e5a_v1._CANONICAL_FD_SLOTS:
        descriptor = runtime._fd_slots[slot]
        record = e5a_v1._OWNED_FDS[descriptor]
        replacements.append(
            (
                slot,
                descriptor,
                e5a_v1._OwnedFDRecordV1(
                    owner=source,
                    slot=slot,
                    identity=record.identity,
                ),
            )
        )
    def apply_finish_forward(*, inject_fault: bool) -> None:
        step = 0

        def boundary() -> None:
            nonlocal step
            step += 1
            if (
                inject_fault
                and _TEST_ONLY_HANDOFF_FAULT_AFTER_STEP == step
            ):
                raise RuntimeError(
                    f"injected B2-A handoff fault after step {step}"
                )

        runtime._handoff_phase = "COMMITTING"
        boundary()
        for slot, descriptor, replacement in replacements:
            source._fd_slots[slot] = descriptor
            e5a_v1._OWNED_FDS[descriptor] = replacement
            runtime._fd_slots[slot] = -1
            boundary()
        for slot in e5a_v1._RETRY_WITNESS_FD_SLOTS:
            source._fd_slots[slot] = -1
            runtime._fd_slots[slot] = -1
        boundary()
        source._state = "CLEANUP_PENDING"
        e5a_v1._LIVE_LEASES.pop(id(source), None)
        boundary()
        runtime._source_handed_back = True
        runtime._state = "CLEANUP_PENDING"
        _LIVE_RUNTIME_LEASES.pop(id(runtime), None)
        boundary()
        runtime._handoff_phase = "COMPLETE"

    original_mask = e5a_v1._block_fd_publication_signals()
    try:
        runtime_reserved = False
        source_reserved = False
        try:
            _QUARANTINED_RUNTIME_LEASES[id(runtime)] = runtime
            runtime_reserved = True
            e5a_v1._QUARANTINED_LEASES[id(source)] = source
            source_reserved = True
        except BaseException:
            if source_reserved:
                e5a_v1._QUARANTINED_LEASES.pop(id(source), None)
            if runtime_reserved:
                _QUARANTINED_RUNTIME_LEASES.pop(id(runtime), None)
            raise
        try:
            try:
                apply_finish_forward(inject_fault=True)
            except BaseException:
                # Reservations and replacement records were allocated before
                # commit.  Replay uses idempotent existing-key/slot writes and
                # always finishes toward cleanup, never ACTIVE.
                apply_finish_forward(inject_fault=False)
        except BaseException:
            # A second failure is outside the bounded injected-fault model;
            # retain both quarantine reservations for explicit recovery.
            raise
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)


def _close_h1_e5a_runtime_lease_successor_impl_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    *,
    postrun_evidence: e5a_v1.H1RouteWidePostrunCleanupEvidenceV1 | None,
    failed_birth_evidence: (
        e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1 | None
    ),
) -> H1E5ARuntimeLeaseClosureV1:
    """Shared runtime handback/closure implementation."""

    if type(runtime) is not H1E5ARuntimeLeaseSuccessorV1:
        _fail("B2-A cleanup requires one exact runtime lease")
    if postrun_evidence is not None and failed_birth_evidence is not None:
        _fail("B2-A cleanup evidence category is ambiguous")
    if runtime._state == "CLOSED" and runtime._closure is not None:
        if not _same_owner_context(runtime):
            _fail("B2-A closed runtime lease crossed its owner context")
        if postrun_evidence is not None and (
            runtime._closure.to_document().get(
                "bounded_supervisor_birth_peak_observation_id"
            )
            != postrun_evidence.to_document().get(
                "bounded_supervisor_birth_peak_observation_id"
            )
        ):
            _fail("B2-A closed postrun evidence changed")
        if failed_birth_evidence is not None and (
            runtime._closure.to_document().get(
                "actual_observed_e3_v2_protocol_failure_closure_id"
            )
            != failed_birth_evidence.to_document().get(
                "actual_observed_e3_v2_protocol_failure_closure_id"
            )
        ):
            _fail("B2-A closed failed-birth evidence changed")
        return runtime._closure
    if postrun_evidence is not None:
        runtime = _require_postrun_runtime(runtime)
    elif failed_birth_evidence is not None:
        runtime = _require_failed_birth_runtime(runtime)
    else:
        runtime = _require_runtime(runtime, cleanup=True)
    source = runtime._source_lease
    with _ADAPTER_LOCK:
        with source._lock:
            with runtime._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    _validate_e5a_bridge()
                    if postrun_evidence is None and failed_birth_evidence is None:
                        _require_runtime(runtime, cleanup=True)
                        if (
                            runtime._postrun_cleanup_evidence is not None
                            or runtime._failed_birth_cleanup_evidence is not None
                        ):
                            _fail("B2-A legacy cleanup crossed an evidenced runtime")
                    elif postrun_evidence is not None:
                        _require_postrun_runtime(runtime)
                        _bind_postrun_evidence_unlocked(runtime, postrun_evidence)
                    else:
                        assert failed_birth_evidence is not None
                        _require_failed_birth_runtime(runtime)
                        _bind_failed_birth_evidence_unlocked(
                            runtime, failed_birth_evidence
                        )
                    runtime._cleanup_attempts += 1
                    try:
                        _close_all_runtime_grants_unlocked(runtime)
                    except BaseException:
                        runtime._state = "CLEANUP_PENDING"
                        _LIVE_RUNTIME_LEASES.pop(id(runtime), None)
                        _QUARANTINED_RUNTIME_LEASES[id(runtime)] = runtime
                        raise
                    if not runtime._source_handed_back:
                        _verify_source_lease_retired(runtime)
                        _verify_runtime_fd_registry_unlocked(runtime)
                        if (
                            postrun_evidence is None
                            and failed_birth_evidence is None
                        ):
                            e5a_v1._verify_live_hierarchy(runtime)
                    _handback_runtime_to_e5a_cleanup_unlocked(runtime)

    # The reviewed V1 cleanup is the sole hierarchy-removal authority.  It is
    # invoked after the adapter releases its locks; the source is already
    # irreversibly CLEANUP_PENDING in V1's quarantine registry.
    if postrun_evidence is not None:
        source_closure = (
            e5a_v1.close_h1_route_wide_working_set_cgroup_lease_postrun_v1(
                source,
                evidence=postrun_evidence,
            )
        )
    elif failed_birth_evidence is not None:
        source_closure = (
            e5a_v1.close_h1_route_wide_working_set_cgroup_lease_failed_birth_v1(
                source,
                evidence=failed_birth_evidence,
            )
        )
    else:
        source_closure = e5a_v1.close_h1_route_wide_working_set_cgroup_lease_v1(
            source
        )
    source_document = source_closure.to_document()
    with _ADAPTER_LOCK:
        with source._lock:
            with runtime._lock:
                with e5a_v1._FD_OWNERSHIP_LOCK:
                    if (
                        source._state != "CLOSED"
                        or source._closure is not source_closure
                        or any(
                            source._fd_slots[slot] != -1
                            for slot in e5a_v1._ALL_OWNED_FD_SLOTS
                        )
                        or any(
                            record.owner in {source, runtime}
                            for record in e5a_v1._OWNED_FDS.values()
                        )
                        or any(
                            grant._runtime_id == id(runtime)
                            for grant in _LIVE_GRANTS.values()
                        )
                        or any(
                            type(record.owner)
                            is H1E5ANonlaunchableLeafCandidateV1
                            and record.owner._runtime_id == id(runtime)
                            for record in e5a_v1._OWNED_FDS.values()
                        )
                    ):
                        _fail("B2-A cleanup-only E5A handoff did not close exactly")
                    payload = _runtime_cleanup_payload(
                        runtime,
                        source_document,
                        postrun_evidence=postrun_evidence,
                        failed_birth_evidence=failed_birth_evidence,
                    )
                    closure_id = domains_v15.extension_content_id_v15(
                        domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN,
                        payload,
                    )
                    document = dict(payload)
                    document["h1_route_wide_runtime_lease_closure_id"] = closure_id
                    closure = H1E5ARuntimeLeaseClosureV1(
                        canonical_json_bytes(document),
                        _issuer=_CLOSURE_ISSUER,
                    )
                    def finish_closure_commit(*, inject_fault: bool) -> None:
                        step = 0

                        def boundary() -> None:
                            nonlocal step
                            step += 1
                            if (
                                inject_fault
                                and _TEST_ONLY_CLOSURE_FAULT_AFTER_STEP == step
                            ):
                                raise RuntimeError(
                                    "injected B2-A closure commit fault "
                                    f"after step {step}"
                                )

                        runtime._closure = closure
                        boundary()
                        runtime._state = "CLOSED"
                        boundary()
                        _QUARANTINED_RUNTIME_LEASES.pop(id(runtime), None)
                        _LIVE_RUNTIME_LEASES.pop(id(runtime), None)

                    original_mask = e5a_v1._block_fd_publication_signals()
                    try:
                        try:
                            finish_closure_commit(inject_fault=True)
                        except BaseException:
                            finish_closure_commit(inject_fault=False)
                    finally:
                        e5a_v1._restore_fd_publication_signals(original_mask)
                    return closure


def close_h1_e5a_runtime_lease_successor_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
) -> H1E5ARuntimeLeaseClosureV1:
    """Legacy unused-hierarchy cleanup; preserve the prelaunch semantics."""

    return _close_h1_e5a_runtime_lease_successor_impl_v1(
        runtime,
        postrun_evidence=None,
        failed_birth_evidence=None,
    )


def close_h1_e5a_runtime_lease_successor_postrun_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    *,
    evidence: e5a_v1.H1RouteWidePostrunCleanupEvidenceV1,
) -> H1E5ARuntimeLeaseClosureV1:
    """Hand back after PEAK_READ without replaying live-hierarchy peak reads."""

    if type(evidence) is not e5a_v1.H1RouteWidePostrunCleanupEvidenceV1:
        _fail("B2-A postrun cleanup requires exact typed evidence")
    return _close_h1_e5a_runtime_lease_successor_impl_v1(
        runtime,
        postrun_evidence=evidence,
        failed_birth_evidence=None,
    )


def close_h1_e5a_runtime_lease_successor_failed_birth_v1(
    runtime: H1E5ARuntimeLeaseSuccessorV1,
    *,
    evidence: e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1,
) -> H1E5ARuntimeLeaseClosureV1:
    """Hand back a killed/reaped failed birth without reading memory.peak."""

    if type(evidence) is not e5a_v1.H1RouteWideFailedBirthCleanupEvidenceV1:
        _fail("B2-A failed-birth cleanup requires exact typed evidence")
    return _close_h1_e5a_runtime_lease_successor_impl_v1(
        runtime,
        postrun_evidence=None,
        failed_birth_evidence=evidence,
    )


def _before_fork() -> None:
    _ADAPTER_LOCK.acquire()


def _after_fork_parent() -> None:
    _ADAPTER_LOCK.release()


def _after_fork_child() -> None:
    # E5A's earlier at-fork callback raw-closes every descriptor in its single
    # registry.  This callback then poisons the exact new owner objects.
    for runtime in tuple(
        {**_LIVE_RUNTIME_LEASES, **_QUARANTINED_RUNTIME_LEASES}.values()
    ):
        runtime._poison_after_fork_child()
    for grant in tuple(_LIVE_GRANTS.values()):
        grant._poison_after_fork_child()
    global _ADAPTER_LOCK
    _LIVE_RUNTIME_LEASES.clear()
    _QUARANTINED_RUNTIME_LEASES.clear()
    _LIVE_GRANTS.clear()
    _ADAPTER_LOCK = threading.RLock()


os.register_at_fork(
    before=_before_fork,
    after_in_parent=_after_fork_parent,
    after_in_child=_after_fork_child,
)


__all__ = (
    "ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT",
    "ACTUAL_PROCESS_BIRTH_PRESENT",
    "COUNTER_COMPLETENESS_GATE",
    "COMPANION_ADAPTER_IN_FUTURE_SOURCE_CLOSURE_REQUIRED",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "ConstructionK7H1E5ARuntimeLeaseSuccessorV1Error",
    "E5A_RUNTIME_LEASE_SUCCESSOR_PRESENT",
    "EXECUTION_SOURCE_CLOSURE_PRESENT",
    "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "FQ11_COUNTER_COMPLETENESS_PRESENT",
    "GUARDIAN_GATED_FIVE_ACTUAL_BIRTHS_PRESENT",
    "GUARDIAN_SESSION_PRESENT",
    "H1E5ANonlaunchableLeafCandidateV1",
    "H1E5ARuntimeLeaseClosureV1",
    "H1E5ARuntimeLeaseSuccessorV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "NONLAUNCHABLE_ONE_SHOT_LEAF_CANDIDATES_PRESENT",
    "PEAK_READ_PRESENT",
    "PREPARED_E5A_SUCCESSOR_PRESENT",
    "PROFILE_KEY",
    "PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT",
    "PROPOSED_CONTRACT_VERSION",
    "PURPOSE_BUILT_ONE_SHOT_LEAF_GRANTS_PRESENT",
    "READINESS",
    "ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT",
    "SCHEMA_VERSION",
    "SLOT_ORDER",
    "SLOT_TO_LEAF",
    "WORKLOAD_ECONOMICS_GATE",
    "close_h1_e5a_nonlaunchable_leaf_candidate_v1",
    "close_h1_e5a_runtime_lease_successor_failed_birth_v1",
    "close_h1_e5a_runtime_lease_successor_v1",
    "close_h1_e5a_runtime_lease_successor_postrun_v1",
    "consume_h1_e5a_runtime_lease_successor_v1",
    "frozen_e5a_runtime_bridge_manifest_v1",
    "issue_h1_e5a_nonlaunchable_leaf_candidate_v1",
    "verify_h1_e5a_runtime_lease_successor_v1",
)
