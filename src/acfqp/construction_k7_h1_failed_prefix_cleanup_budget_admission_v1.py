"""Pre-ordinal-1 admission of the complete H1 failed-prefix cleanup budget.

This construction-only slice freezes the branchwise maximum number of cleanup
operations that any registered normal-prefix failure branch may require.  It
binds the durable C-B envelope, its exact passes/actions and pristine Owner
cutoff, a prospective (not yet allocated) V5 Owner-sidecar baseline, and the
actual predeclared V6 native-receipt spec/allocation.

No cleanup action is executed.  The admitted units are not FQ11 counters and
cannot authorize native effects, output finalization, current access, V7, or
official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import fcntl
import hmac
import os
from pathlib import Path
import stat
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v7 as domains_v7
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_owner_cleanup_continuation_sidecar_v1 as sidecar_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-D"
PROFILE_KEY = "construction_k7_h1_failed_prefix_cleanup_budget_admission_v1"

FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_PRESENT = True
REGISTERED_FAILURE_BRANCH_COUNT = 112
REACHABLE_FAILURE_BRANCH_COUNT = 111
BRANCHWISE_CLEANUP_MAXIMUM_TOTAL = 15
ACTUAL_V5_SIDECAR_SPEC_ALLOCATION_PRESENT = False
CLEANUP_ACTION_EXECUTION_AUTHORITY_PRESENT = False
NATIVE_CLEANUP_EFFECT_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

PROSPECTIVE_SIDECAR_BASELINE_DOMAIN = (
    domains_v7.CONSTRUCTION_K7_H1_PROSPECTIVE_OWNER_CLEANUP_SIDECAR_BASELINE_V1_DOMAIN
)
ADMISSION_DOMAIN = (
    domains_v7.CONSTRUCTION_K7_H1_FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_V1_DOMAIN
)

_BASELINE_ISSUER = object()
_ADMISSION_ISSUER = object()
_ROOT_NAME = ".acfqp-k7-h1-failed-prefix-cleanup-budget-admissions-v1"
_ROOT_LOCK_FILE = ".cleanup-budget-admission.lock"
_ADMISSION_FILE = "cleanup-budget-admission.json"
_SEAL_PREFIX = "cleanup-budget-admission-seal-"

_CATEGORY_ORDER = (
    "RESOLVE",
    "REAP",
    "MOUNT_CLOSE",
    "MEMORY_RELEASE",
    "OUTPUT_RELEASE",
)
_ACTION_CATEGORY = MappingProxyType(
    {
        "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION": "RESOLVE",
        "REAP_DESCENDANT": "REAP",
        "CLOSE_MOUNT": "MOUNT_CLOSE",
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ": (
            "MEMORY_RELEASE"
        ),
        "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE": (
            "OUTPUT_RELEASE"
        ),
    }
)
REQUIRED_CLEANUP_BUDGET_MAXIMA: Mapping[str, int] = MappingProxyType(
    {
        "RESOLVE": 1,
        "REAP": 2,
        "MOUNT_CLOSE": 10,
        "MEMORY_RELEASE": 1,
        "OUTPUT_RELEASE": 1,
    }
)

_TYPED_NULL_V5_SPEC = {
    "kind": "NOT_APPLICABLE",
    "reason": "V5_SPEC_CAN_ONLY_BIND_THE_SELECTED_POST_FAILURE_ACTION",
}
_TYPED_NULL_V5_ALLOCATION = {
    "kind": "NOT_APPLICABLE",
    "reason": "V5_ALLOCATION_DOES_NOT_EXIST_BEFORE_NORMAL_ORDINAL_1",
}

_BASELINE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "h1_attempt_execution_phase_spec_id",
        "h1_attempt_phase_allocation_id",
        "h1_attempt_rejection_gate_id",
        "h1_preadmitted_cleanup_envelope_id",
        "h1_shared_cap_profile_core_v3_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "c_b_owner_cutoff_sequence",
        "c_b_owner_cutoff_head_id",
        "c_b_gate_state_at_preadmission",
        "c_b_gate_owner_join_status_at_preadmission",
        "phase_base_realpath",
        "phase_base_device",
        "phase_base_inode",
        "prospective_sidecar_root_realpath",
        "v5_sidecar_profile_key",
        "v5_sidecar_spec_schema",
        "v5_sidecar_spec_domain",
        "v5_sidecar_allocation_schema",
        "v5_sidecar_allocation_domain",
        "actual_h1_owner_cleanup_sidecar_spec_id",
        "actual_h1_owner_cleanup_sidecar_allocation_id",
        "actual_v5_sidecar_spec_allocation_present",
        "future_v5_spec_must_bind_exact_selected_transition_pass_action",
        "future_v5_spec_must_bind_stable_failure_time_owner_cutoff",
        "future_v5_allocation_must_bind_unique_phase_base_root",
        "prospective_baseline_is_not_a_v5_spec_or_allocation",
        "cleanup_action_execution_authority_present",
        "native_cleanup_effect_authority_present",
        "formal_counter_records_issued",
        "formal_v7_route_authority_present",
        "official_execution_allowed",
    }
)

_ADMISSION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "h1_attempt_execution_phase_spec_id",
        "h1_attempt_phase_allocation_id",
        "h1_attempt_rejection_gate_id",
        "h1_normal_prefix_spec_id",
        "h1_normal_prefix_allocation_id",
        "h1_preadmitted_cleanup_envelope_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "h1_prospective_owner_cleanup_sidecar_baseline_id",
        "prospective_owner_cleanup_sidecar_baseline",
        "h1_native_receipt_journal_spec_id",
        "h1_native_receipt_allocation_id",
        "native_receipt_genesis_cursor_id",
        "native_receipt_slot_count",
        "native_receipt_record_count_at_admission",
        "native_receipt_cutoff_snapshot_id_at_admission",
        "registered_failure_branch_count",
        "dispatcher_reachable_failure_branch_count",
        "unreachable_negative_control_branch_count",
        "branch_budget_rows",
        "branchwise_cleanup_maxima",
        "branchwise_cleanup_maximum_total",
        "available_cleanup_budget",
        "available_cleanup_budget_total",
        "budget_sufficient_on_every_category",
        "preadmitted_before_normal_ordinal_1",
        "normal_completed_event_count_at_admission",
        "normal_next_ordinal_at_admission",
        "normal_dangling_intent_id_at_admission",
        "c_b_owner_cutoff_sequence",
        "c_b_owner_cutoff_head_id",
        "c_b_gate_state_at_preadmission",
        "c_b_gate_owner_join_status_at_preadmission",
        "exact_c_b_pass_action_universe_bound",
        "actual_v6_spec_allocation_bound",
        "actual_v5_sidecar_spec_allocation_present",
        "v5_binding_is_prospective_only",
        "later_native_cutoff_receipt_join_present",
        "cleanup_budget_units_are_construction_admission_tokens_only",
        "fq11_cleanup_counter_leaf_ratified",
        "cleanup_action_execution_authority_present",
        "native_cleanup_effect_authority_present",
        "production_output_leaf_authority_present",
        "production_execution_authority_present",
        "current_access_authority_present",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "official_execution_allowed",
    }
)


class ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(ValueError):
    """The pre-ordinal cleanup budget or one of its identities was crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _content_id(domain: str, payload: Any) -> str:
    return domains_v7.extension_content_id_v7(domain, payload)


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            f"{label} is not canonical"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


@dataclass(frozen=True, slots=True)
class H1ProspectiveOwnerCleanupSidecarBaselineV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _baseline_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BASELINE_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("prospective V5 sidecar baseline is caller-minted")
        payload = _parse(self.payload_bytes, "prospective V5 sidecar baseline")
        if frozenset(payload) != _BASELINE_FIELDS:
            _fail("prospective V5 sidecar baseline fields changed")
        object.__setattr__(
            self,
            "_baseline_id",
            _content_id(PROSPECTIVE_SIDECAR_BASELINE_DOMAIN, payload),
        )

    @property
    def baseline_id(self) -> str:
        return self._baseline_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse(self.payload_bytes, "prospective V5 sidecar baseline")

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_prospective_owner_cleanup_sidecar_baseline_id": self.baseline_id,
        }


@dataclass(frozen=True, slots=True)
class H1FailedPrefixCleanupBudgetAdmissionV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _admission_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ADMISSION_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("failed-prefix cleanup budget admission is caller-minted")
        payload = _parse(self.payload_bytes, "failed-prefix cleanup budget admission")
        if frozenset(payload) != _ADMISSION_FIELDS:
            _fail("failed-prefix cleanup budget admission fields changed")
        baseline_document = payload["prospective_owner_cleanup_sidecar_baseline"]
        if type(baseline_document) is not dict:
            _fail("cleanup admission lost its prospective V5 baseline")
        baseline_payload = dict(baseline_document)
        baseline_claimed = _cid(
            baseline_payload.pop(
                "h1_prospective_owner_cleanup_sidecar_baseline_id", None
            ),
            "prospective V5 sidecar baseline",
        )
        baseline = H1ProspectiveOwnerCleanupSidecarBaselineV1(
            _BASELINE_ISSUER, canonical_json_bytes(baseline_payload)
        )
        if (
            baseline.baseline_id != baseline_claimed
            or payload["h1_prospective_owner_cleanup_sidecar_baseline_id"]
            != baseline.baseline_id
        ):
            _fail("cleanup admission crossed its prospective V5 baseline")
        object.__setattr__(
            self, "_admission_id", _content_id(ADMISSION_DOMAIN, payload)
        )

    @property
    def admission_id(self) -> str:
        return self._admission_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse(self.payload_bytes, "failed-prefix cleanup budget admission")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_failed_prefix_cleanup_budget_admission_id": self.admission_id,
        }


def _normalize_available_budget(value: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(_CATEGORY_ORDER):
        _fail("available cleanup budget must name exactly the five registered categories")
    result: dict[str, int] = {}
    for category in _CATEGORY_ORDER:
        units = value[category]
        if type(units) is not int or units < 0:
            _fail("available cleanup budget values must be nonnegative integers")
        result[category] = units
    return result


def _derive_branch_budget_rows(
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    normal_spec: normal_v1.H1NormalPrefixSpecV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    expected = cleanup_v2._derive_failure_whitelist(
        normal_spec.payload, cleanup_analysis
    )
    if envelope.payload["failure_branch_action_whitelist"] != expected:
        _fail("C-B envelope no longer binds the exact cleanup pass/action universe")
    rows: list[dict[str, Any]] = []
    maxima = {category: 0 for category in _CATEGORY_ORDER}
    for branch in expected:
        counts = {category: 0 for category in _CATEGORY_ORDER}
        actions: list[dict[str, Any]] = []
        for action in branch["planned_cleanup_actions"]:
            kind = action.get("action_kind")
            category = _ACTION_CATEGORY.get(kind)
            if category is None:
                _fail("C-B cleanup action lacks a registered budget category")
            counts[category] += 1
            actions.append(
                {
                    "cleanup_ordinal": action["cleanup_ordinal"],
                    "action_kind": kind,
                    "target": action["target"],
                    "budget_category": category,
                    "budget_units": 1,
                    "exact_c_b_action": dict(action),
                }
            )
        for category in _CATEGORY_ORDER:
            maxima[category] = max(maxima[category], counts[category])
        rows.append(
            {
                "branch_key": branch["branch_key"],
                "failed_ordinal": branch["failed_ordinal"],
                "failed_site_key": branch["failed_site_key"],
                "first_failure_outcome": branch["first_failure_outcome"],
                "dispatcher_outcome_reachable": branch[
                    "dispatcher_outcome_reachable"
                ],
                "h1_lifecycle_cleanup_pass_id": branch[
                    "h1_lifecycle_cleanup_pass_id"
                ],
                "exact_c_b_actions": actions,
                "branch_cleanup_budget": counts,
                "branch_cleanup_budget_total": sum(counts.values()),
            }
        )
    reachable = sum(row["dispatcher_outcome_reachable"] is True for row in rows)
    if (
        len(rows) != REGISTERED_FAILURE_BRANCH_COUNT
        or reachable != REACHABLE_FAILURE_BRANCH_COUNT
        or maxima != dict(REQUIRED_CLEANUP_BUDGET_MAXIMA)
        or sum(maxima.values()) != BRANCHWISE_CLEANUP_MAXIMUM_TOTAL
    ):
        _fail("registered cleanup branch universe or its conservative maxima changed")
    return rows, maxima


def _require_exact_context(
    *,
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_spec: receipts_v1.H1NativeReceiptJournalSpecV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
) -> tuple[
    Path,
    normal_v1.H1NormalPrefixSpecV1,
    dict[str, Any],
    dict[str, Any],
]:
    lease = normal_v1._require_live_lease(lease)
    phase_handle = lease.phase_handle
    normal_handle = lease.handle
    if (
        type(envelope) is not cleanup_v2.H1PreadmittedCleanupEnvelopeV1
        or type(cleanup_analysis) is not cleanup_v1.H1LifecycleCompleteBranchAnalysisV1
        or type(native_receipt_spec)
        is not receipts_v1.H1NativeReceiptJournalSpecV1
        or type(native_receipt_handle)
        is not receipts_v1.H1NativeReceiptJournalHandleV1
    ):
        _fail("cleanup admission requires exact issuer-owned construction artifacts")
    phase_payload = phase_handle.spec.payload
    try:
        base = Path(phase_payload["phase_base_realpath"]).resolve(strict=True)
        base_metadata = base.stat()
    except (OSError, RuntimeError) as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            "phase base cannot be resolved for cleanup admission"
        ) from error
    if (
        not stat.S_ISDIR(base_metadata.st_mode)
        or (base_metadata.st_dev, base_metadata.st_ino)
        != (phase_payload["phase_base_device"], phase_payload["phase_base_inode"])
    ):
        _fail("cleanup admission phase-base identity changed")
    durable_envelope = cleanup_v2._load_envelope_for_phase_handle(phase_handle)
    if (
        durable_envelope.envelope_id != envelope.envelope_id
        or not hmac.compare_digest(
            durable_envelope.canonical_bytes, envelope.canonical_bytes
        )
    ):
        _fail("cleanup admission crossed its durable C-B envelope")
    durable_normal_spec = cleanup_v2._load_normal_prefix_spec_for_envelope(
        phase_handle, durable_envelope
    )
    cleanup_v2._validate_envelope_against_normal_spec(
        durable_envelope, durable_normal_spec
    )
    cleanup_v2._validate_envelope_bindings(
        durable_envelope, lease, cleanup_analysis
    )
    if (
        durable_normal_spec.spec_id != normal_handle.spec.spec_id
        or not hmac.compare_digest(
            canonical_json_bytes(durable_normal_spec.to_document()),
            canonical_json_bytes(normal_handle.spec.to_document()),
        )
        or durable_envelope.payload["h1_normal_prefix_allocation_id"]
        != normal_handle.allocation_id
        or durable_envelope.payload["h1_lifecycle_complete_branch_analysis_id"]
        != cleanup_analysis.analysis_id
    ):
        _fail("cleanup admission crossed its normal allocation or branch analysis")
    context = {
        "logical_occurrence_id": durable_envelope.payload["logical_occurrence_id"],
        "route_attempt_id": durable_envelope.payload["route_attempt_id"],
        "decision_point_id": durable_envelope.payload["decision_point_id"],
        "transaction_id": durable_envelope.payload["transaction_id"],
        "h1_normal_prefix_spec_id": normal_handle.spec.spec_id,
        "h1_normal_prefix_allocation_id": normal_handle.allocation_id,
    }
    native_payload = native_receipt_spec.payload
    if (
        native_receipt_handle.spec.spec_id != native_receipt_spec.spec_id
        or not hmac.compare_digest(
            native_receipt_handle.spec.canonical_bytes,
            native_receipt_spec.canonical_bytes,
        )
        or native_receipt_handle.normal_handle.spec.spec_id
        != normal_handle.spec.spec_id
        or native_receipt_handle.normal_handle.allocation_id
        != normal_handle.allocation_id
        or any(native_payload[key] != value for key, value in context.items())
        or native_payload["predeclared_before_normal_ordinal_1"] is not True
        or native_payload["slot_count"] != 12
    ):
        _fail("cleanup admission crossed its V6 receipt spec/allocation context")
    return base, durable_normal_spec, context, phase_payload


def _build_prospective_sidecar_baseline(
    *,
    base: Path,
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
) -> H1ProspectiveOwnerCleanupSidecarBaselineV1:
    phase_payload = phase_handle.spec.payload
    admitted = envelope.payload
    payload = {
        "schema": "acfqp.k7_h1_prospective_owner_cleanup_sidecar_baseline.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": admitted["logical_occurrence_id"],
        "route_attempt_id": admitted["route_attempt_id"],
        "decision_point_id": admitted["decision_point_id"],
        "transaction_id": admitted["transaction_id"],
        "h1_attempt_execution_phase_spec_id": phase_handle.spec_id,
        "h1_attempt_phase_allocation_id": phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": admitted["h1_attempt_rejection_gate_id"],
        "h1_preadmitted_cleanup_envelope_id": envelope.envelope_id,
        "h1_shared_cap_profile_core_v3_id": admitted[
            "h1_shared_cap_profile_core_v3_id"
        ],
        "h1_shared_cap_owner_v3_runtime_id": admitted[
            "h1_shared_cap_owner_v3_runtime_id"
        ],
        "h1_shared_cap_owner_v4_wal_binding_id": admitted[
            "h1_shared_cap_owner_v4_wal_binding_id"
        ],
        "c_b_owner_cutoff_sequence": admitted[
            "owner_tail_sequence_at_preadmission"
        ],
        "c_b_owner_cutoff_head_id": admitted[
            "owner_tail_head_id_at_preadmission"
        ],
        "c_b_gate_state_at_preadmission": admitted["gate_state_at_preadmission"],
        "c_b_gate_owner_join_status_at_preadmission": admitted[
            "gate_owner_join_status_at_preadmission"
        ],
        "phase_base_realpath": str(base),
        "phase_base_device": phase_payload["phase_base_device"],
        "phase_base_inode": phase_payload["phase_base_inode"],
        "prospective_sidecar_root_realpath": str(base / sidecar_v1._ROOT_NAME),
        "v5_sidecar_profile_key": sidecar_v1.PROFILE_KEY,
        "v5_sidecar_spec_schema": "acfqp.k7_h1_owner_cleanup_sidecar_spec.v1",
        "v5_sidecar_spec_domain": sidecar_v1.SPEC_DOMAIN,
        "v5_sidecar_allocation_schema": (
            "acfqp.k7_h1_owner_cleanup_sidecar_allocation.v1"
        ),
        "v5_sidecar_allocation_domain": sidecar_v1.ALLOCATION_DOMAIN,
        "actual_h1_owner_cleanup_sidecar_spec_id": dict(_TYPED_NULL_V5_SPEC),
        "actual_h1_owner_cleanup_sidecar_allocation_id": dict(
            _TYPED_NULL_V5_ALLOCATION
        ),
        "actual_v5_sidecar_spec_allocation_present": False,
        "future_v5_spec_must_bind_exact_selected_transition_pass_action": True,
        "future_v5_spec_must_bind_stable_failure_time_owner_cutoff": True,
        "future_v5_allocation_must_bind_unique_phase_base_root": True,
        "prospective_baseline_is_not_a_v5_spec_or_allocation": True,
        "cleanup_action_execution_authority_present": False,
        "native_cleanup_effect_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1ProspectiveOwnerCleanupSidecarBaselineV1(
        _BASELINE_ISSUER, canonical_json_bytes(payload)
    )


def _build_admission(
    *,
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    baseline: H1ProspectiveOwnerCleanupSidecarBaselineV1,
    native_receipt_spec: receipts_v1.H1NativeReceiptJournalSpecV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    native_replay: Mapping[str, Any],
    normal_snapshot: normal_v1.H1NormalPrefixSnapshotV1,
    branch_rows: list[dict[str, Any]],
    maxima: dict[str, int],
    available: dict[str, int],
) -> H1FailedPrefixCleanupBudgetAdmissionV1:
    admitted = envelope.payload
    snapshot = normal_snapshot.document
    payload = {
        "schema": "acfqp.k7_h1_failed_prefix_cleanup_budget_admission.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": admitted["logical_occurrence_id"],
        "route_attempt_id": admitted["route_attempt_id"],
        "decision_point_id": admitted["decision_point_id"],
        "transaction_id": admitted["transaction_id"],
        "h1_attempt_execution_phase_spec_id": phase_handle.spec_id,
        "h1_attempt_phase_allocation_id": phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": admitted["h1_attempt_rejection_gate_id"],
        "h1_normal_prefix_spec_id": normal_handle.spec.spec_id,
        "h1_normal_prefix_allocation_id": normal_handle.allocation_id,
        "h1_preadmitted_cleanup_envelope_id": envelope.envelope_id,
        "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
        "h1_prospective_owner_cleanup_sidecar_baseline_id": baseline.baseline_id,
        "prospective_owner_cleanup_sidecar_baseline": baseline.to_document(),
        "h1_native_receipt_journal_spec_id": native_receipt_spec.spec_id,
        "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
        "native_receipt_genesis_cursor_id": native_replay["cursor_head_id"],
        "native_receipt_slot_count": native_replay["slot_count"],
        "native_receipt_record_count_at_admission": native_replay["record_count"],
        "native_receipt_cutoff_snapshot_id_at_admission": native_replay[
            "cutoff_snapshot_id"
        ],
        "registered_failure_branch_count": len(branch_rows),
        "dispatcher_reachable_failure_branch_count": sum(
            row["dispatcher_outcome_reachable"] is True for row in branch_rows
        ),
        "unreachable_negative_control_branch_count": sum(
            row["dispatcher_outcome_reachable"] is False for row in branch_rows
        ),
        "branch_budget_rows": branch_rows,
        "branchwise_cleanup_maxima": maxima,
        "branchwise_cleanup_maximum_total": sum(maxima.values()),
        "available_cleanup_budget": available,
        "available_cleanup_budget_total": sum(available.values()),
        "budget_sufficient_on_every_category": True,
        "preadmitted_before_normal_ordinal_1": True,
        "normal_completed_event_count_at_admission": snapshot[
            "completed_event_count"
        ],
        "normal_next_ordinal_at_admission": snapshot["next_ordinal"],
        "normal_dangling_intent_id_at_admission": snapshot["dangling_intent_id"],
        "c_b_owner_cutoff_sequence": admitted[
            "owner_tail_sequence_at_preadmission"
        ],
        "c_b_owner_cutoff_head_id": admitted[
            "owner_tail_head_id_at_preadmission"
        ],
        "c_b_gate_state_at_preadmission": admitted["gate_state_at_preadmission"],
        "c_b_gate_owner_join_status_at_preadmission": admitted[
            "gate_owner_join_status_at_preadmission"
        ],
        "exact_c_b_pass_action_universe_bound": True,
        "actual_v6_spec_allocation_bound": True,
        "actual_v5_sidecar_spec_allocation_present": False,
        "v5_binding_is_prospective_only": True,
        "later_native_cutoff_receipt_join_present": False,
        "cleanup_budget_units_are_construction_admission_tokens_only": True,
        "fq11_cleanup_counter_leaf_ratified": False,
        "cleanup_action_execution_authority_present": False,
        "native_cleanup_effect_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "current_access_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1FailedPrefixCleanupBudgetAdmissionV1(
        _ADMISSION_ISSUER, canonical_json_bytes(payload)
    )


def _admission_from_raw(raw: bytes) -> H1FailedPrefixCleanupBudgetAdmissionV1:
    document = _parse(raw, "cleanup budget admission file")
    payload = dict(document)
    claimed = _cid(
        payload.pop("h1_failed_prefix_cleanup_budget_admission_id", None),
        "cleanup budget admission",
    )
    admission = H1FailedPrefixCleanupBudgetAdmissionV1(
        _ADMISSION_ISSUER, canonical_json_bytes(payload)
    )
    if admission.admission_id != claimed or admission.canonical_bytes != raw:
        _fail("cleanup budget admission content ID changed")
    return admission


def _read_entry(directory_fd: int, name: str) -> tuple[bytes, os.stat_result] | None:
    return phase_v1._read_file_with_metadata(directory_fd, name)


def _reconcile_or_publish_locked(
    base_fd: int,
    admission: H1FailedPrefixCleanupBudgetAdmissionV1,
) -> H1FailedPrefixCleanupBudgetAdmissionV1:
    try:
        os.mkdir(_ROOT_NAME, mode=0o700, dir_fd=base_fd)
        os.fsync(base_fd)
    except FileExistsError:
        pass
    root_fd = phase_v1._open_directory_at(base_fd, _ROOT_NAME)
    attempt_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_IMODE(root_metadata.st_mode) != 0o700
        ):
            _fail("cleanup admission root is not one private directory")
        route_attempt_id = admission.payload["route_attempt_id"]
        try:
            os.mkdir(route_attempt_id, mode=0o700, dir_fd=root_fd)
            os.fsync(root_fd)
        except FileExistsError:
            pass
        attempt_fd = phase_v1._open_directory_at(root_fd, route_attempt_id)
        attempt_metadata = os.fstat(attempt_fd)
        if stat.S_IMODE(attempt_metadata.st_mode) != 0o700:
            _fail("cleanup admission attempt directory is not private")
        phase_v1._cleanup_temps(attempt_fd)
        seal_name = f"{_SEAL_PREFIX}{route_attempt_id}"
        primary = _read_entry(attempt_fd, _ADMISSION_FILE)
        seal = _read_entry(base_fd, seal_name)
        parsed: H1FailedPrefixCleanupBudgetAdmissionV1 | None = None
        if primary is not None:
            phase_v1._require_mode(
                primary[1], 0o400, "cleanup budget admission"
            )
            parsed = _admission_from_raw(primary[0])
            if (
                parsed.admission_id != admission.admission_id
                or not hmac.compare_digest(
                    parsed.canonical_bytes, admission.canonical_bytes
                )
            ):
                _fail(
                    "existing cleanup budget admission differs from the exact request"
                )
        if seal is not None:
            phase_v1._require_mode(
                seal[1], 0o400, "cleanup budget admission seal"
            )
            sealed = _admission_from_raw(seal[0])
            if (
                sealed.admission_id != admission.admission_id
                or not hmac.compare_digest(
                    sealed.canonical_bytes, admission.canonical_bytes
                )
            ):
                _fail(
                    "existing cleanup budget admission seal differs from the exact request"
                )
        if primary is not None and seal is not None:
            if (
                not hmac.compare_digest(primary[0], seal[0])
                or (primary[1].st_dev, primary[1].st_ino)
                != (seal[1].st_dev, seal[1].st_ino)
                or primary[1].st_nlink != 2
                or seal[1].st_nlink != 2
            ):
                _fail("cleanup admission and immutable root seal differ")
        elif primary is not None:
            if primary[1].st_nlink != 1:
                _fail("lone cleanup admission primary has a foreign hard link")
        elif seal is not None and seal[1].st_nlink != 1:
            _fail("lone cleanup admission seal has a foreign hard link")
        if primary is None and seal is None:
            if not phase_v1._publish_new(
                attempt_fd, _ADMISSION_FILE, admission.canonical_bytes
            ):
                _fail("cleanup admission publication raced")
            primary = _read_entry(attempt_fd, _ADMISSION_FILE)
        if primary is None and seal is not None:
            os.link(
                seal_name,
                _ADMISSION_FILE,
                src_dir_fd=base_fd,
                dst_dir_fd=attempt_fd,
                follow_symlinks=False,
            )
            os.fsync(attempt_fd)
            primary = _read_entry(attempt_fd, _ADMISSION_FILE)
            seal = _read_entry(base_fd, seal_name)
        if primary is None:  # pragma: no cover - publication invariant
            _fail("cleanup admission primary file is absent")
        phase_v1._require_mode(primary[1], 0o400, "cleanup budget admission")
        parsed = _admission_from_raw(primary[0])
        if (
            parsed.admission_id != admission.admission_id
            or not hmac.compare_digest(parsed.canonical_bytes, admission.canonical_bytes)
        ):
            _fail("existing cleanup budget admission differs from the exact request")
        if seal is None:
            try:
                os.link(
                    _ADMISSION_FILE,
                    seal_name,
                    src_dir_fd=attempt_fd,
                    dst_dir_fd=base_fd,
                    follow_symlinks=False,
                )
                os.fsync(base_fd)
            except FileExistsError:
                pass
            seal = _read_entry(base_fd, seal_name)
            primary = _read_entry(attempt_fd, _ADMISSION_FILE)
        if seal is None or primary is None:
            _fail("cleanup admission root seal is absent")
        phase_v1._require_mode(seal[1], 0o400, "cleanup budget admission seal")
        if (
            not hmac.compare_digest(primary[0], seal[0])
            or (primary[1].st_dev, primary[1].st_ino)
            != (seal[1].st_dev, seal[1].st_ino)
            or primary[1].st_nlink != 2
            or seal[1].st_nlink != 2
        ):
            _fail("cleanup admission and immutable root seal differ")
        try:
            current_root = os.stat(
                _ROOT_NAME, dir_fd=base_fd, follow_symlinks=False
            )
            current_attempt = os.stat(
                route_attempt_id, dir_fd=root_fd, follow_symlinks=False
            )
        except OSError as error:
            raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
                "cleanup admission canonical directory mapping disappeared"
            ) from error
        if (
            (current_root.st_dev, current_root.st_ino)
            != (root_metadata.st_dev, root_metadata.st_ino)
            or (current_attempt.st_dev, current_attempt.st_ino)
            != (attempt_metadata.st_dev, attempt_metadata.st_ino)
        ):
            _fail("cleanup admission canonical directory mapping changed")
        return parsed
    finally:
        if attempt_fd >= 0:
            os.close(attempt_fd)
        os.close(root_fd)


def _require_pinned_phase_base_path(base: Path, base_fd: int) -> None:
    try:
        live = base.stat(follow_symlinks=False)
        pinned = os.fstat(base_fd)
    except OSError as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            "cleanup admission phase-base pathname disappeared"
        ) from error
    if (
        not stat.S_ISDIR(live.st_mode)
        or (live.st_dev, live.st_ino) != (pinned.st_dev, pinned.st_ino)
    ):
        _fail("cleanup admission phase-base pathname changed during publication")


def _reconcile_or_publish(
    base: Path,
    base_fd: int,
    admission: H1FailedPrefixCleanupBudgetAdmissionV1,
) -> H1FailedPrefixCleanupBudgetAdmissionV1:
    _require_pinned_phase_base_path(base, base_fd)
    create_flags = os.O_RDWR | os.O_CLOEXEC
    existing_flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        create_flags |= os.O_NOFOLLOW
        existing_flags |= os.O_NOFOLLOW
    created = False
    try:
        lock_fd = os.open(
            _ROOT_LOCK_FILE,
            create_flags | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=base_fd,
        )
        created = True
    except FileExistsError:
        try:
            lock_fd = os.open(
                _ROOT_LOCK_FILE, existing_flags, dir_fd=base_fd
            )
        except OSError as error:
            raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
                "cleanup admission root coordination lock cannot be opened"
            ) from error
    except OSError as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            "cleanup admission root coordination lock cannot be opened"
        ) from error
    try:
        if created:
            os.fchmod(lock_fd, 0o600)
            os.fsync(lock_fd)
            os.fsync(base_fd)
        metadata = os.fstat(lock_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            _fail("cleanup admission root coordination lock changed")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        result = _reconcile_or_publish_locked(base_fd, admission)
        _require_pinned_phase_base_path(base, base_fd)
        return result
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _open_pinned_phase_base(phase_payload: Mapping[str, Any]) -> tuple[Path, int]:
    base = Path(phase_payload["phase_base_realpath"])
    if not base.is_absolute():
        _fail("cleanup admission phase base is not absolute")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        base_fd = os.open(base, flags)
    except OSError as error:
        raise ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error(
            "cleanup admission phase base cannot be pinned"
        ) from error
    try:
        metadata = os.fstat(base_fd)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino)
            != (
                phase_payload["phase_base_device"],
                phase_payload["phase_base_inode"],
            )
        ):
            _fail("cleanup admission pinned phase-base identity changed")
    except BaseException:
        os.close(base_fd)
        raise
    return base, base_fd


def admit_h1_failed_prefix_cleanup_budget_v1(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    envelope: cleanup_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    native_receipt_spec: receipts_v1.H1NativeReceiptJournalSpecV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    available_cleanup_budget: Mapping[str, int],
) -> H1FailedPrefixCleanupBudgetAdmissionV1:
    """Freeze the exact failed-prefix cleanup budget under one live lease.

    The caller must already retain PHASE -> GATE -> NORMAL.  This function then
    acquires stable read-only OWNER -> native-receipt and keeps the entire
    composite authority through the immutable admission seal publication.
    """

    lease = normal_v1._require_live_lease(lease)
    phase_handle = lease.phase_handle
    normal_handle = lease.handle
    available = _normalize_available_budget(available_cleanup_budget)
    base, normal_spec, _context, phase_payload = _require_exact_context(
        lease=lease,
        envelope=envelope,
        cleanup_analysis=cleanup_analysis,
        native_receipt_spec=native_receipt_spec,
        native_receipt_handle=native_receipt_handle,
    )
    branch_rows, maxima = _derive_branch_budget_rows(
        envelope, normal_spec, cleanup_analysis
    )
    if any(available[key] < maxima[key] for key in _CATEGORY_ORDER):
        _fail("available cleanup budget is insufficient for a registered branch maximum")

    base_fd = owner_root_fd = owner_directory_fd = -1
    native_lock_fd = native_cursor_fd = -1
    try:
        base, base_fd = _open_pinned_phase_base(phase_payload)
        normal_state = normal_v1._replay_journal_locked(
            normal_handle,
            lease._journal_root_fd,
            lease._journal_directory_fd,
            lease._journal_cursor_fd,
            repair=False,
        )
        normal_snapshot = normal_v1._snapshot_from_state(
            normal_handle, normal_state
        )
        normal_document = normal_snapshot.document
        if (
            normal_document["status"]
            != normal_v1.H1NormalPrefixStatusV1.READY.value
            or normal_document["completed_event_count"] != 0
            or normal_document["next_ordinal"] != 1
            or normal_document["dangling_intent_id"]
            != _typed_null("NO_DANGLING_INTENT")
        ):
            _fail("cleanup budget admission is late or the normal prefix is stale")

        gate_state, gate_commit, gate_ack = rejection_v1._observe_gate_locked(
            lease.rejection_gate,
            lease._gate_directory_fd,
            advance_cursor=False,
        )
        if (
            gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
            or gate_commit is not None
            or gate_ack is not None
        ):
            _fail("cleanup budget admission requires the live pristine OPEN gate")
        gate_snapshot = rejection_v1.H1AttemptRejectionGateReplaySnapshotV1(
            rejection_v1._REPLAY_SNAPSHOT_ISSUER,
            lease.rejection_gate.spec.gate_id,
            gate_state,
            gate_commit,
            gate_ack,
        )
        (
            owner_root_fd,
            owner_directory_fd,
            owner_state,
            _owner_storage_before,
        ) = sidecar_v1._require_stable_owner_readonly_locked(lease.owner)
        gate_join = owner_v3._validate_owner_gate_join(
            lease.owner.owner, owner_state, gate_snapshot
        )
        admitted = envelope.payload
        if (
            owner_state.pending_cursor is not None
            or owner_v3._incomplete_pair_frontier(owner_state) is not None
            or gate_join.recovery_required
            or gate_join.status.value
            != admitted["gate_owner_join_status_at_preadmission"]
            or owner_state.sequence
            != admitted["owner_tail_sequence_at_preadmission"]
            or owner_state.head_id
            != admitted["owner_tail_head_id_at_preadmission"]
        ):
            _fail("cleanup budget admission crossed the live pristine Owner/gate cutoff")

        normal_evidence = receipts_v1._normal_evidence_from_state(normal_state)
        native_lock_fd, native_cursor_fd, native_state = receipts_v1._with_locked(
            native_receipt_handle,
            normal_evidence=normal_evidence,
            repair=False,
        )
        declared_slots = receipts_v1._declared_slots_for_handle(
            native_receipt_handle
        )
        if (
            len(declared_slots) != 12
            or native_state.records
            or native_state.starts
            or native_state.results
            or native_state.resolutions
            or native_state.cutoff is not None
            or len(native_state.cursor_rows) != 1
        ):
            _fail("cleanup budget admission is late or the V6 receipt journal is stale")
        native_replay = {
            "h1_native_receipt_journal_spec_id": native_receipt_spec.spec_id,
            "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
            "slot_count": len(declared_slots),
            "record_count": 0,
            "cursor_sequence": 0,
            "cursor_head_id": native_state.cursor_rows[0][
                "h1_native_receipt_cursor_id"
            ],
            "cutoff_snapshot_id": _typed_null("NO_CUTOFF"),
            "slot_resolutions": {
                row["slot_key"]: "NOT_STARTED" for row in declared_slots
            },
        }
        baseline = _build_prospective_sidecar_baseline(
            base=base, phase_handle=phase_handle, envelope=envelope
        )
        admission = _build_admission(
            phase_handle=phase_handle,
            normal_handle=normal_handle,
            envelope=envelope,
            cleanup_analysis=cleanup_analysis,
            baseline=baseline,
            native_receipt_spec=native_receipt_spec,
            native_receipt_handle=native_receipt_handle,
            native_replay=native_replay,
            normal_snapshot=normal_snapshot,
            branch_rows=branch_rows,
            maxima=maxima,
            available=available,
        )
        return _reconcile_or_publish(base, base_fd, admission)
    finally:
        try:
            if native_lock_fd >= 0:
                receipts_v1._unlock(native_lock_fd, native_cursor_fd)
        finally:
            try:
                if owner_directory_fd >= 0:
                    os.close(owner_directory_fd)
            finally:
                try:
                    if owner_root_fd >= 0:
                        os.close(owner_root_fd)
                finally:
                    if base_fd >= 0:
                        os.close(base_fd)


__all__ = (
    "ACTUAL_V5_SIDECAR_SPEC_ALLOCATION_PRESENT",
    "ADMISSION_DOMAIN",
    "BRANCHWISE_CLEANUP_MAXIMUM_TOTAL",
    "CLEANUP_ACTION_EXECUTION_AUTHORITY_PRESENT",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "FAILED_PREFIX_CLEANUP_BUDGET_ADMISSION_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1FailedPrefixCleanupBudgetAdmissionV1",
    "H1ProspectiveOwnerCleanupSidecarBaselineV1",
    "NATIVE_CLEANUP_EFFECT_AUTHORITY_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PROSPECTIVE_SIDECAR_BASELINE_DOMAIN",
    "REACHABLE_FAILURE_BRANCH_COUNT",
    "REGISTERED_FAILURE_BRANCH_COUNT",
    "REQUIRED_CLEANUP_BUDGET_MAXIMA",
    "SCHEMA_VERSION",
    "ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error",
    "admit_h1_failed_prefix_cleanup_budget_v1",
)
