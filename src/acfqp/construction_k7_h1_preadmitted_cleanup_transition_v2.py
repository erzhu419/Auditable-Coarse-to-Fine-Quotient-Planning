"""Pre-admitted cleanup envelope and direct normal-prefix V2 transition.

This additive 59E-C-B contract closes exactly one boundary.  Before ordinal 1
it durably freezes the complete set of cleanup branches that ordinals 1--40
may select.  After the 59E-C-A journal commits one unique first-failure event,
the same retained PHASE -> GATE -> JOURNAL lease may bind that event, the exact
gate/Owner tail, and the pre-admitted cleanup pass into a tagged V2
``NORMAL -> CLEANUP_ONLY`` transition.

No legacy dispatch trace is synthesized.  The envelope does not execute a
cleanup action, and in particular cannot authorize native output finalization,
output readback, or output-owner close.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from contextlib import contextmanager
from contextvars import ContextVar
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v4 as domains_v4
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-B"
PROFILE_KEY = "construction_k7_h1_preadmitted_cleanup_transition_v2"

PREADMITTED_CLEANUP_ENVELOPE_PRESENT = True
NORMAL_PREFIX_FAILURE_TO_CLEANUP_TRANSITION_V2_PRESENT = True
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

ENVELOPE_DOMAIN = (
    domains_v4.CONSTRUCTION_K7_H1_PREADMITTED_CLEANUP_ENVELOPE_V1_DOMAIN
)
TRANSITION_DOMAIN = (
    domains_v4.CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V2_DOMAIN
)

_ENVELOPE_ISSUER = object()
_TRANSITION_ISSUER = object()
_ENVELOPE_ROOT_NAME = ".acfqp-k7-h1-preadmitted-cleanup-v2"
_ENVELOPE_FILE = "preadmitted-cleanup-envelope.json"
_ENVELOPE_SEAL_PREFIX = "preadmitted-cleanup-envelope-v2-seal-"
_ENVELOPE_TEMP_PREFIX = ".tmp-"
_ACTIVE_V2_PHASE_LEASES: ContextVar[tuple[str, ...]] = ContextVar(
    "acfqp_k7_h1_active_v2_phase_leases", default=()
)
_V2_LEASE_ISSUER = object()

_ALLOWED_PREFIX_CLEANUP_ACTIONS = frozenset(
    {
        "CLOSE_MOUNT",
        "REAP_DESCENDANT",
        "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION",
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
        "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE",
    }
)
_FORBIDDEN_OUTPUT_AUTHORITY_ACTIONS = frozenset(
    {
        "READBACK_OUTPUT_ROLE",
        "FINALIZE_AND_SETTLE_OUTPUT_RESERVATION",
        "CLOSE_OUTPUT_OWNER",
    }
)

_ENVELOPE_PAYLOAD_FIELDS = frozenset(
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
        "h1_shared_cap_profile_core_v3_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "h1_normal_prefix_spec_id",
        "h1_normal_prefix_allocation_id",
        "h1_lifecycle_dispatch_profile_id",
        "h1_anchored_lifecycle_program_id",
        "h1_anchored_lifecycle_handler_registry_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "normal_prefix_first_ordinal",
        "normal_prefix_last_ordinal",
        "failure_branch_action_whitelist",
        "failure_branch_action_whitelist_count",
        "dispatcher_reachable_failure_branch_count",
        "owner_tail_sequence_at_preadmission",
        "owner_tail_head_id_at_preadmission",
        "gate_state_at_preadmission",
        "gate_owner_join_status_at_preadmission",
        "preadmitted_before_ordinal_1",
        "normal_completed_event_count_at_preadmission",
        "branch_selection_must_follow_unique_failed_tail_event",
        "cleanup_pass_must_be_selected_from_complete_analysis",
        "accounting_only_output_reservation_settlement_plan_present",
        "forbidden_output_authority_action_kinds",
        "legacy_dispatch_trace_translation_allowed",
        "cleanup_actions_are_structural_whitelist_only",
        "native_cleanup_capabilities_retained",
        "v3_owner_semantics_sufficient_for_cleanup_execution",
        "owner_cleanup_continuation_present",
        "native_resource_receipt_journal_present",
        "cleanup_budget_admission_present",
        "cleanup_execution_authority_present",
        "production_output_leaf_authority_present",
        "production_execution_authority_present",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "official_execution_allowed",
    }
)

_TRANSITION_PAYLOAD_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_attempt_execution_phase_spec_id",
        "h1_attempt_phase_allocation_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "h1_attempt_rejection_gate_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "h1_normal_prefix_spec_id",
        "h1_normal_prefix_allocation_id",
        "h1_preadmitted_cleanup_envelope_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "h1_lifecycle_cleanup_pass_id",
        "branch_key",
        "primary_failure_event_id",
        "primary_failure_ordinal",
        "primary_failure_site_key",
        "primary_failure_outcome",
        "primary_failure_trigger_kind",
        "owner_tail_sequence_at_transition",
        "owner_tail_head_id_at_transition",
        "gate_state_at_transition",
        "gate_rejection_commit_id_at_transition",
        "gate_rejection_ack_id_at_transition",
        "gate_owner_join_status_at_transition",
        "from_phase",
        "to_phase",
        "normal_phase_never_reopens",
        "primary_failure_immutable",
        "secondary_failures_append_only",
        "phase_gate_journal_owner_snapshot_held_during_intent_publish",
        "cleanup_envelope_preadmitted",
        "legacy_dispatch_trace_translation_used",
        "cleanup_actions_are_structural_whitelist_only",
        "native_cleanup_capabilities_retained",
        "v3_owner_semantics_sufficient_for_cleanup_execution",
        "owner_cleanup_continuation_present",
        "native_resource_receipt_journal_present",
        "cleanup_budget_admission_present",
        "cleanup_execution_authority_present",
        "production_output_leaf_authority_present",
        "production_execution_authority_present",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "official_execution_allowed",
    }
)


class ConstructionK7H1PreadmittedCleanupTransitionV2Error(ValueError):
    """The cleanup envelope or its V2 phase transition was crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1PreadmittedCleanupTransitionV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PreadmittedCleanupTransitionV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _content_id(domain: str, payload: Any) -> str:
    return domains_v4.extension_content_id_v4(domain, payload)


def _parse_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PreadmittedCleanupTransitionV2Error(
            f"{label} is not canonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


@dataclass(frozen=True, slots=True)
class H1PreadmittedCleanupEnvelopeV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("pre-admitted cleanup envelope is caller-minted")
        payload = _parse_document(self.payload_bytes, "pre-admitted cleanup envelope")
        if frozenset(payload) != _ENVELOPE_PAYLOAD_FIELDS:
            _fail("pre-admitted cleanup envelope fields changed")
        object.__setattr__(self, "_envelope_id", _content_id(ENVELOPE_DOMAIN, payload))

    @property
    def envelope_id(self) -> str:
        return self._envelope_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "pre-admitted cleanup envelope")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_preadmitted_cleanup_envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class H1AttemptCleanupTransitionV2:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _transition_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TRANSITION_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("V2 cleanup transition is caller-minted")
        payload = _parse_document(self.payload_bytes, "V2 cleanup transition")
        if frozenset(payload) != _TRANSITION_PAYLOAD_FIELDS:
            _fail("V2 cleanup transition fields changed")
        object.__setattr__(
            self, "_transition_id", _content_id(TRANSITION_DOMAIN, payload)
        )

    @property
    def transition_id(self) -> str:
        return self._transition_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "V2 cleanup transition")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_attempt_cleanup_transition_id": self.transition_id}


@dataclass(frozen=True, slots=True)
class H1NormalFailureCleanupBoundaryV2:
    """The failed event and its atomic same-outer-lease phase transition."""

    failure_event: normal_v1.H1NormalSiteEventCommitV1
    transition: H1AttemptCleanupTransitionV2

    def __post_init__(self) -> None:
        if (
            type(self.failure_event) is not normal_v1.H1NormalSiteEventCommitV1
            or self.failure_event.outcome == "SUCCESS"
            or type(self.transition) is not H1AttemptCleanupTransitionV2
            or self.transition.payload["primary_failure_event_id"]
            != self.failure_event.event_id
        ):
            _fail("normal failure/cleanup boundary is inconsistent")


def _branch_key(site_key: str, outcome: str) -> str:
    if outcome == cleanup_v1._SUPPLEMENTAL_OUTCOME:
        return f"SUPPLEMENTAL:{site_key}:{outcome}"
    return f"FAIL:{site_key}:{outcome}"


def _validate_cleanup_actions(actions: Any, *, branch_key: str) -> list[dict[str, Any]]:
    if type(actions) is not list:
        _fail("cleanup branch actions are not one ordered list")
    result: list[dict[str, Any]] = []
    for ordinal, value in enumerate(actions, start=1):
        if type(value) is not dict:
            _fail("cleanup branch contains a non-object action")
        action = dict(value)
        kind = action.get("action_kind")
        target = action.get("target")
        if (
            action.get("cleanup_ordinal") != ordinal
            or kind not in _ALLOWED_PREFIX_CLEANUP_ACTIONS
            or kind in _FORBIDDEN_OUTPUT_AUTHORITY_ACTIONS
            or action.get("primary_failure_preserved") is not True
            or action.get("secondary_failure_is_append_only") is not True
            or action.get("continue_with_later_safe_cleanup_after_secondary_failure")
            is not True
            or action.get("new_business_work_allowed") is not False
            or action.get("normal_route_reservation_allowed") is not False
            or action.get("execution_authority_present") is not False
        ):
            _fail("cleanup branch requests an unregistered or authoritative action")
        if type(target) is not str or not target:
            _fail("cleanup branch action target is invalid")
        if target.startswith("output:") and kind != (
            "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE"
        ):
            _fail("cleanup branch attempts to acquire output authority")
        result.append(action)
    return result


def _derive_failure_whitelist(
    normal_spec_payload: Mapping[str, Any],
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
) -> list[dict[str, Any]]:
    if type(cleanup_analysis) is not cleanup_v1.H1LifecycleCompleteBranchAnalysisV1:
        _fail("cleanup whitelist requires one exact complete analysis")
    contracts = normal_spec_payload.get("normal_prefix_site_contracts")
    if (
        type(contracts) is not list
        or len(contracts) != normal_v1.PREFIX_END_ORDINAL
        or [row.get("ordinal") for row in contracts]
        != list(range(1, normal_v1.PREFIX_END_ORDINAL + 1))
    ):
        _fail("normal-prefix spec lost its exact 1..40 contracts")
    contracts_by_ordinal = {row["ordinal"]: row for row in contracts}
    declared_expected = {
        _branch_key(contract["site_key"], outcome)
        for contract in contracts
        for outcome in contract["failure_outcomes"]
    }
    rows: list[dict[str, Any]] = []
    observed_declared: set[str] = set()
    observed_keys: set[str] = set()
    for branch in cleanup_analysis.branches:
        ordinal = branch.get("failed_ordinal")
        if type(ordinal) is not int or ordinal > normal_v1.PREFIX_END_ORDINAL:
            continue
        contract = contracts_by_ordinal.get(ordinal)
        if contract is None:
            _fail("complete analysis names an out-of-prefix failure ordinal")
        outcome = branch.get("first_failure_outcome")
        kind = branch.get("branch_kind")
        key = branch.get("branch_key")
        if kind == "DECLARED_FIRST_FAILURE":
            if outcome not in contract["failure_outcomes"]:
                _fail("declared cleanup branch is absent from the normal contract")
            observed_declared.add(key)
        elif kind == "SUPPLEMENTAL_DISPATCH_PROTOCOL_ABORT":
            if outcome != cleanup_v1._SUPPLEMENTAL_OUTCOME:
                _fail("supplemental cleanup branch changed its protocol outcome")
        else:
            _fail("complete analysis introduced an unknown prefix branch kind")
        expected_key = _branch_key(contract["site_key"], outcome)
        if (
            key != expected_key
            or key in observed_keys
            or branch.get("failed_site_key") != contract["site_key"]
            or branch.get("registered_resource_cleanup_plan_complete") is not True
            or branch.get("cleanup_execution_authority_present") is not False
            or type(branch.get("dispatcher_outcome_reachable")) is not bool
        ):
            _fail("normal-prefix failure branch crossed its complete analysis")
        observed_keys.add(key)
        actions = _validate_cleanup_actions(branch.get("cleanup_actions"), branch_key=key)
        cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
            cleanup_analysis, branch_key=key
        )
        if cleanup_pass.payload["planned_cleanup_actions"] != actions:
            _fail("cleanup pass differs from its exact action whitelist")
        rows.append(
            {
                "failed_ordinal": ordinal,
                "failed_site_key": contract["site_key"],
                "first_failure_outcome": outcome,
                "branch_key": key,
                "dispatcher_outcome_reachable": branch[
                    "dispatcher_outcome_reachable"
                ],
                "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
                "planned_cleanup_actions": actions,
                "planned_cleanup_action_count": len(actions),
            }
        )
    if observed_declared != declared_expected or len(rows) != len(observed_keys):
        _fail("complete analysis and normal-prefix failure universes differ")
    return rows


def _build_envelope(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    *,
    owner_sequence: int,
    owner_head: Any,
    gate_state: rejection_v1.H1AttemptRejectionGateStateV1,
    gate_join: owner_v3._GateOwnerJoinV3,
) -> H1PreadmittedCleanupEnvelopeV1:
    normal_payload = lease.handle.spec.payload
    phase_payload = lease.phase_handle.spec.payload
    analysis = cleanup_analysis.payload
    if (
        analysis["h1_lifecycle_complete_branch_analysis_id"]
        if "h1_lifecycle_complete_branch_analysis_id" in analysis
        else cleanup_analysis.analysis_id
    ) != cleanup_analysis.analysis_id:  # pragma: no cover - issuer invariant
        _fail("complete cleanup analysis identity changed")
    if (
        phase_payload["h1_lifecycle_complete_branch_analysis_id"]
        != cleanup_analysis.analysis_id
        or analysis["h1_anchored_lifecycle_program_id"]
        != normal_payload["h1_anchored_lifecycle_program_id"]
        or analysis["h1_anchored_lifecycle_handler_registry_id"]
        != normal_payload["h1_anchored_lifecycle_handler_registry_id"]
    ):
        _fail("cleanup envelope crossed its phase, program, or registry")
    whitelist = _derive_failure_whitelist(normal_payload, cleanup_analysis)
    payload = {
        "schema": "acfqp.k7_h1_preadmitted_cleanup_envelope.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": normal_payload["logical_occurrence_id"],
        "route_attempt_id": normal_payload["route_attempt_id"],
        "decision_point_id": normal_payload["decision_point_id"],
        "transaction_id": normal_payload["transaction_id"],
        "h1_attempt_execution_phase_spec_id": lease.phase_handle.spec_id,
        "h1_attempt_phase_allocation_id": lease.phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": lease.rejection_gate.spec.gate_id,
        "h1_shared_cap_profile_core_v3_id": lease.owner.profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": lease.owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": lease.owner.binding_id,
        "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
        "h1_normal_prefix_allocation_id": lease.handle.allocation_id,
        "h1_lifecycle_dispatch_profile_id": lease.dispatch_profile.profile_id,
        "h1_anchored_lifecycle_program_id": lease.bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": lease.bundle.registry.registry_id,
        "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
        "normal_prefix_first_ordinal": 1,
        "normal_prefix_last_ordinal": normal_v1.PREFIX_END_ORDINAL,
        "failure_branch_action_whitelist": whitelist,
        "failure_branch_action_whitelist_count": len(whitelist),
        "dispatcher_reachable_failure_branch_count": sum(
            row["dispatcher_outcome_reachable"] is True for row in whitelist
        ),
        "owner_tail_sequence_at_preadmission": owner_sequence,
        "owner_tail_head_id_at_preadmission": owner_head,
        "gate_state_at_preadmission": gate_state.value,
        "gate_owner_join_status_at_preadmission": gate_join.status.value,
        "preadmitted_before_ordinal_1": True,
        "normal_completed_event_count_at_preadmission": 0,
        "branch_selection_must_follow_unique_failed_tail_event": True,
        "cleanup_pass_must_be_selected_from_complete_analysis": True,
        "accounting_only_output_reservation_settlement_plan_present": True,
        "forbidden_output_authority_action_kinds": sorted(
            _FORBIDDEN_OUTPUT_AUTHORITY_ACTIONS
        ),
        "legacy_dispatch_trace_translation_allowed": False,
        "cleanup_actions_are_structural_whitelist_only": True,
        "native_cleanup_capabilities_retained": False,
        "v3_owner_semantics_sufficient_for_cleanup_execution": False,
        "owner_cleanup_continuation_present": False,
        "native_resource_receipt_journal_present": False,
        "cleanup_budget_admission_present": False,
        "cleanup_execution_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1PreadmittedCleanupEnvelopeV1(
        _ENVELOPE_ISSUER, canonical_json_bytes(payload)
    )


def _envelope_from_raw(raw: bytes) -> H1PreadmittedCleanupEnvelopeV1:
    document = _parse_document(raw, "pre-admitted cleanup envelope file")
    claimed = _cid(
        document.pop("h1_preadmitted_cleanup_envelope_id", None),
        "pre-admitted cleanup envelope",
    )
    envelope = H1PreadmittedCleanupEnvelopeV1(
        _ENVELOPE_ISSUER, canonical_json_bytes(document)
    )
    payload = envelope.payload
    if (
        envelope.envelope_id != claimed
        or envelope.canonical_bytes != raw
        or payload["schema"] != "acfqp.k7_h1_preadmitted_cleanup_envelope.v1"
        or payload["schema_version"] != SCHEMA_VERSION
        or payload["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or payload["profile_key"] != PROFILE_KEY
        or payload["normal_prefix_first_ordinal"] != 1
        or payload["normal_prefix_last_ordinal"] != normal_v1.PREFIX_END_ORDINAL
        or payload["preadmitted_before_ordinal_1"] is not True
        or payload["normal_completed_event_count_at_preadmission"] != 0
        or payload["failure_branch_action_whitelist_count"] != 112
        or payload["dispatcher_reachable_failure_branch_count"] != 111
        or type(payload["owner_tail_sequence_at_preadmission"]) is not int
        or payload["owner_tail_sequence_at_preadmission"] < 0
        or payload["gate_state_at_preadmission"]
        != rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        or payload["gate_owner_join_status_at_preadmission"]
        != owner_v3.H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION.value
        or payload["branch_selection_must_follow_unique_failed_tail_event"]
        is not True
        or payload["cleanup_pass_must_be_selected_from_complete_analysis"]
        is not True
        or payload[
            "accounting_only_output_reservation_settlement_plan_present"
        ]
        is not True
        or payload["forbidden_output_authority_action_kinds"]
        != sorted(_FORBIDDEN_OUTPUT_AUTHORITY_ACTIONS)
        or payload["legacy_dispatch_trace_translation_allowed"] is not False
        or payload["cleanup_actions_are_structural_whitelist_only"] is not True
        or payload["native_cleanup_capabilities_retained"] is not False
        or payload["v3_owner_semantics_sufficient_for_cleanup_execution"] is not False
        or payload["owner_cleanup_continuation_present"] is not False
        or payload["native_resource_receipt_journal_present"] is not False
        or payload["cleanup_budget_admission_present"] is not False
        or payload["cleanup_execution_authority_present"] is not False
        or payload["production_output_leaf_authority_present"] is not False
        or payload["production_execution_authority_present"] is not False
        or payload["formal_counter_records_issued"] is not False
        or payload["formal_work_vector_issued"] is not False
        or payload["formal_comparison_vector_issued"] is not False
        or payload["formal_v7_route_authority_present"] is not False
        or payload["official_execution_allowed"] is not False
    ):
        _fail("pre-admitted cleanup envelope claims or identity changed")
    owner_sequence = payload["owner_tail_sequence_at_preadmission"]
    owner_head = payload["owner_tail_head_id_at_preadmission"]
    if owner_sequence == 0:
        if owner_head != _typed_null("JOURNAL_GENESIS"):
            _fail("pre-admitted cleanup envelope genesis Owner head changed")
    else:
        _cid(owner_head, "pre-admitted cleanup envelope Owner head")
    return envelope


def _envelope_seal_name(route_attempt_id: str) -> str:
    return f"{_ENVELOPE_SEAL_PREFIX}{route_attempt_id}.json"


def _open_envelope_directories(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    create: bool,
) -> tuple[int, int] | None:
    base = Path(lease.handle.spec.payload["normal_prefix_base_realpath"])
    base_fd = phase_v1._open_directory(base)
    root_fd = attempt_fd = -1
    try:
        if create:
            try:
                os.mkdir(_ENVELOPE_ROOT_NAME, 0o700, dir_fd=base_fd)
                os.fsync(base_fd)
            except FileExistsError:
                pass
        else:
            try:
                os.stat(_ENVELOPE_ROOT_NAME, dir_fd=base_fd, follow_symlinks=False)
            except FileNotFoundError:
                return None
        root_fd = phase_v1._open_directory_at(base_fd, _ENVELOPE_ROOT_NAME)
        root_metadata = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_IMODE(root_metadata.st_mode) != 0o700
        ):
            _fail("cleanup-envelope successor root is not private")
        attempt = lease.handle.route_attempt_id
        if create:
            try:
                os.mkdir(attempt, 0o700, dir_fd=root_fd)
                os.fsync(root_fd)
            except FileExistsError:
                pass
        else:
            try:
                os.stat(attempt, dir_fd=root_fd, follow_symlinks=False)
            except FileNotFoundError:
                return None
        attempt_fd = phase_v1._open_directory_at(root_fd, attempt)
        attempt_metadata = os.fstat(attempt_fd)
        if (
            not stat.S_ISDIR(attempt_metadata.st_mode)
            or stat.S_IMODE(attempt_metadata.st_mode) != 0o700
        ):
            _fail("cleanup-envelope attempt directory is not private")
        result = (root_fd, attempt_fd)
        root_fd = attempt_fd = -1
        return result
    finally:
        if attempt_fd >= 0:
            os.close(attempt_fd)
        if root_fd >= 0:
            os.close(root_fd)
        os.close(base_fd)


def _reconcile_envelope_locked(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    create: bool = False,
) -> H1PreadmittedCleanupEnvelopeV1 | None:
    opened = _open_envelope_directories(lease, create=create)
    if opened is None:
        return None
    root_fd, attempt_fd = opened
    try:
        envelope_entry = phase_v1._read_file_with_metadata(attempt_fd, _ENVELOPE_FILE)
        seal_name = _envelope_seal_name(lease.handle.route_attempt_id)
        seal_entry = phase_v1._read_file_with_metadata(root_fd, seal_name)
        if envelope_entry is None and seal_entry is not None:
            phase_v1._require_mode(seal_entry[1], 0o400, "cleanup envelope root seal")
            if not phase_v1._link_between_directories(
                root_fd, seal_name, attempt_fd, _ENVELOPE_FILE
            ):
                _fail("cleanup envelope root-seal recovery conflicted")
            envelope_entry = phase_v1._read_file_with_metadata(
                attempt_fd, _ENVELOPE_FILE
            )
        elif envelope_entry is not None and seal_entry is None:
            phase_v1._require_mode(envelope_entry[1], 0o400, "cleanup envelope")
            if not phase_v1._link_between_directories(
                attempt_fd, _ENVELOPE_FILE, root_fd, seal_name
            ):
                _fail("cleanup envelope root-seal publication conflicted")
            seal_entry = phase_v1._read_file_with_metadata(root_fd, seal_name)
        if envelope_entry is None:
            return None
        if seal_entry is None:  # pragma: no cover - exact hard-link convergence
            _fail("cleanup envelope root seal did not converge")
        phase_v1._require_mode(envelope_entry[1], 0o400, "cleanup envelope")
        phase_v1._require_mode(seal_entry[1], 0o400, "cleanup envelope root seal")
        if (
            not hmac.compare_digest(envelope_entry[0], seal_entry[0])
            or (envelope_entry[1].st_dev, envelope_entry[1].st_ino)
            != (seal_entry[1].st_dev, seal_entry[1].st_ino)
        ):
            _fail("cleanup envelope and root seal differ")
        return _envelope_from_raw(envelope_entry[0])
    finally:
        os.close(attempt_fd)
        os.close(root_fd)


def _validate_envelope_bindings(
    envelope: H1PreadmittedCleanupEnvelopeV1,
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
) -> None:
    payload = envelope.payload
    normal_payload = lease.handle.spec.payload
    _validate_envelope_against_normal_spec(envelope, lease.handle.spec)
    expected = {
        "logical_occurrence_id": normal_payload["logical_occurrence_id"],
        "route_attempt_id": normal_payload["route_attempt_id"],
        "decision_point_id": normal_payload["decision_point_id"],
        "transaction_id": normal_payload["transaction_id"],
        "h1_attempt_execution_phase_spec_id": lease.phase_handle.spec_id,
        "h1_attempt_phase_allocation_id": lease.phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": lease.rejection_gate.spec.gate_id,
        "h1_shared_cap_profile_core_v3_id": lease.owner.profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": lease.owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": lease.owner.binding_id,
        "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
        "h1_normal_prefix_allocation_id": lease.handle.allocation_id,
        "h1_lifecycle_dispatch_profile_id": lease.dispatch_profile.profile_id,
        "h1_anchored_lifecycle_program_id": lease.bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": lease.bundle.registry.registry_id,
        "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
    }
    if any(payload[key] != value for key, value in expected.items()):
        _fail("pre-admitted cleanup envelope crossed a frozen binding")
    if (
        payload["owner_tail_sequence_at_preadmission"]
        != normal_payload["owner_baseline_journal_sequence"]
        or payload["owner_tail_head_id_at_preadmission"]
        != normal_payload["owner_baseline_journal_head_id"]
        or payload["gate_state_at_preadmission"]
        != rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        or payload["gate_owner_join_status_at_preadmission"]
        != owner_v3.H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION.value
    ):
        _fail("pre-admitted cleanup envelope changed its pristine cutoff")
    expected_whitelist = _derive_failure_whitelist(normal_payload, cleanup_analysis)
    if (
        payload["failure_branch_action_whitelist"] != expected_whitelist
        or payload["failure_branch_action_whitelist_count"] != len(expected_whitelist)
        or payload["dispatcher_reachable_failure_branch_count"]
        != sum(row["dispatcher_outcome_reachable"] is True for row in expected_whitelist)
    ):
        _fail("pre-admitted cleanup envelope whitelist changed")


def preadmit_h1_normal_prefix_cleanup_envelope_v2(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
) -> H1PreadmittedCleanupEnvelopeV1:
    """Durably admit the exact cleanup universe before ordinal 1."""

    lease = normal_v1._require_live_lease(lease)
    journal_state = normal_v1._replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    existing = _reconcile_envelope_locked(lease)
    if existing is not None:
        _validate_envelope_bindings(existing, lease, cleanup_analysis)
        return existing
    if journal_state.intents or journal_state.callbacks or journal_state.events:
        _fail("cleanup envelope cannot be minted after ordinal 1 began")
    gate_state, gate_commit, gate_ack = rejection_v1._observe_gate_locked(
        lease.rejection_gate, lease._gate_directory_fd, advance_cursor=True
    )
    if (
        gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
        or gate_commit is not None
        or gate_ack is not None
    ):
        _fail("cleanup envelope requires the pristine OPEN attempt gate")
    gate_snapshot = rejection_v1.H1AttemptRejectionGateReplaySnapshotV1(
        rejection_v1._REPLAY_SNAPSHOT_ISSUER,
        lease.rejection_gate.spec.gate_id,
        gate_state,
        gate_commit,
        gate_ack,
    )
    owner_root_fd = owner_directory_fd = -1
    try:
        owner_root_fd, owner_directory_fd, owner_state = owner_v3._require_handle_locked(
            lease.owner.owner
        )
        gate_join = owner_v3._validate_owner_gate_join(
            lease.owner.owner, owner_state, gate_snapshot
        )
        if (
            owner_state.pending_cursor is not None
            or owner_v3._incomplete_pair_frontier(owner_state) is not None
            or gate_join.recovery_required
            or owner_state.sequence
            != lease.handle.spec.payload["owner_baseline_journal_sequence"]
            or owner_state.head_id
            != lease.handle.spec.payload["owner_baseline_journal_head_id"]
        ):
            _fail("cleanup envelope requires the exact pristine Owner tail")
        envelope = _build_envelope(
            lease,
            cleanup_analysis,
            owner_sequence=owner_state.sequence,
            owner_head=owner_state.head_id,
            gate_state=gate_state,
            gate_join=gate_join,
        )
    finally:
        if owner_directory_fd >= 0:
            os.close(owner_directory_fd)
        if owner_root_fd >= 0:
            os.close(owner_root_fd)
    opened = _open_envelope_directories(lease, create=True)
    if opened is None:  # pragma: no cover - create=True invariant
        _fail("cleanup envelope successor root was not created")
    envelope_root_fd, envelope_attempt_fd = opened
    try:
        if not phase_v1._publish_new(
            envelope_attempt_fd, _ENVELOPE_FILE, envelope.canonical_bytes
        ):
            existing_raw = phase_v1._read_file(envelope_attempt_fd, _ENVELOPE_FILE)
            if existing_raw is None or not hmac.compare_digest(
                existing_raw, envelope.canonical_bytes
            ):
                _fail("cleanup envelope publication conflicted")
    finally:
        os.close(envelope_attempt_fd)
        os.close(envelope_root_fd)
    sealed = _reconcile_envelope_locked(lease, create=True)
    if sealed is None or sealed.envelope_id != envelope.envelope_id:
        _fail("cleanup envelope durable seal did not bind the admitted envelope")
    return sealed


def _transition_v2_from_raw(raw: bytes) -> H1AttemptCleanupTransitionV2:
    document = _parse_document(raw, "V2 cleanup transition file")
    claimed = _cid(
        document.pop("h1_attempt_cleanup_transition_id", None),
        "V2 cleanup transition",
    )
    transition = H1AttemptCleanupTransitionV2(
        _TRANSITION_ISSUER, canonical_json_bytes(document)
    )
    payload = transition.payload
    exact_true = (
        "normal_phase_never_reopens",
        "primary_failure_immutable",
        "secondary_failures_append_only",
        "phase_gate_journal_owner_snapshot_held_during_intent_publish",
        "cleanup_envelope_preadmitted",
        "cleanup_actions_are_structural_whitelist_only",
    )
    exact_false = (
        "legacy_dispatch_trace_translation_used",
        "native_cleanup_capabilities_retained",
        "v3_owner_semantics_sufficient_for_cleanup_execution",
        "owner_cleanup_continuation_present",
        "native_resource_receipt_journal_present",
        "cleanup_budget_admission_present",
        "cleanup_execution_authority_present",
        "production_output_leaf_authority_present",
        "production_execution_authority_present",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "official_execution_allowed",
    )
    if (
        transition.transition_id != claimed
        or transition.canonical_bytes != raw
        or payload["schema"] != "acfqp.k7_h1_attempt_cleanup_transition.v2"
        or payload["schema_version"] != SCHEMA_VERSION
        or payload["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or payload["profile_key"] != PROFILE_KEY
        or payload["from_phase"] != phase_v1.H1AttemptExecutionPhaseV1.NORMAL.value
        or payload["to_phase"] != phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY.value
        or any(payload[key] is not True for key in exact_true)
        or any(payload[key] is not False for key in exact_false)
    ):
        _fail("V2 cleanup transition identity or frozen claims changed")
    return transition


def _validate_transition_v2_for_handle(
    transition: H1AttemptCleanupTransitionV2,
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
) -> None:
    if type(transition) is not H1AttemptCleanupTransitionV2:
        _fail("phase replay received a foreign V2 transition")
    payload = transition.payload
    spec = handle.spec.payload
    if (
        payload["h1_attempt_execution_phase_spec_id"] != handle.spec_id
        or payload["h1_attempt_phase_allocation_id"] != handle.allocation_id
        or payload["logical_occurrence_id"] != spec["logical_occurrence_id"]
        or payload["route_attempt_id"] != spec["route_attempt_id"]
        or payload["h1_attempt_rejection_gate_id"]
        != spec["h1_attempt_rejection_gate_id"]
        or payload["h1_lifecycle_complete_branch_analysis_id"]
        != spec["h1_lifecycle_complete_branch_analysis_id"]
    ):
        _fail("V2 cleanup transition crossed its immutable phase identity")
    for key in (
        "decision_point_id",
        "transaction_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "h1_normal_prefix_spec_id",
        "h1_normal_prefix_allocation_id",
        "h1_preadmitted_cleanup_envelope_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "h1_lifecycle_cleanup_pass_id",
        "primary_failure_event_id",
    ):
        _cid(payload[key], f"V2 cleanup transition {key}")
    if (
        type(payload["primary_failure_ordinal"]) is not int
        or not 1 <= payload["primary_failure_ordinal"] <= normal_v1.PREFIX_END_ORDINAL
        or type(payload["owner_tail_sequence_at_transition"]) is not int
        or payload["owner_tail_sequence_at_transition"] < 0
    ):
        _fail("V2 cleanup transition ordinal or Owner sequence is invalid")
    _cid(payload["owner_tail_head_id_at_transition"], "V2 transition Owner head")
    expected_branch = _branch_key(
        payload["primary_failure_site_key"], payload["primary_failure_outcome"]
    )
    expected_trigger = (
        "CAP_REJECTION"
        if payload["primary_failure_outcome"] == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
        else "LIFECYCLE_FAILURE"
    )
    if (
        payload["branch_key"] != expected_branch
        or payload["primary_failure_trigger_kind"] != expected_trigger
    ):
        _fail("V2 cleanup transition primary failure classification changed")
    try:
        rejection_v1.H1AttemptRejectionGateStateV1(
            payload["gate_state_at_transition"]
        )
        owner_v3.H1SharedGateOwnerJoinStatusV3(
            payload["gate_owner_join_status_at_transition"]
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PreadmittedCleanupTransitionV2Error(
            "V2 transition gate/Owner state is invalid"
        ) from error


def _validate_transition_v2_against_envelope(
    transition: H1AttemptCleanupTransitionV2,
    envelope: H1PreadmittedCleanupEnvelopeV1,
) -> None:
    """Rebind every transition field that the structural envelope owns."""

    payload = transition.payload
    admitted = envelope.payload
    exact_pairs = {
        "h1_attempt_execution_phase_spec_id": (
            "h1_attempt_execution_phase_spec_id"
        ),
        "h1_attempt_phase_allocation_id": "h1_attempt_phase_allocation_id",
        "logical_occurrence_id": "logical_occurrence_id",
        "route_attempt_id": "route_attempt_id",
        "decision_point_id": "decision_point_id",
        "transaction_id": "transaction_id",
        "h1_attempt_rejection_gate_id": "h1_attempt_rejection_gate_id",
        "h1_shared_cap_owner_v3_runtime_id": (
            "h1_shared_cap_owner_v3_runtime_id"
        ),
        "h1_shared_cap_owner_v4_wal_binding_id": (
            "h1_shared_cap_owner_v4_wal_binding_id"
        ),
        "h1_normal_prefix_spec_id": "h1_normal_prefix_spec_id",
        "h1_normal_prefix_allocation_id": "h1_normal_prefix_allocation_id",
        "h1_lifecycle_complete_branch_analysis_id": (
            "h1_lifecycle_complete_branch_analysis_id"
        ),
    }
    if any(
        payload[transition_key] != admitted[envelope_key]
        for transition_key, envelope_key in exact_pairs.items()
    ) or payload["h1_preadmitted_cleanup_envelope_id"] != envelope.envelope_id:
        _fail("V2 transition crossed its pre-admitted cleanup envelope")
    matches = [
        row
        for row in admitted["failure_branch_action_whitelist"]
        if row["branch_key"] == payload["branch_key"]
    ]
    if len(matches) != 1:
        _fail("V2 transition branch is absent or duplicate in its envelope")
    selected = matches[0]
    if (
        selected["dispatcher_outcome_reachable"] is not True
        or selected["failed_ordinal"] != payload["primary_failure_ordinal"]
        or selected["failed_site_key"] != payload["primary_failure_site_key"]
        or selected["first_failure_outcome"] != payload["primary_failure_outcome"]
        or selected["h1_lifecycle_cleanup_pass_id"]
        != payload["h1_lifecycle_cleanup_pass_id"]
    ):
        _fail("V2 transition does not select its exact admitted cleanup branch")


def _validate_transition_v2_gate_snapshot(
    transition: H1AttemptCleanupTransitionV2,
    snapshot: rejection_v1.H1AttemptRejectionGateReplaySnapshotV1,
) -> None:
    """Bind the persisted transition to the retained live gate observation."""

    payload = transition.payload
    if snapshot.gate_id != payload["h1_attempt_rejection_gate_id"]:
        _fail("V2 transition crossed its retained rejection gate")
    cap_rejection = payload["primary_failure_trigger_kind"] == "CAP_REJECTION"
    if cap_rejection:
        if (
            payload["gate_state_at_transition"]
            != rejection_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED.value
            or payload["gate_owner_join_status_at_transition"]
            != owner_v3.H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED.value
            or snapshot.state
            is not rejection_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED
            or snapshot.commit is None
            or snapshot.acknowledgement is None
            or payload["gate_rejection_commit_id_at_transition"]
            != snapshot.commit.commit_id
            or payload["gate_rejection_ack_id_at_transition"]
            != snapshot.acknowledgement.ack_id
        ):
            _fail("V2 cap-rejection transition differs from the retained gate")
        return
    if (
        payload["gate_state_at_transition"]
        != rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        or payload["gate_owner_join_status_at_transition"]
        != owner_v3.H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION.value
        or payload["gate_rejection_commit_id_at_transition"]
        != _typed_null("NO_REJECTION_COMMIT")
        or payload["gate_rejection_ack_id_at_transition"]
        != _typed_null("NO_REJECTION_ACK")
        or snapshot.state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
        or snapshot.commit is not None
        or snapshot.acknowledgement is not None
    ):
        _fail("V2 lifecycle-failure transition differs from the retained gate")


def _selected_whitelist_entry(
    envelope: H1PreadmittedCleanupEnvelopeV1,
    event: Mapping[str, Any],
) -> dict[str, Any]:
    key = _branch_key(event["site_key"], event["outcome"])
    matches = [
        row
        for row in envelope.payload["failure_branch_action_whitelist"]
        if row["branch_key"] == key
    ]
    if len(matches) != 1:
        _fail("failed normal-prefix event is absent or duplicate in the envelope")
    selected = matches[0]
    if (
        selected["failed_ordinal"] != event["ordinal"]
        or selected["failed_site_key"] != event["site_key"]
        or selected["first_failure_outcome"] != event["outcome"]
        or selected["dispatcher_outcome_reachable"] is not True
    ):
        _fail("failed normal-prefix event crossed its envelope branch")
    return selected


def transition_failed_h1_normal_prefix_to_cleanup_only_v2(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    envelope: H1PreadmittedCleanupEnvelopeV1,
    crash_point: phase_v1.H1AttemptPhaseCrashPointV1 = (
        phase_v1.H1AttemptPhaseCrashPointV1.NONE
    ),
) -> H1AttemptCleanupTransitionV2:
    """Commit one V2 transition without constructing a legacy dispatch trace."""

    lease = normal_v1._require_live_lease(lease)
    try:
        fault = phase_v1.H1AttemptPhaseCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PreadmittedCleanupTransitionV2Error(
            "V2 phase transition crash point is invalid"
        ) from error
    if type(envelope) is not H1PreadmittedCleanupEnvelopeV1:
        _fail("V2 transition requires one issuer-owned cleanup envelope")
    durable_envelope = _reconcile_envelope_locked(lease)
    if (
        durable_envelope is None
        or durable_envelope.envelope_id != envelope.envelope_id
        or not hmac.compare_digest(
            durable_envelope.canonical_bytes, envelope.canonical_bytes
        )
    ):
        _fail("V2 transition envelope is absent, crossed, or not pre-admitted")
    _validate_envelope_bindings(durable_envelope, lease, cleanup_analysis)
    journal_state = normal_v1._replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    if (
        not journal_state.failed
        or journal_state.dangling_intent is not None
        or not journal_state.events
        or len(journal_state.events) > normal_v1.PREFIX_END_ORDINAL
        or any(event["outcome"] != "SUCCESS" for event in journal_state.events[:-1])
    ):
        _fail("V2 transition requires one unique durable failed tail event")
    failure = journal_state.events[-1]
    selected = _selected_whitelist_entry(durable_envelope, failure)
    cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
        cleanup_analysis, branch_key=selected["branch_key"]
    )
    if (
        cleanup_pass.pass_id != selected["h1_lifecycle_cleanup_pass_id"]
        or cleanup_pass.payload["planned_cleanup_actions"]
        != selected["planned_cleanup_actions"]
    ):
        _fail("selected cleanup pass differs from the pre-admitted envelope")
    gate_state, gate_commit, gate_ack = rejection_v1._observe_gate_locked(
        lease.rejection_gate, lease._gate_directory_fd, advance_cursor=True
    )
    gate_snapshot = rejection_v1.H1AttemptRejectionGateReplaySnapshotV1(
        rejection_v1._REPLAY_SNAPSHOT_ISSUER,
        lease.rejection_gate.spec.gate_id,
        gate_state,
        gate_commit,
        gate_ack,
    )
    owner_root_fd = owner_directory_fd = -1
    try:
        owner_root_fd, owner_directory_fd, owner_state = owner_v3._require_handle_locked(
            lease.owner.owner
        )
        owner_sequence, owner_head, owner_rows = normal_v1._owner_tail_records(
            owner_directory_fd
        )
        normal_v1._verify_durable_event_owner_deltas(journal_state, owner_rows)
        expected_sequence, expected_head = normal_v1._expected_owner_tail(
            lease, journal_state
        )
        gate_join = owner_v3._validate_owner_gate_join(
            lease.owner.owner, owner_state, gate_snapshot
        )
        if (
            owner_state.pending_cursor is not None
            or owner_v3._incomplete_pair_frontier(owner_state) is not None
            or gate_join.recovery_required
            or owner_sequence != expected_sequence
            or owner_head != expected_head
            or failure["owner_journal_sequence_after_site"] != owner_sequence
            or failure["owner_journal_head_id_after_site"] != owner_head
        ):
            _fail("V2 transition requires the exact failed-event Owner tail")
        refs = failure["owner_record_refs"]
        if failure["outcome"] == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            if (
                gate_commit is None
                or gate_ack is None
                or refs["rejection_commit_id"] != gate_commit.commit_id
                or refs["rejection_ack_id"] != gate_ack.ack_id
            ):
                _fail("cap failure event differs from the exact gate rejection")
        elif (
            gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
            or gate_commit is not None
            or gate_ack is not None
            or refs["rejection_commit_id"] != _typed_null("NO_CAP_REJECTION")
            or refs["rejection_ack_id"] != _typed_null("NO_CAP_REJECTION")
        ):
            _fail("lifecycle failure event crossed a rejection gate")
        payload = {
            "schema": "acfqp.k7_h1_attempt_cleanup_transition.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_attempt_execution_phase_spec_id": lease.phase_handle.spec_id,
            "h1_attempt_phase_allocation_id": lease.phase_handle.allocation_id,
            "logical_occurrence_id": lease.handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": lease.handle.route_attempt_id,
            "decision_point_id": lease.owner.profile.decision_point_id,
            "transaction_id": lease.owner.profile.transaction_id,
            "h1_attempt_rejection_gate_id": lease.rejection_gate.spec.gate_id,
            "h1_shared_cap_owner_v3_runtime_id": lease.owner.runtime_id,
            "h1_shared_cap_owner_v4_wal_binding_id": lease.owner.binding_id,
            "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
            "h1_normal_prefix_allocation_id": lease.handle.allocation_id,
            "h1_preadmitted_cleanup_envelope_id": durable_envelope.envelope_id,
            "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
            "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
            "branch_key": selected["branch_key"],
            "primary_failure_event_id": failure["h1_normal_site_event_commit_id"],
            "primary_failure_ordinal": failure["ordinal"],
            "primary_failure_site_key": failure["site_key"],
            "primary_failure_outcome": failure["outcome"],
            "primary_failure_trigger_kind": (
                "CAP_REJECTION"
                if failure["outcome"] == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
                else "LIFECYCLE_FAILURE"
            ),
            "owner_tail_sequence_at_transition": owner_sequence,
            "owner_tail_head_id_at_transition": owner_head,
            "gate_state_at_transition": gate_state.value,
            "gate_rejection_commit_id_at_transition": (
                gate_commit.commit_id
                if gate_commit is not None
                else _typed_null("NO_REJECTION_COMMIT")
            ),
            "gate_rejection_ack_id_at_transition": (
                gate_ack.ack_id
                if gate_ack is not None
                else _typed_null("NO_REJECTION_ACK")
            ),
            "gate_owner_join_status_at_transition": gate_join.status.value,
            "from_phase": phase_v1.H1AttemptExecutionPhaseV1.NORMAL.value,
            "to_phase": phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY.value,
            "normal_phase_never_reopens": True,
            "primary_failure_immutable": True,
            "secondary_failures_append_only": True,
            "phase_gate_journal_owner_snapshot_held_during_intent_publish": True,
            "cleanup_envelope_preadmitted": True,
            "legacy_dispatch_trace_translation_used": False,
            "cleanup_actions_are_structural_whitelist_only": True,
            "native_cleanup_capabilities_retained": False,
            "v3_owner_semantics_sufficient_for_cleanup_execution": False,
            "owner_cleanup_continuation_present": False,
            "native_resource_receipt_journal_present": False,
            "cleanup_budget_admission_present": False,
            "cleanup_execution_authority_present": False,
            "production_output_leaf_authority_present": False,
            "production_execution_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "official_execution_allowed": False,
        }
        transition = H1AttemptCleanupTransitionV2(
            _TRANSITION_ISSUER, canonical_json_bytes(payload)
        )
        _validate_transition_v2_against_envelope(transition, durable_envelope)
        _validate_transition_v2_gate_snapshot(transition, gate_snapshot)
        # The lease is consumed before the first immutable publication.  A
        # caught crash/injected exception can therefore never resume NORMAL in
        # this process with the same authority.
        lease._site_consumed = True
        lease._active = False
        existing = phase_v1._read_file(lease._phase_directory_fd, phase_v1._INTENT_FILE)
        if existing is None:
            if not phase_v1._publish_new(
                lease._phase_directory_fd,
                phase_v1._INTENT_FILE,
                transition.canonical_bytes,
            ):
                _fail("V2 cleanup transition intent publication conflicted")
        elif not hmac.compare_digest(existing, transition.canonical_bytes):
            _fail("attempt already has a different primary cleanup transition")
        if fault is phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC:
            raise phase_v1.H1AttemptPhaseInjectedCrashV1(
                "V2 phase crash after intent fsync"
            )
        sealed = phase_v1._reconcile_root_transition_seal_locked(
            lease._phase_root_fd, lease._phase_directory_fd, lease.phase_handle
        )
        if sealed is None or not hmac.compare_digest(
            sealed[0], transition.canonical_bytes
        ):
            _fail("V2 root transition seal did not bind the exact intent")
        records = phase_v1._read_repairable_cursor_locked(
            lease._phase_cursor_fd,
            lease.phase_handle.spec_id,
            transition_id=transition.transition_id,
        )
        if (
            phase_v1.H1AttemptExecutionPhaseV1(records[-1]["state"])
            is phase_v1.H1AttemptExecutionPhaseV1.NORMAL
        ):
            records = phase_v1._append_cursor(
                lease._phase_cursor_fd,
                records,
                spec_id=lease.phase_handle.spec_id,
                state=phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE,
                transition_id=transition.transition_id,
            )
        if fault is phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_CURSOR_FSYNC:
            raise phase_v1.H1AttemptPhaseInjectedCrashV1(
                "V2 phase crash after intent cursor fsync"
            )
        if not phase_v1._link_intent_to_commit(lease._phase_directory_fd):
            commit = phase_v1._read_file(
                lease._phase_directory_fd, phase_v1._COMMIT_FILE
            )
            if commit is None or not hmac.compare_digest(
                commit, transition.canonical_bytes
            ):
                _fail("V2 cleanup transition commit conflicted")
        if fault is phase_v1.H1AttemptPhaseCrashPointV1.AFTER_COMMIT_LINK_FSYNC:
            raise phase_v1.H1AttemptPhaseInjectedCrashV1(
                "V2 phase crash after commit link fsync"
            )
        records = phase_v1._read_repairable_cursor_locked(
            lease._phase_cursor_fd,
            lease.phase_handle.spec_id,
            transition_id=transition.transition_id,
        )
        if (
            phase_v1.H1AttemptExecutionPhaseV1(records[-1]["state"])
            is phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
        ):
            phase_v1._append_cursor(
                lease._phase_cursor_fd,
                records,
                spec_id=lease.phase_handle.spec_id,
                state=phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY,
                transition_id=transition.transition_id,
            )
        if fault is phase_v1.H1AttemptPhaseCrashPointV1.AFTER_CLEANUP_CURSOR_FSYNC:
            raise phase_v1.H1AttemptPhaseInjectedCrashV1(
                "V2 phase crash after cleanup cursor fsync"
            )
        return transition
    finally:
        if owner_directory_fd >= 0:
            os.close(owner_directory_fd)
        if owner_root_fd >= 0:
            os.close(owner_root_fd)


def execute_next_h1_normal_site_to_cleanup_boundary_v2(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    envelope: H1PreadmittedCleanupEnvelopeV1,
    callback: Any = None,
    normal_crash_point: normal_v1.H1NormalPrefixCrashPointV1 = (
        normal_v1.H1NormalPrefixCrashPointV1.NONE
    ),
    transition_crash_point: phase_v1.H1AttemptPhaseCrashPointV1 = (
        phase_v1.H1AttemptPhaseCrashPointV1.NONE
    ),
) -> (
    normal_v1.H1NormalSiteEventCommitV1
    | normal_v1.H1NormalPrefixSnapshotV1
    | H1NormalFailureCleanupBoundaryV2
):
    """Execute one site and never return a bare durable failure event."""

    lease = normal_v1._require_live_lease(lease)
    durable_envelope = _reconcile_envelope_locked(lease)
    if (
        type(envelope) is not H1PreadmittedCleanupEnvelopeV1
        or durable_envelope is None
        or durable_envelope.envelope_id != envelope.envelope_id
        or not hmac.compare_digest(durable_envelope.canonical_bytes, envelope.canonical_bytes)
    ):
        _fail("integrated normal-site execution requires its durable envelope")
    _validate_envelope_bindings(durable_envelope, lease, cleanup_analysis)
    result = normal_v1.execute_next_h1_phase_aware_normal_site_v1(
        lease, callback=callback, crash_point=normal_crash_point
    )
    if (
        type(result) is normal_v1.H1NormalSiteEventCommitV1
        and result.outcome != "SUCCESS"
    ):
        transition = transition_failed_h1_normal_prefix_to_cleanup_only_v2(
            lease,
            cleanup_analysis=cleanup_analysis,
            envelope=envelope,
            crash_point=transition_crash_point,
        )
        return H1NormalFailureCleanupBoundaryV2(result, transition)
    return result


def recover_h1_normal_site_to_cleanup_boundary_v2(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
    envelope: H1PreadmittedCleanupEnvelopeV1,
    transition_crash_point: phase_v1.H1AttemptPhaseCrashPointV1 = (
        phase_v1.H1AttemptPhaseCrashPointV1.NONE
    ),
) -> (
    normal_v1.H1NormalSiteEventCommitV1
    | normal_v1.H1NormalPrefixSnapshotV1
    | H1NormalFailureCleanupBoundaryV2
):
    """Recover a pending site without accepting or reexecuting a callback."""

    lease = normal_v1._require_live_lease(lease)
    durable_envelope = _reconcile_envelope_locked(lease)
    if (
        type(envelope) is not H1PreadmittedCleanupEnvelopeV1
        or durable_envelope is None
        or durable_envelope.envelope_id != envelope.envelope_id
        or not hmac.compare_digest(durable_envelope.canonical_bytes, envelope.canonical_bytes)
    ):
        _fail("integrated normal-site recovery requires its durable envelope")
    _validate_envelope_bindings(durable_envelope, lease, cleanup_analysis)
    result = normal_v1.recover_pending_h1_phase_aware_normal_site_v1(lease)
    state = normal_v1._replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    if state.failed:
        event = normal_v1.H1NormalSiteEventCommitV1(
            normal_v1._EVENT_ISSUER,
            canonical_json_bytes(state.events[-1]),
        )
        transition = transition_failed_h1_normal_prefix_to_cleanup_only_v2(
            lease,
            cleanup_analysis=cleanup_analysis,
            envelope=envelope,
            crash_point=transition_crash_point,
        )
        return H1NormalFailureCleanupBoundaryV2(event, transition)
    return result


def _load_envelope_for_phase_handle(
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
) -> H1PreadmittedCleanupEnvelopeV1:
    base = Path(handle.spec.payload["phase_base_realpath"])
    root_fd = phase_v1._open_directory(base / _ENVELOPE_ROOT_NAME)
    attempt_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_IMODE(root_metadata.st_mode) != 0o700
        ):
            _fail("V2 phase replay cleanup-envelope root is not private")
        attempt_fd = phase_v1._open_directory_at(root_fd, handle.route_attempt_id)
        attempt_metadata = os.fstat(attempt_fd)
        if (
            not stat.S_ISDIR(attempt_metadata.st_mode)
            or stat.S_IMODE(attempt_metadata.st_mode) != 0o700
        ):
            _fail("V2 phase replay cleanup-envelope attempt is not private")
        envelope_entry = phase_v1._read_file_with_metadata(attempt_fd, _ENVELOPE_FILE)
        seal_entry = phase_v1._read_file_with_metadata(
            root_fd, _envelope_seal_name(handle.route_attempt_id)
        )
        if envelope_entry is None or seal_entry is None:
            _fail("V2 phase replay lost its pre-admitted cleanup envelope")
        phase_v1._require_mode(envelope_entry[1], 0o400, "cleanup envelope")
        phase_v1._require_mode(seal_entry[1], 0o400, "cleanup envelope root seal")
        if (
            not hmac.compare_digest(envelope_entry[0], seal_entry[0])
            or (envelope_entry[1].st_dev, envelope_entry[1].st_ino)
            != (seal_entry[1].st_dev, seal_entry[1].st_ino)
        ):
            _fail("V2 phase replay cleanup envelope seal changed")
        envelope = _envelope_from_raw(envelope_entry[0])
        payload = envelope.payload
        if (
            payload["route_attempt_id"] != handle.route_attempt_id
            or payload["logical_occurrence_id"]
            != handle.spec.payload["logical_occurrence_id"]
            or payload["h1_attempt_execution_phase_spec_id"] != handle.spec_id
            or payload["h1_attempt_phase_allocation_id"] != handle.allocation_id
            or payload["h1_attempt_rejection_gate_id"]
            != handle.spec.payload["h1_attempt_rejection_gate_id"]
            or payload["h1_lifecycle_complete_branch_analysis_id"]
            != handle.spec.payload["h1_lifecycle_complete_branch_analysis_id"]
        ):
            _fail("V2 phase replay envelope crossed its phase handle")
        return envelope
    finally:
        if attempt_fd >= 0:
            os.close(attempt_fd)
        os.close(root_fd)


def _load_normal_prefix_spec_for_envelope(
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    envelope: H1PreadmittedCleanupEnvelopeV1,
) -> normal_v1.H1NormalPrefixSpecV1:
    """Read-only rebind of the envelope cutoff to its immutable normal spec."""

    base = Path(handle.spec.payload["phase_base_realpath"])
    root_fd = phase_v1._open_directory(base / normal_v1._ROOT_NAME)
    journal_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_IMODE(root_metadata.st_mode) != 0o700
        ):
            _fail("normal-prefix root for V2 preflight is not private")
        journal_fd = phase_v1._open_directory_at(root_fd, handle.route_attempt_id)
        journal_metadata = os.fstat(journal_fd)
        if (
            not stat.S_ISDIR(journal_metadata.st_mode)
            or stat.S_IMODE(journal_metadata.st_mode) != 0o700
        ):
            _fail("normal-prefix journal for V2 preflight is not private")
        spec_entry = phase_v1._read_file_with_metadata(
            journal_fd, normal_v1._SPEC_FILE
        )
        allocation_entry = phase_v1._read_file_with_metadata(
            root_fd, normal_v1._allocation_name(handle.route_attempt_id)
        )
        if spec_entry is None or allocation_entry is None:
            _fail("V2 preflight lost its normal-prefix spec or allocation")
        phase_v1._require_mode(spec_entry[1], 0o400, "normal-prefix spec")
        phase_v1._require_mode(
            allocation_entry[1], 0o400, "normal-prefix allocation"
        )
        document = _parse_document(spec_entry[0], "normal-prefix preflight spec")
        claimed = _cid(
            document.pop("h1_normal_prefix_spec_id", None),
            "normal-prefix preflight spec",
        )
        spec = normal_v1.H1NormalPrefixSpecV1(
            normal_v1._SPEC_ISSUER, canonical_json_bytes(document)
        )
        if (
            spec.spec_id != claimed
            or canonical_json_bytes(spec.to_document()) != spec_entry[0]
            or spec.spec_id != envelope.payload["h1_normal_prefix_spec_id"]
        ):
            _fail("V2 preflight normal-prefix spec identity changed")
        allocation, allocation_id = normal_v1._parse_allocation_document(
            allocation_entry[0], spec
        )
        if (
            allocation_id != envelope.payload["h1_normal_prefix_allocation_id"]
            or allocation["normal_prefix_root_device"] != root_metadata.st_dev
            or allocation["normal_prefix_root_inode"] != root_metadata.st_ino
            or allocation["normal_prefix_journal_device"]
            != journal_metadata.st_dev
            or allocation["normal_prefix_journal_inode"]
            != journal_metadata.st_ino
        ):
            _fail("V2 preflight normal-prefix allocation changed")
        return spec
    finally:
        if journal_fd >= 0:
            os.close(journal_fd)
        os.close(root_fd)


def _validate_envelope_against_normal_spec(
    envelope: H1PreadmittedCleanupEnvelopeV1,
    spec: normal_v1.H1NormalPrefixSpecV1,
) -> None:
    admitted = envelope.payload
    normal = spec.payload
    expected = {
        "logical_occurrence_id": normal["logical_occurrence_id"],
        "route_attempt_id": normal["route_attempt_id"],
        "decision_point_id": normal["decision_point_id"],
        "transaction_id": normal["transaction_id"],
        "h1_attempt_rejection_gate_id": normal["h1_attempt_rejection_gate_id"],
        "h1_shared_cap_profile_core_v3_id": normal[
            "h1_shared_cap_profile_core_v3_id"
        ],
        "h1_shared_cap_owner_v3_runtime_id": normal[
            "h1_shared_cap_owner_v3_runtime_id"
        ],
        "h1_shared_cap_owner_v4_wal_binding_id": normal[
            "h1_shared_cap_owner_v4_wal_binding_id"
        ],
        "h1_normal_prefix_spec_id": spec.spec_id,
        "h1_lifecycle_dispatch_profile_id": normal[
            "h1_lifecycle_dispatch_profile_id"
        ],
        "h1_anchored_lifecycle_program_id": normal[
            "h1_anchored_lifecycle_program_id"
        ],
        "h1_anchored_lifecycle_handler_registry_id": normal[
            "h1_anchored_lifecycle_handler_registry_id"
        ],
        "owner_tail_sequence_at_preadmission": normal[
            "owner_baseline_journal_sequence"
        ],
        "owner_tail_head_id_at_preadmission": normal[
            "owner_baseline_journal_head_id"
        ],
    }
    if any(admitted[key] != value for key, value in expected.items()):
        _fail("V2 envelope crossed its immutable normal-prefix cutoff")


def _preflight_successor_transition_locked(
    root_fd: int,
    phase_fd: int,
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
) -> tuple[
    phase_v1.H1AttemptCleanupTransitionV1 | H1AttemptCleanupTransitionV2 | None,
    str | None,
]:
    """Validate the durable transition source without repairing phase state."""

    intent_entry = phase_v1._read_file_with_metadata(
        phase_fd, phase_v1._INTENT_FILE
    )
    seal_entry = phase_v1._read_file_with_metadata(
        root_fd,
        phase_v1._root_transition_seal_name(handle.route_attempt_id),
    )
    if intent_entry is None and seal_entry is None:
        return None, None
    for label, entry in (
        ("successor phase cleanup intent", intent_entry),
        ("successor root cleanup transition seal", seal_entry),
    ):
        if entry is not None:
            phase_v1._require_mode(entry[1], 0o400, label)
    if intent_entry is not None and seal_entry is not None:
        if (
            not hmac.compare_digest(intent_entry[0], seal_entry[0])
            or (intent_entry[1].st_dev, intent_entry[1].st_ino)
            != (seal_entry[1].st_dev, seal_entry[1].st_ino)
        ):
            _fail("successor transition intent and root seal differ")
    source = intent_entry if intent_entry is not None else seal_entry
    if source is None:  # pragma: no cover - guarded above
        _fail("successor transition preflight lost its source")
    raw = source[0]
    document = _parse_document(raw, "successor phase transition preflight")
    schema = document.get("schema")
    if schema == "acfqp.k7_h1_attempt_cleanup_transition.v1":
        transition = phase_v1._transition_from_raw(raw)
        phase_v1._validate_transition_for_handle(transition, handle)
        return transition, "V1"
    if schema != "acfqp.k7_h1_attempt_cleanup_transition.v2":
        _fail("successor phase transition schema is not registered")
    transition = _transition_v2_from_raw(raw)
    _validate_transition_v2_for_handle(transition, handle)
    envelope = _load_envelope_for_phase_handle(handle)
    normal_spec = _load_normal_prefix_spec_for_envelope(handle, envelope)
    _validate_envelope_against_normal_spec(envelope, normal_spec)
    _validate_transition_v2_against_envelope(transition, envelope)
    return transition, "V2"


def _recover_successor_phase_locked(
    root_fd: int,
    phase_fd: int,
    cursor_fd: int,
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
) -> tuple[
    phase_v1.H1AttemptExecutionPhaseV1,
    phase_v1.H1AttemptCleanupTransitionV1 | H1AttemptCleanupTransitionV2 | None,
    str | None,
]:
    """Replay V1 exactly or the disjoint tagged V2 transition."""

    phase_v1._cleanup_temps(phase_fd)
    intent_entry = phase_v1._reconcile_root_transition_seal_locked(
        root_fd, phase_fd, handle
    )
    if intent_entry is None:
        state, transition = phase_v1._recover_locked(
            root_fd, phase_fd, cursor_fd, handle
        )
        return state, transition, "V1" if transition is not None else None
    intent_raw, intent_metadata = intent_entry
    document = _parse_document(intent_raw, "successor phase transition intent")
    schema = document.get("schema")
    if schema == "acfqp.k7_h1_attempt_cleanup_transition.v1":
        state, transition = phase_v1._recover_locked(
            root_fd, phase_fd, cursor_fd, handle
        )
        return state, transition, "V1"
    if schema != "acfqp.k7_h1_attempt_cleanup_transition.v2":
        _fail("successor phase transition schema is not registered")
    phase_v1._require_mode(intent_metadata, 0o400, "V2 phase cleanup intent")
    transition = _transition_v2_from_raw(intent_raw)
    _validate_transition_v2_for_handle(transition, handle)
    envelope = _load_envelope_for_phase_handle(handle)
    _validate_transition_v2_against_envelope(transition, envelope)
    commit_entry = phase_v1._read_file_with_metadata(phase_fd, phase_v1._COMMIT_FILE)
    if commit_entry is not None:
        phase_v1._require_mode(commit_entry[1], 0o400, "V2 phase cleanup commit")
        if (
            not hmac.compare_digest(commit_entry[0], intent_raw)
            or (commit_entry[1].st_dev, commit_entry[1].st_ino)
            != (intent_metadata.st_dev, intent_metadata.st_ino)
        ):
            _fail("V2 phase cleanup commit is not the immutable intent hard link")
    records = phase_v1._read_repairable_cursor_locked(
        cursor_fd, handle.spec_id, transition_id=transition.transition_id
    )
    state = phase_v1.H1AttemptExecutionPhaseV1(records[-1]["state"])
    if state is phase_v1.H1AttemptExecutionPhaseV1.NORMAL:
        records = phase_v1._append_cursor(
            cursor_fd,
            records,
            spec_id=handle.spec_id,
            state=phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE,
            transition_id=transition.transition_id,
        )
        state = phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
    if records[-1]["h1_attempt_cleanup_transition_id"] != transition.transition_id:
        _fail("V2 phase cursor and intent name different transitions")
    if state is phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE:
        if commit_entry is None:
            if not phase_v1._link_intent_to_commit(phase_fd):
                _fail("V2 phase cleanup commit link conflicted")
            commit_entry = phase_v1._read_file_with_metadata(
                phase_fd, phase_v1._COMMIT_FILE
            )
        if commit_entry is None or not hmac.compare_digest(
            commit_entry[0], intent_raw
        ):
            _fail("V2 phase cleanup commit did not converge")
        phase_v1._require_mode(commit_entry[1], 0o400, "V2 phase cleanup commit")
        if (commit_entry[1].st_dev, commit_entry[1].st_ino) != (
            intent_metadata.st_dev,
            intent_metadata.st_ino,
        ):
            _fail("V2 phase cleanup commit is not the immutable intent hard link")
        records = phase_v1._append_cursor(
            cursor_fd,
            records,
            spec_id=handle.spec_id,
            state=phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY,
            transition_id=transition.transition_id,
        )
        state = phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY
    if (
        state is not phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY
        or commit_entry is None
    ):
        _fail("V2 phase transition lacks its commit or did not converge")
    return state, transition, "V2"


def replay_h1_attempt_execution_phase_owner_v2(
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> dict[str, Any]:
    """Replay historical V1 or tagged V2 without changing V1 source bytes."""

    phase_v1._validate_live_gate(handle.spec, rejection_gate)
    root_fd, phase_fd, lock_fd, cursor_fd = phase_v1._require_handle_locked(handle)
    gate_context: Any | None = None
    try:
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        gate_snapshot = gate_context.__enter__()
        preflight, preflight_version = _preflight_successor_transition_locked(
            root_fd, phase_fd, handle
        )
        if type(preflight) is H1AttemptCleanupTransitionV2:
            _validate_transition_v2_gate_snapshot(preflight, gate_snapshot)
        state, transition, transition_version = _recover_successor_phase_locked(
            root_fd, phase_fd, cursor_fd, handle
        )
        if (
            transition_version != preflight_version
            or (transition is None) != (preflight is None)
            or (
                transition is not None
                and preflight is not None
                and transition.transition_id != preflight.transition_id
            )
        ):
            _fail("successor transition changed after retained-gate preflight")
        gate_state = gate_snapshot.state.value
    finally:
        if gate_context is not None:
            gate_context.__exit__(None, None, None)
        phase_v1._release_locked(root_fd, phase_fd, lock_fd, cursor_fd)
    return {
        "schema": "acfqp.k7_h1_attempt_execution_phase_replay.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_attempt_execution_phase_spec_id": handle.spec_id,
        "h1_attempt_phase_allocation_id": handle.allocation_id,
        "state": state.value,
        "h1_attempt_cleanup_transition_id": (
            transition.transition_id
            if transition is not None
            else _typed_null("NO_CLEANUP_TRANSITION")
        ),
        "transition_schema_version": (
            transition_version
            if transition_version is not None
            else _typed_null("NO_CLEANUP_TRANSITION")
        ),
        "h1_attempt_rejection_gate_id": rejection_gate.spec.gate_id,
        "rejection_gate_state": gate_state,
        "v1_transition_parser_delegated_exactly": transition_version == "V1",
        "v1_phase_owner_source_modified": False,
        "cleanup_only_allowed_by_successor_phase": (
            state is phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY
        ),
        "cleanup_execution_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_records_issued": False,
        "official_execution_allowed": False,
    }


@dataclass(slots=True)
class H1AttemptCleanupOnlyLeaseV2:
    _issuer: InitVar[object]
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1
    transition: H1AttemptCleanupTransitionV2
    _root_fd: int = field(repr=False)
    _phase_fd: int = field(repr=False)
    _lock_fd: int = field(repr=False)
    _cursor_fd: int = field(repr=False)
    _gate_context: Any = field(repr=False)
    _gate_snapshot: rejection_v1.H1AttemptRejectionGateReplaySnapshotV1 = field(
        repr=False
    )
    _owner_pid: int = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    _active: bool = field(default=True, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _V2_LEASE_ISSUER:
            _fail("V2 cleanup-only lease is caller-minted")

    def __reduce__(self) -> NoReturn:
        _fail("V2 cleanup-only lease is not serializable")


@contextmanager
def hold_h1_attempt_cleanup_only_lease_v2(
    handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    expected_transition_id: str,
) -> Any:
    """Retain PHASE -> GATE after one exact tagged V2 transition.

    The lease is only a phase barrier.  It carries no cleanup executor,
    resource capability, Owner continuation, or cleanup-budget admission.
    """

    phase_v1._validate_live_gate(handle.spec, rejection_gate)
    expected = _cid(expected_transition_id, "expected V2 cleanup transition")
    if _ACTIVE_V2_PHASE_LEASES.get():
        _fail("V2 cleanup-only leases cannot nest")
    owner_pid = os.getpid()
    owner_thread_id = __import__("threading").get_ident()
    successor_token = _ACTIVE_V2_PHASE_LEASES.set((handle.spec_id,))
    phase_token: Any | None = None
    root_fd = phase_fd = lock_fd = cursor_fd = -1
    gate_context: Any | None = None
    lease: H1AttemptCleanupOnlyLeaseV2 | None = None
    try:
        phase_token = phase_v1._activate_lease_context(handle)
        root_fd, phase_fd, lock_fd, cursor_fd = phase_v1._require_handle_locked(handle)
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        gate_snapshot = gate_context.__enter__()
        preflight, preflight_version = _preflight_successor_transition_locked(
            root_fd, phase_fd, handle
        )
        if (
            preflight_version != "V2"
            or type(preflight) is not H1AttemptCleanupTransitionV2
            or preflight.transition_id != expected
        ):
            _fail("V2 cleanup-only lease requires its exact preflight transition")
        _validate_transition_v2_gate_snapshot(preflight, gate_snapshot)
        state, transition, version = _recover_successor_phase_locked(
            root_fd, phase_fd, cursor_fd, handle
        )
        if (
            state is not phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_ONLY
            or version != "V2"
            or type(transition) is not H1AttemptCleanupTransitionV2
            or transition.transition_id != preflight.transition_id
        ):
            _fail("V2 cleanup-only lease requires the exact committed V2 transition")
        lease = H1AttemptCleanupOnlyLeaseV2(
            _V2_LEASE_ISSUER,
            handle,
            rejection_gate,
            transition,
            root_fd,
            phase_fd,
            lock_fd,
            cursor_fd,
            gate_context,
            gate_snapshot,
            owner_pid,
            owner_thread_id,
        )
        yield lease
    finally:
        current_pid = os.getpid()
        current_thread_id = __import__("threading").get_ident()
        if current_pid == owner_pid and current_thread_id == owner_thread_id:
            if lease is not None:
                lease._active = False
            if gate_context is not None:
                gate_context.__exit__(None, None, None)
            if root_fd >= 0:
                phase_v1._release_locked(
                    root_fd, phase_fd, lock_fd, cursor_fd
                )
            if phase_token is not None:
                phase_v1._ACTIVE_PHASE_LEASES.reset(phase_token)
            _ACTIVE_V2_PHASE_LEASES.reset(successor_token)
        elif current_pid != owner_pid:
            if lease is not None:
                lease._active = False
            if gate_context is not None:
                gate_context.__exit__(None, None, None)
            if root_fd >= 0:
                phase_v1._close_fork_inherited_locked(
                    root_fd, phase_fd, lock_fd, cursor_fd
                )
            phase_v1._ACTIVE_PHASE_LEASES.set(())
            _ACTIVE_V2_PHASE_LEASES.set(())
        else:
            _fail("V2 cleanup-only lease crossed its owning thread")


__all__ = (
    "ConstructionK7H1PreadmittedCleanupTransitionV2Error",
    "H1AttemptCleanupTransitionV2",
    "H1PreadmittedCleanupEnvelopeV1",
    "H1AttemptCleanupOnlyLeaseV2",
    "H1NormalFailureCleanupBoundaryV2",
    "NORMAL_PREFIX_FAILURE_TO_CLEANUP_TRANSITION_V2_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PREADMITTED_CLEANUP_ENVELOPE_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "preadmit_h1_normal_prefix_cleanup_envelope_v2",
    "execute_next_h1_normal_site_to_cleanup_boundary_v2",
    "hold_h1_attempt_cleanup_only_lease_v2",
    "recover_h1_normal_site_to_cleanup_boundary_v2",
    "replay_h1_attempt_execution_phase_owner_v2",
    "transition_failed_h1_normal_prefix_to_cleanup_only_v2",
)
