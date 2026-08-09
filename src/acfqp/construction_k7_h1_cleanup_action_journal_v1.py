"""Construction-only H1 failed-prefix cleanup authorization and journal.

V9 joins the exact V2 cleanup transition, terminal V6 receipt cutoff, V8
process-local guardian, C-C conservative Owner release and C-D componentwise
budget.  It deliberately does *not* reinterpret closing the Guardian's aliases
as proof that the underlying open-file description or mounted resource ceased
to exist.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v9 as domains_v9
from acfqp import construction_k7_h1_failed_prefix_cleanup_budget_admission_v1 as admission_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_native_capability_guardian_v1 as guardian_v1
from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_owner_cleanup_continuation_sidecar_v1 as sidecar_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E2"
PROFILE_KEY = "construction_k7_h1_cleanup_action_journal_v1"

CLEANUP_CUTOFF_JOIN_PRESENT = True
CLEANUP_ACTION_JOURNAL_PRESENT = True
COMPONENTWISE_C_D_BUDGET_SINGLE_SPEND_PRESENT = True
PIDFD_WAITID_REAP_EFFECT_PRESENT = True
GUARDIAN_ALIAS_SET_CLOSE_EFFECT_PRESENT = True
UNDERLYING_OFD_LAST_REFERENCE_RELEASE_PROVEN = False
MOUNT_RESOURCE_RELEASE_PROVEN = False
NORMAL_ORDINAL_41_TO_52_SUCCESS_EVENTS_ISSUED = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

JOIN_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_CUTOFF_JOIN_V1_DOMAIN
MANIFEST_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_ACTION_MANIFEST_V1_DOMAIN
ACTION_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_ACTION_DEFINITION_V1_DOMAIN
ALLOCATION_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_ALLOCATION_V1_DOMAIN
INTENT_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_ACTION_INTENT_V1_DOMAIN
PREOBS_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_PIDFD_PREOBSERVATION_V1_DOMAIN
RESULT_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_ACTION_RESULT_V1_DOMAIN
CURSOR_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_CURSOR_V1_DOMAIN
DRAIN_DOMAIN = domains_v9.CONSTRUCTION_K7_H1_CLEANUP_DRAIN_SNAPSHOT_V1_DOMAIN

_ROOT_NAME = ".acfqp-k7-h1-cleanup-action-journals-v1"
_ROOT_LOCK_FILE = "allocation.lock"
_ATTEMPT_PREFIX = "attempt-"
_MANIFEST_FILE = "cleanup-action-manifest.json"
_ALLOCATION_FILE = "cleanup-action-journal-allocation.json"
_LOCK_FILE = "cleanup-action-journal.lock"
_CURSOR_FILE = "cleanup-action-journal.cursor"
_SEAL_PREFIX = "cleanup-action-journal-allocation-seal-"
_TEMP_PREFIX = ".tmp-"
_TEMP_PATTERN = re.compile(r"^\.tmp-([0-9a-f]{64})-(.+)$")
_RECORD_PATTERN = re.compile(
    r"^record-([0-9]{4})-(intent|preobs|result)-([0-9a-f]{64})\.json$"
)

_MANIFEST_ISSUER = object()
_HANDLE_ISSUER = object()

# Native effects intentionally execute outside the journal flock.  The
# process-local one-shot therefore closes the otherwise possible recursive
# same-(allocation, ordinal) execution window.  Unknown exceptions burn the
# key fail-closed; only the explicit same-broker crash harness may relinquish
# it for durable reconciliation tests.
_EFFECT_RESERVATION_LOCK = threading.Lock()
_ACTIVE_EFFECT_RESERVATIONS: dict[tuple[str, int], object] = {}
_BURNED_EFFECT_RESERVATIONS: set[tuple[str, int]] = set()
_NATIVE_EFFECT_ATTESTATIONS: dict[tuple[str, str], dict[str, Any]] = {}
_HANDLE_REGISTRY_LOCK = threading.Lock()
_LIVE_JOURNAL_HANDLES: dict[int, "H1CleanupActionJournalHandleV1"] = {}


def _lock_effect_reservations_before_fork() -> None:
    _EFFECT_RESERVATION_LOCK.acquire()
    _HANDLE_REGISTRY_LOCK.acquire()


def _unlock_effect_reservations_after_fork_parent() -> None:
    _HANDLE_REGISTRY_LOCK.release()
    _EFFECT_RESERVATION_LOCK.release()


def _poison_effect_reservations_after_fork() -> None:
    global _EFFECT_RESERVATION_LOCK, _HANDLE_REGISTRY_LOCK
    _BURNED_EFFECT_RESERVATIONS.update(_ACTIVE_EFFECT_RESERVATIONS)
    _ACTIVE_EFFECT_RESERVATIONS.clear()
    _NATIVE_EFFECT_ATTESTATIONS.clear()
    for handle in tuple(_LIVE_JOURNAL_HANDLES.values()):
        for descriptor in (handle.attempt_fd, handle.root_fd, handle.base_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        handle.attempt_fd = handle.root_fd = handle.base_fd = -1
        handle._closed = True
    _LIVE_JOURNAL_HANDLES.clear()
    # A mutex inherited while locked by a vanished thread is unusable.  The
    # child is non-authoritative regardless, but replacing it avoids deadlock
    # before the broker-process check rejects the inherited handle.
    _EFFECT_RESERVATION_LOCK = threading.Lock()
    _HANDLE_REGISTRY_LOCK = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_lock_effect_reservations_before_fork,
        after_in_parent=_unlock_effect_reservations_after_fork_parent,
        after_in_child=_poison_effect_reservations_after_fork,
    )


_CATEGORY_ORDER = (
    "RESOLVE",
    "REAP",
    "MOUNT_CLOSE",
    "MEMORY_RELEASE",
    "OUTPUT_RELEASE",
)
_ACTION_CATEGORY = dict(admission_v1._ACTION_CATEGORY)
_CONSERVATIVE_ACTIONS = frozenset(sidecar_v1._SUPPORTED_ACTIONS)


class ConstructionK7H1CleanupActionJournalV1Error(ValueError):
    """The E2 cutoff, budget, action order, capability or journal crossed."""


class H1CleanupActionJournalInjectedCrashV1(RuntimeError):
    """Deterministic same-broker crash window used by focused tests."""


class H1CleanupActionCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_INTENT_FILE_FSYNC = "AFTER_INTENT_FILE_FSYNC"
    AFTER_INTENT_CURSOR_FSYNC = "AFTER_INTENT_CURSOR_FSYNC"
    AFTER_PIDFD_PREOBSERVATION_CURSOR_FSYNC = (
        "AFTER_PIDFD_PREOBSERVATION_CURSOR_FSYNC"
    )
    AFTER_EFFECT_BEFORE_RESULT = "AFTER_EFFECT_BEFORE_RESULT"
    AFTER_RESULT_FILE_FSYNC = "AFTER_RESULT_FILE_FSYNC"
    AFTER_RESULT_CURSOR_FSYNC = "AFTER_RESULT_CURSOR_FSYNC"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1CleanupActionJournalV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            f"{label} is not one content ID"
        ) from error


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _content_id(domain: str, payload: Any) -> str:
    return domains_v9.extension_content_id_v9(domain, payload)


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} bytes changed type")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


@dataclass(frozen=True, slots=True)
class H1CleanupActionManifestV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MANIFEST_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup action manifest is caller-minted")
        payload = _parse(self.payload_bytes, "cleanup action manifest")
        if payload.get("schema") != "acfqp.k7_h1_cleanup_action_manifest.v1":
            _fail("cleanup action manifest schema changed")
        object.__setattr__(self, "_manifest_id", _content_id(MANIFEST_DOMAIN, payload))

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse(self.payload_bytes, "cleanup action manifest")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            {**self.payload, "h1_cleanup_action_manifest_id": self.manifest_id}
        )

    def __reduce__(self) -> NoReturn:
        _fail("cleanup action manifest object is issuer-owned")


@dataclass(slots=True)
class H1CleanupActionJournalHandleV1:
    _issuer: InitVar[object]
    manifest: H1CleanupActionManifestV1
    allocation_bytes: bytes = field(repr=False)
    base_directory: str
    root_directory: str
    attempt_directory: str
    lock_device: int
    lock_inode: int
    cursor_device: int
    cursor_inode: int
    base_fd: int = field(repr=False)
    root_fd: int = field(repr=False)
    attempt_fd: int = field(repr=False)
    broker_process_id: int = field(repr=False)
    broker_thread: threading.Thread = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _allocation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _HANDLE_ISSUER
            or type(self.manifest) is not H1CleanupActionManifestV1
            or type(self.allocation_bytes) is not bytes
        ):
            _fail("cleanup action journal handle is caller-minted")
        document = _parse(self.allocation_bytes, "cleanup action journal allocation")
        payload = dict(document)
        claimed = _cid(
            payload.pop("h1_cleanup_action_journal_allocation_id", None),
            "cleanup action journal allocation",
        )
        if claimed != _content_id(ALLOCATION_DOMAIN, payload):
            _fail("cleanup action journal allocation identity changed")
        object.__setattr__(self, "_allocation_id", claimed)
        for descriptor, label in (
            (self.base_fd, "base"),
            (self.root_fd, "root"),
            (self.attempt_fd, "attempt"),
        ):
            if type(descriptor) is not int or descriptor < 0:
                _fail(f"cleanup action journal {label} directory is not pinned")
        with _HANDLE_REGISTRY_LOCK:
            if id(self) in _LIVE_JOURNAL_HANDLES:
                _fail("cleanup action journal handle registry identity collided")
            _LIVE_JOURNAL_HANDLES[id(self)] = self

    @property
    def allocation_id(self) -> str:
        return self._allocation_id

    @property
    def allocation(self) -> dict[str, Any]:
        return _parse(self.allocation_bytes, "cleanup action journal allocation")

    def __reduce__(self) -> NoReturn:
        _fail("cleanup action journal handle is process-local")


def _require_cleanup_lease(
    lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
) -> None:
    if (
        type(lease) is not cleanup_v2.H1AttemptCleanupOnlyLeaseV2
        or not lease._active
        or lease._owner_pid != os.getpid()
        or lease._owner_thread_id != threading.get_ident()
        or cleanup_v2._ACTIVE_V2_PHASE_LEASES.get() != (lease.handle.spec_id,)
        or phase_v1._ACTIVE_PHASE_LEASES.get() != (lease.handle.spec_id,)
        or type(transition) is not cleanup_v2.H1AttemptCleanupTransitionV2
        or lease.transition.transition_id != transition.transition_id
        or not hmac.compare_digest(
            lease.transition.canonical_bytes, transition.canonical_bytes
        )
    ):
        _fail("E2 requires the exact live V2 cleanup-only lease and transition")
    if rejection_v1._active_gate_modes(lease._gate_snapshot.gate_id) != (
        rejection_v1._CONTEXT_DEPENDENT_REPLAY_EXCLUSIVE,
    ):
        _fail("E2 cleanup-only lease lost its retained gate barrier")


def _require_broker_guardian(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
) -> None:
    try:
        guardian_v1._reject_public_reentry()
        guardian_v1._require_guardian(guardian)
    except guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            "E2 guardian is stale, poisoned, foreign or nonrecoverable"
        ) from error


def _load_or_freeze_native_cutoff(
    native_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    primary_failure_event: Any,
) -> dict[str, Any]:
    if type(native_handle) is not receipts_v1.H1NativeReceiptJournalHandleV1:
        _fail("E2 cutoff requires one exact V6 handle")
    replay = receipts_v1.replay_h1_native_receipt_journal_v1(native_handle)
    if isinstance(replay["cutoff_snapshot_id"], dict):
        if type(primary_failure_event) is not (
            __import__(
                "acfqp.construction_k7_h1_phase_aware_normal_prefix_v1",
                fromlist=["H1NormalSiteEventCommitV1"],
            ).H1NormalSiteEventCommitV1
        ):
            _fail("E2 needs the issuer-owned primary failure event to freeze V6")
        receipts_v1.freeze_h1_native_cutoff_snapshot_for_v2_transition_v1(
            native_handle, primary_failure_event=primary_failure_event
        )
    lock_fd = cursor_fd = -1
    try:
        lock_fd, cursor_fd, state = receipts_v1._with_locked(
            native_handle, repair=False
        )
        if state.cutoff is None:
            _fail("V6 cutoff did not become durable")
        cutoff = dict(state.cutoff)
    finally:
        if lock_fd >= 0:
            receipts_v1._unlock(lock_fd, cursor_fd)
    replayed = receipts_v1.replay_h1_native_receipt_journal_v1(native_handle)
    if replayed["cutoff_snapshot_id"] != cutoff["h1_native_cutoff_snapshot_id"]:
        _fail("V6 cutoff and terminal replay differ")
    return cutoff


def _selected_pass_and_budget_row(
    *,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
) -> tuple[cleanup_v1.H1LifecycleCleanupPassV1, dict[str, Any], list[dict[str, Any]]]:
    if (
        type(envelope) is not cleanup_v2.H1PreadmittedCleanupEnvelopeV1
        or type(cleanup_analysis) is not cleanup_v1.H1LifecycleCompleteBranchAnalysisV1
        or type(admission) is not admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1
    ):
        _fail("E2 manifest requires exact C-B/C-D construction artifacts")
    transition_payload = transition.payload
    cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
        cleanup_analysis, branch_key=transition_payload["branch_key"]
    )
    admission_payload = admission.payload
    if (
        transition_payload["h1_preadmitted_cleanup_envelope_id"]
        != envelope.envelope_id
        or transition_payload["h1_lifecycle_cleanup_pass_id"] != cleanup_pass.pass_id
        or admission_payload["h1_preadmitted_cleanup_envelope_id"]
        != envelope.envelope_id
        or admission_payload["h1_lifecycle_complete_branch_analysis_id"]
        != cleanup_analysis.analysis_id
    ):
        _fail("E2 transition, envelope, pass, analysis and C-D admission crossed")
    rows = [
        row
        for row in admission_payload["branch_budget_rows"]
        if row["branch_key"] == transition_payload["branch_key"]
    ]
    if len(rows) != 1:
        _fail("C-D admission lacks one exact selected branch budget row")
    row = dict(rows[0])
    exact_actions = list(row["exact_c_b_actions"])
    if (
        row["h1_lifecycle_cleanup_pass_id"] != cleanup_pass.pass_id
        or [item["exact_c_b_action"] for item in exact_actions]
        != cleanup_pass.payload["planned_cleanup_actions"]
    ):
        _fail("C-D selected branch no longer equals the exact cleanup pass")
    return cleanup_pass, row, exact_actions


def _verify_two_link_immutable_pair(
    first_fd: int,
    first_name: str,
    second_fd: int,
    second_name: str,
    *,
    expected_raw: bytes,
    label: str,
) -> bytes:
    primary_fd = seal_fd = -1
    try:
        primary_fd = _open_regular_at(
            first_fd,
            first_name,
            flags=os.O_RDONLY,
            label=f"{label} primary",
        )
        seal_fd = _open_regular_at(
            second_fd,
            second_name,
            flags=os.O_RDONLY,
            label=f"{label} seal",
        )
        primary_before = os.fstat(primary_fd)
        seal_before = os.fstat(seal_fd)
        if (
            stat.S_IMODE(primary_before.st_mode) != 0o400
            or stat.S_IMODE(seal_before.st_mode) != 0o400
            or primary_before.st_nlink != 2
            or seal_before.st_nlink != 2
            or (primary_before.st_dev, primary_before.st_ino)
            != (seal_before.st_dev, seal_before.st_ino)
        ):
            _fail(f"{label} durable pair topology changed")
        primary_raw = _read_descriptor(primary_fd)
        seal_raw = _read_descriptor(seal_fd)
        primary_after = os.fstat(primary_fd)
        seal_after = os.fstat(seal_fd)
        primary_map = os.stat(
            first_name, dir_fd=first_fd, follow_symlinks=False
        )
        seal_map = os.stat(
            second_name, dir_fd=second_fd, follow_symlinks=False
        )
        if (
            (primary_before.st_dev, primary_before.st_ino, primary_before.st_mode,
             primary_before.st_nlink, primary_before.st_size)
            != (primary_after.st_dev, primary_after.st_ino, primary_after.st_mode,
                primary_after.st_nlink, primary_after.st_size)
            or (seal_before.st_dev, seal_before.st_ino, seal_before.st_mode,
                seal_before.st_nlink, seal_before.st_size)
            != (seal_after.st_dev, seal_after.st_ino, seal_after.st_mode,
                seal_after.st_nlink, seal_after.st_size)
            or (primary_map.st_dev, primary_map.st_ino)
            != (primary_after.st_dev, primary_after.st_ino)
            or (seal_map.st_dev, seal_map.st_ino)
            != (seal_after.st_dev, seal_after.st_ino)
            or not hmac.compare_digest(primary_raw, expected_raw)
            or not hmac.compare_digest(seal_raw, expected_raw)
        ):
            _fail(f"{label} durable primary/seal pair changed")
        return primary_raw
    finally:
        if seal_fd >= 0:
            os.close(seal_fd)
        if primary_fd >= 0:
            os.close(primary_fd)


def _independently_replay_c_d_and_e1_marker(
    admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    guardian_snapshot: Mapping[str, Any],
) -> str:
    """Read-only replay of the durable C-D admission and E1 burn marker.

    A live Python object or the marker ID exposed by the public E1 snapshot is
    not enough: deleting either durable primary/seal pair must make E2 manifest
    freeze fail rather than silently upgrading process-local state.
    """

    admission_payload = admission.payload
    baseline = admission_payload["prospective_owner_cleanup_sidecar_baseline"]
    base = Path(baseline["phase_base_realpath"])
    base_fd = c_d_root_fd = c_d_attempt_fd = -1
    marker_root_fd = marker_attempt_fd = -1
    try:
        base_fd = _open_directory_path(base, label="E2 phase base replay")
        base_metadata = os.fstat(base_fd)
        if (base_metadata.st_dev, base_metadata.st_ino) != (
            baseline["phase_base_device"],
            baseline["phase_base_inode"],
        ):
            _fail("E2 phase base changed before durable prerequisite replay")
        route_attempt_id = admission_payload["route_attempt_id"]

        c_d_root_fd = _open_directory_at(
            base_fd,
            ".acfqp-k7-h1-failed-prefix-cleanup-budget-admissions-v1",
            label="C-D admission root replay",
        )
        c_d_attempt_fd = _open_directory_at(
            c_d_root_fd,
            route_attempt_id,
            label="C-D admission attempt replay",
        )
        _verify_two_link_immutable_pair(
            c_d_attempt_fd,
            "cleanup-budget-admission.json",
            base_fd,
            f"cleanup-budget-admission-seal-{route_attempt_id}",
            expected_raw=admission.canonical_bytes,
            label="C-D admission",
        )

        marker_root_fd = _open_directory_at(
            base_fd,
            ".acfqp-k7-h1-native-capability-guardian-v1",
            label="E1 marker root replay",
        )
        marker_attempt_fd = _open_directory_at(
            marker_root_fd,
            route_attempt_id,
            label="E1 marker attempt replay",
        )
        if set(os.listdir(marker_attempt_fd)) != {"guardian-init-marker.json"}:
            _fail("E1 marker attempt directory is not exact")
        marker_primary = _read_regular_at(
            marker_attempt_fd,
            "guardian-init-marker.json",
            label="E1 marker primary",
            exact_mode=0o400,
            exact_nlink=2,
        )
        marker_seal = _read_regular_at(
            base_fd,
            f"guardian-init-marker-seal-{route_attempt_id}",
            label="E1 marker seal",
            exact_mode=0o400,
            exact_nlink=2,
        )
        if (
            marker_primary is None
            or marker_seal is None
            or (marker_primary[1].st_dev, marker_primary[1].st_ino)
            != (marker_seal[1].st_dev, marker_seal[1].st_ino)
            or not hmac.compare_digest(marker_primary[0], marker_seal[0])
        ):
            _fail("E1 marker durable primary/seal pair changed")
        document = _parse(marker_primary[0], "E1 durable marker")
        payload = dict(document)
        claimed = _cid(
            payload.pop("h1_native_capability_guardian_init_marker_id", None),
            "E1 durable marker",
        )
        public_marker = _cid(
            guardian_snapshot.get(
                "h1_native_capability_guardian_init_marker_id"
            ),
            "E1 public snapshot marker",
        )
        if (
            claimed != public_marker
            or claimed
            != domains_v8.extension_content_id_v8(
                domains_v8.CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_INIT_MARKER_V1_DOMAIN,
                payload,
            )
            or payload.get("h1_native_capability_guardian_spec_id")
            != guardian.spec.spec_id
            or payload.get("h1_failed_prefix_cleanup_budget_admission_id")
            != admission.admission_id
            or payload.get("h1_native_receipt_allocation_id")
            != admission_payload["h1_native_receipt_allocation_id"]
            or payload.get("route_attempt_id") != route_attempt_id
            or payload.get("phase_base_realpath") != str(base)
        ):
            _fail("E1 durable marker does not match the public E1/C-D identity")
        final_base = os.stat(base, follow_symlinks=False)
        final_c_d_root = os.stat(
            ".acfqp-k7-h1-failed-prefix-cleanup-budget-admissions-v1",
            dir_fd=base_fd,
            follow_symlinks=False,
        )
        final_c_d_attempt = os.stat(
            route_attempt_id, dir_fd=c_d_root_fd, follow_symlinks=False
        )
        final_marker_root = os.stat(
            ".acfqp-k7-h1-native-capability-guardian-v1",
            dir_fd=base_fd,
            follow_symlinks=False,
        )
        final_marker_attempt = os.stat(
            route_attempt_id, dir_fd=marker_root_fd, follow_symlinks=False
        )
        if any(
            (mapped.st_dev, mapped.st_ino) != (os.fstat(pinned).st_dev, os.fstat(pinned).st_ino)
            for mapped, pinned in (
                (final_base, base_fd),
                (final_c_d_root, c_d_root_fd),
                (final_c_d_attempt, c_d_attempt_fd),
                (final_marker_root, marker_root_fd),
                (final_marker_attempt, marker_attempt_fd),
            )
        ):
            _fail("E1/C-D prerequisite directory mapping changed during replay")
        return claimed
    finally:
        for descriptor in (
            marker_attempt_fd,
            marker_root_fd,
            c_d_attempt_fd,
            c_d_root_fd,
            base_fd,
        ):
            if descriptor >= 0:
                os.close(descriptor)


def _guardian_cutoff_join_rows(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    cutoff: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    snapshot = guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
    snapshot_by_key = {row["slot_key"]: row for row in snapshot["slot_states"]}
    resolutions = cutoff.get("typed_resolutions")
    if type(resolutions) is not list or len(resolutions) != 12:
        _fail("V6 cutoff lost its exact twelve typed resolutions")
    joined: list[dict[str, Any]] = []
    with guardian_v1._REGISTRY_LOCK:
        for resolution in resolutions:
            key = resolution["slot_key"]
            snap = snapshot_by_key.get(key)
            state = guardian._slot_states.get(key)
            if snap is None or state is None:
                _fail("V6 cutoff and E1 slot registry differ")
            v6_kind = resolution["resolution_kind"]
            guardian_status = snap["guardian_status"]
            binding = dict(state.binding_document) if state.binding_document else None
            if v6_kind == "KNOWN_PRESENT":
                receipt_id = _cid(resolution.get("receipt_id"), "V6 present receipt")
                if (
                    guardian_status == "PRESENT_LIVE"
                    and state.cell is not None
                    and binding is not None
                    and binding.get("h1_native_resolution_id") == receipt_id
                ):
                    guardian_v1._verify_live_cell_locked(guardian, state.cell)
                    disposition = "PRESENT_LIVE"
                    binding_id: Any = binding[
                        "h1_native_capability_guardian_binding_id"
                    ]
                elif (
                    binding is None
                    and guardian_status == "UNRESOLVED"
                    and state.cell is None
                ):
                    disposition = "UNRESOLVED_DIRECT_V6_PRESENT_WITHOUT_GUARDIAN"
                    binding_id = _typed_null("NO_GUARDIAN_BINDING")
                else:
                    _fail("V6 present receipt contradicts the E1 Guardian state")
            elif v6_kind == "KNOWN_ABSENT":
                reason = resolution.get("reason")
                if reason == "SITE_NOT_REACHED_BEFORE_EXACT_CUTOFF":
                    if state.cell is not None or binding is not None or state.start_id is not None:
                        _fail("control-flow absent V6 slot has E1 native evidence")
                    disposition = "ABSENT_CONTROL_FLOW"
                    binding_id = _typed_null("CONTROL_FLOW_ABSENCE")
                elif (
                    guardian_status == "ABSENT"
                    and state.cell is None
                    and binding is not None
                    and binding.get("h1_native_resolution_id")
                    == resolution.get("resolution_record_id")
                ):
                    disposition = "ABSENT_EXPLICIT"
                    binding_id = binding[
                        "h1_native_capability_guardian_binding_id"
                    ]
                elif (
                    binding is None
                    and guardian_status == "UNRESOLVED"
                    and state.cell is None
                ):
                    disposition = "UNRESOLVED_DIRECT_V6_ABSENCE_WITHOUT_GUARDIAN"
                    binding_id = _typed_null("NO_GUARDIAN_BINDING")
                else:
                    _fail("V6 absence contradicts the E1 Guardian state")
            elif v6_kind == "UNRESOLVED":
                if (
                    binding is not None
                    or guardian_status != "UNRESOLVED"
                    or state.cell is not None
                ):
                    _fail("V6 unresolved contradicts existing E1 resolution evidence")
                disposition = "UNRESOLVED_V6_CUTOFF"
                binding_id = _typed_null("NO_GUARDIAN_BINDING")
            else:
                _fail("V6 cutoff resolution kind is not closed")
            joined.append(
                {
                    "slot_key": key,
                    "h1_native_resource_slot_id": resolution[
                        "h1_native_resource_slot_id"
                    ],
                    "capability_kind": snap["capability_kind"],
                    "v6_resolution_kind": v6_kind,
                    "v6_resolution": dict(resolution),
                    "e2_join_disposition": disposition,
                    "h1_native_capability_guardian_binding_id": binding_id,
                    "raw_descriptor_fields_serialized": False,
                    "generation_secret_serialized": False,
                }
            )
    return joined, snapshot


def freeze_h1_cleanup_action_manifest_v1(
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    *,
    primary_failure_event: Any,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    cleanup_budget_admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
) -> H1CleanupActionManifestV1:
    """Freeze the exact failure-time join before any cleanup effect."""

    _require_cleanup_lease(cleanup_lease, transition)
    _require_broker_guardian(guardian)
    cleanup_pass, budget_row, exact_actions = _selected_pass_and_budget_row(
        transition=transition,
        envelope=envelope,
        cleanup_analysis=cleanup_analysis,
        admission=cleanup_budget_admission,
    )
    transition_payload = transition.payload
    event_document = primary_failure_event.document
    if (
        primary_failure_event.event_id != transition_payload["primary_failure_event_id"]
        or event_document["ordinal"] != transition_payload["primary_failure_ordinal"]
        or event_document["site_key"] != transition_payload["primary_failure_site_key"]
        or event_document["outcome"] != transition_payload["primary_failure_outcome"]
        or event_document.get("declared_first_failure") is not True
    ):
        _fail("E2 primary failure event differs from the V2 transition")
    if (
        guardian._native_handle is not native_receipt_handle
        or guardian._admission is not cleanup_budget_admission
        or cleanup_budget_admission.payload["h1_native_receipt_allocation_id"]
        != native_receipt_handle.allocation_id
    ):
        _fail("E2 crossed Guardian, V6 and C-D live objects")
    cutoff = _load_or_freeze_native_cutoff(
        native_receipt_handle, primary_failure_event
    )
    if (
        cutoff["primary_failure_event_id"] != primary_failure_event.event_id
        or cutoff["primary_failure_ordinal"] != primary_failure_event.ordinal
        or cutoff["h1_normal_prefix_allocation_id"]
        != transition_payload["h1_normal_prefix_allocation_id"]
        or cutoff["h1_native_receipt_allocation_id"]
        != native_receipt_handle.allocation_id
    ):
        _fail("V6 cutoff is not the exact V2 failure boundary")
    join_rows, guardian_snapshot = _guardian_cutoff_join_rows(guardian, cutoff)
    marker_id = _independently_replay_c_d_and_e1_marker(
        cleanup_budget_admission,
        guardian,
        guardian_snapshot,
    )
    join_payload = {
        "schema": "acfqp.k7_h1_cleanup_cutoff_join.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
        "primary_failure_event_id": primary_failure_event.event_id,
        "h1_native_cutoff_snapshot_id": cutoff["h1_native_cutoff_snapshot_id"],
        "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
        "h1_native_capability_guardian_spec_id": guardian.spec.spec_id,
        "h1_native_capability_guardian_init_marker_id": marker_id,
        "h1_failed_prefix_cleanup_budget_admission_id": (
            cleanup_budget_admission.admission_id
        ),
        "phase_base_realpath": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_realpath"],
        "phase_base_device": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_device"],
        "phase_base_inode": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_inode"],
        "slot_joins": join_rows,
        "v2_v6_e1_exact_join_present": True,
        "raw_descriptor_fields_serialized": False,
        "generation_secret_serialized": False,
        "underlying_ofd_last_reference_release_proven": False,
        "mount_resource_release_proven": False,
    }
    join_document = {
        **join_payload,
        "h1_cleanup_cutoff_join_id": _content_id(JOIN_DOMAIN, join_payload),
    }
    actions: list[dict[str, Any]] = []
    for expected_ordinal, row in enumerate(exact_actions, start=1):
        action = dict(row["exact_c_b_action"])
        if (
            action["cleanup_ordinal"] != expected_ordinal
            or row["budget_category"] != _ACTION_CATEGORY[action["action_kind"]]
            or row["budget_units"] != 1
        ):
            _fail("selected C-D action order/category changed")
        action_payload = {
            "schema": "acfqp.k7_h1_cleanup_action_definition.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
            "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
            "cleanup_ordinal": expected_ordinal,
            "exact_c_b_action": action,
            "budget_category": row["budget_category"],
            "budget_units": 1,
        }
        actions.append(
            {
                **action_payload,
                "h1_cleanup_action_definition_id": _content_id(
                    ACTION_DOMAIN, action_payload
                ),
            }
        )
    payload = {
        "schema": "acfqp.k7_h1_cleanup_action_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": transition_payload["logical_occurrence_id"],
        "route_attempt_id": transition_payload["route_attempt_id"],
        "decision_point_id": transition_payload["decision_point_id"],
        "transaction_id": transition_payload["transaction_id"],
        "h1_attempt_execution_phase_spec_id": cleanup_lease.handle.spec_id,
        "h1_attempt_phase_allocation_id": cleanup_lease.handle.allocation_id,
        "h1_attempt_rejection_gate_id": transition_payload[
            "h1_attempt_rejection_gate_id"
        ],
        "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
        "primary_failure_event_id": primary_failure_event.event_id,
        "h1_preadmitted_cleanup_envelope_id": envelope.envelope_id,
        "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
        "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
        "branch_key": transition_payload["branch_key"],
        "h1_failed_prefix_cleanup_budget_admission_id": (
            cleanup_budget_admission.admission_id
        ),
        "phase_base_realpath": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_realpath"],
        "phase_base_device": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_device"],
        "phase_base_inode": cleanup_budget_admission.payload[
            "prospective_owner_cleanup_sidecar_baseline"
        ]["phase_base_inode"],
        "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
        "h1_native_cutoff_snapshot_id": cutoff["h1_native_cutoff_snapshot_id"],
        "h1_native_capability_guardian_spec_id": guardian.spec.spec_id,
        "h1_native_capability_guardian_init_marker_id": marker_id,
        "h1_cleanup_cutoff_join_id": join_document["h1_cleanup_cutoff_join_id"],
        "cleanup_cutoff_join": join_document,
        "selected_branch_budget": dict(budget_row["branch_cleanup_budget"]),
        "selected_branch_budget_total": budget_row["branch_cleanup_budget_total"],
        "available_cleanup_budget": dict(
            cleanup_budget_admission.payload["available_cleanup_budget"]
        ),
        "actions": actions,
        "action_count": len(actions),
        "failure_cleanup_only": True,
        "same_broker_process_thread_incarnation_required": True,
        "broker_death_or_consumed_token_recovery_present": False,
        "normal_ordinal_41_to_52_success_events_issued": False,
        "underlying_ofd_last_reference_release_proven": False,
        "mount_resource_release_proven": False,
        "production_output_leaf_authority_present": False,
        "current_access_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1CleanupActionManifestV1(
        _MANIFEST_ISSUER, canonical_json_bytes(payload)
    )


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written < 1:
            _fail("cleanup journal write made no progress")
        offset += written


def _directory_flags() -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _regular_flags(flags: int) -> int:
    flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_directory_path(path: Path, *, label: str) -> int:
    if not path.is_absolute():
        _fail(f"{label} is not absolute")
    try:
        descriptor = os.open(path, _directory_flags())
    except OSError as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            f"{label} cannot be pinned"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        _fail(f"{label} is not a directory")
    return descriptor


def _open_directory_at(
    parent_fd: int, name: str, *, label: str, exact_mode: int = 0o700
) -> int:
    try:
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    except OSError as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            f"{label} cannot be opened without following links"
        ) from error
    metadata = os.fstat(descriptor)
    try:
        mapped = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        os.close(descriptor)
        raise
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != exact_mode
        or (mapped.st_dev, mapped.st_ino) != (metadata.st_dev, metadata.st_ino)
    ):
        os.close(descriptor)
        _fail(f"{label} type, mode or namespace mapping changed")
    return descriptor


def _ensure_directory_at(parent_fd: int, name: str, *, label: str) -> int:
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    return _open_directory_at(parent_fd, name, label=label)


def _open_regular_at(
    directory_fd: int,
    name: str,
    *,
    flags: int,
    label: str,
    mode: int = 0o600,
) -> int:
    try:
        descriptor = os.open(
            name, _regular_flags(flags), mode, dir_fd=directory_fd
        )
    except OSError as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            f"{label} cannot be opened without following links"
        ) from error
    metadata = os.fstat(descriptor)
    try:
        mapped = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError:
        os.close(descriptor)
        raise
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (mapped.st_dev, mapped.st_ino) != (metadata.st_dev, metadata.st_ino)
    ):
        os.close(descriptor)
        _fail(f"{label} is not one mapped regular file")
    return descriptor


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1 << 16)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _read_regular_at(
    directory_fd: int,
    name: str,
    *,
    label: str,
    exact_mode: int,
    exact_nlink: int,
) -> tuple[bytes, os.stat_result] | None:
    try:
        descriptor = _open_regular_at(
            directory_fd, name, flags=os.O_RDONLY, label=label
        )
    except ConstructionK7H1CleanupActionJournalV1Error as error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise error
    try:
        metadata = os.fstat(descriptor)
        if (
            stat.S_IMODE(metadata.st_mode) != exact_mode
            or metadata.st_nlink != exact_nlink
        ):
            _fail(f"{label} mode or link count changed")
        raw = _read_descriptor(descriptor)
        after = os.fstat(descriptor)
        mapped = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size)
            != (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mode,
                metadata.st_nlink,
                metadata.st_size,
            )
            or (mapped.st_dev, mapped.st_ino)
            != (after.st_dev, after.st_ino)
            or len(raw) != after.st_size
        ):
            _fail(f"{label} changed while pinned read completed")
        return raw, after
    finally:
        os.close(descriptor)


def _read_immutable_with_allowed_nlinks(
    directory_fd: int,
    name: str,
    *,
    label: str,
    allowed_nlinks: set[int],
) -> tuple[bytes, os.stat_result] | None:
    try:
        descriptor = _open_regular_at(
            directory_fd, name, flags=os.O_RDONLY, label=label
        )
    except ConstructionK7H1CleanupActionJournalV1Error as error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise error
    try:
        metadata = os.fstat(descriptor)
        if (
            stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink not in allowed_nlinks
        ):
            _fail(f"{label} mode or link topology changed")
        raw = _read_descriptor(descriptor)
        after = os.fstat(descriptor)
        mapped = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size)
            != (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mode,
                metadata.st_nlink,
                metadata.st_size,
            )
            or (mapped.st_dev, mapped.st_ino)
            != (after.st_dev, after.st_ino)
            or len(raw) != after.st_size
        ):
            _fail(f"{label} changed while pinned read completed")
        return raw, after
    finally:
        os.close(descriptor)


def _publication_temp_name(name: str, raw: bytes) -> str:
    return f"{_TEMP_PREFIX}{hashlib.sha256(raw).hexdigest()}-{name}"


def _recover_expected_publication_temp(
    directory_fd: int, name: str, raw: bytes, *, label: str
) -> None:
    temporary = _publication_temp_name(name, raw)
    try:
        temp_fd = _open_regular_at(
            directory_fd,
            temporary,
            flags=os.O_RDONLY,
            label=f"{label} recovery temporary",
        )
    except ConstructionK7H1CleanupActionJournalV1Error as error:
        try:
            os.stat(temporary, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise error
    target_fd = -1
    try:
        temp_stat = os.fstat(temp_fd)
        try:
            target_fd = _open_regular_at(
                directory_fd, name, flags=os.O_RDONLY, label=label
            )
        except ConstructionK7H1CleanupActionJournalV1Error as error:
            try:
                os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                if temp_stat.st_nlink != 1:
                    _fail(f"{label} orphan temporary has foreign links")
                os.unlink(temporary, dir_fd=directory_fd)
                os.fsync(directory_fd)
                return
            raise error
        target_stat = os.fstat(target_fd)
        temp_raw = _read_descriptor(temp_fd)
        target_raw = _read_descriptor(target_fd)
        if (
            (temp_stat.st_dev, temp_stat.st_ino)
            != (target_stat.st_dev, target_stat.st_ino)
            or temp_stat.st_nlink != 2
            or target_stat.st_nlink != 2
            or stat.S_IMODE(temp_stat.st_mode) != 0o400
            or stat.S_IMODE(target_stat.st_mode) != 0o400
            or not hmac.compare_digest(temp_raw, raw)
            or not hmac.compare_digest(target_raw, raw)
        ):
            _fail(f"{label} publication temporary is not the exact crash edge")
        os.unlink(temporary, dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        if target_fd >= 0:
            os.close(target_fd)
        os.close(temp_fd)


def _publish_immutable_at(
    directory_fd: int,
    name: str,
    raw: bytes,
    *,
    label: str,
    exact_nlink: int = 1,
) -> os.stat_result:
    _recover_expected_publication_temp(directory_fd, name, raw, label=label)
    existing = _read_regular_at(
        directory_fd,
        name,
        label=label,
        exact_mode=0o400,
        exact_nlink=exact_nlink,
    )
    if existing is not None:
        if not hmac.compare_digest(existing[0], raw):
            _fail(f"{label} immutable bytes conflicted")
        return existing[1]
    temporary = _publication_temp_name(name, raw)
    descriptor = _open_regular_at(
        directory_fd,
        temporary,
        flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        label=f"{label} temporary",
        mode=0o600,
    )
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(
            temporary,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        os.fsync(directory_fd)
    except FileExistsError:
        pass
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileNotFoundError:
            pass
    published = _read_regular_at(
        directory_fd,
        name,
        label=label,
        exact_mode=0o400,
        exact_nlink=exact_nlink,
    )
    if published is None or not hmac.compare_digest(published[0], raw):
        _fail(f"{label} immutable publication raced or changed")
    return published[1]


def _open_or_create_lock_at(directory_fd: int, name: str, *, label: str) -> int:
    try:
        descriptor = _open_regular_at(
            directory_fd,
            name,
            flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
            label=label,
            mode=0o600,
        )
        os.fsync(descriptor)
        os.fsync(directory_fd)
    except ConstructionK7H1CleanupActionJournalV1Error:
        try:
            descriptor = _open_regular_at(
                directory_fd, name, flags=os.O_RDWR, label=label
            )
        except ConstructionK7H1CleanupActionJournalV1Error:
            raise
    metadata = os.fstat(descriptor)
    if (
        stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        os.close(descriptor)
        _fail(f"{label} mode or link count changed")
    return descriptor


def _cursor_payload(
    sequence: int,
    previous_id: Any,
    record_kind: str,
    record_id: Any,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_cleanup_journal_cursor.v1",
        "schema_version": SCHEMA_VERSION,
        "sequence": sequence,
        "previous_cursor_id": previous_id,
        "record_kind": record_kind,
        "record_id": record_id,
    }


def _cursor_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    return {
        **value,
        "h1_cleanup_journal_cursor_id": _content_id(CURSOR_DOMAIN, value),
    }


def _cursor_genesis(manifest_id: str) -> dict[str, Any]:
    return _cursor_row(
        _cursor_payload(
            0,
            _typed_null("CURSOR_GENESIS"),
            "GENESIS",
            manifest_id,
        )
    )


def _allocation_payload(
    manifest: H1CleanupActionManifestV1,
    base: Path,
    root: Path,
    attempt: Path,
    base_stat: os.stat_result,
    root_stat: os.stat_result,
    attempt_stat: os.stat_result,
    root_lock_stat: os.stat_result,
    lock_stat: os.stat_result,
    cursor_stat: os.stat_result,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_cleanup_journal_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_cleanup_action_manifest_id": manifest.manifest_id,
        "logical_occurrence_id": manifest.payload["logical_occurrence_id"],
        "route_attempt_id": manifest.payload["route_attempt_id"],
        "decision_point_id": manifest.payload["decision_point_id"],
        "transaction_id": manifest.payload["transaction_id"],
        "h1_attempt_cleanup_transition_v2_id": manifest.payload[
            "h1_attempt_cleanup_transition_v2_id"
        ],
        "h1_failed_prefix_cleanup_budget_admission_id": manifest.payload[
            "h1_failed_prefix_cleanup_budget_admission_id"
        ],
        "base_realpath": str(base),
        "base_device": base_stat.st_dev,
        "base_inode": base_stat.st_ino,
        "root_realpath": str(root),
        "root_device": root_stat.st_dev,
        "root_inode": root_stat.st_ino,
        "attempt_realpath": str(attempt),
        "attempt_device": attempt_stat.st_dev,
        "attempt_inode": attempt_stat.st_ino,
        "root_allocation_lock_device": root_lock_stat.st_dev,
        "root_allocation_lock_inode": root_lock_stat.st_ino,
        "journal_lock_device": lock_stat.st_dev,
        "journal_lock_inode": lock_stat.st_ino,
        "journal_cursor_device": cursor_stat.st_dev,
        "journal_cursor_inode": cursor_stat.st_ino,
        "broker_process_id": os.getpid(),
        "broker_thread_native_id": threading.get_native_id(),
        "broker_process_start_ticks": guardian_v1._process_start_ticks(),
        "same_broker_recovery_only": True,
        "cross_process_native_recovery_present": False,
        "broker_death_or_consumed_token_recovery_present": False,
        "underlying_ofd_last_reference_release_proven": False,
        "mount_resource_release_proven": False,
        "formal_counter_records_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }


def _handle_from_existing(
    manifest: H1CleanupActionManifestV1,
    allocation_raw: bytes,
    *,
    base_fd: int,
    root_fd: int,
    attempt_fd: int,
    lock_stat: os.stat_result,
    cursor_stat: os.stat_result,
) -> H1CleanupActionJournalHandleV1:
    document = _parse(allocation_raw, "cleanup action journal allocation")
    base = Path(document["base_realpath"])
    root = Path(document["root_realpath"])
    attempt = Path(document["attempt_realpath"])
    return H1CleanupActionJournalHandleV1(
        _HANDLE_ISSUER,
        manifest,
        allocation_raw,
        str(base),
        str(root),
        str(attempt),
        lock_stat.st_dev,
        lock_stat.st_ino,
        cursor_stat.st_dev,
        cursor_stat.st_ino,
        base_fd,
        root_fd,
        attempt_fd,
        os.getpid(),
        threading.current_thread(),
    )


def initialize_h1_cleanup_action_journal_v1(
    manifest: H1CleanupActionManifestV1,
    *,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
) -> H1CleanupActionJournalHandleV1:
    """Create/reopen under the exact still-live PHASE -> GATE cleanup lease."""

    if type(manifest) is not H1CleanupActionManifestV1:
        _fail("cleanup journal initialization requires one issuer-owned manifest")
    _require_cleanup_lease(cleanup_lease, transition)
    payload = manifest.payload
    if (
        payload.get("h1_attempt_cleanup_transition_v2_id")
        != transition.transition_id
        or payload.get("h1_attempt_execution_phase_spec_id")
        != cleanup_lease.handle.spec_id
        or payload.get("h1_attempt_phase_allocation_id")
        != cleanup_lease.handle.allocation_id
    ):
        _fail("cleanup journal initialization crossed manifest and live lease")
    cutoff_join = payload.get("cleanup_cutoff_join")
    if type(cutoff_join) is not dict:
        _fail("cleanup manifest lost its cutoff join")
    # C-D already pins the unique phase base.  Reuse that exact durable base.
    admission_base = Path(payload.get("phase_base_realpath", ""))
    if not admission_base.is_absolute():
        _fail("cleanup manifest lacks one exact phase-base realpath")
    base = admission_base.resolve(strict=True)
    base_fd = root_fd = attempt_fd = root_lock_fd = -1
    try:
        base_fd = _open_directory_path(base, label="E2 journal phase base")
        base_metadata = os.fstat(base_fd)
        live_base = os.stat(base, follow_symlinks=False)
        if (
            (base_metadata.st_dev, base_metadata.st_ino)
            != (payload["phase_base_device"], payload["phase_base_inode"])
            or (live_base.st_dev, live_base.st_ino)
            != (base_metadata.st_dev, base_metadata.st_ino)
        ):
            _fail("cleanup manifest phase-base identity changed")
        root_fd = _ensure_directory_at(
            base_fd, _ROOT_NAME, label="E2 journal root"
        )
        root = base / _ROOT_NAME
        root_lock_fd = _open_or_create_lock_at(
            root_fd, _ROOT_LOCK_FILE, label="E2 journal root lock"
        )
        fcntl.flock(root_lock_fd, fcntl.LOCK_EX)
        _require_cleanup_lease(cleanup_lease, transition)
        attempt_name = f"{_ATTEMPT_PREFIX}{payload['route_attempt_id']}"
        attempt_fd = _ensure_directory_at(
            root_fd, attempt_name, label="E2 journal attempt"
        )
        attempt = root / attempt_name
        _publish_immutable_at(
            attempt_fd,
            _MANIFEST_FILE,
            manifest.canonical_bytes,
            label="E2 cleanup manifest",
        )
        lock_fd = _open_or_create_lock_at(
            attempt_fd, _LOCK_FILE, label="E2 journal lock"
        )
        lock_stat = os.fstat(lock_fd)
        os.close(lock_fd)
        try:
            cursor_fd = _open_regular_at(
                attempt_fd,
                _CURSOR_FILE,
                flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
                label="E2 journal cursor",
                mode=0o600,
            )
            created_cursor = True
        except ConstructionK7H1CleanupActionJournalV1Error:
            cursor_fd = _open_regular_at(
                attempt_fd,
                _CURSOR_FILE,
                flags=os.O_RDWR,
                label="E2 journal cursor",
            )
            created_cursor = False
        try:
            cursor_stat = os.fstat(cursor_fd)
            if (
                stat.S_IMODE(cursor_stat.st_mode) != 0o600
                or cursor_stat.st_nlink != 1
            ):
                _fail("E2 journal cursor mode or link count changed")
            genesis_raw = (
                canonical_json_bytes(_cursor_genesis(manifest.manifest_id))
                + b"\n"
            )
            current_cursor = _read_descriptor(cursor_fd)
            if created_cursor:
                _write_all(
                    cursor_fd,
                    genesis_raw,
                )
                os.fsync(cursor_fd)
                os.fsync(attempt_fd)
            elif (
                not current_cursor.endswith(b"\n")
                and len(current_cursor) < len(genesis_raw)
                and hmac.compare_digest(
                    current_cursor, genesis_raw[: len(current_cursor)]
                )
            ):
                # This is the unique create-before-genesis crash edge.  A
                # complete established cursor (including a later torn row) is
                # repaired only by normal immutable-frontier replay.
                os.ftruncate(cursor_fd, 0)
                os.lseek(cursor_fd, 0, os.SEEK_SET)
                _write_all(cursor_fd, genesis_raw)
                os.fsync(cursor_fd)
                os.fsync(attempt_fd)
        finally:
            os.close(cursor_fd)
        allocation_payload = _allocation_payload(
            manifest,
            base,
            root,
            attempt,
            os.fstat(base_fd),
            os.fstat(root_fd),
            os.fstat(attempt_fd),
            os.fstat(root_lock_fd),
            lock_stat,
            cursor_stat,
        )
        allocation_document = {
            **allocation_payload,
            "h1_cleanup_action_journal_allocation_id": _content_id(
                ALLOCATION_DOMAIN, allocation_payload
            ),
        }
        allocation_raw = canonical_json_bytes(allocation_document)
        primary = _read_immutable_with_allowed_nlinks(
            attempt_fd,
            _ALLOCATION_FILE,
            label="E2 journal allocation",
            allowed_nlinks={1, 2},
        )
        seal_name = f"{_SEAL_PREFIX}{payload['route_attempt_id']}"
        seal = _read_immutable_with_allowed_nlinks(
            base_fd,
            seal_name,
            label="E2 journal allocation seal",
            allowed_nlinks={1, 2},
        )
        if primary is None and seal is None:
            _publish_immutable_at(
                attempt_fd,
                _ALLOCATION_FILE,
                allocation_raw,
                label="E2 journal allocation",
                exact_nlink=1,
            )
            primary = _read_immutable_with_allowed_nlinks(
                attempt_fd,
                _ALLOCATION_FILE,
                label="E2 journal allocation",
                allowed_nlinks={1},
            )
        if primary is not None and not hmac.compare_digest(
            primary[0], allocation_raw
        ):
            _fail("E2 journal allocation conflicts with exact manifest")
        if seal is not None and not hmac.compare_digest(seal[0], allocation_raw):
            _fail("E2 journal allocation seal conflicts with exact manifest")
        if primary is not None and seal is None:
            if primary[1].st_nlink != 1:
                _fail("lone E2 allocation primary has a foreign hard link")
            try:
                os.link(
                    _ALLOCATION_FILE,
                    seal_name,
                    src_dir_fd=attempt_fd,
                    dst_dir_fd=base_fd,
                    follow_symlinks=False,
                )
                os.fsync(base_fd)
            except FileExistsError:
                pass
        elif primary is None and seal is not None:
            _fail("seal-only E2 allocation is not a crash-recoverable state")
        elif primary is not None and seal is not None and (
            (primary[1].st_dev, primary[1].st_ino)
            != (seal[1].st_dev, seal[1].st_ino)
            or primary[1].st_nlink != 2
            or seal[1].st_nlink != 2
        ):
            _fail("existing E2 allocation pair has foreign topology")
        primary = _read_regular_at(
            attempt_fd,
            _ALLOCATION_FILE,
            label="E2 journal allocation",
            exact_mode=0o400,
            exact_nlink=2,
        )
        seal = _read_regular_at(
            base_fd,
            seal_name,
            label="E2 journal allocation seal",
            exact_mode=0o400,
            exact_nlink=2,
        )
        if (
            primary is None
            or seal is None
            or (primary[1].st_dev, primary[1].st_ino)
            != (seal[1].st_dev, seal[1].st_ino)
            or not hmac.compare_digest(primary[0], allocation_raw)
            or not hmac.compare_digest(seal[0], allocation_raw)
        ):
            _fail("cleanup journal allocation/base seal topology changed")
        _verify_two_link_immutable_pair(
            attempt_fd,
            _ALLOCATION_FILE,
            base_fd,
            seal_name,
            expected_raw=allocation_raw,
            label="E2 journal allocation",
        )
        _require_cleanup_lease(cleanup_lease, transition)
        handle = _handle_from_existing(
            manifest,
            allocation_raw,
            base_fd=base_fd,
            root_fd=root_fd,
            attempt_fd=attempt_fd,
            lock_stat=lock_stat,
            cursor_stat=cursor_stat,
        )
        base_fd = root_fd = attempt_fd = -1
        return handle
    finally:
        if root_lock_fd >= 0:
            try:
                fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(root_lock_fd)
        for descriptor in (attempt_fd, root_fd, base_fd):
            if descriptor >= 0:
                os.close(descriptor)


def _require_handle(
    handle: H1CleanupActionJournalHandleV1,
) -> tuple[int, int, int]:
    with _HANDLE_REGISTRY_LOCK:
        registered = _LIVE_JOURNAL_HANDLES.get(id(handle)) is handle
    if (
        type(handle) is not H1CleanupActionJournalHandleV1
        or handle._closed
        or not registered
        or handle.broker_process_id != os.getpid()
        or handle.broker_thread is not threading.current_thread()
        or guardian_v1._process_start_ticks()
        != handle.allocation["broker_process_start_ticks"]
    ):
        _fail("cleanup action journal crossed its broker process/thread/incarnation")
    allocation = handle.allocation
    base_stat = os.fstat(handle.base_fd)
    root_stat = os.fstat(handle.root_fd)
    attempt_stat = os.fstat(handle.attempt_fd)
    base_path = os.stat(handle.base_directory, follow_symlinks=False)
    root_map = os.stat(_ROOT_NAME, dir_fd=handle.base_fd, follow_symlinks=False)
    attempt_name = f"{_ATTEMPT_PREFIX}{handle.manifest.payload['route_attempt_id']}"
    attempt_map = os.stat(
        attempt_name, dir_fd=handle.root_fd, follow_symlinks=False
    )
    if (
        not all(stat.S_ISDIR(value.st_mode) for value in (base_stat, root_stat, attempt_stat))
        or stat.S_IMODE(root_stat.st_mode) != 0o700
        or stat.S_IMODE(attempt_stat.st_mode) != 0o700
        or (base_stat.st_dev, base_stat.st_ino)
        != (allocation["base_device"], allocation["base_inode"])
        or (root_stat.st_dev, root_stat.st_ino)
        != (allocation["root_device"], allocation["root_inode"])
        or (attempt_stat.st_dev, attempt_stat.st_ino)
        != (allocation["attempt_device"], allocation["attempt_inode"])
        or (base_path.st_dev, base_path.st_ino)
        != (base_stat.st_dev, base_stat.st_ino)
        or (root_map.st_dev, root_map.st_ino)
        != (root_stat.st_dev, root_stat.st_ino)
        or (attempt_map.st_dev, attempt_map.st_ino)
        != (attempt_stat.st_dev, attempt_stat.st_ino)
    ):
        _fail("cleanup action journal pinned directory mapping changed")
    manifest_entry = _read_regular_at(
        handle.attempt_fd,
        _MANIFEST_FILE,
        label="E2 cleanup manifest",
        exact_mode=0o400,
        exact_nlink=1,
    )
    if manifest_entry is None or not hmac.compare_digest(
        manifest_entry[0], handle.manifest.canonical_bytes
    ):
        _fail("cleanup action journal manifest storage changed")
    seal_name = f"{_SEAL_PREFIX}{handle.manifest.payload['route_attempt_id']}"
    _verify_two_link_immutable_pair(
        handle.attempt_fd,
        _ALLOCATION_FILE,
        handle.base_fd,
        seal_name,
        expected_raw=handle.allocation_bytes,
        label="E2 journal allocation",
    )
    root_lock = _read_regular_at(
        handle.root_fd,
        _ROOT_LOCK_FILE,
        label="E2 journal root lock",
        exact_mode=0o600,
        exact_nlink=1,
    )
    lock = _read_regular_at(
        handle.attempt_fd,
        _LOCK_FILE,
        label="E2 journal lock",
        exact_mode=0o600,
        exact_nlink=1,
    )
    cursor = _read_regular_at(
        handle.attempt_fd,
        _CURSOR_FILE,
        label="E2 journal cursor",
        exact_mode=0o600,
        exact_nlink=1,
    )
    if root_lock is None or lock is None or cursor is None:
        _fail("cleanup action journal mutable control file disappeared")
    if (
        (root_lock[1].st_dev, root_lock[1].st_ino)
        != (
            allocation["root_allocation_lock_device"],
            allocation["root_allocation_lock_inode"],
        )
        or (lock[1].st_dev, lock[1].st_ino)
        != (handle.lock_device, handle.lock_inode)
        or (cursor[1].st_dev, cursor[1].st_ino)
        != (handle.cursor_device, handle.cursor_inode)
    ):
        _fail("cleanup action journal mutable control inode changed")
    final_base_path = os.stat(handle.base_directory, follow_symlinks=False)
    final_root_map = os.stat(
        _ROOT_NAME, dir_fd=handle.base_fd, follow_symlinks=False
    )
    final_attempt_map = os.stat(
        attempt_name, dir_fd=handle.root_fd, follow_symlinks=False
    )
    if (
        (final_base_path.st_dev, final_base_path.st_ino)
        != (base_stat.st_dev, base_stat.st_ino)
        or (final_root_map.st_dev, final_root_map.st_ino)
        != (root_stat.st_dev, root_stat.st_ino)
        or (final_attempt_map.st_dev, final_attempt_map.st_ino)
        != (attempt_stat.st_dev, attempt_stat.st_ino)
    ):
        _fail("cleanup action journal directory mapping changed during replay")
    return handle.base_fd, handle.root_fd, handle.attempt_fd


def close_h1_cleanup_action_journal_v1(
    handle: H1CleanupActionJournalHandleV1,
) -> None:
    """Dispose the process-local directory pins; durable bytes remain."""

    if type(handle) is not H1CleanupActionJournalHandleV1:
        _fail("cleanup journal close requires one issuer-owned handle")
    if (
        handle.broker_process_id != os.getpid()
        or handle.broker_thread is not threading.current_thread()
    ):
        _fail("cleanup journal close crossed broker process or thread")
    with _EFFECT_RESERVATION_LOCK:
        if any(key[0] == handle.allocation_id for key in _ACTIVE_EFFECT_RESERVATIONS):
            _fail("cleanup journal cannot close during an active native effect")
    with _HANDLE_REGISTRY_LOCK:
        if handle._closed or _LIVE_JOURNAL_HANDLES.get(id(handle)) is not handle:
            _fail("cleanup journal handle is already closed or foreign")
        del _LIVE_JOURNAL_HANDLES[id(handle)]
        handle._closed = True
        descriptors = (handle.attempt_fd, handle.root_fd, handle.base_fd)
        handle.attempt_fd = handle.root_fd = handle.base_fd = -1
    for descriptor in descriptors:
        try:
            os.close(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise


def _open_locked(
    handle: H1CleanupActionJournalHandleV1,
) -> tuple[int, int, int]:
    _base, _root, attempt_fd = _require_handle(handle)
    lock_fd = _open_regular_at(
        attempt_fd, _LOCK_FILE, flags=os.O_RDWR, label="E2 journal lock"
    )
    cursor_fd = -1
    try:
        lock_meta = os.fstat(lock_fd)
        if (
            not stat.S_ISREG(lock_meta.st_mode)
            or stat.S_IMODE(lock_meta.st_mode) != 0o600
            or lock_meta.st_nlink != 1
            or (lock_meta.st_dev, lock_meta.st_ino)
            != (handle.lock_device, handle.lock_inode)
        ):
            _fail("cleanup action journal lock identity changed")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        # Revalidate the name after taking the flock: a replacement attempt
        # cannot turn a stale pinned inode into authority.
        lock_map = os.stat(
            _LOCK_FILE, dir_fd=attempt_fd, follow_symlinks=False
        )
        if (lock_map.st_dev, lock_map.st_ino) != (
            lock_meta.st_dev,
            lock_meta.st_ino,
        ):
            _fail("cleanup action journal lock mapping changed under flock")
        cursor_fd = _open_regular_at(
            attempt_fd, _CURSOR_FILE, flags=os.O_RDWR, label="E2 journal cursor"
        )
        cursor_meta = os.fstat(cursor_fd)
        if (
            not stat.S_ISREG(cursor_meta.st_mode)
            or stat.S_IMODE(cursor_meta.st_mode) != 0o600
            or cursor_meta.st_nlink != 1
            or (cursor_meta.st_dev, cursor_meta.st_ino)
            != (handle.cursor_device, handle.cursor_inode)
        ):
            _fail("cleanup action journal cursor identity changed")
        cursor_map = os.stat(
            _CURSOR_FILE, dir_fd=attempt_fd, follow_symlinks=False
        )
        if (cursor_map.st_dev, cursor_map.st_ino) != (
            cursor_meta.st_dev,
            cursor_meta.st_ino,
        ):
            _fail("cleanup action journal cursor mapping changed under flock")
        return attempt_fd, lock_fd, cursor_fd
    except BaseException:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
        raise


def _unlock(lock_fd: int, cursor_fd: int, attempt_fd: int) -> None:
    failure: BaseException | None = None
    try:
        for name, descriptor, mode in (
            (_LOCK_FILE, lock_fd, 0o600),
            (_CURSOR_FILE, cursor_fd, 0o600),
        ):
            pinned = os.fstat(descriptor)
            mapped = os.stat(name, dir_fd=attempt_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(pinned.st_mode)
                or stat.S_IMODE(pinned.st_mode) != mode
                or pinned.st_nlink != 1
                or (mapped.st_dev, mapped.st_ino)
                != (pinned.st_dev, pinned.st_ino)
            ):
                _fail("cleanup journal mutable mapping changed before unlock")
    except BaseException as error:
        failure = error
    os.close(cursor_fd)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    finally:
        os.close(lock_fd)
    if failure is not None:
        raise failure


def _record_identity(document: Mapping[str, Any]) -> tuple[str, str, str]:
    table = {
        "acfqp.k7_h1_cleanup_action_intent.v1": (
            "intent",
            INTENT_DOMAIN,
            "h1_cleanup_action_intent_id",
        ),
        "acfqp.k7_h1_cleanup_pidfd_preobservation.v1": (
            "preobs",
            PREOBS_DOMAIN,
            "h1_cleanup_pidfd_preobservation_id",
        ),
        "acfqp.k7_h1_cleanup_action_result.v1": (
            "result",
            RESULT_DOMAIN,
            "h1_cleanup_action_result_id",
        ),
    }
    row = table.get(document.get("schema"))
    if row is None:
        _fail("cleanup journal record schema is unregistered")
    kind, domain, field_name = row
    payload = dict(document)
    claimed = _cid(payload.pop(field_name, None), f"cleanup {kind} record")
    if claimed != _content_id(domain, payload):
        _fail("cleanup journal record content identity changed")
    return kind, field_name, claimed


def _read_cursor(
    cursor_fd: int,
    expected: list[dict[str, Any]],
    *,
    repair: bool,
) -> list[dict[str, Any]]:
    os.lseek(cursor_fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(cursor_fd, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        _fail("cleanup action journal cursor is empty")
    if not raw.endswith(b"\n"):
        if not repair or b"\n" not in raw:
            _fail("cleanup action journal cursor has an unrepairable torn suffix")
        cutoff = raw.rfind(b"\n") + 1
        retained = raw[:cutoff]
        suffix = raw[cutoff:]
        retained_rows = [
            _parse(line, "cleanup action journal retained cursor row")
            for line in retained.splitlines()
        ]
        if (
            retained_rows != expected[: len(retained_rows)]
            or len(expected) - len(retained_rows) != 1
        ):
            _fail("cleanup action journal torn suffix lacks an exact prefix")
        next_raw = canonical_json_bytes(expected[len(retained_rows)]) + b"\n"
        if (
            not suffix
            or len(suffix) >= len(next_raw)
            or not hmac.compare_digest(suffix, next_raw[: len(suffix)])
        ):
            _fail("cleanup action journal torn suffix is not the unique next row")
        os.ftruncate(cursor_fd, cutoff)
        os.fsync(cursor_fd)
        raw = retained
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        rows.append(_parse(line, "cleanup action journal cursor row"))
    if not rows:
        _fail("cleanup action journal cursor lost genesis")
    return rows


def _scan_records(attempt_fd: int) -> list[dict[str, Any]]:
    records: list[tuple[int, str, str, dict[str, Any]]] = []
    allowed_fixed = {
        _MANIFEST_FILE,
        _ALLOCATION_FILE,
        _LOCK_FILE,
        _CURSOR_FILE,
    }
    for name in os.listdir(attempt_fd):
        if name in allowed_fixed:
            continue
        if name.startswith(_TEMP_PREFIX):
            temp_match = _TEMP_PATTERN.fullmatch(name)
            if temp_match is None:
                _fail("cleanup action journal has a foreign temporary name")
            target = temp_match.group(2)
            if target not in allowed_fixed and _RECORD_PATTERN.fullmatch(target) is None:
                _fail("cleanup action journal temporary targets a foreign name")
            temp_fd = _open_regular_at(
                attempt_fd,
                name,
                flags=os.O_RDONLY,
                label="E2 journal recovery temporary",
            )
            try:
                metadata = os.fstat(temp_fd)
                try:
                    os.stat(target, dir_fd=attempt_fd, follow_symlinks=False)
                except FileNotFoundError:
                    if metadata.st_nlink != 1:
                        _fail("cleanup action journal orphan temporary has links")
                    os.unlink(name, dir_fd=attempt_fd)
                    os.fsync(attempt_fd)
                    continue
                raw = _read_descriptor(temp_fd)
                if hashlib.sha256(raw).hexdigest() != temp_match.group(1):
                    _fail("cleanup action journal linked temporary hash changed")
            finally:
                os.close(temp_fd)
            _recover_expected_publication_temp(
                attempt_fd,
                target,
                raw,
                label="E2 journal linked publication",
            )
            continue
        match = _RECORD_PATTERN.fullmatch(name)
        if match is None:
            _fail("cleanup action journal contains a foreign entry")
        entry = _read_regular_at(
            attempt_fd,
            name,
            label="E2 journal record",
            exact_mode=0o400,
            exact_nlink=1,
        )
        if entry is None:
            _fail("cleanup action journal record disappeared")
        document = _parse(entry[0], "cleanup action journal record")
        kind, _field, record_id = _record_identity(document)
        if kind != match.group(2) or record_id != match.group(3):
            _fail("cleanup action journal filename and content differ")
        records.append((int(match.group(1)), kind, record_id, document))
    records.sort(key=lambda item: item[0])
    if [item[0] for item in records] != list(range(1, len(records) + 1)):
        _fail("cleanup action journal record sequence is gapped")
    return [item[3] for item in records]


def _append_cursor(
    cursor_fd: int,
    rows: list[dict[str, Any]],
    *,
    record_kind: str,
    record_id: str,
) -> list[dict[str, Any]]:
    payload = _cursor_payload(
        len(rows),
        rows[-1]["h1_cleanup_journal_cursor_id"],
        record_kind.upper(),
        record_id,
    )
    row = _cursor_row(payload)
    os.lseek(cursor_fd, 0, os.SEEK_END)
    _write_all(cursor_fd, canonical_json_bytes(row) + b"\n")
    os.fsync(cursor_fd)
    return [*rows, row]


def _load_state_locked(
    handle: H1CleanupActionJournalHandleV1,
    attempt: int,
    cursor_fd: int,
    *,
    repair: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = _scan_records(attempt)
    expected = [_cursor_genesis(handle.manifest.manifest_id)]
    for document in records:
        kind, _field, record_id = _record_identity(document)
        expected.append(
            _cursor_row(
                _cursor_payload(
                    len(expected),
                    expected[-1]["h1_cleanup_journal_cursor_id"],
                    kind.upper(),
                    record_id,
                )
            )
        )
    rows = _read_cursor(cursor_fd, expected, repair=repair)
    if len(rows) > len(expected) or rows != expected[: len(rows)]:
        _fail("cleanup action journal cursor diverged from immutable records")
    if len(rows) < len(expected):
        if not repair or len(expected) - len(rows) != 1:
            _fail("cleanup action journal cursor is behind its immutable frontier")
        missing = expected[-1]
        rows = _append_cursor(
            cursor_fd,
            rows,
            record_kind=missing["record_kind"],
            record_id=missing["record_id"],
        )
        if rows != expected:
            _fail("cleanup action journal cursor repair changed identity")
    _validate_record_semantics(handle, records, verify_external=False)
    return records, rows


def _revalidate_records_outside_action_lock(
    handle: H1CleanupActionJournalHandleV1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attempt, lock_fd, cursor_fd = _open_locked(handle)
    try:
        records, rows = _load_state_locked(
            handle, attempt, cursor_fd, repair=True
        )
    finally:
        _unlock(lock_fd, cursor_fd, attempt)
    # C-C immutable primary/seal replay occurs only after ACTION is released.
    _validate_record_semantics(handle, records, verify_external=True)
    verify_attempt, verify_lock_fd, verify_cursor_fd = _open_locked(handle)
    try:
        final_records, final_rows = _load_state_locked(
            handle, verify_attempt, verify_cursor_fd, repair=False
        )
        if final_records != records or final_rows != rows:
            _fail("cleanup journal changed during external semantic replay")
    finally:
        _unlock(
            verify_lock_fd,
            verify_cursor_fd,
            verify_attempt,
        )
    return records, rows


def _validate_record_semantics(
    handle: H1CleanupActionJournalHandleV1,
    records: list[dict[str, Any]],
    *,
    verify_external: bool = True,
) -> None:
    manifest = handle.manifest.payload
    actions = manifest["actions"]
    consumed = {key: 0 for key in _CATEGORY_ORDER}
    previous_result: Any = _typed_null("NO_PREVIOUS_ACTION_RESULT")
    index = 0
    for action in actions:
        if index >= len(records):
            break
        intent = records[index]
        kind, _field, intent_id = _record_identity(intent)
        expected_intent = _build_intent(
            handle,
            action,
            {"budget_consumed": consumed, "last_result_id": previous_result},
        )
        if kind != "intent" or intent != expected_intent:
            _fail("cleanup action intent is not the exact derived debit")
        consumed = dict(intent["budget_after"])
        index += 1
        preobs: dict[str, Any] | None = None
        if index < len(records) and records[index].get("schema") == (
            "acfqp.k7_h1_cleanup_pidfd_preobservation.v1"
        ):
            preobs = records[index]
            _validate_pidfd_preobservation(handle, action, intent, preobs)
            index += 1
        elif action["exact_c_b_action"]["action_kind"] != "REAP_DESCENDANT":
            preobs = None
        if index >= len(records):
            break
        result = records[index]
        result_kind, _field, result_id = _record_identity(result)
        expected_result = _build_result(
            handle,
            action,
            intent,
            outcome=result.get("outcome"),
            evidence=result.get("effect_evidence", {}),
        )
        if result_kind != "result" or result != expected_result:
            _fail("cleanup action result is not the exact derived envelope")
        _validate_result_outcome(
            handle,
            action,
            intent,
            preobs,
            result,
            verify_external=verify_external,
        )
        previous_result = result_id
        index += 1
    if index != len(records):
        _fail("cleanup action journal has a record outside the selected action frontier")


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{label} evidence schema changed")
    return value


def _waitid_evidence(value: Any, label: str) -> Mapping[str, int]:
    row = _exact_keys(
        value,
        {"si_pid", "si_uid", "si_signo", "si_status", "si_code"},
        label,
    )
    if any(type(row[key]) is not int for key in row):
        _fail(f"{label} fields changed type")
    return row  # type: ignore[return-value]


def _parse_c_c_artifact(
    raw: bytes, *, id_field: str, domain: str, label: str
) -> tuple[dict[str, Any], str]:
    document = _parse(raw, label)
    payload = dict(document)
    claimed = _cid(payload.pop(id_field, None), label)
    if claimed != sidecar_v1._content_id(domain, payload):
        _fail(f"{label} content identity changed")
    return document, claimed


def _verify_owner_release_durable(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> None:
    """Replay the exact C-C allocation/release pairs and combined projection."""

    spec_id = _cid(
        evidence["h1_owner_cleanup_sidecar_spec_id"], "C-C sidecar spec"
    )
    allocation_id = _cid(
        evidence["h1_owner_cleanup_sidecar_allocation_id"],
        "C-C sidecar allocation",
    )
    release_id = _cid(evidence["h1_owner_cleanup_release_id"], "C-C release")
    reservation_id = _cid(
        evidence["h1_shared_cap_owner_v3_reservation_id"],
        "C-C Owner reservation",
    )
    combined = evidence["owner_cleanup_combined_state"]
    if type(combined) is not dict:
        _fail("C-C combined state is not embedded canonically")
    combined_payload = dict(combined)
    combined_id = _cid(
        combined_payload.pop("h1_owner_cleanup_combined_state_id", None),
        "C-C combined state",
    )
    if (
        combined_id != evidence["h1_owner_cleanup_combined_state_id"]
        or combined_id
        != sidecar_v1._content_id(sidecar_v1.COMBINED_DOMAIN, combined_payload)
    ):
        _fail("C-C combined state content identity changed")
    runtime_id = _cid(
        combined.get("h1_shared_cap_owner_v3_runtime_id"), "C-C Owner runtime"
    )
    root_fd = sidecar_fd = -1
    try:
        root_fd = _open_directory_at(
            handle.base_fd,
            ".acfqp-k7-h1-owner-cleanup-sidecars-v1",
            label="C-C sidecar root replay",
        )
        sidecar_fd = _open_directory_at(
            root_fd,
            f"sidecar-{spec_id}",
            label="C-C sidecar allocation replay",
        )
        allocation_entry = _read_regular_at(
            sidecar_fd,
            "allocation.json",
            label="C-C allocation primary",
            exact_mode=0o400,
            exact_nlink=2,
        )
        release_entry = _read_regular_at(
            sidecar_fd,
            "release.json",
            label="C-C release primary",
            exact_mode=0o400,
            exact_nlink=2,
        )
        if allocation_entry is None or release_entry is None:
            _fail("C-C conservative result lacks durable allocation/release")
        allocation, replayed_allocation_id = _parse_c_c_artifact(
            allocation_entry[0],
            id_field="h1_owner_cleanup_sidecar_allocation_id",
            domain=sidecar_v1.ALLOCATION_DOMAIN,
            label="C-C allocation",
        )
        release, replayed_release_id = _parse_c_c_artifact(
            release_entry[0],
            id_field="h1_owner_cleanup_release_id",
            domain=sidecar_v1.RELEASE_DOMAIN,
            label="C-C release",
        )
        allocation_seal = f"allocation-seal-{runtime_id}-{reservation_id}.json"
        release_seal = f"release-seal-{runtime_id}-{reservation_id}.json"
        _verify_two_link_immutable_pair(
            sidecar_fd,
            "allocation.json",
            root_fd,
            allocation_seal,
            expected_raw=allocation_entry[0],
            label="C-C allocation",
        )
        _verify_two_link_immutable_pair(
            sidecar_fd,
            "release.json",
            root_fd,
            release_seal,
            expected_raw=release_entry[0],
            label="C-C release",
        )
        allocation_payload = dict(allocation)
        allocation_payload.pop("h1_owner_cleanup_sidecar_allocation_id")
        release_payload = dict(release)
        release_payload.pop("h1_owner_cleanup_release_id")
        root_lock = _read_regular_at(
            root_fd,
            "allocation.lock",
            label="C-C root allocation lock",
            exact_mode=0o600,
            exact_nlink=1,
        )
        root_stat = os.fstat(root_fd)
        sidecar_stat = os.fstat(sidecar_fd)
        exact = action["exact_c_b_action"]
        if (
            replayed_allocation_id != allocation_id
            or replayed_release_id != release_id
            or root_lock is None
            or allocation_payload.get("h1_owner_cleanup_sidecar_spec_id")
            != spec_id
            or allocation_payload.get("h1_shared_cap_owner_v3_runtime_id")
            != runtime_id
            or allocation_payload.get("h1_shared_cap_owner_v3_reservation_id")
            != reservation_id
            or (
                allocation_payload.get("sidecar_root_device"),
                allocation_payload.get("sidecar_root_inode"),
            )
            != (root_stat.st_dev, root_stat.st_ino)
            or (
                allocation_payload.get("sidecar_directory_device"),
                allocation_payload.get("sidecar_directory_inode"),
            )
            != (sidecar_stat.st_dev, sidecar_stat.st_ino)
            or (
                allocation_payload.get("root_allocation_lock_device"),
                allocation_payload.get("root_allocation_lock_inode"),
            )
            != (root_lock[1].st_dev, root_lock[1].st_ino)
            or release_payload.get("h1_owner_cleanup_sidecar_spec_id") != spec_id
            or release_payload.get("h1_owner_cleanup_sidecar_allocation_id")
            != allocation_id
            or release_payload.get("h1_attempt_cleanup_transition_v2_id")
            != handle.manifest.payload["h1_attempt_cleanup_transition_v2_id"]
            or release_payload.get("h1_preadmitted_cleanup_envelope_id")
            != handle.manifest.payload["h1_preadmitted_cleanup_envelope_id"]
            or release_payload.get("h1_lifecycle_cleanup_pass_id")
            != handle.manifest.payload["h1_lifecycle_cleanup_pass_id"]
            or release_payload.get("cleanup_action_ordinal")
            != action["cleanup_ordinal"]
            or release_payload.get("cleanup_action_kind") != exact["action_kind"]
            or release_payload.get("cleanup_action_target") != exact["target"]
            or release_payload.get("h1_shared_cap_owner_v3_runtime_id")
            != runtime_id
            or release_payload.get("h1_shared_cap_owner_v3_reservation_id")
            != reservation_id
        ):
            _fail("C-C allocation/release crossed the exact E2 action")
        if any(
            release_payload.get(key) is not expected
            for key, expected in (
                ("native_effect_started", False),
                ("memory_read_performed", False),
                ("output_finalize_performed", False),
                ("outstanding_released", True),
                ("single_spend", True),
                ("conservative_charge", True),
                ("v3_owner_record_appended", False),
                ("v4_wal_payload_appended", False),
            )
        ):
            _fail("C-C durable release semantics changed")
        path = release_payload.get("path")
        v3_charged = combined.get("v3_charged_values")
        v3_outstanding = combined.get("v3_outstanding_values")
        expected_charged = dict(v3_charged) if type(v3_charged) is dict else None
        expected_outstanding = (
            dict(v3_outstanding) if type(v3_outstanding) is dict else None
        )
        if expected_charged is not None:
            expected_charged[path] = release_payload.get("charged_after")
        if expected_outstanding is not None:
            expected_outstanding[path] = release_payload.get("outstanding_after")
        if (
            combined.get("h1_owner_cleanup_sidecar_spec_id") != spec_id
            or combined.get("h1_owner_cleanup_sidecar_allocation_id")
            != allocation_id
            or combined.get("h1_owner_cleanup_release_id") != release_id
            or combined.get("released_reservation_id") != reservation_id
            or combined.get("released_path") != path
            or combined.get("released_value")
            != release_payload.get("reservation_upper")
            or combined.get("combined_charged_values") != expected_charged
            or combined.get("combined_outstanding_values") != expected_outstanding
            or combined.get("sidecar_release_count") != 1
            or combined.get("sidecar_single_spend_verified") is not True
            or combined.get("native_effect_started") is not False
            or combined.get("memory_read_performed") is not False
            or combined.get("output_finalize_performed") is not False
        ):
            _fail("C-C embedded combined state differs from durable release")
        final_root = os.stat(
            ".acfqp-k7-h1-owner-cleanup-sidecars-v1",
            dir_fd=handle.base_fd,
            follow_symlinks=False,
        )
        final_sidecar = os.stat(
            f"sidecar-{spec_id}", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            (final_root.st_dev, final_root.st_ino)
            != (root_stat.st_dev, root_stat.st_ino)
            or (final_sidecar.st_dev, final_sidecar.st_ino)
            != (sidecar_stat.st_dev, sidecar_stat.st_ino)
        ):
            _fail("C-C sidecar directory mapping changed during replay")
    finally:
        if sidecar_fd >= 0:
            os.close(sidecar_fd)
        if root_fd >= 0:
            os.close(root_fd)


def _validate_pidfd_preobservation(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    preobs: Mapping[str, Any],
) -> None:
    if action["exact_c_b_action"]["action_kind"] != "REAP_DESCENDANT":
        _fail("non-REAP cleanup action carried a PIDFD preobservation")
    join = _join_for_target(handle.manifest, action["exact_c_b_action"]["target"])
    if (
        join is None
        or join["e2_join_disposition"] != "PRESENT_LIVE"
        or join["capability_kind"] != "PIDFD"
    ):
        _fail("PIDFD preobservation lacks an exact live PIDFD cutoff join")
    observed = _exact_keys(
        preobs.get("preobservation"),
        {
            "waitable_child_provenance_verified",
            "child_exit_observed",
            "waitid_wnowait",
            "signal_sent",
            "guarded_callback_slot_waitable_child_only",
            "business_or_worker_role_identity_proven",
        },
        "PIDFD EXITED preobservation",
    )
    if (
        observed["waitable_child_provenance_verified"] is not True
        or observed["child_exit_observed"] is not True
        or observed["signal_sent"] is not False
        or observed["guarded_callback_slot_waitable_child_only"] is not True
        or observed["business_or_worker_role_identity_proven"] is not False
    ):
        _fail("PIDFD EXITED preobservation overclaims provenance or effect")
    _waitid_evidence(observed["waitid_wnowait"], "PIDFD WNOWAIT")
    expected = _build_pidfd_preobservation(
        handle, action, intent, join, observed
    )
    if dict(preobs) != expected:
        _fail("PIDFD preobservation crossed its action or durable evidence")


def _validate_result_outcome(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    preobs: Mapping[str, Any] | None,
    result: Mapping[str, Any],
    *,
    verify_external: bool,
) -> None:
    kind = action["exact_c_b_action"]["action_kind"]
    outcome = result["outcome"]
    evidence = result["effect_evidence"]
    join, disposition = _classify_native_action(handle.manifest, action)
    if kind != "REAP_DESCENDANT" and preobs is not None:
        _fail("only REAP may consume a PIDFD preobservation")
    if kind == "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION":
        expected_outcome, expected_evidence = _resolution_result(
            handle.manifest, action
        )
        if outcome != expected_outcome or evidence != expected_evidence:
            _fail("RESOLVE result differs from the frozen cutoff join")
        return
    if kind in _CONSERVATIVE_ACTIONS:
        row = _exact_keys(
            evidence,
            {
                "h1_shared_cap_owner_v3_reservation_id",
                "h1_owner_cleanup_sidecar_spec_id",
                "h1_owner_cleanup_sidecar_allocation_id",
                "h1_owner_cleanup_release_id",
                "h1_owner_cleanup_combined_state_id",
                "owner_cleanup_combined_state",
                "native_effect_started",
                "memory_read_performed",
                "output_finalize_performed",
                "c_d_budget_unit_is_not_owner_charged_value",
            },
            "Owner conservative release",
        )
        for key in (
            "h1_shared_cap_owner_v3_reservation_id",
            "h1_owner_cleanup_sidecar_spec_id",
            "h1_owner_cleanup_sidecar_allocation_id",
            "h1_owner_cleanup_release_id",
            "h1_owner_cleanup_combined_state_id",
        ):
            _cid(row[key], f"Owner release {key}")
        if (
            outcome != "OWNER_CONSERVATIVE_RELEASED"
            or row["native_effect_started"] is not False
            or row["memory_read_performed"] is not False
            or row["output_finalize_performed"] is not False
            or row["c_d_budget_unit_is_not_owner_charged_value"] is not True
        ):
            _fail("Owner conservative release result overclaims work")
        if verify_external:
            _verify_owner_release_durable(handle, action, row)
        return
    if kind == "CLOSE_MOUNT":
        if disposition in {"ABSENT_EXPLICIT", "ABSENT_CONTROL_FLOW"}:
            expected = {
                "cutoff_join_disposition": disposition,
                "native_close_performed": False,
            }
            if outcome != "SKIPPED_KNOWN_ABSENT" or evidence != expected:
                _fail("known-absent mount close result changed")
            return
        if disposition != "PRESENT_LIVE" or join is None:
            expected = {
                "cutoff_join_disposition": disposition,
                "native_close_performed": False,
                "callback_replayed": False,
            }
            if outcome != "BLOCKED_UNRESOLVED" or evidence != expected:
                _fail("unresolved mount close result changed")
            return
        if join["capability_kind"] != "OFD":
            if outcome != "NATIVE_EFFECT_FAILED" or evidence != {
                "reason": "MOUNT_CLOSE_SLOT_IS_NOT_AN_OFD",
                "native_close_performed": False,
            }:
                _fail("wrong-kind mount close result changed")
            return
        row = _exact_keys(
            evidence,
            {
                "slot_key",
                "guardian_alias_set_closed",
                "alias_close_status",
                "reconciled_same_broker_consumed_state",
                "underlying_ofd_last_reference_release_proven",
                "mount_resource_release_proven",
                "external_same_ofd_alias_absence_proven",
            },
            "Guardian alias close",
        )
        if (
            outcome != "GUARDIAN_ALIAS_SET_CLOSED"
            or row["slot_key"] != join["slot_key"]
            or row["guardian_alias_set_closed"] is not True
            or row["alias_close_status"]
            not in {
                "GUARDIAN_MASTER_WITNESS_ANCHOR_CLOSED",
                "RECONCILED_SAME_BROKER_CONSUMED_STATE",
            }
            or row["underlying_ofd_last_reference_release_proven"] is not False
            or row["mount_resource_release_proven"] is not False
            or row["external_same_ofd_alias_absence_proven"] is not False
        ):
            _fail("Guardian alias close result exceeded its narrow effect")
        attestation = _require_native_effect_attestation(
            handle,
            intent,
            effect_kind="GUARDIAN_OFD_ALIAS_SET_CLOSED",
            slot_key=join["slot_key"],
        )
        if (
            attestation.get("underlying_ofd_last_reference_release_proven")
            is not False
            or attestation.get("mount_resource_release_proven") is not False
        ):
            _fail("Guardian alias attestation exceeded its narrow effect")
        return
    if kind != "REAP_DESCENDANT":
        _fail("cleanup result action kind has no semantic verifier")
    if disposition in {"ABSENT_EXPLICIT", "ABSENT_CONTROL_FLOW"}:
        expected = {
            "cutoff_join_disposition": disposition,
            "pidfd_waitid_reap_performed": False,
            "pidfd_close_alone_counted_as_reap": False,
        }
        if outcome != "SKIPPED_KNOWN_ABSENT" or evidence != expected:
            _fail("known-absent REAP result changed")
        return
    if disposition != "PRESENT_LIVE" or join is None:
        expected = {
            "cutoff_join_disposition": disposition,
            "pidfd_waitid_reap_performed": False,
            "callback_replayed": False,
        }
        if outcome != "BLOCKED_UNRESOLVED" or evidence != expected:
            _fail("unresolved REAP result changed")
        return
    if join["capability_kind"] != "PIDFD":
        if outcome != "NATIVE_EFFECT_FAILED" or evidence != {
            "reason": "DESCENDANT_REAP_SLOT_IS_NOT_PIDFD",
            "pidfd_waitid_reap_performed": False,
        }:
            _fail("wrong-kind REAP result changed")
        return
    if outcome == "PIDFD_REAPED":
        if preobs is None:
            _fail("PIDFD_REAPED lacks exact durable EXITED preobservation")
        if evidence.get("pidfd_waitid_reap_performed") is not True:
            _fail("PIDFD_REAPED did not record the consuming waitid")
        if evidence.get("pidfd_close_alone_counted_as_reap") is not False:
            _fail("PIDFD close was incorrectly counted as reap")
        if evidence.get("business_or_worker_role_identity_proven") is not False:
            _fail("PIDFD result overclaims BUSINESS/WORKER identity")
        if evidence.get("guarded_callback_slot_waitable_child_only") is not True:
            _fail("PIDFD result lost its guarded callback-slot scope")
        attestation = _require_native_effect_attestation(
            handle,
            intent,
            effect_kind="PIDFD_WAITID_REAPED",
            slot_key=join["slot_key"],
            pidfd_preobservation_id=preobs[
                "h1_cleanup_pidfd_preobservation_id"
            ],
        )
        if (
            attestation.get("waitid_wnowait")
            != preobs["preobservation"]["waitid_wnowait"]
            or attestation.get("guarded_callback_slot_waitable_child_only")
            is not True
            or attestation.get("business_or_worker_role_identity_proven")
            is not False
        ):
            _fail("PIDFD effect attestation differs from durable preobservation")
        allowed_keys = (
            {
                "waitid_result",
                "pidfd_waitid_reap_performed",
                "pidfd_alias_set_closed",
                "alias_close_status",
                "pidfd_close_alone_counted_as_reap",
                "signal_sent",
                "guarded_callback_slot_waitable_child_only",
                "business_or_worker_role_identity_proven",
            },
            {
                "reconciled_same_broker_consumed_state",
                "pidfd_waitid_reap_performed",
                "pidfd_alias_set_closed",
                "pidfd_close_alone_counted_as_reap",
                "guarded_callback_slot_waitable_child_only",
                "business_or_worker_role_identity_proven",
            },
        )
        if type(evidence) is not dict or set(evidence) not in allowed_keys:
            _fail("PIDFD_REAPED evidence schema changed")
        if "waitid_result" in evidence:
            consuming = _waitid_evidence(
                evidence["waitid_result"], "PIDFD consuming waitid"
            )
            observed = preobs["preobservation"]["waitid_wnowait"]
            if dict(consuming) != observed:
                _fail("PIDFD consuming waitid differs from durable EXITED preobservation")
            if (
                evidence["pidfd_alias_set_closed"] is not True
                or evidence["signal_sent"] is not False
                or evidence["alias_close_status"]
                not in {
                    "GUARDIAN_MASTER_WITNESS_ANCHOR_CLOSED",
                    "RECONCILED_SAME_BROKER_CONSUMED_STATE",
                }
            ):
                _fail("PIDFD consuming waitid evidence changed")
        elif (
            evidence["reconciled_same_broker_consumed_state"] is not True
            or evidence["pidfd_alias_set_closed"] is not True
        ):
            _fail("PIDFD same-broker reconciliation evidence changed")
        return
    if preobs is not None and outcome not in {
        "PIDFD_REAP_UNCERTAIN",
        "NATIVE_EFFECT_FAILED",
    }:
        _fail("durable EXITED PIDFD preobservation has an invalid result")
    if preobs is None and outcome not in {"PIDFD_NOT_EXITED", "BLOCKED_UNRESOLVED"}:
        _fail("PIDFD result without EXITED preobservation is invalid")
    if preobs is None and outcome == "PIDFD_NOT_EXITED":
        row = _exact_keys(
            evidence,
            {
                "pidfd_preobservation_status",
                "waitable_child_provenance_verified",
                "child_exit_observed",
                "signal_sent",
                "guarded_callback_slot_waitable_child_only",
                "business_or_worker_role_identity_proven",
            },
            "PIDFD NOT_EXITED",
        )
        if (
            row["pidfd_preobservation_status"] != "NOT_EXITED"
            or row["waitable_child_provenance_verified"] is not True
            or row["child_exit_observed"] is not False
            or row["signal_sent"] is not False
            or row["guarded_callback_slot_waitable_child_only"] is not True
            or row["business_or_worker_role_identity_proven"] is not False
        ):
            _fail("PIDFD NOT_EXITED evidence changed")
    elif preobs is None:
        if (
            type(evidence) is not dict
            or evidence.get("pidfd_preobservation_status")
            not in {"UNSUPPORTED", "UNRESOLVED", "UNVERIFIED"}
            or type(evidence.get("reason")) is not str
            or set(evidence)
            not in (
                {"pidfd_preobservation_status", "reason"},
                {"pidfd_preobservation_status", "reason", "errno"},
            )
        ):
            _fail("blocked PIDFD preobservation evidence changed")
    elif outcome == "PIDFD_REAP_UNCERTAIN":
        if (
            type(evidence) is not dict
            or type(evidence.get("reason")) is not str
            or set(evidence)
            not in ({"reason"}, {"reason", "pidfd_close_alone_counted_as_reap"})
            or evidence.get("pidfd_close_alone_counted_as_reap", False) is not False
        ):
            _fail("PIDFD uncertain reap evidence changed")
    elif outcome == "NATIVE_EFFECT_FAILED":
        row = _exact_keys(
            evidence,
            {"reason", "errno", "pidfd_close_alone_counted_as_reap"},
            "PIDFD failed reap",
        )
        if (
            type(row["reason"]) is not str
            or type(row["errno"]) is not int
            or row["pidfd_close_alone_counted_as_reap"] is not False
        ):
            _fail("PIDFD failed reap evidence changed")


def _state_summary(
    handle: H1CleanupActionJournalHandleV1,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    results = [
        row
        for row in records
        if row["schema"] == "acfqp.k7_h1_cleanup_action_result.v1"
    ]
    intents = [
        row
        for row in records
        if row["schema"] == "acfqp.k7_h1_cleanup_action_intent.v1"
    ]
    consumed = {key: 0 for key in _CATEGORY_ORDER}
    for row in intents:
        consumed[row["budget_category"]] += 1
    action_count = handle.manifest.payload["action_count"]
    unresolved = sum(
        row["outcome"]
        in {
            "BLOCKED_UNRESOLVED",
            "PIDFD_NOT_EXITED",
            "PIDFD_REAP_UNCERTAIN",
            "NATIVE_EFFECT_FAILED",
            "NATIVE_EFFECT_UNCERTAIN",
            "GUARDIAN_ALIAS_SET_CLOSED",
        }
        for row in results
    )
    return {
        "record_count": len(records),
        "intent_count": len(intents),
        "result_count": len(results),
        "next_cleanup_ordinal": len(results) + 1,
        "budget_consumed": consumed,
        "drained": len(results) == action_count,
        "drained_with_unresolved_or_partial_effect": (
            len(results) == action_count and unresolved > 0
        ),
        "unresolved_or_partial_result_count": unresolved,
        "last_result_id": (
            results[-1]["h1_cleanup_action_result_id"]
            if results
            else _typed_null("NO_PREVIOUS_ACTION_RESULT")
        ),
    }


def _append_record_locked(
    handle: H1CleanupActionJournalHandleV1,
    attempt_fd: int,
    cursor_fd: int,
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    document: dict[str, Any],
    *,
    crash_after_file: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kind, _field, record_id = _record_identity(document)
    sequence = len(records) + 1
    name = f"record-{sequence:04d}-{kind}-{record_id}.json"
    _publish_immutable_at(
        attempt_fd,
        name,
        canonical_json_bytes(document),
        label=f"E2 cleanup {kind} record",
    )
    if crash_after_file:
        raise H1CleanupActionJournalInjectedCrashV1(
            f"cleanup action journal crash after {kind} file fsync"
        )
    rows = _append_cursor(
        cursor_fd, rows, record_kind=kind, record_id=record_id
    )
    records = [*records, document]
    _validate_record_semantics(handle, records, verify_external=False)
    return records, rows


def _next_action_context(
    handle: H1CleanupActionJournalHandleV1,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    actions = handle.manifest.payload["actions"]
    results = [
        row
        for row in records
        if row["schema"] == "acfqp.k7_h1_cleanup_action_result.v1"
    ]
    if len(results) == len(actions):
        return None, None, None
    action = actions[len(results)]
    intent = next(
        (
            row
            for row in records
            if row.get("schema") == "acfqp.k7_h1_cleanup_action_intent.v1"
            and row.get("cleanup_ordinal") == action["cleanup_ordinal"]
        ),
        None,
    )
    preobs = next(
        (
            row
            for row in records
            if row.get("schema")
            == "acfqp.k7_h1_cleanup_pidfd_preobservation.v1"
            and intent is not None
            and row.get("h1_cleanup_action_intent_id")
            == intent["h1_cleanup_action_intent_id"]
        ),
        None,
    )
    return action, intent, preobs


def _build_intent(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    exact = action["exact_c_b_action"]
    before = dict(summary["budget_consumed"])
    after = dict(before)
    category = action["budget_category"]
    after[category] += 1
    selected = handle.manifest.payload["selected_branch_budget"]
    available = handle.manifest.payload["available_cleanup_budget"]
    if after[category] > selected[category] or after[category] > available[category]:
        _fail("cleanup action would overspend its selected C-D component")
    payload = {
        "schema": "acfqp.k7_h1_cleanup_action_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_cleanup_action_manifest_id": handle.manifest.manifest_id,
        "h1_cleanup_action_journal_allocation_id": handle.allocation_id,
        "h1_attempt_cleanup_transition_v2_id": handle.manifest.payload[
            "h1_attempt_cleanup_transition_v2_id"
        ],
        "primary_failure_event_id": handle.manifest.payload[
            "primary_failure_event_id"
        ],
        "h1_cleanup_action_definition_id": action[
            "h1_cleanup_action_definition_id"
        ],
        "cleanup_ordinal": action["cleanup_ordinal"],
        "action_kind": exact["action_kind"],
        "target": exact["target"],
        "budget_category": category,
        "budget_units": 1,
        "budget_before": before,
        "budget_after": after,
        "previous_action_result_id": summary["last_result_id"],
        "intent_durable_before_native_effect": True,
        "primary_failure_preserved": True,
        "secondary_failure_is_append_only": True,
        "normal_route_reopened": False,
        "formal_counter_records_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_cleanup_action_intent_id": _content_id(INTENT_DOMAIN, payload),
    }


def _build_result(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    *,
    outcome: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_cleanup_action_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_cleanup_action_manifest_id": handle.manifest.manifest_id,
        "h1_cleanup_action_journal_allocation_id": handle.allocation_id,
        "h1_cleanup_action_definition_id": action[
            "h1_cleanup_action_definition_id"
        ],
        "h1_cleanup_action_intent_id": intent[
            "h1_cleanup_action_intent_id"
        ],
        "cleanup_ordinal": action["cleanup_ordinal"],
        "action_kind": action["exact_c_b_action"]["action_kind"],
        "target": action["exact_c_b_action"]["target"],
        "outcome": outcome,
        "effect_evidence": dict(evidence),
        "budget_debit_retained_after_result": True,
        "primary_failure_preserved": True,
        "secondary_failure_is_append_only": True,
        "continue_with_later_safe_cleanup": True,
        "normal_ordinal_success_event_issued": False,
        "underlying_ofd_last_reference_release_proven": False,
        "mount_resource_release_proven": False,
        "production_output_leaf_authority_present": False,
        "current_access_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_cleanup_action_result_id": _content_id(RESULT_DOMAIN, payload),
    }


def _join_for_target(
    manifest: H1CleanupActionManifestV1,
    target: str,
) -> dict[str, Any] | None:
    if target in {"BUSINESS", "WORKER"}:
        site = f"launch:{target}"
    else:
        site = target
    rows = [
        row
        for row in manifest.payload["cleanup_cutoff_join"]["slot_joins"]
        if row["slot_key"].endswith(f":{site}")
    ]
    if len(rows) > 1:
        _fail("cleanup target maps to duplicate native slots")
    return rows[0] if rows else None


def _resolution_result(
    manifest: H1CleanupActionManifestV1,
    action: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    target = action["exact_c_b_action"]["target"]
    join = _join_for_target(manifest, target)
    if join is None:
        return "BLOCKED_UNRESOLVED", {
            "reason": "NO_REGISTERED_V6_E1_SLOT_FOR_RESOLUTION_TARGET"
        }
    disposition = join["e2_join_disposition"]
    if disposition == "PRESENT_LIVE":
        outcome = "RESOLUTION_PRESENT_LIVE"
    elif disposition == "ABSENT_EXPLICIT":
        outcome = "RESOLUTION_ABSENT_EXPLICIT"
    elif disposition == "ABSENT_CONTROL_FLOW":
        outcome = "RESOLUTION_ABSENT_CONTROL_FLOW"
    else:
        outcome = "BLOCKED_UNRESOLVED"
    return outcome, {
        "slot_key": join["slot_key"],
        "cutoff_join_disposition": disposition,
        "h1_native_capability_guardian_binding_id": join[
            "h1_native_capability_guardian_binding_id"
        ],
        "native_callback_replayed": False,
    }


def _require_execution_context(
    handle: H1CleanupActionJournalHandleV1,
    *,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
) -> cleanup_v1.H1LifecycleCleanupPassV1:
    _require_cleanup_lease(cleanup_lease, transition)
    _require_broker_guardian(guardian)
    if type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle:
        _fail("E2 execution requires one exact V4 Owner")
    manifest = handle.manifest.payload
    guardian_snapshot = guardian_v1.snapshot_h1_native_capability_guardian_v1(
        guardian
    )
    if (
        transition.transition_id != manifest["h1_attempt_cleanup_transition_v2_id"]
        or envelope.envelope_id != manifest["h1_preadmitted_cleanup_envelope_id"]
        or cleanup_analysis.analysis_id
        != manifest["h1_lifecycle_complete_branch_analysis_id"]
        or native_receipt_handle.allocation_id
        != manifest["h1_native_receipt_allocation_id"]
        or guardian.spec.spec_id
        != manifest["h1_native_capability_guardian_spec_id"]
        or guardian_snapshot.get("h1_native_capability_guardian_init_marker_id")
        != manifest["h1_native_capability_guardian_init_marker_id"]
        or guardian._native_handle is not native_receipt_handle
        or owner.runtime_id != transition.payload["h1_shared_cap_owner_v3_runtime_id"]
        or owner.binding_id != transition.payload["h1_shared_cap_owner_v4_wal_binding_id"]
    ):
        _fail("E2 execution objects crossed the frozen action manifest")
    replay = receipts_v1.replay_h1_native_receipt_journal_v1(
        native_receipt_handle
    )
    if replay["cutoff_snapshot_id"] != manifest["h1_native_cutoff_snapshot_id"]:
        _fail("E2 V6 cutoff changed after manifest freeze")
    cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
        cleanup_analysis, branch_key=manifest["branch_key"]
    )
    if cleanup_pass.pass_id != manifest["h1_lifecycle_cleanup_pass_id"]:
        _fail("E2 selected cleanup pass changed")
    return cleanup_pass


def _current_guardian_slot(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    join: Mapping[str, Any],
) -> tuple[Any, Any]:
    key = join["slot_key"]
    state = guardian._slot_states.get(key)
    if state is None:
        _fail("E2 Guardian lost its registered native slot")
    return state, state.cell


def _close_guardian_alias_set(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    join: Mapping[str, Any],
    *,
    intent_id: str,
    marker_kind: str,
) -> tuple[bool, str]:
    marker = f"E2_{marker_kind}:{intent_id}"
    with guardian_v1._REGISTRY_LOCK:
        state, cell = _current_guardian_slot(guardian, join)
        if state.unresolved_reason == marker and state.cell is None:
            return True, "RECONCILED_SAME_BROKER_CONSUMED_STATE"
        binding = state.binding_document
        if (
            state.status
            is not guardian_v1.H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
            or cell is None
            or binding is None
            or binding.get("h1_native_capability_guardian_binding_id")
            != join["h1_native_capability_guardian_binding_id"]
        ):
            _fail("E2 live cleanup token lost its exact Guardian binding")
        guardian_v1._verify_live_cell_locked(guardian, cell)
        anchor = guardian_v1._ANCHOR_FDS.pop(
            (guardian._registry_key, cell.slot_key), -1
        )
        if anchor < 0:
            _fail("E2 Guardian live cell lost its anchor alias")
        guardian_v1._close_fd_quietly(anchor)
        cell._close_master_witness()
        state.cell = None
        # Invalidate every old H1GuardedNativeBindingV1 token.  The immutable
        # V6 receipt remains present, but it no longer confers live authority.
        state.binding_document = None
        state.status = guardian_v1.H1NativeCapabilityGuardianStatusV1.UNRESOLVED
        state.unresolved_reason = marker
        return False, "GUARDIAN_MASTER_WITNESS_ANCHOR_CLOSED"


def _pidfd_info_document(value: Any) -> dict[str, int]:
    return {
        "si_pid": int(value.si_pid),
        "si_uid": int(value.si_uid),
        "si_signo": int(value.si_signo),
        "si_status": int(value.si_status),
        "si_code": int(value.si_code),
    }


def _pidfd_preobserve(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    join: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    if not hasattr(os, "P_PIDFD") or not hasattr(os, "waitid"):
        return "UNSUPPORTED", {"reason": "P_PIDFD_WAITID_UNSUPPORTED"}
    with guardian_v1._REGISTRY_LOCK:
        state, cell = _current_guardian_slot(guardian, join)
        if (
            state.status
            is not guardian_v1.H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
            or cell is None
            or cell.kind is not receipts_v1.H1NativeCapabilityKindV1.PIDFD
        ):
            return "UNRESOLVED", {"reason": "PIDFD_LIVE_BINDING_UNAVAILABLE"}
        guardian_v1._verify_live_cell_locked(guardian, cell)
        try:
            result = os.waitid(
                os.P_PIDFD,
                cell._master_fd,
                os.WEXITED | os.WNOHANG | os.WNOWAIT,
            )
        except ChildProcessError:
            return "UNVERIFIED", {
                "reason": "PIDFD_IS_NOT_A_WAITABLE_CHILD_OF_THIS_BROKER"
            }
        except OSError as error:
            return "UNVERIFIED", {
                "reason": "PIDFD_WAITID_PREOBSERVATION_FAILED",
                "errno": error.errno,
            }
    if result is None:
        return "NOT_EXITED", {
            "waitable_child_provenance_verified": True,
            "child_exit_observed": False,
            "signal_sent": False,
            "guarded_callback_slot_waitable_child_only": True,
            "business_or_worker_role_identity_proven": False,
        }
    return "EXITED", {
        "waitable_child_provenance_verified": True,
        "child_exit_observed": True,
        "waitid_wnowait": _pidfd_info_document(result),
        "signal_sent": False,
        "guarded_callback_slot_waitable_child_only": True,
        "business_or_worker_role_identity_proven": False,
    }


def _build_pidfd_preobservation(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    join: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_cleanup_pidfd_preobservation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_cleanup_action_manifest_id": handle.manifest.manifest_id,
        "h1_cleanup_action_journal_allocation_id": handle.allocation_id,
        "h1_cleanup_action_definition_id": action[
            "h1_cleanup_action_definition_id"
        ],
        "h1_cleanup_action_intent_id": intent[
            "h1_cleanup_action_intent_id"
        ],
        "cleanup_ordinal": action["cleanup_ordinal"],
        "slot_key": join["slot_key"],
        "h1_native_capability_guardian_binding_id": join[
            "h1_native_capability_guardian_binding_id"
        ],
        "preobservation": dict(evidence),
        "waitid_wnowait_only": True,
        "descendant_reaped_by_preobservation": False,
        "raw_pidfd_serialized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_cleanup_pidfd_preobservation_id": _content_id(
            PREOBS_DOMAIN, payload
        ),
    }


def _reap_pidfd_after_preobservation(
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    join: Mapping[str, Any],
    *,
    intent_id: str,
) -> tuple[str, dict[str, Any]]:
    marker = f"E2_PIDFD_REAPED_AND_ALIASES_CLOSED:{intent_id}"
    with guardian_v1._REGISTRY_LOCK:
        state, cell = _current_guardian_slot(guardian, join)
        if state.unresolved_reason == marker and state.cell is None:
            return "PIDFD_REAPED", {
                "reconciled_same_broker_consumed_state": True,
                "pidfd_waitid_reap_performed": True,
                "pidfd_alias_set_closed": True,
                "pidfd_close_alone_counted_as_reap": False,
                "guarded_callback_slot_waitable_child_only": True,
                "business_or_worker_role_identity_proven": False,
            }
        binding = state.binding_document
        if (
            state.status
            is not guardian_v1.H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
            or cell is None
            or cell.kind is not receipts_v1.H1NativeCapabilityKindV1.PIDFD
            or binding is None
            or binding.get("h1_native_capability_guardian_binding_id")
            != join["h1_native_capability_guardian_binding_id"]
        ):
            return "PIDFD_REAP_UNCERTAIN", {
                "reason": "PIDFD_LIVE_STATE_LOST_AFTER_DURABLE_PREOBSERVATION"
            }
        guardian_v1._verify_live_cell_locked(guardian, cell)
        try:
            waited = os.waitid(
                os.P_PIDFD, cell._master_fd, os.WEXITED | os.WNOHANG
            )
        except ChildProcessError:
            return "PIDFD_REAP_UNCERTAIN", {
                "reason": "WAITABLE_CHILD_WAS_REAPED_OUTSIDE_E2",
                "pidfd_close_alone_counted_as_reap": False,
            }
        except OSError as error:
            return "NATIVE_EFFECT_FAILED", {
                "reason": "PIDFD_WAITID_REAP_FAILED",
                "errno": error.errno,
                "pidfd_close_alone_counted_as_reap": False,
            }
        if waited is None:
            return "PIDFD_REAP_UNCERTAIN", {
                "reason": "PIDFD_EXIT_PREOBSERVATION_NO_LONGER_REAPABLE",
                "pidfd_close_alone_counted_as_reap": False,
            }
        # The consuming waitid legitimately changes the pidfd fdinfo.  The
        # exact cell and binding were verified above and the Guardian registry
        # lock has remained held throughout the wait, so close that same alias
        # set directly.  Re-entering the generic OFD close verifier here would
        # compare post-wait fdinfo with its pre-wait fingerprint and reject the
        # successful reap as a provenance crossing.
        anchor = guardian_v1._ANCHOR_FDS.pop(
            (guardian._registry_key, cell.slot_key), -1
        )
        if anchor < 0:
            _fail("E2 Guardian live PIDFD cell lost its anchor alias")
        guardian_v1._close_fd_quietly(anchor)
        cell._close_master_witness()
        state.cell = None
        state.binding_document = None
        state.status = guardian_v1.H1NativeCapabilityGuardianStatusV1.UNRESOLVED
        state.unresolved_reason = marker
        alias_status = "GUARDIAN_MASTER_WITNESS_ANCHOR_CLOSED"
    return "PIDFD_REAPED", {
        "waitid_result": _pidfd_info_document(waited),
        "pidfd_waitid_reap_performed": True,
        "pidfd_alias_set_closed": True,
        "alias_close_status": alias_status,
        "pidfd_close_alone_counted_as_reap": False,
        "signal_sent": False,
        "guarded_callback_slot_waitable_child_only": True,
        "business_or_worker_role_identity_proven": False,
    }


def _unique_owner_reservation_id(
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    action: Mapping[str, Any],
) -> str:
    root_fd = directory_fd = -1
    try:
        root_fd, directory_fd, state, _join = sidecar_v1._validate_owner_cutoff_locked(
            cleanup_lease, owner, transition.payload
        )
        expected_site, expected_path = sidecar_v1._SUPPORTED_ACTIONS[
            action["action_kind"]
        ]
        candidates = [
            reservation_id
            for reservation_id, reservation in state.reservations.items()
            if reservation.get("record_kind") == "RESERVATION_DURABLE"
            and reservation.get("admission_outcome") == "ADMITTED"
            and reservation.get("site_key") == expected_site
            and reservation.get("path") == expected_path
            and reservation_id not in state.cells
            and reservation_id not in state.evidence
            and reservation_id not in state.settlements
        ]
        if len(candidates) != 1:
            _fail("E2 could not select one exact outstanding Owner reservation")
        return _cid(candidates[0], "E2 Owner reservation")
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if root_fd >= 0:
            os.close(root_fd)


def _conservative_owner_release(
    *,
    handle: H1CleanupActionJournalHandleV1,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    reservation_id = _unique_owner_reservation_id(
        cleanup_lease, owner, transition, action
    )
    sidecar = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
        handle.base_directory,
        cleanup_lease=cleanup_lease,
        owner=owner,
        transition=transition,
        envelope=envelope,
        cleanup_pass=cleanup_pass,
        action=action,
        reservation_id=reservation_id,
    )
    release = sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
        sidecar,
        cleanup_lease=cleanup_lease,
        owner=owner,
        transition=transition,
        envelope=envelope,
        cleanup_pass=cleanup_pass,
        action=action,
    )
    combined = sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
        sidecar,
        cleanup_lease=cleanup_lease,
        owner=owner,
        transition=transition,
        envelope=envelope,
        cleanup_pass=cleanup_pass,
        action=action,
    )
    return "OWNER_CONSERVATIVE_RELEASED", {
        "h1_shared_cap_owner_v3_reservation_id": reservation_id,
        "h1_owner_cleanup_sidecar_spec_id": sidecar.spec.spec_id,
        "h1_owner_cleanup_sidecar_allocation_id": sidecar.allocation_id,
        "h1_owner_cleanup_release_id": release.release_id,
        "h1_owner_cleanup_combined_state_id": combined[
            "h1_owner_cleanup_combined_state_id"
        ],
        "owner_cleanup_combined_state": dict(combined),
        "native_effect_started": False,
        "memory_read_performed": False,
        "output_finalize_performed": False,
        "c_d_budget_unit_is_not_owner_charged_value": True,
    }


def _classify_native_action(
    manifest: H1CleanupActionManifestV1,
    action: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    target = action["exact_c_b_action"]["target"]
    join = _join_for_target(manifest, target)
    if join is None:
        return None, "UNRESOLVED_NO_REGISTERED_SLOT"
    return join, join["e2_join_disposition"]


def _effect_for_non_pidfd_action(
    *,
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
) -> tuple[str, dict[str, Any]]:
    exact = action["exact_c_b_action"]
    kind = exact["action_kind"]
    if kind == "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION":
        return _resolution_result(handle.manifest, action)
    if kind in _CONSERVATIVE_ACTIONS:
        return _conservative_owner_release(
            handle=handle,
            cleanup_lease=cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=exact,
        )
    if kind == "CLOSE_MOUNT":
        join, disposition = _classify_native_action(handle.manifest, action)
        if disposition in {"ABSENT_EXPLICIT", "ABSENT_CONTROL_FLOW"}:
            return "SKIPPED_KNOWN_ABSENT", {
                "cutoff_join_disposition": disposition,
                "native_close_performed": False,
            }
        if disposition != "PRESENT_LIVE" or join is None:
            return "BLOCKED_UNRESOLVED", {
                "cutoff_join_disposition": disposition,
                "native_close_performed": False,
                "callback_replayed": False,
            }
        if join["capability_kind"] != "OFD":
            return "NATIVE_EFFECT_FAILED", {
                "reason": "MOUNT_CLOSE_SLOT_IS_NOT_AN_OFD",
                "native_close_performed": False,
            }
        reconciled, alias_status = _close_guardian_alias_set(
            guardian,
            join,
            intent_id=intent["h1_cleanup_action_intent_id"],
            marker_kind="OFD_ALIAS_SET_CLOSED",
        )
        _record_native_effect_attestation(
            handle,
            intent["h1_cleanup_action_intent_id"],
            {
                "effect_kind": "GUARDIAN_OFD_ALIAS_SET_CLOSED",
                "cleanup_ordinal": action["cleanup_ordinal"],
                "slot_key": join["slot_key"],
                "broker_process_id": os.getpid(),
                "broker_thread_native_id": threading.get_native_id(),
                "broker_process_start_ticks": guardian_v1._process_start_ticks(),
                "underlying_ofd_last_reference_release_proven": False,
                "mount_resource_release_proven": False,
            },
        )
        return "GUARDIAN_ALIAS_SET_CLOSED", {
            "slot_key": join["slot_key"],
            "guardian_alias_set_closed": True,
            "alias_close_status": alias_status,
            "reconciled_same_broker_consumed_state": reconciled,
            "underlying_ofd_last_reference_release_proven": False,
            "mount_resource_release_proven": False,
            "external_same_ofd_alias_absence_proven": False,
        }
    _fail("E2 selected action kind has no registered executor")


def _prepare_intent_phase(
    handle: H1CleanupActionJournalHandleV1,
    *,
    expected_cleanup_ordinal: int | None,
    crash: H1CleanupActionCrashPointV1,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    attempt, lock_fd, cursor_fd = _open_locked(handle)
    try:
        records, rows = _load_state_locked(
            handle, attempt, cursor_fd, repair=True
        )
        summary = _state_summary(handle, records)
        actions = handle.manifest.payload["actions"]
        if expected_cleanup_ordinal is not None:
            if type(expected_cleanup_ordinal) is not int or not (
                1 <= expected_cleanup_ordinal <= max(1, len(actions))
            ):
                _fail("expected cleanup ordinal is invalid")
            completed = [
                row
                for row in records
                if row["schema"] == "acfqp.k7_h1_cleanup_action_result.v1"
            ]
            if expected_cleanup_ordinal <= len(completed):
                return None, None, completed[expected_cleanup_ordinal - 1]
            if expected_cleanup_ordinal != len(completed) + 1:
                _fail("cleanup action caller attempted to skip an ordinal")
        action, intent, preobs = _next_action_context(handle, records)
        if action is None:
            return None, None, None
        if intent is None:
            intent = _build_intent(handle, action, summary)
            records, rows = _append_record_locked(
                handle,
                attempt,
                cursor_fd,
                records,
                rows,
                intent,
                crash_after_file=(
                    crash
                    is H1CleanupActionCrashPointV1.AFTER_INTENT_FILE_FSYNC
                ),
            )
            if crash is H1CleanupActionCrashPointV1.AFTER_INTENT_CURSOR_FSYNC:
                raise H1CleanupActionJournalInjectedCrashV1(
                    "cleanup action journal crash after intent cursor fsync"
                )
        return action, intent, preobs
    finally:
        _unlock(lock_fd, cursor_fd, attempt)


def _append_pidfd_preobservation_phase(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    join: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    crash: H1CleanupActionCrashPointV1,
) -> dict[str, Any]:
    attempt, lock_fd, cursor_fd = _open_locked(handle)
    try:
        records, rows = _load_state_locked(
            handle, attempt, cursor_fd, repair=True
        )
        _action, current_intent, preobs = _next_action_context(handle, records)
        if (
            current_intent is None
            or current_intent["h1_cleanup_action_intent_id"]
            != intent["h1_cleanup_action_intent_id"]
        ):
            _fail("PIDFD preobservation crossed the durable current intent")
        if preobs is not None:
            return preobs
        preobs = _build_pidfd_preobservation(
            handle, action, intent, join, evidence
        )
        records, rows = _append_record_locked(
            handle,
            attempt,
            cursor_fd,
            records,
            rows,
            preobs,
            crash_after_file=False,
        )
        if (
            crash
            is H1CleanupActionCrashPointV1.AFTER_PIDFD_PREOBSERVATION_CURSOR_FSYNC
        ):
            raise H1CleanupActionJournalInjectedCrashV1(
                "cleanup action journal crash after PIDFD preobservation cursor"
            )
        return preobs
    finally:
        _unlock(lock_fd, cursor_fd, attempt)


def _append_result_phase(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    *,
    outcome: str,
    evidence: Mapping[str, Any],
    crash: H1CleanupActionCrashPointV1,
) -> dict[str, Any]:
    attempt, lock_fd, cursor_fd = _open_locked(handle)
    try:
        records, rows = _load_state_locked(
            handle, attempt, cursor_fd, repair=True
        )
        current_action, current_intent, _preobs = _next_action_context(
            handle, records
        )
        if current_action is None:
            results = [
                row
                for row in records
                if row["schema"] == "acfqp.k7_h1_cleanup_action_result.v1"
            ]
            existing = results[action["cleanup_ordinal"] - 1]
            return existing
        if (
            current_action["h1_cleanup_action_definition_id"]
            != action["h1_cleanup_action_definition_id"]
            or current_intent is None
            or current_intent["h1_cleanup_action_intent_id"]
            != intent["h1_cleanup_action_intent_id"]
        ):
            _fail("cleanup result crossed the current durable intent")
        result = _build_result(
            handle,
            action,
            intent,
            outcome=outcome,
            evidence=evidence,
        )
        records, rows = _append_record_locked(
            handle,
            attempt,
            cursor_fd,
            records,
            rows,
            result,
            crash_after_file=(
                crash is H1CleanupActionCrashPointV1.AFTER_RESULT_FILE_FSYNC
            ),
        )
        if crash is H1CleanupActionCrashPointV1.AFTER_RESULT_CURSOR_FSYNC:
            raise H1CleanupActionJournalInjectedCrashV1(
                "cleanup action journal crash after result cursor fsync"
            )
        return result
    finally:
        _unlock(lock_fd, cursor_fd, attempt)


def _acquire_effect_reservation(
    handle: H1CleanupActionJournalHandleV1,
    cleanup_ordinal: int,
) -> tuple[tuple[str, int], object]:
    key = (handle.allocation_id, cleanup_ordinal)
    token = object()
    with _EFFECT_RESERVATION_LOCK:
        if key in _ACTIVE_EFFECT_RESERVATIONS:
            _fail("cleanup native effect recursively or concurrently reentered")
        if key in _BURNED_EFFECT_RESERVATIONS:
            _fail("cleanup native effect reservation was burned fail-closed")
        _ACTIVE_EFFECT_RESERVATIONS[key] = token
    return key, token


def _finish_effect_reservation(
    key: tuple[str, int], token: object, *, burn: bool
) -> None:
    with _EFFECT_RESERVATION_LOCK:
        if _ACTIVE_EFFECT_RESERVATIONS.get(key) is not token:
            _BURNED_EFFECT_RESERVATIONS.add(key)
            _fail("cleanup native effect reservation identity changed")
        del _ACTIVE_EFFECT_RESERVATIONS[key]
        if burn:
            _BURNED_EFFECT_RESERVATIONS.add(key)


def _record_native_effect_attestation(
    handle: H1CleanupActionJournalHandleV1,
    intent_id: str,
    attestation: Mapping[str, Any],
) -> None:
    key = (handle.allocation_id, _cid(intent_id, "native effect intent"))
    exact = dict(attestation)
    with _EFFECT_RESERVATION_LOCK:
        previous = _NATIVE_EFFECT_ATTESTATIONS.get(key)
        if previous is not None and previous != exact:
            _BURNED_EFFECT_RESERVATIONS.add(
                (handle.allocation_id, int(exact["cleanup_ordinal"]))
            )
            _fail("same-broker native effect attestation conflicted")
        _NATIVE_EFFECT_ATTESTATIONS[key] = exact


def _require_native_effect_attestation(
    handle: H1CleanupActionJournalHandleV1,
    intent: Mapping[str, Any],
    *,
    effect_kind: str,
    slot_key: str,
    pidfd_preobservation_id: str | None = None,
) -> Mapping[str, Any]:
    key = (handle.allocation_id, intent["h1_cleanup_action_intent_id"])
    with _EFFECT_RESERVATION_LOCK:
        attestation = _NATIVE_EFFECT_ATTESTATIONS.get(key)
        if attestation is None:
            _fail("positive native result lacks same-broker effect attestation")
        exact = dict(attestation)
    if (
        exact.get("effect_kind") != effect_kind
        or exact.get("cleanup_ordinal") != intent["cleanup_ordinal"]
        or exact.get("slot_key") != slot_key
        or exact.get("broker_process_id") != os.getpid()
        or exact.get("broker_thread_native_id") != threading.get_native_id()
        or exact.get("broker_process_start_ticks")
        != guardian_v1._process_start_ticks()
    ):
        _fail("positive native result crossed its process-local attestation")
    if (
        pidfd_preobservation_id is not None
        and exact.get("h1_cleanup_pidfd_preobservation_id")
        != pidfd_preobservation_id
    ):
        _fail("PIDFD effect attestation crossed its durable preobservation")
    return exact


def _perform_cleanup_effect(
    handle: H1CleanupActionJournalHandleV1,
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
    *,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    crash: H1CleanupActionCrashPointV1,
) -> tuple[str, dict[str, Any]]:
    exact = action["exact_c_b_action"]
    if exact["action_kind"] != "REAP_DESCENDANT":
        return _effect_for_non_pidfd_action(
            handle=handle,
            action=action,
            intent=intent,
            cleanup_lease=cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            guardian=guardian,
        )
    join, disposition = _classify_native_action(handle.manifest, action)
    if disposition in {"ABSENT_EXPLICIT", "ABSENT_CONTROL_FLOW"}:
        return "SKIPPED_KNOWN_ABSENT", {
            "cutoff_join_disposition": disposition,
            "pidfd_waitid_reap_performed": False,
            "pidfd_close_alone_counted_as_reap": False,
        }
    if disposition != "PRESENT_LIVE" or join is None:
        return "BLOCKED_UNRESOLVED", {
            "cutoff_join_disposition": disposition,
            "pidfd_waitid_reap_performed": False,
            "callback_replayed": False,
        }
    if join["capability_kind"] != "PIDFD":
        return "NATIVE_EFFECT_FAILED", {
            "reason": "DESCENDANT_REAP_SLOT_IS_NOT_PIDFD",
            "pidfd_waitid_reap_performed": False,
        }
    attempt, lock_fd, cursor_fd = _open_locked(handle)
    try:
        records, _rows = _load_state_locked(
            handle, attempt, cursor_fd, repair=True
        )
        _action, _intent, preobs = _next_action_context(handle, records)
    finally:
        _unlock(lock_fd, cursor_fd, attempt)
    if preobs is None:
        status, observed = _pidfd_preobserve(guardian, join)
        if status != "EXITED":
            return (
                "PIDFD_NOT_EXITED" if status == "NOT_EXITED" else "BLOCKED_UNRESOLVED",
                {"pidfd_preobservation_status": status, **observed},
            )
        preobs = _append_pidfd_preobservation_phase(
            handle,
            action,
            intent,
            join,
            observed,
            crash=crash,
        )
    outcome, evidence = _reap_pidfd_after_preobservation(
        guardian,
        join,
        intent_id=intent["h1_cleanup_action_intent_id"],
    )
    if outcome == "PIDFD_REAPED":
        if preobs is None:  # pragma: no cover - state-machine invariant
            _fail("PIDFD reap lost its durable preobservation")
        _record_native_effect_attestation(
            handle,
            intent["h1_cleanup_action_intent_id"],
            {
                "effect_kind": "PIDFD_WAITID_REAPED",
                "cleanup_ordinal": action["cleanup_ordinal"],
                "slot_key": join["slot_key"],
                "h1_cleanup_pidfd_preobservation_id": preobs[
                    "h1_cleanup_pidfd_preobservation_id"
                ],
                "waitid_wnowait": dict(preobs["preobservation"]["waitid_wnowait"]),
                "broker_process_id": os.getpid(),
                "broker_thread_native_id": threading.get_native_id(),
                "broker_process_start_ticks": guardian_v1._process_start_ticks(),
                "guarded_callback_slot_waitable_child_only": True,
                "business_or_worker_role_identity_proven": False,
            },
        )
    return outcome, evidence


def execute_next_h1_cleanup_action_v1(
    handle: H1CleanupActionJournalHandleV1,
    *,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    expected_cleanup_ordinal: int | None = None,
    crash_point: H1CleanupActionCrashPointV1 | str = H1CleanupActionCrashPointV1.NONE,
) -> dict[str, Any]:
    """Process one exact selected action without holding ACTION over effects.

    Durable bytes support same-broker idempotence only.  Broker death, fork,
    restart, a poisoned Guardian or a consumed token is nonrecoverable and can
    never be converted into a fresh live cleanup capability by this API.
    """

    _require_handle(handle)
    cleanup_pass = _require_execution_context(
        handle,
        cleanup_lease=cleanup_lease,
        transition=transition,
        envelope=envelope,
        cleanup_analysis=cleanup_analysis,
        native_receipt_handle=native_receipt_handle,
        guardian=guardian,
        owner=owner,
    )
    try:
        crash = H1CleanupActionCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CleanupActionJournalV1Error(
            "cleanup action crash point is invalid"
        ) from error
    action, intent, completed = _prepare_intent_phase(
        handle,
        expected_cleanup_ordinal=expected_cleanup_ordinal,
        crash=crash,
    )
    if completed is not None:
        records, _rows = _revalidate_records_outside_action_lock(handle)
        if not any(
            row.get("h1_cleanup_action_result_id")
            == completed["h1_cleanup_action_result_id"]
            for row in records
        ):
            _fail("completed cleanup result disappeared before external replay")
        return completed
    if action is None or intent is None:
        return replay_h1_cleanup_action_journal_v1(handle)
    key, token = _acquire_effect_reservation(handle, action["cleanup_ordinal"])
    try:
        outcome, evidence = _perform_cleanup_effect(
            handle=handle,
            action=action,
            intent=intent,
            cleanup_lease=cleanup_lease,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            guardian=guardian,
            owner=owner,
            crash=crash,
        )
        if crash is H1CleanupActionCrashPointV1.AFTER_EFFECT_BEFORE_RESULT:
            raise H1CleanupActionJournalInjectedCrashV1(
                "cleanup action journal crash after effect before result"
            )
        result = _append_result_phase(
            handle,
            action,
            intent,
            outcome=outcome,
            evidence=evidence,
            crash=crash,
        )
        records, _rows = _revalidate_records_outside_action_lock(handle)
        if not any(
            row.get("h1_cleanup_action_result_id")
            == result["h1_cleanup_action_result_id"]
            for row in records
        ):
            _fail("cleanup result disappeared before external replay")
    except H1CleanupActionJournalInjectedCrashV1:
        _finish_effect_reservation(key, token, burn=False)
        raise
    except BaseException:
        _finish_effect_reservation(key, token, burn=True)
        raise
    _finish_effect_reservation(key, token, burn=False)
    return result


def replay_h1_cleanup_action_journal_v1(
    handle: H1CleanupActionJournalHandleV1,
) -> dict[str, Any]:
    """Replay durable bytes; this does not re-certify live native effects."""

    _require_handle(handle)
    records, rows = _revalidate_records_outside_action_lock(handle)
    summary = _state_summary(handle, records)
    payload = {
            "schema": "acfqp.k7_h1_cleanup_drain_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_cleanup_action_manifest_id": handle.manifest.manifest_id,
            "h1_cleanup_action_journal_allocation_id": handle.allocation_id,
            "h1_attempt_cleanup_transition_v2_id": handle.manifest.payload[
                "h1_attempt_cleanup_transition_v2_id"
            ],
            "h1_native_cutoff_snapshot_id": handle.manifest.payload[
                "h1_native_cutoff_snapshot_id"
            ],
            "cursor_sequence": len(rows) - 1,
            "cursor_head_id": rows[-1]["h1_cleanup_journal_cursor_id"],
            "record_ids": [_record_identity(row)[2] for row in records],
            **summary,
            "selected_action_count": handle.manifest.payload["action_count"],
            "normal_ordinal_41_to_52_success_events_issued": False,
            "journal_integrity_replay_is_not_live_native_reverification": True,
            "cross_process_native_recovery_present": False,
            "broker_death_or_consumed_token_recovery_present": False,
            "underlying_ofd_last_reference_release_proven": False,
            "mount_resource_release_proven": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "production_output_leaf_authority_present": False,
            "current_access_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "production_execution_authority_present": False,
            "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_cleanup_drain_snapshot_id": _content_id(DRAIN_DOMAIN, payload),
    }


def drain_h1_cleanup_actions_v1(
    handle: H1CleanupActionJournalHandleV1,
    *,
    cleanup_lease: cleanup_v2.H1AttemptCleanupOnlyLeaseV2,
    transition: cleanup_v2.H1AttemptCleanupTransitionV2,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    guardian: guardian_v1.H1NativeCapabilityGuardianV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
) -> dict[str, Any]:
    """Drain every selected action, continuing past typed secondary failures."""

    while True:
        snapshot = replay_h1_cleanup_action_journal_v1(handle)
        if snapshot["drained"]:
            return snapshot
        execute_next_h1_cleanup_action_v1(
            handle,
            cleanup_lease=cleanup_lease,
            transition=transition,
            envelope=envelope,
            cleanup_analysis=cleanup_analysis,
            native_receipt_handle=native_receipt_handle,
            guardian=guardian,
            owner=owner,
            expected_cleanup_ordinal=snapshot["next_cleanup_ordinal"],
        )


__all__ = (
    "CLEANUP_ACTION_JOURNAL_PRESENT",
    "CLEANUP_CUTOFF_JOIN_PRESENT",
    "COMPONENTWISE_C_D_BUDGET_SINGLE_SPEND_PRESENT",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "GUARDIAN_ALIAS_SET_CLOSE_EFFECT_PRESENT",
    "H1CleanupActionCrashPointV1",
    "H1CleanupActionJournalHandleV1",
    "H1CleanupActionJournalInjectedCrashV1",
    "H1CleanupActionManifestV1",
    "MOUNT_RESOURCE_RELEASE_PROVEN",
    "NORMAL_ORDINAL_41_TO_52_SUCCESS_EVENTS_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PIDFD_WAITID_REAP_EFFECT_PRESENT",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "UNDERLYING_OFD_LAST_REFERENCE_RELEASE_PROVEN",
    "ConstructionK7H1CleanupActionJournalV1Error",
    "close_h1_cleanup_action_journal_v1",
    "drain_h1_cleanup_actions_v1",
    "execute_next_h1_cleanup_action_v1",
    "freeze_h1_cleanup_action_manifest_v1",
    "initialize_h1_cleanup_action_journal_v1",
    "replay_h1_cleanup_action_journal_v1",
)
